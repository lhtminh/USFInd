"""USFind entry point: page config, app init, sidebar auth, and landing content."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st  # noqa: E402

from app.ui_common import current_user, init_app, render_sidebar  # noqa: E402

st.set_page_config(page_title="USFind", page_icon="🎒", layout="wide")

init_app()
render_sidebar()

st.title("USFind 🎒 — AI-powered lost & found for USF")

if current_user():
    st.write(
        "You're signed in. Use the pages in the sidebar to post an item, browse the "
        "feed, search conversationally, and review AI-matched results."
    )
else:
    st.markdown(
        "Lost something on campus? Found something that isn't yours? USFind uses "
        "multi-modal AI to match lost and found items: upload a photo, and a 2-stage "
        "retrieval pipeline (vector recall + LLM re-ranking) surfaces the most likely "
        "matches with plain-language explanations."
    )
    st.markdown("**Built with:** Streamlit · Postgres · Qdrant · Redis · CLIP · Gemini")
    st.info("Sign in from the sidebar to post items and see your matches.")
