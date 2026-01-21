#!/usr/bin/env python3
"""
ElectWatch Flask Web Application
Monitor elected officials' financial relationships with the financial industry.

A Just Data Tool by NCRC.
"""

import os
import sys
import uuid
import json
import threading
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, Response, send_file, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix

# Add repo root to path
REPO_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(REPO_ROOT))

# Import configuration
from justdata.apps.electwatch.config import ElectWatchConfig, TEMPLATES_DIR_STR, STATIC_DIR_STR
from justdata.apps.electwatch.version import __version__

# Import shared utilities
from justdata.shared.utils.unified_env import ensure_unified_env_loaded, get_unified_config
from justdata.shared.web.app_factory import create_app
from justdata.shared.utils.progress_tracker import (
    get_progress, update_progress, create_progress_tracker,
    store_analysis_result, get_analysis_result
)

# Load unified environment configuration
ensure_unified_env_loaded(verbose=True)
config = get_unified_config(verbose=True)

print(f"[ENV] Environment: {'LOCAL' if config.get('IS_LOCAL') else 'PRODUCTION'}")
print(f"[ENV] FEC_API_KEY available: {bool(ElectWatchConfig.FEC_API_KEY)}")
print(f"[ENV] QUIVER_API_KEY available: {bool(ElectWatchConfig.QUIVER_API_KEY)}")
print(f"[ENV] CONGRESS_GOV_API_KEY available: {bool(ElectWatchConfig.CONGRESS_GOV_API_KEY)}")

# Create Flask app using factory
app = create_app(
    'electwatch',
    template_folder=TEMPLATES_DIR_STR,
    static_folder=STATIC_DIR_STR
)

# Add ProxyFix for request handling behind Render's proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

# Configure Flask
app.secret_key = ElectWatchConfig.SECRET_KEY
app.config['DEBUG'] = True
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.jinja_env.bytecode_cache = None

# Disable caching for all responses
@app.after_request
def add_no_cache_headers(response):
    """Add no-cache headers to prevent browser/proxy caching."""
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# Debug: Log when data is loaded
print("[DEBUG] Flask app initialized - no caching enabled")


@app.before_request
def clear_template_cache():
    """Clear Jinja2 template cache before each request."""
    if hasattr(app, 'jinja_env'):
        app.jinja_env.bytecode_cache = None
        app.jinja_env.cache = {}
        app.jinja_env.auto_reload = True


@app.route('/static/img/ncrc-logo.png')
def serve_shared_logo():
    """Serve shared NCRC logo"""
    shared_logo_path = REPO_ROOT / 'shared' / 'web' / 'static' / 'img' / 'ncrc-logo.png'
    if shared_logo_path.exists():
        return send_from_directory(str(shared_logo_path.parent), shared_logo_path.name)
    return '', 404


# =============================================================================
# MAIN ROUTES
# =============================================================================

@app.route('/')
def index():
    """Main dashboard page - leaderboard of officials by involvement."""
    return render_template(
        'dashboard.html',
        version=__version__,
        sectors=_get_sectors()
    )


@app.route('/official/<official_id>')
def official_profile(official_id: str):
    """Individual official profile page."""
    return render_template(
        'official_profile.html',
        version=__version__,
        official_id=official_id
    )


@app.route('/industry/<sector>')
def industry_view(sector: str):
    """Industry-specific view."""
    from justdata.apps.electwatch.services.firm_mapper import get_sector_info
    sector_info = get_sector_info(sector)
    if not sector_info:
        return jsonify({'error': f'Unknown sector: {sector}'}), 404

    return render_template(
        'industry_view.html',
        version=__version__,
        sector=sector,
        sector_info=sector_info
    )


@app.route('/firm/<firm_name>')
def firm_view(firm_name: str):
    """Firm-specific view showing all connected officials."""
    return render_template(
        'firm_view.html',
        version=__version__,
        firm_name=firm_name
    )


@app.route('/committee/<committee_id>')
def committee_view(committee_id: str):
    """Committee-specific view showing members, votes, and legislation."""
    return render_template(
        'committee_view.html',
        version=__version__,
        committee_id=committee_id
    )


# =============================================================================
# API ROUTES
# =============================================================================

@app.route('/api/officials', methods=['GET'])
def api_get_officials():
    """
    Get list of officials with involvement scores.

    Data is served from weekly-updated static storage.

    Query params:
        - chamber: 'house' or 'senate'
        - party: 'R', 'D', or 'I'
        - state: Two-letter state code
        - industry: Industry sector code
        - sort: 'score', 'total', 'contributions', 'trades'
        - limit: Number of results (default 50)
    """
    chamber = request.args.get('chamber')
    party = request.args.get('party')
    state = request.args.get('state')
    industry = request.args.get('industry')
    sort_by = request.args.get('sort', 'score')
    limit = int(request.args.get('limit', 50))

    # PRIORITY 1: Try to get pre-computed weekly data from data store
    try:
        from justdata.apps.electwatch.services.data_store import get_officials, get_metadata
        stored_officials = get_officials()
        metadata = get_metadata()

        # DEBUG: Log data loading
        if stored_officials:
            first_official = stored_officials[0] if stored_officials else {}
            print(f"[DEBUG] Loaded {len(stored_officials)} officials from data store")
            print(f"[DEBUG] First official: {first_official.get('name')} - photo_url: {first_official.get('photo_url')}")

        if stored_officials and len(stored_officials) >= 5:
            # Filter by parameters
            filtered = stored_officials

            if chamber:
                filtered = [o for o in filtered if o.get('chamber', '').lower() == chamber.lower()]
            if party:
                filtered = [o for o in filtered if o.get('party', '').upper() == party.upper()]
            if state:
                filtered = [o for o in filtered if o.get('state', '').upper() == state.upper()]
            if industry:
                # top_industries can be list of objects [{code, name}] or list of strings
                filtered = [o for o in filtered if any(
                    (ind.get('code') == industry if isinstance(ind, dict) else ind == industry)
                    for ind in o.get('top_industries', [])
                )]

            # Sort
            if sort_by == 'score':
                filtered.sort(key=lambda x: x.get('involvement_score', 0), reverse=True)
            elif sort_by == 'contributions':
                filtered.sort(key=lambda x: x.get('contributions', 0), reverse=True)
            elif sort_by == 'trades':
                filtered.sort(key=lambda x: x.get('stock_trades_max', 0), reverse=True)
            else:
                filtered.sort(key=lambda x: x.get('total_amount', 0), reverse=True)

            # Format for response
            formatted = []
            for o in filtered[:limit]:
                # Get both total PAC and financial sector PAC separately
                total_pac = o.get('contributions', 0) or 0
                financial_pac = o.get('financial_sector_pac') or 0

                # Total stock trades = max of buys + max of sells
                purchases_max = o.get('purchases_max', 0)
                sales_max = o.get('sales_max', 0)
                stock_trades_max = purchases_max + sales_max

                # Total Involvement = Total PAC + Max Stock Trades
                total_amount = total_pac + stock_trades_max

                # Get photo attribution for hover tooltip
                # Photos sourced from Wikimedia Commons or U.S. House Clerk / Bioguide
                photo_attribution = None
                if o.get('photo_url'):
                    try:
                        from justdata.apps.electwatch.services.photo_service import get_photo_citation_for_api
                        photo_attribution = get_photo_citation_for_api(
                            name=o.get('name', ''),
                            photo_url=o.get('photo_url'),
                            photo_source=o.get('photo_source'),
                            bioguide_id=o.get('bioguide_id')
                        )
                        if 'wikimedia' in (o.get('photo_url') or '').lower():
                            print(f"[DEBUG PHOTO] {o.get('name')}: attribution={photo_attribution}")
                    except Exception as e:
                        print(f"[PHOTO ERROR] {o.get('name')}: {e}")
                        logger.error(f"[PHOTO] Error getting attribution for {o.get('name')}: {e}")

                formatted.append({
                    'id': o.get('id', o.get('name', '').lower().replace(' ', '_')),
                    'name': o.get('name', ''),
                    'party': o.get('party', ''),
                    'state': o.get('state', ''),
                    'district': None,
                    'chamber': o.get('chamber', 'house'),
                    'committees': o.get('committees', []),
                    'is_chair': o.get('is_chair', False),
                    'bioguide_id': o.get('bioguide_id', ''),
                    'fec_candidate_id': o.get('fec_candidate_id', ''),
                    'involvement_score': int(o.get('involvement_score', 0)),
                    'total_amount': total_amount,
                    'contributions': total_pac,  # Total PAC contributions
                    'stock_trades': stock_trades_max,
                    'stock_trades_range': {
                        'min': o.get('stock_trades_min', 0),
                        'max': o.get('stock_trades_max', 0),
                        'display': o.get('stock_trades_display', '$0')
                    },
                    # Separate buy/sell data
                    'purchases_min': o.get('purchases_min', 0),
                    'purchases_max': o.get('purchases_max', 0),
                    'purchases_display': o.get('purchases_display', '$0 - $0'),
                    'sales_min': o.get('sales_min', 0),
                    'sales_max': o.get('sales_max', 0),
                    'sales_display': o.get('sales_display', '$0 - $0'),
                    # Financial sector specific data
                    'financial_sector_pac': financial_pac,  # Financial sector PAC $
                    'contributing_pacs': o.get('contributing_pacs', []),
                    'top_industries': o.get('top_industries', []),
                    'score_breakdown': o.get('score_breakdown', {}),
                    'photo_url': o.get('photo_url'),
                    'photo_source': o.get('photo_source'),  # 'wikipedia', 'house_clerk', etc.
                    'photo_attribution': photo_attribution,  # Citation for hover tooltip
                })

            return jsonify({
                'success': True,
                'officials': formatted,
                'total': len(filtered),
                'data_source': 'weekly_update',
                'last_updated': metadata.get('last_updated_display', ''),
                'filters': {
                    'chamber': chamber,
                    'party': party,
                    'state': state,
                    'industry': industry
                }
            })
    except Exception as e:
        logger.warning(f"Could not load stored data: {e}")

    # Sample data for demonstration/fallback
    sample_officials = [
        {
            'id': 'hill_j_french',
            'name': 'J. French Hill',
            'party': 'R',
            'state': 'AR',
            'district': '2',
            'chamber': 'house',
            'committees': ['Financial Services'],
            'is_chair': True,
            'involvement_score': 92,
            'total_amount': 815000,
            'contributions': 590000,
            'stock_trades': 225000,
            'top_industries': ['banking', 'crypto', 'investment']
        },
        {
            'id': 'waters_maxine',
            'name': 'Maxine Waters',
            'party': 'D',
            'state': 'CA',
            'district': '43',
            'chamber': 'house',
            'committees': ['Financial Services'],
            'is_chair': False,
            'involvement_score': 85,
            'total_amount': 520000,
            'contributions': 480000,
            'stock_trades': 40000,
            'top_industries': ['banking', 'consumer_lending']
        },
        {
            'id': 'scott_tim',
            'name': 'Tim Scott',
            'party': 'R',
            'state': 'SC',
            'district': None,
            'chamber': 'senate',
            'committees': ['Banking, Housing, and Urban Affairs'],
            'is_chair': True,
            'involvement_score': 88,
            'total_amount': 720000,
            'contributions': 650000,
            'stock_trades': 70000,
            'top_industries': ['banking', 'investment', 'insurance']
        },
        {
            'id': 'warren_elizabeth',
            'name': 'Elizabeth Warren',
            'party': 'D',
            'state': 'MA',
            'district': None,
            'chamber': 'senate',
            'committees': ['Banking, Housing, and Urban Affairs', 'Finance'],
            'is_chair': False,
            'involvement_score': 65,
            'total_amount': 380000,
            'contributions': 370000,
            'stock_trades': 10000,
            'top_industries': ['consumer_lending', 'fintech']
        },
        {
            'id': 'emmer_tom',
            'name': 'Tom Emmer',
            'party': 'R',
            'state': 'MN',
            'district': '6',
            'chamber': 'house',
            'committees': ['Financial Services'],
            'is_chair': False,
            'involvement_score': 84,
            'total_amount': 580000,
            'contributions': 420000,
            'stock_trades': 160000,
            'top_industries': ['crypto', 'fintech', 'banking']
        },
        {
            'id': 'lummis_cynthia',
            'name': 'Cynthia Lummis',
            'party': 'R',
            'state': 'WY',
            'district': None,
            'chamber': 'senate',
            'committees': ['Banking, Housing, and Urban Affairs'],
            'is_chair': False,
            'involvement_score': 81,
            'total_amount': 520000,
            'contributions': 320000,
            'stock_trades': 200000,
            'top_industries': ['crypto', 'banking']
        },
        {
            'id': 'torres_ritchie',
            'name': 'Ritchie Torres',
            'party': 'D',
            'state': 'NY',
            'district': '15',
            'chamber': 'house',
            'committees': ['Financial Services'],
            'is_chair': False,
            'involvement_score': 76,
            'total_amount': 410000,
            'contributions': 350000,
            'stock_trades': 60000,
            'top_industries': ['crypto', 'fintech']
        },
        {
            'id': 'mchenry_patrick',
            'name': 'Patrick McHenry',
            'party': 'R',
            'state': 'NC',
            'district': '10',
            'chamber': 'house',
            'committees': ['Financial Services'],
            'is_chair': False,
            'involvement_score': 79,
            'total_amount': 480000,
            'contributions': 430000,
            'stock_trades': 50000,
            'top_industries': ['banking', 'crypto', 'investment']
        },
        {
            'id': 'pelosi_nancy',
            'name': 'Nancy Pelosi',
            'party': 'D',
            'state': 'CA',
            'district': '11',
            'chamber': 'house',
            'committees': [],
            'is_chair': False,
            'involvement_score': 91,
            'total_amount': 890000,
            'contributions': 240000,
            'stock_trades': 650000,
            'top_industries': ['investment', 'fintech', 'crypto']
        },
        {
            'id': 'tuberville_tommy',
            'name': 'Tommy Tuberville',
            'party': 'R',
            'state': 'AL',
            'district': None,
            'chamber': 'senate',
            'committees': ['Banking, Housing, and Urban Affairs'],
            'is_chair': False,
            'involvement_score': 78,
            'total_amount': 445000,
            'contributions': 180000,
            'stock_trades': 265000,
            'top_industries': ['banking', 'investment', 'insurance']
        },
        {
            'id': 'smith_jason',
            'name': 'Jason Smith',
            'party': 'R',
            'state': 'MO',
            'district': '8',
            'chamber': 'house',
            'committees': ['Ways and Means'],
            'is_chair': True,
            'involvement_score': 75,
            'total_amount': 420000,
            'contributions': 390000,
            'stock_trades': 30000,
            'top_industries': ['banking', 'insurance', 'investment']
        },
        {
            'id': 'neal_richard',
            'name': 'Richard Neal',
            'party': 'D',
            'state': 'MA',
            'district': '1',
            'chamber': 'house',
            'committees': ['Ways and Means'],
            'is_chair': False,
            'involvement_score': 72,
            'total_amount': 395000,
            'contributions': 380000,
            'stock_trades': 15000,
            'top_industries': ['insurance', 'banking', 'fintech']
        },
        {
            'id': 'crapo_mike',
            'name': 'Mike Crapo',
            'party': 'R',
            'state': 'ID',
            'district': None,
            'chamber': 'senate',
            'committees': ['Finance'],
            'is_chair': True,
            'involvement_score': 74,
            'total_amount': 405000,
            'contributions': 395000,
            'stock_trades': 10000,
            'top_industries': ['banking', 'insurance']
        },
        {
            'id': 'wyden_ron',
            'name': 'Ron Wyden',
            'party': 'D',
            'state': 'OR',
            'district': None,
            'chamber': 'senate',
            'committees': ['Finance'],
            'is_chair': False,
            'involvement_score': 68,
            'total_amount': 340000,
            'contributions': 330000,
            'stock_trades': 10000,
            'top_industries': ['fintech', 'investment']
        },
        {
            'id': 'hagerty_bill',
            'name': 'Bill Hagerty',
            'party': 'R',
            'state': 'TN',
            'district': None,
            'chamber': 'senate',
            'committees': ['Banking, Housing, and Urban Affairs'],
            'is_chair': False,
            'involvement_score': 77,
            'total_amount': 450000,
            'contributions': 320000,
            'stock_trades': 130000,
            'top_industries': ['banking', 'investment', 'crypto']
        },
        {
            'id': 'ossoff_jon',
            'name': 'Jon Ossoff',
            'party': 'D',
            'state': 'GA',
            'district': None,
            'chamber': 'senate',
            'committees': ['Banking, Housing, and Urban Affairs'],
            'is_chair': False,
            'involvement_score': 62,
            'total_amount': 290000,
            'contributions': 275000,
            'stock_trades': 15000,
            'top_industries': ['fintech', 'banking']
        },
        {
            'id': 'huizenga_bill',
            'name': 'Bill Huizenga',
            'party': 'R',
            'state': 'MI',
            'district': '4',
            'chamber': 'house',
            'committees': ['Financial Services'],
            'is_chair': False,
            'involvement_score': 73,
            'total_amount': 380000,
            'contributions': 350000,
            'stock_trades': 30000,
            'top_industries': ['banking', 'mortgage', 'insurance']
        },
        {
            'id': 'green_al',
            'name': 'Al Green',
            'party': 'D',
            'state': 'TX',
            'district': '9',
            'chamber': 'house',
            'committees': ['Financial Services'],
            'is_chair': False,
            'involvement_score': 64,
            'total_amount': 295000,
            'contributions': 285000,
            'stock_trades': 10000,
            'top_industries': ['consumer_lending', 'banking']
        },
        {
            'id': 'barr_andy',
            'name': 'Andy Barr',
            'party': 'R',
            'state': 'KY',
            'district': '6',
            'chamber': 'house',
            'committees': ['Financial Services'],
            'is_chair': False,
            'involvement_score': 71,
            'total_amount': 365000,
            'contributions': 340000,
            'stock_trades': 25000,
            'top_industries': ['banking', 'investment', 'insurance']
        },
        {
            'id': 'foster_bill',
            'name': 'Bill Foster',
            'party': 'D',
            'state': 'IL',
            'district': '11',
            'chamber': 'house',
            'committees': ['Financial Services'],
            'is_chair': False,
            'involvement_score': 67,
            'total_amount': 320000,
            'contributions': 280000,
            'stock_trades': 40000,
            'top_industries': ['fintech', 'banking', 'crypto']
        },
        {
            'id': 'lucas_frank',
            'name': 'Frank Lucas',
            'party': 'R',
            'state': 'OK',
            'district': '3',
            'chamber': 'house',
            'committees': ['Financial Services'],
            'is_chair': False,
            'involvement_score': 69,
            'total_amount': 335000,
            'contributions': 320000,
            'stock_trades': 15000,
            'top_industries': ['banking', 'insurance', 'mortgage']
        },
        {
            'id': 'himes_jim',
            'name': 'Jim Himes',
            'party': 'D',
            'state': 'CT',
            'district': '4',
            'chamber': 'house',
            'committees': ['Financial Services'],
            'is_chair': False,
            'involvement_score': 82,
            'total_amount': 495000,
            'contributions': 380000,
            'stock_trades': 115000,
            'top_industries': ['investment', 'banking', 'fintech']
        },
        {
            'id': 'sessions_pete',
            'name': 'Pete Sessions',
            'party': 'R',
            'state': 'TX',
            'district': '17',
            'chamber': 'house',
            'committees': ['Financial Services'],
            'is_chair': False,
            'involvement_score': 66,
            'total_amount': 315000,
            'contributions': 290000,
            'stock_trades': 25000,
            'top_industries': ['banking', 'insurance']
        },
        {
            'id': 'meeks_gregory',
            'name': 'Gregory Meeks',
            'party': 'D',
            'state': 'NY',
            'district': '5',
            'chamber': 'house',
            'committees': ['Financial Services'],
            'is_chair': False,
            'involvement_score': 70,
            'total_amount': 350000,
            'contributions': 335000,
            'stock_trades': 15000,
            'top_industries': ['banking', 'consumer_lending']
        },
        {
            'id': 'wicker_roger',
            'name': 'Roger Wicker',
            'party': 'R',
            'state': 'MS',
            'district': None,
            'chamber': 'senate',
            'committees': ['Budget'],
            'is_chair': False,
            'involvement_score': 63,
            'total_amount': 285000,
            'contributions': 275000,
            'stock_trades': 10000,
            'top_industries': ['banking', 'insurance']
        },
        {
            'id': 'brown_sherrod',
            'name': 'Sherrod Brown',
            'party': 'D',
            'state': 'OH',
            'district': None,
            'chamber': 'senate',
            'committees': ['Banking, Housing, and Urban Affairs'],
            'is_chair': False,
            'involvement_score': 58,
            'total_amount': 245000,
            'contributions': 240000,
            'stock_trades': 5000,
            'top_industries': ['consumer_lending', 'banking']
        },
        {
            'id': 'steil_bryan',
            'name': 'Bryan Steil',
            'party': 'R',
            'state': 'WI',
            'district': '1',
            'chamber': 'house',
            'committees': ['Financial Services'],
            'is_chair': False,
            'involvement_score': 68,
            'total_amount': 325000,
            'contributions': 300000,
            'stock_trades': 25000,
            'top_industries': ['banking', 'fintech']
        },
        {
            'id': 'perlmutter_ed',
            'name': 'Ed Perlmutter',
            'party': 'D',
            'state': 'CO',
            'district': '7',
            'chamber': 'house',
            'committees': ['Financial Services'],
            'is_chair': False,
            'involvement_score': 61,
            'total_amount': 270000,
            'contributions': 255000,
            'stock_trades': 15000,
            'top_industries': ['mortgage', 'banking', 'cannabis']
        },
        {
            'id': 'davidson_warren',
            'name': 'Warren Davidson',
            'party': 'R',
            'state': 'OH',
            'district': '8',
            'chamber': 'house',
            'committees': ['Financial Services'],
            'is_chair': False,
            'involvement_score': 74,
            'total_amount': 395000,
            'contributions': 280000,
            'stock_trades': 115000,
            'top_industries': ['crypto', 'fintech', 'banking']
        },
        {
            'id': 'sherman_brad',
            'name': 'Brad Sherman',
            'party': 'D',
            'state': 'CA',
            'district': '32',
            'chamber': 'house',
            'committees': ['Financial Services'],
            'is_chair': False,
            'involvement_score': 59,
            'total_amount': 255000,
            'contributions': 245000,
            'stock_trades': 10000,
            'top_industries': ['investment', 'banking']
        },
    ]

    # Apply filters
    filtered = sample_officials
    if chamber:
        filtered = [o for o in filtered if o['chamber'] == chamber]
    if party:
        filtered = [o for o in filtered if o['party'] == party]
    if state:
        filtered = [o for o in filtered if o['state'] == state]
    if industry:
        filtered = [o for o in filtered if industry in o.get('top_industries', [])]

    # Sort by total involvement (descending) by default
    if sort_by == 'score':
        filtered.sort(key=lambda x: x.get('involvement_score', 0), reverse=True)
    elif sort_by == 'contributions':
        filtered.sort(key=lambda x: x.get('contributions', 0), reverse=True)
    elif sort_by == 'trades':
        filtered.sort(key=lambda x: x.get('stock_trades', 0), reverse=True)
    else:  # default: total
        filtered.sort(key=lambda x: x.get('total_amount', 0), reverse=True)

    # Convert stock trades to STOCK Act ranges
    for official in filtered:
        trades = official.get('stock_trades', 0)
        official['stock_trades_range'] = _get_stock_act_range(trades)

    return jsonify({
        'success': True,
        'officials': filtered[:limit],
        'total': len(filtered),
        'filters': {
            'chamber': chamber,
            'party': party,
            'state': state,
            'industry': industry
        }
    })


