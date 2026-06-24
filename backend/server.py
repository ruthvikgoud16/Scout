import os
import re
import json
import uuid
import logging
import asyncio
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Annotated

from dotenv import load_dotenv

# Load env BEFORE importing local modules so they pick up env vars at module load.
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks, Response, Cookie, Header, UploadFile, File, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field, ConfigDict

from emergentintegrations.llm.chat import LlmChat, UserMessage, TextDelta, StreamDone

from seed_data import SEED_HACKATHONS
import auth as auth_lib
from email_service import send_email, reminder_html
from storage import put_object, init_storage, APP_NAME
from skills import extract_pdf_text, extract_docx_text, extract_skills
from ics import build_ics
from scheduler import start_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")
GEMINI_MODEL = "gemini-3-flash-preview"

app = FastAPI(title="HackTrack — Hiring Hackathon Tracker")
api_router = APIRouter(prefix="/api")


# ------------------------- Models -------------------------
class PrepRound(BaseModel):
    name: str
    description: str
    duration: Optional[str] = None
    tips: Optional[str] = None


class PrepResource(BaseModel):
    title: str
    url: str
    type: str = "article"  # article | video | course | docs | practice


class PrepInfo(BaseModel):
    rounds: List[PrepRound] = []
    requirements: List[str] = []
    checklist: List[str] = []
    resources: List[PrepResource] = []
    generated_at: Optional[str] = None


class Hackathon(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    company: str
    company_logo: Optional[str] = None
    event_type: str = "Hackathon"  # Hackathon | Conference | Summit | Workshop | Meetup | Invite-only
    audience: List[str] = ["Students"]  # subset of [Students, Professionals]
    region: str  # India | International
    mode: str  # Online | Offline | Hybrid
    status: str  # Open | Upcoming | Closed
    tags: List[str] = []
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    registration_deadline: Optional[str] = None
    registration_link: Optional[str] = None
    location: Optional[str] = None
    description: str = ""
    eligibility: Optional[str] = None
    prizes: Optional[str] = None
    source_url: Optional[str] = None
    prep: Optional[PrepInfo] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ChatRequest(BaseModel):
    session_id: str
    message: str
    hackathon_id: Optional[str] = None


# ------------------------- Helpers -------------------------
def _strip(doc):
    if doc is None:
        return None
    doc.pop("_id", None)
    return doc


def _extract_json(text: str):
    """Robust JSON extractor — Gemini sometimes wraps with code fences."""
    fenced = re.search(r"```(?:json)?\s*(\[.*?\]|\{.*?\})\s*```", text, re.S)
    if fenced:
        text = fenced.group(1)
    else:
        start_array = text.find("[")
        start_obj = text.find("{")
        starts = [s for s in [start_array, start_obj] if s != -1]
        if starts:
            text = text[min(starts):]
    try:
        return json.loads(text)
    except Exception:
        end = max(text.rfind("]"), text.rfind("}"))
        if end != -1:
            try:
                return json.loads(text[: end + 1])
            except Exception:
                return None
    return None


def _new_llm_chat(session_id: str, system_message: str) -> LlmChat:
    return LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=system_message,
    ).with_model("gemini", GEMINI_MODEL)


async def _llm_full_text(session_id: str, system_message: str, user_text: str) -> str:
    chat = _new_llm_chat(session_id, system_message)
    out = []
    async for ev in chat.stream_message(UserMessage(text=user_text)):
        if isinstance(ev, TextDelta):
            out.append(ev.content)
        elif isinstance(ev, StreamDone):
            break
    return "".join(out)


# ------------------------- Seed -------------------------
async def seed_if_empty():
    """Idempotently upsert seed events by title — adds missing ones,
    keeps existing user/AI-curated content."""
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0
    for h in SEED_HACKATHONS:
        existing = await db.hackathons.find_one({"title": h["title"]})
        if existing:
            # backfill new fields if missing
            patch = {}
            if not existing.get("event_type"):
                patch["event_type"] = h.get("event_type", "Hackathon")
            if not existing.get("audience"):
                patch["audience"] = h.get("audience", ["Students"])
            if patch:
                await db.hackathons.update_one({"_id": existing["_id"]}, {"$set": patch})
            continue
        obj = Hackathon(**h).model_dump()
        obj["created_at"] = now
        obj["updated_at"] = now
        await db.hackathons.insert_one(obj)
        inserted += 1
    if inserted:
        logger.info(f"Seeded {inserted} new events")


