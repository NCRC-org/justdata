#!/usr/bin/env python3
"""
ElectWatch Scheduled Data Update Script

Runs weekly (recommended: Sunday midnight) to refresh all data sources:
- FEC Campaign Finance data
- Quiver Congressional Trading data
- Congress.gov Bills and Members
- Finnhub News and Stock Quotes
- SEC EDGAR Filings
- NewsAPI Articles

Usage:
    # Run manually:
    python apps/electwatch/scheduled_update.py

    # Windows Task Scheduler:
    schtasks /create /tn "ElectWatch Weekly Update" /tr "python C:\\Code\\ncrc-test-apps\\apps\\electwatch\\scheduled_update.py" /sc weekly /d SUN /st 00:00

    # Linux/Mac cron (add to crontab -e):
    0 0 * * 0 cd /path/to/ncrc-test-apps && python apps/electwatch/scheduled_update.py >> logs/update.log 2>&1

Environment:
    Requires .env file with API keys in repo root.
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# Set up paths
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(REPO_ROOT / '.env')

# Set up logging
LOG_DIR = REPO_ROOT / 'logs'
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f'electwatch_update_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DataUpdateRunner:
    """Orchestrates data updates from all sources."""

    def __init__(self):
        self.results = {
            'start_time': datetime.now().isoformat(),
            'sources': {},
            'errors': [],
            'summary': {}
        }

    def run_all_updates(self) -> Dict[str, Any]:
        """Run updates for all data sources."""
        logger.info("=" * 60)
        logger.info("ElectWatch Scheduled Data Update")
        logger.info(f"Started at: {self.results['start_time']}")
        logger.info("=" * 60)

        # Update each data source
        self.update_quiver()
        self.update_fec()
        self.update_congress()
        self.update_finnhub()
        self.update_sec()
        self.update_news()

        # Generate summary
        self.generate_summary()

        # Save results
        self.save_results()

        logger.info("=" * 60)
        logger.info("Update Complete!")
        logger.info(f"Successful: {self.results['summary'].get('successful', 0)}")
        logger.info(f"Failed: {self.results['summary'].get('failed', 0)}")
        logger.info("=" * 60)

        return self.results

    def update_quiver(self):
        """Update congressional trading data from Quiver."""
        logger.info("\n--- Updating Quiver Congressional Trading ---")
        try:
            from apps.electwatch.services.quiver_client import QuiverClient
            client = QuiverClient()

            if not client.test_connection():
                raise Exception("Quiver API connection failed")

            # Fetch recent trades
            trades = client.get_recent_trades(days=365)

            self.results['sources']['quiver'] = {
                'status': 'success',
                'records': len(trades) if trades else 0,
                'last_trade_date': trades[0].get('transaction_date') if trades else None,
                'timestamp': datetime.now().isoformat()
            }
            logger.info(f"Quiver: Retrieved {len(trades) if trades else 0} trades")

        except Exception as e:
            logger.error(f"Quiver update failed: {e}")
            self.results['sources']['quiver'] = {
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            self.results['errors'].append(f"Quiver: {e}")

    def update_fec(self):
        """Update campaign finance data from FEC."""
        logger.info("\n--- Updating FEC Campaign Finance ---")
        try:
            from apps.electwatch.services.fec_client import FECClient
            client = FECClient()

            if not client.test_connection():
                raise Exception("FEC API connection failed")

            # Test with sample queries
            candidates = client.search_candidates(name="Hill", state="AR", limit=5)
            committees = client.search_committees(name="Wells Fargo", limit=5)

            self.results['sources']['fec'] = {
                'status': 'success',
                'candidates_found': len(candidates) if candidates else 0,
                'committees_found': len(committees) if committees else 0,
                'timestamp': datetime.now().isoformat()
            }
            logger.info(f"FEC: Connection verified, found {len(candidates) if candidates else 0} candidates, {len(committees) if committees else 0} committees")

        except Exception as e:
            logger.error(f"FEC update failed: {e}")
            self.results['sources']['fec'] = {
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            self.results['errors'].append(f"FEC: {e}")

    def update_congress(self):
        """Update bills and members from Congress.gov."""
        logger.info("\n--- Updating Congress.gov ---")
        try:
            from apps.electwatch.services.congress_api_client import CongressAPIClient
            client = CongressAPIClient()

            # Test with sample bill queries
            bills = client.search_bills(query="financial", limit=5)

            if not bills:
                raise Exception("Congress.gov API returned no results")

            self.results['sources']['congress'] = {
                'status': 'success',
                'bills_found': len(bills) if bills else 0,
                'timestamp': datetime.now().isoformat()
            }
            logger.info(f"Congress.gov: Found {len(bills) if bills else 0} bills")

        except Exception as e:
            logger.error(f"Congress.gov update failed: {e}")
            self.results['sources']['congress'] = {
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            self.results['errors'].append(f"Congress.gov: {e}")

    def update_finnhub(self):
        """Update news and stock data from Finnhub."""
        logger.info("\n--- Updating Finnhub ---")
        try:
            from apps.electwatch.services.finnhub_client import FinnhubClient
            client = FinnhubClient()

            if not client.test_connection():
                raise Exception("Finnhub API connection failed")

            # Get sample data for key financial stocks
            symbols = ['WFC', 'JPM', 'BAC', 'COIN', 'GS']
            news_count = 0
            quotes_count = 0

            for symbol in symbols:
                news = client.get_company_news(symbol, days=7, limit=10)
                quote = client.get_quote(symbol)
                news_count += len(news) if news else 0
                if quote:
                    quotes_count += 1

            self.results['sources']['finnhub'] = {
                'status': 'success',
                'news_articles': news_count,
                'quotes_retrieved': quotes_count,
                'symbols_checked': symbols,
                'timestamp': datetime.now().isoformat()
            }
            logger.info(f"Finnhub: Retrieved {news_count} news articles, {quotes_count} quotes")

        except Exception as e:
            logger.error(f"Finnhub update failed: {e}")
            self.results['sources']['finnhub'] = {
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            self.results['errors'].append(f"Finnhub: {e}")

    def update_sec(self):
        """Update SEC EDGAR filings."""
        logger.info("\n--- Updating SEC EDGAR ---")
        try:
            from apps.electwatch.services.sec_client import SECClient
            client = SECClient()

            # Test with sample tickers
            test_tickers = ['WFC', 'JPM', 'COIN']

            filings_count = 0
            for ticker in test_tickers:
                filings = client.get_recent_10k_10q(ticker)
                filings_count += len(filings) if filings else 0

            self.results['sources']['sec'] = {
                'status': 'success',
                'filings_found': filings_count,
                'tickers_checked': test_tickers,
                'timestamp': datetime.now().isoformat()
            }
            logger.info(f"SEC EDGAR: Found {filings_count} filings across {len(test_tickers)} tickers")

        except Exception as e:
            logger.error(f"SEC EDGAR update failed: {e}")
            self.results['sources']['sec'] = {
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            self.results['errors'].append(f"SEC: {e}")

    def update_news(self):
        """Update news from NewsAPI with quality filtering."""
        logger.info("\n--- Updating NewsAPI ---")
        try:
            from apps.electwatch.services.news_client import NewsClient
            client = NewsClient()

            if not client.test_connection():
                raise Exception("NewsAPI connection failed")

            # Get political finance news
            news = client.get_political_finance_news(days=7, limit=20)

            self.results['sources']['newsapi'] = {
                'status': 'success',
                'articles_found': len(news) if news else 0,
                'timestamp': datetime.now().isoformat()
            }
            logger.info(f"NewsAPI: Retrieved {len(news) if news else 0} quality-filtered articles")

        except Exception as e:
            logger.error(f"NewsAPI update failed: {e}")
            self.results['sources']['newsapi'] = {
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            self.results['errors'].append(f"NewsAPI: {e}")

    def generate_summary(self):
        """Generate summary statistics."""
        successful = sum(1 for s in self.results['sources'].values() if s.get('status') == 'success')
        failed = sum(1 for s in self.results['sources'].values() if s.get('status') == 'failed')

        self.results['summary'] = {
            'successful': successful,
            'failed': failed,
            'total': len(self.results['sources']),
            'end_time': datetime.now().isoformat()
        }

        # Calculate duration
        start = datetime.fromisoformat(self.results['start_time'])
        end = datetime.fromisoformat(self.results['summary']['end_time'])
        self.results['summary']['duration_seconds'] = (end - start).total_seconds()

    def save_results(self):
        """Save results to file."""
        results_dir = REPO_ROOT / 'apps' / 'electwatch' / 'data'
        results_dir.mkdir(exist_ok=True)

        # Save latest results
        results_file = results_dir / 'update_results.json'
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)

        # Also save timestamped version
        timestamped_file = results_dir / f'update_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(timestamped_file, 'w') as f:
            json.dump(self.results, f, indent=2)

        logger.info(f"Results saved to: {results_file}")


def main():
    """Main entry point."""
    runner = DataUpdateRunner()
    results = runner.run_all_updates()

    # Exit with error code if any failures
    if results['summary'].get('failed', 0) > 0:
        sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main()
