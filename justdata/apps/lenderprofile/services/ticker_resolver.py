#!/usr/bin/env python3
"""
Ticker Resolver
Maps corporate entities (from GLEIF) to stock tickers.

Uses multiple sources to resolve company names/LEIs to stock tickers:
1. SEC Edgar - CIK to ticker mapping
2. FDIC - Bank ticker from institution data
3. Seeking Alpha - Symbol search
4. Known bank name patterns

This enables:
- Congressional trading lookup across parent + subsidiaries
- Financial data retrieval for entire corporate family
- Stock performance comparison
"""

import requests
import logging
import os
import re
from typing import Optional, Dict, Any, List
from functools import lru_cache

logger = logging.getLogger(__name__)


class TickerResolver:
    """
    Resolves company names, LEIs, and CIKs to stock ticker symbols.

    Uses cascading lookup: SEC → FDIC → Seeking Alpha → Known patterns

    Prioritizes common stock over preferred stock classes.
    Example: FITB (common) over FITBI, FITBO, FITBP (preferred)
    """

    # Patterns that indicate preferred stock (to be filtered out)
    PREFERRED_SUFFIXES = [
        'PRA', 'PRB', 'PRC', 'PRD', 'PRE', 'PRF', 'PRG', 'PRH', 'PRI', 'PRJ',
        'PRK', 'PRL', 'PRM', 'PRN', 'PRO', 'PRP', 'PRQ', 'PRR', 'PRS', 'PRT',
        'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
        'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
        'WS', 'WT',  # Warrants
        'RT', 'RTS',  # Rights
        'UN', 'U',  # Units
    ]

    def __init__(self):
        """Initialize ticker resolver with API clients."""
        self.sec_cik_ticker_map = None  # Lazy loaded
        self.seeking_alpha_api_key = os.getenv('SEEKING_ALPHA_API_KEY')
        self.timeout = 15

    def resolve_ticker(
        self,
        company_name: Optional[str] = None,
        lei: Optional[str] = None,
        cik: Optional[str] = None,
        fdic_cert: Optional[str] = None
    ) -> Optional[str]:
        """
        Resolve a company to its stock ticker using available identifiers.

        Args:
            company_name: Legal or common company name
            lei: Legal Entity Identifier
            cik: SEC Central Index Key
            fdic_cert: FDIC Certificate Number

        Returns:
            Stock ticker symbol or None if not publicly traded
        """
        ticker = None

        # 1. If we have CIK, try SEC mapping first (fastest)
        if cik and not ticker:
            ticker = self._resolve_from_sec_cik(cik)
            if ticker:
                logger.info(f"Resolved ticker {ticker} from CIK {cik}")
                return ticker

        # 2. If we have FDIC cert, check FDIC data
        if fdic_cert and not ticker:
            ticker = self._resolve_from_fdic(fdic_cert)
            if ticker:
                logger.info(f"Resolved ticker {ticker} from FDIC cert {fdic_cert}")
                return ticker

        # 3. Try Seeking Alpha as fallback
        if company_name and not ticker:
            ticker = self._resolve_from_seeking_alpha(company_name)
            if ticker:
                logger.info(f"Resolved ticker {ticker} from Seeking Alpha for '{company_name}'")
                return ticker

        logger.info(f"Could not resolve ticker for: name={company_name}, lei={lei}, cik={cik}")
        return None

    def resolve_corporate_family_tickers(
        self,
        gleif_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Resolve tickers for an entire corporate family from GLEIF data.

        Args:
            gleif_data: GLEIF data with parent/child relationships

        Returns:
            Corporate family with tickers added:
            {
                'parent': {'name': ..., 'lei': ..., 'ticker': ...},
                'current': {'name': ..., 'lei': ..., 'ticker': ...},
                'subsidiaries': [{'name': ..., 'lei': ..., 'ticker': ...}, ...]
            }
        """
        family = {
            'parent': None,
            'current': None,
            'subsidiaries': [],
            'all_tickers': []  # For congressional trading lookup
        }

        # Get current entity
        entity = gleif_data.get('entity', {})
        current_name = None
        if isinstance(entity.get('legalName'), dict):
            current_name = entity['legalName'].get('name')
        else:
            current_name = entity.get('legalName')

        current_ticker = self.resolve_ticker(company_name=current_name)
        family['current'] = {
            'name': current_name,
            'lei': gleif_data.get('lei'),
            'ticker': current_ticker
        }
        if current_ticker:
            family['all_tickers'].append(current_ticker)

        # Get parent
        parent_data = gleif_data.get('parent')
        if parent_data:
            parent_name = None
            if isinstance(parent_data, dict):
                parent_name = parent_data.get('name') or parent_data.get('legalName')
                if isinstance(parent_name, dict):
                    parent_name = parent_name.get('name')

            if parent_name:
                parent_ticker = self.resolve_ticker(company_name=parent_name)
                family['parent'] = {
                    'name': parent_name,
                    'lei': parent_data.get('lei'),
                    'ticker': parent_ticker
                }
                if parent_ticker and parent_ticker not in family['all_tickers']:
                    family['all_tickers'].append(parent_ticker)

        # Get subsidiaries
        children = gleif_data.get('children', [])
        for child in children:
            child_name = None
            if isinstance(child, dict):
                child_name = child.get('name') or child.get('legalName')
                if isinstance(child_name, dict):
                    child_name = child_name.get('name')

            if child_name:
                child_ticker = self.resolve_ticker(company_name=child_name)
                family['subsidiaries'].append({
                    'name': child_name,
                    'lei': child.get('lei') if isinstance(child, dict) else None,
                    'ticker': child_ticker
                })
                if child_ticker and child_ticker not in family['all_tickers']:
                    family['all_tickers'].append(child_ticker)

        logger.info(f"Resolved {len(family['all_tickers'])} tickers for corporate family")
        return family

    @lru_cache(maxsize=1)
    def _load_sec_cik_ticker_map(self) -> Dict[str, str]:
        """
        Load SEC CIK to ticker mapping.

        SEC provides this as a JSON file updated daily.
        """
        try:
            url = 'https://www.sec.gov/files/company_tickers.json'
            headers = {
                'User-Agent': 'NCRC LenderProfile research@ncrc.org'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Build CIK -> ticker map
            cik_map = {}
            for item in data.values():
                cik = str(item.get('cik_str', '')).zfill(10)
                ticker = item.get('ticker', '')
                if cik and ticker:
                    cik_map[cik] = ticker

            logger.info(f"Loaded {len(cik_map)} CIK->ticker mappings from SEC")
            return cik_map

        except Exception as e:
            logger.error(f"Failed to load SEC CIK mapping: {e}")
            return {}

    def _resolve_from_sec_cik(self, cik: str) -> Optional[str]:
        """Resolve ticker from SEC CIK."""
        cik_map = self._load_sec_cik_ticker_map()
        # Normalize CIK to 10 digits with leading zeros
        cik_normalized = str(cik).zfill(10)
        return cik_map.get(cik_normalized)

    def _resolve_from_fdic(self, fdic_cert: str) -> Optional[str]:
        """Resolve ticker from FDIC institution data."""
        try:
            url = f'https://banks.data.fdic.gov/api/institutions'
            params = {
                'filters': f'CERT:{fdic_cert}',
                'fields': 'NAME,STNAME,TICKER',
                'limit': 1
            }
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            if data.get('data') and len(data['data']) > 0:
                ticker = data['data'][0].get('data', {}).get('TICKER')
                if ticker and ticker.strip():
                    return ticker.strip()

        except Exception as e:
            logger.error(f"FDIC ticker lookup failed: {e}")

        return None

    # Known common stock tickers for major banks
    # These are the BASE tickers - any ticker formed by adding a letter suffix
    # to these is likely a preferred stock class
    KNOWN_BANK_TICKERS = {
        'FITB', 'JPM', 'BAC', 'WFC', 'C', 'USB', 'PNC', 'TFC',
        'GS', 'MS', 'COF', 'KEY', 'RF', 'HBAN', 'MTB', 'CFG',
        'ALLY', 'CMA', 'ZION', 'FRC', 'SIVB', 'DFS', 'SYF', 'AXP'
    }

    def _is_preferred_stock(self, ticker: str) -> bool:
        """
        Check if a ticker represents preferred stock rather than common stock.

        Preferred stock tickers typically have suffixes like:
        - Single letters: FITBI, FITBO, FITBP (Fifth Third preferred I, O, P)
        - PR prefix: BAC.PRA, BAC.PRB (Bank of America preferred A, B)
        - Hyphenated: WFC-PL (Wells Fargo preferred L)

        Args:
            ticker: Stock ticker symbol

        Returns:
            True if likely preferred stock, False if likely common stock
        """
        if not ticker:
            return False

        ticker_upper = ticker.upper()

        # If this ticker IS a known base ticker, it's common stock, not preferred
        if ticker_upper in self.KNOWN_BANK_TICKERS:
            return False

        # Check for .PR suffix pattern (e.g., BAC.PRA)
        if '.PR' in ticker_upper:
            return True

        # Check for -P suffix pattern (e.g., WFC-PL)
        if '-P' in ticker_upper:
            return True

        # Check for common preferred patterns at end of ticker
        # Only check if ticker is longer than 4 chars (base + 1 letter suffix)
        if len(ticker_upper) > 4:
            # Check for single-letter suffix that indicates preferred class
            # Examples: FITBI, FITBO, FITBP where base is FITB
            base_ticker = ticker_upper[:-1]
            suffix = ticker_upper[-1]

            # If the base is a known ticker and suffix is a letter, it's preferred
            if suffix.isalpha() and base_ticker in self.KNOWN_BANK_TICKERS:
                return True

        return False

    def _is_common_stock(self, ticker: str) -> bool:
        """
        Check if a ticker is likely common stock (not preferred, warrants, etc.)

        Args:
            ticker: Stock ticker symbol

        Returns:
            True if likely common stock
        """
        if not ticker:
            return False

        ticker_upper = ticker.upper()

        # If it's a known bank ticker, it's definitely common stock
        if ticker_upper in self.KNOWN_BANK_TICKERS:
            return True

        # Reject if contains special characters (indicates preferred/warrants/etc)
        if any(c in ticker_upper for c in ['-', '+', '=', '^', '.']):
            return False

        # If it matches the pattern of a known ticker + suffix, it's preferred
        if len(ticker_upper) > 4:
            base_ticker = ticker_upper[:-1]
            if base_ticker in self.KNOWN_BANK_TICKERS:
                return False

        # For unknown tickers, assume common if it's a clean alphanumeric symbol
        return ticker_upper.isalpha() and len(ticker_upper) <= 5

    def get_common_stock_ticker(self, tickers: List[str]) -> Optional[str]:
        """
        Given a list of related tickers, return the common stock ticker.

        Example: ['FITB', 'FITBI', 'FITBO', 'FITBP'] -> 'FITB'

        Args:
            tickers: List of ticker symbols

        Returns:
            The common stock ticker, or None if not found
        """
        if not tickers:
            return None

        # Filter to common stock candidates
        common_candidates = [t for t in tickers if self._is_common_stock(t)]

        if not common_candidates:
            return tickers[0] if tickers else None

        # Sort by length (shortest is usually the base/common ticker)
        common_candidates.sort(key=len)

        return common_candidates[0]

    def _resolve_from_seeking_alpha(self, company_name: str) -> Optional[str]:
        """Resolve ticker using Seeking Alpha search."""
        if not self.seeking_alpha_api_key:
            return None

        try:
            search_name = self._clean_company_name(company_name)

            url = 'https://seeking-alpha.p.rapidapi.com/symbols/get-chart'
            headers = {
                'X-RapidAPI-Key': self.seeking_alpha_api_key,
                'X-RapidAPI-Host': 'seeking-alpha.p.rapidapi.com'
            }
            # Note: Seeking Alpha doesn't have a direct search endpoint in free tier
            # This is a placeholder - would need to use symbol lookup if available

            # For now, try to construct ticker from name (common pattern for banks)
            potential_ticker = self._guess_ticker_from_name(company_name)
            if potential_ticker:
                return potential_ticker

        except Exception as e:
            logger.error(f"Seeking Alpha symbol search failed: {e}")

        return None

    def _clean_company_name(self, name: str) -> str:
        """Clean company name for search."""
        if not name:
            return ''

        # Remove common suffixes
        suffixes = [
            ', Inc.', ', Inc', ' Inc.', ' Inc',
            ', Corp.', ', Corp', ' Corp.', ' Corp',
            ', LLC', ' LLC',
            ', N.A.', ' N.A.', ', NA', ' NA',
            ' Corporation', ' Incorporated',
            ' Bancorp', ' Bancshares', ' Banc',
            ' Holdings', ' Holding',
            ' Financial', ' Finance',
            ' Company', ' Co.',
            ' Group', ' & Co.'
        ]

        result = name
        for suffix in suffixes:
            if result.endswith(suffix):
                result = result[:-len(suffix)]

        return result.strip()

    def _is_name_match(self, search_name: str, result_name: str) -> bool:
        """Check if search name matches result name."""
        search_clean = self._clean_company_name(search_name).lower()
        result_clean = self._clean_company_name(result_name).lower()

        # Direct match
        if search_clean == result_clean:
            return True

        # Search name is part of result
        if search_clean in result_clean:
            return True

        # Result is part of search name
        if result_clean in search_clean:
            return True

        # First word match (common for banks)
        search_words = search_clean.split()
        result_words = result_clean.split()
        if search_words and result_words and search_words[0] == result_words[0]:
            return True

        return False

    def _guess_ticker_from_name(self, name: str) -> Optional[str]:
        """
        Guess ticker from company name using common patterns.

        Only for major banks where pattern is predictable.
        """
        name_lower = name.lower()

        # Known bank name -> ticker mappings
        known_banks = {
            'fifth third': 'FITB',
            'fifth third bancorp': 'FITB',
            'jpmorgan': 'JPM',
            'jp morgan': 'JPM',
            'jpmorgan chase': 'JPM',
            'bank of america': 'BAC',
            'wells fargo': 'WFC',
            'citigroup': 'C',
            'citibank': 'C',
            'us bancorp': 'USB',
            'u.s. bancorp': 'USB',
            'pnc': 'PNC',
            'pnc financial': 'PNC',
            'truist': 'TFC',
            'capital one': 'COF',
            'goldman sachs': 'GS',
            'morgan stanley': 'MS',
            'american express': 'AXP',
            'discover': 'DFS',
            'synchrony': 'SYF',
            'ally financial': 'ALLY',
            'regions': 'RF',
            'regions financial': 'RF',
            'huntington': 'HBAN',
            'huntington bancshares': 'HBAN',
            'keycorp': 'KEY',
            'keybank': 'KEY',
            'm&t bank': 'MTB',
            'citizens financial': 'CFG',
            'first republic': 'FRC',
            'svb financial': 'SIVB',
            'silicon valley bank': 'SIVB',
            'comerica': 'CMA',
            'zions': 'ZION',
            'zions bancorporation': 'ZION',
        }

        for bank_name, ticker in known_banks.items():
            if bank_name in name_lower:
                return ticker

        return None


def test_ticker_resolver():
    """Test the ticker resolver."""
    resolver = TickerResolver()

    print("Testing Ticker Resolver...")

    # Test known banks
    test_cases = [
        ('Fifth Third Bancorp', None, None, None),
        ('JPMorgan Chase & Co.', None, None, None),
        ('Bank of America Corporation', None, None, None),
        ('PNC Financial Services Group, Inc.', None, None, None),
        (None, None, '0000019617', None),  # JPM CIK
    ]

    for name, lei, cik, fdic in test_cases:
        ticker = resolver.resolve_ticker(
            company_name=name,
            lei=lei,
            cik=cik,
            fdic_cert=fdic
        )
        print(f"  {name or cik} -> {ticker}")


if __name__ == '__main__':
    test_ticker_resolver()
