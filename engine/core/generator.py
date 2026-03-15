# Purpose: Generate AI responses, acting as a smart filter that triggers a MISSING_FLAG if a specific medicine is absent from the context.

import yaml
import json
from engine.core.ai_client import gemini_model

def load_personas(filepath: str = "config/personas.yml") -> dict:
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def generate_response(user_query: str, retrieved_data: list[dict], persona_type: str = "General Public") -> str:
    personas = load_personas()
    persona_config = personas.get(persona_type, personas.get("General Public", {}))
    description = persona_config.get("description", "")
    rules = persona_config.get("rules", "")

    context_str = json.dumps(retrieved_data, indent=2) if retrieved_data else "No relevant database records found."

    prompt = f"""
    You are MedidocAI, an expert medicine query assistant.
    
    USER QUERY: "{user_query}"
    
    AI FILTERING LOGIC (CRITICAL):
    1. Scan the database context for the medicine requested. Treat base generic names or different dosages of the same brand as EXACT matches (e.g., 'Risek 20mg' matches 'Risek 40mg' or 'Omeprazole').
    2. IF a match is found, use it to answer.
    3. IF the user asked for a specific medicine and it is COMPLETELY MISSING from the context, YOU MUST ABORT answering and reply EXACTLY with: MISSING_FLAG: [Name of Missing Medicine]. Do not include any other text.
    
    PERSONA INSTRUCTIONS:
    {description}
    {rules}
    
    STRICT LANGUAGE INSTRUCTION:
    1. If responding normally, match the user's language (English -> English, Other -> pure Urdu script).
    
    DATABASE CONTEXT (15 Records):
    {context_str}
    
    Based on the instructions, provide your response directly:
    """

    response = gemini_model.generate_content(prompt)
    return response.text.strip()
