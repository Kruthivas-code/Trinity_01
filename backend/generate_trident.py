#!/usr/bin/env python3
"""Generate a minimalist trident logo using Gemini Nano Banana."""

import google.genai as genai
from google.genai import types
import os
import base64

# Use Emergent LLM key
API_KEY = "sk-emergent-628765d6d28Ee2e3fB"

client = genai.Client(api_key=API_KEY)

prompt = """Create a minimalist, sleek trident icon logo design similar to Maserati's trident.

Requirements:
- Pure icon only, no text, no background
- Three elegant prongs pointing upward
- Clean, modern, geometric lines
- Suitable for a premium software brand called "Trinity"
- The trident should look powerful yet refined
- Use a simple monochrome design (white/light gray on transparent)
- SVG-friendly clean shapes
- Professional, not ornate or decorative
- Think Maserati meets modern tech branding

Style: Minimalist tech logo, vector-style, clean edges"""

print("Generating trident icon with Nano Banana...")

try:
    response = client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_modalities=['Text', 'Image']
        )
    )
    
    for part in response.parts:
        if part.inline_data is not None:
            image = part.as_image()
            output_path = "/app/frontend/public/trident-logo.png"
            image.save(output_path)
            print(f"✅ Trident icon saved to: {output_path}")
            
            # Also save a smaller version for favicon
            small_image = image.resize((32, 32))
            small_image.save("/app/frontend/public/trident-favicon.png")
            print("✅ Favicon version saved")
            break
    else:
        print("❌ No image generated in response")
        
except Exception as e:
    print(f"❌ Error generating image: {e}")
    # Create a fallback SVG trident
    print("Creating fallback SVG trident...")
