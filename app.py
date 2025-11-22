import streamlit as st
import json
import os
from datetime import datetime
from pathlib import Path
import base64
from openai import OpenAI
from dotenv import load_dotenv
from PIL import Image

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Configuration
DATA_FILE = "data.json"
IMAGES_DIR = "images"

# Create images directory if it doesn't exist
Path(IMAGES_DIR).mkdir(exist_ok=True)

# Page configuration
st.set_page_config(
    page_title="USFInd - Lost & Found",
    page_icon="🔍",
    layout="wide"
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

def encode_image_to_base64(image_path):
    """Encode image to base64 for OpenAI API"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def extract_item_info(image_path):
    """Use OpenAI Vision API to extract item information"""
    try:
        base64_image = encode_image_to_base64(image_path)
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Analyze this image of a lost/found item and extract the following information in a structured format:
- Item Type: (e.g., phone, wallet, keys, bag, etc.)
- Color: (primary color)
- Brand/Model: (if visible)
- Distinctive Features: (unique characteristics, damages, stickers, etc.)
- Description: (brief overall description)

Format your response as JSON with these exact keys: item_type, color, brand, features, description"""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=300
        )
        
        # Parse the response
        content = response.choices[0].message.content
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
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["📤 Report Found Item", "🔎 Report Lost Item", "📋 View All Items"])
    
    if page == "📤 Report Found Item":
        page_found_item(data)
    elif page == "🔎 Report Lost Item":
        page_lost_item(data)
    else:
        page_view_all(data)

def page_found_item(data):
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
                
                # Add metadata
                item_info["image_path"] = image_path
                item_info["timestamp"] = datetime.now().isoformat()
                item_info["type"] = "found"
                
                # Save to database
                data["found_items"].append(item_info)
                save_data(data)
                
                st.success("✅ Item successfully added to the database!")
                
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

def page_lost_item(data):
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
        item_info["type"] = "lost"
        data["lost_items"].append(item_info)
        save_data(data)
        
        st.subheader("🎯 Potential Matches:")
        
        if not data["found_items"]:
            st.info("No found items in the database yet.")
        else:
            matches = []
            for found_item in data["found_items"]:
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
                            if os.path.exists(found_item["image_path"]):
                                st.image(found_item["image_path"], width=200)
                        with col2:
                            st.write(f"**Item Type:** {found_item['item_type']}")
                            st.write(f"**Color:** {found_item['color']}")
                            st.write(f"**Brand:** {found_item['brand']}")
                            st.write(f"**Features:** {found_item['features']}")
                            st.write(f"**Description:** {found_item['description']}")
                            st.write(f"**Found on:** {found_item['timestamp'][:10]}")

def page_view_all(data):
    """Page to view all found items"""
    st.header("📋 All Found Items")
    
    if not data["found_items"]:
        st.info("No items found yet. Be the first to report a found item!")
    else:
        st.write(f"Total found items: **{len(data['found_items'])}**")
        
        # Display items in grid
        cols = st.columns(3)
        for idx, item in enumerate(data["found_items"]):
            with cols[idx % 3]:
                with st.container():
                    if os.path.exists(item["image_path"]):
                        st.image(item["image_path"], use_container_width=True)
                    st.write(f"**{item['item_type']}** ({item['color']})")
                    st.write(f"Brand: {item['brand']}")
                    st.write(f"Found: {item['timestamp'][:10]}")
                    st.divider()

if __name__ == "__main__":
    main()
