"""
SEC EDGAR API Client for ElectWatch.

Fetches 10-K, 10-Q filings and company information from SEC EDGAR.
API Documentation: https://www.sec.gov/developer

No API key required - uses public SEC EDGAR endpoints.
"""

import os
import re
import requests
from typing import Dict, List, Optional, Any
from functools import lru_cache
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class SECClient:
    """Client for SEC EDGAR API to fetch company filings."""

    BASE_URL = "https://data.sec.gov"
    SUBMISSIONS_URL = "https://data.sec.gov/submissions"
    COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

    # User-Agent required by SEC
    HEADERS = {
        'User-Agent': 'NCRC ElectWatch research@ncrc.org',
        'Accept': 'application/json'
    }

    # CIK mappings for major financial firms (by ticker and name)
    FIRM_CIK_MAP = {
        # Tickers (uppercase) - SEC recommends using tickers for lookup
        'WFC': '0000072971',
        'JPM': '0000019617',
        'BAC': '0000070858',
        'C': '0000831001',
        'GS': '0000886982',
        'MS': '0000895421',
        'BLK': '0001364742',
        'COIN': '0001679788',
        'HOOD': '0001783879',
        'SQ': '0001512673',
        'V': '0001403161',
        'MA': '0001141391',
        'AXP': '0000004962',
        'COF': '0000927628',
        'DFS': '0001393612',
        'RKT': '0001805284',
        'UWMC': '0001783398',
        'SCHW': '0000316709',
        'IBKR': '0001381197',
        'PYPL': '0001633917',
        'INTU': '0000896878',
        'SOFI': '0001818874',
        'AFRM': '0001820953',
        'UPST': '0001647639',
        'LMND': '0001807707',
        'MKL': '0001096343',
        'PGR': '0000080661',
        'ALL': '0000899051',
        'MET': '0001099219',
        'PRU': '0001137774',
        'AIG': '0000005272',
        'MSTR': '0001050446',
        'MARA': '0001507605',
        'RIOT': '0001167419',
        # Company names (lowercase)
        'wells fargo': '0000072971',
        'jpmorgan chase': '0000019617',
        'jpmorgan': '0000019617',
        'bank of america': '0000070858',
        'citigroup': '0000831001',
        'goldman sachs': '0000886982',
        'morgan stanley': '0000895421',
        'blackrock': '0001364742',
        'coinbase': '0001679788',
        'robinhood': '0001783879',
        'block': '0001512673',
        'square': '0001512673',
        'visa': '0001403161',
        'mastercard': '0001141391',
        'american express': '0000004962',
        'capital one': '0000927628',
        'discover': '0001393612',
        'rocket companies': '0001805284',
        'united wholesale mortgage': '0001783398',
        'fidelity': '0000744461',
        'charles schwab': '0000316709',
        'interactive brokers': '0001381197',
        'paypal': '0001633917',
        'intuit': '0000896878',
        'sofi': '0001818874',
        'affirm': '0001820953',
        'upstart': '0001647639',
        'lemonade': '0001807707',
        'markel': '0001096343',
        'progressive': '0000080661',
        'allstate': '0000899051',
        'metlife': '0001099219',
        'prudential': '0001137774',
        'aig': '0000005272',
        'microstrategy': '0001050446',
        'marathon digital': '0001507605',
        'riot platforms': '0001167419',
    }

    def __init__(self):
        """Initialize the SEC client."""
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def _get_cik(self, firm_name: str) -> Optional[str]:
        """Get CIK number for a firm."""
        normalized = firm_name.lower().strip()

        # First try exact match
        if normalized.upper() in self.FIRM_CIK_MAP:
            return self.FIRM_CIK_MAP[normalized.upper()]
        if normalized in self.FIRM_CIK_MAP:
            return self.FIRM_CIK_MAP[normalized]

        # Then try substring match (only for multi-word names)
        for key, cik in self.FIRM_CIK_MAP.items():
            key_lower = key.lower()
            # Skip short keys for substring matching to avoid false positives
            if len(key_lower) <= 2:
                continue
            if key_lower in normalized or normalized in key_lower:
                return cik

        return None

    def _make_request(self, url: str) -> Optional[Dict]:
        """Make a request to SEC EDGAR."""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"SEC API request failed: {e}")
            return None

    def get_company_info(self, firm_name: str) -> Optional[Dict]:
        """Get company information including recent filings."""
        cik = self._get_cik(firm_name)
        if not cik:
            logger.warning(f"CIK not found for firm: {firm_name}")
            return None

        # Remove leading zeros for API call
        cik_stripped = cik.lstrip('0')
        url = f"{self.SUBMISSIONS_URL}/CIK{cik}.json"

        data = self._make_request(url)
        if not data:
            return None

        return {
            'cik': cik,
            'name': data.get('name', firm_name),
            'sic': data.get('sic'),
            'sic_description': data.get('sicDescription'),
            'tickers': data.get('tickers', []),
            'exchanges': data.get('exchanges', []),
            'filings': self._parse_filings(data.get('filings', {}))
        }

    def _parse_filings(self, filings_data: Dict) -> List[Dict]:
        """Parse filings data from SEC response."""
        recent = filings_data.get('recent', {})

        forms = recent.get('form', [])
        dates = recent.get('filingDate', [])
        accession_numbers = recent.get('accessionNumber', [])
        descriptions = recent.get('primaryDocument', [])

        filings = []
        for i in range(min(len(forms), 50)):  # Limit to 50 most recent
            form = forms[i]
            # Filter for relevant forms
            if form in ['10-K', '10-Q', '8-K', 'DEF 14A', '10-K/A', '10-Q/A']:
                filings.append({
                    'form': form,
                    'filing_date': dates[i] if i < len(dates) else None,
                    'accession_number': accession_numbers[i] if i < len(accession_numbers) else None,
                    'document': descriptions[i] if i < len(descriptions) else None,
                })

        return filings

    def get_recent_10k_10q(self, firm_name: str, limit: int = 5) -> List[Dict]:
        """Get recent 10-K and 10-Q filings for a firm."""
        company_info = self.get_company_info(firm_name)
        if not company_info:
            return []

        filings = company_info.get('filings', [])

        # Filter for 10-K and 10-Q only
        relevant = [f for f in filings if f['form'] in ['10-K', '10-Q', '10-K/A', '10-Q/A']]

        return relevant[:limit]

    def get_filing_url(self, cik: str, accession_number: str, document: str) -> str:
        """Construct URL to filing document."""
        # Format accession number (remove dashes)
        acc_no_formatted = accession_number.replace('-', '')
        return f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{acc_no_formatted}/{document}"

    def get_8k_filings(self, firm_name: str, limit: int = 10) -> List[Dict]:
        """Get recent 8-K filings (material events, investor communications)."""
        company_info = self.get_company_info(firm_name)
        if not company_info:
            return []

        filings = company_info.get('filings', [])

        # Filter for 8-K only
        relevant = [f for f in filings if f['form'] == '8-K']

        return relevant[:limit]


