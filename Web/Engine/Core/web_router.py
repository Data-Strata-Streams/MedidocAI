import os
import json
import base64
from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# Import existing AI engine functions
from engine.core.retrieval import search_medicine
from engine.core.generator import generate_response
from engine.core.audio_handler import transcribe_audio
from engine.core.vision_handler import analyze_image
from engine.core.tts_handler import generate_audio_base64
from engine.core.fallback import get_generic_from_ai, log_missing_medicine

web_app_router = APIRouter()
templates = Jinja2Templates(directory="Web/Pages")

# --- DATA HELPERS ---
def get_all_data():
    with open("data/processed/medicine_database.json", "r", encoding="utf-8") as f:
        return json.load(f)

def get_by_generic(generic_name):
    data = get_all_data()
    return [item for item in data if item["generic_name"].lower() == generic_name.lower()]

def get_by_manufacturer(manufacturer_name):
    data = get_all_data()
    results = []
    for item in data:
        for brand in item.get("local_brands", []):
            if not isinstance(brand, dict):
                continue
            m = brand.get("manufacturer")
            if not isinstance(m, str) or not m:
                continue
            if m.lower() == manufacturer_name.lower():
                results.append({"brand": brand, "generic": item.get("generic_name")})
    return results

def get_unique_generics():
    data = get_all_data()
    return sorted(list(set([d['generic_name'] for d in data if d.get('generic_name')])))

def get_unique_manufacturers():
    data = get_all_data()
    manufacturers = set()
    for item in data:
        for brand in item.get("local_brands", []):
            if brand.get("manufacturer"):
                manufacturers.add(brand["manufacturer"])
    return sorted(list(manufacturers))

def get_by_brand_name(brand_name: str):
    data = get_all_data()
    results = []
    if not isinstance(brand_name, str) or not brand_name:
        return results
    wanted = brand_name.lower()
    for item in data:
        local_brands = item.get("local_brands", [])
        if not isinstance(local_brands, list):
            continue
        for brand in local_brands:
            if not isinstance(brand, dict):
                continue
            bn = brand.get("brand_name")
            if not isinstance(bn, str) or not bn:
                continue
            if bn.lower() == wanted:
                results.append(
                    {
                        "brand": brand,
                        "generic_name": item.get("generic_name"),
                        "clinical_profile": item.get("clinical_profile"),
                    }
                )
    return results

def get_all_blogs():
    blog_file = "Web/Pages/Blog/data/blogs.json"
    if os.path.exists(blog_file):
        with open(blog_file, 'r', encoding='utf-8') as f:
            try: return json.load(f)
            except: return []
    return []

# --- ROUTES ---
@web_app_router.get("/", response_class=HTMLResponse)
async def serve_homepage(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Static Pages
@web_app_router.get("/medical-disclaimer", response_class=HTMLResponse)
async def serve_disclaimer(request: Request):
    return templates.TemplateResponse("disclaimer.html", {"request": request})

@web_app_router.get("/privacy-policy", response_class=HTMLResponse)
async def serve_privacy(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request})

@web_app_router.get("/terms-of-service", response_class=HTMLResponse)
async def serve_terms(request: Request):
    return templates.TemplateResponse("terms.html", {"request": request})

@web_app_router.get("/about-us", response_class=HTMLResponse)
async def serve_about(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})

@web_app_router.get("/contact-us", response_class=HTMLResponse)
async def serve_contact(request: Request):
    return templates.TemplateResponse("contact.html", {"request": request})

@web_app_router.get("/rx-pill-identifier", response_class=HTMLResponse)
async def serve_rx_pill_identifier(request: Request):
    return templates.TemplateResponse(
        "coming_soon.html",
        {
            "request": request,
            "title": "Rx & Pill Identifier",
            "subtitle": "Coming Soon!",
        },
    )

# Browse Routes
@web_app_router.get("/generic-browse", response_class=HTMLResponse)
async def serve_generic_browse(request: Request):
    return templates.TemplateResponse("browse.html", {"request": request, "items": get_unique_generics(), "title": "Browse by Generic Formula", "type": "generic"})

@web_app_router.get("/manufacturer-browse", response_class=HTMLResponse)
async def serve_manufacturer_browse(request: Request):
    return templates.TemplateResponse("browse.html", {"request": request, "items": get_unique_manufacturers(), "title": "Browse by Manufacturer", "type": "manufacturer"})

@web_app_router.get("/generic/{name}", response_class=HTMLResponse)
async def serve_generic_page(request: Request, name: str):
    items = get_by_generic(name)
    return templates.TemplateResponse("list_view.html", {"request": request, "title": f"Medicines: {name}", "items": items, "type": "generic"})

@web_app_router.get("/manufacturer/{name}", response_class=HTMLResponse)
async def serve_manufacturer_page(request: Request, name: str):
    items = get_by_manufacturer(name)
    return templates.TemplateResponse("list_view.html", {"request": request, "title": f"Manufacturer: {name}", "items": items, "type": "manufacturer"})

@web_app_router.get("/medicine/{brand_name}", response_class=HTMLResponse)
async def serve_medicine_detail(request: Request, brand_name: str):
    matches = get_by_brand_name(brand_name)
    if not matches:
        raise HTTPException(status_code=404, detail="Medicine not found")
    generic_name = next((m.get("generic_name") for m in matches if m.get("generic_name")), None)
    clinical_profile = next((m.get("clinical_profile") for m in matches if isinstance(m.get("clinical_profile"), dict)), None)
    return templates.TemplateResponse(
        "medicine_detail.html",
        {
            "request": request,
            "brand_name": brand_name,
            "generic_name": generic_name,
            "matches": matches,
            "clinical_profile": clinical_profile,
        },
    )

# Blog Routes
@web_app_router.get("/blog", response_class=HTMLResponse)
async def serve_blog_index(request: Request):
    return templates.TemplateResponse("Blog/index.html", {"request": request, "posts": get_all_blogs()})

@web_app_router.get("/blog/{slug}", response_class=HTMLResponse)
async def serve_blog_post(request: Request, slug: str):
    post = next((p for p in get_all_blogs() if p["slug"] == slug), None)
    if not post: raise HTTPException(status_code=404, detail="Post not found")
    return templates.TemplateResponse("Blog/post.html", {"request": request, "post": post})

# Chat API
@web_app_router.post("/web/chat")
async def web_chat(text: str = Form(None), audio: UploadFile = File(None), image: UploadFile = File(None), reply_type: str = Form("text"), persona: str = Form("General Public")):
    try:
        user_query = text
        if image:
            image_bytes = await image.read()
            user_query = analyze_image(base64.b64encode(image_bytes).decode('utf-8'), image.content_type, text or "")
        elif audio:
            audio_bytes = await audio.read()
            user_query = transcribe_audio(base64.b64encode(audio_bytes).decode('utf-8'), audio.content_type)
        
        retrieved_context = search_medicine(user_query, limit=15)
        ai_response = generate_response(user_query, retrieved_context, persona)
        
        if "MISSING_FLAG:" in ai_response:
            missing_med = ai_response.split("MISSING_FLAG:")[1].strip()
            generic = get_generic_from_ai(missing_med)
            if generic and generic != "UNKNOWN":
                ai_response = generate_response(user_query, search_medicine(generic, limit=15), persona)
            else:
                log_missing_medicine(missing_med)
                ai_response = f"Information for '{missing_med}' not found yet."

        return {"text": ai_response, "audio_base64": generate_audio_base64(ai_response) if reply_type == "audio" else None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
