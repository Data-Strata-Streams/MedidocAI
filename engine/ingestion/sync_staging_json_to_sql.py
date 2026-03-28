# Purpose: Sync AI-enriched medicine data from staging JSON to PostgreSQL staging DB.
import json
import os
import sys
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

# Add project root to path for imports
sys.path.append("/app") # Inside container path

from config.config import settings
from engine.core.models import Base, Generic, Brand, ClinicalProfile

def sync_data():
    # Connect using sync driver
    sync_url = settings.DATABASE_URL.replace("asyncpg", "psycopg2")
    engine = create_engine(sync_url)
    
    # Ensure tables exist (they should, but safe measure)
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()

    # Path inside container
    json_path = "/app/data_staging/processed/medicine_database.json"
    
    if not os.path.exists(json_path):
        print(f"Error: JSON file not found at {json_path}")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Starting sync of {len(data)} generics...")

    for i, entry in enumerate(data):
        gen_name = entry.get("generic_name")
        if not gen_name:
            continue

        # 1. Find or Create Generic
        generic = session.query(Generic).filter(Generic.generic_name.ilike(gen_name)).first()
        if not generic:
            generic = Generic(generic_name=gen_name)
            session.add(generic)
            session.flush()
            print(f"Created new generic: {gen_name}")
        
        generic.total_local_brands = entry.get("total_local_brands", 0)

        # 2. Sync Clinical Profile
        cp_data = entry.get("clinical_profile", {})
        if not generic.profile:
            generic.profile = ClinicalProfile(generic_id=generic.id)
        
        profile = generic.profile
        profile.indications = cp_data.get("unified_indications")
        profile.mechanism = cp_data.get("unified_mechanism")
        profile.side_effects = cp_data.get("unified_side_effects")
        profile.warnings = cp_data.get("unified_warnings_and_precautions")
        profile.contraindications = cp_data.get("unified_contraindications")
        profile.dosage = cp_data.get("unified_dosage_guidelines")
        profile.black_box = cp_data.get("black_box_warning")

        # 3. Sync Brands
        existing_brands = {b.brand_name.lower(): b for b in generic.brands}
        for b_data in entry.get("local_brands", []):
            b_name = b_data.get("brand_name")
            if not b_name:
                continue
            
            b_name_lower = b_name.lower()
            if b_name_lower not in existing_brands:
                new_brand = Brand(
                    generic_id=generic.id,
                    brand_name=b_name,
                    manufacturer=b_data.get("manufacturer"),
                    price=b_data.get("price"),
                    exact_formula=b_data.get("exact_formula")
                )
                session.add(new_brand)
            else:
                # Update existing brand info if needed
                brand = existing_brands[b_name_lower]
                brand.manufacturer = b_data.get("manufacturer")
                brand.price = b_data.get("price")
                brand.exact_formula = b_data.get("exact_formula")

        if (i+1) % 50 == 0:
            session.commit()
            print(f"Progress: {i+1}/{len(data)} generics synced.")

    session.commit()
    print("Sync completed successfully!")

if __name__ == "__main__":
    sync_data()