def _get_stock_act_range(amount):
    """
    Convert a stock trade amount to STOCK Act disclosure bucket.
    STOCK Act requires disclosure in ranges, not exact amounts.
    """
    if amount <= 0:
        return {'min': 0, 'max': 0, 'display': '$0'}
    elif amount <= 15000:
        return {'min': 1001, 'max': 15000, 'display': '$1K-$15K'}
    elif amount <= 50000:
        return {'min': 15001, 'max': 50000, 'display': '$15K-$50K'}
    elif amount <= 100000:
        return {'min': 50001, 'max': 100000, 'display': '$50K-$100K'}
    elif amount <= 250000:
        return {'min': 100001, 'max': 250000, 'display': '$100K-$250K'}
    elif amount <= 500000:
        return {'min': 250001, 'max': 500000, 'display': '$250K-$500K'}
    elif amount <= 1000000:
        return {'min': 500001, 'max': 1000000, 'display': '$500K-$1M'}
    else:
        return {'min': 1000001, 'max': 5000000, 'display': '$1M-$5M'}


@app.route('/api/official/<official_id>', methods=['GET'])
def api_get_official(official_id: str):
    """Get detailed data for a specific official from weekly data store."""
    # PRIORITY 1: Try to get pre-computed weekly data from data store
    try:
        from justdata.apps.electwatch.services.data_store import get_official, get_metadata
        stored_official = get_official(official_id)
        metadata = get_metadata()

        if stored_official:
            # Format trades list for response
            trades_list = []
            for trade in stored_official.get('trades', [])[:20]:
                trades_list.append({
                    'company': trade.get('company_name', trade.get('ticker', '')),
                    'ticker': trade.get('ticker', ''),
                    'amount': trade.get('amount', {'min': 0, 'max': 0, 'display': '$0'}),
                    'date': trade.get('transaction_date', ''),
                    'transaction_type': trade.get('type', 'unknown').title()
                })

            official = {
                'id': stored_official.get('id', official_id),
                'name': stored_official.get('name', official_id.replace('_', ' ').title()),
                'party': stored_official.get('party', ''),
                'state': stored_official.get('state', ''),
                'chamber': stored_official.get('chamber', 'house'),
                'is_chair': stored_official.get('is_chair', False),
                'committees': stored_official.get('committees', []),
                'involvement_score': int(stored_official.get('involvement_score', 50)),
                'total_amount': stored_official.get('stock_trades_max', 0),
                'contributions': stored_official.get('contributions', 0),
                'stock_trades': stored_official.get('stock_trades_max', 0),
                'contributions_count': stored_official.get('contributions_count', 0),
                'trades_count': stored_official.get('total_trades', 0),
                'stock_trades_range': {
                    'min': stored_official.get('stock_trades_min', 0),
                    'max': stored_official.get('stock_trades_max', 0),
                    'display': stored_official.get('stock_trades_display', '$0')
                },
                'top_industries': stored_official.get('top_industries', []),
                'involvement_by_industry': stored_official.get('involvement_by_industry', {}),
                'firms': stored_official.get('firms', []),
                'contributions_list': stored_official.get('contributions_list', []),
                'trades_list': trades_list,
                'legislation': stored_official.get('legislation', []),
                'recent_news': stored_official.get('recent_news', []),
                # Years in Congress and Net Worth data
                'years_in_congress': stored_official.get('years_in_congress'),
                'first_elected': stored_official.get('first_elected'),
                'net_worth': stored_official.get('net_worth'),
                'net_worth_estimate': stored_official.get('net_worth_estimate'),
                'bioguide_id': stored_official.get('bioguide_id', ''),
                'photo_url': stored_official.get('photo_url'),
                'photo_source': stored_official.get('photo_source'),
                'photo_attribution': None,  # Will be set below
                # Financial PAC data
                'financial_sector_pac': stored_official.get('financial_sector_pac'),
                'top_financial_pacs': stored_official.get('top_financial_pacs', []),
                # Website URL (with overrides for non-standard URLs)
                'website_url': stored_official.get('website_url'),
                'data_source': 'weekly_update'
            }

            # Add photo attribution for hover tooltip
            # Photos sourced from Wikimedia Commons or U.S. House Clerk / Bioguide
            if official.get('photo_url'):
                try:
                    from justdata.apps.electwatch.services.photo_service import get_photo_citation_for_api
                    official['photo_attribution'] = get_photo_citation_for_api(
                        name=official.get('name', ''),
                        photo_url=official.get('photo_url'),
                        photo_source=official.get('photo_source'),
                        bioguide_id=official.get('bioguide_id')
                    )
                except Exception:
                    pass

            return jsonify({
                'success': True,
                'official': official,
                'data_source': 'weekly_update',
                'last_updated': metadata.get('last_updated_display', '')
            })
    except Exception as e:
        logger.warning(f"Could not load stored official data: {e}")

    # Fall back to sample data
    # Sample comprehensive official data
    officials_data = {
        'hill_j_french': {
            'id': 'hill_j_french',
            'name': 'J. French Hill',
            'party': 'R',
            'state': 'AR',
            'district': '2',
            'chamber': 'house',
            'is_chair': True,
            'photo_url': None,
            'born': '1956-12-05',
            'first_elected': 2014,
            'years_in_congress': 11,
            'net_worth_estimate': {'min': 10000000, 'max': 50000000, 'display': '$10M-$50M'},
            'committees': ['Financial Services (Chair)', 'Permanent Select Committee on Intelligence'],
            'subcommittees': ['Digital Assets, Financial Technology and Inclusion'],
            'leadership_roles': ['Chair, House Financial Services Committee'],
            'involvement_score': 92,
            'total_amount': 815000,
            'contributions': 590000,
            'stock_trades': 225000,
            'contributions_count': 47,
            'trades_count': 12,
            'top_industries': ['banking', 'crypto', 'investment'],
            'involvement_by_industry': {
                'banking': {'contributions': 350000, 'stock_trades': 75000, 'total': 425000},
                'crypto': {'contributions': 80000, 'stock_trades': 100000, 'total': 180000},
                'investment': {'contributions': 120000, 'stock_trades': 30000, 'total': 150000},
                'mortgage': {'contributions': 40000, 'stock_trades': 20000, 'total': 60000},
            },
            'firms': [
                {'name': 'Wells Fargo', 'ticker': 'WFC', 'total': 85000, 'type': 'mixed'},
                {'name': 'Coinbase', 'ticker': 'COIN', 'total': 75000, 'type': 'mixed'},
                {'name': 'JPMorgan Chase', 'ticker': 'JPM', 'total': 65000, 'type': 'contributions'},
                {'name': 'Bank of America', 'ticker': 'BAC', 'total': 55000, 'type': 'contributions'},
                {'name': 'BlackRock', 'ticker': 'BLK', 'total': 45000, 'type': 'mixed'},
                {'name': 'Goldman Sachs', 'ticker': 'GS', 'total': 40000, 'type': 'contributions'},
                {'name': 'Robinhood', 'ticker': 'HOOD', 'total': 35000, 'type': 'mixed'},
                {'name': 'Morgan Stanley', 'ticker': 'MS', 'total': 30000, 'type': 'contributions'},
            ],
            'contributions_list': [
                {'source': 'Wells Fargo PAC', 'amount': 50000, 'date': '2025-09-15', 'industry': 'banking'},
                {'source': 'JPMorgan Chase PAC', 'amount': 45000, 'date': '2025-08-20', 'industry': 'banking'},
                {'source': 'Coinbase Global PAC', 'amount': 40000, 'date': '2025-07-12', 'industry': 'crypto'},
                {'source': 'Bank of America PAC', 'amount': 35000, 'date': '2025-06-28', 'industry': 'banking'},
                {'source': 'Goldman Sachs PAC', 'amount': 30000, 'date': '2025-05-10', 'industry': 'investment'},
            ],
            'trades_list': [
                {'company': 'Coinbase Global', 'ticker': 'COIN', 'amount': {'min': 50001, 'max': 100000, 'display': '$50K-$100K'}, 'date': '2025-11-05', 'transaction_type': 'Purchase'},
                {'company': 'Wells Fargo', 'ticker': 'WFC', 'amount': {'min': 15001, 'max': 50000, 'display': '$15K-$50K'}, 'date': '2025-09-22', 'transaction_type': 'Purchase'},
                {'company': 'BlackRock', 'ticker': 'BLK', 'amount': {'min': 15001, 'max': 50000, 'display': '$15K-$50K'}, 'date': '2025-08-14', 'transaction_type': 'Purchase'},
                {'company': 'Robinhood', 'ticker': 'HOOD', 'amount': {'min': 15001, 'max': 50000, 'display': '$15K-$50K'}, 'date': '2025-07-03', 'transaction_type': 'Purchase'},
            ],
            'legislation': [
                {'title': 'Financial Innovation and Technology for the 21st Century Act', 'role': 'Sponsor', 'status': 'Passed House', 'date': '2025-05-22', 'relevance': 'crypto'},
                {'title': 'CBDC Anti-Surveillance State Act', 'role': 'Cosponsor', 'status': 'In Committee', 'date': '2025-03-08', 'relevance': 'crypto'},
                {'title': 'Bank Merger Modernization Act', 'role': 'Sponsor', 'status': 'In Committee', 'date': '2025-02-14', 'relevance': 'banking'},
            ],
            'recent_news': [
                {'headline': 'Rep. Hill Leads Crypto Regulation Push as Financial Services Chair', 'source': 'Bloomberg', 'date': '2025-12-15', 'url': '#'},
                {'headline': 'House Advances Stablecoin Bill with Bipartisan Support', 'source': 'CoinDesk', 'date': '2025-11-28', 'url': '#'},
                {'headline': 'Financial Services Chair Opposes Fed Digital Currency Plan', 'source': 'Wall Street Journal', 'date': '2025-10-12', 'url': '#'},
            ],
            'votes': [
                {'bill': 'Consumer Financial Protection Reform Act', 'vote': 'Yea', 'date': '2025-11-15', 'industry_impact': 'banking'},
                {'bill': 'Digital Asset Market Structure Act', 'vote': 'Yea', 'date': '2025-09-20', 'industry_impact': 'crypto'},
            ],
        },
        'waters_maxine': {
            'id': 'waters_maxine',
            'name': 'Maxine Waters',
            'party': 'D',
            'state': 'CA',
            'district': '43',
            'chamber': 'house',
            'is_chair': False,
            'born': '1938-08-15',
            'first_elected': 1990,
            'years_in_congress': 35,
            'net_worth_estimate': {'min': 1000000, 'max': 5000000, 'display': '$1M-$5M'},
            'committees': ['Financial Services (Ranking Member)'],
            'subcommittees': [],
            'leadership_roles': ['Ranking Member, House Financial Services Committee'],
            'involvement_score': 85,
            'total_amount': 520000,
            'contributions': 480000,
            'stock_trades': 40000,
            'contributions_count': 52,
            'trades_count': 3,
            'top_industries': ['banking', 'consumer_lending'],
            'involvement_by_industry': {
                'banking': {'contributions': 280000, 'stock_trades': 25000, 'total': 305000},
                'consumer_lending': {'contributions': 120000, 'stock_trades': 10000, 'total': 130000},
                'fintech': {'contributions': 80000, 'stock_trades': 5000, 'total': 85000},
            },
            'firms': [
                {'name': 'Bank of America', 'ticker': 'BAC', 'total': 65000, 'type': 'contributions'},
                {'name': 'JPMorgan Chase', 'ticker': 'JPM', 'total': 55000, 'type': 'contributions'},
                {'name': 'Wells Fargo', 'ticker': 'WFC', 'total': 50000, 'type': 'contributions'},
                {'name': 'Capital One', 'ticker': 'COF', 'total': 40000, 'type': 'contributions'},
                {'name': 'PayPal', 'ticker': 'PYPL', 'total': 35000, 'type': 'contributions'},
            ],
            'contributions_list': [
                {'source': 'Bank of America PAC', 'amount': 45000, 'date': '2025-10-20', 'industry': 'banking'},
                {'source': 'JPMorgan Chase PAC', 'amount': 40000, 'date': '2025-08-15', 'industry': 'banking'},
                {'source': 'Capital One PAC', 'amount': 35000, 'date': '2025-07-10', 'industry': 'consumer_lending'},
            ],
            'trades_list': [
                {'company': 'Bank of America', 'ticker': 'BAC', 'amount': {'min': 15001, 'max': 50000, 'display': '$15K-$50K'}, 'date': '2025-06-15', 'transaction_type': 'Purchase'},
            ],
            'legislation': [
                {'title': 'Consumer Protection in Financial Services Act', 'role': 'Sponsor', 'status': 'In Committee', 'date': '2025-04-12', 'relevance': 'consumer_lending'},
                {'title': 'CFPB Strengthening Act', 'role': 'Sponsor', 'status': 'In Committee', 'date': '2025-02-28', 'relevance': 'consumer_lending'},
            ],
            'recent_news': [
                {'headline': 'Waters Calls for Stronger Consumer Protections in Banking', 'source': 'American Banker', 'date': '2025-12-10', 'url': '#'},
                {'headline': 'Ranking Member Waters Questions Bank Merger Wave', 'source': 'Reuters', 'date': '2025-11-05', 'url': '#'},
            ],
        },
        'pelosi_nancy': {
            'id': 'pelosi_nancy',
            'name': 'Nancy Pelosi',
            'party': 'D',
            'state': 'CA',
            'district': '11',
            'chamber': 'house',
            'is_chair': False,
            'born': '1940-03-26',
            'first_elected': 1987,
            'years_in_congress': 38,
            'net_worth_estimate': {'min': 100000000, 'max': 250000000, 'display': '$100M-$250M'},
            'committees': [],
            'subcommittees': [],
            'leadership_roles': ['Former Speaker of the House'],
            'involvement_score': 91,
            'total_amount': 890000,
            'contributions': 240000,
            'stock_trades': 650000,
            'contributions_count': 28,
            'trades_count': 42,
            'top_industries': ['investment', 'fintech', 'crypto'],
            'involvement_by_industry': {
                'investment': {'contributions': 80000, 'stock_trades': 350000, 'total': 430000},
                'fintech': {'contributions': 60000, 'stock_trades': 180000, 'total': 240000},
                'crypto': {'contributions': 40000, 'stock_trades': 80000, 'total': 120000},
                'banking': {'contributions': 60000, 'stock_trades': 40000, 'total': 100000},
            },
            'firms': [
                {'name': 'NVIDIA', 'ticker': 'NVDA', 'total': 180000, 'type': 'trades'},
                {'name': 'Apple', 'ticker': 'AAPL', 'total': 120000, 'type': 'trades'},
                {'name': 'Microsoft', 'ticker': 'MSFT', 'total': 95000, 'type': 'trades'},
                {'name': 'Visa', 'ticker': 'V', 'total': 85000, 'type': 'mixed'},
                {'name': 'Tesla', 'ticker': 'TSLA', 'total': 75000, 'type': 'trades'},
                {'name': 'Alphabet', 'ticker': 'GOOGL', 'total': 65000, 'type': 'trades'},
            ],
            'contributions_list': [
                {'source': 'Goldman Sachs PAC', 'amount': 35000, 'date': '2025-09-10', 'industry': 'investment'},
                {'source': 'Visa PAC', 'amount': 30000, 'date': '2025-07-22', 'industry': 'fintech'},
            ],
            'trades_list': [
                {'company': 'NVIDIA', 'ticker': 'NVDA', 'amount': {'min': 250001, 'max': 500000, 'display': '$250K-$500K'}, 'date': '2025-12-02', 'transaction_type': 'Purchase'},
                {'company': 'Apple', 'ticker': 'AAPL', 'amount': {'min': 100001, 'max': 250000, 'display': '$100K-$250K'}, 'date': '2025-11-15', 'transaction_type': 'Purchase'},
                {'company': 'Microsoft', 'ticker': 'MSFT', 'amount': {'min': 50001, 'max': 100000, 'display': '$50K-$100K'}, 'date': '2025-10-28', 'transaction_type': 'Purchase'},
                {'company': 'Tesla', 'ticker': 'TSLA', 'amount': {'min': 50001, 'max': 100000, 'display': '$50K-$100K'}, 'date': '2025-09-08', 'transaction_type': 'Sale'},
            ],
            'legislation': [],
            'recent_news': [
                {'headline': 'Pelosi Stock Trades Continue to Draw Scrutiny', 'source': 'New York Times', 'date': '2025-12-18', 'url': '#'},
                {'headline': 'Former Speaker Discloses NVIDIA Options Purchase', 'source': 'CNBC', 'date': '2025-12-05', 'url': '#'},
                {'headline': 'Pelosi Among Members Calling for AI Regulation', 'source': 'Washington Post', 'date': '2025-11-20', 'url': '#'},
            ],
        },
    }

    # Get official data or return default
    official = officials_data.get(official_id)
    if not official:
        # Return generic data for unknown officials
        official = {
            'id': official_id,
            'name': official_id.replace('_', ' ').title(),
            'party': 'R',
            'state': 'TX',
            'chamber': 'house',
            'is_chair': False,
            'years_in_congress': 6,
            'net_worth_estimate': {'min': 1000000, 'max': 5000000, 'display': '$1M-$5M'},
            'committees': ['Financial Services'],
            'involvement_score': 65,
            'total_amount': 250000,
            'contributions': 200000,
            'stock_trades': 50000,
            'contributions_count': 15,
            'trades_count': 5,
            'involvement_by_industry': {
                'banking': {'contributions': 100000, 'stock_trades': 25000, 'total': 125000},
                'investment': {'contributions': 50000, 'stock_trades': 15000, 'total': 65000},
            },
            'firms': [
                {'name': 'Wells Fargo', 'ticker': 'WFC', 'total': 45000, 'type': 'contributions'},
                {'name': 'JPMorgan Chase', 'ticker': 'JPM', 'total': 35000, 'type': 'contributions'},
            ],
            'contributions_list': [],
            'trades_list': [],
            'legislation': [],
            'recent_news': [],
        }

    return jsonify({
        'success': True,
        'official': official
    })


