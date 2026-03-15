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

settings = Config()
