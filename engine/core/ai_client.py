# Purpose: Initialize Google Vertex AI, configuring Gemini 2.5 Flash for generation and a text embedding model for Qdrant vectorization.

import vertexai
from vertexai.generative_models import GenerativeModel
from vertexai.language_models import TextEmbeddingModel
from config.config import settings

# Initialize Vertex AI with credentials and project details from config
vertexai.init(project=settings.GCP_PROJECT_ID, location=settings.GCP_LOCATION)

# Initialize the strictly mandated Gemini 2.5 Flash model
gemini_model = GenerativeModel("gemini-2.5-flash")

# Initialize the embedding model for Vector DB (Qdrant) ingestion (Fixed typo here)
embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")

def get_text_embedding(text: str) -> list[float]:
    """Generates a vector embedding for a given text string."""
    embeddings = embedding_model.get_embeddings([text])
    return embeddings[0].values
