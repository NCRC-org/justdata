"""
ProPublica Nonprofit Explorer API Client

Provides access to IRS Form 990 data via ProPublica's free API.
Can search by organization name or EIN (if available).
"""

import requests
import time
import re
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class ProPublicaClient:
    """Client for ProPublica Nonprofit Explorer API."""
    
    BASE_URL = "https://projects.propublica.org/nonprofits/api/v2"
    
    def __init__(self, rate_limit_delay: float = 1.0):
        """
        Initialize ProPublica client.
        
        Args:
            rate_limit_delay: Seconds to wait between API calls (default: 1.0)
            Increased from 0.5 to 1.0 to avoid rate limits
        """
        self.rate_limit_delay = rate_limit_delay
        self.last_request_time = 0
        self.consecutive_errors = 0
    
    def _rate_limit(self):
        """Enforce rate limiting between requests with adaptive delay."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        # Increase delay if we've had consecutive errors (exponential backoff)
        delay = self.rate_limit_delay * (2.0 ** min(self.consecutive_errors, 3))  # Max 8x delay
        delay = min(delay, 10.0)  # Cap at 10 seconds
        
        if time_since_last < delay:
            sleep_time = delay - time_since_last
            logger.debug(f"Rate limiting: waiting {sleep_time:.2f} seconds (errors: {self.consecutive_errors})")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def get_organization_by_ein(self, ein: str) -> Optional[Dict[str, Any]]:
        """
        Get organization data by EIN (Employer Identification Number).
        
        Args:
            ein: 9-digit EIN (with or without dashes)
        
        Returns:
            Organization data dictionary or None if not found
        """
        # Clean EIN (remove dashes, spaces)
        ein_clean = str(ein).replace('-', '').replace(' ', '').strip()
        
        if not ein_clean.isdigit() or len(ein_clean) != 9:
            logger.warning(f"Invalid EIN format: {ein}")
            return None
        
        self._rate_limit()
        
        url = f"{self.BASE_URL}/organizations/{ein_clean}.json"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Return full response to access filings_with_data
            # The organization data is in data['organization']
            # Financial data is in data['filings_with_data']
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching organization by EIN {ein_clean}: {e}")
            return None
    
    def search_organizations(self, query: str, state: Optional[str] = None, 
                            city: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for organizations by name, with optional city and state filters.
        
        Args:
            query: Organization name to search for
            state: Optional state filter (2-letter abbreviation)
            city: Optional city filter (Note: API may not support city parameter)
            limit: Maximum number of results (default: 10)
        
        Returns:
            List of organization dictionaries
        """
        self._rate_limit()
        
        # Use search endpoint with query parameters
        # API endpoint: https://projects.propublica.org/nonprofits/api/v2/search.json
        # Note: ProPublica search API may not support city/state parameters reliably
        url = f"{self.BASE_URL}/search.json"
        params = {"q": query}
        
        # Only add state if it's a 2-letter abbreviation (API may not support full state names)
        # Only add state if it's a 2-letter abbreviation
        # ProPublica API may not support full state names or city parameters
        if state:
            state_upper = state.upper().strip()
            if len(state_upper) == 2:
                params["state"] = state_upper
            else:
                # Convert full state name to abbreviation using state_utils
                try:
                    from apps.memberview.utils.state_utils import STATE_NAME_TO_ABBREV
                    state_abbrev = STATE_NAME_TO_ABBREV.get(state_upper, None)
                    if state_abbrev:
                        params["state"] = state_abbrev
                except ImportError:
                    # Fallback: try common mappings
                    state_map = {
                        'MASSACHUSETTS': 'MA', 'RHODE ISLAND': 'RI', 'MAINE': 'ME',
                        'NEW HAMPSHIRE': 'NH', 'MARYLAND': 'MD', 'VIRGINIA': 'VA',
                        'COLORADO': 'CO', 'NEW MEXICO': 'NM', 'UTAH': 'UT',
                        'DISTRICT OF COLUMBIA': 'DC', 'WASHINGTON': 'WA',
                        'CALIFORNIA': 'CA', 'NEW YORK': 'NY', 'TEXAS': 'TX',
                        'FLORIDA': 'FL', 'ILLINOIS': 'IL', 'PENNSYLVANIA': 'PA'
                    }
                    state_abbrev = state_map.get(state_upper, None)
                    if state_abbrev:
                        params["state"] = state_abbrev
        
        # Don't add city parameter - ProPublica API doesn't support it and causes 500 errors
        # City filtering will be done client-side after getting results
        
        try:
            response = requests.get(url, params=params, timeout=10)
            
            # Handle rate limit errors (429)
            if response.status_code == 429:
                self.consecutive_errors += 1
                retry_after = response.headers.get('Retry-After')
                if retry_after:
                    wait_time = int(retry_after)
                else:
                    wait_time = min(60, 2 ** self.consecutive_errors)  # Exponential backoff, max 60s
                
                logger.warning(f"Rate limit (429) for '{query}'. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
                # Retry once after waiting
                response = requests.get(url, params=params, timeout=10)
            
            # Handle 500 errors gracefully - ProPublica API can be unreliable
            if response.status_code == 500:
                logger.warning(f"ProPublica API returned 500 error for '{query}'. Trying without state filter...")
                # Retry without state parameter
                params_no_state = {"q": query}
                time.sleep(1)  # Brief delay before retry
                response = requests.get(url, params=params_no_state, timeout=10)
                if response.status_code != 200:
                    logger.warning(f"ProPublica API still failing for '{query}' after removing state filter")
                    return []
            
            # Reset error counter on success
            if response.status_code == 200:
                self.consecutive_errors = 0
            
            response.raise_for_status()
            data = response.json()
            
            organizations = data.get('organizations', [])
            
            # If we removed state filter, filter results client-side
            if 'state' not in params and state:
                state_upper = state.upper().strip()
                if len(state_upper) == 2:
                    state_filter = state_upper
                else:
                    try:
                        from apps.memberview.utils.state_utils import STATE_NAME_TO_ABBREV
                        state_filter = STATE_NAME_TO_ABBREV.get(state_upper, None)
                    except ImportError:
                        state_filter = None
                
                if state_filter:
                    organizations = [org for org in organizations 
                                    if org.get('state', '').upper() == state_filter]
            
            return organizations[:limit]
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching organizations for '{query}': {e}")
            return []
    
    def find_organization_by_name(self, name: str, state: Optional[str] = None, 
                                   city: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Find organization by name (fuzzy matching).
        Returns the best match if found.
        
        Args:
            name: Organization name
            state: Optional state filter (2-letter abbreviation or full name)
            city: Optional city filter
        
        Returns:
            Best matching organization or None
        """
        # Try search with state and city filters
        results = self.search_organizations(name, state=state, city=city, limit=10)
        
        if not results:
            return None
        
        # Normalize state (handle both abbreviations and full names)
        state_normalized = None
        if state:
            state_upper = state.upper().strip()
            # If it's a 2-letter abbreviation, use as-is
            if len(state_upper) == 2:
                state_normalized = state_upper
            else:
                # Try to convert full state name to abbreviation
                # Common mappings
                state_map = {
                    'MASSACHUSETTS': 'MA', 'RHODE ISLAND': 'RI', 'MAINE': 'ME',
                    'NEW HAMPSHIRE': 'NH', 'MARYLAND': 'MD', 'VIRGINIA': 'VA',
                    'COLORADO': 'CO', 'NEW MEXICO': 'NM', 'UTAH': 'UT',
                    'DISTRICT OF COLUMBIA': 'DC', 'WASHINGTON': 'WA',
                    'CALIFORNIA': 'CA', 'NEW YORK': 'NY', 'TEXAS': 'TX',
                    'FLORIDA': 'FL', 'ILLINOIS': 'IL', 'PENNSYLVANIA': 'PA'
                }
                state_normalized = state_map.get(state_upper, state_upper[:2])
        
        # Filter results by state and city if provided
        filtered_results = results
        
        if state_normalized:
            state_matches = [
                org for org in filtered_results
                if org.get('state', '').upper() == state_normalized
            ]
            if state_matches:
                filtered_results = state_matches
        
        if city:
            city_normalized = city.upper().strip()
            city_matches = [
                org for org in filtered_results
                if city_normalized in org.get('city', '').upper()
            ]
            if city_matches:
                filtered_results = city_matches
        
        # Score matches (exact name match gets highest score)
        if filtered_results:
            name_normalized = name.upper().strip()
            scored_results = []
            for org in filtered_results:
                org_name = org.get('name', '').upper().strip()
                score = 0
                # Exact match
                if org_name == name_normalized:
                    score = 100
                # Contains full name
                elif name_normalized in org_name or org_name in name_normalized:
                    score = 80
                # Partial match
                else:
                    # Simple word overlap scoring
                    name_words = set(name_normalized.split())
                    org_words = set(org_name.split())
                    if name_words and org_words:
                        overlap = len(name_words & org_words) / len(name_words | org_words)
                        score = int(overlap * 60)
                
                scored_results.append((score, org))
            
            # Sort by score and return best match
            scored_results.sort(key=lambda x: x[0], reverse=True)
            if scored_results and scored_results[0][0] > 0:
                return scored_results[0][1]
        
        # If no filtered results, return first from original results
        if results:
            return results[0]
        
        return None
    
    def get_organization_financials(self, ein: str) -> Optional[Dict[str, Any]]:
        """
        Get financial data for an organization by EIN.
        
        Args:
            ein: 9-digit EIN
        
        Returns:
            Dictionary with financial information including officers
        """
        api_response = self.get_organization_by_ein(ein)
        
        if not api_response:
            return None
        
        # ProPublica API returns: {'organization': {...}, 'filings_with_data': [...]}
        org = api_response.get('organization', {})
        filings_with_data = api_response.get('filings_with_data', [])
        
        if not org:
            return None
        
        # Extract financial data - prioritize most current year from filings_with_data
        latest_filing = None
        tax_period = None
        tax_year = None
        
        if filings_with_data and len(filings_with_data) > 0:
            # Get most recent filing (first in array is usually most recent)
            latest_filing = filings_with_data[0]
            tax_period = latest_filing.get('tax_period')
            tax_year = self._extract_tax_year(tax_period)
        else:
            # Fallback to organization's tax_period
            tax_period = org.get('tax_period')
            tax_year = self._extract_tax_year(tax_period)
        
        # Extract comprehensive financials from latest filing if available
        # ProPublica uses field names like: totrevenue, totfuncexpns
        source = latest_filing if latest_filing else org
        
        financials = {
            'ein': org.get('ein'),
            'name': org.get('name'),
            'tax_period': tax_period,
            'tax_year': tax_year,
            
            # Basic Financials
            'total_revenue': self._safe_numeric(
                source.get('totrevenue') or 
                source.get('total_revenue') or 
                source.get('revenue')
            ),
            'total_expenses': self._safe_numeric(
                source.get('totfuncexpns') or 
                source.get('total_expenses') or 
                source.get('expenses')
            ),
            'total_assets': self._safe_numeric(
                source.get('totassetsend') or 
                source.get('total_assets') or 
                source.get('assets')
            ),
            'total_liabilities': self._safe_numeric(
                source.get('totliabend') or 
                source.get('total_liabilities') or 
                source.get('liabilities')
            ),
            'net_assets': self._safe_numeric(
                source.get('netassetsorfundbalances') or 
                source.get('net_assets')
            ),
            
            # Revenue Breakdown
            'contributions': self._safe_numeric(
                source.get('contributionsgiftsgrantsreceived') or
                source.get('contributions') or
                source.get('total_contributions')
            ),
            'program_service_revenue': self._safe_numeric(
                source.get('pgmservrev') or
                source.get('program_service_revenue') or
                source.get('program_revenue')
            ),
            'investment_income': self._safe_numeric(
                source.get('invstmntinc') or
                source.get('investment_income')
            ),
            'other_revenue': self._safe_numeric(
                source.get('othrevnue') or
                source.get('other_revenue')
            ),
            
            # Expense Breakdown
            'program_expenses': self._safe_numeric(
                source.get('totprgmrevnue') or 
                source.get('program_expenses') or 
                source.get('program_service_revenue')
            ),
            'administrative_expenses': self._safe_numeric(
                source.get('totmngmntgenexpns') or 
                source.get('administrative_expenses') or 
                source.get('management_and_general')
            ),
            'fundraising_expenses': self._safe_numeric(
                source.get('totfundraisingexpns') or 
                source.get('fundraising_expenses')
            ),
            'grants_paid': self._safe_numeric(
                source.get('grntstogovt') or
                source.get('grants_paid') or
                source.get('total_grants')
            ),
            
            # Balance Sheet Items
            'cash_savings': self._safe_numeric(
                source.get('cashnonintbearing') or
                source.get('cash_savings')
            ),
            'accounts_receivable': self._safe_numeric(
                source.get('accntsreceivable') or
                source.get('accounts_receivable')
            ),
            'land_buildings_equipment': self._safe_numeric(
                source.get('landbldgsequip') or
                source.get('land_buildings_equipment')
            ),
            
            # Organization Info
            'ntee_code': org.get('ntee_code'),
            'ntee_classification': org.get('ntee_classification'),
            'ruling_date': org.get('ruling_date'),
            'deductibility': org.get('deductibility'),
            'subsection': org.get('subsection'),
            'classification': org.get('classification'),
            'exempt_status': org.get('exempt_status'),
            
            # Additional Filing Info
            'filing_type': latest_filing.get('tax_period') if latest_filing else None,
            'form_type': latest_filing.get('formtype') if latest_filing else None,
            'pdf_url': latest_filing.get('pdf_url') if latest_filing else None,
        }
        
        # Extract mission/activities if available
        if latest_filing:
            mission = latest_filing.get('mission') or latest_filing.get('missiondesc')
            if mission:
                financials['mission'] = mission
            
            activities = latest_filing.get('activities') or latest_filing.get('activitydesc')
            if activities:
                financials['activities'] = activities
        
        # Extract from organization object if not in filing
        if not financials.get('mission'):
            financials['mission'] = org.get('mission') or org.get('missiondesc')
        if not financials.get('activities'):
            financials['activities'] = org.get('activities') or org.get('activitydesc')
        
        # Extract officers/executives with compensation if available
        # Officers are in latest_filing with field 'compnsatncurrofcr' (compensation of current officers)
        officers = self._extract_officers(api_response)
        if officers:
            financials['officers'] = officers
        
        # Extract key employees (highly compensated employees) if available
        key_employees = self._extract_key_employees(api_response)
        if key_employees:
            financials['key_employees'] = key_employees
        
        # Extract board members (independent directors) if available
        board_members = self._extract_board_members(api_response)
        if board_members:
            financials['board_members'] = board_members
        
        # Store the raw filing data for any additional fields we might want later
        if latest_filing:
            financials['_raw_filing_data'] = latest_filing
        
        return financials
    
    def _safe_numeric(self, value: Any) -> Optional[float]:
        """
        Safely convert value to float, handling None, strings, and numeric types.
        """
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            # Remove commas, dollar signs, etc.
            cleaned = value.replace(',', '').replace('$', '').replace(' ', '').strip()
            try:
                return float(cleaned)
            except ValueError:
                return None
        return None
    
    def _extract_tax_year(self, tax_period: Optional[str]) -> Optional[str]:
        """
        Extract tax year from tax_period string.
        Format is typically YYYY-MM-DD or YYYY.
        """
        if not tax_period:
            return None
        
        # Try to extract year (first 4 digits)
        if len(tax_period) >= 4:
            return tax_period[:4]
        return tax_period
    
    def _extract_officers(self, api_response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract officer/executive information from ProPublica API response.
        
        ProPublica API structure:
        - api_response['organization'] - organization data
        - api_response['filings_with_data'] - array of filings with financial data
        - Officers are in filings_with_data[0]['compnsatncurrofcr'] (compensation of current officers)
        """
        officers = []
        
        # Get organization and filings
        org = api_response.get('organization', {})
        filings_with_data = api_response.get('filings_with_data', [])
        
        # Try to get officers from latest filing
        if filings_with_data and len(filings_with_data) > 0:
            latest_filing = filings_with_data[0]
            
            # Check for officers in compensation field (compnsatncurrofcr)
            # This is an array of officer objects with name, title, compensation
            officer_data = latest_filing.get('compnsatncurrofcr', [])
            if officer_data and isinstance(officer_data, list):
                for officer in officer_data:
                    if isinstance(officer, dict):
                        officers.append({
                            'name': officer.get('name', officer.get('officer_name', '')),
                            'title': officer.get('title', officer.get('position', officer.get('officer_title', ''))),
                            'compensation': self._safe_numeric(
                                officer.get('compensation') or 
                                officer.get('compensation_amount') or
                                officer.get('base_compensation')
                            ),
                        })
        
        # Fallback: Check organization object for officer fields
        if not officers:
            officer_fields = ['officers', 'key_personnel', 'executives', 'officer', 'key_officers']
            for field in officer_fields:
                if field in org and org[field]:
                    data = org[field]
                    if isinstance(data, list):
                        for officer in data:
                            if isinstance(officer, dict):
                                officers.append({
                                    'name': officer.get('name', officer.get('officer_name', '')),
                                    'title': officer.get('title', officer.get('position', officer.get('officer_title', ''))),
                                    'compensation': self._safe_numeric(
                                        officer.get('compensation') or 
                                        officer.get('compensation_amount')
                                    ),
                                })
        
        # Filter out empty entries
        officers = [o for o in officers if o.get('name')]
        
        return officers
    
    def _extract_key_employees(self, api_response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract key employees (highly compensated employees) from ProPublica API response.
        These are employees (not officers) who receive significant compensation.
        """
        key_employees = []
        
        # Get organization and filings
        org = api_response.get('organization', {})
        filings_with_data = api_response.get('filings_with_data', [])
        
        # Try to get key employees from latest filing
        if filings_with_data and len(filings_with_data) > 0:
            latest_filing = filings_with_data[0]
            
            # Check for key employees field (compnsatnandothremp - compensation of other employees)
            employee_data = latest_filing.get('compnsatnandothremp', [])
            if employee_data and isinstance(employee_data, list):
                for employee in employee_data:
                    if isinstance(employee, dict):
                        key_employees.append({
                            'name': employee.get('name', employee.get('employee_name', '')),
                            'title': employee.get('title', employee.get('position', employee.get('employee_title', ''))),
                            'compensation': self._safe_numeric(
                                employee.get('compensation') or 
                                employee.get('compensation_amount') or
                                employee.get('base_compensation')
                            ),
                        })
        
        # Filter out empty entries
        key_employees = [e for e in key_employees if e.get('name')]
        
        return key_employees
    
    def _extract_board_members(self, api_response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract board members (independent directors) from ProPublica API response.
        Board members typically serve without compensation.
        """
        board_members = []
        
        # Get organization and filings
        org = api_response.get('organization', {})
        filings_with_data = api_response.get('filings_with_data', [])
        
        # Try to get board members from latest filing
        if filings_with_data and len(filings_with_data) > 0:
            latest_filing = filings_with_data[0]
            
            # Check for board members field (indpndntdirtrnstxbl - independent directors)
            # Also check for 'officers' where compensation is $0 (likely board members)
            board_data = latest_filing.get('indpndntdirtrnstxbl', [])
            if board_data and isinstance(board_data, list):
                for member in board_data:
                    if isinstance(member, dict):
                        board_members.append({
                            'name': member.get('name', member.get('director_name', '')),
                            'title': member.get('title', member.get('position', 'Board Member')),
                            'compensation': self._safe_numeric(
                                member.get('compensation') or 
                                member.get('compensation_amount')
                            ),
                        })
        
        # Also check officers with $0 compensation (likely board members)
        officers = self._extract_officers(api_response)
        for officer in officers:
            comp = officer.get('compensation')
            if comp is None or comp == 0:
                # Check if title suggests board member
                title = (officer.get('title') or '').lower()
                if any(term in title for term in ['board', 'director', 'trustee', 'chair', 'member']):
                    board_members.append({
                        'name': officer.get('name'),
                        'title': officer.get('title', 'Board Member'),
                        'compensation': 0,
                    })
        
        # Filter out empty entries and duplicates
        seen_names = set()
        unique_board = []
        for member in board_members:
            name = member.get('name')
            if name and name not in seen_names:
                seen_names.add(name)
                unique_board.append(member)
        
        return unique_board
    
    def _expand_abbreviations(self, company_name: str, city: Optional[str] = None, state: Optional[str] = None) -> List[str]:
        """
        Expands common abbreviations in company names for better ProPublica matching.
        ProPublica typically has full legal names with variations like "Chapter Inc", etc.
        Returns a list of potential search terms, including the original.
        """
        search_terms = [company_name]  # Always include the original name
        
        abbreviation_expansions = {
            'NAMC': 'National Association of Minority Contractors',
            'CDC': 'Community Development Corporation',
            'NHS': 'Neighborhood Housing Services',
            'NCRC': 'National Community Reinvestment Coalition',
            'LMI': 'Low-to-Moderate Income',
            'DFW': 'Dallas Fort Worth',
            'NYC': 'New York City',
            'LA': 'Los Angeles',
            'HERE': 'Housing Economic Resources & Education',
            'IERC': 'Inland Empire Resource Centers',
            'ELACC': 'East LA Community Corporation',
            'RurAL CAP': 'Rural Alaska Community Action Program',
            'EforAll': 'Entrepreneurship for All',
        }
        
        # Location expansions
        location_expansions = {
            'DFW': 'Dallas Fort Worth',
            'NYC': 'New York City',
            'LA': 'Los Angeles',
        }
        
        # Detect if name looks like an abbreviation (all caps, short words)
        name_upper = company_name.upper()
        words = company_name.split()
        
        # Check if it's likely an abbreviation (all caps, 2-4 letters per word)
        is_abbreviation = (
            len(words) <= 3 and 
            all(len(w) <= 5 and w.isupper() for w in words if w.isalpha())
        )
        
        # Check if name already has "Chapter", "Inc", "Incorporated", etc.
        has_chapter = any('chapter' in w.lower() for w in words)
        has_inc = any(w.upper() in ['INC', 'INC.', 'INCORPORATED'] for w in words)
        
        if is_abbreviation:
            # Try to expand known abbreviations
            expanded_parts = []
            location_part = None
            other_parts = []
            
            for word in words:
                word_clean = re.sub(r'[^A-Z]', '', word.upper())
                if word_clean in abbreviation_expansions:
                    expanded_parts.append(abbreviation_expansions[word_clean])
                elif word_clean in location_expansions:
                    location_part = word
                elif word_clean in ['INC', 'INC.', 'INCORPORATED', 'CHAPTER', 'CHAPTERS']:
                    other_parts.append(word)
                elif len(word_clean) > 3:  # Likely a location or other word
                    other_parts.append(word)
                else:
                    expanded_parts.append(word)
            
            # If we expanded something, create multiple variations
            if expanded_parts and any(exp in abbreviation_expansions.values() for exp in expanded_parts):
                full_name = ' '.join(expanded_parts)
                
                # Generate variations
                variations = []
                
                if location_part:
                    location_expanded = location_expansions.get(location_part.upper(), location_part)
                    
                    # Variation 1: Full name + location abbreviation
                    variations.append(f"{full_name} {location_part}")
                    
                    # Variation 2: Full name + location expanded
                    variations.append(f"{full_name} {location_expanded}")
                    
                    # Variation 3: Abbreviation + location expanded + Chapter Inc
                    variations.append(f"{company_name.split()[0]} {location_expanded} Chapter Inc")
                    variations.append(f"{company_name.split()[0]} {location_expanded} Chapter")
                    
                    # Variation 4: Full name + location expanded + Chapter Inc
                    variations.append(f"{full_name} {location_expanded} Chapter Inc")
                    variations.append(f"{full_name} {location_expanded} Chapter")
                    
                    # Variation 5: Abbreviation + location expanded + Inc (no Chapter)
                    variations.append(f"{company_name.split()[0]} {location_expanded} Inc")
                    
                    # Variation 6: Full name + location expanded + Inc (no Chapter)
                    variations.append(f"{full_name} {location_expanded} Inc")
                    
                    # Variation 7: Try with "Chapter" before location
                    variations.append(f"{full_name} Chapter {location_expanded} Inc")
                    variations.append(f"{company_name.split()[0]} Chapter {location_expanded} Inc")
                else:
                    # No location, just add Inc/Chapter variations
                    variations.append(full_name)
                    variations.append(f"{full_name} Inc")
                    variations.append(f"{full_name} Chapter Inc")
                    variations.append(f"{company_name.split()[0]} Inc")
                    variations.append(f"{company_name.split()[0]} Chapter Inc")
                
                # Add all variations
                search_terms.extend(variations)
            else:
                # Even if not expanded, try adding Inc/Chapter variations
                if not has_inc:
                    search_terms.append(f"{company_name} Inc")
                    search_terms.append(f"{company_name} Incorporated")
                if not has_chapter:
                    search_terms.append(f"{company_name} Chapter")
                    search_terms.append(f"{company_name} Chapter Inc")
        
        # Also try variations with common suffixes even if not an abbreviation
        if not has_inc and not any(w.upper() in ['INC', 'INC.', 'INCORPORATED'] for w in words):
            search_terms.append(f"{company_name} Inc")
            search_terms.append(f"{company_name} Incorporated")
        
        if not has_chapter and not any('chapter' in w.lower() for w in words):
            search_terms.append(f"{company_name} Chapter")
            search_terms.append(f"{company_name} Chapter Inc")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_terms = []
        for term in search_terms:
            term_lower = term.lower().strip()
            if term_lower and term_lower not in seen:
                seen.add(term_lower)
                unique_terms.append(term)
        
        return unique_terms
    
    def enrich_member_with_form_990(self, company_name: str, 
                                     state: Optional[str] = None,
                                     city: Optional[str] = None,
                                     ein: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Enrich member company with Form 990 data.
        
        Args:
            company_name: Company name from HubSpot (may be abbreviated)
            state: Optional state (for better matching)
            ein: Optional EIN (if available)
        
        Returns:
            Enriched data dictionary or None
        """
        # If EIN provided, use it directly
        if ein:
            org = self.get_organization_by_ein(ein)
            if org:
                return {
                    'found': True,
                    'method': 'ein',
                    'organization': org,
                    'financials': self.get_organization_financials(ein)
                }
        
        # Expand abbreviations to get full names (ProPublica has full legal names)
        search_terms = self._expand_abbreviations(company_name, city, state)
        logger.debug(f"ProPublica search terms for '{company_name}': {search_terms}")
        
        # Try each search term until we find a match
        # Add delay between search attempts to avoid rate limits
        org = None
        for idx, search_term in enumerate(search_terms):
            try:
                # Add extra delay between multiple search attempts (except first)
                if idx > 0:
                    time.sleep(0.5)  # Small delay between search term attempts
                
                org = self.find_organization_by_name(search_term, state=state, city=city)
                if org:
                    logger.info(f"Found ProPublica match using search term '{search_term}' (original: '{company_name}')")
                    break
            except Exception as e:
                logger.debug(f"Error searching ProPublica with '{search_term}': {e}")
                # If rate limit error, wait longer before next attempt
                if "429" in str(e) or "rate limit" in str(e).lower():
                    wait_time = min(30, 2 ** idx)  # Exponential backoff
                    logger.warning(f"Rate limit detected, waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                continue
        
        if not org:
            logger.warning(f"No ProPublica match found for '{company_name}' using any search terms")
        
        if org:
            ein = org.get('ein')
            # Get financials if we have an EIN
            financials = None
            if ein:
                try:
                    financials = self.get_organization_financials(ein)
                except Exception as e:
                    logger.warning(f"Error getting financials for EIN {ein}: {e}")
                    financials = None
            
            return {
                'found': True,
                'method': 'name_search',
                'organization': org,
                'financials': financials,
                'match_confidence': 'medium'  # Could be improved with fuzzy matching
            }
        
        return {
            'found': False,
            'method': 'name_search',
            'organization': None,
            'financials': None
        }


# Example usage
if __name__ == "__main__":
    client = ProPublicaClient()
    
    # Example 1: Search by name
    print("Searching for 'National Community Reinvestment Coalition'...")
    results = client.search_organizations("National Community Reinvestment Coalition", limit=3)
    for org in results:
        print(f"  - {org.get('name')} (EIN: {org.get('ein')})")
    
    # Example 2: Get by EIN
    print("\nGetting organization by EIN...")
    org = client.get_organization_by_ein("52-2098765")
    if org:
        print(f"  Name: {org.get('name')}")
        print(f"  Total Revenue: ${org.get('total_revenue', 'N/A')}")
    
    # Example 3: Enrich member
    print("\nEnriching member company...")
    enriched = client.enrich_member_with_form_990(
        company_name="National Community Reinvestment Coalition",
        state="DC"
    )
    if enriched['found']:
        print(f"  Found: {enriched['organization'].get('name')}")
        if enriched['financials']:
            print(f"  Total Revenue: ${enriched['financials'].get('total_revenue', 'N/A')}")

