#!/usr/bin/env python3
"""
BranchSeeker-specific AI analysis for FDIC bank branch data.
"""

import json
from typing import Dict, Any, List
from justdata.shared.analysis.ai_provider import AIAnalyzer, convert_numpy_types


class BranchSeekerAnalyzer(AIAnalyzer):
    """AI analyzer specifically for bank branch data."""

    def _get_data_source_context(self) -> str:
        """Return context about what FDIC Summary of Deposits branch data represents."""
        return """
        DATA SOURCE CONTEXT - FDIC Summary of Deposits (SOD):
        This report uses FDIC Summary of Deposits data, which tracks bank branch locations and deposits (NOT lending data).

        KEY DISTINCTIONS:
        - This is BRANCH LOCATION data, not lending or mortgage data
        - Shows where banks have physical branch offices
        - Includes deposit amounts at each branch
        - Geographic breakdown by census tract characteristics (income level, minority population)

        TERMINOLOGY:
        - "Branches" = physical bank office locations, NOT loans or lending activity
        - "LMICT" = Low-to-Moderate Income Census Tracts (areas with median family income below 80% of area median)
        - "MMCT" = Majority-Minority Census Tracts (areas where minority populations exceed 50%)
        - "Deposits" = money held at branches, NOT loans made
        - Do NOT confuse branch presence with lending activity - they are different measures

        CENSUS BOUNDARY NOTE:
        The 2020 Census boundaries took effect in 2022, causing a ~30% national increase in MMCT designations.
        Large changes in MMCT branch counts between 2021 and 2022 are likely due to boundary changes, not actual branch movements.

        PLAIN ENGLISH REQUIREMENTS:
        - Write for a general audience unfamiliar with banking regulations
        - Explain acronyms and technical terms in simple language
        - Use "bank branches" or "branch locations" not technical terms
        - Use "low-to-moderate income areas" not just "LMICT"
        - Use "majority-minority areas" not just "MMCT"
        """

    def generate_executive_summary(self, data: Dict[str, Any]) -> str:
        """Generate an executive summary of the bank branch analysis."""
        counties = data.get('counties', [])
        years = data.get('years', [])
        final_year = data.get('final_year', years[-1] if years else None)
        final_year_branch_count = data.get('final_year_branch_count', 0)
        top_banks = data.get('top_banks', [])
        
        # Validate inputs
        if not counties:
            raise ValueError("No counties provided for executive summary")
        if not years:
            raise ValueError("No years provided for executive summary")
        
        # Convert data to JSON-serializable format
        json_data = convert_numpy_types(data)
        
        # Format counties and years for display
        counties_str = ', '.join(str(c) for c in counties) if counties else 'Unknown'
        years_str = f"{years[0]} to {years[-1]}" if len(years) > 1 else str(years[0]) if years else 'Unknown'
        top_banks_str = ', '.join(str(b) for b in top_banks[:5]) if top_banks else 'None'
        
        # Check if 2021 and 2022 are in the years
        has_2021_2022 = 2021 in years and 2022 in years
        census_note = ""
        if has_2021_2022:
            census_note = """
        
        CRITICAL CENSUS BOUNDARY CHANGE NOTE (MUST INCLUDE):
        The census tract changes from 2021 to 2022 created a 30% increase nationally in the number of majority-minority census tracts, most of which are not low to moderate income. The 2020 census boundaries that took effect in 2022 resulted in a dramatic increase in the number of middle and upper income majority-minority census tracts nationally. Therefore, it is expected that there would be a dramatic increase in majority-minority branch locations between 2021 and 2022. When discussing MMCT (Majority-Minority Census Tract) branch changes between 2021 and 2022, you MUST explicitly note this census boundary change effect. This is a methodological artifact of the census boundary update, not necessarily a reflection of actual branch location changes or banking strategy shifts.
        """
        
        prompt = f"""
        Generate a concise executive summary for bank branch analysis:

        {self._get_data_source_context()}

        Counties: {counties_str}
        Years: {years_str}
        Total Branches in {final_year}: {final_year_branch_count}
        Top Banks: {top_banks_str}

        CRITICAL: When mentioning the total number of branches, you MUST explicitly state that this is the number of branches present in {final_year} (the final year of the report). Do NOT sum branches across all years. The number {final_year_branch_count} represents unique branches that existed in {final_year} only.

        {census_note}

        Focus on:
        - Key trends in branch counts over the time period
        - Market concentration among major banks
        - MMCT percentage changes around 2022 (2020 census effect)
        - 2-3 paragraphs maximum

        WRITING REQUIREMENTS:
        - Write in PLAIN ENGLISH accessible to non-technical readers
        - Explain terms like LMICT (low-to-moderate income areas) and MMCT (majority-minority areas) in plain language
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO personal opinions or subjective statements
        - NO speculation about strategic implications or underlying causes
        - Present ONLY factual patterns and observable data trends
        - Describe observable patterns without suggesting underlying causes
        - Describe what the data shows, not why it might be happening
        - Use professional, analytical tone
        - When stating branch counts, explicitly mention the year ({final_year})
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
        """Analyze bank market concentration patterns with HHI analysis."""
        json_data = convert_numpy_types(data)
        counties = data.get('counties', [])
        years = data.get('years', [])
        hhi_data = data.get('hhi', {})
        trends_data = data.get('trends_data', [])
        summary_data = data.get('summary_data', [])
        
        # Prepare trends information
        trends_text = ""
        if trends_data and len(trends_data) > 0:
            # Extract branch count trends
            branch_trends = []
            for trend in trends_data:
                if 'Total Branches' in trend:
                    year = trend.get('Year', '')
                    total = trend.get('Total Branches', 0)
                    lmi = trend.get('LMI Branches', 0)
                    mmct = trend.get('Minority Branches', 0)
                    if year:
                        branch_trends.append(f"{year}: {total} total branches ({lmi} LMI, {mmct} MMCT)")
            if branch_trends:
                trends_text = "\n".join(branch_trends)
        
        # Prepare HHI information
        hhi_text = ""
        if hhi_data and hhi_data.get('hhi') is not None:
            hhi_value = hhi_data.get('hhi', 0)
            concentration = hhi_data.get('concentration_level', 'Unknown')
            hhi_year = hhi_data.get('year', '')
            top_banks = hhi_data.get('top_banks', [])
            
            hhi_text = f"""
