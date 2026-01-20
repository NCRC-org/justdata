#!/usr/bin/env python3
"""
Quiver Quantitative API Client for ElectWatch

Fetches congressional stock trading data from STOCK Act disclosures.
- Trades by politician name (for official profiles)
- Trades by stock ticker (for firm analysis)
- Daily updates from STOCK Act filings

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

# Local imports
from justdata.apps.electwatch.config import ElectWatchConfig
from justdata.apps.electwatch.services.firm_mapper import AmountRange, parse_stock_amount

logger = logging.getLogger(__name__)


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


class QuiverClient:
    """
    Client for fetching congressional trading data from Quiver Quantitative.

    Quiver provides current data on Senate and House stock trades as required
    by the STOCK Act. Data is updated daily.

    Usage:
        client = QuiverClient()

        # Get trades for a specific politician
        trades = client.get_trades_by_politician('Nancy Pelosi')

        # Get trades for a stock ticker
        trades = client.get_trades_by_ticker('AAPL')

        # Get all recent trades
        trades = client.get_recent_trades(days=30)
    """

    BASE_URL = "https://api.quiverquant.com/beta"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Quiver client.

        Args:
            api_key: Quiver API key (defaults to QUIVER_API_KEY env var)
        """
        self.api_key = api_key or ElectWatchConfig.QUIVER_API_KEY
        if not self.api_key:
            logger.warning(
                "QUIVER_API_KEY not set - Congressional trading data will not be available. "
                "Sign up at https://api.quiverquant.com/ (use promo code TWITTER)"
            )

        self.timeout = 30
        self._cache = {}
        self._cache_time = {}
        self._cache_duration = timedelta(hours=1)

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache is still valid for a key."""
        if key not in self._cache_time:
            return False
        return datetime.now() - self._cache_time[key] < self._cache_duration

    def _make_request(self, endpoint: str, params: Optional[Dict] = None, retries: int = 3) -> Optional[List[Dict]]:
        """Make authenticated request to Quiver API with retry logic."""
        if not self.api_key:
            logger.warning("No Quiver API key configured")
            return None

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'application/json'
        }
        url = f"{self.BASE_URL}/{endpoint}"

        for attempt in range(retries):
            try:
                logger.info(f"Quiver API request: {endpoint} (attempt {attempt + 1}/{retries})")
                response = requests.get(url, headers=headers, params=params, timeout=self.timeout)
                response.raise_for_status()

                data = response.json()
                logger.info(f"Quiver API returned {len(data) if isinstance(data, list) else 'non-list'} records")
                return data if isinstance(data, list) else []

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 401:
                    logger.error("Quiver API: Invalid API key")
                    return None  # Don't retry auth errors
                elif e.response.status_code == 403:
                    logger.error("Quiver API: Access forbidden - check subscription tier")
                    return None  # Don't retry forbidden
                elif e.response.status_code == 500:
                    logger.warning(f"Quiver API: Server error (500), attempt {attempt + 1}/{retries}")
                    if attempt < retries - 1:
                        import time
                        time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
                        continue
                else:
                    logger.error(f"Quiver API HTTP error: {e}")
                return None
            except requests.exceptions.RequestException as e:
                logger.warning(f"Quiver API request error: {e}, attempt {attempt + 1}/{retries}")
                if attempt < retries - 1:
                    import time
                    time.sleep(2 ** attempt)
                    continue
                return None
            except json.JSONDecodeError as e:
                logger.error(f"Quiver API JSON decode error: {e}")
                return None

        return None

    def _fetch_all_trades(self) -> List[Dict[str, Any]]:
        """Fetch all congressional trades from Quiver API (live endpoint)."""
        cache_key = "live_trades"
        if cache_key in self._cache and self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        # Try live endpoint first (more reliable), fallback to bulk
        data = self._make_request("live/congresstrading")
        if not data:
            logger.info("Live endpoint failed, trying bulk endpoint...")
            data = self._make_request("bulk/congresstrading")

        if data:
            self._cache[cache_key] = data
            self._cache_time[cache_key] = datetime.now()
            return data
        return []

    def _fetch_trades_by_ticker(self, symbol: str) -> List[Dict[str, Any]]:
        """Fetch congressional trades for a specific ticker."""
        cache_key = f"ticker_{symbol.upper()}"
        if cache_key in self._cache and self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        data = self._make_request(f"historical/congresstrading/{symbol.upper()}")
        if data:
            self._cache[cache_key] = data
            self._cache_time[cache_key] = datetime.now()
            return data
        return []

    def _normalize_trade(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize Quiver trade data to ElectWatch format.

        Returns dict with:
            - politician_name: Name of the official
            - chamber: 'house' or 'senate'
            - party: Party affiliation
            - state: State code
            - ticker: Stock symbol
            - company: Company name
            - type: 'purchase' or 'sale'
            - amount_range: STOCK Act bucket string
            - amount: AmountRange object serialized
            - transaction_date: Date of transaction
            - filing_date: Date of STOCK Act filing
        """
        # Determine chamber
        rep = trade.get('Representative', '')
        house_indicator = trade.get('House', '')
        if house_indicator:
            # Quiver API returns 'Representatives' for House, 'Senate' for Senate
            house_values = ['house', 'h', 'representatives', 'representative']
            chamber = 'house' if house_indicator.lower() in house_values else 'senate'
        else:
            chamber = 'senate' if 'Sen.' in rep or 'Senator' in rep else 'house'

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
        filing_date = trade.get('ReportDate', trade_date)

        def parse_date(date_str):
            if not date_str:
                return ''
            try:
                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%Y-%m-%dT%H:%M:%S']:
                    try:
                        dt = datetime.strptime(date_str[:10], fmt[:len(date_str[:10])])
                        return dt.strftime('%Y-%m-%d')
                    except:
                        continue
            except:
                pass
            return date_str

        trade_date = parse_date(trade_date)
        filing_date = parse_date(filing_date)

        # Parse amount range
        amount_str = trade.get('Amount', trade.get('Range', ''))
        amount_range = AmountRange.from_bucket(amount_str) if amount_str else AmountRange.zero()

        return {
            'politician_name': trade.get('Representative', trade.get('Name', 'Unknown')),
            'bioguide_id': trade.get('BioGuideID', trade.get('bioguide_id', '')),
            'chamber': chamber,
            'party': trade.get('Party', ''),
            'state': trade.get('State', trade.get('District', '')),
            'ticker': trade.get('Ticker', '').upper() if trade.get('Ticker') else '',
            'company': trade.get('Description', trade.get('Asset', '')),
            'type': transaction_type,
            'amount_range': amount_str,
            'amount': amount_range.to_dict(),
            'transaction_date': trade_date,
            'filing_date': filing_date,
            'owner_type': trade.get('Owner', '').lower() if trade.get('Owner') else '',
            'excess_return': trade.get('ExcessReturn'),
            'price_change': trade.get('PriceChange'),
        }

    def get_trades_by_politician(
        self,
        politician_name: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        trade_type: Optional[str] = None  # 'purchase', 'sale', or None for all
    ) -> List[Dict[str, Any]]:
        """
        Get all stock trades for a specific politician.

        Args:
            politician_name: Name of the politician (fuzzy matched)
            from_date: Start date (YYYY-MM-DD), defaults to DATA_START_DATE
            to_date: End date (YYYY-MM-DD), defaults to today
            trade_type: Filter by 'purchase' or 'sale'

        Returns:
            List of trade records for this politician
        """
        if not from_date:
            from_date = ElectWatchConfig.DATA_START_DATE
        if not to_date:
            to_date = datetime.now().strftime('%Y-%m-%d')

        # Normalize the search name
        search_name = normalize_politician_name(politician_name)

        # Fetch all trades
        raw_trades = self._fetch_all_trades()

        results = []
        for trade in raw_trades:
            # Check name match (fuzzy)
            trade_name = normalize_politician_name(trade.get('Representative', ''))
            if search_name not in trade_name and trade_name not in search_name:
                # Try partial match
                search_parts = search_name.split()
                trade_parts = trade_name.split()
                if not any(sp in trade_parts for sp in search_parts):
                    continue

            normalized = self._normalize_trade(trade)

            # Filter by date
            trade_date = normalized.get('transaction_date', '')
            if trade_date and (trade_date < from_date or trade_date > to_date):
                continue

            # Filter by type
            if trade_type and normalized.get('type') != trade_type:
                continue

            results.append(normalized)

        # Sort by date (most recent first)
        results.sort(key=lambda x: x.get('transaction_date', ''), reverse=True)

        logger.info(f"Found {len(results)} trades for {politician_name}")
        return results

    def get_trades_by_ticker(
        self,
        ticker: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all congressional trades for a specific stock ticker.

        Args:
            ticker: Stock symbol (e.g., 'AAPL', 'WFC')
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)

        Returns:
            List of trade records for this ticker
        """
        if not ticker:
            return []

        ticker = ticker.upper().strip()

        if not from_date:
            from_date = ElectWatchConfig.DATA_START_DATE
        if not to_date:
            to_date = datetime.now().strftime('%Y-%m-%d')

        raw_trades = self._fetch_trades_by_ticker(ticker)

        results = []
        for trade in raw_trades:
            normalized = self._normalize_trade(trade)

            # Filter by date
            trade_date = normalized.get('transaction_date', '')
            if trade_date and (trade_date < from_date or trade_date > to_date):
                continue

            results.append(normalized)

        # Sort by date (most recent first)
        results.sort(key=lambda x: x.get('transaction_date', ''), reverse=True)

        logger.info(f"Found {len(results)} congressional trades for {ticker}")
        return results

    def get_recent_trades(
        self,
        days: int = 30,
        chamber: Optional[str] = None,  # 'house' or 'senate'
        party: Optional[str] = None  # 'R', 'D'
    ) -> List[Dict[str, Any]]:
        """
        Get recent congressional trades.

        Args:
            days: Number of days to look back
            chamber: Filter by 'house' or 'senate'
            party: Filter by party

        Returns:
            List of recent trade records
        """
        from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        to_date = datetime.now().strftime('%Y-%m-%d')

        raw_trades = self._fetch_all_trades()

        results = []
        for trade in raw_trades:
            normalized = self._normalize_trade(trade)

            # Filter by date
            trade_date = normalized.get('transaction_date', '')
            if trade_date and trade_date < from_date:
                continue

            # Filter by chamber
            if chamber and normalized.get('chamber', '').lower() != chamber.lower():
                continue

            # Filter by party
            if party and normalized.get('party', '').upper() != party.upper():
                continue

            results.append(normalized)

        # Sort by date (most recent first)
        results.sort(key=lambda x: x.get('transaction_date', ''), reverse=True)

        return results

    def aggregate_politician_trades(
        self,
        politician_name: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Aggregate trading activity for a politician.

        Returns summary with:
            - Total trades
            - Purchases vs sales
            - Amount ranges (proper min/max)
            - Stocks traded
            - Trading patterns
        """
        trades = self.get_trades_by_politician(politician_name, from_date, to_date)

        if not trades:
            return {
                'politician_name': politician_name,
                'has_data': False,
                'total_trades': 0
            }

        # Aggregate purchases and sales with proper range handling
        purchases = [t for t in trades if t.get('type') == 'purchase']
        sales = [t for t in trades if t.get('type') == 'sale']

        purchase_total = AmountRange.zero()
        for t in purchases:
            amt = t.get('amount', {})
            purchase_total = purchase_total + AmountRange(amt.get('min', 0), amt.get('max', 0))

        sale_total = AmountRange.zero()
        for t in sales:
            amt = t.get('amount', {})
            sale_total = sale_total + AmountRange(amt.get('min', 0), amt.get('max', 0))

        # Group by ticker
        by_ticker = {}
        for t in trades:
            ticker = t.get('ticker', 'UNKNOWN')
            if ticker not in by_ticker:
                by_ticker[ticker] = {
                    'ticker': ticker,
                    'company': t.get('company', ''),
                    'purchases': 0,
                    'sales': 0,
                    'purchase_amount': AmountRange.zero(),
                    'sale_amount': AmountRange.zero()
                }

            amt = t.get('amount', {})
            trade_amount = AmountRange(amt.get('min', 0), amt.get('max', 0))

            if t.get('type') == 'purchase':
                by_ticker[ticker]['purchases'] += 1
                by_ticker[ticker]['purchase_amount'] = by_ticker[ticker]['purchase_amount'] + trade_amount
            else:
                by_ticker[ticker]['sales'] += 1
                by_ticker[ticker]['sale_amount'] = by_ticker[ticker]['sale_amount'] + trade_amount

        # Convert AmountRanges in by_ticker to dicts
        for ticker_data in by_ticker.values():
            ticker_data['purchase_amount'] = ticker_data['purchase_amount'].to_dict()
            ticker_data['sale_amount'] = ticker_data['sale_amount'].to_dict()

        # Determine position status
        if len(purchases) > len(sales) * 1.5:
            status = 'Accumulating'
        elif len(sales) > len(purchases) * 1.5:
            status = 'Divesting'
        elif len(purchases) > 0 and len(sales) == 0:
            status = 'Likely Holder'
        elif len(sales) > 0 and len(purchases) == 0:
            status = 'Exited'
        else:
            status = 'Active Trader'

        # Get metadata from first trade
        sample = trades[0]

        return {
            'politician_name': sample.get('politician_name', politician_name),
            'chamber': sample.get('chamber', ''),
            'party': sample.get('party', ''),
            'state': sample.get('state', ''),
            'has_data': True,
            'total_trades': len(trades),
            'purchase_count': len(purchases),
            'sale_count': len(sales),
            'purchase_total': purchase_total.to_dict(),
            'sale_total': sale_total.to_dict(),
            'status': status,
            'by_ticker': list(by_ticker.values()),
            'recent_trades': trades[:10],
            'date_range': {
                'first': min(t.get('transaction_date', '') for t in trades),
                'last': max(t.get('transaction_date', '') for t in trades)
            }
        }

    def test_connection(self) -> bool:
        """Test API connection."""
        if not self.api_key:
            return False
        # Use live endpoint which is more reliable
        result = self._make_request("live/congresstrading")
        return result is not None


