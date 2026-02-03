#!/usr/bin/env python3
"""
SEC-based ticker classification using SIC codes.

Uses SEC EDGAR data to automatically classify stock tickers by industry.
Financial sector is SIC 6000-6799.
"""

import json
import logging
import requests
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# SEC requires a User-Agent with contact info
SEC_HEADERS = {
    'User-Agent': 'NCRC Research research@ncrc.org',
    'Accept': 'application/json'
}

# Cache directory
CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"
TICKER_CACHE_FILE = CACHE_DIR / "sec_ticker_sic_cache.json"

# SIC code ranges for financial sector
FINANCIAL_SIC_RANGES = [
    (6000, 6099, 'Depository Institutions', 'banking'),
    (6100, 6199, 'Non-depository Credit', 'lending'),
    (6200, 6299, 'Securities & Commodities', 'securities'),
    (6300, 6399, 'Insurance Carriers', 'insurance'),
    (6400, 6499, 'Insurance Agents', 'insurance'),
    (6500, 6599, 'Real Estate', 'real_estate'),
    (6700, 6799, 'Holding & Investment', 'investment'),
]

# More specific sub-sector mappings for SIC codes
SIC_SUBSECTOR_MAP = {
    # Banking
    6021: ('banking', 'commercial_banking'),
    6022: ('banking', 'commercial_banking'),
    6029: ('banking', 'commercial_banking'),
    6035: ('banking', 'savings_institutions'),
    6036: ('banking', 'savings_institutions'),
    6099: ('banking', 'other_banking'),

    # Lending/Credit
    6141: ('lending', 'personal_credit'),
    6153: ('lending', 'business_credit'),
    6159: ('lending', 'other_credit'),
    6162: ('lending', 'mortgage_banking'),
    6163: ('lending', 'mortgage_banking'),

    # Securities
    6211: ('securities', 'broker_dealer'),
    6221: ('securities', 'commodities'),
    6282: ('securities', 'investment_advisory'),

    # Insurance
    6311: ('insurance', 'life_insurance'),
    6321: ('insurance', 'health_insurance'),
    6324: ('insurance', 'health_insurance'),
    6331: ('insurance', 'property_casualty'),
    6351: ('insurance', 'surety'),
    6361: ('insurance', 'title_insurance'),
    6411: ('insurance', 'insurance_agents'),

    # Investment
    6712: ('investment', 'bank_holding'),
    6719: ('investment', 'holding_companies'),
    6722: ('investment', 'investment_trusts'),
    6726: ('investment', 'investment_trusts'),
    6792: ('investment', 'oil_royalty'),
    6794: ('investment', 'patent_owners'),
    6795: ('investment', 'mineral_royalty'),
    6798: ('investment', 'reits'),
    6799: ('investment', 'other_investment'),
}


