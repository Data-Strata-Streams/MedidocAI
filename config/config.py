# Purpose: Centralize environment variable loading for the MedidocAI project.

import os
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

class Config:
    GCP_PROJECT_ID = os.getenv("medidocai")
    GCP_LOCATION = os.getenv("GCP_LOCATION", "us-central1")
    QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
    EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL")
    EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY")
    EVOLUTION_INSTANCE_NAME = os.getenv("EVOLUTION_INSTANCE_NAME")

    # Database Settings (PostgreSQL)
    DB_USER = os.getenv("POSTGRES_USER", "medidoc_admin")
    DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "secure_medidoc_pass_123")
    DB_NAME = os.getenv("POSTGRES_DB", "medidoc_db")
    DB_HOST = os.getenv("POSTGRES_HOST", "db")  # 'db' matches the docker-compose service name
    DB_PORT = os.getenv("POSTGRES_PORT", "5432")
    
    # Constructed Database URL for SQLAlchemy (Async)
    DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

settings = Config()