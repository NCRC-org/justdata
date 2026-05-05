"""Seeking Alpha data fetcher."""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

def _get_seeking_alpha_data(collector, name: str) -> Dict[str, Any]:
    """Get Seeking Alpha data (requires ticker symbol)."""
    try:
        # Known ticker mappings for common banks (fallback for edge cases)
        ticker_map = {
            'FIFTH THIRD BANK': 'FITB',
            'FIFTH THIRD': 'FITB',
            'FIFTH THIRD BANCORP': 'FITB',
        }
        
        # Check known mappings first (fast lookup)
        name_upper = name.upper()
        ticker = ticker_map.get(name_upper)
        
        # If not found, use reliable SEC-based lookup
        if not ticker:
            ticker = collector.sec_client.get_ticker_from_company_name(name)
        
        if not ticker:
            logger.info(f"Could not determine ticker symbol for {name}, skipping Seeking Alpha")
            return {}
        
        logger.info(f"Fetching Seeking Alpha data for ticker: {ticker}")
        
        # Get comprehensive data
        result = collector.seeking_alpha_client.search_by_ticker(ticker)
        
        if result:
            logger.info(f"Successfully retrieved Seeking Alpha data for {ticker}")

            # Also fetch news articles
            news = collector.seeking_alpha_client.get_news(ticker, limit=10)

            return {
                'ticker': ticker,
                'profile': result.get('profile'),
                'financials': result.get('financials'),
                'ratings': result.get('ratings'),  # Analyst ratings and recommendations
                'earnings': result.get('earnings'),  # Earnings estimates
                'leading_story': result.get('leading_story'),  # Leading news stories/articles
                'analysis_articles': result.get('analysis_articles'),  # Ticker-specific analysis articles
                'news': news  # News articles with headlines and snippets
            }
        else:
            logger.info(f"No Seeking Alpha data found for ticker {ticker}")
            return {}
            
    except Exception as e:
        logger.error(f"Error getting Seeking Alpha data for {name}: {e}", exc_info=True)
        return {}

