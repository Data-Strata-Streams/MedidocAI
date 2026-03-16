# Purpose: Main FastAPI application entry point. Handles AI core APIs and cleanly routes to external WhatsApp and Web modules.

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from engine.core.retrieval import search_medicine
from engine.core.generator import generate_response
from engine.others.whatsapp_webhook import whatsapp_router
from Web.Engine.Core.web_router import web_app_router  # Import the new Web router

app = FastAPI(
    title="MedidocAI API",
    description="AI-powered medicine query assistant for WhatsApp and Web.",
    version="1.0.0"
)

# Static assets (blog images, etc.)
_MEDIDOC_ROOT = Path(__file__).resolve().parents[1]
_IMAGES_DIR = _MEDIDOC_ROOT / "Web" / "Pages" / "images"
app.mount("/images", StaticFiles(directory=str(_IMAGES_DIR)), name="images")

# Include external routers cleanly
app.include_router(whatsapp_router)
app.include_router(web_app_router)

# Define the request payload structure
class QueryRequest(BaseModel):
    query: str
    persona: str = "General Public"

# Define the response payload structure
class QueryResponse(BaseModel):
    query: str
    persona: str
    response: str

# Pure AI Engine Text API endpoint
@app.post("/api/v1/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
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

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "MedidocAI Engine"}
