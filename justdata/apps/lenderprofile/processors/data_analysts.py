#!/usr/bin/env python3
"""
Data Source Analysts for LenderProfile

Multi-agent architecture using Haiku to analyze each data source independently.
Each analyst produces a standardized summary that feeds into the final synthesis.

Tier 1 Analysts (Haiku - fast/cheap):
- SEC Analyst: Business strategy, risk factors, executive compensation
- HMDA Analyst: Mortgage lending patterns, fair lending indicators
- Branch Analyst: Network changes, geographic footprint
- CRA/SB Lending Analyst: Small business lending, community investment
- CFPB Analyst: Consumer complaints, trends, response quality
- News Analyst: Recent coverage, sentiment, regulatory news

Each analyst outputs a standardized DataSourceAnalysis object.
"""

import logging
import json
import os
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

from shared.analysis.ai_provider import ask_ai

# Path to context files
CONTEXT_DIR = Path(__file__).parent / 'context'

logger = logging.getLogger(__name__)


@dataclass
class DataSourceAnalysis:
    """Standardized output from each data source analyst."""
    source: str  # sec, hmda, branches, cra, cfpb, news
    has_data: bool
    data_quality: str  # excellent, good, limited, poor, none
    key_findings: List[str]  # 3-5 bullet points
    ncrc_insights: List[str]  # NCRC-relevant observations
    risk_flags: List[str]  # Concerns or red flags
    positive_indicators: List[str]  # Positive signs
    talking_points: List[str]  # Suggested discussion topics
    metrics: Dict[str, Any]  # Key numbers/stats
    raw_summary: str  # Full text summary for synthesis


