"""Browse page: paginated feed of open items with lost/found filters."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from app.core import db  # noqa: E402
from app.ui_common import init_app, relative_time, render_sidebar, type_badge_html  # noqa: E402

PAGE_SIZE = 20

st.set_page_config(page_title="Browse · USFind", page_icon="🔍", layout="wide")
init_app()
render_sidebar()

st.header("Browse items 🔍")

choice = st.radio("Filter", ["All", "Lost", "Found"], horizontal=True, key="browse_filter")
type_filter = {"All": None, "Lost": "lost", "Found": "found"}[choice]

# Reset the visible window whenever the filter changes.
if st.session_state.get("_browse_prev_filter") != choice:
    st.session_state["feed_count"] = PAGE_SIZE
    st.session_state["_browse_prev_filter"] = choice

count = st.session_state.get("feed_count", PAGE_SIZE)
rows = db.list_items(type=type_filter, status="open", limit=count, offset=0)

if not rows:
    st.info("No open items yet. Be the first to post one!")
else:
    columns = st.columns(3)
    for index, item in enumerate(rows):
        with columns[index % 3]:
            try:
                st.image(item.image_url, use_column_width=True)
            except Exception:
                st.write("🖼️ image unavailable")
            st.markdown(type_badge_html(item.type), unsafe_allow_html=True)
            st.markdown(f"**{item.title[:60]}**")
            st.caption(f"{item.location or '—'} · {relative_time(item.created_at)}")
            if st.button("View", key=f"view_{item.id}"):
                st.query_params["id"] = str(item.id)
                st.switch_page("pages/3_Item_Detail.py")

    if len(rows) == count:
        if st.button("Load more"):
            st.session_state["feed_count"] = count + PAGE_SIZE
            st.rerun()