def _build_industry_response(sector: str, sector_info: dict, data: dict):
    """Helper function to build industry API response with committees/legislation/news."""
    # Add committees data for each industry
    industry_committees = {
        'banking': [
            {'name': 'Financial Services', 'chamber': 'House', 'chair': 'J. French Hill (R-AR)', 'members': 71, 'industry_focus': 95},
            {'name': 'Banking, Housing, and Urban Affairs', 'chamber': 'Senate', 'chair': 'Tim Scott (R-SC)', 'members': 24, 'industry_focus': 90},
        ],
        'crypto': [
            {'name': 'Financial Services', 'chamber': 'House', 'chair': 'J. French Hill (R-AR)', 'members': 71, 'industry_focus': 85},
            {'name': 'Banking, Housing, and Urban Affairs', 'chamber': 'Senate', 'chair': 'Tim Scott (R-SC)', 'members': 24, 'industry_focus': 70},
        ],
        'investment': [
            {'name': 'Financial Services', 'chamber': 'House', 'chair': 'J. French Hill (R-AR)', 'members': 71, 'industry_focus': 90},
            {'name': 'Banking, Housing, and Urban Affairs', 'chamber': 'Senate', 'chair': 'Tim Scott (R-SC)', 'members': 24, 'industry_focus': 85},
        ],
        'mortgage': [
            {'name': 'Financial Services', 'chamber': 'House', 'chair': 'J. French Hill (R-AR)', 'members': 71, 'industry_focus': 80},
            {'name': 'Banking, Housing, and Urban Affairs', 'chamber': 'Senate', 'chair': 'Tim Scott (R-SC)', 'members': 24, 'industry_focus': 95},
        ],
        'fintech': [
            {'name': 'Financial Services', 'chamber': 'House', 'chair': 'J. French Hill (R-AR)', 'members': 71, 'industry_focus': 70},
        ],
        'insurance': [
            {'name': 'Financial Services', 'chamber': 'House', 'chair': 'J. French Hill (R-AR)', 'members': 71, 'industry_focus': 75},
        ],
    }

    # Add related legislation for each industry
    industry_legislation = {
        'banking': [
            {'bill_id': 'H.R. 1112', 'title': 'CFPB Accountability Act', 'sponsor': 'Rep. Andy Barr (R-KY)', 'status': 'In Committee', 'date': '2025-02-15'},
            {'bill_id': 'S. 234', 'title': 'Bank Merger Review Modernization Act', 'sponsor': 'Sen. Tim Scott (R-SC)', 'status': 'In Committee', 'date': '2025-03-01'},
        ],
        'crypto': [
            {'bill_id': 'H.R. 4763', 'title': 'FIT21 Act', 'sponsor': 'Rep. French Hill (R-AR)', 'status': 'Passed House', 'date': '2025-05-22'},
            {'bill_id': 'H.R. 5403', 'title': 'CBDC Anti-Surveillance Act', 'sponsor': 'Rep. Tom Emmer (R-MN)', 'status': 'Passed House', 'date': '2025-05-23'},
        ],
        'investment': [
            {'bill_id': 'H.R. 3456', 'title': 'Investor Protection Act', 'sponsor': 'Rep. Bill Huizenga (R-MI)', 'status': 'In Committee', 'date': '2025-06-01'},
        ],
        'mortgage': [
            {'bill_id': 'H.R. 2345', 'title': 'Housing Finance Reform Act', 'sponsor': 'Rep. French Hill (R-AR)', 'status': 'In Committee', 'date': '2025-03-20'},
        ],
    }

    # Add recent news for each industry
    industry_news = {
        'banking': [
            {'title': 'Fed Announces New Stress Test Requirements for Regional Banks', 'source': 'Wall Street Journal', 'date': '2026-01-08', 'url': '#'},
            {'title': 'House Financial Services Advances CFPB Reform Bill', 'source': 'American Banker', 'date': '2026-01-05', 'url': '#'},
        ],
        'crypto': [
            {'title': 'FIT21 Implementation Guidelines Expected Q1 2026', 'source': 'CoinDesk', 'date': '2026-01-09', 'url': '#'},
            {'title': 'Coinbase PAC Contributions Surge Ahead of Regulatory Votes', 'source': 'The Block', 'date': '2026-01-06', 'url': '#'},
        ],
        'investment': [
            {'title': 'SEC Announces New ESG Disclosure Rules', 'source': 'Bloomberg', 'date': '2026-01-07', 'url': '#'},
        ],
        'mortgage': [
            {'title': 'FHFA Announces New Capital Requirements for GSEs', 'source': 'Housing Wire', 'date': '2026-01-05', 'url': '#'},
        ],
    }

    return jsonify({
        'success': True,
        'sector': sector,
        'sector_info': sector_info,
        'officials': data['officials'],
        'firms': data['firms'],
        'party_split': data['party_split'],
        'total_amount': data['total_amount'],
        'total_contributions': data['total_contributions'],
        'total_trades': data['total_trades'],
        'committees': industry_committees.get(sector, []),
        'legislation': industry_legislation.get(sector, []),
        'news': industry_news.get(sector, []),
    })


