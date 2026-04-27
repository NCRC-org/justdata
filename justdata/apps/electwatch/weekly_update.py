#!/usr/bin/env python3
"""
ElectWatch Weekly Data Update

Comprehensive weekly batch process that:
1. Fetches ALL data from APIs (Quiver, FEC, Congress.gov, Finnhub, SEC, NewsAPI)
2. Processes and aggregates data
3. Generates AI summaries using Claude
4. Saves everything to local storage
5. Verifies data integrity
6. Updates metadata with timestamps

Run weekly (recommended: Sunday midnight):
    Windows: schtasks /create /tn "ElectWatch Weekly" /tr "python weekly_update.py" /sc weekly /d SUN /st 00:00
    Linux: 0 0 * * 0 cd /path/to/ncrc-test-apps && python apps/electwatch/weekly_update.py

The app then serves this pre-computed static data all week - no live API calls needed.
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# Set up paths
# parents[2] = justdata, parents[3] = JustData (repo root where .env lives)
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

# Load environment variables FIRST
from dotenv import load_dotenv
load_dotenv(REPO_ROOT / '.env')

# Set up logging
LOG_DIR = REPO_ROOT / 'logs'
LOG_DIR.mkdir(exist_ok=True)

log_file = LOG_DIR / f'electwatch_weekly_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# =============================================================================
# ELECTION CYCLE DATE RANGE
# =============================================================================
# Covers the current and previous election cycles (2023-2024 and 2025-2026)
# All data sources should use this start date for consistency
ELECTION_CYCLE_START = '2023-01-01'

# =============================================================================
# NAME MATCHING CONSTANTS
# =============================================================================

# Load comprehensive name mapping from JSON file
NAME_MAPPING_FILE = Path(__file__).parent / 'data' / 'congress_name_mapping.json'
CONGRESS_NAME_MAPPING = {}
FEC_SEARCH_NAMES = {}
NICKNAME_TO_LEGAL = {}

def load_name_mapping():
    """Load congressional name mapping from JSON file."""
    global CONGRESS_NAME_MAPPING, FEC_SEARCH_NAMES, NICKNAME_TO_LEGAL
    try:
        if NAME_MAPPING_FILE.exists():
            with open(NAME_MAPPING_FILE, 'r') as f:
                CONGRESS_NAME_MAPPING = json.load(f)
                FEC_SEARCH_NAMES = CONGRESS_NAME_MAPPING.get('fec_search_names', {})
                NICKNAME_TO_LEGAL = CONGRESS_NAME_MAPPING.get('nickname_to_legal', {})
                logger.info(f"Loaded name mapping: {len(FEC_SEARCH_NAMES)} FEC entries, {len(NICKNAME_TO_LEGAL)} nickname mappings")
    except Exception as e:
        logger.warning(f"Could not load name mapping: {e}")

# Load on module import
load_name_mapping()

# Map alternate names to canonical names (used for deduplication and matching)
# Now populated from JSON file plus static fallbacks
NAME_ALIASES = {
    'Valerie Hoyle': 'Val Hoyle',
    'David McCormick': 'Dave McCormick',
    'James French Hill': 'French Hill',
    'Scott Mr Franklin': 'Scott Franklin',
    'Thomas Kean': 'Thomas H. Kean',
    'Neal Dunn': 'Neal P. Dunn',
    'Carol Miller': 'Carol Devine Miller',
    'Rich McCormick': 'Richard McCormick',
    'Marjorie Greene': 'Marjorie Taylor Greene',
    'Rick Allen': 'Richard W. Allen',
    'Bill Keating': 'William R. Keating',
    'Tommy Tuberville': 'Thomas Tuberville',
    'Ted Cruz': 'Rafael Cruz',
    'Angus King': 'Angus S. King',
    # Additional name mappings for photo coverage
    'Joshua Gottheimer': 'Josh Gottheimer',
    'Daniel Newhouse': 'Dan Newhouse',
    'Deborah Dingell': 'Debbie Dingell',
    'Jacob Auchincloss': 'Jake Auchincloss',
    'Rohit Khanna': 'Ro Khanna',
    'Gregory Landsman': 'Greg Landsman',
    'Peter Sessions': 'Pete Sessions',
    'Anthony Wied': 'Tony Wied',
    'Stephen Cohen': 'Steve Cohen',
    'Shrikant Thanedar': 'Shri Thanedar',
    'Christine Smith': 'Tina Smith',
    'Addison McConnell': 'Mitch McConnell',
    'Thomas R. Carper': 'Tom Carper',
    'Susan M. Collins': 'Susan Collins',
}
# Merge in nickname mappings from JSON
NAME_ALIASES.update(NICKNAME_TO_LEGAL)

# Reverse mapping: canonical -> list of alternates (for FEC matching)
NAME_VARIANTS = {}
for alt, canonical in NAME_ALIASES.items():
    if canonical not in NAME_VARIANTS:
        NAME_VARIANTS[canonical] = [canonical]
    NAME_VARIANTS[canonical].append(alt)

# Reverse mapping: formal/legal names -> public names
# Used to normalize names from disclosures to their commonly-used public names
FORMAL_TO_PUBLIC_NAME = {v: k for k, v in NAME_ALIASES.items()}


def normalize_to_public_name(formal_name: str) -> str:
    """Convert a formal/legal name to the publicly-used name.

    Examples:
        'Rafael Cruz' -> 'Ted Cruz'
        'Thomas Tuberville' -> 'Tommy Tuberville'
        'Angus S. King' -> 'Angus King'
    """
    return FORMAL_TO_PUBLIC_NAME.get(formal_name, formal_name)


def convert_last_first_to_first_last(name: str) -> str:
    """Convert 'Last, First' format to 'First Last' format.
    
    Examples:
        'Khanna, Ro' -> 'Ro Khanna'
        'Pelosi, Nancy' -> 'Nancy Pelosi'
        'Taylor Greene, Marjorie' -> 'Marjorie Taylor Greene'
        'Ro Khanna' -> 'Ro Khanna' (already in correct format)
    """
    if not name:
        return name
    if ', ' in name:
        parts = name.split(', ', 1)
        if len(parts) == 2:
            return f"{parts[1]} {parts[0]}"
    return name

# Common nickname mappings for fuzzy matching
NICKNAME_MAP = {
    'Bill': ['William', 'Billy'],
    'William': ['Bill', 'Billy', 'Will'],
    'Bob': ['Robert', 'Bobby'],
    'Robert': ['Bob', 'Bobby', 'Rob'],
    'Dick': ['Richard', 'Rick'],
    'Richard': ['Dick', 'Rick', 'Rich'],
    'Rick': ['Richard', 'Rich'],
    'Rich': ['Richard', 'Rick'],
    'Ted': ['Theodore', 'Edward', 'Rafael'],
    'Jim': ['James', 'Jimmy'],
    'James': ['Jim', 'Jimmy'],
    'Mike': ['Michael'],
    'Michael': ['Mike'],
    'Dave': ['David'],
    'David': ['Dave'],
    'Dan': ['Daniel', 'Danny'],
    'Daniel': ['Dan', 'Danny'],
    'Tom': ['Thomas', 'Tommy'],
    'Thomas': ['Tom', 'Tommy'],
    'Tommy': ['Thomas', 'Tom'],
    'Val': ['Valerie', 'Valentine'],
    'Valerie': ['Val'],
    'Joe': ['Joseph', 'Joey'],
    'Joseph': ['Joe', 'Joey'],
    'Chris': ['Christopher'],
    'Christopher': ['Chris'],
    'Matt': ['Matthew'],
    'Matthew': ['Matt'],
    'Steve': ['Steven', 'Stephen'],
    'Steven': ['Steve'],
    'Stephen': ['Steve'],
    'Greg': ['Gregory'],
    'Gregory': ['Greg'],
    'Tony': ['Anthony'],
    'Anthony': ['Tony'],
    'Shelley': ['Michelle', 'Shellie'],
}


def get_name_variants(name: str) -> List[str]:
    """Generate all possible name variants for matching against FEC data."""
    variants = set()
    name = name.strip()
    variants.add(name.upper())

    parts = name.split()
    if len(parts) < 2:
        return list(variants)

    first_name = parts[0]
    last_name = parts[-1]
    middle_parts = parts[1:-1] if len(parts) > 2 else []

    # Standard formats
    variants.add(f"{last_name}, {first_name}".upper())  # LASTNAME, FIRSTNAME
    variants.add(f"{last_name}, {' '.join([first_name] + middle_parts)}".upper())  # LASTNAME, FIRSTNAME MIDDLE
    variants.add(f"{first_name} {last_name}".upper())  # FIRSTNAME LASTNAME
    variants.add(last_name.upper())  # Just last name (for partial matching)

    # Add nickname variants
    if first_name in NICKNAME_MAP:
        for nickname in NICKNAME_MAP[first_name]:
            variants.add(f"{nickname} {last_name}".upper())
            variants.add(f"{last_name}, {nickname}".upper())

    # Check NAME_VARIANTS for pre-defined alternates
    if name in NAME_VARIANTS:
        for alt in NAME_VARIANTS[name]:
            variants.add(alt.upper())
            alt_parts = alt.split()
            if len(alt_parts) >= 2:
                variants.add(f"{alt_parts[-1]}, {alt_parts[0]}".upper())

    # Also check if this name is an alias
    canonical = NAME_ALIASES.get(name)
    if canonical:
        variants.update(get_name_variants(canonical))

    return list(variants)


def fuzzy_name_match(name1: str, name2: str, threshold: float = 0.85) -> bool:
    """Check if two names match using fuzzy string comparison."""
    from difflib import SequenceMatcher

    # Normalize
    n1 = name1.upper().strip()
    n2 = name2.upper().strip()

    # Exact match
    if n1 == n2:
        return True

    # Check if one contains the other (for partial matches like last name)
    if len(n1) > 3 and len(n2) > 3:
        if n1 in n2 or n2 in n1:
            return True

    # Fuzzy ratio
    ratio = SequenceMatcher(None, n1, n2).ratio()
    return ratio >= threshold


def fetch_bioguide_photo(name: str, bioguide_id: str = None, chamber: str = 'house') -> Optional[str]:
    """
    Get photo URL for a Congress member.

    Uses bioguide.congress.gov photos as the primary source (works for both chambers).
    Falls back to House Clerk images if needed.

    URL patterns:
    - Primary: https://bioguide.congress.gov/bioguide/photo/{first_letter}/{bioguide_id}.jpg
    - Fallback: https://clerk.house.gov/images/members/{bioguide_id}.jpg
    """
    if bioguide_id:
        # Use Bioguide official photos - works for both House and Senate
        # URL pattern: https://bioguide.congress.gov/bioguide/photo/X/X000000.jpg
        first_letter = bioguide_id[0].upper()
        return f"https://bioguide.congress.gov/bioguide/photo/{first_letter}/{bioguide_id}.jpg"

    return None


class WeeklyDataUpdate:
    """Comprehensive weekly data update process."""

    def __init__(self, use_cache: bool = True, cache_max_age_hours: int = 24):
        self.start_time = datetime.now()
        # Data is stored in BigQuery, weekly_dir kept for backward compatibility
        self.weekly_dir = None  # No longer using file-based storage
        self.errors = []
        self.warnings = []

        # Cache settings
        self.use_cache = use_cache
        self.cache_max_age = timedelta(hours=cache_max_age_hours)
        self.cache_dir = Path(__file__).parent / 'data' / 'cache'
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Data containers
        self.officials_data = []
        self.firms_data = []
        self.industries_data = []
        self.committees_data = []
        self.news_data = []
        self.summaries = {}

        # Source status
        self.source_status = {}

    # =========================================================================
    # CACHE MANAGEMENT
    # =========================================================================

    def _get_cache_path(self, phase_name: str) -> Path:
        """Get the cache file path for a given phase."""
        return self.cache_dir / f"{phase_name}_cache.json"

    def _is_cache_valid(self, phase_name: str) -> bool:
        """Check if cache for a phase exists and is not expired."""
        cache_path = self._get_cache_path(phase_name)
        if not cache_path.exists():
            return False

        try:
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)
            cached_time = datetime.fromisoformat(cache_data.get('cached_at', '2000-01-01'))
            return (datetime.now() - cached_time) < self.cache_max_age
        except Exception:
            return False

    def save_cache(self, phase_name: str, data: Any, metadata: Dict = None):
        """Save data to cache after a successful fetch."""
        cache_path = self._get_cache_path(phase_name)
        cache_data = {
            'cached_at': datetime.now().isoformat(),
            'phase': phase_name,
            'metadata': metadata or {},
            'data': data
        }
        try:
            with open(cache_path, 'w') as f:
                json.dump(cache_data, f, indent=2, default=str)
            logger.info(f"  [CACHE] Saved {phase_name} to cache ({cache_path.name})")
        except Exception as e:
            logger.warning(f"  [CACHE] Failed to save {phase_name}: {e}")

    def load_cache(self, phase_name: str) -> Optional[Dict]:
        """Load data from cache if valid."""
        if not self.use_cache:
            return None

        cache_path = self._get_cache_path(phase_name)
        if not self._is_cache_valid(phase_name):
            return None

        try:
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)
            cached_time = cache_data.get('cached_at', 'unknown')
            logger.info(f"  [CACHE] Loading {phase_name} from cache (saved: {cached_time})")
            return cache_data
        except Exception as e:
            logger.warning(f"  [CACHE] Failed to load {phase_name}: {e}")
            return None

    def clear_cache(self, phase_name: str = None):
        """Clear cache for a specific phase or all phases."""
        if phase_name:
            cache_path = self._get_cache_path(phase_name)
            if cache_path.exists():
                cache_path.unlink()
                logger.info(f"  [CACHE] Cleared {phase_name}")
        else:
            for cache_file in self.cache_dir.glob("*_cache.json"):
                cache_file.unlink()
            logger.info("  [CACHE] Cleared all cache files")

    def run(self) -> bool:
        """Run the complete weekly update process."""
        logger.info("=" * 70)
        logger.info("ELECTWATCH WEEKLY DATA UPDATE")
        logger.info(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("Output: BigQuery (justdata-ncrc.electwatch)")
        logger.info("=" * 70)

        try:
            # Phase 1: Fetch all raw data from APIs
            logger.info("\n" + "=" * 70)
            logger.info("PHASE 1: FETCHING DATA FROM APIs")
            logger.info("=" * 70)
            self.fetch_all_data()

            # Phase 2: Process and aggregate data
            logger.info("\n" + "=" * 70)
            logger.info("PHASE 2: PROCESSING AND AGGREGATING DATA")
            logger.info("=" * 70)
            self.process_data()

            # Phase 3: Generate AI summaries
            logger.info("\n" + "=" * 70)
            logger.info("PHASE 3: GENERATING AI SUMMARIES")
            logger.info("=" * 70)
            self.generate_summaries()

            # Phase 4: Save all data
            logger.info("\n" + "=" * 70)
            logger.info("PHASE 4: SAVING DATA TO STORAGE")
            logger.info("=" * 70)
            self.save_all_data()

            # Phase 5: Verify data
            logger.info("\n" + "=" * 70)
            logger.info("PHASE 5: VERIFYING DATA INTEGRITY")
            logger.info("=" * 70)
            verified = self.verify_data()

            # Final summary
            self.print_summary(verified)

            return verified and len(self.errors) == 0

        except Exception as e:
            logger.error(f"Fatal error during update: {e}")
            import traceback
            traceback.print_exc()
            return False

    # =========================================================================
    # PHASE 1: FETCH DATA
    # =========================================================================

    def fetch_all_data(self):
        """Fetch data from all sources.
        
        Since we use bulk FEC data loaded into BigQuery, we only fetch:
        - Congress members from Congress.gov (for basic info)
        - Stock trades from FMP
        - FEC IDs from crosswalk (no API calls)
        - Incremental FEC updates for last 7 days only
        """
        # FIRST: Get ALL Congress members (not just those with financial activity)
        self.fetch_all_congress_members()

        # Then enrich with financial activity data
        self.fetch_fmp_data()  # FMP for congressional stock trades (replaced Quiver)
        self.fetch_fec_crosswalk_ids()  # Get FEC IDs from crosswalk (no API calls)

        # Financial sector data comes from BigQuery (bulk loaded)
        # Only fetch incremental updates for the last 7 days
        self.fetch_incremental_fec_updates()
    
    def fetch_fec_crosswalk_ids(self):
        """Populate FEC IDs from crosswalk (no API calls needed)."""
        from justdata.apps.electwatch.pipeline.fetchers.fec import fetch_fec_crosswalk_ids
        fetch_fec_crosswalk_ids(self)
    
    def fetch_incremental_fec_updates(self):
        """Fetch only the last 7 days of FEC data (incremental update)."""
        from justdata.apps.electwatch.pipeline.fetchers.fec import fetch_incremental_fec_updates
        fetch_incremental_fec_updates(self)

    def _append_pac_contributions_to_bq(self, contributions: list):
        """Append new PAC contributions to BigQuery (incremental update)."""
        from justdata.apps.electwatch.pipeline.fetchers.fec import _append_pac_contributions_to_bq
        _append_pac_contributions_to_bq(self, contributions)

    def fetch_all_congress_members(self):
        """Fetch complete list of all Congress members from Congress.gov API."""
        from justdata.apps.electwatch.pipeline.fetchers.congress import fetch_all_congress_members
        fetch_all_congress_members(self)


    def fetch_fmp_data(self):
        """Fetch congressional trading data from Financial Modeling Prep (FMP)."""
        from justdata.apps.electwatch.pipeline.fetchers.fmp import fetch_fmp_data
        fetch_fmp_data(self)

    def _build_crosswalk_name_lookup(self) -> Dict[str, Dict]:
        """Build comprehensive name lookup using crosswalk nicknames."""
        from justdata.apps.electwatch.pipeline.fetchers.fmp import _build_crosswalk_name_lookup
        return _build_crosswalk_name_lookup(self)

    def _process_fmp_trades(self, all_trades: List[Dict], house_count: int, senate_count: int, from_cache: bool = False):
        """Process FMP trade data and merge into officials using crosswalk for name matching."""
        from justdata.apps.electwatch.pipeline.fetchers.fmp import _process_fmp_trades
        _process_fmp_trades(self, all_trades, house_count, senate_count, from_cache=from_cache)

    def fetch_quiver_data(self):
        """Fetch congressional trading data from Quiver (LEGACY - replaced by FMP)."""
        from justdata.apps.electwatch.pipeline.fetchers.quiver import fetch_quiver_data
        fetch_quiver_data(self)

    def fetch_fec_data(self):
        """Fetch campaign finance data from FEC for each official."""
        from justdata.apps.electwatch.pipeline.fetchers.fec import fetch_fec_data
        fetch_fec_data(self)

    def fetch_financial_pac_data(self):
        """Fetch financial sector PAC contributions by looking at candidate receipts (Schedule A)."""
        from justdata.apps.electwatch.pipeline.fetchers.fec import fetch_financial_pac_data
        fetch_financial_pac_data(self)

    def fetch_individual_financial_contributions(self):
        """Fetch individual contributions from financial sector executives."""
        from justdata.apps.electwatch.pipeline.fetchers.fec import fetch_individual_financial_contributions
        fetch_individual_financial_contributions(self)

    def fetch_congress_data(self):
        """Fetch bills and member data from Congress.gov."""
        from justdata.apps.electwatch.pipeline.fetchers.congress import fetch_congress_data
        fetch_congress_data(self)

    def fetch_finnhub_data(self):
        """Fetch news and stock data from Finnhub."""
        from justdata.apps.electwatch.pipeline.fetchers.finnhub import fetch_finnhub_data
        fetch_finnhub_data(self)

    def fetch_sec_data(self):
        """Fetch SEC EDGAR filings."""
        from justdata.apps.electwatch.pipeline.fetchers.sec import fetch_sec_data
        fetch_sec_data(self)

    def fetch_news_data(self):
        """Fetch news from NewsAPI with quality filtering."""
        from justdata.apps.electwatch.pipeline.fetchers.news import fetch_news_data
        fetch_news_data(self)

    # =========================================================================
    # PHASE 2: PROCESS DATA
    # =========================================================================

    def process_data(self):
        """Process and aggregate fetched data."""
        from justdata.apps.electwatch.pipeline.transformers.normalize import process_data
        process_data(self)

    def process_officials(self):
        """Process and enrich officials data."""
        from justdata.apps.electwatch.pipeline.transformers.normalize import process_officials
        process_officials(self)

    def _build_top_donors(self):
        """Build top_donors list for each official by merging PAC and individual contributions."""
        from justdata.apps.electwatch.pipeline.transformers.normalize import _build_top_donors
        _build_top_donors(self)

    def _normalize_scores_to_zscore(self):
        """Convert raw involvement scores to percentile rank normalized to 1-100 range."""
        from justdata.apps.electwatch.pipeline.transformers.normalize import _normalize_scores_to_zscore
        _normalize_scores_to_zscore(self)

    def process_firms(self):
        """Build comprehensive firm records from actual trade data."""
        from justdata.apps.electwatch.pipeline.transformers.normalize import process_firms
        process_firms(self)

    def process_industries(self):
        """Build industry aggregations from firms and officials data."""
        from justdata.apps.electwatch.pipeline.transformers.normalize import process_industries
        process_industries(self)

    def process_committees(self):
        """Build committee data (mostly static but enriched with live stats)."""
        from justdata.apps.electwatch.pipeline.transformers.normalize import process_committees
        process_committees(self)

    # =========================================================================
    # PHASE 3: GENERATE AI SUMMARIES
    # =========================================================================

    def generate_summaries(self):
        """Generate AI summaries using Claude."""
        from justdata.apps.electwatch.pipeline.insights import generate_summaries
        generate_summaries(self)

    def _generate_pattern_insights(self) -> List[Dict[str, Any]]:
        """Generate AI pattern insights for the dashboard."""
        from justdata.apps.electwatch.pipeline.insights import generate_pattern_insights
        return generate_pattern_insights(self)

    # =========================================================================
    # PHASE 4: SAVE DATA
    # =========================================================================

    def save_all_data(self):
        """Save all processed data to storage."""
        from justdata.apps.electwatch.pipeline.loaders.bigquery import save_all_data
        save_all_data(self)

    def _generate_matching_report(self) -> Dict:
        """Generate report of matching success/failure rates."""
        from justdata.apps.electwatch.pipeline.loaders.bigquery import _generate_matching_report
        return _generate_matching_report(self)

    def _save_matching_report(self, report: Dict):
        """Save matching report to data/current/matching_report.json."""
        from justdata.apps.electwatch.pipeline.loaders.bigquery import _save_matching_report
        _save_matching_report(report)

    def _validate_data_consistency(self) -> List[str]:
        """Validate that all data is properly connected and consistent."""
        from justdata.apps.electwatch.pipeline.loaders.bigquery import _validate_data_consistency
        return _validate_data_consistency(self)

    # =========================================================================
    # PHASE 5: VERIFY DATA
    # =========================================================================

    def verify_data(self) -> bool:
        """Verify data integrity."""
        from justdata.apps.electwatch.services.data_store import (
            get_officials, get_firms, get_industries,
            get_committees, get_news, get_metadata
        )

        issues = []

        # Check officials
        officials = get_officials()
        if len(officials) < 10:
            issues.append(f"Too few officials: {len(officials)}")

        # Check firms
        firms = get_firms()
        if len(firms) < 5:
            issues.append(f"Too few firms: {len(firms)}")

        # Check metadata
        metadata = get_metadata()
        if metadata.get('status') != 'valid':
            issues.append("Metadata status is not 'valid'")

        if issues:
            logger.error("Data verification failed:")
            for issue in issues:
                logger.error(f"  - {issue}")
            return False

        logger.info("Data verification passed!")
        logger.info(f"  - Officials: {len(officials)}")
        logger.info(f"  - Firms: {len(firms)}")
        logger.info(f"  - Industries: {len(get_industries())}")
        logger.info(f"  - Committees: {len(get_committees())}")
        logger.info(f"  - News: {len(get_news())}")

        return True

    def print_summary(self, verified: bool):
        """Print final summary."""
        duration = (datetime.now() - self.start_time).total_seconds()

        logger.info("\n" + "=" * 70)
        logger.info("UPDATE SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Status: {'SUCCESS' if verified else 'FAILED'}")
        logger.info(f"Duration: {duration:.1f} seconds")
        logger.info("Data saved to: BigQuery (justdata-ncrc.electwatch)")

        logger.info("\nData Sources:")
        for source, status in self.source_status.items():
            emoji = "[OK]" if status.get('status') == 'success' else "[FAIL]"
            logger.info(f"  {emoji} {source}: {status.get('status')}")

        if self.errors:
            logger.info(f"\nErrors ({len(self.errors)}):")
            for error in self.errors:
                logger.info(f"  - {error}")

        if self.warnings:
            logger.info(f"\nWarnings ({len(self.warnings)}):")
            for warning in self.warnings:
                logger.info(f"  - {warning}")

        logger.info("\nCounts:")
        logger.info(f"  - Officials: {len(self.officials_data)}")
        logger.info(f"  - Firms: {len(self.firms_data)}")
        logger.info(f"  - News: {len(self.news_data)}")

        logger.info("=" * 70)


def main():
    """Main entry point."""
    updater = WeeklyDataUpdate()
    success = updater.run()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
