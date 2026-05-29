"""Email-based session auth: upsert a user by email, set a signed cookie."""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from api.auth import SESSION_COOKIE, SESSION_MAX_AGE_SECONDS, encode_user_id
from api.deps import require_user
from api.schemas import UserOut
from app.core import db
from app.core.config import get_settings
from app.core.db import User

router = APIRouter(prefix="/api/auth", tags=["auth"])

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class SignInRequest(BaseModel):
    email: str
    name: str | None = None


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=settings.environment == "production",
        path="/",
    )


@router.post("/sign-in", response_model=UserOut)
def sign_in(payload: SignInRequest, response: Response) -> UserOut:
    """Upsert a user by email and start a session cookie."""
    email = payload.email.strip().lower()
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Invalid email")
    name = (payload.name or "").strip() or None
    user = db.upsert_user(email, name)
    _set_session_cookie(response, encode_user_id(user.id))
    return UserOut(id=user.id, email=user.email, name=user.name)


@router.post("/sign-out")
def sign_out(response: Response) -> dict:
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def get_me(user: User = Depends(require_user)) -> UserOut:
    return UserOut(id=user.id, email=user.email, name=user.name)
