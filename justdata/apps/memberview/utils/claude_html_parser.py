"""
Claude-powered HTML parser for extracting structured data from organization websites.
Uses Anthropic's Claude API to intelligently parse HTML and extract staff, contact, and other information.
"""
import os
import json
import logging
import time
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("anthropic package not installed. Claude parsing will not be available.")


class ClaudeHTMLParser:
    """Parse HTML using Claude API to extract structured data."""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize Claude HTML parser.
        
        Args:
            cache_dir: Directory to cache parsed results
        """
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic package is required. Install with: pip install anthropic")
        
        # Check for both ANTHROPIC_API_KEY and CLAUDE_API_KEY
        api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY or CLAUDE_API_KEY environment variable not set")
        
        self.client = Anthropic(api_key=api_key)
        
        if cache_dir is None:
            self.cache_dir = Path(__file__).parent.parent.parent / "data" / "enriched_data"
        else:
            self.cache_dir = Path(cache_dir)
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.parsing_cache = self.cache_dir / "claude_parsing_cache.json"
        self._cache = self._load_cache()
        
        # Rate limiting for Claude API
        self.last_claude_call_time = 0
        self.claude_rate_limit_delay = 1.0  # 1 second between Claude API calls
        self.consecutive_errors = 0
    
    def _load_cache(self) -> Dict[str, Any]:
        """Load parsing cache from file."""
        if self.parsing_cache.exists():
            try:
                with open(self.parsing_cache, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load parsing cache: {e}")
        return {}
    
    def _save_cache(self):
        """Save parsing cache to file."""
        try:
            with open(self.parsing_cache, 'w') as f:
                json.dump(self._cache, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save parsing cache: {e}")
    
    def extract_staff_from_html(self, html: str, url: str) -> List[Dict[str, str]]:
        """
        Extract staff/leadership information from HTML using Claude.
        
        Args:
            html: HTML content
            url: Source URL (for caching)
            
        Returns:
            List of staff members with name, title, email, phone
        """
        # Check cache
        cache_key = f"{url}_staff"
        if cache_key in self._cache:
            cached_result = self._cache[cache_key]
            logger.debug(f"Using cached staff data for {url}: {len(cached_result)} staff members")
            return cached_result
        
        # Truncate HTML to stay within token limits (50K chars max)
        html_truncated = html[:50000] if len(html) > 50000 else html
        
        prompt = f"""Extract staff and leadership information from this HTML page. 
Look for sections titled "Staff", "Team", "Leadership", "Board of Directors", "About Us", "Who We Are", etc.

Return a JSON object with this structure:
{{
  "executive_staff": [
    {{"name": "Full Name", "title": "Job Title", "email": "email@example.com" or null, "phone": "phone number" or null}}
  ],
  "board_members": [
    {{"name": "Full Name", "title": "Board Position", "email": "email@example.com" or null, "phone": "phone number" or null, "affiliation": "organization or company name" or null}}
  ]
}}

Extract all staff members, executives, and board members you can find. Include their names and titles.
If email addresses, phone numbers, or affiliations are listed, include them. If not available, use null.

HTML content:
{html_truncated}

