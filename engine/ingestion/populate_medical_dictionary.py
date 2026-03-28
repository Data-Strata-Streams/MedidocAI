# Purpose: AI-driven dictionary ingestion with strict filtering and rate-limit handling.
import json
import time
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config.config import settings
from engine.core.models import ClinicalProfile, MedicalTerm
from engine.core.ai_client import gemini_model

# --- DATABASE SETUP ---
sync_url = settings.DATABASE_URL.replace("asyncpg", "psycopg2")
engine = create_engine(sync_url)
SessionLocal = sessionmaker(bind=engine)

def get_simple_definitions(text_batch):
    """Asks Gemini to extract only complex terms with rate-limit protection."""
    prompt = f"""
    Analyze the medical text below. Your goal is to identify terms that a 5th-grade student would struggle to understand.
    
    INCLUSION RULES (Priority):
    1. INCLUDE: Medical conditions (e.g., arrhythmia, afibrinogenemia, convulsions, hypersensitivity).
    2. INCLUDE: Complex clinical/biological processes (e.g., uterine hypertonicity, anaphylactic reaction).
    3. INCLUDE: Pharmacological terms (e.g., infusion, adverse reactions, parenteral).
    
    EXCLUSION RULES (Strict):
    1. ONLY EXCLUDE extremely generic, non-medical words or trivial symptoms (e.g., pain, headache, nausea, vomiting, rash, diarrhea, cough).
    2. DO NOT EXCLUDE complex medical terminology that represents a disease, a syndrome, or a physiological state.

    CRITICAL: You are an expert medical educator. Your definitions must be short, factual, and 5th-grade level.
    
    TEXT:
    {text_batch}

    RESPONSE FORMAT (Strict JSON List):
    [
      {{"term": "arrhythmia", "definition": "A heartbeat that is too fast, too slow, or not steady."}},
      {{"term": "anaphylactic", "definition": "A very serious, sudden allergic reaction."}}
    ]
    """
    try:
        response = gemini_model.generate_content(prompt)
        raw_json = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(raw_json)
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "Resource exhausted" in error_msg:
            print("Rate limit hit (429). Sleeping for 90 seconds...", flush=True)
            time.sleep(90) 
        else:
            print(f"AI Error: {error_msg}", flush=True)
        return []

def run_ingestion():
    session = SessionLocal()
    profiles = session.query(ClinicalProfile).all()
    existing_terms = {t.term.lower() for t in session.query(MedicalTerm.term).all()}
    
    print(f"Total profiles to process: {len(profiles)}", flush=True)
    
    for i, p in enumerate(profiles):
        combined_text = f"{p.indications} {p.mechanism} {p.side_effects}"
        new_entries = get_simple_definitions(combined_text)
        
        # If we got a 429 or error, new_entries is [], loop continues safely
        for entry in new_entries:
            term_name = entry['term'].lower().strip()
            # Basic validation: ensure it's not a common symptom word that slipped through
            if term_name not in existing_terms:
                new_term = MedicalTerm(term=term_name, definition=entry['definition'])
                session.add(new_term)
                existing_terms.add(term_name)
                print(f"Added: {term_name}", flush=True)
        
        session.commit()
        if i % 10 == 0:
            print(f"Processed {i}/{len(profiles)} profiles...", flush=True)
        time.sleep(2) # Extra buffer for rate limits

    session.close()

if __name__ == "__main__":
    run_ingestion()