"""OpportunityOS Iter-2 backend tests.

Covers the new features added on top of HackTrack:
- Auth (register / login / me / logout / JWT)
- Bookmarks toggle + listing
- Skills set
- Resume upload (multipart docx) + Gemini skill extraction + rejection paths
- Personalised feed
- Notify toggle
- ICS calendar export
- Scheduler/cron startup confirmation

Tests are written against the public REACT_APP_BACKEND_URL.
"""
import io
import os
import re
import uuid
import pytest
import requests
from docx import Document

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://recruit-pulse-9.preview.emergentagent.com",
).rstrip("/")
API = f"{BASE_URL}/api"

PRIMARY_EMAIL = "bathiniruthvik380@gmail.com"
PRIMARY_PASSWORD = "opportunity26"


# ------------------------- Helpers -------------------------
def _rand_email() -> str:
    return f"TEST_{uuid.uuid4().hex[:10]}@example.com"


def _make_docx_bytes(text: str) -> bytes:
    doc = Document()
    for line in text.split("\n"):
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


@pytest.fixture(scope="session")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def hackathon_id(client):
    r = client.get(f"{API}/hackathons")
    assert r.status_code == 200, r.text[:200]
    data = r.json()
    assert isinstance(data, list) and len(data) >= 1
    return data[0]["id"]


