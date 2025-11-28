"""Test Claude HTML parser directly."""
import sys
from pathlib import Path
import requests

BASE_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

from apps.memberview.utils.claude_html_parser import ClaudeHTMLParser

# Test with City Fields about-us page
url = 'https://www.cityfieldscdc.com/about-us'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

print(f"Fetching: {url}")
response = requests.get(url, headers=headers, timeout=10)
print(f"Status: {response.status_code}")
print(f"HTML length: {len(response.text)} characters")

print("\nTesting Claude parser...")
try:
    import logging
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
    
    parser = ClaudeHTMLParser()
    print("Parser created successfully")
    
    print("Calling extract_staff_from_html...")
    staff = parser.extract_staff_from_html(response.text, url)
    
    print(f"\nExtracted {len(staff)} staff members:")
    if staff:
        for s in staff:
            print(f"  - {s.get('name')}: {s.get('title')} ({s.get('type', 'staff')})")
            if s.get('email'):
                print(f"    Email: {s['email']}")
            if s.get('phone'):
                print(f"    Phone: {s['phone']}")
    else:
        print("  No staff members found")
        print("  Checking cache...")
        cache_file = Path("#JustData_Repo/apps/memberview/data/enriched_data/claude_parsing_cache.json")
        if cache_file.exists():
            import json
            with open(cache_file) as f:
                cache = json.load(f)
                print(f"  Cache has {len(cache)} entries")
                cache_key = f"{url}_staff"
                if cache_key in cache:
                    print(f"  Found cached data: {len(cache[cache_key])} staff")
                else:
                    print(f"  No cached data for {cache_key}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

