#!/usr/bin/env python3
"""
LendSight-specific AI analysis for HMDA mortgage lending data.
Similar structure to BranchSeeker but for mortgage origination data.
"""

import json
from typing import Dict, Any
from shared.analysis.ai_provider import AIAnalyzer, convert_numpy_types


class LendSightAnalyzer(AIAnalyzer):
    """AI analyzer specifically for HMDA mortgage lending data."""
    
    def generate_intro_paragraph(self, data: Dict[str, Any]) -> str:
        """Generate intro paragraph defining years of data, geographic scope, loan purposes, and filters."""
        counties = data.get('counties', [])
        years = data.get('years', [])
        loan_purpose = data.get('loan_purpose', ['purchase', 'refinance', 'equity'])
        
        # Validate inputs
        if not counties:
            raise ValueError("No counties provided for intro paragraph")
        if not years:
            raise ValueError("No years provided for intro paragraph")
        
        # Format counties and years for display
        if len(counties) == 1:
            counties_str = counties[0]
        elif len(counties) <= 3:
            counties_str = ', '.join(counties)
        else:
            counties_str = f"{counties[0]} and {len(counties) - 1} other counties"
        
        years_str = f"{years[0]} to {years[-1]}" if len(years) > 1 else str(years[0]) if years else 'Unknown'
        
        # Format loan purposes for display
        purpose_map = {
            'purchase': 'home purchase loans',
            'refinance': 'refinance and cash-out refinance loans',
            'equity': 'home equity lending'
        }
        
        # Filter out 'all' if present
        selected_purposes = [p for p in loan_purpose if p != 'all'] if isinstance(loan_purpose, list) else []
        
        # If all three are selected or empty, show all purposes
        if not selected_purposes or set(selected_purposes) == {'purchase', 'refinance', 'equity'}:
            loan_purpose_str = 'all loan purposes (home purchase loans, refinance and cash-out refinance loans, and home equity lending)'
        elif len(selected_purposes) == 1:
            loan_purpose_str = purpose_map.get(selected_purposes[0], selected_purposes[0])
        else:
            purpose_names = [purpose_map.get(p, p) for p in selected_purposes]
            if len(purpose_names) == 2:
                loan_purpose_str = f"{purpose_names[0]} and {purpose_names[1]}"
            else:
                last_purpose = purpose_names.pop()
                loan_purpose_str = ', '.join(purpose_names) + ', and ' + last_purpose
        
        # Get Census demographic data if available
        census_data = data.get('census_data', {})
        census_context = ""
        if census_data:
            # Extract demographic percentages from first county (or aggregate if multiple)
            for county, county_data in census_data.items():
                demographics = county_data.get('demographics', {})
                if demographics:
                    census_year = county_data.get('data_year', 'recent Census data')
                    hispanic_pct = demographics.get('hispanic_percentage', 0)
                    black_pct = demographics.get('black_percentage', 0)
                    white_pct = demographics.get('white_percentage', 0)
                    asian_pct = demographics.get('asian_percentage', 0)
                    
                    # Build context string with key demographics
                    census_context = f" According to {census_year}, the population of {counties_str} is approximately "
                    parts = []
                    if white_pct > 0:
                        parts.append(f"{white_pct:.1f}% White")
                    if hispanic_pct > 0:
                        parts.append(f"{hispanic_pct:.1f}% Hispanic or Latino")
                    if black_pct > 0:
                        parts.append(f"{black_pct:.1f}% Black or African American")
                    if asian_pct > 0:
                        parts.append(f"{asian_pct:.1f}% Asian")
                    
                    if len(parts) >= 2:
                        last_part = parts.pop()
                        census_context += ', '.join(parts) + f', and {last_part}'
                    elif len(parts) == 1:
                        census_context += parts[0]
                    else:
                        census_context = ""  # No valid data
                    census_context += "."
                    break
        
        prompt = f"""
        Generate a single introductory paragraph for a mortgage lending analysis report.
        
        Counties: {counties_str}
        Years: {years_str}
        Loan Purposes: {loan_purpose_str}
        Census Demographics: {census_context if census_context else 'Not available'}
        
        Write a simple, clear paragraph that:
        1. States this is a report on {loan_purpose_str} in {counties_str} from {years_str}
        2. If Census demographic data is available, include a brief mention of the area's population demographics to provide context for the lending patterns
        3. Notes the filters applied to the data:
           - Only loans that were completed (originations)
           - Only owner-occupied properties (homes where the borrower lives)
           - Only site-built homes (traditional homes built on-site, not manufactured/mobile homes)
           - Only forward mortgages (regular mortgages, not reverse mortgages where the bank pays the homeowner)
           - Only 1-4 unit properties (single-family homes, duplexes, triplexes, and four-unit buildings)
        
        CRITICAL WRITING REQUIREMENTS:
        - Write in PLAIN ENGLISH - avoid jargon and technical terms
        - If you must use a technical term, explain it in simple language
        - Explain what "site-built" means (traditional homes built on-site, not manufactured/mobile homes)
        - Explain what "forward mortgages" means (regular mortgages where the borrower pays the bank, not reverse mortgages)
        - If Census data is provided, naturally incorporate the demographic context into the paragraph
        - Keep it simple and straightforward - one paragraph
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO complex sentences or flowery language
        - Accessible to someone with no mortgage industry knowledge
        
        Example structure: "This report examines [loan purposes] in [counties] from [years]. [If Census data available: According to recent Census data, the area's population is...] The analysis includes only [filters explained in plain language]."
        """
        
        return self._call_ai(prompt, max_tokens=300, temperature=0.3)
    
    def generate_executive_summary(self, data: Dict[str, Any]) -> str:
        """Generate an executive summary of the mortgage lending analysis."""
        # For LendSight, we use intro_paragraph instead
        return self.generate_intro_paragraph(data)
    
    def generate_key_findings(self, data: Dict[str, Any]) -> str:
        """Generate 3-5 key findings, each a single sentence explaining a compelling statistic."""
        json_data = convert_numpy_types(data)
        counties = data.get('counties', [])
        years = data.get('years', [])
        demographic_data = data.get('demographic_overview', [])
        
        prompt = f"""
        Generate 3-5 key findings for mortgage lending analysis. Each finding should be a SINGLE SENTENCE explaining a particularly compelling statistic from the data.
        
        Counties: {counties}
        Years: {years[0]} to {years[-1]}
        Data: {json.dumps(json_data, indent=2)[:2000]}
        Demographic Overview Data: {json.dumps(demographic_data, indent=2)[:1500] if demographic_data else 'Not available'}
        
        IMPORTANT DEFINITIONS:
        - LMIB = Low-to-Moderate Income Borrowers
        - LMICT = Low-to-Moderate Income Census Tracts
        - MMCT = Majority-Minority Census Tracts
        
        Focus on:
        - Most significant and compelling statistics from the data
        - Particularly notable trends or patterns
        - Format as bullet points starting with "•"
        - Each bullet point should be ONE SENTENCE ONLY
        - Include specific numbers/percentages when available
        
        WRITING REQUIREMENTS:
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO personal opinions or subjective statements
        - NO speculation about strategic implications or underlying causes
        - Present ONLY factual patterns and observable data trends
        - Each finding must be a single, complete sentence
        - Use professional, analytical tone
        """
        
        return self._call_ai(prompt, max_tokens=400, temperature=0.3)
    
    def generate_trends_analysis(self, data: Dict[str, Any]) -> str:
        """Analyze overall mortgage origination trends."""
        json_data = convert_numpy_types(data)
        counties = data.get('counties', [])
        years = data.get('years', [])
        
        prompt = f"""
        Analyze overall mortgage origination trends:
        
        Counties: {counties}
        Years: {years[0]} to {years[-1]}
        Data: {json.dumps(json_data, indent=2)[:2000]}
        
        IMPORTANT DEFINITIONS:
        - LMIB = Low-to-Moderate Income Borrowers
        - LMICT = Low-to-Moderate Income Census Tracts
        - MMCT = Majority-Minority Census Tracts
        
        Focus on:
        - Overall origination count trends and year-over-year changes
        - MMCT percentage changes around 2022 (2020 census effect)
        - LMI Borrower and LMICT lending trends
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
    
    def generate_lender_strategies_analysis(self, data: Dict[str, Any]) -> str:
        """Analyze lender market concentration patterns with HHI analysis."""
        json_data = convert_numpy_types(data)
        counties = data.get('counties', [])
        years = data.get('years', [])
        hhi_data = data.get('hhi', {})
        trends_data = data.get('trends_data', [])
        summary_data = data.get('summary_data', [])
        
        # Prepare trends information
        trends_text = ""
        if trends_data and len(trends_data) > 0:
            origination_trends = []
            for trend in trends_data:
                if 'Total Originations' in trend or 'Year' in trend:
                    year = trend.get('Year', '')
                    total = trend.get('Total Originations', 0)
                    lmib = trend.get('LMI Borrower Originations', 0)
                    mmct = trend.get('MMCT Originations', 0)
                    if year:
                        origination_trends.append(f"{year}: {total} total originations ({lmib} LMIB, {mmct} MMCT)")
            if origination_trends:
                trends_text = "\n".join(origination_trends)
        
        # Prepare HHI information
        hhi_text = ""
        if hhi_data and hhi_data.get('hhi') is not None:
            hhi_value = hhi_data.get('hhi', 0)
            concentration = hhi_data.get('concentration_level', 'Unknown')
            hhi_year = hhi_data.get('year', '')
            top_lenders = hhi_data.get('top_lenders', [])
            
            hhi_text = f"""
