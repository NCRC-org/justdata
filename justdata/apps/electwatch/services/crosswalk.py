"""Congress member ID crosswalk using unitedstates/congress-legislators.

This module provides authoritative mapping between different ID systems used
for Congress members, most importantly:
- bioguide_id (Congress.gov) -> fec_candidate_id (FEC)

This eliminates error-prone name matching for FEC data by providing direct ID lookups.

Source: https://github.com/unitedstates/congress-legislators
"""
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import requests

try:
    import yaml
except ImportError:
    yaml = None

logger = logging.getLogger(__name__)

# The congress-legislators repo uses YAML format
CROSSWALK_URL = "https://raw.githubusercontent.com/unitedstates/congress-legislators/main/legislators-current.yaml"
CROSSWALK_HISTORICAL_URL = "https://raw.githubusercontent.com/unitedstates/congress-legislators/main/legislators-historical.yaml"
CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"
CACHE_FILE = CACHE_DIR / "congress_legislators_crosswalk.json"
CACHE_MAX_AGE_DAYS = 7


class CongressCrosswalk:
    """Manages bioguide_id to fec_candidate_id mapping using congress-legislators data."""

    def __init__(self, include_historical: bool = False):
        """
        Initialize the crosswalk.

        Args:
            include_historical: If True, also load historical legislators (slower but more complete)
        """
        self._crosswalk: Dict[str, Dict] = {}
        self._fec_to_bioguide: Dict[str, str] = {}  # Reverse lookup
        self._include_historical = include_historical
        self._load_crosswalk()

    def _load_crosswalk(self):
        """Load crosswalk from cache or download fresh."""
        if self._is_cache_valid():
            self._load_from_cache()
        else:
            self._download_fresh()

    def _is_cache_valid(self) -> bool:
        """Check if cache exists and is less than 7 days old."""
        if not CACHE_FILE.exists():
            return False
        try:
            mtime = datetime.fromtimestamp(CACHE_FILE.stat().st_mtime)
            return datetime.now() - mtime < timedelta(days=CACHE_MAX_AGE_DAYS)
        except Exception:
            return False

    def _load_from_cache(self):
        """Load crosswalk from cached file."""
        try:
            with open(CACHE_FILE, encoding='utf-8') as f:
                data = json.load(f)
            self._build_lookup(data.get('legislators', []))
            logger.info(f"Loaded crosswalk from cache: {len(self._crosswalk)} members")
        except Exception as e:
            logger.error(f"Failed to load cache: {e}")
            self._download_fresh()

    def _download_fresh(self):
        """Download fresh crosswalk from GitHub."""
        try:
            logger.info("Downloading congress-legislators crosswalk...")

            # Check if PyYAML is available
            if yaml is None:
                logger.warning("PyYAML not installed - trying to install...")
                try:
                    import subprocess
                    subprocess.check_call(['pip', 'install', 'pyyaml', '-q'])
                    import yaml as yaml_module
                    globals()['yaml'] = yaml_module
                except Exception as install_err:
                    logger.error(f"Could not install PyYAML: {install_err}")
                    self._crosswalk = {}
                    return

            # Always get current legislators
            resp = requests.get(CROSSWALK_URL, timeout=60)
            resp.raise_for_status()
            legislators = yaml.safe_load(resp.text)

            # Optionally get historical legislators
            if self._include_historical:
                try:
                    resp_hist = requests.get(CROSSWALK_HISTORICAL_URL, timeout=60)
                    resp_hist.raise_for_status()
                    hist_legislators = yaml.safe_load(resp_hist.text)
                    if hist_legislators:
                        legislators.extend(hist_legislators)
                except Exception as e:
                    logger.warning(f"Could not load historical legislators: {e}")

            # Cache for future use (as JSON for faster loading)
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_data = {
                'legislators': legislators,
                'downloaded_at': datetime.now().isoformat(),
                'include_historical': self._include_historical
            }
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f)

            self._build_lookup(legislators)
            logger.info(f"Downloaded crosswalk: {len(self._crosswalk)} members")
        except Exception as e:
            logger.error(f"Failed to download crosswalk: {e}")
            self._crosswalk = {}

    def _build_lookup(self, legislators: List[Dict]):
        """Build bioguide -> member data lookup."""
        for member in legislators:
            ids = member.get('id', {})
            bioguide = ids.get('bioguide')
            if not bioguide:
                continue

            fec_ids = ids.get('fec', [])
            # Ensure fec_ids is always a list
            if isinstance(fec_ids, str):
                fec_ids = [fec_ids]

            name_info = member.get('name', {})

            self._crosswalk[bioguide] = {
                'bioguide_id': bioguide,
                'fec_ids': fec_ids,
                'govtrack_id': ids.get('govtrack'),
                'opensecrets_id': ids.get('opensecrets'),
                'thomas_id': ids.get('thomas'),
                'lis_id': ids.get('lis'),  # Legislative Information System (Senate)
                'wikipedia': ids.get('wikipedia'),
                'name': name_info,
                'first_name': name_info.get('first'),
                'middle_name': name_info.get('middle'),
                'last_name': name_info.get('last'),
                'suffix': name_info.get('suffix'),
                'nickname': name_info.get('nickname'),
                'official_full': name_info.get('official_full'),
                'birthday': member.get('bio', {}).get('birthday'),
                'gender': member.get('bio', {}).get('gender'),
            }

            # Build reverse lookup (FEC ID -> bioguide)
            for fec_id in fec_ids:
                self._fec_to_bioguide[fec_id] = bioguide

    def get_fec_id(self, bioguide_id: str) -> Optional[str]:
        """
        Get primary FEC candidate ID for a bioguide_id.

        Args:
            bioguide_id: Congress.gov bioguide ID (e.g., "B001282")

        Returns:
            FEC candidate ID (e.g., "H2KY06054") or None if not found
        """
        member = self._crosswalk.get(bioguide_id)
        if member and member.get('fec_ids'):
            # Return most recent FEC ID (last in list is typically most recent)
            return member['fec_ids'][-1]
        return None

    def get_all_fec_ids(self, bioguide_id: str) -> List[str]:
        """
        Get all FEC candidate IDs for a bioguide_id.

        Some members have multiple FEC IDs (e.g., ran for different offices).

        Args:
            bioguide_id: Congress.gov bioguide ID

        Returns:
            List of FEC candidate IDs (may be empty)
        """
        member = self._crosswalk.get(bioguide_id)
        if member:
            return member.get('fec_ids', [])
        return []

    def get_member_info(self, bioguide_id: str) -> Optional[Dict]:
        """
        Get full member info including nickname and all IDs.

        Args:
            bioguide_id: Congress.gov bioguide ID

        Returns:
            Dict with member info or None if not found
        """
        return self._crosswalk.get(bioguide_id)

    def get_bioguide_from_fec(self, fec_id: str) -> Optional[str]:
        """
        Reverse lookup: get bioguide_id from FEC candidate ID.

        Args:
            fec_id: FEC candidate ID

        Returns:
            bioguide_id or None if not found
        """
        return self._fec_to_bioguide.get(fec_id)

    def get_all_fec_mappings(self) -> Dict[str, str]:
        """
        Return dict of bioguide_id -> fec_candidate_id for all members.

        Returns:
            Dict mapping bioguide IDs to primary FEC IDs
        """
        return {
            bioguide: info['fec_ids'][-1]
            for bioguide, info in self._crosswalk.items()
            if info.get('fec_ids')
        }

    def get_display_name(self, bioguide_id: str) -> Optional[str]:
        """
        Get the common display name for a member (using nickname if available).

        Args:
            bioguide_id: Congress.gov bioguide ID

        Returns:
            Display name like "Ted Cruz" instead of "Rafael Cruz"
        """
        member = self._crosswalk.get(bioguide_id)
        if not member:
            return None

        first = member.get('nickname') or member.get('first_name')
        last = member.get('last_name')
        suffix = member.get('suffix')

        if first and last:
            name = f"{first} {last}"
            if suffix:
                name = f"{name} {suffix}"
            return name
        return member.get('official_full')

    def get_name_variations(self, bioguide_id: str) -> List[str]:
        """
        Get all possible name variations for matching (for FMP trades, etc.).

        Args:
            bioguide_id: Congress.gov bioguide ID

        Returns:
            List of name variations (e.g., ["Ted Cruz", "Rafael Cruz", "Rafael Edward Cruz"])
        """
        member = self._crosswalk.get(bioguide_id)
        if not member:
            return []

        variations = set()
        first = member.get('first_name')
        middle = member.get('middle_name')
        last = member.get('last_name')
        nickname = member.get('nickname')
        suffix = member.get('suffix')
        official_full = member.get('official_full')

        if official_full:
            variations.add(official_full)

        if first and last:
            variations.add(f"{first} {last}")
            if suffix:
                variations.add(f"{first} {last} {suffix}")
            if middle:
                variations.add(f"{first} {middle} {last}")
                variations.add(f"{first} {middle[0]}. {last}")  # First M. Last

        if nickname and last:
            variations.add(f"{nickname} {last}")
            if suffix:
                variations.add(f"{nickname} {last} {suffix}")

        # Just last name for fuzzy matching
        if last:
            variations.add(last)

        return list(variations)

    def build_name_lookup(self, officials: List[Dict]) -> Dict[str, Dict]:
        """
        Build comprehensive name lookup using crosswalk nicknames.

        This is used to match FMP trade disclosure names to officials.

        Args:
            officials: List of official records with bioguide_id

        Returns:
            Dict mapping lowercase name variations to official records
        """
        lookup = {}

        for official in officials:
            bioguide_id = official.get('bioguide_id')
            name = official.get('name', '')

            # Add canonical name
            if name:
                lookup[name.lower()] = official

            # Add crosswalk variations (nicknames, legal names)
            if bioguide_id:
                variations = self.get_name_variations(bioguide_id)
                for variation in variations:
                    key = variation.lower()
                    if key not in lookup:
                        lookup[key] = official

        return lookup

    def get_opensecrets_id(self, bioguide_id: str) -> Optional[str]:
        """Get OpenSecrets/CRP ID for a member."""
        member = self._crosswalk.get(bioguide_id)
        if member:
            return member.get('opensecrets_id')
        return None

    def get_govtrack_id(self, bioguide_id: str) -> Optional[int]:
        """Get GovTrack ID for a member."""
        member = self._crosswalk.get(bioguide_id)
        if member:
            return member.get('govtrack_id')
        return None

    def get_statistics(self) -> Dict:
        """Get statistics about the crosswalk data."""
        total = len(self._crosswalk)
        with_fec = sum(1 for m in self._crosswalk.values() if m.get('fec_ids'))
        with_opensecrets = sum(1 for m in self._crosswalk.values() if m.get('opensecrets_id'))
        with_nickname = sum(1 for m in self._crosswalk.values() if m.get('nickname'))

        return {
            'total_members': total,
            'with_fec_id': with_fec,
            'with_opensecrets_id': with_opensecrets,
            'with_nickname': with_nickname,
            'fec_coverage_pct': round(with_fec / total * 100, 1) if total else 0,
            'cache_file': str(CACHE_FILE),
            'cache_valid': self._is_cache_valid()
        }

    def refresh(self):
        """Force refresh the crosswalk data from GitHub."""
        # Remove cache file to force re-download
        if CACHE_FILE.exists():
            CACHE_FILE.unlink()
        self._download_fresh()


