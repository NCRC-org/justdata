#!/usr/bin/env python3
"""
Section Builders V2 for LenderProfile Intelligence Report
Two-column layout focused on decision-maker intelligence.

Left Column: Strategy & Business, Financial Performance, M&A Activity, Regulatory Risk
Right Column: Leadership & Compensation, Congressional Trading, Corporate Structure, News
Full Width: AI Intelligence Summary

Focus areas:
- SEC 10-K: Strategy, profit areas, growth/contraction expectations
- Leadership: CEO/executives, compensation, recent changes
- Congressional trading activity
- M&A activity (pending/historical)
- Regulatory issues/enforcement
- News and developments
"""

import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)


def _verify_executive_names_with_ai(
    executives: List[Dict[str, Any]],
    institution_name: str
) -> List[Dict[str, Any]]:
    """
    Use AI to verify and correct executive names that appear incomplete.

    Some iXBRL filings only contain first names (e.g., "Jay" instead of "Jay Farner").
    This function uses AI to identify and correct incomplete names.

    Args:
        executives: List of executive dicts with name, title, compensation
        institution_name: Company name for context

    Returns:
        List of executives with corrected names
    """
    # Check if any executives have incomplete names (single word, no spaces)
    incomplete_names = [e for e in executives if e.get('name') and ' ' not in e.get('name', '').strip()]

    if not incomplete_names:
        # All names appear complete, no AI verification needed
        return executives

    logger.info(f"Found {len(incomplete_names)} potentially incomplete executive names, using AI to verify")

    try:
        from shared.analysis.ai_provider import ask_ai

        # Build prompt with executive data
        exec_list = []
        for e in executives:
            exec_list.append({
                'name': e.get('name', ''),
                'title': e.get('title', ''),
                'compensation': e.get('total', 0)
            })

        prompt = f"""You are verifying executive names for {institution_name}.

The following executives were extracted from SEC filings, but some names may be incomplete (first name only):

{json.dumps(exec_list, indent=2)}

For each executive, provide the FULL NAME if you know it. Use your knowledge of {institution_name}'s leadership.

Return ONLY a JSON array with corrected names in this exact format:
[
    {{"original_name": "Jay", "full_name": "Jay Farner", "title": "CEO"}},
    {{"original_name": "Bill", "full_name": "Bill Emerson", "title": "Vice Chairman"}}
]

If you don't know an executive's full name, use the original name.
Return ONLY valid JSON, no markdown or explanation."""

        response = ask_ai(
            prompt,
            model="claude-3-5-haiku-20241022",
            max_tokens=1000,
            temperature=0
        )

        # Parse AI response
        # Clean response of markdown if present
        clean_response = response.strip()
        if clean_response.startswith('```'):
            clean_response = re.sub(r'^```(?:json)?\s*', '', clean_response)
            clean_response = re.sub(r'\s*```$', '', clean_response)

        corrections = json.loads(clean_response)

        # Build correction map
        name_corrections = {}
        for correction in corrections:
            original = correction.get('original_name', '').lower().strip()
            full_name = correction.get('full_name', '')
            if original and full_name and original != full_name.lower():
                name_corrections[original] = full_name

        if name_corrections:
            logger.info(f"AI corrected {len(name_corrections)} executive names: {name_corrections}")

        # Apply corrections
        corrected_executives = []
        for exec in executives:
            exec_copy = exec.copy()
            original_name = exec.get('name', '').strip()
            original_lower = original_name.lower()

            if original_lower in name_corrections:
                exec_copy['name'] = name_corrections[original_lower]
                logger.debug(f"Corrected '{original_name}' to '{exec_copy['name']}'")

            corrected_executives.append(exec_copy)

        return corrected_executives

    except Exception as e:
        logger.warning(f"AI executive name verification failed: {e}")
        return executives  # Return original on error


# =============================================================================
# HEADER / INSTITUTION SUMMARY
# =============================================================================

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


# =============================================================================
# LEFT COLUMN: STRATEGY, FINANCIALS, M&A, REGULATORY
# =============================================================================

