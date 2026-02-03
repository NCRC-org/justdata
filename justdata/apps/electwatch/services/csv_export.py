#!/usr/bin/env python3
"""
CSV Export for ElectWatch Manual Review

Generates a CSV of all entities (PACs, employers, tickers) for Jay to manually classify.
This is the first step in the revamped data pipeline:
1. Collect ALL data without filtering
2. Generate this CSV with suggested classifications
3. Jay reviews and fills in the decision columns
4. Import Jay's decisions into manual_mappings.json
5. THEN calculate financial involvement metrics

Usage:
    from justdata.apps.electwatch.services.csv_export import generate_review_csv

    # After running the unfiltered data pipeline
    generate_review_csv(officials_data, output_path='data/exports/entities_for_review.csv')
"""

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


# =============================================================================
# KEYWORD MATCHING FOR SUGGESTIONS
# =============================================================================

# Keyword -> (sector, sub_sector) mapping for suggestions
SECTOR_KEYWORDS = {
    # Banking
    'BANK': ('financial', 'banking'),
    'BANKING': ('financial', 'banking'),
    'BANKERS': ('financial', 'banking'),
    'BANCORP': ('financial', 'banking'),
    'CREDIT UNION': ('financial', 'banking'),
    'FCU': ('financial', 'banking'),
    'FEDERAL CREDIT': ('financial', 'banking'),
    'SAVINGS AND LOAN': ('financial', 'banking'),

    # Mortgage
    'MORTGAGE': ('financial', 'mortgage'),
    'HOME LOAN': ('financial', 'mortgage'),
    'HOUSING FINANCE': ('financial', 'mortgage'),
    'FANNIE MAE': ('financial', 'mortgage'),
    'FREDDIE MAC': ('financial', 'mortgage'),
    'FHLB': ('financial', 'mortgage'),
    'FEDERAL HOME LOAN': ('financial', 'mortgage'),

    # Payments
    'VISA': ('financial', 'payments'),
    'MASTERCARD': ('financial', 'payments'),
    'AMERICAN EXPRESS': ('financial', 'payments'),
    'PAYPAL': ('financial', 'payments'),
    'PAYMENT': ('financial', 'payments'),

    # Payday
    'PAYDAY': ('financial', 'payday'),
    'CASH ADVANCE': ('financial', 'payday'),
    'CHECK INTO': ('financial', 'payday'),
    'CHECK CASHING': ('financial', 'payday'),

    # Insurance
    'TITLE INSURANCE': ('financial', 'insurance'),
    'TITLE COMPANY': ('financial', 'insurance'),
    'INSURANCE': ('financial', 'insurance'),
    'INSURERS': ('financial', 'insurance'),

    # Housing (supply side: builders, REITs, SFR operators)
    'HOMEBUILDER': ('financial', 'housing'),
    'HOME BUILDER': ('financial', 'housing'),
    'LENNAR': ('financial', 'housing'),
    'HORTON': ('financial', 'housing'),
    'D.R. HORTON': ('financial', 'housing'),
    'TOLL BROS': ('financial', 'housing'),
    'PULTE': ('financial', 'housing'),
    'KB HOME': ('financial', 'housing'),
    'MERITAGE': ('financial', 'housing'),
    'TAYLOR MORRISON': ('financial', 'housing'),
    'HOUSING REIT': ('financial', 'housing'),
    'INVITATION HOMES': ('financial', 'housing'),
    'AMERICAN HOMES': ('financial', 'housing'),

    # Real Estate (transaction side: brokers, agents, NAR, appraisers)
    'REALTOR': ('financial', 'real_estate'),
    'REALTORS': ('financial', 'real_estate'),
    'NATIONAL ASSOCIATION OF REALTORS': ('financial', 'real_estate'),
    'NAR PAC': ('financial', 'real_estate'),
    'REAL ESTATE BROKER': ('financial', 'real_estate'),
    'REAL ESTATE AGENT': ('financial', 'real_estate'),
    'REALTY': ('financial', 'real_estate'),
    'COLDWELL BANKER': ('financial', 'real_estate'),
    'KELLER WILLIAMS': ('financial', 'real_estate'),
    'RE/MAX': ('financial', 'real_estate'),
    'CENTURY 21': ('financial', 'real_estate'),
    'COMPASS REAL': ('financial', 'real_estate'),
    'APPRAISAL': ('financial', 'real_estate'),
    'APPRAISER': ('financial', 'real_estate'),

    # Investment Banking
    'GOLDMAN': ('financial', 'investment_banking'),
    'MORGAN STANLEY': ('financial', 'investment_banking'),
    'CITADEL': ('financial', 'investment_banking'),
    'SECURITIES': ('financial', 'investment_banking'),
    'HEDGE FUND': ('financial', 'investment_banking'),
    'PRIVATE EQUITY': ('financial', 'investment_banking'),
    'INVESTMENT': ('financial', 'investment_banking'),
    'ASSET MANAGEMENT': ('financial', 'investment_banking'),

    # Crypto
    'COINBASE': ('financial', 'crypto'),
    'CRYPTO': ('financial', 'crypto'),
    'BLOCKCHAIN': ('financial', 'crypto'),
    'BITCOIN': ('financial', 'crypto'),
    'DIGITAL ASSET': ('financial', 'crypto'),

    # Debt Collection
    'COLLECTION AGENCY': ('financial', 'debt_collection'),
    'DEBT BUYER': ('financial', 'debt_collection'),
    'DEBT COLLECTION': ('financial', 'debt_collection'),
    'COLLECTOR': ('financial', 'debt_collection'),

    # Credit Reporting
    'EQUIFAX': ('financial', 'credit_reporting'),
    'EXPERIAN': ('financial', 'credit_reporting'),
    'TRANSUNION': ('financial', 'credit_reporting'),
    'FICO': ('financial', 'credit_reporting'),
    'CREDIT BUREAU': ('financial', 'credit_reporting'),
    'CREDIT REPORTING': ('financial', 'credit_reporting'),

    # Community Development
    'CDFI': ('financial', 'community_development'),
    'COMMUNITY DEVELOPMENT': ('financial', 'community_development'),
    'LISC': ('financial', 'community_development'),

    # Consumer Lending
    'CONSUMER LENDING': ('financial', 'consumer_lending'),
    'CONSUMER FINANCE': ('financial', 'consumer_lending'),
    'LOAN': ('financial', 'consumer_lending'),
    'LENDING': ('financial', 'consumer_lending'),

    # Fintech
    'FINTECH': ('financial', 'fintech'),
    'SOFI': ('financial', 'fintech'),
    'ROBINHOOD': ('financial', 'fintech'),
}

