"""Item Detail page: full view of a single item with a link to matches."""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from app.core import db  # noqa: E402
from app.ui_common import init_app, relative_time, render_sidebar, type_badge_html  # noqa: E402

st.set_page_config(page_title="Item · USFind", page_icon="📋", layout="centered")
init_app()
render_sidebar()

raw_id = st.query_params.get("id") or st.session_state.get("view_item_id")
if not raw_id:
    st.info("No item selected. Visit Browse to choose one.")
    st.stop()

try:
    item = db.get_item(UUID(str(raw_id)))
except ValueError:
    item = None

if item is None:
    st.warning("This item doesn't exist or was removed.")
    st.page_link("pages/2_Browse.py", label="← Back to Browse")
    st.stop()

try:
    st.image(item.image_url, width=600)
except Exception:
    st.write("🖼️ image unavailable")

st.markdown(type_badge_html(item.type), unsafe_allow_html=True)
st.title(item.title)
if item.ai_description:
    st.caption("✨ AI-described")
st.write(item.description or "_No description provided._")
st.caption(
    f"{item.location or 'Unknown location'} · "
    f"Posted by {item.poster_name or 'someone'} · {relative_time(item.created_at)}"
)

if st.button("✨ Show possible matches"):
    matches_page = Path(__file__).resolve().parent / "4_Matches.py"
    if matches_page.exists():
        st.query_params["id"] = str(item.id)
        st.switch_page("pages/4_Matches.py")
    else:
        st.info("AI matching arrives in the next build step.")
