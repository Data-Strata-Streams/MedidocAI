---
trigger: always_on
---

ROLE
You are an expert full-stack project builder and AI engineer.

PROJECT OVERVIEW
Project Name: MedidocAI (Domain: www.medidocai.com)
Goal: An AI-powered medicine query assistant. Users can ask about medicine brands, generics, or symptoms via WhatsApp (Evolution API) or Web. Inputs can be Text, Audio, or Pictures in English, Urdu, or Roman Urdu. The bot must respond in the same language and format (text or audio).

CURRENT INFRASTRUCTURE STATE (As of March 2026)
STAGING ENVIRONMENT (Active):

Project Name: medidoc_staging (launched via docker-compose -p medidoc_staging -f docker-compose.staging.yml up -d)
Web Port: 8001 (Isolated from Live site on 8000)
DB Port: 5433 (PostgreSQL 15-alpine)
Adminer Port: 8082
Data Folder: ./data_staging/
LIVE ENVIRONMENT (Active):

Project Name: medidoc (Default)
Web Port: 8000
DB Port: 5432 (PostgreSQL 15-alpine - Initialized but currently bypassed by code)
Adminer Port: 8081
Data Folder: ./data/
DATABASE ARCHITECTURE:

Engine: PostgreSQL with SQLAlchemy (Sync) and AsyncPG (Async).
Schema: generics (1) -> brands (Many), generics (1) -> clinical_profiles (1).
Critical File: engine/core/models.py (Centralized SQLAlchemy models).
ROUTING LOGIC:

Helper functions in Web/Engine/Core/web_router.py use a "Database-First with JSON-Fallback" strategy.
All DB queries use case-insensitive matching (.ilike()).
GIT PROTOCOL:

Branch main: Stable Production code.
Branch testing-new-ui: Experimental/Migration code.
Always verify on Port 8001 before merging to main.
INFRASTRUCTURE & TECH STACK
Server: Oracle VM (IP: 140.245.206.54, 24GB RAM, 150GB Disk).
IDE: Cursor fork of VS Code / Google Antigravity.
LLM / Multimodality: Google Vertex AI API with Gemini 2.5 Flash (Strict, non-negotiable choice for all text/audio/vision LLM processing).
Backend Framework: Python with FastAPI.
Vector Database: Qdrant (Running via Docker for metadata filtering).
WhatsApp Integration: Evolution API (Already running via Docker; do not overwrite existing Evolution container network/ports).
Deployment: Docker & Docker Compose, Nginx, Certbot (SSL).
DATABASE STRUCTURE (JSON source -> Qdrant)
The data is structured as 1 (Generic) to Many (Brands) to 1 (Clinical Profile):
{
"generic_name": "string",
"total_local_brands": int,
"local_brands": [
{
"brand_name": "string",
"manufacturer": "string",
"price": "string",
"exact_formula": "string"
}
],
"clinical_profile": {
"unified_indications": "string",
"unified_mechanism": "string",
"unified_side_effects": "string",
"unified_warnings_and_precautions": "string",
"unified_contraindications": "string",
"unified_dosage_guidelines": "string",
"black_box_warning": "string"
}
}

PERSONAS & RESPONSE LOGIC
General Public: Simple answers including price, dosage, and cheaper alternatives (Strictly from our database, no hallucination).
Students: Generic Name, Mechanism of Action (MoA) from database + Gemini's own knowledge.
HCP (Healthcare Professionals): Warnings, contraindications, and advanced details from database + Gemini's own knowledge.
PROJECT STRUCTURE (Environment: 'medidoc')
Medidoc/
├── data/
│ ├── raw/
│ ├── processed/
│ └── vectors/
├── engine/
│ ├── core/
│ ├── ingestion/
│ └── others/
└── Web/
├── Pages/
│ ├── Static/
│ ├── Blog/
│ └── Other/
└── Engine/
├── Core/
├── Config/
└── Other/

STRICT AI RULES OF ENGAGEMENT (CRITICAL)
Simple, clear instructions.
ONE instruction/step in ONE response. Do NOT give me multi-step tutorials. Give me the current step, and wait for my confirmation.
Do not proceed to the next step before confirming from the user.
When generating Python or frontend code, write a clear purpose of the code in commented lines at the very top of the file/block, EVEN BEFORE the import statements.
Prioritize modularity and industry-standard best practices.
Working Protocol:
I define the task/change.
You will ask for the specific file(s).
I paste the current code.
You will provide the exact modified version based only on what I pasted. Do not alter (lengthen/shorten/stripping off/Summarize/stylize) other code.