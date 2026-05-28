"""Post Item page: upload a photo (with AI auto-description) and create an item."""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from app.core import items  # noqa: E402
from app.core.auto_description import auto_describe  # noqa: E402
from app.core.storage import StorageError  # noqa: E402
from app.ui_common import init_app, render_sidebar, require_login  # noqa: E402

st.set_page_config(page_title="Post · USFind", page_icon="📤", layout="centered")
init_app()
render_sidebar()
user = require_login()

st.header("Report a Lost or Found Item 📤")

# The uploader lives outside the form so a new file triggers a rerun and we can
# auto-describe it and pre-fill the description before submission.
uploaded = st.file_uploader("Upload a photo", type=["jpg", "jpeg", "png", "webp"], key="post_image")

if uploaded is not None:
    st.image(uploaded, width=300)
    signature = (uploaded.name, uploaded.size)
    if st.session_state.get("_ai_sig") != signature:
        st.session_state["_ai_sig"] = signature
        try:
            with st.spinner("✨ Generating an AI description…"):
                st.session_state["ai_description"] = auto_describe(uploaded.getvalue())
        except Exception:
            st.session_state["ai_description"] = ""
        # Pre-fill only when the user hasn't typed their own description yet.
        if st.session_state.get("ai_description") and not st.session_state.get("desc_field"):
            st.session_state["desc_field"] = st.session_state["ai_description"]

ai_suggestion = st.session_state.get("ai_description", "")
if ai_suggestion:
    st.caption("✨ AI suggestion — feel free to edit")
    if st.button("Apply AI suggestion"):
        st.session_state["desc_field"] = ai_suggestion
        st.rerun()

with st.form("post_item"):
    kind = st.radio("I…", ["Lost something", "Found something"], horizontal=True)
    title = st.text_input("Title", max_chars=200, key="title_field")
    description = st.text_area("Description (optional)", max_chars=2000, key="desc_field")
    location = st.text_input("Location (optional)", max_chars=200, key="loc_field")
    submitted = st.form_submit_button("Post item")

if submitted:
    item_type = "lost" if kind.startswith("Lost") else "found"
    if uploaded is None:
        st.error("Please upload a photo.")
    elif not title.strip():
        st.error("Please enter a title.")
    else:
        try:
            with st.status("Posting and indexing your item…", expanded=True) as status:
                st.write("Uploading image…")
                st.write("Generating embeddings…")
                item = items.create_item(
                    user_id=UUID(user["id"]),
                    type=item_type,
                    title=title.strip(),
                    description=description.strip() or None,
                    location=location.strip() or None,
                    uploaded_file=uploaded.getvalue(),
                    ai_description=ai_suggestion or None,
                )
                st.write("Indexing in vector database…")
                status.update(label="Done!", state="complete")
            st.session_state["view_item_id"] = str(item.id)
            st.query_params["id"] = str(item.id)
            st.switch_page("pages/3_Item_Detail.py")
        except StorageError as exc:
            st.error(f"There was a problem with your image: {exc}")
        except Exception:
            st.error("Something went wrong while posting your item. Please try again.")
