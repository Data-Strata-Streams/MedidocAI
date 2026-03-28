# Purpose: Initialize the medical_terms table in the database based on the SQLAlchemy model.
from sqlalchemy import create_engine
from config.config import settings
from engine.core.models import Base

def init_db():
    # Convert async URL to sync for the creation script
    sync_url = settings.DATABASE_URL.replace("asyncpg", "psycopg2")
    engine = create_engine(sync_url)
    
    print("Checking for missing tables...")
    # This command checks the DB and creates any tables defined in models.py 
    # that don't exist yet (it won't delete existing data).
    Base.metadata.create_all(engine)
    print("Success: medical_terms table is ready.")

if __name__ == "__main__":
    init_db()