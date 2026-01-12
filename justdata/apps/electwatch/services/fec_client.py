#!/usr/bin/env python3
"""
FEC (Federal Election Commission) API Client for ElectWatch

Fetches campaign contribution data from the OpenFEC API.
API Documentation: https://api.open.fec.gov/developers/

Key endpoints:
- /candidates/search/ - Find candidates
- /schedules/schedule_a/ - Itemized receipts (contributions)
- /committees/ - PAC and committee data
"""

import os
import sys
import time
import logging
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

REPO_ROOT = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.insert(0, str(REPO_ROOT))

from apps.electwatch.config import ElectWatchConfig

logger = logging.getLogger(__name__)


@dataclass
class FECCandidate:
    """Represents an FEC candidate record."""
    candidate_id: str
    name: str
    party: str
    state: str
    district: Optional[str]
    office: str  # 'H' for House, 'S' for Senate, 'P' for President
    incumbent_challenge: str
    candidate_status: str
    principal_committees: List[str]


@dataclass
class FECContribution:
    """Represents an FEC contribution record."""
    contributor_name: str
    contributor_type: str  # 'individual', 'pac', 'party', etc.
    amount: float
    contribution_date: str
    committee_id: str
    committee_name: str
    employer: Optional[str]
    occupation: Optional[str]
    memo_text: Optional[str]
    transaction_id: str


