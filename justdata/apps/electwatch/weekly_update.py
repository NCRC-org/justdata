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
        from justdata.apps.electwatch.services.data_store import get_weekly_data_path

        self.start_time = datetime.now()
        self.weekly_dir = get_weekly_data_path(self.start_time)
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
        logger.info(f"Output directory: {self.weekly_dir}")
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
        """Fetch data from all sources."""
        # FIRST: Get ALL Congress members (not just those with financial activity)
        self.fetch_all_congress_members()

        # Then enrich with financial activity data
        self.fetch_fmp_data()  # FMP for congressional stock trades (replaced Quiver)
        self.fetch_fec_data()  # Aggregate FEC data + committee IDs

        # Financial sector deep dive
        self.fetch_financial_pac_data()  # PAC contributions from financial sector
        self.fetch_individual_financial_contributions()  # Personal money from financial execs

    def fetch_all_congress_members(self):
        """Fetch complete list of all Congress members from Congress.gov API."""
        logger.info("--- Fetching ALL Congress Members from Congress.gov ---")

        # Try to load from cache first
        cached = self.load_cache('congress_members')
        if cached:
            members = cached.get('data', [])
            if members:
                self.officials_data = members
                self._officials_by_name = {}
                for m in self.officials_data:
                    name_key = m['name'].lower().strip()
                    self._officials_by_name[name_key] = m

                    # Handle "Last, First" format (Congress.gov) vs "First Last" (FMP)
                    name = m['name']
                    if ',' in name:
                        # "Pelosi, Nancy" -> last_name = "pelosi"
                        last_name = name.split(',')[0].strip().lower()
                    else:
                        # "Nancy Pelosi" -> last_name = "pelosi"
                        parts = name.split()
                        last_name = parts[-1].lower() if parts else name_key

                    if last_name and last_name not in self._officials_by_name:
                        self._officials_by_name[last_name] = m

                self.source_status['congress_members'] = cached.get('metadata', {})
                self.source_status['congress_members']['from_cache'] = True
                logger.info(f"  [CACHE] Loaded {len(members)} Congress members from cache")
                return

        try:
            from justdata.apps.electwatch.services.congress_api_client import CongressAPIClient
            client = CongressAPIClient()

            members = client.get_all_members()

            if members:
                self.officials_data = members
                self._officials_by_name = {}
                for m in self.officials_data:
                    name_key = m['name'].lower().strip()
                    self._officials_by_name[name_key] = m

                    # Handle "Last, First" format (Congress.gov) vs "First Last" (FMP)
                    name = m['name']
                    if ',' in name:
                        # "Pelosi, Nancy" -> last_name = "pelosi"
                        last_name = name.split(',')[0].strip().lower()
                    else:
                        # "Nancy Pelosi" -> last_name = "pelosi"
                        parts = name.split()
                        last_name = parts[-1].lower() if parts else name_key

                    if last_name and last_name not in self._officials_by_name:
                        self._officials_by_name[last_name] = m

                house = len([m for m in members if m['chamber'] == 'house'])
                senate = len([m for m in members if m['chamber'] == 'senate'])

                self.source_status['congress_members'] = {
                    'status': 'success',
                    'house_members': house,
                    'senate_members': senate,
                    'total': len(members),
                    'timestamp': datetime.now().isoformat()
                }
                logger.info(f"Fetched {len(members)} Congress members ({house} House, {senate} Senate)")

                # Save to cache
                self.save_cache('congress_members', members, self.source_status['congress_members'])
            else:
                logger.warning("No Congress members fetched - check API key")
                self.warnings.append("Congress.gov: No members fetched")
                self.source_status['congress_members'] = {'status': 'failed', 'error': 'No members returned'}

        except Exception as e:
            logger.error(f"Congress members fetch failed: {e}")
            self.warnings.append(f"Congress.gov members: {e}")
            self.source_status['congress_members'] = {'status': 'failed', 'error': str(e)}


    def fetch_fmp_data(self):
        """Fetch congressional trading data from Financial Modeling Prep (FMP).

        FMP provides comprehensive STOCK Act disclosure data for both House and Senate,
        focused on financial sector stocks only.
        """
        logger.info("\n--- Fetching FMP Congressional Trading (Financial Sector) ---")

        # Try to load from cache first
        cached = self.load_cache('fmp_trades')
        if cached:
            trades_data = cached.get('data', {})
            house_trades = trades_data.get('house', [])
            senate_trades = trades_data.get('senate', [])
            all_trades = house_trades + senate_trades
            if all_trades:
                logger.info(f"  [CACHE] Loaded {len(all_trades)} trades from cache")
                self._process_fmp_trades(all_trades, len(house_trades), len(senate_trades), from_cache=True)
                return

        try:
            from justdata.apps.electwatch.services.fmp_client import FMPClient, ALL_FINANCIAL_SYMBOLS
            client = FMPClient()

            if not client.test_connection():
                raise Exception("FMP API connection failed")

            # Calculate date range (last 24 months / 730 days)
            from_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')

            # Fetch financial sector trades only
            logger.info(f"Fetching trades for {len(ALL_FINANCIAL_SYMBOLS)} financial sector symbols...")
            trades_data = client.get_financial_sector_trades(from_date=from_date)

            house_trades = trades_data.get('house', [])
            senate_trades = trades_data.get('senate', [])
            all_trades = house_trades + senate_trades

            logger.info(f"Fetched {len(house_trades)} House trades, {len(senate_trades)} Senate trades")
            logger.info(f"Total: {len(all_trades)} financial sector trades")

            # Save to cache immediately after successful fetch
            self.save_cache('fmp_trades', trades_data, {
                'house_trades': len(house_trades),
                'senate_trades': len(senate_trades),
                'total_trades': len(all_trades)
            })

            # Process the trades
            self._process_fmp_trades(all_trades, len(house_trades), len(senate_trades), from_cache=False)

        except Exception as e:
            logger.error(f"FMP fetch failed: {e}")
            import traceback
            traceback.print_exc()
            self.errors.append(f"FMP: {e}")
            self.source_status['fmp'] = {'status': 'failed', 'error': str(e)}

    def _build_crosswalk_name_lookup(self) -> Dict[str, Dict]:
        """
        Build comprehensive name lookup using crosswalk nicknames.

        This creates a mapping from all possible name variations (legal names,
        nicknames, etc.) to officials, enabling much better matching for
        FMP trade disclosures.

        Returns:
            Dict mapping lowercase name variations to official records
        """
        try:
            from justdata.apps.electwatch.services.crosswalk import get_crosswalk
            crosswalk = get_crosswalk()
        except Exception as e:
            logger.warning(f"Could not load crosswalk for name lookup: {e}")
            return self._officials_by_name if hasattr(self, '_officials_by_name') else {}

        lookup = {}
        for official in self.officials_data:
            bioguide_id = official.get('bioguide_id')
            name = official.get('name', '')

            # Add canonical name
            if name:
                lookup[name.lower()] = official

            # Add last name
            parts = name.split()
            if len(parts) > 1:
                last_name = parts[-1].lower()
                if last_name not in lookup:
                    lookup[last_name] = official

            # Add crosswalk variations (nicknames, legal names)
            if bioguide_id:
                variations = crosswalk.get_name_variations(bioguide_id)
                for variation in variations:
                    key = variation.lower()
                    if key not in lookup:
                        lookup[key] = official

        logger.info(f"Built crosswalk name lookup with {len(lookup)} entries for {len(self.officials_data)} officials")
        return lookup

    def _process_fmp_trades(self, all_trades: List[Dict], house_count: int, senate_count: int, from_cache: bool = False):
        """Process FMP trade data and merge into officials using crosswalk for name matching."""
        # Aggregate by politician
        politicians = {}
        for trade in all_trades:
            raw_name = trade.get('politician_name', 'Unknown')
            if not raw_name or raw_name == 'Unknown' or raw_name.strip() == '':
                continue

            # Normalize to public name (e.g., 'Rafael Cruz' -> 'Ted Cruz')
            name = normalize_to_public_name(raw_name)

            if name not in politicians:
                # Determine chamber from trade or infer from data
                chamber = trade.get('chamber', '')

                politicians[name] = {
                    'name': name,
                    'party': '',  # FMP doesn't provide party, will be enriched later
                    'state': trade.get('district', '')[:2] if trade.get('district') else '',
                    'chamber': chamber,
                    'bioguide_id': '',
                    'trades': [],
                    'total_trades': 0,
                    'purchase_count': 0,
                    'sale_count': 0,
                    'total_min': 0,
                    'total_max': 0,
                    'purchases_min': 0,
                    'purchases_max': 0,
                    'sales_min': 0,
                    'sales_max': 0,
                    'symbols_traded': set(),
                    'trade_score': 0,  # New scoring: bucket_low / 1000 per trade
                }

            politicians[name]['trades'].append(trade)
            politicians[name]['total_trades'] += 1
            politicians[name]['symbols_traded'].add(trade.get('ticker', ''))

            amt = trade.get('amount', {})
            trade_min = amt.get('min', 0)
            trade_max = amt.get('max', 0)

            if trade.get('type') == 'purchase':
                politicians[name]['purchase_count'] += 1
                politicians[name]['purchases_min'] += trade_min
                politicians[name]['purchases_max'] += trade_max
            elif trade.get('type') == 'sale':
                politicians[name]['sale_count'] += 1
                politicians[name]['sales_min'] += trade_min
                politicians[name]['sales_max'] += trade_max

            politicians[name]['total_min'] += trade_min
            politicians[name]['total_max'] += trade_max

            # New scoring: bucket_low_end / 1000 per trade
            # So $1K-$15K = 1pt, $15K-$50K = 15pt, $50K-$100K = 50pt, etc.
            politicians[name]['trade_score'] += trade_min / 1000

        # Convert to list and finalize
        for name, data in politicians.items():
            data['id'] = data['bioguide_id'] or name.lower().replace(' ', '_').replace('.', '')
            data['stock_trades_min'] = data['total_min']
            data['stock_trades_max'] = data['total_max']
            data['stock_trades_display'] = f"${data['total_min']:,.0f} - ${data['total_max']:,.0f}"

            # Separate display strings for buys and sells
            data['purchases_display'] = f"${data['purchases_min']:,.0f} - ${data['purchases_max']:,.0f}"
            data['sales_display'] = f"${data['sales_min']:,.0f} - ${data['sales_max']:,.0f}"

            # Convert set to list for JSON serialization
            data['symbols_traded'] = list(data['symbols_traded'])

            # Initial score placeholder
            data['involvement_score'] = 0

            # Keep only last 50 trades for each official
            data['trades'] = sorted(data['trades'],
                                   key=lambda x: x.get('transaction_date', ''),
                                   reverse=True)[:50]

        # Merge trade data into existing officials using crosswalk-enhanced name lookup
        if hasattr(self, '_officials_by_name') and self._officials_by_name:
            # Build comprehensive name lookup using crosswalk (includes nicknames)
            crosswalk_lookup = self._build_crosswalk_name_lookup()

            # Track matching stats
            enriched_count = 0
            new_count = 0
            unmatched_names = []

            for name, trade_data in politicians.items():
                # Try to find matching official using crosswalk-enhanced lookup
                name_lower = name.lower().strip()
                parts = name.split()
                last_name = parts[-1].lower() if parts else name_lower

                matching_official = None

                # Try full name first (in crosswalk lookup)
                if name_lower in crosswalk_lookup:
                    matching_official = crosswalk_lookup[name_lower]
                # Try last name
                elif last_name in crosswalk_lookup:
                    matching_official = crosswalk_lookup[last_name]
                # Try original _officials_by_name as fallback
                elif name_lower in self._officials_by_name:
                    matching_official = self._officials_by_name[name_lower]
                elif last_name in self._officials_by_name:
                    matching_official = self._officials_by_name[last_name]

                if matching_official:
                    # Enrich existing official with trade data
                    matching_official['trades'] = trade_data['trades']
                    matching_official['total_trades'] = trade_data['total_trades']
                    matching_official['purchase_count'] = trade_data['purchase_count']
                    matching_official['sale_count'] = trade_data['sale_count']
                    matching_official['stock_trades_min'] = trade_data['total_min']
                    matching_official['stock_trades_max'] = trade_data['total_max']
                    matching_official['stock_trades_display'] = trade_data['stock_trades_display']
                    matching_official['purchases_display'] = trade_data['purchases_display']
                    matching_official['sales_display'] = trade_data['sales_display']
                    matching_official['symbols_traded'] = trade_data['symbols_traded']
                    matching_official['trade_score'] = trade_data.get('trade_score', 0)
                    matching_official['has_financial_activity'] = True
                    enriched_count += 1
                else:
                    # Track unmatched names for reporting
                    unmatched_names.append(name)
                    # Official not in Congress roster - add as new (rare case)
                    trade_data['has_financial_activity'] = True
                    self.officials_data.append(trade_data)
                    new_count += 1

            # Store unmatched names for matching report
            self._unmatched_fmp_names = unmatched_names

            logger.info(f"FMP Trade Matching: {enriched_count} matched via crosswalk, "
                       f"{new_count} new/unmatched")
            if unmatched_names:
                logger.info(f"  Unmatched FMP names: {unmatched_names[:10]}{'...' if len(unmatched_names) > 10 else ''}")
        else:
            # No Congress roster - use trade data as officials (fallback)
            self.officials_data = list(politicians.values())
            self._unmatched_fmp_names = []

        self.source_status['fmp'] = {
            'status': 'success',
            'house_trades': house_count,
            'senate_trades': senate_count,
            'total_trades': len(all_trades),
            'officials': len(self.officials_data),
            'matched_via_crosswalk': enriched_count if 'enriched_count' in dir() else 0,
            'unmatched_count': len(self._unmatched_fmp_names) if hasattr(self, '_unmatched_fmp_names') else 0,
            'from_cache': from_cache,
            'timestamp': datetime.now().isoformat()
        }
        logger.info(f"Processed {len(self.officials_data)} officials from FMP trade data")

    def fetch_quiver_data(self):
        """Fetch congressional trading data from Quiver (LEGACY - replaced by FMP)."""
        logger.info("\n--- Fetching Quiver Congressional Trading ---")
        try:
            from justdata.apps.electwatch.services.quiver_client import QuiverClient
            client = QuiverClient()

            if not client.test_connection():
                raise Exception("Quiver API connection failed")

            # Fetch all trades from the past year
            trades = client.get_recent_trades(days=365)
            logger.info(f"Fetched {len(trades) if trades else 0} trades from Quiver")

            # Aggregate by politician
            politicians = {}
            for trade in (trades or []):
                name = trade.get('politician_name', 'Unknown')
                if name not in politicians:
                    politicians[name] = {
                        'name': name,
                        'party': trade.get('party', ''),
                        'state': trade.get('state', ''),
                        'chamber': trade.get('chamber', ''),
                        'bioguide_id': trade.get('bioguide_id', ''),
                        'trades': [],
                        'total_trades': 0,
                        'purchase_count': 0,
                        'sale_count': 0,
                        'total_min': 0,
                        'total_max': 0,
                        # Separate tracking for buys and sells
                        'purchases_min': 0,
                        'purchases_max': 0,
                        'sales_min': 0,
                        'sales_max': 0,
                    }

                politicians[name]['trades'].append(trade)
                politicians[name]['total_trades'] += 1

                amt = trade.get('amount', {})
                trade_min = amt.get('min', 0)
                trade_max = amt.get('max', 0)

                if trade.get('type') == 'purchase':
                    politicians[name]['purchase_count'] += 1
                    politicians[name]['purchases_min'] += trade_min
                    politicians[name]['purchases_max'] += trade_max
                elif trade.get('type') == 'sale':
                    politicians[name]['sale_count'] += 1
                    politicians[name]['sales_min'] += trade_min
                    politicians[name]['sales_max'] += trade_max

                politicians[name]['total_min'] += trade_min
                politicians[name]['total_max'] += trade_max

            # Convert to list
            for name, data in politicians.items():
                data['id'] = data['bioguide_id'] or name.lower().replace(' ', '_')
                data['stock_trades_min'] = data['total_min']
                data['stock_trades_max'] = data['total_max']
                data['stock_trades_display'] = f"${data['total_min']:,.0f} - ${data['total_max']:,.0f}"

                # Separate display strings for buys and sells
                data['purchases_display'] = f"${data['purchases_min']:,.0f} - ${data['purchases_max']:,.0f}"
                data['sales_display'] = f"${data['sales_min']:,.0f} - ${data['sales_max']:,.0f}"

                # Initial score placeholder - will be recalculated in process_officials
                data['involvement_score'] = 0
                # Keep only last 50 trades for each official
                data['trades'] = data['trades'][:50]

            # Merge trade data into existing officials (from fetch_all_congress_members)
            if hasattr(self, '_officials_by_name') and self._officials_by_name:
                # We have the full Congress roster - merge trades into existing entries
                enriched_count = 0
                new_count = 0
                for name, trade_data in politicians.items():
                    # Try to find matching official
                    name_lower = name.lower().strip()
                    parts = name.split()
                    last_name = parts[-1].lower() if parts else name_lower
                    
                    matching_official = None
                    # Try full name first
                    if name_lower in self._officials_by_name:
                        matching_official = self._officials_by_name[name_lower]
                    # Try last name
                    elif last_name in self._officials_by_name:
                        matching_official = self._officials_by_name[last_name]
                    
                    if matching_official:
                        # Enrich existing official with trade data
                        matching_official['trades'] = trade_data['trades']
                        matching_official['total_trades'] = trade_data['total_trades']
                        matching_official['purchase_count'] = trade_data['purchase_count']
                        matching_official['sale_count'] = trade_data['sale_count']
                        matching_official['stock_trades_min'] = trade_data['total_min']
                        matching_official['stock_trades_max'] = trade_data['total_max']
                        matching_official['stock_trades_display'] = trade_data['stock_trades_display']
                        matching_official['purchases_display'] = trade_data['purchases_display']
                        matching_official['sales_display'] = trade_data['sales_display']
                        matching_official['symbols_traded'] = trade_data['symbols_traded']
                        matching_official['trade_score'] = trade_data.get('trade_score', 0)
                        matching_official['has_financial_activity'] = True
                        enriched_count += 1
                    else:
                        # Official not in Congress roster - add as new (rare case)
                        trade_data['has_financial_activity'] = True
                        self.officials_data.append(trade_data)
                        new_count += 1
                
                logger.info(f"Enriched {enriched_count} existing officials, added {new_count} new")
            else:
                # No Congress roster - use trade data as officials (fallback)
                self.officials_data = list(politicians.values())

            self.source_status['quiver'] = {
                'status': 'success',
                'records': len(trades) if trades else 0,
                'officials': len(self.officials_data),
                'timestamp': datetime.now().isoformat()
            }
            logger.info(f"Processed {len(self.officials_data)} officials from trade data")

        except Exception as e:
            logger.error(f"Quiver fetch failed: {e}")
            self.errors.append(f"Quiver: {e}")
            self.source_status['quiver'] = {'status': 'failed', 'error': str(e)}

    def fetch_fec_data(self):
        """
        Fetch campaign finance data from FEC for each official.

        Uses the congress-legislators crosswalk for direct bioguide_id -> fec_candidate_id
        mapping, eliminating error-prone name matching. This improves match rate from ~6%
        to ~95%+ for current Congress members.
        """
        logger.info("\n--- Fetching FEC Campaign Finance (via Crosswalk) ---")

        # Load cached progress to see which officials already have FEC data
        cached = self.load_cache('fec_enrichment')
        cached_officials = set()
        if cached:
            cached_officials = set(cached.get('data', {}).get('processed_bioguides', []))
            logger.info(f"  [CACHE] Found {len(cached_officials)} already-enriched officials")

        try:
            import time
            from justdata.apps.electwatch.services.fec_client import FECClient
            from justdata.apps.electwatch.services.crosswalk import get_crosswalk

            client = FECClient()
            crosswalk = get_crosswalk()

            if not client.test_connection():
                raise Exception("FEC API connection failed")

            # Get crosswalk statistics
            crosswalk_stats = crosswalk.get_statistics()
            logger.info(f"  Crosswalk loaded: {crosswalk_stats['total_members']} members, "
                       f"{crosswalk_stats['fec_coverage_pct']}% have FEC IDs")

            # Track matching results
            officials_enriched = 0
            total_contributions = 0
            api_calls = 0
            max_api_calls = 700  # FEC allows 1000/hour
            processed_bioguides = list(cached_officials)
            crosswalk_matches = 0
            crosswalk_misses = []  # Track officials not in crosswalk
            save_interval = 50

            for idx, official in enumerate(self.officials_data):
                bioguide_id = official.get('bioguide_id', '')
                name = official.get('name', '')

                if not bioguide_id:
                    logger.debug(f"Skipping {name}: no bioguide_id")
                    continue

                # ALWAYS set fec_candidate_id from crosswalk (even for cached officials)
                # This ensures the ID is available for downstream fetches (financial PACs, etc.)
                if not official.get('fec_candidate_id'):
                    fec_id = crosswalk.get_fec_id(bioguide_id)
                    if fec_id:
                        official['fec_candidate_id'] = fec_id
                        # Also store additional crosswalk IDs
                        member_info = crosswalk.get_member_info(bioguide_id)
                        if member_info:
                            if member_info.get('opensecrets_id'):
                                official['opensecrets_id'] = member_info['opensecrets_id']
                            if member_info.get('govtrack_id'):
                                official['govtrack_id'] = member_info['govtrack_id']

                # Skip API calls if already processed (from cache)
                if bioguide_id in cached_officials:
                    if official.get('fec_candidate_id'):
                        crosswalk_matches += 1
                        officials_enriched += 1
                    continue

                if api_calls >= max_api_calls:
                    logger.info(f"FEC: Reached API call limit ({max_api_calls}), stopping")
                    break

                # Rate limit protection
                if api_calls > 0 and api_calls % 100 == 0:
                    logger.info(f"  FEC: Pausing 60s after {api_calls} API calls (rate limit protection)...")
                    time.sleep(60)

                try:
                    # Use crosswalk for direct FEC ID lookup (no name matching!)
                    fec_id = crosswalk.get_fec_id(bioguide_id)

                    if fec_id:
                        crosswalk_matches += 1
                        official['fec_candidate_id'] = fec_id

                        # Also store additional crosswalk IDs for reference
                        member_info = crosswalk.get_member_info(bioguide_id)
                        if member_info:
                            if member_info.get('opensecrets_id'):
                                official['opensecrets_id'] = member_info['opensecrets_id']
                            if member_info.get('govtrack_id'):
                                official['govtrack_id'] = member_info['govtrack_id']

                        # Add delay before FEC API call
                        time.sleep(0.5)

                        # Fetch candidate totals directly by FEC ID
                        try:
                            totals = client.get_candidate_totals(fec_id, cycle=2024)
                            api_calls += 1

                            if totals:
                                total_amount = totals.get('receipts', 0)
                                individual_contribs = totals.get('individual_contributions', 0)
                                pac_contribs = totals.get('pac_contributions', 0)

                                # Store all contribution data
                                official['contributions'] = pac_contribs
                                official['total_receipts'] = total_amount
                                official['individual_contributions'] = individual_contribs
                                official['pac_contributions'] = pac_contribs
                                official['fec_cycle'] = totals.get('cycle')

                                total_contributions += 1
                                officials_enriched += 1
                                logger.info(f"  FEC: {name} ({bioguide_id}) - ${pac_contribs:,.0f} PAC (${total_amount:,.0f} total)")
                            else:
                                # FEC ID found but no totals data
                                officials_enriched += 1
                                logger.debug(f"  FEC: {name} - ID found but no totals data")

                        except Exception as ce:
                            logger.debug(f"Could not fetch totals for {name} ({fec_id}): {ce}")
                            officials_enriched += 1  # Still count as enriched (has FEC ID)

                    else:
                        # Not in crosswalk - track for reporting
                        crosswalk_misses.append({
                            'name': name,
                            'bioguide_id': bioguide_id,
                            'chamber': official.get('chamber', ''),
                            'state': official.get('state', '')
                        })
                        logger.debug(f"  No FEC ID in crosswalk for {name} ({bioguide_id})")

                except Exception as e:
                    logger.debug(f"FEC lookup failed for {name}: {e}")

                # Mark as processed
                if bioguide_id and bioguide_id not in processed_bioguides:
                    processed_bioguides.append(bioguide_id)

                # Save progress periodically
                if len(processed_bioguides) % save_interval == 0:
                    self.save_cache('fec_enrichment', {
                        'processed_bioguides': processed_bioguides,
                        'officials_enriched': officials_enriched,
                        'api_calls': api_calls,
                        'crosswalk_matches': crosswalk_matches
                    }, {'partial': True, 'count': len(processed_bioguides)})

            # Final cache save
            self.save_cache('fec_enrichment', {
                'processed_bioguides': processed_bioguides,
                'officials_enriched': officials_enriched,
                'api_calls': api_calls,
                'crosswalk_matches': crosswalk_matches,
                'crosswalk_misses': crosswalk_misses
            }, {'partial': False, 'count': len(processed_bioguides)})

            # Calculate match rate
            total_with_bioguide = sum(1 for o in self.officials_data if o.get('bioguide_id'))
            match_rate = (crosswalk_matches / total_with_bioguide * 100) if total_with_bioguide else 0

            self.source_status['fec'] = {
                'status': 'success',
                'officials_enriched': officials_enriched,
                'total_contributions': total_contributions,
                'api_calls': api_calls,
                'from_cache_count': len(cached_officials),
                'crosswalk_matches': crosswalk_matches,
                'crosswalk_misses': len(crosswalk_misses),
                'match_rate_pct': round(match_rate, 1),
                'timestamp': datetime.now().isoformat()
            }

            logger.info(f"FEC: Enriched {officials_enriched} officials via crosswalk "
                       f"({crosswalk_matches} matches, {len(crosswalk_misses)} misses, "
                       f"{match_rate:.1f}% rate, {api_calls} API calls)")

            if crosswalk_misses:
                logger.info(f"  Officials without FEC ID in crosswalk: {[m['name'] for m in crosswalk_misses[:5]]}...")

        except Exception as e:
            logger.error(f"FEC fetch failed: {e}")
            self.warnings.append(f"FEC: {e}")
            self.source_status['fec'] = {'status': 'failed', 'error': str(e)}
            # Save whatever progress we made before the error
            if 'processed_bioguides' in dir():
                self.save_cache('fec_enrichment', {
                    'processed_bioguides': processed_bioguides,
                    'officials_enriched': officials_enriched if 'officials_enriched' in dir() else 0,
                    'api_calls': api_calls if 'api_calls' in dir() else 0
                }, {'partial': True, 'error': str(e)})

    def fetch_financial_pac_data(self):
        """Fetch financial sector PAC contributions by looking at candidate receipts (Schedule A)."""
        logger.info("\n--- Fetching Financial Sector PAC Contributions (Schedule A Receipts) ---")

        import requests
        import time

        api_key = os.getenv('FEC_API_KEY')
        if not api_key:
            logger.warning("FEC_API_KEY not set - skipping financial PAC data")
            self.source_status['financial_pacs'] = {'status': 'skipped', 'reason': 'No API key'}
            return

        # Keywords to identify financial sector PACs
        FINANCIAL_KEYWORDS = [
            'BANK', 'FINANCIAL', 'CAPITAL', 'CREDIT', 'INSURANCE', 'INVEST',
            'SECURITIES', 'MORTGAGE', 'WELLS', 'CHASE', 'CITI', 'GOLDMAN',
            'MORGAN STANLEY', 'AMERICAN EXPRESS', 'VISA', 'MASTERCARD', 'BLACKROCK',
            'FIDELITY', 'SCHWAB', 'PRUDENTIAL', 'METLIFE', 'AIG', 'TRUIST',
            'PNC', 'REGIONS', 'FIFTH THIRD', 'US BANCORP', 'HUNTINGTON',
            'PAYPAL', 'COINBASE', 'ROBINHOOD', 'ALLY', 'SYNCHRONY', 'DISCOVER',
            'LENDING', 'LOAN', 'FINTECH', 'CRYPTO', 'BLOCKCHAIN', 'EXCHANGE',
            'ASSET', 'FUND', 'MUTUAL', 'EQUITY', 'HEDGE', 'PRIVATE EQUITY',
            'VENTURE', 'BROKER', 'DEALER', 'TRADING', 'REAL ESTATE INVEST',
            'REIT', 'SAVINGS', 'THRIFT', 'CONSUMER BANKER', 'COMMUNITY BANKER',
            'INDEPENDENT BANKER', 'AMERICAN BANKER', 'CREDIT UNION'
        ]

        # Calculate rolling 24-month date window
        rolling_end_date = datetime.now()
        rolling_start_date = rolling_end_date - timedelta(days=730)  # 24 months
        min_date_str = rolling_start_date.strftime('%Y-%m-%d')
        max_date_str = rolling_end_date.strftime('%Y-%m-%d')
        logger.info(f"  Using rolling 24-month window: {min_date_str} to {max_date_str}")

        def get_financial_pac_total(committee_id: str) -> dict:
            """
            Get PAC contributions to a candidate's committee (rolling 24 months).

            Returns dict with:
                - financial_total: $ from financial sector PACs (numerator)
                - all_pac_total: $ from ALL PACs (denominator)
                - financial_pct: Percentage from financial sector
                - financial_contributors: List of financial PAC contributors
            """
            url = 'https://api.open.fec.gov/v1/schedules/schedule_a/'
            financial_total = 0
            all_pac_total = 0
            contributors = []
            page = 1
            max_pages = 20  # Limit pages to avoid excessive API calls

            while page <= max_pages:
                params = {
                    'api_key': api_key,
                    'committee_id': committee_id,
                    'min_date': min_date_str,
                    'max_date': max_date_str,
                    'contributor_type': 'committee',
                    'per_page': 100,
                    'page': page
                }

                try:
                    time.sleep(0.5)  # Rate limiting
                    r = requests.get(url, params=params, timeout=60)

                    if r.status_code == 429:
                        logger.warning("  Rate limited - waiting 60 seconds")
                        time.sleep(60)
                        continue

                    if not r.ok:
                        break

                    data = r.json()
                    results = data.get('results', [])
                    if not results:
                        break

                    for c in results:
                        name = c.get('contributor_name', '').upper()
                        amt = c.get('contribution_receipt_amount', 0)
                        # Only count PAC contributions (not employee contributions)
                        is_pac = 'PAC' in name or 'POLITICAL ACTION' in name or 'POLITICAL FUND' in name

                        if amt > 0 and is_pac:
                            # Track ALL PAC contributions (denominator)
                            all_pac_total += amt

                            # Track financial sector PACs (numerator)
                            if any(kw in name for kw in FINANCIAL_KEYWORDS):
                                financial_total += amt
                                contributors.append({
                                    'name': c.get('contributor_name', ''),
                                    'amount': amt
                                })

                    pages = data.get('pagination', {}).get('pages', 1)
                    if page >= pages:
                        break
                    page += 1

                except Exception as e:
                    logger.error(f"  Error fetching receipts: {e}")
                    break

            # Calculate percentage
            financial_pct = 0
            if all_pac_total > 0:
                financial_pct = round((financial_total / all_pac_total) * 100, 1)

            return {
                'financial_total': financial_total,
                'all_pac_total': all_pac_total,
                'financial_pct': financial_pct,
                'financial_contributors': contributors
            }

        def get_committee_from_candidate_id(fec_candidate_id: str) -> Optional[str]:
            """Get principal campaign committee ID directly from FEC candidate ID.

            Uses the /candidate/{candidate_id}/committees/ endpoint to get committee list.
            Returns the first committee (principal campaign committee).
            """
            if not fec_candidate_id:
                return None

            # Use the /committees/ sub-endpoint which returns actual committee data
            url = f'https://api.open.fec.gov/v1/candidate/{fec_candidate_id}/committees/'
            params = {
                'api_key': api_key,
                'designation': 'P'  # Principal campaign committee
            }

            try:
                time.sleep(0.3)
                r = requests.get(url, params=params, timeout=30)
                if r.ok:
                    data = r.json()
                    results = data.get('results', [])
                    if results:
                        committee_id = results[0].get('committee_id')
                        logger.debug(f"  Found committee {committee_id} for candidate {fec_candidate_id}")
                        return committee_id
                    else:
                        # Try without designation filter (some candidates don't have P designation)
                        params.pop('designation', None)
                        time.sleep(0.3)
                        r2 = requests.get(url, params=params, timeout=30)
                        if r2.ok:
                            data2 = r2.json()
                            results2 = data2.get('results', [])
                            if results2:
                                committee_id = results2[0].get('committee_id')
                                logger.debug(f"  Found committee {committee_id} for candidate {fec_candidate_id} (no P designation)")
                                return committee_id
            except Exception as e:
                logger.debug(f"  Error getting committee for {fec_candidate_id}: {e}")

            return None

        # Load cached progress
        cached = self.load_cache('financial_pacs')
        cached_officials = set()
        if cached:
            cached_officials = set(cached.get('data', {}).get('processed_names', []))
            logger.info(f"  [CACHE] Found {len(cached_officials)} already-processed officials")

        try:
            matched_count = 0
            total_financial = 0
            processed_names = list(cached_officials)
            save_interval = 25  # Save every 25 officials (more frequent due to slower API)

            for i, official in enumerate(self.officials_data):
                name = official.get('name', '')

                # Skip if already processed
                if name in cached_officials:
                    if official.get('financial_sector_pac', 0) > 0:
                        matched_count += 1
                        total_financial += official.get('financial_sector_pac', 0)
                    continue

                # Use crosswalk FEC candidate ID for reliable committee lookup
                # The crosswalk provides direct bioguide_id -> fec_candidate_id mapping
                fec_candidate_id = official.get('fec_candidate_id')

                # Get principal campaign committee from FEC candidate ID
                committee_id = get_committee_from_candidate_id(fec_candidate_id)

                if not committee_id and fec_candidate_id:
                    logger.debug(f"  {name}: Has FEC ID {fec_candidate_id} but no committee found")

                if committee_id:
                    pac_result = get_financial_pac_total(committee_id)
                    fin_total = pac_result.get('financial_total', 0)
                    all_pac_total = pac_result.get('all_pac_total', 0)
                    financial_pct = pac_result.get('financial_pct', 0)
                    contributors = pac_result.get('financial_contributors', [])

                    official['financial_sector_pac'] = fin_total
                    official['fec_committee_id'] = committee_id
                    # Store calculated percentage from Schedule A data
                    official['financial_pac_pct'] = financial_pct

                    # If we don't have contributions from the initial FEC fetch,
                    # use the total from this Schedule A fetch as denominator
                    if not official.get('contributions') and all_pac_total > 0:
                        official['contributions'] = all_pac_total
                        official['pac_contributions'] = all_pac_total

                    if fin_total > 0:
                        matched_count += 1
                        total_financial += fin_total
                        # Store top contributors
                        top_contributors = sorted(contributors, key=lambda x: x['amount'], reverse=True)[:5]
                        official['top_financial_pacs'] = top_contributors
                        logger.info(f"  {name}: ${fin_total:,.0f} from {len(contributors)} financial PACs ({financial_pct}% of ${all_pac_total:,.0f} total PACs)")
                    else:
                        official['financial_sector_pac'] = 0
                        if all_pac_total > 0:
                            logger.info(f"  {name}: $0 financial PACs (of ${all_pac_total:,.0f} total PACs)")
                        else:
                            logger.info(f"  {name}: $0 from PACs")
                else:
                    # Couldn't find committee - set to None (unknown)
                    logger.debug(f"  {name}: Could not find FEC committee")

                # Mark as processed
                if name and name not in processed_names:
                    processed_names.append(name)

                # Save progress periodically
                if len(processed_names) % save_interval == 0:
                    self.save_cache('financial_pacs', {
                        'processed_names': processed_names,
                        'matched_count': matched_count,
                        'total_financial': total_financial
                    }, {'partial': True, 'count': len(processed_names)})

                # Progress update
                if (i + 1) % 10 == 0:
                    logger.info(f"  Progress: {i + 1}/{len(self.officials_data)} officials processed")

            # Final cache save
            self.save_cache('financial_pacs', {
                'processed_names': processed_names,
                'matched_count': matched_count,
                'total_financial': total_financial
            }, {'partial': False, 'count': len(processed_names)})

            self.source_status['financial_pacs'] = {
                'status': 'success',
                'matched_officials': matched_count,
                'total_financial_contributions': total_financial,
                'from_cache_count': len(cached_officials),
                'timestamp': datetime.now().isoformat()
            }
            logger.info(f"Financial PACs: {matched_count}/{len(self.officials_data)} officials have financial sector contributions (${total_financial:,.0f} total)")

        except Exception as e:
            logger.error(f"Financial PAC fetch failed: {e}")
            self.warnings.append(f"Financial PACs: {e}")
            self.source_status['financial_pacs'] = {'status': 'failed', 'error': str(e)}
            # Save progress before error
            if 'processed_names' in dir():
                self.save_cache('financial_pacs', {
                    'processed_names': processed_names,
                    'matched_count': matched_count if 'matched_count' in dir() else 0,
                    'total_financial': total_financial if 'total_financial' in dir() else 0
                }, {'partial': True, 'error': str(e)})

    
    def fetch_individual_financial_contributions(self):
        """Fetch individual contributions from financial sector executives."""
        # Load cached progress
        cached = self.load_cache('individual_contributions')
        cached_names = set()
        if cached:
            cached_names = set(cached.get('data', {}).get('processed_names', []))
            logger.info(f"  [CACHE] Found {len(cached_names)} already-processed officials")

        def save_progress(processed_names, matched_count, total_amount):
            self.save_cache('individual_contributions', {
                'processed_names': processed_names,
                'matched_count': matched_count,
                'total_amount': total_amount
            }, {'partial': True, 'count': len(processed_names)})

        try:
            from justdata.apps.electwatch.services.individual_contributions import enrich_officials_with_individual_contributions
            status = enrich_officials_with_individual_contributions(
                self.officials_data,
                cached_names=cached_names,
                save_callback=save_progress
            )
            status['from_cache_count'] = len(cached_names)
            self.source_status['individual_financial'] = status
        except Exception as e:
            logger.error(f"Individual financial contributions fetch failed: {e}")
            self.source_status['individual_financial'] = {'status': 'failed', 'error': str(e)}

    def fetch_congress_data(self):
        """Fetch bills and member data from Congress.gov."""
        logger.info("\n--- Fetching Congress.gov Data ---")
        try:
            from justdata.apps.electwatch.services.congress_api_client import CongressAPIClient
            client = CongressAPIClient()

            # Fetch recent financial-related bills
            bills = client.search_bills(query="financial services", limit=20)
            crypto_bills = client.search_bills(query="cryptocurrency", limit=20)

            all_bills = (bills or []) + (crypto_bills or [])

            self.source_status['congress'] = {
                'status': 'success',
                'bills_found': len(all_bills),
                'timestamp': datetime.now().isoformat()
            }
            logger.info(f"Fetched {len(all_bills)} bills from Congress.gov")

        except Exception as e:
            logger.error(f"Congress.gov fetch failed: {e}")
            self.warnings.append(f"Congress.gov: {e}")
            self.source_status['congress'] = {'status': 'failed', 'error': str(e)}

    def fetch_finnhub_data(self):
        """Fetch news and stock data from Finnhub."""
        logger.info("\n--- Fetching Finnhub Data ---")
        try:
            from justdata.apps.electwatch.services.finnhub_client import FinnhubClient
            client = FinnhubClient()

            if not client.test_connection():
                raise Exception("Finnhub API connection failed")

            # Key financial sector tickers
            tickers = ['WFC', 'JPM', 'BAC', 'C', 'GS', 'MS', 'COIN', 'HOOD', 'SQ', 'PYPL']

            firms_with_data = []
            total_news = 0

            for ticker in tickers:
                try:
                    quote = client.get_quote(ticker)
                    news = client.get_company_news(ticker, days=30, limit=10)
                    profile = client.get_company_profile(ticker)
                    insider = client.get_insider_transactions(ticker, limit=20)

                    firm = {
                        'ticker': ticker,
                        'name': profile.get('name', ticker) if profile else ticker,
                        'industry': profile.get('industry', '') if profile else '',
                        'quote': quote,
                        'news': news or [],
                        'insider_transactions': insider or [],
                        'market_cap': profile.get('market_cap', 0) if profile else 0
                    }
                    firms_with_data.append(firm)
                    total_news += len(news or [])

                except Exception as e:
                    logger.warning(f"Error fetching {ticker}: {e}")

            self.firms_data = firms_with_data

            self.source_status['finnhub'] = {
                'status': 'success',
                'firms': len(firms_with_data),
                'news_articles': total_news,
                'timestamp': datetime.now().isoformat()
            }
            logger.info(f"Fetched data for {len(firms_with_data)} firms, {total_news} news articles")

        except Exception as e:
            logger.error(f"Finnhub fetch failed: {e}")
            self.errors.append(f"Finnhub: {e}")
            self.source_status['finnhub'] = {'status': 'failed', 'error': str(e)}

    def fetch_sec_data(self):
        """Fetch SEC EDGAR filings."""
        logger.info("\n--- Fetching SEC EDGAR Data ---")
        try:
            from justdata.apps.electwatch.services.sec_client import SECClient
            client = SECClient()

            # Add SEC filings to existing firms data
            filings_count = 0
            for firm in self.firms_data:
                try:
                    ticker = firm.get('ticker')
                    if ticker:
                        filings = client.get_recent_10k_10q(ticker)
                        firm['sec_filings'] = filings or []
                        filings_count += len(filings or [])
                except Exception as e:
                    logger.warning(f"SEC error for {firm.get('ticker')}: {e}")
                    firm['sec_filings'] = []

            self.source_status['sec'] = {
                'status': 'success',
                'filings_found': filings_count,
                'timestamp': datetime.now().isoformat()
            }
            logger.info(f"Fetched {filings_count} SEC filings")

        except Exception as e:
            logger.error(f"SEC fetch failed: {e}")
            self.warnings.append(f"SEC: {e}")
            self.source_status['sec'] = {'status': 'failed', 'error': str(e)}

    def fetch_news_data(self):
        """Fetch news from NewsAPI with quality filtering."""
        logger.info("\n--- Fetching NewsAPI Data ---")
        try:
            from justdata.apps.electwatch.services.news_client import NewsClient
            client = NewsClient()

            if not client.test_connection():
                raise Exception("NewsAPI connection failed")

            # Get political finance news
            political_news = client.get_political_finance_news(days=7, limit=30)

            # Get industry-specific news
            industries = ['banking', 'cryptocurrency', 'financial services', 'fintech']
            industry_news = []
            for industry in industries:
                try:
                    news = client.get_industry_news(industry, days=7, limit=10)
                    industry_news.extend(news or [])
                except:
                    pass

            self.news_data = (political_news or []) + industry_news

            self.source_status['newsapi'] = {
                'status': 'success',
                'articles': len(self.news_data),
                'timestamp': datetime.now().isoformat()
            }
            logger.info(f"Fetched {len(self.news_data)} news articles")

        except Exception as e:
            logger.error(f"NewsAPI fetch failed: {e}")
            self.warnings.append(f"NewsAPI: {e}")
            self.source_status['newsapi'] = {'status': 'failed', 'error': str(e)}

    # =========================================================================
    # PHASE 2: PROCESS DATA
    # =========================================================================

    def process_data(self):
        """Process and aggregate fetched data."""
        logger.info("\n--- Processing Officials Data ---")
        self.process_officials()

        logger.info("\n--- Processing Firms Data ---")
        self.process_firms()

        logger.info("\n--- Processing Industries Data ---")
        self.process_industries()

        logger.info("\n--- Processing Committees Data ---")
        self.process_committees()

    def process_officials(self):
        """Process and enrich officials data."""
        from justdata.apps.electwatch.services.firm_mapper import FirmMapper, FINANCIAL_SECTORS

        mapper = FirmMapper()

        # Use module-level NAME_ALIASES for deduplication (defined at top of file)

        # Bioguide IDs for photos - source: https://bioguide.congress.gov
        # Photos: https://clerk.house.gov/images/members/{bioguide_id}.jpg
        BIOGUIDE_IDS = {
            # Top traders (119th Congress freshmen - verified from Congress.gov)
            'Jefferson Shreve': 'S001229',  # https://www.congress.gov/member/jefferson-shreve/S001229
            'Dave McCormick': 'M001243',    # https://www.congress.gov/member/david-mccormick/M001243
            'David McCormick': 'M001243',
            'Tim Moore': 'M001236',          # https://www.congress.gov/member/tim-moore/M001236
            # Note: Other 119th freshmen bioguide IDs need to be verified
            # Existing members (verified)
            'Ro Khanna': 'K000389',
            'Nancy Pelosi': 'P000197',
            'Josh Gottheimer': 'G000583',
            'Michael McCaul': 'M001157',
            'Marjorie Taylor Greene': 'G000596',
            'Tommy Tuberville': 'T000278',
            'Kevin Hern': 'H001082',
            'French Hill': 'H001072',
            'James French Hill': 'H001072',
            'Ted Cruz': 'C001098',
            'Angus King': 'K000383',
            'John Fetterman': 'F000479',
            'Lisa McClain': 'M001136',
            'Byron Donalds': 'D000632',
            'Dan Newhouse': 'N000189',
            'Rick Larsen': 'L000560',
            'Thomas H. Kean': 'K000394',
            'Thomas Kean': 'K000394',
            'Bruce Westerman': 'W000821',
            'John Kennedy': 'K000393',
            'Markwayne Mullin': 'M001190',
            'Debbie Dingell': 'D000624',
            'Ritchie Torres': 'T000481',
            'Daniel Meuser': 'M001204',
            'Neal P. Dunn': 'D000628',
            'Neal Dunn': 'D000628',
            'Carol Devine Miller': 'M001205',
            'Carol Miller': 'M001205',
            'Val Hoyle': 'H001092',
            'Valerie Hoyle': 'H001092',
            'Jake Auchincloss': 'A000376',
            'Greg Landsman': 'L000601',
            'Dwight Evans': 'E000296',
            'James Comer': 'C001108',
            'Richard W. Allen': 'A000372',
            'William R. Keating': 'K000375',
            'Shelley Moore Capito': 'C001047',
            'John Boozman': 'B001236',
            'Tina Smith': 'S001203',
            'Sheldon Whitehouse': 'W000802',
            'Mitch McConnell': 'M000355',
            'Adam Smith': 'S000510',
            'Rich McCormick': 'M001211',
            'Jared Moskowitz': 'M001217',
            'Cleo Fields': 'F000477',
            'Scott Franklin': 'F000472',
            'Scott Mr Franklin': 'F000472',
            'Gilbert Cisneros': 'C001123',
            'Jonathan Jackson': 'J000309',
            # 119th Congress freshmen - added for photo support
            'George Whitesides': 'W000830',  # https://www.congress.gov/member/george-whitesides/W000830
            'Rob Bresnahan': 'B001327',      # https://www.congress.gov/member/robert-bresnahan/B001327
            'Robert Bresnahan': 'B001327',
            'Julie Johnson': 'J000310',       # https://www.congress.gov/member/julie-johnson/J000310
            'Tony Wied': 'W000829',           # https://www.congress.gov/member/tony-wied/W000829
            'Richard McCormick': 'M001218',   # https://www.congress.gov/member/richard-mccormick/M001218
            'April Delaney': 'M001232',       # https://www.congress.gov/member/april-mcclain-delaney/M001232
            'April McClain Delaney': 'M001232',
            'Sheri Biggs': 'B001325',         # https://www.congress.gov/member/sheri-biggs/B001325
            'David Taylor': 'T000490',        # https://www.congress.gov/member/david-taylor/T000490
            'Dave Taylor': 'T000490',
            # New Senators (2025)
            'Ashley Moody': 'M001244',        # https://www.congress.gov/member/ashley-moody/M001244
            # Additional members for photo coverage (verified from Congress.gov)
            'Susan Collins': 'C001035',       # https://www.congress.gov/member/susan-collins/C001035
            'Susan M. Collins': 'C001035',
            'Joshua Gottheimer': 'G000583',   # Alias for Josh Gottheimer
            'Daniel Newhouse': 'N000189',     # Alias for Dan Newhouse
            'Deborah Dingell': 'D000624',     # Alias for Debbie Dingell
            'Jacob Auchincloss': 'A000148',   # Alias for Jake Auchincloss - https://www.congress.gov/member/jake-auchincloss/A000148
            'Laurel Lee': 'L000597',          # https://www.congress.gov/member/laurel-lee/L000597
            'Rohit Khanna': 'K000389',        # Alias for Ro Khanna
            'Gregory Landsman': 'L000601',    # Alias for Greg Landsman
            'Peter Sessions': 'S000250',      # Alias for Pete Sessions - https://www.congress.gov/member/pete-sessions/S000250
            'Pete Sessions': 'S000250',
            'Morgan McGarvey': 'M001220',     # https://www.congress.gov/member/morgan-mcgarvey/M001220
            'Anthony Wied': 'W000829',        # Alias for Tony Wied
            'Roger Williams': 'W000816',      # https://www.congress.gov/member/roger-williams/W000816
            'Lance Gooden': 'G000589',        # https://www.congress.gov/member/lance-gooden/G000589
            'Stephen Cohen': 'C001068',       # Alias for Steve Cohen - https://www.congress.gov/member/steve-cohen/C001068
            'Steve Cohen': 'C001068',
            'Shrikant Thanedar': 'T000488',   # Alias for Shri Thanedar - https://www.congress.gov/member/shri-thanedar/T000488
            'Shri Thanedar': 'T000488',
            'Christine Smith': 'S001203',     # Legal name for Tina Smith
            'Earl Blumenauer': 'B000574',     # https://www.congress.gov/member/earl-blumenauer/B000574 (former)
            'Kathy Manning': 'M001135',       # https://www.congress.gov/member/kathy-manning/M001135 (former)
            'Addison McConnell': 'M000355',   # Legal name for Mitch McConnell
            'Julia Letlow': 'L000595',        # https://www.congress.gov/member/julia-letlow/L000595
            'John Delaney': 'D000620',        # https://www.congress.gov/member/john-delaney/D000620 (former)
            'Paul Mitchell': 'M001201',       # https://www.congress.gov/member/paul-mitchell/M001201 (former)
            'Emily Randall': 'R000621',       # https://www.congress.gov/member/emily-randall/R000621
            'Thomas R. Carper': 'C000174',    # https://www.congress.gov/member/thomas-carper/C000174 (former)
            'Tom Carper': 'C000174',
            'Gary Peters': 'P000595',         # https://www.congress.gov/member/gary-peters/P000595
            # Potential data quality issues - these may be incorrectly named in the source data
            'David Smith': 'S000510',         # Likely Adam Smith (legal name: David Adam Smith) - WA-9
        }

        # Wikipedia photo URLs for Senate members (no House Clerk photos available)
        # License: These images are from Wikimedia Commons under Creative Commons licenses.
        # Attribution: Photos sourced from Wikipedia/Wikimedia Commons. See individual file pages
        # at commons.wikimedia.org for specific license terms and attribution requirements.
        # Citation format: "Title" by Creator (Year). Source: Wikimedia Commons. Public Domain.
        WIKIPEDIA_PHOTOS = {
            'Dave McCormick': 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c6/McCormick_Portrait_%28HR%29.jpg/330px-McCormick_Portrait_%28HR%29.jpg',
            'David McCormick': 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c6/McCormick_Portrait_%28HR%29.jpg/330px-McCormick_Portrait_%28HR%29.jpg',
            'Angus King': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a7/Angus_King%2C_official_portrait%2C_113th_Congress.jpg/330px-Angus_King%2C_official_portrait%2C_113th_Congress.jpg',
            'Angus S. King': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a7/Angus_King%2C_official_portrait%2C_113th_Congress.jpg/330px-Angus_King%2C_official_portrait%2C_113th_Congress.jpg',  # Alias
            'Ted Cruz': 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/Ted_Cruz_official_116th_portrait_%283x4_cropped_b%29.jpg/330px-Ted_Cruz_official_116th_portrait_%283x4_cropped_b%29.jpg',
            'Rafael Cruz': 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/Ted_Cruz_official_116th_portrait_%283x4_cropped_b%29.jpg/330px-Ted_Cruz_official_116th_portrait_%283x4_cropped_b%29.jpg',  # Alias (formal name)
            'Markwayne Mullin': 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c7/Markwayne_Mullin_official_Senate_photo.jpg/330px-Markwayne_Mullin_official_Senate_photo.jpg',
            'Shelley Moore Capito': 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/75/Shelley_Moore_Capito_official_Senate_photo.jpg/330px-Shelley_Moore_Capito_official_Senate_photo.jpg',
            'John Boozman': 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/30/Senator_John_Boozman_Official_Portrait_%28115th_Congress%29.jpg/330px-Senator_John_Boozman_Official_Portrait_%28115th_Congress%29.jpg',
            'Tina Smith': 'https://upload.wikimedia.org/wikipedia/commons/thumb/f/ff/Tina_Smith%2C_official_portrait%2C_116th_congress.jpg/330px-Tina_Smith%2C_official_portrait%2C_116th_congress.jpg',
            'John Kennedy': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/af/John_Kennedy%2C_official_portrait%2C_115th_Congress_%28cropped%29.jpg/330px-John_Kennedy%2C_official_portrait%2C_115th_Congress_%28cropped%29.jpg',
            'Tommy Tuberville': 'https://upload.wikimedia.org/wikipedia/commons/thumb/d/df/Tommy_tuberville.jpg/330px-Tommy_tuberville.jpg',
            'Thomas Tuberville': 'https://upload.wikimedia.org/wikipedia/commons/thumb/d/df/Tommy_tuberville.jpg/330px-Tommy_tuberville.jpg',  # Alias (formal name)
            'Sheldon Whitehouse': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a7/Sheldon_Whitehouse%2C_official_portrait%2C_116th_congress.jpg/330px-Sheldon_Whitehouse%2C_official_portrait%2C_116th_congress.jpg',
            'Mitch McConnell': 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/0b/Mitch_McConnell_2016_official_photo_%281%29.jpg/330px-Mitch_McConnell_2016_official_photo_%281%29.jpg',
            'John Fetterman': 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/John_Fetterman_official_portrait.jpg/330px-John_Fetterman_official_portrait.jpg',
            'Ashley Moody': 'https://upload.wikimedia.org/wikipedia/commons/thumb/b/b7/Official_Portrait_of_Senator_Ashley_Moody_%28cropped%29.jpg/330px-Official_Portrait_of_Senator_Ashley_Moody_%28cropped%29.jpg',
            # Additional senators for photo coverage
            'Susan Collins': 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Senator_Susan_Collins_official_photo%2C_117th_Congress_%28cropped%29.jpeg/330px-Senator_Susan_Collins_official_photo%2C_117th_Congress_%28cropped%29.jpeg',
            'Susan M. Collins': 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Senator_Susan_Collins_official_photo%2C_117th_Congress_%28cropped%29.jpeg/330px-Senator_Susan_Collins_official_photo%2C_117th_Congress_%28cropped%29.jpeg',  # Alias
            'Christine Smith': 'https://upload.wikimedia.org/wikipedia/commons/thumb/f/ff/Tina_Smith%2C_official_portrait%2C_116th_congress.jpg/330px-Tina_Smith%2C_official_portrait%2C_116th_congress.jpg',  # Legal name for Tina Smith
            'Addison McConnell': 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/0b/Mitch_McConnell_2016_official_photo_%281%29.jpg/330px-Mitch_McConnell_2016_official_photo_%281%29.jpg',  # Legal name for Mitch McConnell
            'Gary Peters': 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Gary_Peters%2C_official_portrait%2C_115th_congress.jpg/330px-Gary_Peters%2C_official_portrait%2C_115th_congress.jpg',
            'Thomas R. Carper': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a9/Senator_Thomas_R._Carper_official_portrait%2C_117th_Congress.jpg/330px-Senator_Thomas_R._Carper_official_portrait%2C_117th_Congress.jpg',
            'Tom Carper': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a9/Senator_Thomas_R._Carper_official_portrait%2C_117th_Congress.jpg/330px-Senator_Thomas_R._Carper_official_portrait%2C_117th_Congress.jpg',
        }

        # Known member data: name -> (first_elected_year, chamber, party)
        # Data from Congress.gov/Ballotpedia for active traders
        MEMBER_DATA = {
            'Ro Khanna': (2017, 'house', 'D'),
            'Nancy Pelosi': (1987, 'house', 'D'),
            'Josh Gottheimer': (2017, 'house', 'D'),
            'Michael McCaul': (2005, 'house', 'R'),
            'Marjorie Taylor Greene': (2021, 'house', 'R'),
            'Daniel Goldman': (2023, 'house', 'D'),
            'Tommy Tuberville': (2021, 'senate', 'R'),
            'Dave McCormick': (2025, 'senate', 'R'),
            'John Curtis': (2017, 'house', 'R'),
            'Gilbert Cisneros': (2019, 'house', 'D'),
            'French Hill': (2015, 'house', 'R'),
            'James French Hill': (2015, 'house', 'R'),
            'John Rose': (2019, 'house', 'R'),
            'Alan Lowenthal': (2013, 'house', 'D'),
            'Lisa McClain': (2021, 'house', 'R'),
            'Diana Harshbarger': (2021, 'house', 'R'),
            'Michael Burgess': (2003, 'house', 'R'),
            'Blake Moore': (2021, 'house', 'R'),
            'Mark Green': (2019, 'house', 'R'),
            'Pete Sessions': (1997, 'house', 'R'),
            'Dan Crenshaw': (2019, 'house', 'R'),
            'Brian Higgins': (2005, 'house', 'D'),
            'Kevin Hern': (2018, 'house', 'R'),
            'Bill Huizenga': (2011, 'house', 'R'),
            'Earl Blumenauer': (1996, 'house', 'D'),
            'John Boozman': (2011, 'senate', 'R'),
            'Shelley Moore Capito': (2015, 'senate', 'R'),
            'Gary Peters': (2015, 'senate', 'D'),
            'Debbie Stabenow': (2001, 'senate', 'D'),
            'Cynthia Lummis': (2021, 'senate', 'R'),
            'Steve Daines': (2015, 'senate', 'R'),
            'Tim Scott': (2013, 'senate', 'R'),
            'Roger Wicker': (2007, 'senate', 'R'),
            'Jefferson Shreve': (2025, 'house', 'R'),
            'Dan Newhouse': (2015, 'house', 'R'),
            'Rick Larsen': (2001, 'house', 'D'),
            'Thomas H. Kean': (2023, 'house', 'R'),
            'Thomas Kean': (2023, 'house', 'R'),
            'Bruce Westerman': (2015, 'house', 'R'),
            'Ted Cruz': (2013, 'senate', 'R'),
            'Angus King': (2013, 'senate', 'I'),
            'John Kennedy': (2017, 'senate', 'R'),
            'Markwayne Mullin': (2023, 'senate', 'R'),
            'John Fetterman': (2023, 'senate', 'D'),
            'Byron Donalds': (2021, 'house', 'R'),
            'Tim Moore': (2025, 'house', 'R'),
            'Daniel Meuser': (2019, 'house', 'R'),
            'Debbie Dingell': (2015, 'house', 'D'),
            'Neal P. Dunn': (2017, 'house', 'R'),
            'Neal Dunn': (2017, 'house', 'R'),
            'Carol Devine Miller': (2019, 'house', 'R'),
            'Carol Miller': (2019, 'house', 'R'),
            'Ritchie Torres': (2021, 'house', 'D'),
            'Val Hoyle': (2023, 'house', 'D'),
            'Valerie Hoyle': (2023, 'house', 'D'),
            'Jonathan Jackson': (2023, 'house', 'D'),
            'Julie Johnson': (2025, 'house', 'D'),
            'Jared Moskowitz': (2023, 'house', 'D'),
            'Rich McCormick': (2023, 'house', 'R'),
            'Jake Auchincloss': (2021, 'house', 'D'),
            'Greg Landsman': (2023, 'house', 'D'),
            'Dwight Evans': (2016, 'house', 'D'),
            'James Comer': (2016, 'house', 'R'),
            'Cleo Fields': (2023, 'house', 'D'),
            'Sheri Biggs': (2025, 'house', 'R'),
            'Richard W. Allen': (2017, 'house', 'R'),
            'David Taylor': (2025, 'house', 'R'),
            'Scott Franklin': (2021, 'house', 'R'),
            'Tony Wied': (2025, 'house', 'R'),
            'Rob Bresnahan': (2025, 'house', 'R'),
            'George Whitesides': (2025, 'house', 'D'),
            'William R. Keating': (2011, 'house', 'D'),
            'April Delaney': (2025, 'house', 'D'),
            'Sheldon Whitehouse': (2007, 'senate', 'D'),
            'Tina Smith': (2018, 'senate', 'D'),
            'Adam Smith': (1997, 'house', 'D'),
            'Mitch McConnell': (1985, 'senate', 'R'),
            'John Kennedy': (2017, 'senate'),
            'Mark Warner': (2009, 'senate'),
        }

        # Committee assignments for known officials
        # This data should ideally come from Congress.gov API
        COMMITTEE_ASSIGNMENTS = {
            'James French Hill': ['Financial Services (Chair)', 'Intelligence'],
            'French Hill': ['Financial Services (Chair)', 'Intelligence'],
            'Nancy Pelosi': ['Intelligence', 'Democratic Steering and Policy'],
            'Maxine Waters': ['Financial Services (Ranking)', 'Capital Markets'],
            'Josh Gottheimer': ['Financial Services', 'Homeland Security'],
            'Ro Khanna': ['Armed Services', 'Oversight and Reform'],
            'Michael McCaul': ['Foreign Affairs (Chair)', 'Homeland Security'],
            'Marjorie Taylor Greene': ['Homeland Security', 'Oversight'],
            'Tommy Tuberville': ['Agriculture', 'Armed Services', 'Veterans Affairs'],
            'Dave McCormick': ['Banking (Vice Chair)', 'Finance', 'Commerce'],
            'Tim Scott': ['Banking (Chair)', 'Finance', 'Health'],
            'Shelley Moore Capito': ['Appropriations', 'Commerce', 'Environment'],
            'Ted Cruz': ['Commerce (Chair)', 'Foreign Relations', 'Judiciary'],
            'Mitch McConnell': ['Appropriations', 'Agriculture', 'Rules'],
            'John Kennedy': ['Banking', 'Judiciary', 'Appropriations'],
            'Angus King': ['Armed Services', 'Intelligence', 'Energy'],
            'Markwayne Mullin': ['Armed Services', 'Environment', 'Health'],
            'John Fetterman': ['Agriculture', 'Banking', 'Environment'],
            'Sheldon Whitehouse': ['Budget', 'Environment', 'Judiciary'],
            'Kevin Hern': ['Budget', 'Ways and Means'],
            'Byron Donalds': ['Financial Services', 'Oversight', 'Small Business'],
            'Ritchie Torres': ['Financial Services', 'Homeland Security'],
            'Jake Auchincloss': ['Financial Services', 'Transportation'],
            'Greg Landsman': ['Financial Services', 'Small Business'],
            'Rich McCormick': ['Foreign Affairs', 'Armed Services'],
            'Lisa McClain': ['Armed Services', 'Oversight'],
            'Daniel Meuser': ['Financial Services', 'Small Business'],
            'Debbie Dingell': ['Energy and Commerce', 'Natural Resources'],
            'Dan Newhouse': ['Appropriations', 'Select Intelligence'],
            'Rick Larsen': ['Armed Services', 'Transportation'],
            'William R. Keating': ['Armed Services', 'Foreign Affairs'],
            'James Comer': ['Oversight (Chair)', 'Agriculture'],
            'Jared Moskowitz': ['Foreign Affairs', 'Oversight'],
            'Jefferson Shreve': ['Small Business', 'Transportation'],
            'Bruce Westerman': ['Natural Resources (Chair)', 'Transportation'],
            'Neal P. Dunn': ['Agriculture', 'Veterans Affairs'],
            'Neal Dunn': ['Agriculture', 'Veterans Affairs'],
            'Carol Miller': ['Ways and Means', 'Energy Commerce'],
            'Carol Devine Miller': ['Ways and Means', 'Energy Commerce'],
        }

        current_year = datetime.now().year

        # Normalize names and merge duplicates
        officials_by_name = {}
        for official in self.officials_data:
            name = official.get('name', '')
            # Apply name aliases to normalize
            canonical_name = NAME_ALIASES.get(name, name)
            official['name'] = canonical_name

            if canonical_name in officials_by_name:
                # Merge with existing official
                existing = officials_by_name[canonical_name]
                existing['trades'] = existing.get('trades', []) + official.get('trades', [])
                existing['contributions'] = max(
                    existing.get('contributions', 0) or 0,
                    official.get('contributions', 0) or 0
                )
                existing['financial_sector_pac'] = max(
                    existing.get('financial_sector_pac', 0) or 0,
                    official.get('financial_sector_pac', 0) or 0
                )
                # Keep other fields from existing
            else:
                officials_by_name[canonical_name] = official

        self.officials_data = list(officials_by_name.values())
        logger.info(f"After deduplication: {len(self.officials_data)} unique officials")

        for official in self.officials_data:
            # Get committee assignments
            name = official.get('name', '')
            if name in COMMITTEE_ASSIGNMENTS:
                official['committees'] = COMMITTEE_ASSIGNMENTS[name]
            else:
                official.setdefault('committees', [])
            official.setdefault('contributions', 0)
            official.setdefault('contributions_list', [])

            # Create trades_list from trades for template compatibility
            # Transform trade data to match expected format for renderActivity
            trades = official.get('trades', [])
            official['trades_list'] = [
                {
                    'ticker': t.get('ticker', ''),
                    'company': t.get('company', ''),
                    'type': t.get('type', 'trade'),  # purchase, sale, exchange
                    'transaction_type': t.get('type', 'trade'),  # duplicate for compatibility
                    'amount': t.get('amount', {}),
                    'date': t.get('transaction_date', ''),
                }
                for t in trades
            ]
            official['trades_count'] = len(trades)

            # Add years in Congress data, party info, and photo URL
            name = official.get('name', '')
            if name in MEMBER_DATA:
                member_info = MEMBER_DATA[name]
                first_elected = member_info[0]
                chamber = member_info[1] if len(member_info) > 1 else None
                party = member_info[2] if len(member_info) > 2 else None
                official['first_elected'] = first_elected
                official['years_in_congress'] = current_year - first_elected
                if party:
                    official['party'] = party

            # Add bioguide ID and photo URL
            bioguide_id = BIOGUIDE_IDS.get(name)
            if bioguide_id:
                official['bioguide_id'] = bioguide_id

            # Get photo URL - Wikipedia for Senate, House Clerk for House
            try:
                chamber = official.get('chamber', 'house')

                # First check if we have a Wikipedia photo for this person (mainly Senate)
                if name in WIKIPEDIA_PHOTOS:
                    official['photo_url'] = WIKIPEDIA_PHOTOS[name]
                    official['photo_source'] = 'wikipedia'  # Track for attribution
                else:
                    # Try House Clerk for House members
                    photo_url = fetch_bioguide_photo(name, bioguide_id, chamber)
                    if photo_url:
                        official['photo_url'] = photo_url
                        official['photo_source'] = 'house_clerk'
            except Exception as e:
                logger.debug(f"Could not fetch photo for {name}: {e}")

            if name not in MEMBER_DATA:
                # Estimate from trades if available (rough approximation)
                trades = official.get('trades', [])
                if trades:
                    earliest_trade = min(t.get('transaction_date', '9999') for t in trades if t.get('transaction_date'))
                    if earliest_trade != '9999':
                        # They must have been in office before the trade
                        first_year = int(earliest_trade[:4]) if earliest_trade else current_year
                        official['first_elected'] = first_year
                        official['years_in_congress'] = current_year - first_year
                    else:
                        official['years_in_congress'] = None
                        official['first_elected'] = None
                else:
                    official['years_in_congress'] = None
                    official['first_elected'] = None
            official.setdefault('legislation', [])
            official.setdefault('recent_news', [])

            # Calculate top industries from traded stocks
            industry_counts = {}
            industry_amounts = {}

            for trade in official.get('trades', []):
                ticker = trade.get('ticker', '').upper()
                if not ticker:
                    continue

                # Look up industries for this ticker
                industries = mapper.get_industry_from_ticker(ticker)
                if not industries:
                    # Try to guess industry from ticker/company name
                    company = trade.get('company', '') or ''
                    company_lower = company.lower()
                    if any(kw in company_lower for kw in ['bank', 'financial', 'credit']):
                        industries = ['banking']
                    elif any(kw in company_lower for kw in ['coin', 'crypto', 'bitcoin']):
                        industries = ['crypto']
                    elif any(kw in company_lower for kw in ['insurance', 'insur']):
                        industries = ['insurance']
                    elif any(kw in company_lower for kw in ['payment', 'pay', 'visa', 'master']):
                        industries = ['fintech']

                # Track by industry
                for industry in industries:
                    industry_counts[industry] = industry_counts.get(industry, 0) + 1
                    amt = trade.get('amount', {})
                    if isinstance(amt, dict):
                        # Use midpoint of range for more accurate estimates
                        min_amt = amt.get('min', 0) or 0
                        max_amt = amt.get('max', 0) or 0
                        trade_amt = (min_amt + max_amt) / 2 if max_amt > 0 else min_amt
                    else:
                        trade_amt = float(amt) if amt else 0
                    industry_amounts[industry] = industry_amounts.get(industry, 0) + trade_amt

            # Sort industries by amount and get top 3
            sorted_industries = sorted(
                industry_amounts.items(),
                key=lambda x: x[1],
                reverse=True
            )

            top_industries = []
            for ind_code, amount in sorted_industries[:3]:
                sector_info = FINANCIAL_SECTORS.get(ind_code, {})
                top_industries.append({
                    'code': ind_code,
                    'name': sector_info.get('name', ind_code.title().replace('_', ' ')),
                    'trade_count': industry_counts.get(ind_code, 0),
                    'amount': amount
                })

            official['top_industries'] = top_industries
            official['industry_breakdown'] = {
                code: {
                    'count': industry_counts.get(code, 0),
                    'amount': industry_amounts.get(code, 0)
                }
                for code in industry_counts
            }

            # Build involvement_by_industry in format expected by profile page
            # Format: {'banking': {'contributions': X, 'stock_trades': Y, 'total': Z}, ...}
            involvement_by_industry = {}
            for code, amount in industry_amounts.items():
                # Get PAC contributions for this industry (if available from financial_sector_contributions)
                # For now, use 0 for contributions since we track them separately
                involvement_by_industry[code] = {
                    'contributions': 0,  # Will be enriched later with PAC industry data
                    'stock_trades': amount,
                    'total': amount,
                    'trade_count': industry_counts.get(code, 0)
                }
            official['involvement_by_industry'] = involvement_by_industry

            # Build firms list from trades - aggregate by ticker
            firm_data = {}
            for trade in official.get('trades', []):
                ticker = trade.get('ticker', '').upper()
                if not ticker:
                    continue

                company = trade.get('company', '') or ticker
                amt = trade.get('amount', {})
                if isinstance(amt, dict):
                    trade_amt = amt.get('max', 0) or amt.get('min', 0) or 0
                else:
                    trade_amt = float(amt) if amt else 0

                trade_type = trade.get('type', '').lower()
                is_buy = trade_type in ('purchase', 'buy')
                is_sell = trade_type in ('sale', 'sell')

                if ticker not in firm_data:
                    firm_data[ticker] = {
                        'name': company,
                        'ticker': ticker,
                        'total': 0,
                        'buys': 0,
                        'sells': 0,
                        'trade_count': 0,
                        'type': 'trades'  # Will be 'mixed' if they also have PAC
                    }

                firm_data[ticker]['total'] += trade_amt
                firm_data[ticker]['trade_count'] += 1
                if is_buy:
                    firm_data[ticker]['buys'] += trade_amt
                elif is_sell:
                    firm_data[ticker]['sells'] += trade_amt

            # Sort firms by total amount and take top 10
            sorted_firms = sorted(firm_data.values(), key=lambda x: x['total'], reverse=True)
            official['firms'] = sorted_firms[:10]

            # Get net worth data for display (informational only, not used in scoring)
            from justdata.apps.electwatch.services.net_worth_client import get_net_worth, get_wealth_tier

            net_worth_data = get_net_worth(official.get('name', ''))
            official['net_worth'] = net_worth_data
            tier_code, tier_display = get_wealth_tier(net_worth_data['midpoint'])
            official['wealth_tier'] = tier_code
            official['wealth_tier_display'] = tier_display

            # Scoring system: trade activity + contributions weighted by finance %
            # Trade score: bucket_low_end / 1000 per trade (unchanged)
            trade_score = official.get('trade_score', 0)

            # Contribution score: total contributions weighted by finance sector %
            # Higher finance % = higher score (surfaces people heavily reliant on finance money)
            total_pac = official.get('contributions', 0) or 0
            total_individual = official.get('individual_contributions_total', 0) or 0
            contribution_total = total_pac + total_individual

            financial_pac = official.get('financial_sector_pac', 0) or 0
            financial_individual = official.get('individual_financial_total', 0) or 0
            financial_total = financial_pac + financial_individual

            # Finance percentage (0-1 scale for scoring)
            finance_pct = (financial_total / contribution_total) if contribution_total > 0 else 0

            # New formula: (total_contributions / 1000) * finance_pct
            # So $500K total with 40% finance = 500 * 0.40 = 200 pts
            # And $500K total with 5% finance = 500 * 0.05 = 25 pts
            contrib_score = (contribution_total / 1000) * finance_pct

            # Combined score: trade activity + weighted contributions
            official['involvement_score'] = round(trade_score + contrib_score)

            # Store component scores for transparency
            official['score_breakdown'] = {
                'trade_score': round(trade_score, 1),
                'contributions_score': round(contrib_score, 1),
                'total_contributions': contribution_total,
                'finance_contributions': financial_total,
                'finance_pct': round(finance_pct * 100, 1),
                'total_trades': official.get('total_trades', 0)
            }

            # Calculate component percentages for transparency
            # (total_pac, total_individual, financial_pac, financial_individual already computed above)
            combined_financial_pct = round(finance_pct * 100, 1)
            pac_pct = round((financial_pac / total_pac) * 100, 1) if total_pac > 0 else 0
            individual_pct = round((financial_individual / total_individual) * 100, 1) if total_individual > 0 else 0

            # Store all metrics
            official['financial_sector_pct'] = combined_financial_pct
            official['contributions_display'] = {
                # Combined totals
                'total': contribution_total,
                'financial': financial_total,
                'financial_pct': combined_financial_pct,
                # PAC breakdown
                'pac_total': total_pac,
                'pac_financial': financial_pac,
                'pac_pct': pac_pct,
                # Individual breakdown
                'individual_total': total_individual,
                'individual_financial': financial_individual,
                'individual_pct': individual_pct
            }

        # Keep ALL officials - no filtering based on financial activity
        # Previously filtered to only those with industries or contributions > $10k
        # Now we keep everyone so users can see all Congress members

        # Build top_donors by merging PAC and individual contributions
        self._build_top_donors()

        # Convert raw scores to Z-scores normalized to 1-100
        self._normalize_scores_to_zscore()

        # Re-sort by involvement score (officials with no activity will have score of 0)
        self.officials_data.sort(key=lambda x: x.get('involvement_score', 0), reverse=True)

        # Count officials with and without financial activity for logging
        with_activity = len([o for o in self.officials_data if o.get('top_industries') or o.get('contributions', 0) > 0])
        without_activity = len(self.officials_data) - with_activity
        logger.info(f"Processed {len(self.officials_data)} total officials ({with_activity} with financial activity, {without_activity} without)")

    def _build_top_donors(self):
        """
        Build top_donors list for each official by merging PAC and individual contributions.

        Combines:
        - top_financial_pacs: PAC contributions (e.g., "JPMORGAN CHASE & CO PAC")
        - individual_financial_by_employer: Individual contributions by employer

        Normalizes company names and detects stock trading overlap.
        """
        # Company name normalization mapping (PAC name -> canonical name)
        PAC_TO_COMPANY = {
            'JPMORGAN CHASE': 'JPMorgan Chase',
            'JPMORGAN': 'JPMorgan Chase',
            'JP MORGAN': 'JPMorgan Chase',
            'BANK OF AMERICA': 'Bank of America',
            'BOFA': 'Bank of America',
            'GOLDMAN SACHS': 'Goldman Sachs',
            'MORGAN STANLEY': 'Morgan Stanley',
            'WELLS FARGO': 'Wells Fargo',
            'CITIGROUP': 'Citigroup',
            'CITI': 'Citigroup',
            'AMERICAN EXPRESS': 'American Express',
            'AMEX': 'American Express',
            'CAPITAL ONE': 'Capital One',
            'BLACKROCK': 'BlackRock',
            'CHARLES SCHWAB': 'Charles Schwab',
            'SCHWAB': 'Charles Schwab',
            'FIDELITY': 'Fidelity',
            'VANGUARD': 'Vanguard',
            'STATE STREET': 'State Street',
            'BANK OF NEW YORK': 'BNY Mellon',
            'BNY MELLON': 'BNY Mellon',
            'NORTHERN TRUST': 'Northern Trust',
            'PNC': 'PNC Bank',
            'US BANK': 'U.S. Bank',
            'U.S. BANK': 'U.S. Bank',
            'TRUIST': 'Truist',
            'TD BANK': 'TD Bank',
            'CITIZENS': 'Citizens Bank',
            'FIFTH THIRD': 'Fifth Third Bank',
            'REGIONS': 'Regions Bank',
            'HUNTINGTON': 'Huntington Bank',
            'M&T BANK': 'M&T Bank',
            'SYNCHRONY': 'Synchrony Financial',
            'DISCOVER': 'Discover Financial',
            'NAVIENT': 'Navient',
            'SALLIE MAE': 'Sallie Mae',
            'ROCKET': 'Rocket Companies',
            'QUICKEN': 'Rocket Companies',
            'UNITED WHOLESALE': 'UWM Holdings',
            'PENNYMAC': 'PennyMac',
            'MR. COOPER': 'Mr. Cooper',
            'NATIONSTAR': 'Mr. Cooper',
            'LOANCARE': 'LoanCare',
            'ALLY': 'Ally Financial',
            'COINBASE': 'Coinbase',
            'ROBINHOOD': 'Robinhood',
            'PAYPAL': 'PayPal',
            'SQUARE': 'Block Inc',
            'BLOCK INC': 'Block Inc',
            'VISA': 'Visa',
            'MASTERCARD': 'Mastercard',
            'AFLAC': 'Aflac',
            'METLIFE': 'MetLife',
            'PRUDENTIAL': 'Prudential',
            'AIG': 'AIG',
            'ALLSTATE': 'Allstate',
            'PROGRESSIVE': 'Progressive',
            'BERKSHIRE': 'Berkshire Hathaway',
        }

        # Ticker to company name mapping for stock overlap detection
        TICKER_TO_COMPANY = {
            'JPM': 'JPMorgan Chase',
            'BAC': 'Bank of America',
            'GS': 'Goldman Sachs',
            'MS': 'Morgan Stanley',
            'WFC': 'Wells Fargo',
            'C': 'Citigroup',
            'AXP': 'American Express',
            'COF': 'Capital One',
            'BLK': 'BlackRock',
            'SCHW': 'Charles Schwab',
            'BK': 'BNY Mellon',
            'STT': 'State Street',
            'NTRS': 'Northern Trust',
            'PNC': 'PNC Bank',
            'USB': 'U.S. Bank',
            'TFC': 'Truist',
            'TD': 'TD Bank',
            'CFG': 'Citizens Bank',
            'FITB': 'Fifth Third Bank',
            'RF': 'Regions Bank',
            'HBAN': 'Huntington Bank',
            'MTB': 'M&T Bank',
            'SYF': 'Synchrony Financial',
            'DFS': 'Discover Financial',
            'NAVI': 'Navient',
            'RKT': 'Rocket Companies',
            'UWMC': 'UWM Holdings',
            'PFSI': 'PennyMac',
            'COOP': 'Mr. Cooper',
            'ALLY': 'Ally Financial',
            'COIN': 'Coinbase',
            'HOOD': 'Robinhood',
            'PYPL': 'PayPal',
            'SQ': 'Block Inc',
            'V': 'Visa',
            'MA': 'Mastercard',
            'AFL': 'Aflac',
            'MET': 'MetLife',
            'PRU': 'Prudential',
            'AIG': 'AIG',
            'ALL': 'Allstate',
            'PGR': 'Progressive',
            'BRK.A': 'Berkshire Hathaway',
            'BRK.B': 'Berkshire Hathaway',
        }

        def normalize_company_name(name: str) -> str:
            """Normalize a PAC or employer name to canonical company name."""
            name_upper = name.upper().strip()

            # Remove common suffixes
            for suffix in [' PAC', ' POLITICAL ACTION', ' POLITICAL FUND', ' COMMITTEE',
                           ' INC', ' LLC', ' CORP', ' CORPORATION', ' CO', ' LTD',
                           ' & CO', ' AND CO', ' GROUP', ' HOLDINGS']:
                name_upper = name_upper.replace(suffix, '')

            name_upper = name_upper.strip()

            # Check direct mapping
            for key, canonical in PAC_TO_COMPANY.items():
                if key in name_upper:
                    return canonical

            # Return cleaned name if no mapping found
            return name.strip()

        def get_traded_companies(official: dict) -> set:
            """Get set of canonical company names from stock trades."""
            traded = set()
            for trade in official.get('trades', []):
                ticker = trade.get('ticker', '').upper()
                if ticker in TICKER_TO_COMPANY:
                    traded.add(TICKER_TO_COMPANY[ticker])
                # Also try company name from trade
                company = trade.get('company', '')
                if company:
                    canonical = normalize_company_name(company)
                    traded.add(canonical)
            return traded

        for official in self.officials_data:
            # Get traded companies for overlap detection
            traded_companies = get_traded_companies(official)

            # Aggregate contributions by company
            company_totals = {}

            # Add PAC contributions
            for pac in official.get('top_financial_pacs', []):
                pac_name = pac.get('name', '')
                amount = pac.get('amount', 0)
                canonical = normalize_company_name(pac_name)

                if canonical not in company_totals:
                    company_totals[canonical] = {
                        'name': canonical,
                        'pac_amount': 0,
                        'individual_amount': 0,
                        'total': 0,
                        'stock_overlap': False
                    }
                company_totals[canonical]['pac_amount'] += amount
                company_totals[canonical]['total'] += amount

            # Add individual contributions by employer
            for employer in official.get('individual_financial_by_employer', []):
                employer_name = employer.get('employer', '')
                amount = employer.get('total', 0)
                canonical = normalize_company_name(employer_name)

                if canonical not in company_totals:
                    company_totals[canonical] = {
                        'name': canonical,
                        'pac_amount': 0,
                        'individual_amount': 0,
                        'total': 0,
                        'stock_overlap': False
                    }
                company_totals[canonical]['individual_amount'] += amount
                company_totals[canonical]['total'] += amount

            # Check for stock trading overlap
            for company, data in company_totals.items():
                if company in traded_companies:
                    data['stock_overlap'] = True

            # Sort by total and get top 5
            sorted_donors = sorted(
                company_totals.values(),
                key=lambda x: x['total'],
                reverse=True
            )[:5]

            official['top_donors'] = sorted_donors

            # Count overlaps for logging
            overlap_count = sum(1 for d in sorted_donors if d.get('stock_overlap'))
            if overlap_count > 0:
                logger.debug(f"  {official.get('name')}: {overlap_count} contribution/stock overlaps")

    def _normalize_scores_to_zscore(self):
        """
        Convert raw involvement scores to percentile rank normalized to 1-100 range.

        Using percentile rank instead of Z-score for better distribution.
        Top performer = 100, bottom = 1, everyone else scaled proportionally.

        IMPORTANT: Officials with 0 raw score (no financial activity) get score of 1.
        Ties are handled by giving all tied officials the same percentile.
        """
        # Get all raw scores
        raw_scores = [(i, o.get('involvement_score', 0) or 0) for i, o in enumerate(self.officials_data)]

        if len(raw_scores) < 2:
            # Not enough data to normalize
            return

        # Sort by score to get ranks (secondary sort by name for stability)
        sorted_scores = sorted(raw_scores, key=lambda x: (x[1], self.officials_data[x[0]].get('name', '')))
        n = len(sorted_scores)

        # Create rank lookup with proper tie handling
        # All officials with the same score get the same percentile
        rank_lookup = {}
        current_rank = 0
        prev_score = None
        prev_percentile = None

        for rank, (idx, score) in enumerate(sorted_scores):
            if score != prev_score:
                # New score value - calculate new percentile
                # Officials with 0 score get percentile 1 (minimum)
                if score == 0:
                    percentile = 1
                else:
                    percentile = round(((rank + 1) / n) * 99 + 1)
                prev_score = score
                prev_percentile = percentile
            else:
                # Same score as previous - use same percentile (tie handling)
                percentile = prev_percentile

            rank_lookup[idx] = percentile

        # Count officials with actual activity vs none
        with_activity = sum(1 for i, s in raw_scores if s > 0)
        without_activity = n - with_activity
        logger.info(f"Score normalization: {n} officials ({with_activity} with activity, {without_activity} without)")

        # Apply percentile normalization to each official
        for i, official in enumerate(self.officials_data):
            raw_score = official.get('involvement_score', 0)
            percentile = rank_lookup.get(i, 50)

            # Store both raw and normalized scores
            official['raw_score'] = raw_score
            official['involvement_score'] = percentile
            official['percentile_rank'] = percentile

            # Update score breakdown
            if 'score_breakdown' in official:
                official['score_breakdown']['raw_score'] = raw_score
                official['score_breakdown']['percentile'] = percentile

    def process_firms(self):
        """
        Build comprehensive firm records from actual trade data.

        This replaces the Finnhub-dependent approach by building firms
        from officials' trading activity.
        """
        from justdata.apps.electwatch.services.firm_mapper import (
            get_mapper, get_sector_for_ticker, TICKER_TO_SECTOR
        )

        mapper = get_mapper()
        firms_by_ticker = {}

        # Build firms from all officials' trade data
        for official in self.officials_data:
            for trade in official.get('trades', []):
                ticker = trade.get('ticker', '').upper()
                if not ticker:
                    continue

                if ticker not in firms_by_ticker:
                    # Get sector using both quick lookup and FirmMapper
                    sector = get_sector_for_ticker(ticker)
                    if not sector:
                        # Fall back to FirmMapper for more comprehensive lookup
                        industries = mapper.get_industry_from_ticker(ticker)
                        sector = industries[0] if industries else ''

                    # Get firm name from FirmMapper or use company name from trade
                    firm_record = mapper.get_firm_from_ticker(ticker)
                    firm_name = firm_record.name if firm_record else trade.get('company', ticker)

                    firms_by_ticker[ticker] = {
                        'ticker': ticker,
                        'name': firm_name,
                        'sector': sector,
                        'industry': sector,  # Alias for compatibility
                        'officials': [],
                        'trades': [],
                        'total_value': {'min': 0, 'max': 0},
                        'purchase_count': 0,
                        'sale_count': 0,
                        'officials_count': 0
                    }

                firm = firms_by_ticker[ticker]

                # Add official connection if not already present
                if official['name'] not in [o['name'] for o in firm['officials']]:
                    firm['officials'].append({
                        'id': official.get('id', ''),
                        'name': official['name'],
                        'party': official.get('party', ''),
                        'state': official.get('state', ''),
                        'chamber': official.get('chamber', 'house'),
                        'photo_url': official.get('photo_url')
                    })
                    firm['officials_count'] = len(firm['officials'])

                # Add trade record
                firm['trades'].append({
                    'official': official['name'],
                    'type': trade.get('type'),
                    'amount': trade.get('amount'),
                    'date': trade.get('transaction_date')
                })

                # Track transaction type
                if trade.get('type') == 'purchase':
                    firm['purchase_count'] += 1
                elif trade.get('type') == 'sale':
                    firm['sale_count'] += 1

                # Accumulate value
                amt = trade.get('amount', {})
                if isinstance(amt, dict):
                    firm['total_value']['min'] += amt.get('min', 0)
                    firm['total_value']['max'] += amt.get('max', 0)
                elif isinstance(amt, (int, float)):
                    firm['total_value']['min'] += amt
                    firm['total_value']['max'] += amt

        # Convert to list and add computed fields
        firms_list = []
        for ticker, firm in firms_by_ticker.items():
            # Calculate total for sorting
            firm['total'] = (firm['total_value']['min'] + firm['total_value']['max']) / 2
            firm['stock_trades'] = firm['total']

            # Limit trades to most recent 50
            firm['trades'] = sorted(
                firm['trades'],
                key=lambda x: x.get('date', ''),
                reverse=True
            )[:50]

            firms_list.append(firm)

        # Sort by total value (descending)
        firms_list.sort(key=lambda x: x['total'], reverse=True)

        # Keep existing Finnhub firms data if available (for quotes/news)
        # Merge trade-based data into Finnhub data
        finnhub_firms = {f.get('ticker', '').upper(): f for f in self.firms_data if f.get('ticker')}
        for firm in firms_list:
            ticker = firm['ticker']
            if ticker in finnhub_firms:
                # Merge Finnhub data (quotes, news, insider transactions)
                finnhub_data = finnhub_firms[ticker]
                firm['quote'] = finnhub_data.get('quote')
                firm['news'] = finnhub_data.get('news', [])
                firm['insider_transactions'] = finnhub_data.get('insider_transactions', [])
                firm['sec_filings'] = finnhub_data.get('sec_filings', [])
                firm['market_cap'] = finnhub_data.get('market_cap', 0)

        self.firms_data = firms_list
        logger.info(f"Built {len(self.firms_data)} firms from trade data")

    def process_industries(self):
        """
        Build industry aggregations from firms and officials data.

        Populates each industry with:
        - firms: List of firms in this sector (from firms_data)
        - officials: List of officials who traded in this sector
        - total_trades: Total trade count
        - total_value: Aggregated trade value
        - news: Relevant news articles
        """
        from justdata.apps.electwatch.services.firm_mapper import FINANCIAL_SECTORS

        industries = []
        for sector_id, sector_info in FINANCIAL_SECTORS.items():
            # Find firms in this sector
            sector_firms = [
                {
                    'ticker': f.get('ticker'),
                    'name': f.get('name'),
                    'total': f.get('total', 0),
                    'officials_count': f.get('officials_count', 0),
                    'trade_count': len(f.get('trades', []))
                }
                for f in self.firms_data
                if f.get('sector') == sector_id or f.get('industry') == sector_id
            ]

            # Sort firms by total value and take top 20
            sector_firms = sorted(sector_firms, key=lambda x: x['total'], reverse=True)[:20]

            # Find unique officials who traded in this sector
            officials_set = {}
            total_trades = 0
            total_value_min = 0
            total_value_max = 0

            for firm in self.firms_data:
                if firm.get('sector') != sector_id and firm.get('industry') != sector_id:
                    continue

                total_trades += len(firm.get('trades', []))
                total_value_min += firm.get('total_value', {}).get('min', 0)
                total_value_max += firm.get('total_value', {}).get('max', 0)

                for official in firm.get('officials', []):
                    if official['name'] not in officials_set:
                        officials_set[official['name']] = {
                            'id': official.get('id', ''),
                            'name': official['name'],
                            'party': official.get('party', ''),
                            'state': official.get('state', ''),
                            'chamber': official.get('chamber', 'house'),
                            'photo_url': official.get('photo_url')
                        }

            # Convert officials dict to list and limit to top 30
            sector_officials = list(officials_set.values())[:30]

            industry = {
                'sector': sector_id,
                'name': sector_info.get('name', sector_id.title()),
                'description': sector_info.get('description', ''),
                'color': sector_info.get('color', '#6b7280'),
                'firms': sector_firms,
                'officials': sector_officials,
                'firms_count': len(sector_firms),
                'officials_count': len(officials_set),
                'total_trades': total_trades,
                'total_value': {
                    'min': total_value_min,
                    'max': total_value_max,
                    'display': f"${total_value_min:,.0f} - ${total_value_max:,.0f}"
                },
                'news': []
            }

            # Find relevant news
            keywords = sector_info.get('keywords', [sector_id])
            for article in self.news_data:
                title = article.get('title', '').lower()
                if any(kw.lower() in title for kw in keywords):
                    industry['news'].append(article)
                    if len(industry['news']) >= 10:
                        break

            industries.append(industry)

        # Sort industries by total_trades (descending)
        industries.sort(key=lambda x: x['total_trades'], reverse=True)

        self.industries_data = industries
        logger.info(f"Processed {len(self.industries_data)} industries with {sum(i['firms_count'] for i in industries)} total firm entries and {sum(i['officials_count'] for i in industries)} unique officials")

    def process_committees(self):
        """Build committee data (mostly static but enriched with live stats)."""
        # Committee structure is relatively static
        # This could be enhanced to pull from Congress.gov API
        self.committees_data = [
            {
                'id': 'house-financial-services',
                'name': 'Financial Services',
                'full_name': 'House Committee on Financial Services',
                'chamber': 'House',
                'chair': 'J. French Hill (R-AR)',
                'ranking_member': 'Maxine Waters (D-CA)',
                'members_count': 71,
                'jurisdiction': 'Banking, insurance, securities, housing, urban development, international finance'
            },
            {
                'id': 'senate-banking',
                'name': 'Banking, Housing, and Urban Affairs',
                'full_name': 'Senate Committee on Banking, Housing, and Urban Affairs',
                'chamber': 'Senate',
                'chair': 'Tim Scott (R-SC)',
                'ranking_member': 'Elizabeth Warren (D-MA)',
                'members_count': 24,
                'jurisdiction': 'Banks, financial institutions, money and credit, urban housing, mass transit'
            },
            {
                'id': 'house-ways-means',
                'name': 'Ways and Means',
                'full_name': 'House Committee on Ways and Means',
                'chamber': 'House',
                'chair': 'Jason Smith (R-MO)',
                'ranking_member': 'Richard Neal (D-MA)',
                'members_count': 43,
                'jurisdiction': 'Taxation, tariffs, Social Security, Medicare'
            },
            {
                'id': 'senate-finance',
                'name': 'Finance',
                'full_name': 'Senate Committee on Finance',
                'chamber': 'Senate',
                'chair': 'Mike Crapo (R-ID)',
                'ranking_member': 'Ron Wyden (D-OR)',
                'members_count': 28,
                'jurisdiction': 'Taxation, trade, health programs, Social Security'
            }
        ]
        logger.info(f"Processed {len(self.committees_data)} committees")

    # =========================================================================
    # PHASE 3: GENERATE AI SUMMARIES
    # =========================================================================

    def generate_summaries(self):
        """Generate AI summaries using Claude."""
        logger.info("\n--- Generating AI Summaries ---")

        try:
            from anthropic import Anthropic
            api_key = os.getenv('CLAUDE_API_KEY')

            if not api_key:
                logger.warning("CLAUDE_API_KEY not set - skipping AI summaries")
                self.summaries = {'status': 'skipped', 'reason': 'No API key'}
                return

            client = Anthropic(api_key=api_key)

            # Generate weekly overview
            self.summaries['weekly_overview'] = self._generate_weekly_overview(client)

            # Generate top movers summary
            self.summaries['top_movers'] = self._generate_top_movers(client)

            # Generate industry highlights
            self.summaries['industry_highlights'] = self._generate_industry_highlights(client)

            self.summaries['status'] = 'generated'
            self.summaries['generated_at'] = datetime.now().isoformat()

            logger.info("AI summaries generated successfully")

        except Exception as e:
            logger.error(f"AI summary generation failed: {e}")
            self.warnings.append(f"AI Summaries: {e}")
            self.summaries = {'status': 'failed', 'error': str(e)}

    def _generate_weekly_overview(self, client) -> str:
        """Generate weekly overview summary."""
        try:
            # Build context from data
            top_officials = self.officials_data[:10]
            top_traders = "\n".join([
                f"- {o['name']} ({o['party']}-{o['state']}): {o['total_trades']} trades, {o['stock_trades_display']}"
                for o in top_officials
            ])

            recent_news = "\n".join([
                f"- {n.get('title', '')[:80]}..."
                for n in self.news_data[:10]
            ])

            prompt = f"""Summarize this week's key developments in congressional financial activity in 2-3 paragraphs. Be factual and neutral.

TOP TRADERS THIS WEEK:
{top_traders}

RECENT NEWS:
{recent_news}

Write a concise summary suitable for a dashboard overview."""

            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

            return response.content[0].text

        except Exception as e:
            logger.warning(f"Weekly overview generation failed: {e}")
            return "Weekly summary unavailable."

    def _generate_top_movers(self, client) -> str:
        """Generate summary of notable trading activity."""
        try:
            top_officials = self.officials_data[:5]
            context = "\n".join([
                f"- {o['name']}: {o['purchase_count']} purchases, {o['sale_count']} sales, total value {o['stock_trades_display']}"
                for o in top_officials
            ])

            prompt = f"""Based on this congressional trading data, write 2-3 bullet points highlighting the most notable trading activity:

{context}

Be factual and avoid speculation."""

            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )

            return response.content[0].text

        except Exception as e:
            logger.warning(f"Top movers generation failed: {e}")
            return "Top movers summary unavailable."

    def _generate_industry_highlights(self, client) -> str:
        """Generate industry-focused summary."""
        try:
            # Find most-traded sectors
            sector_trades = {}
            for official in self.officials_data:
                for trade in official.get('trades', [])[:10]:
                    ticker = trade.get('ticker', '')
                    # Simple sector mapping
                    if ticker in ['WFC', 'JPM', 'BAC', 'C', 'GS', 'MS']:
                        sector = 'banking'
                    elif ticker in ['COIN', 'HOOD']:
                        sector = 'crypto'
                    else:
                        sector = 'other'
                    sector_trades[sector] = sector_trades.get(sector, 0) + 1

            prompt = f"""Based on congressional trading patterns showing {sector_trades.get('banking', 0)} banking trades and {sector_trades.get('crypto', 0)} crypto trades, write 2 sentences about industry focus."""

            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}]
            )

            return response.content[0].text

        except Exception as e:
            logger.warning(f"Industry highlights generation failed: {e}")
            return "Industry highlights unavailable."

    def _generate_pattern_insights(self) -> List[Dict[str, Any]]:
        """Generate AI pattern insights for the dashboard using the app's insight generator."""
        try:
            # Import the insight generator from the app
            from justdata.apps.electwatch.app import _generate_ai_pattern_insights

            logger.info("Calling AI to generate pattern insights...")
            insights = _generate_ai_pattern_insights()

            if insights and len(insights) > 0:
                logger.info(f"Generated {len(insights)} pattern insights")
                return insights
            else:
                logger.warning("AI returned no insights")
                return []

        except Exception as e:
            logger.error(f"Pattern insight generation failed: {e}")
            import traceback
            traceback.print_exc()
            return []

    # =========================================================================
    # PHASE 4: SAVE DATA
    # =========================================================================

    def save_all_data(self):
        """Save all processed data to storage."""
        from justdata.apps.electwatch.services.data_store import (
            save_officials, save_firms, save_industries,
            save_committees, save_news, save_summaries, save_insights, save_metadata,
            save_trend_snapshot, enrich_officials_with_trends,
            enrich_officials_with_time_series
        )

        # Save trend snapshot BEFORE enriching (captures raw current state)
        logger.info("Saving trend snapshot...")
        save_trend_snapshot(self.officials_data)

        # Enrich officials with trend data for display (finance_pct trends)
        logger.info("Enriching officials with trend data...")
        enrich_officials_with_trends(self.officials_data)

        # NEW: Enrich with time-series data for charts (trades/contributions by quarter)
        logger.info("Enriching officials with time-series data for trend charts...")
        enrich_officials_with_time_series(self.officials_data)

        logger.info("Saving officials data...")
        save_officials(self.officials_data, self.weekly_dir)

        logger.info("Saving firms data...")
        save_firms(self.firms_data, self.weekly_dir)

        logger.info("Saving industries data...")
        save_industries(self.industries_data, self.weekly_dir)

        logger.info("Saving committees data...")
        save_committees(self.committees_data, self.weekly_dir)

        logger.info("Saving news data...")
        save_news(self.news_data, self.weekly_dir)

        logger.info("Saving AI summaries...")
        save_summaries(self.summaries, self.weekly_dir)

        logger.info("Generating AI pattern insights...")
        insights = self._generate_pattern_insights()
        if insights:
            logger.info(f"Saving {len(insights)} AI insights...")
            save_insights(insights, self.weekly_dir)
        else:
            logger.warning("No insights generated - using sample insights")
            from justdata.apps.electwatch.app import _get_sample_insights
            save_insights(_get_sample_insights(), self.weekly_dir)

        # Calculate next update time (next Sunday midnight)
        now = datetime.now()
        days_until_sunday = (6 - now.weekday()) % 7
        if days_until_sunday == 0 and now.hour >= 1:  # If it's Sunday after 1am, next week
            days_until_sunday = 7
        next_sunday = (now + timedelta(days=days_until_sunday)).replace(hour=0, minute=0, second=0, microsecond=0)

        # Save metadata
        # Calculate date ranges for different data sources
        # Stock trades use 24-month (730 day) rolling window
        stock_start = self.start_time - timedelta(days=730)
        # FEC data uses 24-month rolling window for contributions
        fec_start = self.start_time - timedelta(days=730)

        metadata = {
            'status': 'valid',
            'last_updated': self.start_time.isoformat(),
            'last_updated_display': self.start_time.strftime('%B %d, %Y at %I:%M %p'),
            'data_window': {
                'start': (self.start_time - timedelta(days=365)).strftime('%B %d, %Y'),
                'end': self.start_time.strftime('%B %d, %Y')
            },
            'stock_data_window': {
                'start': stock_start.strftime('%B %d, %Y'),
                'end': self.start_time.strftime('%B %d, %Y'),
                'start_iso': stock_start.strftime('%Y-%m-%d'),
                'end_iso': self.start_time.strftime('%Y-%m-%d'),
                'description': '24-month rolling window of STOCK Act disclosures'
            },
            'fec_data_window': {
                'start': fec_start.strftime('%B %d, %Y'),
                'end': self.start_time.strftime('%B %d, %Y'),
                'start_iso': fec_start.strftime('%Y-%m-%d'),
                'end_iso': self.start_time.strftime('%Y-%m-%d'),
                'description': '24-month rolling window of FEC contributions'
            },
            'next_update': next_sunday.isoformat(),
            'next_update_display': next_sunday.strftime('%B %d, %Y at midnight'),
            'data_sources': self.source_status,
            'counts': {
                'officials': len(self.officials_data),
                'firms': len(self.firms_data),
                'industries': len(self.industries_data),
                'committees': len(self.committees_data),
                'news_articles': len(self.news_data)
            },
            'errors': self.errors,
            'warnings': self.warnings
        }

        logger.info("Saving metadata...")
        save_metadata(metadata, self.weekly_dir)

        logger.info(f"All data saved to {self.weekly_dir}")

        # Generate and save matching report
        logger.info("Generating matching report...")
        matching_report = self._generate_matching_report()
        self._save_matching_report(matching_report)

        # Validate data consistency
        logger.info("Validating data consistency...")
        validation_errors = self._validate_data_consistency()
        if validation_errors:
            logger.warning(f"Data validation found {len(validation_errors)} issues")
            for err in validation_errors[:10]:
                logger.warning(f"  - {err}")

    def _generate_matching_report(self) -> Dict:
        """
        Generate report of matching success/failure rates.

        This report helps track how well the crosswalk is working and
        identify officials or FMP names that aren't being matched.
        """
        total_officials = len(self.officials_data)
        officials_with_fec = sum(1 for o in self.officials_data if o.get('fec_candidate_id'))
        officials_with_trades = sum(1 for o in self.officials_data if o.get('trades'))
        officials_with_contributions = sum(1 for o in self.officials_data if o.get('contributions', 0) > 0)
        officials_with_financial_pac = sum(1 for o in self.officials_data if o.get('financial_sector_pac', 0) > 0)

        # Get unmatched names from FMP processing
        unmatched_fmp = getattr(self, '_unmatched_fmp_names', [])

        # Get officials without FEC match from source status
        fec_status = self.source_status.get('fec', {})
        crosswalk_matches = fec_status.get('crosswalk_matches', 0)
        crosswalk_misses = fec_status.get('crosswalk_misses', 0)

        return {
            'generated_at': datetime.now().isoformat(),
            'total_officials': total_officials,
            'fec_enriched': officials_with_fec,
            'fec_enriched_pct': round(officials_with_fec / total_officials * 100, 1) if total_officials else 0,
            'fmp_enriched': officials_with_trades,
            'fmp_enriched_pct': round(officials_with_trades / total_officials * 100, 1) if total_officials else 0,
            'with_contributions': officials_with_contributions,
            'with_financial_pac': officials_with_financial_pac,
            'crosswalk_stats': {
                'matches': crosswalk_matches,
                'misses': crosswalk_misses,
                'match_rate_pct': round(crosswalk_matches / (crosswalk_matches + crosswalk_misses) * 100, 1) if (crosswalk_matches + crosswalk_misses) > 0 else 0
            },
            'unmatched_fmp_names': unmatched_fmp,
            'unmatched_fmp_count': len(unmatched_fmp),
            'source_status': self.source_status,
            'summary': {
                'fec_rate': f"{officials_with_fec}/{total_officials} ({round(officials_with_fec / total_officials * 100, 1) if total_officials else 0}%)",
                'trade_rate': f"{officials_with_trades}/{total_officials} ({round(officials_with_trades / total_officials * 100, 1) if total_officials else 0}%)",
                'crosswalk_rate': f"{crosswalk_matches}/{crosswalk_matches + crosswalk_misses} ({round(crosswalk_matches / (crosswalk_matches + crosswalk_misses) * 100, 1) if (crosswalk_matches + crosswalk_misses) > 0 else 0}%)"
            }
        }

    def _save_matching_report(self, report: Dict):
        """Save matching report to data/current/matching_report.json."""
        report_path = Path(__file__).parent / 'data' / 'current' / 'matching_report.json'
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Matching report saved to {report_path}")

    def _validate_data_consistency(self) -> List[str]:
        """
        Validate that all data is properly connected and consistent.

        Returns:
            List of validation error messages
        """
        errors = []

        for official in self.officials_data:
            name = official.get('name', 'Unknown')

            # Check required fields
            if not official.get('bioguide_id'):
                # Only warn for officials with significant activity
                if official.get('contributions', 0) > 10000 or official.get('total_trades', 0) > 5:
                    errors.append(f"{name}: Missing bioguide_id (has ${official.get('contributions', 0):,} contributions)")

            # Check contribution consistency
            pac_total = official.get('contributions', 0) or 0
            individual_total = official.get('individual_contributions_total', 0) or official.get('individual_contributions', 0) or 0

            # Get display totals if they exist
            display = official.get('contributions_display', {})
            display_total = display.get('total', 0) if isinstance(display, dict) else 0
            display_financial = display.get('financial', 0) if isinstance(display, dict) else 0

            # Only check if we have display data
            if display_total > 0:
                expected_total = pac_total + individual_total
                # Allow 1% tolerance for rounding
                if abs(expected_total - display_total) > display_total * 0.01 and abs(expected_total - display_total) > 1000:
                    errors.append(f"{name}: Contribution mismatch - PAC({pac_total:,}) + Individual({individual_total:,}) = {expected_total:,} != Display({display_total:,})")

            # Check years in Congress vs first_elected
            years = official.get('years_in_congress', 0)
            first_elected = official.get('first_elected')
            if first_elected and years:
                current_year = datetime.now().year
                expected_years = current_year - first_elected
                # Allow 1 year tolerance
                if abs(years - expected_years) > 1:
                    errors.append(f"{name}: Years mismatch - stored({years}) vs calculated({expected_years}) from first_elected({first_elected})")

            # Check for FEC ID without contributions (suspicious)
            if official.get('fec_candidate_id') and not official.get('contributions') and not official.get('pac_contributions'):
                # This might be normal for new members, just log as info
                logger.debug(f"{name}: Has FEC ID but no contribution data")

        return errors

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
        logger.info(f"Data saved to: {self.weekly_dir}")

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
