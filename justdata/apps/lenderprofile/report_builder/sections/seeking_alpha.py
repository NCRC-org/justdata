"""Seeking Alpha section."""
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from justdata.apps.lenderprofile.report_builder.helpers import _truncate_text

def build_seeking_alpha_section(
    institution_data: Dict[str, Any],
    ticker: str = None
) -> Dict[str, Any]:
    """
    Build Seeking Alpha section with ticker-specific analysis articles.

    Uses the analysis_articles from the API which are already filtered
    to only include articles about this specific ticker/company.
    """
    seeking_alpha_data = institution_data.get('seeking_alpha', {})

    # Get ticker-specific analysis articles (already filtered by ticker)
    analysis_articles = seeking_alpha_data.get('analysis_articles', [])
    if not isinstance(analysis_articles, list):
        analysis_articles = []

    # Format analysis articles
    formatted_articles = []
    for article in analysis_articles:
        if isinstance(article, dict):
            formatted_articles.append({
                'title': article.get('headline', article.get('title', '')),
                'summary': article.get('summary', '') or '',
                'url': article.get('url', ''),
                'published_at': article.get('date', article.get('publishOn', '')),
                'source': 'Seeking Alpha'
            })

    # Get ratings data if available
    # Structure: {data: [{attributes: {ratings: {quantRating, sellSideRating}}}]}
    ratings_data = seeking_alpha_data.get('ratings', {})
    quant_rating = None
    wall_st_rating = None
    if isinstance(ratings_data, dict):
        data_list = ratings_data.get('data', [])
        if isinstance(data_list, list) and len(data_list) > 0:
            first_rating = data_list[0]
            if isinstance(first_rating, dict):
                attrs = first_rating.get('attributes', {})
                ratings = attrs.get('ratings', {})
                if isinstance(ratings, dict):
                    quant_val = ratings.get('quantRating')
                    wall_st_val = ratings.get('sellSideRating')
                    # Convert to display format (1-5 scale)
                    if quant_val:
                        quant_rating = f"{quant_val:.1f}"
                    if wall_st_val:
                        wall_st_rating = f"{wall_st_val:.1f}"

    return {
        'articles': formatted_articles,
        'total_articles': len(formatted_articles),
        'ticker': ticker,
        'quant_rating': quant_rating,
        'wall_st_rating': wall_st_rating,
        'has_data': len(formatted_articles) > 0 or quant_rating or wall_st_rating
    }