class DataSourceAnalysts:
    """
    Orchestrates multiple Haiku analysts to process data sources in parallel.
    """

    # Context file mapping
    CONTEXT_FILES = {
        'sec': 'sec_analyst_context.md',
        'hmda': 'hmda_analyst_context.md',
        'branches': 'branch_analyst_context.md',
        'cra': 'cra_sb_analyst_context.md',
        'cfpb': 'cfpb_analyst_context.md',
        'news': 'news_analyst_context.md',
        'seeking_alpha': None,  # No context file needed - inline prompt
        'congressional': None   # No context file needed - inline prompt
    }

    def __init__(self):
        self.analysts = {
            'sec': self._analyze_sec,
            'hmda': self._analyze_hmda,
            'branches': self._analyze_branches,
            'cra': self._analyze_cra,
            'cfpb': self._analyze_cfpb,
            'news': self._analyze_news,
            'seeking_alpha': self._analyze_seeking_alpha,
            'congressional': self._analyze_congressional
        }
        # Load context files at initialization
        self._contexts = {}
        self._load_contexts()

    def _load_contexts(self):
        """Load analyst context files from disk."""
        for source, filename in self.CONTEXT_FILES.items():
            if filename is None:
                # Some analysts use inline prompts, no context file needed
                self._contexts[source] = ""
                continue
            context_path = CONTEXT_DIR / filename
            try:
                if context_path.exists():
                    self._contexts[source] = context_path.read_text(encoding='utf-8')
                    logger.debug(f"Loaded context for {source}: {len(self._contexts[source])} chars")
                else:
                    logger.warning(f"Context file not found: {context_path}")
                    self._contexts[source] = ""
            except Exception as e:
                logger.error(f"Error loading context for {source}: {e}")
                self._contexts[source] = ""

    def _get_context(self, source: str) -> str:
        """Get context for a specific analyst."""
        return self._contexts.get(source, "")

    def analyze_all(
        self,
        institution_data: Dict[str, Any],
        entity_resolution: Dict[str, Any]
    ) -> Dict[str, DataSourceAnalysis]:
        """
        Run all analysts in parallel and return their findings.

        Args:
            institution_data: Complete collected data
            entity_resolution: AI entity resolution with context

        Returns:
            Dict mapping source name to DataSourceAnalysis
        """
        institution_name = institution_data.get('institution', {}).get('name', 'Unknown')
        corporate_context = entity_resolution.get('corporate_context', {})

        results = {}

        # Run analysts in parallel
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {}

            for source, analyzer in self.analysts.items():
                futures[source] = executor.submit(
                    analyzer,
                    institution_data,
                    institution_name,
                    corporate_context
                )

            for source, future in futures.items():
                try:
                    result = future.result(timeout=30)
                    results[source] = result
                    logger.info(f"Analyst complete: {source} - {result.data_quality} quality, {len(result.key_findings)} findings")
                except Exception as e:
                    logger.error(f"Analyst error ({source}): {e}")
                    results[source] = self._empty_analysis(source)

        return results

    def _call_haiku(self, prompt: str, system_prompt: str) -> str:
        """Make a Haiku API call for fast analysis."""
        try:
            # Include system prompt in main prompt since ask_ai doesn't support system_prompt
            full_prompt = system_prompt + "\n\n" + prompt
            return ask_ai(
                full_prompt,
                model="claude-3-5-haiku-20241022",  # Use Haiku for speed/cost
                max_tokens=1500
            )
        except Exception as e:
            logger.error(f"Haiku call failed: {e}")
            return ""

    def _parse_analysis(self, response: str, source: str) -> DataSourceAnalysis:
        """Parse AI response into DataSourceAnalysis."""
        if not response:
            return self._empty_analysis(source)

        try:
            # Try to parse JSON
            text = response.strip()
            if text.startswith('```'):
                lines = text.split('\n')[1:-1]
                text = '\n'.join(lines)

            data = json.loads(text)

            return DataSourceAnalysis(
                source=source,
                has_data=data.get('has_data', True),
                data_quality=data.get('data_quality', 'unknown'),
                key_findings=data.get('key_findings', [])[:5],
                ncrc_insights=data.get('ncrc_insights', [])[:3],
                risk_flags=data.get('risk_flags', [])[:3],
                positive_indicators=data.get('positive_indicators', [])[:3],
                talking_points=data.get('talking_points', [])[:3],
                metrics=data.get('metrics', {}),
                raw_summary=data.get('summary', '')
            )
        except Exception as e:
            logger.warning(f"Parse error for {source}: {e}")
            # Return response as raw summary
            return DataSourceAnalysis(
                source=source,
                has_data=True,
                data_quality='unknown',
                key_findings=[],
                ncrc_insights=[],
                risk_flags=[],
                positive_indicators=[],
                talking_points=[],
                metrics={},
                raw_summary=response[:2000]
            )

    def _empty_analysis(self, source: str) -> DataSourceAnalysis:
        """Return empty analysis for missing data."""
        return DataSourceAnalysis(
            source=source,
            has_data=False,
            data_quality='none',
            key_findings=['No data available for this source'],
            ncrc_insights=[],
            risk_flags=[],
            positive_indicators=[],
            talking_points=[],
            metrics={},
            raw_summary='No data available'
        )

    # =========================================================================
    # INDIVIDUAL ANALYSTS
    # =========================================================================

    def _analyze_sec(
        self,
        institution_data: Dict[str, Any],
        institution_name: str,
        corporate_context: Dict[str, Any]
    ) -> DataSourceAnalysis:
        """Analyze SEC filings data."""
        sec_data = institution_data.get('sec', {})
        sec_parsed = institution_data.get('sec_parsed', {}) or sec_data.get('parsed', {})

        if not sec_data.get('has_data') and not sec_parsed:
            return self._empty_analysis('sec')

        # Extract key data for prompt
        business_desc = sec_parsed.get('business_description', '')[:2000]
        risk_factors = sec_parsed.get('risk_factors', '')[:2000]
        executives = sec_parsed.get('executives', [])[:5]

        prompt = f"""Analyze this SEC filing data for {institution_name}.

BUSINESS DESCRIPTION (10-K):
{business_desc[:1500] if business_desc else 'Not available'}

RISK FACTORS (10-K):
{risk_factors[:1500] if risk_factors else 'Not available'}

EXECUTIVES (DEF 14A):
{json.dumps(executives, indent=2) if executives else 'Not available'}

Provide analysis in this JSON format:
{{
    "has_data": true,
    "data_quality": "excellent/good/limited/poor",
    "key_findings": ["Finding 1", "Finding 2", "Finding 3"],
    "ncrc_insights": ["NCRC-relevant observation 1", "..."],
    "risk_flags": ["Concern 1", "..."],
    "positive_indicators": ["Positive 1", "..."],
    "talking_points": ["Discussion topic 1", "..."],
    "metrics": {{"key_metric": "value"}},
    "summary": "2-3 sentence executive summary"
}}

Focus on: Business strategy, competitive position, risk exposure, executive compensation, community investment mentions."""

        # Build system prompt with context
        context = self._get_context('sec')
        system_prompt = f"""You are a financial analyst specializing in SEC filings for NCRC (National Community Reinvestment Coalition).

{context}

CRITICAL: Return ONLY valid JSON in the exact format requested. No markdown, no explanations outside JSON."""

        response = self._call_haiku(prompt, system_prompt)

        return self._parse_analysis(response, 'sec')

    def _analyze_hmda(
        self,
        institution_data: Dict[str, Any],
        institution_name: str,
        corporate_context: Dict[str, Any]
    ) -> DataSourceAnalysis:
        """Analyze HMDA mortgage lending data."""
        hmda_data = institution_data.get('hmda_footprint', {})

        if not hmda_data.get('has_data'):
            return self._empty_analysis('hmda')

        by_year = hmda_data.get('by_year', {})
        by_purpose = hmda_data.get('by_purpose_year', {})
        top_states = hmda_data.get('top_states', [])[:10]
        national_by_year = hmda_data.get('national_by_year', {})

        # Calculate market share
        market_shares = {}
        for year, count in by_year.items():
            national = national_by_year.get(year, 1)
            market_shares[year] = round(100 * count / national, 2) if national else 0

        prompt = f"""Analyze HMDA mortgage lending data for {institution_name}.

APPLICATIONS BY YEAR:
{json.dumps(by_year, indent=2)}

MARKET SHARE BY YEAR (%):
{json.dumps(market_shares, indent=2)}

LENDING BY PURPOSE (most recent year):
{json.dumps({k: v.get(max(by_year.keys())) if by_year else 0 for k, v in by_purpose.items()}, indent=2)}

TOP STATES:
{json.dumps(top_states, indent=2)}

Provide analysis in this JSON format:
{{
    "has_data": true,
    "data_quality": "excellent/good/limited/poor",
    "key_findings": ["Finding 1 with specific numbers", "Finding 2", "Finding 3"],
    "ncrc_insights": ["Fair lending observation", "Geographic pattern", "..."],
    "risk_flags": ["Decline in lending?", "Geographic concentration?", "..."],
    "positive_indicators": ["Growing markets?", "Diverse lending?", "..."],
    "talking_points": ["Market position discussion", "..."],
    "metrics": {{"total_applications": X, "market_share": X, "top_state": "XX"}},
    "summary": "2-3 sentence summary of lending footprint"
}}

NCRC Focus: Look for fair lending patterns, underserved market presence, lending declines, geographic redlining indicators."""

        # Build system prompt with context
        context = self._get_context('hmda')
        system_prompt = f"""You are a mortgage lending analyst for NCRC (National Community Reinvestment Coalition).

{context}

CRITICAL: Return ONLY valid JSON in the exact format requested. No markdown, no explanations outside JSON."""

        response = self._call_haiku(prompt, system_prompt)

        return self._parse_analysis(response, 'hmda')

    def _analyze_branches(
        self,
        institution_data: Dict[str, Any],
        institution_name: str,
        corporate_context: Dict[str, Any]
    ) -> DataSourceAnalysis:
        """Analyze branch network data."""
        branch_data = institution_data.get('branches', {})
        branch_network = institution_data.get('branch_network', {})

        # Try both data structures
        trends = branch_network.get('trends', {}) or branch_data.get('trends', {})
        summary = branch_network.get('summary', {}) or branch_data.get('summary', {})

        if not trends.get('by_year') and not summary:
            return self._empty_analysis('branches')

        by_year = trends.get('by_year', {})
        closures = trends.get('closures_by_year', {})
        openings = trends.get('openings_by_year', {})
        by_state = summary.get('by_state', {})

        prompt = f"""Analyze branch network data for {institution_name}.

TOTAL BRANCHES BY YEAR:
{json.dumps(by_year, indent=2)}

CLOSURES BY YEAR:
{json.dumps(closures, indent=2)}

OPENINGS BY YEAR:
{json.dumps(openings, indent=2)}

TOP STATES (branch count):
{json.dumps(dict(list(by_state.items())[:10]) if isinstance(by_state, dict) else {}, indent=2)}

Provide analysis in this JSON format:
{{
    "has_data": true,
    "data_quality": "excellent/good/limited/poor",
    "key_findings": ["Net change trend", "Closure hotspots", "Expansion areas"],
    "ncrc_insights": ["Branch desert concerns", "LMI community impact", "..."],
    "risk_flags": ["Mass closures?", "Abandoning markets?", "..."],
    "positive_indicators": ["Expanding in underserved?", "Stable network?", "..."],
    "talking_points": ["Branch strategy discussion", "..."],
    "metrics": {{"current_branches": X, "net_change": X, "states_count": X}},
    "summary": "2-3 sentence summary of branch network"
}}

NCRC Focus: Branch closures in LMI areas, branch deserts, community access to banking."""

        # Build system prompt with context
        context = self._get_context('branches')
        system_prompt = f"""You are a banking analyst focused on community access for NCRC (National Community Reinvestment Coalition).

{context}

CRITICAL: Return ONLY valid JSON in the exact format requested. No markdown, no explanations outside JSON."""

        response = self._call_haiku(prompt, system_prompt)

        return self._parse_analysis(response, 'branches')

    def _analyze_cra(
        self,
        institution_data: Dict[str, Any],
        institution_name: str,
        corporate_context: Dict[str, Any]
    ) -> DataSourceAnalysis:
        """Analyze CRA/Small Business lending data."""
        sb_data = institution_data.get('sb_lending', {})

        if not sb_data.get('has_data'):
            return self._empty_analysis('cra')

        loan_counts = sb_data.get('lender_loan_counts', [])
        loan_amounts = sb_data.get('lender_loan_amounts', [])
        national_counts = sb_data.get('national_loan_counts', [])
        market_share = sb_data.get('market_share', [])
        by_state = sb_data.get('by_state', {})

        prompt = f"""Analyze CRA Small Business lending data for {institution_name}.

LOAN COUNTS BY YEAR (most recent 5 years):
{json.dumps(loan_counts, indent=2)}

LOAN AMOUNTS BY YEAR ($thousands):
{json.dumps(loan_amounts, indent=2)}

MARKET SHARE BY YEAR (%):
{json.dumps(market_share, indent=2)}

TOP STATES (% of volume):
{json.dumps(dict(list(by_state.items())[:10]) if isinstance(by_state, dict) else {}, indent=2)}

Provide analysis in this JSON format:
{{
    "has_data": true,
    "data_quality": "excellent/good/limited/poor",
    "key_findings": ["Volume trend", "Market position", "Geographic focus"],
    "ncrc_insights": ["Small business support", "Community investment", "..."],
    "risk_flags": ["Declining lending?", "Geographic retreat?", "..."],
    "positive_indicators": ["Growing SB lending?", "Diverse markets?", "..."],
    "talking_points": ["CRA commitment discussion", "..."],
    "metrics": {{"total_loans_5yr": X, "avg_market_share": X}},
    "summary": "2-3 sentence summary of small business lending"
}}

NCRC Focus: CRA performance, small business support in LMI communities, lending trends."""

        # Build system prompt with context
        context = self._get_context('cra')
        system_prompt = f"""You are a CRA/Small Business Lending analyst for NCRC (National Community Reinvestment Coalition).

{context}

CRITICAL: Return ONLY valid JSON in the exact format requested. No markdown, no explanations outside JSON."""

        response = self._call_haiku(prompt, system_prompt)

        return self._parse_analysis(response, 'cra')

    def _analyze_cfpb(
        self,
        institution_data: Dict[str, Any],
        institution_name: str,
        corporate_context: Dict[str, Any]
    ) -> DataSourceAnalysis:
        """Analyze CFPB consumer complaints data."""
        cfpb_data = institution_data.get('cfpb_complaints', {})

        # Also check regulatory_risk for complaints
        if not cfpb_data:
            reg_risk = institution_data.get('regulatory_risk', {})
            cfpb_data = reg_risk.get('complaints', {})

        if not cfpb_data.get('total'):
            return self._empty_analysis('cfpb')

        total = cfpb_data.get('total', 0)
        by_year = cfpb_data.get('by_year', {})
        categories = cfpb_data.get('categories_by_year', {})
        trend = cfpb_data.get('trend', 'stable')

        prompt = f"""Analyze CFPB consumer complaints for {institution_name}.

TOTAL COMPLAINTS: {total:,}

COMPLAINTS BY YEAR:
{json.dumps(by_year, indent=2)}

TREND: {trend}

TOP CATEGORIES (if available):
{json.dumps(list(categories.keys())[:5] if categories else [], indent=2)}

Provide analysis in this JSON format:
{{
    "has_data": true,
    "data_quality": "excellent/good/limited/poor",
    "key_findings": ["Volume assessment", "Trend direction", "Problem areas"],
    "ncrc_insights": ["Consumer protection concerns", "Service quality", "..."],
    "risk_flags": ["Rising complaints?", "Specific issue patterns?", "..."],
    "positive_indicators": ["Declining complaints?", "Good response rate?", "..."],
    "talking_points": ["Consumer satisfaction discussion", "..."],
    "metrics": {{"total_complaints": X, "recent_year": X, "trend": "up/down/stable"}},
    "summary": "2-3 sentence summary of complaint profile"
}}

NCRC Focus: Consumer harm patterns, fair treatment, complaint resolution."""

        # Build system prompt with context
        context = self._get_context('cfpb')
        system_prompt = f"""You are a CFPB Consumer Complaints analyst for NCRC (National Community Reinvestment Coalition).

{context}

CRITICAL: Return ONLY valid JSON in the exact format requested. No markdown, no explanations outside JSON."""

        response = self._call_haiku(prompt, system_prompt)

        return self._parse_analysis(response, 'cfpb')

    def _analyze_news(
        self,
        institution_data: Dict[str, Any],
        institution_name: str,
        corporate_context: Dict[str, Any]
    ) -> DataSourceAnalysis:
        """Analyze recent news coverage."""
        news_data = institution_data.get('news', {})
        recent_news = institution_data.get('recent_news', {})

        articles = news_data.get('articles', []) or recent_news.get('articles', [])

        if not articles:
            return self._empty_analysis('news')

        # Summarize articles for prompt
        article_summaries = []
        for article in articles[:15]:
            article_summaries.append({
                'title': article.get('title', '')[:100],
                'source': article.get('source', {}).get('name', 'Unknown'),
                'category': article.get('ai_relevance', {}).get('category', 'unknown')
            })

        prompt = f"""Analyze recent news coverage for {institution_name}.

RECENT ARTICLES:
{json.dumps(article_summaries, indent=2)}

Provide analysis in this JSON format:
{{
    "has_data": true,
    "data_quality": "excellent/good/limited/poor",
    "key_findings": ["Major story themes", "Coverage sentiment", "Key events"],
    "ncrc_insights": ["Community impact stories", "Regulatory news", "..."],
    "risk_flags": ["Negative coverage?", "Regulatory concerns?", "..."],
    "positive_indicators": ["Positive initiatives?", "Community awards?", "..."],
    "talking_points": ["Current events discussion", "..."],
    "metrics": {{"total_articles": X, "regulatory_count": X, "sentiment": "positive/neutral/negative"}},
    "summary": "2-3 sentence summary of news coverage"
}}

NCRC Focus: Regulatory actions, community impact, fair lending news, merger activity."""

        # Build system prompt with context
        context = self._get_context('news')
        system_prompt = f"""You are a financial news analyst for NCRC (National Community Reinvestment Coalition).

{context}

CRITICAL: Return ONLY valid JSON in the exact format requested. No markdown, no explanations outside JSON."""

        response = self._call_haiku(prompt, system_prompt)

        return self._parse_analysis(response, 'news')

    def _analyze_seeking_alpha(
        self,
        institution_data: Dict[str, Any],
        institution_name: str,
        corporate_context: Dict[str, Any]
    ) -> DataSourceAnalysis:
        """Analyze Seeking Alpha market data and analyst ratings."""
        seeking_alpha_data = institution_data.get('seeking_alpha', {})

        if not seeking_alpha_data or not seeking_alpha_data.get('ticker'):
            return self._empty_analysis('seeking_alpha')

        ticker = seeking_alpha_data.get('ticker', 'N/A')
        ratings = seeking_alpha_data.get('ratings', {})
        financials = seeking_alpha_data.get('financials', [])
        news = seeking_alpha_data.get('news', [])

        # Extract ratings info
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

        # Extract recent news headlines
        news_headlines = []
        for article in news[:5]:
            attrs = article.get('attributes', {})
            news_headlines.append(attrs.get('title', '')[:100])

        prompt = f"""Analyze Seeking Alpha market data for {institution_name} (ticker: {ticker}).

ANALYST RATINGS:
{json.dumps(ratings_data, indent=2)}

RECENT NEWS HEADLINES:
{json.dumps(news_headlines, indent=2)}

Provide analysis in this JSON format:
{{
    "has_data": true,
    "data_quality": "excellent/good/limited/poor",
    "key_findings": ["Analyst sentiment", "Buy/Sell distribution", "Recent news themes"],
    "ncrc_insights": ["Market perception of community focus", "Investor priorities"],
    "risk_flags": ["Negative analyst sentiment?", "Sell recommendations?", "..."],
    "positive_indicators": ["Buy ratings?", "Strong quant score?", "..."],
    "talking_points": ["Market sentiment discussion points", "..."],
    "metrics": {{"quant_rating": X, "buy_count": X, "hold_count": X, "sell_count": X}},
    "summary": "2-3 sentence summary of market positioning and analyst sentiment"
}}

Focus on: Wall Street's view of this institution, analyst recommendations, market sentiment."""

        system_prompt = """You are a financial market analyst helping NCRC understand Wall Street's perspective.

CRITICAL: Return ONLY valid JSON in the exact format requested. No markdown, no explanations outside JSON."""

        response = self._call_haiku(prompt, system_prompt)
        return self._parse_analysis(response, 'seeking_alpha')

    def _analyze_congressional(
        self,
        institution_data: Dict[str, Any],
        institution_name: str,
        corporate_context: Dict[str, Any]
    ) -> DataSourceAnalysis:
        """Analyze congressional stock trading activity."""
        congressional_data = institution_data.get('congressional_trading', {})

        if not congressional_data or not congressional_data.get('has_data'):
            return self._empty_analysis('congressional')

        total_trades = congressional_data.get('total_trades', 0)
        total_purchases = congressional_data.get('total_purchases', 0)
        total_sales = congressional_data.get('total_sales', 0)
        unique_politicians = congressional_data.get('unique_politicians', 0)
        recent_trades = congressional_data.get('recent_trades', [])[:10]

        # Summarize trades
        trade_summaries = []
        for trade in recent_trades:
            trade_summaries.append({
                'politician': trade.get('politician_name', 'Unknown'),
                'type': trade.get('transaction_type', ''),
                'date': trade.get('transaction_date', ''),
                'amount': trade.get('amount_range', '')
            })

        prompt = f"""Analyze congressional stock trading for {institution_name}.

TRADING SUMMARY:
- Total trades: {total_trades}
- Purchases: {total_purchases}
- Sales: {total_sales}
- Unique politicians: {unique_politicians}

RECENT TRADES:
{json.dumps(trade_summaries, indent=2)}

Provide analysis in this JSON format:
{{
    "has_data": true,
    "data_quality": "excellent/good/limited/poor",
    "key_findings": ["Net buying/selling trend", "Notable traders", "Trading patterns"],
    "ncrc_insights": ["Political interest in institution", "Potential regulatory implications"],
    "risk_flags": ["Heavy selling by insiders?", "Unusual trading patterns?", "..."],
    "positive_indicators": ["Buying by politicians?", "Confidence signals?", "..."],
    "talking_points": ["Congressional interest discussion", "..."],
    "metrics": {{"total_trades": {total_trades}, "purchases": {total_purchases}, "sales": {total_sales}}},
    "summary": "2-3 sentence summary of congressional trading sentiment (bullish/bearish)"
}}

Focus on: Is congressional sentiment bullish or bearish? What does this suggest about political perception?"""

        system_prompt = """You are a congressional trading analyst helping NCRC understand political interest in financial institutions.

CRITICAL: Return ONLY valid JSON in the exact format requested. No markdown, no explanations outside JSON."""

        response = self._call_haiku(prompt, system_prompt)
        return self._parse_analysis(response, 'congressional')


