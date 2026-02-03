#!/usr/bin/env python3
"""
DEPRECATED: Employer Classification for ElectWatch.

WARNING: This module uses keyword pattern matching which causes massive false positives.
The production pipeline (fec_bulk.py) uses firm_matcher.py instead, which:
1. Extracts firm names from PAC connected organizations
2. Uses exclusion patterns to filter universities, government, medical, etc.
3. Only matches employers against verified financial firms

This file is kept for reference but should NOT be used.
Use firm_matcher.FirmMatcher instead.

--- Original description ---
Classifies employer names into financial sector subsectors using pattern matching.
Similar approach to PAC classification but for individual contributors.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Cache directory
CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"
EMPLOYER_CACHE_FILE = CACHE_DIR / "employer_classification_cache.json"


# Financial employer patterns
# Format: (keywords, sector, subsector)
EMPLOYER_PATTERNS = [
    # Banking - Major banks
    (['JPMORGAN', 'JP MORGAN'], 'banking', 'major_bank'),
    (['BANK OF AMERICA', 'BOFA'], 'banking', 'major_bank'),
    (['WELLS FARGO'], 'banking', 'major_bank'),
    (['CITIBANK', 'CITIGROUP', 'CITI '], 'banking', 'major_bank'),
    (['GOLDMAN SACHS', 'GOLDMAN, SACHS'], 'investment_banking', 'investment_bank'),
    (['MORGAN STANLEY'], 'investment_banking', 'investment_bank'),

    # Banking - Regional banks
    (['PNC BANK', 'PNC FINANCIAL'], 'banking', 'regional_bank'),
    (['TRUIST', 'SUNTRUST', 'BB&T'], 'banking', 'regional_bank'),
    (['U.S. BANK', 'US BANCORP', 'USB '], 'banking', 'regional_bank'),
    (['REGIONS BANK', 'REGIONS FINANCIAL'], 'banking', 'regional_bank'),
    (['FIFTH THIRD'], 'banking', 'regional_bank'),
    (['KEYBANK', 'KEYCORP'], 'banking', 'regional_bank'),
    (['CITIZENS BANK', 'CITIZENS FINANCIAL'], 'banking', 'regional_bank'),
    (['M&T BANK'], 'banking', 'regional_bank'),
    (['HUNTINGTON BANK', 'HUNTINGTON NATIONAL'], 'banking', 'regional_bank'),
    (['ZIONS BANK', 'ZIONS BANCORP'], 'banking', 'regional_bank'),
    (['COMERICA'], 'banking', 'regional_bank'),
    (['FIRST HORIZON'], 'banking', 'regional_bank'),
    (['WEBSTER BANK'], 'banking', 'regional_bank'),
    (['SANTANDER'], 'banking', 'regional_bank'),
    (['BMO HARRIS', 'BMO FINANCIAL'], 'banking', 'regional_bank'),
    (['TD BANK'], 'banking', 'regional_bank'),

    # Community banks (generic patterns)
    (['COMMUNITY BANK'], 'banking', 'community_bank'),
    (['SAVINGS BANK'], 'banking', 'community_bank'),
    (['NATIONAL BANK'], 'banking', 'community_bank'),
    (['STATE BANK'], 'banking', 'community_bank'),

    # Credit Unions
    (['CREDIT UNION', 'FCU', 'FEDERAL CREDIT UNION'], 'credit_unions', 'institution'),
    (['CUNA', 'NAFCU'], 'credit_unions', 'trade_association'),

    # Mortgage/Lending
    (['ROCKET MORTGAGE', 'QUICKEN LOANS'], 'lending', 'mortgage'),
    (['LOAN DEPOT', 'LOANDEPOT'], 'lending', 'mortgage'),
    (['UNITED WHOLESALE', 'UWM'], 'lending', 'mortgage'),
    (['PENNYMAC'], 'lending', 'mortgage'),
    (['FREEDOM MORTGAGE'], 'lending', 'mortgage'),
    (['NEWREZ', 'NEW RESIDENTIAL'], 'lending', 'mortgage'),
    (['MR. COOPER', 'NATIONSTAR'], 'lending', 'mortgage'),
    (['CALIBER HOME'], 'lending', 'mortgage'),
    (['FANNIE MAE', 'FNMA'], 'lending', 'gse'),
    (['FREDDIE MAC', 'FHLMC'], 'lending', 'gse'),
    (['SALLIE MAE'], 'lending', 'student'),
    (['NAVIENT'], 'lending', 'student'),

    # Insurance - Major insurers
    (['AFLAC'], 'insurance', 'life_health'),
    (['METLIFE'], 'insurance', 'life_health'),
    (['PRUDENTIAL'], 'insurance', 'life_health'),
    (['NEW YORK LIFE'], 'insurance', 'life_health'),
    (['MASSACHUSETTS MUTUAL', 'MASSMUTUAL'], 'insurance', 'life_health'),
    (['NORTHWESTERN MUTUAL'], 'insurance', 'life_health'),
    (['LINCOLN NATIONAL', 'LINCOLN FINANCIAL'], 'insurance', 'life_health'),
    (['PRINCIPAL FINANCIAL'], 'insurance', 'life_health'),
    (['UNUM'], 'insurance', 'life_health'),

    # Insurance - Health
    (['CIGNA'], 'insurance', 'health'),
    (['AETNA'], 'insurance', 'health'),
    (['ANTHEM'], 'insurance', 'health'),
    (['BLUE CROSS', 'BLUE SHIELD', 'BCBS'], 'insurance', 'health'),
    (['UNITEDHEALTH GROUP', 'UNITEDHEALTHCARE', 'UHC '], 'insurance', 'health'),
    (['HUMANA'], 'insurance', 'health'),
    (['CENTENE'], 'insurance', 'health'),
    (['MOLINA HEALTHCARE'], 'insurance', 'health'),
    (['CVS HEALTH', 'CVS CAREMARK'], 'insurance', 'health'),
    (['KAISER PERMANENTE'], 'insurance', 'health'),
    (['HIGHMARK'], 'insurance', 'health'),
    (['EMBLEM HEALTH'], 'insurance', 'health'),

    # Insurance - Property/Casualty
    (['ALLSTATE'], 'insurance', 'property_casualty'),
    (['STATE FARM'], 'insurance', 'property_casualty'),
    (['PROGRESSIVE INSURANCE', 'PROGRESSIVE CORP'], 'insurance', 'property_casualty'),
    (['LIBERTY MUTUAL'], 'insurance', 'property_casualty'),
    (['TRAVELERS'], 'insurance', 'property_casualty'),
    (['HARTFORD'], 'insurance', 'property_casualty'),
    (['CHUBB'], 'insurance', 'property_casualty'),
    (['NATIONWIDE'], 'insurance', 'property_casualty'),
    (['USAA'], 'insurance', 'property_casualty'),
    (['GEICO'], 'insurance', 'property_casualty'),
    (['AIG', 'AMERICAN INTERNATIONAL GROUP'], 'insurance', 'conglomerate'),
    (['ZURICH'], 'insurance', 'property_casualty'),
    (['FARMERS INSURANCE'], 'insurance', 'property_casualty'),
    (['ERIE INSURANCE'], 'insurance', 'property_casualty'),
    (['AMERICAN FAMILY'], 'insurance', 'property_casualty'),
    (['ARBELLA'], 'insurance', 'property_casualty'),

    # Insurance - Generic patterns
    (['INSURANCE COMPANY', 'INSURANCE GROUP', 'INSURANCE SERVICES'], 'insurance', 'general'),
    (['MUTUAL INSURANCE'], 'insurance', 'mutual'),

    # Investment/Asset Management
    (['BLACKROCK'], 'investment', 'asset_management'),
    (['VANGUARD'], 'investment', 'asset_management'),
    (['FIDELITY INVESTMENTS', 'FMR LLC'], 'investment', 'asset_management'),
    (['STATE STREET'], 'investment', 'asset_management'),
    (['T. ROWE PRICE', 'T ROWE PRICE'], 'investment', 'asset_management'),
    (['PIMCO'], 'investment', 'asset_management'),
    (['INVESCO'], 'investment', 'asset_management'),
    (['FRANKLIN TEMPLETON'], 'investment', 'asset_management'),
    (['CAPITAL GROUP', 'AMERICAN FUNDS'], 'investment', 'asset_management'),
    (['NUVEEN'], 'investment', 'asset_management'),
    (['LEGG MASON'], 'investment', 'asset_management'),
    (['JANUS HENDERSON'], 'investment', 'asset_management'),
    (['ALLIANCE BERNSTEIN', 'ALLIANCEBERNSTEIN'], 'investment', 'asset_management'),

    # Brokerages
    (['SCHWAB', 'CHARLES SCHWAB'], 'investment', 'brokerage'),
    (['EDWARD JONES'], 'investment', 'brokerage'),
    (['RAYMOND JAMES'], 'investment', 'brokerage'),
    (['AMERIPRISE'], 'investment', 'brokerage'),
    (['LPL FINANCIAL'], 'investment', 'brokerage'),
    (['INTERACTIVE BROKERS'], 'investment', 'brokerage'),
    (['E*TRADE', 'ETRADE'], 'investment', 'brokerage'),
    (['TD AMERITRADE'], 'investment', 'brokerage'),
    (['MERRILL LYNCH'], 'investment', 'brokerage'),
    (['UBS '], 'investment', 'brokerage'),
    (['CREDIT SUISSE'], 'investment', 'brokerage'),

    # Retirement/Pension
    (['TIAA', 'TEACHERS INSURANCE ANNUITY'], 'investment', 'retirement'),

    # Private Equity
    (['BLACKSTONE'], 'private_equity', 'buyout'),
    (['KKR', 'KOHLBERG KRAVIS'], 'private_equity', 'buyout'),
    (['CARLYLE GROUP'], 'private_equity', 'buyout'),
    (['APOLLO GLOBAL', 'APOLLO MANAGEMENT'], 'private_equity', 'buyout'),
    (['TPG CAPITAL', 'TEXAS PACIFIC'], 'private_equity', 'buyout'),
    (['BAIN CAPITAL'], 'private_equity', 'buyout'),
    (['WARBURG PINCUS'], 'private_equity', 'buyout'),
    (['ADVENT INTERNATIONAL'], 'private_equity', 'buyout'),
    (['GENERAL ATLANTIC'], 'private_equity', 'growth'),
    (['SILVER LAKE'], 'private_equity', 'tech'),
    (['THOMA BRAVO'], 'private_equity', 'tech'),
    (['VISTA EQUITY'], 'private_equity', 'tech'),

    # Venture Capital
    (['SEQUOIA CAPITAL'], 'private_equity', 'venture'),
    (['ANDREESSEN HOROWITZ', 'A16Z'], 'private_equity', 'venture'),
    (['BENCHMARK'], 'private_equity', 'venture'),
    (['ACCEL'], 'private_equity', 'venture'),
    (['KLEINER PERKINS'], 'private_equity', 'venture'),
    (['GREYLOCK'], 'private_equity', 'venture'),
    (['NEA', 'NEW ENTERPRISE ASSOCIATES'], 'private_equity', 'venture'),
    (['LIGHTSPEED VENTURE'], 'private_equity', 'venture'),
    (['INSIGHT PARTNERS'], 'private_equity', 'growth'),
    (['SV ANGEL'], 'private_equity', 'venture'),
    (['WESTLY GROUP'], 'private_equity', 'venture'),

    # Hedge Funds
    (['CITADEL'], 'investment', 'hedge_fund'),
    (['BRIDGEWATER'], 'investment', 'hedge_fund'),
    (['TWO SIGMA'], 'investment', 'hedge_fund'),
    (['RENAISSANCE'], 'investment', 'hedge_fund'),
    (['D.E. SHAW', 'DE SHAW'], 'investment', 'hedge_fund'),
    (['POINT72'], 'investment', 'hedge_fund'),
    (['MILLENNIUM'], 'investment', 'hedge_fund'),
    (['AQR CAPITAL'], 'investment', 'hedge_fund'),
    (['ELLIOTT MANAGEMENT'], 'investment', 'hedge_fund'),
    (['BAUPOST'], 'investment', 'hedge_fund'),

    # Payments/Fintech
    (['VISA'], 'payments', 'card_network'),
    (['MASTERCARD'], 'payments', 'card_network'),
    (['AMERICAN EXPRESS', 'AMEX'], 'payments', 'card_issuer'),
    (['DISCOVER FINANCIAL'], 'payments', 'card_issuer'),
    (['CAPITAL ONE'], 'payments', 'card_issuer'),
    (['SYNCHRONY'], 'payments', 'card_issuer'),
    (['PAYPAL'], 'payments', 'digital'),
    (['SQUARE', 'BLOCK INC'], 'payments', 'digital'),
    (['STRIPE'], 'payments', 'digital'),
    (['FISERV'], 'payments', 'processing'),
    (['FIS ', 'FIDELITY NATIONAL INFO'], 'payments', 'processing'),
    (['GLOBAL PAYMENTS'], 'payments', 'processing'),
    (['WORLDPAY'], 'payments', 'processing'),
    (['PAYCHEX'], 'payments', 'payroll'),
    (['ADP'], 'payments', 'payroll'),
    (['INTUIT'], 'payments', 'software'),

    # Real Estate - Brokerages
    (['CBRE'], 'real_estate', 'commercial'),
    (['JLL', 'JONES LANG'], 'real_estate', 'commercial'),
    (['CUSHMAN & WAKEFIELD', 'CUSHMAN WAKEFIELD'], 'real_estate', 'commercial'),
    (['COLLIERS'], 'real_estate', 'commercial'),
    (['NEWMARK'], 'real_estate', 'commercial'),
    (['COLDWELL BANKER'], 'real_estate', 'residential'),
    (['KELLER WILLIAMS'], 'real_estate', 'residential'),
    (['REMAX', 'RE/MAX'], 'real_estate', 'residential'),
    (['COMPASS REAL ESTATE', 'COMPASS INC'], 'real_estate', 'residential'),
    (['REALOGY', 'ANYWHERE REAL ESTATE'], 'real_estate', 'residential'),
    (['SOTHEBYS', 'SOTHEBY\'S'], 'real_estate', 'residential'),
    (['DOUGLAS ELLIMAN'], 'real_estate', 'residential'),
    (['WEICHERT'], 'real_estate', 'residential'),
    (['HOWARD HANNA'], 'real_estate', 'residential'),
    (['LONG & FOSTER', 'LONG AND FOSTER'], 'real_estate', 'residential'),

    # Real Estate - REITs and Developers
    (['PROLOGIS'], 'real_estate', 'reit'),
    (['SIMON PROPERTY'], 'real_estate', 'reit'),
    (['EQUINIX'], 'real_estate', 'reit'),
    (['PUBLIC STORAGE'], 'real_estate', 'reit'),
    (['DIGITAL REALTY'], 'real_estate', 'reit'),
    (['WELLTOWER'], 'real_estate', 'reit'),
    (['BROOKFIELD'], 'real_estate', 'developer'),
    (['RELATED COMPANIES'], 'real_estate', 'developer'),
    (['HINES'], 'real_estate', 'developer'),
    (['TISHMAN SPEYER'], 'real_estate', 'developer'),
    (['LENNAR'], 'real_estate', 'homebuilder'),
    (['D.R. HORTON', 'DR HORTON'], 'real_estate', 'homebuilder'),
    (['PULTE', 'PULTEGROUP'], 'real_estate', 'homebuilder'),
    (['KB HOME', 'KB HOMES'], 'real_estate', 'homebuilder'),
    (['TOLL BROTHERS'], 'real_estate', 'homebuilder'),
    (['MERITAGE HOMES'], 'real_estate', 'homebuilder'),
    (['NVR INC'], 'real_estate', 'homebuilder'),
    (['TAYLOR MORRISON'], 'real_estate', 'homebuilder'),

    # Real Estate - Title/Services
    (['FIRST AMERICAN TITLE', 'FIRST AMERICAN FINANCIAL'], 'real_estate', 'title'),
    (['FIDELITY NATIONAL TITLE'], 'real_estate', 'title'),
    (['OLD REPUBLIC'], 'real_estate', 'title'),
    (['STEWART TITLE', 'STEWART INFORMATION'], 'real_estate', 'title'),
    (['TITLE INSURANCE'], 'real_estate', 'title'),

    # Securities/Exchanges
    (['NYSE', 'NEW YORK STOCK EXCHANGE'], 'securities', 'exchange'),
    (['NASDAQ'], 'securities', 'exchange'),
    (['CME GROUP'], 'securities', 'exchange'),
    (['ICE INC', 'INTERCONTINENTAL EXCHANGE'], 'securities', 'exchange'),
    (['CBOE'], 'securities', 'exchange'),

    # Generic financial patterns (lower priority - will be overridden by specific matches)
    (['BANK'], 'banking', 'general'),
    (['BANKING'], 'banking', 'general'),
    (['BANKERS'], 'banking', 'general'),
    (['BANCORP'], 'banking', 'general'),
    (['BANCSHARES'], 'banking', 'general'),
    (['INSURANCE'], 'insurance', 'general'),
    (['INVESTMENT'], 'investment', 'general'),
    (['SECURITIES'], 'securities', 'general'),
    (['CAPITAL MANAGEMENT'], 'investment', 'asset_management'),
    (['ASSET MANAGEMENT'], 'investment', 'asset_management'),
    (['FINANCIAL SERVICES'], 'financial_services', 'general'),
    (['FINANCIAL ADVISOR'], 'investment', 'advisory'),
    (['WEALTH MANAGEMENT'], 'investment', 'wealth'),
]


# Exclusion patterns - these indicate NOT financial sector
EXCLUSION_PATTERNS = [
    # Labor unions
    'SEIU', 'SERVICE EMPLOYEES INTERNATIONAL',
    'AFSCME', 'AMERICAN FEDERATION OF STATE',
    'AFT', 'AMERICAN FEDERATION OF TEACHERS',
    'UNITE HERE',
    'UFCW', 'UNITED FOOD AND COMMERCIAL',
    'IBEW', 'INTERNATIONAL BROTHERHOOD OF ELECTRICAL',
    'TEAMSTERS',
    'UAW', 'UNITED AUTO WORKERS',
    'USW', 'UNITED STEELWORKERS',
    'CWA', 'COMMUNICATIONS WORKERS',
    'NURSES UNITED', 'NATIONAL NURSES',
    'HEALTHCARE WORKERS',

    # Non-financial organizations
    'RETIRED', 'NOT EMPLOYED', 'HOMEMAKER', 'UNEMPLOYED', 'NONE',
    'SELF-EMPLOYED', 'SELF EMPLOYED',
    'US GOVERNMENT', 'FEDERAL GOVERNMENT', 'STATE OF ',
    'UNIVERSITY', 'COLLEGE', 'SCHOOL DISTRICT',
    'HOSPITAL', 'MEDICAL CENTER', 'HEALTHCARE SYSTEM',
    'CHURCH', 'MINISTRY',
    'FOUNDATION', 'NONPROFIT', 'NON-PROFIT',

    # Banks that aren't banks
    'FOOD BANK', 'BLOOD BANK', 'SPERM BANK', 'SEED BANK',
    'RIVER BANK', 'WEST BANK', 'BANK SHOT', 'DATA BANK',
    'EUBANKS', 'FAIRBANKS', 'BURBANK', 'BRAINBANK',

    # Insurance that isn't insurance companies
    'TITLE SEARCH', 'ABSTRACT COMPANY',

    # False positive triggers
    'PROGRESSIVE EDUCATION', 'PROGRESSIVE POLICY',
]


class EmployerClassifier:
    """Classifies employers into financial sector subsectors."""

    def __init__(self):
        self._cache: Dict[str, Dict] = {}
        self._load_cache()

    def _load_cache(self):
        """Load cached classifications."""
        if EMPLOYER_CACHE_FILE.exists():
            try:
                with open(EMPLOYER_CACHE_FILE) as f:
                    self._cache = json.load(f)
                logger.info(f"Loaded {len(self._cache)} cached employer classifications")
            except Exception as e:
                logger.warning(f"Failed to load employer cache: {e}")
                self._cache = {}

    def _save_cache(self):
        """Save cache to disk."""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(EMPLOYER_CACHE_FILE, 'w') as f:
            json.dump(self._cache, f, indent=2)

    def classify_employer(self, employer: str) -> Dict:
        """
        Classify an employer by name.

        Returns:
            Dict with keys: employer, is_financial, sector, subsector, confidence
        """
        employer = employer.upper().strip()

        if employer in self._cache:
            return self._cache[employer]

        result = {
            'employer': employer,
            'is_financial': False,
            'sector': None,
            'subsector': None,
            'confidence': 'none',
        }

        # Check exclusions first
        for exclusion in EXCLUSION_PATTERNS:
            if exclusion in employer:
                self._cache[employer] = result
                return result

        # Try matching patterns
        for keywords, sector, subsector in EMPLOYER_PATTERNS:
            for kw in keywords:
                if kw in employer:
                    result['is_financial'] = True
                    result['sector'] = sector
                    result['subsector'] = subsector
                    result['confidence'] = 'high' if len(kw) > 5 else 'medium'
                    self._cache[employer] = result
                    return result

        self._cache[employer] = result
        return result

    def classify_batch(self, employers: list) -> Dict[str, Dict]:
        """Classify a batch of employers."""
        results = {}
        for employer in employers:
            results[employer] = self.classify_employer(employer)
        self._save_cache()
        return results

    def get_stats(self) -> Dict:
        """Get classification statistics."""
        total = len(self._cache)
        if total == 0:
            return {'total': 0}

        financial = sum(1 for c in self._cache.values() if c.get('is_financial'))
        by_sector = {}
        for c in self._cache.values():
            sector = c.get('sector')
            if sector:
                by_sector[sector] = by_sector.get(sector, 0) + 1

        return {
            'total': total,
            'financial': financial,
            'non_financial': total - financial,
            'by_sector': dict(sorted(by_sector.items(), key=lambda x: -x[1])),
        }


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    # Test some employers
    classifier = EmployerClassifier()

    test_employers = [
        'GOLDMAN SACHS',
        'JP MORGAN CHASE',
        'ARBELLA INSURANCE GROUP',
        'SEIU HEALTHCARE WORKERS',
        'STATE FARM INSURANCE',
        'BLACKSTONE GROUP',
        'FIDELITY INVESTMENTS',
        'SELF EMPLOYED',
        'RETIRED',
        'SV ANGEL, LLC',
    ]

    print("Employer Classification Test:")
    print("=" * 70)
    for emp in test_employers:
        result = classifier.classify_employer(emp)
        print(f"{emp[:40]:<40} -> {result['is_financial']}, {result['sector']}, {result['subsector']}")
