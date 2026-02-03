#!/usr/bin/env python3
"""
ETF and stock classifier using yfinance.

Classifies tickers that SEC doesn't have SIC codes for (ETFs, ADRs, etc.)
Uses yfinance to get category/sector information.
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

try:
    import yfinance as yf
except ImportError:
    yf = None

logger = logging.getLogger(__name__)

# Cache directory
CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"
ETF_CACHE_FILE = CACHE_DIR / "etf_classification_cache.json"

# Financial sector keywords in ETF categories/names
FINANCIAL_KEYWORDS = [
    'financial', 'bank', 'banking', 'insurance', 'reit', 'real estate',
    'mortgage', 'credit', 'lending', 'investment', 'asset management',
    'broker', 'securities', 'capital markets', 'fintech', 'payments',
    'diversified financials', 'specialty finance', 'consumer finance',
    'regional banks', 'money center banks', 'thrifts', 'savings'
]

# Sector mappings from yfinance sector names
SECTOR_MAPPINGS = {
    'financial services': ('financial_services', True),
    'financial': ('financial_services', True),
    'real estate': ('real_estate', True),
    'technology': ('technology', False),
    'healthcare': ('healthcare', False),
    'consumer cyclical': ('consumer_cyclical', False),
    'consumer defensive': ('consumer_defensive', False),
    'communication services': ('communication_services', False),
    'energy': ('energy', False),
    'industrials': ('industrials', False),
    'basic materials': ('basic_materials', False),
    'utilities': ('utilities', False),
}

# ETF category to sector mappings
ETF_CATEGORY_MAPPINGS = {
    # Financial
    'financial': ('financial_services', 'general', True),
    'financials': ('financial_services', 'general', True),
    'financial services': ('financial_services', 'general', True),
    'bank': ('financial_services', 'banking', True),
    'banking': ('financial_services', 'banking', True),
    'regional banks': ('financial_services', 'regional_banking', True),
    'insurance': ('financial_services', 'insurance', True),
    'real estate': ('real_estate', 'general', True),
    'reit': ('real_estate', 'reits', True),

    # Non-financial
    'technology': ('technology', 'general', False),
    'large growth': ('equity', 'large_cap_growth', False),
    'large blend': ('equity', 'large_cap_blend', False),
    'large value': ('equity', 'large_cap_value', False),
    'mid-cap': ('equity', 'mid_cap', False),
    'small cap': ('equity', 'small_cap', False),
    'health': ('healthcare', 'general', False),
    'healthcare': ('healthcare', 'general', False),
    'energy': ('energy', 'general', False),
    'utilities': ('utilities', 'general', False),
    'consumer': ('consumer', 'general', False),
    'industrial': ('industrials', 'general', False),
    'materials': ('basic_materials', 'general', False),
    'bond': ('fixed_income', 'bonds', False),
    'treasury': ('fixed_income', 'treasuries', False),
    'corporate bond': ('fixed_income', 'corporate', False),
    'high yield': ('fixed_income', 'high_yield', False),
    'muni': ('fixed_income', 'municipal', False),
    'emerging markets': ('international', 'emerging_markets', False),
    'international': ('international', 'developed', False),
    'foreign': ('international', 'foreign', False),
    'global': ('international', 'global', False),
    'commodity': ('commodities', 'general', False),
    'gold': ('commodities', 'precious_metals', False),
    'silver': ('commodities', 'precious_metals', False),
    'oil': ('commodities', 'energy', False),
}


class ETFClassifier:
    """Classifies ETFs and stocks using yfinance."""

    def __init__(self):
        self._cache: Dict[str, Dict] = {}
        self._load_cache()

        if yf is None:
            logger.warning("yfinance not installed. Run: pip install yfinance")

    def _load_cache(self):
        """Load cached classification data."""
        if ETF_CACHE_FILE.exists():
            try:
                with open(ETF_CACHE_FILE) as f:
                    self._cache = json.load(f)
                logger.info(f"Loaded {len(self._cache)} cached ETF classifications")
            except Exception as e:
                logger.warning(f"Failed to load ETF cache: {e}")
                self._cache = {}

    def _save_cache(self):
        """Save classification cache to disk."""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(ETF_CACHE_FILE, 'w') as f:
            json.dump(self._cache, f, indent=2)

    def _is_financial_keyword(self, text: str) -> bool:
        """Check if text contains financial keywords."""
        if not text:
            return False
        text_lower = text.lower()
        return any(kw in text_lower for kw in FINANCIAL_KEYWORDS)

    def _classify_category(self, category: str) -> Dict:
        """Classify based on ETF category string."""
        if not category:
            return {'sector': None, 'sub_sector': None, 'is_financial': False}

        category_lower = category.lower()

        # Check exact/partial matches
        for key, (sector, sub_sector, is_fin) in ETF_CATEGORY_MAPPINGS.items():
            if key in category_lower:
                return {
                    'sector': sector,
                    'sub_sector': sub_sector,
                    'is_financial': is_fin
                }

        # Check financial keywords
        if self._is_financial_keyword(category):
            return {
                'sector': 'financial_services',
                'sub_sector': 'general',
                'is_financial': True
            }

        return {'sector': 'other', 'sub_sector': category_lower, 'is_financial': False}

    def classify_ticker(self, ticker: str) -> Dict:
        """
        Classify a ticker using yfinance.

        Returns:
            Dict with keys: ticker, is_financial, sector, sub_sector, asset_type,
                          company_name, category, source
        """
        ticker = ticker.upper().strip()

        # Check cache first
        if ticker in self._cache:
            return self._cache[ticker]

        result = {
            'ticker': ticker,
            'is_financial': False,
            'sector': None,
            'sub_sector': None,
            'asset_type': None,
            'company_name': None,
            'category': None,
            'source': 'yfinance',
            'classified_at': datetime.now().isoformat()
        }

        if yf is None:
            result['source'] = 'unavailable'
            return result

        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            if not info or info.get('regularMarketPrice') is None:
                # No data found
                result['source'] = 'not_found'
                self._cache[ticker] = result
                return result

            # Get basic info
            result['company_name'] = info.get('longName') or info.get('shortName')
            result['asset_type'] = info.get('quoteType', 'UNKNOWN')

            # Check if it's an ETF
            if info.get('quoteType') == 'ETF':
                category = info.get('category', '')
                result['category'] = category

                # Classify by category
                classification = self._classify_category(category)
                result.update(classification)

                # Also check fund name for financial keywords
                fund_name = result.get('company_name', '')
                if not result['is_financial'] and self._is_financial_keyword(fund_name):
                    result['is_financial'] = True
                    result['sector'] = 'financial_services'
                    result['sub_sector'] = 'fund'

            else:
                # It's a stock - use sector/industry
                sector = info.get('sector', '')
                industry = info.get('industry', '')

                result['sector'] = sector.lower().replace(' ', '_') if sector else None
                result['sub_sector'] = industry.lower().replace(' ', '_') if industry else None
                result['category'] = f"{sector} / {industry}" if sector else None

                # Check if financial sector
                sector_lower = sector.lower() if sector else ''
                if sector_lower in ['financial services', 'financial', 'real estate']:
                    result['is_financial'] = True
                elif self._is_financial_keyword(sector) or self._is_financial_keyword(industry):
                    result['is_financial'] = True

            self._cache[ticker] = result
            return result

        except Exception as e:
            logger.debug(f"Failed to classify {ticker}: {e}")
            result['source'] = 'error'
            result['error'] = str(e)
            self._cache[ticker] = result
            return result

    def classify_tickers_bulk(self, tickers: List[str],
                              rate_limit: float = 0.2,
                              save_interval: int = 50) -> Dict[str, Dict]:
        """
        Classify multiple tickers with rate limiting.

        Args:
            tickers: List of ticker symbols
            rate_limit: Seconds between API calls (default 0.2 = 5/sec)
            save_interval: Save cache every N new lookups

        Returns:
            Dict mapping ticker -> classification result
        """
        results = {}
        new_lookups = 0

        for i, ticker in enumerate(tickers):
            ticker = ticker.upper().strip()

            # Skip if already cached
            if ticker in self._cache:
                results[ticker] = self._cache[ticker]
                continue

            # Rate limit for new lookups
            if new_lookups > 0:
                time.sleep(rate_limit)

            results[ticker] = self.classify_ticker(ticker)
            new_lookups += 1

            # Progress logging
            if (i + 1) % 50 == 0:
                logger.info(f"Classified {i + 1}/{len(tickers)} tickers...")
                print(f"Classified {i + 1}/{len(tickers)} tickers...")

            # Periodic cache save
            if new_lookups % save_interval == 0:
                self._save_cache()
                logger.info(f"Saved cache ({len(self._cache)} entries)")

        # Final cache save
        if new_lookups > 0:
            self._save_cache()
            logger.info(f"Saved cache with {len(self._cache)} entries")

        return results

    def get_summary(self, classifications: Dict[str, Dict]) -> Dict:
        """
        Summarize classification results.

        Returns:
            Dict with counts by sector, asset type, and financial status
        """
        total = len(classifications)
        financial = sum(1 for c in classifications.values() if c.get('is_financial'))

        by_sector = {}
        by_type = {}
        by_source = {}

        for c in classifications.values():
            sector = c.get('sector') or 'unknown'
            asset_type = c.get('asset_type') or 'unknown'
            source = c.get('source') or 'unknown'

            by_sector[sector] = by_sector.get(sector, 0) + 1
            by_type[asset_type] = by_type.get(asset_type, 0) + 1
            by_source[source] = by_source.get(source, 0) + 1

        return {
            'total_tickers': total,
            'financial_count': financial,
            'non_financial_count': total - financial,
            'financial_pct': round(financial / total * 100, 1) if total else 0,
            'by_sector': dict(sorted(by_sector.items(), key=lambda x: -x[1])),
            'by_asset_type': dict(sorted(by_type.items(), key=lambda x: -x[1])),
            'by_source': by_source,
        }


def classify_uncached_tickers():
    """Classify tickers not in SEC cache."""
    from pathlib import Path
    import json

    # Load officials
    officials_path = Path(__file__).parent.parent / "data" / "current" / "officials.json"
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

    # Load SEC cache to find uncached
    sec_cache_path = Path(__file__).parent.parent / "data" / "cache" / "sec_ticker_sic_cache.json"
    if sec_cache_path.exists():
        with open(sec_cache_path) as f:
            sec_cache = json.load(f)
    else:
        sec_cache = {}

    # Find tickers not in SEC cache
    uncached = [t for t in tickers if t not in sec_cache]

    print(f"Total tickers: {len(tickers)}")
    print(f"In SEC cache: {len(tickers) - len(uncached)}")
    print(f"Need ETF classification: {len(uncached)}")

    if not uncached:
        print("All tickers already classified!")
        return {}, {}

    # Classify
    classifier = ETFClassifier()
    results = classifier.classify_tickers_bulk(uncached)

    # Summary
    summary = classifier.get_summary(results)
    print(f"\nETF Classification Summary:")
    print(f"  Total classified: {summary['total_tickers']}")
    print(f"  Financial: {summary['financial_count']} ({summary['financial_pct']}%)")
    print(f"\nBy asset type:")
    for atype, count in summary['by_asset_type'].items():
        print(f"  {atype}: {count}")
    print(f"\nBy sector (top 10):")
    for sector, count in list(summary['by_sector'].items())[:10]:
        print(f"  {sector}: {count}")
    print(f"\nBy source:")
    for source, count in summary['by_source'].items():
        print(f"  {source}: {count}")

    return results, summary


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    classify_uncached_tickers()
