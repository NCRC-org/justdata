"""Corporate structure section."""
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from justdata.apps.lenderprofile.report_builder.helpers import _format_currency

def build_corporate_structure(
    institution_data: Dict[str, Any],
    ticker_map: Optional[Dict[str, str]] = None,
    identifier_map: Optional[Dict[str, Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Build corporate structure tree from GLEIF and SEC data.
    Shows full GLEIF hierarchy with links to GLEIF pages.
    LEI numbers are included but not displayed - used for GLEIF links and copy button.

    Args:
        institution_data: Complete institution data
        ticker_map: Map of LEI/name to ticker symbols
        identifier_map: Map of LEI/name to identifiers (ticker, cik, fdic_cert)
    """
    details = institution_data.get('details', {})
    gleif_data = details.get('gleif_data', {})
    corporate_structure = institution_data.get('corporate_structure', {})
    sec_parsed = institution_data.get('sec_parsed', {}) or institution_data.get('sec', {}).get('parsed', {})

    ticker_map = ticker_map or {}
    identifier_map = identifier_map or {}

    # Current entity
    identifiers = institution_data.get('identifiers', {})
    current_lei = identifiers.get('lei', '')
    current_entity = {
        'name': institution_data.get('institution', {}).get('name', 'Unknown'),
        'lei': current_lei,
        'gleif_url': f'https://search.gleif.org/#/record/{current_lei}' if current_lei else None,
        'ticker': identifiers.get('ticker'),
        'cik': identifiers.get('cik'),
        'fdic_cert': identifiers.get('fdic_cert'),
        'is_current': True
    }

    # Ultimate parent - include all identifiers for linking
    ultimate_parent = None
    if corporate_structure.get('ultimate_parent'):
        up = corporate_structure['ultimate_parent']
        lei = up.get('lei', '')
        name = up.get('name', 'Unknown')

        # Get identifiers from map or direct data
        parent_ids = identifier_map.get(lei) or identifier_map.get(name) or {}

        ultimate_parent = {
            'name': name,
            'lei': lei,
            'gleif_url': f'https://search.gleif.org/#/record/{lei}' if lei else None,
            'ticker': ticker_map.get(lei) or ticker_map.get(name) or parent_ids.get('ticker'),
            'cik': up.get('cik') or parent_ids.get('cik'),
            'fdic_cert': up.get('fdic_cert') or parent_ids.get('fdic_cert')
        }

    # Get GLEIF subsidiaries structure (direct vs ultimate children)
    gleif_subs = corporate_structure.get('subsidiaries', {})
    direct_children_data = gleif_subs.get('direct', []) if isinstance(gleif_subs, dict) else []
    ultimate_children_data = gleif_subs.get('ultimate', []) if isinstance(gleif_subs, dict) else []

    # Build direct children list (first-level subsidiaries)
    direct_children = []
    for child in direct_children_data:
        lei = child.get('lei', '')
        name = child.get('name', 'Unknown')
        child_ids = identifier_map.get(lei) or identifier_map.get(name) or {}

        direct_children.append({
            'name': name,
            'lei': lei,
            'gleif_url': f'https://search.gleif.org/#/record/{lei}' if lei else None,
            'ticker': ticker_map.get(lei) or ticker_map.get(name) or child_ids.get('ticker'),
            'cik': child.get('cik') or child_ids.get('cik'),
            'fdic_cert': child.get('fdic_cert') or child_ids.get('fdic_cert'),
            'source': 'GLEIF',
            'relationship': 'direct'
        })

    # Build ultimate children list (grandchildren - subsidiaries of subsidiaries)
    ultimate_children = []
    for child in ultimate_children_data:
        lei = child.get('lei', '')
        name = child.get('name', 'Unknown')
        child_ids = identifier_map.get(lei) or identifier_map.get(name) or {}

        # Skip if already in direct children
        if any(d.get('lei') == lei for d in direct_children):
            continue

        ultimate_children.append({
            'name': name,
            'lei': lei,
            'gleif_url': f'https://search.gleif.org/#/record/{lei}' if lei else None,
            'ticker': ticker_map.get(lei) or ticker_map.get(name) or child_ids.get('ticker'),
            'cik': child.get('cik') or child_ids.get('cik'),
            'fdic_cert': child.get('fdic_cert') or child_ids.get('fdic_cert'),
            'source': 'GLEIF',
            'relationship': 'ultimate'
        })

    # Sort helper: main entities (banks) first, then by name
    def sort_priority(entity):
        name = (entity.get('name') or '').upper()
        # Main banks get highest priority
        if 'NATIONAL ASSOCIATION' in name or ', N.A.' in name:
            return (0, name)
        if 'BANK' in name and 'PENSION' not in name and 'TRUST FUND' not in name:
            return (1, name)
        # Funds and trusts get lowest priority
        if 'PENSION' in name or 'TRUST FUND' in name or 'COMMINGLED' in name:
            return (9, name)
        # Everything else in between
        return (5, name)

    # Sort direct and ultimate children to put main entities first
    direct_children.sort(key=sort_priority)
    ultimate_children.sort(key=sort_priority)

    # Combined list for backwards compatibility
    subsidiaries = direct_children + ultimate_children

    # Fall back to combined children list if no structured data
    if not subsidiaries:
        for child in corporate_structure.get('children', [])[:15]:
            lei = child.get('lei', '')
            name = child.get('name', 'Unknown')
            child_ids = identifier_map.get(lei) or identifier_map.get(name) or {}

            subsidiaries.append({
                'name': name,
                'lei': lei,
                'gleif_url': f'https://search.gleif.org/#/record/{lei}' if lei else None,
                'ticker': ticker_map.get(lei) or ticker_map.get(name) or child_ids.get('ticker'),
                'cik': child.get('cik') or child_ids.get('cik'),
                'fdic_cert': child.get('fdic_cert') or child_ids.get('fdic_cert'),
                'source': 'GLEIF'
            })
        # Sort fallback list too
        subsidiaries.sort(key=sort_priority)

    return {
        'ultimate_parent': ultimate_parent,
        'current_entity': current_entity,
        'direct_children': direct_children,
        'ultimate_children': ultimate_children,
        'subsidiaries': subsidiaries,
        'total_subsidiaries': len(subsidiaries),
        'has_data': bool(ultimate_parent or subsidiaries)
    }


