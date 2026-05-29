"""Signed-cookie session helpers (itsdangerous)."""

from __future__ import annotations

from uuid import UUID

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.core.config import get_settings

SESSION_COOKIE = "usfind_session"
SESSION_MAX_AGE_SECONDS = 30 * 24 * 3600  # 30 days
_SALT = "usfind-session-v1"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().session_secret, salt=_SALT)


def encode_user_id(user_id: UUID) -> str:
    """Return a signed token carrying the user id."""
    return _serializer().dumps(str(user_id))


def decode_user_id(token: str) -> UUID | None:
    """Verify a signed token and return the embedded user id, or None on failure."""
    try:
        raw = _serializer().loads(token, max_age=SESSION_MAX_AGE_SECONDS)
        return UUID(raw)
    except (BadSignature, SignatureExpired, ValueError):
        return None
