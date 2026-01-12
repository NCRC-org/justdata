#!/usr/bin/env python3
"""
LoanTrends-specific AI analysis for HMDA quarterly national trends data.
Similar structure to LendSight but for national-level quarterly data.
"""

import json
from typing import Dict, Any
from justdata.shared.analysis.ai_provider import AIAnalyzer, convert_numpy_types


class LoanTrendsAnalyzer(AIAnalyzer):
    """AI analyzer specifically for HMDA quarterly national trends data."""
    
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
    
    def generate_overall_trends_intro(self, data: Dict[str, Any]) -> str:
        """Generate 3-sentence introduction for overall trends section."""
        selected_endpoints = data.get('selected_endpoints', [])
        time_period = data.get('time_period', 'last 12 quarters')
        
        # Count metrics by category
        categories = {
            'Loan & Application Counts': 0,
            'Credit Metrics': 0,
            'Loan Characteristics': 0,
            'Market Dynamics': 0,
            'Demographic Analysis': 0
        }
        
        for endpoint in selected_endpoints:
            if endpoint in ['applications', 'loans']:
                categories['Loan & Application Counts'] += 1
            elif 'credit' in endpoint:
                categories['Credit Metrics'] += 1
            elif endpoint in ['ltv', 'dti']:
                categories['Loan Characteristics'] += 1
            elif endpoint in ['interest-rates', 'denials', 'tlc']:
                categories['Market Dynamics'] += 1
            elif 're' in endpoint:  # race/ethnicity endpoints
                categories['Demographic Analysis'] += 1
        
        active_categories = [cat for cat, count in categories.items() if count > 0]
        
        prompt = f"""
        Generate exactly 3 sentences that introduce the overall national mortgage lending trends analysis.
        
        Time Period: {time_period}
        Metrics Analyzed: {', '.join(active_categories) if active_categories else 'Various mortgage lending metrics'}
        Number of Metrics: {len(selected_endpoints)}
        
        The introduction should:
        1. State that this report analyzes national-level quarterly mortgage lending trends from the CFPB HMDA Quarterly Data Graph API
        2. Mention the time period covered and the types of metrics included
        3. Note that the data represents aggregated national trends, not individual loan-level data
        
        WRITING REQUIREMENTS:
        - Exactly 3 sentences
        - Plain English, accessible to non-technical readers
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO assumptions about causality
        - NO policy recommendations
        - NO speculation about underlying reasons
        - Present ONLY what the data represents
        - Use professional, analytical tone
        """
        
        return self._call_ai(prompt, max_tokens=200, temperature=0.3)
    
    def generate_section_intro(self, section_name: str, data: Dict[str, Any]) -> str:
        """Generate 3-sentence introduction for each grouped section."""
        json_data = convert_numpy_types(data)
        selected_endpoints = data.get('selected_endpoints', [])
        time_period = data.get('time_period', 'last 12 quarters')
        
        # Get relevant endpoints for this section
        section_endpoints = []
        if section_name == 'Loan & Application Counts':
            section_endpoints = [e for e in selected_endpoints if e in ['applications', 'loans']]
        elif section_name == 'Credit Metrics':
            section_endpoints = [e for e in selected_endpoints if 'credit' in e]
        elif section_name == 'Loan Characteristics':
            section_endpoints = [e for e in selected_endpoints if e in ['ltv', 'dti']]
        elif section_name == 'Market Dynamics':
            section_endpoints = [e for e in selected_endpoints if e in ['interest-rates', 'denials', 'tlc']]
        elif section_name == 'Demographic Analysis':
            section_endpoints = [e for e in selected_endpoints if 're' in e]
        
        prompt = f"""
        Generate exactly 3 sentences that introduce the {section_name} section of the national mortgage lending trends report.
        
        Section: {section_name}
        Time Period: {time_period}
        Metrics in this section: {', '.join(section_endpoints) if section_endpoints else 'N/A'}
        
        The introduction should:
        1. Explain what types of metrics are covered in this section
        2. Describe the significance of these metrics for understanding mortgage lending trends
        3. Note the time period and data source (CFPB HMDA Quarterly Data Graph API)
        
        WRITING REQUIREMENTS:
        - Exactly 3 sentences
        - Plain English, accessible to non-technical readers
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO assumptions about causality
        - NO policy recommendations
        - NO speculation about underlying reasons
        - Present ONLY what the data represents
        - Use professional, analytical tone
        """
        
        return self._call_ai(prompt, max_tokens=200, temperature=0.3)
    
    def generate_table_intro(self, table_id: str, data: Dict[str, Any]) -> str:
        """Generate 3-sentence introduction for specific tables."""
        json_data = convert_numpy_types(data)
        table_data = data.get('table_data', {})
        endpoint = data.get('endpoint', table_id)
        time_period = data.get('time_period', 'last 12 quarters')
        
        # Get table metadata
        graph_data = data.get('graph_data', {}).get(endpoint, {})
        title = graph_data.get('title', f'Table: {endpoint}')
        y_label = graph_data.get('yLabel', 'Value')
        
        prompt = f"""
        Generate exactly 3 sentences that introduce the table showing {title}.
        
        Table: {title}
        Y-Axis Label: {y_label}
        Time Period: {time_period}
        Data Source: CFPB HMDA Quarterly Data Graph API
        
        The introduction should:
        1. Explain what this table shows (the metric and its measurement)
        2. Describe the time period and data granularity (quarterly national data)
        3. Note any important context about how to interpret the data
        
        WRITING REQUIREMENTS:
        - Exactly 3 sentences
        - Plain English, accessible to non-technical readers
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO assumptions about causality
        - NO policy recommendations
        - NO speculation about underlying reasons
        - Present ONLY what the data represents
        - Use professional, analytical tone
        """
        
        return self._call_ai(prompt, max_tokens=200, temperature=0.3)
    
    def generate_table_narrative(self, table_id: str, data: Dict[str, Any]) -> str:
        """Generate 2-paragraph narrative analysis for a specific table."""
        json_data = convert_numpy_types(data)
        table_data = data.get('table_data', [])
        endpoint = data.get('endpoint', table_id)
        time_period = data.get('time_period', 'last 12 quarters')
        
        # Get graph data for context
        graph_data = data.get('graph_data', {}).get(endpoint, {})
        title = graph_data.get('title', f'Table: {endpoint}')
        subtitle = graph_data.get('subtitle', '')
        y_label = graph_data.get('yLabel', 'Value')
        
        # Prepare table data summary (first 1000 chars)
        table_summary = json.dumps(table_data, indent=2)[:1000] if table_data else "No table data available"
        
        prompt = f"""
        Analyze the table data and provide a narrative explanation in exactly 2 paragraphs.
        
        Table: {title}
        Subtitle: {subtitle}
        Y-Axis Label: {y_label}
        Time Period: {time_period}
        
        Table Data (sample):
        {table_summary}
        
        {self._get_ncrc_report_sources()}
        
        Write exactly 2 paragraphs that:
        1. First paragraph: Describe the overall trends and patterns visible in the data over time, including any notable increases, decreases, or periods of stability. Reference specific quarters or time periods when discussing significant changes.
        2. Second paragraph: Analyze the relationships between different series (if multiple series are present), compare trends across different loan types or categories, and note any significant patterns or anomalies in the data.
        
        WRITING REQUIREMENTS:
        - Exactly 2 paragraphs (not 1, not 3)
        - Plain English, accessible to non-technical readers
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO assumptions about causality or why patterns exist
        - NO policy recommendations
        - NO speculation about underlying reasons
        - Present ONLY what the data shows
        - Use professional, analytical tone
        - Include specific numbers, percentages, or quarters when discussing trends
        - If referencing NCRC reports, include hypertext links in markdown format
        """
        
        return self._call_ai(prompt, max_tokens=600, temperature=0.3)
    
    def generate_overall_summary(self, data: Dict[str, Any]) -> str:
        """Generate executive summary of all trends."""
        json_data = convert_numpy_types(data)
        selected_endpoints = data.get('selected_endpoints', [])
        time_period = data.get('time_period', 'last 12 quarters')
        
        # Get summary of all tables
        tables_summary = {}
        for endpoint in selected_endpoints:
            table_data = data.get('tables', {}).get(endpoint, [])
            if table_data:
                # Get first and last values for trend indication
                if len(table_data) > 0:
                    first_row = table_data[0]
                    last_row = table_data[-1]
                    tables_summary[endpoint] = {
                        'first': first_row,
                        'last': last_row,
                        'quarters': len(table_data)
                    }
        
        summary_text = json.dumps(tables_summary, indent=2)[:2000] if tables_summary else "No data available"
        
        prompt = f"""
        Generate an executive summary of the overall national mortgage lending trends analysis.
        
        Time Period: {time_period}
        Metrics Analyzed: {len(selected_endpoints)} different metrics
        Selected Endpoints: {', '.join(selected_endpoints[:10])}{'...' if len(selected_endpoints) > 10 else ''}
        
        Tables Summary:
        {summary_text}
        
        {self._get_ncrc_report_sources()}
        
        Write 3-4 paragraphs that:
        1. Provide a high-level overview of the key trends across all metrics analyzed
        2. Highlight the most significant patterns or changes observed
        3. Note any relationships or correlations between different metrics
        4. Summarize the overall state of national mortgage lending based on the quarterly data
        
        WRITING REQUIREMENTS:
        - 3-4 paragraphs
        - Plain English, accessible to non-technical readers
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO assumptions about causality
        - NO policy recommendations
        - NO speculation about underlying reasons
        - Present ONLY what the data shows
        - Use professional, analytical tone
        - Include specific numbers or trends when relevant
        - If referencing NCRC reports, include hypertext links in markdown format
        """
        
        return self._call_ai(prompt, max_tokens=1000, temperature=0.3)
    
    def generate_executive_summary(self, data: Dict[str, Any]) -> str:
        """Generate executive summary (alias for generate_overall_summary)."""
        return self.generate_overall_summary(data)
    
    def generate_key_findings(self, data: Dict[str, Any]) -> str:
        """Generate 3-5 key findings from the analysis."""
        json_data = convert_numpy_types(data)
        selected_endpoints = data.get('selected_endpoints', [])
        time_period = data.get('time_period', 'last 12 quarters')
        
        # Extract key statistics from tables
        key_stats = []
        for endpoint in selected_endpoints[:5]:  # Limit to first 5 for summary
            table_data = data.get('tables', {}).get(endpoint, [])
            if table_data and len(table_data) > 0:
                first_row = table_data[0]
                last_row = table_data[-1]
                key_stats.append({
                    'endpoint': endpoint,
                    'first_quarter': first_row.get('Quarter', ''),
                    'last_quarter': last_row.get('Quarter', ''),
                    'data': {
                        'first': first_row,
                        'last': last_row
                    }
                })
        
        stats_text = json.dumps(key_stats, indent=2)[:1500] if key_stats else "No data available"
        
        prompt = f"""
        Generate 3-5 key findings from the national mortgage lending trends analysis.
        
        Time Period: {time_period}
        Metrics Analyzed: {len(selected_endpoints)}
        
        Key Statistics:
        {stats_text}
        
        {self._get_ncrc_report_sources()}
        
        FORMAT REQUIREMENTS:
        - Each finding must be formatted as: **Title:** Sentence describing the finding
        - The title should be a short, descriptive phrase (3-8 words) that summarizes the finding
        - The sentence after the colon should be ONE COMPLETE SENTENCE explaining the compelling statistic
        - Format as bullet points starting with "•"
        - Example format: • **Applications Trend:** National mortgage applications increased by 15.3% from Q1 2020 to Q4 2024, reaching 1.2 million applications in the most recent quarter.
        - Include specific numbers/percentages when available
        
        Focus on:
        - Most significant and compelling statistics from the data
        - Particularly notable trends or patterns
        - Title should be concise and descriptive (e.g., "Applications Growth", "Credit Score Trends", "Interest Rate Changes")
        
        WRITING REQUIREMENTS:
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO personal opinions or subjective statements
        - NO speculation about strategic implications or underlying causes
        - Present ONLY factual patterns and observable data trends
        - Each finding must have a bold title followed by a colon and one complete sentence
        - Use professional, analytical tone
        - If referencing NCRC reports, include hypertext links in markdown format
        """
        
        return self._call_ai(prompt, max_tokens=400, temperature=0.3)
    
    def generate_trends_analysis(self, data: Dict[str, Any]) -> str:
        """Generate trends analysis (same as overall summary for LoanTrends)."""
        return self.generate_overall_summary(data)




