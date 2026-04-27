"""Report generation modules for LenderProfile.

Public API:
    build_complete_report_v2  -- coordinator that orchestrates all section builders
    ReportBuilder             -- thin wrapper class used by blueprint.py

Each section builder (build_business_strategy, build_financial_performance, ...)
is also re-exported for direct use from tests and downstream callers.
"""
from justdata.apps.lenderprofile.report_builder.coordinator import build_complete_report_v2
from justdata.apps.lenderprofile.report_builder.sections.ai_intelligence_summary import (
    build_ai_intelligence_summary,
)
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

__all__ = [
    "build_complete_report_v2",
    "build_ai_intelligence_summary",
    "build_branch_network",
    "build_business_strategy",
    "build_community_investment",
    "build_congressional_trading",
    "build_corporate_structure",
    "build_financial_performance",
    "build_institution_header",
    "build_leadership_section",
    "build_lending_footprint",
    "build_merger_activity",
    "build_recent_news",
    "build_regulatory_risk",
    "build_risk_factors",
    "build_sb_lending",
    "build_sec_filings_analysis",
    "build_seeking_alpha_section",
]
