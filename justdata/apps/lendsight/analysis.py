#!/usr/bin/env python3
"""
LendSight-specific AI analysis for HMDA mortgage lending data.
Similar structure to BranchSeeker but for mortgage origination data.
"""

import json
from typing import Dict, Any
from justdata.shared.analysis.ai_provider import AIAnalyzer, convert_numpy_types


class LendSightAnalyzer(AIAnalyzer):
    """AI analyzer specifically for HMDA mortgage lending data."""
    
    def _get_ncrc_report_sources(self) -> str:
        """Return formatted NCRC report sources for AI prompts."""
        return """
        REFERENCE SOURCES - NCRC Mortgage Market Report Series:
        You may reference these NCRC research reports if the information is relevant and valid for the analysis:
        - Part 1: Introduction to Mortgage Market Trends: https://ncrc.org/mortgage-market-report-series-part-1-introduction-to-mortgage-market-trends/
        - Part 2: Lending Trends by Borrower and Neighborhood Characteristics: https://ncrc.org/mortgage-market-report-series-part-2-lending-trends-by-borrower-and-neighborhood-characteristics/
        - Part 3: Native American and Hawaiian Lending: https://ncrc.org/mortgage-market-report-series-part-3-native-american-and-hawaiian-lending/
        - Part 4: Mortgage Lending Across American Cities: https://ncrc.org/mortgage-market-report-series-part-4-mortgage-lending-across-american-cities/
        - Part 5: Top 50 Home Purchase Lenders Analysis for 2024: https://ncrc.org/mortgage-market-report-series-part-5-top-50-home-purchase-lenders-analysis-for-2024/
        
        If you reference any of these reports, you MUST include a hypertext link using markdown format: [link text](URL)
        Example: "As noted in NCRC's mortgage market analysis ([Part 1: Introduction to Mortgage Market Trends](https://ncrc.org/mortgage-market-report-series-part-1-introduction-to-mortgage-market-trends/)), non-bank lenders now dominate the market."
        Only reference these sources if the information is directly relevant and supports your analysis.
        """
    
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
        Generate 3-5 key findings for mortgage lending analysis. Each finding should have a BOLD TITLE followed by a colon and then a sentence summarizing the major data point.
        
        Counties: {counties}
        Years: {years[0]} to {years[-1]}
        Data: {json.dumps(json_data, indent=2)[:2000]}
        Demographic Overview Data: {json.dumps(demographic_data, indent=2)[:1500] if demographic_data else 'Not available'}
        
        {self._get_ncrc_report_sources()}
        
        IMPORTANT DEFINITIONS:
        - LMIB = Low-to-Moderate Income Borrowers
        - LMICT = Low-to-Moderate Income Census Tracts
        - MMCT = Majority-Minority Census Tracts
        
        FORMAT REQUIREMENTS:
        - Each finding must be formatted as: **Title:** Sentence describing the finding
        - The title should be a short, descriptive phrase (3-8 words) that summarizes the finding
        - The sentence after the colon should be ONE COMPLETE SENTENCE explaining the compelling statistic
        - Format as bullet points starting with "•"
        - Example format: • **Total Originations:** Mortgage originations in Hillsborough County, Florida declined by 38.5% from 25,510 loans in 2020 to 15,701 loans in 2024, representing a net decrease of 9,809 loans over the five-year period.
        - Include specific numbers/percentages when available
        
        Focus on:
        - Most significant and compelling statistics from the data
        - Particularly notable trends or patterns
        - Title should be concise and descriptive (e.g., "Total Originations", "LMI Borrower Lending", "Hispanic Borrower Share", "MMCT Originations", "White Borrower Share")
        
        WRITING REQUIREMENTS:
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO personal opinions or subjective statements
        - NO speculation about strategic implications or underlying causes
        - Present ONLY factual patterns and observable data trends
        - Each finding must have a bold title followed by a colon and one complete sentence
        - Use professional, analytical tone
        - If referencing NCRC reports, include hypertext links in markdown format: [link text](URL)
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
        
        {self._get_ncrc_report_sources()}
        
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
        1. FIRST PARAGRAPH: Explain how to interpret the table and identify the most significant patterns
           - Explain what the table shows (lending percentages vs. population shares) in plain English
           - Explain HOW TO READ the table - what each column means and how to interpret the data
           - Identify the MOST COMPELLING disparities - ONLY cite 1-2 groups with the LARGEST gaps or most notable differences
           - For those selected groups, briefly note whether lending is above, below, or approximately equal to population share
           - DO NOT list every single group's numbers - the reader can see those in the table
           - DO NOT recite all the data - focus on explaining what the patterns mean
           - Reference national trends from NCRC reports when relevant (e.g., "This pattern aligns with [national trends](link) showing...")
           - Use plain English to explain what the disparities mean, not just what they are
        2. SECOND PARAGRAPH: Explain the trends over time in plain English
           - Describe the overall direction of changes (which groups are gaining or losing share) in simple terms
           - ONLY cite the MOST SIGNIFICANT changes - the BIGGEST percentage point shifts or those that differ most from national trends
           - Explain what these trends suggest about the market in plain English (e.g., "The data shows a shift toward greater representation of certain groups")
           - DO NOT list every single change - focus ONLY on the most compelling trends
           - Help readers understand how to interpret the "Change Over Time" column
           - Reference national trends from NCRC reports when the local pattern differs or aligns with broader patterns
           - Use plain English to explain what the trends mean, not just what they are
        
        CRITICAL WRITING REQUIREMENTS (SAME AS SECTION 2):
        - Write in PLAIN ENGLISH - explain what the data means, not just what it says
        - The reader can see all the numbers in the table - your job is to explain the trends and patterns
        - ONLY cite the MOST COMPELLING numbers: the biggest changes, largest gaps, or patterns that differ most from national trends
        - DO NOT create a "wall of numbers" - cite at most 2-3 specific percentages per paragraph
        - Focus on explaining HOW TO READ the table and WHAT TRENDS are visible
        - Use simple, clear language accessible to non-technical readers
        - Explain trends in plain English, not just cite numbers
        - Use "lending data" or "mortgage lending patterns" - NEVER say "demographic data"
        - Use "borrowers" - NEVER use "individuals" or "people"
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO assumptions about causality or why patterns exist
        - NO policy recommendations
        - NO speculation about underlying reasons
        - Present ONLY what the lending data shows compared to population demographics
        - Use professional, analytical tone
        - AT LEAST 2 PARAGRAPHS (minimum requirement)
        - The first paragraph MUST explain how to interpret the table and identify the most significant patterns
        - If referencing NCRC reports, include hypertext links in markdown format: [link text](URL)
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
        
        {self._get_ncrc_report_sources()}
        
        CRITICAL: The reader can see ALL the numbers in the table. Your job is NOT to recite the data, but to EXPLAIN what it means in plain English.
        
        ABSOLUTE REQUIREMENTS:
        - Cite AT MOST ONE specific number per paragraph (one percentage point change OR one starting/ending percentage, not both)
        - DO NOT list multiple categories with numbers - the reader can see all the data in the table
        - DO NOT cite year-by-year changes - focus on overall trends
        - MUST reference NCRC national reports when discussing patterns
        - Explain concepts in plain English that a non-expert can understand
        
        The discussion should:
        1. FIRST PARAGRAPH: Explain how to read the table and identify the most significant patterns
           - Start by explaining WHAT THE TABLE SHOWS in plain English (lending by income and neighborhood characteristics)
           - Explain HOW TO READ the table - what each category means (LMIB, LMICT, MMCT) in simple terms
           - Explain that these categories OVERLAP - a loan can be in multiple categories simultaneously (this is critical to understand)
           - Identify the SINGLE MOST COMPELLING pattern - cite ONLY 1 category with the BIGGEST change
           - For that ONE category, note ONLY the direction of change (increased/decreased) and what it means conceptually
           - DO NOT cite specific percentages or percentage point changes in this paragraph - just explain the concept
           - MUST reference national trends from NCRC reports (e.g., "This pattern aligns with [NCRC research](link) showing that...")
           - Use plain English to explain what the pattern means conceptually, not numerically
        2. SECOND PARAGRAPH: Explain the trends over time in plain English
           - Describe the OVERALL DIRECTION of changes in simple terms (e.g., "some categories increased while others decreased")
           - Identify the SINGLE MOST SIGNIFICANT change - cite ONLY 1 category
           - For that ONE category, cite AT MOST ONE number (either the percentage point change OR the starting/ending percentage, not both)
           - Explain what this trend suggests about lending patterns in plain English (e.g., "This suggests a shift toward...")
           - DO NOT cite multiple numbers or year-by-year changes - focus on explaining what the overall trend means
           - Help readers understand how to interpret the "Change Over Time" column conceptually
           - MUST reference national trends from NCRC reports when the local pattern differs or aligns with broader patterns
           - Use plain English to explain what the trends mean conceptually, not just cite numbers
           - If patterns differ from national trends, note that (e.g., "Unlike [national patterns](link), this area shows...")
        
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
        
        CRITICAL WRITING REQUIREMENTS (SAME AS SECTION 1):
        - Write in PLAIN ENGLISH - explain what the data means, not just what it says
        - The reader can see all the numbers in the table - your job is to explain the trends and patterns
        - ONLY cite the MOST COMPELLING numbers: the biggest changes, largest gaps, or patterns that differ most from national trends
        - DO NOT create a "wall of numbers" - cite at most 2-3 specific percentages per paragraph
        - Focus on explaining HOW TO READ the table and WHAT TRENDS are visible
        - Use simple, clear language accessible to non-technical readers
        - Explain trends in plain English, not just cite numbers
        - If you must use an acronym, explain it in plain English the first time
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO assumptions about causality or why patterns exist
        - NO policy recommendations
        - NO speculation about underlying reasons
        - Present ONLY what the data shows
        - Use professional, analytical tone
        - AT LEAST 2 PARAGRAPHS (minimum requirement)
        - The first paragraph MUST explain how to interpret the table and identify the most significant patterns
        - If referencing NCRC reports, include hypertext links in markdown format: [link text](URL)
        """
        
        return self._call_ai(prompt, max_tokens=1000, temperature=0.3)
    
    def generate_all_table_discussions(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Generate all four table discussions in a single API call to reduce rate limit issues.
        
        Returns a dictionary with keys:
        - demographic_overview_discussion
        - income_neighborhood_discussion
        - top_lenders_detailed_discussion
        - market_concentration_discussion
        """
        counties = data.get('counties', [])
        years = data.get('years', [])
        demographic_data = data.get('demographic_overview', [])
        income_neighborhood_data = data.get('income_neighborhood_indicators', [])
        top_lenders_data = data.get('top_lenders_detailed', [])
        market_concentration_data = data.get('market_concentration', [])
        
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
        Generate four separate discussion sections for a mortgage lending analysis report. Each section must be AT LEAST 2 PARAGRAPHS (minimum requirement).
        
        IMPORTANT: Return your response as a JSON object with exactly these four keys:
        - "demographic_overview_discussion"
        - "income_neighborhood_discussion"
        - "top_lenders_detailed_discussion"
        - "market_concentration_discussion"
        
        Counties: {counties_str}
        Years: {year_range}
        Latest Year: {latest_year}
        
        {self._get_ncrc_report_sources()}
        
        === DATA FOR SECTION 1: DEMOGRAPHIC OVERVIEW ===
        Lending Table Data: {json.dumps(demographic_data, indent=2)[:2000] if demographic_data else 'Not available'}
        
        Population Demographics (Most Recent ACS Data):
        {self._get_population_context(data)}
        
        CRITICAL: The population demographics data above IS AVAILABLE and MUST be used in your analysis. Do NOT say the data is missing or unavailable. The data shows the racial and ethnic composition of the population in {counties_str} from the most recent American Community Survey (ACS) data.
        
        For "demographic_overview_discussion":
        - This is LENDING DATA for {counties_str}, NOT demographic data about the population
        - The table shows mortgage lending patterns by race and ethnicity of BORROWERS
        - CRITICAL: The population demographics data IS PROVIDED ABOVE - use it to make comparisons
        - FIRST PARAGRAPH: Explain how to interpret the table and identify the most significant patterns
          * Explain what the table shows (lending percentages vs. population shares) in plain English
          * Explain HOW TO READ the table - what each column means and how to interpret the data
          * Identify the MOST COMPELLING disparities - ONLY cite 1-2 groups with the LARGEST gaps or most notable differences
          * For those selected groups, briefly note whether lending is above, below, or approximately equal to population share
          * DO NOT list every single group's numbers - the reader can see those in the table
          * DO NOT recite all the data - focus on explaining what the patterns mean
          * Reference national trends from NCRC reports when relevant (e.g., "This pattern aligns with [national trends](link) showing...")
          * Use plain English to explain what the disparities mean, not just what they are
        - SECOND PARAGRAPH: Explain the trends over time in plain English
          * Describe the overall direction of changes (which groups are gaining or losing share) in simple terms
          * ONLY cite the MOST SIGNIFICANT changes - the BIGGEST percentage point shifts or those that differ most from national trends
          * Explain what these trends suggest about the market in plain English (e.g., "The data shows a shift toward greater representation of certain groups")
          * DO NOT list every single change - focus ONLY on the most compelling trends
          * Help readers understand how to interpret the "Change Over Time" column
          * Reference national trends from NCRC reports when the local pattern differs or aligns with broader patterns
          * Use plain English to explain what the trends mean, not just what they are
        - Use "lending data" or "mortgage lending patterns" - NEVER say "demographic data"
        - Use "borrowers" - NEVER use "individuals" or "people"
        - The reader can see all the numbers in the table - your job is to explain the trends and patterns
        - ONLY cite the MOST COMPELLING numbers: the biggest changes, largest gaps, or patterns that differ most from national trends
        - DO NOT create a "wall of numbers" - cite at most 2-3 specific percentages per paragraph
        - Focus on explaining HOW TO READ the table and WHAT TRENDS are visible in plain English
        - Use simple, clear language accessible to non-technical readers
        - Explain trends in plain English, not just cite numbers
        - AT LEAST 2 PARAGRAPHS (minimum requirement)
        - DO NOT mention that population data is missing or unavailable - it is provided above
        
        === DATA FOR SECTION 2: INCOME AND NEIGHBORHOOD INDICATORS ===
        Table Data: {json.dumps(income_neighborhood_data, indent=2)[:2000] if income_neighborhood_data else 'Not available'}
        
        For "income_neighborhood_discussion":
        - CRITICAL: The reader can see ALL the numbers in the table. Your job is NOT to recite the data, but to EXPLAIN what it means in plain English.
        - ABSOLUTE REQUIREMENTS:
          * Cite AT MOST ONE specific number per paragraph (one percentage point change OR one starting/ending percentage, not both)
          * DO NOT list multiple categories with numbers - the reader can see all the data in the table
          * DO NOT cite year-by-year changes - focus on overall trends
          * MUST reference NCRC national reports when discussing patterns
          * Explain concepts in plain English that a non-expert can understand
        - FIRST PARAGRAPH: Explain how to read the table and identify the most significant patterns
          * Start by explaining WHAT THE TABLE SHOWS in plain English (lending by income and neighborhood characteristics)
          * Explain HOW TO READ the table - what each category means (LMIB, LMICT, MMCT) in simple terms
          * Explain that these categories OVERLAP - a loan can be in multiple categories simultaneously (this is critical to understand)
          * Identify the SINGLE MOST COMPELLING pattern - cite ONLY 1 category with the BIGGEST change
          * For that ONE category, note ONLY the direction of change (increased/decreased) and what it means conceptually
          * DO NOT cite specific percentages or percentage point changes in this paragraph - just explain the concept
          * MUST reference national trends from NCRC reports (e.g., "This pattern aligns with [NCRC research](link) showing that...")
          * Use plain English to explain what the pattern means conceptually, not numerically
        - SECOND PARAGRAPH: Explain the trends over time in plain English
          * Describe the OVERALL DIRECTION of changes in simple terms (e.g., "some categories increased while others decreased")
          * Identify the SINGLE MOST SIGNIFICANT change - cite ONLY 1 category
          * For that ONE category, cite AT MOST ONE number (either the percentage point change OR the starting/ending percentage, not both)
          * Explain what this trend suggests about lending patterns in plain English (e.g., "This suggests a shift toward...")
          * DO NOT cite multiple numbers or year-by-year changes - focus on explaining what the overall trend means
          * Help readers understand how to interpret the "Change Over Time" column conceptually
          * MUST reference national trends from NCRC reports when the local pattern differs or aligns with broader patterns
          * Use plain English to explain what the trends mean conceptually, not just cite numbers
          * If patterns differ from national trends, note that (e.g., "Unlike [national patterns](link), this area shows...")
        - CRITICAL: These categories are OVERLAPPING, not mutually exclusive:
          * LMICT = Low to Moderate Income Census Tract (areas where median income is below 80% of the area median)
          * LMIB = Low to Moderate Income Borrower (borrowers with income below 80% of the area median)
          * MMCT = Majority Minority Census Tract (areas where more than half the population is from minority groups)
        - A single loan can be counted in MULTIPLE categories simultaneously (e.g., a loan can be to an LMIB borrower, in an LMICT, AND in an MMCT all at the same time)
        - DO NOT say things like "loans in both X and Y" or treat these as mutually exclusive categories
        - Each percentage represents the share of total loans that meet that specific criteria, regardless of whether they also meet other criteria
        - The percentages can add up to more than 100% because loans can be in multiple categories
        - The reader can see all the numbers in the table - your job is to explain the trends and patterns
        - Only cite the MOST COMPELLING numbers: the biggest changes or most notable patterns
        - DO NOT create a "wall of numbers" - cite at most 2-3 specific percentages per paragraph
        - AT LEAST 2 PARAGRAPHS (minimum requirement)
        
        === DATA FOR SECTION 3: TOP LENDERS ===
        Table Data: {json.dumps(top_lenders_data, indent=2)[:2000] if top_lenders_data else 'Not available'}
        
        For "top_lenders_detailed_discussion":
        - This is LENDING DATA showing mortgage lending patterns, NOT demographic data
        - DO NOT mention specific lender names
        - FIRST PARAGRAPH: Explain how to read the table and identify the most significant patterns
          * Explain what the table shows (lending patterns by lender type)
          * Explain that lenders are categorized as mortgage companies, banks, bank affiliates, or credit unions
          * Identify the MOST COMPELLING patterns - only cite 1-2 lender types or groups with the most notable differences
          * DO NOT list every single statistic - the reader can see those in the table
          * Focus on explaining what the patterns mean, not reciting all the data
          * Reference national trends from NCRC reports when relevant (e.g., "[NCRC research](link) shows that mortgage companies...")
        - SECOND PARAGRAPH: Explain the trends and patterns in plain English
          * Describe overall patterns in how different lender types serve traditionally excluded groups (Hispanic, Black, LMIB, LMICT, MMCT)
          * Only cite the MOST SIGNIFICANT differences between lender types
          * Explain what these patterns suggest about market access
          * DO NOT list every single percentage - focus on the most compelling trends
          * Reference national trends from NCRC reports when the local pattern differs or aligns with broader patterns
        - CRITICAL: The data includes lender_type field which categorizes lenders as mortgage companies, banks, bank affiliates, or credit unions
        - The reader can see all the numbers in the table - your job is to explain the trends and patterns
        - Only cite the MOST COMPELLING numbers: the biggest differences or most notable patterns
        - DO NOT create a "wall of numbers" - cite at most 2-3 specific percentages per paragraph
        - AT LEAST 2 PARAGRAPHS (minimum requirement)
        
        === DATA FOR SECTION 4: MARKET CONCENTRATION ===
        Market Concentration Data (HHI by year and loan purpose): {json.dumps(market_concentration_data, indent=2)[:2000] if market_concentration_data else 'Not available'}
        
        For "market_concentration_discussion":
        - This table shows market concentration using the Herfindahl-Hirschman Index (HHI) for all loans, home purchase loans, refinance loans, and home equity lending by year
        - HHI measures market concentration by calculating the sum of squared market shares for all lenders
        - HHI values range from 0 to 10,000, where:
          * Lower values (below 1,500) indicate more competitive markets with many lenders sharing market share
          * Moderate values (1,500-2,500) indicate moderate concentration
          * Higher values (above 2,500) indicate highly concentrated markets dominated by fewer lenders
        - The table shows HHI values for each loan type (All Loans, Home Purchase, Refinance, Home Equity) for each year
        - CRITICAL: Before analyzing trends, you MUST first assess the overall competitive nature of the market:
          * If HHI values are consistently below 1,500 (or even well below 1,500), the market is HIGHLY COMPETITIVE
          * You MUST acknowledge this competitive nature prominently in your analysis
          * Even if concentration increased over time, if values remain well below 1,500, emphasize that the market remains highly competitive overall
          * Put any increases in concentration in proper context - a market that goes from 200 to 400 HHI is still highly competitive (both well below 1,500)
          * Do NOT focus solely on increases without acknowledging the overall competitive nature
        - FIRST PARAGRAPH: Explain how to read the table and what it means
          * Explain what HHI measures and what it means for market competition in plain English
          * CRITICALLY: If HHI values are below 1,500, explicitly state that the market is highly competitive
          * Explain what the different loan types represent
          * Describe the overall competitive nature of the market - do NOT list every HHI value
          * Reference national trends from NCRC reports when relevant
        - SECOND PARAGRAPH: Explain the trends and patterns in plain English
          * CRITICALLY: If HHI values are well below 1,500, acknowledge that the market remains highly competitive even if concentration increased
          * Describe overall trends (is the market becoming more or less competitive?)
          * Only cite the MOST SIGNIFICANT changes or differences between loan types
          * Explain what these patterns mean for borrowers and the lending market
          * DO NOT list every single HHI value - focus on the most compelling trends
          * Reference national trends from NCRC reports when the local pattern differs or aligns with broader patterns
        - Use PLAIN ENGLISH - avoid technical jargon
        - Do NOT include specific HHI numbers or calculations in the discussion
        - Focus on explaining what the patterns mean, not the mathematical details
        - The reader can see all the numbers in the table - your job is to explain the trends and patterns
        - Only cite the MOST COMPELLING information: the biggest changes or most notable patterns
        - DO NOT create a "wall of numbers" - cite at most 1-2 specific examples per paragraph
        - AT LEAST 2 PARAGRAPHS (minimum requirement)
        - CRITICAL: If all HHI values in the data are below 1,500, you MUST emphasize the competitive nature of the market prominently, even if discussing increases over time
        
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
        - If referencing NCRC reports, include hypertext links in markdown format: [link text](URL)
        
        Return ONLY a valid JSON object with the four keys specified above. Do not include any other text or explanation.
        """
        
        try:
            response = self._call_ai(prompt, max_tokens=3000, temperature=0.3)
        except Exception as api_error:
            print(f"[ERROR] AI API call failed: {api_error}")
            import traceback
            traceback.print_exc()
            return {
                'demographic_overview_discussion': '',
                'income_neighborhood_discussion': '',
                'top_lenders_detailed_discussion': '',
                'market_concentration_discussion': ''
            }

        # Log the raw response for debugging
        print(f"[DEBUG] Raw AI response length: {len(response) if response else 0}")
        if response:
            print(f"[DEBUG] Raw AI response preview (first 500 chars): {response[:500]}")
            print(f"[DEBUG] Raw AI response preview (last 500 chars): {response[-500:] if len(response) > 500 else response}")
        else:
            print(f"[ERROR] AI returned empty response!")
            return {
                'demographic_overview_discussion': '',
                'income_neighborhood_discussion': '',
                'top_lenders_detailed_discussion': '',
                'market_concentration_discussion': ''
            }

        # Parse the JSON response
        try:
            import re

            # First, try to extract JSON from markdown code fences (```json ... ``` or ``` ... ```)
            # Use greedy matching to capture the full JSON object (including nested braces)
            code_fence_match = re.search(r'```(?:json)?\s*(\{[\s\S]*\})\s*```', response)
            if code_fence_match:
                response = code_fence_match.group(1)
                print(f"[DEBUG] Extracted JSON from markdown code fence, length: {len(response)}")
            else:
                # Fall back to extracting JSON object from response (handles extra text before/after)
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    response = json_match.group(0)
                    print(f"[DEBUG] Extracted JSON from response, length: {len(response)}")
                else:
                    print(f"[ERROR] No JSON object found in AI response")
                    print(f"[ERROR] Full response: {response}")
                    return {
                        'demographic_overview_discussion': '',
                        'income_neighborhood_discussion': '',
                        'top_lenders_detailed_discussion': '',
                        'market_concentration_discussion': ''
                    }
            
            discussions = json.loads(response)
            print(f"[DEBUG] Successfully parsed JSON, keys: {list(discussions.keys())}")
            
            # Validate that we have all four keys
            required_keys = ['demographic_overview_discussion', 'income_neighborhood_discussion', 'top_lenders_detailed_discussion', 'market_concentration_discussion']
            for key in required_keys:
                if key not in discussions:
                    print(f"[WARNING] Missing required key in AI response: {key}")
                    print(f"[WARNING] Available keys: {list(discussions.keys())}")
                    raise ValueError(f"Missing required key in response: {key}")
                # Check if the value is empty or None
                value = discussions.get(key)
                value_str = str(value).strip() if value else ''
                if not value or len(value_str) == 0:
                    print(f"[WARNING] Key {key} exists but is empty in AI response")
                    print(f"[WARNING] Value type: {type(value)}, Value: {repr(value)}")
                else:
                    print(f"[DEBUG] Key {key} has content, length: {len(value_str)}")
            
            # Log success
            print(f"[DEBUG] Successfully parsed AI discussions, lengths: demographic={len(discussions.get('demographic_overview_discussion', ''))}, income={len(discussions.get('income_neighborhood_discussion', ''))}, lenders={len(discussions.get('top_lenders_detailed_discussion', ''))}, market_concentration={len(discussions.get('market_concentration_discussion', ''))}")
            
            return discussions
        except json.JSONDecodeError as e:
            print(f"[ERROR] Error parsing JSON response from AI: {e}")
            print(f"[ERROR] Response length: {len(response)}")
            print(f"[ERROR] Response preview (first 1000 chars): {response[:1000]}")
            print(f"[ERROR] Response preview (last 500 chars): {response[-500:] if len(response) > 500 else response}")
            # Fallback: return empty strings
            return {
                'demographic_overview_discussion': '',
                'income_neighborhood_discussion': '',
                'top_lenders_detailed_discussion': '',
                'market_concentration_discussion': ''
            }
        except Exception as e:
            print(f"[ERROR] Unexpected error parsing AI response: {e}")
            print(f"[ERROR] Response type: {type(response)}, length: {len(response) if response else 0}")
            import traceback
            traceback.print_exc()
            # Fallback: return empty strings
            return {
                'demographic_overview_discussion': '',
                'income_neighborhood_discussion': '',
                'top_lenders_detailed_discussion': '',
                'market_concentration_discussion': ''
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
        
        {self._get_ncrc_report_sources()}
        
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
        1. FIRST PARAGRAPH: Explain how to read the table and identify the most significant patterns
           - Explain what the table shows (lending patterns by lender type)
           - Explain that lenders are categorized as mortgage companies, banks, bank affiliates, or credit unions
           - Identify the MOST COMPELLING patterns - only cite 1-2 lender types or groups with the most notable differences
           - DO NOT list every single statistic - the reader can see those in the table
           - Focus on explaining what the patterns mean, not reciting all the data
           - Reference national trends from NCRC reports when relevant (e.g., "[NCRC research](link) shows that mortgage companies...")
        2. SECOND PARAGRAPH: Explain the trends and patterns in plain English
           - Describe overall patterns in how different lender types serve traditionally excluded groups (Hispanic, Black, LMIB, LMICT, MMCT)
           - Only cite the MOST SIGNIFICANT differences between lender types
           - Explain what these patterns suggest about market access
           - DO NOT list every single percentage - focus on the most compelling trends
           - Reference national trends from NCRC reports when the local pattern differs or aligns with broader patterns
        
        IMPORTANT NOTES:
        - Race/ethnicity percentages are calculated using the same methodology as Section 1
        - Income and neighborhood indicator percentages use the same calculations as Section 2
        - LMIB = Low to Moderate Income Borrower (explain in plain English: borrowers with income below 80% of the area median)
        - LMICT = Low to Moderate Income Census Tract (explain in plain English: areas where median income is below 80% of the area median)
        - MMCT = Majority Minority Census Tract (explain in plain English: areas where more than half the population is from minority groups)
        - Use "borrowers" terminology, not "individuals" or "people"
        
        CRITICAL WRITING REQUIREMENTS:
        - Write in PLAIN ENGLISH - explain what the data means, not just what it says
        - The reader can see all the numbers in the table - your job is to explain the trends and patterns
        - Only cite the MOST COMPELLING numbers: the biggest differences or most notable patterns
        - DO NOT create a "wall of numbers" - cite at most 2-3 specific percentages per paragraph
        - Focus on explaining HOW TO READ the table and WHAT TRENDS are visible
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
        - If referencing NCRC reports, include hypertext links in markdown format: [link text](URL)
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
            
            # Check if multi-racial borrowers are present in the data
            has_multi_racial = False
            multi_racial_count = 0
            
            # First check summary_data structure
            if summary_data:
                for row in summary_data:
                    if isinstance(row, dict):
                        # Check all possible key variations
                        multi_racial_keys = ['multi_racial', 'Multi-Racial', 'multi-racial', 'multi_racial_originations', 'Multi-Racial Originations']
                        for key in multi_racial_keys:
                            if key in row:
                                count = row[key]
                                # Convert to int if it's a number
                                try:
                                    count = int(count) if count is not None else 0
                                except (ValueError, TypeError):
                                    count = 0
                                if count > 0:
                                    has_multi_racial = True
                                    multi_racial_count = count
                                    break
                        if has_multi_racial:
                            break
                    else:
                        # Check string representation
                        row_str = str(row).lower()
                        if 'multi_racial' in row_str or 'multi-racial' in row_str:
                            has_multi_racial = True
                            break
            
            # Also check summary_text as fallback (in case data is nested differently)
            if not has_multi_racial and summary_text:
                import re
                # Look for patterns like "multi_racial": 123 or percentages like 2.1%
                multi_racial_patterns = [
                    r'"multi_racial"\s*:\s*(\d+)',
                    r'"Multi-Racial[^"]*"\s*:\s*(\d+)',
                    r'multi[_-]?racial[^:]*:\s*(\d+)',
                    r'Multi[_-]?Racial[^:]*:\s*(\d+)',
                    r'multi[_-]?racial[^%]*[:\s]+([\d.]+)%',  # Percentage format
                ]
                for pattern in multi_racial_patterns:
                    matches = re.findall(pattern, summary_text, re.IGNORECASE)
                    if matches:
                        # Check if any match is > 0
                        for match in matches:
                            try:
                                value = float(match)
                                if value > 0:
                                    has_multi_racial = True
                                    break
                            except ValueError:
                                pass
                        if has_multi_racial:
                            break
            
            # Build multi-racial explanation if present
            multi_racial_explanation = ""
            if has_multi_racial:
                multi_racial_explanation = """
            
            MULTI-RACIAL BORROWER EXPLANATION (REQUIRED IF MULTI-RACIAL DATA IS PRESENT):
            If the table includes multi-racial borrowers, you MUST include a clear explanation in your narrative:
            
            1. Definition: Multi-racial borrowers are defined as non-Hispanic borrowers who identify with 2 or more DISTINCT main race categories. The main race categories are:
               - Native American (category 1)
               - Asian (category 2, includes all Asian subcategories like Chinese, Japanese, Filipino, etc.)
               - Black (category 3)
               - Native Hawaiian or Other Pacific Islander/HoPI (category 4, includes all HoPI subcategories)
               - White (category 5)
            
            2. Important Logic:
               - Multi-racial status requires 2+ DISTINCT main categories (not just multiple subcategories of the same race)
               - For example: Someone who selects both "Chinese" and "Japanese" is NOT multi-racial - both map to the "Asian" main category (2)
               - For example: Someone who selects "Black" (3) and "White" (5) IS multi-racial - these are two distinct main categories
               - Hispanic borrowers CANNOT be multi-racial - Hispanic ethnicity takes precedence over race combinations
            
            3. Census Alignment: This definition aligns with Census Bureau's "Two or More Races" category, which counts people who identify with two or more of the five main race categories, excluding Hispanic ethnicity.
            
            4. Race Combination Mix: If multi-racial data is present, note the most common race combinations based on national HMDA data patterns. According to national HMDA data (2018-2024), the top 5 most common multi-racial combinations are:
               - Asian/White: 38.01% of all multi-racial borrowers
               - Native American/White: 21.80% of all multi-racial borrowers
               - Black/White: 17.47% of all multi-racial borrowers
               - HoPI/White: 4.84% of all multi-racial borrowers
               - Native American/Black: 3.74% of all multi-racial borrowers
               These top 5 combinations account for approximately 86% of all multi-racial borrowers nationally. If specific combination data is available in the table for this analysis, reference those local patterns instead.
            
            This explanation should be integrated naturally into your narrative, typically when first discussing borrower demographics or race/ethnicity breakdowns."""
            
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
            {multi_racial_explanation}
            
            Write 1-2 paragraphs that:
            1. Describe the changes over time in total originations and each category
            2. Indicate the percentage of originations that are to LMI Borrowers only, in MMCT only, and both LMIB/MMCT combined over time
            3. Note any significant trends or patterns in the net change column
            4. Discuss what these changes mean for origination distribution patterns
            {f"5. If multi-racial borrowers are present, explain the multi-racial definition and logic as specified above, including the most common race combinations" if has_multi_racial else ""}
            
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

