"""Test staff extraction for City Fields CDC."""
import sys
from pathlib import Path
import requests
import re
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

# Test direct access to about-us page
url = 'https://www.cityfieldscdc.com/about-us'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
print(f"Fetching: {url}")
response = requests.get(url, headers=headers, timeout=10)
print(f"Status: {response.status_code}")
soup = BeautifulSoup(response.text, 'html.parser')

# Look for "Staff" heading
print("\nLooking for 'Staff' heading...")
headings = soup.find_all(['h1', 'h2', 'h3'])
for h in headings:
    text = h.get_text().strip().lower()
    if 'staff' in text:
        print(f"Found: {h.get_text()}")
        # Get parent container
        parent = h.find_parent(['section', 'div', 'article', 'main'])
        if parent:
            print(f"Parent tag: {parent.name}")
            # Find all h2/h3 that are names
            name_headings = parent.find_all(['h2', 'h3', 'h4'])
            print(f"Found {len(name_headings)} headings in parent")
            for nh in name_headings[:10]:
                name = nh.get_text().strip()
                # Check if it looks like a name
                if re.match(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}$', name) and len(name) < 50:
                    print(f"  Potential name: {name}")
                    # Get next sibling
                    next_sib = nh.find_next_sibling()
                    if next_sib:
                        title = next_sib.get_text().strip()
                        print(f"    Title: {title}")
                    # Also check parent text
                    parent_text = parent.get_text()
                    name_pos = parent_text.find(name)
                    if name_pos >= 0:
                        after_name = parent_text[name_pos + len(name):].strip()
                        title_from_text = after_name.split('\n')[0].split('.')[0].strip()[:100]
                        print(f"    Title from text: {title_from_text}")

print("\n" + "="*80)
print("Testing WebsiteEnricher...")
from apps.memberview.utils.website_enricher import WebsiteEnricher

enricher = WebsiteEnricher()
result = enricher.extract_staff_info('https://www.cityfieldscdc.com/')

print(f'\nExtracted {len(result)} staff members')
print("\nStaff members:")
for s in result:
    print(f"  - {s['name']}: {s['title']}")

