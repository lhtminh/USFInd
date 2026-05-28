"""Matches page: run the 2-stage retrieval pipeline and show ranked matches."""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from app.core import db, items, retrieval  # noqa: E402
from app.ui_common import (  # noqa: E402
    init_app,
    relative_time,
    render_sidebar,
    require_login,
    type_badge_html,
)

st.set_page_config(page_title="Matches · USFind", page_icon="✨", layout="wide")
init_app()
render_sidebar()
user = require_login()

# Surface the most recent confirmation result across reruns.
_match_msg = st.session_state.pop("_last_match_msg", None)
if _match_msg:
    (st.success if _match_msg.startswith("✅") else st.error)(_match_msg)

raw_id = st.query_params.get("id") or st.session_state.get("view_item_id")
if not raw_id:
    st.info("No item selected. Open an item and choose “Show possible matches”.")
    st.stop()

try:
    query_item = db.get_item(UUID(str(raw_id)))
except ValueError:
    query_item = None

if query_item is None:
    st.warning("That item doesn't exist anymore.")
    st.page_link("pages/2_Browse.py", label="← Back to Browse")
    st.stop()

st.markdown("#### Finding matches for")
header_left, header_right = st.columns([1, 4])
with header_left:
    try:
        st.image(query_item.image_url, width=120)
    except Exception:
        st.write("🖼️")
with header_right:
    st.markdown(type_badge_html(query_item.type), unsafe_allow_html=True)
    st.markdown(f"**{query_item.title}**")

try:
    with st.spinner("🔍 Stage 1 vector recall → 🧠 Stage 2 Gemini Pro re-ranking…"):
        result = retrieval.full_retrieval(query_item.id)
except retrieval.RetrievalError:
    st.error("We can't search yet — this item may still be indexing. Try again shortly.")
    st.stop()
except Exception:
    st.error("Something went wrong while finding matches. Please try again.")
    st.stop()

if not result.candidates:
    st.info(
        "No likely matches yet. We'll keep looking as new items are posted — "
        "or try conversational search to broaden the criteria."
    )
else:
    st.success(f"Found {len(result.candidates)} likely match(es).")
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
                    f"{item.location or '—'} · Posted by {item.poster_name or 'someone'} · "
                    f"{relative_time(item.created_at)}"
                )
                score = int(candidate.rerank_score or 0)
                st.progress(score / 100, text=f"Match confidence: {score}%")
                if candidate.explanation:
                    st.markdown(f"_{candidate.explanation}_")
                with st.expander("🔬 Technical scores"):
                    st.write(
                        {
                            "combined_score": round(candidate.combined_score, 3),
                            "image_score": round(candidate.image_score, 3),
                            "text_score": round(candidate.text_score, 3),
                            "rerank_score": candidate.rerank_score,
                        }
                    )
                pending_key = f"_pending_confirm_{item.id}"
                if not st.session_state.get(pending_key):
                    if st.button("This is mine!", key=f"mine_{item.id}"):
                        st.session_state[pending_key] = True
                        st.rerun()
                else:
                    st.warning(
                        f"Confirm **{item.title}** is the same as your "
                        f"**{query_item.title}**? The poster's email will be shared "
                        "so you can coordinate."
                    )
                    yes_col, no_col = st.columns(2)
                    with yes_col:
                        if st.button("Yes, confirm", key=f"yes_{item.id}", type="primary"):
                            try:
                                items.confirm_match(
                                    query_item.id,
                                    candidate.item_id,
                                    UUID(user["id"]),
                                    candidate.combined_score,
                                    candidate.rerank_score,
                                )
                                other = db.get_user(item.user_id)
                                contact = other.email if other else "the poster"
                                st.session_state["_last_match_msg"] = (
                                    f"✅ Match confirmed! Contact: {contact}"
                                )
                            except Exception:
                                st.session_state["_last_match_msg"] = (
                                    "❌ Couldn't confirm the match. Please try again."
                                )
                            st.session_state.pop(pending_key, None)
                            st.rerun()
                    with no_col:
                        if st.button("Cancel", key=f"no_{item.id}"):
                            st.session_state.pop(pending_key, None)
                            st.rerun()

st.divider()
st.caption(
    f"Stage 1: {result.stage1_ms:.0f}ms | Stage 2: {result.stage2_ms:.0f}ms | "
    f"Total: {result.total_ms:.0f}ms"
)
st.caption(f"Cache: {'HIT' if result.cache_hit else 'MISS'}")
st.caption("🧠 Pipeline: Qdrant HNSW recall (top 50) → Gemini 2.5 Pro re-ranking (top 10)")
