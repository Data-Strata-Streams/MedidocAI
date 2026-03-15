# Purpose: Clean text, dynamically detect language (English vs Urdu), safely chunk text, and generate MP3 audio via Google Cloud TTS using official voice codes.

import re
import base64
import textwrap
from google.cloud import texttospeech
from config.config import settings

def clean_text_for_speech(text: str) -> str:
    """Removes markdown formatting so the TTS engine reads it naturally."""
    clean_text = re.sub(r'[*#_]', '', text)
    clean_text = clean_text.replace('\n', ' ')
    return clean_text

def is_urdu_text(text: str) -> bool:
    """Detects if the text contains Urdu/Arabic script characters."""
    return bool(re.search(r'[\u0600-\u06FF]', text))

def generate_audio_base64(text: str) -> str:
    """Generates MP3 audio, automatically switching between English and Urdu voices."""
    clean_text = clean_text_for_speech(text)
    client = texttospeech.TextToSpeechClient()
    
    text_chunks = textwrap.wrap(clean_text, width=4000, break_long_words=False)
    combined_audio = b""
    
    # FIX: Use the officially supported ur-IN (Urdu) language code and voice
    if is_urdu_text(clean_text):
        voice = texttospeech.VoiceSelectionParams(
            language_code="ur-IN",
            name="ur-IN-Standard-A"  # Official female Urdu voice
        )
    else:
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Journey-F"
        )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    for chunk in text_chunks:
        if not chunk.strip():
            continue
        synthesis_input = texttospeech.SynthesisInput(text=chunk)
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        combined_audio += response.audio_content

    return base64.b64encode(combined_audio).decode('utf-8')
