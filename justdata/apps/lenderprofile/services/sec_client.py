#!/usr/bin/env python3
"""
SEC Edgar API Client
Fetches corporate filings and financial data using SEC's JSON APIs.

Documentation: https://www.sec.gov/edgar/sec-api-documentation
Base URL: https://data.sec.gov/
Authentication: User-Agent header required (no API key needed)
Rate Limit: 10 requests per second
"""

import requests
import logging
import re
import time
from typing import Optional, Dict, Any, List
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class SECClient:
    """
    Client for SEC Edgar API.
    
    Uses JSON APIs from data.sec.gov for structured data access.
    No API key required, but User-Agent header is mandatory.
    Rate limit: 10 requests per second.
    """
    
    def __init__(self):
        """Initialize SEC API client."""
        self.base_url = 'https://www.sec.gov'
        self.data_url = 'https://data.sec.gov'
        self.browse_url = f'{self.base_url}/cgi-bin/browse-edgar'
        self.timeout = 30
        self.user_agent = 'NCRC Lender Intelligence Platform contact@ncrc.org'
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms = 10 requests per second max
        self._company_tickers_cache = None  # Cache for company_tickers.json
        self._company_tickers_cache_time = 0
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with User-Agent (required by SEC)."""
        return {
            'User-Agent': self.user_agent,
            'Accept': 'application/json'
        }
    
    def _rate_limit(self):
        """Enforce rate limiting (10 requests per second)."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()
    
    def _format_cik(self, cik: str) -> str:
        """Format CIK as 10-digit string with leading zeros."""
        cik_str = str(cik).strip()
        # Remove leading zeros if present, then pad to 10 digits
        cik_int = int(cik_str)
        return f"{cik_int:010d}"

    def _load_company_tickers(self) -> Dict[str, Any]:
        """
        Load SEC company_tickers.json (fast lookup of all public companies).
        Caches for 1 hour to avoid repeated downloads.

        Returns:
            Dict mapping index to {ticker, cik_str, title}
        """
        current_time = time.time()
        # Return cache if valid (1 hour)
        if self._company_tickers_cache and (current_time - self._company_tickers_cache_time) < 3600:
            return self._company_tickers_cache

        try:
            url = f'{self.base_url}/files/company_tickers.json'
            self._rate_limit()
            response = requests.get(url, headers=self._get_headers(), timeout=60)
            response.raise_for_status()

            self._company_tickers_cache = response.json()
            self._company_tickers_cache_time = current_time
            logger.info(f"Loaded {len(self._company_tickers_cache)} companies from SEC company_tickers.json")
            return self._company_tickers_cache
        except Exception as e:
            logger.error(f"Error loading company_tickers.json: {e}")
            return {}

    def search_companies_by_name_json(self, name: str) -> List[Dict[str, Any]]:
        """
        Search for companies by name using SEC's company_tickers.json (fast and reliable).

        Handles common bank naming patterns:
        - "JPMORGAN CHASE BANK" -> searches for "JPMORGAN CHASE" (removes BANK suffix)
        - "BANK OF AMERICA" -> searches for "BANK OF AMERICA" (keeps BANK prefix)
        - Tries multiple variations to find holding companies

        Args:
            name: Company name to search for

        Returns:
            List of matching companies with cik, ticker, and name
        """
        try:
            data = self._load_company_tickers()
            if not data:
                return []

            name_upper = name.upper()

            # Common bank suffixes to remove when searching
            # These are typically on bank subsidiaries, not the parent holding company
            bank_suffixes = [
                ' BANK, NATIONAL ASSOCIATION',
                ' BANK NATIONAL ASSOCIATION',
                ' BANK, N.A.',
                ' BANK N.A.',
                ', N.A.',
                ', NA',
                ' N.A.',
                ' BANK',
            ]

            # Common word variations (SEC often uses abbreviations)
            word_variations = {
                'CORPORATION': 'CORP',
                'INCORPORATED': 'INC',
                'COMPANY': 'CO',
                'LIMITED': 'LTD',
                'ASSOCIATES': 'ASSOC',
            }

            # Create search variations: original, then without bank suffixes
            search_variations = [name_upper]

            # Also add variation with common abbreviations
            abbreviated = name_upper
            for full, abbrev in word_variations.items():
                abbreviated = abbreviated.replace(full, abbrev)
            if abbreviated != name_upper and abbreviated not in search_variations:
                search_variations.append(abbreviated)

            for suffix in bank_suffixes:
                if name_upper.endswith(suffix):
                    core_name = name_upper[:-len(suffix)].strip()
                    if core_name and core_name not in search_variations:
                        search_variations.append(core_name)

            matches = []
            seen_ciks = set()  # Avoid duplicates

            # Helper to normalize text for comparison (remove punctuation, keep alphanumeric and spaces)
            def normalize(text):
                # Replace & with AND for matching, remove other punctuation
                text = text.replace('&', ' AND ')
                # Remove punctuation except spaces
                text = re.sub(r'[^\w\s]', '', text)
                # Collapse whitespace
                text = ' '.join(text.split())
                return text.upper()

            for search_name in search_variations:
                # Normalize and split into words
                normalized_search = normalize(search_name)
                name_words = set(normalized_search.split())
                # Filter out short words like "AND", "THE", "OF" for more flexible matching
                significant_words = {w for w in name_words if len(w) > 2}

                for key, company in data.items():
                    title = company.get('title', '').upper()
                    normalized_title = normalize(title)
                    ticker = company.get('ticker', '')
                    cik = company.get('cik_str')

                    # Skip if already matched this company
                    if cik in seen_ciks:
                        continue

                    # Match if significant search words appear in normalized title
                    if significant_words and all(word in normalized_title for word in significant_words):
                        matches.append({
                            'name': company.get('title'),
                            'cik': self._format_cik(cik) if cik else None,
                            'ticker': ticker
                        })
                        seen_ciks.add(cik)

            # Sort matches: prefer primary common stock tickers (shorter, no suffix letters)
            # JPM before JPM-PC, JPM-PD (preferred shares)
            def ticker_priority(m):
                t = m.get('ticker', '')
                # Shorter tickers first, alphabetical as tiebreaker
                return (len(t), t)

            matches.sort(key=ticker_priority)
            logger.info(f"SEC search for '{name}': {len(matches)} matches (search variations: {search_variations})")
            return matches
        except Exception as e:
            logger.error(f"Error searching companies by name '{name}': {e}")
            return []

    def get_ticker_from_cik(self, cik: str) -> Optional[str]:
        """
        Get ticker symbol from CIK using SEC submissions API (most reliable method).
        
        Args:
            cik: Central Index Key (10-digit, zero-padded)
            
        Returns:
            Primary ticker symbol or None
        """
        try:
            submissions = self.get_company_submissions(cik)
            if submissions and 'tickers' in submissions:
                tickers = submissions.get('tickers', [])
                if tickers:
                    # Return the first ticker (usually the primary one)
                    return tickers[0].upper()
            return None
        except Exception as e:
            logger.debug(f"Error getting ticker from CIK {cik}: {e}")
            return None
    
    def get_ticker_from_company_name(self, company_name: str) -> Optional[str]:
        """
        Get ticker symbol from company name using multiple methods (most reliable first).
        
        Strategy:
        1. Search SEC for company to get CIK
        2. Use SEC submissions API to get ticker from CIK (most reliable)
        3. Fallback to web search
        4. Fallback to name extraction
        
        Args:
            company_name: Company name
            
        Returns:
            Ticker symbol or None
        """
        try:
            # Method 1: Search SEC for company, get CIK, then get ticker from submissions API
            companies = self.search_companies(company_name, use_ticker=False)
            if companies:
                # Try each company until we find one with a ticker
                for company in companies:
                    cik = company.get('cik')
                    if cik:
                        ticker = self.get_ticker_from_cik(cik)
                        if ticker:
                            logger.info(f"Found ticker '{ticker}' for '{company_name}' via SEC CIK {cik}")
                            return ticker
                
                # If no ticker found via submissions, check if company dict has ticker
                for company in companies:
                    ticker = company.get('ticker')
                    if ticker:
                        logger.info(f"Found ticker '{ticker}' for '{company_name}' from SEC search")
                        return ticker.upper()
            
            # Method 2: Fallback to web search
            ticker = self._get_ticker_from_web_search(company_name)
            if ticker:
                logger.info(f"Found ticker '{ticker}' for '{company_name}' via web search")
                return ticker
            
            # Method 3: Fallback to name extraction
            ticker = self._extract_ticker_from_name(company_name)
            if ticker:
                logger.debug(f"Extracted ticker '{ticker}' from company name '{company_name}'")
                return ticker
            
            return None
        except Exception as e:
            logger.debug(f"Error getting ticker from company name '{company_name}': {e}")
            return None
    
    def _get_ticker_from_web_search(self, company_name: str) -> Optional[str]:
        """Try to get ticker symbol from web search (fallback method)."""
        try:
            # Try DuckDuckGo instant answer API
            query = f"{company_name} stock ticker symbol"
            response = requests.get('https://api.duckduckgo.com/',
                                   params={'q': query, 'format': 'json', 'no_html': '1'},
                                   headers={'User-Agent': 'NCRC Lender Intelligence Platform'},
                                   timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get('Answer', '')
                if answer:
                    # Look for ticker pattern (1-5 uppercase letters)
                    ticker_match = re.search(r'\b([A-Z]{1,5})\b', answer)
                    if ticker_match:
                        return ticker_match.group(1)
            return None
        except Exception as e:
            logger.debug(f"Error in web search for ticker: {e}")
            return None
    
    def _extract_ticker_from_name(self, company_name: str) -> Optional[str]:
        """Try to extract ticker from company name (last resort)."""
        try:
            # Common patterns: "PNC Bank" -> "PNC", "Bank of America" -> "BAC"
            name_clean = company_name.upper().replace(' BANK', '').replace(' FINANCIAL', '').replace(' SERVICES', '').strip()
            words = name_clean.split()

            # Only extract if it's a single short word (like "PNC" alone)
            # Don't extract first word from multi-word names like "FIFTH THIRD"
            if len(words) == 1:
                first_word = words[0]
                if first_word and len(first_word) <= 5 and first_word.isalpha():
                    return first_word
            return None
        except Exception:
            return None
    
    def get_ticker_from_search(self, company_name: str) -> Optional[str]:
        """
        DEPRECATED: Use get_ticker_from_company_name() instead.
        
        Legacy method for backward compatibility.
        """
        return self.get_ticker_from_company_name(company_name)
    
    def search_companies(self, name: str, use_ticker: bool = True) -> List[Dict[str, Any]]:
        """
        Search for company by name.
        Uses fast JSON lookup first, then falls back to HTML search if needed.

        Args:
            name: Company name
            use_ticker: If True, include ticker in results (default True)

        Returns:
            List of matching companies with CIK, name, and optionally ticker
        """
        # Try fast JSON-based search first (company_tickers.json)
        companies = self.search_companies_by_name_json(name)
        if companies:
            logger.info(f"Found {len(companies)} companies for '{name}' via JSON lookup")
            return companies

        # Fallback to HTML search (slower, may timeout)
        self._rate_limit()
        companies = []

        try:
            url = f'{self.browse_url}'
            params = {
                'company': name,
                'type': '',
                'owner': 'exclude',
                'count': '100',
                'action': 'getcompany'
            }

            response = requests.get(url, params=params, headers=self._get_headers(), timeout=self.timeout)
            response.raise_for_status()

            # Parse HTML response
            soup = BeautifulSoup(response.text, 'html.parser')

            # Find company table
            table = soup.find('table', {'class': 'tableFile2'})
            if table:
                rows = table.find_all('tr')[1:]  # Skip header
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        name_cell = cells[0]
                        cik_link = name_cell.find('a')
                        if cik_link:
                            cik = cik_link.get('href', '').split('CIK=')[-1].split('&')[0]
                            company_name = cik_link.text.strip()
                            companies.append({
                                'name': company_name,
                                'cik': self._format_cik(cik)
                            })

            return companies
        except requests.exceptions.RequestException as e:
            logger.error(f"SEC API error searching for '{name}': {e}")
            return []
    
    def _search_by_ticker(self, ticker: str) -> List[Dict[str, Any]]:
        """Search SEC by ticker symbol."""
        self._rate_limit()
        try:
            # Try JSON API first (submissions endpoint with ticker lookup)
            # Use company tickers API if available, otherwise fall back to HTML
            url = f'{self.browse_url}'
            params = {
                'company': ticker,
                'type': '',
                'owner': 'exclude',
                'count': '100',
                'action': 'getcompany'
            }
            
            response = requests.get(url, params=params, headers=self._get_headers(), timeout=self.timeout)
            response.raise_for_status()
            
            # Parse HTML response
            soup = BeautifulSoup(response.text, 'html.parser')
            companies = []
            
            # Find company table
            table = soup.find('table', {'class': 'tableFile2'})
            if table:
                rows = table.find_all('tr')[1:]  # Skip header
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        name_cell = cells[0]
                        cik_link = name_cell.find('a')
                        if cik_link:
                            cik = cik_link.get('href', '').split('CIK=')[-1].split('&')[0]
                            company_name = cik_link.text.strip()
                            companies.append({
                                'name': company_name,
                                'cik': self._format_cik(cik),
                                'ticker': ticker
                            })
            
            return companies
        except Exception as e:
            logger.debug(f"Error searching by ticker {ticker}: {e}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"SEC API error searching by ticker {ticker}: {e}")
            return []
    
    def get_company_submissions(self, cik: str) -> Optional[Dict[str, Any]]:
        """
        Get company submissions (filing history) using JSON API.
        
        Args:
            cik: Central Index Key (10-digit, zero-padded)
            
        Returns:
            Company submissions data including filing history
        """
        self._rate_limit()
        try:
            cik_formatted = self._format_cik(cik)
            url = f'{self.data_url}/submissions/CIK{cik_formatted}.json'
            
            response = requests.get(url, headers=self._get_headers(), timeout=self.timeout)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.info(f"CIK not found: {cik}")
                return None
            logger.error(f"SEC API error getting submissions for CIK {cik}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"SEC API error getting submissions for CIK {cik}: {e}")
            return None
    
    def get_company_facts(self, cik: str) -> Optional[Dict[str, Any]]:
        """
        Get all XBRL company facts for a company.
        
        Args:
            cik: Central Index Key (10-digit, zero-padded)
            
        Returns:
            Company facts data with all XBRL concepts
        """
        self._rate_limit()
        try:
            cik_formatted = self._format_cik(cik)
            url = f'{self.data_url}/api/xbrl/companyfacts/CIK{cik_formatted}.json'
            
            response = requests.get(url, headers=self._get_headers(), timeout=self.timeout)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.info(f"Company facts not found for CIK: {cik}")
                return None
            logger.error(f"SEC API error getting company facts for CIK {cik}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"SEC API error getting company facts for CIK {cik}: {e}")
            return None
    
    def get_10k_filings(self, cik: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get the last N 10-K filings for a company.
        
        Args:
            cik: Central Index Key (10-digit, zero-padded)
            limit: Number of 10-K filings to retrieve (default: 5)
            
        Returns:
            List of 10-K filings with type, date, accession_number, and URL
        """
        return self.get_company_filings(cik, filing_type='10-K', limit=limit)
    
    def get_10k_filing_content(self, cik: str, accession_number: str) -> Optional[str]:
        """
        Get the full text content of a 10-K filing for AI analysis.

        Args:
            cik: Central Index Key (10-digit, zero-padded)
            accession_number: Filing accession number (e.g., '0000035527-25-000079')

        Returns:
            Full text content of the filing or None
        """
        try:
            # First get the filing index to find the main document
            cik_int = int(cik)
            acc_clean = accession_number.replace('-', '')
            index_url = f"{self.base_url}/Archives/edgar/data/{cik_int}/{acc_clean}/{accession_number}-index.htm"

            self._rate_limit()
            response = requests.get(index_url, headers=self._get_headers(), timeout=self.timeout)

            if response.status_code != 200:
                logger.warning(f"Could not fetch filing index: {response.status_code}")
                return None

            # Parse index to find main document
            soup = BeautifulSoup(response.text, 'html.parser')
            doc_url = None

            # Look for iXBRL viewer link first (modern SEC filings)
            # Format: /ix?doc=/Archives/edgar/data/{cik}/{accession}/{filename}.htm
            for link in soup.find_all('a'):
                href = link.get('href', '')
                if '/ix?doc=' in href:
                    # Extract the actual document path from iXBRL viewer URL
                    doc_path = href.split('/ix?doc=')[-1]
                    if doc_path.startswith('/'):
                        doc_url = f"{self.base_url}{doc_path}"
                    else:
                        doc_url = f"{self.base_url}/{doc_path}"
                    logger.info(f"Found iXBRL document: {doc_url}")
                    break

            # Fallback: Look for direct .htm link with 10-k pattern
            if not doc_url:
                for link in soup.find_all('a'):
                    href = link.get('href', '')
                    text = link.get_text().lower()
                    if href.endswith('.htm') and ('10-k' in text or 'form10k' in href.lower()):
                        if href.startswith('/Archives'):
                            doc_url = f"{self.base_url}{href}"
                        elif not href.startswith('http'):
                            doc_url = f"{self.base_url}/Archives/edgar/data/{cik_int}/{acc_clean}/{href}"
                        else:
                            doc_url = href
                        break

            # Last fallback: any .htm in /Archives that's not an exhibit
            if not doc_url:
                for link in soup.find_all('a'):
                    href = link.get('href', '')
                    if '/Archives/' in href and href.endswith('.htm') and 'ex' not in href.lower():
                        if href.startswith('/'):
                            doc_url = f"{self.base_url}{href}"
                        else:
                            doc_url = href
                        break

            if not doc_url:
                logger.warning(f"Could not find main document in filing index")
                return None

            # Fetch the main document
            self._rate_limit()
            doc_response = requests.get(doc_url, headers=self._get_headers(), timeout=90)
            if doc_response.status_code != 200:
                logger.warning(f"Could not fetch filing document: {doc_response.status_code}")
                return None

            # Parse HTML and extract text content
            doc_soup = BeautifulSoup(doc_response.text, 'html.parser')

            # Remove script and style elements
            for element in doc_soup(["script", "style"]):
                element.decompose()

            # Get text content
            text = doc_soup.get_text()

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)

            logger.info(f"Retrieved 10-K content: {len(text)} chars from {doc_url}")
            return text

        except Exception as e:
            logger.error(f"Error getting 10-K filing content for CIK {cik}, accession {accession_number}: {e}")
            return None
    
    def get_company_filings(self, cik: str, filing_type: Optional[str] = None,
                           limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get company filings using submissions API (JSON) or HTML fallback.

        Args:
            cik: Central Index Key (10-digit, zero-padded)
            filing_type: Optional filing type filter (10-K, 10-Q, 8-K, DEF 14A, etc.)
            limit: Maximum number of results

        Returns:
            List of filings with type, date, and URL
        """
        # Try JSON API first
        submissions = self.get_company_submissions(cik)
        if submissions and 'filings' in submissions:
            filings = []
            recent = submissions.get('filings', {}).get('recent', {})

            if recent:
                filing_types = recent.get('form', [])
                filing_dates = recent.get('filingDate', [])
                filing_nums = recent.get('accessionNumber', [])

                # Iterate through ALL filings to find matches
                # This is critical for companies like JPMorgan that file hundreds of 424B2
                # prospectuses, pushing DEF 14A to index 16000+
                for i, form_type in enumerate(filing_types):
                    # Stop if we've collected enough filings
                    if len(filings) >= limit:
                        break

                    # Filter by filing type if specified
                    if filing_type and form_type != filing_type:
                        continue

                    filing_date = filing_dates[i] if i < len(filing_dates) else None
                    accession_num = filing_nums[i] if i < len(filing_nums) else None

                    # Build filing URL
                    if accession_num:
                        # Format: CIK/accession-number (e.g., 0000001750/0000000000-20-000001)
                        accession_clean = accession_num.replace('-', '')
                        filing_url = f"{self.base_url}/cgi-bin/viewer?action=view&cik={cik}&accession_number={accession_num}&xbrl_type=v"
                    else:
                        filing_url = None

                    filings.append({
                        'type': form_type,
                        'date': filing_date,
                        'accession_number': accession_num,
                        'url': filing_url
                    })

            if filings:
                return filings

            # If filtering by type and no results from recent,
            # we need to return empty (caller can try HTML fallback)
            if filing_type:
                logger.info(f"No {filing_type} filings found in recent for CIK {cik}")
        
        # Fallback to HTML scraping if JSON API doesn't have data
        self._rate_limit()
        try:
            url = f'{self.browse_url}'
            params = {
                'CIK': cik,
                'count': limit,
                'action': 'getcompany'
            }
            
            if filing_type:
                params['type'] = filing_type
            
            response = requests.get(url, params=params, headers=self._get_headers(), timeout=self.timeout)
            response.raise_for_status()
            
            # Parse HTML response
            soup = BeautifulSoup(response.text, 'html.parser')
            filings = []
            
            # Find filings table
            table = soup.find('table', {'class': 'tableFile2'})
            if table:
                rows = table.find_all('tr')[1:]  # Skip header
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 4:
                        filing_link = cells[1].find('a')
                        if filing_link:
                            filing_url = filing_link.get('href', '')
                            form_type = cells[0].text.strip()
                            filing_date = cells[3].text.strip()
                            
                            filings.append({
                                'type': form_type,
                                'date': filing_date,
                                'url': f"{self.base_url}{filing_url}"
                            })
            
            return filings
            
        except requests.exceptions.RequestException as e:
            logger.error(f"SEC API error getting filings for CIK {cik}: {e}")
            return []
    
    def get_filing_document(self, filing_url: str) -> Optional[str]:
        """
        Get filing document text.
        
        Args:
            filing_url: URL to filing document
            
        Returns:
            Document text or None
        """
        self._rate_limit()
        try:
            response = requests.get(filing_url, headers=self._get_headers(), timeout=self.timeout)
            response.raise_for_status()
            return response.text
            
        except requests.exceptions.RequestException as e:
            logger.error(f"SEC API error getting document {filing_url}: {e}")
            return None
    
    def get_company_concept(self, cik: str, concept: str, taxonomy: str = 'us-gaap') -> Optional[Dict[str, Any]]:
        """
        Get XBRL concept data for a specific company and concept.
        
        Args:
            cik: Central Index Key (10-digit, zero-padded)
            concept: XBRL concept name (e.g., 'AccountsPayableCurrent', 'Assets')
            taxonomy: Taxonomy (default: 'us-gaap')
            
        Returns:
            Concept data with all disclosures organized by units
        """
        self._rate_limit()
        try:
            cik_formatted = self._format_cik(cik)
            url = f'{self.data_url}/api/xbrl/companyconcept/CIK{cik_formatted}/{taxonomy}/{concept}.json'
            
            response = requests.get(url, headers=self._get_headers(), timeout=self.timeout)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.info(f"Concept {concept} not found for CIK {cik}")
                return None
            logger.error(f"SEC API error getting concept {concept} for CIK {cik}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"SEC API error getting concept {concept} for CIK {cik}: {e}")
            return None
    
    def parse_xbrl_financials(self, cik: str) -> Optional[Dict[str, Any]]:
        """
        Parse XBRL financial data from company facts API.

        Args:
            cik: Central Index Key

        Returns:
            Parsed financial data dictionary
        """
        facts = self.get_company_facts(cik)
        if not facts:
            return None

        try:
            # Extract key financial metrics
            financials = {
                'assets': None,
                'liabilities': None,
                'equity': None,
                'revenue': None,
                'net_income': None,
                'total_debt': None
            }

            # Common US-GAAP concepts
            concept_map = {
                'assets': 'Assets',
                'liabilities': 'Liabilities',
                'equity': 'Equity',
                'revenue': 'Revenues',
                'net_income': 'NetIncomeLoss',
                'total_debt': 'Debt'
            }

            us_gaap = facts.get('facts', {}).get('us-gaap', {})

            for key, concept_name in concept_map.items():
                if concept_name in us_gaap:
                    concept_data = us_gaap[concept_name]
                    units = concept_data.get('units', {})

                    # Try to get most recent USD value
                    if 'USD' in units:
                        usd_data = units['USD']
                        if usd_data:
                            # Get most recent value
                            latest = sorted(usd_data, key=lambda x: x.get('end', ''), reverse=True)
                            if latest:
                                financials[key] = latest[0].get('val')

            return financials

        except Exception as e:
            logger.error(f"Error parsing XBRL financials for CIK {cik}: {e}")
            return None

    def _get_latest_xbrl_value(self, us_gaap: Dict[str, Any], concept_name: str,
                                form_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get the most recent value for an XBRL concept.

        Args:
            us_gaap: US-GAAP facts dictionary
            concept_name: Name of the concept (e.g., 'Assets')
            form_type: Optional filter by form type (e.g., '10-K', '10-Q')

        Returns:
            Dict with 'value', 'end_date', 'form', and 'filed' or None
        """
        if concept_name not in us_gaap:
            return None

        concept_data = us_gaap[concept_name]
        units = concept_data.get('units', {})

        # Try USD first, then 'pure' for ratios
        unit_data = units.get('USD', units.get('pure', units.get('shares', [])))
        if not unit_data:
            return None

        # Filter by form type if specified
        if form_type:
            unit_data = [d for d in unit_data if d.get('form') == form_type]

        if not unit_data:
            return None

        # Get most recent value
        latest = sorted(unit_data, key=lambda x: x.get('end', ''), reverse=True)[0]
        return {
            'value': latest.get('val'),
            'end_date': latest.get('end'),
            'form': latest.get('form'),
            'filed': latest.get('filed')
        }

    def get_comprehensive_xbrl_data(self, cik: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive XBRL financial data for a company including:
        - Core financials (assets, liabilities, equity, income)
        - Bank-specific metrics (deposits, loans, allowances)
        - Community investment data (affordable housing, tax credits)

        Args:
            cik: Central Index Key

        Returns:
            Comprehensive financial data dictionary
        """
        facts = self.get_company_facts(cik)
        if not facts:
            return None

        try:
            us_gaap = facts.get('facts', {}).get('us-gaap', {})

            result = {
                'entity_name': facts.get('entityName'),
                'cik': facts.get('cik'),
                'core_financials': {},
                'bank_metrics': {},
                'community_investment': {},
                'all_available_concepts': list(us_gaap.keys())
            }

            # Core financial metrics
            core_concepts = {
                'assets': 'Assets',
                'liabilities': 'Liabilities',
                'stockholders_equity': 'StockholdersEquity',
                'net_income': 'NetIncomeLoss',
                'interest_income_expense_net': 'InterestIncomeExpenseNet',
                'common_shares_outstanding': 'CommonStockSharesOutstanding',
            }

            for key, concept in core_concepts.items():
                data = self._get_latest_xbrl_value(us_gaap, concept)
                if data:
                    result['core_financials'][key] = data

            # Bank-specific metrics
            bank_concepts = {
                'deposits': 'Deposits',
                'loans_net': 'LoansAndLeasesReceivableNetReportedAmount',
                'allowance_for_loan_losses': 'AllowanceForLoanAndLeaseLosses',
                'financing_receivable_nonaccrual': 'FinancingReceivableRecordedInvestmentNonaccrualStatus',
                'financing_receivable_past_due': 'FinancingReceivableRecordedInvestmentPastDue',
            }

            for key, concept in bank_concepts.items():
                data = self._get_latest_xbrl_value(us_gaap, concept)
                if data:
                    result['bank_metrics'][key] = data

            # Community investment / affordable housing metrics
            community_concepts = {
                'affordable_housing_tax_credits': 'AffordableHousingTaxCreditsAndOtherTaxBenefitsAmount',
                'affordable_housing_amortization': 'AmortizationMethodQualifiedAffordableHousingProjectInvestmentsAmortization',
                'affordable_housing_writedown': 'AffordableHousingProjectInvestmentWriteDownAmount',
                'equity_method_investments': 'EquityMethodInvestments',
                'investment_tax_credit': 'IncomeTaxReconciliationTaxCreditsInvestment',
                'defined_contribution_cost': 'DefinedContributionPlanCostRecognized',
            }

            for key, concept in community_concepts.items():
                data = self._get_latest_xbrl_value(us_gaap, concept)
                if data:
                    result['community_investment'][key] = data

            # Log what we found
            found_core = len(result['core_financials'])
            found_bank = len(result['bank_metrics'])
            found_community = len(result['community_investment'])
            logger.info(f"XBRL data for {result['entity_name']}: {found_core} core, {found_bank} bank, {found_community} community metrics")

            return result

        except Exception as e:
            logger.error(f"Error getting comprehensive XBRL data for CIK {cik}: {e}")
            return None

    def get_8k_filings(self, cik: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the last N 8-K filings for a company.

        8-K filings are current reports for material events like:
        - Bankruptcy/receivership
        - Mine safety issues
        - Disclosure amendments
        - Regulation FD disclosures
        - Other material events

        Args:
            cik: Central Index Key (10-digit, zero-padded)
            limit: Number of 8-K filings to retrieve (default: 10)

        Returns:
            List of 8-K filings with type, date, accession_number, and URL
        """
        return self.get_company_filings(cik, filing_type='8-K', limit=limit)

    def get_8k_filing_content(self, cik: str, accession_number: str) -> Optional[str]:
        """
        Get the full text content of an 8-K filing.

        Args:
            cik: Central Index Key (10-digit, zero-padded)
            accession_number: Filing accession number (e.g., '0000035527-25-000079')

        Returns:
            Full text content of the filing or None
        """
        try:
            # First get the filing index to find the main document
            cik_int = int(cik)
            acc_clean = accession_number.replace('-', '')
            index_url = f"{self.base_url}/Archives/edgar/data/{cik_int}/{acc_clean}/{accession_number}-index.htm"

            self._rate_limit()
            response = requests.get(index_url, headers=self._get_headers(), timeout=self.timeout)

            if response.status_code != 200:
                logger.warning(f"Could not fetch 8-K filing index: {response.status_code}")
                return None

            # Parse index to find main document
            soup = BeautifulSoup(response.text, 'html.parser')
            doc_url = None

            # Look for 8-K document link
            for link in soup.find_all('a'):
                href = link.get('href', '')
                text = link.get_text().lower()
                if href.endswith('.htm') and ('8-k' in text or 'form8k' in href.lower()):
                    if not href.startswith('http'):
                        doc_url = f"{self.base_url}/Archives/edgar/data/{cik_int}/{acc_clean}/{href}"
                    else:
                        doc_url = href
                    break

            if not doc_url:
                # Try to find any .htm file that looks like the main filing
                for link in soup.find_all('a'):
                    href = link.get('href', '')
                    if href.endswith('.htm') and '-index' not in href:
                        if not href.startswith('http'):
                            doc_url = f"{self.base_url}/Archives/edgar/data/{cik_int}/{acc_clean}/{href}"
                        else:
                            doc_url = href
                        break

            if not doc_url:
                logger.warning(f"Could not find main document in 8-K filing index")
                return None

            # Fetch the main document
            self._rate_limit()
            doc_response = requests.get(doc_url, headers=self._get_headers(), timeout=60)
            if doc_response.status_code != 200:
                logger.warning(f"Could not fetch 8-K filing document: {doc_response.status_code}")
                return None

            # Parse HTML and extract text content
            doc_soup = BeautifulSoup(doc_response.text, 'html.parser')

            # Remove script and style elements
            for element in doc_soup(["script", "style"]):
                element.decompose()

            # Get text content
            text = doc_soup.get_text()

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)

            logger.info(f"Retrieved 8-K content: {len(text)} chars from {doc_url}")
            return text

        except Exception as e:
            logger.error(f"Error getting 8-K filing content for CIK {cik}, accession {accession_number}: {e}")
            return None

    def get_def14a_filing_content(self, cik: str, accession_number: str) -> Optional[str]:
        """
        Get the full text content of a DEF 14A (proxy statement) filing.

        Args:
            cik: Central Index Key (10-digit, zero-padded)
            accession_number: Filing accession number (e.g., '0001193125-25-045653')

        Returns:
            Full text content of the proxy statement or None
        """
        try:
            # First get the filing index to find the main document
            cik_int = int(cik)
            acc_clean = accession_number.replace('-', '')
            index_url = f"{self.base_url}/Archives/edgar/data/{cik_int}/{acc_clean}/{accession_number}-index.htm"

            self._rate_limit()
            response = requests.get(index_url, headers=self._get_headers(), timeout=60)

            if response.status_code != 200:
                logger.warning(f"Could not fetch DEF 14A filing index: {response.status_code}")
                return None

            # Parse index to find main document
            soup = BeautifulSoup(response.text, 'html.parser')
            doc_url = None

            # Look for DEF 14A document link (proxy statement patterns)
            for link in soup.find_all('a'):
                href = link.get('href', '')
                text = link.get_text().lower()
                href_lower = href.lower()
                # Match DEF 14A document patterns
                if '.htm' in href_lower and (
                    'def14a' in href_lower or
                    'def 14a' in text or
                    'proxy' in text or
                    'definitive proxy' in text
                ):
                    # Handle new SEC inline viewer format: /ix?doc=/Archives/...
                    if '/ix?doc=' in href:
                        doc_path = href.split('/ix?doc=')[-1]
                        doc_url = f"{self.base_url}{doc_path}"
                    elif href.startswith('http'):
                        doc_url = href
                    elif href.startswith('/'):
                        doc_url = f"{self.base_url}{href}"
                    else:
                        doc_url = f"{self.base_url}/Archives/edgar/data/{cik_int}/{acc_clean}/{href}"
                    break

            if not doc_url:
                # Fallback: find any .htm file that's not the index
                for link in soup.find_all('a'):
                    href = link.get('href', '')
                    if '.htm' in href and '-index' not in href and 'R' not in href:
                        # Handle new SEC inline viewer format
                        if '/ix?doc=' in href:
                            doc_path = href.split('/ix?doc=')[-1]
                            doc_url = f"{self.base_url}{doc_path}"
                        elif href.startswith('http'):
                            doc_url = href
                        elif href.startswith('/'):
                            doc_url = f"{self.base_url}{href}"
                        else:
                            doc_url = f"{self.base_url}/Archives/edgar/data/{cik_int}/{acc_clean}/{href}"
                        break

            if not doc_url:
                logger.warning(f"Could not find main document in DEF 14A filing index")
                return None

            # Fetch the main document (proxy statements can be large, use longer timeout)
            self._rate_limit()
            doc_response = requests.get(doc_url, headers=self._get_headers(), timeout=120)
            if doc_response.status_code != 200:
                logger.warning(f"Could not fetch DEF 14A document: {doc_response.status_code}")
                return None

            # Parse HTML and extract text content
            doc_soup = BeautifulSoup(doc_response.text, 'html.parser')

            # Remove script and style elements
            for element in doc_soup(["script", "style"]):
                element.decompose()

            # Get text content
            text = doc_soup.get_text()

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)

            logger.info(f"Retrieved DEF 14A content: {len(text)} chars from {doc_url}")
            return text

        except Exception as e:
            logger.error(f"Error getting DEF 14A filing content for CIK {cik}, accession {accession_number}: {e}")
            return None
