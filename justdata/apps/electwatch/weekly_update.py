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

# Map alternate names to canonical names (used for deduplication and matching)
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
}

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

    Uses House Clerk images for House members (reliable) and
    bioguide.congress.gov API for Senate members.
    """
    import requests

    # For House members, use the House Clerk's image service (most reliable)
    if bioguide_id and chamber == 'house':
        return f"https://clerk.house.gov/content/assets/img/members/{bioguide_id}.jpg"

    # For Senate members or if no bioguide_id, try bioguide.congress.gov API
    try:
        search_url = "https://bioguide.congress.gov/search/bio"

        # Parse name for search
        name_parts = name.split()
        if len(name_parts) >= 2:
            first_name = name_parts[0]
            last_name = name_parts[-1]
        else:
            first_name = name
            last_name = name

        params = {
            'firstName': first_name,
            'lastName': last_name,
            'currentMember': 'true'
        }

        response = requests.get(search_url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            members = data.get('members', [])

            for member in members:
                member_bio_id = member.get('bioguideId', '')
                if bioguide_id and member_bio_id == bioguide_id:
                    photo_id = member.get('profileImage', '')
                    if photo_id:
                        return f"https://bioguide.congress.gov/photo/{photo_id}.jpg"
                elif not bioguide_id:
                    photo_id = member.get('profileImage', '')
                    if photo_id:
                        return f"https://bioguide.congress.gov/photo/{photo_id}.jpg"

        # Fallback to House Clerk for any bioguide_id
        if bioguide_id:
            return f"https://clerk.house.gov/content/assets/img/members/{bioguide_id}.jpg"

    except Exception as e:
        logger.debug(f"Could not fetch bioguide photo for {name}: {e}")

    return None


class WeeklyDataUpdate:
    """Comprehensive weekly data update process."""

    def __init__(self):
        from justdata.apps.electwatch.services.data_store import get_weekly_data_path

        self.start_time = datetime.now()
        self.weekly_dir = get_weekly_data_path(self.start_time)
        self.errors = []
        self.warnings = []

        # Data containers
        self.officials_data = []
        self.firms_data = []
        self.industries_data = []
        self.committees_data = []
        self.news_data = []
        self.summaries = {}

        # Source status
        self.source_status = {}

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
                    parts = m['name'].split()
                    if len(parts) > 1:
                        last_name = parts[-1].lower()
                        if last_name not in self._officials_by_name:
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
        try:
            from justdata.apps.electwatch.services.fmp_client import FMPClient, ALL_FINANCIAL_SYMBOLS
            client = FMPClient()

            if not client.test_connection():
                raise Exception("FMP API connection failed")

            # Calculate date range (last 365 days)
            from_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

            # Fetch financial sector trades only
            logger.info(f"Fetching trades for {len(ALL_FINANCIAL_SYMBOLS)} financial sector symbols...")
            trades_data = client.get_financial_sector_trades(from_date=from_date)

            house_trades = trades_data.get('house', [])
            senate_trades = trades_data.get('senate', [])
            all_trades = house_trades + senate_trades

            logger.info(f"Fetched {len(house_trades)} House trades, {len(senate_trades)} Senate trades")
            logger.info(f"Total: {len(all_trades)} financial sector trades")

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

            self.source_status['fmp'] = {
                'status': 'success',
                'house_trades': len(house_trades),
                'senate_trades': len(senate_trades),
                'total_trades': len(all_trades),
                'officials': len(self.officials_data),
                'timestamp': datetime.now().isoformat()
            }
            logger.info(f"Processed {len(self.officials_data)} officials from FMP trade data")

        except Exception as e:
            logger.error(f"FMP fetch failed: {e}")
            import traceback
            traceback.print_exc()
            self.errors.append(f"FMP: {e}")
            self.source_status['fmp'] = {'status': 'failed', 'error': str(e)}
            # Don't fall back to Quiver - FMP is our primary source

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
        """Fetch campaign finance data from FEC for each official."""
        logger.info("\n--- Fetching FEC Campaign Finance ---")
        try:
            import time
            from justdata.apps.electwatch.services.fec_client import FECClient
            client = FECClient()

            if not client.test_connection():
                raise Exception("FEC API connection failed")

            # For each official, search FEC to find their candidate record and contributions
            officials_enriched = 0
            total_contributions = 0
            api_calls = 0
            max_api_calls = 700  # Increased limit - FEC allows 1000/hour

            for official in self.officials_data:
                if api_calls >= max_api_calls:
                    logger.info(f"FEC: Reached API call limit ({max_api_calls}), stopping")
                    break

                # Every 100 API calls, pause for 60 seconds to respect rate limits
                if api_calls > 0 and api_calls % 100 == 0:
                    logger.info(f"  FEC: Pausing 60s after {api_calls} API calls (rate limit protection)...")
                    time.sleep(60)

                try:
                    name = official.get('name', '')
                    if not name:
                        continue

                    # Parse name for FEC search (last name works best)
                    name_parts = name.split()
                    last_name = name_parts[-1] if name_parts else name

                    # Skip invalid last names that cause API errors
                    if last_name.lower() in ['jr', 'jr.', 'sr', 'sr.', 'ii', 'iii', 'iv', 'dr', 'dr.']:
                        # Try second-to-last name part
                        if len(name_parts) >= 2:
                            last_name = name_parts[-2]
                        else:
                            continue

                    # Skip very short names
                    if len(last_name) < 3:
                        continue

                    # Add delay to avoid rate limiting (0.5s between requests)
                    time.sleep(0.5)

                    # Determine office type from chamber
                    chamber = official.get('chamber', '').lower()
                    office = 'S' if chamber == 'senate' else 'H' if chamber == 'house' else None

                    # Search FEC for this official (use 2024 cycle for complete data)
                    candidates = client.search_candidates(
                        name=last_name,
                        office=office,
                        cycle=2024,
                        limit=5
                    )
                    api_calls += 1

                    if candidates:
                        # Find best match by comparing full name
                        best_match = None
                        first_name = name_parts[0].lower() if name_parts else ''

                        for cand in candidates:
                            cand_name_lower = cand.name.lower()
                            # Check if both first and last name match
                            if last_name.lower() in cand_name_lower and first_name in cand_name_lower:
                                best_match = cand
                                break

                        if best_match:
                            # Enrich official with FEC data
                            official['fec_candidate_id'] = best_match.candidate_id
                            # Only update state if we don't have it
                            if not official.get('state'):
                                official['state'] = best_match.state or ''
                            official['chamber'] = 'senate' if best_match.office == 'S' else 'house' if best_match.office == 'H' else official.get('chamber', '')
                            official['fec_party'] = best_match.party
                            # Update main party field from FEC data
                            if best_match.party:
                                official['party'] = best_match.party

                            # Add delay before next API call
                            time.sleep(0.5)

                            # Fetch candidate totals (faster than individual contributions)
                            try:
                                totals = client.get_candidate_totals(
                                    best_match.candidate_id,
                                    cycle=2024
                                )
                                api_calls += 1

                                if totals:
                                    # Use PAC contributions as primary metric (industry-specific)
                                    total_amount = totals.get('receipts', 0)
                                    individual_contribs = totals.get('individual_contributions', 0)
                                    pac_contribs = totals.get('pac_contributions', 0)

                                    # Use PAC contributions as the main "contributions" field
                                    # since PACs are organized by industry/company
                                    official['contributions'] = pac_contribs
                                    official['total_receipts'] = total_amount
                                    official['individual_contributions'] = individual_contribs
                                    official['pac_contributions'] = pac_contribs
                                    official['fec_cycle'] = totals.get('cycle')

                                    total_contributions += 1
                                    officials_enriched += 1
                                    logger.info(f"  FEC: {name} - ${pac_contribs:,.0f} PAC (${total_amount:,.0f} total)")
                            except Exception as ce:
                                logger.debug(f"Could not fetch totals for {name}: {ce}")

                except Exception as e:
                    logger.debug(f"FEC lookup failed for {official.get('name', 'unknown')}: {e}")
                    continue

            self.source_status['fec'] = {
                'status': 'success',
                'officials_enriched': officials_enriched,
                'total_contributions': total_contributions,
                'api_calls': api_calls,
                'timestamp': datetime.now().isoformat()
            }
            logger.info(f"FEC: Enriched {officials_enriched} officials with contribution data ({total_contributions} total contributions, {api_calls} API calls)")

        except Exception as e:
            logger.error(f"FEC fetch failed: {e}")
            self.warnings.append(f"FEC: {e}")
            self.source_status['fec'] = {'status': 'failed', 'error': str(e)}

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

        # Calculate rolling 12-month date window
        rolling_end_date = datetime.now()
        rolling_start_date = rolling_end_date - timedelta(days=365)
        min_date_str = rolling_start_date.strftime('%Y-%m-%d')
        max_date_str = rolling_end_date.strftime('%Y-%m-%d')
        logger.info(f"  Using rolling 12-month window: {min_date_str} to {max_date_str}")

        def get_financial_pac_total(committee_id: str) -> dict:
            """
            Get PAC contributions to a candidate's committee (rolling 12 months).

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

        def find_candidate_committee(name: str, state: str, chamber: str) -> Optional[str]:
            """Find a candidate's principal campaign committee ID."""
            url = 'https://api.open.fec.gov/v1/candidates/search/'

            # Build search query from name parts
            parts = name.split()
            if not parts:
                return None

            first_name = parts[0].upper()
            last_name = parts[-1].upper()

            # Handle names like "James French Hill" - use last significant name part
            # FEC format is typically "LASTNAME, FIRSTNAME MIDDLENAME"
            params = {
                'api_key': api_key,
                'q': last_name,
                'state': state,
                'office': 'H' if chamber == 'house' else 'S',
                'is_active_candidate': True,
                'per_page': 20
            }

            try:
                time.sleep(0.3)
                r = requests.get(url, params=params, timeout=30)
                if r.ok:
                    best_match = None
                    best_score = 0

                    for candidate in r.json().get('results', []):
                        cand_name = candidate.get('name', '').upper()

                        # FEC names are "LASTNAME, FIRSTNAME" format
                        # Score based on how well it matches
                        score = 0

                        # Must have last name
                        if last_name not in cand_name:
                            continue

                        score += 1

                        # Check if first name also matches
                        if first_name in cand_name:
                            score += 2

                        # Check for middle names if present
                        for part in parts[1:-1]:
                            if part.upper() in cand_name:
                                score += 1

                        # Prefer exact format match: "LASTNAME, FIRSTNAME"
                        expected_format = f"{last_name}, {first_name}"
                        if expected_format in cand_name:
                            score += 3

                        if score > best_score:
                            committees = candidate.get('principal_committees', [])
                            if committees:
                                best_score = score
                                best_match = committees[0].get('committee_id')

                    return best_match

            except Exception as e:
                logger.debug(f"  Error finding committee for {name}: {e}")

            return None

        try:
            matched_count = 0
            total_financial = 0

            for i, official in enumerate(self.officials_data):
                name = official.get('name', '')
                state = official.get('state', '')
                chamber = official.get('chamber', 'house')

                # Try to find candidate's committee ID
                # Note: fec_candidate_id is NOT the same as committee_id
                # We need to search for the actual principal campaign committee
                committee_id = find_candidate_committee(name, state, chamber)

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

                # Progress update
                if (i + 1) % 10 == 0:
                    logger.info(f"  Progress: {i + 1}/{len(self.officials_data)} officials processed")

            self.source_status['financial_pacs'] = {
                'status': 'success',
                'matched_officials': matched_count,
                'total_financial_contributions': total_financial,
                'timestamp': datetime.now().isoformat()
            }
            logger.info(f"Financial PACs: {matched_count}/{len(self.officials_data)} officials have financial sector contributions (${total_financial:,.0f} total)")

        except Exception as e:
            logger.error(f"Financial PAC fetch failed: {e}")
            self.warnings.append(f"Financial PACs: {e}")
            self.source_status['financial_pacs'] = {'status': 'failed', 'error': str(e)}

    
    def fetch_individual_financial_contributions(self):
        """Fetch individual contributions from financial sector executives."""
        try:
            from justdata.apps.electwatch.services.individual_contributions import enrich_officials_with_individual_contributions
            status = enrich_officials_with_individual_contributions(self.officials_data)
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
        # House photos: https://clerk.house.gov/content/assets/img/members/{bioguide_id}.jpg
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
                        trade_amt = amt.get('min', 0) or 0
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

            # Scoring system: trade activity + PAC contributions
            # Trade score: bucket_low_end / 1000 per trade
            trade_score = official.get('trade_score', 0)

            # PAC contributions (scaled to same units)
            contributions = official.get('contributions', 0)
            contrib_score = contributions / 1000  # $1K contrib = 1 pt

            # Combined score: trade activity + contributions
            official['involvement_score'] = round(trade_score + contrib_score)

            # Store component scores for transparency
            official['score_breakdown'] = {
                'trade_score': round(trade_score, 1),
                'contributions_score': round(contrib_score, 1),
                'total_trades': official.get('total_trades', 0)
            }

            # Calculate combined Financial Sector Influence %
            # Formula: (Financial PAC $ + Financial Individual $) / (Total PAC $ + Total Individual $)
            # This captures both organized PAC money AND personal relationships

            # PAC contributions
            total_pac = official.get('contributions', 0) or 0
            financial_pac = official.get('financial_sector_pac', 0) or 0

            # Individual contributions (from individual_contributions.py)
            total_individual = official.get('individual_contributions_total', 0) or 0
            financial_individual = official.get('individual_financial_total', 0) or 0

            # Combined numerator and denominator
            financial_total = financial_pac + financial_individual
            contribution_total = total_pac + total_individual

            # Calculate combined percentage
            if contribution_total > 0:
                combined_financial_pct = round((financial_total / contribution_total) * 100, 1)
            else:
                combined_financial_pct = 0

            # Also calculate component percentages for transparency
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

        # Filter out officials with no financial industry affiliation
        officials_with_industries = [
            o for o in self.officials_data
            if o.get('top_industries') and len(o['top_industries']) > 0
        ]

        # Also include officials with significant contributions even without mapped industries
        officials_with_contributions = [
            o for o in self.officials_data
            if o.get('contributions', 0) > 10000 and o not in officials_with_industries
        ]

        filtered_count = len(self.officials_data) - len(officials_with_industries) - len(officials_with_contributions)
        self.officials_data = officials_with_industries + officials_with_contributions

        # Convert raw scores to Z-scores normalized to 1-100
        self._normalize_scores_to_zscore()

        # Re-sort by involvement score
        self.officials_data.sort(key=lambda x: x.get('involvement_score', 0), reverse=True)

        logger.info(f"Processed {len(self.officials_data)} officials with industry data (filtered {filtered_count} without financial industry affiliation)")

    def _normalize_scores_to_zscore(self):
        """
        Convert raw involvement scores to percentile rank normalized to 1-100 range.

        Using percentile rank instead of Z-score for better distribution.
        Top performer = 100, bottom = 1, everyone else scaled proportionally.
        """
        # Get all raw scores and sort
        raw_scores = [(i, o.get('involvement_score', 0)) for i, o in enumerate(self.officials_data)]

        if len(raw_scores) < 2:
            # Not enough data to normalize
            return

        # Sort by score to get ranks
        sorted_scores = sorted(raw_scores, key=lambda x: x[1])
        n = len(sorted_scores)

        # Create rank lookup (index -> percentile rank)
        rank_lookup = {}
        for rank, (idx, score) in enumerate(sorted_scores):
            # Percentile rank: 1 for lowest, 100 for highest
            percentile = round(((rank + 1) / n) * 99 + 1)
            rank_lookup[idx] = percentile

        logger.info(f"Score normalization: {n} officials, percentile rank 1-100")

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
        """Process and enrich firms data."""
        for firm in self.firms_data:
            # Find officials who traded this stock
            ticker = firm.get('ticker', '').upper()
            officials_trading = []

            for official in self.officials_data:
                for trade in official.get('trades', []):
                    if trade.get('ticker', '').upper() == ticker:
                        if official['name'] not in [o['name'] for o in officials_trading]:
                            officials_trading.append({
                                'name': official['name'],
                                'party': official['party'],
                                'state': official['state'],
                                'chamber': official['chamber'],
                                'trade_count': sum(1 for t in official['trades'] if t.get('ticker', '').upper() == ticker)
                            })
                        break

            firm['officials'] = officials_trading
            firm['officials_count'] = len(officials_trading)

        logger.info(f"Processed {len(self.firms_data)} firms with official connections")

    def process_industries(self):
        """Build industry aggregations."""
        from justdata.apps.electwatch.services.firm_mapper import FINANCIAL_SECTORS

        industries = []
        for sector_id, sector_info in FINANCIAL_SECTORS.items():
            industry = {
                'sector': sector_id,
                'name': sector_info.get('name', sector_id.title()),
                'description': sector_info.get('description', ''),
                'firms': [],
                'officials': [],
                'news': [],
                'total_trades': 0
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

        self.industries_data = industries
        logger.info(f"Processed {len(self.industries_data)} industries")

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
            save_committees, save_news, save_summaries, save_insights, save_metadata
        )

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
        metadata = {
            'status': 'valid',
            'last_updated': self.start_time.isoformat(),
            'last_updated_display': self.start_time.strftime('%B %d, %Y at %I:%M %p'),
            'data_window': {
                'start': (self.start_time - timedelta(days=365)).strftime('%B %d, %Y'),
                'end': self.start_time.strftime('%B %d, %Y')
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
