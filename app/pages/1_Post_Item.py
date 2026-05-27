"""Post Item page: upload a photo and create a lost/found item."""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from app.core import items  # noqa: E402
from app.core.storage import StorageError  # noqa: E402
from app.ui_common import init_app, render_sidebar, require_login  # noqa: E402

st.set_page_config(page_title="Post · USFind", page_icon="📤", layout="centered")
init_app()
render_sidebar()
user = require_login()

st.header("Report a Lost or Found Item 📤")

with st.form("post_item", clear_on_submit=False):
    kind = st.radio("I…", ["Lost something", "Found something"], horizontal=True)
    uploaded = st.file_uploader("Upload a photo", type=["jpg", "jpeg", "png", "webp"])
    if uploaded is not None:
        st.image(uploaded, width=300)
    title = st.text_input("Title", max_chars=200)
    description = st.text_area("Description (optional)", max_chars=2000)
    location = st.text_input("Location (optional)", max_chars=200)
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
