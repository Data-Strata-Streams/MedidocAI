# Purpose: Process incoming audio using Gemini 2.5 Flash, transcribing strictly to English or Urdu (اردو).

import base64
from vertexai.generative_models import Part
from engine.core.ai_client import gemini_model

def transcribe_audio(base64_audio: str, mime_type: str = "audio/ogg") -> str:
    audio_bytes = base64.b64decode(base64_audio)
    audio_part = Part.from_data(data=audio_bytes, mime_type=mime_type)
    
    prompt = """
    You are an expert medical transcriptionist. Listen to the attached audio.
    
    STRICT LANGUAGE RULES:
    1. If the user is speaking English, transcribe their exact medical question in English.
    2. If the user is speaking ANY other language (e.g., Urdu, Hindi, Punjabi, etc.), translate and transcribe their intent STRICTLY into the pure Urdu script (اردو).
    3. ABSOLUTELY DO NOT output Roman Urdu, Arabic, or Persian scripts.
    4. Output ONLY the query itself. No introductory words, no conversational filler.
    """
    
    response = gemini_model.generate_content([audio_part, prompt])
    return response.text.strip()
