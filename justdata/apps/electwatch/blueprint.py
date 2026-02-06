"""
ElectWatch Blueprint for main JustData app.
Self-contained blueprint that works within the unified platform.
"""

from flask import Blueprint, render_template, jsonify, request
from pathlib import Path
from urllib.parse import unquote
import json
import logging
import threading

from justdata.main.auth import get_user_type, login_required, require_access, admin_required, staff_required

logger = logging.getLogger(__name__)

# Get directories
APP_DIR = Path(__file__).parent.absolute()
TEMPLATES_DIR = APP_DIR / 'templates'
STATIC_DIR = APP_DIR / 'static'

# Create blueprint
electwatch_bp = Blueprint(
    'electwatch',
    __name__,
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(STATIC_DIR),
    static_url_path='/electwatch/static'
)

# Import version
try:
    from justdata.apps.electwatch.version import __version__
except ImportError:
    __version__ = '0.9.0'


def _get_sectors():
    """
    Get dict of sectors for the dashboard with PAC contribution data.

    Returns sectors with:
    - officials_count: Number of officials with financial activity in that industry
    - total_contributions: Sum of stock trade amounts from that industry
    - pacs: List of PACs in that industry
    """
    # Import firm_mapper for sector definitions and PAC-to-industry mapping
    try:
        from justdata.apps.electwatch.services.firm_mapper import FINANCIAL_SECTORS, get_mapper
        from justdata.apps.electwatch.services.financial_pac_client import FINANCIAL_SECTOR_PACS
    except ImportError:
        FINANCIAL_SECTORS = {}
        FINANCIAL_SECTOR_PACS = {}
        get_mapper = None

    # Try to load industries.json for any pre-computed data
    data_file = APP_DIR / 'data' / 'current' / 'industries.json'
    industries_data = {}
    if data_file.exists():
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                industries_data = json.load(f)
        except Exception as e:
            print(f"Error loading industries.json: {e}")

    # Try to compute real stats from officials data
    officials_by_sector = {}
    contributions_by_sector = {}
    pacs_by_sector = {}

    # Initialize from FINANCIAL_SECTOR_PACS
    for pac_id, pac_info in FINANCIAL_SECTOR_PACS.items():
        sector = pac_info.get('sector', '')
        if sector:
            if sector not in pacs_by_sector:
                pacs_by_sector[sector] = []
            pacs_by_sector[sector].append(pac_info.get('name', 'Unknown'))

    # Try to load officials data to compute real stats
    officials_file = APP_DIR / 'data' / 'current' / 'officials.json'
    if officials_file.exists():
        try:
            with open(officials_file, 'r', encoding='utf-8') as f:
                officials_data = json.load(f)

            officials_list = officials_data.get('officials', [])
            mapper = get_mapper() if get_mapper else None

            for official in officials_list:
                # Check stock trades for sector involvement
                trades = official.get('trades', [])
                official_sectors = set()

                for trade in trades:
                    ticker = trade.get('ticker', '')
                    if mapper and ticker:
                        industries = mapper.get_industry_from_ticker(ticker)
                        official_sectors.update(industries)

                # Count this official for each sector they are involved with
                for sector in official_sectors:
                    if sector not in officials_by_sector:
                        officials_by_sector[sector] = set()
                    officials_by_sector[sector].add(official.get('name', ''))

                    # Add trade amounts to sector totals
                    if sector not in contributions_by_sector:
                        contributions_by_sector[sector] = 0
                    for trade in trades:
                        ticker = trade.get('ticker', '')
                        if mapper and ticker:
                            trade_industries = mapper.get_industry_from_ticker(ticker)
                            if sector in trade_industries:
                                # Use amount midpoint if available
                                amount_info = trade.get('amount', {})
                                if isinstance(amount_info, dict):
                                    min_amt = amount_info.get('min', 0)
                                    max_amt = amount_info.get('max', 0)
                                    contributions_by_sector[sector] += (min_amt + max_amt) / 2
                                elif isinstance(amount_info, (int, float)):
                                    contributions_by_sector[sector] += amount_info

        except Exception as e:
            print(f"Error computing sector stats from officials: {e}")

    # Build final sectors dict
    sectors = {}

    # Start with FINANCIAL_SECTORS definitions
    for code, info in FINANCIAL_SECTORS.items():
        # Get computed values or fall back to sample values
        computed_officials = len(officials_by_sector.get(code, set()))
        computed_total = contributions_by_sector.get(code, 0)

        # Use computed values if available, otherwise use sample values from FINANCIAL_SECTORS
        officials_count = computed_officials if computed_officials > 0 else info.get('sample_officials', 0)
        total_contributions = computed_total if computed_total > 0 else info.get('sample_total', 0)

        sectors[code] = {
            'name': info.get('name', code.replace('_', ' ').title()),
            'code': code,
            'description': info.get('description', ''),
            'sample_officials': officials_count,
            'sample_total': total_contributions,
            'officials_count': officials_count,
            'total_contributions': total_contributions,
            'pacs': pacs_by_sector.get(code, []),
            'color': info.get('color', '#6b7280')
        }

    # Merge any additional data from industries.json (like news)
    by_sector = industries_data.get('by_sector', {})
    for code in sectors:
        if code in by_sector:
            sectors[code]['news'] = by_sector[code].get('news', [])[:3]  # Limit to 3 news items

    return sectors



@electwatch_bp.route('/')
@login_required
def index():
    """Main dashboard page - leaderboard of officials by involvement."""
    user_type = get_user_type()
    is_staff = (user_type in ('staff', 'admin'))
    is_admin = (user_type == 'admin')
    breadcrumb_items = [{'name': 'ElectWatch', 'url': '/electwatch'}]
    return render_template(
        'electwatch_dashboard.html',
        version=__version__,
        sectors=_get_sectors(),
        is_staff=is_staff,
        is_admin=is_admin,
        app_name='ElectWatch',
        breadcrumb_items=breadcrumb_items
    )


@electwatch_bp.route('/official/<official_id>')
@login_required
@require_access('electwatch', 'full')
def official_profile(official_id):
    """Individual official profile page."""
    breadcrumb_items = [
        {'name': 'ElectWatch', 'url': '/electwatch'},
        {'name': 'Official Profile', 'url': f'/electwatch/official/{official_id}'}
    ]
    return render_template(
        'official_profile.html',
        version=__version__,
        official_id=official_id,
        app_name='ElectWatch',
        breadcrumb_items=breadcrumb_items
    )


@electwatch_bp.route('/firm/<firm_id>')
@login_required
@require_access('electwatch', 'full')
def firm_view(firm_id):
    """Firm view page."""
    # URL decode the firm_id to get the firm name
    firm_name = unquote(firm_id)
    breadcrumb_items = [
        {'name': 'ElectWatch', 'url': '/electwatch'},
        {'name': 'Firm', 'url': f'/electwatch/firm/{firm_id}'}
    ]
    return render_template(
        'firm_view.html',
        version=__version__,
        firm_name=firm_name,
        app_name='ElectWatch',
        breadcrumb_items=breadcrumb_items
    )