@app.route('/api/industry/<sector>', methods=['GET'])
def api_get_industry(sector: str):
    """Get officials involved in a specific industry sector."""
    from justdata.apps.electwatch.services.firm_mapper import get_sector_info
    sector_info = get_sector_info(sector)
    if not sector_info:
        return jsonify({'error': f'Unknown sector: {sector}'}), 404

    # Try to get data from weekly data store first
    try:
        from justdata.apps.electwatch.services.data_store import get_officials, get_industry
        all_officials = get_officials()

        if all_officials:
            # Build officials list for this sector from their involvement_by_industry
            sector_officials = []
            sector_firms = {}
            total_amount = 0
            total_contributions = 0
            total_trades = 0
            party_counts = {'r': 0, 'd': 0}

            for official in all_officials:
                involvement = official.get('involvement_by_industry', {})
                if sector in involvement:
                    industry_data = involvement[sector]
                    official_total = industry_data.get('total', 0)
                    if official_total > 0:
                        sector_officials.append({
                            'id': official.get('id', ''),
                            'name': official.get('name', ''),
                            'party': official.get('party', ''),
                            'state': official.get('state', ''),
                            'chamber': official.get('chamber', 'house'),
                            'total': official_total,
                            'photo_url': official.get('photo_url'),
                        })
                        total_amount += official_total
                        total_contributions += industry_data.get('contributions', 0)
                        total_trades += industry_data.get('stock_trades', 0)

                        # Count by party
                        party = official.get('party', '').upper()
                        if party == 'R':
                            party_counts['r'] += 1
                        elif party == 'D':
                            party_counts['d'] += 1

                        # Aggregate firms for this sector
                        for firm in official.get('firms', []):
                            ticker = firm.get('ticker', '')
                            if ticker:
                                if ticker not in sector_firms:
                                    sector_firms[ticker] = {
                                        'name': firm.get('name', ticker),
                                        'ticker': ticker,
                                        'total': 0,
                                        'officials_count': 0
                                    }
                                sector_firms[ticker]['total'] += firm.get('total', 0)
                                sector_firms[ticker]['officials_count'] += 1

            # Sort officials by total amount
            sector_officials.sort(key=lambda x: x['total'], reverse=True)

            # Sort firms by total amount
            firms_list = sorted(sector_firms.values(), key=lambda x: x['total'], reverse=True)[:10]

            # Calculate party split percentage
            total_party = party_counts['r'] + party_counts['d']
            if total_party > 0:
                party_split = {
                    'r': round(party_counts['r'] / total_party * 100),
                    'd': round(party_counts['d'] / total_party * 100)
                }
            else:
                party_split = {'r': 50, 'd': 50}

            if sector_officials:
                # Use real data
                data = {
                    'officials': sector_officials[:20],
                    'firms': firms_list,
                    'party_split': party_split,
                    'total_amount': total_amount,
                    'total_contributions': total_contributions,
                    'total_trades': total_trades,
                }
                sector_info['data_source'] = 'weekly_update'

                # Skip to return (will be handled below)
                return _build_industry_response(sector, sector_info, data)

    except Exception as e:
        logger.warning(f"Could not load industry data from store: {e}")

    # Try to get live data
    try:
        from justdata.apps.electwatch.services.data_aggregator import get_data_aggregator
        aggregator = get_data_aggregator()
        live_data = aggregator.get_industry_detail(sector)

        if live_data and live_data.get('news'):
            # Format news
            news = []
            for article in live_data.get('news', [])[:10]:
                news.append({
                    'title': article.get('headline', article.get('title', '')),
                    'source': article.get('source', ''),
                    'date': article.get('datetime', article.get('date', ''))[:10] if article.get('datetime') or article.get('date') else '',
                    'url': article.get('url', '#')
                })

            # Add news to sector info if we have live data
            sector_info['news'] = news
            sector_info['data_source'] = 'live'
    except Exception as e:
        logger.warning(f"Could not fetch live industry data: {e}")

    # Sample data for each industry
    sample_data = {
        'banking': {
            'officials': [
                {'id': 'hill_j_french', 'name': 'J. French Hill', 'party': 'R', 'state': 'AR', 'chamber': 'house', 'total': 425000},
                {'id': 'waters_maxine', 'name': 'Maxine Waters', 'party': 'D', 'state': 'CA', 'chamber': 'house', 'total': 380000},
                {'id': 'scott_tim', 'name': 'Tim Scott', 'party': 'R', 'state': 'SC', 'chamber': 'senate', 'total': 320000},
                {'id': 'warren_elizabeth', 'name': 'Elizabeth Warren', 'party': 'D', 'state': 'MA', 'chamber': 'senate', 'total': 95000},
            ],
            'firms': [
                {'name': 'Wells Fargo', 'ticker': 'WFC', 'total': 850000, 'officials_count': 45},
                {'name': 'JPMorgan Chase', 'ticker': 'JPM', 'total': 780000, 'officials_count': 42},
                {'name': 'Bank of America', 'ticker': 'BAC', 'total': 620000, 'officials_count': 38},
                {'name': 'Citigroup', 'ticker': 'C', 'total': 540000, 'officials_count': 35},
            ],
            'party_split': {'r': 62, 'd': 38},
            'total_amount': 4200000,
            'total_contributions': 3100000,
            'total_trades': 1100000,
        },
        'crypto': {
            'officials': [
                {'id': 'hill_j_french', 'name': 'J. French Hill', 'party': 'R', 'state': 'AR', 'chamber': 'house', 'total': 180000},
                {'id': 'emmer_tom', 'name': 'Tom Emmer', 'party': 'R', 'state': 'MN', 'chamber': 'house', 'total': 145000},
                {'id': 'lummis_cynthia', 'name': 'Cynthia Lummis', 'party': 'R', 'state': 'WY', 'chamber': 'senate', 'total': 120000},
                {'id': 'torres_ritchie', 'name': 'Ritchie Torres', 'party': 'D', 'state': 'NY', 'chamber': 'house', 'total': 95000},
            ],
            'firms': [
                {'name': 'Coinbase', 'ticker': 'COIN', 'total': 450000, 'officials_count': 23},
                {'name': 'Robinhood', 'ticker': 'HOOD', 'total': 280000, 'officials_count': 18},
                {'name': 'Block (Square)', 'ticker': 'SQ', 'total': 150000, 'officials_count': 12},
            ],
            'party_split': {'r': 71, 'd': 29},
            'total_amount': 1500000,
            'total_contributions': 900000,
            'total_trades': 600000,
        },
    }

    # Get sample data for this sector or use defaults
    data = sample_data.get(sector, {
        'officials': [
            {'id': 'hill_j_french', 'name': 'J. French Hill', 'party': 'R', 'state': 'AR', 'chamber': 'house', 'total': 150000},
            {'id': 'waters_maxine', 'name': 'Maxine Waters', 'party': 'D', 'state': 'CA', 'chamber': 'house', 'total': 120000},
        ],
        'firms': [
            {'name': 'Sample Firm', 'ticker': 'SMPL', 'total': 200000, 'officials_count': 15},
        ],
        'party_split': {'r': 55, 'd': 45},
        'total_amount': sector_info.get('sample_total', 1000000),
        'total_contributions': int(sector_info.get('sample_total', 1000000) * 0.7),
        'total_trades': int(sector_info.get('sample_total', 1000000) * 0.3),
    })

    # Add committees data for each industry
    industry_committees = {
        'banking': [
            {'name': 'Financial Services', 'chamber': 'House', 'chair': 'J. French Hill (R-AR)', 'members': 71, 'industry_focus': 95},
            {'name': 'Banking, Housing, and Urban Affairs', 'chamber': 'Senate', 'chair': 'Tim Scott (R-SC)', 'members': 24, 'industry_focus': 90},
            {'name': 'Ways and Means', 'chamber': 'House', 'chair': 'Jason Smith (R-MO)', 'members': 43, 'industry_focus': 45},
        ],
        'crypto': [
            {'name': 'Financial Services', 'chamber': 'House', 'chair': 'J. French Hill (R-AR)', 'members': 71, 'industry_focus': 85},
            {'name': 'Agriculture', 'chamber': 'House', 'chair': 'Glenn Thompson (R-PA)', 'members': 51, 'industry_focus': 40},
            {'name': 'Banking, Housing, and Urban Affairs', 'chamber': 'Senate', 'chair': 'Tim Scott (R-SC)', 'members': 24, 'industry_focus': 70},
        ],
        'investment': [
            {'name': 'Financial Services', 'chamber': 'House', 'chair': 'J. French Hill (R-AR)', 'members': 71, 'industry_focus': 90},
            {'name': 'Banking, Housing, and Urban Affairs', 'chamber': 'Senate', 'chair': 'Tim Scott (R-SC)', 'members': 24, 'industry_focus': 85},
            {'name': 'Ways and Means', 'chamber': 'House', 'chair': 'Jason Smith (R-MO)', 'members': 43, 'industry_focus': 60},
        ],
        'mortgage': [
            {'name': 'Financial Services', 'chamber': 'House', 'chair': 'J. French Hill (R-AR)', 'members': 71, 'industry_focus': 80},
            {'name': 'Banking, Housing, and Urban Affairs', 'chamber': 'Senate', 'chair': 'Tim Scott (R-SC)', 'members': 24, 'industry_focus': 95},
        ],
        'consumer_lending': [
            {'name': 'Financial Services', 'chamber': 'House', 'chair': 'J. French Hill (R-AR)', 'members': 71, 'industry_focus': 85},
            {'name': 'Banking, Housing, and Urban Affairs', 'chamber': 'Senate', 'chair': 'Tim Scott (R-SC)', 'members': 24, 'industry_focus': 80},
        ],
        'insurance': [
            {'name': 'Financial Services', 'chamber': 'House', 'chair': 'J. French Hill (R-AR)', 'members': 71, 'industry_focus': 75},
            {'name': 'Banking, Housing, and Urban Affairs', 'chamber': 'Senate', 'chair': 'Tim Scott (R-SC)', 'members': 24, 'industry_focus': 60},
        ],
        'fintech': [
            {'name': 'Financial Services', 'chamber': 'House', 'chair': 'J. French Hill (R-AR)', 'members': 71, 'industry_focus': 70},
            {'name': 'Small Business', 'chamber': 'House', 'chair': 'Roger Williams (R-TX)', 'members': 27, 'industry_focus': 45},
        ],
    }

    # Add related legislation for each industry
    industry_legislation = {
        'banking': [
            {'bill_id': 'H.R. 1112', 'title': 'CFPB Accountability Act', 'sponsor': 'Rep. Andy Barr (R-KY)', 'status': 'In Committee', 'date': '2025-02-15'},
            {'bill_id': 'S. 234', 'title': 'Bank Merger Review Modernization Act', 'sponsor': 'Sen. Tim Scott (R-SC)', 'status': 'In Committee', 'date': '2025-03-01'},
            {'bill_id': 'H.R. 2890', 'title': 'Community Bank Relief Act', 'sponsor': 'Rep. Blaine Luetkemeyer (R-MO)', 'status': 'Passed House', 'date': '2025-04-10'},
        ],
        'crypto': [
            {'bill_id': 'H.R. 4763', 'title': 'FIT21 Act', 'sponsor': 'Rep. French Hill (R-AR)', 'status': 'Passed House', 'date': '2025-05-22'},
            {'bill_id': 'H.R. 5403', 'title': 'CBDC Anti-Surveillance Act', 'sponsor': 'Rep. Tom Emmer (R-MN)', 'status': 'Passed House', 'date': '2025-05-23'},
            {'bill_id': 'H.R. 4766', 'title': 'Clarity for Payment Stablecoins Act', 'sponsor': 'Rep. Patrick McHenry (R-NC)', 'status': 'In Committee', 'date': '2025-07-15'},
            {'bill_id': 'S. 1582', 'title': 'Lummis-Gillibrand Responsible Financial Innovation Act', 'sponsor': 'Sen. Cynthia Lummis (R-WY)', 'status': 'In Committee', 'date': '2025-05-10'},
        ],
        'investment': [
            {'bill_id': 'H.R. 3456', 'title': 'Investor Protection and Capital Markets Fairness Act', 'sponsor': 'Rep. Bill Huizenga (R-MI)', 'status': 'In Committee', 'date': '2025-06-01'},
            {'bill_id': 'S. 789', 'title': 'SEC Regulatory Accountability Act', 'sponsor': 'Sen. Bill Hagerty (R-TN)', 'status': 'In Committee', 'date': '2025-04-15'},
        ],
        'mortgage': [
            {'bill_id': 'H.R. 2345', 'title': 'Housing Finance Reform Act', 'sponsor': 'Rep. French Hill (R-AR)', 'status': 'In Committee', 'date': '2025-03-20'},
            {'bill_id': 'S. 567', 'title': 'GSE Reform Act', 'sponsor': 'Sen. Tim Scott (R-SC)', 'status': 'In Committee', 'date': '2025-02-28'},
        ],
        'consumer_lending': [
            {'bill_id': 'H.R. 1112', 'title': 'CFPB Accountability Act', 'sponsor': 'Rep. Andy Barr (R-KY)', 'status': 'In Committee', 'date': '2025-02-15'},
            {'bill_id': 'H.R. 4567', 'title': 'Fair Credit Reporting Modernization Act', 'sponsor': 'Rep. Barry Loudermilk (R-GA)', 'status': 'In Committee', 'date': '2025-08-01'},
        ],
        'insurance': [
            {'bill_id': 'H.R. 5678', 'title': 'Federal Insurance Office Modernization Act', 'sponsor': 'Rep. Sean Casten (D-IL)', 'status': 'In Committee', 'date': '2025-09-10'},
        ],
        'fintech': [
            {'bill_id': 'H.R. 4763', 'title': 'FIT21 Act', 'sponsor': 'Rep. French Hill (R-AR)', 'status': 'Passed House', 'date': '2025-05-22'},
            {'bill_id': 'H.R. 6789', 'title': 'Payment Systems Modernization Act', 'sponsor': 'Rep. Stephen Lynch (D-MA)', 'status': 'In Committee', 'date': '2025-10-05'},
        ],
    }

    # Add recent news for each industry
    industry_news = {
        'banking': [
            {'title': 'Fed Announces New Stress Test Requirements for Regional Banks', 'source': 'Wall Street Journal', 'date': '2026-01-08', 'url': '#'},
            {'title': 'House Financial Services Advances CFPB Reform Bill', 'source': 'American Banker', 'date': '2026-01-05', 'url': '#'},
            {'title': 'Bank Lobbyists Increase Spending Amid Regulatory Uncertainty', 'source': 'Politico', 'date': '2025-12-28', 'url': '#'},
        ],
        'crypto': [
            {'title': 'FIT21 Implementation Guidelines Expected Q1 2026', 'source': 'CoinDesk', 'date': '2026-01-09', 'url': '#'},
            {'title': 'Coinbase PAC Contributions Surge Ahead of Regulatory Votes', 'source': 'The Block', 'date': '2026-01-06', 'url': '#'},
            {'title': 'Senate Banking Committee Schedules Crypto Hearing', 'source': 'Bloomberg', 'date': '2026-01-03', 'url': '#'},
            {'title': 'Stablecoin Bill Gains Bipartisan Support in House', 'source': 'Reuters', 'date': '2025-12-20', 'url': '#'},
        ],
        'investment': [
            {'title': 'SEC Proposes New Rules for Private Fund Advisers', 'source': 'Financial Times', 'date': '2026-01-07', 'url': '#'},
            {'title': 'Asset Managers Lobby Against ESG Disclosure Requirements', 'source': 'Bloomberg', 'date': '2025-12-30', 'url': '#'},
        ],
        'mortgage': [
            {'title': 'FHFA Announces New Capital Requirements for GSEs', 'source': 'Housing Wire', 'date': '2026-01-05', 'url': '#'},
            {'title': 'Mortgage Lenders Push for Regulatory Relief', 'source': 'National Mortgage News', 'date': '2025-12-22', 'url': '#'},
        ],
        'consumer_lending': [
            {'title': 'CFPB Rule on Credit Card Late Fees Faces Legal Challenge', 'source': 'American Banker', 'date': '2026-01-04', 'url': '#'},
            {'title': 'Consumer Groups Urge Stronger BNPL Protections', 'source': 'Consumer Finance Monitor', 'date': '2025-12-18', 'url': '#'},
        ],
        'insurance': [
            {'title': 'State Insurance Regulators Push Back on Federal Oversight', 'source': 'Insurance Journal', 'date': '2026-01-02', 'url': '#'},
        ],
        'fintech': [
            {'title': 'Payment Processors Face New AML Requirements', 'source': 'Payments Dive', 'date': '2026-01-06', 'url': '#'},
            {'title': 'Neobanks Seek Banking Charter Clarity', 'source': 'Fintech Futures', 'date': '2025-12-15', 'url': '#'},
        ],
    }

    return _build_industry_response(sector, sector_info, data)


