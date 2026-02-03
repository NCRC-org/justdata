#!/usr/bin/env python3
"""
Firm Matcher for ElectWatch.

Matches individual contribution employers against known financial firms
extracted from PAC connected organizations.

APPROACH: Exact matching only.
- Extract connected_org from all classified financial PACs
- Normalize firm names (remove INC, LLC, etc.)
- Match employers ONLY if they exactly match a known firm
- If no exact match, employer is NOT classified as financial

This approach prioritizes accuracy over coverage. We only classify employers
that can be verified through PAC data. This is appropriate for research that
will be cited in advocacy work where defensibility matters.

What we capture:
- All major banks (JPMorgan, Wells Fargo, BofA, Citi, regionals with PACs)
- Investment banks (Goldman Sachs, Morgan Stanley)
- Asset managers (BlackRock, Vanguard, Fidelity)
- Insurance companies (State Farm, Allstate, MetLife)
- Card networks (Visa, Mastercard, Amex)
- Private equity (Blackstone, KKR, Carlyle)

What we intentionally skip (to avoid false positives):
- Small banks without PACs
- Solo financial advisors
- Fintech startups
- Boutique firms
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)

# Cache directory
CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"
FIRM_LIST_CACHE = CACHE_DIR / "financial_firms_list.json"
EMPLOYER_MATCH_CACHE = CACHE_DIR / "employer_firm_matches.json"

# Suffixes to strip when normalizing firm names
SUFFIXES_TO_STRIP = [
    # Corporate suffixes (longest first to avoid partial matches)
    ' POLITICAL ACTION COMMITTEE', ' PAC',
    ' CORPORATION', ' COMPANY', ' COMPANIES',
    ' & COMPANY', ' AND COMPANY', '& CO.', ' & CO', ' AND CO',
    ', INC.', ', INC', ' INC.', ' INC',
    ', LLC', ' LLC',
    ', LP', ' LP', ', L.P.', ' L.P.',
    ', LLP', ' LLP',
    ', CORP.', ', CORP', ' CORP.', ' CORP',
    ', CO.', ', CO', ' CO.', ' CO',
    ', LTD.', ', LTD', ' LTD.', ' LTD',
    ', PC', ' PC', ', P.C.', ' P.C.',
    ', NA', ' NA', ', N.A.', ' N.A.',
    ', FSB', ' FSB', ', F.S.B.', ' F.S.B.',
    ' GROUP', ' HOLDINGS', ' HOLDING',
    ' SERVICES', ' SERVICE',
    ' FINANCIAL', ' BANCORP', ' BANCSHARES',
    ' INTERNATIONAL', ' NATIONAL',
    ' INSURANCE', ' ASSURANCE',
    ' INVESTMENTS', ' INVESTMENT',
    ' MANAGEMENT', ' MGMT',
    ' ASSOCIATES', ' ASSOCIATION', ' ASSN',
    ' PARTNERS', ' PARTNERSHIP',
    ' SOLUTIONS', ' SYSTEMS',
    ' AMERICA', ' AMERICAS', ' USA', ' US',
    ' OF AMERICA',
    ' BANK',  # Strip " BANK" suffix to match "WELLS FARGO" from "WELLS FARGO BANK"
]

# Minimum firm name length after normalization
MIN_FIRM_NAME_LENGTH = 3

# Supplemental firms - major financial companies with common employer name variations
# These are manually verified and added to ensure major firms aren't missed due to
# PAC connected org naming variations (e.g., "THE GOLDMAN SACHS GROUP INC" vs "GOLDMAN SACHS")
SUPPLEMENTAL_FIRMS = [
    # Investment banks
    ('GOLDMAN SACHS', 'investment_banking', 'investment_bank'),
    ('GOLDMAN SACHS & CO', 'investment_banking', 'investment_bank'),
    ('GOLDMAN SACHS GROUP', 'investment_banking', 'investment_bank'),
    ('MORGAN STANLEY', 'investment_banking', 'investment_bank'),

    # Major banks
    ('JPMORGAN', 'banking', 'major_bank'),
    ('JPMORGAN CHASE', 'banking', 'major_bank'),
    ('JPMORGAN CHASE BANK', 'banking', 'major_bank'),
    ('JP MORGAN', 'banking', 'major_bank'),
    ('JP MORGAN CHASE', 'banking', 'major_bank'),
    ('WELLS FARGO', 'banking', 'major_bank'),
    ('WELLS FARGO BANK', 'banking', 'major_bank'),
    ('WELLS FARGO & COMPANY', 'banking', 'major_bank'),
    ('BANK OF AMERICA', 'banking', 'major_bank'),
    ('CITIBANK', 'banking', 'major_bank'),
    ('CITI', 'banking', 'major_bank'),
    ('US BANK', 'banking', 'major_bank'),
    ('US BANCORP', 'banking', 'major_bank'),
    ('PNC', 'banking', 'regional_bank'),
    ('PNC BANK', 'banking', 'regional_bank'),
    ('TRUIST', 'banking', 'regional_bank'),
    ('SUNTRUST', 'banking', 'regional_bank'),
    ('BB&T', 'banking', 'regional_bank'),
    ('FIFTH THIRD', 'banking', 'regional_bank'),
    ('FIFTH THIRD BANK', 'banking', 'regional_bank'),
    ('REGIONS BANK', 'banking', 'regional_bank'),
    ('REGIONS', 'banking', 'regional_bank'),
    ('KEYBANK', 'banking', 'regional_bank'),
    ('CITIZENS BANK', 'banking', 'regional_bank'),
    ('HUNTINGTON BANK', 'banking', 'regional_bank'),
    ('M&T BANK', 'banking', 'regional_bank'),

    # Asset managers
    ('BLACKROCK', 'investment', 'asset_management'),
    ('VANGUARD', 'investment', 'asset_management'),
    ('FIDELITY', 'investment', 'asset_management'),
    ('FIDELITY INVESTMENTS', 'investment', 'asset_management'),
    ('STATE STREET', 'investment', 'asset_management'),
    ('T ROWE PRICE', 'investment', 'asset_management'),
    ('PIMCO', 'investment', 'asset_management'),
    ('CAPITAL GROUP', 'investment', 'asset_management'),

    # Brokerages
    ('CHARLES SCHWAB', 'investment', 'brokerage'),
    ('SCHWAB', 'investment', 'brokerage'),
    ('EDWARD JONES', 'investment', 'brokerage'),
    ('RAYMOND JAMES', 'investment', 'brokerage'),
    ('AMERIPRISE', 'investment', 'brokerage'),
    ('LPL FINANCIAL', 'investment', 'brokerage'),
    ('MERRILL LYNCH', 'investment', 'brokerage'),

    # Insurance
    ('STATE FARM', 'insurance', 'property_casualty'),
    ('ALLSTATE', 'insurance', 'property_casualty'),
    ('PROGRESSIVE', 'insurance', 'property_casualty'),
    ('GEICO', 'insurance', 'property_casualty'),
    ('LIBERTY MUTUAL', 'insurance', 'property_casualty'),
    ('USAA', 'insurance', 'property_casualty'),
    ('NATIONWIDE', 'insurance', 'property_casualty'),
    ('FARMERS INSURANCE', 'insurance', 'property_casualty'),
    ('METLIFE', 'insurance', 'life_health'),
    ('PRUDENTIAL', 'insurance', 'life_health'),
    ('NEW YORK LIFE', 'insurance', 'life_health'),
    ('NORTHWESTERN MUTUAL', 'insurance', 'life_health'),
    ('AFLAC', 'insurance', 'life_health'),
    ('CIGNA', 'insurance', 'health'),
    ('AETNA', 'insurance', 'health'),
    ('ANTHEM', 'insurance', 'health'),
    ('UNITEDHEALTH', 'insurance', 'health'),
    ('HUMANA', 'insurance', 'health'),
    ('BLUE CROSS', 'insurance', 'health'),
    ('KAISER PERMANENTE', 'insurance', 'health'),

    # Private equity
    ('BLACKSTONE', 'private_equity', 'buyout'),
    ('KKR', 'private_equity', 'buyout'),
    ('CARLYLE', 'private_equity', 'buyout'),
    ('APOLLO', 'private_equity', 'buyout'),
    ('TPG', 'private_equity', 'buyout'),
    ('BAIN CAPITAL', 'private_equity', 'buyout'),

    # Hedge funds
    ('CITADEL', 'investment', 'hedge_fund'),
    ('BRIDGEWATER', 'investment', 'hedge_fund'),
    ('TWO SIGMA', 'investment', 'hedge_fund'),
    ('RENAISSANCE', 'investment', 'hedge_fund'),
    ('D E SHAW', 'investment', 'hedge_fund'),
    ('DE SHAW', 'investment', 'hedge_fund'),
    ('POINT72', 'investment', 'hedge_fund'),

    # Payments
    ('VISA', 'payments', 'card_network'),
    ('MASTERCARD', 'payments', 'card_network'),
    ('AMERICAN EXPRESS', 'payments', 'card_issuer'),
    ('AMEX', 'payments', 'card_issuer'),
    ('DISCOVER', 'payments', 'card_issuer'),
    ('CAPITAL ONE', 'payments', 'card_issuer'),
    ('PAYPAL', 'payments', 'digital'),
    ('STRIPE', 'payments', 'digital'),
    ('SQUARE', 'payments', 'digital'),

    # Real estate
    ('CBRE', 'real_estate', 'commercial'),
    ('JLL', 'real_estate', 'commercial'),
    ('CUSHMAN WAKEFIELD', 'real_estate', 'commercial'),
    ('KELLER WILLIAMS', 'real_estate', 'residential'),
    ('COLDWELL BANKER', 'real_estate', 'residential'),
    ('RE MAX', 'real_estate', 'residential'),
    ('REMAX', 'real_estate', 'residential'),

    # Lending
    ('ROCKET MORTGAGE', 'lending', 'mortgage'),
    ('QUICKEN LOANS', 'lending', 'mortgage'),
    ('FANNIE MAE', 'lending', 'gse'),
    ('FREDDIE MAC', 'lending', 'gse'),
]

# Company aliases - Maps parent companies to their subsidiaries and name variations.
# Used to combine PAC + individual contributions that come from the same corporate family.
# For example, "CHASE BANK" employees should be combined with "JPMORGAN CHASE" PAC contributions.
COMPANY_ALIASES = {
    # Major Banks - Parent company as key, aliases as values
    'JPMORGAN CHASE': [
        'JP MORGAN', 'JPMORGAN', 'CHASE BANK', 'CHASE', 'J.P. MORGAN',
        'JPMORGAN CHASE BANK', 'JPMORGAN CHASE & CO', 'JP MORGAN CHASE',
        'CHASE MANHATTAN', 'BEAR STEARNS', 'WASHINGTON MUTUAL', 'WAMU'
    ],
    'BANK OF AMERICA': [
        'BOA', 'BOFA', 'BANK OF AMERICA MERRILL LYNCH', 'MERRILL LYNCH',
        'MERRILL', 'COUNTRYWIDE', 'FLEET BANK', 'FLEET BOSTON',
        'NATIONSBANK', 'USBANK'
    ],
    'WELLS FARGO': [
        'WELLS FARGO BANK', 'WELLS FARGO HOME MORTGAGE', 'WELLS FARGO ADVISORS',
        'WELLS FARGO SECURITIES', 'WACHOVIA', 'FIRST UNION'
    ],
    'CITIGROUP': [
        'CITI', 'CITIBANK', 'CITICORP', 'CITIGROUP INC', 'CITI PRIVATE BANK',
        'CITIGROUP GLOBAL MARKETS', 'SALOMON BROTHERS', 'SMITH BARNEY',
        'TRAVELERS GROUP'
    ],
    'GOLDMAN SACHS': [
        'GOLDMAN SACHS & CO', 'GOLDMAN SACHS GROUP', 'THE GOLDMAN SACHS GROUP',
        'GOLDMAN SACHS BANK', 'GS BANK', 'UNITED CAPITAL'
    ],
    'MORGAN STANLEY': [
        'MORGAN STANLEY & CO', 'MORGAN STANLEY SMITH BARNEY', 'MS',
        'E*TRADE', 'ETRADE', 'E-TRADE', 'DEAN WITTER'
    ],

    # Regional Banks
    'PNC FINANCIAL': [
        'PNC', 'PNC BANK', 'PNC INVESTMENTS', 'BBVA USA', 'NATIONAL CITY',
        'RIGGS BANK', 'MERCANTILE BANKSHARES'
    ],
    'TRUIST': [
        'TRUIST BANK', 'TRUIST FINANCIAL', 'BB&T', 'BBT', 'SUNTRUST',
        'SUNTRUST BANK', 'SUNTRUST ROBINSON HUMPHREY'
    ],
    'US BANCORP': [
        'US BANK', 'U.S. BANK', 'USB', 'ELAVON', 'FIRSTAR'
    ],
    'CAPITAL ONE': [
        'CAPITAL ONE BANK', 'CAPITAL ONE FINANCIAL', 'ING DIRECT',
        'CAPITAL ONE 360'
    ],
    'FIFTH THIRD': [
        'FIFTH THIRD BANK', 'FIFTH THIRD BANCORP', '5/3 BANK', '53 BANK'
    ],

    # Investment Banks & Asset Managers
    'BLACKROCK': [
        'BLACKROCK INC', 'BLACKROCK FINANCIAL', 'ISHARES', 'BARCLAYS GLOBAL INVESTORS',
        'BGI', 'BLACKROCK FUNDS SERVICES', 'BLACKROCK FUND ADVISORS',
        'BLACKROCK FINANCIAL MANAGEMENT', 'BLK'
    ],
    'BLACKSTONE': [
        'BLACKSTONE GROUP', 'THE BLACKSTONE GROUP', 'BLACKSTONE INC',
        'BLACKSTONE REAL ESTATE', 'BLACKSTONE CREDIT'
    ],
    'STATE STREET': [
        'STATE STREET CORPORATION', 'STATE STREET BANK', 'STATE STREET GLOBAL ADVISORS',
        'SSGA'
    ],
    'FIDELITY': [
        'FIDELITY INVESTMENTS', 'FMR LLC', 'FMR', 'FIDELITY MANAGEMENT',
        'FIDELITY BROKERAGE', 'FIDELITY INSTITUTIONAL'
    ],
    'VANGUARD': [
        'VANGUARD GROUP', 'THE VANGUARD GROUP', 'VANGUARD INVESTMENTS'
    ],
    'CHARLES SCHWAB': [
        'SCHWAB', 'CHARLES SCHWAB BANK', 'CHARLES SCHWAB & CO',
        'TD AMERITRADE', 'TDAMERITRADE', 'AMERITRADE'
    ],

    # Private Equity
    'KKR': [
        'KKR & CO', 'KOHLBERG KRAVIS ROBERTS', 'KKR CREDIT'
    ],
    'CARLYLE': [
        'CARLYLE GROUP', 'THE CARLYLE GROUP', 'CARLYLE INVESTMENT MANAGEMENT'
    ],
    'APOLLO': [
        'APOLLO GLOBAL', 'APOLLO MANAGEMENT', 'APOLLO GLOBAL MANAGEMENT'
    ],

    # Insurance
    'METLIFE': [
        'METROPOLITAN LIFE', 'METLIFE INC', 'METLIFE INSURANCE'
    ],
    'PRUDENTIAL': [
        'PRUDENTIAL FINANCIAL', 'PRUDENTIAL INSURANCE', 'PRUCO',
        'PRUDENTIAL RETIREMENT'
    ],
    'ALLSTATE': [
        'ALLSTATE INSURANCE', 'ALLSTATE CORP', 'THE ALLSTATE CORPORATION',
        'ESURANCE', 'ENCOMPASS INSURANCE'
    ],
    'AIG': [
        'AMERICAN INTERNATIONAL GROUP', 'AIG INSURANCE', 'AIG LIFE',
        'SUNAMERICA', 'VALIC'
    ],
    'PROGRESSIVE': [
        'PROGRESSIVE INSURANCE', 'PROGRESSIVE CORP', 'THE PROGRESSIVE CORPORATION'
    ],
    'CIGNA': [
        'CIGNA CORPORATION', 'CIGNA HEALTHCARE', 'EXPRESS SCRIPTS', 'EVERNORTH'
    ],

    # Payments & Consumer Finance
    'VISA': [
        'VISA INC', 'VISA USA', 'VISA INTERNATIONAL'
    ],
    'MASTERCARD': [
        'MASTERCARD INC', 'MASTERCARD INTERNATIONAL', 'MASTERCARD WORLDWIDE'
    ],
    'AMERICAN EXPRESS': [
        'AMEX', 'AMERICAN EXPRESS COMPANY', 'AMERICANEXPRESS'
    ],
    'PAYPAL': [
        'PAYPAL HOLDINGS', 'PAYPAL INC', 'VENMO', 'BRAINTREE'
    ],
    'DISCOVER': [
        'DISCOVER FINANCIAL', 'DISCOVER BANK', 'DISCOVER CARD'
    ],

    # Mortgage
    'ROCKET': [
        'ROCKET MORTGAGE', 'ROCKET COMPANIES', 'QUICKEN LOANS', 'QUICKEN'
    ],
    'UNITED WHOLESALE MORTGAGE': [
        'UWM', 'UWM HOLDINGS', 'UNITED SHORE'
    ],

    # Credit Rating & Data
    'MOODYS': [
        "MOODY'S", 'MOODYS CORPORATION', "MOODY'S INVESTORS SERVICE",
        "MOODY'S ANALYTICS"
    ],
    'S&P GLOBAL': [
        'S&P', 'STANDARD & POORS', 'STANDARD AND POORS', "STANDARD & POOR'S"
    ],

    # Stock Exchanges
    'INTERCONTINENTAL EXCHANGE': [
        'ICE', 'NYSE', 'NEW YORK STOCK EXCHANGE', 'ICE DATA SERVICES'
    ],
    'NASDAQ': [
        'NASDAQ INC', 'NASDAQ OMX', 'THE NASDAQ'
    ],
    'CME GROUP': [
        'CME', 'CHICAGO MERCANTILE EXCHANGE', 'CBOT', 'NYMEX', 'COMEX'
    ]
}


def normalize_firm_name(name: str) -> str:
    """
    Normalize a firm name for matching.

    - Uppercase
    - Strip corporate suffixes (INC, LLC, etc.)
    - Remove extra whitespace and punctuation
    """
    if not name:
        return ''

    normalized = name.upper().strip()

    # Strip suffixes (longest first to avoid partial matches)
    suffixes_sorted = sorted(SUFFIXES_TO_STRIP, key=len, reverse=True)
    for suffix in suffixes_sorted:
        if normalized.endswith(suffix.upper()):
            normalized = normalized[:-len(suffix)].strip()

    # Remove common punctuation
    normalized = re.sub(r'[,.\'\"-]', ' ', normalized)

    # Collapse multiple spaces
    normalized = re.sub(r'\s+', ' ', normalized).strip()

    return normalized


def resolve_to_parent_company(name: str) -> str:
    """
    Resolve a company name to its canonical parent company using COMPANY_ALIASES.

    This is used to combine contributions from subsidiaries under their parent company.
    For example: "CHASE BANK" -> "JPMORGAN CHASE", "MERRILL LYNCH" -> "BANK OF AMERICA"

    Args:
        name: Company or employer name (will be normalized)

    Returns:
        Parent company name if found in aliases, otherwise the normalized input name
    """
    if not name:
        return ''

    normalized = normalize_firm_name(name)

    # Check if this name is a direct match for a parent company
    for parent in COMPANY_ALIASES:
        if normalize_firm_name(parent) == normalized:
            return parent

    # Check if this name is an alias for a parent company
    for parent, aliases in COMPANY_ALIASES.items():
        for alias in aliases:
            if normalize_firm_name(alias) == normalized:
                return parent

    # Not found in aliases - return normalized name
    return normalized


def get_all_aliases_for_company(company: str) -> list:
    """
    Get all known aliases for a company, including the parent name itself.

    Args:
        company: Company name to look up

    Returns:
        List of all known name variations for this company
    """
    normalized = normalize_firm_name(company)

    # First check if it's a parent company
    for parent, aliases in COMPANY_ALIASES.items():
        if normalize_firm_name(parent) == normalized:
            return [parent] + aliases

    # Check if it's an alias and return the parent's full list
    for parent, aliases in COMPANY_ALIASES.items():
        for alias in aliases:
            if normalize_firm_name(alias) == normalized:
                return [parent] + aliases

    # Not found - return just the input
    return [company]


class FirmMatcher:
    """
    Matches employers against known financial firms from PAC connected organizations.

    Uses EXACT MATCHING ONLY - no keywords, no fuzzy matching.
    If an employer doesn't exactly match a known firm, it's not classified.
    """

    def __init__(self):
        self._firms: Dict[str, Dict] = {}  # normalized_name -> {sector, subsector, original_name}
        self._match_cache: Dict[str, Optional[Dict]] = {}
        self._loaded = False

    def build_firm_list(self, force: bool = False):
        """
        Build the list of financial firms from PAC connected organizations.

        Args:
            force: Rebuild even if cache exists
        """
        # Check cache first
        if not force and FIRM_LIST_CACHE.exists():
            try:
                with open(FIRM_LIST_CACHE) as f:
                    data = json.load(f)
                self._firms = data.get('firms', {})
                self._loaded = True
                logger.info(f"Loaded {len(self._firms)} firms from cache")
                return
            except Exception as e:
                logger.warning(f"Failed to load firm cache: {e}")

        # Build from PAC data
        from justdata.apps.electwatch.services.fec_bulk import FECBulkProcessor
        from justdata.apps.electwatch.services.pac_classifier import PACClassifier

        processor = FECBulkProcessor()
        committees = processor.load_committee_master()
        pac_classifier = PACClassifier()

        # Track firms by normalized name
        firms_raw = {}

        for cmte_id, info in committees.items():
            pac_name = info.get('name', '')
            connected_org = info.get('connected_org', '')

            # Classify the PAC
            result = pac_classifier.classify_pac(pac_name, connected_org)
            if not result.get('is_financial'):
                continue

            sector = result.get('sector')
            subsector = result.get('subsector')

            # Process connected organization (primary source)
            if connected_org and connected_org.upper() not in ('', 'NONE', 'N/A'):
                normalized = normalize_firm_name(connected_org)
                if len(normalized) >= MIN_FIRM_NAME_LENGTH:
                    if normalized not in firms_raw:
                        firms_raw[normalized] = {
                            'sector': sector,
                            'subsector': subsector,
                            'original_name': connected_org,
                        }

            # Also extract firm name from PAC name if no connected_org
            # e.g., "GOLDMAN SACHS PAC" -> "GOLDMAN SACHS"
            if not connected_org or connected_org.upper() in ('', 'NONE', 'N/A'):
                pac_upper = pac_name.upper()
                for suffix in [' POLITICAL ACTION COMMITTEE', ' PAC', ' FEDERAL PAC', ' GOOD GOVERNMENT']:
                    if suffix in pac_upper:
                        company_part = pac_upper.split(suffix)[0].strip()
                        # Clean up common prefixes
                        for prefix in ['THE ', 'FMR LLC ', 'FMR ']:
                            if company_part.startswith(prefix):
                                company_part = company_part[len(prefix):]
                        normalized = normalize_firm_name(company_part)
                        if len(normalized) >= MIN_FIRM_NAME_LENGTH and normalized not in firms_raw:
                            firms_raw[normalized] = {
                                'sector': sector,
                                'subsector': subsector,
                                'original_name': pac_name,
                            }
                        break

        # Add supplemental firms (major financial companies with common name variations)
        # These ensure we don't miss major firms due to PAC naming differences
        for firm_name, sector, subsector in SUPPLEMENTAL_FIRMS:
            normalized = normalize_firm_name(firm_name)
            if normalized not in firms_raw:
                firms_raw[normalized] = {
                    'sector': sector,
                    'subsector': subsector,
                    'original_name': firm_name,
                }

        # Store the firms
        self._firms = firms_raw

        # Save cache
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(FIRM_LIST_CACHE, 'w') as f:
            json.dump({'firms': self._firms}, f, indent=2)

        self._loaded = True
        logger.info(f"Built firm list with {len(self._firms)} firms (exact match only)")

    def match_employer(self, employer: str) -> Optional[Dict]:
        """
        Match an employer against known financial firms.

        First tries exact match, then checks COMPANY_ALIASES to find
        parent company matches. No fuzzy matching.

        Args:
            employer: The employer name to match

        Returns:
            Dict with sector, subsector, matched_firm, parent_company if matched
            None if no match (employer is NOT classified as financial)
        """
        if not self._loaded:
            self.build_firm_list()

        if not employer:
            return None

        # Check cache
        employer_upper = employer.upper().strip()
        if employer_upper in self._match_cache:
            return self._match_cache[employer_upper]

        # Normalize the employer name
        normalized = normalize_firm_name(employer)
        if len(normalized) < MIN_FIRM_NAME_LENGTH:
            self._match_cache[employer_upper] = None
            return None

        # EXACT MATCH first
        if normalized in self._firms:
            info = self._firms[normalized]
            result = {
                'employer': employer,
                'matched_firm': normalized,
                'parent_company': resolve_to_parent_company(normalized),
                'sector': info['sector'],
                'subsector': info['subsector'],
                'match_type': 'exact',
            }
            self._match_cache[employer_upper] = result
            return result

        # Check COMPANY_ALIASES for parent company resolution
        parent = resolve_to_parent_company(normalized)
        if parent != normalized:
            # Found via alias - check if parent is in our firm list
            parent_normalized = normalize_firm_name(parent)
            if parent_normalized in self._firms:
                info = self._firms[parent_normalized]
                result = {
                    'employer': employer,
                    'matched_firm': parent_normalized,
                    'parent_company': parent,
                    'sector': info['sector'],
                    'subsector': info['subsector'],
                    'match_type': 'alias',
                }
                self._match_cache[employer_upper] = result
                return result

        # No match - employer is NOT classified as financial
        self._match_cache[employer_upper] = None
        return None

    def get_stats(self) -> Dict:
        """Get statistics about the firm list."""
        if not self._loaded:
            self.build_firm_list()

        by_sector = defaultdict(int)
        for info in self._firms.values():
            by_sector[info['sector']] += 1

        return {
            'total_firms': len(self._firms),
            'by_sector': dict(sorted(by_sector.items(), key=lambda x: -x[1])),
        }

    def save_match_cache(self):
        """Save the match cache to disk."""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        # Only save non-None matches
        matches_to_save = {k: v for k, v in self._match_cache.items() if v is not None}
        with open(EMPLOYER_MATCH_CACHE, 'w') as f:
            json.dump(matches_to_save, f, indent=2)
        logger.info(f"Saved {len(matches_to_save)} employer matches to cache")

    def get_all_firms(self) -> Dict[str, Dict]:
        """Return all known firms for inspection."""
        if not self._loaded:
            self.build_firm_list()
        return self._firms.copy()


def test_firm_matcher():
    """Test the firm matcher with exact matching only."""
    logging.basicConfig(level=logging.INFO)

    matcher = FirmMatcher()
    matcher.build_firm_list(force=True)

    print("\nFirm List Statistics (Exact Match Only):")
    print("=" * 60)
    stats = matcher.get_stats()
    print(f"Total firms: {stats['total_firms']}")
    print("\nBy sector:")
    for sector, count in stats['by_sector'].items():
        print(f"  {sector}: {count}")

    # Test employers that SHOULD match (exact matches to PAC connected orgs)
    should_match = [
        ('GOLDMAN SACHS', 'investment_banking'),
        ('GOLDMAN SACHS & CO', 'investment_banking'),  # Normalizes to GOLDMAN SACHS
        ('JPMORGAN CHASE', 'banking'),
        ('WELLS FARGO', 'banking'),
        ('WELLS FARGO BANK', 'banking'),  # Normalizes to WELLS FARGO
        ('BANK OF AMERICA', 'banking'),
        ('BLACKROCK', 'investment'),
        ('BLACKROCK INC', 'investment'),  # Normalizes to BLACKROCK
        ('FIDELITY', 'investment'),
        ('STATE FARM', 'insurance'),
        ('ALLSTATE', 'insurance'),
        ('EDWARD JONES', 'investment'),
        ('CITIGROUP', 'banking'),
        ('CITIBANK', 'banking'),
    ]

    # Test employers that should NOT match (not PAC connected orgs)
    should_not_match = [
        'INDIANA SPINE GROUP',
        'UNIVERSITY OF MICHIGAN',
        'TEXAS TECH UNIVERSITY',
        'STATE OF CALIFORNIA',
        'GOVERNMENT',
        'SECURITY GUARD PATROL SERVICES',
        'WELLS ENTERPRISES',  # Ice cream company, not Wells Fargo
        'GOOGLE',
        'APPLE',
        'MICROSOFT',
        'SMALL TOWN BANK',  # Generic - probably no PAC
        'REGIONAL FINANCIAL ADVISORS',  # Boutique firm
        'RETIRED',
        'SELF-EMPLOYED',
    ]

    print("\n" + "=" * 70)
    print("SHOULD MATCH (PAC Connected Organizations):")
    print("=" * 70)
    match_passed = 0
    match_failed = 0
    for emp, expected_sector in should_match:
        result = matcher.match_employer(emp)
        if result:
            status = "PASS" if expected_sector in result['sector'] else "WARN"
            print(f"[{status}] {emp:40} -> {result['matched_firm']} ({result['sector']})")
            match_passed += 1
        else:
            print(f"[FAIL] {emp:40} -> NO MATCH (expected {expected_sector})")
            match_failed += 1

    print(f"\nMatched: {match_passed}/{len(should_match)}")

    print("\n" + "=" * 70)
    print("SHOULD NOT MATCH (Not PAC Connected Orgs):")
    print("=" * 70)
    no_match_passed = 0
    no_match_failed = 0
    for emp in should_not_match:
        result = matcher.match_employer(emp)
        if result:
            print(f"[FAIL] {emp:40} -> {result['matched_firm']} ({result['sector']}) - FALSE POSITIVE!")
            no_match_failed += 1
        else:
            print(f"[PASS] {emp:40} -> NO MATCH (correct)")
            no_match_passed += 1

    print(f"\nCorrectly rejected: {no_match_passed}/{len(should_not_match)}")

    print("\n" + "=" * 70)
    print("SUMMARY:")
    print("=" * 70)
    print(f"True positives: {match_passed}/{len(should_match)}")
    print(f"False positives prevented: {no_match_passed}/{len(should_not_match)}")

    # Show sample of firms in the list
    print("\n" + "=" * 70)
    print("Sample of firms in exact match list:")
    print("=" * 70)
    firms = matcher.get_all_firms()
    for i, (name, info) in enumerate(sorted(firms.items())[:30]):
        print(f"  {name[:45]:45} {info['sector']}")


if __name__ == '__main__':
    test_firm_matcher()
