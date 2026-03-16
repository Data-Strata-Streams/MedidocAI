# Purpose: Generate AI responses using Gemini 2.5 Flash with a robust language classifier for English vs. Urdu/Mixed queries.

import yaml
import json
from engine.core.ai_client import gemini_model

def load_personas(filepath: str = "config/personas.yml") -> dict:
    """Loads persona definitions from a YAML configuration file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def generate_response(user_query: str, retrieved_data: list[dict], persona_type: str = "General Public") -> str:
    """
    Generates a persona-based response while strictly enforcing language rules for Pakistan (English vs Urdu).
    """
    personas = load_personas()
    persona_config = personas.get(persona_type, personas.get("General Public", {}))
    description = persona_config.get("description", "")
    rules = persona_config.get("rules", "")

    context_str = json.dumps(retrieved_data, indent=2) if retrieved_data else "No relevant database records found."

    prompt = f"""
    You are MedidocAI, an expert medicine query assistant in Pakistan.
    
    USER QUERY: "{user_query}"
    
    AI FILTERING & MATCHING LOGIC:
    1. Scan the database context for the generic or brand name. Match base generic names (e.g., 'Entamizole' for 'Entamizole DS').
    2. If a match is found, answer using that data.
    3. If the medicine is COMPLETELY MISSING, reply ONLY with: MISSING_FLAG: [Medicine Name].
    
    STRICT LANGUAGE CLASSIFICATION:
    - If the USER QUERY is 100% fluent English, you MUST respond in English.
    - If the USER QUERY contains ANY Urdu words, Roman Urdu, or is a mix of Urdu and English (e.g., 'bata do', 'ki details', 'kya hai'), you MUST respond STRICTLY in the pure Urdu script (اردو).
    - NEVER use Roman Urdu (English alphabets for Urdu) in your response.
    
    PERSONA INSTRUCTIONS:
    {description}
    {rules}
    
    DATABASE CONTEXT:
    {context_str}
    
    Based on the instructions, provide your response directly:
    """

    response = gemini_model.generate_content(prompt)
    return response.text.strip()
