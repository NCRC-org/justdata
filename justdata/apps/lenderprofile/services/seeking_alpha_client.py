#!/usr/bin/env python3
"""
Seeking Alpha API Client
Fetches financial data, earnings, and news for companies.

Documentation: https://rapidapi.com/apidojo/api/seeking-alpha
Base URL: https://seeking-alpha.p.rapidapi.com
Authentication: RapidAPI key in x-rapidapi-key header
"""

import requests
import logging
from typing import Optional, Dict, Any, List
from justdata.shared.utils.unified_env import get_unified_config

logger = logging.getLogger(__name__)


class SeekingAlphaClient:
    """
    Client for Seeking Alpha API via RapidAPI.
    
    Note: This API uses ticker symbols (e.g., 'PNC') not company names.
    You may need to resolve company name to ticker symbol first.
    """
    
    def __init__(self, api_key: Optional[str] = None, use_alternative_api: bool = False):
        """
        Initialize Seeking Alpha API client.
        
        Args:
            api_key: RapidAPI key (or from unified_env if not provided)
            use_alternative_api: If True, use seeking-alpha-api.p.rapidapi.com (has articles/leading-story)
        """
        # Two different API providers on RapidAPI:
        # 1. seeking-alpha.p.rapidapi.com - Financial data, earnings, ratings (current default)
        # 2. seeking-alpha-api.p.rapidapi.com - Has articles, leading-story, news (requires subscription)
        if use_alternative_api:
            self.base_url = 'https://seeking-alpha-api.p.rapidapi.com'
            self.api_host = 'seeking-alpha-api.p.rapidapi.com'
        else:
            self.base_url = 'https://seeking-alpha.p.rapidapi.com'
            self.api_host = 'seeking-alpha.p.rapidapi.com'
        
        self.use_alternative_api = use_alternative_api
        self.timeout = 30
        
        if not api_key:
            config = get_unified_config(load_env=True, verbose=False)
            api_key = config.get('SEEKING_ALPHA_API_KEY')
        
        self.api_key = api_key
        if not self.api_key:
            logger.warning("Seeking Alpha API key not set, skipping requests")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with RapidAPI authentication."""
        return {
            'x-rapidapi-host': self.api_host,
            'x-rapidapi-key': self.api_key
        } if self.api_key else {}
    
    def get_financials(self, ticker: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get financial data for a ticker symbol.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'PNC', 'BAC', 'JPM')
            
        Returns:
            List of financial data sections or None
        """
        if not self.api_key:
            logger.warning("Seeking Alpha API key not set, skipping request")
            return None
        
        try:
            url = f'{self.base_url}/symbols/get-financials'
            params = {'symbol': ticker.upper()}
            
            logger.info(f"Seeking Alpha API request: {url} with symbol {ticker}")
            response = requests.get(url, params=params, headers=self._get_headers(), timeout=self.timeout)
            logger.info(f"Seeking Alpha API response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    logger.info(f"Seeking Alpha returned {len(data)} financial sections for {ticker}")
                    return data
                return None
            elif response.status_code == 204:
                logger.info(f"No financial data found for ticker {ticker}")
                return None
            else:
                response.raise_for_status()
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Seeking Alpha API error getting financials for {ticker}: {e}")
            return None
    
    def get_earnings(self, ticker_ids: List[int], period_type: str = 'quarterly',
                    relative_periods: Optional[List[int]] = None,
                    estimates_data_items: Optional[List[str]] = None,
                    revisions_data_items: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """
        Get earnings data for ticker IDs.
        
        Note: Requires ticker_id (numeric), not ticker symbol.
        You may need to look up ticker_id from ticker symbol first.
        
        Args:
            ticker_ids: List of ticker IDs (e.g., [1742])
            period_type: 'quarterly' or 'annual'
            relative_periods: List of relative periods (e.g., [-3, -2, -1, 0, 1, 2, 3])
            estimates_data_items: List of data items to retrieve
            revisions_data_items: List of revision data items
            
        Returns:
            Earnings data dictionary or None
        """
        if not self.api_key:
            logger.warning("Seeking Alpha API key not set, skipping request")
            return None
        
        try:
            url = f'{self.base_url}/symbols/get-earnings'
            params = {
                'ticker_ids': ','.join(str(tid) for tid in ticker_ids),
                'period_type': period_type
            }
            
            if relative_periods:
                params['relative_periods'] = ','.join(str(p) for p in relative_periods)
            if estimates_data_items:
                params['estimates_data_items'] = ','.join(estimates_data_items)
            if revisions_data_items:
                params['revisions_data_items'] = ','.join(revisions_data_items)
            
            logger.info(f"Seeking Alpha API request: {url} with ticker_ids {ticker_ids}")
            response = requests.get(url, params=params, headers=self._get_headers(), timeout=self.timeout)
            logger.info(f"Seeking Alpha API response status: {response.status_code}")
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Seeking Alpha API error getting earnings: {e}")
            return None
    
    def get_profile(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get company profile for a ticker symbol.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Profile data or None
        """
        if not self.api_key:
            logger.warning("Seeking Alpha API key not set, skipping request")
            return None
        
        try:
            url = f'{self.base_url}/symbols/get-profile'
            params = {'symbol': ticker.upper()}
            
            response = requests.get(url, params=params, headers=self._get_headers(), timeout=self.timeout)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 204:
                logger.debug(f"No profile found for ticker {ticker}")
                return None
            else:
                response.raise_for_status()
                return None
                
        except requests.exceptions.RequestException as e:
            logger.debug(f"Seeking Alpha API error getting profile for {ticker}: {e}")
            return None
    
    def get_ratings(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get stock ratings and analyst recommendations for a ticker symbol.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'FITB', 'PNC')
            
        Returns:
            Ratings data dictionary or None
        """
        if not self.api_key:
            logger.warning("Seeking Alpha API key not set, skipping request")
            return None
        
        try:
            url = f'{self.base_url}/symbols/get-ratings'
            params = {'symbol': ticker.upper()}
            
            logger.info(f"Seeking Alpha API request: {url} with symbol {ticker}")
            response = requests.get(url, params=params, headers=self._get_headers(), timeout=self.timeout)
            logger.info(f"Seeking Alpha API response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Seeking Alpha returned ratings data for {ticker}")
                return data
            elif response.status_code == 204:
                logger.debug(f"No ratings found for ticker {ticker}")
                return None
            else:
                response.raise_for_status()
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Seeking Alpha API error getting ratings for {ticker}: {e}")
            return None
    
    def search_by_ticker(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive data for a ticker symbol.
        Combines profile, financials, ratings, and other available data.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'PNC')
            
        Returns:
            Combined data dictionary or None
        """
        if not self.api_key:
            logger.warning("Seeking Alpha API key not set, skipping request")
            return None
        
        result = {
            'ticker': ticker.upper(),
            'profile': None,
            'financials': None,
            'ratings': None,
            'earnings': None,
            'leading_story': None,
            'analysis_articles': None  # Ticker-specific analysis articles
        }

        # Get profile
        result['profile'] = self.get_profile(ticker)

        # Get financials
        result['financials'] = self.get_financials(ticker)

        # Get ratings (analyst recommendations, quant ratings, etc.)
        result['ratings'] = self.get_ratings(ticker)

        # Get leading story (auto-uses alternative API)
        result['leading_story'] = self.get_leading_story(ticker)

        # Get ticker-specific analysis articles (these are about this specific company)
        result['analysis_articles'] = self.get_analysis_articles(ticker, limit=10)

        return result if any([result['profile'], result['financials'], result['ratings'], result['leading_story'], result['analysis_articles']]) else None
    
    def get_leading_story(self, symbol: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get leading story/article for a symbol.
        
        This endpoint is available at: https://rapidapi.com/belchiorarkad-FqvHs2EDOtP/api/seeking-alpha-api
        
        Note: Requires subscription to the alternative API provider
        (seeking-alpha-api.p.rapidapi.com). The same RapidAPI key works, but you
        must subscribe to this specific API on RapidAPI.
        
        Args:
            symbol: Optional ticker symbol (e.g., 'FITB')
            
        Returns:
            Leading story data or None
        """
        if not self.api_key:
            logger.warning("Seeking Alpha API key not set, skipping request")
            return None
        
        # Auto-detect if we should use alternative API for this endpoint
        # (leading-story only exists in alternative API)
        original_use_alt = self.use_alternative_api
        if not self.use_alternative_api:
            # Temporarily switch to alternative API for this call
            self.base_url = 'https://seeking-alpha-api.p.rapidapi.com'
            self.api_host = 'seeking-alpha-api.p.rapidapi.com'
        
        try:
            url = f'{self.base_url}/leading-story'
            params = {}
            if symbol:
                params['symbol'] = symbol.upper()
            
            logger.info(f"Seeking Alpha API request: {url} with params {params}")
            response = requests.get(url, params=params, headers=self._get_headers(), timeout=self.timeout)
            logger.info(f"Seeking Alpha API response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Seeking Alpha returned {len(data.get('leading_news_story', []))} leading stories for {symbol or 'general'}")
                return data
            elif response.status_code == 403:
                logger.warning("Not subscribed to Seeking Alpha alternative API (leading-story endpoint). Subscribe at: https://rapidapi.com/belchiorarkad-FqvHs2EDOtP/api/seeking-alpha-api")
                return None
            elif response.status_code == 204:
                logger.debug(f"No leading story found for {symbol or 'general'}")
                return None
            else:
                response.raise_for_status()
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Seeking Alpha API error getting leading story: {e}")
            return None
        finally:
            # Restore original API setting
            if not original_use_alt:
                self.base_url = 'https://seeking-alpha.p.rapidapi.com'
                self.api_host = 'seeking-alpha.p.rapidapi.com'

    def get_news(self, ticker: str, limit: int = 10) -> Optional[List[Dict[str, Any]]]:
        """
        Get news articles for a ticker symbol.

        Uses the primary Seeking Alpha API (seeking-alpha.p.rapidapi.com)
        /news/v2/list endpoint which returns ticker-specific news.

        Args:
            ticker: Stock ticker symbol (e.g., 'FITB', 'PNC', 'JPM')
            limit: Maximum number of articles to return

        Returns:
            List of news articles with headline, summary, date, and URL, or None
        """
        if not self.api_key:
            logger.warning("Seeking Alpha API key not set, skipping request")
            return None

        try:
            # Use primary API - news/v2/list endpoint works with ticker as 'id'
            url = 'https://seeking-alpha.p.rapidapi.com/news/v2/list'
            params = {
                'id': ticker.upper(),
                'size': str(limit),
                'number': '1'
            }
            headers = {
                'x-rapidapi-host': 'seeking-alpha.p.rapidapi.com',
                'x-rapidapi-key': self.api_key
            }

            logger.info(f"Seeking Alpha news request: {url} for {ticker}")
            response = requests.get(url, params=params, headers=headers, timeout=self.timeout)
            logger.info(f"Seeking Alpha news response: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                articles = []

                # Parse response structure: {data: [{id, type, attributes: {title, publishOn, ...}}]}
                news_items = data.get('data', [])
                for item in news_items[:limit]:
                    attrs = item.get('attributes', {})
                    # Build URL from URI if available
                    uri = attrs.get('uri', '')
                    article_url = f"https://seekingalpha.com{uri}" if uri else ''

                    article = {
                        'headline': attrs.get('title', ''),
                        'summary': (attrs.get('content', '') or '')[:300],
                        'date': attrs.get('publishOn', attrs.get('lastModified', '')),
                        'url': article_url,
                        'source': 'Seeking Alpha'
                    }
                    if article['headline']:
                        articles.append(article)

                if articles:
                    logger.info(f"Found {len(articles)} news articles for {ticker}")
                    return articles

            elif response.status_code == 403:
                logger.warning("Not subscribed to Seeking Alpha news API")

        except requests.exceptions.RequestException as e:
            logger.error(f"Seeking Alpha news API error: {e}")

        logger.info(f"No news articles found for {ticker}")
        return None

    def get_analysis_articles(self, ticker: str, limit: int = 10) -> Optional[List[Dict[str, Any]]]:
        """
        Get analysis articles specifically about a ticker symbol.

        Uses the primary Seeking Alpha API /analysis/v2/list endpoint
        which returns ticker-specific analysis articles (not general market news).

        Args:
            ticker: Stock ticker symbol (e.g., 'JPM', 'PNC')
            limit: Maximum number of articles to return

        Returns:
            List of analysis articles with headline, date, and URL, or None
        """
        if not self.api_key:
            logger.warning("Seeking Alpha API key not set, skipping request")
            return None

        try:
            url = 'https://seeking-alpha.p.rapidapi.com/analysis/v2/list'
            params = {
                'id': ticker.upper(),
                'size': str(limit),
                'number': '1'
            }
            headers = {
                'x-rapidapi-host': 'seeking-alpha.p.rapidapi.com',
                'x-rapidapi-key': self.api_key
            }

            logger.info(f"Seeking Alpha analysis request: {url} for {ticker}")
            response = requests.get(url, params=params, headers=headers, timeout=self.timeout)
            logger.info(f"Seeking Alpha analysis response: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                articles = []

                # Parse response: {data: [{id, type, attributes, links}]}
                items = data.get('data', [])
                for item in items[:limit]:
                    attrs = item.get('attributes', {})
                    links = item.get('links', {})
                    # Build full URL from links.self
                    uri = links.get('self', '')
                    article_url = f"https://seekingalpha.com{uri}" if uri else ''

                    article = {
                        'headline': attrs.get('title', ''),
                        'summary': '',  # Analysis articles don't have summary in this endpoint
                        'date': attrs.get('publishOn', ''),
                        'url': article_url,
                        'source': 'Seeking Alpha',
                        'type': 'analysis'
                    }
                    if article['headline']:
                        articles.append(article)

                if articles:
                    logger.info(f"Found {len(articles)} analysis articles for {ticker}")
                    return articles

            elif response.status_code == 403:
                logger.warning("Not subscribed to Seeking Alpha analysis API")

        except requests.exceptions.RequestException as e:
            logger.error(f"Seeking Alpha analysis API error: {e}")

        logger.info(f"No analysis articles found for {ticker}")
        return None

