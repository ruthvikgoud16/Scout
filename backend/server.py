import os
import re
import json
import uuid
import logging
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional, Annotated

from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, ConfigDict

from emergentintegrations.llm.chat import LlmChat, UserMessage, TextDelta, StreamDone

from seed_data import SEED_HACKATHONS

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

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
    count = await db.hackathons.count_documents({})
    if count > 0:
        return
    docs = []
    now = datetime.now(timezone.utc).isoformat()
    for h in SEED_HACKATHONS:
        obj = Hackathon(**h).model_dump()
        obj["created_at"] = now
        obj["updated_at"] = now
        docs.append(obj)
    if docs:
        await db.hackathons.insert_many(docs)
        logger.info(f"Seeded {len(docs)} hackathons")


@app.on_event("startup")
async def on_startup():
    await seed_if_empty()
    # update meta
    await db.meta.update_one(
        {"_id": "app"},
        {"$setOnInsert": {"last_refreshed_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )


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
    meta = await db.meta.find_one({"_id": "app"}) or {}
    return {
        "total": total,
        "open": open_now,
        "upcoming": upcoming,
        "india": india,
        "international": intl,
        "companies_count": len(companies),
        "last_refreshed_at": meta.get("last_refreshed_at"),
    }


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
            "You are a research assistant tracking hiring hackathons and recruiting challenges "
            "from real companies worldwide. Return ONLY JSON — never prose, never markdown fences. "
            "Focus on 2025-2026 events from Indian and international tech companies."
        )
        existing = await db.hackathons.distinct("title")
        prompt = f"""List 8 currently-running or upcoming hiring hackathons / recruiting challenges from real companies.
Mix Indian companies (Myntra, Meesho, Flipkart, Zomato, Swiggy, Razorpay, Cred, Paytm, PhonePe, Sharechan, Postman, Browserstack, Freshworks, Zoho, Tata 1mg, etc.)
and International companies (Google, Meta, Amazon, Microsoft, Atlassian, Stripe, GitHub, Cloudflare, Datadog, MongoDB, Salesforce, Adobe, Uber, Airbnb, etc.).
Avoid duplicates of: {existing[:30]}

Return ONLY a JSON array — each item with this exact schema:
[
  {{
    "title": "string",
    "company": "string",
    "company_logo": "https://logo.clearbit.com/<domain>",
    "region": "India" | "International",
    "mode": "Online" | "Offline" | "Hybrid",
    "status": "Open" | "Upcoming" | "Closed",
    "tags": ["short tag", "short tag"],
    "start_date": "ISO 8601 datetime",
    "end_date": "ISO 8601 datetime",
    "registration_deadline": "ISO 8601 datetime",
    "registration_link": "https://...",
    "location": "string",
    "description": "1-2 sentence description",
    "eligibility": "1 sentence",
    "prizes": "1 sentence",
    "source_url": "https://..."
  }}
]
- Dates must be realistic for 2025-2026.
- Use real, plausible URLs (company career pages, hackerearth.com/challenges, unstop.com).
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
        "You are HackPilot — a friendly, expert career coach for engineering students "
        "preparing for hiring hackathons (India + global). Give concrete, actionable advice. "
        "When useful, include resource links (LeetCode, NeetCode, Striver SDE sheet, GFG, "
        "official company blogs, YouTube channels like CodeWithHarry, Take U Forward, Tech Dummies). "
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
    """Curated static prep resources hub for students."""
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
        ],
        "Behavioral & HR": [
            {"title": "STAR method guide", "url": "https://www.themuse.com/advice/star-interview-method", "type": "article"},
            {"title": "Tech Interview Handbook", "url": "https://www.techinterviewhandbook.org/", "type": "docs"},
        ],
        "Hackathon Platforms": [
            {"title": "Unstop", "url": "https://unstop.com/hackathons", "type": "practice"},
            {"title": "HackerEarth Challenges", "url": "https://www.hackerearth.com/challenges/", "type": "practice"},
            {"title": "Devfolio", "url": "https://devfolio.co/hackathons", "type": "practice"},
            {"title": "MLH", "url": "https://mlh.io/seasons/2026/events", "type": "practice"},
        ],
        "Aptitude & Logical": [
            {"title": "IndiaBix Aptitude", "url": "https://www.indiabix.com/", "type": "practice"},
            {"title": "PrepInsta", "url": "https://prepinsta.com/", "type": "practice"},
        ],
    }


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
