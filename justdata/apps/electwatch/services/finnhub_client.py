#!/usr/bin/env python3
"""
Finnhub API Client for ElectWatch

Provides access to:
- Company news (working on free tier)
- Stock quotes (working on free tier)
- Insider trading / SEC Form 4 (working on free tier)
- Company profiles (working on free tier)

Note: Congressional trading endpoint requires premium tier ($149+/mo)

Requires FINNHUB_API_KEY environment variable.
"""

import logging
import os
import sys
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports when running directly
if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

logger = logging.getLogger(__name__)


class FinnhubClient:
    """
    Client for Finnhub API - stock data, news, and insider trading.

    Usage:
        client = FinnhubClient()

        # Get company news
        news = client.get_company_news('COIN', days=30)

        # Get stock quote
        quote = client.get_quote('WFC')

        # Get insider transactions (SEC Form 4)
        insider = client.get_insider_transactions('JPM')
    """

    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Finnhub client."""
        self.api_key = api_key or os.getenv('FINNHUB_API_KEY')
        if not self.api_key:
            logger.warning("FINNHUB_API_KEY not set - Finnhub features will be limited")

        self.timeout = 30
        self._cache = {}
        self._cache_time = {}
        self._cache_duration = timedelta(minutes=15)  # 15 min cache for quotes
        self._news_cache_duration = timedelta(hours=1)  # 1 hour for news

    def _is_cache_valid(self, key: str, duration: Optional[timedelta] = None) -> bool:
        """Check if cache is still valid."""
        if key not in self._cache_time:
            return False
        cache_dur = duration or self._cache_duration
        return datetime.now() - self._cache_time[key] < cache_dur

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make authenticated request to Finnhub API."""
        if not self.api_key:
            return None

        url = f"{self.BASE_URL}/{endpoint}"
        params = params or {}
        params['token'] = self.api_key

        try:
            logger.info(f"Finnhub API request: {endpoint}")
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error("Finnhub API: Invalid API key")
            elif e.response.status_code == 403:
                logger.error("Finnhub API: Access forbidden - endpoint may require premium")
            elif e.response.status_code == 429:
                logger.warning("Finnhub API: Rate limited")
            else:
                logger.error(f"Finnhub API HTTP error: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Finnhub API request error: {e}")
            return None

    def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get real-time stock quote.

        Args:
            symbol: Stock ticker (e.g., 'COIN', 'WFC')

        Returns:
            Dict with current_price, high, low, open, prev_close, change, change_percent
        """
        cache_key = f"quote_{symbol.upper()}"
        if cache_key in self._cache and self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        data = self._make_request("quote", {"symbol": symbol.upper()})
        if not data or not data.get('c'):
            return None

        result = {
            'symbol': symbol.upper(),
            'current_price': data.get('c'),
            'high': data.get('h'),
            'low': data.get('l'),
            'open': data.get('o'),
            'prev_close': data.get('pc'),
            'change': data.get('d'),
            'change_percent': data.get('dp'),
            'timestamp': datetime.now().isoformat()
        }

        self._cache[cache_key] = result
        self._cache_time[cache_key] = datetime.now()
        return result

    def get_company_news(
        self,
        symbol: str,
        days: int = 30,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get recent news for a company.

        Args:
            symbol: Stock ticker
            days: Number of days to look back
            limit: Maximum articles to return

        Returns:
            List of news articles with headline, source, url, datetime, summary
        """
        cache_key = f"news_{symbol.upper()}_{days}"
        if cache_key in self._cache and self._is_cache_valid(cache_key, self._news_cache_duration):
            return self._cache[cache_key][:limit]

        from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        to_date = datetime.now().strftime('%Y-%m-%d')

        data = self._make_request("company-news", {
            "symbol": symbol.upper(),
            "from": from_date,
            "to": to_date
        })

        if not data:
            return []

        results = []
        for article in data[:limit]:
            results.append({
                'headline': article.get('headline', ''),
                'source': article.get('source', ''),
                'url': article.get('url', ''),
                'datetime': datetime.fromtimestamp(article.get('datetime', 0)).isoformat() if article.get('datetime') else '',
                'summary': article.get('summary', ''),
                'image': article.get('image', ''),
                'category': article.get('category', ''),
                'related': article.get('related', '')
            })

        self._cache[cache_key] = results
        self._cache_time[cache_key] = datetime.now()
        return results

    def get_insider_transactions(
        self,
        symbol: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get insider transactions (SEC Form 4 filings).

        Args:
            symbol: Stock ticker
            limit: Maximum transactions to return

        Returns:
            List of insider transactions with name, share, change, filing_date, transaction_date
        """
        cache_key = f"insider_{symbol.upper()}"
        if cache_key in self._cache and self._is_cache_valid(cache_key, self._news_cache_duration):
            return self._cache[cache_key][:limit]

        data = self._make_request("stock/insider-transactions", {"symbol": symbol.upper()})

        if not data or not data.get('data'):
            return []

        results = []
        for txn in data['data'][:limit]:
            results.append({
                'name': txn.get('name', ''),
                'share': txn.get('share', 0),
                'change': txn.get('change', 0),
                'filing_date': txn.get('filingDate', ''),
                'transaction_date': txn.get('transactionDate', ''),
                'transaction_code': txn.get('transactionCode', ''),
                'transaction_price': txn.get('transactionPrice', 0),
                'symbol': symbol.upper()
            })

        self._cache[cache_key] = results
        self._cache_time[cache_key] = datetime.now()
        return results

    def get_company_profile(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get company profile information.

        Args:
            symbol: Stock ticker

        Returns:
            Dict with company name, industry, sector, market cap, etc.
        """
        cache_key = f"profile_{symbol.upper()}"
        if cache_key in self._cache and self._is_cache_valid(cache_key, timedelta(hours=24)):
            return self._cache[cache_key]

        data = self._make_request("stock/profile2", {"symbol": symbol.upper()})

        if not data or not data.get('name'):
            return None

        result = {
            'symbol': symbol.upper(),
            'name': data.get('name', ''),
            'country': data.get('country', ''),
            'currency': data.get('currency', ''),
            'exchange': data.get('exchange', ''),
            'industry': data.get('finnhubIndustry', ''),
            'ipo_date': data.get('ipo', ''),
            'logo': data.get('logo', ''),
            'market_cap': data.get('marketCapitalization', 0),
            'shares_outstanding': data.get('shareOutstanding', 0),
            'website': data.get('weburl', ''),
            'phone': data.get('phone', '')
        }

        self._cache[cache_key] = result
        self._cache_time[cache_key] = datetime.now()
        return result

    def get_market_news(self, category: str = 'general', limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get general market news.

        Args:
            category: 'general', 'forex', 'crypto', or 'merger'
            limit: Maximum articles to return

        Returns:
            List of news articles
        """
        cache_key = f"market_news_{category}"
        if cache_key in self._cache and self._is_cache_valid(cache_key, self._news_cache_duration):
            return self._cache[cache_key][:limit]

        data = self._make_request("news", {"category": category})

        if not data:
            return []

        results = []
        for article in data[:limit]:
            results.append({
                'headline': article.get('headline', ''),
                'source': article.get('source', ''),
                'url': article.get('url', ''),
                'datetime': datetime.fromtimestamp(article.get('datetime', 0)).isoformat() if article.get('datetime') else '',
                'summary': article.get('summary', ''),
                'image': article.get('image', ''),
                'category': category
            })

        self._cache[cache_key] = results
        self._cache_time[cache_key] = datetime.now()
        return results

    def test_connection(self) -> bool:
        """Test API connection."""
        if not self.api_key:
            return False
        result = self.get_quote('AAPL')
        return result is not None


# =============================================================================
# MODULE-LEVEL CONVENIENCE FUNCTIONS
# =============================================================================

_client = None


def get_finnhub_client() -> FinnhubClient:
    """Get singleton FinnhubClient instance."""
    global _client
    if _client is None:
        _client = FinnhubClient()
    return _client


def get_company_news(symbol: str, **kwargs) -> List[Dict]:
    """Convenience function to get company news."""
    return get_finnhub_client().get_company_news(symbol, **kwargs)


def get_quote(symbol: str) -> Optional[Dict]:
    """Convenience function to get stock quote."""
    return get_finnhub_client().get_quote(symbol)


def get_insider_transactions(symbol: str, **kwargs) -> List[Dict]:
    """Convenience function to get insider transactions."""
    return get_finnhub_client().get_insider_transactions(symbol, **kwargs)


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(Path(__file__).parent.parent.parent.parent / '.env')

    client = FinnhubClient()

    if not client.api_key:
        print("ERROR: FINNHUB_API_KEY not set")
    else:
        print("Testing Finnhub Client for ElectWatch...")
        print("=" * 50)

        # Test quote
        print("\n=== Stock Quote ===")
        quote = client.get_quote('COIN')
        if quote:
            print(f"COIN: ${quote['current_price']:.2f} ({quote['change_percent']:+.2f}%)")

        # Test news
        print("\n=== Company News ===")
        news = client.get_company_news('WFC', days=7, limit=3)
        for article in news:
            print(f"  - {article['headline'][:60]}... ({article['source']})")

        # Test insider trading
        print("\n=== Insider Transactions ===")
        insider = client.get_insider_transactions('JPM', limit=5)
        for txn in insider:
            print(f"  - {txn['name']}: {txn['change']:+,} shares on {txn['filing_date']}")

        # Test profile
        print("\n=== Company Profile ===")
        profile = client.get_company_profile('COIN')
        if profile:
            print(f"  {profile['name']} ({profile['symbol']})")
            print(f"  Industry: {profile['industry']}")
            print(f"  Market Cap: ${profile['market_cap']:,.0f}M")
