# Data Enrichment Proposal

## Date: November 22, 2025

## Current Data Gaps
Based on user feedback, the following data is missing or incomplete:
- **Website information**: Many members don't have websites in HubSpot
- **Staff information**: No staff/employee data available
- **Contact information**: Limited contact details beyond what's in HubSpot

## Proposed Enrichment Strategy

### 1. Website Discovery
**Approach**: Search for company websites using multiple methods

#### Method A: Google Search API
- Use Google Custom Search API or Google Places API
- Search: "{company name} {city} {state} official website"
- Extract top result URL
- Pros: High accuracy, official sources
- Cons: Requires API key, has usage limits

#### Method B: Web Scraping Search Engines
- Use DuckDuckGo (no API key needed) or Bing Search API
- Search for company name + location
- Parse search results for official websites
- Pros: Free, no API key needed (DuckDuckGo)
- Cons: May need to handle rate limiting

#### Method C: Domain Name Search
- Use company name to generate likely domain names
- Check if domains exist and are active
- Use WHOIS or DNS lookup
- Pros: Fast, can check multiple variations
- Cons: May find wrong domain if company name is common

### 2. Website Content Extraction
**Approach**: Once we have a website, extract structured information

#### Tools/Libraries:
- **BeautifulSoup4**: HTML parsing
- **Selenium/Playwright**: For JavaScript-heavy sites
- **Scrapy**: For more complex scraping
- **readability-lxml**: Extract main content from pages

#### Information to Extract:
1. **Contact Information**:
   - Email addresses (contact@, info@, etc.)
   - Phone numbers
   - Physical addresses
   - Contact forms

2. **Staff Information**:
   - Leadership team (CEO, President, Executive Director)
   - Board members
   - Key staff members
   - Staff directory pages

3. **Organization Details**:
   - Mission statement
   - Services offered
   - Service areas
   - Annual reports

### 3. Implementation Approach

#### Phase 1: Website Discovery
```python
class WebsiteEnricher:
    def find_website(self, company_name, city, state):
        # Try multiple methods
        # 1. Google Search API
        # 2. DuckDuckGo search
        # 3. Domain name variations
        # Return best match with confidence score
```

#### Phase 2: Website Scraping
```python
class WebsiteScraper:
    def extract_contact_info(self, url):
        # Extract emails, phones, addresses
        # Return structured data
    
    def extract_staff_info(self, url):
        # Look for "About Us", "Team", "Staff" pages
        # Extract names and titles
        # Return list of staff members
```

#### Phase 3: Data Integration
- Store enriched data in cache/database
- Update member records with new information
- Flag data source (HubSpot vs. Enriched)

## Recommended Tools & Libraries

### For Web Search
1. **DuckDuckGo Search** (Free, no API key)
   - Library: `duckduckgo-search` or `requests` + HTML parsing
   - Good for: General web searches

2. **Google Custom Search API** (Paid, requires API key)
   - More accurate results
   - Higher rate limits with paid tier

3. **Bing Web Search API** (Free tier available)
   - Good alternative to Google

### For Web Scraping
1. **BeautifulSoup4** + **requests**
   - Simple HTML parsing
   - Good for: Static websites

2. **Selenium** or **Playwright**
   - Browser automation
   - Good for: JavaScript-heavy sites

3. **Scrapy**
   - Full-featured scraping framework
   - Good for: Complex scraping tasks

### For Contact Extraction
1. **email-validator**: Validate email addresses
2. **phonenumbers**: Parse and validate phone numbers
3. **tldextract**: Extract domain information

## Implementation Considerations

### Rate Limiting
- Implement delays between requests (1-2 seconds)
- Use rotating user agents
- Respect robots.txt
- Cache results to avoid re-scraping

### Error Handling
- Handle timeouts
- Handle blocked requests
- Handle missing data gracefully
- Log failures for manual review

### Data Quality
- Validate extracted data (email format, phone format)
- Confidence scoring for matches
- Manual review queue for low-confidence matches

### Legal/Ethical
- Respect robots.txt
- Don't overload servers
- Use public information only
- Consider terms of service

## Proposed File Structure
```
apps/memberview/
├── utils/
│   ├── website_enricher.py      # Find websites
│   ├── website_scraper.py       # Scrape website content
│   ├── contact_extractor.py     # Extract contact info
│   └── staff_extractor.py       # Extract staff info
├── data/
│   └── enriched_data/
│       ├── websites_cache.json
│       ├── contacts_cache.json
│       └── staff_cache.json
└── scripts/
    └── enrich_member_data.py    # Main enrichment script
```

## Example Implementation

### Website Discovery
```python
def find_company_website(company_name, city, state):
    """
    Find company website using multiple methods.
    Returns URL and confidence score.
    """
    # Method 1: DuckDuckGo search
    query = f"{company_name} {city} {state} official website"
    results = duckduckgo_search(query, max_results=5)
    
    # Score results based on:
    # - Domain matches company name
    # - Contains location info
    # - Has contact information
    # - SSL certificate (https)
    
    return best_match_url, confidence_score
```

### Contact Extraction
```python
def extract_contact_info(url):
    """
    Extract contact information from website.
    """
    page = fetch_page(url)
    
    # Look for common patterns:
    # - Email: contact@, info@, etc.
    # - Phone: Various formats
    # - Address: In footer, contact page
    
    contacts = {
        'emails': extract_emails(page),
        'phones': extract_phones(page),
        'address': extract_address(page)
    }
    
    return contacts
```

### Staff Extraction
```python
def extract_staff_info(url):
    """
    Extract staff information from website.
    """
    # Find "About Us", "Team", "Staff" pages
    about_pages = find_about_pages(url)
    
    staff = []
    for page_url in about_pages:
        page = fetch_page(page_url)
        # Extract names and titles
        staff_members = parse_staff_page(page)
        staff.extend(staff_members)
    
    return staff
```

## Implementation Status

### ✅ Completed
1. **WebsiteEnricher Class** (`utils/website_enricher.py`)
   - Website discovery using DuckDuckGo search
   - Domain pattern matching
   - Contact information extraction (emails, phones, addresses)
   - Staff information extraction
   - Caching system to avoid re-scraping

2. **Enrichment Script** (`scripts/enrich_member_data.py`)
   - Processes all members
   - Saves progress incrementally
   - Supports resuming from specific index
   - Progress bar with tqdm

### 📋 Next Steps
1. Test the enrichment script on a small sample
2. Integrate enriched data into member detail view
3. Add API endpoint to trigger enrichment for specific members
4. Add UI to display enriched data (website, contacts, staff)
5. Consider using paid APIs (Google Search, Clearbit) for better accuracy

## Usage

### Run Enrichment Script
```bash
# Enrich all members
python scripts/enrich_member_data.py

# Enrich first 10 members (for testing)
python scripts/enrich_member_data.py --limit 10

# Resume from index 100
python scripts/enrich_member_data.py --start-from 100
```

### Use in Code
```python
from apps.memberview.utils.website_enricher import WebsiteEnricher

enricher = WebsiteEnricher()
result = enricher.enrich_member(
    company_name="NCRC",
    city="Washington",
    state="DC"
)

print(result['website'])
print(result['contacts']['emails'])
print(result['staff'])
```

