# app.py
import os
from datetime import datetime
from pathlib import Path

import streamlit as st
from PIL import Image

from ai_service import extract_item_info
from matching_service import calculate_match_score
from database import (
    init_database,
    add_found_item,
    add_lost_item,
    get_all_found_items,
    get_all_lost_items,
    get_database_stats,
)

# ---------- Setup ----------

IMAGES_DIR = "images"
Path(IMAGES_DIR).mkdir(exist_ok=True)

# Init DB once
init_database()

st.set_page_config(
    page_title="USFind",
    page_icon="🌿",
    layout="wide",
)

# ---------- Global styling ----------

st.markdown(
    """
<style>

/* Page container */
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 900px;
}

/* Background: light green mist */
.main {
    background: linear-gradient(180deg, #F4FFF6 0%, #EFFFF5 100%);
}

/* Typography */
h1, h2, h3 {
    color: #1B3A29;
    font-weight: 600;
    letter-spacing: 0.01em;
}
.small-muted {
    color: #5E7F6E;
    font-size: 0.85rem;
}

/* Cards */
.usf-card {
    border-radius: 16px;
    padding: 1.25rem 1.5rem;
    background: #E2F7E8;
    border: 1px solid #C4EBD0;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.06);
    transition: transform 0.08s ease-out, box-shadow 0.08s ease-out;
}
.usf-card:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.10);
}

/* Remove Streamlit form chrome (we're not using forms, but just in case) */
.stForm {
    background: transparent !important;
    padding: 0 !important;
    border-radius: 0 !important;
    border: none !important;
    box-shadow: none !important;
}

/* Inputs */
.stTextInput > div > div > input,
.stTextArea textarea {
    background-color: #F9FFF9 !important;
    border-radius: 12px !important;
    border: 1px solid #C6EAD2 !important;
    color: #1B3A29 !important;
}

/* Buttons (all) */
.stButton button {
    border-radius: 10px;         /* rectangular, soft corners */
    padding: 0.45rem 1.4rem;
    border: none;
    background: #4CAF50;
    color: white;
    font-weight: 600;
    letter-spacing: 0.02em;
    transition: transform 0.08s ease-out, box-shadow 0.08s ease-out, background 0.08s ease-out;
    cursor: pointer;
}
.stButton button:hover {
    background: #6BCF74;
    transform: translateY(-1px);
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.12);
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #E8F8EC;
    border-right: 1px solid #C4EBD0;
}
section[data-testid="stSidebar"] > div {
    padding-top: 1.5rem;
}

/* Sidebar nav: rectangular, centered buttons */
section[data-testid="stSidebar"] div[role="radiogroup"] {
    gap: 0.5rem;
}

/* Each nav "button" */
section[data-testid="stSidebar"] div[role="radiogroup"] > label {
    border-radius: 10px;
    padding: 0.5rem 0.9rem;
    background: #C8ECCF;                /* darker than sidebar bg */
    border: 1px solid #7BB889;
    cursor: pointer;
    font-weight: 600;
    text-align: center;
    transition:
        background 0.08s ease-out,
        border-color 0.08s ease-out,
        transform 0.05s ease-out,
        box-shadow 0.08s ease-out;
}

/* Hide default circular radio dot */
section[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child {
    display: none;
}

/* Text inside nav buttons */
section[data-testid="stSidebar"] div[role="radiogroup"] > label span {
    color: #1B3A29;
    font-size: 0.95rem;
}

/* Hover / cursor feedback on nav */
section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
    background: #B4E3C3;
    border-color: #4CAF50;
    transform: translateY(-1px);
    box-shadow: 0 3px 8px rgba(0, 0, 0, 0.12);
}

</style>
""",
    unsafe_allow_html=True,
)

# ---------- Hero header ----------

