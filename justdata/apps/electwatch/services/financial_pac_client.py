#!/usr/bin/env python3
"""
Financial Sector PAC Contributions Client

Tracks contributions from major financial sector PACs to candidates.
Uses FEC Schedule B (disbursements) data to find PAC-to-candidate contributions.
"""

import os
import time
import logging
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# Major financial sector PAC committee IDs
# These are the primary campaign committees for major financial firms
# Source: FEC.gov - Updated periodically from investsnips.com financial sector lists
FINANCIAL_SECTOR_PACS = {
    # Major Banks
    'C00034595': {'name': 'Wells Fargo', 'sector': 'banking'},
    'C00104299': {'name': 'JPMorgan Chase', 'sector': 'banking'},
    'C00008474': {'name': 'Citigroup', 'sector': 'banking'},
    'C00326595': {'name': 'Capital One', 'sector': 'banking'},
    'C00386524': {'name': 'Truist', 'sector': 'banking'},
    'C00142596': {'name': 'PNC', 'sector': 'banking'},
    'C00817395': {'name': 'Fifth Third', 'sector': 'banking'},
    'C00185884': {'name': 'BNY Mellon', 'sector': 'banking'},
    'C00515148': {'name': 'Northern Trust', 'sector': 'banking'},
    'C00019711': {'name': 'Bank of America', 'sector': 'banking'},
    'C00040279': {'name': 'US Bancorp', 'sector': 'banking'},
    'C00095208': {'name': 'Regions Financial', 'sector': 'banking'},
    'C00040899': {'name': 'KeyCorp', 'sector': 'banking'},
    'C00148791': {'name': 'M&T Bank', 'sector': 'banking'},
    'C00040741': {'name': 'Huntington Bancshares', 'sector': 'banking'},
    'C00148403': {'name': 'Citizens Financial', 'sector': 'banking'},
    'C00039602': {'name': 'BB&T (now Truist)', 'sector': 'banking'},
    'C00039685': {'name': 'SunTrust (now Truist)', 'sector': 'banking'},
    'C00040634': {'name': 'Comerica', 'sector': 'banking'},
    'C00040469': {'name': 'Zions Bancorporation', 'sector': 'banking'},

    # Investment Banks & Asset Managers
    'C00201483': {'name': 'Goldman Sachs', 'sector': 'investment'},
    'C00067215': {'name': 'Morgan Stanley', 'sector': 'investment'},
    'C00479246': {'name': 'BlackRock', 'sector': 'investment'},
    'C00457531': {'name': 'Fidelity Investments', 'sector': 'investment'},
    'C00370114': {'name': 'Charles Schwab', 'sector': 'investment'},
    'C00040956': {'name': 'State Street', 'sector': 'investment'},
    'C00148262': {'name': 'T. Rowe Price', 'sector': 'investment'},
    'C00123406': {'name': 'Franklin Resources', 'sector': 'investment'},
    'C00164301': {'name': 'Invesco', 'sector': 'investment'},
    'C00254367': {'name': 'Raymond James', 'sector': 'investment'},
    'C00345553': {'name': 'Edward Jones', 'sector': 'investment'},
    'C00101600': {'name': 'TIAA', 'sector': 'investment'},
    'C00329029': {'name': 'Vanguard', 'sector': 'investment'},
    'C00355321': {'name': 'KKR', 'sector': 'investment'},
    'C00495317': {'name': 'Blackstone', 'sector': 'investment'},
    'C00371963': {'name': 'Apollo Global', 'sector': 'investment'},
    'C00476879': {'name': 'Carlyle Group', 'sector': 'investment'},

    # Credit Cards & Consumer Finance
    'C00040535': {'name': 'American Express', 'sector': 'consumer_lending'},
    'C00365122': {'name': 'Visa', 'sector': 'fintech'},
    'C00410274': {'name': 'Mastercard', 'sector': 'fintech'},
    'C00438051': {'name': 'Discover Financial', 'sector': 'consumer_lending'},
    'C00579540': {'name': 'Ally Financial', 'sector': 'consumer_lending'},
    'C00589119': {'name': 'Synchrony', 'sector': 'consumer_lending'},
    'C00502963': {'name': 'Santander Consumer', 'sector': 'consumer_lending'},
    'C00501775': {'name': 'Navient', 'sector': 'consumer_lending'},
    'C00137836': {'name': 'SLM Corporation (Sallie Mae)', 'sector': 'consumer_lending'},

    # Mortgage & Real Estate Finance
    'C00040014': {'name': 'Fannie Mae', 'sector': 'mortgage'},
    'C00040030': {'name': 'Freddie Mac', 'sector': 'mortgage'},
    'C00094847': {'name': 'Mortgage Bankers Association', 'sector': 'mortgage'},
    'C00122465': {'name': 'National Association of Realtors', 'sector': 'mortgage'},
    'C00347443': {'name': 'Quicken Loans/Rocket', 'sector': 'mortgage'},

    # Insurance
    'C00040063': {'name': 'MetLife', 'sector': 'insurance'},
    'C00040097': {'name': 'Prudential Financial', 'sector': 'insurance'},
    'C00040121': {'name': 'AIG', 'sector': 'insurance'},
    'C00040147': {'name': 'Hartford Financial', 'sector': 'insurance'},
    'C00040170': {'name': 'Travelers', 'sector': 'insurance'},
    'C00135137': {'name': 'Aflac', 'sector': 'insurance'},
    'C00040659': {'name': 'Principal Financial', 'sector': 'insurance'},
    'C00040683': {'name': 'Lincoln National', 'sector': 'insurance'},

    # Crypto & Fintech
    'C00804179': {'name': 'Coinbase', 'sector': 'crypto'},
    'C00780304': {'name': 'Robinhood', 'sector': 'fintech'},
    'C00820092': {'name': 'Block (Square)', 'sector': 'fintech'},
    'C00792531': {'name': 'PayPal', 'sector': 'fintech'},
    'C00575068': {'name': 'Intuit', 'sector': 'fintech'},

    # Exchanges & Financial Infrastructure
    'C00148585': {'name': 'CME Group', 'sector': 'exchanges'},
    'C00314138': {'name': 'Intercontinental Exchange (ICE)', 'sector': 'exchanges'},
    'C00394882': {'name': 'Nasdaq', 'sector': 'exchanges'},
    'C00370734': {'name': 'CBOE Global Markets', 'sector': 'exchanges'},

    # Industry Associations
    'C00004275': {'name': 'American Bankers Association', 'sector': 'banking'},
    'C00024240': {'name': 'Credit Union National Association', 'sector': 'banking'},
    'C00035675': {'name': 'Independent Community Bankers', 'sector': 'banking'},
    'C00042069': {'name': 'Securities Industry and Financial Markets Association', 'sector': 'investment'},
    'C00027466': {'name': 'Investment Company Institute', 'sector': 'investment'},
}


