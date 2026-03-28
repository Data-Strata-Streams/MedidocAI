# Purpose: Handle incoming webhooks, route to AI, intercept missing medicines, 
# trigger generic-fallback searches, log missing data, and manage user onboarding state.

import json
import logging
from fastapi import APIRouter, Request, BackgroundTasks
from engine.core.retrieval import search_medicine
from engine.core.generator import generate_response
from engine.others.whatsapp_client import send_whatsapp_text, send_whatsapp_audio, get_media_base64, send_whatsapp_list, send_whatsapp_poll
from engine.core.audio_handler import transcribe_audio
from engine.core.vision_handler import analyze_image
from engine.core.tts_handler import generate_audio_base64
from engine.core.fallback import get_generic_from_ai, log_missing_medicine
from engine.core.user_state import get_or_create_user, update_user_state

# DEFINITIONS
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
whatsapp_router = APIRouter()

def process_and_reply(remote_jid: str, user_query: str, reply_type: str = "text", persona: str = "General Public"):
    try:
        logger.info(f"Processing query for {remote_jid} | Type: {reply_type} | Persona: {persona} | Query: {user_query}")
        
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
        ai_response = generate_response(final_user_query, retrieved_context, persona)
        
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
                ai_response = generate_response(final_user_query, fallback_context, persona)
            
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
        if payload.get("event") != "messages.upsert":
            return {"status": "ignored"}

        data = payload.get("data", {})
        message_data = data.get("message", {})
        key = data.get("key", {})
        remote_jid = key.get("remoteJid")
        
        if not remote_jid or key.get("fromMe", False):
            return {"status": "ignored"}

        # DEBUG: Log full payload to see the exact structure received
        # logger.info(f"FULL WEBHOOK PAYLOAD: {json.dumps(payload, indent=2)}")

        phone_number = remote_jid.split("@")[0]
        text = message_data.get("conversation") or message_data.get("extendedTextMessage", {}).get("text") or message_data.get("listResponseMessage", {}).get("title")
        audio_message = message_data.get("audioMessage")
        image_message = message_data.get("imageMessage")
        poll_update = message_data.get("pollUpdateMessage")

        # 1. Poll Response Extraction (Evolution API v2)
        if poll_update and not text:
            # Fixed Path: vote -> selectedOptions (as seen in RAW POLL UPDATE)
            selected_options = poll_update.get("vote", {}).get("selectedOptions", [])
            if selected_options:
                text = selected_options[0]
                logger.info(f"POLL RESPONSE EXTRACTED: {text}")

        # 2. STRICT CONTENT GUARD
        has_text = bool(text and str(text).strip())
        has_audio = bool(audio_message)
        has_image = bool(image_message)
        
        user_data = get_or_create_user(phone_number)
        persona = user_data.get("persona", "General Public")

        # Log decision factors
        logger.info(f"WEBHOOK DEBUG | phone={phone_number} | text='{text}' | step='{user_data.get('current_step')}' | audio={has_audio} | image={has_image} | poll={bool(poll_update)}")

        if not any([has_text, has_audio, has_image]):
            logger.info("Ignoring empty or non-human message (system event / poll creation).")
            return {"status": "ignored_no_content"}

        # --- SANDBOX FILTER ---
        if phone_number == "923338888761":
            
            # Reset/Settings Trigger
            if text and text.strip().lower() in ["menu", "reset", "settings", "hi", "hello"]:
                update_user_state(phone_number, step='asking_persona')
                send_whatsapp_text(remote_jid, "⚙️ Resetting... Menu triggered.")
                user_data["current_step"] = "asking_persona"  # Update local var to trigger the next block

            # Onboarding Logic
            if user_data["current_step"] in ['new', 'asking_persona']:
                user_text = str(text).strip().lower() if text else ""
                
                valid_selections = {
                    "1": "General Public",
                    "2": "Student",
                    "3": "HCP",
                    "general public": "General Public",
                    "student": "Student",
                    "hcp": "HCP"
                }

                if user_text in valid_selections:
                    chosen_persona = valid_selections[user_text]
                    update_user_state(phone_number, step='active', persona=chosen_persona)
                    send_whatsapp_text(remote_jid, f"✅ Persona set to *{chosen_persona}*. You can now ask medical questions!")
                    return {"status": "success"}

                # Use Native Interactive Poll for Persona Selection (Bypasses WhatsApp Button Block)
                welcome_msg = "👋 Welcome to MedidocAI!\n\nPlease select your persona to get started:"
                options = [
                    "General Public",
                    "Student",
                    "HCP"
                ]
                
                send_whatsapp_poll(remote_jid, welcome_msg, options)
                return {"status": "success"}

        # --- NORMAL AI PROCESSING ---
        if image_message:
            base64_image = get_media_base64(key)
            if base64_image:
                mime_type = image_message.get("mimetype", "image/jpeg").split(";")[0]
                caption = image_message.get("caption", "")
                extracted_query = analyze_image(base64_image, mime_type, caption)
                background_tasks.add_task(process_and_reply, remote_jid, extracted_query, "text", persona)
        elif audio_message:
            base64_audio = get_media_base64(key)
            if base64_audio:
                mime_type = audio_message.get("mimetype", "audio/ogg").split(";")[0]
                transcribed_text = transcribe_audio(base64_audio, mime_type)
                background_tasks.add_task(process_and_reply, remote_jid, transcribed_text, "audio", persona)
        elif text:
            background_tasks.add_task(process_and_reply, remote_jid, text, "text", persona)
            
        return {"status": "success"}

    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        return {"status": "error"}