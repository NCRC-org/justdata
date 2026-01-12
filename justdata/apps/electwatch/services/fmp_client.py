#!/usr/bin/env python3
"""
Financial Modeling Prep (FMP) API Client for ElectWatch

Fetches congressional stock trading data from FMP API.
- House trades by stock symbol
- Senate trades by stock symbol
- Focused on financial sector stocks only

Requires FMP_API_KEY environment variable.
Starter tier ($22/mo) required for congressional trading data.
"""

import logging
import os
import requests
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


# Financial sector stock symbols organized by category
FINANCIAL_SECTOR_SYMBOLS = {
    # Major Banks
    'banking': [
        'WFC',   # Wells Fargo
        'JPM',   # JPMorgan Chase
        'BAC',   # Bank of America
        'C',     # Citigroup
        'GS',    # Goldman Sachs
        'MS',    # Morgan Stanley
        'USB',   # U.S. Bancorp
        'PNC',   # PNC Financial
        'TFC',   # Truist Financial
        'COF',   # Capital One
        'FITB',  # Fifth Third
        'KEY',   # KeyCorp
        'RF',    # Regions Financial
        'HBAN',  # Huntington Bancshares
        'CFG',   # Citizens Financial
        'MTB',   # M&T Bank
        'ZION',  # Zions Bancorp
        'CMA',   # Comerica
        'FCNCA', # First Citizens BancShares
        'FHN',   # First Horizon
        'ALLY',  # Ally Financial
        'SIVB',  # SVB Financial (if still trading)
        'WAL',   # Western Alliance
        'PACW',  # PacWest Bancorp
    ],

    # Investment Banks / Asset Managers
    'investment': [
        'BLK',   # BlackRock
        'SCHW',  # Charles Schwab
        'BX',    # Blackstone
        'KKR',   # KKR & Co
        'APO',   # Apollo Global
        'ARES',  # Ares Management
        'CG',    # Carlyle Group
        'OWL',   # Blue Owl Capital
        'TROW',  # T. Rowe Price
        'IVZ',   # Invesco
        'BEN',   # Franklin Resources
        'NTRS',  # Northern Trust
        'STT',   # State Street
        'BK',    # Bank of New York Mellon
        'AMG',   # Affiliated Managers
        'EV',    # Eaton Vance
        'LPLA',  # LPL Financial
        'SF',    # Stifel Financial
        'MKTX',  # MarketAxess
        'VIRT',  # Virtu Financial
        'RJF',   # Raymond James
    ],

    # Payment Processing / Fintech
    'payments': [
        'V',     # Visa
        'MA',    # Mastercard
        'AXP',   # American Express
        'PYPL',  # PayPal
        'SQ',    # Block (Square)
        'FIS',   # Fidelity National Info
        'FISV',  # Fiserv
        'GPN',   # Global Payments
        'ADP',   # ADP
        'PAYX',  # Paychex
        'DFS',   # Discover Financial
        'SYF',   # Synchrony Financial
        'AFRM',  # Affirm
        'UPST',  # Upstart
        'SOFI',  # SoFi Technologies
        'NU',    # Nu Holdings
        'BILL',  # Bill.com
        'FOUR',  # Shift4 Payments
        'MELI',  # MercadoLibre
        'SHOP',  # Shopify
        'PAGS',  # PagSeguro
        'ADYEY', # Adyen
        'STNE',  # Stone
        'LSPD',  # Lightspeed POS
        'FLYW',  # Flywire
        'PAY',   # Paymentus
        'PAYO',  # Payoneer
        'MQ',    # Marqeta
        'TOST',  # Toast
        'RELY',  # Remitly
        'AVDX',  # AvidXchange
        'DLO',   # dLocal
        'WPLCF', # Wise
        'OLO',   # Olo
        'GDOT',  # Green Dot
        'CMPO',  # CompoSecure
    ],

    # Insurance
    'insurance': [
        'MET',   # MetLife
        'PRU',   # Prudential
        'AIG',   # AIG
        'ALL',   # Allstate
        'TRV',   # Travelers
        'AFL',   # Aflac
        'PGR',   # Progressive
        'CB',    # Chubb
        'HIG',   # Hartford Financial
        'LNC',   # Lincoln National
        'UNM',   # Unum Group
        'GL',    # Globe Life
        'PFG',   # Principal Financial
        'CINF',  # Cincinnati Financial
        'L',     # Loews Corp
        'EQH',   # Equitable Holdings
        'VOYA',  # Voya Financial
        'BHF',   # Brighthouse Financial
        'EVER',  # EverQuote
        'LMND',  # Lemonade
        'CLOV',  # Clover Health
        'OSCR',  # Oscar Health
        'BHG',   # Bright Health
        'HIPO',  # Hippo Insurance
    ],

    # Mortgage / Real Estate Finance
    'mortgage': [
        'FNMA',  # Fannie Mae
        'FMCC',  # Freddie Mac
        'RKT',   # Rocket Companies
        'UWMC',  # UWM Holdings
        'PFSI',  # PennyMac Financial
        'NLY',   # Annaly Capital
        'AGNC',  # AGNC Investment
        'STWD',  # Starwood Property
        'BXMT',  # Blackstone Mortgage
        'TWO',   # Two Harbors
        'MFA',   # MFA Financial
        'NYMT',  # New York Mortgage
    ],

    # Crypto / Digital Assets
    'crypto': [
        'COIN',  # Coinbase
        'HOOD',  # Robinhood
        'MSTR',  # MicroStrategy / Strategy Inc
        'RIOT',  # Riot Platforms
        'MARA',  # Marathon Digital / MARA Holdings
        'CLSK',  # CleanSpark
        'HUT',   # Hut 8 Mining
        'ARBK',  # Argo Blockchain
        'BTCS',  # BTCS Inc
        'BKKT',  # Bakkt Holdings
        'BTBT',  # Bit Digital
        'BTM',   # Bitcoin Depot
        'BTDR',  # Bitdeer Technologies
        'BITF',  # Bitfarms
        'CAN',   # Canaan Inc
        'CIFR',  # Cipher Mining
        'CORZ',  # Core Scientific
        'GREE',  # Greenidge Generation
        'HIVE',  # HIVE Digital
        'IREN',  # IREN Limited
        'MIGI',  # Mawson Infrastructure
        'SLNH',  # Soluna Holdings
        'WULF',  # TeraWulf
        'ANY',   # Sphere 3D
        'BULL',  # Webull
        'DFDV',  # DeFi Development Corp
    ],

    # Consumer Finance / Credit / Lending
    'consumer_finance': [
        'AXP',   # American Express
        'DFS',   # Discover
        'SYF',   # Synchrony
        'CACC',  # Credit Acceptance
        'OMF',   # OneMain Financial
        'SLM',   # SLM Corp (Sallie Mae)
        'NAVI',  # Navient
        'ENVA',  # Enova International
        'LU',    # Lufax
        'LDI',   # loanDepot
        'OPRT',  # Oportun Financial
        'OPFI',  # OppFi
        'ML',    # MoneyLion
        'NRDS',  # NerdWallet
        'MFIN',  # Medallion Financial
        'VEL',   # Velocity Financial
        'WD',    # Walker & Dunlop
        'CPSS',  # Consumer Portfolio Services
        'LX',    # LexinFintech
        'QFIN',  # Qfin Holdings
        'YRD',   # Yiren Digital
        'XYF',   # X Financial
        'JFIN',  # Jiayin Group
        'CNF',   # CNFinance
        'PGY',   # Pagaya Technologies
    ],

    # PropTech / Real Estate Tech
    'proptech': [
        'RDFN',  # Redfin
        'OPEN',  # OpenDoor
        'COMP',  # Compass
        'BLND',  # Blend Labs
    ],

    # Financial B2B SaaS
    'fintech_saas': [
        'ENV',   # Envestnet
        'QTWO',  # Q2 Holdings
        'NCNO',  # nCino
        'ALKT',  # Alkami Technology
        'INTA',  # Intapp
        'EXFY',  # Expensify
        'BL',    # Blackline
        'XROLF', # Xero
        'DAVE',  # Dave Inc
    ],
}