@app.route('/api/committee/<committee_id>', methods=['GET'])
def api_get_committee(committee_id: str):
    """
    Get detailed information for a specific committee.

    Includes:
        - Committee info (name, chamber, jurisdiction)
        - Members with financial involvement data
        - Recent votes
        - Legislation from committee
        - News
    """
    # Committee data mapping
    committees = {
        'house-financial-services': {
            'id': 'house-financial-services',
            'name': 'Financial Services',
            'full_name': 'House Committee on Financial Services',
            'chamber': 'House',
            'chair': {'name': 'J. French Hill', 'party': 'R', 'state': 'AR', 'id': 'hill_j_french'},
            'ranking_member': {'name': 'Maxine Waters', 'party': 'D', 'state': 'CA', 'id': 'waters_maxine'},
            'jurisdiction': 'Banking, insurance, securities, housing, urban development, international finance',
            'members_count': 71,
            'subcommittees': [
                'Capital Markets',
                'Digital Assets, Financial Technology and Inclusion',
                'Financial Institutions and Monetary Policy',
                'Housing and Insurance',
                'National Security, Illicit Finance, and International Financial Institutions',
                'Oversight and Investigations'
            ],
            'total_contributions': 8500000,
            'total_stock_trades': 2100000,
            'party_split': {'r': 38, 'd': 33},
        },
        'senate-banking': {
            'id': 'senate-banking',
            'name': 'Banking, Housing, and Urban Affairs',
            'full_name': 'Senate Committee on Banking, Housing, and Urban Affairs',
            'chamber': 'Senate',
            'chair': {'name': 'Tim Scott', 'party': 'R', 'state': 'SC', 'id': 'scott_tim'},
            'ranking_member': {'name': 'Elizabeth Warren', 'party': 'D', 'state': 'MA', 'id': 'warren_elizabeth'},
            'jurisdiction': 'Banks, financial institutions, money and credit, urban housing, mass transit',
            'members_count': 24,
            'subcommittees': [
                'Economic Policy',
                'Financial Institutions and Consumer Protection',
                'Housing, Transportation, and Community Development',
                'National Security and International Trade and Finance',
                'Securities, Insurance, and Investment'
            ],
            'total_contributions': 5200000,
            'total_stock_trades': 1400000,
            'party_split': {'r': 13, 'd': 11},
        },
        'house-ways-means': {
            'id': 'house-ways-means',
            'name': 'Ways and Means',
            'full_name': 'House Committee on Ways and Means',
            'chamber': 'House',
            'chair': {'name': 'Jason Smith', 'party': 'R', 'state': 'MO', 'id': 'smith_jason'},
            'ranking_member': {'name': 'Richard Neal', 'party': 'D', 'state': 'MA', 'id': 'neal_richard'},
            'jurisdiction': 'Taxation, tariffs, Social Security, Medicare',
            'members_count': 43,
            'subcommittees': [
                'Health',
                'Oversight',
                'Select Revenue Measures',
                'Social Security',
                'Tax Policy',
                'Trade',
                'Work and Welfare'
            ],
            'total_contributions': 6800000,
            'total_stock_trades': 1800000,
            'party_split': {'r': 25, 'd': 18},
        },
        'house-budget': {
            'id': 'house-budget',
            'name': 'Budget',
            'full_name': 'House Committee on the Budget',
            'chamber': 'House',
            'chair': {'name': 'Jodey Arrington', 'party': 'R', 'state': 'TX', 'id': 'arrington_jodey'},
            'ranking_member': {'name': 'Brendan Boyle', 'party': 'D', 'state': 'PA', 'id': 'boyle_brendan'},
            'jurisdiction': 'Federal budget process, budget resolution',
            'members_count': 36,
            'subcommittees': [],
            'total_contributions': 3200000,
            'total_stock_trades': 950000,
            'party_split': {'r': 22, 'd': 14},
        },
        'senate-finance': {
            'id': 'senate-finance',
            'name': 'Finance',
            'full_name': 'Senate Committee on Finance',
            'chamber': 'Senate',
            'chair': {'name': 'Mike Crapo', 'party': 'R', 'state': 'ID', 'id': 'crapo_mike'},
            'ranking_member': {'name': 'Ron Wyden', 'party': 'D', 'state': 'OR', 'id': 'wyden_ron'},
            'jurisdiction': 'Taxation, trade, health programs, Social Security',
            'members_count': 28,
            'subcommittees': [
                'Energy, Natural Resources, and Infrastructure',
                'Fiscal Responsibility and Economic Growth',
                'Health Care',
                'International Trade, Customs, and Global Competitiveness',
                'Social Security, Pensions, and Family Policy',
                'Taxation and IRS Oversight'
            ],
            'total_contributions': 7100000,
            'total_stock_trades': 2200000,
            'party_split': {'r': 15, 'd': 13},
        },
    }

    # Normalize committee_id
    normalized_id = committee_id.lower().replace(' ', '-').replace('_', '-')

    # Find committee
    committee = committees.get(normalized_id)
    if not committee:
        # Try partial match
        for key, data in committees.items():
            if normalized_id in key or key in normalized_id:
                committee = data
                break

    if not committee:
        return jsonify({'error': f'Committee not found: {committee_id}'}), 404

    # Master list of all committee members (used to ensure everyone is shown)
    # These will be enriched with financial data from the data store
    all_committee_members = {
        'house-financial-services': [
            {'name': 'French Hill', 'party': 'R', 'state': 'AR', 'role': 'Chair'},
            {'name': 'Maxine Waters', 'party': 'D', 'state': 'CA', 'role': 'Ranking Member'},
            {'name': 'Andy Barr', 'party': 'R', 'state': 'KY', 'role': 'Vice Chair'},
            {'name': 'Bill Huizenga', 'party': 'R', 'state': 'MI', 'role': 'Member'},
            {'name': 'Ann Wagner', 'party': 'R', 'state': 'MO', 'role': 'Member'},
            {'name': 'Frank Lucas', 'party': 'R', 'state': 'OK', 'role': 'Member'},
            {'name': 'Pete Sessions', 'party': 'R', 'state': 'TX', 'role': 'Member'},
            {'name': 'Bill Posey', 'party': 'R', 'state': 'FL', 'role': 'Member'},
            {'name': 'Blaine Luetkemeyer', 'party': 'R', 'state': 'MO', 'role': 'Member'},
            {'name': 'Tom Emmer', 'party': 'R', 'state': 'MN', 'role': 'Member'},
            {'name': 'Ralph Norman', 'party': 'R', 'state': 'SC', 'role': 'Member'},
            {'name': 'Dan Meuser', 'party': 'R', 'state': 'PA', 'role': 'Member'},
            {'name': 'John Rose', 'party': 'R', 'state': 'TN', 'role': 'Member'},
            {'name': 'Bryan Steil', 'party': 'R', 'state': 'WI', 'role': 'Member'},
            {'name': 'Mike Lawler', 'party': 'R', 'state': 'NY', 'role': 'Member'},
            {'name': 'Zach Nunn', 'party': 'R', 'state': 'IA', 'role': 'Member'},
            {'name': 'Monica De La Cruz', 'party': 'R', 'state': 'TX', 'role': 'Member'},
            {'name': 'Erin Houchin', 'party': 'R', 'state': 'IN', 'role': 'Member'},
            {'name': 'Andy Ogles', 'party': 'R', 'state': 'TN', 'role': 'Member'},
            {'name': 'Mike Flood', 'party': 'R', 'state': 'NE', 'role': 'Member'},
            {'name': 'Brad Sherman', 'party': 'D', 'state': 'CA', 'role': 'Member'},
            {'name': 'Gregory Meeks', 'party': 'D', 'state': 'NY', 'role': 'Member'},
            {'name': 'David Scott', 'party': 'D', 'state': 'GA', 'role': 'Member'},
            {'name': 'Nydia Velazquez', 'party': 'D', 'state': 'NY', 'role': 'Member'},
            {'name': 'Al Green', 'party': 'D', 'state': 'TX', 'role': 'Member'},
            {'name': 'Emanuel Cleaver', 'party': 'D', 'state': 'MO', 'role': 'Member'},
            {'name': 'Jim Himes', 'party': 'D', 'state': 'CT', 'role': 'Member'},
            {'name': 'Bill Foster', 'party': 'D', 'state': 'IL', 'role': 'Member'},
            {'name': 'Joyce Beatty', 'party': 'D', 'state': 'OH', 'role': 'Member'},
            {'name': 'Juan Vargas', 'party': 'D', 'state': 'CA', 'role': 'Member'},
            {'name': 'Sean Casten', 'party': 'D', 'state': 'IL', 'role': 'Member'},
            {'name': 'Ayanna Pressley', 'party': 'D', 'state': 'MA', 'role': 'Member'},
            {'name': 'Ritchie Torres', 'party': 'D', 'state': 'NY', 'role': 'Member'},
            {'name': 'Sylvia Garcia', 'party': 'D', 'state': 'TX', 'role': 'Member'},
            {'name': 'Nikema Williams', 'party': 'D', 'state': 'GA', 'role': 'Member'},
        ],
        'senate-banking': [
            {'name': 'Tim Scott', 'party': 'R', 'state': 'SC', 'role': 'Chair'},
            {'name': 'Elizabeth Warren', 'party': 'D', 'state': 'MA', 'role': 'Ranking Member'},
            {'name': 'Mike Crapo', 'party': 'R', 'state': 'ID', 'role': 'Member'},
            {'name': 'Mike Rounds', 'party': 'R', 'state': 'SD', 'role': 'Member'},
            {'name': 'Thom Tillis', 'party': 'R', 'state': 'NC', 'role': 'Member'},
            {'name': 'John Kennedy', 'party': 'R', 'state': 'LA', 'role': 'Member'},
            {'name': 'Bill Hagerty', 'party': 'R', 'state': 'TN', 'role': 'Member'},
            {'name': 'Cynthia Lummis', 'party': 'R', 'state': 'WY', 'role': 'Member'},
            {'name': 'Kevin Cramer', 'party': 'R', 'state': 'ND', 'role': 'Member'},
            {'name': 'Katie Britt', 'party': 'R', 'state': 'AL', 'role': 'Member'},
            {'name': 'Dave McCormick', 'party': 'R', 'state': 'PA', 'role': 'Member'},
            {'name': 'Bernie Moreno', 'party': 'R', 'state': 'OH', 'role': 'Member'},
            {'name': 'Ruben Gallego', 'party': 'D', 'state': 'AZ', 'role': 'Member'},
            {'name': 'Jack Reed', 'party': 'D', 'state': 'RI', 'role': 'Member'},
            {'name': 'Mark Warner', 'party': 'D', 'state': 'VA', 'role': 'Member'},
            {'name': 'Chris Van Hollen', 'party': 'D', 'state': 'MD', 'role': 'Member'},
            {'name': 'Catherine Cortez Masto', 'party': 'D', 'state': 'NV', 'role': 'Member'},
            {'name': 'Tina Smith', 'party': 'D', 'state': 'MN', 'role': 'Member'},
            {'name': 'Raphael Warnock', 'party': 'D', 'state': 'GA', 'role': 'Member'},
            {'name': 'John Fetterman', 'party': 'D', 'state': 'PA', 'role': 'Member'},
            {'name': 'Andy Kim', 'party': 'D', 'state': 'NJ', 'role': 'Member'},
        ],
        'senate-finance': [
            {'name': 'Mike Crapo', 'party': 'R', 'state': 'ID', 'role': 'Chair'},
            {'name': 'Ron Wyden', 'party': 'D', 'state': 'OR', 'role': 'Ranking Member'},
            {'name': 'Chuck Grassley', 'party': 'R', 'state': 'IA', 'role': 'Member'},
            {'name': 'John Cornyn', 'party': 'R', 'state': 'TX', 'role': 'Member'},
            {'name': 'John Thune', 'party': 'R', 'state': 'SD', 'role': 'Member'},
            {'name': 'Tim Scott', 'party': 'R', 'state': 'SC', 'role': 'Member'},
            {'name': 'Bill Cassidy', 'party': 'R', 'state': 'LA', 'role': 'Member'},
            {'name': 'James Lankford', 'party': 'R', 'state': 'OK', 'role': 'Member'},
            {'name': 'Steve Daines', 'party': 'R', 'state': 'MT', 'role': 'Member'},
            {'name': 'Todd Young', 'party': 'R', 'state': 'IN', 'role': 'Member'},
            {'name': 'John Barrasso', 'party': 'R', 'state': 'WY', 'role': 'Member'},
            {'name': 'Marsha Blackburn', 'party': 'R', 'state': 'TN', 'role': 'Member'},
            {'name': 'Debbie Stabenow', 'party': 'D', 'state': 'MI', 'role': 'Member'},
            {'name': 'Maria Cantwell', 'party': 'D', 'state': 'WA', 'role': 'Member'},
            {'name': 'Bob Menendez', 'party': 'D', 'state': 'NJ', 'role': 'Member'},
            {'name': 'Tom Carper', 'party': 'D', 'state': 'DE', 'role': 'Member'},
            {'name': 'Ben Cardin', 'party': 'D', 'state': 'MD', 'role': 'Member'},
            {'name': 'Sheldon Whitehouse', 'party': 'D', 'state': 'RI', 'role': 'Member'},
            {'name': 'Michael Bennet', 'party': 'D', 'state': 'CO', 'role': 'Member'},
            {'name': 'Bob Casey', 'party': 'D', 'state': 'PA', 'role': 'Member'},
            {'name': 'Mark Warner', 'party': 'D', 'state': 'VA', 'role': 'Member'},
        ],
    }

    # Try to get financial data from data store and merge with master list
    real_members = []
    try:
        from justdata.apps.electwatch.services.data_store import get_officials
        all_officials = get_officials()

        # Create lookup by name for quick matching
        officials_by_name = {}
        for official in all_officials:
            name = official.get('name', '')
            officials_by_name[name.lower()] = official
            # Also add without middle names/initials
            parts = name.split()
            if len(parts) > 2:
                short_name = f"{parts[0]} {parts[-1]}"
                officials_by_name[short_name.lower()] = official

        # Get the master list for this committee, or fall back to data store matching
        master_list = all_committee_members.get(committee['id'], [])

        if master_list:
            # Use master list and enrich with financial data
            for member in master_list:
                name = member['name']
                # Try to find matching official in data store
                official = officials_by_name.get(name.lower())

                real_members.append({
                    'id': official.get('id', name.lower().replace(' ', '_').replace('.', '')) if official else name.lower().replace(' ', '_').replace('.', ''),
                    'name': name,
                    'party': member['party'],
                    'state': member['state'],
                    'role': member['role'],
                    'contributions': official.get('contributions', 0) if official else 0,
                    'financial_sector_pac': official.get('financial_sector_pac', 0) if official else 0,
                    'stock_trades': official.get('stock_trades_max', 0) if official else 0,
                    'photo_url': official.get('photo_url') if official else None,
                })
        else:
            # Fall back to finding members from data store by committee assignment
            committee_name = committee.get('name', '')
            for official in all_officials:
                official_committees = official.get('committees', [])
                for comm in official_committees:
                    if committee_name.lower() in comm.lower() or comm.lower() in committee_name.lower():
                        role = 'Member'
                        if '(Chair)' in comm or '(Vice Chair)' in comm:
                            role = 'Chair' if '(Vice Chair)' not in comm else 'Vice Chair'
                        elif '(Ranking)' in comm:
                            role = 'Ranking Member'

                        real_members.append({
                            'id': official.get('id', ''),
                            'name': official.get('name', ''),
                            'party': official.get('party', ''),
                            'state': official.get('state', ''),
                            'role': role,
                            'contributions': official.get('contributions', 0),
                            'financial_sector_pac': official.get('financial_sector_pac', 0),
                            'stock_trades': official.get('stock_trades_max', 0),
                            'photo_url': official.get('photo_url'),
                        })
                        break

        # Sort by role (Chair/Ranking first), then by party, then by name
        role_order = {'Chair': 0, 'Vice Chair': 1, 'Ranking Member': 2, 'Member': 3}
        real_members.sort(key=lambda x: (role_order.get(x.get('role', 'Member'), 3), x.get('party', 'R') == 'D', x.get('name', '')))

    except Exception as e:
        logger.warning(f"Could not load committee members from store: {e}")

    # Sample members for the committee (fallback)
    sample_members = {
        'house-financial-services': [
            {'id': 'hill_j_french', 'name': 'J. French Hill', 'party': 'R', 'state': 'AR', 'role': 'Chair', 'contributions': 425000, 'stock_trades': 75000, 'score': 92},
            {'id': 'waters_maxine', 'name': 'Maxine Waters', 'party': 'D', 'state': 'CA', 'role': 'Ranking Member', 'contributions': 380000, 'stock_trades': 0, 'score': 78},
            {'id': 'mchenry_patrick', 'name': 'Patrick McHenry', 'party': 'R', 'state': 'NC', 'role': 'Member', 'contributions': 320000, 'stock_trades': 45000, 'score': 85},
            {'id': 'huizenga_bill', 'name': 'Bill Huizenga', 'party': 'R', 'state': 'MI', 'role': 'Member', 'contributions': 285000, 'stock_trades': 55000, 'score': 81},
            {'id': 'green_al', 'name': 'Al Green', 'party': 'D', 'state': 'TX', 'role': 'Member', 'contributions': 195000, 'stock_trades': 0, 'score': 62},
            {'id': 'barr_andy', 'name': 'Andy Barr', 'party': 'R', 'state': 'KY', 'role': 'Member', 'contributions': 275000, 'stock_trades': 35000, 'score': 79},
            {'id': 'sherman_brad', 'name': 'Brad Sherman', 'party': 'D', 'state': 'CA', 'role': 'Member', 'contributions': 210000, 'stock_trades': 85000, 'score': 74},
            {'id': 'emmer_tom', 'name': 'Tom Emmer', 'party': 'R', 'state': 'MN', 'role': 'Member', 'contributions': 245000, 'stock_trades': 120000, 'score': 82},
        ],
        'senate-banking': [
            {'id': 'scott_tim', 'name': 'Tim Scott', 'party': 'R', 'state': 'SC', 'role': 'Chair', 'contributions': 520000, 'stock_trades': 85000, 'score': 88},
            {'id': 'warren_elizabeth', 'name': 'Elizabeth Warren', 'party': 'D', 'state': 'MA', 'role': 'Ranking Member', 'contributions': 95000, 'stock_trades': 0, 'score': 45},
            {'id': 'rounds_mike', 'name': 'Mike Rounds', 'party': 'R', 'state': 'SD', 'role': 'Member', 'contributions': 180000, 'stock_trades': 45000, 'score': 68},
            {'id': 'lummis_cynthia', 'name': 'Cynthia Lummis', 'party': 'R', 'state': 'WY', 'role': 'Member', 'contributions': 145000, 'stock_trades': 250000, 'score': 85},
            {'id': 'brown_sherrod', 'name': 'Sherrod Brown', 'party': 'D', 'state': 'OH', 'role': 'Member', 'contributions': 165000, 'stock_trades': 0, 'score': 52},
            {'id': 'hagerty_bill', 'name': 'Bill Hagerty', 'party': 'R', 'state': 'TN', 'role': 'Member', 'contributions': 225000, 'stock_trades': 180000, 'score': 79},
        ],
    }

    # Get members - use real members if available, otherwise fallback to sample
    if real_members:
        members = real_members
    else:
        members = sample_members.get(committee['id'], [
            {'id': 'hill_j_french', 'name': 'J. French Hill', 'party': 'R', 'state': 'AR', 'role': 'Member', 'contributions': 200000, 'stock_trades': 50000, 'score': 75},
            {'id': 'waters_maxine', 'name': 'Maxine Waters', 'party': 'D', 'state': 'CA', 'role': 'Member', 'contributions': 180000, 'stock_trades': 0, 'score': 65},
        ])

    # Committee votes
    votes = [
        {'bill_id': 'H.R. 4763', 'title': 'Financial Innovation and Technology for the 21st Century Act (FIT21)', 'date': '2025-05-22', 'result': 'Passed', 'yeas': 35, 'nays': 15, 'present': 0},
        {'bill_id': 'H.R. 5403', 'title': 'CBDC Anti-Surveillance State Act', 'date': '2025-05-23', 'result': 'Passed', 'yeas': 32, 'nays': 18, 'present': 1},
        {'bill_id': 'H.R. 1112', 'title': 'CFPB Accountability Act', 'date': '2025-03-15', 'result': 'Passed', 'yeas': 34, 'nays': 16, 'present': 0},
        {'bill_id': 'H.R. 2890', 'title': 'Community Bank Relief Act', 'date': '2025-04-10', 'result': 'Passed', 'yeas': 40, 'nays': 10, 'present': 1},
    ]

    # Legislation from committee
    legislation = [
        {'bill_id': 'H.R. 4763', 'title': 'FIT21 Act', 'sponsor': 'Rep. French Hill (R-AR)', 'status': 'Passed House', 'date': '2025-05-22', 'industries': ['crypto', 'fintech']},
        {'bill_id': 'H.R. 5403', 'title': 'CBDC Anti-Surveillance Act', 'sponsor': 'Rep. Tom Emmer (R-MN)', 'status': 'Passed House', 'date': '2025-05-23', 'industries': ['crypto']},
        {'bill_id': 'H.R. 4766', 'title': 'Clarity for Payment Stablecoins Act', 'sponsor': 'Rep. Patrick McHenry (R-NC)', 'status': 'In Committee', 'date': '2025-07-15', 'industries': ['crypto', 'fintech']},
        {'bill_id': 'H.R. 1112', 'title': 'CFPB Accountability Act', 'sponsor': 'Rep. Andy Barr (R-KY)', 'status': 'In Committee', 'date': '2025-02-15', 'industries': ['banking', 'consumer_lending']},
        {'bill_id': 'H.R. 2890', 'title': 'Community Bank Relief Act', 'sponsor': 'Rep. Blaine Luetkemeyer (R-MO)', 'status': 'Passed House', 'date': '2025-04-10', 'industries': ['banking']},
    ]

    # News - try to get real news from data store first
    news = []
    try:
        from justdata.apps.electwatch.services.data_store import get_news
        all_news = get_news()
        committee_keywords = [committee['name'].lower(), committee.get('full_name', '').lower()]

        # Filter news relevant to this committee
        for item in all_news:
            title_lower = item.get('title', '').lower()
            if any(kw in title_lower for kw in committee_keywords if kw):
                news.append({
                    'title': item.get('title', ''),
                    'source': item.get('source', ''),
                    'date': item.get('published_date', item.get('date', '')),
                    'url': item.get('url', ''),
                    'reliable': item.get('reliable', True)
                })
                if len(news) >= 5:
                    break
    except Exception as e:
        logger.warning(f"Could not load news from store: {e}")

    # Fallback to placeholder news with search URLs if no real news found
    if not news:
        search_term = committee['name'].replace(' ', '+')
        news = [
            {'title': f'{committee["name"]} Committee Advances Major Crypto Legislation', 'source': 'Politico', 'date': '2026-01-08', 'url': f'https://www.politico.com/search?q={search_term}', 'reliable': True},
            {'title': f'{committee["chair"]["name"]} Outlines 2026 Legislative Priorities', 'source': 'American Banker', 'date': '2026-01-05', 'url': f'https://www.americanbanker.com/search?q={search_term}', 'reliable': True},
            {'title': f'Banking Industry Lobbying Intensifies as {committee["name"]} Considers Reform', 'source': 'Wall Street Journal', 'date': '2025-12-28', 'url': f'https://www.wsj.com/search?query={search_term}', 'reliable': True},
            {'title': f'Bipartisan Support Grows for Stablecoin Framework in {committee["chamber"]}', 'source': 'Reuters', 'date': '2025-12-20', 'url': f'https://www.reuters.com/search/news?query={search_term}', 'reliable': True},
        ]

    return jsonify({
        'success': True,
        'committee': {
            **committee,
            'members': members,
            'votes': votes,
            'legislation': legislation,
            'news': news,
        }
    })


@app.route('/api/sectors', methods=['GET'])
def api_get_sectors():
    """Get all industry sectors."""
    return jsonify({
        'success': True,
        'sectors': _get_sectors()
    })


@app.route('/api/freshness', methods=['GET'])
def api_get_freshness():
    """
    Get data freshness information from weekly update metadata.

    Returns timestamps showing when data was last updated and next scheduled update.
    """
    from datetime import datetime, timedelta

    # Try to get actual metadata from data store
    try:
        from justdata.apps.electwatch.services.data_store import get_metadata, get_freshness
        metadata = get_metadata()

        if metadata.get('status') == 'valid':
            sources = metadata.get('data_sources', {})
            last_updated = metadata.get('last_updated')
            last_updated_dt = datetime.fromisoformat(last_updated) if last_updated else datetime.now()

            return jsonify({
                'success': True,
                'last_updated': metadata.get('last_updated_display', last_updated_dt.strftime('%B %d, %Y')),
                'last_updated_iso': last_updated,
                'next_update': metadata.get('next_update_display', ''),
                'next_update_iso': metadata.get('next_update'),
                'sources': {
                    'fec': {
                        'name': 'FEC Campaign Finance',
                        'date': last_updated_dt.strftime('%b %d, %Y'),
                        'date_full': last_updated_dt.strftime('%B %d, %Y'),
                        'days_old': (datetime.now() - last_updated_dt).days,
                        'status': sources.get('fec', {}).get('status', 'unknown'),
                        'records': sources.get('fec', {}).get('records', 0),
                        'refresh_schedule': 'Weekly (Sundays at midnight)',
                        'note': 'Campaign contributions and PAC data'
                    },
                    'stock_act': {
                        'name': 'STOCK Act Disclosures',
                        'date': last_updated_dt.strftime('%b %d, %Y'),
                        'date_full': last_updated_dt.strftime('%B %d, %Y'),
                        'days_old': (datetime.now() - last_updated_dt).days,
                        'status': sources.get('quiver', {}).get('status', 'unknown'),
                        'records': sources.get('quiver', {}).get('records', 0),
                        'refresh_schedule': 'Weekly (Sundays at midnight)',
                        'note': 'Congressional stock trades (may lag up to 45 days per STOCK Act)'
                    },
                    'committees': {
                        'name': 'Committee Assignments',
                        'date': last_updated_dt.strftime('%b %d, %Y'),
                        'date_full': last_updated_dt.strftime('%B %d, %Y'),
                        'days_old': (datetime.now() - last_updated_dt).days,
                        'status': 'success',
                        'records': metadata.get('counts', {}).get('officials', 0),
                        'refresh_schedule': 'Weekly (Sundays at midnight)',
                        'note': 'House and Senate committee membership'
                    }
                },
                'data_window': metadata.get('data_window', {
                    'start': (datetime.now() - timedelta(days=365)).strftime('%B %d, %Y'),
                    'end': datetime.now().strftime('%B %d, %Y')
                }),
                'counts': metadata.get('counts', {})
            })
    except Exception as e:
        logger.warning(f"Could not load freshness metadata: {e}")

    # Fallback to sample data if no metadata
    now = datetime.now()
    fec_last_update = now - timedelta(days=(now.weekday() + 1) % 7)

    return jsonify({
        'success': True,
        'last_updated': fec_last_update.strftime('%B %d, %Y'),
        'last_updated_iso': fec_last_update.isoformat(),
        'status': 'no_weekly_data',
        'message': 'Run weekly_update.py to populate data',
        'sources': {
            'fec': {'name': 'FEC', 'date': 'Not loaded', 'status': 'pending', 'records': 0},
            'stock_act': {'name': 'STOCK Act', 'date': 'Not loaded', 'status': 'pending', 'records': 0},
            'committees': {'name': 'Committees', 'date': 'Not loaded', 'status': 'pending', 'records': 0}
        },
        'data_window': {
            'start': (now - timedelta(days=365)).strftime('%B %d, %Y'),
            'end': now.strftime('%B %d, %Y')
        }
    })


