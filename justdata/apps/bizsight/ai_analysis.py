#!/usr/bin/env python3
"""
BizSight AI Analysis Module
Generates AI-powered narratives for BizSight reports.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add repo root to path
REPO_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(REPO_ROOT))

from justdata.apps.bizsight.utils.ai_provider import AIProvider


class BizSightAnalyzer:
    """AI analyzer for BizSight small business lending reports."""

    def __init__(self):
        self.ai = AIProvider()

    def _get_data_source_context(self) -> str:
        """Return context about what Section 1071 small business lending data represents."""
        return """
        DATA SOURCE CONTEXT - Section 1071 Small Business Lending:
        This report uses Section 1071 data, which tracks small business lending (NOT mortgage lending).

        KEY DISTINCTIONS:
        - This is SMALL BUSINESS lending data (loans to businesses), not consumer/mortgage lending
        - Loan size categories: Under $100K, $100K-$250K, $250K-$1M
        - Data includes: Number of loans, dollar amounts, lender information
        - Geographic breakdown: By census tract income level and minority population
        - Time period may include PPP (Paycheck Protection Program) effects in 2020-2021

        TERMINOLOGY:
        - "Small business loans" = loans to businesses, NOT mortgages
        - "LMI tracts" = Low-to-Moderate Income census tracts (median family income below 80% of area median)
        - "Businesses with revenue under $1M" = smaller businesses that may have more difficulty accessing credit
        - Do NOT confuse with mortgage lending, homeownership, or consumer credit data

        PLAIN ENGLISH REQUIREMENTS:
        - Write for a general audience unfamiliar with banking regulations
        - Explain acronyms and technical terms in simple language
        - Use "small business loans" not "SB loans" or "1071 loans"
        - Use "low-to-moderate income areas" not just "LMI tracts"
        """

    def generate_county_summary_number_discussion(self, data: Dict[str, Any]) -> str:
        """
        Generate 1 paragraph discussing the County Summary NUMBER of loans table (Section 2, Table 1).
        """
        county_name = data.get('county_name', 'the selected county')
        years = data.get('years', [])
        year_range = f"{min(years)}-{max(years)}" if years else "the selected period"
        summary_data = data.get('county_summary_table', [])

        if not summary_data or len(summary_data) == 0:
            return ""

        prompt = f"""
        Generate exactly 1 paragraph (3-5 sentences) discussing the NUMBER of small business loans in {county_name} from {year_range}.

        IMPORTANT: Focus ONLY on the NUMBER of loans, not dollar amounts.

        County: {county_name}
        Years: {year_range}
        Data: {json.dumps(summary_data, indent=2)[:1500] if summary_data else 'Not available'}

        REQUIREMENTS:
        - EXACTLY 1 PARAGRAPH (3-5 sentences maximum)
        - Focus on loan COUNT trends over time
        - Discuss how total loan numbers changed year-over-year
        - Mention patterns in loan size categories (under $100K, $100K-$250K, $250K-$1M) by count
        - Plain English, no jargon
        - Third-person, objective tone
        - NO policy recommendations or speculation
        """

        return self.ai.generate_text(prompt, max_tokens=300, temperature=0.3)

    def generate_county_summary_amount_discussion(self, data: Dict[str, Any]) -> str:
        """
        Generate 1 paragraph discussing the County Summary AMOUNT of loans table (Section 2, Table 2).
        """
        county_name = data.get('county_name', 'the selected county')
        years = data.get('years', [])
        year_range = f"{min(years)}-{max(years)}" if years else "the selected period"
        summary_data = data.get('county_summary_table', [])

        if not summary_data or len(summary_data) == 0:
            return ""

        prompt = f"""
        Generate exactly 1 paragraph (3-5 sentences) discussing the DOLLAR AMOUNTS of small business loans in {county_name} from {year_range}.

        IMPORTANT: Focus ONLY on loan AMOUNTS (dollars), not the number of loans.

        County: {county_name}
        Years: {year_range}
        Data: {json.dumps(summary_data, indent=2)[:1500] if summary_data else 'Not available'}

        REQUIREMENTS:
        - EXACTLY 1 PARAGRAPH (3-5 sentences maximum)
        - Focus on dollar amount trends over time
        - Discuss how total lending volume changed year-over-year
        - Mention patterns in loan size categories by dollar amount
        - Note any PPP-related spikes in 2020-2021 if visible
        - Plain English, no jargon
        - Third-person, objective tone
        - NO policy recommendations or speculation
        """

        return self.ai.generate_text(prompt, max_tokens=300, temperature=0.3)

    def generate_county_summary_discussion(self, data: Dict[str, Any]) -> str:
        """
        Legacy method - kept for backward compatibility.
        Generate 2 paragraphs discussing BOTH county summary tables (Section 2).
        """
        county_name = data.get('county_name', 'the selected county')
        years = data.get('years', [])
        year_range = f"{min(years)}-{max(years)}" if years else "the selected period"
        summary_data = data.get('county_summary_table', [])

        if not summary_data or len(summary_data) == 0:
            return ""

        summary = summary_data[0] if isinstance(summary_data, list) else summary_data

        prompt = f"""
        Generate exactly 2 paragraphs discussing small business lending patterns in {county_name} from {year_range}.

        IMPORTANT: This is SMALL BUSINESS LENDING DATA, not mortgage lending data.

        County: {county_name}
        Years: {year_range}
        Summary Data: {json.dumps(summary, indent=2)[:1500] if summary else 'Not available'}

        REQUIREMENTS:
        - EXACTLY 2 PARAGRAPHS
        - First paragraph: Discuss NUMBER of loans and trends
        - Second paragraph: Discuss AMOUNTS and any notable patterns
        - Plain English, no jargon
        - Third-person, objective tone
        - NO policy recommendations or speculation
        """

        return self.ai.generate_text(prompt, max_tokens=600, temperature=0.3)

    def generate_comparison_number_discussion(self, data: Dict[str, Any]) -> str:
        """
        Generate 1 paragraph discussing the Comparison NUMBER of loans table (Section 3, Table 1).
        """
        county_name = data.get('county_name', 'the selected county')
        state_name = data.get('state_name', 'the state')
        comparison_data = data.get('comparison_table', [])

        if not comparison_data:
            return ""

        prompt = f"""
        Generate exactly 1 paragraph (3-5 sentences) comparing {county_name}'s NUMBER of small business loans to {state_name} state and national averages for 2024.

        IMPORTANT: Focus ONLY on the NUMBER of loans, not dollar amounts.

        County: {county_name}
        State: {state_name}
        Data: {json.dumps(comparison_data, indent=2)[:1500]}

        REQUIREMENTS:
        - EXACTLY 1 PARAGRAPH (3-5 sentences maximum)
        - Focus on loan COUNT comparisons
        - Compare county to state and national benchmarks
        - Identify whether county is higher, lower, or similar
        - Plain English, no jargon
        - Third-person, objective tone
        - NO policy recommendations or speculation
        """

        return self.ai.generate_text(prompt, max_tokens=300, temperature=0.3)

    def generate_comparison_amount_discussion(self, data: Dict[str, Any]) -> str:
        """
        Generate 1 paragraph discussing the Comparison AMOUNT of loans table (Section 3, Table 2).
        """
        county_name = data.get('county_name', 'the selected county')
        state_name = data.get('state_name', 'the state')
        comparison_data = data.get('comparison_table', [])

        if not comparison_data:
            return ""

        prompt = f"""
        Generate exactly 1 paragraph (3-5 sentences) comparing {county_name}'s small business loan DOLLAR AMOUNTS to {state_name} state and national averages for 2024.

        IMPORTANT: Focus ONLY on loan AMOUNTS (dollars), not the number of loans.

        County: {county_name}
        State: {state_name}
        Data: {json.dumps(comparison_data, indent=2)[:1500]}

        REQUIREMENTS:
        - EXACTLY 1 PARAGRAPH (3-5 sentences maximum)
        - Focus on dollar amount comparisons
        - Compare county lending volume to state and national benchmarks
        - Identify whether county is higher, lower, or similar
        - Plain English, no jargon
        - Third-person, objective tone
        - NO policy recommendations or speculation
        """

        return self.ai.generate_text(prompt, max_tokens=300, temperature=0.3)

    def generate_comparison_discussion(self, data: Dict[str, Any]) -> str:
        """Legacy method for backward compatibility."""
        county_name = data.get('county_name', 'the selected county')
        state_name = data.get('state_name', 'the state')
        comparison_data = data.get('comparison_table', [])

        if not comparison_data:
            return ""

        prompt = f"""
        Generate exactly 2 paragraphs comparing {county_name}'s 2024 small business lending to {state_name} state and national averages.

        Data: {json.dumps(comparison_data, indent=2)[:2000]}

        REQUIREMENTS:
        - EXACTLY 2 PARAGRAPHS
        - First paragraph: Compare NUMBER of loans
        - Second paragraph: Compare AMOUNTS
        - Plain English, third-person, objective tone
        """

        return self.ai.generate_text(prompt, max_tokens=600, temperature=0.3)

    def generate_top_lenders_number_discussion(self, data: Dict[str, Any]) -> str:
        """
        Generate 1 paragraph discussing the Top Lenders NUMBER of loans table (Section 4, Table 1).
        """
        county_name = data.get('county_name', 'the selected county')
        top_lenders_data = data.get('top_lenders_table', [])

        if not top_lenders_data:
            return ""

        prompt = f"""
        Generate exactly 1 paragraph (3-5 sentences) discussing the top lenders by NUMBER of small business loans in {county_name} for 2024.

        IMPORTANT: Focus ONLY on the NUMBER of loans, not dollar amounts.

        County: {county_name}
        Top Lenders Data: {json.dumps(top_lenders_data[:10], indent=2)[:1500] if top_lenders_data else 'Not available'}

        REQUIREMENTS:
        - EXACTLY 1 PARAGRAPH (3-5 sentences maximum)
        - Discuss which lenders originated the most loans by count
        - Note patterns in loan size distribution (under $100K, $100K-$250K, $250K-$1M)
        - NO specific lender names
        - Plain English, no jargon
        - Third-person, objective tone
        - NO policy recommendations or speculation
        """

        return self.ai.generate_text(prompt, max_tokens=300, temperature=0.3)

    def generate_top_lenders_amount_discussion(self, data: Dict[str, Any]) -> str:
        """
        Generate 1 paragraph discussing the Top Lenders AMOUNT of loans table (Section 4, Table 2).
        """
        county_name = data.get('county_name', 'the selected county')
        top_lenders_data = data.get('top_lenders_table', [])

        if not top_lenders_data:
            return ""

        prompt = f"""
        Generate exactly 1 paragraph (3-5 sentences) discussing the top lenders by DOLLAR AMOUNT of small business loans in {county_name} for 2024.

        IMPORTANT: Focus ONLY on loan AMOUNTS (dollars), not the number of loans.

        County: {county_name}
        Top Lenders Data: {json.dumps(top_lenders_data[:10], indent=2)[:1500] if top_lenders_data else 'Not available'}

        REQUIREMENTS:
        - EXACTLY 1 PARAGRAPH (3-5 sentences maximum)
        - Discuss which lenders had the highest lending volume by dollars
        - Note any differences between number rankings and amount rankings
        - NO specific lender names
        - Plain English, no jargon
        - Third-person, objective tone
        - NO policy recommendations or speculation
        """

        return self.ai.generate_text(prompt, max_tokens=300, temperature=0.3)

    def generate_top_lenders_discussion(self, data: Dict[str, Any]) -> str:
        """
        Generate 2 paragraphs discussing BOTH top lenders tables (Section 4).
        This narrative appears after Table 2 (Amount) and discusses both Number and Amount patterns.

        Args:
            data: Dictionary with top_lenders_table, metadata, etc.

        Returns:
            Plain English narrative (2 paragraphs minimum)
        """
        county_name = data.get('county_name', 'the selected county')
        top_lenders_data = data.get('top_lenders_table', [])

        if not top_lenders_data:
            return ""

        prompt = f"""
        Generate exactly 2 paragraphs discussing the top lenders of small business loans in {county_name} in 2024.

        {self._get_data_source_context()}

        County: {county_name}
        Year: 2024
        Top Lenders Data (up to 10 lenders shown): {json.dumps(top_lenders_data[:10], indent=2)[:2000] if top_lenders_data else 'Not available'}

        CRITICAL WRITING REQUIREMENTS:
        - Write in PLAIN ENGLISH - avoid jargon and technical terms
        - Use simple, clear language accessible to non-technical readers
        - If you must use an acronym, explain it in plain English the first time
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO specific lender names (e.g., don't mention "Bank of America" or "Wells Fargo")
        - NO assumptions about causality or why patterns exist
        - NO policy recommendations
        - NO speculation about underlying reasons
        - NO discussion of market concentration or HHI (Herfindahl-Hirschman Index) - that is covered in a separate section
        - Present ONLY what the lending data shows
        - Use professional, analytical tone
        - EXACTLY 2 PARAGRAPHS (required)
        - First paragraph: Focus on overall lending market patterns, loan size distributions, and which types of loans (under $100K, $100K-$250K, $250K-$1M) dominate the market BY NUMBER
        - Second paragraph: Focus on lending to low-to-moderate income (LMI) tracts and businesses with revenue under $1 million, and discuss the distribution of lending across different income categories (Low, Moderate, Middle, Upper Income tracts)
        - Focus on patterns and distributions rather than specific lender details
        - Avoid listing too many specific numbers - focus on patterns and trends

        Use terms like:
        - "small business loans" not "SB loans"
        - "low-to-moderate income areas" not "LMI tracts" (or explain LMI first)
        - "loan amounts" not "amts"
        - Plain English throughout
        """

        return self.ai.generate_text(prompt, max_tokens=800, temperature=0.3)

    def generate_hhi_trends_discussion(self, data: Dict[str, Any]) -> str:
        """
        Generate 2 paragraphs discussing HHI trends over time (Section 5).

        Args:
            data: Dictionary with hhi_by_year, metadata, etc.

        Returns:
            Plain English narrative (2 paragraphs minimum)
        """
        county_name = data.get('county_name', 'the selected county')
        hhi_by_year_data = data.get('hhi_by_year', [])

        if not hhi_by_year_data:
            return ""

        # Extract HHI values by year
        hhi_values = {}
        for year_data in hhi_by_year_data:
            year = year_data.get('year')
            hhi_value = year_data.get('hhi_value')
            concentration = year_data.get('concentration_level', 'Unknown')
            if year and hhi_value is not None:
                hhi_values[year] = {
                    'value': hhi_value,
                    'concentration': concentration
                }

        # Calculate trends
        years_sorted = sorted(hhi_values.keys())
        if len(years_sorted) >= 2:
            first_year = years_sorted[0]
            last_year = years_sorted[-1]
            first_hhi = hhi_values[first_year]['value']
            last_hhi = hhi_values[last_year]['value']
            hhi_change = last_hhi - first_hhi
            pct_change = ((last_hhi - first_hhi) / first_hhi * 100) if first_hhi > 0 else 0
        else:
            first_year = None
            last_year = None
            first_hhi = None
            last_hhi = None
            hhi_change = None
            pct_change = None

        # Identify baseline and most recent years (2020-2024)
        baseline_hhi = hhi_values.get(2020, {}).get('value') if 2020 in hhi_values else None
        post_ppp_hhi = hhi_values.get(2024, {}).get('value') if 2024 in hhi_values else None

        prompt = f"""
        Generate exactly 2 paragraphs discussing market concentration trends in {county_name} from 2020 to 2024, using the Herfindahl-Hirschman Index (HHI).

        HHI Data by Year:
        {json.dumps(hhi_values, indent=2)}

        Key Trends:
        - First year (2020) HHI: {first_hhi if first_hhi else 'Not available'}
        - Last year (2024) HHI: {last_hhi if last_hhi else 'Not available'}
        - Change from 2020 to 2024: {hhi_change if hhi_change is not None else 'Not available'} ({pct_change:.1f}% change if available)
        - Baseline (2020) HHI: {baseline_hhi if baseline_hhi else 'Not available'}
        - Post-PPP (2024) HHI: {post_ppp_hhi if post_ppp_hhi else 'Not available'}

        HHI Scale:
        - HHI < 1,500: Low concentration (competitive market)
        - HHI 1,500-2,500: Moderate concentration
        - HHI > 2,500: High concentration

        IMPORTANT CONTEXT:
        - HHI measures market concentration using the dollar amount of small business loans across ALL lenders
        - Lower HHI = more competitive market (more lenders sharing the market)
        - Higher HHI = more concentrated market (fewer lenders dominate)
        - The Paycheck Protection Program (PPP) in 2020-2021 may have affected market concentration patterns
        - Compare 2020 (baseline) to 2024 (most recent) to see underlying trends

        CRITICAL WRITING REQUIREMENTS:
        - Write in PLAIN ENGLISH - avoid jargon and technical terms
        - Use simple, clear language accessible to non-technical readers
        - Explain HHI in plain English the first time you mention it
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO assumptions about causality or why patterns exist
        - NO policy recommendations
        - NO speculation about underlying reasons
        - Present ONLY what the HHI data shows
        - Use professional, analytical tone
        - EXACTLY 2 PARAGRAPHS (required)
        - First paragraph: Discuss overall trends from 2020 to 2024, whether the market is becoming more or less competitive, and the impact of PPP years (2020-2021)
        - Second paragraph: Compare 2020 (baseline) to 2024 (most recent) to identify underlying trends, and explain what the HHI values mean for the small business lending market in the county
        - Focus on trends and patterns rather than listing every year's value
        - If HHI increased, the market became more concentrated (less competitive)
        - If HHI decreased, the market became more competitive (less concentrated)
        - Note any significant changes during PPP years and whether patterns returned to pre-PPP levels

        Use terms like:
        - "market concentration" not "HHI" (or explain HHI first)
        - "competitive market" not "low HHI"
        - "concentrated market" not "high HHI"
        - Plain English throughout
        """

        return self.ai.generate_text(prompt, max_tokens=1000, temperature=0.3)