@electwatch_bp.route('/industry/<industry_code>')
@login_required
@require_access('electwatch', 'full')
def industry_view(industry_code):
    """Industry view page."""
    try:
        from justdata.apps.electwatch.services.firm_mapper import get_sector_info
        sector_info = get_sector_info(industry_code)
    except ImportError:
        sector_info = {'name': industry_code.replace('_', ' ').title(), 'code': industry_code}

    breadcrumb_items = [
        {'name': 'ElectWatch', 'url': '/electwatch'},
        {'name': 'Industry', 'url': f'/electwatch/industry/{industry_code}'}
    ]
    return render_template(
        'industry_view.html',
        version=__version__,
        sector=industry_code,
        sector_info=sector_info,
        app_name='ElectWatch',
        breadcrumb_items=breadcrumb_items
    )


@electwatch_bp.route('/committee/<committee_id>')
@login_required
@require_access('electwatch', 'full')
def committee_view(committee_id):
    """Committee view page."""
    breadcrumb_items = [
        {'name': 'ElectWatch', 'url': '/electwatch'},
        {'name': 'Committee', 'url': f'/electwatch/committee/{committee_id}'}
    ]
    return render_template(
        'committee_view.html',
        version=__version__,
        committee_id=committee_id,
        app_name='ElectWatch',
        breadcrumb_items=breadcrumb_items
    )


@electwatch_bp.route('/bill/<bill_id>')
@login_required
@require_access('electwatch', 'full')
def bill_view(bill_id):
    """Bill view page."""
    breadcrumb_items = [
        {'name': 'ElectWatch', 'url': '/electwatch'},
        {'name': 'Bill', 'url': f'/electwatch/bill/{bill_id}'}
    ]
    return render_template(
        'bill_view.html',
        version=__version__,
        bill_id=bill_id,
        app_name='ElectWatch',
        breadcrumb_items=breadcrumb_items
    )


# =============================================================================
# API ROUTES
# =============================================================================

@electwatch_bp.route('/api/officials')
@login_required
@require_access('electwatch', 'full')
def api_officials():
    """
    Officials API endpoint with filtering support.

    Query params:
        - chamber: 'house' or 'senate'
        - party: 'R', 'D', or 'I'
        - state: Two-letter state code
        - industry: Industry sector code
        - sort: 'score', 'total', 'contributions', 'trades'
        - limit: Number of results (default 100)
    """
    try:
        from justdata.apps.electwatch.services.data_store import get_officials

        # Get filter parameters
        chamber = request.args.get('chamber')
        party = request.args.get('party')
        state = request.args.get('state')
        industry = request.args.get('industry')
        sort_by = request.args.get('sort', 'score')
        limit = request.args.get('limit', 100, type=int)

        officials = get_officials()

        # Apply filters
        filtered = officials

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

        # Apply limit
        if limit:
            filtered = filtered[:limit]

        return jsonify({'success': True, 'officials': filtered})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@electwatch_bp.route('/api/official/<official_id>')