@app.route('/api/firm/<firm_name>', methods=['GET'])
def api_get_firm_detail(firm_name: str):
    """
    Get detailed information for a specific firm.

    Includes:
        - Connected officials
        - Contribution breakdown
        - Stock trades
        - SEC filings (10-K, 10-Q)
        - Regulatory/litigation mentions
        - Recent news
    """
    from justdata.apps.electwatch.services.sec_client import get_sample_sec_data

    # Try to get live data first
    try:
        from justdata.apps.electwatch.services.data_aggregator import get_data_aggregator
        aggregator = get_data_aggregator()
        live_data = aggregator.get_firm_detail(firm_name)

        if live_data and (live_data.get('congressional_trades') or live_data.get('news') or live_data.get('sec_filings')):
            # Format officials from congressional trades
            officials = []
            for off in live_data.get('officials', [])[:10]:
                officials.append({
                    'id': off.get('name', '').lower().replace(' ', '_'),
                    'name': off.get('name', ''),
                    'party': off.get('party', ''),
                    'state': off.get('state', ''),
                    'chamber': off.get('chamber', 'house'),
                    'committee': '',
                    'total': len(off.get('trades', [])) * 25000,  # Estimate
                    'has_pac': False,
                    'has_stock': True
                })

            # Format activity from trades
            activity = []
            for trade in live_data.get('congressional_trades', [])[:10]:
                activity.append({
                    'type': 'trade',
                    'official_name': trade.get('politician_name', ''),
                    'transaction': trade.get('type', 'unknown').title(),
                    'date': trade.get('transaction_date', ''),
                    'amount': trade.get('amount', {}).get('max', 0)
                })

            # Format news
            news = []
            for article in live_data.get('news', [])[:5]:
                news.append({
                    'title': article.get('headline', article.get('title', '')),
                    'source': article.get('source', ''),
                    'date': article.get('datetime', article.get('date', ''))[:10] if article.get('datetime') or article.get('date') else '',
                    'url': article.get('url', '#'),
                    'reliable': True
                })

            # Get stock quote
            quote = live_data.get('quote')
            quote_info = None
            if quote:
                quote_info = {
                    'current_price': quote.get('current_price', 0),
                    'change': quote.get('change', 0),
                    'change_percent': quote.get('change_percent', 0)
                }

            firm = {
                'name': live_data.get('name', firm_name),
                'ticker': live_data.get('ticker'),
                'industries': live_data.get('industries', []),
                'total': len(officials) * 50000,  # Estimate from trades
                'contributions': 0,
                'stock_trades': len(live_data.get('congressional_trades', [])) * 25000,
                'officials_count': len(officials),
                'party_split': {'r': 50, 'd': 50},
                'r_amount': 0,
                'd_amount': 0,
                'quote': quote_info,
                'officials': officials,
                'activity': activity,
                'sec_filings': live_data.get('sec_filings', []),
                'insider_transactions': live_data.get('insider_transactions', [])[:10],
                'regulatory_mentions': [],
                'litigation': [],
                'news': news,
                'data_source': 'live'
            }

            return jsonify({
                'success': True,
                'firm': firm,
                'data_source': 'live'
            })
    except Exception as e:
        logger.warning(f"Could not fetch live firm data: {e}")

    # Normalize firm name
    normalized = firm_name.lower().strip()

    # Try to get data from weekly data store
    try:
        from justdata.apps.electwatch.services.data_store import get_officials
        from justdata.apps.electwatch.services.firm_mapper import FirmMapper
        all_officials = get_officials()

        # Get firm record to find associated PACs
        mapper = FirmMapper()
        firm_record = mapper.get_firm_from_name(firm_name)
        firm_pac_names = []
        if firm_record:
            firm_pac_names = [pac.upper() for pac in firm_record.pac_names]
            logger.info(f"[FIRM] Found PACs for {firm_name}: {firm_pac_names}")

        # Find officials who have traded this firm OR received PAC contributions
        firm_officials = []
        pac_contributions = []  # PAC contribution records for this firm
        total_amount = 0
        total_pac_amount = 0
        party_counts = {'r': 0, 'd': 0}
        party_amounts = {'r': 0, 'd': 0}

        for official in all_officials:
            # Check for structured firms data first
            firms_data = official.get('firms', [])
            has_match = False
            official_buys = 0
            official_sells = 0

            for firm in firms_data:
                firm_ticker = firm.get('ticker', '').upper()
                firm_name_lower = firm.get('name', '').lower()

                # Match by ticker or name
                if firm_ticker and firm_ticker.upper() == normalized.upper():
                    match = True
                elif normalized in firm_name_lower or firm_name_lower in normalized:
                    match = True
                else:
                    match = False

                if match:
                    has_match = True
                    official_buys = firm.get('buys', 0)
                    official_sells = firm.get('sells', 0)
                    firm_total = firm.get('total', 0)
                    break

            # If no firms data, check trades array for ticker match
            if not has_match and official.get('trades'):
                # Check if official traded this ticker
                from justdata.apps.electwatch.services.firm_mapper import AmountRange
                for trade in official.get('trades', []):
                    # Handle both dict and string formats
                    if isinstance(trade, dict):
                        trade_ticker = trade.get('ticker', '').upper()
                        trade_company = trade.get('company', '').lower()
                    else:
                        # Parse string format
                        trade_str = str(trade)
                        trade_ticker = ''
                        trade_company = ''
                        if 'ticker=' in trade_str:
                            trade_ticker = trade_str.split('ticker=')[1].split(';')[0].upper()
                        if 'company=' in trade_str:
                            trade_company = trade_str.split('company=')[1].split(';')[0].lower()

                    # Match by ticker or company name
                    if trade_ticker == normalized.upper() or normalized.lower() in trade_company:
                        has_match = True
                        # Count buys and sells
                        trade_type = ''
                        amount_range = ''
                        if isinstance(trade, dict):
                            trade_type = trade.get('type', '')
                            amount_range = trade.get('amount_range', '')
                        else:
                            trade_str = str(trade)
                            if 'type=' in trade_str:
                                trade_type = trade_str.split('type=')[1].split(';')[0]
                            if 'amount_range=' in trade_str:
                                amount_range = trade_str.split('amount_range=')[1].split(';')[0]

                        try:
                            amount = AmountRange.from_bucket(amount_range)
                            if 'purchase' in trade_type.lower():
                                official_buys += amount.max_amount
                            elif 'sale' in trade_type.lower():
                                official_sells += amount.max_amount
                        except:
                            pass

            if has_match:
                party = official.get('party', '').upper()
                firm_total = official_buys + official_sells

                firm_officials.append({
                    'id': official.get('id', ''),
                    'name': official.get('name', ''),
                    'party': party,
                    'state': official.get('state', ''),
                    'chamber': official.get('chamber', 'house'),
                    'committee': ', '.join(official.get('committees', [])[:2]),
                    'total': firm_total,
                    'buys': official_buys,
                    'sells': official_sells,
                    'has_pac': False,
                    'has_stock': True,
                    'photo_url': official.get('photo_url'),
                })

                total_amount += firm_total
                if party == 'R':
                    party_counts['r'] += 1
                    party_amounts['r'] += firm_total
                elif party == 'D':
                    party_counts['d'] += 1
                    party_amounts['d'] += firm_total

            # Also check for PAC contributions from this firm
            if firm_pac_names:
                for contrib in official.get('contributions_list', []):
                    pac_name = contrib.get('pac_name', '') or contrib.get('source', '')
                    if pac_name.upper() in firm_pac_names or any(fp in pac_name.upper() for fp in firm_pac_names):
                        amount = contrib.get('amount', 0)
                        party = official.get('party', '').upper()

                        pac_contributions.append({
                            'official_id': official.get('id', ''),
                            'official_name': official.get('name', ''),
                            'party': party,
                            'state': official.get('state', ''),
                            'chamber': official.get('chamber', 'house'),
                            'pac_name': pac_name,
                            'amount': amount,
                            'date': contrib.get('date', ''),
                            'photo_url': official.get('photo_url'),
                        })
                        total_pac_amount += amount

        if firm_officials or pac_contributions:
            # Sort by total amount
            firm_officials.sort(key=lambda x: x['total'], reverse=True)

            # Calculate party split percentage
            total_party = party_counts['r'] + party_counts['d']
            if total_party > 0:
                party_split = {
                    'r': round(party_counts['r'] / total_party * 100),
                    'd': round(party_counts['d'] / total_party * 100)
                }
            else:
                party_split = {'r': 50, 'd': 50}

            # Get firm info from mapper if available
            firm_ticker = None
            firm_industries = []
            if firm_record:
                firm_ticker = firm_record.ticker
                firm_industries = firm_record.industries

            return jsonify({
                'success': True,
                'firm': {
                    'name': firm_record.name if firm_record else firm_name,
                    'ticker': firm_ticker or (normalized.upper() if len(normalized) <= 5 else None),
                    'industries': firm_industries,
                    'total': total_amount + total_pac_amount,
                    'contributions': total_pac_amount,  # PAC contributions
                    'stock_trades': total_amount,
                    'officials_count': len(firm_officials),
                    'party_split': party_split,
                    'r_amount': party_amounts['r'],
                    'd_amount': party_amounts['d'],
                    'officials': firm_officials[:20],
                    # PAC contribution data
                    'pac_name': firm_pac_names[0] if firm_pac_names else None,
                    'pac_names': firm_pac_names,
                    'pac_contributions': sorted(pac_contributions, key=lambda x: x['amount'], reverse=True)[:20],
                    'pac_contributions_total': total_pac_amount,
                    'pac_recipients_count': len(set(c['official_name'] for c in pac_contributions)),
                    'activity': [],
                    'sec_filings': [],
                    'insider_transactions': [],
                    'regulatory_mentions': [],
                    'litigation': [],
                    'news': [],
                    'data_source': 'weekly_update'
                },
                'data_source': 'weekly_update'
            })

    except Exception as e:
        logger.warning(f"Could not load firm data from store: {e}")

    # Sample firm data - fallback for when live data not available
    firm_data = {
        'wells fargo': {
            'name': 'Wells Fargo & Company',
            'ticker': 'WFC',
            'industries': ['banking'],
            'total': 850000,
            'contributions': 720000,
            'stock_trades': 130000,
            'officials_count': 45,
            'party_split': {'r': 58, 'd': 42},
            'r_amount': 493000,
            'd_amount': 357000,
        },
        'jpmorgan': {
            'name': 'JPMorgan Chase & Co.',
            'ticker': 'JPM',
            'industries': ['banking', 'investment'],
            'total': 780000,
            'contributions': 650000,
            'stock_trades': 130000,
            'officials_count': 42,
            'party_split': {'r': 55, 'd': 45},
            'r_amount': 429000,
            'd_amount': 351000,
        },
        'coinbase': {
            'name': 'Coinbase Global, Inc.',
            'ticker': 'COIN',
            'industries': ['crypto', 'fintech'],
            'total': 450000,
            'contributions': 310000,
            'stock_trades': 140000,
            'officials_count': 23,
            'party_split': {'r': 68, 'd': 32},
            'r_amount': 306000,
            'd_amount': 144000,
        },
        'bank of america': {
            'name': 'Bank of America Corporation',
            'ticker': 'BAC',
            'industries': ['banking'],
            'total': 620000,
            'contributions': 540000,
            'stock_trades': 80000,
            'officials_count': 38,
            'party_split': {'r': 52, 'd': 48},
            'r_amount': 322400,
            'd_amount': 297600,
        },
    }

    # Find matching firm
    firm = None
    for key, data in firm_data.items():
        if key in normalized or normalized in key:
            firm = data
            break

    if not firm:
        # Return default data for unknown firm
        firm = {
            'name': firm_name,
            'ticker': None,
            'industries': [],
            'total': 0,
            'contributions': 0,
            'stock_trades': 0,
            'officials_count': 0,
            'party_split': {'r': 50, 'd': 50},
            'r_amount': 0,
            'd_amount': 0,
        }

    # Get SEC filings data
    sec_data = get_sample_sec_data(firm_name)

    # Sample connected officials
    officials = [
        {'id': 'hill_j_french', 'name': 'J. French Hill', 'party': 'R', 'state': 'AR', 'chamber': 'house', 'committee': 'Financial Services (Chair)', 'total': 85000, 'has_pac': True, 'has_stock': True},
        {'id': 'waters_maxine', 'name': 'Maxine Waters', 'party': 'D', 'state': 'CA', 'chamber': 'house', 'committee': 'Financial Services', 'total': 72000, 'has_pac': True, 'has_stock': False},
        {'id': 'scott_tim', 'name': 'Tim Scott', 'party': 'R', 'state': 'SC', 'chamber': 'senate', 'committee': 'Banking (Chair)', 'total': 68000, 'has_pac': True, 'has_stock': True},
        {'id': 'warren_elizabeth', 'name': 'Elizabeth Warren', 'party': 'D', 'state': 'MA', 'chamber': 'senate', 'committee': 'Banking', 'total': 45000, 'has_pac': True, 'has_stock': False},
        {'id': 'mchenry_patrick', 'name': 'Patrick McHenry', 'party': 'R', 'state': 'NC', 'chamber': 'house', 'committee': 'Financial Services', 'total': 42000, 'has_pac': True, 'has_stock': False},
    ]

    # Sample recent activity
    activity = [
        {'type': 'contribution', 'official_name': 'J. French Hill', 'date': '2025-12-15', 'amount': 15000},
        {'type': 'trade', 'official_name': 'Tim Scott', 'transaction': 'Purchase', 'date': '2025-12-10', 'amount': 25000},
        {'type': 'contribution', 'official_name': 'Maxine Waters', 'date': '2025-11-20', 'amount': 10000},
        {'type': 'contribution', 'official_name': 'Patrick McHenry', 'date': '2025-11-15', 'amount': 12000},
        {'type': 'trade', 'official_name': 'J. French Hill', 'transaction': 'Purchase', 'date': '2025-10-28', 'amount': 35000},
    ]

    # Curated reliable news sources
    RELIABLE_SOURCES = [
        'Wall Street Journal', 'Reuters', 'Bloomberg', 'Financial Times',
        'New York Times', 'Washington Post', 'American Banker', 'Politico',
        'The Block', 'CoinDesk', 'CNBC', 'Associated Press', 'Axios'
    ]

    # Sample news with source reliability
    news = [
        {'title': f'{firm["name"]} Reports Q3 Earnings Beat', 'source': 'Wall Street Journal', 'date': '2026-01-08', 'url': 'https://www.wsj.com', 'reliable': True},
        {'title': f'Congressional Oversight of {firm["name"]} Practices Intensifies', 'source': 'American Banker', 'date': '2026-01-05', 'url': 'https://www.americanbanker.com', 'reliable': True},
        {'title': f'{firm["name"]} PAC Contributions Rise in Q4', 'source': 'Politico', 'date': '2025-12-20', 'url': 'https://www.politico.com', 'reliable': True},
    ]

    return jsonify({
        'success': True,
        'firm': {
            **firm,
            'officials': officials,
            'activity': activity,
            'sec_filings': sec_data.get('filings', []),
            'regulatory_mentions': sec_data.get('regulatory_mentions', []),
            'litigation': sec_data.get('litigation', []),
            'news': news,
        }
    })


