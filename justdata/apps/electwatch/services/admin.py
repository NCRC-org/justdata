"""Admin mapping / merge / unmatched route handlers.

Route-handler implementations extracted from blueprint.py. Each
function uses Flask's request context the same way it did inline
in the blueprint; the blueprint now contains thin wrappers that call
into here.
"""
import json
import logging
import threading
import uuid
from pathlib import Path
from urllib.parse import unquote

from flask import jsonify, render_template, request, Response, session

from justdata.main.auth import (
    admin_required,
    get_user_type,
    login_required,
    require_access,
    staff_required,
)
from justdata.shared.utils.progress_tracker import (
    create_progress_tracker,
    get_analysis_result,
    get_progress,
    store_analysis_result,
)

logger = logging.getLogger(__name__)


def api_admin_get_official_merges():
    """Get all official merge mappings (admin only)."""

    from justdata.apps.electwatch.services.mapping_store import get_official_merges
    return jsonify({'merges': get_official_merges()})

def api_admin_merge_official():
    """Add an alias to a canonical official (admin only)."""

    data = request.get_json()
    canonical = data.get('canonical')
    alias = data.get('alias')

    if not canonical or not alias:
        return jsonify({'success': False, 'error': 'Both canonical and alias required'})

    from justdata.apps.electwatch.services.mapping_store import add_official_merge
    result = add_official_merge(canonical, alias)
    return jsonify(result)

def api_admin_unmerge_official():
    """Remove an alias from a canonical official (admin only)."""

    data = request.get_json()
    canonical = data.get('canonical')
    alias = data.get('alias')

    from justdata.apps.electwatch.services.mapping_store import remove_official_alias
    result = remove_official_alias(canonical, alias)
    return jsonify(result)

def api_admin_delete_official_merge():
    """Delete all aliases for a canonical official (admin only)."""

    data = request.get_json()
    canonical = data.get('canonical')

    from justdata.apps.electwatch.services.mapping_store import delete_official_merge
    result = delete_official_merge(canonical)
    return jsonify(result)

def api_admin_potential_duplicate_officials():
    """
    Find potential duplicate officials - officials with the same last name but different first names.
    This helps identify cases like "Rick Allen" vs "Allen, Rick" that may need to be confirmed as
    the same or different people.
    """

    from justdata.apps.electwatch.services.data_store import get_officials
    from justdata.apps.electwatch.services.mapping_store import get_official_merges, get_distinct_officials
    from collections import defaultdict

    officials = get_officials()
    existing_merges = get_official_merges()
    distinct_pairs = get_distinct_officials()  # Pairs confirmed as different people

    # Create lookup for existing merge aliases
    merged_aliases = set()
    for merge in existing_merges:
        for alias in merge.get('aliases', []):
            merged_aliases.add(alias.lower())

    # Create lookup for distinct pairs
    distinct_set = set()
    for pair in distinct_pairs:
        # Store both directions
        key1 = (pair['official1'].lower(), pair['official2'].lower())
        key2 = (pair['official2'].lower(), pair['official1'].lower())
        distinct_set.add(key1)
        distinct_set.add(key2)

    # Group officials by last name
    by_last_name = defaultdict(list)
    for official in officials:
        name = official.get('name', '')
        if not name:
            continue

        # Parse name - handle both "First Last" and "Last, First" formats
        name_clean = name.strip()
        if ',' in name_clean:
            # "Last, First" format
            parts = [p.strip() for p in name_clean.split(',', 1)]
            if len(parts) == 2:
                last_name = parts[0].upper()
                first_name = parts[1].split()[0].upper() if parts[1] else ''
            else:
                last_name = name_clean.split()[-1].upper() if name_clean.split() else ''
                first_name = name_clean.split()[0].upper() if len(name_clean.split()) > 1 else ''
        else:
            # "First Last" format
            parts = name_clean.split()
            if len(parts) >= 2:
                last_name = parts[-1].upper()
                first_name = parts[0].upper()
            else:
                last_name = name_clean.upper()
                first_name = ''

        if last_name:
            by_last_name[last_name].append({
                'name': name,
                'first_name': first_name,
                'last_name': last_name,
                'id': official.get('id', ''),
                'bioguide_id': official.get('bioguide_id', ''),
                'state': official.get('state', ''),
                'party': official.get('party', ''),
                'chamber': official.get('chamber', '')
            })

    # Find groups with multiple officials (potential duplicates)
    potential_duplicates = []
    for last_name, group in by_last_name.items():
        if len(group) < 2:
            continue

        # Check if any pair in this group hasn't been handled yet
        unresolved_pairs = []
        for i, o1 in enumerate(group):
            for o2 in group[i + 1:]:
                # Skip if already merged
                if o1['name'].lower() in merged_aliases or o2['name'].lower() in merged_aliases:
                    continue

                # Skip if confirmed as distinct
                pair_key = (o1['name'].lower(), o2['name'].lower())
                if pair_key in distinct_set:
                    continue

                # Use BioGuide IDs to definitively determine if same/different person
                bio1 = o1.get('bioguide_id', '').strip()
                bio2 = o2.get('bioguide_id', '').strip()

                # If both have BioGuide IDs and they're different, these are definitely different people
                if bio1 and bio2 and bio1 != bio2:
                    continue  # Skip - confirmed different people by BioGuide

                # If different chambers (Senator vs Representative) with different states, different people
                chamber1 = o1.get('chamber', '').lower()
                chamber2 = o2.get('chamber', '').lower()
                state1 = o1.get('state', '').upper()
                state2 = o2.get('state', '').upper()

                # Different states = different people (unless same BioGuide which means they moved)
                if state1 and state2 and state1 != state2 and not (bio1 and bio2 and bio1 == bio2):
                    continue  # Skip - different states, clearly different people

                # Determine match confidence
                same_bioguide = bio1 == bio2 if bio1 and bio2 else None
                confidence = 'high' if same_bioguide else ('medium' if chamber1 == chamber2 and state1 == state2 else 'low')

                # This is an unresolved potential duplicate
                unresolved_pairs.append({
                    'official1': o1,
                    'official2': o2,
                    'same_bioguide': same_bioguide,
                    'confidence': confidence,
                    'reason': 'Same BioGuide ID' if same_bioguide else f'Same last name, {state1 or "unknown state"}'
                })

        if unresolved_pairs:
            potential_duplicates.extend(unresolved_pairs)

    return jsonify({
        'potential_duplicates': potential_duplicates,
        'count': len(potential_duplicates)
    })

