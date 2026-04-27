"""SEC EDGAR fetcher for the ElectWatch weekly pipeline."""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def fetch_sec_data(coordinator):
    """Fetch SEC EDGAR filings."""
    logger.info("\n--- Fetching SEC EDGAR Data ---")
    try:
        from justdata.apps.electwatch.services.sec_client import SECClient
        client = SECClient()

        # Add SEC filings to existing firms data
        filings_count = 0
        for firm in coordinator.firms_data:
            try:
                ticker = firm.get('ticker')
                if ticker:
                    filings = client.get_recent_10k_10q(ticker)
                    firm['sec_filings'] = filings or []
                    filings_count += len(filings or [])
            except Exception as e:
                logger.warning(f"SEC error for {firm.get('ticker')}: {e}")
                firm['sec_filings'] = []

        coordinator.source_status['sec'] = {
            'status': 'success',
            'filings_found': filings_count,
            'timestamp': datetime.now().isoformat()
        }
        logger.info(f"Fetched {filings_count} SEC filings")

    except Exception as e:
        logger.error(f"SEC fetch failed: {e}")
        coordinator.warnings.append(f"SEC: {e}")
        coordinator.source_status['sec'] = {'status': 'failed', 'error': str(e)}
