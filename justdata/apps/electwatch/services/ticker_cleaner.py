#!/usr/bin/env python3
"""
Ticker Data Cleaner for ElectWatch

Cleans dirty ticker/company data from STOCK Act disclosures.

Problem: Quiver API's 'Description' field often contains transaction text like:
- "SOLD 5,000 SHARES."
- "EXERCISED 50 CALL OPTIONS PURCHASED 1/14/25..."
- "CONTRIBUTION OF 28,200 SHARES TO DONOR-ADVISED FUND."

This module:
1. Detects if a company name is actually transaction text
2. Looks up proper company names from the SEC ticker cache
3. Classifies industries for tickers not in the FirmMapper

Author: Claude (Agent 4 - STOCK Act Data Cleaning)
Date: January 31, 2026
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, Optional, Tuple
from functools import lru_cache

logger = logging.getLogger(__name__)

# Path to SEC ticker cache
DATA_DIR = Path(__file__).parent.parent / "data"
SEC_CACHE_PATH = DATA_DIR / "cache" / "sec_ticker_sic_cache.json"


# =============================================================================
# TRANSACTION TEXT PATTERNS (indicates dirty company name)
# =============================================================================

TRANSACTION_PATTERNS = [
    r'^SOLD\s+',
    r'^PURCHASED\s+',
    r'^EXERCISED\s+',
    r'^CONTRIBUTION\s+OF',
    r'^EXCHANGE\s+',
    r'^RECEIVED\s+',
    r'^VESTED\s+',
    r'^DIVIDEND\s+',
    r'SHARES\.$',
    r'SHARES\s*$',
    r'CALL\s+OPTIONS',
    r'PUT\s+OPTIONS',
    r'STRIKE\s+PRICE',
    r'EXPIRATION\s+DATE',
    r'DONOR-ADVISED',
    r'WITHOUT\s+KNOWLEDGE',
    r'FORWARD\s+CONTRACT',
    r'NYSE\s+LISTED',
    r'ENTIRE\s+HOLDING',
    r'PART\s+OF\s+HOLDING',
    r'FOR\s+A\s+LOSS',
    r'SOLD\s+LOSS',
    r'CUSIP\s+\d',
    r'AT\s+A\s+PRICE\s+OF',
    r'AT\s+AVERAGE\s+PRICE',
]

# Compile patterns for efficiency
_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in TRANSACTION_PATTERNS]


def is_transaction_text(text: str) -> bool:
    """
    Check if text is actually a transaction description, not a company name.

    Examples:
        "SOLD 5,000 SHARES." -> True
        "Microsoft Corporation" -> False
        "EXERCISED 50 CALL OPTIONS..." -> True
        "NVDA" -> False
    """
    if not text:
        return False

    # Check against patterns
    for pattern in _COMPILED_PATTERNS:
        if pattern.search(text):
            return True

    # Check for common transaction keywords
    text_upper = text.upper()
    transaction_keywords = [
        'SOLD', 'PURCHASED', 'EXERCISED', 'CONTRIBUTION', 'EXCHANGE',
        'SHARES.', 'OPTIONS', 'STRIKE', 'EXPIRATION', 'DIVIDEND',
        'REINVESTMENT', 'VESTED', 'CUSIP'
    ]
    if any(kw in text_upper for kw in transaction_keywords):
        return True

    return False


# =============================================================================
# TICKER TO COMPANY LOOKUP
# =============================================================================

@lru_cache(maxsize=1)
def _load_sec_cache() -> Dict[str, Dict]:
    """Load SEC ticker cache (cached in memory)."""
    if not SEC_CACHE_PATH.exists():
        logger.warning(f"SEC ticker cache not found at {SEC_CACHE_PATH}")
        return {}

    try:
        with open(SEC_CACHE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.info(f"Loaded SEC ticker cache with {len(data)} tickers")
            return data
    except Exception as e:
        logger.error(f"Failed to load SEC ticker cache: {e}")
        return {}


def get_company_name_from_ticker(ticker: str) -> Optional[str]:
    """
    Look up company name from ticker using SEC cache.

    Args:
        ticker: Stock ticker symbol (e.g., 'MSFT', 'AAPL')

    Returns:
        Company name if found, None otherwise

    Example:
        get_company_name_from_ticker('MSFT') -> 'MICROSOFT CORP'
        get_company_name_from_ticker('AAPL') -> 'APPLE INC'
    """
    if not ticker:
        return None

    ticker = ticker.upper().strip()
    sec_cache = _load_sec_cache()

    if ticker in sec_cache:
        return sec_cache[ticker].get('company_name')

    return None


def get_ticker_info(ticker: str) -> Optional[Dict]:
    """
    Get full info for a ticker from SEC cache.

    Returns dict with:
        - ticker
        - company_name
        - sic (industry code)
        - sic_description
    """
    if not ticker:
        return None

    ticker = ticker.upper().strip()
    sec_cache = _load_sec_cache()

    return sec_cache.get(ticker)


# =============================================================================
# SIC TO FINANCIAL SECTOR MAPPING
# =============================================================================

# Known financial sector tickers that may have non-financial SIC codes
# (e.g., payment processors classified as "business services")
FINANCIAL_TICKER_OVERRIDES = {
    # Payment processors (often classified as business services)
    'V': 'fintech',       # Visa
    'MA': 'fintech',      # Mastercard
    'PYPL': 'fintech',    # PayPal
    'SQ': 'fintech',      # Block/Square
    'FIS': 'fintech',     # FIS
    'FI': 'fintech',      # Fiserv
    'FISV': 'fintech',    # Fiserv (alternate ticker)
    'GPN': 'fintech',     # Global Payments
    'PAYX': 'fintech',    # Paychex (payroll processing)
    'ADP': 'fintech',     # ADP (payroll processing)
    'FLYW': 'fintech',    # Flywire (payments)
    'INTU': 'fintech',    # Intuit

    # Mortgage (may be classified as real estate)
    'RKT': 'mortgage',    # Rocket Companies
    'UWMC': 'mortgage',   # United Wholesale Mortgage

    # Consumer lending
    'SOFI': 'consumer_lending',  # SoFi
    'AFRM': 'consumer_lending',  # Affirm
    'OMF': 'consumer_lending',   # OneMain Holdings

    # Crypto (often classified as tech/software)
    'COIN': 'crypto',     # Coinbase
    'HOOD': 'crypto',     # Robinhood
    'MSTR': 'crypto',     # MicroStrategy

    # Credit bureaus
    'EFX': 'fintech',     # Equifax
    'TRU': 'fintech',     # TransUnion
}


# Map SIC codes to ElectWatch financial sectors
SIC_TO_SECTOR = {
    # Banking & Depository (SIC 60xx)
    '6020': 'banking',  # Commercial Banks
    '6021': 'banking',  # National Commercial Banks
    '6022': 'banking',  # State Commercial Banks
    '6029': 'banking',  # Commercial Banks, NEC
    '6035': 'banking',  # Savings Institutions, Federally Chartered
    '6036': 'banking',  # Savings Institutions, Not Federally Chartered
    '6061': 'banking',  # Credit Unions, Federally Chartered
    '6062': 'banking',  # Credit Unions, Not Federally Chartered

    # Consumer Lending (SIC 61xx)
    '6141': 'consumer_lending',  # Personal Credit Institutions
    '6153': 'consumer_lending',  # Short-Term Business Credit
    '6159': 'consumer_lending',  # Misc Business Credit Institutions

    # Mortgage (SIC 61xx)
    '6162': 'mortgage',  # Mortgage Bankers & Loan Correspondents
    '6163': 'mortgage',  # Loan Brokers

    # Investment (SIC 62xx)
    '6200': 'investment',  # Securities & Commodity Brokers
    '6211': 'investment',  # Security Brokers & Dealers
    '6221': 'investment',  # Commodity Contracts Dealers & Brokers
    '6282': 'investment',  # Investment Advice
    '6289': 'investment',  # Services Allied With The Exchange Of Securities

    # Insurance (SIC 63xx, 64xx)
    '6311': 'insurance',  # Life Insurance
    '6321': 'insurance',  # Accident & Health Insurance
    '6324': 'insurance',  # Hospital & Medical Service Plans
    '6331': 'insurance',  # Fire, Marine & Casualty Insurance
    '6351': 'insurance',  # Surety Insurance
    '6361': 'insurance',  # Title Insurance
    '6399': 'insurance',  # Insurance Carriers, NEC
    '6411': 'insurance',  # Insurance Agents, Brokers & Service

    # Real Estate / Mortgage Adjacent (SIC 65xx)
    '6512': 'mortgage',  # Operators of Nonresidential Buildings
    '6531': 'mortgage',  # Real Estate Agents & Managers
    '6552': 'mortgage',  # Land Subdividers & Developers

    # Holding Companies (SIC 67xx)
    '6712': 'investment',  # Offices of Bank Holding Companies
    '6719': 'investment',  # Offices of Holding Companies, NEC
    '6722': 'investment',  # Management Investment Offices, Open-End
    '6726': 'investment',  # Other Investment Offices
    '6792': 'investment',  # Oil Royalty Traders
    '6794': 'investment',  # Patent Owners & Lessors
    '6798': 'mortgage',  # Real Estate Investment Trusts
    '6799': 'investment',  # Investors, NEC

    # Fintech (often classified under business services)
    '7370': 'fintech',  # Services-Computer Programming, Data Processing
    '7371': 'fintech',  # Services-Computer Programming Services
    '7372': 'fintech',  # Services-Prepackaged Software
    '7374': 'fintech',  # Services-Computer Processing & Data Preparation
}


def get_sector_from_sic(sic_code: str) -> Optional[str]:
    """
    Map SIC code to ElectWatch financial sector.

    Args:
        sic_code: 4-digit SIC code

    Returns:
        Sector code (e.g., 'banking', 'investment') or None if not financial
    """
    if not sic_code:
        return None

    # Try exact match
    if sic_code in SIC_TO_SECTOR:
        return SIC_TO_SECTOR[sic_code]

    # Try 2-digit prefix for broader matching
    prefix = sic_code[:2]
    if prefix == '60':
        return 'banking'
    elif prefix == '61':
        return 'consumer_lending'
    elif prefix == '62':
        return 'investment'
    elif prefix == '63' or prefix == '64':
        return 'insurance'
    elif prefix == '65':
        return 'mortgage'
    elif prefix == '67':
        return 'investment'

    return None


def classify_ticker_industry(ticker: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Classify a ticker's industry using SEC SIC codes with financial overrides.

    Priority:
    1. Check FINANCIAL_TICKER_OVERRIDES for known financial companies with non-financial SIC codes
    2. Use SIC code classification

    Args:
        ticker: Stock ticker symbol

    Returns:
        Tuple of (sector, sic_description) or (None, None) if not found/not financial

    Example:
        classify_ticker_industry('JPM') -> ('banking', 'National Commercial Banks')
        classify_ticker_industry('V') -> ('fintech', 'Payment Processor')  # Override
    """
    if not ticker:
        return None, None

    ticker = ticker.upper().strip()

    # Check override first (for known financial companies with non-financial SIC codes)
    if ticker in FINANCIAL_TICKER_OVERRIDES:
        sector = FINANCIAL_TICKER_OVERRIDES[ticker]
        return sector, f"Financial Services ({sector.title()})"

    # Fall back to SIC code classification
    info = get_ticker_info(ticker)
    if not info:
        return None, None

    sic = info.get('sic')
    sic_desc = info.get('sic_description')
    sector = get_sector_from_sic(sic)

    return sector, sic_desc