@app.route('/api/firms', methods=['GET'])
def api_get_firms():
    """
    Get top firms/PACs by total contributions.

    Query params:
        - limit: Number of results (default 100)
        - industry: Filter by industry sector
    """
    limit = int(request.args.get('limit', 100))
    industry = request.args.get('industry')

    # Sample firms data sorted by total contributions (descending)
    all_firms = [
        {'name': 'Wells Fargo', 'ticker': 'WFC', 'industry': 'banking', 'total': 850000, 'officials': 45, 'stock_trades': 23},
        {'name': 'JPMorgan Chase', 'ticker': 'JPM', 'industry': 'banking', 'total': 780000, 'officials': 42, 'stock_trades': 31},
        {'name': 'Bank of America', 'ticker': 'BAC', 'industry': 'banking', 'total': 620000, 'officials': 38, 'stock_trades': 18},
        {'name': 'Citigroup', 'ticker': 'C', 'industry': 'banking', 'total': 540000, 'officials': 35, 'stock_trades': 15},
        {'name': 'Coinbase', 'ticker': 'COIN', 'industry': 'crypto', 'total': 450000, 'officials': 23, 'stock_trades': 28},
        {'name': 'Goldman Sachs', 'ticker': 'GS', 'industry': 'investment', 'total': 420000, 'officials': 31, 'stock_trades': 22},
        {'name': 'Morgan Stanley', 'ticker': 'MS', 'industry': 'investment', 'total': 390000, 'officials': 28, 'stock_trades': 19},
        {'name': 'BlackRock', 'ticker': 'BLK', 'industry': 'investment', 'total': 380000, 'officials': 26, 'stock_trades': 24},
        {'name': 'American Express', 'ticker': 'AXP', 'industry': 'consumer_lending', 'total': 350000, 'officials': 29, 'stock_trades': 14},
        {'name': 'Visa', 'ticker': 'V', 'industry': 'fintech', 'total': 340000, 'officials': 32, 'stock_trades': 26},
        {'name': 'Mastercard', 'ticker': 'MA', 'industry': 'fintech', 'total': 320000, 'officials': 30, 'stock_trades': 21},
        {'name': 'Robinhood', 'ticker': 'HOOD', 'industry': 'crypto', 'total': 280000, 'officials': 18, 'stock_trades': 35},
        {'name': 'Capital One', 'ticker': 'COF', 'industry': 'consumer_lending', 'total': 275000, 'officials': 24, 'stock_trades': 12},
        {'name': 'U.S. Bancorp', 'ticker': 'USB', 'industry': 'banking', 'total': 265000, 'officials': 22, 'stock_trades': 9},
        {'name': 'PNC Financial', 'ticker': 'PNC', 'industry': 'banking', 'total': 250000, 'officials': 21, 'stock_trades': 8},
        {'name': 'Charles Schwab', 'ticker': 'SCHW', 'industry': 'investment', 'total': 245000, 'officials': 19, 'stock_trades': 27},
        {'name': 'Fidelity Investments', 'ticker': None, 'industry': 'investment', 'total': 240000, 'officials': 25, 'stock_trades': 0},
        {'name': 'Truist Financial', 'ticker': 'TFC', 'industry': 'banking', 'total': 230000, 'officials': 18, 'stock_trades': 7},
        {'name': 'MetLife', 'ticker': 'MET', 'industry': 'insurance', 'total': 225000, 'officials': 20, 'stock_trades': 11},
        {'name': 'Prudential Financial', 'ticker': 'PRU', 'industry': 'insurance', 'total': 220000, 'officials': 19, 'stock_trades': 9},
        {'name': 'Rocket Companies', 'ticker': 'RKT', 'industry': 'mortgage', 'total': 210000, 'officials': 15, 'stock_trades': 6},
        {'name': 'PayPal', 'ticker': 'PYPL', 'industry': 'fintech', 'total': 205000, 'officials': 22, 'stock_trades': 18},
        {'name': 'Block (Square)', 'ticker': 'SQ', 'industry': 'crypto', 'total': 195000, 'officials': 16, 'stock_trades': 24},
        {'name': 'Discover Financial', 'ticker': 'DFS', 'industry': 'consumer_lending', 'total': 185000, 'officials': 17, 'stock_trades': 8},
        {'name': 'Synchrony Financial', 'ticker': 'SYF', 'industry': 'consumer_lending', 'total': 175000, 'officials': 14, 'stock_trades': 5},
        {'name': 'UnitedHealth Group', 'ticker': 'UNH', 'industry': 'insurance', 'total': 170000, 'officials': 28, 'stock_trades': 32},
        {'name': 'Aflac', 'ticker': 'AFL', 'industry': 'insurance', 'total': 165000, 'officials': 16, 'stock_trades': 7},
        {'name': 'KeyCorp', 'ticker': 'KEY', 'industry': 'banking', 'total': 160000, 'officials': 13, 'stock_trades': 4},
        {'name': 'Regions Financial', 'ticker': 'RF', 'industry': 'banking', 'total': 155000, 'officials': 12, 'stock_trades': 5},
        {'name': 'Fifth Third Bancorp', 'ticker': 'FITB', 'industry': 'banking', 'total': 150000, 'officials': 11, 'stock_trades': 3},
        {'name': 'Citizens Financial', 'ticker': 'CFG', 'industry': 'banking', 'total': 145000, 'officials': 10, 'stock_trades': 4},
        {'name': 'Ally Financial', 'ticker': 'ALLY', 'industry': 'consumer_lending', 'total': 140000, 'officials': 12, 'stock_trades': 6},
        {'name': 'Mr. Cooper Group', 'ticker': 'COOP', 'industry': 'mortgage', 'total': 135000, 'officials': 9, 'stock_trades': 2},
        {'name': 'Intercontinental Exchange', 'ticker': 'ICE', 'industry': 'investment', 'total': 130000, 'officials': 14, 'stock_trades': 10},
        {'name': 'CME Group', 'ticker': 'CME', 'industry': 'investment', 'total': 125000, 'officials': 13, 'stock_trades': 8},
        {'name': 'State Street', 'ticker': 'STT', 'industry': 'investment', 'total': 120000, 'officials': 11, 'stock_trades': 7},
        {'name': 'T. Rowe Price', 'ticker': 'TROW', 'industry': 'investment', 'total': 115000, 'officials': 10, 'stock_trades': 9},
        {'name': 'Stripe', 'ticker': None, 'industry': 'fintech', 'total': 110000, 'officials': 14, 'stock_trades': 0},
        {'name': 'Plaid', 'ticker': None, 'industry': 'fintech', 'total': 95000, 'officials': 8, 'stock_trades': 0},
        {'name': 'Marathon Digital', 'ticker': 'MARA', 'industry': 'crypto', 'total': 85000, 'officials': 7, 'stock_trades': 12},
    ]

    # Filter by industry if specified
    if industry:
        all_firms = [f for f in all_firms if f['industry'] == industry]

    # Already sorted by total descending
    firms = all_firms[:limit]

    return jsonify({
        'success': True,
        'firms': firms,
        'total': len(all_firms)
    })


@app.route('/api/search', methods=['GET'])
def api_search():
    """Search for officials, firms, or PACs."""
    query = request.args.get('q', '')
    search_type = request.args.get('type', 'all')  # 'official', 'firm', 'pac', 'all'

    # TODO: Implement search
    return jsonify({
        'success': True,
        'query': query,
        'type': search_type,
        'results': []
    })


# =============================================================================
# BILL LOOKUP API ENDPOINTS
# =============================================================================

@app.route('/api/bills/search', methods=['GET'])
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


@app.route('/api/bills/<bill_id>', methods=['GET'])
def api_get_bill(bill_id: str):
    """
    Get detailed information about a specific bill including sponsors, votes, and financial involvement.

    Args:
        bill_id: Bill identifier like "hr4763", "s1234", "H.R. 4763"
    """
    from justdata.apps.electwatch.services.congress_api_client import get_congress_client

    client = get_congress_client()

    # Parse bill ID
    parsed = client.parse_bill_id(bill_id)
    if not parsed:
        return jsonify({
            'success': False,
            'error': f'Invalid bill ID format: {bill_id}. Use format like "H.R. 4763" or "S. 1234"'
        }), 400

    # Get bill details
    bill = client.get_bill(parsed['type'], parsed['number'], parsed.get('congress', '119'))

    if not bill:
        return jsonify({
            'success': False,
            'error': f'Bill not found: {bill_id}'
        }), 404

    # Cross-reference with financial involvement data
    bill_with_involvement = _enrich_bill_with_financial_data(bill)

    return jsonify({
        'success': True,
        'bill': bill_with_involvement
    })


def _enrich_bill_with_financial_data(bill: dict) -> dict:
    """
    Add financial involvement data for sponsors, cosponsors, and voters.

    For each official involved with the bill, we add:
    - Their financial involvement in the bill's industries
    - Stock trades in related sectors
    - PAC contributions from related firms

    This creates the conflict-of-interest analysis.
    """
    # Get industries this bill relates to
    bill_industries = bill.get('industries', [])

    # Sample financial involvement data (would come from database in production)
    involvement_data = {
        'hill_j_french': {
            'total_involvement': 815000,
            'by_industry': {
                'crypto': {'contributions': 80000, 'stock_trades': 100000, 'total': 180000},
                'banking': {'contributions': 350000, 'stock_trades': 75000, 'total': 425000},
            },
            'related_firms': ['Coinbase', 'Robinhood', 'Wells Fargo']
        },
        'waters_maxine': {
            'total_involvement': 520000,
            'by_industry': {
                'banking': {'contributions': 280000, 'stock_trades': 25000, 'total': 305000},
                'consumer_lending': {'contributions': 120000, 'stock_trades': 10000, 'total': 130000},
            },
            'related_firms': ['Bank of America', 'JPMorgan Chase']
        },
        'emmer_tom': {
            'total_involvement': 580000,
            'by_industry': {
                'crypto': {'contributions': 180000, 'stock_trades': 120000, 'total': 300000},
                'fintech': {'contributions': 80000, 'stock_trades': 40000, 'total': 120000},
            },
            'related_firms': ['Coinbase', 'Block', 'Robinhood']
        },
        'mchenry_patrick': {
            'total_involvement': 480000,
            'by_industry': {
                'crypto': {'contributions': 95000, 'stock_trades': 50000, 'total': 145000},
                'banking': {'contributions': 200000, 'stock_trades': 35000, 'total': 235000},
            },
            'related_firms': ['Coinbase', 'JPMorgan Chase', 'Bank of America']
        },
        'torres_ritchie': {
            'total_involvement': 410000,
            'by_industry': {
                'crypto': {'contributions': 65000, 'stock_trades': 30000, 'total': 95000},
                'fintech': {'contributions': 80000, 'stock_trades': 25000, 'total': 105000},
            },
            'related_firms': ['Coinbase', 'Circle']
        },
        'pelosi_nancy': {
            'total_involvement': 890000,
            'by_industry': {
                'investment': {'contributions': 80000, 'stock_trades': 350000, 'total': 430000},
                'fintech': {'contributions': 60000, 'stock_trades': 180000, 'total': 240000},
            },
            'related_firms': ['NVIDIA', 'Apple', 'Microsoft', 'Visa']
        },
        'davidson_warren': {
            'total_involvement': 395000,
            'by_industry': {
                'crypto': {'contributions': 120000, 'stock_trades': 95000, 'total': 215000},
                'fintech': {'contributions': 60000, 'stock_trades': 20000, 'total': 80000},
            },
            'related_firms': ['Coinbase', 'Marathon Digital']
        },
        'lummis_cynthia': {
            'total_involvement': 520000,
            'by_industry': {
                'crypto': {'contributions': 85000, 'stock_trades': 200000, 'total': 285000},
                'banking': {'contributions': 120000, 'stock_trades': 15000, 'total': 135000},
            },
            'related_firms': ['Bitcoin (direct holdings)', 'Coinbase']
        },
    }

    # Enrich sponsors
    for sponsor in bill.get('sponsors', []):
        official_id = sponsor.get('official_id', '').lower().replace(' ', '_')
        if official_id in involvement_data:
            sponsor['financial_involvement'] = involvement_data[official_id]
            # Calculate industry-specific involvement for this bill
            relevant_amount = sum(
                involvement_data[official_id]['by_industry'].get(ind, {}).get('total', 0)
                for ind in bill_industries
            )
            sponsor['relevant_involvement'] = relevant_amount
            sponsor['has_conflict'] = relevant_amount > 50000

    # Enrich cosponsors
    for cosponsor in bill.get('cosponsors', []):
        official_id = cosponsor.get('official_id', '').lower().replace(' ', '_')
        if official_id in involvement_data:
            cosponsor['financial_involvement'] = involvement_data[official_id]
            relevant_amount = sum(
                involvement_data[official_id]['by_industry'].get(ind, {}).get('total', 0)
                for ind in bill_industries
            )
            cosponsor['relevant_involvement'] = relevant_amount
            cosponsor['has_conflict'] = relevant_amount > 50000

    # Enrich vote positions
    for vote in bill.get('votes', []):
        for position in vote.get('positions', []):
            official_id = position.get('official_id', '').lower().replace(' ', '_')
            if official_id in involvement_data:
                position['financial_involvement'] = involvement_data[official_id]
                relevant_amount = sum(
                    involvement_data[official_id]['by_industry'].get(ind, {}).get('total', 0)
                    for ind in bill_industries
                )
                position['relevant_involvement'] = relevant_amount
                position['has_conflict'] = relevant_amount > 50000

    # Add summary statistics
    total_with_conflicts = 0
    total_conflict_amount = 0

    for vote in bill.get('votes', []):
        for position in vote.get('positions', []):
            if position.get('has_conflict'):
                total_with_conflicts += 1
                total_conflict_amount += position.get('relevant_involvement', 0)

    bill['conflict_summary'] = {
        'voters_with_industry_ties': total_with_conflicts,
        'total_industry_involvement': total_conflict_amount,
        'industries_affected': bill_industries
    }

    return bill


@app.route('/bill/<bill_id>')
def view_bill(bill_id: str):
    """Render bill detail page."""
    return render_template('bill_view.html', bill_id=bill_id)


@app.route('/api/insights', methods=['GET'])
def api_get_insights():
    """
    Get AI-generated pattern insights across officials, industries, and firms.

    In production, insights are pre-generated during weekly update and served from file.
    Use ?refresh=true to regenerate insights on demand (dev/testing only).

    This endpoint uses Claude to analyze aggregate data and identify patterns
    like coordinated contributions, stock trading aligned with PAC activity, etc.
    """
    try:
        from justdata.apps.electwatch.services.data_store import get_insights, get_insights_metadata

        # Check if refresh is requested (dev/testing only)
        refresh = request.args.get('refresh', 'false').lower() == 'true'

        if not refresh:
            # Try to load pre-generated insights from file
            stored_insights = get_insights()
            insights_meta = get_insights_metadata()

            if stored_insights and len(stored_insights) > 0:
                return jsonify({
                    'success': True,
                    'insights': stored_insights,
                    'generated_at': insights_meta.get('generated_at', datetime.now().isoformat()),
                    'source': 'weekly_update'
                })

        # No stored insights or refresh requested - generate new ones
        if not ElectWatchConfig.CLAUDE_API_KEY:
            # Return sample insights when no API key
            return jsonify({
                'success': True,
                'insights': _get_sample_insights(),
                'generated_at': datetime.now().isoformat(),
                'note': 'Sample insights - Claude API key not configured'
            })

        # Generate real AI insights
        insights = _generate_ai_pattern_insights()

        return jsonify({
            'success': True,
            'insights': insights,
            'generated_at': datetime.now().isoformat(),
            'source': 'live_generation'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'insights': _get_sample_insights()
        }), 500


