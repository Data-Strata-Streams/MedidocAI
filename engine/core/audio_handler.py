# Purpose: Advanced Audio Handler using Gemini 2.5 Flash with strict transcription logic to distinguish between fluent English and Urdu/Mixed speech.

import base64
from vertexai.generative_models import Part, GenerativeModel
from engine.core.ai_client import gemini_model
from config.config import settings

def transcribe_audio(base64_audio: str, mime_type: str = "audio/ogg") -> str:
    """
    Transcribes medical queries from audio. 
    Strict Rule: Fluent English -> English Text. Anything else (Urdu/Mixed) -> Urdu Script.
    """
    audio_bytes = base64.b64decode(base64_audio)
    audio_part = Part.from_data(data=audio_bytes, mime_type=mime_type)
    
    # We redefine the model call here to include a very strict System Instruction for transcription
    system_instruction = """
    You are an expert Pakistani Medical Transcriptionist. 
    Your goal is to transcribe medicine-related audio queries with 100% accuracy.
    
    TRANSCRIPTION RULES:
    1. If the speaker is using 100% fluent English, transcribe in English.
    2. If the speaker uses ANY Urdu words, Roman Urdu, or a mix of Urdu/English (e.g., 'Panadol ki price kya hai?'), you MUST transcribe the entire query into the pure Urdu Script (اردو).
    3. Be highly sensitive to Pakistani medicine names (e.g., Entamizole, Risek, Panadol, Arinac, Augmentin).
    4. NEVER output Roman Urdu (Urdu words in English letters).
    5. Output ONLY the transcribed text. No conversational fillers.
    """
    
    # Re-initializing model specifically for this task to ensure instructions are followed
    model = GenerativeModel("gemini-1.5-flash", system_instruction=system_instruction)
    
    response = model.generate_content([audio_part])
    
    return response.text.strip()