# Flatten to single list
ALL_FINANCIAL_SYMBOLS = []
for category, symbols in FINANCIAL_SECTOR_SYMBOLS.items():
    ALL_FINANCIAL_SYMBOLS.extend(symbols)
ALL_FINANCIAL_SYMBOLS = list(set(ALL_FINANCIAL_SYMBOLS))  # Remove duplicates


class FMPClient:
    """
    Client for Financial Modeling Prep congressional trading data.

    Usage:
        client = FMPClient()

        # Get all financial sector trades
        trades = client.get_financial_sector_trades()

        # Get trades for specific symbol
        trades = client.get_house_trades('WFC')
        trades = client.get_senate_trades('JPM')
    """

    BASE_URL = "https://financialmodelingprep.com/stable"

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the FMP client."""
        self.api_key = api_key or os.getenv('FMP_API_KEY')
        if not self.api_key:
            logger.warning("FMP_API_KEY not set - Congressional trading data will not be available")

        self.timeout = 30
        self._cache = {}
        self._cache_time = {}
        self._cache_duration = timedelta(hours=1)

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache is still valid."""
        if key not in self._cache_time:
            return False
        return datetime.now() - self._cache_time[key] < self._cache_duration

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[List[Dict]]:
        """Make authenticated request to FMP API."""
        if not self.api_key:
            logger.warning("No FMP API key configured")
            return None

        url = f"{self.BASE_URL}/{endpoint}"
        params = params or {}
        params['apikey'] = self.api_key

        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else []
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error("FMP API: Invalid API key")
            elif e.response.status_code == 402:
                logger.error("FMP API: Subscription required - upgrade to Starter tier")
            elif e.response.status_code == 403:
                logger.error("FMP API: Access forbidden")
            elif e.response.status_code == 429:
                logger.warning("FMP API: Rate limited")
            else:
                logger.error(f"FMP API HTTP error: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"FMP API request error: {e}")
            return None

    def get_house_trades(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Get House trades for a specific stock symbol.

        Args:
            symbol: Stock ticker (e.g., 'WFC', 'JPM')

        Returns:
            List of trade records
        """
        cache_key = f"house_{symbol.upper()}"
        if cache_key in self._cache and self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        data = self._make_request("house-trades", {"symbol": symbol.upper()})
        if data:
            # Normalize the data
            normalized = [self._normalize_trade(t, 'house') for t in data]
            self._cache[cache_key] = normalized
            self._cache_time[cache_key] = datetime.now()
            return normalized
        return []

    def get_senate_trades(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Get Senate trades for a specific stock symbol.

        Args:
            symbol: Stock ticker (e.g., 'WFC', 'JPM')

        Returns:
            List of trade records
        """
        cache_key = f"senate_{symbol.upper()}"
        if cache_key in self._cache and self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        data = self._make_request("senate-trades", {"symbol": symbol.upper()})
        if data:
            normalized = [self._normalize_trade(t, 'senate') for t in data]
            self._cache[cache_key] = normalized
            self._cache_time[cache_key] = datetime.now()
            return normalized
        return []

    def _normalize_trade(self, trade: Dict[str, Any], chamber: str) -> Dict[str, Any]:
        """Normalize FMP trade data to ElectWatch format."""
        # Parse amount range
        amount_str = trade.get('amount', '$0')
        amount_range = self._parse_amount_range(amount_str)

        # Normalize transaction type
        trans_type = trade.get('type', '').lower()
        if 'purchase' in trans_type or 'buy' in trans_type:
            transaction_type = 'purchase'
        elif 'sale' in trans_type or 'sell' in trans_type:
            transaction_type = 'sale'
        elif 'exchange' in trans_type:
            transaction_type = 'exchange'
        else:
            transaction_type = trans_type

        return {
            'politician_name': f"{trade.get('firstName', '')} {trade.get('lastName', '')}".strip(),
            'first_name': trade.get('firstName', ''),
            'last_name': trade.get('lastName', ''),
            'chamber': chamber,
            'district': trade.get('district', ''),
            'ticker': trade.get('symbol', ''),
            'company': trade.get('assetDescription', ''),
            'type': transaction_type,
            'amount_range': amount_str,
            'amount': amount_range,
            'owner': trade.get('owner', ''),  # Self, Spouse, Joint, Dependent
            'transaction_date': trade.get('transactionDate', ''),
            'disclosure_date': trade.get('disclosureDate', ''),
            'filing_url': trade.get('link', ''),
            'capital_gains': trade.get('capitalGainsOver200USD', 'False') == 'True',
            'source': 'fmp',
        }

    def _parse_amount_range(self, amount_str: str) -> Dict[str, Any]:
        """Parse FMP amount string to min/max values."""
        import re

        # Common patterns: "$1,001 - $15,000", "$15,001 - $50,000", "$50,001 - $100,000"
        # Also: "$1,000,001 - $5,000,000", "Over $50,000,000"

        amount_str = amount_str.replace(',', '').replace('$', '')

        if 'over' in amount_str.lower():
            # "Over $50,000,000" -> min=50000000, max=100000000
            match = re.search(r'(\d+)', amount_str)
            if match:
                min_val = int(match.group(1))
                return {'min': min_val, 'max': min_val * 2, 'display': f">${min_val:,}+"}

        # Try to parse range
        match = re.search(r'(\d+)\s*-\s*(\d+)', amount_str)
        if match:
            min_val = int(match.group(1))
            max_val = int(match.group(2))
            return {'min': min_val, 'max': max_val, 'display': f"${min_val:,}-${max_val:,}"}

        # Single number
        match = re.search(r'(\d+)', amount_str)
        if match:
            val = int(match.group(1))
            return {'min': val, 'max': val, 'display': f"${val:,}"}

        return {'min': 0, 'max': 0, 'display': amount_str}

    def get_financial_sector_trades(
        self,
        categories: Optional[List[str]] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all congressional trades in financial sector stocks.

        Args:
            categories: List of categories to include (e.g., ['banking', 'payments'])
                       If None, includes all financial sector categories
            from_date: Filter trades from this date (YYYY-MM-DD)
            to_date: Filter trades to this date (YYYY-MM-DD)

        Returns:
            Dict with 'house' and 'senate' keys containing lists of trades
        """
        if categories:
            symbols = []
            for cat in categories:
                if cat in FINANCIAL_SECTOR_SYMBOLS:
                    symbols.extend(FINANCIAL_SECTOR_SYMBOLS[cat])
            symbols = list(set(symbols))
        else:
            symbols = ALL_FINANCIAL_SYMBOLS

        logger.info(f"Fetching FMP trades for {len(symbols)} financial sector symbols...")

        house_trades = []
        senate_trades = []

        for i, symbol in enumerate(symbols):
            if (i + 1) % 20 == 0:
                logger.info(f"  Progress: {i + 1}/{len(symbols)} symbols...")

            # Get house trades
            trades = self.get_house_trades(symbol)
            if trades:
                house_trades.extend(trades)

            # Get senate trades
            trades = self.get_senate_trades(symbol)
            if trades:
                senate_trades.extend(trades)

        # Filter by date if specified
        if from_date or to_date:
            house_trades = self._filter_by_date(house_trades, from_date, to_date)
            senate_trades = self._filter_by_date(senate_trades, from_date, to_date)

        # Remove duplicates (same trade might appear if politician traded multiple financial stocks)
        house_trades = self._deduplicate_trades(house_trades)
        senate_trades = self._deduplicate_trades(senate_trades)

        logger.info(f"FMP: Found {len(house_trades)} House trades, {len(senate_trades)} Senate trades")

        return {
            'house': house_trades,
            'senate': senate_trades,
        }

    def _filter_by_date(
        self,
        trades: List[Dict],
        from_date: Optional[str],
        to_date: Optional[str]
    ) -> List[Dict]:
        """Filter trades by date range."""
        filtered = []
        for trade in trades:
            trade_date = trade.get('transaction_date', '')
            if from_date and trade_date < from_date:
                continue
            if to_date and trade_date > to_date:
                continue
            filtered.append(trade)
        return filtered

    def _deduplicate_trades(self, trades: List[Dict]) -> List[Dict]:
        """Remove duplicate trades based on key fields."""
        seen = set()
        unique = []
        for trade in trades:
            key = (
                trade.get('politician_name'),
                trade.get('ticker'),
                trade.get('transaction_date'),
                trade.get('type'),
                trade.get('amount_range'),
            )
            if key not in seen:
                seen.add(key)
                unique.append(trade)
        return unique

    def aggregate_by_politician(
        self,
        trades: List[Dict[str, Any]],
        from_date: Optional[str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate trades by politician.

        Returns dict keyed by politician name with:
            - total_trades: Number of trades
            - purchases_min/max: Sum of purchase ranges
            - sales_min/max: Sum of sale ranges
            - symbols: Set of traded symbols
            - latest_trade: Most recent trade date
        """
        politicians = defaultdict(lambda: {
            'trades': [],
            'total_trades': 0,
            'purchases_min': 0,
            'purchases_max': 0,
            'sales_min': 0,
            'sales_max': 0,
            'symbols': set(),
            'latest_trade': '',
            'chamber': '',
        })

        for trade in trades:
            name = trade.get('politician_name', 'Unknown')
            if not name or name == 'Unknown':
                continue

            # Filter by date
            trade_date = trade.get('transaction_date', '')
            if from_date and trade_date < from_date:
                continue

            pol = politicians[name]
            pol['trades'].append(trade)
            pol['total_trades'] += 1
            pol['symbols'].add(trade.get('ticker', ''))
            pol['chamber'] = trade.get('chamber', pol['chamber'])

            # Track latest trade
            if trade_date > pol['latest_trade']:
                pol['latest_trade'] = trade_date

            # Sum amounts by type
            amount = trade.get('amount', {})
            if trade.get('type') == 'purchase':
                pol['purchases_min'] += amount.get('min', 0)
                pol['purchases_max'] += amount.get('max', 0)
            elif trade.get('type') == 'sale':
                pol['sales_min'] += amount.get('min', 0)
                pol['sales_max'] += amount.get('max', 0)

        # Convert symbol sets to lists
        for pol in politicians.values():
            pol['symbols'] = list(pol['symbols'])

        return dict(politicians)

    def test_connection(self) -> bool:
        """Test API connection."""
        if not self.api_key:
            return False
        trades = self.get_house_trades('JPM')
        return trades is not None and len(trades) > 0

    def get_category_for_symbol(self, symbol: str) -> Optional[str]:
        """Get the financial category for a symbol."""
        symbol = symbol.upper()
        for category, symbols in FINANCIAL_SECTOR_SYMBOLS.items():
            if symbol in symbols:
                return category
        return None


# Module-level convenience functions
_client = None

def get_fmp_client() -> FMPClient:
    """Get singleton FMPClient instance."""
    global _client
    if _client is None:
        _client = FMPClient()
    return _client


def get_financial_sector_trades(**kwargs) -> Dict[str, List[Dict]]:
    """Convenience function to get financial sector trades."""
    return get_fmp_client().get_financial_sector_trades(**kwargs)


if __name__ == '__main__':
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(Path(__file__).parent.parent.parent.parent / '.env')

    client = FMPClient()

    if not client.api_key:
        print("ERROR: FMP_API_KEY not set")
    else:
        print("Testing FMP Client for ElectWatch...")
        print("=" * 60)

        # Test connection
        print("\n=== Connection Test ===")
        if client.test_connection():
            print("Connection successful!")
        else:
            print("Connection failed!")

        # Test financial sector trades
        print("\n=== Financial Sector Trades (Banking only) ===")
        trades = client.get_financial_sector_trades(categories=['banking'])
        print(f"House trades: {len(trades['house'])}")
        print(f"Senate trades: {len(trades['senate'])}")

        # Aggregate
        all_trades = trades['house'] + trades['senate']
        aggregated = client.aggregate_by_politician(all_trades)

        print(f"\nTop 10 traders in banking stocks:")
        sorted_pols = sorted(aggregated.items(), key=lambda x: -x[1]['total_trades'])
        for name, data in sorted_pols[:10]:
            total_max = data['purchases_max'] + data['sales_max']
            print(f"  {data['total_trades']:4d} trades, ${total_max:,} max: {name} ({data['chamber']})")
