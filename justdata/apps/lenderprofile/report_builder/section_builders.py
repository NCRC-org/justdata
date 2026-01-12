#!/usr/bin/env python3
"""
Section Builders for LenderProfile Report
Individual builders for each of the 13 report sections.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def build_executive_summary(
    institution_data: Dict[str, Any],
    ai_analyzer,
    report_focus: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build Section 1: Executive Summary.
    
    Args:
        institution_data: Complete institution data
        ai_analyzer: AI analyzer instance
        report_focus: Optional user focus
        
    Returns:
        Executive summary section data
    """
    institution = institution_data.get('institution', {})
    identifiers = institution_data.get('identifiers', {})
    details = institution_data.get('details', {})
    
    # Get data from CFPB metadata (primary source) or GLEIF
    cfpb_metadata = details.get('cfpb_metadata', {})
    corporate_structure = institution_data.get('corporate_structure', {})
    gleif_data = details.get('gleif_data', {})
    
    # Extract key information - use institution dict first (populated by data collector)
    name = institution.get('name') or identifiers.get('name', 'Unknown')
    
    # Institution type from institution dict (set by data collector) or CFPB
    institution_type = institution.get('type') or cfpb_metadata.get('type') or 'Unknown'
    
    # Location from institution dict (set by data collector) or GLEIF
    location = institution.get('location')
    if location:
        # Location is already formatted
        city = ''
        state = ''
    else:
        # Extract from GLEIF corporate structure
        headquarters = corporate_structure.get('headquarters', {}) if corporate_structure else {}
        if not headquarters or not headquarters.get('city'):
            # Fallback to GLEIF entity data
            entity = gleif_data.get('entity', {})
            if entity:
                hq_address = entity.get('headquartersAddress', {})
                headquarters = {
                    'city': hq_address.get('city', ''),
                    'state': hq_address.get('region', '')
                }
        
        city = headquarters.get('city', '') if headquarters else ''
        state = headquarters.get('state', '') if headquarters else ''
        location = f"{city}, {state}" if city and state else (city or state or 'N/A')
    
    # Assets from institution dict (set by data collector) or CFPB or financial data
    assets = institution.get('assets')
    if not assets:
        assets = cfpb_metadata.get('assets')
    if not assets:
        # Try from financial processed data
        financial_processed = institution_data.get('financial', {}).get('processed', {})
        if financial_processed and financial_processed.get('available'):
            metrics = financial_processed.get('metrics', {})
            assets = metrics.get('assets', 0)
    assets = assets or 0
    
    # Format assets
    if assets and assets > 0:
        if assets >= 1000000000:
            assets_display = f"${assets / 1000000000:.2f}B"
        elif assets >= 1000000:
            assets_display = f"${assets / 1000000:.2f}M"
        else:
            assets_display = f"${assets:,.0f}"
    else:
        assets_display = "N/A"
    
    # Get recent enforcement/litigation counts
    enforcement_data = institution_data.get('enforcement', {})
    recent_enforcement = len(enforcement_data.get('recent_actions', []))
    litigation_data = institution_data.get('litigation', {})
    recent_cases = len(litigation_data.get('recent_cases', []))
    
    # Prepare data for AI
    ai_data = {
        'institution': {
            'name': name,
            'type': institution_type,
            'city': city,
            'state': state,
            'assets': assets_display
        },
        'identifiers': identifiers,
        'recent_enforcement': recent_enforcement,
        'recent_cases': recent_cases,
        'cra_rating': institution_data.get('cra', {}).get('current_rating'),
        'financial_trends': institution_data.get('financial', {}).get('trends', {})
    }
    
    # Generate AI summary
    try:
        ai_summary = ai_analyzer.generate_executive_summary(ai_data, report_focus)
        key_findings = ai_analyzer.generate_key_findings(ai_data)
    except Exception as e:
        logger.error(f"Error generating AI summary: {e}", exc_info=True)
        ai_summary = "AI summary generation unavailable."
        key_findings = "AI key findings generation unavailable."
    
    return {
        'institution_name': name,
        'institution_type': institution_type,
        'location': location if 'location' in locals() else (f"{city}, {state}" if city and state else (city or state or 'N/A')),
        'assets': assets_display,
        'fdic_cert': identifiers.get('fdic_cert'),
        'rssd_id': identifiers.get('rssd_id'),
        'lei': identifiers.get('lei'),
        'ai_summary': ai_summary,
        'key_findings': key_findings,
        'risk_indicators': {
            'recent_enforcement': recent_enforcement,
            'recent_cases': recent_cases,
            'has_pending_merger': bool(institution_data.get('mergers', {}).get('pending', []))
        }
    }


