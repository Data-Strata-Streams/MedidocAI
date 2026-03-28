# Purpose: Migration script to move data from medicine_database.json to PostgreSQL.
# This script defines the SQL schema and performs the data ingestion.

import json
import asyncio
from sqlalchemy import Column, Integer, String, Text, ForeignKey, create_engine
from sqlalchemy.orm import relationship, sessionmaker, declarative_base
from config.config import settings

Base = declarative_base()

# --- SQL Models ---
class Generic(Base):
    __tablename__ = 'generics'
    id = Column(Integer, primary_key=True)
    generic_name = Column(String, unique=True, nullable=False)
    total_local_brands = Column(Integer)
    brands = relationship("Brand", back_populates="generic")
    profile = relationship("ClinicalProfile", back_populates="generic", uselist=False)

class Brand(Base):
    __tablename__ = 'brands'
    id = Column(Integer, primary_key=True)
    generic_id = Column(Integer, ForeignKey('generics.id'))
    brand_name = Column(String)
    manufacturer = Column(String)
    price = Column(String)
    exact_formula = Column(String)
    generic = relationship("Generic", back_populates="brands")

class ClinicalProfile(Base):
    __tablename__ = 'clinical_profiles'
    id = Column(Integer, primary_key=True)
    generic_id = Column(Integer, ForeignKey('generics.id'))
    indications = Column(Text)
    mechanism = Column(Text)
    side_effects = Column(Text)
    warnings = Column(Text)
    contraindications = Column(Text)
    dosage = Column(Text)
    black_box = Column(Text)
    generic = relationship("Generic", back_populates="profile")

# --- Migration Logic ---
def migrate():
    # Connect to DB (removing 'asyncpg' for simple sync migration script)
    sync_url = settings.DATABASE_URL.replace("asyncpg", "psycopg2")
    engine = create_engine(sync_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Load JSON
    with open("data/processed/medicine_database.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    for entry in data:
        # Create/Get Generic
        generic = Generic(
            generic_name=entry.get("generic_name"),
            total_local_brands=entry.get("total_local_brands")
        )
        session.add(generic)
        session.flush() # Populate ID

        # Add Brands
        for b in entry.get("local_brands", []):
            brand = Brand(
                generic_id=generic.id,
                brand_name=b.get("brand_name"),
                manufacturer=b.get("manufacturer"),
                price=b.get("price"),
                exact_formula=b.get("exact_formula")
            )
            session.add(brand)

        # Add Clinical Profile
        cp = entry.get("clinical_profile", {})
        profile = ClinicalProfile(
            generic_id=generic.id,
            indications=cp.get("unified_indications"),
            mechanism=cp.get("unified_mechanism"),
            side_effects=cp.get("unified_side_effects"),
            warnings=cp.get("unified_warnings_and_precautions"),
            contraindications=cp.get("unified_contraindications"),
            dosage=cp.get("unified_dosage_guidelines"),
            black_box=cp.get("black_box_warning")
        )
        session.add(profile)
    
    session.commit()
    print("Migration successful!")

if __name__ == "__main__":
    migrate()