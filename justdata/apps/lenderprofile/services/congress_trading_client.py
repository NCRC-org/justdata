#!/usr/bin/env python3
"""
Congress Trading Client - Quiver Quantitative API

Fetches congressional stock trading data from Quiver Quantitative.
- Current data for both Senate and House
- Daily updates from STOCK Act disclosures

Requires QUIVER_API_KEY environment variable.
Sign up at: https://api.quiverquant.com/ (Hobbyist plan: $10/mo, 7-day free trial)
Use promo code: TWITTER
"""

import logging
import os
import re
import requests
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


# Amount range buckets from STOCK Act disclosures
# Used to convert ranges to numeric values for aggregation
AMOUNT_RANGES = {
    '$1,001 - $15,000': (1001, 15000),
    '$15,001 - $50,000': (15001, 50000),
    '$50,001 - $100,000': (50001, 100000),
    '$100,001 - $250,000': (100001, 250000),
    '$250,001 - $500,000': (250001, 500000),
    '$500,001 - $1,000,000': (500001, 1000000),
    '$1,000,001 - $5,000,000': (1000001, 5000000),
    '$5,000,001 - $25,000,000': (5000001, 25000000),
    '$25,000,001 - $50,000,000': (25000001, 50000000),
    'Over $50,000,000': (50000001, 100000000),
}


def normalize_politician_name(name: str) -> str:
    """
    Normalize politician name for fuzzy matching/deduplication.
    Removes common variations like 'Mrs', 'Jr.', 'III', etc.

    Examples:
        "Marjorie Taylor Mrs Greene" -> "marjorie taylor greene"
        "David J. Taylor" -> "david taylor"
        "Tommy Tuberville Jr." -> "tommy tuberville"
    """
    if not name:
        return ""

    # Lowercase
    name = name.lower().strip()

    # Remove common titles and suffixes
    remove_patterns = [
        r'\bmrs\.?\b', r'\bmr\.?\b', r'\bms\.?\b', r'\bdr\.?\b',
        r'\bjr\.?\b', r'\bsr\.?\b', r'\biii\b', r'\bii\b', r'\biv\b',
        r'\bhon\.?\b', r'\bsen\.?\b', r'\brep\.?\b',
    ]
    for pattern in remove_patterns:
        name = re.sub(pattern, '', name)

    # Remove middle initials (single letters followed by period or space)
    name = re.sub(r'\b[a-z]\.\s*', '', name)
    name = re.sub(r'\b[a-z]\s+', ' ', name)

    # Remove extra spaces
    name = ' '.join(name.split())

    return name


def parse_amount_range(amount_str: str) -> Tuple[int, int]:
    """
    Parse STOCK Act amount range to (min, max) tuple.

    Args:
        amount_str: Amount string like "$1,001 - $15,000" or "$100K - $250K"

    Returns:
        Tuple of (min_amount, max_amount) in dollars
    """
    if not amount_str:
        return (0, 0)

    # Normalize the string
    amount_str = amount_str.strip()

    # Check known ranges first
    for range_str, (min_val, max_val) in AMOUNT_RANGES.items():
        if range_str.lower() in amount_str.lower():
            return (min_val, max_val)

    # Try to parse custom format
    # Remove $ and commas, handle K/M suffixes
    clean = amount_str.replace('$', '').replace(',', '')

    # Handle "Over $X" format
    over_match = re.match(r'over\s+(\d+)', clean.lower())
    if over_match:
        val = int(over_match.group(1))
        return (val, val * 2)  # Estimate upper bound

    # Handle "X - Y" format
    range_match = re.match(r'(\d+)\s*-\s*(\d+)', clean)
    if range_match:
        return (int(range_match.group(1)), int(range_match.group(2)))

    return (0, 0)


def format_amount_range(min_val: int, max_val: int) -> str:
    """
    Format amount range for display.

    Args:
        min_val: Minimum amount in dollars
        max_val: Maximum amount in dollars

    Returns:
        Formatted string like "$1.5M - $3.2M" or "$15K - $50K"
    """
    def fmt(val: int) -> str:
        if val >= 1000000:
            return f"${val/1000000:.1f}M".replace('.0M', 'M')
        elif val >= 1000:
            return f"${val/1000:.0f}K"
        else:
            return f"${val:,}"

    return f"{fmt(min_val)} - {fmt(max_val)}"

# Lazy import to avoid circular dependencies
_congressional_data_client = None