def build_business_strategy(
    institution_data: Dict[str, Any],
    sec_parsed: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build business strategy section from SEC 10-K Item 1 and Item 7.

    Extracts:
    - Business description and segments
    - Strategic priorities
    - Growth areas and expansion plans
    - Contraction or exit areas
    """
    sec_data = institution_data.get('sec', {})

    # Get parsed SEC data
    if not sec_parsed:
        sec_parsed = sec_data.get('parsed', {})

    sections = sec_parsed.get('sections', {}) if sec_parsed else {}

    # Item 1: Business Description
    item1 = sections.get('item1_business', '')

    # Item 7: Management's Discussion & Analysis
    item7 = sections.get('item7_mda', '')

    # Extract key themes (code-based extraction)
    business_segments = _extract_business_segments(item1)
    strategic_priorities = _extract_strategic_priorities(item7)
    growth_areas = _extract_growth_areas(item7)
    contraction_areas = _extract_contraction_areas(item7)

    return {
        'business_description': _truncate_text(item1, 2000),
        'business_segments': business_segments,
        'strategic_priorities': strategic_priorities,
        'growth_areas': growth_areas,
        'contraction_areas': contraction_areas,
        'mda_highlights': _truncate_text(item7, 2000),
        'has_data': bool(item1 or item7)
    }


def build_risk_factors(
    institution_data: Dict[str, Any],
    sec_parsed: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build risk factors section from SEC 10-K Item 1A.
    """
    sec_data = institution_data.get('sec', {})

    if not sec_parsed:
        sec_parsed = sec_data.get('parsed', {})

    sections = sec_parsed.get('sections', {}) if sec_parsed else {}
    item1a = sections.get('item1a_risks', '')

    # Extract categorized risks
    risk_categories = _categorize_risks(item1a)

    return {
        'risk_text': _truncate_text(item1a, 3000),
        'risk_categories': risk_categories,
        'has_data': bool(item1a)
    }


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


def build_merger_activity(institution_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build M&A activity section.

    Includes:
    - Pending acquisitions (from 8-K filings or news)
    - Historical acquisitions (from SEC 10-K)
    - Expected branch changes
    """
    merger_data = institution_data.get('mergers', {})
    sec_data = institution_data.get('sec', {})
    sec_parsed = institution_data.get('sec_parsed', {})

    # Historical acquisitions from SEC 10-K
    historical = sec_parsed.get('business_combinations', []) if sec_parsed else []

    # Pending from merger data (8-K filings, news, etc.)
    pending = merger_data.get('pending', [])

    # Format pending acquisitions for display
    formatted_pending = []
    for item in pending:
        formatted_pending.append({
            'date': item.get('date', ''),
            'target': item.get('target', item.get('description', '')),
            'description': item.get('description', ''),
            'url': item.get('url', '')
        })

    return {
        'pending_acquisitions': formatted_pending,
        'historical_acquisitions': historical,
        'total_pending': len(formatted_pending),
        'total_historical': len(historical),
        'expected_branch_changes': merger_data.get('expected_closures', []),
        'has_pending': len(formatted_pending) > 0,
        'has_data': bool(formatted_pending or historical)
    }


def build_regulatory_risk(institution_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build regulatory risk section.

    Includes:
    - Enforcement actions
    - Consumer complaints summary
    - CRA rating and history
    """
    enforcement = institution_data.get('enforcement', {})
    cfpb_complaints = institution_data.get('cfpb_complaints', {})
    cra_data = institution_data.get('cra', {})

    # Enforcement actions
    actions = enforcement.get('actions', [])
    recent_actions = [a for a in actions if _is_recent(a.get('date'), years=3)]

    # Complaints
    complaint_total = cfpb_complaints.get('total', 0)
    complaint_trends = cfpb_complaints.get('trends', {})
    main_issues = cfpb_complaints.get('main_topics', [])[:5]
    main_products = cfpb_complaints.get('main_products', [])[:5]  # Top 5 product categories
    cfpb_company_name = cfpb_complaints.get('cfpb_company_name', '')

    # CRA
    cra_rating = cra_data.get('current_rating', '--')
    cra_exam_date = cra_data.get('exam_date')
    cra_history = cra_data.get('rating_history', [])

    return {
        'enforcement': {
            'total_actions': len(actions),
            'recent_actions': recent_actions,
            'recent_count': len(recent_actions)
        },
        'complaints': {
            'total': complaint_total,
            'trend': complaint_trends.get('recent_trend', 'stable'),
            'main_issues': main_issues,
            'main_categories': main_products,  # Top 5 product categories
            'by_year': complaint_trends.get('by_year', {}),
            'cfpb_company_name': cfpb_company_name,
            'latest_complaint_date': cfpb_complaints.get('latest_complaint_date'),
            # Multi-year data for trend charts
            'national_by_year': cfpb_complaints.get('national_by_year', {}),
            'categories_by_year': cfpb_complaints.get('categories_by_year', {})
        },
        'cra': {
            'current_rating': cra_rating,
            'exam_date': cra_exam_date,
            'history': cra_history[:5]
        },
        'has_data': bool(actions or complaint_total > 0 or cra_rating != '--')
    }


def build_community_investment(
    institution_data: Dict[str, Any],
    sec_parsed: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build community investment section from SEC 10-K data and XBRL API.

    Includes:
    - CRA rating and performance
    - Community development loans and investments
    - Affordable housing tax credits (from XBRL)
    - Charitable contributions and philanthropy
    - Community commitments (affordable housing, minority lending, etc.)

    Args:
        institution_data: Complete institution data
        sec_parsed: Parsed SEC 10-K data (may include merged XBRL data)

    Returns:
        Dictionary with community investment metrics
    """
    # Get community investment data from SEC parsing
    if not sec_parsed:
        sec_parsed = institution_data.get('sec_parsed', {})

    community_data = sec_parsed.get('community_investment', {}) if sec_parsed else {}

    # Also get CRA data from dedicated CRA source (may be more current)
    cra_data = institution_data.get('cra', {})

    # Use SEC-extracted CRA rating if available, else use CRA data source
    cra_rating = community_data.get('cra_rating') or cra_data.get('current_rating')
    cra_exam_date = cra_data.get('exam_date')

    # Community Development metrics (from text parsing)
    cd_data = community_data.get('community_development', {})
    cd_loans = cd_data.get('loans')
    cd_investments = cd_data.get('investments')
    cd_services = cd_data.get('services')

    # XBRL-sourced affordable housing data (more reliable when available)
    affordable_housing_tax_credits = community_data.get('affordable_housing_tax_credits')
    affordable_housing_amortization = community_data.get('affordable_housing_amortization')
    investment_tax_credit = community_data.get('investment_tax_credit')

    # Philanthropy
    charitable = community_data.get('charitable_contributions')
    foundation = community_data.get('foundation')

    # Commitments (affordable housing, minority lending, etc.)
    commitments = community_data.get('commitments', [])

    # Format amounts for display
    def format_amount(amount):
        if amount is None:
            return None
        if amount >= 1_000_000_000:
            return f"${amount / 1_000_000_000:.1f}B"
        elif amount >= 1_000_000:
            return f"${amount / 1_000_000:.0f}M"
        elif amount >= 1_000:
            return f"${amount / 1_000:.0f}K"
        else:
            return f"${amount:,.0f}"

    formatted_commitments = []
    for c in commitments:
        formatted_commitments.append({
            'amount': format_amount(c.get('amount')),
            'purpose': c.get('purpose', '').title()
        })

    has_data = bool(
        cra_rating or
        cd_loans or cd_investments or
        affordable_housing_tax_credits or
        charitable or foundation or
        commitments
    )

    return {
        'cra': {
            'rating': cra_rating,
            'exam_date': cra_exam_date
        },
        'community_development': {
            'loans': format_amount(cd_loans),
            'loans_raw': cd_loans,
            'investments': format_amount(cd_investments),
            'investments_raw': cd_investments,
            'services': cd_services
        },
        'affordable_housing': {
            'tax_credits': format_amount(affordable_housing_tax_credits),
            'tax_credits_raw': affordable_housing_tax_credits,
            'amortization': format_amount(affordable_housing_amortization),
            'amortization_raw': affordable_housing_amortization,
            'investment_tax_credit': format_amount(investment_tax_credit),
            'investment_tax_credit_raw': investment_tax_credit,
        },
        'philanthropy': {
            'charitable_contributions': format_amount(charitable),
            'charitable_raw': charitable,
            'foundation': {
                'name': foundation.get('name') if foundation else None,
                'assets': format_amount(foundation.get('amount')) if foundation else None
            } if foundation else None
        },
        'commitments': formatted_commitments,
        'has_data': has_data,
        'has_xbrl_data': sec_parsed.get('has_xbrl_data', False) if sec_parsed else False
    }


def build_branch_network(institution_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build branch network summary (simplified for intelligence focus).
    """
    branch_data = institution_data.get('branches', {})
    branches = branch_data.get('locations', [])
    analysis = branch_data.get('analysis', {})
    history = branch_data.get('history', {})

    total_branches = len(branches)

    # Group by state (top 10) for current year
    by_state = {}
    for branch in branches:
        state = branch.get('state') or branch.get('STALP', 'Unknown')
        if state not in by_state:
            by_state[state] = 0
        by_state[state] += 1

    # All states sorted by count (no limit)
    top_states = sorted(by_state.items(), key=lambda x: x[1], reverse=True)

    # Build states_by_year from history for interactive chart
    states_by_year = {}
    for year, year_branches in history.items():
        year_states = {}
        for branch in year_branches:
            state = branch.get('state') or branch.get('STALP', 'Unknown')
            if state not in year_states:
                year_states[state] = 0
            year_states[state] += 1
        # All states for this year, sorted by count
        all_year_states = sorted(year_states.items(), key=lambda x: x[1], reverse=True)
        states_by_year[year] = dict(all_year_states)

    # Trends - use total branches by year from analysis summary
    trends = {}
    if analysis:
        summary = analysis.get('summary', {})
        total_branches_by_year = summary.get('total_branches_by_year', {})
        net_change_by_year = analysis.get('net_change_by_year', {})
        trends = {
            'net_change': net_change_by_year,
            'by_year': total_branches_by_year,  # Total branches per year for chart
            'trend': 'expanding' if sum(net_change_by_year.values()) > 0 else 'contracting'
        }

    # National branch totals for comparison (FDIC data - approximate)
    # TODO: Replace with actual BigQuery data
    national_branches_by_year = {
        '2021': 76659,
        '2022': 74923,
        '2023': 72723,
        '2024': 70987,
        '2025': 69548
    }

    return {
        'total_branches': total_branches,
        'top_states': dict(top_states),
        'states_by_year': states_by_year,
        'trends': trends,
        'national_by_year': national_branches_by_year,
        'has_data': total_branches > 0
    }


def build_lending_footprint(
    institution_data: Dict[str, Any],
    hmda_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build lending footprint section from HMDA data.

    Shows top metros where the lender concentrates lending activity.
    Especially important for mortgage companies that don't have branches.

    Args:
        institution_data: Complete institution data
        hmda_data: HMDA lending footprint data from BigQueryHMDAClient

    Returns:
        Dictionary with:
        - top_metros: Top 10 metros by application count
        - states: State-level breakdown
        - concentration: Geographic concentration metrics
        - lender_type: Bank, Mortgage Company, Credit Union, etc.
    """
    # Get lender type from institution data
    identifiers = institution_data.get('identifiers', {})
    details = institution_data.get('details', {})

    lender_type = (
        identifiers.get('type') or
        identifiers.get('lender_type') or
        details.get('type_name') or
        'Unknown'
    )

    # Normalize lender type
    lender_type_lower = lender_type.lower()
    if 'mortgage' in lender_type_lower:
        lender_category = 'Mortgage Company'
    elif 'credit union' in lender_type_lower or 'cu' == lender_type_lower:
        lender_category = 'Credit Union'
    elif 'bank' in lender_type_lower:
        lender_category = 'Bank'
    else:
        lender_category = lender_type

    if not hmda_data:
        return {
            'has_data': False,
            'lender_type': lender_category,
            'top_metros': [],
            'states': [],
            'message': 'No HMDA lending data available.'
        }

    # Get yearly data from the actual data structure
    by_year = hmda_data.get('by_year', {})
    states_by_year = hmda_data.get('states_by_year', {})
    by_purpose_year = hmda_data.get('by_purpose_year', {})
    year = hmda_data.get('year')

    # Calculate total applications across all years
    total_applications = sum(by_year.values()) if by_year else 0

    # Calculate unique states from states_by_year
    all_states = set()
    state_totals = {}  # For building state breakdown
    for year_key, year_states in states_by_year.items():
        if isinstance(year_states, list):
            all_states.update(year_states)
            for s in year_states:
                state_totals[s] = state_totals.get(s, 0) + 1  # Count years active
        elif isinstance(year_states, dict):
            all_states.update(year_states.keys())
            for s, count in year_states.items():
                state_totals[s] = state_totals.get(s, 0) + count

    # Build formatted states for display (sorted by total activity)
    formatted_states = []
    sorted_states = sorted(state_totals.items(), key=lambda x: -x[1])
    for state, count in sorted_states[:10]:
        pct = (count / total_applications * 100) if total_applications > 0 else 0
        formatted_states.append({
            'state': state,
            'applications': count,
            'pct_of_total': round(pct, 1)
        })

    # Create by_state dict for chart
    by_state = {s['state']: s['applications'] for s in formatted_states}

    # Calculate concentration metrics
    state_count = len(all_states)
    is_national = state_count >= 40
    top_5_pct = sum(s['pct_of_total'] for s in formatted_states[:5]) if formatted_states else 0
    is_concentrated = top_5_pct > 60

    concentration = {
        'top_5_metros_pct': 0,  # No metro data available in current structure
        'is_concentrated': is_concentrated,
        'is_national': is_national
    }

    return {
        'has_data': total_applications > 0 or len(all_states) > 0,
        'lender_type': lender_category,
        'year': year,
        'total_applications': total_applications,
        'top_metros': [],  # Not available in current data structure
        'states': formatted_states,
        'by_state': by_state,
        'top_states': formatted_states,
        'total_states': state_count,
        'total_metros': 0,  # Not available in current data structure
        'concentration': concentration,
        'footprint_description': _describe_footprint(lender_category, state_count, concentration),
        # Multi-year data for trend charts
        'by_year': by_year,
        'states_by_year': states_by_year,
        'national_by_year': hmda_data.get('national_by_year', {}),
        # Loan purpose data for stacked column chart
        'by_purpose_year': by_purpose_year,
        'national_by_purpose_year': hmda_data.get('national_by_purpose_year', {})
    }


def _describe_footprint(lender_type: str, state_count: int, concentration: Dict[str, Any]) -> str:
    """Generate a natural language description of the lender's footprint."""
    is_national = concentration.get('is_national', False)
    is_concentrated = concentration.get('is_concentrated', False)
    top_5_pct = concentration.get('top_5_metros_pct', 0)

    if is_national:
        scope = "national"
    elif state_count >= 20:
        scope = "multi-regional"
    elif state_count >= 5:
        scope = "regional"
    else:
        scope = "local"

    if is_concentrated:
        focus = f"concentrated in top 5 metros ({top_5_pct:.0f}% of lending)"
    else:
        focus = "diversified across markets"

    return f"{scope.capitalize()} {lender_type.lower()} with lending {focus}."


def build_sb_lending(
    institution_data: Dict[str, Any],
    sb_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build small business lending section from CRA data.

    Shows lender's SB lending volume by year compared to national totals,
    plus geographic breakdown by state.

    Args:
        institution_data: Complete institution data
        sb_data: CRA small business lending data from BigQueryCRAClient

    Returns:
        Dictionary with yearly lending, national comparison, and top states
    """
    if not sb_data or not sb_data.get('has_data'):
        return {
            'has_data': False,
            'error': sb_data.get('error') if sb_data else 'No CRA data available'
        }

    yearly = sb_data.get('yearly_lending', {})
    national = sb_data.get('national_lending', {})
    top_states = sb_data.get('top_states', {})
    market_share = sb_data.get('market_share', [])

    # Format for chart display
    years = yearly.get('years', [])
    lender_counts = yearly.get('loan_counts', [])
    lender_amounts = yearly.get('loan_amounts', [])  # In thousands

    national_counts = national.get('loan_counts', [])
    national_amounts = national.get('loan_amounts', [])

    # Calculate totals
    total_loans = sum(lender_counts) if lender_counts else 0
    total_amount = sum(lender_amounts) if lender_amounts else 0  # In thousands

    # Format top states for bubble chart
    states = top_states.get('states', [])
    state_counts = top_states.get('loan_counts', [])
    state_percentages = top_states.get('percentages', [])

    # Build by_state dict for chart compatibility
    by_state = {}
    for i, state in enumerate(states):
        by_state[state] = {
            'count': state_counts[i] if i < len(state_counts) else 0,
            'pct': state_percentages[i] if i < len(state_percentages) else 0
        }

    return {
        'has_data': True,
        'respondent_id': sb_data.get('respondent_id'),
        'lender_name': sb_data.get('lender_name'),
        'data_source': sb_data.get('data_source', 'CRA Data'),

        # Yearly data for chart
        'years': years,
        'lender_loan_counts': lender_counts,
        'lender_loan_amounts': lender_amounts,  # In thousands
        'national_loan_counts': national_counts,
        'national_loan_amounts': national_amounts,

        # Summary metrics
        'total_loans': total_loans,
        'total_amount_thousands': total_amount,
        'market_share': market_share,

        # State breakdown
        'top_states': states,
        'state_counts': state_counts,
        'state_percentages': state_percentages,
        'by_state': by_state,

        # States by year for interactive chart
        'states_by_year': sb_data.get('states_by_year', {})
    }


# =============================================================================
# RIGHT COLUMN: LEADERSHIP, CONGRESSIONAL, STRUCTURE, NEWS
# =============================================================================

def build_leadership_section(
    institution_data: Dict[str, Any],
    sec_parsed: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build leadership and compensation section from SEC proxy (DEF 14A).

    Includes:
    - CEO and top executives
    - Compensation details
    - Recent leadership changes
    """
    sec_data = institution_data.get('sec', {})

    if not sec_parsed:
        sec_parsed = sec_data.get('parsed', {})

    proxy_data = sec_parsed.get('proxy', {}) if sec_parsed else {}
    executives = proxy_data.get('executive_compensation', [])
    board = proxy_data.get('board_composition', [])

    # Get institution name for AI verification
    institution_name = institution_data.get('institution', {}).get('name', '')

    # Verify executive names with AI if any appear incomplete (single word only)
    if executives and institution_name:
        executives = _verify_executive_names_with_ai(executives, institution_name)

    # Find CEO
    ceo = None
    for exec in executives:
        title = (exec.get('title') or '').lower()
        if 'chief executive' in title or 'ceo' in title or 'president' in title:
            ceo = exec
            break

    if not ceo and executives:
        ceo = executives[0]

    # Format top 5 executives (excluding CEO who is shown separately)
    # Dedupe by name (case-insensitive)
    top_executives = []
    seen_names = set()
    ceo_name = ceo.get('name', '').lower() if ceo else ''
    if ceo_name:
        seen_names.add(ceo_name)  # Mark CEO as seen to skip duplicates

    for exec in executives:
        exec_name = exec.get('name', 'Unknown')
        exec_name_lower = exec_name.lower()

        # Skip the CEO - they're shown separately in the CEO profile section
        # Skip duplicates
        if exec_name_lower in seen_names:
            continue
        seen_names.add(exec_name_lower)

        top_executives.append({
            'name': exec_name,
            'title': exec.get('title', ''),
            'salary': _format_currency(exec.get('salary')),
            'bonus': _format_currency(exec.get('bonus')),
            'stock_awards': _format_currency(exec.get('stock_awards')),
            'total': _format_currency(exec.get('total', 0))
        })
        if len(top_executives) >= 5:  # Limit to top 5 non-CEO executives
            break

    return {
        'ceo': {
            'name': ceo.get('name', '--') if ceo else '--',
            'title': ceo.get('title', 'Chief Executive Officer') if ceo else 'CEO',
            'total_compensation': _format_currency(ceo.get('total', 0)) if ceo else '--'
        },
        'top_executives': top_executives,
        'board_size': len(board),
        'board_members': board[:10],
        'has_data': bool(ceo or executives)
    }


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


def build_corporate_structure(
    institution_data: Dict[str, Any],
    ticker_map: Optional[Dict[str, str]] = None,
    identifier_map: Optional[Dict[str, Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Build corporate structure tree from GLEIF and SEC data.
    Shows full GLEIF hierarchy with links to GLEIF pages.
    LEI numbers are included but not displayed - used for GLEIF links and copy button.

    Args:
        institution_data: Complete institution data
        ticker_map: Map of LEI/name to ticker symbols
        identifier_map: Map of LEI/name to identifiers (ticker, cik, fdic_cert)
    """
    details = institution_data.get('details', {})
    gleif_data = details.get('gleif_data', {})
    corporate_structure = institution_data.get('corporate_structure', {})
    sec_parsed = institution_data.get('sec_parsed', {}) or institution_data.get('sec', {}).get('parsed', {})

    ticker_map = ticker_map or {}
    identifier_map = identifier_map or {}

    # Current entity
    identifiers = institution_data.get('identifiers', {})
    current_lei = identifiers.get('lei', '')
    current_entity = {
        'name': institution_data.get('institution', {}).get('name', 'Unknown'),
        'lei': current_lei,
        'gleif_url': f'https://search.gleif.org/#/record/{current_lei}' if current_lei else None,
        'ticker': identifiers.get('ticker'),
        'cik': identifiers.get('cik'),
        'fdic_cert': identifiers.get('fdic_cert'),
        'is_current': True
    }

    # Ultimate parent - include all identifiers for linking
    ultimate_parent = None
    if corporate_structure.get('ultimate_parent'):
        up = corporate_structure['ultimate_parent']
        lei = up.get('lei', '')
        name = up.get('name', 'Unknown')

        # Get identifiers from map or direct data
        parent_ids = identifier_map.get(lei) or identifier_map.get(name) or {}

        ultimate_parent = {
            'name': name,
            'lei': lei,
            'gleif_url': f'https://search.gleif.org/#/record/{lei}' if lei else None,
            'ticker': ticker_map.get(lei) or ticker_map.get(name) or parent_ids.get('ticker'),
            'cik': up.get('cik') or parent_ids.get('cik'),
            'fdic_cert': up.get('fdic_cert') or parent_ids.get('fdic_cert')
        }

    # Get GLEIF subsidiaries structure (direct vs ultimate children)
    gleif_subs = corporate_structure.get('subsidiaries', {})
    direct_children_data = gleif_subs.get('direct', []) if isinstance(gleif_subs, dict) else []
    ultimate_children_data = gleif_subs.get('ultimate', []) if isinstance(gleif_subs, dict) else []

    # Build direct children list (first-level subsidiaries)
    direct_children = []
    for child in direct_children_data:
        lei = child.get('lei', '')
        name = child.get('name', 'Unknown')
        child_ids = identifier_map.get(lei) or identifier_map.get(name) or {}

        direct_children.append({
            'name': name,
            'lei': lei,
            'gleif_url': f'https://search.gleif.org/#/record/{lei}' if lei else None,
            'ticker': ticker_map.get(lei) or ticker_map.get(name) or child_ids.get('ticker'),
            'cik': child.get('cik') or child_ids.get('cik'),
            'fdic_cert': child.get('fdic_cert') or child_ids.get('fdic_cert'),
            'source': 'GLEIF',
            'relationship': 'direct'
        })

    # Build ultimate children list (grandchildren - subsidiaries of subsidiaries)
    ultimate_children = []
    for child in ultimate_children_data:
        lei = child.get('lei', '')
        name = child.get('name', 'Unknown')
        child_ids = identifier_map.get(lei) or identifier_map.get(name) or {}

        # Skip if already in direct children
        if any(d.get('lei') == lei for d in direct_children):
            continue

        ultimate_children.append({
            'name': name,
            'lei': lei,
            'gleif_url': f'https://search.gleif.org/#/record/{lei}' if lei else None,
            'ticker': ticker_map.get(lei) or ticker_map.get(name) or child_ids.get('ticker'),
            'cik': child.get('cik') or child_ids.get('cik'),
            'fdic_cert': child.get('fdic_cert') or child_ids.get('fdic_cert'),
            'source': 'GLEIF',
            'relationship': 'ultimate'
        })

    # Sort helper: main entities (banks) first, then by name
    def sort_priority(entity):
        name = (entity.get('name') or '').upper()
        # Main banks get highest priority
        if 'NATIONAL ASSOCIATION' in name or ', N.A.' in name:
            return (0, name)
        if 'BANK' in name and 'PENSION' not in name and 'TRUST FUND' not in name:
            return (1, name)
        # Funds and trusts get lowest priority
        if 'PENSION' in name or 'TRUST FUND' in name or 'COMMINGLED' in name:
            return (9, name)
        # Everything else in between
        return (5, name)

    # Sort direct and ultimate children to put main entities first
    direct_children.sort(key=sort_priority)
    ultimate_children.sort(key=sort_priority)

    # Combined list for backwards compatibility
    subsidiaries = direct_children + ultimate_children

    # Fall back to combined children list if no structured data
    if not subsidiaries:
        for child in corporate_structure.get('children', [])[:15]:
            lei = child.get('lei', '')
            name = child.get('name', 'Unknown')
            child_ids = identifier_map.get(lei) or identifier_map.get(name) or {}

            subsidiaries.append({
                'name': name,
                'lei': lei,
                'gleif_url': f'https://search.gleif.org/#/record/{lei}' if lei else None,
                'ticker': ticker_map.get(lei) or ticker_map.get(name) or child_ids.get('ticker'),
                'cik': child.get('cik') or child_ids.get('cik'),
                'fdic_cert': child.get('fdic_cert') or child_ids.get('fdic_cert'),
                'source': 'GLEIF'
            })
        # Sort fallback list too
        subsidiaries.sort(key=sort_priority)

    return {
        'ultimate_parent': ultimate_parent,
        'current_entity': current_entity,
        'direct_children': direct_children,
        'ultimate_children': ultimate_children,
        'subsidiaries': subsidiaries,
        'total_subsidiaries': len(subsidiaries),
        'has_data': bool(ultimate_parent or subsidiaries)
    }


def build_recent_news(
    institution_data: Dict[str, Any],
    limit: int = None  # No limit by default - show all articles
) -> Dict[str, Any]:
    """
    Build recent news section with categorization.

    Uses news_processed (filtered for primary subject) if available,
    falls back to raw news data. Shows all articles from the available
    time period (up to 3 years depending on API tier).
    """
    # Prefer news_processed (filtered) over raw news
    news_data = institution_data.get('news_processed', institution_data.get('news', {}))
    articles = news_data.get('articles', [])

    # Categorize ALL articles (no limit)
    categorized = {
        'regulatory': [],
        'merger': [],
        'earnings': [],
        'leadership': [],
        'other': []
    }

    for article in articles:
        title = (article.get('title') or '').lower()
        description = (article.get('description') or '').lower()
        text = f"{title} {description}"

        # Categorize
        if any(w in text for w in ['enforcement', 'cfpb', 'fine', 'penalty', 'consent', 'investigation']):
            category = 'regulatory'
        elif any(w in text for w in ['merger', 'acquisition', 'acquire', 'deal', 'buy']):
            category = 'merger'
        elif any(w in text for w in ['earnings', 'profit', 'revenue', 'quarter', 'results']):
            category = 'earnings'
        elif any(w in text for w in ['ceo', 'appoint', 'resign', 'executive', 'board']):
            category = 'leadership'
        else:
            category = 'other'

        # Get summary/snippet (first 2-3 lines of content)
        summary = article.get('summary', article.get('description', article.get('content', '')))
        if summary and len(summary) > 200:
            summary = summary[:200] + '...'

        categorized[category].append({
            'title': article.get('title', article.get('headline', '')),
            'summary': summary,
            'source': article.get('source', {}).get('name', '') if isinstance(article.get('source'), dict) else article.get('source', ''),
            'published_at': article.get('publishedAt', article.get('date', '')),
            'url': article.get('url', ''),
            'category': category
        })

    # Flatten for display - prioritize regulatory and merger news first, then all others
    # No limits - show all articles
    all_articles = (
        categorized['regulatory'] +
        categorized['merger'] +
        categorized['leadership'] +
        categorized['earnings'] +
        categorized['other']
    )

    # Apply limit only if explicitly specified
    final_articles = all_articles[:limit] if limit else all_articles

    return {
        'articles': final_articles,
        'by_category': {k: len(v) for k, v in categorized.items()},
        'total': len(articles),
        'has_regulatory_news': len(categorized['regulatory']) > 0,
        'has_merger_news': len(categorized['merger']) > 0,
        'has_data': len(all_articles) > 0
    }


def build_seeking_alpha_section(
    institution_data: Dict[str, Any],
    ticker: str = None
) -> Dict[str, Any]:
    """
    Build Seeking Alpha section with ticker-specific analysis articles.

    Uses the analysis_articles from the API which are already filtered
    to only include articles about this specific ticker/company.
    """
    seeking_alpha_data = institution_data.get('seeking_alpha', {})

    # Get ticker-specific analysis articles (already filtered by ticker)
    analysis_articles = seeking_alpha_data.get('analysis_articles', [])
    if not isinstance(analysis_articles, list):
        analysis_articles = []

    # Format analysis articles
    formatted_articles = []
    for article in analysis_articles:
        if isinstance(article, dict):
            formatted_articles.append({
                'title': article.get('headline', article.get('title', '')),
                'summary': article.get('summary', '') or '',
                'url': article.get('url', ''),
                'published_at': article.get('date', article.get('publishOn', '')),
                'source': 'Seeking Alpha'
            })

    # Get ratings data if available
    # Structure: {data: [{attributes: {ratings: {quantRating, sellSideRating}}}]}
    ratings_data = seeking_alpha_data.get('ratings', {})
    quant_rating = None
    wall_st_rating = None
    if isinstance(ratings_data, dict):
        data_list = ratings_data.get('data', [])
        if isinstance(data_list, list) and len(data_list) > 0:
            first_rating = data_list[0]
            if isinstance(first_rating, dict):
                attrs = first_rating.get('attributes', {})
                ratings = attrs.get('ratings', {})
                if isinstance(ratings, dict):
                    quant_val = ratings.get('quantRating')
                    wall_st_val = ratings.get('sellSideRating')
                    # Convert to display format (1-5 scale)
                    if quant_val:
                        quant_rating = f"{quant_val:.1f}"
                    if wall_st_val:
                        wall_st_rating = f"{wall_st_val:.1f}"

    return {
        'articles': formatted_articles,
        'total_articles': len(formatted_articles),
        'ticker': ticker,
        'quant_rating': quant_rating,
        'wall_st_rating': wall_st_rating,
        'has_data': len(formatted_articles) > 0 or quant_rating or wall_st_rating
    }


# =============================================================================
# SEC FILINGS ANALYSIS (NCRC-Relevant Topics)
# =============================================================================

def build_sec_filings_analysis(
    institution_data: Dict[str, Any],
    cik: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build SEC Filing Overview with 8-10 AI-generated key findings.

    Analyzes data from:
    - SEC 10-K and 10-Q filings (NCRC-relevant topics)
    - HMDA mortgage lending data
    - Branch network data
    - Small business lending data
    - Recent news
    - Executive leadership

    Returns 8-10 bulleted key findings covering all data sources.
    """
    # Get company info
    institution = institution_data.get('institution', {})
    company_name = institution.get('name', 'The company')

    # Collect data from all sources for AI analysis
    data_summary = _collect_comprehensive_data(institution_data)

    if not data_summary.get('has_any_data'):
        return {
            'has_data': False,
            'message': 'No data available for SEC filing overview'
        }

    # Generate 8-10 key findings using AI
    key_findings = _generate_comprehensive_key_findings(company_name, data_summary)

    return {
        'has_data': True,
        'key_findings': key_findings,
        'data_sources': data_summary.get('sources_used', []),
        'filings_analyzed': data_summary.get('sec_filings', [])
    }


def _collect_comprehensive_data(institution_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Collect and summarize data from all sources for key findings generation.
    """
    data = {
        'has_any_data': False,
        'sources_used': [],
        'sec_filings': [],
        'sec_topics': {},
        'hmda': {},
        'branches': {},
        'sb_lending': {},
        'news': {},
        'leadership': {},
        'complaints': {},
        'enforcement': {}
    }

    # SEC Filing Topics
    identifiers = institution_data.get('identifiers', {})
    cik = identifiers.get('cik') or institution_data.get('sec', {}).get('cik')

    if cik:
        try:
            from apps.lenderprofile.processors.sec_topic_extractor import SECTopicExtractor
            extractor = SECTopicExtractor()
            sec_results = extractor.analyze_filings(cik)
            if sec_results.get('has_data'):
                data['sec_filings'] = sec_results.get('filings', [])
                data['sec_topics'] = sec_results.get('by_topic', {})
                data['sources_used'].append('SEC Filings')
                data['has_any_data'] = True
        except Exception as e:
            logger.warning(f"SEC analysis failed: {e}")

    # HMDA/Mortgage Data
    hmda = institution_data.get('hmda_footprint', {})
    if hmda and hmda.get('by_year'):
        # Calculate states from states_by_year
        states_by_year = hmda.get('states_by_year', {})
        all_states = set()
        for year_states in states_by_year.values():
            if isinstance(year_states, list):
                all_states.update(year_states)
            elif isinstance(year_states, dict):
                all_states.update(year_states.keys())

        # Format top metros for AI analysis
        top_metros = hmda.get('top_metros', [])
        formatted_metros = []
        for metro in top_metros[:15]:  # Top 15 metros
            formatted_metros.append({
                'metro_name': metro.get('msa_name', f"MSA {metro.get('msa_code', '')}"),
                'cbsa_code': metro.get('msa_code', ''),
                'applications': metro.get('application_count', 0),
                'pct_of_total': metro.get('pct_of_total', 0)
            })

        data['hmda'] = {
            'total_applications': sum(hmda.get('by_year', {}).values()),
            'total_states': len(all_states),
            'by_year': hmda.get('by_year', {}),
            'by_purpose_year': hmda.get('by_purpose_year', {}),
            'top_metros': formatted_metros  # CBSA-level data for AI
        }
        data['sources_used'].append('HMDA')
        data['has_any_data'] = True

    # Branch Network
    branches = institution_data.get('branches', {})
    branch_locations = branches.get('locations', [])
    if branch_locations:
        by_state = {}
        for b in branch_locations:
            state = b.get('state') or b.get('STALP', 'Unknown')
            by_state[state] = by_state.get(state, 0) + 1

        data['branches'] = {
            'total': len(branch_locations),
            'states': len(by_state),
            'top_states': sorted(by_state.items(), key=lambda x: -x[1])[:5],
            'trends': branches.get('analysis', {}).get('summary', {})
        }
        data['sources_used'].append('Branch Network')
        data['has_any_data'] = True

    # Small Business Lending
    sb = institution_data.get('sb_lending', {})
    if sb and sb.get('has_data'):
        # Get yearly lending data
        yearly = sb.get('yearly_lending', {})
        loan_counts = yearly.get('loan_counts', [])
        loan_amounts = yearly.get('loan_amounts', [])
        years = yearly.get('years', [])

        # top_states might be a list or dict, handle both
        top_states_raw = sb.get('top_states', [])
        if isinstance(top_states_raw, list):
            top_states = top_states_raw[:5]
        elif isinstance(top_states_raw, dict):
            top_states = list(top_states_raw.keys())[:5]
        else:
            top_states = []

        data['sb_lending'] = {
            'total_loans': sum(loan_counts) if loan_counts else 0,
            'total_amount': sum(loan_amounts) if loan_amounts else 0,
            'years': years,
            'yearly_data': yearly,
            'top_states': top_states
        }
        data['sources_used'].append('SB Lending')
        data['has_any_data'] = True

    # News
    news = institution_data.get('news_processed', institution_data.get('news', {}))
    articles = news.get('articles', [])
    if articles:
        data['news'] = {
            'count': len(articles),
            'headlines': [a.get('title', '')[:80] for a in articles[:5]],
            'categories': news.get('categorized', {})
        }
        data['sources_used'].append('News')
        data['has_any_data'] = True

    # Leadership
    sec_parsed = institution_data.get('sec_parsed', {})
    proxy = sec_parsed.get('proxy', {})
    executives = proxy.get('executive_compensation', [])
    if executives:
        data['leadership'] = {
            'count': len(executives),
            'executives': [{'name': e.get('name'), 'title': e.get('title'), 'total': e.get('total')}
                          for e in executives[:5]]
        }
        data['sources_used'].append('Leadership')
        data['has_any_data'] = True

    # CFPB Complaints - include year-by-year trends and categories
    complaints = institution_data.get('cfpb_complaints', {})
    if complaints.get('total', 0) > 0:
        # Get year-by-year data for trend analysis
        trends = complaints.get('trends', {})
        by_year = trends.get('by_year', {})

        # Get top product categories
        products = complaints.get('aggregations', {}).get('products', [])[:5]

        data['complaints'] = {
            'total': complaints.get('total', 0),
            'by_year': by_year,  # e.g., {"2024": 45000, "2023": 42000, "2022": 38000}
            'products': products,  # Top 5 product categories with counts
            'trend': trends.get('recent_trend', 'stable')  # up, down, or stable
        }
        data['sources_used'].append('Complaints')
        data['has_any_data'] = True

    # Enforcement Actions
    enforcement = institution_data.get('enforcement', {})
    actions = enforcement.get('actions', [])
    if actions:
        data['enforcement'] = {
            'count': len(actions),
            'recent': actions[:3]
        }
        data['sources_used'].append('Enforcement')
        data['has_any_data'] = True

    # Seeking Alpha Market Data
    seeking_alpha = institution_data.get('seeking_alpha', {})
    if seeking_alpha and seeking_alpha.get('ticker'):
        ratings = seeking_alpha.get('ratings', {})
        ratings_data = {}
        if ratings and isinstance(ratings, dict):
            data_list = ratings.get('data', [])
            if data_list:
                attrs = data_list[0].get('attributes', {}).get('ratings', {})
                ratings_data = {
                    'quant_rating': attrs.get('quantRating'),
                    'authors_rating': attrs.get('authorsRating'),
                    'sell_side_rating': attrs.get('sellSideRating'),
                    'buy_count': attrs.get('authorsRatingBuyCount', 0),
                    'hold_count': attrs.get('authorsRatingHoldCount', 0),
                    'sell_count': attrs.get('authorsRatingSellCount', 0)
                }
        data['seeking_alpha'] = {
            'ticker': seeking_alpha.get('ticker'),
            'ratings': ratings_data
        }
        data['sources_used'].append('Seeking Alpha')
        data['has_any_data'] = True

    # Congressional Trading
    congressional = institution_data.get('congressional_trading', {})
    if congressional and congressional.get('has_data'):
        data['congressional'] = {
            'total_trades': congressional.get('total_trades', 0),
            'total_purchases': congressional.get('total_purchases', 0),
            'total_sales': congressional.get('total_sales', 0),
            'unique_politicians': congressional.get('unique_politicians', 0),
            'recent_trades': congressional.get('recent_trades', [])[:5]
        }
        data['sources_used'].append('Congressional Trading')
        data['has_any_data'] = True

    return data


def _generate_comprehensive_key_findings(company_name: str, data: Dict[str, Any]) -> str:
    """
    Generate Executive Summary combining SEC filings with lending/branch/leadership data.
    Returns a natural narrative about the company for NCRC staff.
    """
    import json
    import logging
    logger = logging.getLogger(__name__)

    # Format filing list with dates
    filing_list = []
    if data.get('sec_filings'):
        for f in data['sec_filings'][:4]:  # Last 4 filings
            if isinstance(f, str):
                filing_list.append(f"- {f}")
            else:
                filing_list.append(f"- {f.get('form', 'Unknown')} ({f.get('filed', 'Unknown')})")
    filing_list_str = "\n".join(filing_list) if filing_list else "No SEC filings available"

    # Get all data sources
    sec_topics = data.get('sec_topics', {})
    hmda_data = data.get('hmda', {})
    branch_data = data.get('branches', {})
    sb_data = data.get('sb_lending', {})
    leadership_data = data.get('leadership', {})
    complaints_data = data.get('complaints', {})
    news_data = data.get('news', {})

    # Build the Executive Summary prompt - following lendsight/branchsight pattern
    prompt = f"""Generate an executive summary for {company_name}:

DATA SOURCES:

1. SEC FILINGS (10-K, 10-Q, DEF 14A):
{filing_list_str}

2. SEC DISCLOSURE TOPICS (extracted from filings):
{json.dumps(sec_topics, indent=2)[:6000]}

3. BRANCH NETWORK (FDIC SOD):
{json.dumps(branch_data, indent=2)[:1500]}

4. MORTGAGE LENDING (HMDA):
{json.dumps(hmda_data, indent=2)[:1500]}

5. SMALL BUSINESS LENDING (CRA):
{json.dumps(sb_data, indent=2)[:1000]}

6. EXECUTIVE LEADERSHIP (SEC DEF 14A):
{json.dumps(leadership_data, indent=2)[:800]}

7. CONSUMER COMPLAINTS (CFPB):
{json.dumps(complaints_data, indent=2)[:500]}

8. RECENT NEWS:
{json.dumps(news_data, indent=2)[:1500]}

9. SEEKING ALPHA (Wall Street Analyst Sentiment):
{json.dumps(data.get('seeking_alpha', {}), indent=2)[:800]}

10. CONGRESSIONAL TRADING (Stock purchases/sales by members of Congress):
{json.dumps(data.get('congressional', {}), indent=2)[:800]}

NCRC FOCUS AREAS (this is for National Community Reinvestment Coalition):
1. Corporate overview - size, headquarters, business segments, recent major developments (mergers, acquisitions)
2. Community investment and CRA - PRIORITIZE: affordable housing investments, LIHTC, CDFIs, community development loans, philanthropy programs
3. Branch network - geographic footprint in underserved communities, expansion/contraction trends
4. Mortgage lending - focus on lending patterns in LMI communities, fair lending, and access
5. Small business lending - volume trends supporting small businesses (note: 2020-2021 includes PPP loans)
6. Leadership - CEO and key executives
7. Consumer complaints and regulatory matters - top complaint categories and trends
8. Wall Street sentiment (Seeking Alpha) - include analyst Buy/Hold/Sell ratings if data available
9. Congressional trading - include if members of Congress are buying/selling stock (bullish or bearish signal)

EXCLUDE these financial metrics (NOT relevant for NCRC):
- Tier 1 capital ratios and regulatory capital
- Credit loss allowances and loan loss reserves
- Net interest income projections
- ROA, ROE, and pure financial performance metrics
- Investment-grade credit ratings

IMPORTANT: Focus on community impact and reinvestment patterns, not pure financial metrics.

WRITING REQUIREMENTS:
- Write in objective, third-person style
- NO first-person language (no "I", "we", "my", "our")
- NO personal opinions or subjective statements
- NO speculation about strategic implications or underlying causes
- Present ONLY factual patterns and observable data trends
- DO NOT make comparative judgments (e.g., "higher than typical", "exceptionally high") unless you have comparison data
- Use professional, analytical tone
- Cite SEC filings when referencing that data: "(10-K, 2024)" or "(DEF 14A)"

CRITICAL - LIMIT NUMBERS:
- Use NO MORE than 2-3 specific numbers per paragraph
- NEVER list multiple years of data with specific counts (e.g., "4,761 in 2022, 4,889 in 2023, 4,993 in 2024")
- Instead describe trends in prose: "branch network grew steadily over three years" or "mortgage applications declined by roughly two-thirds"
- Use ranges and approximations: "approximately 5,000 branches" not "4,993 branches"
- Use percentages for changes: "increased 25%" not "from 812,057 to 2,219,044"
- Focus on the STORY and PATTERNS, not reciting data tables
- For complaints: just describe the trend direction and top categories, not year-by-year counts

FORMAT:
- Output in plain HTML. Use <strong>text</strong> for emphasis, NOT markdown
- Flowing paragraphs, NOT bullet points
- 7-9 paragraphs, approximately 900-1200 words total
- IMPORTANT: Include a paragraph on Wall Street sentiment (Seeking Alpha ratings) if data is available
- IMPORTANT: Include a paragraph on Congressional trading activity if data is available
"""

    try:
        from shared.analysis.ai_provider import ask_ai
        logger.info(f"SEC ANALYSIS PROMPT for {company_name} (first 2000 chars):\n{prompt[:2000]}")

        # Use Sonnet 4.5 with temperature=0
        model_id = "claude-sonnet-4-5-20250929"
        response = ask_ai(
            prompt,
            model=model_id,
            max_tokens=3000,
            temperature=0
        )

        logger.info(f"SEC ANALYSIS RESPONSE (first 1500 chars):\n{response[:1500] if response else 'None'}")

        # Add AI model attribution at the end
        if response:
            model_display = "Claude Sonnet 4.5"
            response += f'\n\n<p class="ai-attribution"><em>Generated by {model_display}</em></p>'
            return response
        return "SEC filing analysis not available."

    except Exception as e:
        logger.error(f"Error generating SEC analysis: {e}")
        return f"SEC filing analysis unavailable due to error: {str(e)}"


def _generate_fallback_findings(company_name: str, data: Dict[str, Any]) -> List[str]:
    """Generate basic findings without AI if the AI call fails."""
    findings = []

    if data.get('branches'):
        b = data['branches']
        findings.append(f"**Branch Network:** {company_name} operates {b.get('total', 0):,} branches across {b.get('states', 0)} states.")

    if data.get('hmda'):
        h = data['hmda']
        findings.append(f"**Mortgage Lending:** Active in {h.get('total_states', 0)} states with {h.get('total_metros', 0)} metro markets.")

    if data.get('sb_lending'):
        sb = data['sb_lending']
        findings.append(f"**Small Business Lending:** Originated {sb.get('total_loans', 0):,} small business loans totaling ${sb.get('total_amount', 0):,.0f} thousand.")

    if data.get('complaints'):
        c = data['complaints']
        findings.append(f"**Consumer Complaints:** {c.get('total', 0):,} CFPB complaints on record.")

    if data.get('leadership'):
        l = data['leadership']
        findings.append(f"**Executive Team:** {l.get('count', 0)} named executive officers with disclosed compensation.")

    return findings if findings else ["No data available for key findings."]


# =============================================================================
# FULL WIDTH: AI SUMMARY
# =============================================================================

def build_ai_intelligence_summary(
    institution_data: Dict[str, Any],
    ai_analyzer,
    report_focus: Optional[str] = None,
    sec_parsed: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build AI-powered intelligence summary.

    This is the strategic AI call - synthesizes all data into
    actionable intelligence for decision-makers.
    """
    # Get executive compensation data from sec_parsed
    proxy_data = (sec_parsed or {}).get('proxy', {})
    executives = proxy_data.get('executive_compensation', [])
    
    # Format executive summary for AI
    exec_summary = []
    for ex in executives[:5]:  # Top 5 executives
        name = ex.get('name', '')
        title = ex.get('title', '')[:50] if ex.get('title') else ''
        total = ex.get('total', 0)
        if name and total:
            exec_summary.append(f"{name} ({title}): ${total:,.0f}")
    
    # Get complaint details
    complaints = institution_data.get('cfpb_complaints', {})
    complaint_topics = []
    for topic in complaints.get('aggregations', {}).get('products', [])[:3]:
        if isinstance(topic, dict):
            complaint_topics.append(topic.get('name', ''))
    
    # Get news headlines (prefer filtered news_processed)
    news_data = institution_data.get('news_processed', institution_data.get('news', {}))
    news_articles = news_data.get('articles', [])
    news_headlines = [a.get('title', '')[:80] for a in news_articles[:5]]
    
    # Prepare condensed data for AI - NO technical identifiers
    institution = institution_data.get('institution', {})
    identifiers = institution_data.get('identifiers', {})

    # Get name from multiple sources
    inst_name = (institution.get('name') or
                 identifiers.get('name') or
                 institution_data.get('name', 'Unknown'))

    # Get location from multiple sources
    location = institution.get('location', '')
    if not location:
        city = institution.get('city', '') or identifiers.get('city', '')
        state = institution.get('state', '') or identifiers.get('state', '')
        if city and state:
            location = f"{city}, {state}"
        elif state:
            location = state

    # Get assets from multiple sources
    assets = institution.get('assets')
    if not assets:
        fdic_data = institution_data.get('financial', {}).get('fdic_call_reports', [])
        if fdic_data and isinstance(fdic_data, list) and len(fdic_data) > 0:
            assets = fdic_data[0].get('ASSET', 0) * 1000  # FDIC reports in thousands

    # Get branch count
    branches = institution_data.get('branches', {})
    branch_count = len(branches.get('locations', [])) if branches else 0

    # Get HMDA summary
    hmda = institution_data.get('hmda_footprint', {})
    hmda_summary = {}
    if hmda:
        # Calculate total applications from by_year data
        by_year = hmda.get('by_year', {})
        total_apps = sum(by_year.values()) if by_year else 0

        # Calculate unique states from states_by_year data
        states_by_year = hmda.get('states_by_year', {})
        all_states = set()
        for year_states in states_by_year.values():
            if isinstance(year_states, list):
                all_states.update(year_states)
            elif isinstance(year_states, dict):
                all_states.update(year_states.keys())

        hmda_summary = {
            'total_applications': total_apps,
            'states': len(all_states),
            'by_year': by_year,  # Include yearly breakdown for AI analysis
            'top_metros': []  # Not available in current data structure
        }

    # Get SB lending summary
    sb_lending = institution_data.get('sb_lending', {})
    sb_summary = {}
    if sb_lending and sb_lending.get('has_data'):
        yearly = sb_lending.get('yearly_lending', {})
        loan_counts = yearly.get('loan_counts', [])
        loan_amounts = yearly.get('loan_amounts', [])
        sb_summary = {
            'total_loans': sum(loan_counts) if loan_counts else 0,
            'total_amount': sum(loan_amounts) if loan_amounts else 0,  # In thousands
            'yearly_data': yearly  # Include for AI analysis
        }

    # Get Seeking Alpha data for AI
    seeking_alpha = institution_data.get('seeking_alpha', {})
    seeking_alpha_summary = {}
    if seeking_alpha and seeking_alpha.get('has_data'):
        ratings = seeking_alpha.get('ratings', {})
        if ratings and isinstance(ratings, dict):
            ratings_data = ratings.get('data', [])
            if ratings_data:
                latest_rating = ratings_data[0].get('attributes', {}).get('ratings', {})
                seeking_alpha_summary = {
                    'authors_rating': latest_rating.get('authorsRating'),
                    'sell_side_rating': latest_rating.get('sellSideRating'),
                    'quant_rating': latest_rating.get('quantRating'),
                    'buy_count': latest_rating.get('authorsRatingBuyCount', 0),
                    'hold_count': latest_rating.get('authorsRatingHoldCount', 0),
                    'sell_count': latest_rating.get('authorsRatingSellCount', 0)
                }

    # Get branch network trends
    branches = institution_data.get('branches', {})
    branch_trends = {}
    if branches:
        branch_trends = {
            'total_branches': branch_count,
            'by_year': branches.get('total_branches_by_year', {}),
            'net_change_by_year': branches.get('net_change_by_year', {}),
            'top_states': branches.get('top_states', [])[:5],
            'trend': branches.get('trends', {}).get('overall_trend', 'stable')
        }

    # Get congressional trading summary
    congressional = institution_data.get('congressional_trading', {})
    congressional_summary = {}
    if congressional and congressional.get('has_data'):
        congressional_summary = {
            'total_trades': congressional.get('total_trades', 0),
            'total_purchases': congressional.get('total_purchases', 0),
            'total_sales': congressional.get('total_sales', 0),
            'unique_politicians': congressional.get('unique_politicians', 0),
            'sentiment': congressional.get('sentiment', 'Mixed')
        }

    # Get corporate structure
    corporate = institution_data.get('corporate_structure', {})
    corporate_summary = {}
    if corporate:
        corporate_summary = {
            'ultimate_parent': corporate.get('ultimate_parent', {}).get('name') if corporate.get('ultimate_parent') else None,
            'subsidiaries_count': len(corporate.get('subsidiaries', {}).get('direct', [])) + len(corporate.get('subsidiaries', {}).get('ultimate', []))
        }

    summary_data = {
        'institution_name': inst_name,
        'institution_type': institution.get('type', ''),
        'location': location,
        'assets': assets or 'N/A',
        'executive_compensation': exec_summary,
        'financial_summary': _extract_financial_summary(institution_data),
        'cra_rating': institution_data.get('cra', {}).get('current_rating'),
        'enforcement_count': len(institution_data.get('enforcement', {}).get('actions', [])),
        'complaint_count': complaints.get('total', 0),
        'complaint_topics': complaint_topics,
        'complaint_trends': complaints.get('trends', {}),
        'pending_mergers': len(institution_data.get('mergers', {}).get('pending', [])),
        'news_headlines': news_headlines,
        'recent_news_count': len(news_articles),
        'branch_trends': branch_trends,
        'hmda_summary': hmda_summary,
        'sb_lending_summary': sb_summary,
        'seeking_alpha_summary': seeking_alpha_summary,
        'congressional_trading': congressional_summary,
        'corporate_structure': corporate_summary
    }

    try:
        # Check if we have Tier 1 analyst summaries available
        analyst_summaries = institution_data.get('analyst_summaries', {})
        entity_resolution = institution_data.get('ai_entity_resolution', {})

        if analyst_summaries and analyst_summaries.get('analyst_summaries'):
            # Use template-based assembly for guaranteed data source coverage
            logger.info("Generating executive summary using template-based assembly (all sources guaranteed)")
            ai_summary = ai_analyzer.generate_executive_summary_assembled(
                inst_name,
                analyst_summaries,
                entity_resolution,
                report_focus
            )
        else:
            # Fallback to original method without analyst pre-processing
            logger.info("Generating executive summary (no analyst summaries available)")
            ai_summary = ai_analyzer.generate_executive_summary(summary_data, report_focus)

        # Skip key findings to save API costs - summary is comprehensive
        key_findings = []
    except Exception as e:
        logger.error(f"Error generating AI summary: {e}", exc_info=True)
        ai_summary = "AI summary generation unavailable."
        key_findings = []

    # Convert markdown-formatted AI output into plain text with simple headers/subheads
    def _markdown_to_plain(md_text: Optional[str]) -> str:
        if not md_text:
            return ''
        text = md_text

        # Replace markdown links [text](url) -> text (url)
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)

        # Convert headings: # H1 -> H1\n====, ## H2 -> H2\n----, ### H3 -> H3
        def _hdr(m):
            level = len(m.group(1))
            title = m.group(2).strip()
            if level == 1:
                return f"{title.upper()}\n{'=' * len(title)}\n"
            if level == 2:
                return f"{title}\n{'-' * len(title)}\n"
            return f"{title}\n"

        text = re.sub(r'^(#{1,3})\s*(.+)$', _hdr, text, flags=re.MULTILINE)

        # Bold markers -> uppercase heading-like text (e.g., **Title:** -> TITLE:)
        text = re.sub(r"\*\*([^*]+)\*\*\s*:\s*", lambda m: f"{m.group(1).upper()}: ", text)
        text = re.sub(r"\*\*([^*]+)\*\*", lambda m: m.group(1), text)

        # Bullet points: unify common bullet tokens to '- '
        text = re.sub(r'^[\s]*[\u2022\-*+]\s+', '- ', text, flags=re.MULTILINE)

        # Remove remaining markdown code ticks
        text = text.replace('`', '')

        # Collapse multiple blank lines to two
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    plain_summary = _markdown_to_plain(ai_summary)

    # Normalize key_findings to a LIST of plain text strings
    # Filter out header lines and other non-finding content
    header_patterns = [
        'key findings', 'key finding', '====', '----',
        'summary', 'overview', 'report for', 'analysis for'
    ]

    def is_valid_finding(text: str) -> bool:
        """Check if text is a valid finding (not a header or separator)."""
        text_lower = text.lower().strip()
        if not text_lower or len(text_lower) < 10:  # Too short to be a finding
            return False
        if text_lower.startswith('key findings') or text_lower.startswith('findings for'):
            return False
        for pattern in header_patterns:
            if pattern in text_lower and len(text_lower) < 80:  # Short line with header text
                return False
        return True

    if isinstance(key_findings, list):
        plain_key_findings = [_markdown_to_plain(k) for k in key_findings if is_valid_finding(k)]
    elif isinstance(key_findings, str):
        # Parse string into list by splitting on bullet points or newlines
        lines = key_findings.split('\n')
        plain_key_findings = []
        for line in lines:
            line = line.strip()
            # Remove bullet prefixes
            line = re.sub(r'^[\u2022\-*•]\s*', '', line)
            if line and is_valid_finding(line):
                plain_key_findings.append(_markdown_to_plain(line))
    else:
        plain_key_findings = []

    return {
        'summary': plain_summary,
        'key_findings': plain_key_findings,  # Keep as LIST for JavaScript
        'focus_area': report_focus
    }


# =============================================================================
# MASTER BUILD FUNCTION
# =============================================================================

def build_complete_report_v2(
    institution_data: Dict[str, Any],
    ai_analyzer,
    ticker_resolver=None,
    report_focus: Optional[str] = None,
    congressional_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build complete V2 intelligence report with all sections.
    """
    identifiers = institution_data.get('identifiers', {})
    ticker = identifiers.get('ticker', '') or institution_data.get('sec', {}).get('ticker', '')

    # Get congressional data from institution_data if not provided
    ticker_map = {}
    congressional_data = congressional_data or institution_data.get('congressional_trading', {})

    if ticker_resolver:
        try:
            ticker_map = ticker_resolver.resolve_corporate_family_tickers(
                institution_data.get('corporate_structure', {}),
                institution_data.get('identifiers', {})
            )
        except Exception as e:
            logger.error(f"Ticker resolution error: {e}")

    # Get SEC parsed data (check both locations for compatibility)
    sec_parsed = institution_data.get('sec_parsed', {}) or institution_data.get('sec', {}).get('parsed', {})

    # Build all sections
    report = {
        'generated_at': datetime.now().isoformat(),
        'version': '2.0',

        # Header
        'header': build_institution_header(
            institution_data,
            None  # Stock data (optional)
        ),

        # Left column - Strategy & Operations
        'business_strategy': build_business_strategy(institution_data, sec_parsed),
        'risk_factors': build_risk_factors(institution_data, sec_parsed),
        'financial_performance': build_financial_performance(institution_data),
        'merger_activity': build_merger_activity(institution_data),
        'regulatory_risk': build_regulatory_risk(institution_data),
        'community_investment': build_community_investment(institution_data, sec_parsed),
        'branch_network': build_branch_network(institution_data),
        'lending_footprint': build_lending_footprint(
            institution_data,
            institution_data.get('hmda_footprint')
        ),
        'sb_lending': build_sb_lending(
            institution_data,
            institution_data.get('sb_lending')
        ),

        # Right column - People & External
        'leadership': build_leadership_section(institution_data, sec_parsed),
        'congressional_trading': build_congressional_trading(
            congressional_data,
            ticker,
            ai_sentiment_summary=ai_analyzer.generate_congressional_sentiment(ticker, congressional_data) if ai_analyzer and congressional_data and congressional_data.get('has_data') else ""
        ),
        'corporate_structure': build_corporate_structure(institution_data, ticker_map),
        'recent_news': build_recent_news(institution_data),
        'seeking_alpha': build_seeking_alpha_section(institution_data, ticker),

        # Full width
        'ai_summary': build_ai_intelligence_summary(
            institution_data,
            ai_analyzer,
            report_focus
        ),

        # SEC Filings Analysis (below AI Summary in left column)
        'sec_filings_analysis': build_sec_filings_analysis(institution_data)
    }

    return report



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


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _format_currency(value: Optional[float], suffix: str = '') -> str:
    """Format currency value with appropriate suffix."""
    if value is None or value == 0:
        return '--'

    if value >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.2f}T{suffix}"
    elif value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B{suffix}"
    elif value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M{suffix}"
    elif value >= 1_000:
        return f"${value / 1_000:.1f}K{suffix}"
    else:
        return f"${value:,.0f}{suffix}"


def _truncate_text(text: Optional[str], max_length: int) -> str:
    """Truncate text to max length."""
    if not text:
        return ''
    if len(text) <= max_length:
        return text
    return text[:max_length] + '...'


def _calculate_growth(current: float, previous: float) -> Optional[float]:
    """Calculate growth rate."""
    if not previous or previous == 0:
        return None
    return ((current - previous) / previous) * 100


def _is_recent(date_str: Optional[str], years: int = 3) -> bool:
    """Check if date is within recent years."""
    if not date_str:
        return False
    try:
        date = datetime.strptime(date_str[:10], '%Y-%m-%d')
        cutoff = datetime.now() - timedelta(days=years * 365)
        return date >= cutoff
    except:
        return False


def _extract_business_segments(text: str) -> List[Dict[str, str]]:
    """Extract business segment information from Item 1."""
    if not text:
        return []

    segments = []
    # Look for common segment patterns
    patterns = [
        r'(?:commercial|retail|consumer|corporate|investment|wealth|mortgage)\s*banking',
        r'(?:commercial|residential)\s*(?:real estate|lending)',
        r'(?:treasury|capital markets|trading)',
        r'(?:insurance|wealth management|asset management)'
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if match.strip() not in [s.get('name') for s in segments]:
                segments.append({'name': match.strip().title()})

    return segments[:10]


def _extract_strategic_priorities(text: str) -> List[str]:
    """Extract strategic priorities from MD&A."""
    if not text:
        return []

    priorities = []
    # Look for priority indicators
    indicators = ['focus on', 'priority', 'key initiative', 'strategic', 'invest in', 'expand']

    sentences = text.split('.')
    for sentence in sentences:
        if any(ind in sentence.lower() for ind in indicators):
            clean = sentence.strip()
            if 10 < len(clean) < 300:
                priorities.append(clean)

    return priorities[:5]


def _extract_growth_areas(text: str) -> List[str]:
    """Extract growth areas from MD&A."""
    if not text:
        return []

    growth = []
    indicators = ['growth', 'expand', 'increase', 'opportunity', 'invest']

    sentences = text.split('.')
    for sentence in sentences:
        if any(ind in sentence.lower() for ind in indicators):
            if 'expect' in sentence.lower() or 'will' in sentence.lower() or 'plan' in sentence.lower():
                clean = sentence.strip()
                if 10 < len(clean) < 300:
                    growth.append(clean)

    return growth[:5]


def _extract_contraction_areas(text: str) -> List[str]:
    """Extract contraction/exit areas from MD&A."""
    if not text:
        return []

    contraction = []
    indicators = ['exit', 'reduce', 'decline', 'close', 'divest', 'wind down']

    sentences = text.split('.')
    for sentence in sentences:
        if any(ind in sentence.lower() for ind in indicators):
            clean = sentence.strip()
            if 10 < len(clean) < 300:
                contraction.append(clean)

    return contraction[:5]


def _categorize_risks(text: str) -> Dict[str, int]:
    """Categorize risk factors by type."""
    if not text:
        return {}

    categories = {
        'credit_risk': ['credit', 'loan', 'default', 'non-performing'],
        'market_risk': ['interest rate', 'market', 'trading', 'investment'],
        'operational_risk': ['operational', 'cyber', 'technology', 'systems'],
        'regulatory_risk': ['regulatory', 'compliance', 'legislation', 'law'],
        'competitive_risk': ['competition', 'competitor', 'market share'],
        'economic_risk': ['economic', 'recession', 'unemployment', 'housing']
    }

    counts = {}
    text_lower = text.lower()

    for category, keywords in categories.items():
        count = sum(1 for kw in keywords if kw in text_lower)
        if count > 0:
            counts[category] = count

    return counts


def _extract_financial_summary(institution_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract key financial metrics for AI summary."""
    financial = institution_data.get('financial', {})
    fdic_reports = financial.get('fdic_call_reports', [])

    if not fdic_reports:
        return _build_financial_from_sec_xbrl(institution_data)

    # FDIC data is available - FDIC reports dollar amounts in thousands
    latest = fdic_reports[0]
    return {
        'total_assets': latest.get('ASSET', 0) * 1000,
        'total_deposits': latest.get('DEP', 0) * 1000,
        'net_income': latest.get('NETINC', 0) * 1000,
        'roa': latest.get('ROA', 0),
        'roe': latest.get('ROE', 0),
        'tier1_ratio': latest.get('RBCT1J', 0)
    }