def build_corporate_structure(institution_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build Section 2: Corporate Structure.
    
    Args:
        institution_data: Complete institution data
        
    Returns:
        Corporate structure section data
    """
    details = institution_data.get('details', {})
    gleif_data = details.get('gleif_data', {})
    theorg_data = institution_data.get('theorg', {})
    
    # Build entity hierarchy from GLEIF
    hierarchy = []
    if gleif_data:
        entity = gleif_data.get('entity', {})
        if entity:
            hierarchy.append({
                'lei': entity.get('lei'),
                'name': entity.get('legalName', {}).get('name') if isinstance(entity.get('legalName'), dict) else entity.get('legalName'),
                'status': entity.get('status'),
                'type': 'entity'
            })
    
    return {
        'legal_hierarchy': hierarchy,
        'operational_org_chart': theorg_data.get('org_chart'),
        'has_org_chart': bool(theorg_data.get('org_chart')),
        'parent_entities': gleif_data.get('parent', []),
        'subsidiaries': gleif_data.get('children', [])
    }


def build_financial_profile(institution_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build Section 3: Financial Profile.
    
    Args:
        institution_data: Complete institution data
        
    Returns:
        Financial profile section data
    """
    financial_data = institution_data.get('financial', {})
    fdic_financials = financial_data.get('fdic_call_reports', [])
    
    # Process 5-year financial trends
    trends = {
        'assets': [],
        'equity': [],
        'net_income': [],
        'roa': [],
        'roe': [],
        'years': []
    }
    
    if fdic_financials:
        # Sort by date and extract last 5 years
        sorted_financials = sorted(fdic_financials, key=lambda x: x.get('REPDTE', ''), reverse=True)[:20]  # Last 20 quarters = 5 years
        
        for record in sorted_financials:
            year = record.get('REPDTE', '')[:4] if record.get('REPDTE') else None
            if year:
                trends['years'].append(year)
                trends['assets'].append(record.get('ASSET', 0))
                trends['equity'].append(record.get('EQ', 0))
                trends['net_income'].append(record.get('NETINC', 0))
                trends['roa'].append(record.get('ROA', 0))
                trends['roe'].append(record.get('ROE', 0))
    
    return {
        'trends': trends,
        'latest_quarter': fdic_financials[0] if fdic_financials else {},
        'peer_comparison': financial_data.get('peer_comparison', {}),
        'business_model': financial_data.get('business_model', 'Unknown')
    }


def build_branch_network(institution_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build Section 4: Branch Network and Market Presence.
    
    Args:
        institution_data: Complete institution data
        
    Returns:
        Branch network section data
    """
    branch_data = institution_data.get('branches', {})
    branch_analysis = branch_data.get('analysis', {})
    branches = branch_data.get('locations', [])
    summary = branch_data.get('summary', {})
    
    # Get data from branch analysis if available
    if branch_analysis:
        summary_data = branch_analysis.get('summary', {})
        total_branches_by_year = summary_data.get('total_branches_by_year', {})
        trends = summary_data.get('trends', {})
        geographic_shifts = summary_data.get('geographic_shifts', {})
        
        # Get current year total
        current_year = max(total_branches_by_year.keys()) if total_branches_by_year else None
        total_branches = total_branches_by_year.get(current_year, len(branches)) if current_year else len(branches)
        
        # Group branches by state and CBSA for map visualization
        by_state = {}
        by_cbsa = {}
        cbsa_coordinates = {}  # For map markers
        
        for branch in branches:
            state = branch.get('state') or branch.get('STALP') or branch.get('state_abbr', 'Unknown')
            if state not in by_state:
                by_state[state] = 0
            by_state[state] += 1
            
            cbsa_name = branch.get('cbsa_name') or branch.get('CBSA_METRO_NAME', '')
            if cbsa_name:
                if cbsa_name not in by_cbsa:
                    by_cbsa[cbsa_name] = 0
                by_cbsa[cbsa_name] += 1
                
                # Store coordinates for map (use first branch in each CBSA)
                if cbsa_name not in cbsa_coordinates:
                    lat = branch.get('latitude') or branch.get('LATITUDE')
                    lon = branch.get('longitude') or branch.get('LONGITUDE')
                    if lat and lon:
                        cbsa_coordinates[cbsa_name] = {
                            'lat': float(lat),
                            'lon': float(lon),
                            'count': 1
                        }
                    else:
                        cbsa_coordinates[cbsa_name] = {'count': 1}
                else:
                    cbsa_coordinates[cbsa_name]['count'] += 1
        
        return {
            'total_branches': total_branches,
            'total_branches_by_year': total_branches_by_year,
            'by_state': by_state,
            'by_cbsa': by_cbsa,
            'cbsa_coordinates': cbsa_coordinates,
            'branches': branches[:500],  # Limit for display but more than before
            'trends': trends,
            'geographic_shifts': geographic_shifts,
            'closures_by_year': branch_analysis.get('closures_by_year', {}),
            'openings_by_year': branch_analysis.get('openings_by_year', {}),
            'net_change_by_year': branch_analysis.get('net_change_by_year', {}),
            'years_analyzed': branch_analysis.get('years_analyzed', [])
        }
    else:
        # Fallback if no analysis available
        total_branches = len(branches)
        by_state = {}
        by_cbsa = {}
        
        for branch in branches:
            state = branch.get('state') or branch.get('STALP') or branch.get('STATE', 'Unknown')
            if state not in by_state:
                by_state[state] = 0
            by_state[state] += 1
            
            cbsa_name = branch.get('cbsa_name') or branch.get('CBSA_METRO_NAME', '')
            if cbsa_name:
                if cbsa_name not in by_cbsa:
                    by_cbsa[cbsa_name] = 0
                by_cbsa[cbsa_name] += 1
        
        return {
            'total_branches': total_branches,
            'by_state': by_state,
            'by_cbsa': by_cbsa,
            'branches': branches[:100],
            'trends': {},
            'geographic_shifts': {}
        }


def build_cra_performance(
    institution_data: Dict[str, Any],
    ai_analyzer
) -> Dict[str, Any]:
    """
    Build Section 5: CRA Performance.
    
    Args:
        institution_data: Complete institution data
        ai_analyzer: AI analyzer instance
        
    Returns:
        CRA performance section data
    """
    cra_data = institution_data.get('cra', {})
    
    # Get current rating
    current_rating = cra_data.get('current_rating', 'N/A')
    exam_date = cra_data.get('exam_date')
    
    # Get rating history
    rating_history = cra_data.get('rating_history', [])
    
    # Get test-level ratings
    test_ratings = {
        'lending': cra_data.get('lending_test_rating'),
        'investment': cra_data.get('investment_test_rating'),
        'service': cra_data.get('service_test_rating')
    }
    
    # Generate AI summary
    try:
        section_data = {
            'current_rating': current_rating,
            'exam_date': exam_date,
            'rating_history': rating_history,
            'test_ratings': test_ratings,
            'examiner_findings': cra_data.get('examiner_findings', {})
        }
        ai_summary = ai_analyzer.generate_section_summary('CRA Performance', section_data)
    except Exception as e:
        logger.error(f"Error generating CRA AI summary: {e}", exc_info=True)
        ai_summary = "AI summary unavailable."
    
    return {
        'current_rating': current_rating,
        'exam_date': exam_date,
        'rating_history': rating_history,
        'test_ratings': test_ratings,
        'examiner_findings': cra_data.get('examiner_findings', {}),
        'ai_summary': ai_summary,
        'community_development_totals': cra_data.get('community_development', {})
    }


def _calculate_rating_trend(rating_history: List[Dict[str, Any]]) -> str:
    """Calculate rating trend from history (helper function)."""
    if not rating_history or len(rating_history) < 2:
        return 'insufficient_data'
    
    # Get most recent two ratings
    sorted_history = sorted(rating_history, key=lambda x: x.get('date', ''), reverse=True)
    recent = sorted_history[0].get('rating', '').upper()
    previous = sorted_history[1].get('rating', '').upper()
    
    rating_order = {'OUTSTANDING': 4, 'SATISFACTORY': 3, 'NEEDS TO IMPROVE': 2, 'SUBSTANTIAL NONCOMPLIANCE': 1}
    recent_val = rating_order.get(recent, 0)
    previous_val = rating_order.get(previous, 0)
    
    if recent_val > previous_val:
        return 'improving'
    elif recent_val < previous_val:
        return 'declining'
    else:
        return 'stable'


def build_regulatory_history(
    institution_data: Dict[str, Any],
    ai_analyzer
) -> Dict[str, Any]:
    """
    Build Section 6: Regulatory and Legal History.
    
    Args:
        institution_data: Complete institution data
        ai_analyzer: AI analyzer instance
        
    Returns:
        Regulatory history section data
    """
    enforcement_data = institution_data.get('enforcement', {})
    litigation_data = institution_data.get('litigation', {})
    cfpb_complaints = institution_data.get('cfpb_complaints', {})
    
    # Categorize enforcement actions
    actions_by_agency = {
        'CFPB': [],
        'OCC': [],
        'Fed': [],
        'FDIC': [],
        'HUD': [],
        'DOJ': []
    }
    
    all_actions = enforcement_data.get('actions', [])
    for action in all_actions:
        agency = action.get('agency', 'Unknown')
        if agency in actions_by_agency:
            actions_by_agency[agency].append(action)
    
    # Categorize violations
    violation_types = {
        'fair_lending': [],
        'udaap': [],
        'bsa': [],
        'safety_soundness': []
    }
    
    for action in all_actions:
        violations = action.get('violations', [])
        for violation in violations:
            v_type = (violation.get('type') or '').lower()
            if 'fair lending' in v_type or 'discrimination' in v_type:
                violation_types['fair_lending'].append(action)
            elif 'udaap' in v_type or 'unfair' in v_type:
                violation_types['udaap'].append(action)
            elif 'bsa' in v_type or 'bank secrecy' in v_type:
                violation_types['bsa'].append(action)
            elif 'safety' in v_type or 'soundness' in v_type:
                violation_types['safety_soundness'].append(action)
    
    # Extract consumer complaint trends and topics
    complaint_trends = {}
    main_topics = []
    main_products = []
    total_complaints = 0
    
    if cfpb_complaints:
        total_complaints = cfpb_complaints.get('total', 0)
        trends = cfpb_complaints.get('trends', {})
        if trends:
            complaint_trends = {
                'recent_trend': trends.get('recent_trend', 'stable'),  # 'increasing', 'decreasing', 'stable'
                'by_year': trends.get('by_year', {}),
                'year_over_year_changes': trends.get('year_over_year_changes', {}),
                'most_recent_year': trends.get('most_recent_year'),
                'most_recent_count': trends.get('most_recent_count', 0)
            }
        main_topics = cfpb_complaints.get('main_topics', [])
        main_products = cfpb_complaints.get('main_products', [])
    
    # Generate AI summary
    try:
        section_data = {
            'actions_by_agency': actions_by_agency,
            'violation_types': violation_types,
            'litigation_cases': litigation_data.get('cases', []),
            'consumer_complaints': {
                'total': total_complaints,
                'trends': complaint_trends,
                'main_topics': main_topics[:5],  # Top 5 topics
                'main_products': main_products[:5]  # Top 5 products
            }
        }
        ai_summary = ai_analyzer.generate_section_summary('Regulatory and Legal History', section_data)
    except Exception as e:
        logger.error(f"Error generating regulatory history AI summary: {e}", exc_info=True)
        ai_summary = "AI summary unavailable."
    
    return {
        'actions_by_agency': actions_by_agency,
        'violation_types': violation_types,
        'total_actions': len(all_actions),
        'litigation_cases': litigation_data.get('cases', []),
        'total_cases': len(litigation_data.get('cases', [])),
        'consumer_complaints': {
            'total': total_complaints,
            'trends': complaint_trends,
            'main_topics': main_topics,
            'main_products': main_products,
            'trend_description': _format_complaint_trend(complaint_trends)
        },
        'ai_summary': ai_summary,
        'timeline': enforcement_data.get('timeline', [])
    }


def _format_complaint_trend(trends: Dict[str, Any]) -> str:
    """
    Format complaint trend into a readable description.
    
    Args:
        trends: Trend data dictionary
        
    Returns:
        Formatted trend description
    """
    if not trends or not trends.get('recent_trend'):
        return "Insufficient data to determine trend."
    
    recent_trend = trends.get('recent_trend', 'stable')
    by_year = trends.get('by_year', {})
    most_recent_year = trends.get('most_recent_year')
    most_recent_count = trends.get('most_recent_count', 0)
    
    if not by_year or len(by_year) < 2:
        return f"Total of {sum(by_year.values())} complaints recorded."
    
    # Get last two years for comparison
    sorted_years = sorted(by_year.keys())
    if len(sorted_years) >= 2:
        prev_year = sorted_years[-2]
        curr_year = sorted_years[-1]
        prev_count = by_year[prev_year]
        curr_count = by_year[curr_year]
        
        if prev_count > 0:
            change_pct = ((curr_count - prev_count) / prev_count) * 100
            direction = "increased" if change_pct > 0 else "decreased" if change_pct < 0 else "remained stable"
            return f"Complaints {direction} by {abs(change_pct):.1f}% from {prev_year} ({prev_count}) to {curr_year} ({curr_count})."
    
    return f"Total of {sum(by_year.values())} complaints across {len(by_year)} years, with {most_recent_count} in {most_recent_year}."


def build_strategic_positioning(
    institution_data: Dict[str, Any],
    ai_analyzer,
    report_focus: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build Section 7: Strategic Positioning.
    
    Args:
        institution_data: Complete institution data
        ai_analyzer: AI analyzer instance
        report_focus: Optional user focus
        
    Returns:
        Strategic positioning section data
    """
    sec_data = institution_data.get('sec', {})
    filings = sec_data.get('filings', {})
    
    # Handle filings - it might be a dict with keys like '10k', '10q', etc.
    # or it might be structured differently
    if isinstance(filings, dict):
        # Extract 10-K business description
        tenk_data = filings.get('10k', {})
        if isinstance(tenk_data, list) and len(tenk_data) > 0:
            # If it's a list of filings, get the first one
            tenk_data = tenk_data[0] if isinstance(tenk_data[0], dict) else {}
        elif not isinstance(tenk_data, dict):
            tenk_data = {}
        
        business_description = tenk_data.get('business_description', '')
        risk_factors = tenk_data.get('risk_factors', [])
    else:
        business_description = ''
        risk_factors = []
    
    # Get executive profiles
    executives = sec_data.get('executives', [])
    
    # Generate AI summary of business strategy
    try:
        section_data = {
            'business_description': business_description,
            'risk_factors': risk_factors[:5],  # Top 5
            'executives': executives
        }
        ai_summary = ai_analyzer.generate_section_summary('Strategic Positioning', section_data, report_focus)
    except Exception as e:
        logger.error(f"Error generating strategic positioning AI summary: {e}", exc_info=True)
        ai_summary = "AI summary unavailable."
    
    return {
        'business_description': business_description,
        'risk_factors': risk_factors[:5],
        'executives': executives,
        'board_composition': sec_data.get('board', []),
        'ai_summary': ai_summary,
        'recent_initiatives': sec_data.get('recent_initiatives', [])
    }


def build_organizational_analysis(institution_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build Section 7B: Organizational Analysis (TheOrg data).
    
    Args:
        institution_data: Complete institution data
        
    Returns:
        Organizational analysis section data
    """
    theorg_data = institution_data.get('theorg', {})
    
    if not theorg_data or not theorg_data.get('org_chart'):
        return {
            'available': False,
            'message': 'Organizational data not available for this institution.'
        }
    
    org_chart = theorg_data.get('org_chart', {})
    people = theorg_data.get('people', [])
    
    # Analyze department sizing
    departments = {}
    for person in people:
        dept = person.get('department', 'Unknown')
        if dept not in departments:
            departments[dept] = 0
        departments[dept] += 1
    
    return {
        'available': True,
        'org_chart': org_chart,
        'total_people': len(people),
        'departments': departments,
        'reporting_structure': theorg_data.get('reporting_structure', {}),
        'recent_changes': theorg_data.get('recent_changes', [])
    }


def build_merger_activity(institution_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build Section 8: Merger and Acquisition Activity.
    
    Args:
        institution_data: Complete institution data
        
    Returns:
        Merger activity section data
    """
    merger_data = institution_data.get('mergers', {})
    
    historical = merger_data.get('historical', [])
    pending = merger_data.get('pending', [])
    
    return {
        'historical_acquisitions': historical,
        'pending_applications': pending,
        'total_historical': len(historical),
        'total_pending': len(pending),
        'market_impact': merger_data.get('market_impact', {}),
        'expected_branch_closures': merger_data.get('expected_closures', [])
    }


def build_market_context(institution_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build Section 9: Market Context and Competitive Position.
    
    Args:
        institution_data: Complete institution data
        
    Returns:
        Market context section data
    """
    market_data = institution_data.get('market', {})
    
    return {
        'asset_ranking': {
            'national': market_data.get('national_ranking'),
            'regional': market_data.get('regional_ranking')
        },
        'deposit_market_share': market_data.get('deposit_share', {}),
        'peer_group': market_data.get('peer_group', []),
        'hhi_scores': market_data.get('hhi', {}),
        'performance_vs_peers': market_data.get('peer_performance', {})
    }


def build_recent_developments(
    institution_data: Dict[str, Any],
    ai_analyzer
) -> Dict[str, Any]:
    """
    Build Section 10: Recent Developments and News.
    
    Args:
        institution_data: Complete institution data
        ai_analyzer: AI analyzer instance
        
    Returns:
        Recent developments section data
    """
    news_data = institution_data.get('news', {})
    articles = news_data.get('articles', [])
    
    # Categorize articles
    categories = {
        'enforcement': [],
        'merger': [],
        'strategic': [],
        'controversy': []
    }
    
    for article in articles:
        # Handle None values safely
        title = (article.get('title') or '').lower()
        description = (article.get('description') or '').lower()
        text = f"{title} {description}"
        
        if any(word in text for word in ['enforcement', 'cfpb', 'consent order', 'penalty']):
            categories['enforcement'].append(article)
        elif any(word in text for word in ['merger', 'acquisition', 'acquire']):
            categories['merger'].append(article)
        elif any(word in text for word in ['strategy', 'expansion', 'initiative', 'launch']):
            categories['strategic'].append(article)
        elif any(word in text for word in ['controversy', 'lawsuit', 'scandal', 'investigation']):
            categories['controversy'].append(article)
        else:
            categories['strategic'].append(article)  # Default
    
    # Generate timeline
    timeline = []
    for article in articles:
        published = article.get('publishedAt', '')
        if published:
            timeline.append({
                'date': published,
                'title': article.get('title'),
                'category': 'enforcement' if article in categories['enforcement'] else
                           'merger' if article in categories['merger'] else
                           'controversy' if article in categories['controversy'] else 'strategic'
            })
    
    timeline.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    return {
        'articles': articles[:20],  # Limit to 20 most recent
        'total_articles': len(articles),
        'categories': categories,
        'timeline': timeline[:30],  # Last 30 items
        'major_events': news_data.get('major_events', []),
        'regulatory_proposals': institution_data.get('regulatory_proposals', [])
    }


def build_regulatory_engagement(
    institution_data: Dict[str, Any],
    ai_analyzer
) -> Dict[str, Any]:
    """
    Build Section 11: Regulatory Engagement and Policy Positions.
    
    Args:
        institution_data: Complete institution data
        ai_analyzer: AI analyzer instance
        
    Returns:
        Regulatory engagement section data
    """
    regulations_data = institution_data.get('regulations', {})
    comment_letters = regulations_data.get('comment_letters', [])
    
    # Categorize by topic
    topics = {
        'cra_reform': [],
        'capital_rules': [],
        'fair_lending': [],
        'dodd_frank': []
    }
    
    for letter in comment_letters:
        topic = (letter.get('topic') or '').lower()
        if 'cra' in topic:
            topics['cra_reform'].append(letter)
        elif 'capital' in topic:
            topics['capital_rules'].append(letter)
        elif 'fair lending' in topic or 'discrimination' in topic:
            topics['fair_lending'].append(letter)
        elif 'dodd' in topic or 'frank' in topic:
            topics['dodd_frank'].append(letter)
    
    # Generate AI summary
    try:
        section_data = {
            'comment_letters': comment_letters,
            'topics': topics,
            'trade_associations': regulations_data.get('trade_associations', [])
        }
        ai_summary = ai_analyzer.generate_section_summary('Regulatory Engagement', section_data)
    except Exception as e:
        logger.error(f"Error generating regulatory engagement AI summary: {e}", exc_info=True)
        ai_summary = "AI summary unavailable."
    
    return {
        'comment_letters': comment_letters,
        'topics': topics,
        'trade_associations': regulations_data.get('trade_associations', []),
        'advocacy_priorities': regulations_data.get('advocacy_priorities', []),
        'ai_summary': ai_summary
    }


def build_advocacy_intelligence(
    institution_data: Dict[str, Any],
    ai_analyzer,
    report_focus: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build Section 12: Advocacy Intelligence Summary.
    
    Args:
        institution_data: Complete institution data
        ai_analyzer: AI analyzer instance
        report_focus: Optional user focus
        
    Returns:
        Advocacy intelligence section data
    """
    # Generate AI-powered advocacy intelligence
    try:
        ai_analysis = ai_analyzer.generate_advocacy_intelligence(institution_data, report_focus)
    except Exception as e:
        logger.error(f"Error generating advocacy intelligence: {e}", exc_info=True)
        ai_analysis = "AI analysis unavailable."
    
    # Calculate scores (placeholder - will be enhanced)
    cra_data = institution_data.get('cra', {})
    current_rating = cra_data.get('current_rating', 'Unknown')
    
    # CBA opportunity score (0-100)
    cba_score = 0
    if current_rating in ['Outstanding', 'Satisfactory']:
        cba_score = 60
    if current_rating == 'Outstanding':
        cba_score = 80
    
    # Merger opposition score (0-100)
    merger_score = 0
    pending_mergers = institution_data.get('mergers', {}).get('pending', [])
    if pending_mergers:
        merger_score = 50
    if current_rating in ['Needs to Improve', 'Substantial Noncompliance']:
        merger_score += 30
    
    # Partnership score (0-100)
    partnership_score = 0
    if current_rating == 'Outstanding':
        partnership_score = 70
    elif current_rating == 'Satisfactory':
        partnership_score = 50
    
    return {
        'ai_analysis': ai_analysis,
        'overall_assessment': 'monitor',  # Will be determined by AI
        'cba_opportunity': {
            'score': cba_score,
            'status': cra_data.get('cba_status'),
            'expiration': cra_data.get('cba_expiration')
        },
        'merger_opposition': {
            'score': merger_score,
            'pending_applications': len(pending_mergers)
        },
        'partnership_opportunity': {
            'score': partnership_score
        },
        'priority_concerns': institution_data.get('priority_concerns', []),
        'recommended_approach': institution_data.get('recommended_approach', {})
    }

