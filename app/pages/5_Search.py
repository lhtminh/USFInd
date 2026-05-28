"""Conversational search: parse free text into filters and run semantic recall."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from app.core import retrieval  # noqa: E402
from app.ui_common import init_app, relative_time, render_sidebar, type_badge_html  # noqa: E402

st.set_page_config(page_title="Search · USFind", page_icon="💬", layout="wide")
init_app()
render_sidebar()

st.header("Conversational search 💬")

query = st.text_input(
    "Describe what you're looking for",
    placeholder="e.g., I lost a blue water bottle near the library yesterday",
)
go = st.button("Search", type="primary")

if go and query.strip():
    try:
        with st.spinner("🧠 Understanding your search…"):
            parsed = retrieval.parse_search_query(query.strip())
    except Exception:
        st.error("Couldn't understand the query right now. Please try again or rephrase.")
        st.stop()

    chips = []
    if parsed.item_type:
        chips.append(f"🏷️ {parsed.item_type}")
    if parsed.color:
        chips.append(f"🎨 {parsed.color}")
    if parsed.location:
        chips.append(f"📍 {parsed.location}")
    if parsed.time_window_hours:
        chips.append(f"⏰ last {parsed.time_window_hours}h")
    chips.append(f"🔎 searching: {parsed.search_type}")
    if chips:
        st.caption(" · ".join(chips))

    try:
        with st.spinner("🎯 Searching and re-ranking…"):
            result = retrieval.conversational_search(parsed)
    except Exception:
        st.error("Search failed. Please try again shortly.")
        st.stop()

    if not result.candidates:
        st.info("No matching items yet. Try broadening your description.")
    else:
        st.success(f"Top {len(result.candidates)} matches:")
        for candidate in result.candidates:
            item = candidate.item
            with st.container(border=True):
                left, right = st.columns([1, 3])
                with left:
                    try:
                        st.image(item.image_url, width=200)
                    except Exception:
                        st.write("🖼️")
                with right:
                    st.markdown(type_badge_html(item.type), unsafe_allow_html=True)
                    st.markdown(f"**{item.title}**")
                    st.caption(
                        f"{item.location or '—'} · "
                        f"Posted by {item.poster_name or 'someone'} · "
                        f"{relative_time(item.created_at)}"
                    )
                    score = int(candidate.rerank_score or 0)
                    st.progress(score / 100, text=f"Match confidence: {score}%")
                    if candidate.explanation:
                        st.markdown(f"_{candidate.explanation}_")

    st.divider()
    st.caption(
        f"Stage 1 (text recall): {result.stage1_ms:.0f}ms | "
        f"Stage 2 (rerank): {result.stage2_ms:.0f}ms | "
        f"Total: {result.total_ms:.0f}ms"
    )
