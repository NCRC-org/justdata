"""Committee-related route handlers.

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

# Import version
try:
    from justdata.apps.electwatch.version import __version__
except ImportError:
    __version__ = '0.9.0'

logger = logging.getLogger(__name__)


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

def api_committees():
    """Committees API endpoint."""
    try:
        from justdata.apps.electwatch.services.data_store import get_committees
        committees = get_committees()
        return jsonify(committees)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

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

