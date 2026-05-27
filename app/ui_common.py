"""Shared Streamlit helpers: app initialization, session auth, and formatting.

Imported by the entry script and every page. Keeping these here (rather than in
streamlit_app.py) lets pages reuse them without re-executing the entry script.
"""

from __future__ import annotations

import os
import sys
import threading
from datetime import UTC, datetime
from pathlib import Path

# Ensure the repo root is importable when launched via
# `streamlit run app/streamlit_app.py` (Streamlit only adds the script's dir).
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st  # noqa: E402

from app.core import db  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.logging_config import configure_logging  # noqa: E402


def init_app() -> None:
    """Configure logging, apply migrations, and warm the model once per session."""
    if st.session_state.get("_initialized"):
        return
    settings = get_settings()
    configure_logging(settings.log_level, settings.environment)
    if settings.environment != "production" or os.getenv("RUN_MIGRATIONS_ON_BOOT") == "true":
        db.run_migrations()
    _warm_clip_async()
    st.session_state["_initialized"] = True


def _warm_clip_async() -> None:
    def _warm() -> None:
        try:
            from app.core import embeddings

            embeddings._load()
        except Exception:
            pass

    threading.Thread(target=_warm, daemon=True).start()


def current_user() -> dict | None:
    """Return the signed-in user dict ({id, email, name}) or None."""
    return st.session_state.get("user")


def require_login() -> dict:
    """Return the current user, or render a prompt and halt the page if absent."""
    user = current_user()
    if not user:
        st.warning("Please sign in from the sidebar to continue.")
        st.stop()
    return user


def render_sidebar() -> None:
    """Render the sidebar identity panel: sign in (email + name) or sign out."""
    with st.sidebar:
        st.markdown("### USFind 🎒")
        user = current_user()
        if user:
            st.success(f"Signed in as {user['name'] or user['email']}")
            if st.button("Sign out"):
                del st.session_state["user"]
                st.rerun()
        else:
            with st.expander("Sign in", expanded=False):
                email = st.text_input("Email", key="signin_email")
                name = st.text_input("Name", key="signin_name")
                if st.button("Continue"):
                    if email and "@" in email:
                        record = db.upsert_user(email.strip(), name.strip() or None)
                        st.session_state["user"] = {
                            "id": str(record.id),
                            "email": record.email,
                            "name": record.name,
                        }
                        st.rerun()
                    else:
                        st.error("Enter a valid email address.")


def relative_time(moment: datetime) -> str:
    """Render a coarse 'time ago' string from a timestamp."""
    now = datetime.now(UTC)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    seconds = (now - moment).total_seconds()
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{int(seconds // 60)}m ago"
    if seconds < 86400:
        return f"{int(seconds // 3600)}h ago"
    return f"{int(seconds // 86400)}d ago"


def type_badge_html(item_type: str) -> str:
    """Return an inline-styled HTML badge (red for lost, green for found)."""
    color = "#dc2626" if item_type == "lost" else "#16a34a"
    return (
        f"<span style='background:{color};color:#fff;padding:2px 8px;"
        f"border-radius:6px;font-size:0.75rem;text-transform:uppercase;'>{item_type}</span>"
    )