def _get_sample_insights():
    """Return sample insights for demo/testing with detailed entity data and sources."""
    return [
        {
            'title': 'Crypto Industry Concentration',
            'summary': 'Coinbase and related crypto firms have contributed $1.2M to Republican '
                      'members of the House Financial Services Committee in 2025. Simultaneously, '
                      '8 of these members have reported COIN stock purchases totaling $180K-$400K.',
            'detailed_summary': '''Analysis reveals a significant concentration of crypto industry financial activity among Republican members of the [[committee:house-financial-services|House Financial Services Committee]].

Between January 2025 and January 2026, [[firm:Coinbase|Coinbase Global Inc PAC]] contributed $450,000 across 23 committee members, while [[firm:Robinhood|Robinhood Markets]] contributed $280,000 to 18 members.

**Key Finding:** 8 of these same members reported purchasing COIN stock during this period, with disclosure ranges indicating total purchases between $180,000 and $400,000.

**Notable Members:**
• [[official:french_hill|Rep. French Hill]] (R-AR) - Committee Chair, received $180,000 in crypto PAC contributions and purchased COIN stock
• [[official:tom_emmer|Rep. Tom Emmer]] (R-MN) - Majority Whip, received $145,000 and purchased COIN
• [[official:cynthia_lummis|Sen. Cynthia Lummis]] (R-WY) - Senate Banking member, known Bitcoin advocate

This pattern suggests potential coordination between PAC contribution strategies and personal investment decisions among members with direct oversight authority over [[industry:crypto|cryptocurrency regulation]].''',
            'evidence': 'Based on FEC filings and STOCK Act disclosures through Jan 2026',
            'category': 'cross_correlation',
            'severity': 'high',
            'firms': [
                {'name': 'Coinbase', 'ticker': 'COIN', 'amount': 450000, 'detail': '23 officials received contributions'},
                {'name': 'Robinhood', 'ticker': 'HOOD', 'amount': 280000, 'detail': '18 officials received contributions'},
                {'name': 'Block (Square)', 'ticker': 'SQ', 'amount': 195000, 'detail': '16 officials received contributions'},
            ],
            'officials': [
                {'id': 'french_hill', 'name': 'French Hill', 'party': 'R', 'state': 'AR', 'amount': 180000, 'detail': 'Chair, purchased COIN stock'},
                {'id': 'tom_emmer', 'name': 'Tom Emmer', 'party': 'R', 'state': 'MN', 'amount': 145000, 'detail': 'Majority Whip, purchased COIN'},
                {'id': 'cynthia_lummis', 'name': 'Cynthia Lummis', 'party': 'R', 'state': 'WY', 'amount': 120000, 'detail': 'Senate Banking, Bitcoin advocate'},
                {'id': 'ritchie_torres', 'name': 'Ritchie Torres', 'party': 'D', 'state': 'NY', 'amount': 95000, 'detail': 'Crypto Caucus member'},
            ],
            'industries': [
                {'code': 'crypto', 'name': 'Digital Assets & Crypto', 'amount': 1200000, 'detail': 'Primary sector, 71% to Republicans'},
            ],
            'committees': [
                {'id': 'house-financial-services', 'name': 'House Financial Services', 'chamber': 'house', 'members': 71, 'detail': 'Primary jurisdiction over crypto regulation'},
            ],
            'sources': [
                {'title': 'Coinbase PAC spending surges as crypto regulation heats up', 'url': 'https://www.politico.com/news/2025/crypto-pac-spending', 'source': 'Politico', 'date': '2025-11-15'},
                {'title': 'Congressional Stock Trading in Crypto Sector Under Scrutiny', 'url': 'https://www.reuters.com/markets/congressional-crypto-trading', 'source': 'Reuters', 'date': '2025-12-02'},
                {'title': 'FEC Records: Crypto Industry PAC Disbursements Q3-Q4 2025', 'url': 'https://www.fec.gov/data/disbursements/', 'source': 'FEC.gov', 'date': '2026-01-05'},
            ]
        },
        {
            'title': 'Banking PAC Activity Spike',
            'summary': 'Wells Fargo and JPMorgan PAC contributions to Senate Banking Committee '
                      'members increased 45% in Q4 2025 compared to Q3, correlating with '
                      'upcoming CFPB oversight hearings scheduled for February 2026.',
            'detailed_summary': '''A significant spike in [[industry:banking|banking sector]] PAC contributions occurred in Q4 2025, coinciding with scheduled CFPB oversight hearings.

**Contribution Increases (Q3 to Q4 2025):**
• [[firm:Wells Fargo|Wells Fargo PAC]]: +52% ($850,000 total)
• [[firm:JPMorgan Chase|JPMorgan Chase PAC]]: +41% ($780,000 total)
• [[firm:Bank of America|Bank of America PAC]]: +28% ($620,000 total)

This surge correlates with the scheduling of CFPB oversight hearings for February 2026 and pending consideration of the Consumer Financial Protection Reform Act.

**Key Recipients on [[committee:senate-banking|Senate Banking Committee]]:**
• [[official:tim_scott|Sen. Tim Scott]] (R-SC) - Ranking Member, received $320,000
• [[official:elizabeth_warren|Sen. Elizabeth Warren]] (D-MA) - CFPB advocate, received $95,000

The [[committee:house-financial-services|House Financial Services Committee]] is expected to hold joint oversight hearings. Total combined contributions from these two institutions to Banking Committee members: $1.4M.

The timing suggests strategic deployment of PAC resources ahead of significant regulatory review periods.''',
            'evidence': 'FEC data analysis comparing quarterly contribution trends',
            'category': 'timing',
            'severity': 'medium',
            'firms': [
                {'name': 'Wells Fargo', 'ticker': 'WFC', 'amount': 850000, 'detail': '52% increase Q3 to Q4'},
                {'name': 'JPMorgan Chase', 'ticker': 'JPM', 'amount': 780000, 'detail': '41% increase Q3 to Q4'},
                {'name': 'Bank of America', 'ticker': 'BAC', 'amount': 620000, 'detail': '28% increase Q3 to Q4'},
            ],
            'officials': [
                {'id': 'tim_scott', 'name': 'Tim Scott', 'party': 'R', 'state': 'SC', 'amount': 320000, 'detail': 'Ranking Member, Banking'},
                {'id': 'elizabeth_warren', 'name': 'Elizabeth Warren', 'party': 'D', 'state': 'MA', 'amount': 95000, 'detail': 'Banking Committee, CFPB advocate'},
            ],
            'industries': [
                {'code': 'banking', 'name': 'Banking & Depository', 'amount': 2250000, 'detail': '45% Q4 increase'},
            ],
            'committees': [
                {'id': 'senate-banking', 'name': 'Banking, Housing, and Urban Affairs', 'chamber': 'senate', 'members': 24, 'detail': 'Primary CFPB oversight authority'},
                {'id': 'house-financial-services', 'name': 'House Financial Services', 'chamber': 'house', 'members': 71, 'detail': 'Joint oversight hearings'},
            ],
            'sources': [
                {'title': 'Big Banks Ramp Up Political Spending Ahead of CFPB Hearings', 'url': 'https://www.wsj.com/finance/banking-pac-spending-cfpb', 'source': 'Wall Street Journal', 'date': '2025-12-18'},
                {'title': 'Senate Banking Committee schedules February CFPB oversight', 'url': 'https://www.banking.senate.gov/hearings', 'source': 'Senate.gov', 'date': '2025-11-30'},
                {'title': 'Q4 2025 PAC Activity Report', 'url': 'https://www.opensecrets.org/pacs', 'source': 'OpenSecrets', 'date': '2026-01-08'},
            ]
        },
        {
            'title': 'Cross-Party Pattern: Fintech',
            'summary': 'Fintech firms (PayPal, Block, Stripe) show unusually balanced contributions '
                      'across party lines, with 52% to Democrats and 48% to Republicans—significantly '
                      'more balanced than traditional banking (68% R / 32% D).',
            'detailed_summary': '''[[industry:fintech|Fintech sector]] PAC contributions display a notably different partisan distribution compared to traditional financial services.

**Partisan Split Comparison:**
| Sector | Democrat | Republican |
|--------|----------|------------|
| Traditional Banking | 32% | 68% |
| Fintech | 52% | 48% |

**Individual Firm Breakdowns:**
• [[firm:Visa|Visa]]: 54% D / 46% R ($340,000 total)
• [[firm:Mastercard|Mastercard]]: 51% D / 49% R ($320,000 total)
• [[firm:PayPal|PayPal]]: 55% D / 45% R ($205,000 total)

**Key Recipients:**
• [[official:maxine_waters|Rep. Maxine Waters]] (D-CA) - Ranking Member, [[committee:house-financial-services|House Financial Services]]: $125,000
• [[official:french_hill|Rep. French Hill]] (R-AR) - Chair, House Financial Services: $110,000

This balanced approach may reflect the sector's interest in maintaining regulatory relationships regardless of which party controls Congress. Total [[industry:fintech|fintech]] contributions reached $865,000 in the analysis period.''',
            'evidence': 'Comparative analysis of contribution patterns by industry',
            'category': 'party_balance',
            'severity': 'low',
            'firms': [
                {'name': 'Visa', 'ticker': 'V', 'amount': 340000, 'detail': '54% D / 46% R split'},
                {'name': 'Mastercard', 'ticker': 'MA', 'amount': 320000, 'detail': '51% D / 49% R split'},
                {'name': 'PayPal', 'ticker': 'PYPL', 'amount': 205000, 'detail': '55% D / 45% R split'},
            ],
            'officials': [
                {'id': 'maxine_waters', 'name': 'Maxine Waters', 'party': 'D', 'state': 'CA', 'amount': 125000, 'detail': 'Ranking Member, Fin Services'},
                {'id': 'french_hill', 'name': 'French Hill', 'party': 'R', 'state': 'AR', 'amount': 110000, 'detail': 'Chair, Fin Services'},
            ],
            'industries': [
                {'code': 'fintech', 'name': 'Financial Technology', 'amount': 865000, 'detail': '52% D / 48% R overall'},
                {'code': 'banking', 'name': 'Banking & Depository', 'amount': 4200000, 'detail': '32% D / 68% R for comparison'},
            ],
            'committees': [
                {'id': 'house-financial-services', 'name': 'House Financial Services', 'chamber': 'house', 'members': 71, 'detail': 'Fintech regulatory oversight'},
                {'id': 'senate-banking', 'name': 'Banking, Housing, and Urban Affairs', 'chamber': 'senate', 'members': 24, 'detail': 'Payments regulation'},
            ],
            'sources': [
                {'title': 'Fintech lobbying takes bipartisan approach as regulation looms', 'url': 'https://www.americanbanker.com/fintech-lobbying-bipartisan', 'source': 'American Banker', 'date': '2025-10-22'},
                {'title': 'Payment Industry PAC Spending Analysis 2025', 'url': 'https://www.opensecrets.org/industries/indus.php?ind=F03', 'source': 'OpenSecrets', 'date': '2025-12-15'},
            ]
        },
        {
            'title': 'Pre-Vote Stock Activity',
            'summary': '12 House Financial Services Committee members traded bank stocks within '
                      '30 days of the committee vote on the Regional Bank Stability Act. '
                      '9 of these trades were in institutions directly affected by the legislation.',
            'detailed_summary': '''STOCK Act disclosure analysis reveals concerning trading patterns surrounding the Regional Bank Stability Act vote.

**Key Finding:** 12 [[committee:house-financial-services|House Financial Services Committee]] members executed trades in [[industry:banking|banking sector]] stocks within 30 days of the November 2025 committee vote. Of these, **9 trades involved institutions directly affected by the legislation**.

**Stocks Traded Before Vote:**
• [[firm:KeyCorp|KeyCorp (KEY)]]: 4 members traded, $160,000 total value
• [[firm:Regions Financial|Regions Financial (RF)]]: 3 members traded, $155,000 total
• [[firm:Fifth Third Bancorp|Fifth Third Bancorp (FITB)]]: 2 members traded, $150,000 total

**Notable Trading Activity:**
• [[official:french_hill|Rep. French Hill]] (R-AR) - Purchased KEY stock 14 days before committee vote, disclosed value $95,000
• [[official:maxine_waters|Rep. Maxine Waters]] (D-CA) - No trades in affected stocks during window

The legislation's provisions on capital requirements and stress testing would directly benefit regional banks. Members who purchased shares voted in favor of relaxing these requirements.

Total disclosed trade value ranges from $245,000 to $780,000 due to STOCK Act bucket reporting requirements.''',
            'evidence': 'Cross-referenced STOCK Act disclosures with committee vote calendar',
            'category': 'timing',
            'severity': 'high',
            'firms': [
                {'name': 'KeyCorp', 'ticker': 'KEY', 'amount': 160000, 'detail': '4 members traded before vote'},
                {'name': 'Regions Financial', 'ticker': 'RF', 'amount': 155000, 'detail': '3 members traded before vote'},
                {'name': 'Fifth Third Bancorp', 'ticker': 'FITB', 'amount': 150000, 'detail': '2 members traded before vote'},
            ],
            'officials': [
                {'id': 'french_hill', 'name': 'French Hill', 'party': 'R', 'state': 'AR', 'amount': 95000, 'detail': 'Purchased KEY 14 days before vote'},
                {'id': 'maxine_waters', 'name': 'Maxine Waters', 'party': 'D', 'state': 'CA', 'amount': 0, 'detail': 'No trades in affected stocks'},
            ],
            'industries': [
                {'code': 'banking', 'name': 'Banking & Depository', 'amount': 465000, 'detail': '12 members, 9 in affected institutions'},
            ],
            'committees': [
                {'id': 'house-financial-services', 'name': 'House Financial Services', 'chamber': 'house', 'members': 71, 'detail': 'Regional Bank Stability Act vote'},
            ],
            'sources': [
                {'title': 'Lawmakers traded bank stocks ahead of key committee vote', 'url': 'https://www.nytimes.com/2025/12/lawmakers-stock-trading-bank-vote', 'source': 'New York Times', 'date': '2025-12-10'},
                {'title': 'Regional Bank Stability Act advances from committee', 'url': 'https://financialservices.house.gov/news/regional-bank-stability-act', 'source': 'House.gov', 'date': '2025-11-18'},
                {'title': 'STOCK Act Filings Database', 'url': 'https://efdsearch.senate.gov/search/', 'source': 'Senate.gov', 'date': '2025-12-01'},
                {'title': 'Analysis: Congressional Trading and Banking Legislation', 'url': 'https://www.propublica.org/congress-stock-trading', 'source': 'ProPublica', 'date': '2025-12-22'},
            ]
        }
    ]


def _generate_ai_pattern_insights():
    """Generate real AI insights using Claude based on actual data."""
    import sys
    print("[AI] Starting insight generation...", flush=True)
    try:
        from justdata.shared.analysis.ai_provider import AIAnalyzer
        from justdata.apps.electwatch.services.data_store import get_officials, get_firms, get_metadata

        print("[AI] Imports successful, loading data...", flush=True)

        # Load actual data
        officials = get_officials()
        firms = get_firms()
        metadata = get_metadata()

        print(f"[AI] Loaded {len(officials) if officials else 0} officials, {len(firms) if firms else 0} firms", flush=True)

        if not officials or len(officials) < 5:
            print("[AI] Not enough data to generate insights", flush=True)
            return _get_sample_insights()

        # Build data summary for AI analysis
        # Top 20 by financial sector PAC
        top_pac_recipients = sorted(
            [o for o in officials if o.get('financial_sector_pac', 0) > 0],
            key=lambda x: x.get('financial_sector_pac', 0),
            reverse=True
        )[:20]

        # Top 20 by stock trades
        top_traders = sorted(
            [o for o in officials if o.get('stock_trades_max', 0) > 0],
            key=lambda x: x.get('stock_trades_max', 0),
            reverse=True
        )[:20]

        # Group by party
        rep_pac_total = sum(o.get('financial_sector_pac', 0) for o in officials if o.get('party') == 'R')
        dem_pac_total = sum(o.get('financial_sector_pac', 0) for o in officials if o.get('party') == 'D')

        # Build context strings
        pac_recipients_str = "\n".join([
            f"- {o['name']} ({o['party']}-{o['state']}): ${o.get('financial_sector_pac', 0):,.0f} financial PAC, "
            f"${o.get('stock_trades_max', 0):,.0f} max trades, committees: {', '.join(o.get('committees', [])[:2])}"
            for o in top_pac_recipients[:15]
        ])

        traders_str = "\n".join([
            f"- {o['name']} ({o['party']}-{o['state']}): ${o.get('purchases_max', 0):,.0f} buys, "
            f"${o.get('sales_max', 0):,.0f} sells, top industries: {', '.join([i.get('name', i) if isinstance(i, dict) else i for i in o.get('top_industries', [])[:2]])}"
            for o in top_traders[:15]
        ])

        # Top firms by connected officials
        top_firms_str = ""
        if firms:
            sorted_firms = sorted(firms, key=lambda x: x.get('connected_officials', 0), reverse=True)[:10]
            top_firms_str = "\n".join([
                f"- {f['name']} ({f.get('ticker', 'N/A')}): {f.get('connected_officials', 0)} connected officials, "
                f"${f.get('total_pac', 0):,.0f} PAC contributions"
                for f in sorted_firms
            ])

        prompt = f"""Analyze congressional financial activity data and identify patterns for a transparency research tool.

IMPORTANT DEFINITIONS:
- Financial Sector PAC: Political Action Committee contributions from banks, insurance, investment, and fintech firms
- Stock Trades: Disclosed securities transactions by members of Congress (STOCK Act filings)
- Cross-correlation: Pattern where PAC contributions and stock trades occur in same industry sector

DATA SUMMARY (as of {metadata.get('last_updated_display', 'January 2026')}):

Top Financial Sector PAC Recipients:
{pac_recipients_str}

Top Financial Sector Stock Traders:
{traders_str}

Top Financial Firms by Congressional Connections:
{top_firms_str}

Aggregate Statistics:
- Republican financial PAC total: ${rep_pac_total:,.0f}
- Democratic financial PAC total: ${dem_pac_total:,.0f}
- Total officials tracked: {len(officials)}

ANALYSIS REQUIREMENTS:
Generate exactly 4 findings based ONLY on the data above. Each finding must:
1. Reference specific officials and dollar amounts from the provided data
2. Identify a clear pattern (cross-correlation, concentration, or party distribution)
3. Use professional, analytical tone without speculation
4. Cite actual data points, not hypothetical scenarios

OUTPUT FORMAT (JSON array with 4 objects):
{{
  "title": "5-8 word headline",
  "summary": "2 sentences max referencing specific data",
  "detailed_summary": "3-4 paragraphs with entity links: [[official:name_id|Display Name]], [[firm:Firm Name|Display]], [[committee:house-financial-services|Committee Name]], [[industry:banking|industry name]]. Use **bold** for emphasis and bullet points with •",
  "evidence": "Data source (FEC filings, STOCK Act disclosures, etc.)",
  "category": "cross_correlation|concentration|party_balance",
  "severity": "high|medium|low",
  "firms": [{{"name": "...", "ticker": "...", "amount": 0, "detail": "..."}}],
  "officials": [{{"id": "lowercase_name", "name": "...", "party": "R|D", "state": "XX", "amount": 0, "detail": "..."}}],
  "industries": [{{"code": "banking|crypto|fintech|insurance", "name": "...", "amount": 0, "detail": "..."}}],
  "committees": [{{"id": "house-financial-services|senate-banking", "name": "...", "chamber": "house|senate", "members": 0, "detail": "..."}}],
  "sources": [{{"title": "...", "url": "https://...", "source": "FEC.gov|House.gov|Senate.gov", "date": "YYYY-MM-DD"}}]
}}

IMPORTANT:
- Use ONLY data provided above - do not invent officials, amounts, or patterns
- Official IDs should be lowercase with underscores (e.g., "french_hill", "tommy_tuberville")
- Include 2-4 sources per insight from government data sources (FEC.gov, House.gov, Senate.gov, efdsearch.senate.gov)
- Severity should reflect actual concentration: high = significant pattern affecting oversight, medium = notable trend, low = interesting observation

Return ONLY the JSON array, no additional text."""

        print("[AI] Generating insights from real data...", flush=True)
        print(f"[AI] Prompt length: {len(prompt)} chars", flush=True)
        analyzer = AIAnalyzer(ai_provider='claude')
        print("[AI] Calling Claude API...", flush=True)
        response = analyzer._call_ai(prompt, max_tokens=8000, temperature=0.3)
        print(f"[AI] Got response: {len(response) if response else 0} chars", flush=True)

        # Try to parse JSON response
        try:
            # Clean up response - sometimes Claude adds markdown code blocks
            cleaned = response.strip()
            if cleaned.startswith('```json'):
                cleaned = cleaned[7:]
            if cleaned.startswith('```'):
                cleaned = cleaned[3:]
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            insights = json.loads(cleaned)
            if isinstance(insights, list) and len(insights) > 0:
                print(f"[AI] Successfully generated {len(insights)} insights")
                return insights
        except json.JSONDecodeError as e:
            print(f"[AI] JSON parse error: {e}")
            print(f"[AI] Response preview: {response[:500]}...")

        # Fallback to sample if parsing fails
        return _get_sample_insights()

    except Exception as e:
        print(f"[AI] Error generating insights: {e}")
        import traceback
        traceback.print_exc()
        return _get_sample_insights()


@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    """
    Run analysis for an official.

    Request body:
        {
            "official_id": "hill_j_french",
            "include_ai_insights": true
        }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data received'}), 400

        official_id = data.get('official_id')
        if not official_id:
            return jsonify({'success': False, 'error': 'official_id required'}), 400

        include_ai = data.get('include_ai_insights', True)

        # Create job ID and progress tracker
        job_id = str(uuid.uuid4())
        progress_tracker = create_progress_tracker(job_id)

        # Store request in session
        session['official_id'] = official_id
        session['job_id'] = job_id

        def run_analysis():
            try:
                from justdata.apps.electwatch.core import run_official_analysis
                result = run_official_analysis(
                    official_id=official_id,
                    include_ai=include_ai,
                    job_id=job_id,
                    progress_tracker=progress_tracker
                )

                if not result.get('success'):
                    error_msg = result.get('error', 'Unknown error')
                    progress_tracker.complete(success=False, error=error_msg)
                    return

                store_analysis_result(job_id, result)
                progress_tracker.complete(success=True)

            except Exception as e:
                progress_tracker.complete(success=False, error=str(e))

        # Run analysis in background thread
        thread = threading.Thread(target=run_analysis)
        thread.daemon = True
        thread.start()

        return jsonify({'success': True, 'job_id': job_id})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/progress/<job_id>')
def progress_handler(job_id: str):
    """Progress tracking endpoint using Server-Sent Events."""
    def event_stream():
        import time
        last_percent = -1
        while True:
            progress = get_progress(job_id)
            percent = progress.get("percent", 0)
            step = progress.get("step", "Starting...")
            done = progress.get("done", False)
            error = progress.get("error", None)

            if percent != last_percent or done or error:
                yield f"data: {json.dumps({'percent': percent, 'step': step, 'done': done, 'error': error})}\n\n"
                last_percent = percent

            if done or error:
                break

            time.sleep(0.5)

    return Response(event_stream(), mimetype="text/event-stream")


@app.route('/api/result/<job_id>')
def api_get_result(job_id: str):
    """Get analysis result for a job."""
    result = get_analysis_result(job_id)
    if not result:
        return jsonify({'success': False, 'error': 'Result not found'}), 404

    return jsonify({'success': True, 'result': result})


# =============================================================================
# EXPORT ROUTES
# =============================================================================

@app.route('/download')
def download():
    """Download generated reports."""
    try:
        format_type = request.args.get('format', 'excel').lower()
        job_id = request.args.get('job_id') or session.get('job_id')

        if not job_id:
            return jsonify({'error': 'No analysis session found'}), 400

        analysis_result = get_analysis_result(job_id)
        if not analysis_result:
            return jsonify({'error': 'No analysis data found'}), 400

        # TODO: Implement export
        return jsonify({'error': 'Export not yet implemented'}), 501

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_sectors():
    """Get all sector definitions."""
    from justdata.apps.electwatch.services.firm_mapper import get_mapper
    return get_mapper().get_all_sectors()


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error'}), 500


# Expose app for gunicorn/render
application = app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8083, debug=True)
