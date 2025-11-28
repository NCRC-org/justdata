"""
Website discovery and enrichment utilities.

Finds company websites and extracts contact/staff information.
Includes CMS detection and platform-specific URL pattern discovery.
"""
import re
import requests
import os
from typing import Dict, List, Optional, Tuple, Set, Any
from urllib.parse import urlparse, urljoin
import logging
from pathlib import Path
import json
import time

# Import BeautifulSoup at module level to avoid scope issues
try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    BEAUTIFULSOUP_AVAILABLE = False
    logger.warning("beautifulsoup4 not installed. Some features may not work.")

logger = logging.getLogger(__name__)


class WebsiteEnricher:
    """Find and extract information from company websites."""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize website enricher.
        
        Args:
            cache_dir: Directory to cache results (default: data/enriched_data)
        """
        if cache_dir is None:
            self.cache_dir = Path(__file__).parent.parent.parent / "data" / "enriched_data"
        else:
            self.cache_dir = Path(cache_dir)
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.websites_cache = self.cache_dir / "websites_cache.json"
        self.contacts_cache = self.cache_dir / "contacts_cache.json"
        self.staff_cache = self.cache_dir / "staff_cache.json"
        
        # Load existing caches
        self._websites = self._load_cache(self.websites_cache)
        self._contacts = self._load_cache(self.contacts_cache)
        self._staff = self._load_cache(self.staff_cache)
        self._org_info = {}
        # Try to load org_info cache if it exists
        org_info_cache_file = self.cache_dir / "org_info_cache.json"
        if org_info_cache_file.exists():
            self._org_info = self._load_cache(org_info_cache_file)
        
        # User agent for requests
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # CMS/platform detection patterns
        self.cms_patterns = {
            'wordpress': [
                r'wp-content', r'wp-includes', r'/wp-json/', r'wordpress',
                r'wp\.com', r'Powered by WordPress'
            ],
            'squarespace': [
                r'squarespace', r'sqspcdn\.com', r'squarespace\.com',
                r'<!-- This is Squarespace\. -->'
            ],
            'drupal': [
                r'drupal', r'/sites/default/', r'Drupal\.settings'
            ],
            'wix': [
                r'wix\.com', r'wixstatic\.com', r'wixpress\.com'
            ],
            'weebly': [
                r'weebly\.com', r'ws\.weebly\.com'
            ],
            'shopify': [
                r'shopify', r'shopifycdn\.com'
            ]
        }
        
        # Platform-specific URL patterns for staff/team pages
        self.platform_url_patterns = {
            'wordpress': [
                '/staff/', '/staff-directory/', '/team/', '/our-team/',
                '/about/staff/', '/about/team/', '/about-us/staff/',
                '/who-we-are/staff/', '/who-we-are/staff-directory/',
                '/people/', '/leadership/', '/board/', '/board-of-directors/',
                '/about/leadership/', '/about-us/team/', '/meet-our-team/',
                '/about/people/', '/staff-members/', '/team-members/',
                '/partners/', '/funders/', '/supporters/', '/sponsors/',
                '/programs/', '/services/', '/what-we-do/', '/our-work/',
                '/about/', '/about-us/', '/mission/', '/vision/'
            ],
            'squarespace': [
                '/team', '/staff', '/about/team', '/about/staff',
                '/leadership', '/board', '/people', '/who-we-are/team',
                '/who-we-are/staff', '/meet-our-team', '/our-team',
                '/partners', '/funders', '/supporters', '/sponsors',
                '/programs', '/services', '/what-we-do', '/our-work',
                '/about', '/about-us', '/mission', '/vision'
            ],
            'drupal': [
                '/staff', '/team', '/about/staff', '/people',
                '/leadership', '/board', '/staff-directory',
                '/partners', '/funders', '/supporters', '/sponsors',
                '/programs', '/services', '/what-we-do', '/our-work',
                '/about', '/about-us', '/mission', '/vision'
            ],
            'generic': [  # Fallback patterns for any CMS
                '/staff/', '/staff-directory/', '/team/', '/our-team/',
                '/about/staff/', '/about/team/', '/about-us/staff/',
                '/about-us/staff-directory/', '/who-we-are/staff/',
                '/who-we-are/staff-directory/', '/who-we-are/team/',
                '/people/', '/leadership/', '/board/', '/board-of-directors/',
                '/about/leadership/', '/about-us/team/', '/meet-our-team/',
                '/about/people/', '/staff-members/', '/team-members/',
                '/about-us/meet-our-team/', '/about/meet-our-team/',
                '/partners/', '/funders/', '/supporters/', '/sponsors/',
                '/programs/', '/services/', '/what-we-do/', '/our-work/',
                '/about/', '/about-us/', '/mission/', '/vision/'
            ]
        }
    
    def _load_cache(self, cache_file: Path) -> Dict:
        """Load cache from file."""
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load cache {cache_file}: {e}")
        return {}
    
    def _save_cache(self, cache_file: Path, data: Dict):
        """Save cache to file."""
        try:
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save cache {cache_file}: {e}")
    
    def _expand_abbreviation(self, company_name: str) -> List[str]:
        """
        Expand common abbreviations to full names for better website matching.
        Returns a list of search terms to try (original + expanded versions).
        
        Args:
            company_name: Company name (may be an abbreviation)
            
        Returns:
            List of search terms to try
        """
        search_terms = [company_name]  # Always include original
        
        # Common abbreviation patterns and expansions
        abbreviation_expansions = {
            'NAMC': 'National Association of Minority Contractors',
            'CDC': 'Community Development Corporation',
            'NHS': 'Neighborhood Housing Services',
            'CDFI': 'Community Development Financial Institution',
            'CRA': 'Community Reinvestment Act',
            'HUD': 'Housing and Urban Development',
            'LMI': 'Low to Moderate Income',
            'CBO': 'Community Based Organization',
            'NCRC': 'National Community Reinvestment Coalition',
        }
        
        # Detect if name looks like an abbreviation (all caps, short words)
        name_upper = company_name.upper()
        words = company_name.split()
        
        # Check if it's likely an abbreviation (all caps, 2-4 letters per word)
        is_abbreviation = (
            len(words) <= 3 and 
            all(len(w) <= 5 and w.isupper() for w in words if w.isalpha())
        )
        
        if is_abbreviation:
            # Try to expand known abbreviations
            expanded_parts = []
            location_part = None
            
            for word in words:
                word_clean = re.sub(r'[^A-Z]', '', word.upper())
                if word_clean in abbreviation_expansions:
                    expanded_parts.append(abbreviation_expansions[word_clean])
                elif len(word_clean) > 3:  # Likely a location (e.g., DFW, NYC)
                    location_part = word
                else:
                    expanded_parts.append(word)
            
            # If we expanded something, create full name
            if expanded_parts and any(exp in abbreviation_expansions.values() for exp in expanded_parts):
                full_name = ' '.join(expanded_parts)
                if location_part:
                    # Try with location at end: "National Association of Minority Contractors DFW"
                    search_terms.append(f"{full_name} {location_part}")
                    # Try with location expanded if it's a known metro
                    if location_part.upper() == 'DFW':
                        search_terms.append(f"{full_name} Dallas Fort Worth")
                    elif location_part.upper() == 'NYC':
                        search_terms.append(f"{full_name} New York")
                    elif location_part.upper() == 'LA':
                        search_terms.append(f"{full_name} Los Angeles")
                else:
                    search_terms.append(full_name)
        
        return search_terms
    
    def find_website(self, company_name: str, city: Optional[str] = None, 
                    state: Optional[str] = None) -> Optional[Tuple[str, float]]:
        """
        Find company website using multiple methods.
        Tries DuckDuckGo first (free), falls back to Google Custom Search if needed.
        Expands abbreviations to full names for better matching.
        
        Args:
            company_name: Company name
            city: Optional city
            state: Optional state
            
        Returns:
            Tuple of (URL, confidence_score) or None if not found
        """
        logger.info(f"find_website called for: {company_name} ({city}, {state})")
        
        # Expand abbreviations to get multiple search terms
        search_terms = self._expand_abbreviation(company_name)
        logger.debug(f"Search terms to try: {search_terms}")
        
        # Check cache first (for original name)
        cache_key = f"{company_name}|{city or ''}|{state or ''}".lower()
        logger.debug(f"Cache key: {cache_key}")
        if cache_key in self._websites:
            cached = self._websites[cache_key]
            logger.info(f"Found in cache: {cached}")
            if cached.get('url'):
                return (cached['url'], cached.get('confidence', 0.5))
            logger.info("Cached as not found, returning None")
            return None  # Cached as not found
        
        # Try each search term until we find a website
        for search_term in search_terms:
            logger.debug(f"Trying search term: {search_term}")
            
            # Try multiple methods - trust search engine rankings
            results = []
            google_result = None
            ddg_result = None
            
            # Method 1: Try Google Custom Search first (more reliable, especially first result)
            google_result = self._search_google_custom(search_term, city, state)
            if google_result:
                url, confidence = google_result
                # Trust Google's ranking - if it returns a result, especially first result, accept it
                if confidence >= 0.70:
                    self._websites[cache_key] = {
                        'url': url,
                        'confidence': confidence,
                        'method': 'google',
                        'search_term_used': search_term
                    }
                    self._save_cache(self.websites_cache, self._websites)
                    logger.info(f"Found website using Google search term '{search_term}': {url}")
                    return google_result
                results.append(google_result)
            
            # Method 2: DuckDuckGo search (free, no API key) - fallback if Google failed
            if not google_result or (google_result and google_result[1] < 0.70):
                logger.debug(f"Google {'failed' if not google_result else 'low confidence'} for '{search_term}', trying DuckDuckGo...")
                ddg_result = self._search_duckduckgo(search_term, city, state)
                if ddg_result:
                    url, confidence = ddg_result
                    # Trust DuckDuckGo's ranking - if it returns a result, accept it with lower threshold
                    if confidence >= 0.70:
                        self._websites[cache_key] = {
                            'url': url,
                            'confidence': confidence,
                            'method': 'duckduckgo',
                            'search_term_used': search_term
                        }
                        self._save_cache(self.websites_cache, self._websites)
                        logger.info(f"Found website using DuckDuckGo search term '{search_term}': {url}")
                        return ddg_result
                    # Otherwise, add to results for comparison
                    results.append(ddg_result)
            if google_result:
                url, confidence = google_result
                logger.info(f"Google returned: {url} with confidence {confidence:.2f}")
                # Trust Google's ranking - if Google returns it, especially first result, accept it
                if confidence >= 0.70:
                    logger.info(f"Accepting Google result (confidence {confidence:.2f} >= 0.70)")
                    self._websites[cache_key] = {
                        'url': url,
                        'confidence': confidence,
                        'method': 'google'
                    }
                    self._save_cache(self.websites_cache, self._websites)
                    return google_result
                else:
                    logger.info(f"Google result confidence {confidence:.2f} < 0.70, adding to results list")
                results.append(google_result)
            else:
                logger.info("Google Custom Search returned no result")
        
        # Method 3: Try common domain patterns
        domain_result = self._try_domain_patterns(company_name)
        if domain_result:
            results.append(domain_result)
        
        # Select best result from remaining options
        if results:
            # Sort by confidence
            results.sort(key=lambda x: x[1], reverse=True)
            best_url, best_confidence = results[0]
            
            # Determine method for caching
            method_name = 'domain_pattern'
            if google_result and results[0] == google_result:
                method_name = 'google'
            elif ddg_result and results[0] == ddg_result:
                method_name = 'duckduckgo'
            
            # For search engine results, trust them more (lower threshold)
            # For domain pattern guesses, require higher confidence
            if method_name in ['google', 'duckduckgo']:
                min_confidence = 0.70  # Trust search engines
            else:
                min_confidence = 0.80  # Domain patterns are guesses
            
            if best_confidence >= min_confidence:
                # Cache result
                self._websites[cache_key] = {
                    'url': best_url,
                    'confidence': best_confidence,
                    'method': method_name
                }
                self._save_cache(self.websites_cache, self._websites)
                
                return (best_url, best_confidence)
            else:
                logger.info(f"Best result confidence {best_confidence:.2f} below threshold {min_confidence}, rejecting: {best_url}")
                return None
        
        # Cache as not found
        self._websites[cache_key] = {'url': None, 'confidence': 0}
        self._save_cache(self.websites_cache, self._websites)
        
        return None
    
    def _search_duckduckgo(self, company_name: str, city: Optional[str] = None,
                          state: Optional[str] = None) -> Optional[Tuple[str, float]]:
        """
        Search for company website using DuckDuckGo.
        
        Returns:
            Tuple of (URL, confidence) or None
        """
        try:
            # Build search query
            query_parts = [company_name]
            if city:
                query_parts.append(city)
            if state:
                query_parts.append(state)
            query = " ".join(query_parts) + " official website"
            
            # Use DuckDuckGo HTML search (no API needed)
            url = "https://html.duckduckgo.com/html/"
            params = {'q': query}
            
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            # Parse HTML for results (simple regex for now)
            # In production, use BeautifulSoup
            if not BEAUTIFULSOUP_AVAILABLE:
                logger.warning("BeautifulSoup not available, skipping HTML parsing")
                return None
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find result links
            results = soup.find_all('a', class_='result__a', limit=5)
            
            for result in results:
                url = result.get('href', '')
                if not url:
                    continue
                
                # Check if URL is likely the company website
                if not self._is_likely_company_website(url, company_name):
                    logger.debug(f"Rejected URL (not likely company website): {url}")
                    continue
                
                confidence = self._calculate_confidence(url, company_name, city, state)
                if confidence >= 0.80:  # Require higher confidence (0.80 minimum)
                    logger.info(f"DuckDuckGo found: {url} (confidence: {confidence:.2f})")
                    return (url, confidence)
                else:
                    logger.debug(f"Rejected URL (low confidence {confidence:.2f}): {url}")
            
            time.sleep(1)  # Rate limiting
            return None
            
        except Exception as e:
            logger.warning(f"Error searching DuckDuckGo for {company_name}: {e}")
            return None
    
    def _search_google_custom(self, company_name: str, city: Optional[str] = None,
                             state: Optional[str] = None) -> Optional[Tuple[str, float]]:
        """
        Search for company website using Google Custom Search API (fallback).
        
        Returns:
            Tuple of (URL, confidence) or None
        """
        api_key = os.getenv("GOOGLE_CUSTOM_SEARCH_API_KEY")
        search_engine_id = os.getenv("GOOGLE_CUSTOM_SEARCH_ENGINE_ID", "0206fd2849c6e48e5")
        
        if not api_key:
            logger.debug("Google Custom Search API key not configured (using DuckDuckGo only)")
            return None
        
        try:
            # Build search query
            query_parts = [company_name]
            if city:
                query_parts.append(city)
            if state:
                query_parts.append(state)
            query = " ".join(query_parts) + " official website"
            
            # Call Google Custom Search API
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': api_key,
                'cx': search_engine_id,
                'q': query,
                'num': 5  # Get top 5 results
            }
            
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Process results - require higher confidence for Google results
            if 'items' in data and len(data['items']) > 0:
                best_result = None
                best_confidence = 0.0
                
                for idx, item in enumerate(data['items']):
                    result_url = item.get('link', '')
                    is_first_result = (idx == 0)
                    
                    # For first Google result, be more lenient - trust Google's ranking
                    if is_first_result:
                        # Quick exclusion check only (no strict matching required)
                        domain = urlparse(result_url).netloc.lower()
                        exclude_terms = ['facebook', 'linkedin', 'twitter', 'instagram', 'youtube', 
                                        'google', 'bing', 'wikipedia', 'volunteer', 'university', 'edu']
                        if any(ex in domain for ex in exclude_terms):
                            logger.debug(f"Rejected first Google result (exclude term): {result_url}")
                            continue
                        # Trust Google's first result - give it high confidence
                        confidence = 0.85
                        logger.debug(f"Trusting first Google result: {result_url} (confidence: {confidence:.2f})")
                    elif result_url and self._is_likely_company_website(result_url, company_name):
                        confidence = self._calculate_confidence(result_url, company_name, city, state)
                        # Google results are generally more reliable, boost confidence
                        confidence = min(confidence + 0.1, 1.0)
                    else:
                        # Not first result and doesn't pass strict check, skip
                        continue
                    
                    # Track best result
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_result = result_url
                
                # Trust Google's ranking - if it's in the results, especially first result, accept it
                # Lower threshold to 0.70 since Google does good matching
                if best_result and best_confidence >= 0.70:
                    logger.info(f"Google Custom Search found: {best_result} (confidence: {best_confidence:.2f})")
                    return (best_result, best_confidence)
                elif best_result:
                    logger.info(f"Google Custom Search found result but confidence too low: {best_result} (confidence: {best_confidence:.2f})")
            
            logger.info("Google Custom Search returned results but none matched company")
            return None
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                logger.warning(f"Google Custom Search API error (403): Check API key and billing")
            else:
                logger.warning(f"Google Custom Search API error: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error searching Google Custom Search for {company_name}: {e}")
            return None
    
    def _try_domain_patterns(self, company_name: str) -> Optional[Tuple[str, float]]:
        """
        Try common domain name patterns.
        
        Returns:
            Tuple of (URL, confidence) or None
        """
        # Clean company name for domain
        domain_base = re.sub(r'[^a-z0-9]', '', company_name.lower())
        domain_base = re.sub(r'\s+', '', domain_base)
        
        # Common patterns
        patterns = [
            f"https://www.{domain_base}.org",
            f"https://{domain_base}.org",
            f"https://www.{domain_base}.com",
            f"https://{domain_base}.com",
            f"https://www.{domain_base}.net",
        ]
        
        for url in patterns:
            if self._check_url_exists(url):
                return (url, 0.6)  # Medium confidence for pattern match
        
        return None
    
    def _check_url_exists(self, url: str) -> bool:
        """Check if URL exists and is accessible."""
        try:
            response = requests.head(url, headers=self.headers, timeout=5, allow_redirects=True)
            return response.status_code == 200
        except:
            return False
    
    def _is_likely_company_website(self, url: str, company_name: str) -> bool:
        """Check if URL is likely the company's official website."""
        domain = urlparse(url).netloc.lower()
        path = urlparse(url).path.lower()
        name_clean = re.sub(r'[^a-z0-9]', '', company_name.lower())
        
        # FIRST: Exclude common non-company sites - be very strict (check this FIRST)
        # Check for exclude terms in domain (case-insensitive)
        exclude_terms = [
            'facebook', 'linkedin', 'twitter', 'instagram', 'youtube', 
            'google', 'bing', 'wikipedia', 'yellowpages', 
            'volunteer', 'volunteermatch', 'volunteerhub', 'volunteers',
            'university', 'edu', 'college', 'school', 'campus',
            'usm.edu', 'usm', 'nsudemons', 'ncbi', 'pmc.ncbi',
            'usda.gov', 'ncdhhs.gov', 'dshs.wa.gov', 'calhfa.ca.gov',
        ]
        
        # Check if domain contains any exclude terms - reject immediately
        domain_lower = domain.lower()
        if any(ex.lower() in domain_lower for ex in exclude_terms):
            logger.debug(f"Rejected domain (contains exclude term): {domain}")
            return False
        
        # Also check the full URL for exclude terms
        url_lower = url.lower()
        if any(ex.lower() in url_lower for ex in ['/volunteer/', '/agency/', '/sports/', '/articles/']):
            logger.debug(f"Rejected URL (contains exclude path): {url}")
            return False
        
        # Exclude if it's clearly a university/educational institution subdomain
        domain_parts = domain.split('.')
        if len(domain_parts) >= 3:
            # Check if it's a subdomain of .edu or university site
            if 'edu' in domain_parts or any(uni_term in domain for uni_term in ['university', 'college', 'school', 'campus']):
                return False
        
        # Exclude PDFs and non-HTML content
        if url.lower().endswith(('.pdf', '.doc', '.docx', '.xls', '.xlsx')):
            return False
        
        # Exclude paths that suggest it's not the main site
        exclude_paths = ['/agency/', '/volunteer/', '/sports/', '/articles/', '/detail/', '/divisions/']
        if any(exclude_path in path for exclude_path in exclude_paths):
            return False
        
        # Exclude government sites unless they're clearly the organization's own site
        if '.gov' in domain:
            # Only allow if domain clearly matches company name
            if name_clean not in domain:
                return False
        
        # NOW check if domain contains company name or key keywords (only if it passed exclusion checks)
        # Extract key words from company name (remove common words)
        common_words = ['the', 'for', 'of', 'and', 'inc', 'llc', 'corp', 'ltd', 'association', 
                       'associates', 'services', 'service', 'community', 'development', 'corporation',
                       'cdc', 'nhs', 'housing', 'economic', 'resources', 'education', 'neighborhood']
        name_words = [w for w in re.findall(r'\b\w+\b', company_name.lower()) 
                     if w not in common_words and len(w) > 2]
        name_keywords = ''.join(name_words[:3])  # Use first 3 meaningful words
        
        # Extract potential acronyms/abbreviations (capital letters or first letters of words)
        # Example: "Bronx Neighborhood Housing Services CDC Inc" -> "BNHSCDC" or "BNHS"
        acronym_pattern = re.findall(r'\b[A-Z][a-z]*', company_name)
        if acronym_pattern:
            # Try full acronym
            full_acronym = ''.join([w[0].upper() for w in acronym_pattern if len(w) > 0])
            # Try shortened acronym (first 2-4 words)
            short_acronym = ''.join([w[0].upper() for w in acronym_pattern[:4] if len(w) > 0])
            # Try common abbreviation patterns (e.g., "Bronx NHS" from "Bronx Neighborhood Housing Services")
            if len(acronym_pattern) >= 2:
                location_acronym = acronym_pattern[0] + ' ' + ''.join([w[0].upper() for w in acronym_pattern[1:4]])
                location_acronym_clean = re.sub(r'[^a-z0-9]', '', location_acronym.lower())
        else:
            full_acronym = ''
            short_acronym = ''
            location_acronym_clean = ''
        
        # Check multiple matching strategies
        # 1. Full cleaned name match
        if name_clean in domain:
            return True
        
        # 2. Key keywords match
        if name_keywords and name_keywords in domain:
            return True
        
        # 3. Acronym matches (e.g., "bronxnhs" matches "Bronx Neighborhood Housing Services")
        if full_acronym and full_acronym.lower() in domain:
            return True
        if short_acronym and short_acronym.lower() in domain:
            return True
        if location_acronym_clean and location_acronym_clean in domain:
            return True
        
        # 4. Check if domain contains significant words from company name
        # (at least 2 meaningful words that are 4+ characters)
        significant_words = [w for w in name_words if len(w) >= 4]
        if len(significant_words) >= 2:
            matches = sum(1 for word in significant_words[:3] if word in domain)
            if matches >= 2:  # At least 2 significant words match
                return True
        
        # 5. Handle "E for All" -> "eforall" pattern (first letter + "for" + last word)
        # Example: "Entrepreneurship for All" -> "eforall"
        words = re.findall(r'\b\w+\b', company_name.lower())
        if len(words) >= 3 and 'for' in words:
            # Find "for" in the name
            for_idx = words.index('for')
            if for_idx > 0 and for_idx < len(words) - 1:
                # Get first letter of first word + "for" + last word
                first_letter = words[0][0] if words[0] else ''
                last_word = words[-1] if words[-1] else ''
                pattern = f"{first_letter}for{last_word}"
                if pattern in domain:
                    return True
        
        # 6. Handle other abbreviation patterns: first letter of each significant word
        # Example: "Entrepreneurship for All" -> "efa" (but domain might be "eforall")
        if len(words) >= 2:
            # Try first letter of each word
            first_letters = ''.join([w[0] for w in words if len(w) > 0])
            if len(first_letters) >= 2 and first_letters in domain:
                return True
            # Try first letter + "for" + first letter of last word
            if 'for' in words and len(words) >= 3:
                first_letter_first = words[0][0] if words[0] else ''
                first_letter_last = words[-1][0] if words[-1] else ''
                pattern2 = f"{first_letter_first}for{first_letter_last}"
                if pattern2 in domain:
                    return True
        
        # 5. Special case: Check for common nonprofit patterns
        # e.g., "bronxnhs" for "Bronx Neighborhood Housing Services"
        # Extract location + first letters of key words
        if len(name_words) >= 2:
            # Try location + first letters pattern
            location = name_words[0] if name_words else ''
            first_letters = ''.join([w[0] for w in name_words[1:4] if len(w) > 0])
            pattern_match = location + first_letters
            if pattern_match and pattern_match in domain:
                return True
        
        # If no clear match, reject
        logger.debug(f"Rejected domain (no name/keyword/acronym match): {domain} for {company_name}")
        return False
    
    def _calculate_confidence(self, url: str, company_name: str, 
                             city: Optional[str] = None, state: Optional[str] = None) -> float:
        """Calculate confidence score for URL match."""
        confidence = 0.3  # Lower base confidence - require stronger matches
        
        domain = urlparse(url).netloc.lower()
        name_clean = re.sub(r'[^a-z0-9]', '', company_name.lower())
        
        # Extract key words from company name (same logic as _is_likely_company_website)
        common_words = ['the', 'for', 'of', 'and', 'inc', 'llc', 'corp', 'ltd', 'association', 
                       'associates', 'services', 'service', 'community', 'development', 'corporation',
                       'cdc', 'nhs', 'housing', 'economic', 'resources', 'education', 'neighborhood']
        name_words = [w for w in re.findall(r'\b\w+\b', company_name.lower()) 
                     if w not in common_words and len(w) > 2]
        name_keywords = ''.join(name_words[:3])
        
        # Extract acronyms (same as _is_likely_company_website)
        acronym_pattern = re.findall(r'\b[A-Z][a-z]*', company_name)
        if acronym_pattern:
            full_acronym = ''.join([w[0].upper() for w in acronym_pattern if len(w) > 0])
            short_acronym = ''.join([w[0].upper() for w in acronym_pattern[:4] if len(w) > 0])
            if len(acronym_pattern) >= 2:
                location_acronym = acronym_pattern[0] + ' ' + ''.join([w[0].upper() for w in acronym_pattern[1:4]])
                location_acronym_clean = re.sub(r'[^a-z0-9]', '', location_acronym.lower())
            else:
                location_acronym_clean = ''
        else:
            full_acronym = ''
            short_acronym = ''
            location_acronym_clean = ''
        
        # Strong boost if domain contains full company name (cleaned)
        if name_clean in domain:
            confidence += 0.4
        
        # Strong boost if domain contains acronym (e.g., "bronxnhs" for "Bronx Neighborhood Housing Services")
        # Acronyms are very common for nonprofits, so give them high confidence
        if full_acronym and full_acronym.lower() in domain:
            confidence += 0.45
        elif short_acronym and short_acronym.lower() in domain:
            confidence += 0.4
        elif location_acronym_clean and location_acronym_clean in domain:
            confidence += 0.4
        
        # Handle "E for All" -> "eforall" pattern (first letter + "for" + last word)
        words = re.findall(r'\b\w+\b', company_name.lower())
        if len(words) >= 3 and 'for' in words:
            for_idx = words.index('for')
            if for_idx > 0 and for_idx < len(words) - 1:
                # Get first letter of first word + "for" + last word
                first_letter = words[0][0] if words[0] else ''
                last_word = words[-1] if words[-1] else ''
                pattern = f"{first_letter}for{last_word}"
                if pattern in domain:
                    confidence += 0.45  # High confidence for this pattern
                # Also try first letter + "for" + first letter of last word
                first_letter_last = words[-1][0] if words[-1] else ''
                pattern2 = f"{first_letter}for{first_letter_last}"
                if pattern2 in domain:
                    confidence += 0.4
        
        # Medium boost if domain contains key keywords
        if name_keywords and name_keywords in domain:
            confidence += 0.2
        
        # Check if multiple meaningful words from company name are in domain
        elif name_words:
            significant_words = [w for w in name_words if len(w) >= 4]
            matches = sum(1 for word in significant_words[:3] if word in domain)
            if matches >= 2:  # At least 2 significant words match
                confidence += 0.15
            elif matches >= 1:
                confidence += 0.1
        
        # Boost if .org (common for nonprofits)
        if '.org' in domain:
            confidence += 0.1
        
        # Boost if HTTPS
        if url.startswith('https://'):
            confidence += 0.05
        
        # Heavy penalty if it's a subdomain of a large site (likely not the main site)
        if domain.count('.') > 2:  # e.g., volunteer.usm.edu
            confidence -= 0.4  # Much heavier penalty
        
        # Heavy penalty if path is too long (likely a sub-page, not main site)
        path = urlparse(url).path
        path_depth = len([p for p in path.split('/') if p])  # Count non-empty path segments
        if path_depth > 3:  # e.g., /divisions/social-services/child-welfare-services/...
            confidence -= 0.3  # Much heavier penalty
        
        # Penalize if URL contains suspicious patterns
        suspicious_patterns = ['/agency/', '/volunteer/', '/sports/', '/articles/', '/detail/']
        if any(pattern in url.lower() for pattern in suspicious_patterns):
            confidence -= 0.3
        
        return max(0.0, min(confidence, 1.0))  # Ensure between 0 and 1
    
    def extract_contact_info(self, url: str) -> Dict[str, List[str]]:
        """
        Extract contact information from website.
        Uses Claude API for intelligent HTML parsing if available, falls back to regex patterns.
        
        Args:
            url: Website URL
            
        Returns:
            Dictionary with emails, phones, addresses
        """
        # Check cache
        if url in self._contacts:
            return self._contacts[url]
        
        # Try Claude API first if available
        try:
            from apps.memberview.utils.claude_html_parser import ClaudeHTMLParser
            claude_parser = ClaudeHTMLParser()
            
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                contacts = claude_parser.extract_contacts_from_html(response.text, url)
                if contacts and (contacts.get('emails') or contacts.get('phones') or contacts.get('addresses')):
                    # Cache and return
                    self._contacts[url] = contacts
                    self._save_cache(self.contacts_cache, self._contacts)
                    logger.info(f"Claude extracted contacts from {url}")
                    return contacts
        except (ImportError, ValueError) as e:
            logger.debug(f"Claude parser not available, using fallback: {e}")
        except Exception as e:
            logger.debug(f"Error using Claude parser: {e}")
        
        # Fallback to regex-based extraction
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            if not BEAUTIFULSOUP_AVAILABLE:
                logger.warning("BeautifulSoup not available, skipping HTML parsing")
                return {'emails': [], 'phones': [], 'addresses': []}
            soup = BeautifulSoup(response.text, 'html.parser')
            text = soup.get_text()
            
            contacts = {
                'emails': self._extract_emails(text, url),
                'phones': self._extract_phones(text),
                'addresses': self._extract_addresses(text)
            }
            
            # Cache result
            self._contacts[url] = contacts
            self._save_cache(self.contacts_cache, self._contacts)
            
            time.sleep(1)  # Rate limiting
            return contacts
            
        except Exception as e:
            logger.warning(f"Error extracting contacts from {url}: {e}")
            return {'emails': [], 'phones': [], 'addresses': []}
    
    def _extract_emails(self, text: str, base_url: str) -> List[str]:
        """Extract email addresses from text."""
        # Email regex pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        
        # Filter out common non-contact emails
        exclude = ['noreply', 'no-reply', 'donotreply', 'example', 'test']
        emails = [e for e in emails if not any(ex in e.lower() for ex in exclude)]
        
        # Also check mailto links
        try:
            if not BEAUTIFULSOUP_AVAILABLE:
                return emails
            response = requests.get(base_url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            mailto_links = soup.find_all('a', href=re.compile(r'^mailto:'))
            for link in mailto_links:
                email = link.get('href', '').replace('mailto:', '').split('?')[0]
                if email and email not in emails:
                    emails.append(email)
        except:
            pass
        
        return list(set(emails))[:10]  # Limit to 10 unique emails
    
    def _extract_phones(self, text: str) -> List[str]:
        """Extract phone numbers from text."""
        # Common phone patterns
        patterns = [
            r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # (123) 456-7890
            r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',        # 123-456-7890
            r'\+1[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',  # +1 123-456-7890
        ]
        
        phones = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            phones.extend(matches)
        
        # Clean and deduplicate
        phones = [re.sub(r'[^\d+]', '', p) for p in phones]
        phones = [p for p in phones if len(p) >= 10]  # Valid US phone length
        
        return list(set(phones))[:5]  # Limit to 5 unique phones
    
    def _extract_addresses(self, text: str) -> List[str]:
        """Extract addresses from text (basic pattern matching)."""
        # Look for common address patterns
        # This is basic - could be improved with NLP
        address_pattern = r'\d+\s+[A-Za-z0-9\s,]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Circle|Cir)[\s,]+[A-Za-z\s,]+(?:[A-Z]{2})?\s+\d{5}'
        addresses = re.findall(address_pattern, text, re.IGNORECASE)
        
        return addresses[:3]  # Limit to 3 addresses
    
    def _detect_cms(self, html: str, url: str) -> Optional[str]:
        """
        Detect the CMS/platform used by the website.
        
        Args:
            html: HTML content
            url: Website URL
            
        Returns:
            CMS name ('wordpress', 'squarespace', 'drupal', etc.) or None
        """
        html_lower = html.lower()
        url_lower = url.lower()
        
        for cms, patterns in self.cms_patterns.items():
            for pattern in patterns:
                if re.search(pattern, html_lower, re.IGNORECASE) or re.search(pattern, url_lower, re.IGNORECASE):
                    logger.debug(f"Detected CMS: {cms}")
                    return cms
        
        return None
    
    def _discover_staff_pages(self, base_url: str, html: str, detected_cms: Optional[str] = None) -> List[str]:
        """
        Discover staff/team page URLs using multiple strategies:
        1. CMS-specific URL patterns
        2. Navigation link analysis
        3. Common path patterns
        
        Args:
            base_url: Base website URL
            html: HTML content from homepage
            detected_cms: Detected CMS platform (optional)
            
        Returns:
            List of potential staff page URLs
        """
        if not BEAUTIFULSOUP_AVAILABLE:
            logger.warning("BeautifulSoup not available, skipping staff page discovery")
            return []
        soup = BeautifulSoup(html, 'html.parser')
        
        discovered_urls: Set[str] = set()
        base_url_clean = base_url.rstrip('/')
        
        # Strategy 1: Use CMS-specific patterns
        if detected_cms and detected_cms in self.platform_url_patterns:
            patterns = self.platform_url_patterns[detected_cms]
        else:
            patterns = self.platform_url_patterns['generic']
        
        for pattern in patterns:
            test_url = base_url_clean + pattern
            discovered_urls.add(test_url)
        
        # Strategy 2: Find navigation links that mention staff/team/about
        nav_keywords = [
            'staff', 'team', 'about', 'leadership', 'board', 'directors',
            'people', 'who we are', 'meet', 'our team', 'our staff'
        ]
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            link_text = link.get_text().lower().strip()
            
            # Skip external links, mailto, javascript, etc.
            if any(href.startswith(prefix) for prefix in ['http://', 'https://', 'mailto:', 'javascript:', '#']):
                # Only include external links if they're on the same domain
                if href.startswith('http'):
                    parsed_href = urlparse(href)
                    parsed_base = urlparse(base_url)
                    if parsed_href.netloc != parsed_base.netloc:
                        continue
                elif href.startswith(('mailto:', 'javascript:', '#')):
                    continue
            
            # Check if link text or href contains keywords
            href_lower = href.lower()
            if any(keyword in href_lower or keyword in link_text for keyword in nav_keywords):
                full_url = urljoin(base_url, href)
                # Only add if it's on the same domain
                parsed_full = urlparse(full_url)
                parsed_base = urlparse(base_url)
                if parsed_full.netloc == parsed_base.netloc or not parsed_full.netloc:
                    discovered_urls.add(full_url)
        
        # Strategy 3: Look for common menu structures (WordPress, etc.)
        # Find nav menus, main menus, etc.
        for nav in soup.find_all(['nav', 'ul'], class_=re.compile(r'nav|menu', re.I)):
            for link in nav.find_all('a', href=True):
                href = link.get('href', '')
                link_text = link.get_text().lower().strip()
                
                if any(keyword in href.lower() or keyword in link_text for keyword in nav_keywords):
                    full_url = urljoin(base_url, href)
                    parsed_full = urlparse(full_url)
                    parsed_base = urlparse(base_url)
                    if parsed_full.netloc == parsed_base.netloc or not parsed_full.netloc:
                        discovered_urls.add(full_url)
        
        # Strategy 4: Try nested paths (like /who-we-are/staff-directory/)
        nested_patterns = [
            '/who-we-are/staff/', '/who-we-are/staff-directory/',
            '/who-we-are/team/', '/about/staff/', '/about/staff-directory/',
            '/about/team/', '/about-us/staff/', '/about-us/staff-directory/',
            '/about-us/team/', '/about-us/meet-our-team/',
            '/people/staff/', '/people/team/', '/leadership/staff/'
        ]
        
        for pattern in nested_patterns:
            discovered_urls.add(base_url_clean + pattern)
        
        # Convert to list and limit to reasonable number
        url_list = list(discovered_urls)
        logger.info(f"Discovered {len(url_list)} potential staff pages")
        
        return url_list[:20]  # Limit to 20 URLs to check
    
    def extract_staff_info(self, url: str) -> List[Dict[str, str]]:
        """
        Extract staff/leadership information from website.
        Uses Claude API for intelligent HTML parsing if available, falls back to regex patterns.
        
        Args:
            url: Website URL
            
        Returns:
            List of staff members with name, title, email, phone
        """
        # Check cache
        if url in self._staff:
            return self._staff[url]
        
        # Get homepage HTML to detect CMS and discover pages
        try:
            homepage_response = requests.get(url, headers=self.headers, timeout=10)
            homepage_response.raise_for_status()
            homepage_html = homepage_response.text
            
            # Detect CMS
            detected_cms = self._detect_cms(homepage_html, url)
            logger.info(f"Detected CMS for {url}: {detected_cms or 'unknown'}")
            
            # Discover staff pages using intelligent discovery
            discovered_pages = self._discover_staff_pages(url, homepage_html, detected_cms)
            
        except Exception as e:
            logger.warning(f"Error fetching homepage for {url}: {e}")
            discovered_pages = []
            homepage_html = ""
            detected_cms = None
        
        # Try Claude API first if available
        try:
            from apps.memberview.utils.claude_html_parser import ClaudeHTMLParser
            claude_parser = ClaudeHTMLParser()
            
            # Check homepage first, then discovered pages
            pages_to_check = [url] + discovered_pages[:15]  # Check homepage + up to 15 discovered pages
            
            logger.info(f"Checking {len(pages_to_check)} pages with Claude: {pages_to_check[:3]}...")
            
            for page_url in pages_to_check:
                try:
                    response = requests.get(page_url, headers=self.headers, timeout=10)
                    if response.status_code == 200:
                        staff = claude_parser.extract_staff_from_html(response.text, page_url)
                        if staff:
                            # Cache and return
                            self._staff[url] = staff
                            self._save_cache(self.staff_cache, self._staff)
                            logger.info(f"Claude extracted {len(staff)} staff members from {page_url}")
                            return staff
                except Exception as e:
                    logger.debug(f"Error checking {page_url} with Claude: {e}")
                    continue
        except (ImportError, ValueError) as e:
            logger.debug(f"Claude parser not available, using fallback: {e}")
        except Exception as e:
            logger.debug(f"Error using Claude parser: {e}")
        
        # Fallback to regex-based extraction
        try:
            # Use discovered pages from CMS detection, or fallback to basic discovery
            if not discovered_pages:
                # Basic fallback discovery
                response = requests.get(url, headers=self.headers, timeout=10)
                response.raise_for_status()
                if not BEAUTIFULSOUP_AVAILABLE:
                    return []  # Can't parse without BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Simple link discovery
                staff_links = []
                for link in soup.find_all('a', href=True):
                    href = link.get('href', '').lower()
                    text = link.get_text().lower()
                    if any(keyword in href or keyword in text for keyword in 
                           ['team', 'staff', 'about', 'leadership', 'board', 'directors']):
                        full_url = urljoin(url, link['href'])
                        if full_url not in staff_links:
                            staff_links.append(full_url)
                
                base_url = url.rstrip('/')
                common_paths = [
                    '/about-us', '/about', '/team', '/staff', '/leadership', 
                    '/board', '/board-of-directors', '/our-team', '/our-staff',
                    '/people', '/who-we-are', '/meet-our-team',
                    '/who-we-are/staff-directory/', '/about/staff-directory/'
                ]
                for path in common_paths:
                    test_url = base_url + path
                    if test_url not in staff_links:
                        staff_links.append(test_url)
                
                pages_to_check = [url] + staff_links[:10]
            else:
                pages_to_check = [url] + discovered_pages[:15]
            
            staff = []
            
            logger.info(f"Checking {len(pages_to_check)} pages for staff info (fallback method): {pages_to_check[:3]}...")
            
            for page_url in pages_to_check:
                try:
                    page_response = requests.get(page_url, headers=self.headers, timeout=10)
                    if page_response.status_code != 200:
                        logger.debug(f"Skipping {page_url} - status {page_response.status_code}")
                        continue
                    page_soup = BeautifulSoup(page_response.text, 'html.parser')
                    logger.debug(f"Processing {page_url} - found {len(page_soup.find_all())} HTML elements")
                    
                    # Look for staff in structured HTML (headings, list items, divs)
                    # Method 1: Find section with "Staff" or "Team" heading, then extract names/titles
                    all_headings = page_soup.find_all(['h1', 'h2', 'h3', 'h4'])
                    for heading in all_headings:
                        heading_text = heading.get_text().strip().lower()
                        # Check if this is a section heading for staff/team
                        if any(keyword in heading_text for keyword in 
                               ['staff', 'team', 'leadership', 'board', 'directors', 'officers']):
                            # Find all following headings that look like names
                            current = heading.find_next_sibling()
                            while current:
                                # Check if current element is a heading that looks like a name
                                if current.name in ['h2', 'h3', 'h4', 'h5', 'h6']:
                                    name_text = current.get_text().strip()
                                    # Check if it looks like a name (2-3 capitalized words)
                                    if re.match(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}$', name_text):
                                        # Get title from next sibling or next text node
                                        title_text = None
                                        next_sib = current.find_next_sibling()
                                        if next_sib:
                                            title_text = next_sib.get_text().strip()
                                        # Also check if title is in same parent or next element
                                        if not title_text or len(title_text) > 100:
                                            # Try getting text from parent or next element
                                            parent = current.find_parent()
                                            if parent:
                                                # Get all text after the heading
                                                full_text = parent.get_text()
                                                # Extract text after name
                                                name_pos = full_text.find(name_text)
                                                if name_pos >= 0:
                                                    after_name = full_text[name_pos + len(name_text):].strip()
                                                    # Get first line or sentence
                                                    title_text = after_name.split('\n')[0].split('.')[0].strip()
                                        
                                        if title_text and any(t in title_text.lower() for t in 
                                                              ['ceo', 'president', 'director', 'executive', 'manager', 'officer', 
                                                               'chair', 'board', 'coordinator', 'vista', 'secretary', 'treasurer', 
                                                               'vice', 'chief', 'administrative', 'development', 'resource']):
                                            staff.append({
                                                'name': name_text.strip(),
                                                'title': title_text.strip(),
                                                'source_url': page_url
                                            })
                                
                                # Move to next sibling
                                current = current.find_next_sibling()
                                # Stop if we hit another major section heading
                                if current and current.name in ['h1', 'h2']:
                                    next_heading_text = current.get_text().strip().lower()
                                    if any(kw in next_heading_text for kw in ['support', 'contact', 'learn', 'donate', 'volunteer']):
                                        break
                    
                    # Method 1b: Look for any heading that looks like a name, check if followed by title
                    name_headings = page_soup.find_all(['h2', 'h3', 'h4', 'h5', 'h6'])
                    for name_heading in name_headings:
                        name_text = name_heading.get_text().strip()
                        # Check if it looks like a name (2-3 capitalized words, not too long)
                        if re.match(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}$', name_text) and len(name_text) < 50:
                            # Get next sibling for title
                            next_elem = name_heading.find_next_sibling()
                            if next_elem:
                                title_text = next_elem.get_text().strip()
                                # Also check parent's text for title
                                if not title_text or len(title_text) > 100:
                                    parent = name_heading.find_parent()
                                    if parent:
                                        full_text = parent.get_text()
                                        name_pos = full_text.find(name_text)
                                        if name_pos >= 0:
                                            after_name = full_text[name_pos + len(name_text):].strip()
                                            title_text = after_name.split('\n')[0].split('.')[0].strip()[:100]
                                
                                if title_text and any(t in title_text.lower() for t in 
                                                      ['ceo', 'president', 'director', 'executive', 'manager', 'officer', 
                                                       'chair', 'board', 'coordinator', 'vista', 'secretary', 'treasurer']):
                                    staff.append({
                                        'name': name_text.strip(),
                                        'title': title_text.strip(),
                                        'source_url': page_url
                                    })
                    
                    # Method 2: Look for list items with staff info
                    lists = page_soup.find_all(['ul', 'ol', 'dl'])
                    for list_elem in lists:
                        items = list_elem.find_all('li', limit=30)
                        for item in items:
                            text = item.get_text().strip()
                            # Pattern: "Name - Title" or "Name, Title"
                            name_title_pattern = r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)[\s,–-]+\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+[A-Z][a-z]+)*)'
                            match = re.match(name_title_pattern, text)
                            if match:
                                name, title = match.groups()
                                if any(t in title.lower() for t in ['ceo', 'president', 'director', 'executive', 
                                                                     'manager', 'officer', 'chair', 'board', 'coordinator', 'vista', 'secretary', 'treasurer']):
                                    staff.append({
                                        'name': name.strip(),
                                        'title': title.strip(),
                                        'source_url': page_url
                                    })
                    
                    # Method 3: Text-based pattern matching (more flexible)
                    text = page_soup.get_text()
                    
                    # Pattern 1: "Name\nTitle" - Look for capitalized names followed by titles on next line
                    lines = [l.strip() for l in text.split('\n') if l.strip()]  # Remove empty lines
                    for i, line in enumerate(lines):
                        # Check if line looks like a name (2-3 capitalized words, reasonable length)
                        if re.match(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}$', line) and 5 < len(line) < 50:
                            # Check next 1-3 lines for title
                            for offset in range(1, 4):
                                if i + offset < len(lines):
                                    next_line = lines[i + offset].strip()
                                    # Check if it looks like a title (contains common title words)
                                    if next_line and any(t in next_line.lower() for t in 
                                                          ['ceo', 'president', 'director', 'executive', 'manager', 'officer', 
                                                           'chair', 'board', 'coordinator', 'vista', 'secretary', 'treasurer',
                                                           'administrative', 'development', 'resource', 'strategic', 'partnerships',
                                                           'housing', 'youth', 'community', 'marketing', 'engagement', 'chief']):
                                        # Make sure it's not too long (likely not a title if > 50 chars)
                                        if len(next_line) < 80:
                                            staff.append({
                                                'name': line.strip(),
                                                'title': next_line.strip(),
                                                'source_url': page_url
                                            })
                                            break  # Found title, move to next name
                    
                    # Pattern 2: "Name - Title" or "Name, Title" in same line
                    name_title_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)[\s,–-]+\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+[A-Z][a-z]+)*)'
                    matches = re.findall(name_title_pattern, text)
                    
                    for name, title in matches[:15]:  # Limit to 15 per page
                        # Filter for common titles
                        if any(t in title.lower() for t in ['ceo', 'president', 'director', 'executive', 
                                                             'manager', 'officer', 'chair', 'board', 'coordinator', 'vista', 
                                                             'secretary', 'treasurer', 'administrative', 'development', 
                                                             'resource', 'strategic', 'partnerships', 'housing', 'youth', 
                                                             'community', 'marketing', 'engagement']):
                            staff.append({
                                'name': name.strip(),
                                'title': title.strip(),
                                'source_url': page_url
                            })
                    
                    time.sleep(0.5)  # Rate limiting between pages
                    
                except Exception as e:
                    logger.warning(f"Error processing staff page {page_url}: {e}")
                    continue
            
            # Deduplicate
            seen = set()
            unique_staff = []
            for person in staff:
                key = (person['name'].lower(), person['title'].lower())
                if key not in seen:
                    seen.add(key)
                    unique_staff.append(person)
            
            # Cache result
            self._staff[url] = unique_staff[:20]  # Limit to 20 staff members
            self._save_cache(self.staff_cache, self._staff)
            
            return unique_staff[:20]
            
        except Exception as e:
            logger.warning(f"Error extracting staff from {url}: {e}")
            return []
    
    def extract_organization_info(self, url: str) -> Dict[str, Any]:
        """
        Extract comprehensive organization information from website.
        Includes: funders/partners, major areas of work, affiliations, etc.
        
        Args:
            url: Website URL
            
        Returns:
            Dictionary with organization information
        """
        # Check cache
        if url in self._org_info:
            return self._org_info[url]
        
        # Try Claude API first if available
        try:
            from apps.memberview.utils.claude_html_parser import ClaudeHTMLParser
            claude_parser = ClaudeHTMLParser()
            
            # Get homepage and key pages
            pages_to_check = [url]
            
            # Add common info pages
            base_url = url.rstrip('/')
            info_pages = [
                '/about', '/about-us', '/partners', '/funders', '/supporters',
                '/sponsors', '/programs', '/services', '/what-we-do', '/our-work',
                '/mission', '/vision', '/who-we-are'
            ]
            
            for page_path in info_pages:
                pages_to_check.append(base_url + page_path)
            
            # Try each page
            for page_url in pages_to_check[:5]:  # Limit to 5 pages
                try:
                    response = requests.get(page_url, headers=self.headers, timeout=10)
                    if response.status_code == 200:
                        org_info = claude_parser.extract_organization_info(response.text, page_url)
                        # If we got meaningful data, use it
                        if (org_info.get('funders_partners') or 
                            org_info.get('major_areas_of_work') or 
                            org_info.get('affiliations') or
                            org_info.get('mission')):
                            # Cache and return
                            self._org_info[url] = org_info
                            # Save cache
                            org_info_cache_file = self.cache_dir / "org_info_cache.json"
                            self._save_cache(org_info_cache_file, self._org_info)
                            logger.info(f"Claude extracted org info from {page_url}")
                            return org_info
                except Exception as e:
                    logger.debug(f"Error checking {page_url} for org info: {e}")
                    continue
        except (ImportError, ValueError) as e:
            logger.debug(f"Claude parser not available, skipping org info extraction: {e}")
        except Exception as e:
            logger.debug(f"Error using Claude parser for org info: {e}")
        
        # Return empty structure if nothing found
        empty_info = {
            'funders_partners': [],
            'major_areas_of_work': [],
            'affiliations': [],
            'contact_info': {'emails': [], 'phones': [], 'addresses': []},
            'mission': None,
            'programs_services': []
        }
        self._org_info[url] = empty_info
        # Save cache even for empty results
        org_info_cache_file = self.cache_dir / "org_info_cache.json"
        self._save_cache(org_info_cache_file, self._org_info)
        return empty_info
    
    def enrich_member(self, company_name: str, city: Optional[str] = None,
                     state: Optional[str] = None) -> Dict[str, any]:
        """
        Complete enrichment process for a member.
        
        Args:
            company_name: Company name
            city: Optional city
            state: Optional state
            
        Returns:
            Dictionary with website, contacts, staff, and organization information
        """
        result = {
            'website': None,
            'website_confidence': 0,
            'contacts': {'emails': [], 'phones': [], 'addresses': []},
            'staff': [],
            'organization_info': {
                'funders_partners': [],
                'major_areas_of_work': [],
                'affiliations': [],
                'mission': None,
                'programs_services': []
            }
        }
        
        # Find website
        website_result = self.find_website(company_name, city, state)
        if website_result:
            url, confidence = website_result
            result['website'] = url
            result['website_confidence'] = confidence
            
            # Extract contact info
            result['contacts'] = self.extract_contact_info(url)
            
            # Extract staff info
            result['staff'] = self.extract_staff_info(url)
            
            # Extract comprehensive organization info (funders, partners, major areas of work, etc.)
            try:
                org_info = self.extract_organization_info(url)
                result['organization_info'] = org_info
            except Exception as e:
                logger.warning(f"Error extracting organization info from {url}: {e}")
        
        return result

