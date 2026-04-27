"""Recent news section."""
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from justdata.apps.lenderprofile.report_builder.helpers import (
    _is_recent,
    _truncate_text,
)

def build_recent_news(
    institution_data: Dict[str, Any],
    limit: int = None  # No limit by default - show all articles
) -> Dict[str, Any]:
    """
    Build recent news section with categorization.

    Uses news_processed (filtered for primary subject) if available,
    falls back to raw news data. Shows all articles from the available
    time period (up to 3 years depending on API tier).
    """
    # Prefer news_processed (filtered) over raw news
    news_data = institution_data.get('news_processed', institution_data.get('news', {}))
    articles = news_data.get('articles', [])

    # Categorize ALL articles (no limit)
    categorized = {
        'regulatory': [],
        'merger': [],
        'earnings': [],
        'leadership': [],
        'other': []
    }

    for article in articles:
        title = (article.get('title') or '').lower()
        description = (article.get('description') or '').lower()
        text = f"{title} {description}"

        # Categorize
        if any(w in text for w in ['enforcement', 'cfpb', 'fine', 'penalty', 'consent', 'investigation']):
            category = 'regulatory'
        elif any(w in text for w in ['merger', 'acquisition', 'acquire', 'deal', 'buy']):
            category = 'merger'
        elif any(w in text for w in ['earnings', 'profit', 'revenue', 'quarter', 'results']):
            category = 'earnings'
        elif any(w in text for w in ['ceo', 'appoint', 'resign', 'executive', 'board']):
            category = 'leadership'
        else:
            category = 'other'

        # Get summary/snippet (first 2-3 lines of content)
        summary = article.get('summary', article.get('description', article.get('content', '')))
        if summary and len(summary) > 200:
            summary = summary[:200] + '...'

        categorized[category].append({
            'title': article.get('title', article.get('headline', '')),
            'summary': summary,
            'source': article.get('source', {}).get('name', '') if isinstance(article.get('source'), dict) else article.get('source', ''),
            'published_at': article.get('publishedAt', article.get('date', '')),
            'url': article.get('url', ''),
            'category': category
        })

    # Flatten for display - prioritize regulatory and merger news first, then all others
    # No limits - show all articles
    all_articles = (
        categorized['regulatory'] +
        categorized['merger'] +
        categorized['leadership'] +
        categorized['earnings'] +
        categorized['other']
    )

    # Apply limit only if explicitly specified
    final_articles = all_articles[:limit] if limit else all_articles

    return {
        'articles': final_articles,
        'by_category': {k: len(v) for k, v in categorized.items()},
        'total': len(articles),
        'has_regulatory_news': len(categorized['regulatory']) > 0,
        'has_merger_news': len(categorized['merger']) > 0,
        'has_data': len(all_articles) > 0
    }


