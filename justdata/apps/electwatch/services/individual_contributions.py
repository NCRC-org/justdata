"""
Individual Financial & Housing Sector Contributions Fetcher

This module identifies personal contributions from employees of financial and
housing-related firms. These represent personal relationships and social influence
beyond PAC money.

The financial and housing sectors are deeply intertwined:
- Mortgage lending is core bank business
- REITs are financial instruments
- Private equity owns millions of rental homes
- Real estate developers lobby alongside banks
- Housing policy IS financial policy (CRA, fair lending, etc.)

Example: Salvatore Fratto, Partner at Goldman Sachs, gave $6,600 to Dave McCormick.
Example: A landlord with 500 units gives $10K to a congressman on Banking Committee.

Both create social relationships - they'll see each other at fundraisers, industry
events. That social pressure is the real mechanism of influence.

Usage:
    from justdata.apps.electwatch.services.individual_contributions import fetch_individual_contributions

    # For a single official with their FEC committee ID
    results = fetch_individual_contributions(committee_id, api_key)

    # Returns: (total_amount, contributors_list, by_employer_list)
"""

import os
import logging
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

# Financial & Housing sector employers - these are the social relationships that matter
FINANCIAL_HOUSING_EMPLOYERS = {
    # Major Banks
    'GOLDMAN SACHS', 'JPMORGAN', 'JP MORGAN', 'MORGAN STANLEY', 'CITIGROUP', 'CITI',
    'BANK OF AMERICA', 'WELLS FARGO', 'BARCLAYS', 'DEUTSCHE BANK', 'UBS', 'CREDIT SUISSE',
    'HSBC', 'LAZARD', 'EVERCORE', 'MOELIS', 'JEFFERIES', 'PIPER SANDLER', 'RAYMOND JAMES',
    'COWEN', 'STIFEL',

    # Regional Banks
    'PNC', 'TRUIST', 'US BANCORP', 'U.S. BANCORP', 'FIFTH THIRD', 'REGIONS',
    'CITIZENS', 'HUNTINGTON', 'M&T BANK', 'KEYCORP', 'KEY BANK', 'ZIONS',
    'COMERICA', 'FIRST REPUBLIC', 'WESTERN ALLIANCE',

    # Investment Firms
    'BLACKROCK', 'BLACKSTONE', 'KKR', 'CARLYLE', 'APOLLO', 'TPG', 'WARBURG',
    'BAIN CAPITAL', 'ADVENT', 'VISTA EQUITY', 'SILVER LAKE', 'HELLMAN',
    'FIDELITY', 'VANGUARD', 'STATE STREET', 'NORTHERN TRUST', 'BNY MELLON',
    'CHARLES SCHWAB', 'TD AMERITRADE', 'INTERACTIVE BROKERS',

    # Hedge Funds
    'CITADEL', 'BRIDGEWATER', 'TWO SIGMA', 'DE SHAW', 'D.E. SHAW', 'RENAISSANCE',
    'MILLENNIUM', 'POINT72', 'ELLIOTT', 'BAUPOST', 'LONE PINE', 'TIGER GLOBAL',
    'COATUE', 'VIKING', 'THIRD POINT', 'PERSHING SQUARE', 'GREENLIGHT',

    # PE/VC
    'SEQUOIA', 'ANDREESSEN', 'A16Z', 'KLEINER', 'BENCHMARK', 'GREYLOCK',
    'GENERAL ATLANTIC', 'INSIGHT PARTNERS', 'THOMA BRAVO', 'LIGHTSPEED',

    # Insurance
    'AIG', 'METLIFE', 'PRUDENTIAL', 'ALLSTATE', 'PROGRESSIVE', 'TRAVELERS',
    'CHUBB', 'HARTFORD', 'AFLAC', 'LINCOLN FINANCIAL', 'PRINCIPAL',

    # Fintech/Payments
    'VISA', 'MASTERCARD', 'AMERICAN EXPRESS', 'PAYPAL', 'STRIPE', 'SQUARE', 'BLOCK INC',
    'COINBASE', 'ROBINHOOD', 'SOFI', 'AFFIRM', 'KLARNA', 'PLAID', 'CHIME',

    # Mortgage Lenders & Servicers
    'ROCKET MORTGAGE', 'QUICKEN LOANS', 'UNITED WHOLESALE', 'UWM', 'PENNYMAC',
    'FREEDOM MORTGAGE', 'MR COOPER', 'CALIBER HOME', 'GUILD MORTGAGE',
    'NATIONSTAR', 'LOANCARE', 'CENLAR', 'NEWREZ', 'PHH MORTGAGE',

    # Consumer Finance
    'CAPITAL ONE', 'DISCOVER', 'SYNCHRONY', 'ALLY FINANCIAL', 'SALLIE MAE',
    'NAVIENT', 'ONEMAIN', 'WORLD ACCEPTANCE',

    # Rating Agencies / Data
    'MOODY', "MOODY'S", 'S&P GLOBAL', 'FITCH', 'BLOOMBERG', 'REFINITIV', 'FACTSET',
    'MSCI', 'ICE', 'CME GROUP', 'NASDAQ', 'NYSE', 'CBOE',

    # Energy/Infrastructure Finance
    'MANIFEST ENERGY',

    # =========================================================================
    # HOUSING SECTOR - Real Estate, REITs, Developers, Property Management
    # =========================================================================

    # Large Homebuilders / Developers
    'LENNAR', 'D.R. HORTON', 'DR HORTON', 'PULTEGROUP', 'PULTE', 'NVR INC',
    'TOLL BROTHERS', 'MERITAGE HOMES', 'TAYLOR MORRISON', 'KB HOME',
    'CENTURY COMMUNITIES', 'TRI POINTE', 'DREAM FINDERS', 'SMITH DOUGLAS',

    # Commercial Real Estate Developers
    'RELATED COMPANIES', 'BROOKFIELD', 'HINES', 'TISHMAN SPEYER', 'BOSTON PROPERTIES',
    'VORNADO', 'SL GREEN', 'SILVERSTEIN', 'EXTELL', 'JDS DEVELOPMENT',
    'STARWOOD', 'LENDLEASE', 'SKANSKA',

    # REITs - Residential
    'INVITATION HOMES', 'AMERICAN HOMES 4 RENT', 'ESSEX PROPERTY', 'AVALONBAY',
    'EQUITY RESIDENTIAL', 'UDR INC', 'CAMDEN PROPERTY', 'MID-AMERICA APARTMENT',
    'APARTMENT INVESTMENT', 'AIMCO', 'INDEPENDENCE REALTY',

    # REITs - Commercial/Industrial
    'PROLOGIS', 'SIMON PROPERTY', 'REALTY INCOME', 'DIGITAL REALTY', 'EQUINIX',
    'PUBLIC STORAGE', 'EXTRA SPACE', 'CUBESMART', 'LIFE STORAGE',
    'WELLTOWER', 'VENTAS', 'HEALTHPEAK', 'MEDICAL PROPERTIES',
    'HOST HOTELS', 'PARK HOTELS', 'RLJ LODGING',

    # Large Property Management Companies
    'GREYSTAR', 'LINCOLN PROPERTY', 'CUSHMAN', 'JLL', 'JONES LANG LASALLE',
    'CBRE', 'COLLIERS', 'MARCUS & MILLICHAP', 'NEWMARK', 'BERKADIA',
    'FIRSTSERVICE', 'ASSOCIA', 'RPM LIVING', 'CORTLAND', 'MORGAN PROPERTIES',

    # Single-Family Rental Operators (Institutional Landlords)
    'PROGRESS RESIDENTIAL', 'TRICON RESIDENTIAL', 'PRETIUM PARTNERS',
    'AMHERST HOLDINGS', 'FRONT YARD RESIDENTIAL', 'VINEBROOK HOMES',

    # Title & Escrow Companies
    'FIRST AMERICAN', 'FIDELITY NATIONAL TITLE', 'OLD REPUBLIC', 'STEWART TITLE',
    'CHICAGO TITLE', 'COMMONWEALTH LAND',

    # Appraisal / Valuation
    'CORELOGIC', 'BLACK KNIGHT', 'CLEAR CAPITAL', 'VEROS',
}

