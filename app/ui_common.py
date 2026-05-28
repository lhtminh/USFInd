"""Shared Streamlit helpers: app init, session auth, formatting, CSS, and cards.

Every page calls ``init_app()`` and ``inject_css()`` right after ``set_page_config``.
``render_item_card``, ``render_empty_state``, and the badge helpers are the
single source of truth for the polished UI — never render cards/empty states ad
hoc in a page.
"""

from __future__ import annotations

import os
import sys
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

# Ensure repo root importable when launched via `streamlit run app/streamlit_app.py`.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st  # noqa: E402

from app.core import db  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.logging_config import configure_logging  # noqa: E402


# ---------------- App init --------------------------------------------------


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


# ---------------- Auth ------------------------------------------------------


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
        st.markdown("### 🎒 USFind")
        user = current_user()
        if user:
            st.success(f"Signed in as **{user['name'] or user['email']}**")
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


# ---------------- Formatting ------------------------------------------------


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
    """Return the class-based badge HTML for a 'lost' or 'found' item."""
    return f"<span class='usfind-badge usfind-badge-{item_type}'>{item_type}</span>"


def status_badge_html(status: str) -> str:
    """Return the class-based badge HTML for an item lifecycle status."""
    return f"<span class='usfind-badge usfind-badge-{status}'>{status}</span>"


# ---------------- Global CSS ------------------------------------------------


_CSS = """
<style>
html, body, [data-testid="stAppViewContainer"] { background-color: #ffffff; }
[data-testid="stSidebar"] { background-color: #f8fafc; }

[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] { right: 1rem; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }

html, body, [class*="css"] {
  font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto,
               Oxygen, Ubuntu, sans-serif !important;
}
h1, h2, h3, h4 { letter-spacing: -0.01em; line-height: 1.18; }

[data-testid="stButton"] > button {
  border-radius: 10px !important;
  font-weight: 600 !important;
  padding: 0.45rem 1rem !important;
  border: 1px solid rgba(15, 23, 42, 0.08) !important;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  transition: transform 80ms ease, box-shadow 120ms ease;
}
[data-testid="stButton"] > button:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.08);
}

[data-testid="stContainer"] { border-radius: 14px !important; }
[data-testid="stContainer"] [data-testid="stImage"] img {
  border-radius: 10px;
  object-fit: cover;
}

hr { opacity: 0.6; }

.usfind-badge {
  display: inline-block;
  padding: 2px 9px;
  border-radius: 999px;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-right: 0.35rem;
}
.usfind-badge-lost    { background: #fee2e2; color: #b91c1c; }
.usfind-badge-found   { background: #dcfce7; color: #166534; }
.usfind-badge-matched { background: #dbeafe; color: #1d4ed8; }
.usfind-badge-open    { background: #e0f2fe; color: #075985; }
.usfind-badge-closed  { background: #e5e7eb; color: #374151; }

.usfind-hero { padding: 1.4rem 0 1rem; }
.usfind-hero h1 { font-size: 2.4rem; font-weight: 700; margin: 0 0 0.5rem 0; }
.usfind-hero-sub { color: #475569; font-size: 1.05rem; max-width: 62ch; }
.usfind-chips {
  margin-top: 0.9rem;
  display: flex;
  gap: 0.4rem;
  flex-wrap: wrap;
}
.usfind-chip {
  background: #f1f5f9;
  color: #0f172a;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  padding: 3px 10px;
  font-size: 0.78rem;
  font-weight: 600;
}

.usfind-feature-title { font-weight: 700; margin-bottom: 0.2rem; }
.usfind-feature-body  { color: #475569; font-size: 0.92rem; }

.usfind-empty {
  text-align: center;
  padding: 2.2rem 1rem 1rem;
  color: #475569;
}
.usfind-empty-emoji { font-size: 2.6rem; }
.usfind-empty-title { font-size: 1.15rem; font-weight: 700; color: #0f172a; margin-top: 0.4rem; }
.usfind-empty-body  { max-width: 46ch; margin: 0.3rem auto 0.9rem; }

@media (max-width: 720px) {
  [data-testid="stHorizontalBlock"] { flex-direction: column; }
  [data-testid="stHorizontalBlock"] > [data-testid="column"] {
    flex: 1 1 100% !important;
    width: 100% !important;
    min-width: 100% !important;
  }
}
</style>
"""


def inject_css() -> None:
    """Inject the project-wide stylesheet. Safe to call once per page."""
    st.markdown(_CSS, unsafe_allow_html=True)


# ---------------- Card + empty-state components -----------------------------


def render_item_card(
    item: object,
    *,
    on_view_key: str | None = None,
    view_label: str = "View details →",
    extra_badge_html: str | None = None,
    body_renderer: Callable[[], None] | None = None,
    image_width: int | None = None,
) -> bool:
    """Render a consistent card for an item and return True iff View was clicked."""
    clicked = False
    with st.container(border=True):
        try:
            if image_width is not None:
                st.image(item.image_url, width=image_width)
            else:
                st.image(item.image_url, use_column_width=True)
        except Exception:
            st.markdown("🖼️ _image unavailable_")
        badges = type_badge_html(item.type)
        if extra_badge_html:
            badges += " " + extra_badge_html
        st.markdown(badges, unsafe_allow_html=True)
        st.markdown(f"**{item.title[:80]}**")
        meta_parts: list[str] = []
        if item.location:
            meta_parts.append(item.location)
        if getattr(item, "poster_name", None):
            meta_parts.append(f"by {item.poster_name}")
        meta_parts.append(relative_time(item.created_at))
        st.caption(" · ".join(meta_parts))
        if body_renderer is not None:
            body_renderer()
        if on_view_key:
            clicked = st.button(view_label, key=on_view_key)
    return clicked


def render_empty_state(
    emoji: str,
    title: str,
    body: str,
    *,
    cta_label: str | None = None,
    cta_page: str | None = None,
) -> None:
    """Friendly empty/no-results state with optional CTA."""
    st.markdown(
        f"""
        <div class='usfind-empty'>
          <div class='usfind-empty-emoji'>{emoji}</div>
          <div class='usfind-empty-title'>{title}</div>
          <div class='usfind-empty-body'>{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if cta_label and cta_page:
        st.page_link(cta_page, label=cta_label)