Return only valid JSON, no other text."""
        
        try:
            # Rate limit Claude API calls
            current_time = time.time()
            time_since_last = current_time - self.last_claude_call_time
            if time_since_last < self.claude_rate_limit_delay:
                sleep_time = self.claude_rate_limit_delay - time_since_last
                logger.debug(f"Rate limiting Claude API: waiting {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
            self.last_claude_call_time = time.time()
            
            logger.info(f"Calling Claude API to extract staff from {url} (HTML length: {len(html_truncated)} chars)...")
            try:
                message = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4000,
                    messages=[{"role": "user", "content": prompt}]
                )
                self.consecutive_errors = 0  # Reset on success
            except Exception as api_error:
                # Handle rate limit errors
                if "rate limit" in str(api_error).lower() or "429" in str(api_error):
                    self.consecutive_errors += 1
                    wait_time = min(60, 2 ** self.consecutive_errors)  # Exponential backoff, max 60s
                    logger.warning(f"Claude API rate limit detected. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    # Retry once
                    message = self.client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=4000,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    self.consecutive_errors = 0
                else:
                    raise api_error
            
            # Extract JSON from response
            response_text = message.content[0].text.strip()
            logger.debug(f"Claude response length: {len(response_text)} characters")
            
            # Try to extract JSON if wrapped in markdown code blocks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            # Parse JSON
            try:
                data = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse Claude JSON response: {e}")
                logger.debug(f"Response text (first 500 chars): {response_text[:500]}")
                # Try to extract JSON object from text
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    try:
                        data = json.loads(json_match.group())
                    except:
                        raise e
                else:
                    raise e
            
            # Log what we got from Claude
            logger.debug(f"Claude returned data keys: {list(data.keys())}")
            
            # Combine executive staff and board members into single list
            staff_list = []
            
            if data.get('executive_staff'):
                logger.debug(f"Found {len(data['executive_staff'])} executive staff")
                for person in data['executive_staff']:
                    if person.get('name'):  # Only add if name exists
                        staff_list.append({
                            'name': person.get('name', ''),
                            'title': person.get('title', ''),
                            'email': person.get('email'),
                            'phone': person.get('phone'),
                            'type': 'staff'
                        })
            
            if data.get('board_members'):
                logger.debug(f"Found {len(data['board_members'])} board members")
                for person in data['board_members']:
                    if person.get('name'):  # Only add if name exists
                        staff_list.append({
                            'name': person.get('name', ''),
                            'title': person.get('title', ''),
                            'email': person.get('email'),
                            'phone': person.get('phone'),
                            'affiliation': person.get('affiliation'),
                            'type': 'board'
                        })
            
            # Cache result
            self._cache[cache_key] = staff_list
            self._save_cache()
            
            logger.info(f"Claude extracted {len(staff_list)} staff/board members from {url}")
            if len(staff_list) == 0:
                logger.warning(f"No staff found. Claude response data: {json.dumps(data, indent=2)[:500]}")
            return staff_list
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse Claude JSON response for {url}: {e}")
            logger.debug(f"Response was: {response_text[:500]}")
            return []
        except Exception as e:
            logger.warning(f"Error using Claude to extract staff from {url}: {e}")
            return []
    
    def extract_organization_info(self, html: str, url: str) -> Dict[str, Any]:
        """
        Extract comprehensive organization information from HTML using Claude.
        Includes: funders/partners, major areas of work, affiliations, contact info, etc.
        
        Args:
            html: HTML content
            url: Source URL (for caching)
            
        Returns:
            Dictionary with organization information
        """
        # Check cache
        cache_key = f"{url}_org_info"
        if cache_key in self._cache:
            logger.debug(f"Using cached org info for {url}")
            return self._cache[cache_key]
        
        # Truncate HTML
        html_truncated = html[:50000] if len(html) > 50000 else html
        
        prompt = f"""Extract comprehensive organization information from this HTML page.
Look for information about:
- Funders, partners, sponsors, supporters (often in "Partners", "Funders", "Supporters", "Sponsors" sections)
- Major areas of work, programs, services, focus areas
- Affiliations (memberships, networks, coalitions)
- Contact information (emails, phones, addresses)
- Mission, vision, values

Return a JSON object with this structure:
{{
  "funders_partners": [
    {{"name": "Organization Name", "type": "funder" or "partner" or "sponsor", "description": "brief description" or null}}
  ],
  "major_areas_of_work": [
    "Area 1", "Area 2", "Area 3"
  ],
  "affiliations": [
    {{"name": "Organization/Network Name", "type": "membership" or "coalition" or "network" or null}}
  ],
  "contact_info": {{
    "emails": ["email1@example.com", "email2@example.com"],
    "phones": ["(123) 456-7890", "+1-234-567-8900"],
    "addresses": ["123 Main St, City, State 12345"]
  }},
  "mission": "mission statement" or null,
  "programs_services": [
    "Program/Service 1", "Program/Service 2"
  ]
}}

Extract all relevant information you can find. If a field has no data, use an empty array or null.

HTML content:
{html_truncated}

