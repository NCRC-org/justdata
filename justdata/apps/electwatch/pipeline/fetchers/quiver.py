"""Quiver Quant congressional trading fetcher (LEGACY - replaced by FMP)."""
import logging
from datetime import datetime

from justdata.apps.electwatch.weekly_update import ELECTION_CYCLE_START

logger = logging.getLogger(__name__)


def fetch_quiver_data(coordinator):
    """Fetch congressional trading data from Quiver (LEGACY - replaced by FMP)."""
    logger.info("\n--- Fetching Quiver Congressional Trading ---")
    try:
        from justdata.apps.electwatch.services.quiver_client import QuiverClient
        client = QuiverClient()

        if not client.test_connection():
            raise Exception("Quiver API connection failed")

        # Fetch all trades from election cycle start (covers 2023-2024 and 2025-2026)
        days_since_cycle_start = (datetime.now() - datetime.strptime(ELECTION_CYCLE_START, '%Y-%m-%d')).days
        trades = client.get_recent_trades(days=days_since_cycle_start)
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
        if hasattr(coordinator, '_officials_by_name') and coordinator._officials_by_name:
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
                if name_lower in coordinator._officials_by_name:
                    matching_official = coordinator._officials_by_name[name_lower]
                # Try last name
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
                    # Official not in Congress roster - add as new (rare case)
                    trade_data['has_financial_activity'] = True
                    coordinator.officials_data.append(trade_data)
                    new_count += 1

            logger.info(f"Enriched {enriched_count} existing officials, added {new_count} new")
        else:
            # No Congress roster - use trade data as officials (fallback)
            coordinator.officials_data = list(politicians.values())

        coordinator.source_status['quiver'] = {
            'status': 'success',
            'records': len(trades) if trades else 0,
            'officials': len(coordinator.officials_data),
            'timestamp': datetime.now().isoformat()
        }
        logger.info(f"Processed {len(coordinator.officials_data)} officials from trade data")

    except Exception as e:
        logger.error(f"Quiver fetch failed: {e}")
        coordinator.errors.append(f"Quiver: {e}")
        coordinator.source_status['quiver'] = {'status': 'failed', 'error': str(e)}