# =============================================================================
# CLEAN COMPANY NAME
# =============================================================================

def clean_company_name(ticker: str, dirty_name: Optional[str]) -> str:
    """
    Get a clean company name for a ticker.

    Priority:
    1. If dirty_name is valid (not transaction text), use it
    2. Look up from SEC cache
    3. Fall back to ticker itself

    Args:
        ticker: Stock ticker symbol
        dirty_name: Potentially dirty company name from data source

    Returns:
        Clean company name

    Examples:
        clean_company_name('AAPL', None) -> 'APPLE INC'
        clean_company_name('MSFT', 'SOLD 5,000 SHARES.') -> 'MICROSOFT CORP'
        clean_company_name('GOOGL', 'Alphabet Inc.') -> 'Alphabet Inc.'
    """
    # If we have a valid name that's not transaction text, use it
    if dirty_name and not is_transaction_text(dirty_name):
        return dirty_name

    # Look up from SEC cache
    sec_name = get_company_name_from_ticker(ticker)
    if sec_name:
        return sec_name

    # Fall back to ticker
    return ticker or 'Unknown'


# =============================================================================
# BATCH PROCESSING
# =============================================================================

def clean_trade_records(trades: list) -> list:
    """
    Clean company names in a batch of trade records.

    Args:
        trades: List of trade dicts with 'ticker' and 'company' fields

    Returns:
        Same list with cleaned 'company' fields
    """
    for trade in trades:
        ticker = trade.get('ticker', '')
        dirty_company = trade.get('company')
        trade['company'] = clean_company_name(ticker, dirty_company)

    return trades


