import streamlit as st
import os
from datetime import datetime
from pathlib import Path
from PIL import Image

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
    page_title="USFInd - Lost & Found",
    page_icon="🔍",
    layout="wide"
)

# Main app
def main():
    st.title("🔍 USFInd - Lost & Found App")
    st.markdown("*AI-Powered Item Matching System*")
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["📤 Report Found Item", "🔎 Report Lost Item", "📋 View All Items"])
    
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
                    if os.path.exists(image_path):
                        os.remove(image_path)

def page_lost_item():
    """Page for reporting lost items"""
    st.header("🔎 Report a Lost Item")
    st.write("Upload an image or describe your lost item to find potential matches.")
    
    input_method = st.radio("How would you like to describe your lost item?", ["Upload Image", "Text Description"])
    
    item_info = None
    
    if input_method == "Upload Image":
        uploaded_file = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png"])
        
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Image", width=300)
            
            if st.button("🔍 Analyze & Find Matches", type="primary"):
                with st.spinner("Analyzing image..."):
                    # Save image
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    image_filename = f"lost_{timestamp}.jpg"
                    image_path = os.path.join(IMAGES_DIR, image_filename)
                    image.save(image_path)
                    
                    # Extract info
                    item_info = extract_item_info(image_path)
                    item_info["image_path"] = image_path
    else:
        st.subheader("Describe your lost item:")
        col1, col2 = st.columns(2)
        with col1:
            item_type = st.text_input("Item Type", placeholder="e.g., phone, wallet, keys")
            color = st.text_input("Color", placeholder="e.g., black, blue, red")
        with col2:
            brand = st.text_input("Brand/Model", placeholder="e.g., iPhone 13, Nike")
            features = st.text_area("Distinctive Features", placeholder="e.g., cracked screen, red sticker")
        
        if st.button("🔍 Find Matches", type="primary"):
            item_info = {
                "item_type": item_type,
                "color": color,
                "brand": brand,
                "features": features,
                "description": f"{color} {brand} {item_type}"
            }
    
    # Find matches
    if item_info:
        item_info["timestamp"] = datetime.now().isoformat()
        
        # Save lost item to database
        item_id = add_lost_item(item_info)
        
        st.subheader("🎯 Potential Matches:")
        
        # Get all found items from database
        found_items = get_all_found_items()
        
        if not found_items:
            st.info("No found items in the database yet.")
        else:
            matches = []
            for found_item in found_items:
                score = calculate_match_score(item_info, found_item)
                if score >= 30:  # Threshold
                    matches.append((score, found_item))
            
            matches.sort(reverse=True, key=lambda x: x[0])
            
            if not matches:
                st.warning("No matches found. Try again later or adjust your description.")
            else:
                for score, found_item in matches[:5]:  # Top 5 matches
                    with st.expander(f"Match Score: {score}% - {found_item['item_type']} ({found_item['color']})"):
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            if found_item.get("image_path") and os.path.exists(found_item["image_path"]):
                                st.image(found_item["image_path"], width=200)
                        with col2:
                            st.write(f"**Item Type:** {found_item['item_type']}")
                            st.write(f"**Color:** {found_item['color']}")
                            st.write(f"**Brand:** {found_item['brand']}")
                            st.write(f"**Features:** {found_item['features']}")
                            st.write(f"**Description:** {found_item['description']}")
                            st.write(f"**Found on:** {found_item['timestamp'][:10]}")
                            st.write(f"**Database ID:** {found_item['id']}")

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
