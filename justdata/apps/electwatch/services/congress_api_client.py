"""
Congress.gov API Client for ElectWatch.

Fetches bill information, sponsors, cosponsors, and vote records.
API Documentation: https://api.congress.gov/

Note: Congress.gov API requires an API key for production use.
Get one at: https://api.congress.gov/sign-up/
"""

import os
import re
import requests
from typing import Dict, List, Optional, Any
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


class CongressAPIClient:
    """Client for Congress.gov API to fetch bill and vote data."""

    BASE_URL = "https://api.congress.gov/v3"

    # Keywords to map bills to industries
    INDUSTRY_KEYWORDS = {
        'crypto': [
            'cryptocurrency', 'crypto', 'digital asset', 'blockchain',
            'bitcoin', 'stablecoin', 'virtual currency', 'cbdc',
            'central bank digital', 'defi', 'token'
        ],
        'banking': [
            'bank', 'banking', 'depository', 'fdic', 'federal reserve',
            'credit union', 'bank merger', 'bank holding', 'basel',
            'capital requirements', 'systemic risk'
        ],
        'mortgage': [
            'mortgage', 'housing finance', 'fannie mae', 'freddie mac',
            'fha', 'home loan', 'foreclosure', 'gse', 'housing',
            'real estate finance'
        ],
        'consumer_lending': [
            'consumer credit', 'cfpb', 'consumer protection', 'payday',
            'credit card', 'fair lending', 'predatory lending', 'usury',
            'debt collection', 'credit reporting', 'bnpl', 'buy now pay later'
        ],
        'investment': [
            'securities', 'sec', 'investment', 'broker', 'dealer',
            'hedge fund', 'private equity', 'asset management',
            'investment adviser', 'fiduciary', 'stock market'
        ],
        'insurance': [
            'insurance', 'insurer', 'underwriting', 'reinsurance',
            'life insurance', 'health insurance', 'property casualty'
        ],
        'fintech': [
            'fintech', 'financial technology', 'payment', 'money transmission',
            'remittance', 'mobile payment', 'digital payment', 'neobank'
        ]
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Congress API client.

        Args:
            api_key: Congress.gov API key. If not provided, uses CONGRESS_API_KEY env var.
        """
        self.api_key = api_key or os.getenv('CONGRESS_GOV_API_KEY', '')
        self.session = requests.Session()
        if self.api_key:
            self.session.params = {'api_key': self.api_key}

    
    def get_all_members(self, congress: str = '119') -> List[Dict]:
        """
        Get all members of Congress (House + Senate).
        Returns list of all 535 members with basic profile data.
        """
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
        """Calculate years in Congress from earliest term start to now."""
        from datetime import datetime as dt
        term_items = terms.get('item', [])
        if not term_items:
            return 0

        current_year = dt.now().year

        # Find the earliest start year across all terms
        earliest_start = current_year
        for term in term_items:
            start_year = term.get('startYear')
            if start_year and start_year < earliest_start:
                earliest_start = start_year

        # Calculate years from earliest start to now
        years_served = current_year - earliest_start
        return max(years_served, 1)  # At least 1 year if they have any terms

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make a request to the Congress.gov API."""
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
        """
        Parse a bill identifier into its components.

        Args:
            bill_input: Bill ID like "H.R. 4763", "HR4763", "S. 1234", "S1234"

        Returns:
            Dict with 'type', 'number', 'congress' keys or None if invalid
        """
        # Normalize input
        bill_input = bill_input.upper().strip()

        # Patterns for different bill formats
        patterns = [
            # H.R. 4763, H. R. 4763, HR 4763, HR4763
            r'^H\.?\s*R\.?\s*(\d+)$',
            # S. 1234, S 1234, S1234
            r'^S\.?\s*(\d+)$',
            # H.RES. 123, HRES123
            r'^H\.?\s*RES\.?\s*(\d+)$',
            # S.RES. 123
            r'^S\.?\s*RES\.?\s*(\d+)$',
            # H.J.RES. 123
            r'^H\.?\s*J\.?\s*RES\.?\s*(\d+)$',
            # S.J.RES. 123
            r'^S\.?\s*J\.?\s*RES\.?\s*(\d+)$',
        ]

        type_map = {
            0: 'hr',
            1: 's',
            2: 'hres',
            3: 'sres',
            4: 'hjres',
            5: 'sjres'
        }

        for i, pattern in enumerate(patterns):
            match = re.match(pattern, bill_input)
            if match:
                return {
                    'type': type_map[i],
                    'number': match.group(1),
                    'congress': '119'  # Current congress (2025-2027)
                }

        return None

    def search_bills(self, query: str, limit: int = 20) -> List[Dict]:
        """
        Search for bills by keyword.

        Args:
            query: Search query (e.g., "cryptocurrency", "stablecoin")
            limit: Maximum results to return

        Returns:
            List of bill summaries
        """
        # For now, return sample data since API key might not be available
        # In production, this would call the actual API
        if not self.api_key:
            return self._get_sample_bill_search(query)

        data = self._make_request('bill', {
            'q': query,
            'limit': limit,
            'sort': 'updateDate desc'
        })

        if not data or 'bills' not in data:
            return []

        return [self._format_bill_summary(b) for b in data['bills']]

    def get_bill(self, bill_type: str, bill_number: str, congress: str = '119') -> Optional[Dict]:
        """
        Get detailed information about a specific bill.

        Args:
            bill_type: 'hr', 's', 'hres', 'sres', 'hjres', 'sjres'
            bill_number: The bill number
            congress: Congress number (default 119 for 2025-2027)

        Returns:
            Bill details including sponsors, cosponsors, actions, and votes
        """
        # For demo, return sample data
        if not self.api_key:
            return self._get_sample_bill(bill_type, bill_number)

        data = self._make_request(f'bill/{congress}/{bill_type}/{bill_number}')

        if not data or 'bill' not in data:
            return None

        bill = data['bill']

        # Get additional details
        sponsors = self._get_bill_sponsors(congress, bill_type, bill_number)
        cosponsors = self._get_bill_cosponsors(congress, bill_type, bill_number)
        actions = self._get_bill_actions(congress, bill_type, bill_number)

        return {
            'bill_id': f"{bill_type.upper()}{bill_number}",
            'title': bill.get('title', ''),
            'short_title': bill.get('shortTitle', bill.get('title', '')[:100]),
            'congress': congress,
            'introduced_date': bill.get('introducedDate', ''),
            'latest_action': bill.get('latestAction', {}),
            'sponsors': sponsors,
            'cosponsors': cosponsors,
            'actions': actions,
            'industries': self._detect_industries(bill.get('title', '') + ' ' + bill.get('summary', '')),
            'policy_area': bill.get('policyArea', {}).get('name', ''),
            'committees': [c.get('name', '') for c in bill.get('committees', {}).get('item', [])]
        }

    def _get_bill_sponsors(self, congress: str, bill_type: str, bill_number: str) -> List[Dict]:
        """Get bill sponsors."""
        data = self._make_request(f'bill/{congress}/{bill_type}/{bill_number}/sponsors')
        if not data:
            return []
        return data.get('sponsors', [])

    def _get_bill_cosponsors(self, congress: str, bill_type: str, bill_number: str) -> List[Dict]:
        """Get bill cosponsors."""
        data = self._make_request(f'bill/{congress}/{bill_type}/{bill_number}/cosponsors')
        if not data:
            return []
        return data.get('cosponsors', [])

    def _get_bill_actions(self, congress: str, bill_type: str, bill_number: str) -> List[Dict]:
        """Get bill actions/votes."""
        data = self._make_request(f'bill/{congress}/{bill_type}/{bill_number}/actions')
        if not data:
            return []
        return data.get('actions', [])

    def _detect_industries(self, text: str) -> List[str]:
        """Detect which industries a bill relates to based on keywords."""
        text_lower = text.lower()
        industries = []

        for industry, keywords in self.INDUSTRY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    if industry not in industries:
                        industries.append(industry)
                    break

        return industries

    def _format_bill_summary(self, bill: Dict) -> Dict:
        """Format a bill for display."""
        return {
            'bill_id': bill.get('number', ''),
            'title': bill.get('title', ''),
            'congress': bill.get('congress', ''),
            'introduced_date': bill.get('introducedDate', ''),
            'latest_action': bill.get('latestAction', {}).get('text', ''),
            'sponsor': bill.get('sponsor', {}).get('name', 'Unknown')
        }

    def _get_sample_bill_search(self, query: str) -> List[Dict]:
        """Return sample bill search results for demo."""
        query_lower = query.lower()

        sample_bills = [
            {
                'bill_id': 'H.R. 4763',
                'title': 'Financial Innovation and Technology for the 21st Century Act (FIT21)',
                'short_title': 'FIT21 Act',
                'congress': '119',
                'introduced_date': '2025-03-15',
                'latest_action': 'Passed House 279-136',
                'sponsor': 'Rep. French Hill (R-AR)',
                'industries': ['crypto', 'fintech'],
                'keywords': ['crypto', 'digital asset', 'cryptocurrency', 'fit21', 'blockchain']
            },
            {
                'bill_id': 'H.R. 5403',
                'title': 'CBDC Anti-Surveillance State Act',
                'short_title': 'CBDC Anti-Surveillance Act',
                'congress': '119',
                'introduced_date': '2025-02-08',
                'latest_action': 'Passed House 216-192',
                'sponsor': 'Rep. Tom Emmer (R-MN)',
                'industries': ['crypto', 'banking'],
                'keywords': ['cbdc', 'digital currency', 'central bank', 'crypto', 'surveillance']
            },
            {
                'bill_id': 'H.R. 4766',
                'title': 'Clarity for Payment Stablecoins Act',
                'short_title': 'Stablecoin Act',
                'congress': '119',
                'introduced_date': '2025-04-20',
                'latest_action': 'Reported by Committee',
                'sponsor': 'Rep. Patrick McHenry (R-NC)',
                'industries': ['crypto', 'banking'],
                'keywords': ['stablecoin', 'crypto', 'payment', 'digital dollar']
            },
            {
                'bill_id': 'S. 2281',
                'title': 'Lummis-Gillibrand Responsible Financial Innovation Act',
                'short_title': 'Crypto Innovation Act',
                'congress': '119',
                'introduced_date': '2025-05-10',
                'latest_action': 'Referred to Committee on Banking',
                'sponsor': 'Sen. Cynthia Lummis (R-WY)',
                'industries': ['crypto', 'fintech'],
                'keywords': ['crypto', 'innovation', 'digital asset', 'bitcoin', 'lummis']
            },
            {
                'bill_id': 'H.R. 1112',
                'title': 'Consumer Financial Protection Bureau Accountability Act',
                'short_title': 'CFPB Accountability Act',
                'congress': '119',
                'introduced_date': '2025-01-20',
                'latest_action': 'In Committee',
                'sponsor': 'Rep. Andy Barr (R-KY)',
                'industries': ['consumer_lending', 'banking'],
                'keywords': ['cfpb', 'consumer', 'protection', 'banking', 'regulation']
            },
            {
                'bill_id': 'H.R. 2890',
                'title': 'Bank Merger Review Modernization Act',
                'short_title': 'Bank Merger Act',
                'congress': '119',
                'introduced_date': '2025-02-14',
                'latest_action': 'Markup scheduled',
                'sponsor': 'Rep. French Hill (R-AR)',
                'industries': ['banking'],
                'keywords': ['bank', 'merger', 'consolidation', 'fdic', 'occ']
            },
            {
                'bill_id': 'S. 1450',
                'title': 'Housing Finance Reform Act',
                'short_title': 'GSE Reform Act',
                'congress': '119',
                'introduced_date': '2025-03-01',
                'latest_action': 'Hearings held',
                'sponsor': 'Sen. Tim Scott (R-SC)',
                'industries': ['mortgage', 'banking'],
                'keywords': ['housing', 'mortgage', 'fannie', 'freddie', 'gse', 'finance']
            },
            {
                'bill_id': 'H.R. 3340',
                'title': 'Protecting Consumers from Payment Scams Act',
                'short_title': 'Payment Scams Act',
                'congress': '119',
                'introduced_date': '2025-04-05',
                'latest_action': 'Referred to Financial Services',
                'sponsor': 'Rep. Maxine Waters (D-CA)',
                'industries': ['consumer_lending', 'fintech'],
                'keywords': ['consumer', 'payment', 'scam', 'fraud', 'protection', 'zelle']
            },
        ]

        # Filter by query
        results = []
        for bill in sample_bills:
            if any(query_lower in kw for kw in bill.get('keywords', [])):
                results.append(bill)
            elif query_lower in bill['title'].lower():
                results.append(bill)
            elif query_lower in bill['bill_id'].lower().replace('.', '').replace(' ', ''):
                results.append(bill)

        # If no matches, return all as "related"
        if not results and query:
            results = sample_bills[:5]

        return results

    def _get_sample_bill(self, bill_type: str, bill_number: str) -> Optional[Dict]:
        """Return sample bill data for demo."""
        sample_bills = {
            ('hr', '4763'): {
                'bill_id': 'H.R. 4763',
                'title': 'Financial Innovation and Technology for the 21st Century Act',
                'short_title': 'FIT21 Act',
                'congress': '119',
                'introduced_date': '2025-03-15',
                'latest_action': {
                    'date': '2025-05-22',
                    'text': 'Passed House by recorded vote: 279-136'
                },
                'policy_area': 'Finance and Financial Sector',
                'industries': ['crypto', 'fintech'],
                'committees': ['House Financial Services', 'House Agriculture'],
                'summary': 'Establishes a regulatory framework for digital assets, clarifying SEC and CFTC jurisdiction over cryptocurrencies and providing consumer protections.',
                'sponsors': [
                    {
                        'bioguide_id': 'H001072',
                        'name': 'J. French Hill',
                        'party': 'R',
                        'state': 'AR',
                        'district': '2',
                        'official_id': 'hill_j_french'
                    }
                ],
                'cosponsors': [
                    {'name': 'Patrick McHenry', 'party': 'R', 'state': 'NC', 'official_id': 'mchenry_patrick'},
                    {'name': 'Tom Emmer', 'party': 'R', 'state': 'MN', 'official_id': 'emmer_tom'},
                    {'name': 'Ritchie Torres', 'party': 'D', 'state': 'NY', 'official_id': 'torres_ritchie'},
                    {'name': 'Warren Davidson', 'party': 'R', 'state': 'OH', 'official_id': 'davidson_warren'},
                    {'name': 'Bill Huizenga', 'party': 'R', 'state': 'MI', 'official_id': 'huizenga_bill'},
                ],
                'votes': [
                    {
                        'date': '2025-05-22',
                        'chamber': 'house',
                        'result': 'Passed',
                        'yea': 279,
                        'nay': 136,
                        'not_voting': 17,
                        'positions': [
                            {'name': 'J. French Hill', 'party': 'R', 'state': 'AR', 'vote': 'Yea', 'official_id': 'hill_j_french'},
                            {'name': 'Maxine Waters', 'party': 'D', 'state': 'CA', 'vote': 'Nay', 'official_id': 'waters_maxine'},
                            {'name': 'Patrick McHenry', 'party': 'R', 'state': 'NC', 'vote': 'Yea', 'official_id': 'mchenry_patrick'},
                            {'name': 'Tom Emmer', 'party': 'R', 'state': 'MN', 'vote': 'Yea', 'official_id': 'emmer_tom'},
                            {'name': 'Nancy Pelosi', 'party': 'D', 'state': 'CA', 'vote': 'Nay', 'official_id': 'pelosi_nancy'},
                            {'name': 'Ritchie Torres', 'party': 'D', 'state': 'NY', 'vote': 'Yea', 'official_id': 'torres_ritchie'},
                            {'name': 'Warren Davidson', 'party': 'R', 'state': 'OH', 'vote': 'Yea', 'official_id': 'davidson_warren'},
                            {'name': 'Bill Foster', 'party': 'D', 'state': 'IL', 'vote': 'Yea', 'official_id': 'foster_bill'},
                            {'name': 'Brad Sherman', 'party': 'D', 'state': 'CA', 'vote': 'Nay', 'official_id': 'sherman_brad'},
                            {'name': 'Al Green', 'party': 'D', 'state': 'TX', 'vote': 'Nay', 'official_id': 'green_al'},
                        ]
                    }
                ]
            },
            ('hr', '5403'): {
                'bill_id': 'H.R. 5403',
                'title': 'CBDC Anti-Surveillance State Act',
                'short_title': 'CBDC Anti-Surveillance Act',
                'congress': '119',
                'introduced_date': '2025-02-08',
                'latest_action': {
                    'date': '2025-05-23',
                    'text': 'Passed House by recorded vote: 216-192'
                },
                'policy_area': 'Finance and Financial Sector',
                'industries': ['crypto', 'banking'],
                'committees': ['House Financial Services'],
                'summary': 'Prohibits the Federal Reserve from issuing a central bank digital currency (CBDC) directly to individuals.',
                'sponsors': [
                    {
                        'bioguide_id': 'E000294',
                        'name': 'Tom Emmer',
                        'party': 'R',
                        'state': 'MN',
                        'district': '6',
                        'official_id': 'emmer_tom'
                    }
                ],
                'cosponsors': [
                    {'name': 'J. French Hill', 'party': 'R', 'state': 'AR', 'official_id': 'hill_j_french'},
                    {'name': 'Warren Davidson', 'party': 'R', 'state': 'OH', 'official_id': 'davidson_warren'},
                ],
                'votes': [
                    {
                        'date': '2025-05-23',
                        'chamber': 'house',
                        'result': 'Passed',
                        'yea': 216,
                        'nay': 192,
                        'not_voting': 24,
                        'positions': [
                            {'name': 'Tom Emmer', 'party': 'R', 'state': 'MN', 'vote': 'Yea', 'official_id': 'emmer_tom'},
                            {'name': 'J. French Hill', 'party': 'R', 'state': 'AR', 'vote': 'Yea', 'official_id': 'hill_j_french'},
                            {'name': 'Maxine Waters', 'party': 'D', 'state': 'CA', 'vote': 'Nay', 'official_id': 'waters_maxine'},
                            {'name': 'Warren Davidson', 'party': 'R', 'state': 'OH', 'vote': 'Yea', 'official_id': 'davidson_warren'},
                        ]
                    }
                ]
            }
        }

        key = (bill_type.lower(), bill_number)
        return sample_bills.get(key)


# Singleton instance
_client = None


def get_congress_client() -> CongressAPIClient:
    """Get or create the Congress API client singleton."""
    global _client
    if _client is None:
        _client = CongressAPIClient()
    return _client