# Global instance
_crosswalk: Optional[CongressCrosswalk] = None


def get_crosswalk(include_historical: bool = False) -> CongressCrosswalk:
    """
    Get or create global crosswalk instance.

    Args:
        include_historical: Include historical legislators (slower but more complete)

    Returns:
        CongressCrosswalk instance
    """
    global _crosswalk
    if _crosswalk is None:
        _crosswalk = CongressCrosswalk(include_historical=include_historical)
    return _crosswalk


def get_fec_id(bioguide_id: str) -> Optional[str]:
    """Convenience function to get FEC ID from bioguide ID."""
    return get_crosswalk().get_fec_id(bioguide_id)


def get_member_info(bioguide_id: str) -> Optional[Dict]:
    """Convenience function to get member info."""
    return get_crosswalk().get_member_info(bioguide_id)


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    print("=== Testing Congress Crosswalk ===\n")

    crosswalk = get_crosswalk()
    stats = crosswalk.get_statistics()

    print(f"Loaded {stats['total_members']} members")
    print(f"  With FEC ID: {stats['with_fec_id']} ({stats['fec_coverage_pct']}%)")
    print(f"  With OpenSecrets ID: {stats['with_opensecrets_id']}")
    print(f"  With nickname: {stats['with_nickname']}")
    print()

    # Test specific lookups
    test_cases = [
        ("B001282", "Andy Barr"),      # Should map to H2KY06054
        ("C001098", "Ted Cruz"),        # Has nickname
        ("K000389", "Ro Khanna"),       # Also has nickname (Rohit)
        ("G000583", "Josh Gottheimer"), # Financial Services
        ("W000187", "Maxine Waters"),   # Ranking member
    ]

    print("=== Testing Specific Members ===\n")
    for bioguide, expected_name in test_cases:
        info = crosswalk.get_member_info(bioguide)
        if info:
            fec_id = crosswalk.get_fec_id(bioguide)
            display = crosswalk.get_display_name(bioguide)
            variations = crosswalk.get_name_variations(bioguide)
            print(f"{expected_name} ({bioguide}):")
            print(f"  FEC ID: {fec_id}")
            print(f"  Display name: {display}")
            print(f"  Name variations: {variations[:3]}...")
            print()
        else:
            print(f"{expected_name} ({bioguide}): NOT FOUND")
            print()