# Alias for backwards compatibility
FINANCIAL_EMPLOYERS = FINANCIAL_HOUSING_EMPLOYERS

# Keywords to catch additional financial & housing sector employers
FINANCIAL_HOUSING_KEYWORDS = [
    # Traditional Finance
    'BANK', 'CAPITAL', 'INVESTMENT', 'SECURITIES', 'ASSET MANAGEMENT',
    'HEDGE FUND', 'PRIVATE EQUITY', 'VENTURE CAPITAL', 'FINANCIAL',
    'MORTGAGE', 'LENDING', 'CREDIT UNION', 'WEALTH MANAGEMENT',
    'BROKERAGE', 'TRADING', 'FUND MANAGER',

    # Housing/Real Estate
    'REAL ESTATE', 'REALTY', 'PROPERTY', 'PROPERTIES', 'REIT',
    'HOMEBUILDER', 'HOME BUILDER', 'DEVELOPER', 'DEVELOPMENT',
    'APARTMENT', 'RESIDENTIAL', 'HOUSING', 'LANDLORD',
    'PROPERTY MANAGEMENT', 'TITLE COMPANY', 'ESCROW',
]

# Occupations that indicate financial/housing sector involvement
# (even if employer name doesn't match)
FINANCIAL_HOUSING_OCCUPATIONS = [
    # Finance
    'BANKER', 'INVESTMENT BANKER', 'PORTFOLIO MANAGER', 'FUND MANAGER',
    'HEDGE FUND', 'PRIVATE EQUITY', 'VENTURE CAPITAL', 'VENTURE CAPITALIST',
    'FINANCIAL ADVISOR', 'FINANCIAL PLANNER', 'WEALTH MANAGER',
    'BROKER', 'STOCK BROKER', 'MORTGAGE BROKER', 'TRADER', 'TRADING',

    # Housing/Real Estate
    'LANDLORD', 'PROPERTY MANAGER', 'PROPERTY OWNER',
    'REAL ESTATE DEVELOPER', 'REAL ESTATE INVESTOR', 'REAL ESTATE',
    'REALTOR', 'REAL ESTATE BROKER', 'REAL ESTATE AGENT',
    'MORTGAGE BANKER', 'MORTGAGE OFFICER', 'LOAN OFFICER',
    'APPRAISER', 'TITLE AGENT',
    'HOMEBUILDER', 'HOME BUILDER', 'DEVELOPER',
]

