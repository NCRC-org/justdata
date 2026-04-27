"""Finnhub fetcher for the ElectWatch weekly pipeline."""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def fetch_finnhub_data(coordinator):
    """Fetch news and stock data from Finnhub."""
    logger.info("\n--- Fetching Finnhub Data ---")
    try:
        from justdata.apps.electwatch.services.finnhub_client import FinnhubClient
        client = FinnhubClient()

        if not client.test_connection():
            raise Exception("Finnhub API connection failed")

        # Key financial sector tickers
        tickers = ['WFC', 'JPM', 'BAC', 'C', 'GS', 'MS', 'COIN', 'HOOD', 'SQ', 'PYPL']

        firms_with_data = []
        total_news = 0

        for ticker in tickers:
            try:
                quote = client.get_quote(ticker)
                news = client.get_company_news(ticker, days=30, limit=10)
                profile = client.get_company_profile(ticker)
                insider = client.get_insider_transactions(ticker, limit=20)

                firm = {
                    'ticker': ticker,
                    'name': profile.get('name', ticker) if profile else ticker,
                    'industry': profile.get('industry', '') if profile else '',
                    'quote': quote,
                    'news': news or [],
                    'insider_transactions': insider or [],
                    'market_cap': profile.get('market_cap', 0) if profile else 0
                }
                firms_with_data.append(firm)
                total_news += len(news or [])

            except Exception as e:
                logger.warning(f"Error fetching {ticker}: {e}")

        coordinator.firms_data = firms_with_data

        coordinator.source_status['finnhub'] = {
            'status': 'success',
            'firms': len(firms_with_data),
            'news_articles': total_news,
            'timestamp': datetime.now().isoformat()
        }
        logger.info(f"Fetched data for {len(firms_with_data)} firms, {total_news} news articles")

    except Exception as e:
        logger.error(f"Finnhub fetch failed: {e}")
        coordinator.errors.append(f"Finnhub: {e}")
        coordinator.source_status['finnhub'] = {'status': 'failed', 'error': str(e)}
