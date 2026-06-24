"""Auth helpers — JWT email/password + Emergent Google session token."""
import os
import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt as pyjwt
import requests
from fastapi import Depends, HTTPException, Request, Cookie, Header

logger = logging.getLogger(__name__)

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret")
JWT_ALG = "HS256"
JWT_TTL_DAYS = 7
GOOGLE_SESSION_URL = (
    "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"
)

# --- password hashing -------------------------------------------------
def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False


# --- JWT helpers ------------------------------------------------------
def make_jwt(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_TTL_DAYS),
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def decode_jwt(token: str) -> Optional[str]:
    try:
        data = pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return data.get("sub")
    except Exception:
        return None


# --- Google session exchange -----------------------------------------
def exchange_google_session(session_id: str) -> Optional[dict]:
    try:
        r = requests.get(
            GOOGLE_SESSION_URL,
            headers={"X-Session-ID": session_id},
            timeout=15,
        )
        if r.status_code != 200:
            logger.warning(f"Google session exchange failed: {r.status_code}")
            return None
        return r.json()
    except Exception:
        logger.exception("Google session exchange exception")
        return None


# --- FastAPI dependency ----------------------------------------------
def _extract_token(
    session_token: Optional[str], authorization: Optional[str]
) -> Optional[str]:
    if session_token:
        return session_token
    if authorization:
        if authorization.lower().startswith("bearer "):
            return authorization[7:].strip()
        return authorization
    return None


async def get_current_user_from_db(token: str, db) -> Optional[dict]:
    """Validate token via either JWT or Emergent session_token row."""
    # 1) try JWT
    user_id = decode_jwt(token)
    if user_id:
        u = await db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
        if u:
            return u
    # 2) try emergent session row
    row = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if row:
        exp = row.get("expires_at")
        if isinstance(exp, str):
            try:
                exp = datetime.fromisoformat(exp)
            except Exception:
                exp = None
        if exp:
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp < datetime.now(timezone.utc):
                return None
        u = await db.users.find_one(
            {"user_id": row["user_id"]}, {"_id": 0, "password_hash": 0}
        )
        return u
    return None


def new_user_id() -> str:
    return f"user_{uuid.uuid4().hex[:12]}"