Return only valid JSON, no other text."""
        
        try:
            # Rate limit Claude API calls
            current_time = time.time()
            time_since_last = current_time - self.last_claude_call_time
            if time_since_last < self.claude_rate_limit_delay:
                sleep_time = self.claude_rate_limit_delay - time_since_last
                logger.debug(f"Rate limiting Claude API: waiting {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
            self.last_claude_call_time = time.time()
            
            logger.info(f"Calling Claude API to extract org info from {url}...")
            try:
                message = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4000,
                    messages=[{"role": "user", "content": prompt}]
                )
                self.consecutive_errors = 0  # Reset on success
            except Exception as api_error:
                # Handle rate limit errors
                if "rate limit" in str(api_error).lower() or "429" in str(api_error):
                    self.consecutive_errors += 1
                    wait_time = min(60, 2 ** self.consecutive_errors)  # Exponential backoff, max 60s
                    logger.warning(f"Claude API rate limit detected. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    # Retry once
                    message = self.client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=4000,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    self.consecutive_errors = 0
                else:
                    raise api_error
            
            response_text = message.content[0].text.strip()
            
            # Extract JSON
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            data = json.loads(response_text)
            
            # Structure the result
            org_info = {
                'funders_partners': data.get('funders_partners', [])[:20],  # Limit to 20
                'major_areas_of_work': data.get('major_areas_of_work', [])[:15],  # Limit to 15
                'affiliations': data.get('affiliations', [])[:15],  # Limit to 15
                'contact_info': data.get('contact_info', {'emails': [], 'phones': [], 'addresses': []}),
                'mission': data.get('mission'),
                'programs_services': data.get('programs_services', [])[:20]  # Limit to 20
            }
            
            # Cache result
            self._cache[cache_key] = org_info
            self._save_cache()
            
            logger.info(f"Claude extracted org info from {url}")
            return org_info
            
        except Exception as e:
            logger.warning(f"Error using Claude to extract org info from {url}: {e}")
            return {
                'funders_partners': [],
                'major_areas_of_work': [],
                'affiliations': [],
                'contact_info': {'emails': [], 'phones': [], 'addresses': []},
                'mission': None,
                'programs_services': []
            }
    
    def extract_contacts_from_html(self, html: str, url: str) -> Dict[str, List[str]]:
        """
        Extract contact information from HTML using Claude.
        
        Args:
            html: HTML content
            url: Source URL (for caching)
            
        Returns:
            Dictionary with emails, phones, addresses
        """
        # Check cache
        cache_key = f"{url}_contacts"
        if cache_key in self._cache:
            logger.debug(f"Using cached contact data for {url}")
            return self._cache[cache_key]
        
        # Truncate HTML
        html_truncated = html[:50000] if len(html) > 50000 else html
        
        prompt = f"""Extract contact information from this HTML page.
Look for email addresses, phone numbers, and physical/mailing addresses.

Return a JSON object with this structure:
{{
  "emails": ["email1@example.com", "email2@example.com"],
  "phones": ["(123) 456-7890", "+1-234-567-8900"],
  "addresses": ["123 Main St, City, State 12345"]
}}

Extract all contact information you can find. If a field has no data, use an empty array.

HTML content:
{html_truncated}

Return only valid JSON, no other text."""
        
        try:
            # Rate limit Claude API calls
            current_time = time.time()
            time_since_last = current_time - self.last_claude_call_time
            if time_since_last < self.claude_rate_limit_delay:
                sleep_time = self.claude_rate_limit_delay - time_since_last
                logger.debug(f"Rate limiting Claude API: waiting {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
            self.last_claude_call_time = time.time()
            
        try:
            # Rate limit Claude API calls
            current_time = time.time()
            time_since_last = current_time - self.last_claude_call_time
            if time_since_last < self.claude_rate_limit_delay:
                sleep_time = self.claude_rate_limit_delay - time_since_last
                logger.debug(f"Rate limiting Claude API: waiting {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
            self.last_claude_call_time = time.time()
            
            try:
                message = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}]
                )
                self.consecutive_errors = 0  # Reset on success
            except Exception as api_error:
                # Handle rate limit errors
                if "rate limit" in str(api_error).lower() or "429" in str(api_error):
                    self.consecutive_errors += 1
                    wait_time = min(60, 2 ** self.consecutive_errors)  # Exponential backoff, max 60s
                    logger.warning(f"Claude API rate limit detected. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    # Retry once
                    message = self.client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=2000,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    self.consecutive_errors = 0
                else:
                    raise api_error
                self.consecutive_errors = 0  # Reset on success
            except Exception as api_error:
                # Handle rate limit errors
                if "rate limit" in str(api_error).lower() or "429" in str(api_error):
                    self.consecutive_errors += 1
                    wait_time = min(60, 2 ** self.consecutive_errors)  # Exponential backoff, max 60s
                    logger.warning(f"Claude API rate limit detected. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    # Retry once
                    message = self.client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=2000,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    self.consecutive_errors = 0
                else:
                    raise api_error
            
            response_text = message.content[0].text.strip()
            
            # Extract JSON
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            data = json.loads(response_text)
            
            contacts = {
                'emails': data.get('emails', [])[:10],  # Limit to 10
                'phones': data.get('phones', [])[:5],   # Limit to 5
                'addresses': data.get('addresses', [])[:3]  # Limit to 3
            }
            
            # Cache result
            self._cache[cache_key] = contacts
            self._save_cache()
            
            logger.info(f"Claude extracted contacts from {url}")
            return contacts
            
        except Exception as e:
            logger.warning(f"Error using Claude to extract contacts from {url}: {e}")
            return {'emails': [], 'phones': [], 'addresses': []}
