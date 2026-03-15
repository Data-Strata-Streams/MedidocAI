# Purpose: Handle outgoing communications (text/audio) and fetch media from WhatsApp via the Evolution API.

import requests
import logging
from config.config import settings

logger = logging.getLogger(__name__)

def send_whatsapp_text(remote_jid: str, text: str) -> bool:
    """Sends a text message to a specific WhatsApp number."""
    if not settings.EVOLUTION_API_URL or not settings.EVOLUTION_INSTANCE_NAME:
        logger.error("Evolution API configuration is missing.")
        return False

    url = f"{settings.EVOLUTION_API_URL}/message/sendText/{settings.EVOLUTION_INSTANCE_NAME}"
    headers = {"apikey": settings.EVOLUTION_API_KEY, "Content-Type": "application/json"}
    payload = {"number": remote_jid, "text": text}
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send text: {str(e)}")
        return False

def send_whatsapp_audio(remote_jid: str, base64_audio: str) -> bool:
    """Sends a raw base64 encoded audio as a Voice Note (PTT) to WhatsApp."""
    url = f"{settings.EVOLUTION_API_URL}/message/sendWhatsAppAudio/{settings.EVOLUTION_INSTANCE_NAME}"
    headers = {"apikey": settings.EVOLUTION_API_KEY, "Content-Type": "application/json"}
    
    # FIX: Send the pure base64 string WITHOUT the "data:audio..." prefix!
    payload = {
        "number": remote_jid,
        "audio": base64_audio,
        "delay": 1200
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        logger.info(f"Successfully sent Voice Note to {remote_jid}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send Voice Note: {str(e)}")
        if e.response is not None:
            logger.error(f"Evolution API Response: {e.response.text}")
        return False

def get_media_base64(message_key: dict) -> str:
    """Fetches media attached to a message from Evolution API."""
    url = f"{settings.EVOLUTION_API_URL}/chat/getBase64FromMediaMessage/{settings.EVOLUTION_INSTANCE_NAME}"
    headers = {"apikey": settings.EVOLUTION_API_KEY, "Content-Type": "application/json"}
    payload = {"message": {"key": message_key}}
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json().get("base64", "")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch media base64: {str(e)}")
        return ""
