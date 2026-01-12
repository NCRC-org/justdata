#!/usr/bin/env python3
"""
DuckDuckGo News Search Client for LenderProfile.

Uses DuckDuckGo search to find news articles.
No API key required - uses web scraping approach.
"""

import requests
import logging
import time
from typing import Dict, Any, List, Optional
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)


class DuckDuckGoClient:
    """
    Client for searching news via DuckDuckGo.

    Uses the DuckDuckGo HTML interface to search for news.
    """

    def __init__(self):
        self.base_url = "https://html.duckduckgo.com/html/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Rate limit: 1 request per second

    def _rate_limit(self):
        """Enforce rate limiting."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()

    def search_news(self, query: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Search DuckDuckGo for news articles.

        Args:
            query: Search query (company name)
            max_results: Maximum number of results to return

        Returns:
            List of article dicts with title, url, description, source
        """
        try:
            self._rate_limit()

            # Add "news" to the query to bias towards news results
            search_query = f"{query} news financial"

            params = {
                'q': search_query,
                'kl': 'us-en',  # US English results
            }

            response = requests.post(
                self.base_url,
                data=params,
                headers=self.headers,
                timeout=10
            )

            if response.status_code != 200:
                logger.warning(f"DuckDuckGo returned status {response.status_code}")
                return []

            # Parse HTML response
            articles = self._parse_results(response.text, max_results)

            if articles:
                logger.info(f"DuckDuckGo found {len(articles)} results for '{query}'")
            else:
                logger.info(f"DuckDuckGo found no results for '{query}'")

            return articles

        except Exception as e:
            logger.error(f"DuckDuckGo search failed for '{query}': {e}")
            return []

    def _parse_results(self, html: str, max_results: int) -> List[Dict[str, Any]]:
        """Parse DuckDuckGo HTML results."""
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, 'html.parser')
            results = []

            # Find result links
            for result in soup.find_all('div', class_='result'):
                if len(results) >= max_results:
                    break

                # Get title and URL
                title_elem = result.find('a', class_='result__a')
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                url = title_elem.get('href', '')

                # Get description/snippet
                snippet_elem = result.find('a', class_='result__snippet')
                description = snippet_elem.get_text(strip=True) if snippet_elem else ''

                # Extract source domain from URL
                source = ''
                if url:
                    try:
                        from urllib.parse import urlparse
                        parsed = urlparse(url)
                        source = parsed.netloc.replace('www.', '')
                    except:
                        pass

                if title and url:
                    results.append({
                        'title': title,
                        'url': url,
                        'description': description,
                        'source': {'name': source, 'id': source},
                        'source_type': 'duckduckgo'
                    })

            return results

        except Exception as e:
            logger.error(f"Error parsing DuckDuckGo results: {e}")
            return []
