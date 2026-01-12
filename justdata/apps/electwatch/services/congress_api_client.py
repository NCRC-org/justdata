"""
Congress.gov API Client for ElectWatch.
Fetches bill information, sponsors, cosponsors, vote records, and member data.
"""

import os
import re
import requests
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class CongressAPIClient:
    BASE_URL = "https://api.congress.gov/v3"

    INDUSTRY_KEYWORDS = {
        'crypto': ['cryptocurrency', 'crypto', 'digital asset', 'blockchain', 'bitcoin'],
        'banking': ['bank', 'banking', 'depository', 'fdic', 'federal reserve'],
        'mortgage': ['mortgage', 'housing finance', 'fannie mae', 'freddie mac'],
        'consumer_lending': ['consumer credit', 'cfpb', 'consumer protection'],
        'investment': ['securities', 'sec', 'investment', 'broker'],
        'insurance': ['insurance', 'insurer', 'underwriting'],
        'fintech': ['fintech', 'financial technology', 'payment']
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('CONGRESS_GOV_API_KEY', '')
        self.session = requests.Session()
        if self.api_key:
            self.session.params = {'api_key': self.api_key}

    def get_all_members(self, congress: str = '119') -> List[Dict]:
        """Get all members of Congress (House + Senate)."""
        from datetime import datetime as dt

        if not self.api_key:
            logger.warning('No Congress API key available')
            return []

        all_members = []
        offset = 0
        limit = 250

        while True:
            params = {'limit': limit, 'offset': offset, 'currentMember': 'true'}
            data = self._make_request(f'member/congress/{congress}', params)

            if not data or 'members' not in data:
                break

            members = data['members']
            if not members:
                break

            for m in members:
                terms = m.get('terms', {}).get('item', [])
                latest_term = terms[-1] if terms else {}
                chamber = 'senate' if latest_term.get('chamber') == 'Senate' else 'house'
                bioguide_id = m.get('bioguideId', '')

                member = {
                    'name': m.get('name', ''),
                    'bioguide_id': bioguide_id,
                    'party': self._normalize_party(m.get('partyName', '')),
                    'state': m.get('state', ''),
                    'district': m.get('district'),
                    'chamber': chamber,
                    'photo_url': f'https://bioguide.congress.gov/bioguide/photo/{bioguide_id[0]}/{bioguide_id}.jpg' if bioguide_id else None,
                    'years_in_congress': self._calculate_years_served(m.get('terms', {})),
                    'has_financial_activity': False,
                    'trades': [],
                    'top_financial_pacs': [],
                    'financial_sector_score': 0,
                }
                all_members.append(member)

            offset += limit
            if offset > 600:
                break

        logger.info(f'Fetched {len(all_members)} members from Congress.gov')
        return all_members

    def _normalize_party(self, party_name: str) -> str:
        party_map = {'Republican': 'R', 'Democratic': 'D', 'Democrat': 'D', 'Independent': 'I'}
        return party_map.get(party_name, party_name[0] if party_name else 'U')

    def _calculate_years_served(self, terms: Dict) -> int:
        from datetime import datetime as dt
        term_items = terms.get('item', [])
        if not term_items:
            return 0
        total_years = 0
        current_year = dt.now().year
        for term in term_items:
            start_year = term.get('startYear', current_year)
            end_year = term.get('endYear', current_year)
            total_years += (end_year - start_year) if end_year else (current_year - start_year)
        return total_years

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        url = f"{self.BASE_URL}/{endpoint}"
        try:
            params = params or {}
            if self.api_key:
                params['api_key'] = self.api_key
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Congress API request failed: {e}")
            return None

    def parse_bill_id(self, bill_input: str) -> Optional[Dict[str, str]]:
        bill_input = bill_input.upper().strip()
        patterns = [r'^H\.?\s*R\.?\s*(\d+)$', r'^S\.?\s*(\d+)$']
        type_map = {0: 'hr', 1: 's'}
        for i, pattern in enumerate(patterns):
            match = re.match(pattern, bill_input)
            if match:
                return {'type': type_map[i], 'number': match.group(1), 'congress': '119'}
        return None

    def search_bills(self, query: str, limit: int = 20) -> List[Dict]:
        if not self.api_key:
            return []
        data = self._make_request('bill', {'q': query, 'limit': limit})
        if not data or 'bills' not in data:
            return []
        return [{'bill_id': b.get('number', ''), 'title': b.get('title', '')} for b in data['bills']]

    def get_bill(self, bill_type: str, bill_number: str, congress: str = '119') -> Optional[Dict]:
        if not self.api_key:
            return None
        data = self._make_request(f'bill/{congress}/{bill_type}/{bill_number}')
        if not data or 'bill' not in data:
            return None
        bill = data['bill']
        return {
            'bill_id': f"{bill_type.upper()}{bill_number}",
            'title': bill.get('title', ''),
            'congress': congress,
        }


_client = None

def get_congress_client() -> CongressAPIClient:
    global _client
    if _client is None:
        _client = CongressAPIClient()
    return _client
