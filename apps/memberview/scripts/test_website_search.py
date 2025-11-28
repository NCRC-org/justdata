"""Test website search with DuckDuckGo and Google Custom Search fallback."""
import sys
from pathlib import Path

# Add paths to sys.path
BASE_DIR = Path(__file__).parent.parent.parent.parent  # Go up to #JustData_Repo
JUSTDATA_BASE = BASE_DIR
sys.path.insert(0, str(JUSTDATA_BASE))

# Also add the memberview app directory
MEMBERVIEW_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(MEMBERVIEW_DIR))

from dotenv import load_dotenv
import os

# Load environment variables
env_path = JUSTDATA_BASE / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"Loaded .env from: {env_path}")
else:
    print(f"Warning: .env file not found at {env_path}")

# Import after path setup
try:
    from utils.website_enricher import WebsiteEnricher
except ImportError:
    from apps.memberview.utils.website_enricher import WebsiteEnricher

def test_website_search():
    """Test website search functionality."""
    print("=" * 80)
    print("TESTING WEBSITE SEARCH")
    print("=" * 80)
    
    # Check API key configuration
    api_key = os.getenv("GOOGLE_CUSTOM_SEARCH_API_KEY")
    engine_id = os.getenv("GOOGLE_CUSTOM_SEARCH_ENGINE_ID")
    
    print(f"\nGoogle Custom Search API Key: {'[OK] Configured' if api_key else '[MISSING] Not configured'}")
    print(f"Google Custom Search Engine ID: {engine_id if engine_id else 'Not configured'}")
    
    enricher = WebsiteEnricher()
    
    # Test cases (excluding NCRC since we know it's ncrc.org)
    test_cases = [
        ("Center for Housing Economics", "Seattle", "WA"),
        ("The Collaborative", "Raleigh", "NC"),
        ("Ability Housing, Inc.", "Jacksonville", "FL"),
    ]
    
    print("\n" + "=" * 80)
    print("TESTING WEBSITE DISCOVERY")
    print("=" * 80)
    
    for company_name, city, state in test_cases:
        print(f"\nSearching for: {company_name} ({city}, {state})")
        print("-" * 80)
        
        result = enricher.find_website(company_name, city, state)
        
        if result:
            url, confidence = result
            print(f"[FOUND] {url}")
            print(f"  Confidence: {confidence:.2f}")
            
            # Check cache to see which method was used
            cache_key = f"{company_name}|{city}|{state}".lower()
            if cache_key in enricher._websites:
                method = enricher._websites[cache_key].get('method', 'unknown')
                print(f"  Method: {method}")
        else:
            print("[NOT FOUND]")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    test_website_search()