@dataclass
class PACContribution:
    """Represents a PAC contribution to a candidate."""
    pac_id: str
    pac_name: str
    recipient_name: str
    recipient_id: Optional[str]
    amount: float
    date: str
    sector: str


class FinancialPACClient:
    """Client for tracking financial sector PAC contributions."""

    BASE_URL = 'https://api.open.fec.gov/v1'

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('FEC_API_KEY')
        if not self.api_key:
            logger.warning("FEC_API_KEY not set - financial PAC tracking disabled")

        self._session = requests.Session()
        self._last_request_time = 0
        self._min_request_interval = 0.5  # Rate limiting

    def _request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make an API request with rate limiting."""
        if not self.api_key:
            return None

        # Rate limiting
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)

        url = f"{self.BASE_URL}{endpoint}"
        params = params or {}
        params['api_key'] = self.api_key

        try:
            self._last_request_time = time.time()
            response = self._session.get(url, params=params, timeout=60)

            if response.status_code == 429:
                logger.warning("Rate limited - waiting 60 seconds")
                time.sleep(60)
                return self._request(endpoint, params)

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"FEC API error: {e}")
            return None

    def get_pac_disbursements(
        self,
        committee_id: str,
        cycle: int = 2024,
        limit: int = 500
    ) -> List[PACContribution]:
        """
        Get disbursements (contributions to candidates) from a PAC.

        Uses Schedule B data which shows where PACs send money.
        """
        pac_info = FINANCIAL_SECTOR_PACS.get(committee_id, {})
        pac_name = pac_info.get('name', 'Unknown')
        sector = pac_info.get('sector', 'financial')

        params = {
            'committee_id': committee_id,
            'two_year_transaction_period': cycle,
            'per_page': min(limit, 100),
            'sort': '-disbursement_amount'
        }

        contributions = []
        page = 1
        total_fetched = 0

        while total_fetched < limit:
            params['page'] = page
            data = self._request('/schedules/schedule_b/', params)

            if not data:
                break

            results = data.get('results', [])
            if not results:
                break

            for r in results:
                amount = r.get('disbursement_amount', 0)
                purpose = (r.get('disbursement_description', '') or '').upper()
                recipient_name = r.get('recipient_name', '').upper()

                # Skip operating expenses, refunds, and non-contribution payments
                skip_keywords = ['REFUND', 'OPERATING', 'SALARY', 'PAYROLL', 'RENT',
                                'TRAVEL', 'POSTAGE', 'PRINTING', 'CONSULTANT', 'FEE',
                                'BANK', 'CREDIT CARD', 'UTILITIES', 'INSURANCE']

                if amount > 0:
                    # Include if it looks like a contribution to a candidate/committee
                    # (has keywords OR recipient name looks like a candidate/committee)
                    is_contribution = any(kw in purpose for kw in ['CONTRIB', 'DONATION', 'SUPPORT', 'CANDIDATE'])
                    is_to_committee = ' FOR ' in recipient_name or 'COMMITTEE' in recipient_name or 'PAC' in recipient_name or 'VICTORY' in recipient_name
                    is_to_person = any(title in recipient_name for title in ['FRIENDS OF', 'CITIZENS FOR', 'PEOPLE FOR', 'AMERICANS FOR'])
                    is_expense = any(kw in purpose for kw in skip_keywords)

                    if (is_contribution or is_to_committee or is_to_person) and not is_expense:
                        contributions.append(PACContribution(
                            pac_id=committee_id,
                            pac_name=pac_name,
                            recipient_name=r.get('recipient_name', ''),
                            recipient_id=r.get('recipient_committee_id'),
                            amount=amount,
                            date=r.get('disbursement_date', ''),
                            sector=sector
                        ))

            total_fetched += len(results)

            # Check if there are more pages
            pagination = data.get('pagination', {})
            if page >= pagination.get('pages', 1):
                break
            page += 1

        return contributions

    def get_all_financial_pac_contributions(
        self,
        cycle: int = 2024,
        limit_per_pac: int = 200
    ) -> Dict[str, Dict]:
        """
        Get contributions from all tracked financial sector PACs.

        Returns a dict keyed by recipient name with total amounts and PAC sources.
        """
        logger.info(f"Fetching contributions from {len(FINANCIAL_SECTOR_PACS)} financial PACs...")

        all_contributions = {}
        pacs_processed = 0

        for committee_id, pac_info in FINANCIAL_SECTOR_PACS.items():
            try:
                contributions = self.get_pac_disbursements(
                    committee_id,
                    cycle=cycle,
                    limit=limit_per_pac
                )

                for c in contributions:
                    recipient_key = c.recipient_name.upper().strip()

                    if recipient_key not in all_contributions:
                        all_contributions[recipient_key] = {
                            'total': 0,
                            'pacs': [],
                            'sectors': set(),
                            'contributions': []
                        }

                    all_contributions[recipient_key]['total'] += c.amount
                    all_contributions[recipient_key]['sectors'].add(c.sector)

                    if c.pac_name not in all_contributions[recipient_key]['pacs']:
                        all_contributions[recipient_key]['pacs'].append(c.pac_name)

                    all_contributions[recipient_key]['contributions'].append({
                        'pac': c.pac_name,
                        'amount': c.amount,
                        'date': c.date
                    })

                pacs_processed += 1
                logger.info(f"  [{pacs_processed}/{len(FINANCIAL_SECTOR_PACS)}] {pac_info['name']}: {len(contributions)} contributions")

            except Exception as e:
                logger.warning(f"Error fetching {pac_info['name']}: {e}")

        # Convert sets to lists for JSON serialization
        for recipient in all_contributions:
            all_contributions[recipient]['sectors'] = list(all_contributions[recipient]['sectors'])

        logger.info(f"Found contributions to {len(all_contributions)} recipients")
        return all_contributions

    def match_contributions_to_officials(
        self,
        contributions: Dict[str, Dict],
        officials: List[Dict]
    ) -> List[Dict]:
        """
        Match PAC contributions to officials in our list.

        Uses fuzzy matching on names since FEC recipient names may differ
        from how we store official names.
        """
        # Build a lookup of official names (various formats)
        official_lookup = {}
        for official in officials:
            name = official.get('name', '')

            # Create various name formats for matching
            name_upper = name.upper().strip()
            official_lookup[name_upper] = official

            # Also try "LASTNAME, FIRSTNAME" format (FEC style)
            parts = name.split()
            if len(parts) >= 2:
                fec_format = f"{parts[-1]}, {' '.join(parts[:-1])}".upper()
                official_lookup[fec_format] = official

                # Just last name for partial matching
                official_lookup[parts[-1].upper()] = official

        matched_count = 0

        for recipient_name, data in contributions.items():
            matched_official = None

            # Try exact match first
            if recipient_name in official_lookup:
                matched_official = official_lookup[recipient_name]
            else:
                # Try partial matching
                for official_name, official in official_lookup.items():
                    # Check if recipient contains official's last name
                    if len(official_name) > 3 and official_name in recipient_name:
                        matched_official = official
                        break

            if matched_official:
                # Add financial sector contributions to this official
                current = matched_official.get('financial_sector_contributions', 0)
                matched_official['financial_sector_contributions'] = current + data['total']

                # Track which PACs contributed
                existing_pacs = matched_official.get('contributing_pacs', [])
                for pac in data['pacs']:
                    if pac not in existing_pacs:
                        existing_pacs.append(pac)
                matched_official['contributing_pacs'] = existing_pacs

                matched_count += 1

        logger.info(f"Matched financial sector contributions to {matched_count} officials")
        return officials


def get_financial_pac_client() -> FinancialPACClient:
    """Get singleton client instance."""
    return FinancialPACClient()


# Testing
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    from dotenv import load_dotenv
    load_dotenv()

    client = FinancialPACClient()

    print("=== Testing Financial PAC Client ===")
    print(f"Tracking {len(FINANCIAL_SECTOR_PACS)} financial sector PACs")

    # Test with one PAC
    print("\n--- Wells Fargo PAC Contributions ---")
    contributions = client.get_pac_disbursements('C00034595', cycle=2024, limit=20)
    for c in contributions[:10]:
        print(f"  {c.recipient_name}: ${c.amount:,.0f}")