def clean_firms_data(firms: list) -> list:
    """
    Clean firm names and add industry classifications.

    Args:
        firms: List of firm dicts with 'ticker' and 'name' fields

    Returns:
        Same list with cleaned 'name' fields and updated 'sector'/'industry'
    """
    for firm in firms:
        ticker = firm.get('ticker', '')
        dirty_name = firm.get('name')

        # Clean the name
        firm['name'] = clean_company_name(ticker, dirty_name)

        # Add industry classification if missing
        if not firm.get('sector') or firm.get('sector') == '':
            sector, sic_desc = classify_ticker_industry(ticker)
            if sector:
                firm['sector'] = sector
                firm['industry'] = sector
                firm['sic_description'] = sic_desc

    return firms


# =============================================================================
# REPROCESS EXISTING DATA
# =============================================================================

def reprocess_firms_json(input_path: Path, output_path: Optional[Path] = None) -> Dict:
    """
    Reprocess a firms.json file to clean dirty data.

    Args:
        input_path: Path to firms.json
        output_path: Path for cleaned output (defaults to same as input)

    Returns:
        Statistics about the cleaning process
    """
    if output_path is None:
        output_path = input_path

    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        return {'error': 'File not found'}

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    firms = data.get('firms', [])
    if not firms:
        logger.warning(f"No firms found in {input_path}")
        return {'cleaned': 0, 'total': 0}

    # Track statistics
    stats = {
        'total': len(firms),
        'had_transaction_text': 0,
        'had_null_name': 0,
        'had_empty_sector': 0,
        'cleaned_names': 0,
        'added_sectors': 0
    }

    for firm in firms:
        ticker = firm.get('ticker', '')
        original_name = firm.get('name')
        original_sector = firm.get('sector')

        # Check for issues
        if original_name and is_transaction_text(original_name):
            stats['had_transaction_text'] += 1
        if original_name in [None, 'null', 'NULL', '']:
            stats['had_null_name'] += 1
        if not original_sector or original_sector in ['', 'OTHER', None]:
            stats['had_empty_sector'] += 1

        # Clean name
        new_name = clean_company_name(ticker, original_name)
        if new_name != original_name:
            firm['name'] = new_name
            stats['cleaned_names'] += 1

        # Add sector if missing
        if not firm.get('sector') or firm.get('sector') in ['', 'OTHER']:
            sector, sic_desc = classify_ticker_industry(ticker)
            if sector:
                firm['sector'] = sector
                firm['industry'] = sector
                firm['sic_description'] = sic_desc
                stats['added_sectors'] += 1

    # Rebuild by_name index
    data['firms'] = firms
    data['by_name'] = {f['name']: f for f in firms if f.get('name')}
    data['count'] = len(firms)

    # Save
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    logger.info(f"Reprocessed {stats['total']} firms: "
                f"{stats['cleaned_names']} names cleaned, "
                f"{stats['added_sectors']} sectors added")

    return stats


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    import sys

    logging.basicConfig(level=logging.INFO)

    print("Testing Ticker Cleaner")
    print("=" * 60)

    # Test transaction text detection
    print("\n=== Transaction Text Detection ===")
    test_cases = [
        "SOLD 5,000 SHARES.",
        "Microsoft Corporation",
        "EXERCISED 50 CALL OPTIONS PURCHASED 1/14/25...",
        "NVDA",
        "CONTRIBUTION OF 28,200 SHARES TO DONOR-ADVISED FUND.",
        "Apple Inc.",
        "DIVIDEND REINVESTMENT",
        "JPMorgan Chase & Co.",
        None,
    ]
    for text in test_cases:
        result = is_transaction_text(text) if text else "N/A (None)"
        print(f"  {text!r:55} -> {result}")

    # Test company name lookup
    print("\n=== SEC Company Name Lookup ===")
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'JPM', 'WFC', 'NVDA', 'TSLA', 'META', 'AMZN', 'COIN']
    for ticker in tickers:
        name = get_company_name_from_ticker(ticker)
        print(f"  {ticker:6} -> {name or 'Not found'}")

    # Test industry classification
    print("\n=== Industry Classification ===")
    financial_tickers = ['JPM', 'WFC', 'GS', 'V', 'MA', 'BLK', 'MET', 'AIG', 'RKT', 'COIN']
    for ticker in financial_tickers:
        sector, sic_desc = classify_ticker_industry(ticker)
        print(f"  {ticker:6} -> {sector or 'non-financial':20} ({sic_desc or 'N/A'})")

    # Test clean_company_name
    print("\n=== Clean Company Name ===")
    dirty_cases = [
        ('AAPL', None),
        ('MSFT', 'SOLD 5,000 SHARES.'),
        ('GOOGL', 'Alphabet Inc.'),
        ('NVDA', 'EXERCISED 50 CALL OPTIONS...'),
        ('XYZ123', 'Unknown Ticker'),
    ]
    for ticker, dirty in dirty_cases:
        clean = clean_company_name(ticker, dirty)
        print(f"  ({ticker}, {dirty!r:30}) -> {clean!r}")

    # If a file path is provided, reprocess it
    if len(sys.argv) > 1:
        print(f"\n=== Reprocessing {sys.argv[1]} ===")
        stats = reprocess_firms_json(Path(sys.argv[1]))
        print(f"  Statistics: {stats}")