def get_sample_sec_data(firm_name: str) -> Dict:
    """
    Get sample SEC data for demo purposes.
    This provides realistic-looking data when API is not available.
    """
    # Normalize firm name
    normalized = firm_name.lower().strip()

    # Sample data for major firms
    sample_filings = {
        'wells fargo': {
            'cik': '0000072971',
            'ticker': 'WFC',
            'name': 'Wells Fargo & Company',
            'filings': [
                {
                    'form': '10-K',
                    'filing_date': '2025-02-21',
                    'description': 'Annual Report',
                    'url': 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000072971&type=10-K',
                    'highlights': [
                        'Total assets of $1.9 trillion as of December 31, 2024',
                        'Regulatory matters: Consent order with OCC ongoing',
                        'Litigation: Multiple class actions related to sales practices',
                        'CFPB enforcement action disclosed in Risk Factors section'
                    ]
                },
                {
                    'form': '10-Q',
                    'filing_date': '2025-10-28',
                    'description': 'Quarterly Report Q3 2025',
                    'url': '#',
                    'highlights': [
                        'Net income of $5.1B for Q3 2025',
                        'Continued progress on consent order remediation',
                        'Disclosed settlement discussions with DOJ'
                    ]
                },
            ],
            'regulatory_mentions': [
                {'agency': 'OCC', 'matter': 'Consent Order - Sales Practices', 'status': 'Ongoing'},
                {'agency': 'CFPB', 'matter': 'Auto Lending Practices Investigation', 'status': 'Under Review'},
                {'agency': 'Fed', 'matter': 'Asset Cap', 'status': 'In Effect'},
            ],
            'litigation': [
                {'case': 'In re Wells Fargo Fake Account Litigation', 'status': 'Pending', 'amount': '$3B reserve'},
                {'case': 'DOJ Investigation - FHA Lending', 'status': 'Settlement Discussions', 'amount': 'TBD'},
            ]
        },
        'jpmorgan': {
            'cik': '0000019617',
            'ticker': 'JPM',
            'name': 'JPMorgan Chase & Co.',
            'filings': [
                {
                    'form': '10-K',
                    'filing_date': '2025-02-20',
                    'description': 'Annual Report',
                    'url': 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000019617&type=10-K',
                    'highlights': [
                        'Total assets of $4.0 trillion',
                        'Regulatory capital ratios well above requirements',
                        'Consumer & Community Banking segment performance',
                        'Digital banking initiatives and fintech competition'
                    ]
                },
                {
                    'form': '10-Q',
                    'filing_date': '2025-11-01',
                    'description': 'Quarterly Report Q3 2025',
                    'url': '#',
                    'highlights': [
                        'Record quarterly revenue of $43.1B',
                        'Credit quality remains strong',
                        'Investment banking fees up 15% YoY'
                    ]
                },
            ],
            'regulatory_mentions': [
                {'agency': 'OCC', 'matter': 'BSA/AML Compliance Program Review', 'status': 'Satisfactory'},
                {'agency': 'Fed', 'matter': 'CCAR Stress Test', 'status': 'Passed'},
            ],
            'litigation': [
                {'case': 'Epstein-Related Litigation', 'status': 'Settled', 'amount': '$290M'},
                {'case': 'Precious Metals Spoofing', 'status': 'Settled', 'amount': '$920M'},
            ]
        },
        'coinbase': {
            'cik': '0001679788',
            'ticker': 'COIN',
            'name': 'Coinbase Global, Inc.',
            'filings': [
                {
                    'form': '10-K',
                    'filing_date': '2025-02-22',
                    'description': 'Annual Report',
                    'url': 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001679788&type=10-K',
                    'highlights': [
                        'Total revenue of $3.1B for FY2024',
                        'SEC Wells Notice received - potential enforcement action',
                        'State-by-state regulatory landscape discussion',
                        'Custody services for institutional clients growing'
                    ]
                },
                {
                    'form': '10-Q',
                    'filing_date': '2025-11-05',
                    'description': 'Quarterly Report Q3 2025',
                    'url': '#',
                    'highlights': [
                        'Transaction revenue up 40% QoQ',
                        'Regulatory clarity from FIT21 passage',
                        'International expansion in regulated markets'
                    ]
                },
            ],
            'regulatory_mentions': [
                {'agency': 'SEC', 'matter': 'Securities Registration - Staking Services', 'status': 'Litigation Ongoing'},
                {'agency': 'CFTC', 'matter': 'Derivatives Trading License', 'status': 'Application Pending'},
                {'agency': 'NY DFS', 'matter': 'BitLicense Compliance', 'status': 'In Good Standing'},
            ],
            'litigation': [
                {'case': 'SEC v. Coinbase (Staking)', 'status': 'Active Litigation', 'amount': 'N/A'},
                {'case': 'State AG Consumer Protection', 'status': 'Under Investigation', 'amount': 'TBD'},
            ]
        },
        'bank of america': {
            'cik': '0000070858',
            'ticker': 'BAC',
            'name': 'Bank of America Corporation',
            'filings': [
                {
                    'form': '10-K',
                    'filing_date': '2025-02-20',
                    'description': 'Annual Report',
                    'url': '#',
                    'highlights': [
                        'Total assets of $3.3 trillion',
                        'Digital banking users exceed 45 million',
                        'Climate risk disclosure and net-zero commitments',
                        'Consumer lending portfolio performance'
                    ]
                },
            ],
            'regulatory_mentions': [
                {'agency': 'OCC', 'matter': 'CRA Rating', 'status': 'Satisfactory'},
                {'agency': 'CFPB', 'matter': 'Overdraft Fee Review', 'status': 'Closed'},
            ],
            'litigation': []
        },
    }

    # Find matching firm
    for key, data in sample_filings.items():
        if key in normalized or normalized in key:
            return data

    # Default sample data for unknown firms
    return {
        'cik': None,
        'ticker': None,
        'name': firm_name,
        'filings': [
            {
                'form': '10-K',
                'filing_date': '2025-02-15',
                'description': 'Annual Report',
                'url': '#',
                'highlights': [
                    'Standard annual disclosure',
                    'See Risk Factors section for regulatory matters'
                ]
            }
        ],
        'regulatory_mentions': [],
        'litigation': []
    }
