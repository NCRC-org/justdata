"""NewsAPI fetcher for the ElectWatch weekly pipeline."""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def fetch_news_data(coordinator):
    """Fetch news from NewsAPI with quality filtering."""
    logger.info("\n--- Fetching NewsAPI Data ---")
    try:
        from justdata.apps.electwatch.services.news_client import NewsClient
        client = NewsClient()

        if not client.test_connection():
            raise Exception("NewsAPI connection failed")

        # Get political finance news
        political_news = client.get_political_finance_news(days=7, limit=30)

        # Get industry-specific news
        industries = ['banking', 'cryptocurrency', 'financial services', 'fintech']
        industry_news = []
        for industry in industries:
            try:
                news = client.get_industry_news(industry, days=7, limit=10)
                industry_news.extend(news or [])
            except:
                pass

        coordinator.news_data = (political_news or []) + industry_news

        coordinator.source_status['newsapi'] = {
            'status': 'success',
            'articles': len(coordinator.news_data),
            'timestamp': datetime.now().isoformat()
        }
        logger.info(f"Fetched {len(coordinator.news_data)} news articles")

    except Exception as e:
        logger.error(f"NewsAPI fetch failed: {e}")
        coordinator.warnings.append(f"NewsAPI: {e}")
        coordinator.source_status['newsapi'] = {'status': 'failed', 'error': str(e)}