# Alias for backwards compatibility
FINANCIAL_KEYWORDS = FINANCIAL_HOUSING_KEYWORDS


def is_financial_housing_employer(employer: str) -> bool:
    """
    Check if employer is in financial or housing sector.

    Args:
        employer: Employer name from FEC contribution record

    Returns:
        True if employer is a financial/housing sector firm
    """
    if not employer:
        return False

    emp_upper = employer.upper()

    # Check exact/partial matches against known firms
    for firm in FINANCIAL_HOUSING_EMPLOYERS:
        if firm in emp_upper:
            return True

    # Check keyword matches
    for keyword in FINANCIAL_HOUSING_KEYWORDS:
        if keyword in emp_upper:
            return True

    return False


def is_financial_housing_occupation(occupation: str) -> bool:
    """
    Check if occupation indicates financial or housing sector involvement.

    Args:
        occupation: Occupation from FEC contribution record

    Returns:
        True if occupation is financial/housing related
    """
    if not occupation:
        return False

    occ_upper = occupation.upper()

    for occ_keyword in FINANCIAL_HOUSING_OCCUPATIONS:
        if occ_keyword in occ_upper:
            return True

    return False


def is_financial_housing_contributor(employer: str, occupation: str) -> bool:
    """
    Check if contributor is in financial/housing sector based on employer OR occupation.

    Args:
        employer: Employer name from FEC contribution record
        occupation: Occupation from FEC contribution record

    Returns:
        True if either employer or occupation indicates financial/housing sector
    """
    return is_financial_housing_employer(employer) or is_financial_housing_occupation(occupation)


