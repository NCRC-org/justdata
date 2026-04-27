"""Search / bill-lookup route handlers.

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


def api_search():
    """Search for officials, firms, or PACs."""
    query = request.args.get('q', '')
    search_type = request.args.get('type', 'all')  # 'official', 'firm', 'pac', 'all'

    return jsonify({
        'success': True,
        'query': query,
        'type': search_type,
        'results': []
    })

def api_search_bills():
    """
    Search for bills by keyword or bill ID.

    Query params:
        q: Search query (e.g., "cryptocurrency", "H.R. 4763", "stablecoin")
        limit: Max results (default 20)
    """
    from justdata.apps.electwatch.services.congress_api_client import get_congress_client

    query = request.args.get('q', '').strip()
    limit = int(request.args.get('limit', 20))

    if not query:
        return jsonify({
            'success': False,
            'error': 'Search query is required'
        }), 400

    client = get_congress_client()
    results = client.search_bills(query, limit=limit)

    return jsonify({
        'success': True,
        'query': query,
        'bills': results,
        'count': len(results)
    })

def api_get_bill(bill_id: str):
    """
    Get detailed information about a specific bill including sponsors, votes, and financial involvement.

    Args:
        bill_id: Bill identifier like "hr4763", "s1234", "H.R. 4763"
    """
    from justdata.apps.electwatch.services.bill_financial_enrichment import enrich_bill_with_financial_data
    from justdata.apps.electwatch.services.congress_api_client import get_congress_client

    client = get_congress_client()

    parsed = client.parse_bill_id(bill_id)
    if not parsed:
        return jsonify({
            'success': False,
            'error': f'Invalid bill ID format: {bill_id}. Use format like "H.R. 4763" or "S. 1234"'
        }), 400

    bill = client.get_bill(parsed['type'], parsed['number'], parsed.get('congress', '119'))

    if not bill:
        return jsonify({
            'success': False,
            'error': f'Bill not found: {bill_id}'
        }), 404

    bill_with_involvement = enrich_bill_with_financial_data(bill)

    return jsonify({
        'success': True,
        'bill': bill_with_involvement
    })

def normalize_bill_number(query: str) -> str:
    """
    Normalize various bill number formats to Congress.gov format.

    Examples:
        'HR 1234' -> 'hr1234'
        'S. 567' -> 's567'
        'H.R.1234' -> 'hr1234'
    """
    import re
    query = query.upper().replace(' ', '').replace('.', '')

    # Match patterns like HR1234, S123, HRES45, SRES67
    match = re.match(r'^(HR|S|HRES|SRES|HJRES|SJRES|HCONRES|SCONRES)(\d+)$', query)
    if match:
        prefix, number = match.groups()
        prefix_map = {
            'HR': 'hr', 'S': 's',
            'HRES': 'hres', 'SRES': 'sres',
            'HJRES': 'hjres', 'SJRES': 'sjres',
            'HCONRES': 'hconres', 'SCONRES': 'sconres'
        }
        return f"{prefix_map.get(prefix, prefix.lower())}{number}"

    return query.lower()

def fetch_bill_from_congress_api(bill_id: str):
    """
    Fetch bill data from Congress.gov API.

    Args:
        bill_id: Normalized bill ID (e.g., 'hr1234', 's567')

    Returns:
        Bill data dict or None if not found
    """
    import os
    import re
    import requests

    api_key = os.getenv('CONGRESS_API_KEY')
    if not api_key:
        logger.warning("CONGRESS_API_KEY not set - cannot fetch bill data")
        return None

    # Parse bill type and number
    match = re.match(r'^([a-z]+)(\d+)$', bill_id.lower())
    if not match:
        return None

    bill_type, bill_number = match.groups()

    # Current Congress (119th as of 2025)
    congress = 119

    # Congress.gov API endpoint
    url = f"https://api.congress.gov/v3/bill/{congress}/{bill_type}/{bill_number}"

    try:
        response = requests.get(
            url,
            params={'api_key': api_key},
            headers={'Accept': 'application/json'},
            timeout=30
        )

        if response.ok:
            data = response.json()
            bill = data.get('bill', {})
            return {
                'id': bill_id,
                'number': f"{bill_type.upper()} {bill_number}",
                'title': bill.get('title', ''),
                'short_title': bill.get('titles', [{}])[0].get('title', '') if bill.get('titles') else '',
                'sponsor': bill.get('sponsors', [{}])[0].get('fullName', '') if bill.get('sponsors') else '',
                'introduced': bill.get('introducedDate', ''),
                'latest_action': bill.get('latestAction', {}).get('text', ''),
                'latest_action_date': bill.get('latestAction', {}).get('actionDate', ''),
                'summary': bill.get('summaries', [{}])[0].get('text', '') if bill.get('summaries') else '',
                'congress': congress,
                'url': f"https://www.congress.gov/bill/{congress}th-congress/{bill_type}/{bill_number}"
            }
        else:
            logger.debug(f"Bill not found: {bill_id} (status {response.status_code})")
            return None

    except Exception as e:
        logger.error(f"Error fetching bill {bill_id}: {e}")
        return None

def api_bill_search():
    """Search for a bill by number."""
    query = request.args.get('q', '').strip()

    if not query:
        return jsonify({'success': False, 'error': 'No search query provided'}), 400

    # Normalize bill number
    bill_id = normalize_bill_number(query)

    # Fetch from Congress.gov API
    bill_data = fetch_bill_from_congress_api(bill_id)

    if bill_data:
        return jsonify({'success': True, 'bill': bill_data})
    else:
        return jsonify({'success': False, 'error': f'Bill {query} not found'})

