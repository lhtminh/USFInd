"""AI service for extracting item information from images"""
import os
import json
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Google Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def extract_item_info(image_path):
    """Use Google Gemini Vision API to extract item information"""
    try:
        # Check if API key is loaded
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key == "your-api-key-here":
            raise ValueError("Gemini API key not found or not set properly in .env file")
        
        # Load image
        img = Image.open(image_path)
        
        # Initialize Gemini model (using available model with vision support)
        model = genai.GenerativeModel('gemini-2.5-pro')
        
        # Create prompt
        prompt = """Analyze this image of a lost/found item and extract the following information in a structured format:
- Item Type: (e.g., phone, wallet, keys, bag, etc.)
- Color: (primary color)
- Brand/Model: (if visible)
- Distinctive Features: (unique characteristics, damages, stickers, etc.)
- Description: (brief overall description)

Format your response as JSON with these exact keys: item_type, color, brand, features, description"""
        
        # Generate content
        response = model.generate_content([prompt, img])
        
        # Parse the response
        content = response.text
        # Try to extract JSON from response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        return json.loads(content)
    except Exception as e:
        print(f"DEBUG - Full error: {str(e)}")
        print(f"DEBUG - Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return {
            "item_type": "Unknown",
            "color": "Unknown",
            "brand": "Unknown",
            "features": f"Error: {str(e)}",
            "description": "Extraction failed"
        }
