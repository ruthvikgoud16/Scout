"""HackTrack backend API tests.

Covers:
- root, stats, hackathons list & filters, single hackathon, 404, companies, resources
- prep generation via Gemini (AI, ~30-60s)
- refresh background task
- chat stream SSE + chat history
"""
import os
import json
import time
import uuid
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else "https://recruit-pulse-9.preview.emergentagent.com"
API = f"{BASE_URL}/api"


@pytest.fixture(scope="session")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def hackathons(client):
    r = client.get(f"{API}/hackathons")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 10
    return data


# ------------- Basic endpoints -------------
class TestBasics:
    def test_root(self, client):
        r = client.get(f"{API}/")
        assert r.status_code == 200
        body = r.json()
        assert body.get("app") == "HackTrack"
        assert body.get("status") == "live"

    def test_stats(self, client):
        r = client.get(f"{API}/stats")
        assert r.status_code == 200
        d = r.json()
        for key in ["total", "open", "upcoming", "india", "international", "companies_count", "last_refreshed_at"]:
            assert key in d, f"missing {key}"
        assert d["total"] >= 10
        assert d["india"] + d["international"] == d["total"]
        assert d["companies_count"] >= 8

    def test_companies(self, client):
        r = client.get(f"{API}/companies")
        assert r.status_code == 200
        names = r.json()
        assert isinstance(names, list)
        assert names == sorted(names)
        assert "Myntra" in names

    def test_resources(self, client):
        r = client.get(f"{API}/resources")
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d, dict)
        assert "DSA" in d
        assert "System Design" in d
        # validate items shape
        for cat, items in d.items():
            for it in items:
                assert "title" in it and "url" in it and "type" in it
                assert it["url"].startswith("http")


# ------------- Hackathons -------------
class TestHackathons:
    def test_list_all(self, hackathons):
        # sorted by registration_deadline asc
        deadlines = [h.get("registration_deadline") or "" for h in hackathons]
        assert deadlines == sorted(deadlines)

    def test_filter_region_india(self, client):
        r = client.get(f"{API}/hackathons", params={"region": "India"})
        assert r.status_code == 200
        for h in r.json():
            assert h["region"] == "India"

    def test_filter_mode_online(self, client):
        r = client.get(f"{API}/hackathons", params={"mode": "Online"})
        assert r.status_code == 200
        for h in r.json():
            assert h["mode"] == "Online"

    def test_filter_status_open(self, client):
        r = client.get(f"{API}/hackathons", params={"status": "Open"})
        assert r.status_code == 200
        for h in r.json():
            assert h["status"] == "Open"

    def test_filter_company_myntra(self, client):
        r = client.get(f"{API}/hackathons", params={"company": "Myntra"})
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        for h in data:
            assert h["company"] == "Myntra"

    def test_search_maverix(self, client):
        r = client.get(f"{API}/hackathons", params={"search": "Maverix"})
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        assert any("Maverix" in (h.get("title") or "") for h in data)

    def test_get_single(self, client, hackathons):
        hid = hackathons[0]["id"]
        r = client.get(f"{API}/hackathons/{hid}")
        assert r.status_code == 200
        h = r.json()
        assert h["id"] == hid
        for k in ["title", "company", "region", "mode", "status"]:
            assert k in h

    def test_get_invalid_id_404(self, client):
        r = client.get(f"{API}/hackathons/{uuid.uuid4()}")
        assert r.status_code == 404


# ------------- AI Prep -------------
class TestPrep:
    def test_generate_prep(self, client, hackathons):
        # Pick the Meesho Maverix hackathon for stability
        target = next((h for h in hackathons if "Maverix" in h.get("title", "")), hackathons[0])
        hid = target["id"]
        r = client.post(f"{API}/hackathons/{hid}/prep", timeout=120)
        assert r.status_code == 200, f"prep failed: {r.status_code} {r.text[:300]}"
        prep = r.json()
        assert isinstance(prep.get("rounds"), list) and len(prep["rounds"]) >= 1
        assert isinstance(prep.get("requirements"), list) and len(prep["requirements"]) >= 1
        assert isinstance(prep.get("checklist"), list) and len(prep["checklist"]) >= 1
        assert isinstance(prep.get("resources"), list) and len(prep["resources"]) >= 1
        for rd in prep["rounds"]:
            assert "name" in rd and "description" in rd
        for res in prep["resources"]:
            assert "title" in res and "url" in res and res["url"].startswith("http")
        assert prep.get("generated_at")
        # Verify persisted
        g = client.get(f"{API}/hackathons/{hid}").json()
        assert g.get("prep") is not None
        assert len(g["prep"]["rounds"]) >= 1


# ------------- Refresh -------------
class TestRefresh:
    def test_refresh_kicks_off(self, client):
        r = client.post(f"{API}/hackathons/refresh")
        assert r.status_code == 200
        assert r.json().get("status") == "refresh_started"


# ------------- Chat stream + history -------------
class TestChat:
    def test_chat_stream_and_history(self, client):
        sid = f"TEST_sess_{uuid.uuid4().hex[:8]}"
        payload = {"session_id": sid, "message": "In one short sentence, what is DSA?"}
        deltas = 0
        done = False
        err = None
        with client.post(f"{API}/chat/stream", json=payload, stream=True, timeout=90) as r:
            assert r.status_code == 200
            start = time.time()
            for raw in r.iter_lines(decode_unicode=True):
                if not raw:
                    continue
                if not raw.startswith("data:"):
                    continue
                try:
                    ev = json.loads(raw[5:].strip())
                except Exception:
                    continue
                if "delta" in ev:
                    deltas += 1
                if ev.get("done"):
                    done = True
                    break
                if ev.get("error"):
                    err = ev["error"]
                    break
                if time.time() - start > 80:
                    break
        assert err is None, f"stream error: {err}"
        assert deltas >= 1, "no delta tokens received"
        assert done, "no done event"

        # history should include both user + assistant
        time.sleep(1.0)
        h = client.get(f"{API}/chat/history/{sid}")
        assert h.status_code == 200
        msgs = h.json()
        roles = [m["role"] for m in msgs]
        assert "user" in roles
        assert "assistant" in roles
