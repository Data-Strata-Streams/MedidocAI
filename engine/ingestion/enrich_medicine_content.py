import json
import time
import os
import sys

# Add project root to path for imports
sys.path.append("/home/ubuntu/Medidoc")

from engine.core.ai_client import gemini_model

# --- CONFIGURATION ---
AUDIT_RESULTS_PATH = "/tmp/medicine_audit_results.json"
STAGING_DB_PATH = "/home/ubuntu/Medidoc/data_staging/processed/medicine_database.json"
OUTPUT_DB_PATH = "/home/ubuntu/Medidoc/data_staging/processed/medicine_database.json" # Overwrite staging
BATCH_SIZE = 5 # Save every 5 generics
SLEEP_TIME = 2 # Buffer between AI calls

def get_enriched_content(generic_name, brand_example, short_sections):
    """Asks Gemini to generate high-quality clinical content for deficient sections."""
    sections_str = ", ".join(short_sections)
    prompt = f"""
    Act as an expert medical writer specializing in YMYL (Your Money Your Life) healthcare content.
    Provide detailed, accurate, and professional clinical information for the medicine: {generic_name} (Example brand: {brand_example}).

    REQUIRED SECTIONS: {sections_str}

    GUIDELINES:
    1. Each section MUST be at least 300 characters long to ensure comprehensive coverage.
    2. Maintain a professional, clinical tone suitable for a healthcare portal.
    3. Only expand based on the known pharmacological class of this drug. Do not invent uses that are not in the primary indication data.
    4. For 'Black Box Warning', provide the specific FDA-style boxed warning if applicable, or a detailed safety warning if no formal boxed warning exists but high-risk factors are present. If it truly doesn't have one, provide a 'Serious Warnings' section instead.
    5. Ensure content is accurate and follows the latest medical guidelines.
    6. Provide the response strictly in the following JSON format:
    {{
        "Indications": "...",
        "Dosage": "...",
        "Side Effects": "...",
        "Warnings": "...",
        "Mechanism of Action": "...",
        "Contraindications": "...",
        "Black Box Warning": "..."
    }}
    (Only include the sections requested above).
    """

    try:
        response = gemini_model.generate_content(prompt)
        text = response.text.strip()
        # Clean potential markdown formatting
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        
        data = json.loads(text.strip())
        return data
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "Resource exhausted" in error_msg:
            print(f"Rate limit hit for {generic_name}. Sleeping for 90 seconds...", flush=True)
            time.sleep(90)
        else:
            print(f"AI Enrichment Error for {generic_name}: {error_msg}", flush=True)
        return None

def run_enrichment():
    # 1. Load Audit Results
    if not os.path.exists(AUDIT_RESULTS_PATH):
        print(f"Audit results not found at {AUDIT_RESULTS_PATH}. Please run the audit first.", flush=True)
        return

    with open(AUDIT_RESULTS_PATH, "r") as f:
        audit_results = json.load(f)

    # 2. Group by Generic to minimize calls
    generic_issues = {}
    for entry in audit_results:
        gen = entry["generic"]
        brand = entry["brand"]
        # Extract section names from issues like "Indications (71 chars)"
        issues = [iss.split(" (")[0] for iss in entry["issues"] if " (" in iss]
        
        if gen not in generic_issues:
            generic_issues[gen] = {"brand_example": brand, "sections": set()}
        
        # If 'No clinical profile found' is also there, check all sections
        if "No clinical profile found" in entry["issues"]:
            generic_issues[gen]["sections"].update(["Indications", "Dosage", "Side Effects", "Warnings", "Mechanism of Action", "Contraindications", "Black Box Warning"])
        else:
            generic_issues[gen]["sections"].update(issues)

    print(f"Total generics to enrich: {len(generic_issues)}", flush=True)

    # 3. Load Staging DB
    if not os.path.exists(STAGING_DB_PATH):
        print(f"Staging DB not found at {STAGING_DB_PATH}.", flush=True)
        return

    with open(STAGING_DB_PATH, "r") as f:
        database = json.load(f)

    # Map generic names to their objects in the database
    db_map = {entry["generic_name"].lower(): entry for entry in database}

    # 4. Enrich Content
    count = 0
    for gen_name, data in generic_issues.items():
        gen_name_lower = gen_name.lower()
        if gen_name_lower not in db_map:
            # Maybe the generic name in audit (DB) is slightly different than JSON
            print(f"Warning: Generic '{gen_name}' not found in database. Skipping.", flush=True)
            continue

        entry = db_map[gen_name_lower]
        short_sections = sorted(list(data["sections"]))
        
        if not short_sections:
            continue

        print(f"Enriching '{gen_name}' (Sections: {', '.join(short_sections)})...", flush=True)
        enriched = get_enriched_content(gen_name, data["brand_example"], short_sections)

        if enriched:
            # Map labels to DB keys
            key_map = {
                "Indications": "unified_indications",
                "Dosage": "unified_dosage_guidelines",
                "Side Effects": "unified_side_effects",
                "Warnings": "unified_warnings_and_precautions",
                "Mechanism of Action": "unified_mechanism",
                "Contraindications": "unified_contraindications",
                "Black Box Warning": "black_box_warning"
            }
            
            if "clinical_profile" not in entry or not isinstance(entry["clinical_profile"], dict):
                entry["clinical_profile"] = {
                    "unified_indications": "",
                    "unified_mechanism": "",
                    "unified_side_effects": "",
                    "unified_warnings_and_precautions": "",
                    "unified_contraindications": "",
                    "unified_dosage_guidelines": "",
                    "black_box_warning": ""
                }

            profile = entry["clinical_profile"]
            for label, new_text in enriched.items():
                db_key = key_map.get(label)
                # Only update if new content is decent and not just a placeholder
                if db_key and new_text and len(str(new_text)) > 150 and str(new_text).strip().lower() not in ["none", "n/a"]:
                    profile[db_key] = new_text
                    print(f"  Enriched: {label} ({len(new_text)} chars)", flush=True)

            count += 1
            # Periodic Save
            if count % BATCH_SIZE == 0:
                with open(OUTPUT_DB_PATH, "w") as f:
                    json.dump(database, f, indent=2)
                print(f"Saved checkpoint ({count} generics processed).", flush=True)
            
            time.sleep(SLEEP_TIME)

    # Final Save
    with open(OUTPUT_DB_PATH, "w") as f:
        json.dump(database, f, indent=2)
    print(f"Enrichment complete! Processed {count} generics.", flush=True)

if __name__ == "__main__":
    run_enrichment()
