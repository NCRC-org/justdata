"""News data fetcher + keyword aggregation."""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

def _aggregate_news_by_keywords(collector, news_keywords: List[str], institution_name: str) -> Dict[str, Any]:
    """Query news using AI-resolved keywords instead of all entities.

    This is much faster than querying all 24 subsidiaries - instead uses
    AI-determined keywords like ["Bank of America", "BofA"] for focused search.

    Args:
        news_keywords: List of search keywords from AI entity resolution
        institution_name: Primary institution name for fallback
    """
    all_articles = []
    seen_titles = set()

    # Limit to first 3 keywords to prevent timeout
    keywords_to_search = news_keywords[:3] if news_keywords else [institution_name]

    logger.info(f"News searching for keywords: {keywords_to_search}")

    for keyword in keywords_to_search:
        if not keyword:
            continue

        try:
            news_data = collector._get_news_data(keyword)
            articles = news_data.get('articles', [])

            for article in articles:
                # Deduplicate by title
                title = article.get('title', '')
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    # Tag with search keyword
                    article['source_entity'] = keyword
                    article['entity_relationship'] = 'primary'
                    all_articles.append(article)

        except Exception as e:
            logger.warning(f"Error getting news for {keyword}: {e}")

    logger.info(f"News search found {len(all_articles)} total articles")

    return {
        'articles': all_articles,
        'total_articles': len(all_articles),
        'source': 'aggregated'
    }

def _get_news_data(collector, name: str) -> Dict[str, Any]:
    """
    Get news data from reputable sources.

    Priority order:
    1. Google Custom Search (higher quality, limited free tier)
    2. NewsAPI with reputable domain filtering (fallback)

    Both sources are filtered to only include reputable financial news outlets.
    """
    cache_key = f'news_{name}'
    cached = collector.cache.get('news', cache_key)
    if cached:
        return cached

    articles = []
    source = 'none'

    # Try Google Custom Search first (higher quality results)
    try:
        if collector.google_news_client.api_key and collector.google_news_client.search_engine_id:
            logger.info(f"Fetching news via Google Custom Search for: {name}")
            google_result = collector.google_news_client.search_news_extended(
                query=name,
                num_results=20,
                date_restrict='m3'  # Last 3 months
            )
            articles = google_result.get('articles', [])
            if articles:
                source = 'google_custom_search'
                logger.info(f"Google Custom Search found {len(articles)} articles for {name}")
    except Exception as e:
        logger.warning(f"Google Custom Search failed for {name}: {e}")

    # Fallback to NewsAPI with reputable domain filtering
    if not articles:
        try:
            logger.info(f"Fetching news via NewsAPI (reputable sources only) for: {name}")
            response = collector.newsapi_client.search_everything(
                query=f'"{name}"',
                language='en',
                sort_by='relevancy',
                page_size=50,
                use_reputable_sources=True  # Filter to reputable domains
            )
            articles = response.get('articles', [])
            if articles:
                source = 'newsapi_filtered'
                logger.info(f"NewsAPI found {len(articles)} articles from reputable sources for {name}")
        except Exception as e:
            logger.warning(f"NewsAPI failed for {name}: {e}")

    # Fallback to DuckDuckGo search
    if not articles:
        try:
            logger.info(f"Fetching news via DuckDuckGo for: {name}")
            ddg_articles = collector.duckduckgo_client.search_news(name, max_results=20)
            if ddg_articles:
                articles = ddg_articles
                source = 'duckduckgo'
                logger.info(f"DuckDuckGo found {len(articles)} results for {name}")
        except Exception as e:
            logger.warning(f"DuckDuckGo search failed for {name}: {e}")

    result = {
        'articles': articles,
        'total_articles': len(articles),
        'source': source
    }

    if articles:
        collector.cache.set('news', result, collector.cache.get_ttl('news'), cache_key)

    return result

# TheOrg API removed - not using organizational data
