"""Industry / sector / committee-overview route handlers.

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

def api_sectors():
    """Sectors API endpoint - returns industry sectors with stats."""
    sectors = _get_sectors()
    return jsonify({'success': True, 'sectors': sectors})

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

