#!/usr/bin/env python3
"""
BranchSeeker-specific AI analysis for FDIC bank branch data.
"""

import json
from typing import Dict, Any
from justdata.shared.analysis.ai_provider import AIAnalyzer, convert_numpy_types


class BranchSeekerAnalyzer(AIAnalyzer):
    """AI analyzer specifically for bank branch data."""
    
    def generate_executive_summary(self, data: Dict[str, Any]) -> str:
        """Generate an executive summary of the bank branch analysis."""
        counties = data.get('counties', [])
        years = data.get('years', [])
        total_branches = data.get('total_branches', 0)
        top_banks = data.get('top_banks', [])
        
        # Convert data to JSON-serializable format
        json_data = convert_numpy_types(data)
        
        prompt = f"""
        Generate a concise executive summary for bank branch analysis:
        
        Counties: {counties}
        Years: {years[0]} to {years[-1]}
        Total Branches: {total_branches}
        Top Banks: {top_banks[:5]}
        
        IMPORTANT DEFINITIONS:
        - LMICT = Low-to-Moderate Income Census Tracts (areas with median family income below 80% of area median)
        - MMCT = Majority-Minority Census Tracts (areas where minority populations represent more than 50% of total population)
        
        Focus on:
        - Key trends in branch counts
        - Market concentration among major banks
        - MMCT percentage changes around 2022 (2020 census effect)
        - 2-3 paragraphs maximum
        
        WRITING REQUIREMENTS:
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO personal opinions or subjective statements
        - NO speculation about strategic implications or underlying causes
        - Present ONLY factual patterns and observable data trends
        - Describe observable patterns without suggesting underlying causes
        - Describe what the data shows, not why it might be happening
        - Use professional, analytical tone
        """
        
        return self._call_ai(prompt, max_tokens=800, temperature=0.3)
    
    def generate_key_findings(self, data: Dict[str, Any]) -> str:
        """Generate key findings from the bank branch analysis."""
        json_data = convert_numpy_types(data)
        counties = data.get('counties', [])
        years = data.get('years', [])
        
        prompt = f"""
        Generate 3-5 key findings for bank branch analysis:
        
        Counties: {counties}
        Years: {years[0]} to {years[-1]}
        Data: {json.dumps(json_data, indent=2)[:2000]}
        
        IMPORTANT DEFINITIONS:
        - LMICT = Low-to-Moderate Income Census Tracts
        - MMCT = Majority-Minority Census Tracts
        
        Focus on:
        - Most significant trends and patterns
        - MMCT changes around 2022 (2020 census effect)
        - Format as bullet points starting with "•"
        
        WRITING REQUIREMENTS:
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO personal opinions or subjective statements
        - NO speculation about strategic implications or underlying causes
        - Present ONLY factual patterns and observable data trends
        - Describe observable patterns without suggesting underlying causes
        - Describe what the data shows, not why it might be happening
        - Use professional, analytical tone
        """
        
        return self._call_ai(prompt, max_tokens=600, temperature=0.3)
    
    def generate_trends_analysis(self, data: Dict[str, Any]) -> str:
        """Analyze overall branch trends."""
        json_data = convert_numpy_types(data)
        counties = data.get('counties', [])
        years = data.get('years', [])
        
        prompt = f"""
        Analyze overall branch trends:
        
        Counties: {counties}
        Years: {years[0]} to {years[-1]}
        Data: {json.dumps(json_data, indent=2)[:2000]}
        
        IMPORTANT DEFINITIONS:
        - LMICT = Low-to-Moderate Income Census Tracts
        - MMCT = Majority-Minority Census Tracts
        
        Focus on:
        - Overall branch count trends and year-over-year changes
        - MMCT percentage changes around 2022 (2020 census effect)
        - Comparison to broader patterns where relevant
        - 2-3 paragraphs maximum
        
        WRITING REQUIREMENTS:
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO personal opinions or subjective statements
        - NO speculation about strategic implications or underlying causes
        - Present ONLY factual patterns and observable data trends
        - Describe observable patterns without suggesting underlying causes
        - Describe what the data shows, not why it might be happening
        - Use professional, analytical tone
        """
        
        return self._call_ai(prompt, max_tokens=800, temperature=0.3)
    
    def generate_bank_strategies_analysis(self, data: Dict[str, Any]) -> str:
        """Analyze bank market concentration patterns."""
        json_data = convert_numpy_types(data)
        counties = data.get('counties', [])
        years = data.get('years', [])
        
        prompt = f"""
        Analyze market concentration patterns:
        
        Counties: {counties}
        Years: {years[0]} to {years[-1]}
        Top Banks: {data.get('top_banks', [])}
        
        IMPORTANT DEFINITIONS:
        - LMICT = Low-to-Moderate Income Census Tracts (areas with median family income below 80% of area median)
        - MMCT = Majority-Minority Census Tracts (areas where minority populations represent more than 50% of total population)
        
        Focus on:
        - Market concentration patterns among major banks
        - Performance differences in serving LMICT and MMCT communities
        - Competitive dynamics observable in data
        - 2-3 paragraphs maximum
        
        WRITING REQUIREMENTS:
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO personal opinions or subjective statements
        - NO speculation about strategic implications or underlying causes
        - Present ONLY factual patterns and observable data trends
        - Describe observable patterns without suggesting underlying causes
        - Describe what the data shows, not why it might be happening
        - Use professional, analytical tone
        """
        
        return self._call_ai(prompt, max_tokens=800, temperature=0.3)
    
    def generate_community_impact_analysis(self, data: Dict[str, Any]) -> str:
        """Analyze community banking patterns."""
        json_data = convert_numpy_types(data)
        counties = data.get('counties', [])
        years = data.get('years', [])
        
        prompt = f"""
        Analyze community banking patterns:
        
        Counties: {counties}
        Years: {years[0]} to {years[-1]}
        
        IMPORTANT DEFINITIONS:
        - LMICT = Low-to-Moderate Income Census Tracts (areas with median family income below 80% of area median)
        - MMCT = Majority-Minority Census Tracts (areas where minority populations represent more than 50% of total population)
        
        Focus on:
        - How banks serve different community types (LMICT, MMCT)
        - 2020 census impact on MMCT designations (effective 2022)
        - Observable access patterns in data
        - 2-3 paragraphs maximum
        
        WRITING REQUIREMENTS:
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO personal opinions or subjective statements
        - NO speculation about strategic implications or underlying causes
        - Present ONLY factual patterns and observable data trends
        - Describe observable patterns without suggesting underlying causes
        - Describe what the data shows, not why it might be happening
        - Use professional, analytical tone
        """
        
        return self._call_ai(prompt, max_tokens=800, temperature=0.3)
    
    def generate_conclusion(self, data: Dict[str, Any]) -> str:
        """Generate a conclusion."""
        json_data = convert_numpy_types(data)
        counties = data.get('counties', [])
        years = data.get('years', [])
        
        prompt = f"""
        Generate conclusion for bank branch analysis:
        
        Counties: {counties}
        Years: {years[0]} to {years[-1]}
        
        Focus on:
        - Key data patterns
        - LMICT and MMCT categories
        - 2020 census impact on MMCT data
        - Observable trends and their measurable effects
        - 2-3 paragraphs maximum
        
        WRITING REQUIREMENTS:
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO personal opinions or subjective statements
        - NO speculation about strategic implications or underlying causes
        - Present ONLY factual patterns and observable data trends
        - Describe observable patterns without suggesting underlying causes
        - Describe what the data shows, not why it might be happening
        - Use professional, analytical tone
        """
        
        return self._call_ai(prompt, max_tokens=800, temperature=0.3)

