"""AI service for extracting item information from images"""
import os
import json
import base64
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
        return {
            "item_type": "Unknown",
            "color": "Unknown",
            "brand": "Unknown",
            "features": f"Error: {str(e)}",
            "description": "Extraction failed"
        }
