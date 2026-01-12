#!/usr/bin/env python3
"""
NewsAPI Client
Fetches news articles and coverage from reputable sources only.
"""

import requests
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from justdata.shared.utils.unified_env import get_unified_config

logger = logging.getLogger(__name__)

# Reputable financial and business news sources
# These are filtered to exclude low-quality aggregators and clickbait sites
REPUTABLE_NEWS_DOMAINS = [
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
    'bbc.com',

    # Banking and mortgage industry publications
    'americanbanker.com',
    'bankingdive.com',
    'housingwire.com',
    'nationalmortgagenews.com',
    'mortgagenewsdaily.com',

    # Business and finance publications
    'businessinsider.com',
    'fortune.com',
    'forbes.com',
    'barrons.com',
    'thestreet.com',

    # Wire services
    'prnewswire.com',
    'businesswire.com',
]


class NewsAPIClient:
    """
    Client for NewsAPI.
    
    Base URL: https://newsapi.org/v2/
    Authentication: API key as query parameter or header
    Rate Limit: 100 requests/day (free tier)
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize NewsAPI client.
        
        Args:
            api_key: API key (or from unified_env if not provided)
        """
        self.base_url = 'https://newsapi.org/v2'
        self.timeout = 30
        
        if not api_key:
            config = get_unified_config(load_env=True, verbose=False)
            api_key = config.get('NEWSAPI_API_KEY')
        
        self.api_key = api_key
        if not self.api_key:
            logger.warning("NewsAPI key not set, skipping search")
    
    def _get_params(self) -> Dict[str, str]:
        """Get request parameters with API key."""
        params = {}
        if self.api_key:
            params['apiKey'] = self.api_key
        return params
    
    def search_everything(self, query: str, language: str = 'en',
                         sort_by: str = 'relevancy', page_size: int = 100,
                         from_date: Optional[str] = None,
                         to_date: Optional[str] = None,
                         domains: Optional[List[str]] = None,
                         use_exact_phrase: bool = True,
                         use_reputable_sources: bool = True) -> Dict[str, Any]:
        """
        Search all articles (last 30 days on free tier).

        By default, filters to reputable financial news sources only.

        Tries multiple search strategies:
        1. Exact phrase match (if use_exact_phrase=True)
        2. Full company name
        3. Original query

        Args:
            query: Search query (company name)
            language: Language code (default: 'en')
            sort_by: Sort order ('relevancy', 'popularity', 'publishedAt')
            page_size: Number of results (max 100)
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            domains: Filter by domains (overrides reputable sources if provided)
            use_exact_phrase: If True, try exact phrase match first
            use_reputable_sources: If True, filter to REPUTABLE_NEWS_DOMAINS (default: True)

        Returns:
            Dictionary with 'articles' list and 'totalResults'
        """
        if not self.api_key:
            logger.warning("NewsAPI key not set, skipping search")
            return {'articles': [], 'totalResults': 0}

        # Use reputable sources by default unless specific domains are provided
        if domains is None and use_reputable_sources:
            domains = REPUTABLE_NEWS_DOMAINS
            logger.info(f"NewsAPI: Filtering to {len(domains)} reputable news sources")

        # Build query variations for better results
        query_variations = []

        if use_exact_phrase:
            # Try exact phrase match first (most relevant)
            query_variations.append(f'"{query}"')

        # Try full company name variations
        if 'Bank' in query:
            # Replace " Bank" with " Financial Services"
            financial_services_name = query.replace(' Bank', ' Financial Services')
            query_variations.append(f'"{financial_services_name}"')
            query_variations.append(f'"{query} Financial Services"')

        # Add original query as fallback
        if query not in query_variations:
            query_variations.append(query)

        # Remove duplicates while preserving order
        seen = set()
        query_variations = [q for q in query_variations if q not in seen and not seen.add(q)]

        for search_query in query_variations:
            try:
                url = f'{self.base_url}/everything'
                params = self._get_params()
                params.update({
                    'q': search_query,
                    'language': language,
                    'sortBy': sort_by,
                    'pageSize': min(page_size, 100)
                })

                if from_date:
                    params['from'] = from_date
                if to_date:
                    params['to'] = to_date
                if domains:
                    params['domains'] = ','.join(domains)
                
                logger.debug(f"NewsAPI search: {url} with query '{search_query}'")
                response = requests.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                
                data = response.json()
                articles = data.get('articles', [])
                total = data.get('totalResults', 0)
                
                # If we got results and they seem relevant, return them
                if articles and total > 0:
                    # Check if first article is relevant (contains company name keywords)
                    first_title = articles[0].get('title', '').lower()
                    query_keywords = [w.lower() for w in query.split() if len(w) > 3]  # Words longer than 3 chars
                    if any(keyword in first_title for keyword in query_keywords):
                        logger.info(f"NewsAPI found {total} relevant results with query '{search_query}'")
                        return data
                    elif search_query == query_variations[-1]:  # Last variation, return anyway
                        logger.info(f"NewsAPI found {total} results with query '{search_query}' (relevance uncertain)")
                        return data
                elif search_query == query_variations[-1]:  # Last variation, return anyway
                    return data
                
            except requests.exceptions.RequestException as e:
                logger.debug(f"NewsAPI error with query '{search_query}': {e}")
                continue
        
        # If all queries failed, return empty result
        logger.warning(f"NewsAPI: All query variations failed for '{query}'")
        return {'articles': [], 'totalResults': 0}
    
    def get_top_headlines(self, query: Optional[str] = None,
                         country: str = 'us', category: Optional[str] = None,
                         page_size: int = 100) -> Dict[str, Any]:
        """
        Get top headlines.
        
        Args:
            query: Search query
            country: Country code (default: 'us')
            category: News category
            page_size: Number of results
            
        Returns:
            Dictionary with 'articles' list
        """
        if not self.api_key:
            logger.warning("NewsAPI key not set, skipping request")
            return {'articles': [], 'totalResults': 0}
        
        try:
            url = f'{self.base_url}/top-headlines'
            params = self._get_params()
            params.update({
                'country': country,
                'pageSize': min(page_size, 100)
            })
            
            if query:
                params['q'] = query
            if category:
                params['category'] = category
            
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"NewsAPI error getting headlines: {e}")
            return {'articles': [], 'totalResults': 0}