# =============================================================================
# MODULE-LEVEL CONVENIENCE FUNCTIONS
# =============================================================================

_client = None


def get_quiver_client() -> QuiverClient:
    """Get singleton QuiverClient instance."""
    global _client
    if _client is None:
        _client = QuiverClient()
    return _client


def get_trades_by_politician(politician_name: str, **kwargs) -> List[Dict]:
    """Convenience function to get trades for a politician."""
    return get_quiver_client().get_trades_by_politician(politician_name, **kwargs)


def get_trades_by_ticker(ticker: str, **kwargs) -> List[Dict]:
    """Convenience function to get trades for a ticker."""
    return get_quiver_client().get_trades_by_ticker(ticker, **kwargs)


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    client = QuiverClient()

    if not client.api_key:
        print("ERROR: QUIVER_API_KEY not set in environment")
        print("Sign up at: https://api.quiverquant.com/")
        print("Use promo code: TWITTER")
        print("Then add to .env: QUIVER_API_KEY=your_token_here")
    else:
        print("Testing Quiver Client for ElectWatch...")
        print("=" * 50)

        # Test by politician
        print("\n=== Trades by Politician ===")
        summary = client.aggregate_politician_trades('Nancy Pelosi')
        if summary.get('has_data'):
            print(f"Politician: {summary['politician_name']}")
            print(f"Total Trades: {summary['total_trades']}")
            print(f"Purchases: {summary['purchase_count']} ({summary['purchase_total']['display']})")
            print(f"Sales: {summary['sale_count']} ({summary['sale_total']['display']})")
            print(f"Status: {summary['status']}")
        else:
            print("No data found")

        # Test by ticker
        print("\n=== Trades by Ticker ===")
        trades = client.get_trades_by_ticker('AAPL')[:5]
        for t in trades:
            print(f"  {t['politician_name']} ({t['party']}-{t['state']}): "
                  f"{t['type']} {t['amount_range']} on {t['transaction_date']}")
