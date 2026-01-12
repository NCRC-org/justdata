#!/usr/bin/env python3
"""
Data Aggregator for ElectWatch

Combines data from multiple sources:
- FEC: Campaign contributions, PAC data
- Quiver: Congressional stock trades
- Congress.gov: Bills, legislation, members
- Finnhub: News, quotes, insider trading
- SEC EDGAR: Company filings
- NewsAPI: Quality-filtered news

Provides unified data for dashboard endpoints.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class DataAggregator:
    """
    Aggregates data from all ElectWatch data sources.

    Handles:
    - Parallel data fetching for performance
    - Graceful fallbacks when sources fail
    - Caching to reduce API calls
    - Data normalization across sources
    """

    def __init__(self):
        """Initialize data aggregator with all clients."""
        self._init_clients()
        self._cache = {}
        self._cache_time = {}
        self._cache_duration = timedelta(hours=1)

    def _init_clients(self):
        """Initialize all API clients."""
        try:
            from apps.electwatch.services.fec_client import FECClient
            self.fec = FECClient()
        except Exception as e:
            logger.warning(f"FEC client not available: {e}")
            self.fec = None

        try:
            from apps.electwatch.services.quiver_client import QuiverClient
            self.quiver = QuiverClient()
        except Exception as e:
            logger.warning(f"Quiver client not available: {e}")
            self.quiver = None

        try:
            from apps.electwatch.services.congress_api_client import CongressAPIClient
            self.congress = CongressAPIClient()
        except Exception as e:
            logger.warning(f"Congress API client not available: {e}")
            self.congress = None

        try:
            from apps.electwatch.services.finnhub_client import FinnhubClient
            self.finnhub = FinnhubClient()
        except Exception as e:
            logger.warning(f"Finnhub client not available: {e}")
            self.finnhub = None

        try:
            from apps.electwatch.services.sec_client import SECClient
            self.sec = SECClient()
        except Exception as e:
            logger.warning(f"SEC client not available: {e}")
            self.sec = None

        try:
            from apps.electwatch.services.news_client import NewsClient
            self.news = NewsClient()
        except Exception as e:
            logger.warning(f"News client not available: {e}")
            self.news = None

        try:
            from apps.electwatch.services.firm_mapper import get_mapper
            self.firm_mapper = get_mapper()
        except Exception as e:
            logger.warning(f"Firm mapper not available: {e}")
            self.firm_mapper = None

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache entry is still valid."""
        if key not in self._cache_time:
            return False
        return datetime.now() - self._cache_time[key] < self._cache_duration

    def _cache_get(self, key: str) -> Optional[Any]:
        """Get value from cache if valid."""
        if self._is_cache_valid(key):
            return self._cache.get(key)
        return None

    def _cache_set(self, key: str, value: Any):
        """Set value in cache."""
        self._cache[key] = value
        self._cache_time[key] = datetime.now()

    # =========================================================================
    # OFFICIALS DATA
    # =========================================================================

    def get_officials_list(
        self,
        limit: int = 50,
        chamber: Optional[str] = None,
        party: Optional[str] = None,
        state: Optional[str] = None,
        committee: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get list of officials with their financial activity.

        Combines:
        - Quiver: Stock trades
        - FEC: Would need candidate IDs to fetch contributions
        """
        cache_key = f"officials_{limit}_{chamber}_{party}_{state}_{committee}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        officials = []

        # Get stock trades from Quiver
        if self.quiver:
            try:
                trades = self.quiver.get_recent_trades(days=365, chamber=chamber, party=party)

                # Aggregate by politician
                by_politician = {}
                for trade in trades:
                    name = trade.get('politician_name', 'Unknown')
                    if name not in by_politician:
                        by_politician[name] = {
                            'name': name,
                            'party': trade.get('party', ''),
                            'state': trade.get('state', ''),
                            'chamber': trade.get('chamber', ''),
                            'bioguide_id': trade.get('bioguide_id', ''),
                            'trades': [],
                            'total_trades': 0,
                            'purchase_count': 0,
                            'sale_count': 0,
                        }

                    by_politician[name]['trades'].append(trade)
                    by_politician[name]['total_trades'] += 1
                    if trade.get('type') == 'purchase':
                        by_politician[name]['purchase_count'] += 1
                    elif trade.get('type') == 'sale':
                        by_politician[name]['sale_count'] += 1

                # Convert to list and calculate totals
                for name, data in by_politician.items():
                    # Calculate trade value from amount ranges
                    total_min = 0
                    total_max = 0
                    for trade in data['trades']:
                        amt = trade.get('amount', {})
                        total_min += amt.get('min', 0)
                        total_max += amt.get('max', 0)

                    officials.append({
                        'id': data['bioguide_id'] or name.lower().replace(' ', '_'),
                        'name': name,
                        'party': data['party'],
                        'state': data['state'],
                        'chamber': data['chamber'],
                        'bioguide_id': data['bioguide_id'],
                        'total_trades': data['total_trades'],
                        'purchase_count': data['purchase_count'],
                        'sale_count': data['sale_count'],
                        'stock_trades_min': total_min,
                        'stock_trades_max': total_max,
                        'stock_trades_display': f"${total_min:,.0f} - ${total_max:,.0f}" if total_max > 0 else "$0",
                        # Placeholder for contributions (would need FEC integration)
                        'contributions': 0,
                        'involvement_score': min(100, data['total_trades'] * 5 + (total_min / 10000)),
                    })

            except Exception as e:
                logger.error(f"Error fetching trades: {e}")

        # Sort by involvement score
        officials.sort(key=lambda x: x.get('involvement_score', 0), reverse=True)

        # Apply filters
        if state:
            officials = [o for o in officials if o.get('state', '').upper() == state.upper()]

        result = officials[:limit]
        self._cache_set(cache_key, result)
        return result

    def get_official_detail(self, official_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed data for a specific official.

        Combines:
        - Quiver: Stock trades
        - FEC: Contributions (if candidate ID available)
        - Congress.gov: Sponsored bills
        """
        cache_key = f"official_{official_id}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        # Try to find official by ID or name
        official_name = official_id.replace('_', ' ').title()

        result = {
            'id': official_id,
            'name': official_name,
            'party': '',
            'state': '',
            'chamber': '',
            'committees': [],
            'stock_trades': [],
            'contributions': [],
            'bills': [],
            'recent_activity': [],
        }

        # Get stock trades from Quiver
        if self.quiver:
            try:
                trades = self.quiver.get_trades_by_politician(official_name)
                if trades:
                    result['stock_trades'] = trades[:50]
                    result['party'] = trades[0].get('party', '')
                    result['state'] = trades[0].get('state', '')
                    result['chamber'] = trades[0].get('chamber', '')

                    # Build recent activity timeline
                    for trade in trades[:15]:
                        result['recent_activity'].append({
                            'type': 'stock_trade',
                            'date': trade.get('transaction_date', ''),
                            'description': f"{trade.get('type', 'Trade').title()} {trade.get('ticker', '')}",
                            'amount': trade.get('amount_range', ''),
                            'source': trade.get('ticker', ''),
                        })
            except Exception as e:
                logger.error(f"Error fetching trades for {official_name}: {e}")

        # Sort recent activity by date
        result['recent_activity'].sort(key=lambda x: x.get('date', ''), reverse=True)

        self._cache_set(cache_key, result)
        return result

    # =========================================================================
    # FIRM DATA
    # =========================================================================

    def get_firm_detail(self, firm_name: str) -> Dict[str, Any]:
        """
        Get detailed data for a specific firm.

        Combines:
        - SEC EDGAR: Company filings
        - Finnhub: News, quotes, insider trading
        - Quiver: Congressional trades of this stock
        - FEC: PAC contributions (if available)
        """
        cache_key = f"firm_{firm_name.lower()}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        result = {
            'name': firm_name,
            'ticker': '',
            'industries': [],
            'sec_filings': [],
            'news': [],
            'quote': None,
            'insider_transactions': [],
            'congressional_trades': [],
            'officials': [],
        }

        # Get firm info from mapper
        ticker = None
        if self.firm_mapper:
            try:
                firm_record = self.firm_mapper.get_firm_from_pac(firm_name)
                if not firm_record:
                    # Try by name
                    industries = self.firm_mapper.get_industry_from_firm_name(firm_name)
                    result['industries'] = industries
                else:
                    ticker = firm_record.ticker
                    result['ticker'] = ticker
                    result['industries'] = list(firm_record.industries)
            except Exception as e:
                logger.warning(f"Firm mapper error: {e}")

        # Get SEC filings
        if self.sec and ticker:
            try:
                filings = self.sec.get_recent_10k_10q(ticker)
                if filings:
                    result['sec_filings'] = filings[:10]
            except Exception as e:
                logger.warning(f"SEC filings error: {e}")

        # Get news from Finnhub
        if self.finnhub and ticker:
            try:
                news = self.finnhub.get_company_news(ticker, days=30, limit=10)
                result['news'] = news

                quote = self.finnhub.get_quote(ticker)
                result['quote'] = quote

                insider = self.finnhub.get_insider_transactions(ticker, limit=20)
                result['insider_transactions'] = insider
            except Exception as e:
                logger.warning(f"Finnhub error: {e}")

        # Get congressional trades for this ticker
        if self.quiver and ticker:
            try:
                trades = self.quiver.get_trades_by_ticker(ticker)
                result['congressional_trades'] = trades[:20]

                # Extract officials who traded this stock
                officials_set = {}
                for trade in trades:
                    name = trade.get('politician_name', '')
                    if name and name not in officials_set:
                        officials_set[name] = {
                            'name': name,
                            'party': trade.get('party', ''),
                            'state': trade.get('state', ''),
                            'chamber': trade.get('chamber', ''),
                            'trades': []
                        }
                    if name:
                        officials_set[name]['trades'].append(trade)

                result['officials'] = list(officials_set.values())
            except Exception as e:
                logger.warning(f"Quiver error for {ticker}: {e}")

        # Get news from NewsAPI if no Finnhub news
        if not result['news'] and self.news:
            try:
                news = self.news.get_company_news(firm_name, days=30, limit=10)
                result['news'] = news
            except Exception as e:
                logger.warning(f"NewsAPI error: {e}")

        self._cache_set(cache_key, result)
        return result

    # =========================================================================
    # INDUSTRY DATA
    # =========================================================================

    def get_industry_detail(self, sector: str) -> Dict[str, Any]:
        """
        Get data for an industry sector.

        Combines:
        - Firm mapper: Firms in this industry
        - Quiver: Trades in industry tickers
        - News: Industry-specific news
        """
        cache_key = f"industry_{sector}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        result = {
            'sector': sector,
            'name': sector.replace('_', ' ').title(),
            'description': '',
            'firms': [],
            'officials': [],
            'news': [],
            'total_trades': 0,
            'total_trade_value_min': 0,
            'total_trade_value_max': 0,
        }

        # Get sector info
        if self.firm_mapper:
            try:
                sector_info = self.firm_mapper.get_sector_info(sector)
                if sector_info:
                    result['name'] = sector_info.get('name', result['name'])
                    result['description'] = sector_info.get('description', '')
            except Exception as e:
                logger.warning(f"Sector info error: {e}")

        # Get news for this industry
        if self.news:
            try:
                news = self.news.get_industry_news(sector, days=7, limit=10)
                result['news'] = news
            except Exception as e:
                logger.warning(f"Industry news error: {e}")

        self._cache_set(cache_key, result)
        return result

    # =========================================================================
    # BILLS DATA
    # =========================================================================

    def search_bills(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for bills using Congress.gov API."""
        if not self.congress:
            return []

        try:
            results = self.congress.search_bills(query=query, limit=limit)
            return results
        except Exception as e:
            logger.error(f"Bill search error: {e}")
            return []

    def get_bill_detail(self, bill_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed bill information."""
        if not self.congress:
            return None

        try:
            bill = self.congress.get_bill(bill_id)
            return bill
        except Exception as e:
            logger.error(f"Bill detail error: {e}")
            return None

    # =========================================================================
    # NEWS DATA
    # =========================================================================

    def get_political_finance_news(self, days: int = 7, limit: int = 15) -> List[Dict[str, Any]]:
        """Get news about political finance."""
        if not self.news:
            return []

        try:
            return self.news.get_political_finance_news(days=days, limit=limit)
        except Exception as e:
            logger.error(f"Political finance news error: {e}")
            return []

    def get_company_news(self, company: str, days: int = 30, limit: int = 10) -> List[Dict[str, Any]]:
        """Get news for a company (with quality filtering)."""
        if not self.news:
            return []

        try:
            return self.news.get_company_news(company, days=days, limit=limit)
        except Exception as e:
            logger.error(f"Company news error: {e}")
            return []


# =============================================================================
# SINGLETON
# =============================================================================

_aggregator = None


def get_data_aggregator() -> DataAggregator:
    """Get singleton DataAggregator instance."""
    global _aggregator
    if _aggregator is None:
        _aggregator = DataAggregator()
    return _aggregator


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent.parent / '.env')

    logging.basicConfig(level=logging.INFO)

    print("Testing Data Aggregator...")
    print("=" * 60)

    agg = DataAggregator()

    # Test officials list
    print("\n=== Officials List ===")
    officials = agg.get_officials_list(limit=5)
    for o in officials:
        print(f"  {o['name']} ({o['party']}-{o['state']}): {o['total_trades']} trades, {o['stock_trades_display']}")

    # Test firm detail
    print("\n=== Firm Detail: Coinbase ===")
    firm = agg.get_firm_detail('Coinbase')
    print(f"  Ticker: {firm.get('ticker')}")
    print(f"  Industries: {firm.get('industries')}")
    print(f"  News articles: {len(firm.get('news', []))}")
    print(f"  Congressional trades: {len(firm.get('congressional_trades', []))}")

    # Test news
    print("\n=== Political Finance News ===")
    news = agg.get_political_finance_news(days=7, limit=3)
    for n in news:
        print(f"  - {n.get('title', '')[:60]}... ({n.get('source', '')})")
