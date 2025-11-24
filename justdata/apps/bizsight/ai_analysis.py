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
    
    def generate_county_summary_discussion(self, data: Dict[str, Any]) -> str:
        """
        Generate 2 paragraphs discussing the county summary table (Section 2).
        
        Args:
            data: Dictionary with county_summary_table, metadata, etc.
        
        Returns:
            Plain English narrative (2 paragraphs minimum)
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
        The data shows loans to small businesses, categorized by loan size and LMI tract status.
        
        County: {county_name}
        Years: {year_range}
        Summary Data: {json.dumps(summary, indent=2)[:1500] if summary else 'Not available'}
        
        CRITICAL WRITING REQUIREMENTS:
        - Write in PLAIN ENGLISH - avoid jargon and technical terms
        - Use simple, clear language accessible to non-technical readers
        - If you must use an acronym, explain it in plain English the first time
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO assumptions about causality or why patterns exist
        - NO policy recommendations
        - NO speculation about underlying reasons
        - Present ONLY what the lending data shows
        - Use professional, analytical tone
        - EXACTLY 2 PARAGRAPHS (required)
        - Focus on trends and patterns rather than specific numbers
        - Explain what the data means in accessible language
        - Avoid listing too many specific numbers - focus on patterns and trends
        
        The discussion should:
        1. Explain the overall lending activity in the county over the time period
        2. Discuss patterns in loan sizes (under $100K, $100K-$250K, $250K-$1M)
        3. Discuss lending to LMI tracts and what that means
        4. Note any notable patterns or trends visible in the data
        5. Keep numbers to a minimum - focus on what the patterns mean
        
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
        
        # Identify PPP years (2020-2021)
        pre_ppp_hhi = hhi_values.get(2018, {}).get('value') if 2018 in hhi_values else None
        post_ppp_hhi = hhi_values.get(2024, {}).get('value') if 2024 in hhi_values else None
        
        prompt = f"""
        Generate exactly 2 paragraphs discussing market concentration trends in {county_name} from 2018 to 2024, using the Herfindahl-Hirschman Index (HHI).
        
        HHI Data by Year:
        {json.dumps(hhi_values, indent=2)}
        
        Key Trends:
        - First year (2018) HHI: {first_hhi if first_hhi else 'Not available'}
        - Last year (2024) HHI: {last_hhi if last_hhi else 'Not available'}
        - Change from 2018 to 2024: {hhi_change if hhi_change is not None else 'Not available'} ({pct_change:.1f}% change if available)
        - Pre-PPP (2018) HHI: {pre_ppp_hhi if pre_ppp_hhi else 'Not available'}
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
        - Compare pre-PPP (2018) to post-PPP (2024) to see underlying trends
        
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
        - First paragraph: Discuss overall trends from 2018 to 2024, whether the market is becoming more or less competitive, and the impact of PPP years (2020-2021)
        - Second paragraph: Compare pre-PPP (2018) to post-PPP (2024) to identify underlying trends, and explain what the HHI values mean for the small business lending market in the county
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
    
    def generate_comparison_discussion(self, data: Dict[str, Any]) -> str:
        """
        Generate 2 paragraphs discussing the comparison table (Section 3).
        
        Args:
            data: Dictionary with comparison_table, metadata, etc.
        
        Returns:
            Plain English narrative (2 paragraphs minimum)
        """
        county_name = data.get('county_name', 'the selected county')
        state_name = data.get('state_name', 'the state')
        comparison_data = data.get('comparison_table', [])
        
        if not comparison_data:
            return ""
        
        # Extract key values for the prompt
        county_values = {}
        state_values = {}
        national_values = {}
        
        for row in comparison_data:
            metric = row.get('Metric', '')
            county_val = row.get('County (2024)', None)
            state_val = row.get('State (2024)', None)
            national_val = row.get('National (2024)', None)
            
            if 'Total Loans' in metric:
                county_values['total_loans'] = county_val
                state_values['total_loans'] = state_val
                national_values['total_loans'] = national_val
            elif 'Loans Under $100K' in metric:
                county_values['pct_under_100k'] = county_val
                state_values['pct_under_100k'] = state_val
                national_values['pct_under_100k'] = national_val
            elif 'Loans to LMI Tracts' in metric:
                county_values['pct_lmi'] = county_val
                state_values['pct_lmi'] = state_val
                national_values['pct_lmi'] = national_val
        
        prompt = f"""
        Generate exactly 2 paragraphs comparing {county_name}'s 2024 small business lending patterns to {state_name} state and national averages.
        
        IMPORTANT: This is SMALL BUSINESS LENDING DATA, not mortgage lending data.
        
        County: {county_name}
        State: {state_name}
        
        Key Data Points:
        - County total loans (2024): {county_values.get('total_loans', 'N/A')}
        - State total loans (2024): {state_values.get('total_loans', 'N/A')}
        - National total loans (2024): {national_values.get('total_loans', 'N/A')}
        - County % loans under $100K: {county_values.get('pct_under_100k', 'N/A')}%
        - State % loans under $100K: {state_values.get('pct_under_100k', 'N/A')}%
        - National % loans under $100K: {national_values.get('pct_under_100k', 'N/A')}%
        - County % loans to LMI tracts: {county_values.get('pct_lmi', 'N/A')}%
        - State % loans to LMI tracts: {state_values.get('pct_lmi', 'N/A')}%
        - National % loans to LMI tracts: {national_values.get('pct_lmi', 'N/A')}%
        
        Full comparison data: {json.dumps(comparison_data, indent=2)[:2000]}
        
        CRITICAL WRITING REQUIREMENTS:
        - Write in PLAIN ENGLISH - avoid jargon
        - Use simple, clear language
        - Write in objective, third-person style
        - NO first-person language
        - NO assumptions about causality
        - NO policy recommendations
        - EXACTLY 2 PARAGRAPHS (required)
        - First paragraph: Compare county to state and national in 2024
        - Second paragraph: Discuss changes since 2018 (if % change data available)
        - Accurately identify which values are HIGHER, LOWER, or SIMILAR
        - Use mathematical comparisons: if county value > state value, say "higher"
        - If county value < state value, say "lower"
        - If values are within 2-3 percentage points, say "similar" or "comparable"
        - Focus on meaningful differences, not minor variations
        
        Use terms like:
        - "small business loans" not "SB loans"
        - "low-to-moderate income areas" not "LMI tracts" (or explain LMI first)
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
        
        # Identify PPP years (2020-2021)
        pre_ppp_hhi = hhi_values.get(2018, {}).get('value') if 2018 in hhi_values else None
        post_ppp_hhi = hhi_values.get(2024, {}).get('value') if 2024 in hhi_values else None
        
        prompt = f"""
        Generate exactly 2 paragraphs discussing market concentration trends in {county_name} from 2018 to 2024, using the Herfindahl-Hirschman Index (HHI).
        
        HHI Data by Year:
        {json.dumps(hhi_values, indent=2)}
        
        Key Trends:
        - First year (2018) HHI: {first_hhi if first_hhi else 'Not available'}
        - Last year (2024) HHI: {last_hhi if last_hhi else 'Not available'}
        - Change from 2018 to 2024: {hhi_change if hhi_change is not None else 'Not available'} ({pct_change:.1f}% change if available)
        - Pre-PPP (2018) HHI: {pre_ppp_hhi if pre_ppp_hhi else 'Not available'}
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
        - Compare pre-PPP (2018) to post-PPP (2024) to see underlying trends
        
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
        - First paragraph: Discuss overall trends from 2018 to 2024, whether the market is becoming more or less competitive, and the impact of PPP years (2020-2021)
        - Second paragraph: Compare pre-PPP (2018) to post-PPP (2024) to identify underlying trends, and explain what the HHI values mean for the small business lending market in the county
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
    
    def generate_top_lenders_discussion(self, data: Dict[str, Any]) -> str:
        """
        Generate 2 paragraphs discussing the top lenders table (Section 3).
        
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
        
        IMPORTANT: This is SMALL BUSINESS LENDING DATA, not mortgage lending data.
        The data shows which lenders made the most small business loans in 2024.
        
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
        - First paragraph: Focus on overall lending market patterns, loan size distributions, and which types of loans (under $100K, $100K-$250K, $250K-$1M) dominate the market
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
        
        # Identify PPP years (2020-2021)
        pre_ppp_hhi = hhi_values.get(2018, {}).get('value') if 2018 in hhi_values else None
        post_ppp_hhi = hhi_values.get(2024, {}).get('value') if 2024 in hhi_values else None
        
        prompt = f"""
        Generate exactly 2 paragraphs discussing market concentration trends in {county_name} from 2018 to 2024, using the Herfindahl-Hirschman Index (HHI).
        
        HHI Data by Year:
        {json.dumps(hhi_values, indent=2)}
        
        Key Trends:
        - First year (2018) HHI: {first_hhi if first_hhi else 'Not available'}
        - Last year (2024) HHI: {last_hhi if last_hhi else 'Not available'}
        - Change from 2018 to 2024: {hhi_change if hhi_change is not None else 'Not available'} ({pct_change:.1f}% change if available)
        - Pre-PPP (2018) HHI: {pre_ppp_hhi if pre_ppp_hhi else 'Not available'}
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
        - Compare pre-PPP (2018) to post-PPP (2024) to see underlying trends
        
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
        - First paragraph: Discuss overall trends from 2018 to 2024, whether the market is becoming more or less competitive, and the impact of PPP years (2020-2021)
        - Second paragraph: Compare pre-PPP (2018) to post-PPP (2024) to identify underlying trends, and explain what the HHI values mean for the small business lending market in the county
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