HHI Analysis ({hhi_year}):
- HHI Score: {hhi_value}
- Market Concentration: {concentration}
- Total Loan Amount: ${hhi_data.get('total_loan_amount', 0):,}
- Number of Lenders: {hhi_data.get('total_lenders', 0)}

Top Lenders by Loan Volume:
"""
            for i, lender in enumerate(top_lenders[:5], 1):
                lender_name = lender.get('lender_name', 'Unknown')
                loan_amount = lender.get('total_loan_amount', 0)
                share = lender.get('market_share', 0)
                hhi_text += f"{i}. {lender_name}: ${loan_amount:,} ({share:.1f}% market share)\n"
        
        prompt = f"""
        Analyze lender strategies and market concentration:
        
        Counties: {counties}
        Years: {years[0]} to {years[-1]}
        
        IMPORTANT DEFINITIONS:
        - LMIB = Low-to-Moderate Income Borrowers (borrowers with income below 80% of area median)
        - LMICT = Low-to-Moderate Income Census Tracts (areas with median family income below 80% of area median)
        - MMCT = Majority-Minority Census Tracts (areas where minority populations represent more than 50% of total population)
        - HHI (Herfindahl-Hirschman Index): Measures market concentration (0-10,000 scale)
          * HHI < 1,500: Low concentration (competitive market)
          * HHI 1,500-2,500: Moderate concentration
          * HHI > 2,500: High concentration
        
        ORIGINATION TRENDS OVER TIME PERIOD:
        {trends_text if trends_text else "Review the summary data for origination trends."}
        
        HHI MARKET CONCENTRATION ANALYSIS:
        {hhi_text if hhi_text else "HHI data not available for this analysis."}
        
        ANALYSIS REQUIREMENTS (in this order):
        
        1. FIRST PARAGRAPH - Origination Trends:
           - Describe trends in the total number of mortgage originations over the time period
           - Analyze the distribution of originations to LMIB borrowers over time
           - Analyze the distribution of originations in LMICT census tracts over time
           - Analyze the distribution of originations in MMCT census tracts over time
           - Note any significant changes or patterns
        
        2. SECOND PARAGRAPH - Market Concentration (HHI):
           - State the HHI score and interpret the market concentration level
           - Explain what the concentration level means for the mortgage lending market
           - Reference the HHI analysis year
        
        3. THIRD PARAGRAPH - Market Structure:
           - Analyze whether one or two lenders dominate the market (based on loan volume market share)
           - OR describe if the market is spread among several smaller players
           - Identify any peculiarities in the market structure
           - Reference specific lenders and their market positions if relevant
        
        WRITING REQUIREMENTS:
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO personal opinions or subjective statements beyond data interpretation
        - Present factual patterns and observable data trends
        - Use professional, analytical tone
        - 3-4 paragraphs total
        """
        
        return self._call_ai(prompt, max_tokens=1200, temperature=0.3)
    
    def generate_community_impact_analysis(self, data: Dict[str, Any]) -> str:
        """Analyze community lending patterns."""
        json_data = convert_numpy_types(data)
        counties = data.get('counties', [])
        years = data.get('years', [])
        
        prompt = f"""
        Analyze community lending patterns:
        
        Counties: {counties}
        Years: {years[0]} to {years[-1]}
        
        IMPORTANT DEFINITIONS:
        - LMIB = Low-to-Moderate Income Borrowers (borrowers with income below 80% of area median)
        - LMICT = Low-to-Moderate Income Census Tracts (areas with median family income below 80% of area median)
        - MMCT = Majority-Minority Census Tracts (areas where minority populations represent more than 50% of total population)
        
        Focus on:
        - How lenders serve different community types (LMIB, LMICT, MMCT)
        - 2020 census impact on MMCT designations (effective 2022)
        - Observable lending patterns in data
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
    
    def generate_county_comparison_analysis(self, data: Dict[str, Any]) -> str:
        """Analyze differences between counties in origination distribution."""
        json_data = convert_numpy_types(data)
        counties = data.get('counties', [])
        county_data = data.get('county_data', [])
        
        if not county_data or len(counties) <= 1:
            return ""
        
        # Prepare county comparison data
        county_text = ""
        for county_info in county_data:
            county_name = county_info.get('County', '')
            total = county_info.get('Total Originations', 0)
            lmib_str = county_info.get('LMI Borrower Only Originations', '0 (0.0%)')
            mmct_str = county_info.get('MMCT Only Originations', '0 (0.0%)')
            lenders = county_info.get('Number of Lenders', 0)
            county_text += f"{county_name}: {total} total originations, {lmib_str} to LMIB, {mmct_str} in MMCT, {lenders} lenders\n"
        
        prompt = f"""
        Analyze differences in origination distribution between counties:
        
        Counties: {counties}
        Year: 2023 (or most recent year in report)
        
        IMPORTANT DEFINITIONS:
        - LMIB = Low-to-Moderate Income Borrowers (borrowers with income below 80% of area median)
        - LMICT = Low-to-Moderate Income Census Tracts (areas with median family income below 80% of area median)
        - MMCT = Majority-Minority Census Tracts (areas where minority populations represent more than 50% of total population)
        
        COUNTY DATA:
        {county_text}
        
        ANALYSIS REQUIREMENTS:
        
        1. Compare the total number of originations across counties
        2. Analyze differences in the share of originations to LMIB borrowers between counties
        3. Analyze differences in the share of originations in MMCT areas between counties
        4. Identify which counties have more originations to LMIB or in MMCT areas
        5. Note any significant disparities or patterns
        
        WRITING REQUIREMENTS:
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO personal opinions or subjective statements
        - Present ONLY factual patterns and observable data trends
        - Use professional, analytical tone
        - 1-2 paragraphs
        - Reference specific counties and numbers from the data
        """
        
        return self._call_ai(prompt, max_tokens=600, temperature=0.3)
    
    def generate_demographic_overview_intro(self, data: Dict[str, Any]) -> str:
        """Generate at least 2 sentences leading into the demographic overview table.
        
        NOTE: This is hardcoded in JavaScript, so this method is not actually used.
        Kept for backward compatibility.
        """
        # This is hardcoded in the report template, so return empty string
        return ""
    
    def generate_demographic_overview_discussion(self, data: Dict[str, Any]) -> str:
        """Generate at least 2 paragraphs discussing the demographic overview table data."""
        counties = data.get('counties', [])
        years = data.get('years', [])
        demographic_data = data.get('demographic_overview', [])
        census_data = data.get('census_data', {})
        
        if len(years) > 1:
            year_range = f"{min(years)} to {max(years)}"
        else:
            year_range = str(years[0]) if years else "the selected years"
        
        latest_year = max(years) if years else ""
        
        # Format counties for display
        if len(counties) == 1:
            counties_str = counties[0]
        elif len(counties) <= 3:
            counties_str = ', '.join(counties)
        else:
            counties_str = f"{counties[0]} and {len(counties) - 1} other counties"
        
        # Extract population demographics from most recent Census data (ACS)
        population_context = ""
        if census_data:
            # Aggregate across counties and get most recent ACS data
            total_pop = 0
            white_sum = 0
            black_sum = 0
            hispanic_sum = 0
            asian_sum = 0
            native_am_sum = 0
            hopi_sum = 0
            
            for county_name, county_data in census_data.items():
                time_periods = county_data.get('time_periods', {})
                acs_data = time_periods.get('acs')
                
                if acs_data and acs_data.get('demographics'):
                    demo = acs_data['demographics']
                    pop = demo.get('total_population', 0)
                    if pop > 0:
                        total_pop += pop
                        white_sum += (demo.get('white_percentage', 0) * pop) / 100
                        black_sum += (demo.get('black_percentage', 0) * pop) / 100
                        hispanic_sum += (demo.get('hispanic_percentage', 0) * pop) / 100
                        asian_sum += (demo.get('asian_percentage', 0) * pop) / 100
                        native_am_sum += (demo.get('native_american_percentage', 0) * pop) / 100
                        hopi_sum += (demo.get('hopi_percentage', 0) * pop) / 100
            
            if total_pop > 0:
                white_pct = (white_sum / total_pop) * 100
                black_pct = (black_sum / total_pop) * 100
                hispanic_pct = (hispanic_sum / total_pop) * 100
                asian_pct = (asian_sum / total_pop) * 100
                native_am_pct = (native_am_sum / total_pop) * 100
                hopi_pct = (hopi_sum / total_pop) * 100
                
                population_context = f"""
        Population Demographics (Most Recent ACS Data):
        - White: {white_pct:.1f}% of population
        - Black or African American: {black_pct:.1f}% of population
        - Hispanic or Latino: {hispanic_pct:.1f}% of population
        - Asian: {asian_pct:.1f}% of population
        - Native American: {native_am_pct:.1f}% of population
        - Hawaiian/Pacific Islander: {hopi_pct:.1f}% of population
        """
        
        prompt = f"""
        Generate at least 2 paragraphs (minimum 2 paragraphs required) discussing the lending data shown in the demographic overview table.
        
        IMPORTANT: This is LENDING DATA for {counties_str}, NOT demographic data about the population.
        The table shows mortgage lending patterns by race and ethnicity of BORROWERS, not population demographics.
        
        Counties: {counties}
        Years: {year_range}
        Most Recent Year: {latest_year}
        Lending Table Data: {json.dumps(demographic_data, indent=2)[:2000] if demographic_data else 'Not available'}
        {population_context if population_context else "Population demographics data not available for comparison."}
        
        CRITICAL: {f"The population demographics data IS PROVIDED ABOVE and MUST be used. Do NOT say the data is missing or unavailable." if population_context else "Population demographics data is not available for this analysis."}
        
        CRITICAL ANALYSIS REQUIREMENT - COMPARE LENDING TO POPULATION:
        {f"You MUST compare the lending percentage for each race/ethnicity group to their share of the population in the most recent year ({latest_year}). The population data IS PROVIDED ABOVE - use it." if population_context else "Population demographics data is not available, so you cannot compare lending to population shares. Focus only on lending trends over time."}
        For each group shown in the lending table, compare:
        - The percentage of loans to that group (from the lending data for {latest_year})
        - The percentage of the population that is that group (from the population demographics above)
        - Note whether lending to that group is higher, lower, or approximately equal to their population share
        - Calculate and mention the difference (e.g., "White borrowers received X% of loans, compared to Y% of the population, a difference of Z percentage points")
        - DO NOT say the population data is missing - it is provided above
        
        The discussion should:
        1. FIRST PARAGRAPH: Compare lending percentages to population shares for each race/ethnicity group in the most recent year ({latest_year})
           - For each group, state their lending percentage and population percentage
           - Note whether lending is above, below, or approximately equal to population share
           - Calculate and mention the difference in percentage points
           - Focus on groups where there are notable differences (gaps) between lending and population shares
        2. SECOND PARAGRAPH: Analyze trends over time
           - Focus on the growth or shrinkage of lending to specific race/ethnic groups over time
           - Discuss changes in PERCENTAGES over the time period (focus on percentage points, not raw numbers)
           - Note any particularly notable trends or patterns in lending
           - Discuss what the "Change Over Time" column shows in terms of percentage point changes
        3. Use PERCENTAGES ONLY - do NOT include raw numbers or counts of borrowers
        
        CRITICAL WRITING REQUIREMENTS:
        - Write in PLAIN ENGLISH - avoid jargon and technical terms
        - Use simple, clear language accessible to non-technical readers
        - Use "lending data" or "mortgage lending patterns" - NEVER say "demographic data" or "demographic composition"
        - Use "borrowers" - NEVER use "individuals" or "people"
        - Focus ONLY on percentages and percentage point changes - NO raw numbers
        - Example: "White borrowers received 53.0% of loans, compared to 68.2% of the population, a gap of 15.2 percentage points" 
        - Example: "Hispanic borrowers' share increased from 29.5% to 35.1%" NOT "fell from 4,406 to 3,255"
        - Make the analysis narrative and readable - avoid creating a "wall of numbers"
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO assumptions about causality or why patterns exist
        - NO policy recommendations
        - NO speculation about underlying reasons
        - Present ONLY what the lending data shows compared to population demographics
        - Use professional, analytical tone
        - AT LEAST 2 PARAGRAPHS (minimum requirement)
        - The first paragraph MUST compare lending to population shares for the most recent year
        """
        
        return self._call_ai(prompt, max_tokens=1000, temperature=0.3)
    
    def generate_income_neighborhood_intro(self, data: Dict[str, Any]) -> str:
        """Generate at least 2 sentences leading into the income and neighborhood indicators table."""
        counties = data.get('counties', [])
        years = data.get('years', [])
        income_neighborhood_data = data.get('income_neighborhood_indicators', [])
        
        if len(years) > 1:
            year_range = f"{min(years)} to {max(years)}"
        else:
            year_range = str(years[0]) if years else "the selected years"
        
        prompt = f"""
        Generate at least 2 sentences (but no more than 3) that introduce the income and neighborhood indicators table for Section 2.
        
        Counties: {counties}
        Years: {year_range}
        Table Data: {json.dumps(income_neighborhood_data, indent=2)[:1500] if income_neighborhood_data else 'Not available'}
        
        The introduction should:
        1. Explain what the table shows (lending activity by income and neighborhood characteristics over time)
        2. Mention that it shows both number of loans and percentage for each category
        3. Note the time period covered ({year_range})
        4. Mention the categories: Total loans, LMICT, LMIB, and MMCT
        
        WRITING REQUIREMENTS:
        - At least 2 sentences, no more than 3
        - Plain English, accessible to non-technical readers
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - Professional, analytical tone
        """
        
        return self._call_ai(prompt, max_tokens=300, temperature=0.3)
    
    def generate_income_neighborhood_discussion(self, data: Dict[str, Any]) -> str:
        """Generate at least 2 paragraphs discussing the income and neighborhood indicators table data."""
        counties = data.get('counties', [])
        years = data.get('years', [])
        income_neighborhood_data = data.get('income_neighborhood_indicators', [])
        
        if len(years) > 1:
            year_range = f"{min(years)} to {max(years)}"
        else:
            year_range = str(years[0]) if years else "the selected years"
        
        prompt = f"""
        Generate at least 2 paragraphs (minimum 2 paragraphs required) discussing the income and neighborhood indicators table data.
        
        Counties: {counties}
        Years: {year_range}
        Table Data: {json.dumps(income_neighborhood_data, indent=2)[:2000] if income_neighborhood_data else 'Not available'}
        
        The discussion should:
        1. Analyze the data within the table
        2. Especially focus on the growth or shrinkage of each category over time
        3. Discuss changes in percentages over the time period
        4. Note any particularly notable trends or patterns
        5. Reference specific numbers and percentages from the table
        6. Discuss what the "Change Over Time" column shows
        
        CRITICAL UNDERSTANDING - THESE CATEGORIES OVERLAP:
        - LMICT = Low to Moderate Income Census Tract (areas where median income is below 80% of the area median)
        - LMIB = Low to Moderate Income Borrower (borrowers with income below 80% of the area median)
        - MMCT = Majority Minority Census Tract (areas where more than half the population is from minority groups)
        - These are NOT mutually exclusive categories - a single loan can be counted in MULTIPLE categories at the same time
        - For example, a loan can be: to an LMIB borrower, located in an LMICT, AND located in an MMCT - all simultaneously
        - Each percentage shows what share of total loans meets that specific criteria, regardless of other criteria
        - The percentages can add up to more than 100% because loans overlap across categories
        - DO NOT say "loans in both X and Y" or treat these as if they are mutually exclusive
        - DO NOT combine or intersect these categories in your analysis
        - Percentages are calculated as: (category loans / total loans) × 100
        - The Change Over Time column shows the change from the first year to the last year
        
        CRITICAL WRITING REQUIREMENTS:
        - Write in PLAIN ENGLISH - avoid jargon and technical terms
        - Use simple, clear language accessible to non-technical readers
        - If you must use an acronym, explain it in plain English the first time
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO assumptions about causality or why patterns exist
        - NO policy recommendations
        - NO speculation about underlying reasons
        - Present ONLY what the data shows
        - Use professional, analytical tone
        - AT LEAST 2 PARAGRAPHS (minimum requirement)
        - Include specific numbers and percentages when discussing changes
        - Focus especially on growth or shrinkage of specific categories
        """
        
        return self._call_ai(prompt, max_tokens=1000, temperature=0.3)
    
    def generate_all_table_discussions(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Generate all three table discussions in a single API call to reduce rate limit issues.
        
        Returns a dictionary with keys:
        - demographic_overview_discussion
        - income_neighborhood_discussion
        - top_lenders_detailed_discussion
        """
        counties = data.get('counties', [])
        years = data.get('years', [])
        demographic_data = data.get('demographic_overview', [])
        income_neighborhood_data = data.get('income_neighborhood_indicators', [])
        top_lenders_data = data.get('top_lenders_detailed', [])
        
        if len(years) > 1:
            year_range = f"{min(years)} to {max(years)}"
        else:
            year_range = str(years[0]) if years else "the selected years"
        
        latest_year = max(years) if years else ""
        
        # Format counties for display
        if len(counties) == 1:
            counties_str = counties[0]
        elif len(counties) <= 3:
            counties_str = ', '.join(counties)
        else:
            counties_str = f"{counties[0]} and {len(counties) - 1} other counties"
        
        prompt = f"""
        Generate three separate discussion sections for a mortgage lending analysis report. Each section must be AT LEAST 2 PARAGRAPHS (minimum requirement).
        
        IMPORTANT: Return your response as a JSON object with exactly these three keys:
        - "demographic_overview_discussion"
        - "income_neighborhood_discussion"
        - "top_lenders_detailed_discussion"
        
        Counties: {counties_str}
        Years: {year_range}
        Latest Year: {latest_year}
        
        === DATA FOR SECTION 1: DEMOGRAPHIC OVERVIEW ===
        Lending Table Data: {json.dumps(demographic_data, indent=2)[:2000] if demographic_data else 'Not available'}
        
        Population Demographics (Most Recent ACS Data):
        {self._get_population_context(data)}
        
        CRITICAL: The population demographics data above IS AVAILABLE and MUST be used in your analysis. Do NOT say the data is missing or unavailable. The data shows the racial and ethnic composition of the population in {counties_str} from the most recent American Community Survey (ACS) data.
        
        For "demographic_overview_discussion":
        - This is LENDING DATA for {counties_str}, NOT demographic data about the population
        - The table shows mortgage lending patterns by race and ethnicity of BORROWERS
        - CRITICAL: You MUST compare the lending percentage for each race/ethnicity group to their share of the population in the most recent year ({latest_year})
        - The population demographics data IS PROVIDED ABOVE - use it to make comparisons
        - FIRST PARAGRAPH: Compare lending percentages to population shares for each group in {latest_year}
          * For each group shown in the lending table, state their lending percentage and population percentage (from the data above)
          * Note whether lending is above, below, or approximately equal to population share
          * Calculate and mention the difference in percentage points
          * Focus on groups where there are notable differences (gaps) between lending and population shares
          * DO NOT say the population data is missing - it is provided above
        - SECOND PARAGRAPH: Analyze trends over time
          * Focus on the growth or shrinkage of lending to specific race/ethnic groups over time
          * Discuss changes in PERCENTAGES over the time period (focus on percentage points, not raw numbers)
          * Note any particularly notable trends or patterns in lending
        - Use PERCENTAGES ONLY - do NOT include raw numbers or counts of borrowers
        - Use "lending data" or "mortgage lending patterns" - NEVER say "demographic data"
        - Use "borrowers" - NEVER use "individuals" or "people"
        - Make the analysis narrative and readable - avoid creating a "wall of numbers"
        - AT LEAST 2 PARAGRAPHS (minimum requirement)
        - The first paragraph MUST compare lending to population shares for the most recent year
        - DO NOT mention that population data is missing or unavailable - it is provided above
        
        === DATA FOR SECTION 2: INCOME AND NEIGHBORHOOD INDICATORS ===
        Table Data: {json.dumps(income_neighborhood_data, indent=2)[:2000] if income_neighborhood_data else 'Not available'}
        
        For "income_neighborhood_discussion":
        - Analyze the data within the table
        - Focus on the growth or shrinkage of each category over time
        - Discuss changes in percentages over the time period
        - Note any particularly notable trends or patterns
        - Reference specific numbers and percentages from the table
        - Discuss what the "Change Over Time" column shows
        - CRITICAL: These categories are OVERLAPPING, not mutually exclusive:
          * LMICT = Low to Moderate Income Census Tract (areas where median income is below 80% of the area median)
          * LMIB = Low to Moderate Income Borrower (borrowers with income below 80% of the area median)
          * MMCT = Majority Minority Census Tract (areas where more than half the population is from minority groups)
        - A single loan can be counted in MULTIPLE categories simultaneously (e.g., a loan can be to an LMIB borrower, in an LMICT, AND in an MMCT all at the same time)
        - DO NOT say things like "loans in both X and Y" or treat these as mutually exclusive categories
        - Each percentage represents the share of total loans that meet that specific criteria, regardless of whether they also meet other criteria
        - The percentages can add up to more than 100% because loans can be in multiple categories
        - AT LEAST 2 PARAGRAPHS (minimum requirement)
        
        === DATA FOR SECTION 3: TOP LENDERS ===
        Table Data: {json.dumps(top_lenders_data, indent=2)[:2000] if top_lenders_data else 'Not available'}
        
        For "top_lenders_detailed_discussion":
        - This is LENDING DATA showing mortgage lending patterns, NOT demographic data
        - DO NOT mention specific lender names
        - Focus on TRENDS and PATTERNS at a higher level
        - Discuss variations in lending to traditionally excluded groups: Hispanic, Black, LMIB, LMICT, MMCT
        - CRITICAL: The data includes lender_type field (from lenders18.type_name) which categorizes lenders as:
          * Mortgage companies
          * Banks
          * Bank affiliates
          * Credit unions
        - You MUST analyze and discuss differences between these lender types:
          * Compare how mortgage companies vs. banks vs. credit unions perform
          * Discuss which lender types serve higher or lower shares of traditionally excluded groups
          * Note patterns in lending to Hispanic borrowers, Black borrowers, LMIB, LMICT, and MMCT by lender type
          * Discuss performance differences between lender types
        - Focus on percentage ranges and patterns by lender type rather than specific lender statistics
        - AT LEAST 2 PARAGRAPHS (minimum requirement)
        
        CRITICAL WRITING REQUIREMENTS FOR ALL SECTIONS:
        - Write in PLAIN ENGLISH - avoid jargon and technical terms
        - Use simple, clear language accessible to non-technical readers
        - If you must use an acronym, explain it in plain English the first time
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO specific lender names in top_lenders_detailed_discussion
        - NO assumptions about causality or why patterns exist
        - NO policy recommendations
        - NO speculation about underlying reasons
        - Present ONLY what the data shows
        - Use professional, analytical tone
        - AT LEAST 2 PARAGRAPHS for each section (minimum requirement)
        
        Return ONLY a valid JSON object with the three keys specified above. Do not include any other text or explanation.
        """
        
        response = self._call_ai(prompt, max_tokens=3000, temperature=0.3)
        
        # Parse the JSON response
        try:
            # Try to extract JSON from the response (in case there's extra text)
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                response = json_match.group(0)
            
            discussions = json.loads(response)
            
            # Validate that we have all three keys
            required_keys = ['demographic_overview_discussion', 'income_neighborhood_discussion', 'top_lenders_detailed_discussion']
            for key in required_keys:
                if key not in discussions:
                    raise ValueError(f"Missing required key in response: {key}")
            
            return discussions
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            print(f"Response was: {response[:500]}")
            # Fallback: return empty strings
            return {
                'demographic_overview_discussion': '',
                'income_neighborhood_discussion': '',
                'top_lenders_detailed_discussion': ''
            }
    
    def generate_top_lenders_detailed_discussion(self, data: Dict[str, Any]) -> str:
        """Generate at least 2 paragraphs discussing the top lenders detailed table data."""
        counties = data.get('counties', [])
        years = data.get('years', [])
        top_lenders_data = data.get('top_lenders_detailed', [])
        
        latest_year = max(years) if years else ""
        
        # Format counties for display
        if len(counties) == 1:
            counties_str = counties[0]
        elif len(counties) <= 3:
            counties_str = ', '.join(counties)
        else:
            counties_str = f"{counties[0]} and {len(counties) - 1} other counties"
        
        prompt = f"""
        Generate at least 2 paragraphs (minimum 2 paragraphs required) discussing lending patterns and trends among the top lenders in {counties_str} during {latest_year}.
        
        IMPORTANT: This is LENDING DATA showing mortgage lending patterns, NOT demographic data about the population.
        The table shows mortgage lending by race/ethnicity of BORROWERS and income/neighborhood characteristics.
        
        Counties: {counties}
        Year: {latest_year} (most recent year in report)
        Table Data: {json.dumps(top_lenders_data, indent=2)[:2000] if top_lenders_data else 'Not available'}
        
        CRITICAL WRITING REQUIREMENTS:
        - DO NOT mention specific lender names (e.g., "Nova Financial", "Crosscountry Mortgage", "Loandepotcom")
        - Focus on TRENDS and PATTERNS at a higher level of analysis
        - Discuss variations in lending to traditionally excluded groups: Hispanic borrowers, Black borrowers, Low to Moderate Income Borrowers (LMIB), Low to Moderate Income Census Tracts (LMICT), and Majority Minority Census Tracts (MMCT)
        - CRITICAL: The data includes lender_type field which categorizes lenders as mortgage companies, banks, bank affiliates, or credit unions
        - You MUST analyze and discuss differences between these lender types:
          * Compare how mortgage companies perform vs. banks vs. credit unions
          * Discuss which lender types serve higher or lower shares of traditionally excluded groups
          * Note patterns in lending to Hispanic borrowers, Black borrowers, LMIB, LMICT, and MMCT by lender type
          * Discuss performance differences between lender types
        - Focus on percentage ranges and patterns by lender type rather than specific lender statistics
        - Note any notable variations in lending patterns between different lender types
        
        The discussion should:
        1. Analyze overall trends in lending patterns across the top lenders
        2. Discuss variations in lending to traditionally excluded groups (Hispanic, Black, LMIB, LMICT, MMCT)
        3. CRITICALLY: Compare and contrast patterns between different lender types (mortgage companies vs. banks vs. credit unions)
        4. Discuss which lender types serve higher or lower shares of traditionally excluded groups
        5. Note ranges and patterns in percentages by lender type rather than specific lender statistics
        6. Discuss whether there are distinct market segments or lending approaches visible between lender types
        
        IMPORTANT NOTES:
        - Race/ethnicity percentages are calculated using the same methodology as Section 1
        - Income and neighborhood indicator percentages use the same calculations as Section 2
        - LMIB = Low to Moderate Income Borrower (explain in plain English: borrowers with income below 80% of the area median)
        - LMICT = Low to Moderate Income Census Tract (explain in plain English: areas where median income is below 80% of the area median)
        - MMCT = Majority Minority Census Tract (explain in plain English: areas where more than half the population is from minority groups)
        - Use "borrowers" terminology, not "individuals" or "people"
        - Focus on percentages and percentage ranges, not raw numbers
        
        CRITICAL WRITING REQUIREMENTS:
        - Write in PLAIN ENGLISH - avoid jargon and technical terms
        - Use simple, clear language accessible to non-technical readers
        - If you must use an acronym, explain it in plain English the first time
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO specific lender names
        - NO assumptions about causality or why patterns exist
        - NO policy recommendations
        - NO speculation about underlying reasons
        - Present ONLY what the lending data shows
        - Use professional, analytical tone
        - AT LEAST 2 PARAGRAPHS (minimum requirement)
        - Focus on trends, patterns, and variations rather than specific lender details
        - Discuss at a higher level of analysis
        """
        
        return self._call_ai(prompt, max_tokens=1000, temperature=0.3)
    
    def generate_table_introduction(self, table_id: str, data: Dict[str, Any]) -> str:
        """Generate a 2-sentence introduction for a specific table (hardcoded templates)."""
        counties = data.get('counties', [])
        years = data.get('years', [])
        latest_year = max(years) if years else ""
        first_year = min(years) if years else ""
        
        if table_id == 'table1':
            # Section 1: Yearly Breakdown
            if len(years) > 1:
                year_range = f"{first_year} to {latest_year}"
            else:
                year_range = str(latest_year) if latest_year else "the selected years"
            
            return f"This table shows the total number of mortgage originations, the number that are to LMI Borrowers only (distinct from MMCT), the number that are in MMCT only (distinct from LMI Borrower), and the number that are both to LMI Borrowers and in MMCT census tracts over the entire study period ({year_range}). The data is deduplicated so that each origination appears in only one category, and includes a net change column showing the difference between the first and final year of the analysis."
            
        elif table_id == 'table2':
            # Section 2: Analysis by Lender
            if len(years) > 1:
                year_range = f"{first_year} to {latest_year}"
            else:
                year_range = str(latest_year) if latest_year else "the selected year"
            
            return f"This table shows data from {latest_year} (the final year of the report) for the top lenders in descending order by total originations. It includes LMI Borrower only originations, MMCT only originations, and both LMIB/MMCT originations (with percentages of each lender's total originations) and net change in total originations over the study period ({year_range})."
            
        elif table_id == 'table3':
            # Section 3: County by County Analysis
            return f"This table compares each selected county by number of originations and their distribution to LMI Borrowers only, in MMCT only, and both to LMI Borrowers and in MMCT areas using {latest_year} data (the most recent year in the report). It shows both the number and percentage of originations in each deduplicated category."
        else:
            return ""
    
    def generate_table_narrative(self, table_id: str, data: Dict[str, Any]) -> str:
        """Generate narrative analysis for a specific table."""
        json_data = convert_numpy_types(data)
        counties = data.get('counties', [])
        years = data.get('years', [])
        
        if table_id == 'table1':
            # Section 1: Yearly Breakdown
            summary_data = data.get('summary_data', [])
            summary_text = json.dumps(summary_data, indent=2)[:1500] if summary_data else "No summary data available"
            
            prompt = f"""
            Analyze the yearly breakdown table data and provide a narrative explanation:
            
            Counties: {counties}
            Years: {years[0]} to {years[-1]}
            
            Table Data:
            {summary_text}
            
            IMPORTANT DEFINITIONS:
            - LMIB = Low-to-Moderate Income Borrowers
            - LMICT = Low-to-Moderate Income Census Tracts
            - MMCT = Majority-Minority Census Tracts
            - The table shows: Total Originations, LMI Borrower Only Originations, MMCT Only Originations, and Both LMIB/MMCT Originations
            - These categories are mutually exclusive (deduplicated)
            
            Write 1-2 paragraphs that:
            1. Describe the changes over time in total originations and each category
            2. Indicate the percentage of originations that are to LMI Borrowers only, in MMCT only, and both LMIB/MMCT combined over time
            3. Note any significant trends or patterns in the net change column
            4. Discuss what these changes mean for origination distribution patterns
            
            WRITING REQUIREMENTS:
            - Plain English, accessible to non-technical readers
            - Write in objective, third-person style
            - NO first-person language (no "I", "we", "my", "our")
            - NO assumptions about causality or why patterns exist
            - NO policy recommendations
            - NO speculation about underlying reasons
            - Present ONLY what the data shows
            - Use professional, analytical tone
            - Include specific percentages when discussing categories
            """
            
        elif table_id == 'table2':
            # Section 2: Analysis by Lender
            lender_data = data.get('by_lender', [])
            lender_text = json.dumps(lender_data, indent=2)[:1500] if lender_data else "No lender data available"
            latest_year = max(years) if years else ""
            hhi_data = data.get('hhi', {})
            
            prompt = f"""
            Analyze the top lenders table data and provide a narrative explanation:
            
            Counties: {counties}
            Year: {latest_year} (most recent year, final year of report)
            
            Top Lenders Data (up to 10 lenders shown, or fewer if there are fewer lenders in the area):
            {lender_text}
            
            HHI Market Concentration Data:
            {json.dumps(hhi_data, indent=2)[:1000] if hhi_data and hhi_data.get('hhi') is not None else "HHI data not available - loan amount data was not included in this dataset."}
            
            IMPORTANT DEFINITIONS:
            - LMIB = Low-to-Moderate Income Borrowers
            - LMICT = Low-to-Moderate Income Census Tracts
            - MMCT = Majority-Minority Census Tracts
            - The table shows: Total Originations, LMI Borrower Only Originations (with %), MMCT Only Originations (with %), Both LMIB/MMCT Originations (with %), and Net Change
            - These categories are mutually exclusive (deduplicated)
            - HHI (Herfindahl-Hirschman Index) measures market concentration using ALL lenders' loan volume shares, not just the lenders shown in the table
            - HHI scale: 0-10,000 (HHI < 1,500 = Low concentration, 1,500-2,500 = Moderate, > 2,500 = High)
            
            Write 1-2 paragraphs that:
            1. Discuss trends over time: which lenders have grown the most or shrunk the most over the study period (use Net Change column)
            2. {"Analyze market concentration using the HHI calculation. State the HHI score (" + str(hhi_data.get('hhi', 'N/A')) + "), the concentration level (" + str(hhi_data.get('concentration_level', 'N/A')) + "), and explain what this means for the mortgage lending market. Note that the HHI calculation uses ALL lenders in the study area, not just the lenders shown in the table." if hhi_data.get('hhi') is not None else "Note that HHI (Herfindahl-Hirschman Index) analysis could not be performed because loan amount data was not available in this dataset. HHI would measure market concentration using all lenders' loan volume shares."}
            3. Note patterns in how top lenders serve LMIB and MMCT communities based on the percentages shown
            
            WRITING REQUIREMENTS:
            - Plain English, accessible to non-technical readers
            - Write in objective, third-person style
            - NO first-person language (no "I", "we", "my", "our")
            - NO assumptions about causality or why patterns exist
            - NO policy recommendations
            - NO speculation about underlying reasons
            - Present ONLY what the data shows
            - Use professional, analytical tone
            - Include a sentence explaining that HHI uses all lenders, not just the lenders shown in the table
            """
            
        elif table_id == 'table3':
            # Table 3: Analysis by County
            county_data = data.get('county_data', [])
            county_text = json.dumps(county_data, indent=2)[:1500] if county_data else "No county data available"
            latest_year = max(years) if years else ""
            
            prompt = f"""
            Analyze the county comparison table data and provide a narrative explanation:
            
            Counties: {counties}
            Year: {latest_year} (most recent year in the report)
            
            County Data:
            {county_text}
            
            IMPORTANT DEFINITIONS:
            - LMIB = Low-to-Moderate Income Borrowers
            - LMICT = Low-to-Moderate Income Census Tracts
            - MMCT = Majority-Minority Census Tracts
            - The table shows: Total Originations, LMI Borrower Only Originations (with %), MMCT Only Originations (with %), and Both LMIB/MMCT Originations (with %)
            - These categories are mutually exclusive (deduplicated)
            
            Write 1-2 paragraphs that:
            1. Compare the total number of originations across counties
            2. Explain differences in the share of LMI Borrower Only originations between counties
            3. Explain differences in the share of MMCT Only originations between counties
            4. Explain differences in the share of Both LMIB/MMCT originations between counties
            5. Note which counties have more originations to LMIB or in MMCT areas
            6. Discuss what these differences mean for origination access patterns
            
            WRITING REQUIREMENTS:
            - Plain English, accessible to non-technical readers
            - Write in objective, third-person style
            - NO first-person language (no "I", "we", "my", "our")
            - NO assumptions about causality or why patterns exist
            - NO policy recommendations
            - NO speculation about underlying reasons
            - Present ONLY what the data shows
            - Use professional, analytical tone
            - Reference specific counties and numbers from the data
            - Explicitly mention that the data is from {latest_year} (the most recent year in the report)
            """
        else:
            return ""
        
        return self._call_ai(prompt, max_tokens=600, temperature=0.3)
    
    def _get_population_context(self, data: Dict[str, Any]) -> str:
        """Extract population demographics from most recent Census data for prompt context."""
        census_data = data.get('census_data', {})
        
        if not census_data:
            return "Population demographics data not available for comparison."
        
        # Aggregate across counties and get most recent ACS data
        total_pop = 0
        white_sum = 0
        black_sum = 0
        hispanic_sum = 0
        asian_sum = 0
        native_am_sum = 0
        hopi_sum = 0
        
        for county_name, county_data in census_data.items():
            time_periods = county_data.get('time_periods', {})
            acs_data = time_periods.get('acs')
            
            if acs_data and acs_data.get('demographics'):
                demo = acs_data['demographics']
                pop = demo.get('total_population', 0)
                if pop > 0:
                    total_pop += pop
                    white_sum += (demo.get('white_percentage', 0) * pop) / 100
                    black_sum += (demo.get('black_percentage', 0) * pop) / 100
                    hispanic_sum += (demo.get('hispanic_percentage', 0) * pop) / 100
                    asian_sum += (demo.get('asian_percentage', 0) * pop) / 100
                    native_am_sum += (demo.get('native_american_percentage', 0) * pop) / 100
                    hopi_sum += (demo.get('hopi_percentage', 0) * pop) / 100
        
        if total_pop == 0:
            return "Population demographics data not available for comparison."
        
        white_pct = (white_sum / total_pop) * 100
        black_pct = (black_sum / total_pop) * 100
        hispanic_pct = (hispanic_sum / total_pop) * 100
        asian_pct = (asian_sum / total_pop) * 100
        native_am_pct = (native_am_sum / total_pop) * 100
        hopi_pct = (hopi_sum / total_pop) * 100
        
        return f"""- White: {white_pct:.1f}% of population
        - Black or African American: {black_pct:.1f}% of population
        - Hispanic or Latino: {hispanic_pct:.1f}% of population
        - Asian: {asian_pct:.1f}% of population
        - Native American: {native_am_pct:.1f}% of population
        - Hawaiian/Pacific Islander: {hopi_pct:.1f}% of population"""
    
    def generate_conclusion(self, data: Dict[str, Any]) -> str:
        """Generate a conclusion."""
        json_data = convert_numpy_types(data)
        counties = data.get('counties', [])
        years = data.get('years', [])
        
        prompt = f"""
        Generate conclusion for mortgage lending analysis:
        
        Counties: {counties}
        Years: {years[0]} to {years[-1]}
        
        Focus on:
        - Key data patterns
        - LMIB, LMICT and MMCT categories
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

