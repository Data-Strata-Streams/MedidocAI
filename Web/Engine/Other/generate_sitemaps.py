import json
import urllib.parse
import os

def generate_xml(items, folder_path, priority):
    """Generates the XML string for dynamic items."""
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    for name in items:
        if not name:
            continue
        clean_name = str(name).strip().replace(" ", "-")
        slug = urllib.parse.quote(clean_name)
        xml += '  <url>\n'
        xml += f'    <loc>https://www.medidocai.com/{folder_path}/{slug}</loc>\n'
        xml += '    <changefreq>monthly</changefreq>\n'
        xml += f'    <priority>{priority}</priority>\n'
        xml += '  </url>\n'
        
    xml += '</urlset>'
    return xml

def generate_static_sitemap():
    """Generates the XML string for your hardcoded core pages."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <!-- Core Pages -->
  <url><loc>https://www.medidocai.com/</loc><priority>1.0</priority></url>
  <url><loc>https://www.medidocai.com/generic-browse</loc><priority>0.9</priority></url>
  <url><loc>https://www.medidocai.com/manufacturer-browse</loc><priority>0.9</priority></url>
  <url><loc>https://www.medidocai.com/blog</loc><priority>0.8</priority></url>

  <!-- Legal & Info Pages -->
  <url><loc>https://www.medidocai.com/about-us</loc><priority>0.5</priority></url>
  <url><loc>https://www.medidocai.com/contact-us</loc><priority>0.5</priority></url>
  <url><loc>https://www.medidocai.com/terms-of-service</loc><priority>0.5</priority></url>
  <url><loc>https://www.medidocai.com/privacy-policy</loc><priority>0.5</priority></url>
  <url><loc>https://www.medidocai.com/medical-disclaimer</loc><priority>0.5</priority></url>
</urlset>"""

def generate_sitemap_index():
    """Generates the Master Index file for Google."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://www.medidocai.com/sitemap-pages.xml</loc></sitemap>
  <sitemap><loc>https://www.medidocai.com/sitemap-generics.xml</loc></sitemap>
  <sitemap><loc>https://www.medidocai.com/sitemap-manufacturers.xml</loc></sitemap>
  <sitemap><loc>https://www.medidocai.com/sitemap-medicines.xml</loc></sitemap>
</sitemapindex>"""

def generate_robots_txt():
    """Generates the robots.txt file to protect your SEO from AI queries."""
    return """User-agent: *
Disallow: /*?chat=
Disallow: /*?query=

Sitemap: https://www.medidocai.com/sitemap.xml
"""

def main():
    # 1. Figure out absolute paths based on this script's location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Path to database (Up 3 levels to Medidoc, then into data/processed)
    db_path = os.path.abspath(os.path.join(script_dir, "../../../data/processed/medicine_database.json"))
    
    # Path to output folder (Up 2 levels to Web, then into Pages)
    output_dir = os.path.abspath(os.path.join(script_dir, "../../Pages"))

    if not os.path.exists(db_path):
        print(f"❌ Error: Database file not found at:\n{db_path}")
        return

    # Ensure the Pages directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        print(f"Loading database from:\n{db_path}\n")
        with open(db_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            
        generics = set()
        medicines = set()
        manufacturers = set()

        # 2. Extract and deduplicate the data
        for item in data:
            generic = item.get("generic_name")
            if generic: generics.add(generic)
                
            for brand in item.get("local_brands", []):
                brand_name = brand.get("brand_name")
                manufacturer = brand.get("manufacturer")
                if brand_name: medicines.add(brand_name)
                if manufacturer: manufacturers.add(manufacturer)

        print(f"📊 Extracted:")
        print(f"  - {len(generics)} Unique Generics")
        print(f"  - {len(medicines)} Unique Medicines")
        print(f"  - {len(manufacturers)} Unique Manufacturers\n")

        print(f"Writing all SEO files directly to:\n{output_dir}\n")

        # 3. Write Dynamic Sitemaps to /Pages
        with open(os.path.join(output_dir, 'sitemap-medicines.xml'), 'w', encoding='utf-8') as f:
            f.write(generate_xml(medicines, 'medicine', '0.6'))
            print("✅ Created sitemap-medicines.xml")

        with open(os.path.join(output_dir, 'sitemap-generics.xml'), 'w', encoding='utf-8') as f:
            f.write(generate_xml(generics, 'generic', '0.8'))
            print("✅ Created sitemap-generics.xml")

        with open(os.path.join(output_dir, 'sitemap-manufacturers.xml'), 'w', encoding='utf-8') as f:
            f.write(generate_xml(manufacturers, 'manufacturer', '0.7'))
            print("✅ Created sitemap-manufacturers.xml")

        # 4. Write Static Sitemaps & Configurations to /Pages
        with open(os.path.join(output_dir, 'sitemap-pages.xml'), 'w', encoding='utf-8') as f:
            f.write(generate_static_sitemap())
            print("✅ Created sitemap-pages.xml")

        with open(os.path.join(output_dir, 'sitemap.xml'), 'w', encoding='utf-8') as f:
            f.write(generate_sitemap_index())
            print("✅ Created Master sitemap.xml")

        with open(os.path.join(output_dir, 'robots.txt'), 'w', encoding='utf-8') as f:
            f.write(generate_robots_txt())
            print("✅ Created robots.txt")

        print("\n🎉 SUCCESS! All files are now sitting perfectly in your 'Pages' directory.")

    except Exception as e:
        print(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    main()