class FECClient:
    """
    Client for the Federal Election Commission OpenFEC API.

    Usage:
        client = FECClient()
        candidates = client.search_candidates(name='Nancy Pelosi')
        contributions = client.get_candidate_contributions(candidate_id='H0CA08007')
    """

    BASE_URL = 'https://api.open.fec.gov/v1'

    def __init__(self, api_key: str = None):
        """
        Initialize FEC client.

        Args:
            api_key: FEC API key (defaults to FEC_API_KEY env var)
        """
        self.api_key = api_key or ElectWatchConfig.FEC_API_KEY
        if not self.api_key:
            logger.warning("FEC_API_KEY not set - API calls will fail")
            logger.info("Get a free API key at: https://api.open.fec.gov/developers/")

        self._session = requests.Session()
        self._session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'NCRC-ElectWatch/0.9.0'
        })

        # Rate limiting
        self._last_request_time = 0
        self._min_request_interval = 0.1  # 10 requests per second max

    def _request(
        self,
        endpoint: str,
        params: Dict = None,
        method: str = 'GET'
    ) -> Optional[Dict]:
        """
        Make an API request with rate limiting and error handling.
        """
        if not self.api_key:
            logger.error("FEC_API_KEY not configured")
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
            response = self._session.request(method, url, params=params)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error: {e}")
            if response.status_code == 429:
                logger.warning("Rate limited - waiting 60 seconds")
                time.sleep(60)
                return self._request(endpoint, params, method)
            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            return None

    # =========================================================================
    # CANDIDATE SEARCH
    # =========================================================================

    def search_candidates(
        self,
        name: str = None,
        state: str = None,
        office: str = None,
        party: str = None,
        cycle: int = None,
        is_active: bool = True,
        limit: int = 20
    ) -> List[FECCandidate]:
        """
        Search for candidates.

        Args:
            name: Candidate name (partial match)
            state: Two-letter state code
            office: 'H' for House, 'S' for Senate, 'P' for President
            party: Party code ('DEM', 'REP', etc.)
            cycle: Election cycle year
            is_active: Only active candidates
            limit: Maximum results

        Returns:
            List of FECCandidate objects
        """
        params = {
            'per_page': min(limit, 100),
            'sort': '-election_years'
        }

        if name:
            params['q'] = name
        if state:
            params['state'] = state
        if office:
            params['office'] = office
        if party:
            params['party'] = party
        if cycle:
            params['cycle'] = cycle
        if is_active:
            params['candidate_status'] = 'C'  # Current candidate

        data = self._request('/candidates/search/', params)
        if not data:
            return []

        candidates = []
        for result in data.get('results', []):
            candidates.append(FECCandidate(
                candidate_id=result.get('candidate_id', ''),
                name=result.get('name', ''),
                party=result.get('party', ''),
                state=result.get('state', ''),
                district=result.get('district'),
                office=result.get('office', ''),
                incumbent_challenge=result.get('incumbent_challenge', ''),
                candidate_status=result.get('candidate_status', ''),
                principal_committees=result.get('principal_committees', [])
            ))

        return candidates

    def get_candidate(self, candidate_id: str) -> Optional[FECCandidate]:
        """Get details for a specific candidate."""
        data = self._request(f'/candidate/{candidate_id}/')
        if not data or not data.get('results'):
            return None

        result = data['results'][0]
        return FECCandidate(
            candidate_id=result.get('candidate_id', ''),
            name=result.get('name', ''),
            party=result.get('party', ''),
            state=result.get('state', ''),
            district=result.get('district'),
            office=result.get('office', ''),
            incumbent_challenge=result.get('incumbent_challenge', ''),
            candidate_status=result.get('candidate_status', ''),
            principal_committees=result.get('principal_committees', [])
        )

    # =========================================================================
    # CONTRIBUTIONS (Schedule A)
    # =========================================================================

    def get_candidate_contributions(
        self,
        candidate_id: str,
        min_date: str = None,
        max_date: str = None,
        min_amount: float = None,
        contributor_type: str = None,
        limit: int = 100
    ) -> List[FECContribution]:
        """
        Get contributions received by a candidate.

        Args:
            candidate_id: FEC candidate ID
            min_date: Start date (YYYY-MM-DD)
            max_date: End date (YYYY-MM-DD)
            min_amount: Minimum contribution amount
            contributor_type: 'individual', 'committee', etc.
            limit: Maximum results

        Returns:
            List of FECContribution objects
        """
        # First get the candidate's principal committee
        candidate = self.get_candidate(candidate_id)
        if not candidate or not candidate.principal_committees:
            logger.warning(f"No principal committee found for {candidate_id}")
            return []

        committee_id = candidate.principal_committees[0].get('committee_id')
        return self.get_committee_contributions(
            committee_id=committee_id,
            min_date=min_date,
            max_date=max_date,
            min_amount=min_amount,
            contributor_type=contributor_type,
            limit=limit
        )

    def get_committee_contributions(
        self,
        committee_id: str,
        min_date: str = None,
        max_date: str = None,
        min_amount: float = None,
        contributor_type: str = None,
        limit: int = 100
    ) -> List[FECContribution]:
        """
        Get contributions received by a committee.

        Args:
            committee_id: FEC committee ID
            min_date: Start date (YYYY-MM-DD)
            max_date: End date (YYYY-MM-DD)
            min_amount: Minimum contribution amount
            contributor_type: 'individual', 'committee', etc.
            limit: Maximum results

        Returns:
            List of FECContribution objects
        """
        params = {
            'committee_id': committee_id,
            'per_page': min(limit, 100),
            'sort': '-contribution_receipt_date'
        }

        if min_date:
            params['min_date'] = min_date
        if max_date:
            params['max_date'] = max_date
        if min_amount:
            params['min_amount'] = min_amount
        if contributor_type:
            params['contributor_type'] = contributor_type

        data = self._request('/schedules/schedule_a/', params)
        if not data:
            return []

        contributions = []
        for result in data.get('results', []):
            contributions.append(FECContribution(
                contributor_name=result.get('contributor_name', ''),
                contributor_type=result.get('entity_type', ''),
                amount=result.get('contribution_receipt_amount', 0),
                contribution_date=result.get('contribution_receipt_date', ''),
                committee_id=result.get('committee_id', ''),
                committee_name=result.get('committee_name', ''),
                employer=result.get('contributor_employer'),
                occupation=result.get('contributor_occupation'),
                memo_text=result.get('memo_text'),
                transaction_id=result.get('transaction_id', '')
            ))

        return contributions

    def get_pac_contributions_to_candidate(
        self,
        candidate_id: str,
        cycle: int = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get PAC contributions to a candidate.

        This uses the /schedules/schedule_a/by_contributor/ endpoint
        to get aggregated PAC contributions.
        """
        params = {
            'candidate_id': candidate_id,
            'per_page': min(limit, 100),
            'sort': '-total'
        }

        if cycle:
            params['cycle'] = cycle

        data = self._request('/schedules/schedule_a/by_contributor/', params)
        if not data:
            return []

        return data.get('results', [])

    # =========================================================================
    # COMMITTEE (PAC) SEARCH
    # =========================================================================

    def search_committees(
        self,
        name: str = None,
        committee_type: str = None,
        state: str = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        Search for committees/PACs.

        Args:
            name: Committee name (partial match)
            committee_type: Type code (e.g., 'Q' for PAC)
            state: Two-letter state code
            limit: Maximum results

        Returns:
            List of committee records
        """
        params = {
            'per_page': min(limit, 100),
            'sort': '-receipts'
        }

        if name:
            params['q'] = name
        if committee_type:
            params['committee_type'] = committee_type
        if state:
            params['state'] = state

        data = self._request('/committees/', params)
        if not data:
            return []

        return data.get('results', [])

    def get_committee(self, committee_id: str) -> Optional[Dict]:
        """Get details for a specific committee."""
        data = self._request(f'/committee/{committee_id}/')
        if not data or not data.get('results'):
            return None
        return data['results'][0]

    # =========================================================================
    # AGGREGATE DATA
    # =========================================================================

    def get_contributions_by_industry(
        self,
        candidate_id: str,
        cycle: int = None
    ) -> List[Dict]:
        """
        Get contributions to a candidate aggregated by industry.

        Note: FEC doesn't directly provide industry codes for all contributions.
        This returns employer-based aggregations that can be mapped to industries.
        """
        params = {
            'candidate_id': candidate_id,
            'per_page': 100,
            'sort': '-total'
        }

        if cycle:
            params['cycle'] = cycle

        # Use the by_employer endpoint for industry analysis
        data = self._request('/schedules/schedule_a/by_employer/', params)
        if not data:
            return []

        return data.get('results', [])

    def get_contributions_by_size(
        self,
        candidate_id: str,
        cycle: int = None
    ) -> Dict:
        """
        Get contribution distribution by size.

        Returns breakdown: $200 and under, $200.01-$499, etc.
        """
        params = {
            'candidate_id': candidate_id,
        }

        if cycle:
            params['cycle'] = cycle

        data = self._request('/schedules/schedule_a/by_size/', params)
        if not data:
            return {}

        return data.get('results', {})

    def get_contributions_by_state(
        self,
        candidate_id: str,
        cycle: int = None
    ) -> List[Dict]:
        """Get contributions to a candidate by state."""
        params = {
            'candidate_id': candidate_id,
            'per_page': 100
        }

        if cycle:
            params['cycle'] = cycle

        data = self._request('/schedules/schedule_a/by_state/', params)
        if not data:
            return []

        return data.get('results', [])

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def get_candidate_totals(
        self,
        candidate_id: str,
        cycle: int = None
    ) -> Optional[Dict]:
        """
        Get aggregate financial totals for a candidate.

        This is much faster than fetching individual contributions
        and provides total receipts, individual/PAC contributions, etc.

        Args:
            candidate_id: FEC candidate ID
            cycle: Election cycle (defaults to most recent)

        Returns:
            Dict with receipts, individual_contributions, pac_contributions, etc.
        """
        params = {}
        if cycle:
            params['cycle'] = cycle

        data = self._request(f'/candidate/{candidate_id}/totals/', params)
        if not data or not data.get('results'):
            return None

        # Return most recent cycle data
        results = data['results']
        if cycle:
            # Find matching cycle
            for r in results:
                if r.get('cycle') == cycle:
                    return {
                        'cycle': r.get('cycle'),
                        'receipts': r.get('receipts', 0),
                        'individual_contributions': r.get('individual_contributions', 0),
                        'pac_contributions': r.get('other_political_committee_contributions', 0),
                        'disbursements': r.get('disbursements', 0),
                        'cash_on_hand': r.get('cash_on_hand_end_period', 0),
                        'debt': r.get('debts_owed_by_committee', 0)
                    }

        # Return first (most recent) result
        r = results[0]
        return {
            'cycle': r.get('cycle'),
            'receipts': r.get('receipts', 0),
            'individual_contributions': r.get('individual_contributions', 0),
            'pac_contributions': r.get('other_political_committee_contributions', 0),
            'disbursements': r.get('disbursements', 0),
            'cash_on_hand': r.get('cash_on_hand_end_period', 0),
            'debt': r.get('debts_owed_by_committee', 0)
        }

    def get_current_cycle(self) -> int:
        """Get the current election cycle year."""
        year = datetime.now().year
        # Election cycles are even years
        return year if year % 2 == 0 else year + 1

    def test_connection(self) -> bool:
        """Test API connection."""
        data = self._request('/candidates/', {'per_page': 1})
        return data is not None


# =============================================================================
# MODULE-LEVEL CONVENIENCE FUNCTIONS
# =============================================================================

_client = None


def get_fec_client() -> FECClient:
    """Get singleton FECClient instance."""
    global _client
    if _client is None:
        _client = FECClient()
    return _client


def search_candidates(name: str) -> List[FECCandidate]:
    """Convenience function to search candidates."""
    return get_fec_client().search_candidates(name=name)


def get_candidate_contributions(candidate_id: str, **kwargs) -> List[FECContribution]:
    """Convenience function to get candidate contributions."""
    return get_fec_client().get_candidate_contributions(candidate_id, **kwargs)


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    client = FECClient()

    if not client.api_key:
        print("ERROR: FEC_API_KEY not set")
        print("Set the environment variable or add to .env file")
        sys.exit(1)

    print("=== Testing FEC API Connection ===")
    if client.test_connection():
        print("Connection successful!")
    else:
        print("Connection failed!")
        sys.exit(1)

    print("\n=== Searching for Candidates ===")
    candidates = client.search_candidates(name='Pelosi', office='H', limit=5)
    for c in candidates:
        print(f"  {c.name} ({c.party}-{c.state}) - {c.candidate_id}")

    if candidates:
        print(f"\n=== Getting Contributions for {candidates[0].name} ===")
        # Get PAC contributions
        pac_contribs = client.get_pac_contributions_to_candidate(
            candidates[0].candidate_id,
            limit=10
        )
        for contrib in pac_contribs[:5]:
            print(f"  {contrib.get('contributor_name', 'Unknown')}: ${contrib.get('total', 0):,.0f}")

    print("\n=== Searching for Financial PACs ===")
    pacs = client.search_committees(name='Wells Fargo', limit=5)
    for pac in pacs:
        print(f"  {pac.get('name', 'Unknown')} - {pac.get('committee_id', '')}")