@login_required
@require_access('electwatch', 'full')
def api_official(official_id):
    """Single official API endpoint."""
    try:
        from justdata.apps.electwatch.services.data_store import get_official
        official = get_official(official_id)
        if official:
            return jsonify({'success': True, 'official': official})
        return jsonify({'success': False, 'error': 'Official not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@electwatch_bp.route('/api/official/<official_id>/trends')
@login_required
@require_access('electwatch', 'full')
def api_official_trends(official_id):
    """
    Get time-series trend data for a specific official.

    Returns quarterly aggregated data for trades and contributions,
    suitable for rendering trend charts.

    Response:
    {
        "success": true,
        "official_id": "ted_cruz",
        "name": "Ted Cruz",
        "trades_by_quarter": [
            {"quarter": "Q1 2024", "purchases": 50000, "sales": 25000, "net": 25000, "count": 5},
            ...
        ],
        "contributions_by_quarter": [
            {"quarter": "Q1 2024", "amount": 100000, "count": 10},
            ...
        ],
        "trade_trend": "increasing|decreasing|stable",
        "has_trend_data": true
    }
    """
    try:
        from justdata.apps.electwatch.services.data_store import (
            get_official, compute_official_trends
        )

        official = get_official(official_id)
        if not official:
            return jsonify({'success': False, 'error': 'Official not found'}), 404

        # Check if trend data was pre-computed during weekly update
        if official.get('trades_by_quarter'):
            return jsonify({
                'success': True,
                'official_id': official_id,
                'name': official.get('name', ''),
                'trades_by_quarter': official.get('trades_by_quarter', []),
                'contributions_by_quarter': official.get('contributions_by_quarter', []),
                'trade_trend': official.get('trade_trend', 'stable'),
                'has_trend_data': official.get('has_trend_data', False)
            })

        # Compute trends on-demand if not pre-computed
        trend_data = compute_official_trends(official)

        return jsonify({
            'success': True,
            'official_id': official_id,
            'name': official.get('name', ''),
            **trend_data
        })

    except Exception as e:
        logger.error(f"Error getting trends for {official_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@electwatch_bp.route('/api/firm/<firm_name>')
@login_required
@require_access('electwatch', 'full')
def api_firm(firm_name):
    """
    Single firm API endpoint.

    Returns detailed information for a specific firm including:
    - Connected officials (stock traders)
    - PAC contributions
    - Party split
    - Recent activity
    - News
    """
    from justdata.apps.electwatch.services.data_store import get_officials

    try:
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
                        'total': len(off.get('trades', [])) * 25000,
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
                    'total': len(officials) * 50000,
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
            logger.warning(f'Could not fetch live firm data: {e}')

        # Normalize firm name
        normalized = firm_name.lower().strip()

        # Try to get data from weekly data store
        try:
            from justdata.apps.electwatch.services.firm_mapper import FirmMapper, AmountRange
            all_officials = get_officials()

            # Get firm record to find associated PACs
            mapper = FirmMapper()
            firm_record = mapper.get_firm_from_name(firm_name)
            firm_pac_names = []
            if firm_record:
                firm_pac_names = [pac.upper() for pac in firm_record.pac_names]

            # Find officials who have traded this firm OR received PAC contributions
            firm_officials = []
            pac_contributions = []
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
                        break

                # If no firms data, check trades array for ticker match
                if not has_match and official.get('trades'):
                    for trade in official.get('trades', []):
                        if isinstance(trade, dict):
                            trade_ticker = trade.get('ticker', '').upper()
                            trade_company = trade.get('company', '').lower()
                        else:
                            trade_str = str(trade)
                            trade_ticker = ''
                            trade_company = ''
                            if 'ticker=' in trade_str:
                                trade_ticker = trade_str.split('ticker=')[1].split(';')[0].upper()
                            if 'company=' in trade_str:
                                trade_company = trade_str.split('company=')[1].split(';')[0].lower()

                        if trade_ticker == normalized.upper() or normalized.lower() in trade_company:
                            has_match = True
                            trade_type = ''
                            amount_range = ''
                            if isinstance(trade, dict):
                                trade_type = trade.get('type', '')
                                amount_range = trade.get('amount_range', '')

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
                firm_officials.sort(key=lambda x: x['total'], reverse=True)

                total_party = party_counts['r'] + party_counts['d']
                if total_party > 0:
                    party_split = {
                        'r': round(party_counts['r'] / total_party * 100),
                        'd': round(party_counts['d'] / total_party * 100)
                    }
                else:
                    party_split = {'r': 50, 'd': 50}

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
                        'contributions': total_pac_amount,
                        'stock_trades': total_amount,
                        'officials_count': len(firm_officials),
                        'party_split': party_split,
                        'r_amount': party_amounts['r'],
                        'd_amount': party_amounts['d'],
                        'officials': firm_officials[:20],
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
            logger.warning(f'Could not load firm data from store: {e}')

        # Try to get firm data directly from firms.json (built from trades)
        try:
            from justdata.apps.electwatch.services.data_store import get_firms
            all_firms = get_firms()

            # Search for firm by name or ticker
            matched_firm = None
            for f in all_firms:
                f_name = f.get('name', '').lower()
                f_ticker = f.get('ticker', '').upper()

                # Match by ticker (exact) or name (partial)
                if f_ticker == normalized.upper():
                    matched_firm = f
                    break
                elif normalized in f_name or f_name in normalized:
                    matched_firm = f
                    break

            if matched_firm:
                # Return data from firms.json (built from weekly update)
                officials = matched_firm.get('officials', [])
                return jsonify({
                    'success': True,
                    'firm': {
                        'name': matched_firm.get('name', firm_name),
                        'ticker': matched_firm.get('ticker'),
                        'industries': [matched_firm.get('sector', '')] if matched_firm.get('sector') else [],
                        'total': matched_firm.get('total', 0),
                        'contributions': 0,
                        'stock_trades': matched_firm.get('stock_trades', matched_firm.get('total', 0)),
                        'officials_count': len(officials),
                        'party_split': {'r': 50, 'd': 50},
                        'r_amount': 0,
                        'd_amount': 0,
                        'officials': [{
                            'id': o.get('id', ''),
                            'name': o.get('name', ''),
                            'party': o.get('party', ''),
                            'state': o.get('state', ''),
                            'chamber': o.get('chamber', 'house'),
                            'committee': '',
                            'total': 0,
                            'has_pac': False,
                            'has_stock': True,
                            'photo_url': o.get('photo_url')
                        } for o in officials[:20]],
                        'pac_contributions': [],
                        'activity': matched_firm.get('trades', [])[:10],
                        'sec_filings': matched_firm.get('sec_filings', []),
                        'insider_transactions': matched_firm.get('insider_transactions', []),
                        'regulatory_mentions': [],
                        'litigation': [],
                        'news': matched_firm.get('news', []),
                        'data_source': 'firms_json'
                    },
                    'data_source': 'firms_json'
                })
        except Exception as e:
            logger.warning(f'Could not load from firms.json: {e}')

        # Return default empty data for unknown firm
        return jsonify({
            'success': True,
            'firm': {
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
                'officials': [],
                'pac_contributions': [],
                'activity': [],
                'sec_filings': [],
                'regulatory_mentions': [],
                'litigation': [],
                'news': [],
                'data_source': 'empty'
            }
        })

    except Exception as e:
        logger.error(f'Error in api_firm: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500

@electwatch_bp.route('/api/firms')
@login_required
@require_access('electwatch', 'full')
def api_firms():
    """Firms API endpoint."""
    try:
        from justdata.apps.electwatch.services.data_store import get_firms_with_stats
        limit = request.args.get('limit', 100, type=int)
        firms = get_firms_with_stats()
        # Apply limit after fetching
        if limit:
            firms = firms[:limit]
        return jsonify({'success': True, 'firms': firms})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@electwatch_bp.route('/api/sectors')
@login_required
@require_access('electwatch', 'full')
def api_sectors():
    """Sectors API endpoint - returns industry sectors with stats."""
    sectors = _get_sectors()
    return jsonify({'success': True, 'sectors': sectors})




@electwatch_bp.route('/api/industry/<industry_code>')
@login_required
@require_access('electwatch', 'full')
def api_industry(industry_code):
    """
    Industry detail API endpoint.

    Returns comprehensive data for a specific industry/sector:
    - officials: List of officials with financial activity in this industry
    - firms: List of firms in this industry
    - total_amount: Total financial involvement (contributions + trades)
    - total_contributions: PAC contributions total
    - total_trades: Stock trades total
    - party_split: R/D contribution percentages
    - committees: Related congressional committees
    - legislation: Related legislation
    - news: Industry news
    """
    try:
        from justdata.apps.electwatch.services.data_store import get_officials, get_firms_with_stats, get_news
        from justdata.apps.electwatch.services.firm_mapper import (
            get_mapper, FINANCIAL_SECTORS, get_sector_info
        )

        sector_code = industry_code.lower()
        sector_info = get_sector_info(sector_code)

        if not sector_info:
            return jsonify({'success': False, 'error': f'Unknown industry: {industry_code}'}), 404

        mapper = get_mapper()
        officials = get_officials()
        all_firms = get_firms_with_stats()

        # Filter officials who have activity in this sector
        sector_officials = []
        party_totals = {'R': 0, 'D': 0, 'I': 0}
        total_contributions = 0
        total_trades = 0

        for official in officials:
            official_total = 0
            official_contributions = 0
            official_trades = 0

            # Check contributions
            contributions = official.get('contributions_list', []) or official.get('top_financial_pacs', [])
            for contrib in contributions:
                pac_name = contrib.get('pac_name', '') or contrib.get('source', '') or contrib.get('name', '')
                industries = mapper.get_industry_from_pac(pac_name)
                if sector_code in industries:
                    amount = contrib.get('amount', 0)
                    official_contributions += amount
                    official_total += amount

            # Check stock trades
            trades = official.get('trades', [])
            for trade in trades:
                ticker = trade.get('ticker', '')
                industries = mapper.get_industry_from_ticker(ticker)
                if sector_code in industries:
                    amount_info = trade.get('amount', {})
                    if isinstance(amount_info, dict):
                        min_amt = amount_info.get('min', 0)
                        max_amt = amount_info.get('max', 0)
                        midpoint = (min_amt + max_amt) / 2
                    elif isinstance(amount_info, (int, float)):
                        midpoint = amount_info
                    else:
                        midpoint = 0
                    official_trades += midpoint
                    official_total += midpoint

            if official_total > 0:
                party = official.get('party', 'I')
                party_totals[party] = party_totals.get(party, 0) + official_total
                total_contributions += official_contributions
                total_trades += official_trades

                sector_officials.append({
                    'id': official.get('id', ''),
                    'name': official.get('name', ''),
                    'party': party,
                    'chamber': official.get('chamber', 'house'),
                    'state': official.get('state', ''),
                    'total': official_total,
                    'contributions': official_contributions,
                    'trades': official_trades
                })

        # Sort officials by total (descending)
        sector_officials.sort(key=lambda x: x.get('total', 0), reverse=True)

        # Filter firms by industry
        sector_firms = []
        for firm in all_firms:
            firm_industry = firm.get('industry', '').lower()
            if firm_industry == sector_code:
                sector_firms.append({
                    'name': firm.get('name', ''),
                    'ticker': firm.get('ticker', ''),
                    'total': firm.get('total', 0),
                    'officials_count': firm.get('officials', 0),
                    'stock_trades': firm.get('stock_trades', 0)
                })

        # Sort firms by total (descending)
        sector_firms.sort(key=lambda x: x.get('total', 0), reverse=True)

        # Calculate party split percentages
        total_party = party_totals['R'] + party_totals['D'] + party_totals.get('I', 0)
        if total_party > 0:
            r_pct = round((party_totals['R'] / total_party) * 100)
            d_pct = round((party_totals['D'] / total_party) * 100)
        else:
            r_pct = 50
            d_pct = 50

        total_amount = total_contributions + total_trades

        # Get committees (static data for financial sectors)
        committees = _get_industry_committees(sector_code)

        # Get legislation (placeholder - could be enhanced with real data)
        legislation = _get_industry_legislation(sector_code)

        # Get news for this industry
        all_news = get_news()
        sector_keywords = sector_info.get('keywords', [])
        sector_name = sector_info.get('name', '').lower()

        industry_news = []
        for article in all_news[:50]:  # Check first 50 articles
            title = article.get('title', '').lower()
            # Check if any keyword matches
            if any(kw.lower() in title for kw in sector_keywords) or sector_name in title:
                industry_news.append({
                    'title': article.get('title', ''),
                    'source': article.get('source', ''),
                    'date': article.get('date', ''),
                    'url': article.get('url', '')
                })
                if len(industry_news) >= 5:
                    break

        return jsonify({
            'success': True,
            'sector': sector_code,
            'sector_info': sector_info,
            'officials': sector_officials,
            'firms': sector_firms,
            'total_amount': total_amount,
            'total_contributions': total_contributions,
            'total_trades': total_trades,
            'party_split': {'r': r_pct, 'd': d_pct},
            'committees': committees,
            'legislation': legislation,
            'news': industry_news
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


def _get_industry_committees(sector_code: str) -> list:
    """Get congressional committees relevant to an industry sector."""
    # Financial services committees
    financial_committees = [
        {
            'name': 'Financial Services',
            'chamber': 'House',
            'chair': 'French Hill (R-AR)',
            'industry_focus': 100 if sector_code in ['banking', 'mortgage', 'consumer_lending', 'fintech'] else 80
        },
        {
            'name': 'Banking, Housing, and Urban Affairs',
            'chamber': 'Senate',
            'chair': 'Tim Scott (R-SC)',
            'industry_focus': 100 if sector_code in ['banking', 'mortgage', 'consumer_lending'] else 75
        }
    ]

    # Add sector-specific committees
    if sector_code == 'crypto':
        financial_committees.append({
            'name': 'Agriculture',
            'chamber': 'House',
            'chair': 'Glenn Thompson (R-PA)',
            'industry_focus': 60  # CFTC jurisdiction over crypto derivatives
        })
    elif sector_code == 'insurance':
        financial_committees.append({
            'name': 'Commerce, Science, and Transportation',
            'chamber': 'Senate',
            'chair': 'Ted Cruz (R-TX)',
            'industry_focus': 40
        })
    elif sector_code == 'investment':
        financial_committees.append({
            'name': 'Ways and Means',
            'chamber': 'House',
            'chair': 'Jason Smith (R-MO)',
            'industry_focus': 50  # Tax implications
        })

    return financial_committees


def _get_industry_legislation(sector_code: str) -> list:
    """Get relevant legislation for an industry sector."""
    # Placeholder legislation data - in production, this would come from a legislative API
    legislation_map = {
        'banking': [
            {
                'bill_id': 'H.R. 4763',
                'title': 'Financial Innovation and Technology for the 21st Century Act',
                'status': 'Passed House',
                'sponsor': 'Rep. French Hill (R-AR)',
                'date': '2024-05-22'
            },
            {
                'bill_id': 'S. 2281',
                'title': 'Bank Merger Review Modernization Act',
                'status': 'In Committee',
                'sponsor': 'Sen. Elizabeth Warren (D-MA)',
                'date': '2024-03-15'
            }
        ],
        'crypto': [
            {
                'bill_id': 'H.R. 4763',
                'title': 'Financial Innovation and Technology for the 21st Century Act',
                'status': 'Passed House',
                'sponsor': 'Rep. French Hill (R-AR)',
                'date': '2024-05-22'
            },
            {
                'bill_id': 'S. 4760',
                'title': 'Responsible Financial Innovation Act',
                'status': 'In Committee',
                'sponsor': 'Sen. Cynthia Lummis (R-WY)',
                'date': '2024-07-12'
            }
        ],
        'mortgage': [
            {
                'bill_id': 'H.R. 2876',
                'title': 'Housing Finance Reform Act',
                'status': 'In Committee',
                'sponsor': 'Rep. Andy Barr (R-KY)',
                'date': '2024-04-18'
            }
        ],
        'insurance': [
            {
                'bill_id': 'H.R. 5491',
                'title': 'Insurance Data Protection Act',
                'status': 'In Committee',
                'sponsor': 'Rep. Ann Wagner (R-MO)',
                'date': '2024-06-20'
            }
        ],
        'consumer_lending': [
            {
                'bill_id': 'S. 3847',
                'title': 'Consumer Credit Protection Enhancement Act',
                'status': 'In Committee',
                'sponsor': 'Sen. Sherrod Brown (D-OH)',
                'date': '2024-02-28'
            }
        ],
        'investment': [
            {
                'bill_id': 'H.R. 6502',
                'title': 'Retail Investor Protection Act',
                'status': 'In Committee',
                'sponsor': 'Rep. Bill Huizenga (R-MI)',
                'date': '2024-08-05'
            }
        ],
        'fintech': [
            {
                'bill_id': 'H.R. 4763',
                'title': 'Financial Innovation and Technology for the 21st Century Act',
                'status': 'Passed House',
                'sponsor': 'Rep. French Hill (R-AR)',
                'date': '2024-05-22'
            }
        ],
        'payments': [
            {
                'bill_id': 'H.R. 4763',
                'title': 'Financial Innovation and Technology for the 21st Century Act',
                'status': 'Passed House',
                'sponsor': 'Rep. French Hill (R-AR)',
                'date': '2024-05-22'
            }
        ],
        'proptech': [
            {
                'bill_id': 'H.R. 2876',
                'title': 'Housing Finance Reform Act',
                'status': 'In Committee',
                'sponsor': 'Rep. Andy Barr (R-KY)',
                'date': '2024-04-18'
            }
        ]
    }

    return legislation_map.get(sector_code, [])


@electwatch_bp.route('/api/committees')
@login_required
@require_access('electwatch', 'full')
def api_committees():
    """Committees API endpoint."""
    try:
        from justdata.apps.electwatch.services.data_store import get_committees
        committees = get_committees()
        return jsonify(committees)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@electwatch_bp.route('/api/committee/<committee_id>')
@login_required
@require_access('electwatch', 'full')
def api_committee(committee_id):
    """Get detailed information for a specific committee."""
    try:
        from justdata.apps.electwatch.services.data_store import get_committee, get_officials

        # Normalize committee_id
        committee_id = committee_id.lower().replace(' ', '-')

        # Try to get committee from data store first
        committee_data = get_committee(committee_id)

        # Define committee details with member lists
        committees_detail = {
            'house-financial-services': {
                'id': 'house-financial-services',
                'name': 'Financial Services',
                'full_name': 'House Committee on Financial Services',
                'chamber': 'House',
                'chair': {'name': 'French Hill', 'party': 'R', 'state': 'AR', 'id': 'french_hill'},
                'ranking_member': {'name': 'Maxine Waters', 'party': 'D', 'state': 'CA', 'id': 'maxine_waters'},
                'jurisdiction': 'Banking, insurance, securities, housing, urban development',
                'members_count': 71,
                'total_contributions': 8500000,
                'total_stock_trades': 2100000,
                'party_split': {'r': 38, 'd': 33},
                'subcommittees': ['Capital Markets', 'Digital Assets', 'Financial Institutions', 'Housing and Insurance', 'National Security'],
                'members': [
                    {'name': 'French Hill', 'party': 'R', 'state': 'AR', 'role': 'Chair', 'id': 'french_hill'},
                    {'name': 'Maxine Waters', 'party': 'D', 'state': 'CA', 'role': 'Ranking Member', 'id': 'maxine_waters'},
                    {'name': 'Frank Lucas', 'party': 'R', 'state': 'OK', 'role': 'Member', 'id': 'frank_lucas'},
                    {'name': 'Bill Huizenga', 'party': 'R', 'state': 'MI', 'role': 'Member', 'id': 'bill_huizenga'},
                    {'name': 'Ann Wagner', 'party': 'R', 'state': 'MO', 'role': 'Member', 'id': 'ann_wagner'},
                    {'name': 'Andy Barr', 'party': 'R', 'state': 'KY', 'role': 'Member', 'id': 'andy_barr'},
                    {'name': 'Roger Williams', 'party': 'R', 'state': 'TX', 'role': 'Member', 'id': 'roger_williams'},
                    {'name': 'Nydia Velazquez', 'party': 'D', 'state': 'NY', 'role': 'Member', 'id': 'nydia_velazquez'},
                    {'name': 'Brad Sherman', 'party': 'D', 'state': 'CA', 'role': 'Member', 'id': 'brad_sherman'},
                    {'name': 'Gregory Meeks', 'party': 'D', 'state': 'NY', 'role': 'Member', 'id': 'gregory_meeks'},
                    {'name': 'David Scott', 'party': 'D', 'state': 'GA', 'role': 'Member', 'id': 'david_scott'},
                    {'name': 'Al Green', 'party': 'D', 'state': 'TX', 'role': 'Member', 'id': 'al_green'},
                ]
            },
            'senate-banking': {
                'id': 'senate-banking',
                'name': 'Banking',
                'full_name': 'Senate Committee on Banking, Housing, and Urban Affairs',
                'chamber': 'Senate',
                'chair': {'name': 'Tim Scott', 'party': 'R', 'state': 'SC', 'id': 'tim_scott'},
                'ranking_member': {'name': 'Elizabeth Warren', 'party': 'D', 'state': 'MA', 'id': 'elizabeth_warren'},
                'jurisdiction': 'Banking, financial institutions, housing, urban development',
                'members_count': 23,
                'total_contributions': 6200000,
                'total_stock_trades': 1800000,
                'party_split': {'r': 12, 'd': 11},
                'subcommittees': ['Financial Institutions', 'Housing', 'Securities', 'Economic Policy'],
                'members': [
                    {'name': 'Tim Scott', 'party': 'R', 'state': 'SC', 'role': 'Chair', 'id': 'tim_scott'},
                    {'name': 'Elizabeth Warren', 'party': 'D', 'state': 'MA', 'role': 'Ranking Member', 'id': 'elizabeth_warren'},
                    {'name': 'Mike Crapo', 'party': 'R', 'state': 'ID', 'role': 'Member', 'id': 'mike_crapo'},
                    {'name': 'Sherrod Brown', 'party': 'D', 'state': 'OH', 'role': 'Member', 'id': 'sherrod_brown'},
                    {'name': 'Thom Tillis', 'party': 'R', 'state': 'NC', 'role': 'Member', 'id': 'thom_tillis'},
                    {'name': 'Jack Reed', 'party': 'D', 'state': 'RI', 'role': 'Member', 'id': 'jack_reed'},
                    {'name': 'John Kennedy', 'party': 'R', 'state': 'LA', 'role': 'Member', 'id': 'john_kennedy'},
                    {'name': 'Mark Warner', 'party': 'D', 'state': 'VA', 'role': 'Member', 'id': 'mark_warner'},
                    {'name': 'Bill Hagerty', 'party': 'R', 'state': 'TN', 'role': 'Member', 'id': 'bill_hagerty'},
                    {'name': 'Catherine Cortez Masto', 'party': 'D', 'state': 'NV', 'role': 'Member', 'id': 'catherine_cortez_masto'},
                ]
            },
            'house-ways-means': {
                'id': 'house-ways-means',
                'name': 'Ways and Means',
                'full_name': 'House Committee on Ways and Means',
                'chamber': 'House',
                'chair': {'name': 'Jason Smith', 'party': 'R', 'state': 'MO', 'id': 'jason_smith'},
                'ranking_member': {'name': 'Richard Neal', 'party': 'D', 'state': 'MA', 'id': 'richard_neal'},
                'jurisdiction': 'Taxation, trade, Social Security, Medicare',
                'members_count': 42,
                'total_contributions': 7800000,
                'total_stock_trades': 1500000,
                'party_split': {'r': 25, 'd': 17},
                'subcommittees': ['Tax Policy', 'Trade', 'Social Security', 'Health', 'Oversight'],
                'members': [
                    {'name': 'Jason Smith', 'party': 'R', 'state': 'MO', 'role': 'Chair', 'id': 'jason_smith'},
                    {'name': 'Richard Neal', 'party': 'D', 'state': 'MA', 'role': 'Ranking Member', 'id': 'richard_neal'},
                    {'name': 'Vern Buchanan', 'party': 'R', 'state': 'FL', 'role': 'Member', 'id': 'vern_buchanan'},
                    {'name': 'Lloyd Doggett', 'party': 'D', 'state': 'TX', 'role': 'Member', 'id': 'lloyd_doggett'},
                    {'name': 'Adrian Smith', 'party': 'R', 'state': 'NE', 'role': 'Member', 'id': 'adrian_smith'},
                    {'name': 'Mike Kelly', 'party': 'R', 'state': 'PA', 'role': 'Member', 'id': 'mike_kelly'},
                    {'name': 'John Larson', 'party': 'D', 'state': 'CT', 'role': 'Member', 'id': 'john_larson'},
                    {'name': 'Earl Blumenauer', 'party': 'D', 'state': 'OR', 'role': 'Member', 'id': 'earl_blumenauer'},
                ]
            },
            'senate-finance': {
                'id': 'senate-finance',
                'name': 'Finance',
                'full_name': 'Senate Committee on Finance',
                'chamber': 'Senate',
                'chair': {'name': 'Mike Crapo', 'party': 'R', 'state': 'ID', 'id': 'mike_crapo'},
                'ranking_member': {'name': 'Ron Wyden', 'party': 'D', 'state': 'OR', 'id': 'ron_wyden'},
                'jurisdiction': 'Taxation, trade agreements, health programs, Social Security',
                'members_count': 28,
                'total_contributions': 9100000,
                'total_stock_trades': 2400000,
                'party_split': {'r': 15, 'd': 13},
                'subcommittees': ['Taxation and IRS Oversight', 'Health Care', 'International Trade', 'Social Security'],
                'members': [
                    {'name': 'Mike Crapo', 'party': 'R', 'state': 'ID', 'role': 'Chair', 'id': 'mike_crapo'},
                    {'name': 'Ron Wyden', 'party': 'D', 'state': 'OR', 'role': 'Ranking Member', 'id': 'ron_wyden'},
                    {'name': 'Chuck Grassley', 'party': 'R', 'state': 'IA', 'role': 'Member', 'id': 'chuck_grassley'},
                    {'name': 'Debbie Stabenow', 'party': 'D', 'state': 'MI', 'role': 'Member', 'id': 'debbie_stabenow'},
                    {'name': 'John Cornyn', 'party': 'R', 'state': 'TX', 'role': 'Member', 'id': 'john_cornyn'},
                    {'name': 'Maria Cantwell', 'party': 'D', 'state': 'WA', 'role': 'Member', 'id': 'maria_cantwell'},
                    {'name': 'John Thune', 'party': 'R', 'state': 'SD', 'role': 'Member', 'id': 'john_thune'},
                    {'name': 'Bob Menendez', 'party': 'D', 'state': 'NJ', 'role': 'Member', 'id': 'bob_menendez'},
                ]
            }
        }

        # Get committee detail or use data from store
        committee = committees_detail.get(committee_id)

        if not committee and committee_data:
            # Build from data store
            committee = {
                'id': committee_id,
                'name': committee_data.get('name', committee_id.replace('-', ' ').title()),
                'full_name': committee_data.get('full_name', ''),
                'chamber': committee_data.get('chamber', 'House' if 'house' in committee_id else 'Senate'),
                'chair': committee_data.get('chair', {}),
                'ranking_member': committee_data.get('ranking_member', {}),
                'jurisdiction': committee_data.get('jurisdiction', ''),
                'members_count': committee_data.get('members_count', 0),
                'total_contributions': committee_data.get('total_contributions', 0),
                'total_stock_trades': committee_data.get('total_stock_trades', 0),
                'party_split': committee_data.get('party_split', {'r': 0, 'd': 0}),
                'subcommittees': committee_data.get('subcommittees', []),
                'members': committee_data.get('members', [])
            }

        if not committee:
            return jsonify({'success': False, 'error': f'Committee not found: {committee_id}'}), 404

        # Enrich members with financial data from officials
        try:
            officials = get_officials()
            officials_by_name = {}
            for official in officials:
                name = official.get('name', '').lower()
                officials_by_name[name] = official

            enriched_members = []
            for member in committee.get('members', []):
                member_name = member.get('name', '').lower()
                official_data = officials_by_name.get(member_name, {})
                enriched_member = {
                    **member,
                    'contributions': official_data.get('contributions', member.get('contributions', 0)),
                    'stock_trades': official_data.get('stock_trades', member.get('stock_trades', 0)),
                    'stock_value': official_data.get('stock_value', member.get('stock_value', 0)),
                    'top_donors': official_data.get('top_donors', []),
                    'recent_trades': official_data.get('recent_trades', [])
                }
                enriched_members.append(enriched_member)

            committee['members'] = enriched_members
        except Exception:
            pass  # Keep original members if enrichment fails

        # Add sample votes
        committee['votes'] = [
            {
                'id': 'vote_1',
                'bill': 'H.R. 4763',
                'title': 'Financial Innovation and Technology for the 21st Century Act',
                'date': '2024-05-22',
                'result': 'Passed',
                'vote_count': {'yes': 279, 'no': 136}
            },
            {
                'id': 'vote_2',
                'bill': 'H.R. 5403',
                'title': 'CBDC Anti-Surveillance State Act',
                'date': '2024-05-23',
                'result': 'Passed',
                'vote_count': {'yes': 216, 'no': 192}
            },
            {
                'id': 'vote_3',
                'bill': 'S. 2281',
                'title': 'Bank Merger Review Modernization Act',
                'date': '2024-03-15',
                'result': 'In Committee',
                'vote_count': {'yes': 0, 'no': 0}
            }
        ]

        # Add sample legislation
        committee['legislation'] = [
            {
                'id': 'hr4763',
                'number': 'H.R. 4763',
                'title': 'Financial Innovation and Technology for the 21st Century Act',
                'sponsor': 'French Hill (R-AR)',
                'status': 'Passed House',
                'introduced': '2023-07-20',
                'summary': 'Establishes regulatory framework for digital assets and cryptocurrency markets.'
            },
            {
                'id': 'hr5403',
                'number': 'H.R. 5403',
                'title': 'CBDC Anti-Surveillance State Act',
                'sponsor': 'Tom Emmer (R-MN)',
                'status': 'Passed House',
                'introduced': '2023-09-12',
                'summary': 'Prohibits the Federal Reserve from issuing a central bank digital currency.'
            },
            {
                'id': 's2281',
                'number': 'S. 2281',
                'title': 'Bank Merger Review Modernization Act',
                'sponsor': 'Elizabeth Warren (D-MA)',
                'status': 'In Committee',
                'introduced': '2023-07-13',
                'summary': 'Updates standards for reviewing bank mergers and acquisitions.'
            }
        ]

        # Add news items
        try:
            from justdata.apps.electwatch.services.data_store import get_news
            news = get_news()
            committee['news'] = news[:5] if news else []
        except Exception:
            committee['news'] = [
                {
                    'title': f'{committee["name"]} Committee Advances Key Financial Legislation',
                    'date': '2025-01-10',
                    'source': 'Congressional Quarterly',
                    'summary': 'Committee moves forward with bipartisan financial reform package.'
                },
                {
                    'title': 'Hearing on Banking Sector Oversight Scheduled',
                    'date': '2025-01-08',
                    'source': 'Roll Call',
                    'summary': 'Committee to examine regulatory compliance and consumer protection.'
                }
            ]

        return jsonify({'success': True, 'committee': committee})

    except Exception as e:
        import traceback
        return jsonify({'success': False, 'error': str(e), 'traceback': traceback.format_exc()}), 500


@electwatch_bp.route('/api/freshness')
@login_required
@require_access('electwatch', 'full')
def api_freshness():
    """Data freshness API endpoint."""
    try:
        from justdata.apps.electwatch.services.data_store import get_freshness
        freshness = get_freshness()
        return jsonify(freshness)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@electwatch_bp.route('/api/trends/aggregate')
@login_required
@require_access('electwatch', 'full')
def api_aggregate_trends():
    """
    Get aggregate trend data across all officials for dashboard charts.

    Returns quarterly aggregated totals for all trading and contribution activity,
    plus breakdowns by party and chamber.

    Response:
    {
        "success": true,
        "total_trades_by_quarter": [...],
        "total_contributions_by_quarter": [...],
        "by_party": {"R": [...], "D": [...]},
        "by_chamber": {"house": [...], "senate": [...]}
    }
    """
    try:
        from collections import defaultdict
        from justdata.apps.electwatch.services.data_store import get_officials

        officials = get_officials()

        # Aggregate across all officials
        total_trades = defaultdict(lambda: {'purchases': 0, 'sales': 0, 'count': 0})
        total_contribs = defaultdict(lambda: {'amount': 0, 'count': 0})

        # By party and chamber breakdowns
        by_party_trades = {
            'R': defaultdict(lambda: {'purchases': 0, 'sales': 0, 'count': 0}),
            'D': defaultdict(lambda: {'purchases': 0, 'sales': 0, 'count': 0})
        }
        by_chamber_trades = {
            'house': defaultdict(lambda: {'purchases': 0, 'sales': 0, 'count': 0}),
            'senate': defaultdict(lambda: {'purchases': 0, 'sales': 0, 'count': 0})
        }

        for official in officials:
            party = official.get('party', '').upper()
            if party not in ('R', 'D'):
                party = 'R' if 'REP' in party else 'D' if 'DEM' in party else None

            chamber = official.get('chamber', '').lower()

            # Aggregate trades by quarter
            for q in official.get('trades_by_quarter', []):
                quarter = q.get('quarter', '')
                total_trades[quarter]['purchases'] += q.get('purchases', 0)
                total_trades[quarter]['sales'] += q.get('sales', 0)
                total_trades[quarter]['count'] += q.get('count', 0)

                if party and party in by_party_trades:
                    by_party_trades[party][quarter]['purchases'] += q.get('purchases', 0)
                    by_party_trades[party][quarter]['sales'] += q.get('sales', 0)
                    by_party_trades[party][quarter]['count'] += q.get('count', 0)

                if chamber in by_chamber_trades:
                    by_chamber_trades[chamber][quarter]['purchases'] += q.get('purchases', 0)
                    by_chamber_trades[chamber][quarter]['sales'] += q.get('sales', 0)
                    by_chamber_trades[chamber][quarter]['count'] += q.get('count', 0)

            # Aggregate contributions by quarter
            for q in official.get('contributions_by_quarter', []):
                quarter = q.get('quarter', '')
                total_contribs[quarter]['amount'] += q.get('amount', 0)
                total_contribs[quarter]['count'] += q.get('count', 0)

        # Convert to sorted lists
        def to_sorted_list(data_dict):
            result = []
            for quarter, data in sorted(data_dict.items(), key=lambda x: (
                int(x[0].split()[1]) if x[0] and len(x[0].split()) > 1 else 0,
                int(x[0][1]) if x[0] and len(x[0]) > 1 else 0
            )):
                result.append({'quarter': quarter, **data})
            return result

        return jsonify({
            'success': True,
            'total_trades_by_quarter': to_sorted_list(total_trades),
            'total_contributions_by_quarter': to_sorted_list(total_contribs),
            'by_party': {
                'R': to_sorted_list(by_party_trades['R']),
                'D': to_sorted_list(by_party_trades['D'])
            },
            'by_chamber': {
                'house': to_sorted_list(by_chamber_trades['house']),
                'senate': to_sorted_list(by_chamber_trades['senate'])
            }
        })

    except Exception as e:
        logger.error(f"Error getting aggregate trends: {e}")
        import traceback
        return jsonify({'success': False, 'error': str(e), 'traceback': traceback.format_exc()}), 500


@electwatch_bp.route('/api/insights')
@login_required
@require_access('electwatch', 'full')
def api_insights():
    """Insights API endpoint."""
    try:
        from justdata.apps.electwatch.services.data_store import get_insights
        insights = get_insights()
        return jsonify({"success": True, "insights": insights})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@electwatch_bp.route('/api/refresh-data', methods=['POST'])
@login_required
@staff_required
def api_refresh_data():
    """
    Trigger a refresh of the ElectWatch data store (staff/admin only).

    This runs the weekly update process to fetch fresh data from all sources.
    The update runs in a background thread to avoid blocking the request.
    """
    user_type = get_user_type()
    if user_type not in ('staff', 'admin'):
        return jsonify({
            'success': False,
            'error': 'Only staff/admin users can refresh data'
        }), 403

    try:
        # Run the weekly update in a background thread
        def run_update():
            try:
                from justdata.apps.electwatch.weekly_update import main as weekly_update_main
                logger.info("Starting ElectWatch data refresh (triggered by admin)")
                weekly_update_main()
                logger.info("ElectWatch data refresh completed successfully")
            except Exception as e:
                logger.error(f"ElectWatch data refresh failed: {e}")

        thread = threading.Thread(target=run_update, daemon=True)
        thread.start()

        return jsonify({
            'success': True,
            'message': 'Data refresh started. This may take several minutes to complete.',
            'status': 'in_progress'
        })
    except Exception as e:
        logger.error(f"Error starting data refresh: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@electwatch_bp.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'app': 'electwatch',
        'version': __version__
    })


# =============================================================================
# BILL SEARCH AND KEY BILLS API
# =============================================================================

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


@electwatch_bp.route('/api/bill/search')
@login_required
@require_access('electwatch', 'full')
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


@electwatch_bp.route('/api/key-bills')
@login_required
@require_access('electwatch', 'full')
def api_key_bills():
    """Get the list of key finance bills."""
    key_bills_file = APP_DIR / 'data' / 'current' / 'key_bills.json'
    if key_bills_file.exists():
        try:
            with open(key_bills_file, 'r', encoding='utf-8') as f:
                return jsonify(json.load(f))
        except Exception as e:
            logger.error(f"Error loading key_bills.json: {e}")
    return jsonify({'bills': []})


@electwatch_bp.route('/api/bill/save-key-bill', methods=['POST'])
@login_required
@staff_required
def api_save_key_bill():
    """Save a bill to the Key Finance Bills list (staff/admin only)."""
    from datetime import datetime

    user_type = get_user_type()
    if user_type not in ('staff', 'admin'):
        return jsonify({'success': False, 'error': 'Only staff/admin can save key bills'}), 403

    data = request.get_json()
    bill_id = data.get('bill_id')
    bill_title = data.get('title')
    bill_summary = data.get('summary', '')

    if not bill_id:
        return jsonify({'success': False, 'error': 'Bill ID required'}), 400

    # Ensure data directory exists
    data_dir = APP_DIR / 'data' / 'current'
    data_dir.mkdir(parents=True, exist_ok=True)

    # Load existing key bills
    key_bills_file = data_dir / 'key_bills.json'
    key_bills = []
    if key_bills_file.exists():
        try:
            with open(key_bills_file, 'r', encoding='utf-8') as f:
                key_bills = json.load(f).get('bills', [])
        except Exception as e:
            logger.warning(f"Could not load existing key_bills.json: {e}")

    # Check if already saved
    if any(b['id'] == bill_id for b in key_bills):
        return jsonify({'success': False, 'error': 'Bill already in key bills list'})

    # Add to list
    key_bills.append({
        'id': bill_id,
        'title': bill_title,
        'summary': bill_summary[:500] if bill_summary else '',  # Truncate summary
        'added_by': user_type,
        'added_at': datetime.now().isoformat()
    })

    # Save
    try:
        with open(key_bills_file, 'w', encoding='utf-8') as f:
            json.dump({'bills': key_bills, 'updated_at': datetime.now().isoformat()}, f, indent=2)
        return jsonify({'success': True, 'message': f'Bill {bill_id} added to Key Finance Bills'})
    except Exception as e:
        logger.error(f"Error saving key_bills.json: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@electwatch_bp.route('/api/bill/remove-key-bill', methods=['POST'])
@login_required
@staff_required
def api_remove_key_bill():
    """Remove a bill from the Key Finance Bills list (staff/admin only)."""
    from datetime import datetime

    user_type = get_user_type()
    if user_type not in ('staff', 'admin'):
        return jsonify({'success': False, 'error': 'Only staff/admin can remove key bills'}), 403

    data = request.get_json()
    bill_id = data.get('bill_id')

    key_bills_file = APP_DIR / 'data' / 'current' / 'key_bills.json'
    if not key_bills_file.exists():
        return jsonify({'success': False, 'error': 'No key bills file'})

    try:
        with open(key_bills_file, 'r', encoding='utf-8') as f:
            key_bills = json.load(f).get('bills', [])

        key_bills = [b for b in key_bills if b['id'] != bill_id]

        with open(key_bills_file, 'w', encoding='utf-8') as f:
            json.dump({'bills': key_bills, 'updated_at': datetime.now().isoformat()}, f, indent=2)

        return jsonify({'success': True, 'message': f'Bill {bill_id} removed from Key Finance Bills'})
    except Exception as e:
        logger.error(f"Error removing key bill: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# =============================================================================
# ADMIN MAPPING API ROUTES
# =============================================================================

@electwatch_bp.route('/api/admin/mappings/officials')
@login_required
@admin_required
def api_admin_get_official_merges():
    """Get all official merge mappings (admin only)."""

    from justdata.apps.electwatch.services.mapping_store import get_official_merges
    return jsonify({'merges': get_official_merges()})


@electwatch_bp.route('/api/admin/mappings/officials/merge', methods=['POST'])
@login_required
@admin_required
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


@electwatch_bp.route('/api/admin/mappings/officials/unmerge', methods=['POST'])
@login_required
@admin_required
def api_admin_unmerge_official():
    """Remove an alias from a canonical official (admin only)."""

    data = request.get_json()
    canonical = data.get('canonical')
    alias = data.get('alias')

    from justdata.apps.electwatch.services.mapping_store import remove_official_alias
    result = remove_official_alias(canonical, alias)
    return jsonify(result)


@electwatch_bp.route('/api/admin/mappings/officials/delete', methods=['POST'])
@login_required
@admin_required
def api_admin_delete_official_merge():
    """Delete all aliases for a canonical official (admin only)."""

    data = request.get_json()
    canonical = data.get('canonical')

    from justdata.apps.electwatch.services.mapping_store import delete_official_merge
    result = delete_official_merge(canonical)
    return jsonify(result)


@electwatch_bp.route('/api/admin/mappings/officials/potential-duplicates')
@login_required
@staff_required
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


@electwatch_bp.route('/api/admin/mappings/officials/mark-distinct', methods=['POST'])
@login_required
@staff_required
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


@electwatch_bp.route('/api/admin/mappings/firms')
@login_required
@admin_required
def api_admin_get_firms():
    """Get custom firm definitions (admin only)."""

    from justdata.apps.electwatch.services.mapping_store import get_custom_firms
    return jsonify({'firms': get_custom_firms()})


@electwatch_bp.route('/api/admin/mappings/firms/all')
@login_required
@admin_required
def api_admin_get_all_firms():
    """Get all firms (built-in + custom) for dropdown (admin only)."""

    from justdata.apps.electwatch.services.mapping_store import get_all_firms
    return jsonify({'firms': get_all_firms()})


@electwatch_bp.route('/api/admin/mappings/firms', methods=['POST'])
@login_required
@admin_required
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


@electwatch_bp.route('/api/admin/mappings/firms/delete', methods=['POST'])
@login_required
@admin_required
def api_admin_delete_firm():
    """Delete a custom firm (admin only)."""

    data = request.get_json()
    name = data.get('name')

    from justdata.apps.electwatch.services.mapping_store import delete_custom_firm
    result = delete_custom_firm(name)
    return jsonify(result)


@electwatch_bp.route('/api/admin/mappings/firms/<firm_id>/aliases')
@login_required
@admin_required
def api_admin_get_firm_aliases(firm_id):
    """Get employer aliases for a firm (admin only)."""

    from justdata.apps.electwatch.services.mapping_store import get_firm_employer_aliases
    return jsonify({'aliases': get_firm_employer_aliases(firm_id)})


@electwatch_bp.route('/api/admin/mappings/employers', methods=['POST'])
@login_required
@admin_required
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


@electwatch_bp.route('/api/admin/mappings/employers/delete', methods=['POST'])
@login_required
@admin_required
def api_admin_remove_employer_alias():
    """Remove an employer alias from a firm (admin only)."""

    data = request.get_json()
    firm_id = data.get('firm_id')
    employer_name = data.get('employer_name')

    from justdata.apps.electwatch.services.mapping_store import remove_employer_alias
    result = remove_employer_alias(firm_id, employer_name)
    return jsonify(result)


@electwatch_bp.route('/api/admin/employers/unmatched')
@login_required
@admin_required
def api_admin_get_unmatched_employers():
    """Get unmatched employers from FEC data (admin only)."""

    limit = request.args.get('limit', 50, type=int)

    from justdata.apps.electwatch.services.mapping_store import get_unmatched_employers
    return jsonify({'employers': get_unmatched_employers(limit)})


@electwatch_bp.route('/api/admin/employers/search')
@login_required
@admin_required
def api_admin_search_employers():
    """Search for employer names in FEC data (admin only)."""

    query = request.args.get('q', '')
    limit = request.args.get('limit', 20, type=int)

    from justdata.apps.electwatch.services.mapping_store import search_employers
    return jsonify({'employers': search_employers(query, limit)})


@electwatch_bp.route('/api/admin/unmatched/pacs')
@login_required
@admin_required
def api_admin_get_unmatched_pacs():
    """Get unmatched PAC names that couldn't be mapped to companies (admin only)."""

    from justdata.apps.electwatch.services.mapping_store import get_unmatched_pacs
    return jsonify({'pacs': get_unmatched_pacs()})


@electwatch_bp.route('/api/admin/unmatched/tickers')
@login_required
@admin_required
def api_admin_get_unmatched_tickers():
    """Get stock tickers that haven't been categorized into an industry (admin only)."""

    from justdata.apps.electwatch.services.mapping_store import get_uncategorized_tickers
    return jsonify({'tickers': get_uncategorized_tickers()})
