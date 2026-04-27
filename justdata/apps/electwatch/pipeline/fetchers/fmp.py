"""Financial Modeling Prep (FMP) congressional trading fetcher."""
import logging
from datetime import datetime
from typing import Dict, List

from justdata.apps.electwatch.weekly_update import (
    ELECTION_CYCLE_START,
    normalize_to_public_name,
)

logger = logging.getLogger(__name__)


def fetch_fmp_data(coordinator):
    """Fetch congressional trading data from Financial Modeling Prep (FMP).

    FMP provides comprehensive STOCK Act disclosure data for both House and Senate,
    focused on financial sector stocks only.
    """
    logger.info("\n--- Fetching FMP Congressional Trading (Financial Sector) ---")

    # Try to load from cache first
    cached = coordinator.load_cache('fmp_trades')
    if cached:
        trades_data = cached.get('data', {})
        house_trades = trades_data.get('house', [])
        senate_trades = trades_data.get('senate', [])
        all_trades = house_trades + senate_trades
        if all_trades:
            logger.info(f"  [CACHE] Loaded {len(all_trades)} trades from cache")
            _process_fmp_trades(coordinator, all_trades, len(house_trades), len(senate_trades), from_cache=True)
            return

    try:
        from justdata.apps.electwatch.services.fmp_client import FMPClient, ALL_FINANCIAL_SYMBOLS
        client = FMPClient()

        if not client.test_connection():
            raise Exception("FMP API connection failed")

        # Use election cycle start date (covers 2023-2024 and 2025-2026 cycles)
        from_date = ELECTION_CYCLE_START

        # Fetch financial sector trades only
        logger.info(f"Fetching trades for {len(ALL_FINANCIAL_SYMBOLS)} financial sector symbols...")
        trades_data = client.get_financial_sector_trades(from_date=from_date)

        house_trades = trades_data.get('house', [])
        senate_trades = trades_data.get('senate', [])
        all_trades = house_trades + senate_trades

        logger.info(f"Fetched {len(house_trades)} House trades, {len(senate_trades)} Senate trades")
        logger.info(f"Total: {len(all_trades)} financial sector trades")

        # Save to cache immediately after successful fetch
        coordinator.save_cache('fmp_trades', trades_data, {
            'house_trades': len(house_trades),
            'senate_trades': len(senate_trades),
            'total_trades': len(all_trades)
        })

        # Process the trades
        _process_fmp_trades(coordinator, all_trades, len(house_trades), len(senate_trades), from_cache=False)

    except Exception as e:
        logger.error(f"FMP fetch failed: {e}")
        import traceback
        traceback.print_exc()
        coordinator.errors.append(f"FMP: {e}")
        coordinator.source_status['fmp'] = {'status': 'failed', 'error': str(e)}


def _build_crosswalk_name_lookup(coordinator) -> Dict[str, Dict]:
    """Build comprehensive name lookup using crosswalk nicknames.

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
        return coordinator._officials_by_name if hasattr(coordinator, '_officials_by_name') else {}

    lookup = {}
    for official in coordinator.officials_data:
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

    logger.info(f"Built crosswalk name lookup with {len(lookup)} entries for {len(coordinator.officials_data)} officials")
    return lookup


def _process_fmp_trades(coordinator, all_trades: List[Dict], house_count: int, senate_count: int, from_cache: bool = False):
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
    if hasattr(coordinator, '_officials_by_name') and coordinator._officials_by_name:
        # Build comprehensive name lookup using crosswalk (includes nicknames)
        crosswalk_lookup = _build_crosswalk_name_lookup(coordinator)

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
            elif name_lower in coordinator._officials_by_name:
                matching_official = coordinator._officials_by_name[name_lower]
            elif last_name in coordinator._officials_by_name:
                matching_official = coordinator._officials_by_name[last_name]

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
                coordinator.officials_data.append(trade_data)
                new_count += 1

        # Store unmatched names for matching report
        coordinator._unmatched_fmp_names = unmatched_names

        logger.info(f"FMP Trade Matching: {enriched_count} matched via crosswalk, "
                   f"{new_count} new/unmatched")
        if unmatched_names:
            logger.info(f"  Unmatched FMP names: {unmatched_names[:10]}{'...' if len(unmatched_names) > 10 else ''}")
    else:
        # No Congress roster - use trade data as officials (fallback)
        coordinator.officials_data = list(politicians.values())
        coordinator._unmatched_fmp_names = []

    coordinator.source_status['fmp'] = {
        'status': 'success',
        'house_trades': house_count,
        'senate_trades': senate_count,
        'total_trades': len(all_trades),
        'officials': len(coordinator.officials_data),
        'matched_via_crosswalk': enriched_count if 'enriched_count' in dir() else 0,
        'unmatched_count': len(coordinator._unmatched_fmp_names) if hasattr(coordinator, '_unmatched_fmp_names') else 0,
        'from_cache': from_cache,
        'timestamp': datetime.now().isoformat()
    }
    logger.info(f"Processed {len(coordinator.officials_data)} officials from FMP trade data")
