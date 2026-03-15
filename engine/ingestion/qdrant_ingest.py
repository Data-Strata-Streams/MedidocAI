# Purpose: Read processed medicine JSON, generate vector embeddings via Vertex AI, and ingest into Qdrant database.

import json
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from config.config import settings
from engine.core.ai_client import get_text_embedding

def init_qdrant() -> tuple[QdrantClient, str]:
    """Initializes Qdrant client and creates the collection if it doesn't exist."""
    client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
    collection_name = "medicines"
    
    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE),
        )
    return client, collection_name

def ingest_data(file_path: str):
    """Reads JSON data, vectorizes the clinical context, and uploads to Qdrant."""
    client, collection_name = init_qdrant()
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    points = []
    for item in data:
        generic_name = item.get("generic_name", "")
        clinical = item.get("clinical_profile", {})
        
        search_text = (
            f"Generic Name: {generic_name}. "
            f"Indications: {clinical.get('unified_indications', '')}. "
            f"Mechanism of Action: {clinical.get('unified_mechanism', '')}."
        )
        
        vector = get_text_embedding(search_text)
        point_id = str(uuid.uuid4())
        
        points.append(
            PointStruct(
                id=point_id,
                vector=vector,
                payload=item
            )
        )
        print(f"Processed embedding for: {generic_name}")
        
    if points:
        client.upsert(collection_name=collection_name, points=points)
        print(f"\nSuccessfully ingested {len(points)} records into Qdrant collection '{collection_name}'.")

if __name__ == "__main__":
    ingest_data("data/processed/medicine_database.json")
