"""AI intelligence summary section (high-level prose summary)."""
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

import json
from justdata.apps.lenderprofile.report_builder.helpers import (
    _format_currency,
    _is_recent,
    _truncate_text,
)
from justdata.apps.lenderprofile.report_builder.sections.ai_intelligence_data import (
    _collect_comprehensive_data,
    _generate_comprehensive_key_findings,
)

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
