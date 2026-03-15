# Purpose: Main FastAPI application entry point. Handles incoming HTTP requests, orchestrates retrieval, and includes WhatsApp webhook routes.

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from engine.core.retrieval import search_medicine
from engine.core.generator import generate_response
from engine.others.whatsapp_webhook import whatsapp_router  # Import the new webhook router

app = FastAPI(
    title="MedidocAI API",
    description="AI-powered medicine query assistant for WhatsApp and Web.",
    version="1.0.0"
)

# Include the WhatsApp webhook router
app.include_router(whatsapp_router)

# Define the request payload structure
class QueryRequest(BaseModel):
    query: str
    persona: str = "General Public"  # Default persona

# Define the response payload structure
class QueryResponse(BaseModel):
    query: str
    persona: str
    response: str

@app.post("/api/v1/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """
    Receives a text query, retrieves relevant medical context from Qdrant,
    and generates a persona-specific response using Gemini 2.5 Flash.
    """
    try:
        retrieved_context = search_medicine(request.query)
        ai_response = generate_response(
            user_query=request.query,
            retrieved_data=retrieved_context,
            persona_type=request.persona
        )
        return QueryResponse(
            query=request.query,
            persona=request.persona,
            response=ai_response
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy", "service": "MedidocAI Engine"}