def compile_analyst_summaries(analyses: Dict[str, DataSourceAnalysis]) -> Dict[str, Any]:
    """
    Compile all analyst outputs into a format for the final synthesizer.

    Returns:
        Structured summary for the Tier 2 synthesizer
    """
    compiled = {
        'analyst_summaries': {},
        'all_key_findings': [],
        'all_ncrc_insights': [],
        'all_risk_flags': [],
        'all_positive_indicators': [],
        'data_quality_summary': {},
        'generated_at': datetime.now().isoformat()
    }

    for source, analysis in analyses.items():
        # Convert dataclass to dict
        analysis_dict = asdict(analysis) if hasattr(analysis, '__dict__') else analysis

        compiled['analyst_summaries'][source] = {
            'summary': analysis_dict.get('raw_summary', ''),
            'quality': analysis_dict.get('data_quality', 'unknown'),
            'key_findings': analysis_dict.get('key_findings', []),
            'metrics': analysis_dict.get('metrics', {})
        }

        # Aggregate findings with source attribution
        for finding in analysis_dict.get('key_findings', []):
            compiled['all_key_findings'].append(f"[{source.upper()}] {finding}")

        for insight in analysis_dict.get('ncrc_insights', []):
            compiled['all_ncrc_insights'].append(f"[{source.upper()}] {insight}")

        for flag in analysis_dict.get('risk_flags', []):
            compiled['all_risk_flags'].append(f"[{source.upper()}] {flag}")

        for positive in analysis_dict.get('positive_indicators', []):
            compiled['all_positive_indicators'].append(f"[{source.upper()}] {positive}")

        compiled['data_quality_summary'][source] = analysis_dict.get('data_quality', 'unknown')

    return compiled