# Alias for backwards compatibility
def is_financial_employer(employer: str) -> bool:
    """Backwards compatible alias for is_financial_housing_employer."""
    return is_financial_housing_employer(employer)


def fetch_individual_contributions(
    committee_id: str,
    api_key: str,
    days_back: int = 730,
    max_pages: int = 10
) -> Dict:
    """
    Fetch individual contributions, tracking both financial/housing sector AND total.

    Args:
        committee_id: FEC committee ID for the candidate
        api_key: FEC API key
        days_back: How many days back to look (default 730 = 24 months)
        max_pages: Maximum API pages to fetch (default 10)

    Returns:
        Dict with:
            - financial_total: Total $ from financial/housing sector individuals
            - all_individual_total: Total $ from ALL individual contributors
            - financial_contributors: List of financial/housing sector contributors
            - by_employer: Aggregated by employer for financial/housing contributors
            - financial_pct: Percentage of individual $ from financial/housing sector
    """
    url = 'https://api.open.fec.gov/v1/schedules/schedule_a/'

    financial_total = 0
    all_individual_total = 0
    financial_contributors = []
    employers_seen = {}

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    min_date_str = start_date.strftime('%Y-%m-%d')
    max_date_str = end_date.strftime('%Y-%m-%d')

    for page in range(1, max_pages + 1):
        params = {
            'api_key': api_key,
            'committee_id': committee_id,
            'min_date': min_date_str,
            'max_date': max_date_str,
            'contributor_type': 'individual',  # Only individuals, not PACs
            'per_page': 100,
            'page': page,
            'sort': '-contribution_receipt_amount'  # Largest first
        }

        try:
            time.sleep(0.5)  # Rate limiting
            response = requests.get(url, params=params, timeout=60)

            if response.status_code == 429:
                logger.warning("FEC rate limited - waiting 60 seconds")
                time.sleep(60)
                continue

            if not response.ok:
                logger.error(f"FEC API error: {response.status_code}")
                break

            data = response.json()
            results = data.get('results', [])

            if not results:
                break

            for contrib in results:
                employer = contrib.get('contributor_employer', '')
                occupation = contrib.get('contributor_occupation', '')
                amount = contrib.get('contribution_receipt_amount', 0)

                if amount > 0:
                    # Track ALL individual contributions (denominator)
                    all_individual_total += amount

                    # Check if this is a financial/housing sector contributor
                    if is_financial_housing_contributor(employer, occupation):
                        financial_total += amount

                        # Track why this matched (for debugging/transparency)
                        match_reason = []
                        if is_financial_housing_employer(employer):
                            match_reason.append('employer')
                        if is_financial_housing_occupation(occupation):
                            match_reason.append('occupation')

                        contributor_info = {
                            'name': contrib.get('contributor_name', ''),
                            'employer': employer,
                            'occupation': occupation,
                            'amount': amount,
                            'date': contrib.get('contribution_receipt_date', ''),
                            'city': contrib.get('contributor_city', ''),
                            'state': contrib.get('contributor_state', ''),
                            'match_reason': '+'.join(match_reason)
                        }
                        financial_contributors.append(contributor_info)

                        # Aggregate by employer
                        emp_key = employer.upper().strip() if employer else 'UNKNOWN'
                        if emp_key not in employers_seen:
                            employers_seen[emp_key] = {
                                'name': employer or 'Unknown',
                                'total': 0,
                                'count': 0
                            }
                        employers_seen[emp_key]['total'] += amount
                        employers_seen[emp_key]['count'] += 1

            # Check if we've fetched all pages
            pages = data.get('pagination', {}).get('pages', 1)
            if page >= pages:
                break

        except Exception as e:
            logger.error(f"Error fetching individual contributions: {e}")
            break

    # Calculate percentage
    financial_pct = 0
    if all_individual_total > 0:
        financial_pct = round((financial_total / all_individual_total) * 100, 1)

    return {
        'financial_total': financial_total,
        'all_individual_total': all_individual_total,
        'financial_contributors': financial_contributors,
        'by_employer': list(employers_seen.values()),
        'financial_pct': financial_pct,
        'contributor_count': len(financial_contributors)
    }


