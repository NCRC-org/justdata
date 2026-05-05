"""Financial performance section."""
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from justdata.apps.lenderprofile.report_builder.helpers import (
    _calculate_growth,
    _format_currency,
)

def build_financial_performance(institution_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build financial performance section from FDIC call reports.
    Focus on trends and key metrics relevant to decision-makers.
    """
    financial = institution_data.get('financial', {})
    fdic_reports = financial.get('fdic_call_reports', [])

    if not fdic_reports:
        return _build_financial_from_sec_xbrl(institution_data)

    # Latest metrics
    latest = fdic_reports[0]

    # Calculate key ratios and metrics
    # FDIC reports dollar amounts in thousands - multiply by 1000
    metrics = {
        'total_assets': latest.get('ASSET', 0) * 1000,
        'total_deposits': latest.get('DEP', 0) * 1000,
        'total_loans': latest.get('LNLSNET', 0) * 1000,
        'net_income': latest.get('NETINC', 0) * 1000,
        'roa': latest.get('ROA', 0),  # Percentage - don't multiply
        'roe': latest.get('ROE', 0),  # Percentage - don't multiply
        'tier1_capital_ratio': latest.get('RBCT1J', 0),  # Percentage
        'npa_ratio': latest.get('NPAASSET', 0),  # Percentage - Non-performing assets ratio
        'efficiency_ratio': latest.get('EEFFR', 0)  # Percentage
    }

    # Build trend data (last 20 quarters = 5 years)
    trends = []
    for report in fdic_reports[:20]:
        # REPDTE is YYYYMMDD format (e.g., 20250930), convert to YYYY-MM for JS Date parsing
        repdte = report.get('REPDTE', '')
        if repdte and len(repdte) >= 6:
            period = f"{repdte[:4]}-{repdte[4:6]}"  # Convert 20250930 to 2025-09
        else:
            period = ''
        trends.append({
            'period': period,
            'assets': report.get('ASSET', 0) * 1000,  # FDIC reports in thousands
            'deposits': report.get('DEP', 0) * 1000,
            'net_income': report.get('NETINC', 0) * 1000,
            'roa': report.get('ROA', 0)
        })

    # Reverse for chronological order (oldest to newest for charts)
    trends_chronological = list(reversed(trends))

    # Calculate growth rates
    if len(fdic_reports) >= 5:
        oldest = fdic_reports[4]  # ~1 year ago
        newest = fdic_reports[0]

        asset_growth = _calculate_growth(newest.get('ASSET', 0), oldest.get('ASSET', 0))
        deposit_growth = _calculate_growth(newest.get('DEP', 0), oldest.get('DEP', 0))
        loan_growth = _calculate_growth(newest.get('LNLSNET', 0), oldest.get('LNLSNET', 0))
    else:
        asset_growth = deposit_growth = loan_growth = None

    return {
        'metrics': metrics,
        'trends': trends,
        'trends_chronological': trends_chronological,  # For line chart (oldest to newest)
        'growth': {
            'asset_growth_yoy': asset_growth,
            'deposit_growth_yoy': deposit_growth,
            'loan_growth_yoy': loan_growth
        },
        'formatted': {
            'total_assets': _format_currency(metrics['total_assets']),
            'total_deposits': _format_currency(metrics['total_deposits']),
            'net_income': _format_currency(metrics['net_income']),
            'roa': f"{metrics['roa']:.2f}%" if metrics['roa'] else '--',
            'roe': f"{metrics['roe']:.2f}%" if metrics['roe'] else '--',
            'tier1': f"{metrics['tier1_capital_ratio']:.2f}%" if metrics['tier1_capital_ratio'] else '--'
        },
        'has_data': True
    }



def _build_financial_from_sec_xbrl(institution_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build financial performance from SEC XBRL data when FDIC data is unavailable.
    Used for holding companies that file with SEC but aren't in FDIC database.
    """
    sec_parsed = institution_data.get('sec_parsed', {})
    xbrl_data = sec_parsed.get('xbrl_data', {}) if sec_parsed else {}
    core_financials = xbrl_data.get('core_financials', {})
    bank_metrics = xbrl_data.get('bank_metrics', {})

    # Check if we have XBRL financial data
    has_xbrl = bool(core_financials.get('assets') or bank_metrics.get('deposits'))

    if not has_xbrl:
        return {'has_data': False}

    # Extract values from XBRL data
    assets_data = core_financials.get('assets', {})
    deposits_data = bank_metrics.get('deposits', {})
    net_income_data = core_financials.get('net_income', {})
    equity_data = core_financials.get('stockholders_equity', {})
    loans_data = bank_metrics.get('loans_net', {})

    # Get latest values (XBRL returns {value, unit, period, filed})
    total_assets = assets_data.get('value', 0) if isinstance(assets_data, dict) else (assets_data or 0)
    total_deposits = deposits_data.get('value', 0) if isinstance(deposits_data, dict) else (deposits_data or 0)
    net_income = net_income_data.get('value', 0) if isinstance(net_income_data, dict) else (net_income_data or 0)
    equity = equity_data.get('value', 0) if isinstance(equity_data, dict) else (equity_data or 0)
    loans = loans_data.get('value', 0) if isinstance(loans_data, dict) else (loans_data or 0)

    # Calculate ratios (avoid division by zero)
    roa = (net_income / total_assets * 100) if total_assets and net_income else 0
    roe = (net_income / equity * 100) if equity and net_income else 0

    metrics = {
        'total_assets': total_assets,
        'total_deposits': total_deposits,
        'total_loans': loans,
        'net_income': net_income,
        'roa': round(roa, 2) if roa else 0,
        'roe': round(roe, 2) if roe else 0,
        'tier1_capital_ratio': 0,
    }

    return {
        'metrics': metrics,
        'trends': [],
        'growth': {
            'asset_growth_yoy': None,
            'deposit_growth_yoy': None,
            'loan_growth_yoy': None
        },
        'formatted': {
            'total_assets': _format_currency(metrics['total_assets']),
            'total_deposits': _format_currency(metrics['total_deposits']),
            'net_income': _format_currency(metrics['net_income']),
            'roa': f"{metrics['roa']:.2f}%" if metrics['roa'] else '--',
            'roe': f"{metrics['roe']:.2f}%" if metrics['roe'] else '--',
            'tier1': '--'
        },
        'has_data': True,
        'data_source': 'SEC XBRL'
    }


