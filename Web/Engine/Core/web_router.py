# Purpose: Web router updated with Corrected Data Structure for Database integration and dynamic Medical Dictionary injection for tooltips.
import os
import json
import base64
from urllib.parse import unquote
from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.templating import Jinja2Templates

# Database Imports
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config.config import settings
from engine.core.models import Generic, Brand, ClinicalProfile

from engine.core.retrieval import search_medicine
from engine.core.generator import generate_response
from engine.core.audio_handler import transcribe_audio
from engine.core.vision_handler import analyze_image
from engine.core.tts_handler import generate_audio_base64
from engine.core.fallback import get_generic_from_ai, log_missing_medicine
from engine.core.models import Generic, Brand, ClinicalProfile, MedicalTerm # Updated import

web_app_router = APIRouter()
BASE_DIR = os.getcwd() 
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "Web/Pages"))

# --- DATABASE SETUP ---
sync_url = settings.DATABASE_URL.replace("asyncpg", "psycopg2")
engine = create_engine(sync_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- DEFENSIVE DATA HELPERS ---
def get_all_data():
    try:
        with open("data/processed/medicine_database.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except: return []

# Initialize a global cache for the dictionary
cached_dictionary = {}

def get_medical_dictionary(filter_text: str = None):
    """Fetches medical terms from the database with an in-memory cache and optional filtering."""
    global cached_dictionary
    
    # If cache is empty, load from DB
    if not cached_dictionary:
        session = SessionLocal()
        try:
            terms = session.query(MedicalTerm.term, MedicalTerm.definition).all()
            cached_dictionary = {term.lower(): definition for term, definition in terms}
        except Exception as e:
            print(f"Error loading dictionary: {e}")
            return {}
        finally:
            session.close()
            
    if not filter_text:
        return cached_dictionary
        
    # Only return terms that actually appear in the clinical content
    filter_text_lower = filter_text.lower()
    return {
        term: definition 
        for term, definition in cached_dictionary.items() 
        if term in filter_text_lower
    }

def get_by_generic(generic_name):
    session = SessionLocal()
    try:
        # Search for both exact hyphenated name and space-separated variation
        name_variations = [generic_name, generic_name.replace("-", " ")]
        db_generic = session.query(Generic).filter(
            (Generic.generic_name.ilike(name_variations[0])) | 
            (Generic.generic_name.ilike(name_variations[1]))
        ).first()
        if db_generic and db_generic.brands:
            # Reconstruct the EXACT structure expected by list_view.html
            return [{
                "generic_name": db_generic.generic_name,
                "total_local_brands": db_generic.total_local_brands,
                "local_brands": [
                    {"brand_name": b.brand_name, "manufacturer": b.manufacturer, "price": b.price, "exact_formula": b.exact_formula}
                    for b in db_generic.brands
                ],
                "clinical_profile": {
                    "unified_indications": db_generic.profile.indications,
                    "unified_mechanism": db_generic.profile.mechanism,
                    "unified_side_effects": db_generic.profile.side_effects,
                    "unified_warnings_and_precautions": db_generic.profile.warnings,
                    "unified_contraindications": db_generic.profile.contraindications,
                    "unified_dosage_guidelines": db_generic.profile.dosage,
                    "black_box_warning": db_generic.profile.black_box
                } if db_generic.profile else {}
            }]
    except Exception as e:
        print(f"DB Error: {e}")
    finally:
        session.close()
    
    # Fallback to JSON
    data = get_all_data()
    wanted_variations = [generic_name.lower(), generic_name.replace("-", " ").lower()]
    return [item for item in data if item.get("generic_name") and item["generic_name"].lower() in wanted_variations]

def get_by_manufacturer(manufacturer_name):
    session = SessionLocal()
    try:
        name_variations = [manufacturer_name, manufacturer_name.replace("-", " ")]
        db_brands = session.query(Brand).filter(
            (Brand.manufacturer.ilike(name_variations[0])) | 
            (Brand.manufacturer.ilike(name_variations[1]))
        ).all()
        if db_brands:
            # Structure matches the original JSON results for manufacturer browse
            return [{"brand": {"brand_name": b.brand_name, "manufacturer": b.manufacturer, "price": b.price, "exact_formula": b.exact_formula}, "generic": b.generic.generic_name} for b in db_brands]
    except Exception as e:
        print(f"DB Error: {e}")
    finally:
        session.close()

    data = get_all_data()
    results = []
    target_variations = [manufacturer_name.lower(), manufacturer_name.replace("-", " ").lower()]
    for item in data:
        brands = item.get("local_brands", [])
        if not isinstance(brands, list): continue
        for brand in brands:
            if isinstance(brand, dict):
                m_name = brand.get("manufacturer")
                if isinstance(m_name, str) and m_name.lower() in target_variations:
                    results.append({"brand": brand, "generic": item.get("generic_name")})
    return results

def get_unique_generics():
    session = SessionLocal()
    try:
        generics = session.query(Generic.generic_name).order_by(Generic.generic_name).all()
        if generics: return [g[0] for g in generics]
    except: pass
    finally: session.close()

    data = get_all_data()
    return sorted(list(set([d['generic_name'] for d in data if d.get('generic_name')])))

def get_unique_manufacturers():
    session = SessionLocal()
    try:
        mfts = session.query(Brand.manufacturer).distinct().order_by(Brand.manufacturer).all()
        if mfts: return [m[0] for m in mfts if m[0]]
    except: pass
    finally: session.close()

    data = get_all_data()
    manufacturers = set()
    for item in data:
        for brand in item.get("local_brands", []):
            m = brand.get("manufacturer")
            if isinstance(m, str):
                manufacturers.add(m)
    return sorted(list(manufacturers))

def get_by_brand_name(brand_name: str):
    session = SessionLocal()
    try:
        # Try both the name with hyphens (literal) and spaces (SEO replacement)
        decoded = unquote(brand_name)
        wanted_variations = [decoded, decoded.replace("-", " ")]
        db_brand = session.query(Brand).filter(
            (Brand.brand_name.ilike(wanted_variations[0])) | 
            (Brand.brand_name.ilike(wanted_variations[1]))
        ).first()
        if db_brand:
            gen = db_brand.generic
            return [{
                "brand": {"brand_name": db_brand.brand_name, "manufacturer": db_brand.manufacturer, "price": db_brand.price, "exact_formula": db_brand.exact_formula},
                "generic_name": gen.generic_name,
                "clinical_profile": {
                    "unified_indications": gen.profile.indications,
                    "unified_mechanism": gen.profile.mechanism,
                    "unified_side_effects": gen.profile.side_effects,
                    "unified_warnings_and_precautions": gen.profile.warnings,
                    "unified_contraindications": gen.profile.contraindications,
                    "unified_dosage_guidelines": gen.profile.dosage,
                    "black_box_warning": gen.profile.black_box
                } if gen.profile else {},
            }]
    except Exception as e:
        print(f"DB Error: {e}")
    finally:
        session.close()

    # JSON Fallback
    data = get_all_data()
    results = []
    if not brand_name: return results
    decoded = unquote(brand_name).lower()
    wanted_variations = [decoded, decoded.replace("-", " ")]
    for item in data:
        for brand in item.get("local_brands", []):
            if isinstance(brand, dict):
                bn = brand.get("brand_name", "")
                if isinstance(bn, str) and bn.lower() in wanted_variations:
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
    
    generic_name = next((m.get("generic_name") for m in matches), None)
    
    # Fetch alternatives (other brands with same generic)
    alternatives = []
    if generic_name:
        all_generic_data = get_by_generic(generic_name)
        if all_generic_data:
            all_brands = all_generic_data[0].get('local_brands', [])
            current_brand_names = [m['brand']['brand_name'].lower() for m in matches]
            # Format alternatives to match the 'm.brand.brand_name' access pattern in template
            alternatives = [{"brand": b} for b in all_brands if b['brand_name'].lower() not in current_brand_names]
            

    clinical_profile = next((m.get("clinical_profile") for m in matches if isinstance(m.get("clinical_profile"), dict)), None)
    
    # Optimize: Only send dictionary terms that appear in this medicine's content
    combined_text = ""
    if clinical_profile:
        combined_text = " ".join([str(v) for v in clinical_profile.values() if v])

    return templates.TemplateResponse(
        request=request, 
        name="medicine_detail.html", 
        context={
            "request": request, 
            "brand_name": brand_name, 
            "generic_name": generic_name, 
            "matches": matches, 
            "alternatives": alternatives[:6], 
            "clinical_profile": clinical_profile,
            "medical_dictionary": json.dumps(get_medical_dictionary(combined_text))
        }
    )

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