"""Firm-related route handlers (list / detail / view).

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

