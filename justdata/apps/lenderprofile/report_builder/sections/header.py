"""Institution header section."""
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

def build_institution_header(
    institution_data: Dict[str, Any],
    stock_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build the institution header bar with key identifiers and metrics.
    """
    institution = institution_data.get('institution', {})
    identifiers = institution_data.get('identifiers', {})
    details = institution_data.get('details', {})
    financial = institution_data.get('financial', {})

    name = institution.get('name') or identifiers.get('name', 'Unknown Institution')
    ticker = identifiers.get('ticker') or details.get('ticker', '')
    inst_type = institution.get('type') or details.get('cfpb_metadata', {}).get('type', '')

    # Total assets from FDIC
    total_assets = None
    fdic_data = financial.get('fdic_call_reports', [])
    if fdic_data:
        latest = fdic_data[0] if isinstance(fdic_data, list) else fdic_data
        # FDIC reports all dollar amounts in thousands - multiply by 1000
        total_assets = latest.get('ASSET', 0) * 1000
    if not total_assets:
        total_assets = institution.get('assets', 0)

    # CRA Rating
    cra_rating = institution_data.get('cra', {}).get('current_rating', '--')

    # Stock price if available
    stock_price = None
    if stock_data:
        stock_price = stock_data.get('current_price')

    # Headquarters location - try multiple sources
    city = institution.get('city', '') or identifiers.get('city', '')
    state = institution.get('state', '') or identifiers.get('state', '')

    # Try CFPB metadata
    if not city or not state:
        cfpb_meta = details.get('cfpb_metadata', {})
        city = city or cfpb_meta.get('city', '')
        state = state or cfpb_meta.get('state', '')

    # Try GLEIF corporate structure data
    if not city or not state:
        corp_structure = institution_data.get('corporate_structure', {})
        gleif_hq = corp_structure.get('headquarters', {})
        city = city or gleif_hq.get('city', '')
        state = state or gleif_hq.get('state', '')

    # Try SEC data if no city/state found
    if not city or not state:
        sec_data = institution_data.get('sec', {})
        submissions = sec_data.get('submissions', {})
        addresses = submissions.get('addresses', {})
        business_addr = addresses.get('business', {}) or addresses.get('mailing', {})
        if business_addr:
            city = city or business_addr.get('city', '')
            state = state or business_addr.get('stateOrCountry', '')

    # Convert to proper case
    if city:
        city = city.title()

    headquarters = f"{city}, {state}" if city and state else ''

    return {
        'institution_name': name,
        'headquarters': headquarters,
        'ticker': ticker,
        'institution_type': inst_type,
        'total_assets': _format_currency(total_assets),
        'cra_rating': cra_rating,
        'stock_price': f"${stock_price:.2f}" if stock_price else '--',
        'identifiers': {
            'fdic_cert': identifiers.get('fdic_cert'),
            'rssd_id': identifiers.get('rssd_id'),
            'lei': identifiers.get('lei'),
            'cik': identifiers.get('cik')
        }
    }


