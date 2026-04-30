"""AI intelligence data collection and key-findings prompt builder."""
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

import json
from justdata.apps.lenderprofile.report_builder.helpers import (
    _calculate_growth,
    _format_currency,
    _is_recent,
    _truncate_text,
)

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
            from justdata.apps.lenderprofile.processors.sec_topic_extractor import SECTopicExtractor
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
        from justdata.shared.analysis.ai_provider import ask_ai
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


