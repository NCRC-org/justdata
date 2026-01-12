#!/usr/bin/env python3
"""
Google Custom Search News Client
Fetches news articles from reputable sources using Google Custom Search API.

This provides higher quality results than NewsAPI by:
1. Using Google's search ranking algorithms
2. Restricting searches to reputable financial news sites
3. Better relevance matching for company names
"""

import requests
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from justdata.shared.utils.unified_env import get_unified_config

logger = logging.getLogger(__name__)

# Reputable financial and business news sources for site-restricted search
REPUTABLE_NEWS_SITES = [
    # Major financial news outlets
    'wsj.com',
    'bloomberg.com',
    'reuters.com',
    'ft.com',
    'cnbc.com',
    'marketwatch.com',

    # General news (business sections)
    'nytimes.com',
    'washingtonpost.com',
    'apnews.com',

    # Banking and mortgage industry publications
    'americanbanker.com',
    'bankingdive.com',
    'housingwire.com',
    'nationalmortgagenews.com',

    # Business and finance publications
    'fortune.com',
    'forbes.com',
    'barrons.com',
]


class GoogleNewsClient:
    """
    Client for Google Custom Search API to fetch news articles.

    Uses Google's Programmable Search Engine (formerly Custom Search Engine)
    to search only reputable news sources.

    API Documentation: https://developers.google.com/custom-search/v1/overview
    Pricing: 100 queries/day free, then $5 per 1000 queries
    """

    BASE_URL = 'https://www.googleapis.com/customsearch/v1'

    def __init__(self, api_key: Optional[str] = None, search_engine_id: Optional[str] = None):
        """
        Initialize Google Custom Search client.

        Args:
            api_key: Google API key (or from unified_env if not provided)
            search_engine_id: Custom Search Engine ID (or from unified_env)
        """
        self.timeout = 30

        if not api_key or not search_engine_id:
            config = get_unified_config(load_env=True, verbose=False)
            api_key = api_key or config.get('GOOGLE_CUSTOM_SEARCH_API_KEY')
            search_engine_id = search_engine_id or config.get('GOOGLE_CUSTOM_SEARCH_ENGINE_ID')

        self.api_key = api_key
        self.search_engine_id = search_engine_id

        if not self.api_key:
            logger.warning("Google Custom Search API key not set")
        if not self.search_engine_id:
            logger.warning("Google Custom Search Engine ID not set")

    def search_news(
        self,
        query: str,
        num_results: int = 10,
        date_restrict: str = 'm1',
        sites: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Search for news articles about a company.

        Args:
            query: Search query (company name)
            num_results: Number of results (max 10 per request)
            date_restrict: Date restriction (d1=1 day, w1=1 week, m1=1 month, y1=1 year)
            sites: List of sites to search (defaults to REPUTABLE_NEWS_SITES)

        Returns:
            Dictionary with 'articles' list and 'totalResults'
        """
        if not self.api_key or not self.search_engine_id:
            logger.warning("Google Custom Search not configured, skipping search")
            return {'articles': [], 'totalResults': 0, 'source': 'google_custom_search'}

        # Use reputable sites by default
        if sites is None:
            sites = REPUTABLE_NEWS_SITES

        # Build site-restricted query
        # Format: "JPMorgan Chase" site:wsj.com OR site:bloomberg.com OR ...
        site_restrictions = ' OR '.join([f'site:{site}' for site in sites[:10]])  # Limit to 10 sites per query
        full_query = f'"{query}" ({site_restrictions})'

        try:
            params = {
                'key': self.api_key,
                'cx': self.search_engine_id,
                'q': full_query,
                'num': min(num_results, 10),  # Max 10 per request
                'dateRestrict': date_restrict,
                'sort': 'date',  # Most recent first
            }

            logger.info(f"Google Custom Search: Searching for '{query}' across {len(sites)} sites")
            response = requests.get(self.BASE_URL, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()

            # Parse results into article format
            articles = []
            for item in data.get('items', []):
                # Extract source domain from URL
                url = item.get('link', '')
                source = self._extract_domain(url)

                articles.append({
                    'title': item.get('title', ''),
                    'description': item.get('snippet', ''),
                    'url': url,
                    'source': {'name': source},
                    'publishedAt': item.get('pagemap', {}).get('metatags', [{}])[0].get('article:published_time', ''),
                    'content': item.get('snippet', ''),
                })

            total_results = int(data.get('searchInformation', {}).get('totalResults', 0))

            logger.info(f"Google Custom Search: Found {len(articles)} articles (total: {total_results})")

            return {
                'articles': articles,
                'totalResults': total_results,
                'source': 'google_custom_search'
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Google Custom Search error: {e}")
            return {'articles': [], 'totalResults': 0, 'source': 'google_custom_search', 'error': str(e)}

    def search_news_extended(
        self,
        query: str,
        num_results: int = 20,
        date_restrict: str = 'm3'
    ) -> Dict[str, Any]:
        """
        Extended search that queries multiple site groups to get more results.

        Since Google CSE limits to 10 results per query, this method:
        1. Queries major financial news (wsj, bloomberg, reuters, ft)
        2. Queries banking industry publications
        3. Queries general business news
        4. Combines and deduplicates results

        Args:
            query: Search query (company name)
            num_results: Target number of results
            date_restrict: Date restriction

        Returns:
            Dictionary with 'articles' list and 'totalResults'
        """
        if not self.api_key or not self.search_engine_id:
            return {'articles': [], 'totalResults': 0, 'source': 'google_custom_search'}

        # Define site groups
        site_groups = [
            # Major financial news
            ['wsj.com', 'bloomberg.com', 'reuters.com', 'ft.com', 'cnbc.com'],
            # Banking industry
            ['americanbanker.com', 'bankingdive.com', 'housingwire.com', 'nationalmortgagenews.com'],
            # General business
            ['nytimes.com', 'washingtonpost.com', 'fortune.com', 'forbes.com'],
        ]

        all_articles = []
        seen_urls = set()

        for sites in site_groups:
            result = self.search_news(
                query=query,
                num_results=10,
                date_restrict=date_restrict,
                sites=sites
            )

            for article in result.get('articles', []):
                url = article.get('url', '')
                if url and url not in seen_urls:
                    all_articles.append(article)
                    seen_urls.add(url)

            # Stop if we have enough articles
            if len(all_articles) >= num_results:
                break

        # Sort by date (most recent first) if we have dates
        all_articles.sort(
            key=lambda x: x.get('publishedAt', ''),
            reverse=True
        )

        return {
            'articles': all_articles[:num_results],
            'totalResults': len(all_articles),
            'source': 'google_custom_search'
        }

    def _extract_domain(self, url: str) -> str:
        """Extract domain name from URL for source attribution."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc
            # Remove www. prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except Exception:
            return 'Unknown'


def test_google_news_client():
    """Test the Google News client."""
    client = GoogleNewsClient()

    if not client.api_key or not client.search_engine_id:
        print("ERROR: Google Custom Search not configured")
        print("Set GOOGLE_CUSTOM_SEARCH_API_KEY and GOOGLE_CUSTOM_SEARCH_ENGINE_ID in .env")
        return

    print("Testing Google Custom Search News Client...")
    print("=" * 50)

    for company in ['JPMorgan Chase', 'Bank of America', 'Wells Fargo']:
        print(f"\n{company}:")
        result = client.search_news(company, num_results=5, date_restrict='m1')

        print(f"  Total Results: {result.get('totalResults')}")
        print(f"  Articles Found: {len(result.get('articles', []))}")

        for article in result.get('articles', [])[:3]:
            print(f"    - {article.get('title', '')[:60]}...")
            print(f"      Source: {article.get('source', {}).get('name', 'Unknown')}")
            print()


if __name__ == '__main__':
    test_google_news_client()