def api_admin_mark_officials_distinct():
    """
    Mark two officials as distinct (confirmed different people, not duplicates).
    This prevents them from being shown as potential duplicates in the future.
    """

    data = request.get_json()
    official1 = data.get('official1')
    official2 = data.get('official2')

    if not official1 or not official2:
        return jsonify({'success': False, 'error': 'Both official1 and official2 required'})

    from justdata.apps.electwatch.services.mapping_store import add_distinct_officials
    result = add_distinct_officials(official1, official2)
    return jsonify(result)

def api_admin_get_firms():
    """Get custom firm definitions (admin only)."""

    from justdata.apps.electwatch.services.mapping_store import get_custom_firms
    return jsonify({'firms': get_custom_firms()})

def api_admin_get_all_firms():
    """Get all firms (built-in + custom) for dropdown (admin only)."""

    from justdata.apps.electwatch.services.mapping_store import get_all_firms
    return jsonify({'firms': get_all_firms()})

def api_admin_add_firm():
    """Add a custom firm definition (admin only)."""

    data = request.get_json()
    name = data.get('name')
    ticker = data.get('ticker')
    industry = data.get('industry')

    if not name or not industry:
        return jsonify({'success': False, 'error': 'Name and industry required'})

    from justdata.apps.electwatch.services.mapping_store import add_custom_firm
    result = add_custom_firm(name, ticker, industry)
    return jsonify(result)

def api_admin_delete_firm():
    """Delete a custom firm (admin only)."""

    data = request.get_json()
    name = data.get('name')

    from justdata.apps.electwatch.services.mapping_store import delete_custom_firm
    result = delete_custom_firm(name)
    return jsonify(result)

def api_admin_get_firm_aliases(firm_id):
    """Get employer aliases for a firm (admin only)."""

    from justdata.apps.electwatch.services.mapping_store import get_firm_employer_aliases
    return jsonify({'aliases': get_firm_employer_aliases(firm_id)})

def api_admin_add_employer_alias():
    """Add an employer alias to a firm (admin only)."""

    data = request.get_json()
    firm_id = data.get('firm_id')
    employer_name = data.get('employer_name')

    if not firm_id or not employer_name:
        return jsonify({'success': False, 'error': 'firm_id and employer_name required'})

    from justdata.apps.electwatch.services.mapping_store import add_employer_alias
    result = add_employer_alias(firm_id, employer_name)
    return jsonify(result)

def api_admin_remove_employer_alias():
    """Remove an employer alias from a firm (admin only)."""

    data = request.get_json()
    firm_id = data.get('firm_id')
    employer_name = data.get('employer_name')

    from justdata.apps.electwatch.services.mapping_store import remove_employer_alias
    result = remove_employer_alias(firm_id, employer_name)
    return jsonify(result)

def api_admin_get_unmatched_employers():
    """Get unmatched employers from FEC data (admin only)."""

    limit = request.args.get('limit', 50, type=int)

    from justdata.apps.electwatch.services.mapping_store import get_unmatched_employers
    return jsonify({'employers': get_unmatched_employers(limit)})

def api_admin_search_employers():
    """Search for employer names in FEC data (admin only)."""

    query = request.args.get('q', '')
    limit = request.args.get('limit', 20, type=int)

    from justdata.apps.electwatch.services.mapping_store import search_employers
    return jsonify({'employers': search_employers(query, limit)})

def api_admin_get_unmatched_pacs():
    """Get unmatched PAC names that couldn't be mapped to companies (admin only)."""

    from justdata.apps.electwatch.services.mapping_store import get_unmatched_pacs
    return jsonify({'pacs': get_unmatched_pacs()})

def api_admin_get_unmatched_tickers():
    """Get stock tickers that haven't been categorized into an industry (admin only)."""

    from justdata.apps.electwatch.services.mapping_store import get_uncategorized_tickers
    return jsonify({'tickers': get_uncategorized_tickers()})