class SECClassifier:
    """Classifies tickers using SEC SIC codes."""

    def __init__(self):
        self._ticker_to_cik: Dict[str, str] = {}
        self._cik_cache: Dict[str, Dict] = {}
        self._load_ticker_map()
        self._load_cache()

    def _load_ticker_map(self):
        """Load SEC ticker to CIK mapping."""
        try:
            url = 'https://www.sec.gov/files/company_tickers.json'
            resp = requests.get(url, headers=SEC_HEADERS, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            # Build ticker -> CIK map
            for entry in data.values():
                ticker = entry.get('ticker', '').upper()
                cik = str(entry.get('cik_str', ''))
                if ticker and cik:
                    self._ticker_to_cik[ticker] = cik

            logger.info(f"Loaded {len(self._ticker_to_cik)} ticker mappings from SEC")
        except Exception as e:
            logger.error(f"Failed to load SEC ticker map: {e}")

    def _load_cache(self):
        """Load cached SIC data."""
        if TICKER_CACHE_FILE.exists():
            try:
                with open(TICKER_CACHE_FILE) as f:
                    self._cik_cache = json.load(f)
                logger.info(f"Loaded {len(self._cik_cache)} cached SIC entries")
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
                self._cik_cache = {}

    def _save_cache(self):
        """Save SIC cache to disk."""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(TICKER_CACHE_FILE, 'w') as f:
            json.dump(self._cik_cache, f)

    def get_sic_for_ticker(self, ticker: str) -> Optional[Dict]:
        """
        Get SIC code and company info for a ticker.

        Returns:
            Dict with keys: sic, sic_description, company_name, or None if not found
        """
        ticker = ticker.upper().strip()

        # Check cache first
        if ticker in self._cik_cache:
            return self._cik_cache[ticker]

        # Get CIK
        cik = self._ticker_to_cik.get(ticker)
        if not cik:
            return None

        try:
            url = f'https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json'
            resp = requests.get(url, headers=SEC_HEADERS, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            result = {
                'ticker': ticker,
                'cik': cik,
                'company_name': data.get('name', ''),
                'sic': data.get('sic', ''),
                'sic_description': data.get('sicDescription', ''),
            }

            # Cache it
            self._cik_cache[ticker] = result

            return result

        except Exception as e:
            logger.debug(f"Failed to get SIC for {ticker}: {e}")
            return None

    def classify_ticker(self, ticker: str) -> Dict:
        """
        Classify a ticker as financial or non-financial.

        Returns:
            Dict with keys: ticker, is_financial, sector, sub_sector, sic, company_name
        """
        result = {
            'ticker': ticker.upper(),
            'is_financial': False,
            'sector': None,
            'sub_sector': None,
            'sic': None,
            'sic_description': None,
            'company_name': None,
        }

        sic_data = self.get_sic_for_ticker(ticker)
        if not sic_data:
            return result

        result['sic'] = sic_data.get('sic')
        result['sic_description'] = sic_data.get('sic_description')
        result['company_name'] = sic_data.get('company_name')

        try:
            sic_code = int(sic_data.get('sic', 0))
        except (ValueError, TypeError):
            return result

        # Check specific sub-sector mappings first
        if sic_code in SIC_SUBSECTOR_MAP:
            sector, sub_sector = SIC_SUBSECTOR_MAP[sic_code]
            result['is_financial'] = True
            result['sector'] = sector
            result['sub_sector'] = sub_sector
            return result

        # Check general financial ranges
        for start, end, description, sector in FINANCIAL_SIC_RANGES:
            if start <= sic_code <= end:
                result['is_financial'] = True
                result['sector'] = sector
                result['sub_sector'] = description.lower().replace(' ', '_')
                return result

        return result

    def classify_tickers_bulk(self, tickers: List[str],
                              rate_limit: float = 0.1,
                              save_interval: int = 100) -> Dict[str, Dict]:
        """
        Classify multiple tickers with rate limiting.

        Args:
            tickers: List of ticker symbols
            rate_limit: Seconds between SEC API calls (default 0.1 = 10/sec)
            save_interval: Save cache every N new lookups

        Returns:
            Dict mapping ticker -> classification result
        """
        results = {}
        new_lookups = 0

        for i, ticker in enumerate(tickers):
            ticker = ticker.upper().strip()

            # Skip if already cached
            if ticker in self._cik_cache:
                results[ticker] = self.classify_ticker(ticker)
                continue

            # Rate limit for new lookups
            if new_lookups > 0:
                time.sleep(rate_limit)

            results[ticker] = self.classify_ticker(ticker)
            new_lookups += 1

            # Progress logging
            if (i + 1) % 100 == 0:
                logger.info(f"Classified {i + 1}/{len(tickers)} tickers...")

            # Periodic cache save
            if new_lookups % save_interval == 0:
                self._save_cache()

        # Final cache save
        if new_lookups > 0:
            self._save_cache()
            logger.info(f"Saved cache with {len(self._cik_cache)} entries")

        return results

    def get_financial_summary(self, classifications: Dict[str, Dict]) -> Dict:
        """
        Summarize classification results.

        Returns:
            Dict with counts by sector and financial status
        """
        total = len(classifications)
        financial = sum(1 for c in classifications.values() if c.get('is_financial'))

        sectors = {}
        for c in classifications.values():
            sector = c.get('sector') or 'non_financial'
            sectors[sector] = sectors.get(sector, 0) + 1

        return {
            'total_tickers': total,
            'financial_count': financial,
            'non_financial_count': total - financial,
            'financial_pct': round(financial / total * 100, 1) if total else 0,
            'by_sector': sectors,
        }


def classify_electwatch_tickers():
    """Classify all tickers from ElectWatch data."""
    # Load officials
    officials_path = Path(__file__).parent.parent / "data" / "weekly" / "2026-01-31" / "officials.json"

    if not officials_path.exists():
        # Try current
        officials_path = Path(__file__).parent.parent / "data" / "current" / "officials.json"

    with open(officials_path) as f:
        data = json.load(f)

    officials = data.get('officials', data.get('data', []))

    # Collect unique tickers
    tickers = set()
    for o in officials:
        for trade in o.get('trades', []):
            ticker = trade.get('ticker', '').upper().strip()
            if ticker:
                tickers.add(ticker)

    print(f"Found {len(tickers)} unique tickers to classify")

    # Classify
    classifier = SECClassifier()
    results = classifier.classify_tickers_bulk(list(tickers))

    # Summary
    summary = classifier.get_financial_summary(results)
    print(f"\nClassification Summary:")
    print(f"  Total tickers: {summary['total_tickers']}")
    print(f"  Financial: {summary['financial_count']} ({summary['financial_pct']}%)")
    print(f"  Non-financial: {summary['non_financial_count']}")
    print(f"\nBy sector:")
    for sector, count in sorted(summary['by_sector'].items(), key=lambda x: -x[1]):
        print(f"  {sector}: {count}")

    return results, summary


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    classify_electwatch_tickers()
