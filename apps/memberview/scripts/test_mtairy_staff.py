"""Test staff extraction from Mt. Airy CDC."""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

from apps.memberview.utils.website_enricher import WebsiteEnricher

print("Testing enhanced staff discovery on Mt. Airy CDC...")
print("=" * 80)

enricher = WebsiteEnricher()

# Clear cache for this test
url = 'https://mtairycdc.org'
if url in enricher._staff:
    del enricher._staff[url]

print(f"\nExtracting staff from: {url}")
staff = enricher.extract_staff_info(url)

print(f"\nFound {len(staff)} staff members:")
print("-" * 80)

for i, s in enumerate(staff, 1):
    name = s.get('name', 'N/A')
    title = s.get('title', 'N/A')
    email = s.get('email', '')
    phone = s.get('phone', '')
    staff_type = s.get('type', 'staff')
    
    print(f"{i}. {name}")
    print(f"   Title: {title} ({staff_type})")
    if email:
        print(f"   Email: {email}")
    if phone:
        print(f"   Phone: {phone}")
    print()



