"""Skill extraction from resume text using Gemini."""
import os
import re
import json
import logging
from emergentintegrations.llm.chat import LlmChat, UserMessage, TextDelta, StreamDone

logger = logging.getLogger(__name__)

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")
GEMINI_MODEL = "gemini-3-flash-preview"


def extract_pdf_text(data: bytes) -> str:
    from pypdf import PdfReader
    import io
    out = []
    try:
        r = PdfReader(io.BytesIO(data))
        for p in r.pages:
            out.append(p.extract_text() or "")
    except Exception as e:
        logger.warning(f"PDF parse error: {e}")
    return "\n".join(out)[:20000]


def extract_docx_text(data: bytes) -> str:
    from docx import Document
    import io
    try:
        d = Document(io.BytesIO(data))
        return "\n".join(p.text for p in d.paragraphs)[:20000]
    except Exception as e:
        logger.warning(f"DOCX parse error: {e}")
        return ""


async def extract_skills(resume_text: str) -> list:
    if not resume_text.strip():
        return []
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id="skills-extract",
        system_message=(
            "You extract technical skills, tools, frameworks, programming "
            "languages and domains from resumes. Return ONLY a JSON array of "
            "short skill strings (max 30 items). No markdown, no commentary."
        ),
    ).with_model("gemini", GEMINI_MODEL)
    parts = []
    async for ev in chat.stream_message(
        UserMessage(text=f"Resume text:\n\n{resume_text}\n\nReturn JSON array of skills only.")
    ):
        if isinstance(ev, TextDelta):
            parts.append(ev.content)
        elif isinstance(ev, StreamDone):
            break
    text = "".join(parts)
    m = re.search(r"\[.*\]", text, re.S)
    if m:
        text = m.group(0)
    try:
        arr = json.loads(text)
        return [str(s).strip() for s in arr if str(s).strip()][:30]
    except Exception:
        return []
