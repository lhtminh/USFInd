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

# Initialize data storage
def load_data():
    """Load data from JSON file"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {"found_items": [], "lost_items": []}

def save_data(data):
    """Save data to JSON file"""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def extract_item_info(image_path):
    """Use Google Gemini Vision API to extract item information"""
    try:
        # Load the image
        img = Image.open(image_path)
        
        # Initialize Gemini model
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = """Analyze this image of a lost/found item and extract the following information in a structured format:
- Item Type: (e.g., phone, wallet, keys, bag, etc.)
- Color: (primary color)
- Brand/Model: (if visible)
- Distinctive Features: (unique characteristics, damages, stickers, etc.)
- Description: (brief overall description)

Format your response as JSON with these exact keys: item_type, color, brand, features, description"""
        
        # Generate response
        response = model.generate_content([prompt, img])
        content = response.text
        
        # Try to extract JSON from response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        return json.loads(content)
    except Exception as e:
        st.error(f"Error extracting item info: {str(e)}")
        return {
            "item_type": "Unknown",
            "color": "Unknown",
            "brand": "Unknown",
            "features": "Could not extract",
            "description": "Manual description needed"
        }

def calculate_match_score(lost_item, found_item):
    """Calculate similarity score between lost and found items"""
    score = 0
    
    # Compare item types (highest weight)
    if lost_item.get("item_type", "").lower() == found_item.get("item_type", "").lower():
        score += 40
    
    # Compare colors
    if lost_item.get("color", "").lower() in found_item.get("color", "").lower() or \
       found_item.get("color", "").lower() in lost_item.get("color", "").lower():
        score += 25
    
    # Compare brands
    if lost_item.get("brand", "").lower() == found_item.get("brand", "").lower() and lost_item.get("brand", "") != "Unknown":
        score += 20
    
    # Compare features (keyword matching)
    lost_features = set(lost_item.get("features", "").lower().split())
    found_features = set(found_item.get("features", "").lower().split())
    feature_overlap = len(lost_features & found_features)
    if feature_overlap > 0:
        score += min(15, feature_overlap * 5)
    
    return score

# Main app
def main():
    st.title("🔍 USFInd - Lost & Found App")
    st.markdown("*AI-Powered Item Matching System*")
    
    # Load data
    data = load_data()
    
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

            # Save to database
            data["found_items"].append(item_info)
            save_data(data)

            st.success("✅ Item added to the database!")

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