def get_congressional_data_client():
    """Get or create the Congressional Data client for committee lookups."""
    global _congressional_data_client
    if _congressional_data_client is None:
        try:
            from apps.lenderprofile.services.congressional_data_client import CongressionalDataClient
            _congressional_data_client = CongressionalDataClient()
        except Exception as e:
            logger.warning(f"Could not load Congressional Data client: {e}")
    return _congressional_data_client


class CongressTradingClient:
    """
    Client for fetching congressional trading data from Quiver Quantitative.

    Quiver provides current data on Senate and House stock trades as required
    by the STOCK Act. Data is updated daily.
    """

    BASE_URL = "https://api.quiverquant.com/beta"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Congress Trading client.

        Args:
            api_key: Quiver API key (defaults to QUIVER_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('QUIVER_API_KEY')
        if not self.api_key:
            logger.warning("QUIVER_API_KEY not set - Congressional trading data will not be available. "
                          "Sign up at https://api.quiverquant.com/ (use promo code TWITTER)")

        self.timeout = 30
        self._cache = {}
        self._cache_time = {}
        self._cache_duration = timedelta(hours=1)

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache is still valid for a key."""
        if key not in self._cache_time:
            return False
        return datetime.now() - self._cache_time[key] < self._cache_duration

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[List[Dict]]:
        """Make authenticated request to Quiver API."""
        if not self.api_key:
            logger.warning("No Quiver API key configured")
            return None

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'application/json'
        }
        url = f"{self.BASE_URL}/{endpoint}"

        try:
            logger.info(f"Quiver API request: {endpoint}")
            response = requests.get(url, headers=headers, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Quiver API returned {len(data) if isinstance(data, list) else 'non-list'} records")
            return data if isinstance(data, list) else []

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error("Quiver API: Invalid API key")
            elif e.response.status_code == 403:
                logger.error("Quiver API: Access forbidden - check subscription tier")
            else:
                logger.error(f"Quiver API HTTP error: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Quiver API request error: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Quiver API JSON decode error: {e}")
            return None

    def _fetch_congress_trades(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch congressional trades from Quiver API."""
        cache_key = f"congress_{symbol or 'all'}"
        if cache_key in self._cache and self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        # Quiver endpoint: /bulk/congresstrading for all, or /historical/congresstrading/{ticker}
        if symbol:
            endpoint = f"historical/congresstrading/{symbol.upper()}"
        else:
            endpoint = "bulk/congresstrading"

        data = self._make_request(endpoint)
        if data:
            self._cache[cache_key] = data
            self._cache_time[cache_key] = datetime.now()
            return data
        return []

    def _normalize_quiver_trade(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Quiver trade data to common format."""
        # Quiver fields: Date, Representative, Transaction, Amount, Ticker, House/Senate, etc.

        # Determine chamber
        rep = trade.get('Representative', '')
        house_indicator = trade.get('House', '')
        if house_indicator:
            chamber = 'House' if house_indicator.lower() in ['house', 'h'] else 'Senate'
        else:
            chamber = 'Senate' if 'Sen.' in rep or 'Senator' in rep else 'House'

        # Normalize transaction type
        trans_type = trade.get('Transaction', '').lower()
        if 'purchase' in trans_type or 'buy' in trans_type:
            transaction_type = 'purchase'
        elif 'sale' in trans_type or 'sell' in trans_type:
            transaction_type = 'sale'
        elif 'exchange' in trans_type:
            transaction_type = 'exchange'
        else:
            transaction_type = trans_type

        # Parse date
        trade_date = trade.get('Date', trade.get('TransactionDate', ''))
        if trade_date:
            try:
                # Handle various date formats
                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%Y-%m-%dT%H:%M:%S']:
                    try:
                        dt = datetime.strptime(trade_date[:10], fmt[:len(trade_date[:10])])
                        trade_date = dt.strftime('%Y-%m-%d')
                        break
                    except:
                        continue
            except:
                pass

        return {
            'name': trade.get('Representative', trade.get('Name', 'Unknown')),
            'position': 'Senator' if chamber == 'Senate' else 'Representative',
            'chamber': chamber,
            'transactionDate': trade_date,
            'filingDate': trade.get('ReportDate', trade_date),
            'transactionType': transaction_type,
            'transactionAmount': trade.get('Amount', trade.get('Range', '')),
            'assetName': trade.get('Description', trade.get('Asset', '')),
            'symbol': trade.get('Ticker', '').upper() if trade.get('Ticker') else '',
            'ownerType': trade.get('Owner', '').lower() if trade.get('Owner') else '',
            'party': trade.get('Party', ''),
            'state': trade.get('State', trade.get('District', ''))
        }

    def get_congressional_trading(
        self,
        symbol: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get congressional trading data for a stock symbol.

        Args:
            symbol: Stock ticker symbol (e.g., 'FITB', 'AAPL')
            from_date: Start date (YYYY-MM-DD), defaults to 2 years ago
            to_date: End date (YYYY-MM-DD), defaults to today

        Returns:
            List of congressional trades matching the symbol
        """
        if not symbol:
            return []

        symbol = symbol.upper().strip()

        # Set default date range - 5 years to capture more trades
        if not from_date:
            from_date = (datetime.now() - timedelta(days=1825)).strftime('%Y-%m-%d')  # 5 years
        if not to_date:
            to_date = datetime.now().strftime('%Y-%m-%d')

        # Fetch trades for this symbol
        raw_trades = self._fetch_congress_trades(symbol)

        all_trades = []
        for trade in raw_trades:
            normalized = self._normalize_quiver_trade(trade)
            # Filter by date
            trade_date = normalized.get('transactionDate', '')
            if trade_date and from_date <= trade_date <= to_date:
                all_trades.append(normalized)

        # Sort by date (most recent first)
        all_trades.sort(key=lambda x: x.get('transactionDate', ''), reverse=True)

        logger.info(f"Found {len(all_trades)} congressional trades for {symbol}")
        return all_trades

    def format_congressional_trades_for_report(
        self,
        trades: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Format congressional trades for display in report."""
        formatted = []

        for trade in trades:
            formatted.append({
                'politician_name': trade.get('name', 'Unknown'),
                'position': trade.get('position', ''),
                'chamber': trade.get('chamber', ''),
                'party': trade.get('party', ''),
                'state': trade.get('state', ''),
                'transaction_date': trade.get('transactionDate', ''),
                'filing_date': trade.get('filingDate', ''),
                'transaction_type': trade.get('transactionType', '').lower(),
                'amount_range': trade.get('transactionAmount', ''),
                'asset_name': trade.get('assetName', ''),
                'symbol': trade.get('symbol', ''),
                'owner_type': trade.get('ownerType', '')
            })

        return formatted

    def _determine_position_status(self, purchases: int, sales: int) -> str:
        """
        Determine a politician's position status based on trading activity.

        Returns:
            Status string: 'Accumulating', 'Divesting', 'Active Trader', 'Likely Holder', 'Exited'
        """
        if purchases == 0 and sales == 0:
            return 'No Activity'
        if purchases > 0 and sales == 0:
            return 'Likely Holder'  # Only bought, never sold
        if purchases == 0 and sales > 0:
            return 'Exited'  # Only sold, never bought (had prior position)
        if purchases > sales:
            return 'Accumulating'  # Net buyer
        if sales > purchases:
            return 'Divesting'  # Net seller
        return 'Active Trader'  # Equal buys and sells

    def _enrich_politician_with_committees(self, politician: Dict[str, Any]) -> Dict[str, Any]:
        """Add committee membership data to politician profile."""
        cong_client = get_congressional_data_client()
        if not cong_client:
            return politician

        try:
            profile = cong_client.get_politician_profile(politician.get('name', ''))
            if profile and profile.get('has_data'):
                politician['committees'] = profile.get('committees', [])[:3]  # Top 3 committees
                politician['finance_committees'] = profile.get('finance_committees', [])
                politician['is_finance_member'] = profile.get('is_finance_committee_member', False)
                politician['leadership_roles'] = profile.get('leadership_roles', [])[:2]
        except Exception as e:
            logger.warning(f"Could not get committee data for {politician.get('name')}: {e}")

        return politician

    def get_congressional_summary(
        self,
        symbol: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get summary of congressional trading activity for intelligence report.

        Returns enhanced data including:
        - Net position analysis (Accumulating, Divesting, Holder, etc.)
        - Committee memberships for each politician
        - Finance committee flags for relevant oversight
        - Sentiment summary

        Args:
            symbol: Stock ticker symbol
            from_date: Start date
            to_date: End date

        Returns:
            Summary dict with trade counts, politician profiles, and analysis
        """
        if not self.api_key:
            return {
                'total_trades': 0,
                'total_purchases': 0,
                'total_sales': 0,
                'unique_politicians': 0,
                'recent_trades': [],
                'top_buyers': [],
                'recent_buyers': [],
                'recent_sellers': [],
                'politician_profiles': [],
                'notable_traders': [],
                'has_data': False,
                'error': 'QUIVER_API_KEY not configured. Sign up at https://api.quiverquant.com/'
            }

        trades = self.get_congressional_trading(symbol, from_date, to_date)

        if not trades:
            return {
                'total_trades': 0,
                'total_purchases': 0,
                'total_sales': 0,
                'unique_politicians': 0,
                'recent_trades': [],
                'top_buyers': [],
                'recent_buyers': [],
                'recent_sellers': [],
                'politician_profiles': [],
                'notable_traders': [],
                'has_data': False,
                'data_source': 'Quiver Quantitative'
            }

        # Count purchases and sales
        purchases = [t for t in trades if t.get('transactionType', '').lower() == 'purchase']
        sales = [t for t in trades if t.get('transactionType', '').lower() == 'sale']

        # Build detailed politician profiles with net positions
        # Use fuzzy name matching to deduplicate similar names
        politicians = {}
        name_to_canonical = {}  # Maps normalized name -> canonical display name

        for trade in trades:
            original_name = trade.get('name', 'Unknown')
            normalized = normalize_politician_name(original_name)

            # Find or create canonical name for this normalized form
            if normalized not in name_to_canonical:
                name_to_canonical[normalized] = original_name  # First occurrence becomes canonical
            canonical_name = name_to_canonical[normalized]

            if canonical_name not in politicians:
                politicians[canonical_name] = {
                    'name': canonical_name,
                    'position': trade.get('position', ''),
                    'chamber': trade.get('chamber', ''),
                    'party': trade.get('party', ''),
                    'state': trade.get('state', ''),
                    'purchases': 0,
                    'sales': 0,
                    'purchase_amount_min': 0,
                    'purchase_amount_max': 0,
                    'sale_amount_min': 0,
                    'sale_amount_max': 0,
                    'last_trade_date': trade.get('transactionDate', ''),
                    'first_trade_date': trade.get('transactionDate', ''),
                    'last_filing_date': trade.get('filingDate', ''),
                    'committees': [],
                    'finance_committees': [],
                    'is_finance_member': False,
                }

            # Parse and accumulate amount ranges
            amount_str = trade.get('transactionAmount', '')
            min_amt, max_amt = parse_amount_range(amount_str)

            if trade.get('transactionType', '').lower() == 'purchase':
                politicians[canonical_name]['purchases'] += 1
                politicians[canonical_name]['purchase_amount_min'] += min_amt
                politicians[canonical_name]['purchase_amount_max'] += max_amt
            else:
                politicians[canonical_name]['sales'] += 1
                politicians[canonical_name]['sale_amount_min'] += min_amt
                politicians[canonical_name]['sale_amount_max'] += max_amt

            # Track earliest trade and latest filing
            trade_date = trade.get('transactionDate', '')
            if trade_date and trade_date < politicians[canonical_name].get('first_trade_date', '9999'):
                politicians[canonical_name]['first_trade_date'] = trade_date

            filing_date = trade.get('filingDate', '')
            if filing_date and filing_date > politicians[canonical_name].get('last_filing_date', ''):
                politicians[canonical_name]['last_filing_date'] = filing_date

        # Enrich each politician with position status, committees, and formatted amounts
        for name, pol in politicians.items():
            pol['status'] = self._determine_position_status(pol['purchases'], pol['sales'])
            pol['net_position'] = pol['purchases'] - pol['sales']

            # Format amount ranges for display
            if pol['purchase_amount_min'] > 0:
                pol['purchase_amount_range'] = format_amount_range(
                    pol['purchase_amount_min'], pol['purchase_amount_max']
                )
            else:
                pol['purchase_amount_range'] = ''

            if pol['sale_amount_min'] > 0:
                pol['sale_amount_range'] = format_amount_range(
                    pol['sale_amount_min'], pol['sale_amount_max']
                )
            else:
                pol['sale_amount_range'] = ''

            pol = self._enrich_politician_with_committees(pol)

        # Create sorted politician profiles
        politician_profiles = sorted(
            list(politicians.values()),
            key=lambda x: (
                -x['purchases'],  # Most purchases first
                -x['sales'],      # Then most sales
                x['name']         # Then alphabetical
            )
        )

        # Top buyers (by number of purchases)
        top_buyers = [p for p in politician_profiles if p['purchases'] > 0][:5]

        # Categorize by status
        accumulators = [p for p in politician_profiles if p['status'] == 'Accumulating']
        holders = [p for p in politician_profiles if p['status'] == 'Likely Holder']
        divesters = [p for p in politician_profiles if p['status'] in ['Divesting', 'Exited']]

        # Finance committee members trading this stock (notable)
        finance_traders = [p for p in politician_profiles if p.get('is_finance_member')]

        # Format trades for display
        formatted_trades = self.format_congressional_trades_for_report(trades)

        # Recent buyers and sellers (formatted)
        recent_buyers = self.format_congressional_trades_for_report(purchases[:5])
        recent_sellers = self.format_congressional_trades_for_report(sales[:5])

        # Determine data date range based on FILING dates (not transaction dates)
        # Filing date = when the disclosure was reported, transaction date = when trade occurred
        filing_dates = [t.get('filingDate', '') for t in trades if t.get('filingDate')]
        if filing_dates:
            latest_filing = max(filing_dates)
            date_range = f"Most recent filing: {latest_filing}"
        else:
            # Fall back to transaction dates if no filing dates
            dates = [t.get('transactionDate', '') for t in trades if t.get('transactionDate')]
            date_range = f"Most recent trade: {max(dates)}" if dates else "Unknown"

        # Overall sentiment
        if len(purchases) > len(sales) * 1.5:
            sentiment = 'Bullish'
        elif len(sales) > len(purchases) * 1.5:
            sentiment = 'Bearish'
        else:
            sentiment = 'Mixed'

        # Summary text
        summary_parts = []
        if accumulators:
            summary_parts.append(f"{len(accumulators)} accumulating")
        if holders:
            summary_parts.append(f"{len(holders)} likely holding")
        if divesters:
            summary_parts.append(f"{len(divesters)} divesting/exited")
        position_summary = ", ".join(summary_parts) if summary_parts else "No clear pattern"

        return {
            'total_trades': len(trades),
            'total_purchases': len(purchases),
            'total_sales': len(sales),
            'unique_politicians': len(politicians),
            'sentiment': sentiment,
            'position_summary': position_summary,
            'recent_trades': formatted_trades[:10],
            'top_buyers': top_buyers,
            'recent_buyers': recent_buyers,
            'recent_sellers': recent_sellers,
            'politician_profiles': politician_profiles,
            'accumulators': accumulators,
            'holders': holders,
            'divesters': divesters,
            'finance_committee_traders': finance_traders,
            'notable_traders': list(politicians.values()),  # Keep for backwards compatibility
            'has_data': True,
            'data_source': 'Quiver Quantitative (STOCK Act Data)',
            'date_range': date_range
        }


# Convenience function for quick testing
def test_congress_trading_client():
    """Test the Congress Trading client with Quiver API."""
    client = CongressTradingClient()

    if not client.api_key:
        print("ERROR: QUIVER_API_KEY not set in environment")
        print("Sign up at: https://api.quiverquant.com/")
        print("Use promo code: TWITTER")
        print("Then add to .env: QUIVER_API_KEY=your_token_here")
        return

    print("Testing Congress Trading Client (Quiver API)...")
    print("=" * 50)

    for symbol in ['AAPL', 'MSFT', 'NVDA']:
        print(f"\n{symbol}:")
        summary = client.get_congressional_summary(symbol)
        print(f"  Total Trades: {summary.get('total_trades')}")
        print(f"  Purchases: {summary.get('total_purchases')}")
        print(f"  Sales: {summary.get('total_sales')}")
        print(f"  Unique Politicians: {summary.get('unique_politicians')}")
        print(f"  Date Range: {summary.get('date_range', 'N/A')}")
        print(f"  Source: {summary.get('data_source')}")

        if summary.get('recent_trades'):
            print("  Recent Trades:")
            for t in summary['recent_trades'][:3]:
                print(f"    - {t['politician_name']} ({t['chamber']}, {t['party']})")
                print(f"      {t['transaction_type'].upper()} on {t['transaction_date']}")
                print(f"      Amount: {t['amount_range']}")


if __name__ == '__main__':
    test_congress_trading_client()