HHI Analysis ({hhi_year}):
- HHI Score: {hhi_value}
- Market Concentration: {concentration}
- Total Deposits: ${hhi_data.get('total_deposits', 0):,}
- Number of Banks: {hhi_data.get('total_banks', 0)}

Top Banks by Deposits:
"""
            for i, bank in enumerate(top_banks[:5], 1):
                bank_name = bank.get('bank_name', 'Unknown')
                deposits = bank.get('total_deposits', 0)
                share = bank.get('market_share', 0)
                hhi_text += f"{i}. {bank_name}: ${deposits:,} ({share:.1f}% market share)\n"
        
        prompt = f"""
        Analyze bank strategies and market concentration:
        
        Counties: {counties}
        Years: {years[0]} to {years[-1]}
        
        IMPORTANT DEFINITIONS:
        - LMICT = Low-to-Moderate Income Census Tracts (areas with median family income below 80% of area median)
        - MMCT = Majority-Minority Census Tracts (areas where minority populations represent more than 50% of total population)
        - HHI (Herfindahl-Hirschman Index): Measures market concentration (0-10,000 scale)
          * HHI < 1,500: Low concentration (competitive market)
          * HHI 1,500-2,500: Moderate concentration
          * HHI > 2,500: High concentration
        
        BRANCH TRENDS OVER TIME PERIOD:
        {trends_text if trends_text else "Review the summary data for branch trends."}
        
        HHI MARKET CONCENTRATION ANALYSIS:
        {hhi_text if hhi_text else "HHI data not available for this analysis."}
        
        ANALYSIS REQUIREMENTS (in this order):
        
        1. FIRST PARAGRAPH - Branch Trends:
           - Describe trends in the total number of branches over the time period
           - Analyze the distribution of branches in LMICT census tracts over time
           - Analyze the distribution of branches in MMCT census tracts over time
           - Note any significant changes or patterns
        
        2. SECOND PARAGRAPH - Market Concentration (HHI):
           - State the HHI score and interpret the market concentration level
           - Explain what the concentration level means for the banking market
           - Reference the HHI analysis year
        
        3. THIRD PARAGRAPH - Market Structure:
           - Analyze whether one or two banks dominate the market (based on deposit market share)
           - OR describe if the market is spread among several smaller players
           - Identify any peculiarities in the market structure
           - Reference specific banks and their market positions if relevant
        
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
    
    def generate_county_comparison_analysis(self, data: Dict[str, Any]) -> str:
        """Analyze differences between counties in branch distribution."""
        json_data = convert_numpy_types(data)
        counties = data.get('counties', [])
        county_data = data.get('county_data', [])
        
        if not county_data or len(counties) <= 1:
            return ""
        
        # Prepare county comparison data
        county_text = ""
        for county_info in county_data:
            county_name = county_info.get('County', '')
            total = county_info.get('Total Branches', 0)
            lmi_str = county_info.get('LMI Branches', '0 (0.0%)')
            mmct_str = county_info.get('Minority Branches', '0 (0.0%)')
            banks = county_info.get('Number of Banks', 0)
            county_text += f"{county_name}: {total} total branches, {lmi_str} in LMICT, {mmct_str} in MMCT, {banks} banks\n"
        
        prompt = f"""
        Analyze differences in branch distribution between counties:
        
        Counties: {counties}
        Year: 2024
        
        IMPORTANT DEFINITIONS:
        - LMICT = Low-to-Moderate Income Census Tracts (areas with median family income below 80% of area median)
        - MMCT = Majority-Minority Census Tracts (areas where minority populations represent more than 50% of total population)
        
        COUNTY DATA (2024):
        {county_text}
        
        ANALYSIS REQUIREMENTS:
        
        1. Compare the total number of branches across counties
        2. Analyze differences in the share of branches located in LMICT areas between counties
        3. Analyze differences in the share of branches located in MMCT areas between counties
        4. Identify which counties have more branches in LMICT or MMCT areas
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
    
    def generate_table_introduction(self, table_id: str, data: Dict[str, Any]) -> str:
        """Generate a 3-sentence introduction for a specific table (hardcoded templates)."""
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
            
            return f"This table shows the total number of open branches, the number that are LMI only (distinct from MMCT), the number that are MMCT only (distinct from LMI), and the number that are both LMICT and MMCT over the entire study period ({year_range}). The data is deduplicated so that each branch appears in only one category, and includes a net change column showing the difference between the first and final year of the analysis. This breakdown helps identify trends in branch distribution patterns across different community types over time."
            
        elif table_id == 'table2':
            # Section 2: Analysis by Bank
            if len(years) > 1:
                year_range = f"{first_year} to {latest_year}"
            else:
                year_range = str(latest_year) if latest_year else "the selected year"
            
            return f"This table shows data from {latest_year} (the final year of the report) for the top banks in descending order by total branches. It includes LMI only branches, MMCT only branches, and both LMICT/MMCT branches (with percentages of each bank's total branches) and net change in total branches over the study period ({year_range}). This analysis helps identify which banks have the strongest presence in different community types and how their branch networks have changed over time."
            
        elif table_id == 'table3':
            # Section 3: County by County Analysis
            return f"This table compares each selected county by number of branches and their distribution in LMI only, MMCT only, and both LMICT/MMCT areas using {latest_year} data (the most recent year in the report). It shows both the number and percentage of branches in each deduplicated category. This comparison helps identify variations in branch distribution patterns across different counties in the analysis area."
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
            if summary_data:
                for row in summary_data:
                    if 'multi_racial' in str(row).lower() or 'Multi-Racial' in str(row):
                        has_multi_racial = True
                        # Try to extract count if available
                        if isinstance(row, dict):
                            multi_racial_count = row.get('multi_racial_originations', row.get('Multi-Racial Originations', 0))
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
            
            4. Race Combination Mix: If multi-racial data is present, note the most common race combinations (e.g., "The majority of multi-racial borrowers identify as Black/White" or "Multi-racial borrowers most commonly identify as Asian/White combinations"). If specific combination data is available in the table, reference it.
            
            This explanation should be integrated naturally into your narrative, typically in the first paragraph when discussing borrower demographics."""
            
            prompt = f"""
            Analyze the yearly breakdown table data and provide a narrative explanation:
            
            Counties: {counties}
            Years: {years[0]} to {years[-1]}
            
            Table Data:
            {summary_text}
            
            IMPORTANT DEFINITIONS:
            - LMICT = Low-to-Moderate Income Census Tracts
            - MMCT = Majority-Minority Census Tracts
            - The table shows: Total Branches, LMI Only Branches, MMCT Only Branches, and Both LMICT/MMCT Branches
            - These categories are mutually exclusive (deduplicated)
            {multi_racial_explanation}
            
            Write exactly 2 paragraphs that focus on BROAD TRENDS and MAJOR GAPS OR CHANGES:
            
            Paragraph 1: Focus on broad trends over time
            - Describe the overall changes in total branches across the study period
            - Identify major trends in LMI only, MMCT only, and both LMICT/MMCT branch categories
            - Note the percentage of branches in each category over time
            - Highlight any significant net changes between the first and final year
            {f"- If multi-racial borrowers are present, explain the multi-racial definition and logic as specified above" if has_multi_racial else ""}
            
            Paragraph 2: Focus on major gaps or changes
            - Identify any major gaps or significant changes in branch distribution patterns
            - Note any substantial shifts in the proportion of branches serving LMI or MMCT communities
            - Discuss what these patterns indicate about branch access over the study period
            
            WRITING REQUIREMENTS (NCRC Style Guide):
            - Plain English, accessible to non-technical readers
            - Write in objective, third-person style
            - NO first-person language (no "I", "we", "my", "our")
            - NO assumptions about causality or why patterns exist
            - NO policy recommendations
            - NO speculation about underlying reasons
            - Present ONLY what the data shows
            - Use professional, analytical tone
            - Focus on BROAD TRENDS and MAJOR GAPS/CHANGES only - avoid minor details
            - Include specific percentages when discussing categories
            - Limit discussion to observable patterns in the data
            """
            
        elif table_id == 'table2':
            # Section 2: Analysis by Bank
            bank_data = data.get('by_bank', [])
            bank_text = json.dumps(bank_data, indent=2)[:1500] if bank_data else "No bank data available"
            latest_year = max(years) if years else ""
            
            prompt = f"""
            Analyze the top banks table data and provide a narrative explanation:
            
            Counties: {counties}
            Year: {latest_year} (most recent year, final year of report)
            
            Top Banks Data (up to 10 banks shown, or fewer if there are fewer banks in the area):
            {bank_text}
            
            IMPORTANT DEFINITIONS:
            - LMICT = Low-to-Moderate Income Census Tracts
            - MMCT = Majority-Minority Census Tracts
            - The table shows: Total Branches, LMI Only Branches (with %), MMCT Only Branches (with %), Both LMICT/MMCT Branches (with %), and Net Change
            - These categories are mutually exclusive (deduplicated)
            
            Write exactly 2 paragraphs that focus on BROAD TRENDS and MAJOR GAPS OR CHANGES:
            
            Paragraph 1: Focus on broad trends over time
            - Identify which banks have grown the most or shrunk the most over the study period (use Net Change column)
            - Note that bank mergers may result in dramatic changes in some branch networks
            - Describe overall patterns in how banks serve LMICT and MMCT communities based on percentages
            - Note any broad trends in branch distribution across the top banks
            
            Paragraph 2: Talk about the trends in the context of changes to the census boundaries in 2022.
            - Note that nationally there was a 30% increase in majority minority tracts but the vast majority of those were not LMI.
            - Note that locally this plays out in different ways, and that detailed closings and openings but large changes in 2022 should be interpreted as likely to be due to changes in those boundaries, not movement in the actual locations.
            
            WRITING REQUIREMENTS (NCRC Style Guide):
            - Plain English, accessible to non-technical readers
            - Write in objective, third-person style
            - NO first-person language (no "I", "we", "my", "our")
            - NO assumptions about causality or why patterns exist
            - NO policy recommendations
            - NO speculation about underlying reasons
            - Present ONLY what the data shows
            - Use professional, analytical tone
            - Focus on BROAD TRENDS and MAJOR GAPS/CHANGES only - avoid minor details
            - Limit discussion to observable patterns in the data
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
            - LMICT = Low-to-Moderate Income Census Tracts
            - MMCT = Majority-Minority Census Tracts
            - The table shows: Total Branches, LMI Only Branches (with %), MMCT Only Branches (with %), and Both LMICT/MMCT Branches (with %)
            - These categories are mutually exclusive (deduplicated)
            
            Write exactly 2 paragraphs that focus on BROAD TRENDS and MAJOR GAPS OR CHANGES:
            
            Paragraph 1: Focus on broad trends across counties
            - Compare the total number of branches across counties
            - Describe overall patterns in branch distribution between counties
            - Note any broad trends in how counties differ in total branch counts
            
            Paragraph 2: Focus on major gaps or changes in branch access
            - Identify major differences in the share of LMI Only, MMCT Only, and Both LMICT/MMCT branches between counties
            - Highlight which counties have notably more or fewer branches in LMICT or MMCT areas
            - Discuss what these major differences indicate about branch access patterns across counties
            
            WRITING REQUIREMENTS (NCRC Style Guide):
            - Plain English, accessible to non-technical readers
            - Write in objective, third-person style
            - NO first-person language (no "I", "we", "my", "our")
            - NO assumptions about causality or why patterns exist
            - NO policy recommendations
            - NO speculation about underlying reasons
            - Present ONLY what the data shows
            - Use professional, analytical tone
            - Focus on BROAD TRENDS and MAJOR GAPS/CHANGES only - avoid minor details
            - Include specific percentages when discussing categories
            - Limit discussion to observable patterns in the data
            - Reference specific counties and numbers from the data
            - Explicitly mention that the data is from {latest_year} (the most recent year in the report)
            """
            
        elif table_id == 'table4':
            # Table 4: Year-over-Year Trends
            trends_data = data.get('trends_data', [])
            trends_text = json.dumps(trends_data, indent=2)[:1500] if trends_data else "No trends data available"
            
            prompt = f"""
            Analyze the year-over-year trends table data and provide a narrative explanation:
            
            Counties: {counties}
            Years: {years[0]} to {years[-1]}
            
            Trends Data:
            {trends_text}
            
            IMPORTANT DEFINITIONS:
            - LMICT = Low-to-Moderate Income Census Tracts
            - MMCT = Majority-Minority Census Tracts
            
            Write 1-2 paragraphs that:
            1. Describe the year-over-year trends in branch counts
            2. Explain the patterns in LMI and MMCT branch changes
            3. Note any acceleration or deceleration in trends
            4. Discuss what the percentage changes mean
            
            WRITING REQUIREMENTS:
            - Plain English, accessible to non-technical readers
            - Write in objective, third-person style
            - NO first-person language (no "I", "we", "my", "our")
            - NO assumptions about causality or why patterns exist
            - NO policy recommendations
            - NO speculation about underlying reasons
            - Present ONLY what the data shows
            - Use professional, analytical tone
            """
        else:
            return ""
        
        return self._call_ai(prompt, max_tokens=600, temperature=0.3)
    
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
    
    def generate_market_concentration_discussion(self, data: Dict[str, Any], hhi_by_year: List[Dict[str, Any]]) -> str:
        """
        Generate a 2-paragraph discussion of market concentration trends using HHI by year data.
        
        Args:
            data: Dictionary with counties, years, and other context
            hhi_by_year: List of dictionaries with HHI data by year
        
        Returns:
            Two paragraphs discussing market concentration trends in plain English
        """
        counties = data.get('counties', [])
        years = data.get('years', [])
        counties_str = ', '.join(str(c) for c in counties) if counties else 'the selected area'
        year_range = f"{min(years)} to {max(years)}" if len(years) > 1 else str(years[0]) if years else "the selected years"
        
        # Format HHI data for the prompt
        hhi_text = ""
        if hhi_by_year:
            hhi_text = json.dumps(hhi_by_year, indent=2)
        
        prompt = f"""
        Generate a 2-paragraph discussion of market concentration trends for a bank branch analysis report.
        
        Counties: {counties_str}
        Years: {year_range}
        
        Market Concentration Data (HHI by year): {hhi_text}
        
        The Herfindahl-Hirschman Index (HHI) measures market concentration by calculating the sum of squared market shares for all bank networks based on total deposit amounts.
        HHI values range from 0 to 10,000, where:
        - Lower values (below 1,500) indicate more competitive markets with many bank networks sharing market share
        - Moderate values (1,500-2,500) indicate moderate concentration
        - Higher values (above 2,500) indicate highly concentrated markets dominated by fewer bank networks
        
        FIRST PARAGRAPH: Explain what the table shows in plain English without using a lot of numbers or calculations
        - Describe what HHI measures and what it means for market competition
        - Note the general trends in concentration levels over time
        - Explain what the different concentration levels mean for the banking market
        
        SECOND PARAGRAPH: Analyze the patterns and trends visible in the data
        - Discuss how concentration has changed over time
        - Note whether the market is becoming more or less competitive over time
        - Explain what these patterns mean for consumers and the banking market
        
        WRITING REQUIREMENTS:
        - Use PLAIN ENGLISH - avoid technical jargon
        - Do NOT include specific HHI numbers or calculations in the discussion
        - Focus on explaining what the patterns mean, not the mathematical details
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO assumptions about causality or why patterns exist
        - NO policy recommendations
        - NO speculation about underlying reasons
        - Present ONLY what the data shows
        - Use professional, analytical tone
        - AT LEAST 2 PARAGRAPHS (minimum requirement)
        
        Return your response as plain text (not JSON or markdown).
        """
        
        return self._call_ai(prompt, max_tokens=600, temperature=0.3)

    def generate_hhi_trends_narrative(self, data: Dict[str, Any]) -> str:
        """Generate AI narrative for HHI market concentration trends section."""
        json_data = convert_numpy_types(data)
        counties = data.get('counties', [])
        years = data.get('years', [])
        hhi_by_year = data.get('hhi_by_year', [])

        if not hhi_by_year or len(hhi_by_year) == 0:
            return "Market concentration data is not available for this analysis period."

        # Sort by year
        sorted_hhi = sorted(hhi_by_year, key=lambda x: int(x.get('year', 0)))
        hhi_text = json.dumps(sorted_hhi, indent=2)

        years_str = f"{years[0]} to {years[-1]}" if len(years) > 1 else str(years[0]) if years else "the study period"

        prompt = f"""
        Analyze market concentration trends using Herfindahl-Hirschman Index (HHI) data:

        Counties: {counties}
        Analysis Period: {years_str}

        HHI Data by Year:
        {hhi_text}

        IMPORTANT DEFINITIONS:
        - HHI (Herfindahl-Hirschman Index) measures market concentration based on deposit market share
        - HHI scale: 0-10,000
          * HHI < 1,500: Low concentration (competitive market)
          * HHI 1,500-2,500: Moderate concentration
          * HHI > 2,500: High concentration
        - Higher HHI values indicate greater market concentration (fewer banks controlling more of the market)
        - Lower HHI values suggest a more competitive market with diverse banking options

        ANALYSIS REQUIREMENTS:

        1. FIRST PARAGRAPH - Overall Market Concentration:
           - State the current HHI level (latest year) and concentration category
           - Describe the overall market structure (competitive, moderately concentrated, or highly concentrated)
           - Explain what the concentration level means for banking competition and service availability

        2. SECOND PARAGRAPH - Trends Over Time:
           - Analyze how HHI has changed over the study period
           - Identify whether the market has become more or less concentrated over time
           - Note any significant changes in concentration levels (e.g., moved from low to moderate, or moderate to high)
           - Discuss what these trends might indicate about market dynamics

        3. THIRD PARAGRAPH - Market Implications:
           - Explain how the concentration level affects competition, pricing, and service availability
           - Discuss implications for community access to banking services
           - Note any relationship between concentration trends and branch network changes

        WRITING REQUIREMENTS:
        - Use PLAIN ENGLISH - avoid excessive technical jargon
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO policy recommendations
        - Present ONLY what the data shows
        - Use professional, analytical tone
        - Include specific HHI values where relevant to support your analysis
        """

        return self._call_ai(prompt, max_tokens=800, temperature=0.3)

