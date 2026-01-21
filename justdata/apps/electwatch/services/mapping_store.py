#!/usr/bin/env python3
"""
ElectWatch Mapping Store

Admin-managed mappings for entity resolution:
- Official merges (deduplication of Congress members)
- Firm definitions (company → industry)
- Employer aliases (FEC employer names → canonical firms)

Storage: JSON files in data/admin/
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# Data directory
APP_DIR = Path(__file__).parent.parent.absolute()
ADMIN_DIR = APP_DIR / 'data' / 'admin'


def ensure_dirs():
    """Ensure admin data directory exists."""
    ADMIN_DIR.mkdir(parents=True, exist_ok=True)


def _load_json(filename: str) -> Dict:
    """Load a JSON file from admin directory."""
    ensure_dirs()
    filepath = ADMIN_DIR / filename
    if not filepath.exists():
        return {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading {filepath}: {e}")
        return {}


def _save_json(filename: str, data: Dict):
    """Save data to JSON file in admin directory."""
    ensure_dirs()
    filepath = ADMIN_DIR / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    logger.info(f"Saved {filename}")


# =============================================================================
# OFFICIAL MERGES
# =============================================================================

def get_official_merges() -> List[Dict]:
    """
    Get all official merge mappings.

    Returns:
        List of merge records: [
            {
                "canonical": "Ted Cruz",
                "aliases": ["Rafael Cruz", "Rafael Edward Cruz"],
                "created_at": "2026-01-20T15:30:00"
            }
        ]
    """
    data = _load_json('official_merges.json')
    return data.get('merges', [])


def add_official_merge(canonical: str, alias: str) -> Dict:
    """
    Add an alias to a canonical official.

    Args:
        canonical: The canonical (preferred) name
        alias: The alias name to merge into canonical

    Returns:
        Result dict with success status
    """
    data = _load_json('official_merges.json')
    merges = data.get('merges', [])

    # Check if alias is already mapped somewhere
    for merge in merges:
        if alias in merge.get('aliases', []):
            return {'success': False, 'error': f'"{alias}" is already mapped to "{merge["canonical"]}"'}
        if alias == merge.get('canonical'):
            return {'success': False, 'error': f'"{alias}" is a canonical name, cannot use as alias'}

    # Find or create canonical entry
    existing = None
    for merge in merges:
        if merge.get('canonical') == canonical:
            existing = merge
            break

    if existing:
        if alias not in existing.get('aliases', []):
            existing.setdefault('aliases', []).append(alias)
            existing['updated_at'] = datetime.now().isoformat()
    else:
        merges.append({
            'canonical': canonical,
            'aliases': [alias],
            'created_at': datetime.now().isoformat()
        })

    data['merges'] = merges
    data['updated_at'] = datetime.now().isoformat()
    _save_json('official_merges.json', data)

    return {'success': True}


def remove_official_alias(canonical: str, alias: str) -> Dict:
    """Remove an alias from a canonical official."""
    data = _load_json('official_merges.json')
    merges = data.get('merges', [])

    for merge in merges:
        if merge.get('canonical') == canonical:
            if alias in merge.get('aliases', []):
                merge['aliases'].remove(alias)
                merge['updated_at'] = datetime.now().isoformat()
                data['merges'] = merges
                data['updated_at'] = datetime.now().isoformat()
                _save_json('official_merges.json', data)
                return {'success': True}

    return {'success': False, 'error': 'Alias not found'}


def delete_official_merge(canonical: str) -> Dict:
    """Delete all aliases for a canonical official."""
    data = _load_json('official_merges.json')
    merges = data.get('merges', [])

    new_merges = [m for m in merges if m.get('canonical') != canonical]

    if len(new_merges) == len(merges):
        return {'success': False, 'error': 'Canonical not found'}

    data['merges'] = new_merges
    data['updated_at'] = datetime.now().isoformat()
    _save_json('official_merges.json', data)

    return {'success': True}


def get_canonical_name(name: str) -> str:
    """
    Get canonical name for an official, resolving any aliases.

    Args:
        name: Official name (may be canonical or alias)

    Returns:
        Canonical name if mapped, otherwise original name
    """
    merges = get_official_merges()
    for merge in merges:
        if name in merge.get('aliases', []):
            return merge['canonical']
    return name


# =============================================================================
# FIRM DEFINITIONS
# =============================================================================

def get_custom_firms() -> List[Dict]:
    """
    Get all custom firm definitions.

    Returns:
        List of firm records: [
            {
                "id": "goldman_sachs",
                "name": "Goldman Sachs",
                "ticker": "GS",
                "industry": "investment",
                "employer_aliases": ["GOLDMAN", "GOLDMAN SACHS NYC"],
                "created_at": "2026-01-20T15:30:00"
            }
        ]
    """
    data = _load_json('custom_firms.json')
    return data.get('firms', [])


def get_all_firms() -> List[Dict]:
    """
    Get all firms (built-in + custom).

    Returns combined list from FIRM_DATABASE and custom firms.
    """
    # Import built-in firms
    try:
        from justdata.apps.electwatch.services.firm_mapper import FIRM_DATABASE
        builtin = [
            {
                'id': firm_id,
                'name': firm.name,
                'ticker': firm.ticker,
                'industry': firm.industries[0] if firm.industries else None,
                'is_builtin': True
            }
            for firm_id, firm in FIRM_DATABASE.items()
        ]
    except ImportError:
        builtin = []

    # Get custom firms
    custom = get_custom_firms()
    for firm in custom:
        firm['is_builtin'] = False

    return builtin + custom


def add_custom_firm(name: str, ticker: Optional[str], industry: str) -> Dict:
    """Add a custom firm definition."""
    data = _load_json('custom_firms.json')
    firms = data.get('firms', [])

    # Generate ID from name
    firm_id = name.lower().replace(' ', '_').replace('.', '').replace(',', '')

    # Check if already exists
    for firm in firms:
        if firm.get('id') == firm_id or firm.get('name').lower() == name.lower():
            # Update existing
            firm['name'] = name
            firm['ticker'] = ticker
            firm['industry'] = industry
            firm['updated_at'] = datetime.now().isoformat()
            data['firms'] = firms
            _save_json('custom_firms.json', data)
            return {'success': True, 'updated': True}

    # Add new
    firms.append({
        'id': firm_id,
        'name': name,
        'ticker': ticker,
        'industry': industry,
        'employer_aliases': [],
        'created_at': datetime.now().isoformat()
    })

    data['firms'] = firms
    data['updated_at'] = datetime.now().isoformat()
    _save_json('custom_firms.json', data)

    return {'success': True}


def delete_custom_firm(name: str) -> Dict:
    """Delete a custom firm definition."""
    data = _load_json('custom_firms.json')
    firms = data.get('firms', [])

    new_firms = [f for f in firms if f.get('name') != name]

    if len(new_firms) == len(firms):
        return {'success': False, 'error': 'Firm not found'}

    data['firms'] = new_firms
    data['updated_at'] = datetime.now().isoformat()
    _save_json('custom_firms.json', data)

    return {'success': True}


# =============================================================================
# EMPLOYER ALIASES
# =============================================================================

def get_firm_employer_aliases(firm_id: str) -> List[str]:
    """Get employer aliases for a firm."""
    # Check custom firms first
    firms = get_custom_firms()
    for firm in firms:
        if firm.get('id') == firm_id:
            return firm.get('employer_aliases', [])

    # Check built-in firm aliases
    try:
        from justdata.apps.electwatch.services.firm_mapper import FIRM_DATABASE
        if firm_id in FIRM_DATABASE:
            return FIRM_DATABASE[firm_id].aliases or []
    except ImportError:
        pass

    return []


def add_employer_alias(firm_id: str, employer_name: str) -> Dict:
    """Add an employer alias to a firm."""
    data = _load_json('custom_firms.json')
    firms = data.get('firms', [])

    # Normalize employer name
    employer_name = employer_name.upper().strip()

    # Find firm in custom firms
    firm = None
    for f in firms:
        if f.get('id') == firm_id:
            firm = f
            break

    if not firm:
        # Check if it's a built-in firm - if so, create a custom entry for aliases
        try:
            from justdata.apps.electwatch.services.firm_mapper import FIRM_DATABASE
            if firm_id in FIRM_DATABASE:
                builtin = FIRM_DATABASE[firm_id]
                firm = {
                    'id': firm_id,
                    'name': builtin.name,
                    'ticker': builtin.ticker,
                    'industry': builtin.industries[0] if builtin.industries else None,
                    'employer_aliases': [],
                    'created_at': datetime.now().isoformat()
                }
                firms.append(firm)
        except ImportError:
            pass

    if not firm:
        return {'success': False, 'error': 'Firm not found'}

    # Add alias if not already present
    if 'employer_aliases' not in firm:
        firm['employer_aliases'] = []

    if employer_name not in firm['employer_aliases']:
        firm['employer_aliases'].append(employer_name)
        firm['updated_at'] = datetime.now().isoformat()

    data['firms'] = firms
    data['updated_at'] = datetime.now().isoformat()
    _save_json('custom_firms.json', data)

    return {'success': True, 'firm_name': firm.get('name')}


def remove_employer_alias(firm_id: str, employer_name: str) -> Dict:
    """Remove an employer alias from a firm."""
    data = _load_json('custom_firms.json')
    firms = data.get('firms', [])

    employer_name = employer_name.upper().strip()

    for firm in firms:
        if firm.get('id') == firm_id:
            if employer_name in firm.get('employer_aliases', []):
                firm['employer_aliases'].remove(employer_name)
                firm['updated_at'] = datetime.now().isoformat()
                data['firms'] = firms
                _save_json('custom_firms.json', data)
                return {'success': True}

    return {'success': False, 'error': 'Alias not found'}


def get_firm_for_employer(employer_name: str) -> Optional[Dict]:
    """
    Look up firm for an employer name.

    Checks custom aliases first, then built-in firm database.

    Returns:
        Firm record dict or None
    """
    employer_upper = employer_name.upper().strip()

    # Check custom firms
    for firm in get_custom_firms():
        if employer_upper in firm.get('employer_aliases', []):
            return firm

    # Check built-in firms
    try:
        from justdata.apps.electwatch.services.firm_mapper import FirmMapper
        mapper = FirmMapper()
        result = mapper.get_firm_from_name(employer_name)
        if result:
            return {
                'name': result.name,
                'ticker': result.ticker,
                'industry': result.industries[0] if result.industries else None
            }
    except ImportError:
        pass

    return None


# =============================================================================
# UNMATCHED EMPLOYERS (for admin review)
# =============================================================================

def get_unmatched_employers(limit: int = 50) -> List[Dict]:
    """
    Get list of employer names from FEC data that haven't been matched.

    This would typically query the FEC data cache and filter out
    employers that are already mapped.

    For now, returns a placeholder - will be implemented when
    FEC individual contribution data is integrated.
    """
    # TODO: Implement when FEC individual contributions are stored
    # For now, return empty list
    return []


def search_employers(query: str, limit: int = 20) -> List[Dict]:
    """
    Search for employer names in FEC data.

    Args:
        query: Search term
        limit: Max results

    Returns:
        List of employer records with name and contribution count
    """
    # TODO: Implement when FEC individual contributions are stored
    # For now, return empty list
    return []


# =============================================================================
# UNMATCHED ENTITIES (for admin review)
# =============================================================================

# Known PAC name patterns that map to canonical companies
KNOWN_PAC_PATTERNS = {
    'JPMORGAN', 'JP MORGAN', 'BANK OF AMERICA', 'GOLDMAN SACHS', 'MORGAN STANLEY',
    'WELLS FARGO', 'CITIGROUP', 'CITI', 'AMERICAN EXPRESS', 'CAPITAL ONE',
    'BLACKROCK', 'CHARLES SCHWAB', 'FIDELITY', 'VANGUARD', 'STATE STREET',
    'BANK OF NEW YORK', 'BNY MELLON', 'NORTHERN TRUST', 'PNC', 'US BANK',
    'TRUIST', 'TD BANK', 'CITIZENS', 'FIFTH THIRD', 'REGIONS', 'HUNTINGTON',
    'M&T BANK', 'SYNCHRONY', 'DISCOVER', 'NAVIENT', 'SALLIE MAE', 'ROCKET',
    'ALLY', 'COINBASE', 'ROBINHOOD', 'PAYPAL', 'SQUARE', 'BLOCK INC',
    'VISA', 'MASTERCARD', 'AFLAC', 'METLIFE', 'PRUDENTIAL', 'AIG', 'ALLSTATE',
    'PROGRESSIVE', 'BERKSHIRE', 'FANNIE MAE', 'FREDDIE MAC', 'QUICKEN',
}

# Known financial sector tickers
KNOWN_FINANCIAL_TICKERS = {
    'JPM', 'BAC', 'GS', 'MS', 'WFC', 'C', 'AXP', 'COF', 'BLK', 'SCHW',
    'BK', 'STT', 'NTRS', 'PNC', 'USB', 'TFC', 'TD', 'CFG', 'FITB', 'RF',
    'HBAN', 'MTB', 'SYF', 'DFS', 'NAVI', 'RKT', 'UWMC', 'PFSI', 'COOP',
    'ALLY', 'COIN', 'HOOD', 'PYPL', 'SQ', 'V', 'MA', 'AFL', 'MET', 'PRU',
    'AIG', 'ALL', 'PGR', 'BRK.A', 'BRK.B', 'FNMA', 'FMCC',
}


def get_unmatched_pacs(limit: int = 50) -> List[Dict]:
    """
    Get PAC names from contribution data that couldn't be matched to known companies.

    Returns:
        List of unmatched PAC records with name, count, and total amount
    """
    from justdata.apps.electwatch.services.data_store import get_officials

    officials = get_officials()
    if not officials:
        return []

    # Collect all PAC names and their totals
    pac_totals = {}

    for official in officials:
        for pac in official.get('top_financial_pacs', []):
            pac_name = pac.get('name', '').upper().strip()
            if not pac_name:
                continue

            # Check if this PAC matches any known pattern
            is_known = any(pattern in pac_name for pattern in KNOWN_PAC_PATTERNS)
            if is_known:
                continue

            # Track unmatched PACs
            if pac_name not in pac_totals:
                pac_totals[pac_name] = {'name': pac.get('name', ''), 'count': 0, 'total_amount': 0}
            pac_totals[pac_name]['count'] += 1
            pac_totals[pac_name]['total_amount'] += pac.get('amount', 0)

    # Sort by total amount (descending) and return top N
    sorted_pacs = sorted(pac_totals.values(), key=lambda x: x['total_amount'], reverse=True)
    return sorted_pacs[:limit]


def get_uncategorized_tickers(limit: int = 50) -> List[Dict]:
    """
    Get stock tickers that haven't been categorized into a financial industry.

    Returns:
        List of uncategorized ticker records with ticker, company, trade count, and official count
    """
    from justdata.apps.electwatch.services.data_store import get_officials

    officials = get_officials()
    if not officials:
        return []

    # Collect all tickers from trades
    ticker_data = {}

    for official in officials:
        for trade in official.get('trades', []):
            ticker = trade.get('ticker', '').upper().strip()
            if not ticker:
                continue

            # Check if this ticker is in our known financial tickers
            if ticker in KNOWN_FINANCIAL_TICKERS:
                continue

            # Track unknown tickers
            if ticker not in ticker_data:
                ticker_data[ticker] = {
                    'ticker': ticker,
                    'company': trade.get('company', 'Unknown'),
                    'trade_count': 0,
                    'officials': set()
                }
            ticker_data[ticker]['trade_count'] += 1
            ticker_data[ticker]['officials'].add(official.get('name', ''))

    # Convert sets to counts and sort by trade count
    results = []
    for ticker, data in ticker_data.items():
        results.append({
            'ticker': data['ticker'],
            'company': data['company'],
            'trade_count': data['trade_count'],
            'official_count': len(data['officials'])
        })

    sorted_results = sorted(results, key=lambda x: x['trade_count'], reverse=True)
    return sorted_results[:limit]


# =============================================================================
# TESTING
# =============================================================================

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    print("Mapping Store Test")
    print("=" * 40)
    print(f"Admin directory: {ADMIN_DIR}")

    # Test official merges
    print("\n--- Official Merges ---")
    result = add_official_merge("Ted Cruz", "Rafael Cruz")
    print(f"Add merge: {result}")

    result = add_official_merge("Ted Cruz", "Rafael Edward Cruz")
    print(f"Add merge: {result}")

    merges = get_official_merges()
    print(f"All merges: {merges}")

    canonical = get_canonical_name("Rafael Cruz")
    print(f"Canonical for 'Rafael Cruz': {canonical}")

    # Test firm definitions
    print("\n--- Firm Definitions ---")
    result = add_custom_firm("Test Bank", "TEST", "banking")
    print(f"Add firm: {result}")

    firms = get_custom_firms()
    print(f"Custom firms: {len(firms)}")

    all_firms = get_all_firms()
    print(f"All firms (builtin + custom): {len(all_firms)}")
