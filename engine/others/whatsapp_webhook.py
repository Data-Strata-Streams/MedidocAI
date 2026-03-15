# Purpose: Handle incoming webhooks, route to AI, intercept missing medicines, trigger generic-fallback searches, and log missing data.

import json
from fastapi import APIRouter, Request, BackgroundTasks
import logging
from engine.core.retrieval import search_medicine
from engine.core.generator import generate_response
from engine.others.whatsapp_client import send_whatsapp_text, send_whatsapp_audio, get_media_base64
from engine.core.audio_handler import transcribe_audio
from engine.core.vision_handler import analyze_image
from engine.core.tts_handler import generate_audio_base64
from engine.core.fallback import get_generic_from_ai, log_missing_medicine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

whatsapp_router = APIRouter()

def process_and_reply(remote_jid: str, user_query: str, reply_type: str = "text"):
    try:
        logger.info(f"Processing query for {remote_jid} | Type: {reply_type} | Query: {user_query}")
        
        retrieved_context = []
        final_user_query = user_query
        
        # 1. Initial Retrieval
        try:
            parsed_query = json.loads(user_query)
            if isinstance(parsed_query, list):
                for med in parsed_query:
                    retrieved_context.extend(search_medicine(med, limit=5))
                final_user_query = "Provide details for: " + ", ".join(parsed_query)
            else:
                retrieved_context = search_medicine(user_query, limit=15)
        except json.JSONDecodeError:
            retrieved_context = search_medicine(user_query, limit=15)

        unique_context = {item.get("generic_name", str(i)): item for i, item in enumerate(retrieved_context)}.values()
        retrieved_context = list(unique_context)
        
        # 2. First AI Generation
        ai_response = generate_response(final_user_query, retrieved_context, "General Public")
        
        # 3. Fallback Logic Interception
        if "MISSING_FLAG:" in ai_response:
            missing_med = ai_response.split("MISSING_FLAG:")[1].strip()
            logger.info(f"Fallback triggered for: {missing_med}")
            
            # Step A: Ask Gemini for the generic name
            generic_name = get_generic_from_ai(missing_med)
            
            if generic_name and generic_name != "UNKNOWN":
                logger.info(f"Fallback Generic found: {generic_name}. Re-searching...")
                fallback_context = search_medicine(generic_name, limit=15)
                
                # Step B: Try generating the answer again with the new generic context
                ai_response = generate_response(final_user_query, fallback_context, "General Public")
            
            # Step C: If it's STILL missing after fallback, log it and apologize
            if "MISSING_FLAG:" in ai_response or not generic_name or generic_name == "UNKNOWN":
                log_missing_medicine(missing_med)
                ai_response = f"Information for '{missing_med}' is not yet found in our database. However, it has been noted and will be added soon."
        
        # 4. Send Reply
        if reply_type == "audio":
            logger.info("Converting AI response to audio...")
            audio_b64 = generate_audio_base64(ai_response)
            send_whatsapp_audio(remote_jid, audio_b64)
        else:
            send_whatsapp_text(remote_jid, ai_response)
        
    except Exception as e:
        logger.error(f"Error in process_and_reply: {str(e)}")
        send_whatsapp_text(remote_jid, "Sorry, I am facing a temporary technical issue. Please try again later.")

@whatsapp_router.post("/webhook/evolution")
async def evolution_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        payload = await request.json()
        if payload.get("event") == "messages.upsert":
            data = payload.get("data", {})
            message_data = data.get("message", {})
            key = data.get("key", {})
            remote_jid = key.get("remoteJid")
            from_me = key.get("fromMe", False)
            
            if from_me or not remote_jid:
                return {"status": "ignored"}

            text = message_data.get("conversation") or message_data.get("extendedTextMessage", {}).get("text")
            audio_message = message_data.get("audioMessage")
            image_message = message_data.get("imageMessage")

            if image_message:
                base64_image = get_media_base64(key)
                if base64_image:
                    mime_type = image_message.get("mimetype", "image/jpeg").split(";")[0]
                    caption = image_message.get("caption", "")
                    extracted_query = analyze_image(base64_image, mime_type, caption)
                    background_tasks.add_task(process_and_reply, remote_jid, extracted_query, "text")
                    return {"status": "success"}
            elif audio_message:
                base64_audio = get_media_base64(key)
                if base64_audio:
                    mime_type = audio_message.get("mimetype", "audio/ogg").split(";")[0]
                    transcribed_text = transcribe_audio(base64_audio, mime_type)
                    background_tasks.add_task(process_and_reply, remote_jid, transcribed_text, "audio")
                    return {"status": "success"}
            elif text:
                background_tasks.add_task(process_and_reply, remote_jid, text, "text")
                return {"status": "success"}
        return {"status": "ignored"}
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        return {"status": "error"}