@pytest.fixture(scope="session")
def primary_token(client):
    """Login (or register) the Resend-verified primary user and return JWT."""
    r = client.post(
        f"{API}/auth/login",
        json={"email": PRIMARY_EMAIL, "password": PRIMARY_PASSWORD},
    )
    if r.status_code != 200:
        r = client.post(
            f"{API}/auth/register",
            json={"email": PRIMARY_EMAIL, "password": PRIMARY_PASSWORD, "name": "Ruthvik"},
        )
        assert r.status_code == 200, f"primary register failed: {r.status_code} {r.text[:300]}"
    return r.json()["token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ------------------------- Auth -------------------------
class TestAuth:
    def test_register_login_me_logout(self, client):
        email = _rand_email()
        # Register
        r = client.post(
            f"{API}/auth/register",
            json={"email": email, "password": "passw0rd", "name": "Test User"},
        )
        assert r.status_code == 200, r.text[:200]
        body = r.json()
        assert "token" in body and isinstance(body["token"], str) and len(body["token"]) > 10
        assert body["user"]["email"] == email.lower()
        assert body["user"]["name"] == "Test User"
        assert body["user"]["auth_provider"] == "password"
        assert body["user"]["bookmarks"] == []
        token = body["token"]

        # Duplicate register → 400
        r2 = client.post(
            f"{API}/auth/register",
            json={"email": email, "password": "passw0rd", "name": "Test User"},
        )
        assert r2.status_code == 400

        # Short password → 400
        r3 = client.post(
            f"{API}/auth/register",
            json={"email": _rand_email(), "password": "a1", "name": "X"},
        )
        assert r3.status_code == 400

        # Login OK
        r4 = client.post(f"{API}/auth/login", json={"email": email, "password": "passw0rd"})
        assert r4.status_code == 200
        assert r4.json()["user"]["email"] == email.lower()

        # Login wrong password
        r5 = client.post(f"{API}/auth/login", json={"email": email, "password": "WRONG_pw"})
        assert r5.status_code == 401

        # /me with token
        r6 = client.get(f"{API}/auth/me", headers=_auth(token))
        assert r6.status_code == 200
        assert r6.json()["email"] == email.lower()

        # /me without token
        r7 = requests.get(f"{API}/auth/me")
        assert r7.status_code == 401

        # Logout (with JWT) — for JWT users it should still return ok=True;
        # JWT remains valid until expiry which is expected behaviour.
        r8 = client.post(f"{API}/auth/logout", headers=_auth(token))
        assert r8.status_code == 200
        assert r8.json().get("ok") is True


# ------------------------- Bookmarks -------------------------
class TestBookmarks:
    def test_toggle_and_list(self, client, primary_token, hackathon_id):
        # Reset to known state — first toggle removes (if present) or adds.
        # We will toggle twice and assert symmetric behaviour.
        r1 = client.post(
            f"{API}/me/bookmarks/{hackathon_id}", headers=_auth(primary_token)
        )
        assert r1.status_code == 200
        action1 = r1.json()["action"]
        assert action1 in {"added", "removed"}
        ids_after_1 = r1.json()["bookmarks"]

        r2 = client.post(
            f"{API}/me/bookmarks/{hackathon_id}", headers=_auth(primary_token)
        )
        assert r2.status_code == 200
        action2 = r2.json()["action"]
        assert action2 != action1

        # End state with this hackathon bookmarked
        if action2 == "removed":
            client.post(f"{API}/me/bookmarks/{hackathon_id}", headers=_auth(primary_token))

        # List
        rb = client.get(f"{API}/me/bookmarks", headers=_auth(primary_token))
        assert rb.status_code == 200
        items = rb.json()
        assert any(h["id"] == hackathon_id for h in items)
        # Returned objects are full hackathons
        for h in items:
            for k in ["id", "title", "company", "status"]:
                assert k in h

    def test_unknown_id_404(self, client, primary_token):
        r = client.post(
            f"{API}/me/bookmarks/{uuid.uuid4()}", headers=_auth(primary_token)
        )
        assert r.status_code == 404

    def test_unauthenticated_401(self, client, hackathon_id):
        r = requests.post(f"{API}/me/bookmarks/{hackathon_id}")
        assert r.status_code == 401


# ------------------------- Skills + Feed + Notify -------------------------
class TestSkillsFeedNotify:
    def test_set_skills(self, client, primary_token):
        skills = ["Python", "FastAPI", "MongoDB", "python", "  React  "]
        r = client.put(
            f"{API}/me/skills",
            headers=_auth(primary_token),
            json={"skills": skills},
        )
        assert r.status_code == 200
        out = r.json()["skills"]
        # trimmed
        assert "React" in out
        # deduplication is best-effort case-insensitive in resume merge.
        # set_skills only trims & caps to 50 — duplicates may still appear.
        assert all(s.strip() == s for s in out)
        assert len(out) <= 50

        # confirm persisted via /me
        me = client.get(f"{API}/auth/me", headers=_auth(primary_token)).json()
        assert "Python" in me["skills"]

    def test_feed_personalised(self, client, primary_token):
        # Bias with very generic skill present in many descriptions
        client.put(
            f"{API}/me/skills",
            headers=_auth(primary_token),
            json={"skills": ["AI", "Design", "Engineering"]},
        )
        r = client.get(f"{API}/me/feed", headers=_auth(primary_token))
        assert r.status_code == 200
        feed = r.json()
        assert isinstance(feed, list)
        assert len(feed) <= 30
        # status restricted
        for h in feed:
            assert h["status"] in {"Open", "Upcoming"}

    def test_feed_empty_skills(self, client):
        # New user with no skills → first 30 chronologically.
        email = _rand_email()
        reg = client.post(
            f"{API}/auth/register",
            json={"email": email, "password": "passw0rd", "name": "Feed User"},
        )
        assert reg.status_code == 200
        tok = reg.json()["token"]
        r = client.get(f"{API}/me/feed", headers=_auth(tok))
        assert r.status_code == 200
        items = r.json()
        assert len(items) <= 30
        for h in items:
            assert h["status"] in {"Open", "Upcoming"}

    def test_notify_toggle(self, client, primary_token):
        r = client.put(
            f"{API}/me/notify?enabled=false", headers=_auth(primary_token)
        )
        assert r.status_code == 200
        assert r.json()["email_notify"] is False
        me = client.get(f"{API}/auth/me", headers=_auth(primary_token)).json()
        assert me["email_notify"] is False

        # toggle back
        r2 = client.put(
            f"{API}/me/notify?enabled=true", headers=_auth(primary_token)
        )
        assert r2.status_code == 200
        assert r2.json()["email_notify"] is True


# ------------------------- Resume -------------------------
class TestResume:
    def test_resume_docx_upload_and_skill_extraction(self, client, primary_token):
        docx_bytes = _make_docx_bytes(
            "Ruthvik Bathini — Software Engineer\n"
            "Skills: Python, FastAPI, MongoDB, React, TypeScript, Docker, Kubernetes, AWS\n"
            "Experience: Built an AI-powered hackathon tracker using Gemini and Resend.\n"
        )
        files = {"file": ("resume.docx", docx_bytes,
                          "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        r = requests.post(
            f"{API}/me/resume",
            headers={"Authorization": f"Bearer {primary_token}"},
            files=files,
            timeout=120,
        )
        assert r.status_code == 200, f"resume failed: {r.status_code} {r.text[:400]}"
        body = r.json()
        assert body["filename"] == "resume.docx"
        assert isinstance(body["extracted_skills"], list)
        assert len(body["extracted_skills"]) >= 1, "Gemini returned no skills"
        assert isinstance(body["all_skills"], list)
        # at least one of the obvious skills should be present (case-insensitive)
        lc_all = {s.lower() for s in body["all_skills"]}
        assert any(k in lc_all for k in ["python", "fastapi", "react", "docker"])

    def test_resume_reject_txt(self, client, primary_token):
        files = {"file": ("resume.txt", b"hello world", "text/plain")}
        r = requests.post(
            f"{API}/me/resume",
            headers={"Authorization": f"Bearer {primary_token}"},
            files=files,
        )
        assert r.status_code == 400

    def test_resume_reject_oversize(self, client, primary_token):
        big = b"x" * (5 * 1024 * 1024 + 10)
        files = {"file": ("big.pdf", big, "application/pdf")}
        r = requests.post(
            f"{API}/me/resume",
            headers={"Authorization": f"Bearer {primary_token}"},
            files=files,
        )
        assert r.status_code == 400

    def test_resume_unauthenticated_401(self, client):
        files = {"file": ("resume.docx", b"x", "application/octet-stream")}
        r = requests.post(f"{API}/me/resume", files=files)
        assert r.status_code == 401


# ------------------------- ICS -------------------------
class TestICS:
    def test_ics_calendar_format(self, client, hackathon_id):
        r = client.get(f"{API}/hackathons/{hackathon_id}/ics")
        assert r.status_code == 200
        ct = r.headers.get("content-type", "")
        assert "text/calendar" in ct
        cd = r.headers.get("content-disposition", "")
        assert "attachment" in cd.lower()
        assert "filename" in cd.lower()
        body = r.text
        assert body.startswith("BEGIN:VCALENDAR")
        assert "END:VCALENDAR" in body
        assert "BEGIN:VEVENT" in body and "END:VEVENT" in body
        assert "SUMMARY" in body
        assert "DTSTART" in body
        assert "DTEND" in body
        assert "URL" in body
        # Reminder VALARM block
        assert "BEGIN:VALARM" in body
        assert "END:VALARM" in body

    def test_ics_unknown_404(self, client):
        r = client.get(f"{API}/hackathons/{uuid.uuid4()}/ics")
        assert r.status_code == 404


# ------------------------- Scheduler -------------------------
class TestSchedulerStartup:
    def test_scheduler_log_present(self):
        # Backend log path under supervisor
        paths = [
            "/var/log/supervisor/backend.err.log",
            "/var/log/supervisor/backend.out.log",
        ]
        blob = ""
        for p in paths:
            if os.path.exists(p):
                with open(p, "r", errors="ignore") as f:
                    blob += f.read()
        assert "Scheduler started" in blob, "Scheduler startup log missing"
