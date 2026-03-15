# Purpose: Process incoming images using Gemini 2.5 Flash, extracting medicine names as a structured JSON list for multi-query retrieval.

import base64
import json
from vertexai.generative_models import Part
from engine.core.ai_client import gemini_model

def analyze_image(base64_image: str, mime_type: str = "image/jpeg", text_query: str = "") -> str:
    """
    Takes a base64 encoded image, feeds it to Gemini 2.5 Flash, 
    and extracts medicine names as a strict JSON list string (e.g., '["Med A", "Med B"]').
    """
    image_bytes = base64.b64decode(base64_image)
    image_part = Part.from_data(data=image_bytes, mime_type=mime_type)
    
    if not text_query or text_query.strip() == "":
        text_query = "Identify the medicines in this image."
    
    prompt = f"""
    You are an expert pharmacist. Analyze the attached image (prescription or medicine box).
    
    USER QUERY: "{text_query}"
    
    RULES:
    1. Identify every distinct medicine name visible.
    2. Output the result STRICTLY as a JSON list of strings.
    3. Example Output: ["Bisoprolol 5mg", "Panadol", "Amoxicillin"]
    4. Do not output any other text, markdown, or explanation. JUST the JSON list.
    5. If only one medicine is found, output a list with one item: ["Medicine Name"].
    """
    
    response = gemini_model.generate_content([image_part, prompt])
    
    # Clean response to ensure it's valid JSON (remove markdown code blocks if Gemini adds them)
    cleaned_text = response.text.strip().replace("```json", "").replace("```", "")
    return cleaned_text
