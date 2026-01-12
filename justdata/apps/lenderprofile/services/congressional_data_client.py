#!/usr/bin/env python3
"""
Congressional Data Client - Committee Memberships

Fetches and caches congressional committee membership data from the
unitedstates/congress-legislators GitHub repository.

Data is cached for 24 hours to minimize API calls.
"""

import logging
import requests
import yaml
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from functools import lru_cache

logger = logging.getLogger(__name__)


class CongressionalDataClient:
    """
    Client for fetching congressional committee membership data.

    Uses public domain data from github.com/unitedstates/congress-legislators
    """

    BASE_URL = "https://raw.githubusercontent.com/unitedstates/congress-legislators/main"

    # Key committees relevant to financial/banking stocks
    FINANCE_COMMITTEES = {
        'SSBK': 'Banking, Housing, and Urban Affairs',
        'SSFI': 'Finance',
        'SSBU': 'Budget',
        'SSAP': 'Appropriations',
        'HSBA': 'Financial Services',
        'HSWM': 'Ways and Means',
        'HSBU': 'Budget',
        'HSAP': 'Appropriations',
    }

    def __init__(self):
        """Initialize the Congressional Data client."""
        self._legislators_cache = None
        self._committees_cache = None
        self._membership_cache = None
        self._cache_time = None
        self._cache_duration = timedelta(hours=24)
        self.timeout = 30

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if self._cache_time is None:
            return False
        return datetime.now() - self._cache_time < self._cache_duration

    def _fetch_yaml(self, filename: str) -> Optional[Any]:
        """Fetch YAML file from GitHub."""
        url = f"{self.BASE_URL}/{filename}"
        try:
            logger.info(f"Fetching {filename} from GitHub...")
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = yaml.safe_load(response.text)
            logger.info(f"Loaded {filename}: {len(data) if isinstance(data, (list, dict)) else 'N/A'} entries")
            return data
        except Exception as e:
            logger.error(f"Failed to fetch {filename}: {e}")
            return None

    def _load_data(self) -> bool:
        """Load all data files from GitHub."""
        if self._is_cache_valid():
            return True

        # Fetch legislators (for bioguide -> name mapping)
        legislators_data = self._fetch_yaml("legislators-current.yaml")
        if not legislators_data:
            return False

        # Fetch committees (for committee ID -> name mapping)
        committees_data = self._fetch_yaml("committees-current.yaml")
        if not committees_data:
            return False

        # Fetch committee memberships
        membership_data = self._fetch_yaml("committee-membership-current.yaml")
        if not membership_data:
            return False

        # Build bioguide -> legislator mapping
        self._legislators_cache = {}
        for leg in legislators_data:
            bioguide = leg.get('id', {}).get('bioguide')
            if bioguide:
                name_info = leg.get('name', {})
                terms = leg.get('terms', [])
                current_term = terms[-1] if terms else {}

                self._legislators_cache[bioguide] = {
                    'bioguide': bioguide,
                    'first_name': name_info.get('first', ''),
                    'last_name': name_info.get('last', ''),
                    'official_name': name_info.get('official_full', ''),
                    'party': current_term.get('party', ''),
                    'state': current_term.get('state', ''),
                    'chamber': 'Senate' if current_term.get('type') == 'sen' else 'House',
                    'district': current_term.get('district'),
                }

        # Build committee ID -> name mapping
        self._committees_cache = {}
        for comm in committees_data:
            comm_type = comm.get('type', '')
            comm_name = comm.get('name', '')

            # Get committee ID (thomas_id or house_committee_id)
            if comm_type == 'house':
                comm_id = 'HS' + comm.get('house_committee_id', comm.get('thomas_id', ''))
            elif comm_type == 'senate':
                comm_id = 'SS' + comm.get('thomas_id', '')[-2:] if comm.get('thomas_id') else ''
            else:
                comm_id = comm.get('thomas_id', '')

            # Store by thomas_id for lookup
            thomas_id = comm.get('thomas_id', '')
            if thomas_id:
                self._committees_cache[thomas_id] = {
                    'id': thomas_id,
                    'name': comm_name,
                    'type': comm_type,
                    'is_finance': thomas_id in self.FINANCE_COMMITTEES,
                }

            # Also map subcommittees
            for sub in comm.get('subcommittees', []):
                sub_id = f"{thomas_id}{sub.get('thomas_id', '')}"
                self._committees_cache[sub_id] = {
                    'id': sub_id,
                    'name': f"{comm_name} - {sub.get('name', '')}",
                    'type': comm_type,
                    'parent': thomas_id,
                    'is_finance': thomas_id in self.FINANCE_COMMITTEES,
                }

        # Build bioguide -> committees mapping
        self._membership_cache = {}
        for comm_id, members in membership_data.items():
            if not isinstance(members, list):
                continue

            # Get committee info
            comm_info = self._committees_cache.get(comm_id, {'name': comm_id})

            for member in members:
                bioguide = member.get('bioguide', '')
                if not bioguide:
                    continue

                if bioguide not in self._membership_cache:
                    self._membership_cache[bioguide] = []

                self._membership_cache[bioguide].append({
                    'committee_id': comm_id,
                    'committee_name': comm_info.get('name', comm_id),
                    'rank': member.get('rank', 0),
                    'title': member.get('title', ''),
                    'party': member.get('party', ''),
                    'is_finance': comm_info.get('is_finance', False),
                })

        self._cache_time = datetime.now()
        logger.info(f"Loaded congressional data: {len(self._legislators_cache)} legislators, "
                   f"{len(self._committees_cache)} committees, {len(self._membership_cache)} membership records")
        return True

    def get_legislator_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Find a legislator by name (fuzzy matching).

        Args:
            name: Politician name (e.g., "Ro Khanna", "Tommy Tuberville")

        Returns:
            Legislator dict with bioguide, name, party, state, chamber, committees
        """
        if not self._load_data():
            return None

        name_lower = name.lower().strip()

        # Try exact match first
        for bioguide, leg in self._legislators_cache.items():
            official = leg.get('official_name', '').lower()
            if official == name_lower:
                return self._enrich_legislator(leg)

        # Try partial match
        for bioguide, leg in self._legislators_cache.items():
            official = leg.get('official_name', '').lower()
            last_name = leg.get('last_name', '').lower()
            first_name = leg.get('first_name', '').lower()

            # Check if search name contains last name
            if last_name and last_name in name_lower:
                # Verify first name or initial matches
                name_parts = name_lower.split()
                if any(first_name.startswith(part) or part.startswith(first_name[:1]) for part in name_parts):
                    return self._enrich_legislator(leg)

            # Check if official name contains search name or vice versa
            if name_lower in official or official in name_lower:
                return self._enrich_legislator(leg)

        logger.warning(f"Could not find legislator: {name}")
        return None

    def _enrich_legislator(self, leg: Dict[str, Any]) -> Dict[str, Any]:
        """Add committee data to legislator."""
        bioguide = leg.get('bioguide', '')
        committees = self._membership_cache.get(bioguide, [])

        # Sort committees by rank (leadership positions first)
        committees_sorted = sorted(committees, key=lambda x: (x.get('rank', 99), x.get('committee_name', '')))

        # Identify finance-related committees
        finance_committees = [c for c in committees_sorted if c.get('is_finance')]

        # Get key committee names (top 5)
        committee_names = [c.get('committee_name', '') for c in committees_sorted[:5]]

        # Check for leadership positions
        leadership_roles = [c for c in committees_sorted if c.get('title')]

        return {
            **leg,
            'committees': committee_names,
            'all_committees': committees_sorted,
            'finance_committees': [c.get('committee_name') for c in finance_committees],
            'is_finance_committee_member': len(finance_committees) > 0,
            'leadership_roles': [f"{c.get('title')} - {c.get('committee_name')}" for c in leadership_roles],
            'has_data': True,
        }

    def get_committees_for_name(self, name: str) -> List[str]:
        """Get list of committee names for a politician."""
        leg = self.get_legislator_by_name(name)
        if leg:
            return leg.get('committees', [])
        return []

    def is_finance_committee_member(self, name: str) -> bool:
        """Check if politician is on a finance-related committee."""
        leg = self.get_legislator_by_name(name)
        if leg:
            return leg.get('is_finance_committee_member', False)
        return False

    def get_politician_profile(self, name: str, chamber: Optional[str] = None) -> Dict[str, Any]:
        """
        Get complete profile for a politician including committees.

        Args:
            name: Politician name
            chamber: Optional chamber hint ('Senate' or 'House')

        Returns:
            Complete politician profile with committee memberships
        """
        leg = self.get_legislator_by_name(name)
        if not leg:
            # Return basic info if not found
            return {
                'name': name,
                'chamber': chamber or 'Unknown',
                'committees': [],
                'has_data': False,
            }

        return leg


def test_congressional_data():
    """Test the Congressional Data client."""
    client = CongressionalDataClient()

    print("Testing Congressional Data Client...")
    print("=" * 50)

    # Test with known politicians
    test_names = [
        "Ro Khanna",
        "Tommy Tuberville",
        "Nancy Pelosi",
        "Mitch McConnell",
    ]

    for name in test_names:
        print(f"\n{name}:")
        profile = client.get_politician_profile(name)
        if profile.get('has_data'):
            print(f"  Chamber: {profile.get('chamber')}")
            print(f"  Party: {profile.get('party')}")
            print(f"  State: {profile.get('state')}")
            print(f"  Committees: {', '.join(profile.get('committees', [])[:3])}")
            if profile.get('finance_committees'):
                print(f"  Finance Committees: {', '.join(profile.get('finance_committees'))}")
            if profile.get('leadership_roles'):
                print(f"  Leadership: {', '.join(profile.get('leadership_roles')[:2])}")
        else:
            print("  Not found in current legislators")


if __name__ == '__main__':
    test_congressional_data()
