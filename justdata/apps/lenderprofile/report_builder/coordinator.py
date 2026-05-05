"""LenderProfile report builder coordinator (orchestrates all sections)."""
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from justdata.apps.lenderprofile.report_builder.sections.ai_intelligence_summary import build_ai_intelligence_summary
from justdata.apps.lenderprofile.report_builder.sections.branch_network import build_branch_network
from justdata.apps.lenderprofile.report_builder.sections.business_strategy import build_business_strategy
from justdata.apps.lenderprofile.report_builder.sections.community_investment import build_community_investment
from justdata.apps.lenderprofile.report_builder.sections.congressional_trading import build_congressional_trading
from justdata.apps.lenderprofile.report_builder.sections.corporate_structure import build_corporate_structure
from justdata.apps.lenderprofile.report_builder.sections.financial_performance import build_financial_performance
from justdata.apps.lenderprofile.report_builder.sections.header import build_institution_header
from justdata.apps.lenderprofile.report_builder.sections.leadership import build_leadership_section
from justdata.apps.lenderprofile.report_builder.sections.lending_footprint import build_lending_footprint
from justdata.apps.lenderprofile.report_builder.sections.merger_activity import build_merger_activity
from justdata.apps.lenderprofile.report_builder.sections.recent_news import build_recent_news
from justdata.apps.lenderprofile.report_builder.sections.regulatory_risk import build_regulatory_risk
from justdata.apps.lenderprofile.report_builder.sections.risk_factors import build_risk_factors
from justdata.apps.lenderprofile.report_builder.sections.sb_lending import build_sb_lending
from justdata.apps.lenderprofile.report_builder.sections.sec_filings import build_sec_filings_analysis
from justdata.apps.lenderprofile.report_builder.sections.seeking_alpha import build_seeking_alpha_section

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



