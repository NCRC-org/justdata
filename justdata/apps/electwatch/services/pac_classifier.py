#!/usr/bin/env python3
"""
PAC Classification for ElectWatch.

Classifies PACs into financial sector subsectors using pattern matching.
Identifies banking, insurance, real estate, payments, investment, and
credit union PACs from their names and connected organizations.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)

# Cache directory
CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"
PAC_CACHE_FILE = CACHE_DIR / "pac_classification_cache.json"


# Financial subsector patterns - aligned with FINANCIAL_SECTORS taxonomy in firm_mapper.py
# Sectors: banking, mortgage, consumer_lending, investment, insurance, crypto, fintech, proptech, payments
# Format: (keywords, sector, subsector)
FINANCIAL_PATTERNS = [
    # Banking - Major banks
    (['JPMORGAN', 'JP MORGAN', 'CHASE BANK'], 'banking', 'major_bank'),
    (['BANK OF AMERICA', 'BOFA'], 'banking', 'major_bank'),
    (['WELLS FARGO'], 'banking', 'major_bank'),
    (['CITIBANK', 'CITIGROUP', 'CITI '], 'banking', 'major_bank'),
    (['GOLDMAN SACHS', 'GOLDMAN, SACHS'], 'investment', 'investment_bank'),
    (['MORGAN STANLEY'], 'investment', 'investment_bank'),

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

    # Banking - Trade associations
    (['AMERICAN BANKERS ASSOCIATION', 'BANKPAC'], 'banking', 'trade_association'),
    (['INDEPENDENT COMMUNITY BANKERS', 'ICBA'], 'banking', 'trade_association'),
    (['CONSUMER BANKERS'], 'banking', 'trade_association'),

    # Credit Unions (classified under banking - depository institutions)
    (['CREDIT UNION', 'CUNA', 'NAFCU'], 'banking', 'credit_union'),
    (['AMERICA\'S CREDIT UNIONS'], 'banking', 'credit_union'),

    # Mortgage & Real Estate Finance
    (['MORTGAGE BANKER', 'MBA PAC'], 'mortgage', 'trade_association'),
    (['QUICKEN', 'ROCKET MORTGAGE'], 'mortgage', 'lender'),
    (['FARM CREDIT'], 'mortgage', 'agricultural_credit'),
    (['FANNIE MAE', 'FREDDIE MAC'], 'mortgage', 'gse'),
    (['TITLE INSURANCE', 'TITLE COMPANY', 'TITLE ASSOCIATION'], 'mortgage', 'title'),
    (['LAND TITLE'], 'mortgage', 'title'),

    # Consumer Lending
    (['SALLIE MAE', 'NAVIENT'], 'consumer_lending', 'student_lending'),
    (['CAPITAL ONE'], 'consumer_lending', 'card_issuer'),
    (['DISCOVER FINANCIAL'], 'consumer_lending', 'card_issuer'),
    (['SYNCHRONY'], 'consumer_lending', 'card_issuer'),

    # Insurance - Major insurers
    (['AFLAC'], 'insurance', 'life_health'),
    (['METLIFE'], 'insurance', 'life_health'),
    (['PRUDENTIAL'], 'insurance', 'life_health'),
    (['NEW YORK LIFE'], 'insurance', 'life_health'),
    (['MASSACHUSETTS MUTUAL', 'MASSMUTUAL'], 'insurance', 'life_health'),
    (['NORTHWESTERN MUTUAL'], 'insurance', 'life_health'),
    (['LINCOLN NATIONAL', 'LINCOLN FINANCIAL'], 'insurance', 'life_health'),
    (['CIGNA'], 'insurance', 'health'),
    (['AETNA'], 'insurance', 'health'),
    (['ANTHEM'], 'insurance', 'health'),
    (['BLUE CROSS', 'BLUE SHIELD', 'BCBS'], 'insurance', 'health'),
    (['UNITEDHEALTH GROUP', 'UNITEDHEALTHCARE'], 'insurance', 'health'),
    (['ALLSTATE'], 'insurance', 'property_casualty'),
    (['STATE FARM'], 'insurance', 'property_casualty'),
    (['PROGRESSIVE INSURANCE', 'PROGRESSIVE CORP', 'PROGRESSIVE CASUALTY'], 'insurance', 'property_casualty'),
    (['LIBERTY MUTUAL'], 'insurance', 'property_casualty'),
    (['TRAVELERS'], 'insurance', 'property_casualty'),
    (['HARTFORD'], 'insurance', 'property_casualty'),
    (['CHUBB'], 'insurance', 'property_casualty'),
    (['NATIONWIDE'], 'insurance', 'property_casualty'),
    (['USAA'], 'insurance', 'property_casualty'),
    (['GEICO'], 'insurance', 'property_casualty'),
    (['AIG', 'AMERICAN INTERNATIONAL GROUP'], 'insurance', 'conglomerate'),

    # Insurance - Trade associations
    (['INSURANCE AGENTS & BROKERS', 'CIAB'], 'insurance', 'trade_association'),
    (['INDEPENDENT INSURANCE AGENTS', 'IIABA'], 'insurance', 'trade_association'),
    (['PROPERTY CASUALTY', 'APCIA'], 'insurance', 'trade_association'),
    (['MUTUAL INSURANCE COMPANIES', 'NAMIC PAC', 'NAMIC POLITICAL'], 'insurance', 'trade_association'),
    (['LIFE INSURERS', 'ACLI'], 'insurance', 'trade_association'),
    (['CROP INSURANCE'], 'insurance', 'agricultural'),
    (['INSURANCE AND FINANCIAL ADVISOR', 'NAIFA'], 'insurance', 'trade_association'),

    # Investment & Securities (includes asset managers, brokers, private equity, exchanges)
    (['BLACKROCK'], 'investment', 'asset_management'),
    (['VANGUARD'], 'investment', 'asset_management'),
    (['FIDELITY'], 'investment', 'asset_management'),
    (['STATE STREET'], 'investment', 'asset_management'),
    (['SCHWAB', 'CHARLES SCHWAB'], 'investment', 'brokerage'),
    (['INVESTMENT COMPANY INSTITUTE', 'ICI '], 'investment', 'trade_association'),
    (['AMERICAN INVESTMENT COUNCIL'], 'investment', 'trade_association'),
    (['TIAA', 'TEACHERS INSURANCE ANNUITY'], 'investment', 'retirement'),
    (['BLACKSTONE'], 'investment', 'private_equity'),
    (['KKR', 'KOHLBERG KRAVIS'], 'investment', 'private_equity'),
    (['CARLYLE'], 'investment', 'private_equity'),
    (['APOLLO'], 'investment', 'private_equity'),
    (['TPG '], 'investment', 'private_equity'),
    (['BAIN CAPITAL'], 'investment', 'private_equity'),
    (['SECURITIES INDUSTRY', 'SIFMA'], 'investment', 'trade_association'),
    (['NYSE', 'NEW YORK STOCK EXCHANGE'], 'investment', 'exchange'),
    (['NASDAQ'], 'investment', 'exchange'),
    (['CME GROUP', 'CHICAGO MERCANTILE'], 'investment', 'exchange'),
    (['INTERCONTINENTAL EXCHANGE', 'ICE INC'], 'investment', 'exchange'),

    # Digital Assets & Crypto
    (['COINBASE'], 'crypto', 'exchange'),
    (['BLOCKCHAIN ASSOCIATION'], 'crypto', 'trade_association'),
    (['CRYPTO', 'CRYPTOCURRENCY'], 'crypto', 'general'),
    (['BITCOIN', 'DIGITAL ASSET'], 'crypto', 'general'),

    # Financial Technology
    (['INTUIT'], 'fintech', 'software'),
    (['EQUIFAX', 'EXPERIAN', 'TRANSUNION'], 'fintech', 'credit_bureau'),
    (['PLAID'], 'fintech', 'data_aggregation'),

    # PropTech & Real Estate Tech
    (['ZILLOW'], 'proptech', 'platform'),
    (['REDFIN'], 'proptech', 'platform'),
    (['OPENDOOR'], 'proptech', 'ibuyer'),
    (['COMPASS REAL ESTATE'], 'proptech', 'brokerage'),

    # Real Estate - Trade Associations (mapped to mortgage for financing focus)
    (['NATIONAL ASSOCIATION OF REALTORS', 'REALTORS PAC', 'REALTOR PAC'], 'mortgage', 'trade_association'),
    (['ASSOCIATION OF REALTORS'], 'mortgage', 'trade_association'),
    (['REAL ESTATE INVESTMENT TRUSTS', 'NAREIT'], 'investment', 'reits'),
    (['REAL ESTATE ROUNDTABLE'], 'mortgage', 'trade_association'),
    (['REAL ESTATE BOARD'], 'mortgage', 'trade_association'),

    # Real Estate - Homebuilders (mapped to mortgage)
    (['HOME BUILDER', 'HOMEBUILDER', 'NAHB'], 'mortgage', 'homebuilders'),
    (['NATIONAL ASSOCIATION OF HOME BUILDERS'], 'mortgage', 'homebuilders'),

    # Real Estate - Housing types (mapped to mortgage)
    (['MULTIFAMILY HOUSING', 'APARTMENT ASSOCIATION'], 'mortgage', 'multifamily'),
    (['SENIORS HOUSING', 'SENIOR HOUSING'], 'mortgage', 'seniors_housing'),
    (['AFFORDABLE HOUSING', 'WORKFORCE HOUSING'], 'mortgage', 'affordable_housing'),
    (['COMMERCIAL REAL ESTATE'], 'mortgage', 'commercial'),
    (['MANUFACTURED HOUSING'], 'mortgage', 'manufactured_housing'),
    (['RESIDENTIAL PROPERTY'], 'mortgage', 'residential'),

    # Real Estate - Brokerages (traditional = mortgage, tech-focused = proptech)
    (['RE/MAX', 'REMAX'], 'mortgage', 'brokerage'),
    (['COLDWELL BANKER'], 'mortgage', 'brokerage'),
    (['KELLER WILLIAMS'], 'mortgage', 'brokerage'),
    (['CENTURY 21'], 'mortgage', 'brokerage'),
    (['BERKSHIRE HATHAWAY HOME'], 'mortgage', 'brokerage'),
    (['ARBOR REALTY', 'REALTY TRUST'], 'investment', 'reits'),
    (['APPRAISAL', 'APPRAISER'], 'mortgage', 'appraisal'),

    # Payments & Processing
    (['VISA'], 'payments', 'card_network'),
    (['MASTERCARD'], 'payments', 'card_network'),
    (['AMERICAN EXPRESS', 'AMEX'], 'payments', 'card_network'),
    (['PAYPAL'], 'payments', 'digital_payments'),
    (['FISERV'], 'payments', 'processing'),
    (['FIS ', 'FIDELITY NATIONAL INFORMATION'], 'payments', 'processing'),
    (['GLOBAL PAYMENTS'], 'payments', 'processing'),
    (['PAYCHEX'], 'payments', 'payroll'),
    (['ADP'], 'payments', 'payroll'),
    (['SQUARE', 'BLOCK INC'], 'payments', 'digital_payments'),
]

# Exclusion patterns (not financial even if contains keywords)
EXCLUSION_PATTERNS = [
    # Banks (not financial)
    'FOOD BANK', 'BLOOD BANK', 'RIVER BANK', 'WEST BANK', 'DATA BANK',
    'SEED BANK', 'SPERM BANK', 'MEMORY BANK', 'EYE BANK',

    # Labor unions (not financial sector even if in healthcare/finance adjacent fields)
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
    'HEALTHCARE WORKERS',  # Union healthcare workers, not insurance

    # Political/advocacy (not financial)
    'HUMAN RIGHTS CAMPAIGN',
    'END CITIZENS UNITED',
    'EMILY\'S LIST',
    'PLANNED PARENTHOOD',
    'SIERRA CLUB',
    'LEAGUE OF CONSERVATION',

    # Not real estate
    'INTELLECTUAL PROPERTY',
    'PROPERTY RIGHTS ASSOCIATION',
    'PROPERTY TAX',

    # Other false positive triggers
    'EMERGENCY MEDICINE',
]


class PACClassifier:
    """Classifies PACs into financial sector subsectors."""

    def __init__(self):
        self._cache: Dict[str, Dict] = {}
        self._load_cache()

    def _load_cache(self):
        """Load cached classifications."""
        if PAC_CACHE_FILE.exists():
            try:
                with open(PAC_CACHE_FILE) as f:
                    self._cache = json.load(f)
                logger.info(f"Loaded {len(self._cache)} cached PAC classifications")
            except Exception as e:
                logger.warning(f"Failed to load PAC cache: {e}")
                self._cache = {}

    def _save_cache(self):
        """Save cache to disk."""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(PAC_CACHE_FILE, 'w') as f:
            json.dump(self._cache, f, indent=2)

    def classify_pac(self, pac_name: str, connected_org: str = '') -> Dict:
        """
        Classify a PAC by name and connected organization.

        Returns:
            Dict with keys: pac_name, is_financial, sector, subsector, confidence
        """
        pac_name = pac_name.upper().strip()
        cache_key = f"{pac_name}|{connected_org.upper().strip()}"

        if cache_key in self._cache:
            return self._cache[cache_key]

        result = {
            'pac_name': pac_name,
            'connected_org': connected_org,
            'is_financial': False,
            'sector': None,
            'subsector': None,
            'confidence': 'none',
        }

        # Check exclusions first
        for exclusion in EXCLUSION_PATTERNS:
            if exclusion in pac_name or exclusion in connected_org.upper():
                self._cache[cache_key] = result
                return result

        # Try matching patterns
        names_to_check = [pac_name, connected_org.upper()]

        for name in names_to_check:
            if not name:
                continue

            for keywords, sector, subsector in FINANCIAL_PATTERNS:
                for kw in keywords:
                    if kw in name:
                        result['is_financial'] = True
                        result['sector'] = sector
                        result['subsector'] = subsector
                        result['confidence'] = 'high' if len(kw) > 5 else 'medium'
                        self._cache[cache_key] = result
                        return result

        # Generic financial keyword matching (lower confidence)
        # Aligned with FINANCIAL_SECTORS: banking, mortgage, consumer_lending, investment,
        # insurance, crypto, fintech, proptech, payments
        GENERIC_KEYWORDS = [
            ('BANK', 'banking', 'unknown'),
            ('CREDIT', 'consumer_lending', 'unknown'),
            ('INSURANCE', 'insurance', 'unknown'),
            ('INVESTMENT', 'investment', 'unknown'),
            ('SECURITIES', 'investment', 'unknown'),
            ('MORTGAGE', 'mortgage', 'unknown'),
            ('FINANCIAL', 'fintech', 'unknown'),
            ('REALTOR', 'mortgage', 'unknown'),
            ('REALTY', 'mortgage', 'unknown'),
            ('CRYPTO', 'crypto', 'unknown'),
            ('BLOCKCHAIN', 'crypto', 'unknown'),
            ('FINTECH', 'fintech', 'unknown'),
            ('PAYMENT', 'payments', 'unknown'),
        ]

        for name in names_to_check:
            if not name:
                continue

            for kw, sector, subsector in GENERIC_KEYWORDS:
                if kw in name:
                    result['is_financial'] = True
                    result['sector'] = sector
                    result['subsector'] = subsector
                    result['confidence'] = 'low'
                    self._cache[cache_key] = result
                    return result

        self._cache[cache_key] = result
        return result

    def classify_bulk(self, pacs: List[Dict]) -> Dict[str, Dict]:
        """
        Classify multiple PACs.

        Args:
            pacs: List of dicts with 'name' and optionally 'connected_org' keys

        Returns:
            Dict mapping pac_name -> classification
        """
        results = {}
        for pac in pacs:
            name = pac.get('name', '')
            connected = pac.get('connected_org', '')
            results[name] = self.classify_pac(name, connected)

        self._save_cache()
        return results

    def get_summary(self, classifications: Dict[str, Dict]) -> Dict:
        """Get summary statistics."""
        total = len(classifications)
        financial = sum(1 for c in classifications.values() if c.get('is_financial'))

        by_sector = defaultdict(int)
        by_subsector = defaultdict(int)
        by_confidence = defaultdict(int)

        for c in classifications.values():
            if c.get('is_financial'):
                sector = c.get('sector', 'unknown')
                subsector = f"{sector}/{c.get('subsector', 'unknown')}"
                by_sector[sector] += 1
                by_subsector[subsector] += 1
                by_confidence[c.get('confidence', 'none')] += 1

        return {
            'total': total,
            'financial': financial,
            'financial_pct': round(financial / total * 100, 1) if total else 0,
            'by_sector': dict(sorted(by_sector.items(), key=lambda x: -x[1])),
            'by_subsector': dict(sorted(by_subsector.items(), key=lambda x: -x[1])),
            'by_confidence': dict(by_confidence),
        }


def classify_all_pacs():
    """Classify all PACs from FEC committee master file."""
    import csv

    cm_path = Path("C:/JustData-LocalData/fec_bulk/cm.txt")
    if not cm_path.exists():
        print("Committee master file not found!")
        return

    # Load committees
    committees = []
    with open(cm_path, 'r', encoding='latin-1') as f:
        reader = csv.reader(f, delimiter='|')
        for row in reader:
            if len(row) >= 14:
                # Only include traditional PACs
                cmte_type = row[9]
                if cmte_type in ('Q', 'N', 'V', 'W'):
                    committees.append({
                        'id': row[0],
                        'name': row[1],
                        'type': cmte_type,
                        'connected_org': row[13] if len(row) > 13 else ''
                    })

    print(f"Loaded {len(committees)} traditional PACs")

    # Classify
    classifier = PACClassifier()
    results = {}
    for c in committees:
        results[c['name']] = classifier.classify_pac(c['name'], c['connected_org'])

    # Save cache
    classifier._save_cache()

    # Summary
    summary = classifier.get_summary(results)
    print(f"\nPAC Classification Summary:")
    print(f"  Total PACs: {summary['total']}")
    print(f"  Financial: {summary['financial']} ({summary['financial_pct']}%)")
    print(f"\nBy Sector:")
    for sector, count in summary['by_sector'].items():
        print(f"  {sector}: {count}")
    print(f"\nBy Confidence:")
    for conf, count in summary['by_confidence'].items():
        print(f"  {conf}: {count}")

    # Show top financial PACs by subsector
    print(f"\nTop Financial PACs by Subsector (sample):")
    subsector_examples = defaultdict(list)
    for name, c in results.items():
        if c.get('is_financial'):
            key = f"{c['sector']}/{c['subsector']}"
            if len(subsector_examples[key]) < 3:
                subsector_examples[key].append(name[:50])

    for subsector in sorted(subsector_examples.keys()):
        print(f"\n  {subsector}:")
        for name in subsector_examples[subsector]:
            print(f"    - {name}")

    return results, summary


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    classify_all_pacs()
