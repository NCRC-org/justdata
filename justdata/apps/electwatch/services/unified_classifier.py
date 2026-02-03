#!/usr/bin/env python3
"""
Unified ticker classification combining SEC SIC codes and yfinance data.

Provides a single interface that:
1. Tries SEC EDGAR first (authoritative for public US companies)
2. Falls back to yfinance for ETFs, ADRs, and mutual funds
3. Marks garbage entries (CUSIPs, treasury notes, invalid) as INVALID
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Cache directory
CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"
UNIFIED_CACHE_FILE = CACHE_DIR / "unified_classification_cache.json"

# Patterns to detect invalid/garbage tickers
INVALID_PATTERNS = [
    r'^\d{9}$',           # CUSIPs (9 digits)
    r'^\d+\.[A-Z]+',      # Like "3.MONTH"
    r'^MATURE',           # Treasury notes
    r'^SYMBOL:',          # Parsing errors
    r'^SYMBOL$',
    r'MATURE$',           # Ends with MATURE
    r'^\d+\.WEEK',        # Treasury bills
    r'^\d+\.MONTH',
    r'^STATE OF',         # Municipal bonds
    r'^BITCOIN$',
    r'^RIPPLE$',
    r'^SOLANA$',
    r'^ETHEREUM$',
    r'^ICAPITAL$',
    r'_FAILED$',          # Failed lookups
    r'-P-[A-Z]-CL$',      # Weird preferred share notation
    r'\$[A-Z]$',          # Like BAC$I (preferred shares - often not in APIs)
    r'^[A-Z]+-W$',        # Warrants with dash
    r'^[A-Z]+\d$',        # Like BAC1, UST1 (historical/delisted)
]

# Compile patterns for efficiency
INVALID_REGEX = [re.compile(p) for p in INVALID_PATTERNS]


def is_invalid_ticker(ticker: str) -> bool:
    """Check if ticker is garbage/invalid."""
    ticker = ticker.upper().strip()

    # Too short
    if len(ticker) < 1:
        return True

    # Contains spaces (usually parsing errors)
    if ' ' in ticker and ticker not in ['BRK A', 'BRK B']:
        return True

    # Starts with number (except some ETFs)
    if ticker[0].isdigit():
        return True

    # Check patterns
    for pattern in INVALID_REGEX:
        if pattern.search(ticker):
            return True

    return False


class UnifiedClassifier:
    """
    Combines SEC SIC codes and yfinance data for comprehensive ticker classification.
    """

    def __init__(self):
        self._sec_cache: Dict[str, Dict] = {}
        self._etf_cache: Dict[str, Dict] = {}
        self._unified_cache: Dict[str, Dict] = {}
        self._load_caches()

    def _load_caches(self):
        """Load all available cache files."""
        # SEC cache
        sec_cache_path = CACHE_DIR / "sec_ticker_sic_cache.json"
        if sec_cache_path.exists():
            try:
                with open(sec_cache_path) as f:
                    self._sec_cache = json.load(f)
                logger.info(f"Loaded {len(self._sec_cache)} SEC cache entries")
            except Exception as e:
                logger.warning(f"Failed to load SEC cache: {e}")

        # ETF cache
        etf_cache_path = CACHE_DIR / "etf_classification_cache.json"
        if etf_cache_path.exists():
            try:
                with open(etf_cache_path) as f:
                    self._etf_cache = json.load(f)
                logger.info(f"Loaded {len(self._etf_cache)} ETF cache entries")
            except Exception as e:
                logger.warning(f"Failed to load ETF cache: {e}")

        # Unified cache
        if UNIFIED_CACHE_FILE.exists():
            try:
                with open(UNIFIED_CACHE_FILE) as f:
                    self._unified_cache = json.load(f)
                logger.info(f"Loaded {len(self._unified_cache)} unified cache entries")
            except Exception as e:
                logger.warning(f"Failed to load unified cache: {e}")

    def _save_cache(self):
        """Save unified cache to disk."""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(UNIFIED_CACHE_FILE, 'w') as f:
            json.dump(self._unified_cache, f, indent=2)

    def classify_ticker(self, ticker: str) -> Dict:
        """
        Classify a single ticker using all available sources.

        Returns:
            Dict with keys:
                - ticker: The ticker symbol
                - is_financial: True if financial sector
                - sector: Sector name
                - sub_sector: Sub-sector name
                - asset_type: EQUITY, ETF, MUTUALFUND, INVALID, etc.
                - company_name: Company/fund name
                - source: Where classification came from (sec, yfinance, invalid)
                - sic: SIC code (if from SEC)
                - category: ETF category (if applicable)
        """
        ticker = ticker.upper().strip()

        # Check unified cache first
        if ticker in self._unified_cache:
            return self._unified_cache[ticker]

        result = {
            'ticker': ticker,
            'is_financial': False,
            'sector': None,
            'sub_sector': None,
            'asset_type': 'UNKNOWN',
            'company_name': None,
            'source': None,
            'sic': None,
            'sic_description': None,
            'category': None,
            'classified_at': datetime.now().isoformat()
        }

        # Check if invalid ticker
        if is_invalid_ticker(ticker):
            result['asset_type'] = 'INVALID'
            result['source'] = 'pattern_match'
            result['sector'] = 'invalid'
            self._unified_cache[ticker] = result
            return result

        # Try SEC cache first (authoritative for US public companies)
        if ticker in self._sec_cache:
            sec_data = self._sec_cache[ticker]
            if sec_data.get('sic'):  # Has valid SIC code
                result['source'] = 'sec'
                result['sic'] = sec_data.get('sic')
                result['sic_description'] = sec_data.get('sic_description')
                result['company_name'] = sec_data.get('company_name')
                result['asset_type'] = 'EQUITY'

                # Classify by SIC
                try:
                    sic_code = int(sec_data.get('sic', 0))
                    result.update(self._classify_by_sic(sic_code))
                except (ValueError, TypeError):
                    pass

                self._unified_cache[ticker] = result
                return result

        # Try ETF/yfinance cache
        if ticker in self._etf_cache:
            etf_data = self._etf_cache[ticker]
            source = etf_data.get('source', 'yfinance')

            if source == 'not_found':
                result['asset_type'] = 'NOT_FOUND'
                result['source'] = 'yfinance'
            elif source == 'error':
                result['asset_type'] = 'ERROR'
                result['source'] = 'yfinance'
            else:
                result['source'] = 'yfinance'
                result['asset_type'] = etf_data.get('asset_type', 'UNKNOWN')
                result['company_name'] = etf_data.get('company_name')
                result['category'] = etf_data.get('category')
                result['sector'] = etf_data.get('sector')
                result['sub_sector'] = etf_data.get('sub_sector')
                result['is_financial'] = etf_data.get('is_financial', False)

            self._unified_cache[ticker] = result
            return result

        # Not found in any cache
        result['source'] = 'not_classified'
        self._unified_cache[ticker] = result
        return result

    def _classify_by_sic(self, sic_code: int) -> Dict:
        """Classify based on SIC code."""
        # Financial sector ranges
        FINANCIAL_SIC_RANGES = [
            (6000, 6099, 'Depository Institutions', 'banking'),
            (6100, 6199, 'Non-depository Credit', 'lending'),
            (6200, 6299, 'Securities & Commodities', 'securities'),
            (6300, 6399, 'Insurance Carriers', 'insurance'),
            (6400, 6499, 'Insurance Agents', 'insurance'),
            (6500, 6599, 'Real Estate', 'real_estate'),
            (6700, 6799, 'Holding & Investment', 'investment'),
        ]

        # SIC Division mapping for non-financial
        SIC_DIVISIONS = {
            range(100, 1000): ('agriculture', 'Agriculture, Forestry, Fishing'),
            range(1000, 1500): ('mining', 'Mining'),
            range(1500, 1800): ('construction', 'Construction'),
            range(2000, 4000): ('manufacturing', 'Manufacturing'),
            range(4000, 5000): ('transportation', 'Transportation, Communications, Utilities'),
            range(5000, 5200): ('wholesale_trade', 'Wholesale Trade'),
            range(5200, 6000): ('retail_trade', 'Retail Trade'),
            range(7000, 9000): ('services', 'Services'),
            range(9100, 10000): ('public_admin', 'Public Administration'),
        }

        result = {'is_financial': False, 'sector': None, 'sub_sector': None}

        # Check financial ranges first
        for start, end, description, sector in FINANCIAL_SIC_RANGES:
            if start <= sic_code <= end:
                result['is_financial'] = True
                result['sector'] = sector
                result['sub_sector'] = description.lower().replace(' ', '_')
                return result

        # Check other divisions
        for sic_range, (sector, description) in SIC_DIVISIONS.items():
            if sic_code in sic_range:
                result['sector'] = sector
                result['sub_sector'] = description.lower().replace(' ', '_').replace(',', '')
                return result

        return result

    def classify_all(self) -> Dict[str, Dict]:
        """
        Classify all tickers from officials data.

        Returns:
            Dict mapping ticker -> classification result
        """
        # Load officials
        officials_path = CACHE_DIR.parent / "current" / "officials.json"
        with open(officials_path) as f:
            data = json.load(f)

        officials = data.get('officials', data.get('data', []))

        # Get unique tickers
        tickers = set()
        for o in officials:
            for trade in o.get('trades', []):
                ticker = trade.get('ticker', '').upper().strip()
                if ticker:
                    tickers.add(ticker)

        logger.info(f"Classifying {len(tickers)} unique tickers...")

        # Classify all
        results = {}
        for ticker in sorted(tickers):
            results[ticker] = self.classify_ticker(ticker)

        # Save cache
        self._save_cache()

        return results

    def get_summary(self, classifications: Dict[str, Dict] = None) -> Dict:
        """
        Get summary statistics for classifications.
        """
        if classifications is None:
            classifications = self._unified_cache

        total = len(classifications)
        if total == 0:
            return {'total': 0}

        by_source = {}
        by_type = {}
        by_sector = {}
        financial_count = 0

        for c in classifications.values():
            source = c.get('source') or 'unknown'
            atype = c.get('asset_type') or 'unknown'
            sector = c.get('sector') or 'unknown'
            is_fin = c.get('is_financial', False)

            by_source[source] = by_source.get(source, 0) + 1
            by_type[atype] = by_type.get(atype, 0) + 1
            by_sector[sector] = by_sector.get(sector, 0) + 1
            if is_fin:
                financial_count += 1

        return {
            'total_tickers': total,
            'financial_count': financial_count,
            'financial_pct': round(financial_count / total * 100, 1),
            'by_source': dict(sorted(by_source.items(), key=lambda x: -x[1])),
            'by_asset_type': dict(sorted(by_type.items(), key=lambda x: -x[1])),
            'by_sector': dict(sorted(by_sector.items(), key=lambda x: -x[1])),
        }

    def export_csv(self, output_path: Path = None) -> Path:
        """Export unified classifications to CSV."""
        import csv

        if output_path is None:
            output_path = CACHE_DIR.parent / "exports" / "ticker_classifications.csv"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Classify all first
        results = self.classify_all()

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'ticker', 'company_name', 'asset_type', 'source',
                'is_financial', 'sector', 'sub_sector',
                'sic', 'sic_description', 'category'
            ])
            writer.writeheader()

            for ticker in sorted(results.keys()):
                c = results[ticker]
                writer.writerow({
                    'ticker': ticker,
                    'company_name': c.get('company_name', ''),
                    'asset_type': c.get('asset_type', ''),
                    'source': c.get('source', ''),
                    'is_financial': 'Yes' if c.get('is_financial') else 'No',
                    'sector': c.get('sector', ''),
                    'sub_sector': c.get('sub_sector', ''),
                    'sic': c.get('sic', ''),
                    'sic_description': c.get('sic_description', ''),
                    'category': c.get('category', ''),
                })

        print(f"Exported {len(results)} classifications to {output_path}")
        return output_path


def main():
    """Run unified classification and print summary."""
    logging.basicConfig(level=logging.INFO)

    classifier = UnifiedClassifier()
    results = classifier.classify_all()
    summary = classifier.get_summary(results)

    print(f"\n{'='*60}")
    print("UNIFIED TICKER CLASSIFICATION SUMMARY")
    print(f"{'='*60}")
    print(f"\nTotal tickers: {summary['total_tickers']}")
    print(f"Financial: {summary['financial_count']} ({summary['financial_pct']}%)")

    print(f"\nBy Source:")
    for source, count in summary['by_source'].items():
        pct = round(count / summary['total_tickers'] * 100, 1)
        print(f"  {source}: {count} ({pct}%)")

    print(f"\nBy Asset Type:")
    for atype, count in summary['by_asset_type'].items():
        pct = round(count / summary['total_tickers'] * 100, 1)
        print(f"  {atype}: {count} ({pct}%)")

    print(f"\nBy Sector (top 15):")
    for sector, count in list(summary['by_sector'].items())[:15]:
        pct = round(count / summary['total_tickers'] * 100, 1)
        print(f"  {sector}: {count} ({pct}%)")

    # Export CSV
    csv_path = classifier.export_csv()
    print(f"\nCSV exported to: {csv_path}")

    return results, summary


if __name__ == '__main__':
    main()