st.markdown(
    """
    <div style="text-align:center; margin-bottom: 1.5rem;">
        <div style="font-size: 2.1rem; font-weight: 600; color:#1B3A29; margin-bottom: 0.25rem;">
            🌿 USFind
        </div>
        <div class="small-muted">
            Minimal, calm lost & found.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------- Pages ----------

def page_found_item() -> None:
    """Page for reporting found items (simple, no extra green box)."""
    st.header("Found item")
    st.markdown(
        "<p class='small-muted'>Add a found item so its owner can look for it.</p>",
        unsafe_allow_html=True,
    )

    # no st.markdown("<div class='usf-card'>") here

    uploaded_file = st.file_uploader(
        "Photo",
        type=["jpg", "jpeg", "png"],
        key="found_photo",
    )

    col1, col2 = st.columns(2)
    with col1:
        manual_type = st.text_input("Item", placeholder="Wallet, keys, phone")
        manual_color = st.text_input("Color")
    with col2:
        manual_brand = st.text_input("Brand / model")
        manual_features = st.text_area("Details", placeholder="Scratches, stickers, tag…")

    if st.button("Save item", key="save_found"):
        if uploaded_file is None:
            st.warning("Please add a photo.")
        else:
            with st.spinner("Saving item..."):
                image = Image.open(uploaded_file)

                # Save image to disk
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                image_filename = f"found_{timestamp}.jpg"
                image_path = os.path.join(IMAGES_DIR, image_filename)
                image.save(image_path)

                # Extract info with AI
                item_info = extract_item_info(image_path)

                # Manual overrides
                if manual_type:
                    item_info["item_type"] = manual_type
                if manual_color:
                    item_info["color"] = manual_color
                if manual_brand:
                    item_info["brand"] = manual_brand
                if manual_features:
                    item_info["features"] = manual_features

                # Metadata
                item_info["image_path"] = image_path
                item_info["timestamp"] = datetime.now().isoformat()
                item_info["type"] = "found"

                item_id = add_found_item(item_info)

                st.success(f"Item saved (ID: {item_id}).")

                col_img, col_text = st.columns([1, 2])
                with col_img:
                    if os.path.exists(image_path):
                        st.image(image_path, use_column_width=True)
                with col_text:
                    st.markdown(f"**Item:** {item_info.get('item_type','Unknown')}")
                    st.markdown(f"**Color:** {item_info.get('color','Unknown')}")
                    st.markdown(f"**Brand:** {item_info.get('brand','Unknown')}")
                    st.markdown(f"**Details:** {item_info.get('features','') or '—'}")
                    st.markdown(f"**Description:** {item_info.get('description','') or '—'}")



def page_lost_item() -> None:
    """Page for reporting lost items and finding matches."""
    st.header("Lost item")
    st.markdown(
        "<p class='small-muted'>Tell us about it and we’ll look for a match.</p>",
        unsafe_allow_html=True,
    )

    item_info = None  # ensure defined

    input_method = st.radio(
        "How do you want to describe it?",
        ["Photo", "Text"],
        horizontal=True,
        key="lost_method",
    )

    if input_method == "Photo":
        uploaded_file = st.file_uploader(
            "Photo",
            type=["jpg", "jpeg", "png"],
            key="lost_photo",
        )
        if st.button("Find matches", key="lost_photo_button"):
            if uploaded_file is None:
                st.warning("Please add a photo.")
            else:
                with st.spinner("Analyzing photo..."):
                    image = Image.open(uploaded_file)

                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    image_filename = f"lost_{timestamp}.jpg"
                    image_path = os.path.join(IMAGES_DIR, image_filename)
                    image.save(image_path)

                    item_info = extract_item_info(image_path)
                    item_info["image_path"] = image_path

                    st.image(image_path, caption="Your item", width=260)

    else:  # Text description
        col1, col2 = st.columns(2)
        with col1:
            item_type = st.text_input("Item", placeholder="Phone, wallet, bag")
            color = st.text_input("Color", placeholder="Black, blue, red")
        with col2:
            brand = st.text_input("Brand / model", placeholder="iPhone 13, Nike")
            features = st.text_area("Details", placeholder="Cracked screen, red sticker…")

        if st.button("Find matches", key="lost_text_button"):
            if not (item_type or color or brand or features):
                st.warning("Please add a few details.")
            else:
                item_info = {
                    "item_type": item_type.strip() or "Unknown",
                    "color": color.strip() or "Unknown",
                    "brand": brand.strip() or "Unknown",
                    "features": features.strip() or "",
                    "description": f"{color} {brand} {item_type}".strip(),
                }

    # If we have a description, search for matches
    if item_info:
        item_info["timestamp"] = datetime.now().isoformat()

        # Save lost item
        item_id = add_lost_item(item_info)
        st.markdown(f"<p class='small-muted'>Saved as lost item ID {item_id}.</p>", unsafe_allow_html=True)

        st.subheader("Possible matches")

        found_items = get_all_found_items()
        if not found_items:
            st.info("No found items yet.")
            return

        matches = []
        for found_item in found_items:
            score = calculate_match_score(item_info, found_item)
            if score >= 30:  # threshold
                matches.append((score, found_item))

        matches.sort(reverse=True, key=lambda x: x[0])

        if not matches:
            st.warning("No clear matches yet. Try a different photo or description.")
            return

        for score, found_item in matches[:6]:
            with st.container():
                st.markdown("<div class='usf-card'>", unsafe_allow_html=True)
                col_img, col_text = st.columns([1, 3])
                with col_img:
                    if os.path.exists(found_item.get("image_path", "")):
                        st.image(found_item["image_path"], width=180)
                with col_text:
                    st.markdown(f"**Match score:** {score}%")
                    st.markdown(
                        f"**Item:** {found_item.get('item_type','Unknown').title()} "
                        f"({found_item.get('color','')})"
                    )
                    st.markdown(f"**Brand:** {found_item.get('brand','Unknown')}")
                    st.markdown(f"**Details:** {found_item.get('features','') or '—'}")
                    st.markdown(f"**Found on:** {found_item.get('timestamp','')[:10]}")
                st.markdown("</div>", unsafe_allow_html=True)


def page_view_all() -> None:
    """Page to view all found items."""
    st.header("All found items")

    found_items = get_all_found_items()
    if not found_items:
        st.info("No items yet. Add the first found item.")
        return

    st.markdown(
        f"<p class='small-muted'>Total items: {len(found_items)}</p>",
        unsafe_allow_html=True,
    )

    cols = st.columns(3)
    for idx, item in enumerate(found_items):
        with cols[idx % 3]:
            st.markdown("<div class='usf-card'>", unsafe_allow_html=True)
            if item.get("image_path") and os.path.exists(item["image_path"]):
                st.image(item["image_path"], use_container_width=True)
            st.markdown(f"**{item.get('item_type','Unknown')}** ({item.get('color','')})")
            st.markdown(f"Brand: {item.get('brand','Unknown')}")
            st.markdown(f"Found: {item.get('timestamp','')[:10]}")
            st.caption(f"ID: {item.get('id','?')}")
            st.markdown("</div>", unsafe_allow_html=True)


# ---------- Main ----------

def main() -> None:
    # Sidebar navigation
    st.sidebar.markdown("### Navigation")
    st.sidebar.markdown(
        "<p class='small-muted'>What do you want to do?</p>",
        unsafe_allow_html=True,
    )

    page = st.sidebar.radio(
        "",
        ["Found item", "Lost item", "View items"],
        index=0,
        key="nav",
    )

    # Sidebar stats
    stats = get_database_stats()
    st.sidebar.markdown("---")
    st.sidebar.subheader("Database")
    st.sidebar.metric("Found", stats.get("found_items", 0))
    st.sidebar.metric("Lost", stats.get("lost_items", 0))

    if page == "Found item":
        page_found_item()
    elif page == "Lost item":
        page_lost_item()
    else:
        page_view_all()


if __name__ == "__main__":
    main()
