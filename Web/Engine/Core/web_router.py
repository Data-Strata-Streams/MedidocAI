# Purpose: Web router updated to support modern FastAPI/Starlette TemplateResponse signature.
import os
import json
import base64
from urllib.parse import unquote
from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.templating import Jinja2Templates

from engine.core.retrieval import search_medicine
from engine.core.generator import generate_response
from engine.core.audio_handler import transcribe_audio
from engine.core.vision_handler import analyze_image
from engine.core.tts_handler import generate_audio_base64
from engine.core.fallback import get_generic_from_ai, log_missing_medicine

web_app_router = APIRouter()
# Fix: Ensure absolute pathing for Docker compatibility
BASE_DIR = os.getcwd() 
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "Web/Pages"))

# --- DEFENSIVE DATA HELPERS ---
def get_all_data():
    try:
        with open("data/processed/medicine_database.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except: return []

def get_by_generic(generic_name):
    data = get_all_data()
    return [item for item in data if item.get("generic_name") and item["generic_name"].lower() == generic_name.lower()]

def get_by_manufacturer(manufacturer_name):
    data = get_all_data()
    results = []
    target = manufacturer_name.lower()
    for item in data:
        brands = item.get("local_brands", [])
        if not isinstance(brands, list): continue
        for brand in brands:
            if isinstance(brand, dict):
                m_name = brand.get("manufacturer")
                # Ensure manufacturer is a string before calling .lower()
                if isinstance(m_name, str) and m_name.lower() == target:
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
            m = brand.get("manufacturer")
            if isinstance(m, str):
                manufacturers.add(m)
    return sorted(list(manufacturers))

def get_by_brand_name(brand_name: str):
    data = get_all_data()
    results = []
    if not brand_name: return results
    wanted = unquote(brand_name).replace("-", " ").lower()
    for item in data:
        for brand in item.get("local_brands", []):
            if isinstance(brand, dict):
                bn = brand.get("brand_name", "")
                if isinstance(bn, str) and bn.lower() == wanted:
                    results.append({
                        "brand": brand,
                        "generic_name": item.get("generic_name"),
                        "clinical_profile": item.get("clinical_profile"),
                    })
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
    return templates.TemplateResponse(request=request, name="index.html", context={"request": request})

@web_app_router.get("/medical-disclaimer", response_class=HTMLResponse)
async def serve_disclaimer(request: Request):
    return templates.TemplateResponse(request=request, name="disclaimer.html", context={"request": request})

@web_app_router.get("/privacy-policy", response_class=HTMLResponse)
async def serve_privacy(request: Request):
    return templates.TemplateResponse(request=request, name="privacy.html", context={"request": request})

@web_app_router.get("/terms-of-service", response_class=HTMLResponse)
async def serve_terms(request: Request):
    return templates.TemplateResponse(request=request, name="terms.html", context={"request": request})

@web_app_router.get("/about-us", response_class=HTMLResponse)
async def serve_about(request: Request):
    return templates.TemplateResponse(request=request, name="about.html", context={"request": request})

@web_app_router.get("/contact-us", response_class=HTMLResponse)
async def serve_contact(request: Request):
    return templates.TemplateResponse(request=request, name="contact.html", context={"request": request})

@web_app_router.get("/rx-pill-identifier", response_class=HTMLResponse)
async def serve_rx_pill_identifier(request: Request):
    return templates.TemplateResponse(request=request, name="coming_soon.html", context={"request": request, "title": "Rx & Pill Identifier", "subtitle": "Coming Soon!"})

# SEO ROUTES
@web_app_router.get("/robots.txt")
async def serve_robots():
    content = "User-agent: *\nDisallow:\nSitemap: https://www.medidocai.com/sitemap.xml"
    return Response(content=content, media_type="text/plain")

@web_app_router.get("/sitemap.xml")
async def serve_sitemap(request: Request):
    base_url = "https://www.medidocai.com"
    all_posts = get_all_blogs()
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    # Adding sitemaps
    sitemaps = ["sitemap-medicines.xml", "sitemap-generics.xml", "sitemap-manufacturers.xml"]
    for sitemap in sitemaps:
        xml_content += f'  <sitemap><loc>{base_url}/{sitemap}</loc></sitemap>\n'
    xml_content += f'  <sitemap><loc>{base_url}/sitemap-pages.xml</loc></sitemap>\n'
    xml_content += '</sitemapindex>'
    return Response(content=xml_content, media_type="application/xml")

# Browse Routes
@web_app_router.get("/generic-browse", response_class=HTMLResponse)
async def serve_generic_browse(request: Request):
    return templates.TemplateResponse(request=request, name="browse.html", context={"request": request, "items": get_unique_generics(), "title": "Browse by Generic Formula", "type": "generic"})

@web_app_router.get("/manufacturer-browse", response_class=HTMLResponse)
async def serve_manufacturer_browse(request: Request):
    return templates.TemplateResponse(request=request, name="browse.html", context={"request": request, "items": get_unique_manufacturers(), "title": "Browse by Manufacturer", "type": "manufacturer"})

@web_app_router.get("/generic/{name}", response_class=HTMLResponse)
async def serve_generic_page(request: Request, name: str):
    return templates.TemplateResponse(request=request, name="list_view.html", context={"request": request, "title": f"Medicines: {name}", "items": get_by_generic(name), "type": "generic"})

@web_app_router.get("/manufacturer/{name}", response_class=HTMLResponse)
async def serve_manufacturer_page(request: Request, name: str):
    return templates.TemplateResponse(request=request, name="list_view.html", context={"request": request, "title": f"Manufacturer: {name}", "items": get_by_manufacturer(name), "type": "manufacturer"})

@web_app_router.get("/medicine/{brand_name}", response_class=HTMLResponse)
async def serve_medicine_detail(request: Request, brand_name: str):
    matches = get_by_brand_name(brand_name)
    if not matches: raise HTTPException(status_code=404, detail="Medicine not found")
    return templates.TemplateResponse(request=request, name="medicine_detail.html", context={"request": request, "brand_name": brand_name, "generic_name": next((m.get("generic_name") for m in matches), None), "matches": matches, "clinical_profile": next((m.get("clinical_profile") for m in matches if isinstance(m.get("clinical_profile"), dict)), None)})

@web_app_router.get("/blog", response_class=HTMLResponse)
async def serve_blog_index(request: Request):
    return templates.TemplateResponse(request=request, name="Blog/index.html", context={"request": request, "posts": get_all_blogs()})

@web_app_router.get("/blog/{slug}", response_class=HTMLResponse)
async def serve_blog_post(request: Request, slug: str):
    post = next((p for p in get_all_blogs() if p["slug"] == slug), None)
    if not post: raise HTTPException(status_code=404, detail="Post not found")
    return templates.TemplateResponse(request=request, name="Blog/post.html", context={"request": request, "post": post})

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