"""Me page: my posted items and my confirmed matches."""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from app.core import db  # noqa: E402
from app.ui_common import (  # noqa: E402
    init_app,
    relative_time,
    render_sidebar,
    require_login,
    type_badge_html,
)

st.set_page_config(page_title="Me · USFind", page_icon="👤", layout="wide")
init_app()
render_sidebar()
user = require_login()
user_id = UUID(user["id"])

st.header("Your USFind 👤")

st.subheader("Your posted items")
posts = db.list_user_items(user_id)
if not posts:
    st.info("You haven't posted any items yet.")
else:
    columns = st.columns(3)
    for index, item in enumerate(posts):
        with columns[index % 3]:
            try:
                st.image(item.image_url, use_column_width=True)
            except Exception:
                st.write("🖼️")
            st.markdown(type_badge_html(item.type), unsafe_allow_html=True)
            st.markdown(f"**{item.title}**")
            color = {"matched": "green", "closed": "orange"}.get(item.status, "blue")
            st.caption(f":{color}[{item.status}] · {relative_time(item.created_at)}")

st.divider()
st.subheader("Your confirmed matches")
matches = db.list_user_matches(user_id)
if not matches:
    st.info("No confirmed matches yet.")
else:
    for match in matches:
        with st.container(border=True):
            left, right = st.columns(2)
            for side, prefix in [(left, "item_a"), (right, "item_b")]:
                with side:
                    try:
                        st.image(match[f"{prefix}_image"], use_column_width=True)
                    except Exception:
                        st.write("🖼️")
                    is_mine = match[f"{prefix}_user_id"] == user_id
                    label = "**your post**" if is_mine else "**other party**"
                    st.markdown(f"{label} — {match[f'{prefix}_title']}")
            rerank = match.get("rerank_score")
            st.caption(
                f"Confirmed {relative_time(match['confirmed_at'])} · "
                f"rerank score {int(rerank) if rerank is not None else '—'}"
            )

st.divider()
if st.button("Sign out", key="me_signout"):
    st.session_state.pop("user", None)
    st.rerun()
