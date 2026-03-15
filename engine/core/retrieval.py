# Purpose: Handle vector similarity search by converting user queries into embeddings and retrieving a broad set of medical data from Qdrant.

from qdrant_client import QdrantClient
from config.config import settings
from engine.core.ai_client import get_text_embedding

def search_medicine(query: str, limit: int = 15) -> list[dict]:
    """Retrieves the top 15 matching medicine records to act as a broad net for the AI filter."""
    client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
    collection_name = "medicines"
    
    query_vector = get_text_embedding(query)
    
    search_results = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        limit=limit
    ).points
    
    return [hit.payload for hit in search_results]