def enrich_officials_with_individual_contributions(
    officials_data: List[Dict],
    api_key: Optional[str] = None,
    cached_names: Optional[set] = None,
    save_callback: Optional[callable] = None
) -> Dict:
    """
    Enrich a list of officials with individual financial sector contributions.

    Args:
        officials_data: List of official dicts (must have 'fec_committee_id')
        api_key: FEC API key (defaults to FEC_API_KEY env var)
        cached_names: Set of official names already processed (skip these)
        save_callback: Function to call periodically to save progress

    Returns:
        Status dict with matched count, total contributions, etc.
    """
    if api_key is None:
        api_key = os.getenv('FEC_API_KEY')

    if not api_key:
        logger.warning("FEC_API_KEY not set - skipping individual contributions")
        return {'status': 'skipped', 'reason': 'No API key'}

    logger.info("--- Fetching Individual Financial & Housing Sector Contributions ---")

    if cached_names:
        logger.info(f"  [CACHE] Skipping {len(cached_names)} already-processed officials")

    matched_count = 0
    total_amount = 0
    processed_names = list(cached_names) if cached_names else []
    save_interval = 25

    for i, official in enumerate(officials_data):
        name = official.get('name', '')

        # Skip if already processed
        if cached_names and name in cached_names:
            if official.get('individual_financial_total', 0) > 0:
                matched_count += 1
                total_amount += official.get('individual_financial_total', 0)
            continue

        committee_id = official.get('fec_committee_id')

        if not committee_id:
            continue

        # fetch_individual_contributions now returns a Dict
        result = fetch_individual_contributions(committee_id, api_key)

        financial_total = result.get('financial_total', 0)
        all_individual_total = result.get('all_individual_total', 0)
        contributors = result.get('financial_contributors', [])
        by_employer = result.get('by_employer', [])
        financial_pct = result.get('financial_pct', 0)

        # Store financial sector individual contributions (numerator)
        official['individual_financial_total'] = financial_total
        # Store ALL individual contributions (denominator for % calc)
        official['individual_contributions_total'] = all_individual_total
        # Store calculated percentage
        official['individual_financial_pct'] = financial_pct

        if financial_total > 0:
            matched_count += 1
            total_amount += financial_total

            # Store top individual contributors (sorted by amount)
            official['top_individual_financial'] = sorted(
                contributors,
                key=lambda x: x['amount'],
                reverse=True
            )[:10]

            # Store by employer ("5 Goldman employees gave $32K")
            official['individual_financial_by_employer'] = sorted(
                by_employer,
                key=lambda x: x['total'],
                reverse=True
            )[:5]

            logger.info(
                f"  {name}: ${financial_total:,.0f} from {len(contributors)} "
                f"financial/housing sector individuals ({len(by_employer)} employers) "
                f"= {financial_pct}% of ${all_individual_total:,.0f} total individual contributions"
            )
        elif all_individual_total > 0:
            # Log officials who have individual contributions but none from financial sector
            logger.debug(f"  {name}: $0 financial sector of ${all_individual_total:,.0f} total individual contributions")

        # Track processed name
        if name and name not in processed_names:
            processed_names.append(name)

        # Save progress periodically
        if save_callback and len(processed_names) % save_interval == 0:
            save_callback(processed_names, matched_count, total_amount)

        # Progress update
        if (i + 1) % 20 == 0:
            logger.info(f"  Progress: {i + 1}/{len(officials_data)} officials")

    # Final callback
    if save_callback:
        save_callback(processed_names, matched_count, total_amount)

    logger.info(
        f"Individual Financial/Housing: {matched_count}/{len(officials_data)} officials "
        f"have ${total_amount:,.0f} from financial & housing sector individuals"
    )

    return {
        'status': 'success',
        'matched_officials': matched_count,
        'total_contributions': total_amount,
        'processed_names': processed_names,
        'timestamp': datetime.now().isoformat()
    }
