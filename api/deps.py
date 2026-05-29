"""Shared FastAPI dependencies — currently auth-only."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request

from api.auth import SESSION_COOKIE, decode_user_id
from app.core import db
from app.core.db import User


def current_user(request: Request) -> User | None:
    """Return the signed-in user from the session cookie, or None."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    user_id = decode_user_id(token)
    if user_id is None:
        return None
    return db.get_user(user_id)


def require_user(user: User | None = Depends(current_user)) -> User:
    """Resolve the current user or raise 401."""
    if user is None:
        raise HTTPException(status_code=401, detail="Not signed in")
    return user