@app.on_event("startup")
async def on_startup():
    await seed_if_empty()
    # update meta
    await db.meta.update_one(
        {"_id": "app"},
        {"$setOnInsert": {"last_refreshed_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    # Object storage init is lazy — called on first upload
    # start cron scheduler (auto refresh + reminders)
    try:
        start_scheduler(db, _refresh_with_gemini, send_email, reminder_html)
    except Exception:
        logger.exception("Failed to start scheduler")


# ------------------------- Routes -------------------------
@api_router.get("/")
async def root():
    return {"app": "HackTrack", "status": "live"}


@api_router.get("/hackathons", response_model=List[Hackathon])
async def list_hackathons(
    region: Optional[str] = None,
    mode: Optional[str] = None,
    status: Optional[str] = None,
    company: Optional[str] = None,
    event_type: Optional[str] = None,
    audience: Optional[str] = None,
    search: Optional[str] = None,
):
    q = {}
    if region and region != "All":
        q["region"] = region
    if mode and mode != "All":
        q["mode"] = mode
    if status and status != "All":
        q["status"] = status
    if company and company != "All":
        q["company"] = company
    if event_type and event_type != "All":
        q["event_type"] = event_type
    if audience and audience != "All":
        q["audience"] = audience
    if search:
        q["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"company": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"tags": {"$regex": search, "$options": "i"}},
        ]
    docs = await db.hackathons.find(q, {"_id": 0}).sort("registration_deadline", 1).to_list(500)
    return docs


@api_router.get("/hackathons/{hid}", response_model=Hackathon)
async def get_hackathon(hid: str):
    doc = await db.hackathons.find_one({"id": hid}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Hackathon not found")
    return doc


@api_router.get("/stats")
async def stats():
    total = await db.hackathons.count_documents({})
    open_now = await db.hackathons.count_documents({"status": "Open"})
    upcoming = await db.hackathons.count_documents({"status": "Upcoming"})
    india = await db.hackathons.count_documents({"region": "India"})
    intl = await db.hackathons.count_documents({"region": "International"})
    companies = await db.hackathons.distinct("company")
    event_types = await db.hackathons.distinct("event_type")
    meta = await db.meta.find_one({"_id": "app"}) or {}
    return {
        "total": total,
        "open": open_now,
        "upcoming": upcoming,
        "india": india,
        "international": intl,
        "companies_count": len(companies),
        "event_types_count": len(event_types),
        "last_refreshed_at": meta.get("last_refreshed_at"),
    }


@api_router.get("/event-types")
async def event_types():
    names = await db.hackathons.distinct("event_type")
    return sorted([n for n in names if n])


@api_router.get("/companies")
async def companies():
    names = await db.hackathons.distinct("company")
    return sorted(names)


@api_router.post("/hackathons/{hid}/prep")
async def generate_prep(hid: str):
    doc = await db.hackathons.find_one({"id": hid}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Hackathon not found")

    system = (
        "You are a senior tech recruiter & coach helping engineering students prepare for "
        "hiring hackathons in India and globally. Always respond with valid JSON only — no prose, "
        "no markdown fences. Always include 2025+ relevant resources (LeetCode, NeetCode, Striver SDE Sheet, "
        "GFG, system design primer, official docs, Educative, YouTube channels)."
    )

    prompt = f"""Generate a complete preparation guide for the following hiring hackathon.

HACKATHON:
- Title: {doc.get('title')}
- Company: {doc.get('company')}
- Region: {doc.get('region')}
- Mode: {doc.get('mode')}
- Description: {doc.get('description')}
- Eligibility: {doc.get('eligibility')}

Return ONLY JSON in this exact schema (no markdown):
{{
  "rounds": [
    {{"name": "Round name", "description": "what happens", "duration": "e.g. 90 mins", "tips": "1-2 practical tips"}}
  ],
  "requirements": ["bullet point requirement"],
  "checklist": ["actionable to-do item"],
  "resources": [
    {{"title": "Resource name", "url": "https://...", "type": "article|video|course|docs|practice"}}
  ]
}}

Rules:
- 3-5 rounds typical for this company / hackathon.
- 4-7 requirements (skills, eligibility, tools).
- 6-10 concrete checklist items (e.g. "Solve 50 Easy + 30 Medium LeetCode", "Build a small project on X").
- 6-10 high-quality resources with WORKING URLs (leetcode.com, neetcode.io, takeuforward.org, geeksforgeeks.org, youtube.com, github.com, official company blog).
- No commentary, no markdown, no code fences."""

    try:
        text = await _llm_full_text(f"prep-{hid}", system, prompt)
        parsed = _extract_json(text)
        if not parsed:
            raise ValueError("Could not parse Gemini output as JSON")
        prep = PrepInfo(
            rounds=[PrepRound(**r) for r in parsed.get("rounds", [])],
            requirements=parsed.get("requirements", []),
            checklist=parsed.get("checklist", []),
            resources=[PrepResource(**r) for r in parsed.get("resources", [])],
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
        prep_dict = prep.model_dump()
        await db.hackathons.update_one(
            {"id": hid},
            {"$set": {"prep": prep_dict, "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        return prep_dict
    except Exception as e:
        logger.exception("Prep generation failed")
        raise HTTPException(500, f"AI prep generation failed: {e}")


@api_router.post("/hackathons/refresh")
async def refresh_hackathons(background_tasks: BackgroundTasks):
    """Trigger Gemini to discover & add fresh hiring hackathons.
    Runs in background so the request returns quickly."""
    background_tasks.add_task(_refresh_with_gemini)
    return {"status": "refresh_started"}


async def _refresh_with_gemini():
    try:
        system = (
            "You are a research assistant tracking hiring hackathons, tech conferences, "
            "summits, workshops, meetups and invite-only professional events worldwide. "
            "Return ONLY JSON — never prose, never markdown fences. Focus on 2025-2026 "
            "events for both students and working professionals."
        )
        existing = await db.hackathons.distinct("title")
        prompt = f"""List 10 currently-running or upcoming events. Mix of types:
- Hiring hackathons (Myntra, Meesho, Flipkart, Zomato, Swiggy, Razorpay, Cred, Paytm, PhonePe, Postman, Browserstack, Freshworks, Zoho, Google, Meta, Amazon, Microsoft, Atlassian, Stripe, GitHub, Cloudflare, Datadog, Salesforce, Adobe, Uber, Airbnb)
- Tech conferences (AWS re:Invent, Google I/O, KubeCon, PyCon, DroidCon, Devoxx, JSConf, Strange Loop, GopherCon)
- Summits (NVIDIA GTC, GitHub Universe, Apple WWDC, Microsoft Build, Render ATL)
- Workshops / bootcamps (cloud certifications, ML bootcamps, fellowships)
- Meetups (city-based dev meetups, ProductTank, GDG)
- Invite-only programs (YC Startup School, On Deck, South Park Commons, Stripe Sessions)

Avoid duplicates of: {existing[:40]}

Return ONLY a JSON array — each item with this exact schema:
[
  {{
    "title": "string",
    "company": "string (organising company / org)",
    "company_logo": "https://logo.clearbit.com/<domain>",
    "event_type": "Hackathon" | "Conference" | "Summit" | "Workshop" | "Meetup" | "Invite-only",
    "audience": ["Students"] | ["Professionals"] | ["Students", "Professionals"],
    "region": "India" | "International",
    "mode": "Online" | "Offline" | "Hybrid",
    "status": "Open" | "Upcoming" | "Closed",
    "tags": ["short tag", "short tag"],
    "start_date": "ISO 8601 datetime",
    "end_date": "ISO 8601 datetime",
    "registration_deadline": "ISO 8601 datetime",
    "registration_link": "https://...",
    "location": "string (city + country, or 'Online (Global)')",
    "description": "1-2 sentence description",
    "eligibility": "1 sentence",
    "prizes": "1 sentence (what attendees get — offer, swag, networking, prize money)",
    "source_url": "https://..."
  }}
]
- Dates must be realistic for 2025-2026.
- Use real, plausible URLs (company event pages, hackerearth.com, unstop.com, lu.ma, eventbrite, meetup.com).
- No code fences, no commentary."""
        text = await _llm_full_text("refresh-feed", system, prompt)
        parsed = _extract_json(text)
        if not isinstance(parsed, list):
            logger.warning("Refresh: bad LLM output")
            return
        now = datetime.now(timezone.utc).isoformat()
        added = 0
        for item in parsed:
            try:
                title = (item.get("title") or "").strip()
                if not title:
                    continue
                exists = await db.hackathons.find_one({"title": title})
                if exists:
                    continue
                obj = Hackathon(**item).model_dump()
                obj["created_at"] = now
                obj["updated_at"] = now
                await db.hackathons.insert_one(obj)
                added += 1
            except Exception:
                continue
        await db.meta.update_one(
            {"_id": "app"},
            {"$set": {"last_refreshed_at": now, "last_added": added}},
            upsert=True,
        )
        logger.info(f"Gemini refresh added {added} hackathons")
    except Exception:
        logger.exception("Refresh failed")


@api_router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """Streaming AI assistant for student prep guidance."""
    context = ""
    if req.hackathon_id:
        doc = await db.hackathons.find_one({"id": req.hackathon_id}, {"_id": 0})
        if doc:
            context = (
                f"\nThe student is asking about this hackathon:\nTitle: {doc.get('title')}\n"
                f"Company: {doc.get('company')}\nDescription: {doc.get('description')}\n"
                f"Eligibility: {doc.get('eligibility')}\nMode: {doc.get('mode')}\n"
            )

    system = (
        "You are HackPilot — a friendly, expert career coach for STUDENTS and WORKING "
        "PROFESSIONALS preparing for hiring hackathons, tech conferences, summits, "
        "workshops, invite-only programs and meetups (India + global). Give concrete, "
        "actionable advice. When useful, include real resource links (LeetCode, NeetCode, "
        "Striver SDE sheet, GFG, system-design primer, official company blogs, "
        "YouTube channels like ByteByteGo, CodeWithHarry, Take U Forward, Tech Dummies, "
        "and platforms like Unstop, HackerEarth, Lu.ma, Meetup, Eventbrite). "
        "Use short paragraphs and bullet points. Be encouraging."
        + context
    )

    # persist user message
    await db.chat_messages.insert_one(
        {
            "session_id": req.session_id,
            "role": "user",
            "content": req.message,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
    )

    async def event_gen():
        full = []
        try:
            chat = _new_llm_chat(req.session_id, system)
            async for ev in chat.stream_message(UserMessage(text=req.message)):
                if isinstance(ev, TextDelta):
                    full.append(ev.content)
                    yield f"data: {json.dumps({'delta': ev.content})}\n\n"
                elif isinstance(ev, StreamDone):
                    break
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            logger.exception("Chat stream failed")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            await db.chat_messages.insert_one(
                {
                    "session_id": req.session_id,
                    "role": "assistant",
                    "content": "".join(full),
                    "ts": datetime.now(timezone.utc).isoformat(),
                }
            )

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@api_router.get("/chat/history/{session_id}")
async def chat_history(session_id: str):
    msgs = (
        await db.chat_messages.find({"session_id": session_id}, {"_id": 0})
        .sort("ts", 1)
        .to_list(200)
    )
    return msgs


@api_router.get("/resources")
async def resources():
    """Curated static prep resources hub for students AND working professionals."""
    return {
        "DSA": [
            {"title": "NeetCode 150", "url": "https://neetcode.io/practice", "type": "practice"},
            {"title": "Striver SDE Sheet", "url": "https://takeuforward.org/interviews/strivers-sde-sheet-top-coding-interview-problems", "type": "practice"},
            {"title": "LeetCode Top Interview 150", "url": "https://leetcode.com/studyplan/top-interview-150/", "type": "practice"},
            {"title": "GeeksForGeeks DSA", "url": "https://www.geeksforgeeks.org/data-structures/", "type": "article"},
        ],
        "System Design": [
            {"title": "System Design Primer (GitHub)", "url": "https://github.com/donnemartin/system-design-primer", "type": "docs"},
            {"title": "ByteByteGo YouTube", "url": "https://www.youtube.com/@ByteByteGo", "type": "video"},
            {"title": "Educative – Grokking System Design", "url": "https://www.educative.io/courses/grokking-the-system-design-interview", "type": "course"},
            {"title": "Designing Data-Intensive Applications", "url": "https://dataintensive.net/", "type": "article"},
        ],
        "Behavioral & HR": [
            {"title": "STAR method guide", "url": "https://www.themuse.com/advice/star-interview-method", "type": "article"},
            {"title": "Tech Interview Handbook", "url": "https://www.techinterviewhandbook.org/", "type": "docs"},
            {"title": "Levels.fyi salary data", "url": "https://www.levels.fyi/", "type": "article"},
        ],
        "Hackathon Platforms": [
            {"title": "Unstop", "url": "https://unstop.com/hackathons", "type": "practice"},
            {"title": "HackerEarth Challenges", "url": "https://www.hackerearth.com/challenges/", "type": "practice"},
            {"title": "Devfolio", "url": "https://devfolio.co/hackathons", "type": "practice"},
            {"title": "MLH", "url": "https://mlh.io/seasons/2026/events", "type": "practice"},
            {"title": "Devpost", "url": "https://devpost.com/hackathons", "type": "practice"},
        ],
        "Conferences & Events": [
            {"title": "Lu.ma — tech events", "url": "https://lu.ma/discover", "type": "practice"},
            {"title": "Meetup tech groups", "url": "https://www.meetup.com/topics/tech/", "type": "practice"},
            {"title": "Eventbrite tech", "url": "https://www.eventbrite.com/d/online/tech/", "type": "practice"},
            {"title": "Conference Index (worldwide)", "url": "https://conferenceindex.org/", "type": "article"},
            {"title": "DEV.to upcoming events", "url": "https://dev.to/t/events", "type": "article"},
        ],
        "Career Growth (Professionals)": [
            {"title": "Staff Engineer's Path (book)", "url": "https://www.staffeng.com/", "type": "article"},
            {"title": "Pragmatic Engineer Newsletter", "url": "https://newsletter.pragmaticengineer.com/", "type": "article"},
            {"title": "Manager's Path (Camille Fournier)", "url": "https://www.oreilly.com/library/view/the-managers-path/9781491973882/", "type": "course"},
            {"title": "Lenny's Newsletter (Product)", "url": "https://www.lennysnewsletter.com/", "type": "article"},
        ],
        "Aptitude & Logical": [
            {"title": "IndiaBix Aptitude", "url": "https://www.indiabix.com/", "type": "practice"},
            {"title": "PrepInsta", "url": "https://prepinsta.com/", "type": "practice"},
        ],
        "Startup & Founder": [
            {"title": "YC Startup School", "url": "https://www.startupschool.org/", "type": "course"},
            {"title": "Paul Graham's essays", "url": "http://www.paulgraham.com/articles.html", "type": "article"},
            {"title": "First Round Review", "url": "https://review.firstround.com/", "type": "article"},
        ],
    }


# ------------------------- Auth / User Models -------------------------
class RegisterReq(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None


class LoginReq(BaseModel):
    email: EmailStr
    password: str


class GoogleSessionReq(BaseModel):
    session_id: str


class SkillsReq(BaseModel):
    skills: List[str]


async def _require_user(
    session_token: Optional[str] = Cookie(default=None),
    authorization: Optional[str] = Header(default=None),
) -> dict:
    token = auth_lib._extract_token(session_token, authorization)
    if not token:
        raise HTTPException(401, "Authentication required")
    user = await auth_lib.get_current_user_from_db(token, db)
    if not user:
        raise HTTPException(401, "Invalid or expired session")
    return user


async def _optional_user(
    session_token: Optional[str] = Cookie(default=None),
    authorization: Optional[str] = Header(default=None),
) -> Optional[dict]:
    token = auth_lib._extract_token(session_token, authorization)
    if not token:
        return None
    return await auth_lib.get_current_user_from_db(token, db)


def _user_public(u: dict) -> dict:
    if not u:
        return None
    return {
        "user_id": u.get("user_id"),
        "email": u.get("email"),
        "name": u.get("name"),
        "picture": u.get("picture"),
        "skills": u.get("skills", []),
        "bookmarks": u.get("bookmarks", []),
        "resume_filename": u.get("resume_filename"),
        "email_notify": u.get("email_notify", True),
        "auth_provider": u.get("auth_provider", "password"),
    }


# ------------------------- Auth Routes -------------------------
@api_router.post("/auth/register")
async def auth_register(req: RegisterReq):
    existing = await db.users.find_one({"email": req.email.lower()}, {"_id": 0})
    if existing:
        raise HTTPException(400, "Email already registered")
    if len(req.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    user_id = auth_lib.new_user_id()
    doc = {
        "user_id": user_id,
        "email": req.email.lower(),
        "name": req.name or req.email.split("@")[0],
        "picture": None,
        "password_hash": auth_lib.hash_password(req.password),
        "auth_provider": "password",
        "skills": [],
        "bookmarks": [],
        "email_notify": True,
        "resume_path": None,
        "resume_filename": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(doc)
    token = auth_lib.make_jwt(user_id)
    return {"token": token, "user": _user_public(doc)}


@api_router.post("/auth/login")
async def auth_login(req: LoginReq):
    u = await db.users.find_one({"email": req.email.lower()}, {"_id": 0})
    if not u or not u.get("password_hash"):
        raise HTTPException(401, "Invalid email or password")
    if not auth_lib.verify_password(req.password, u["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    token = auth_lib.make_jwt(u["user_id"])
    return {"token": token, "user": _user_public(u)}


@api_router.post("/auth/google-session")
async def auth_google_session(req: GoogleSessionReq, response: Response):
    """Exchange Emergent session_id → user + cookie."""
    info = auth_lib.exchange_google_session(req.session_id)
    if not info:
        raise HTTPException(401, "Invalid Google session")
    email = (info.get("email") or "").lower()
    if not email:
        raise HTTPException(400, "No email on Google account")
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    now = datetime.now(timezone.utc).isoformat()
    if existing:
        user_id = existing["user_id"]
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "name": info.get("name") or existing.get("name"),
                "picture": info.get("picture") or existing.get("picture"),
                "auth_provider": existing.get("auth_provider") or "google",
            }},
        )
    else:
        user_id = auth_lib.new_user_id()
        await db.users.insert_one({
            "user_id": user_id,
            "email": email,
            "name": info.get("name") or email.split("@")[0],
            "picture": info.get("picture"),
            "password_hash": None,
            "auth_provider": "google",
            "skills": [],
            "bookmarks": [],
            "email_notify": True,
            "resume_path": None,
            "resume_filename": None,
            "created_at": now,
        })
    # Store emergent session_token row (7 days)
    session_token = info["session_token"]
    expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    await db.user_sessions.insert_one({
        "session_token": session_token,
        "user_id": user_id,
        "expires_at": expires_at,
        "created_at": now,
    })
    response.set_cookie(
        key="session_token",
        value=session_token,
        max_age=7 * 24 * 3600,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
    )
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
    return {"token": session_token, "user": _user_public(user)}


@api_router.get("/auth/me")
async def auth_me(user: dict = Depends(_require_user)):
    return _user_public(user)


@api_router.post("/auth/logout")
async def auth_logout(
    response: Response,
    session_token: Optional[str] = Cookie(default=None),
    authorization: Optional[str] = Header(default=None),
):
    token = auth_lib._extract_token(session_token, authorization)
    if token:
        await db.user_sessions.delete_many({"session_token": token})
    response.delete_cookie("session_token", path="/")
    return {"ok": True}


# ------------------------- Bookmark Routes -------------------------
@api_router.post("/me/bookmarks/{hid}")
async def toggle_bookmark(
    hid: str, user: dict = Depends(_require_user)
):
    h = await db.hackathons.find_one({"id": hid}, {"_id": 0, "id": 1})
    if not h:
        raise HTTPException(404, "Event not found")
    current = user.get("bookmarks", [])
    if hid in current:
        new_list = [x for x in current if x != hid]
        action = "removed"
    else:
        new_list = current + [hid]
        action = "added"
    await db.users.update_one(
        {"user_id": user["user_id"]}, {"$set": {"bookmarks": new_list}}
    )
    return {"action": action, "bookmarks": new_list}


@api_router.get("/me/bookmarks", response_model=List[Hackathon])
async def my_bookmarks(user: dict = Depends(_require_user)):
    ids = user.get("bookmarks", [])
    if not ids:
        return []
    docs = await db.hackathons.find({"id": {"$in": ids}}, {"_id": 0}).to_list(500)
    return docs


@api_router.put("/me/notify")
async def update_notify(
    enabled: bool, user: dict = Depends(_require_user)
):
    await db.users.update_one(
        {"user_id": user["user_id"]}, {"$set": {"email_notify": enabled}}
    )
    return {"email_notify": enabled}


# ------------------------- Skills / Resume / Feed -------------------------
@api_router.put("/me/skills")
async def set_skills(
    req: SkillsReq, user: dict = Depends(_require_user)
):
    skills = [s.strip() for s in req.skills if s and s.strip()][:50]
    await db.users.update_one(
        {"user_id": user["user_id"]}, {"$set": {"skills": skills}}
    )
    return {"skills": skills}


@api_router.post("/me/resume")
async def upload_resume(
    file: UploadFile = File(...),
    user: dict = Depends(_require_user),
):
    if not file.filename:
        raise HTTPException(400, "No filename")
    ext = file.filename.lower().split(".")[-1]
    if ext not in {"pdf", "docx"}:
        raise HTTPException(400, "Only PDF or DOCX allowed")
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(400, "Max 5MB")
    path = f"{APP_NAME}/resumes/{user['user_id']}/{uuid.uuid4().hex}.{ext}"
    try:
        result = put_object(path, data, file.content_type or "application/octet-stream")
    except Exception:
        logger.exception("Resume upload failed")
        raise HTTPException(500, "Upload failed")
    text = extract_pdf_text(data) if ext == "pdf" else extract_docx_text(data)
    skills = await extract_skills(text)
    # merge with existing skills (dedup, case-insensitive)
    existing_skills = user.get("skills") or []
    merged = list({s.lower(): s for s in existing_skills + skills}.values())[:50]
    await db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {
            "resume_path": result["path"],
            "resume_filename": file.filename,
            "skills": merged,
        }},
    )
    return {"filename": file.filename, "extracted_skills": skills, "all_skills": merged}


@api_router.get("/me/feed", response_model=List[Hackathon])
async def personalised_feed(
    user: dict = Depends(_require_user)
):
    skills_lower = [s.lower() for s in (user.get("skills") or [])]
    docs = await db.hackathons.find(
        {"status": {"$in": ["Open", "Upcoming"]}}, {"_id": 0}
    ).to_list(500)
    if not skills_lower:
        return docs[:30]
    # naive scoring: count of skills appearing in title/description/tags
    def score(h):
        bag = " ".join([
            h.get("title", ""),
            h.get("description", ""),
            " ".join(h.get("tags") or []),
            h.get("eligibility", "") or "",
        ]).lower()
        return sum(1 for s in skills_lower if s in bag)
    docs.sort(key=score, reverse=True)
    return docs[:30]


# ------------------------- ICS Calendar -------------------------
@api_router.get("/hackathons/{hid}/ics")
async def event_ics(hid: str):
    h = await db.hackathons.find_one({"id": hid}, {"_id": 0})
    if not h:
        raise HTTPException(404, "Event not found")
    body = build_ics(h)
    safe = re.sub(r"[^a-z0-9]+", "-", (h.get("title") or "event").lower()).strip("-")
    return Response(
        content=body,
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="{safe}.ics"'},
    )


# Register routes & middleware
app.include_router(api_router)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
