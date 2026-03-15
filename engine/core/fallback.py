# Purpose: AI fallback logic to extract generic names for missing medicines and log permanently missing queries.

import os
from engine.core.ai_client import gemini_model

def get_generic_from_ai(medicine_name: str) -> str:
    """Asks Gemini to identify the generic formula of a given medicine brand."""
    prompt = f"What is the generic name (active ingredient) for the medicine '{medicine_name}'? Reply ONLY with the generic name. Do not include any other text. If you do not know, reply with 'UNKNOWN'."
    
    response = gemini_model.generate_content(prompt)
    return response.text.strip()

def log_missing_medicine(medicine_name: str):
    """Logs the permanently missing medicine to a backend text file."""
    # Ensure the directory exists
    os.makedirs("data/others", exist_ok=True)
    log_path = "data/others/missing_medicines.log"
    
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"{medicine_name}\n")
    print(f"Logged missing medicine: {medicine_name}")