# Keywords that indicate "industry" level (trade associations, not firms)
INDUSTRY_LEVEL_KEYWORDS = [
    'ASSOCIATION', 'ASSN', 'ASSOC',
    'INSTITUTE', 'COUNCIL', 'COALITION',
    'LEAGUE', 'FEDERATION', 'ALLIANCE',
    'SOCIETY', 'CONFERENCE', 'FORUM',
]


def suggest_sector(entity_name: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Suggest sector and sub_sector based on keyword matching.

    Args:
        entity_name: PAC name, employer name, etc.

    Returns:
        Tuple of (suggested_sector, suggested_sub_sector)
    """
    if not entity_name:
        return (None, None)

    name_upper = entity_name.upper()

    # Check each keyword (longer keywords first for better matching)
    sorted_keywords = sorted(SECTOR_KEYWORDS.keys(), key=len, reverse=True)
    for keyword in sorted_keywords:
        if keyword in name_upper:
            return SECTOR_KEYWORDS[keyword]

    return (None, None)


def suggest_entity_level(entity_name: str, entity_type: str) -> Optional[str]:
    """
    Suggest whether entity is 'industry' (trade association) or 'firm'.

    Args:
        entity_name: PAC name, employer name, or ticker
        entity_type: 'pac', 'employer', or 'ticker'

    Returns:
        'industry', 'firm', or None
    """
    if not entity_name:
        return None

    # Tickers are always firms
    if entity_type == 'ticker':
        return 'firm'

    # Employers are usually firms
    if entity_type == 'employer':
        return 'firm'

    # For PACs, check for industry association keywords
    name_upper = entity_name.upper()

    # Check for "OF AMERICA" combined with sector keywords (indicates industry group)
    if 'OF AMERICA' in name_upper:
        for keyword in INDUSTRY_LEVEL_KEYWORDS:
            if keyword in name_upper:
                return 'industry'

    # Check for standalone association keywords
    for keyword in INDUSTRY_LEVEL_KEYWORDS:
        if keyword in name_upper:
            return 'industry'

    # Check for firm indicators
    firm_indicators = ['INC', 'CORP', 'LLC', 'LP', 'LTD', '& CO', 'COMPANY']
    for indicator in firm_indicators:
        if indicator in name_upper:
            return 'firm'

    return None


# =============================================================================
# CSV GENERATION
# =============================================================================

def aggregate_entities_from_officials(officials_data: List[Dict]) -> Dict[str, Dict]:
    """
    Aggregate all PACs, employers, and tickers from officials data.

    Args:
        officials_data: List of official records with contributions and trades

    Returns:
        Dict with three keys: 'pacs', 'employers', 'tickers'
        Each maps entity names to aggregated stats
    """
    pacs = defaultdict(lambda: {'total_dollars': 0, 'officials': set(), 'transactions': 0})
    employers = defaultdict(lambda: {'total_dollars': 0, 'officials': set(), 'transactions': 0})
    tickers = defaultdict(lambda: {'total_dollars': 0, 'officials': set(), 'transactions': 0})

    for official in officials_data:
        official_name = official.get('name', 'Unknown')

        # Aggregate PAC contributions (check both field names - pac_contributions may be a total, not a list)
        pac_contribs = official.get('pac_contributions')
        if not isinstance(pac_contribs, list):
            pac_contribs = official.get('top_financial_pacs', [])
        if not isinstance(pac_contribs, list):
            pac_contribs = []
        for contrib in pac_contribs:
            pac_name = contrib.get('name', '') or contrib.get('source', '') or contrib.get('pac_name', '')
            if pac_name:
                pac_key = pac_name.upper().strip()
                pacs[pac_key]['total_dollars'] += contrib.get('amount', 0)
                pacs[pac_key]['officials'].add(official_name)
                pacs[pac_key]['transactions'] += contrib.get('count', 1)
                pacs[pac_key]['display_name'] = pac_name  # Preserve original case

        # Aggregate individual contributions by employer
        indiv_financial = official.get('top_individual_financial', [])
        if not isinstance(indiv_financial, list):
            indiv_financial = []
        for contrib in indiv_financial:
            employer = contrib.get('employer', '')
            if employer and employer.upper() not in ['SELF', 'SELF-EMPLOYED', 'RETIRED', 'N/A', 'NONE']:
                emp_key = employer.upper().strip()
                employers[emp_key]['total_dollars'] += contrib.get('amount', 0)
                employers[emp_key]['officials'].add(official_name)
                employers[emp_key]['transactions'] += 1
                employers[emp_key]['display_name'] = employer

        # Also check individual_financial_by_employer if available
        indiv_by_emp = official.get('individual_financial_by_employer', [])
        if not isinstance(indiv_by_emp, list):
            indiv_by_emp = []
        for emp_data in indiv_by_emp:
            employer = emp_data.get('name', '')
            if employer and employer.upper() not in ['SELF', 'SELF-EMPLOYED', 'RETIRED', 'N/A', 'NONE', 'UNKNOWN']:
                emp_key = employer.upper().strip()
                employers[emp_key]['total_dollars'] += emp_data.get('total', 0)
                employers[emp_key]['officials'].add(official_name)
                employers[emp_key]['transactions'] += emp_data.get('count', 1)
                employers[emp_key]['display_name'] = employer

        # Aggregate stock trades by ticker (check both field names)
        stock_trades = official.get('stock_trades') or official.get('trades', [])
        if not isinstance(stock_trades, list):
            stock_trades = []
        for trade in stock_trades:
            ticker = trade.get('ticker', '')
            if ticker:
                ticker_key = ticker.upper().strip()
                # Use minimum of amount range for aggregation
                amount = trade.get('amount', {})
                if isinstance(amount, dict):
                    min_amount = amount.get('min', 0)
                else:
                    min_amount = amount or 0
                tickers[ticker_key]['total_dollars'] += min_amount
                tickers[ticker_key]['officials'].add(official_name)
                tickers[ticker_key]['transactions'] += 1
                tickers[ticker_key]['display_name'] = ticker
                tickers[ticker_key]['company_name'] = trade.get('company', '')

    # Convert sets to counts
    for entity_dict in [pacs, employers, tickers]:
        for key in entity_dict:
            entity_dict[key]['official_count'] = len(entity_dict[key]['officials'])
            del entity_dict[key]['officials']  # Don't need the set anymore

    return {
        'pacs': dict(pacs),
        'employers': dict(employers),
        'tickers': dict(tickers)
    }


def generate_review_csv(
    officials_data: List[Dict],
    output_path: Optional[str] = None,
    min_threshold: int = 1000
) -> str:
    """
    Generate a CSV of all entities for manual classification.

    Args:
        officials_data: List of official records with contributions and trades
        output_path: Path for output CSV. If None, auto-generates in data/exports/
        min_threshold: Minimum total dollars to include (default $1,000)

    Returns:
        Path to the generated CSV file
    """
    # Set default output path
    if output_path is None:
        exports_dir = Path(__file__).parent.parent / "data" / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now().strftime('%Y%m%d')
        output_path = exports_dir / f"entities_for_review_{date_str}.csv"
    else:
        output_path = Path(output_path)

    # Aggregate entities
    logger.info("Aggregating entities from officials data...")
    entities = aggregate_entities_from_officials(officials_data)

    # Prepare rows
    rows = []

    # Process PACs
    for pac_key, data in entities['pacs'].items():
        if data['total_dollars'] >= min_threshold:
            sector, sub_sector = suggest_sector(data.get('display_name', pac_key))
            entity_level = suggest_entity_level(data.get('display_name', pac_key), 'pac')
            rows.append({
                'entity_type': 'pac',
                'entity_name': data.get('display_name', pac_key),
                'total_dollars': data['total_dollars'],
                'official_count': data['official_count'],
                'transaction_count': data['transactions'],
                'suggested_sector': sector or '',
                'suggested_sub_sector': sub_sector or '',
                'suggested_level': entity_level or '',
                'include': '',
                'sector': '',
                'sub_sector': '',
                'entity_level': ''
            })

    # Process employers
    for emp_key, data in entities['employers'].items():
        if data['total_dollars'] >= min_threshold:
            sector, sub_sector = suggest_sector(data.get('display_name', emp_key))
            entity_level = suggest_entity_level(data.get('display_name', emp_key), 'employer')
            rows.append({
                'entity_type': 'employer',
                'entity_name': data.get('display_name', emp_key),
                'total_dollars': data['total_dollars'],
                'official_count': data['official_count'],
                'transaction_count': data['transactions'],
                'suggested_sector': sector or '',
                'suggested_sub_sector': sub_sector or '',
                'suggested_level': entity_level or '',
                'include': '',
                'sector': '',
                'sub_sector': '',
                'entity_level': ''
            })

    # Process tickers
    for ticker_key, data in entities['tickers'].items():
        if data['total_dollars'] >= min_threshold:
            # Import here to avoid circular imports
            from justdata.apps.electwatch.services.fmp_client import suggest_sector_for_ticker
            sector, sub_sector = suggest_sector_for_ticker(ticker_key)
            rows.append({
                'entity_type': 'ticker',
                'entity_name': f"{ticker_key} ({data.get('company_name', '')})" if data.get('company_name') else ticker_key,
                'total_dollars': data['total_dollars'],
                'official_count': data['official_count'],
                'transaction_count': data['transactions'],
                'suggested_sector': sector or '',
                'suggested_sub_sector': sub_sector or '',
                'suggested_level': 'firm',  # Tickers are always firms
                'include': '',
                'sector': '',
                'sub_sector': '',
                'entity_level': ''
            })

    # Sort by total_dollars descending
    rows.sort(key=lambda x: x['total_dollars'], reverse=True)

    # Write CSV
    fieldnames = [
        'entity_type', 'entity_name', 'total_dollars', 'official_count', 'transaction_count',
        'suggested_sector', 'suggested_sub_sector', 'suggested_level',
        'include', 'sector', 'sub_sector', 'entity_level'
    ]

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    logger.info(f"Generated review CSV: {output_path}")
    logger.info(f"  PACs: {len([r for r in rows if r['entity_type'] == 'pac'])}")
    logger.info(f"  Employers: {len([r for r in rows if r['entity_type'] == 'employer'])}")
    logger.info(f"  Tickers: {len([r for r in rows if r['entity_type'] == 'ticker'])}")
    logger.info(f"  Total: {len(rows)} entities")

    return str(output_path)


def import_reviewed_csv(csv_path: str, mappings_path: Optional[str] = None) -> Dict:
    """
    Import Jay's reviewed CSV into manual_mappings.json.

    Args:
        csv_path: Path to the reviewed CSV file
        mappings_path: Path to manual_mappings.json. If None, uses default location.

    Returns:
        Stats dict with counts of imported decisions
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    if mappings_path is None:
        mappings_path = Path(__file__).parent.parent / "data" / "manual_mappings.json"
    else:
        mappings_path = Path(mappings_path)

    # Load existing mappings
    if mappings_path.exists():
        with open(mappings_path, 'r', encoding='utf-8') as f:
            mappings = json.load(f)
    else:
        mappings = {
            'version': 1,
            'last_updated': None,
            'pac_decisions': {},
            'employer_decisions': {},
            'ticker_decisions': {}
        }

    # Read and process CSV
    stats = {'pacs': 0, 'employers': 0, 'tickers': 0, 'skipped': 0}

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip if no decision made
            include = row.get('include', '').strip().upper()
            if include not in ['Y', 'N', 'YES', 'NO']:
                stats['skipped'] += 1
                continue

            entity_type = row.get('entity_type', '').lower()
            entity_name = row.get('entity_name', '').strip()
            sector = row.get('sector', '').strip().lower() or row.get('suggested_sector', '').strip().lower()
            sub_sector = row.get('sub_sector', '').strip().lower() or row.get('suggested_sub_sector', '').strip().lower()
            entity_level = row.get('entity_level', '').strip().lower() or row.get('suggested_level', '').strip().lower()

            # Extract ticker from "TICKER (Company Name)" format
            if entity_type == 'ticker' and '(' in entity_name:
                entity_name = entity_name.split('(')[0].strip()

            decision = {
                'include': include in ['Y', 'YES'],
                'sector': sector if sector else None,
                'sub_sector': sub_sector if sub_sector else None,
                'entity_level': entity_level if entity_level else None,
                'decided_by': 'jay',
                'decided_date': datetime.now().strftime('%Y-%m-%d')
            }

            key = entity_name.upper().strip()

            if entity_type == 'pac':
                mappings['pac_decisions'][key] = decision
                stats['pacs'] += 1
            elif entity_type == 'employer':
                mappings['employer_decisions'][key] = decision
                stats['employers'] += 1
            elif entity_type == 'ticker':
                mappings['ticker_decisions'][key] = decision
                stats['tickers'] += 1

    # Update timestamp and save
    mappings['last_updated'] = datetime.now().isoformat()

    with open(mappings_path, 'w', encoding='utf-8') as f:
        json.dump(mappings, f, indent=2)

    logger.info(f"Imported decisions into {mappings_path}")
    logger.info(f"  PACs: {stats['pacs']}, Employers: {stats['employers']}, Tickers: {stats['tickers']}")
    logger.info(f"  Skipped (no decision): {stats['skipped']}")

    return stats


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    # Test keyword matching
    test_names = [
        "AMERICAN BANKERS ASSOCIATION PAC",
        "JPMORGAN CHASE & CO PAC",
        "MORTGAGE BANKERS ASSOCIATION OF AMERICA PAC",
        "NATIONAL ASSOCIATION OF REALTORS PAC",
        "NATIONAL BEER WHOLESALERS PAC",
        "GOLDMAN SACHS",
        "ROCKET MORTGAGE",
        "COINBASE GLOBAL INC PAC",
    ]

    print("Testing keyword suggestions:")
    print("-" * 80)
    for name in test_names:
        sector, sub_sector = suggest_sector(name)
        level = suggest_entity_level(name, 'pac')
        print(f"{name}")
        print(f"  -> sector: {sector}, sub_sector: {sub_sector}, level: {level}")
        print()
