import streamlit as st
import os
from datetime import datetime
from pathlib import Path
from PIL import Image

st.set_page_config(
    page_title="USFind",
    page_icon="🌿",
    layout="wide"
)

# Minimalistic nature-themed styling
st.markdown("""
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

/* Headers */
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
}

/* Inputs */
.stTextInput > div > div > input,
.stTextArea textarea {
    background-color: #F9FFF9 !important;
    border-radius: 12px !important;
    border: 1px solid #C6EAD2 !important;
    color: #1B3A29 !important;
}

/* Buttons */
.stButton button {
    border-radius: 999px;
    padding: 0.45rem 1.7rem;
    border: none;
    background: #4CAF50;
    color: white;
    font-weight: 600;
    letter-spacing: 0.02em;
}
.stButton button:hover {
    background: #6BCF74;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #E8F8EC;
    border-right: 1px solid #C4EBD0;
}
section[data-testid="stSidebar"] > div {
    padding-top: 1.5rem;
}

</style>
""", unsafe_allow_html=True)

# Hero header
st.markdown(
    """
    <div style="text-align:center; margin-bottom: 1.5rem;">
        <div style="font-size: 2.1rem; font-weight: 600; color:#1B3A29; margin-bottom: 0.25rem;">
            🌿 USFInd
        </div>
        <div class="small-muted">
            A calm, light-green place to reconnect people with their lost items.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Import services
from ai_service import extract_item_info
from matching_service import calculate_match_score
from database import (
    init_database, 
    add_found_item, 
    add_lost_item, 
    get_all_found_items, 
    get_all_lost_items,
    get_database_stats
)

# Configuration
IMAGES_DIR = "images"

# Create images directory if it doesn't exist
Path(IMAGES_DIR).mkdir(exist_ok=True)

# Initialize database
init_database()

# Page configuration
st.set_page_config(
    page_title="USFind - Lost & Found",
    page_icon="🔍",
    layout="wide"
)

# Light styling to make the app look nicer
st.markdown(
    """
    <style>
    .big-title {font-size:32px; font-weight:700;}
    .muted {color: #6c757d}
    .card {border-radius:8px; padding:12px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);}
    </style>
    """,
    unsafe_allow_html=True,
)

# Use service modules for AI extraction, matching, and storage.
# Local JSON helpers and duplicate AI/matching implementations were removed
# to keep logic centralized in `ai_service.py`, `matching_service.py`, and `database.py`.

# Main app
def main():
    st.title("🔍 USFind - Lost & Found App")
    st.markdown("*AI-Powered Item Matching System*")
    
    # (Data persisted via SQLite through `database.py` functions)
    
    # Sidebar navigation + help
    st.sidebar.title("Navigation")
    st.sidebar.markdown("Use this app to report found items, report lost items, and search for matches.")
    page = st.sidebar.radio("Go to", ["📤 Report Found Item", "🔎 Report Lost Item", "📋 View All Items"])
    with st.sidebar.expander("Helpful tips"):
        st.write("• Upload clear photos that show distinctive features.")
        st.write("• If AI extraction fails, use the manual description option.")
        st.write("• Matches are heuristic-based; check details carefully.")
    
    # Display stats in sidebar
    stats = get_database_stats()
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Database Stats")
    st.sidebar.metric("Found Items", stats['found_items'])
    st.sidebar.metric("Lost Items", stats['lost_items'])
    st.sidebar.metric("Total Items", stats['total_items'])
    
    if page == "📤 Report Found Item":
        page_found_item()
    elif page == "🔎 Report Lost Item":
        page_lost_item()
    else:
        page_view_all()

def page_found_item():
    """Page for reporting found items"""
    st.header("📤 Report a Found Item")
    st.write("Upload an image of the item you found, and AI will extract its details.")
    
    uploaded_file = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        # Display uploaded image
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image", width=300)
        
        if st.button("🔍 Extract Item Information", type="primary"):
            with st.spinner("Analyzing image with AI..."):
                # Save image
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                image_filename = f"found_{timestamp}.jpg"
                image_path = os.path.join(IMAGES_DIR, image_filename)
                image.save(image_path)
                
                # Extract info using AI
                item_info = extract_item_info(image_path)
                
                # Only save if extraction was successful
                if item_info.get("item_type") != "Unknown":
                    # Add metadata
                    item_info["image_path"] = image_path
                    item_info["timestamp"] = datetime.now().isoformat()
                    
                    # Save to database
                    item_id = add_found_item(item_info)
                    
                    st.success(f"✅ Item successfully added to the database! (ID: {item_id})")
                    
                    # Display extracted information
                    st.subheader("Extracted Information:")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Item Type:** {item_info['item_type']}")
                        st.write(f"**Color:** {item_info['color']}")
                        st.write(f"**Brand:** {item_info['brand']}")
                    with col2:
                        st.write(f"**Features:** {item_info['features']}")
                        st.write(f"**Description:** {item_info['description']}")
                else:
                    st.error("❌ Failed to extract item information. Please check your API key and try again.")
                    # Clean up the saved image
                    image.close()
                    if os.path.exists(image_path):
                        try:
                            os.remove(image_path)
                        except PermissionError:
                            pass  # Skip if file is in use
    st.write("Upload a clear image of the found item. The app will try to extract details using AI — you can edit them before saving.")

    with st.form(key="found_form", clear_on_submit=False):
        uploaded_file = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png"], key="found_upload")
        manual_type = st.text_input("Item Type", placeholder="e.g., wallet, keys, phone")
        manual_color = st.text_input("Color")
        manual_brand = st.text_input("Brand/Model")
        manual_features = st.text_area("Distinctive Features")
        submitted = st.form_submit_button("🔍 Analyze & Save")

    if uploaded_file is not None and submitted:
        with st.spinner("Processing image and extracting information..."):
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Image", width=320)

            # Save image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_filename = f"found_{timestamp}.jpg"
            image_path = os.path.join(IMAGES_DIR, image_filename)
            image.save(image_path)

            # Try AI extraction, but allow manual overrides
            item_info = extract_item_info(image_path)

            # Merge manual fields (manual input takes precedence if provided)
            if manual_type:
                item_info["item_type"] = manual_type
            if manual_color:
                item_info["color"] = manual_color
            if manual_brand:
                item_info["brand"] = manual_brand
            if manual_features:
                item_info["features"] = manual_features

            # Add metadata
            item_info["image_path"] = image_path
            item_info["timestamp"] = datetime.now().isoformat()
            item_info["type"] = "found"

            # Save to database (SQLite)
            item_id = add_found_item(item_info)

            st.success(f"✅ Item added to the database (ID: {item_id})!")

            st.subheader("Extracted / Saved Information")
            col1, col2 = st.columns([1, 2])
            with col1:
                if os.path.exists(item_info["image_path"]):
                    st.image(item_info["image_path"], use_column_width=True)
            with col2:
                st.markdown(f"**Item Type:** {item_info.get('item_type','Unknown')}")
                st.markdown(f"**Color:** {item_info.get('color','Unknown')}")
                st.markdown(f"**Brand:** {item_info.get('brand','Unknown')}")
                st.markdown(f"**Features:** {item_info.get('features','')}")
                st.markdown(f"**Description:** {item_info.get('description','')}")

def page_lost_item():
    """Page for reporting lost items"""
    st.header("🔎 Report a Lost Item")
    st.write("Upload a photo or enter a description to search for potential matches among reported found items.")

    input_method = st.radio("How would you like to describe your lost item?", ["Upload Image", "Text Description"]) 
    item_info = None

    if input_method == "Upload Image":
        with st.form(key="lost_image_form"):
            uploaded_file = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png"], key="lost_upload")
            analyze = st.form_submit_button("🔍 Analyze & Find Matches")

        if uploaded_file is not None and analyze:
            with st.spinner("Analyzing image..."):
                image = Image.open(uploaded_file)
                st.image(image, caption="Uploaded Image", width=320)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                image_filename = f"lost_{timestamp}.jpg"
                image_path = os.path.join(IMAGES_DIR, image_filename)
                image.save(image_path)

                item_info = extract_item_info(image_path)
                item_info["image_path"] = image_path
    else:
        with st.form(key="lost_text_form"):
            st.subheader("Describe your lost item:")
            col1, col2 = st.columns(2)
            with col1:
                item_type = st.text_input("Item Type", placeholder="e.g., phone, wallet, keys")
                color = st.text_input("Color", placeholder="e.g., black, blue, red")
            with col2:
                brand = st.text_input("Brand/Model", placeholder="e.g., iPhone 13, Nike")
                features = st.text_area("Distinctive Features", placeholder="e.g., cracked screen, red sticker")
            find_matches = st.form_submit_button("🔍 Find Matches")

        if find_matches:
            item_info = {
                "item_type": item_type.strip() or "Unknown",
                "color": color.strip() or "Unknown",
                "brand": brand.strip() or "Unknown",
                "features": features.strip() or "",
                "description": f"{color} {brand} {item_type}".strip()
            }
    
    # Find matches
    if item_info:
        item_info["timestamp"] = datetime.now().isoformat()
        
        # Save lost item to database
        item_id = add_lost_item(item_info)

        st.subheader("🎯 Potential Matches")

        # Get all found items from database
        found_items = get_all_found_items()
        
        if not found_items:
            st.info("No found items in the database yet. Consider adding a found item first.")
        else:
            matches = []
            for found_item in found_items:
                score = calculate_match_score(item_info, found_item)
                if score >= 30:  # Threshold
                    matches.append((score, found_item))

            matches.sort(reverse=True, key=lambda x: x[0])

            if not matches:
                st.warning("No matches found. Try adjusting your description or upload a clearer image.")
            else:
                # Display top matches as cards with progress bars
                for score, found_item in matches[:6]:  # Top 6 matches
                    with st.container():
                        st.markdown("<div class='card'>", unsafe_allow_html=True)
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            if os.path.exists(found_item["image_path"]):
                                st.image(found_item["image_path"], width=200)
                        with col2:
                            st.metric(label="Match Score", value=f"{score}%")
                            st.markdown(f"**{found_item.get('item_type','Unknown').title()}** — {found_item.get('color','')}")
                            st.markdown(f"**Brand:** {found_item.get('brand','Unknown')}")
                            st.markdown(f"**Features:** {found_item.get('features','')}")
                            st.markdown(f"**Found on:** {found_item.get('timestamp','')[:10]}")
                            st.progress(min(score/100, 1.0))
                        st.markdown("</div>", unsafe_allow_html=True)

def page_view_all():
    """Page to view all found items"""
    st.header("📋 All Found Items")
    
    # Get all found items from database
    found_items = get_all_found_items()
    
    if not found_items:
        st.info("No items found yet. Be the first to report a found item!")
    else:
        st.write(f"Total found items: **{len(found_items)}**")
        
        # Display items in grid
        cols = st.columns(3)
        for idx, item in enumerate(found_items):
            with cols[idx % 3]:
                with st.container():
                    if item.get("image_path") and os.path.exists(item["image_path"]):
                        st.image(item["image_path"], use_container_width=True)
                    st.write(f"**{item['item_type']}** ({item['color']})")
                    st.write(f"Brand: {item['brand']}")
                    st.write(f"Found: {item['timestamp'][:10]}")
                    st.caption(f"ID: {item['id']}")
                    st.divider()

if __name__ == "__main__":
    main()
