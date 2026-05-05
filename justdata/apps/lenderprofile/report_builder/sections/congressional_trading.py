"""Congressional trading section."""
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from justdata.apps.lenderprofile.report_builder.helpers import _format_currency

def build_congressional_trading(
    congressional_data: Dict[str, Any],
    ticker: str,
    ai_sentiment_summary: str = ""
) -> Dict[str, Any]:
    """
    Build congressional trading section from STOCK Act disclosure data.

    Shows politicians who have bought/sold this stock.

    Args:
        congressional_data: Congressional trading data
        ticker: Stock ticker symbol
        ai_sentiment_summary: AI-generated sentiment summary (2-3 sentences)
    """
    if not congressional_data or not congressional_data.get('has_data'):
        return {
            'has_data': False,
            'total_trades': 0,
            'recent_trades': [],
            'message': 'No congressional trading data available.',
            'ai_sentiment_summary': ''
        }

    trades = congressional_data.get('recent_trades', [])

    # Format trades
    formatted_trades = []
    for trade in trades[:15]:  # Show last 15
        formatted_trades.append({
            'politician_name': trade.get('politician_name', 'Unknown'),
            'position': trade.get('position', ''),
            'transaction_date': trade.get('transaction_date', ''),
            'transaction_type': trade.get('transaction_type', '').lower(),
            'amount_range': trade.get('amount_range', ''),
            'is_buy': trade.get('transaction_type', '').lower() == 'purchase'
        })

    # Summary stats
    total_purchases = congressional_data.get('total_purchases', 0)
    total_sales = congressional_data.get('total_sales', 0)

    # Get politician profiles with status and committees
    politician_profiles = congressional_data.get('politician_profiles', [])

    return {
        'has_data': True,
        'ticker': ticker,
        'total_trades': congressional_data.get('total_trades', 0),
        'total_purchases': total_purchases,
        'total_sales': total_sales,
        'buy_sell_ratio': f"{total_purchases}:{total_sales}",
        'unique_politicians': congressional_data.get('unique_politicians', 0),
        'sentiment': congressional_data.get('sentiment', 'Mixed'),
        'position_summary': congressional_data.get('position_summary', ''),
        'ai_sentiment_summary': ai_sentiment_summary,  # AI-generated bullish/bearish summary
        'recent_trades': formatted_trades,
        'top_buyers': congressional_data.get('top_buyers', [])[:5],
        'recent_buyers': congressional_data.get('recent_buyers', [])[:5],
        'recent_sellers': congressional_data.get('recent_sellers', [])[:5],
        'politician_profiles': politician_profiles,
        'accumulators': congressional_data.get('accumulators', []),
        'holders': congressional_data.get('holders', []),
        'divesters': congressional_data.get('divesters', []),
        'finance_committee_traders': congressional_data.get('finance_committee_traders', []),
        'notable_traders': congressional_data.get('notable_traders', [])[:5],
        'date_range': congressional_data.get('date_range', ''),
        'data_source': congressional_data.get('data_source', 'STOCK Act Data'),
    }


