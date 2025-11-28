"""Test website search for Pillsbury United Communities."""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

from apps.memberview.utils.website_enricher import WebsiteEnricher
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

print("Testing website search for Pillsbury United Communities")
print("=" * 80)

enricher = WebsiteEnricher()

company_name = "Pillsbury United Communities"
city = None
state = None

print(f"\nSearching for: {company_name}")

# Test the confidence calculation directly
test_url = "https://pillsburyunited.org/"
print(f"\nTesting URL: {test_url}")

# Check if it's likely a company website
is_likely = enricher._is_likely_company_website(test_url, company_name)
print(f"Is likely company website: {is_likely}")

if is_likely:
    confidence = enricher._calculate_confidence(test_url, company_name, city, state)
    print(f"Confidence: {confidence:.2f}")
    print(f"Would be accepted: {confidence >= 0.70}")

# Now try the actual search
print("\n" + "=" * 80)
print("Running actual search...")

# Test Google Custom Search directly
print("\nTesting Google Custom Search...")
google_result = enricher._search_google_custom(company_name, city, state)
if google_result:
    print(f"Google found: {google_result[0]} (confidence: {google_result[1]:.2f})")
else:
    print("Google Custom Search did not find website")

# Now try the full search
print("\n" + "=" * 80)
print("Running full find_website()...")
result = enricher.find_website(company_name, city, state)

if result:
    url, conf = result
    print(f"\nFound website: {url}")
    print(f"Confidence: {conf:.2f}")
else:
    print("\nNo website found!")



