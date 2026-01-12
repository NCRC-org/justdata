#!/usr/bin/env python3
"""
LenderProfile AI Summarizer
Generates AI-powered summaries and insights for lender intelligence reports.
Follows NCRC style guide and LendSight narrative prompt patterns.
"""

import json
import re
from typing import Dict, Any, Optional, List
from shared.analysis.ai_provider import AIAnalyzer, convert_numpy_types


class LenderProfileAnalyzer(AIAnalyzer):
    """AI analyzer for LenderProfile lender intelligence reports."""
    
    def _get_ncrc_report_sources(self) -> str:
        """Return formatted NCRC report sources for AI prompts."""
        return """
        REFERENCE SOURCES - NCRC Research Reports:
        You may reference these NCRC research reports if the information is relevant and valid for the analysis:
        - NCRC Mortgage Market Report Series: https://ncrc.org/mortgage-market-report-series-part-1-introduction-to-mortgage-market-trends/
        - CRA performance research and analysis
        - Fair lending analysis and studies
        - Community reinvestment research
        
        If you reference any of these reports, you MUST include a hypertext link using markdown format: [link text](URL)
        Example: "As noted in NCRC's research ([Mortgage Market Report Series](https://ncrc.org/mortgage-market-report-series-part-1-introduction-to-mortgage-market-trends/)), non-bank lenders now dominate the market."
        Only reference these sources if the information is directly relevant and supports your analysis.
        """
    
    def generate_executive_summary(self, data: Dict[str, Any], report_focus: Optional[str] = None) -> str:
        """
        Generate executive summary for lender intelligence report.
        
        Args:
            data: Report data dictionary
            report_focus: Optional user-specified focus (max 250 chars)
            
        Returns:
            Executive summary text
        """
        institution = data.get('institution', {})
        identifiers = data.get('identifiers', {})
        
        focus_context = ""
        if report_focus:
            focus_context = f"""
    
    USER REPORT FOCUS: {report_focus}
    The user has requested that this report focus on: {report_focus}
    While maintaining objectivity and factual analysis, ensure that sections relevant to this focus receive appropriate attention in the analysis.
    """
        
        prompt = f"""
        Generate an executive summary for a lender intelligence report.
        
        Institution: {institution.get('name', 'Unknown')}
        Type: {institution.get('type', 'Unknown')}
        Location: {institution.get('city', '')}, {institution.get('state', '')}
        Assets: {institution.get('assets', 'N/A')}
        FDIC Cert: {identifiers.get('fdic_cert', 'N/A')}
        RSSD ID: {identifiers.get('rssd_id', 'N/A')}
        LEI: {identifiers.get('lei', 'N/A')}
        
        {focus_context}
        
        {self._get_ncrc_report_sources()}
        
        The executive summary should:
        1. Provide a brief overview of the institution (name, type, size, location)
        2. Highlight 3-5 key findings from the comprehensive analysis
        3. Note any significant regulatory, financial, or strategic patterns
        4. Be concise (3-4 paragraphs maximum)
        
        WRITING REQUIREMENTS:
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO personal opinions or subjective statements
        - NO speculation about strategic implications or underlying causes
        - Present ONLY factual patterns and observable data trends
        - Use professional, analytical tone
        - Write in PLAIN ENGLISH - avoid jargon
        - If referencing NCRC reports, include hypertext links in markdown format: [link text](URL)
        - IMPORTANT: After the first full mention of the company name, use the stock ticker (if available) as a shorthand. For example, "Rocket Companies, Inc." becomes "RKT" in subsequent mentions.
        """
        
        # Handle both nested and flattened data formats
        # Flattened format has keys like institution_name, assets, branch_count, etc.
        # Nested format has institution: {name, type, ...}, identifiers: {...}, etc.

        if data.get('institution_name'):
            # Flattened format from build_ai_intelligence_summary
            structured_input = {
                'institution_name': data.get('institution_name'),
                'institution_type': data.get('institution_type', ''),
                'location': data.get('location', ''),
                'assets': data.get('assets'),
                'branch_count': data.get('branch_count', 0),
                'executive_compensation': data.get('executive_compensation', []),
                'financial_summary': data.get('financial_summary', {}),
                'cra_rating': data.get('cra_rating'),
                'complaint_count': data.get('complaint_count', 0),
                'complaint_topics': data.get('complaint_topics', []),
                'news_headlines': data.get('news_headlines', []),
                'hmda_summary': data.get('hmda_summary', {}),
                'sb_lending_summary': data.get('sb_lending_summary', {})
            }
        else:
            # Original nested format
            processed_data = data.get('processed', {})
            corporate_structure = data.get('corporate_structure', {})
            financial_processed = data.get('financial', {}).get('processed', {})

            structured_input = {
                'corporate': corporate_structure,
                'financial': financial_processed,
                'identifiers': identifiers,
                'institution': institution
            }

        prompt = f"""
        Generate a comprehensive 4-6 paragraph executive summary for this financial institution based on the following structured data:

        {json.dumps(structured_input, indent=2)[:8000]}

        {focus_context}

        {self._get_ncrc_report_sources()}

        Write as intelligence briefing for NCRC leadership preparing for meeting with this institution.

        COVERAGE REQUIREMENTS - Address ALL of these areas if data is available:
        1. **Institution Overview**: Size, geographic footprint, branch network trends
        2. **Lending Activity**: HMDA mortgage lending trends (temporal and geographic), small business lending patterns
        3. **Consumer Experience**: Complaint volumes and trends, product categories with issues
        4. **Market Position**: Analyst ratings, market sentiment from Seeking Alpha data
        5. **Community Focus**: CRA performance, presence in underserved communities
        6. **Recent Developments**: News, regulatory actions, strategic shifts

        FOCUS ON TRENDS NOT NUMBERS:
        - Describe whether metrics are INCREASING, DECREASING, or STABLE over time
        - Highlight GEOGRAPHIC patterns (which states/metros are growing vs shrinking)
        - Compare TEMPORAL trends (year-over-year changes, multi-year patterns)
        - Avoid listing raw numbers - instead describe what the numbers MEAN
        - Example: Instead of "Branch count was 4,500 in 2020 and 4,993 in 2024" say "The branch network expanded steadily over five years, adding nearly 500 locations"

        NCRC FOCUS AREAS (prioritize these topics):
        - Community investment commitments and affordable housing initiatives
        - Branch network presence in underserved communities
        - Mortgage lending in low-to-moderate income (LMI) areas
        - Small business lending patterns and community impact
        - Consumer complaint patterns and resolution trends
        - Recent news about community programs or regulatory actions

        WRITING REQUIREMENTS:
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO personal opinions or subjective statements
        - Present ONLY factual patterns and observable data trends
        - Use professional, analytical tone
        - Write in PLAIN ENGLISH - avoid jargon
        - If referencing NCRC reports, include hypertext links in markdown format: [link text](URL)
        """

        return self._call_ai(prompt, max_tokens=4000, temperature=0.3)

    def generate_key_findings(self, data: Dict[str, Any]) -> str:
        """
        Generate 5-7 key findings from the lender intelligence analysis.
        Uses bullet format matching lendsight/branchsight pattern.

        Args:
            data: Report data dictionary

        Returns:
            Key findings text (bullet list)
        """
        json_data = convert_numpy_types(data)

        # Get institution name from either format
        if data.get('institution_name'):
            inst_name = data.get('institution_name')
        else:
            institution = data.get('institution', {})
            inst_name = institution.get('name', 'Unknown')

        # Get corporate family info if available
        corporate_family = data.get('corporate_family', {})
        parent_name = corporate_family.get('parent_name')
        all_entities = corporate_family.get('all_entities', [])

        entity_context = ""
        if parent_name and parent_name != inst_name:
            entity_context = f"""
CORPORATE FAMILY CONTEXT:
This report covers {inst_name} and its corporate family.
- Parent Company: {parent_name}
- Total entities in family: {len(all_entities)}

CRITICAL: When citing data from the corporate family, ALWAYS specify which entity:
- "{parent_name} (parent holding company)" for parent data
- "{inst_name}" for the primary entity being analyzed
- Use "(subsidiary)" after any subsidiary name

Example: "Consumer complaints for JPMORGAN CHASE BANK (the primary bank) totaled 15,000, while CHASE HOME FINANCE (subsidiary) received 3,000."
"""

        prompt = f"""Generate 5-7 key findings for {inst_name}:
{entity_context}
Data: {json.dumps(json_data, indent=2)[:12000]}

FORMAT REQUIREMENTS:
- Each finding must be formatted as: • **Title:** Sentence describing the finding
- The title should be a short, descriptive phrase (3-6 words)
- The sentence after the colon should be ONE COMPLETE SENTENCE with specific data
- Format as bullet points starting with "•"
- Example: • **Mortgage Volume Declined:** Home lending applications fell from 110,674 in 2021 to 56,152 in 2024, a decrease of 49%.
- IMPORTANT: If data comes from multiple entities (parent + subsidiaries), clearly identify which entity the data belongs to

NCRC FOCUS AREAS (prioritize these topics):
- Community investment and development commitments
- Affordable housing investments and lending
- Philanthropy and charitable contributions
- CRA ratings and community reinvestment performance
- Branch network trends (expansion/contraction in underserved areas)
- Mortgage lending patterns in LMI communities
- Small business lending (note: 2020-2021 includes PPP loans)
- Consumer complaints and resolution patterns (specify if parent vs subsidiary)
- Recent news and developments
- Fair lending issues or enforcement actions (ALWAYS specify which entity)

DO NOT focus on:
- Tier 1 capital ratios or regulatory capital
- Credit loss allowances or loan loss reserves
- Pure financial metrics like ROA/ROE (unless tied to community impact)
- Investment grade ratings

WRITING REQUIREMENTS:
- Write in objective, third-person style
- NO first-person language (no "I", "we", "my", "our")
- NO personal opinions or subjective statements
- NO speculation about strategic implications or underlying causes
- Present ONLY factual patterns and observable data trends
- Use professional, analytical tone
- Include specific numbers when available
- ALWAYS attribute data to the specific entity (parent, subsidiary, or the bank itself)
"""

        # Use Sonnet 4.5 with temperature=0 for deterministic factual output
        # Increased max_tokens to allow for entity attribution in each finding
        return self._call_ai(prompt, max_tokens=1200, temperature=0)
    
    def generate_section_summary(self, section_name: str, section_data: Dict[str, Any], report_focus: Optional[str] = None) -> str:
        """
        Generate AI summary for a specific report section.
        
        Args:
            section_name: Name of the section (e.g., "Financial Profile", "CRA Performance")
            section_data: Data for the section
            report_focus: Optional user-specified focus
            
        Returns:
            Section summary text
        """
        json_data = convert_numpy_types(section_data)
        
        focus_context = ""
        if report_focus:
            focus_context = f"""
    
    USER REPORT FOCUS: {report_focus}
    If this section is relevant to the user's focus, ensure it receives appropriate attention.
    """
        
        prompt = f"""
        Generate a summary analysis for the "{section_name}" section of a lender intelligence report.
        
        Section Data: {json.dumps(json_data, indent=2)[:2000]}
        
        {focus_context}
        
        {self._get_ncrc_report_sources()}
        
        The summary should:
        1. Explain the key patterns and trends in the data
        2. Highlight the most significant findings
        3. Note any notable strengths or weaknesses
        4. Be 2-3 paragraphs maximum
        
        WRITING REQUIREMENTS:
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO personal opinions or subjective statements
        - NO speculation about strategic implications or underlying causes
        - Present ONLY factual patterns and observable data trends
        - Use professional, analytical tone
        - Write in PLAIN ENGLISH - avoid jargon
        - If you must use an acronym, explain it in plain English the first time
        - DO NOT create a "wall of numbers" - cite at most 2-3 specific percentages per paragraph
        - Focus on explaining what the data means, not just what it says
        - If referencing NCRC reports, include hypertext links in markdown format: [link text](URL)
        """
        
        return self._call_ai(prompt, max_tokens=800, temperature=0.3)
    
    def generate_advocacy_intelligence(self, data: Dict[str, Any], report_focus: Optional[str] = None) -> str:
        """
        Generate advocacy intelligence summary with scoring and recommendations.
        
        Args:
            data: Complete report data
            report_focus: Optional user-specified focus
            
        Returns:
            Advocacy intelligence analysis
        """
        json_data = convert_numpy_types(data)
        institution = data.get('institution', {})
        
        focus_context = ""
        if report_focus:
            focus_context = f"""
    
    USER REPORT FOCUS: {report_focus}
    The user has requested that this report focus on: {report_focus}
    Ensure the advocacy intelligence addresses this focus appropriately.
    """
        
        prompt = f"""
        Generate an advocacy intelligence summary for a lender intelligence report.
        
        Institution: {institution.get('name', 'Unknown')}
        Complete Report Data: {json.dumps(json_data, indent=2)[:3000]}
        
        {focus_context}
        
        {self._get_ncrc_report_sources()}
        
        The advocacy intelligence summary should include:
        1. Overall assessment (partner/monitor/oppose recommendation)
        2. CBA Opportunity Evaluation (if applicable):
           - Existing CBA status and expiration
           - Performance against commitments
           - Renewal likelihood
           - Negotiation leverage points
           - Score (0-100) with brief rationale
        3. Merger Opposition Decision Framework (if applicable):
           - Pending applications requiring action
           - CRA weaknesses to cite
           - Fair lending concerns
           - Market concentration arguments
           - Priority score (0-100) with brief rationale
        4. Partnership Opportunities:
           - Strong CRA performers with capacity
           - Geographic alignment with NCRC members
           - Collaborative potential
           - Partnership score (0-100) with brief rationale
        5. Priority Concerns Summary:
           - Top 3 regulatory/compliance issues
           - Top 3 CRA weaknesses
           - Top 3 leverage points
        6. Recommended Engagement Approach:
           - Initial contact strategy
           - Key decision-makers
           - Timing considerations
           - Specific talking points from data
        
        WRITING REQUIREMENTS:
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO personal opinions beyond data interpretation
        - Present factual patterns and observable data trends
        - Use professional, analytical tone
        - Write in PLAIN ENGLISH - avoid jargon
        - Be specific and actionable
        - If referencing NCRC reports, include hypertext links in markdown format: [link text](URL)
        """
        
        return self._call_ai(prompt, max_tokens=2000, temperature=0.3)
    
    def generate_sec_10k_analysis(self, institution_name: str, sec_data: Dict[str, Any], report_focus: Optional[str] = None) -> str:
        """
        Generate analysis of SEC 10-K filings for the institution.
        
        Args:
            institution_name: Institution name
            sec_data: SEC data dictionary with 10-K content
            report_focus: Optional user-specified focus
            
        Returns:
            SEC 10-K analysis text
        """
        focus_context = ""
        if report_focus:
            focus_context = f"""
    
    USER REPORT FOCUS: {report_focus}
    The user has requested that this report focus on: {report_focus}
    While maintaining objectivity, ensure SEC analysis addresses this focus appropriately.
    """
        
        # Extract 10-K content (limit to avoid token limits)
        filings_data = sec_data.get('filings', {})
        ten_k_content = filings_data.get('10k_content', [])
        content_summary = []
        for filing in ten_k_content[:5]:  # Last 5 filings
            filing_date = filing.get('filing_date', 'Unknown')
            content_preview = filing.get('content', '')[:5000]  # First 5000 chars per filing
            content_summary.append(f"Filing Date: {filing_date}\nContent Preview: {content_preview[:5000]}...")
        
        prompt = f"""
        Analyze SEC 10-K filings (annual reports) for {institution_name} to extract key business information and trends.
        
        INSTITUTION CONTEXT:
        - Institution: {institution_name}
        - Ticker: {sec_data.get('ticker', 'N/A')}
        - CIK: {sec_data.get('cik', 'N/A')}
        
        10-K FILING CONTENT:
        {chr(10).join(content_summary) if content_summary else 'No 10-K filing content available'}
        
        {focus_context}
        
        {self._get_ncrc_report_sources()}
        
        IMPORTANT DEFINITIONS:
        - 10-K: Annual report filed with the SEC (Securities and Exchange Commission) that provides comprehensive overview of a company's business, financial condition, and operations
        - Business Description: Section of 10-K that describes what the company does, its markets, and operations
        - Risk Factors: Section identifying potential risks to the business
        - Management Discussion and Analysis (MD&A): Section where management explains financial results and trends
        
        ANALYSIS REQUIREMENTS:
        1. FIRST PARAGRAPH: Summarize the institution's primary business activities, markets served, and geographic footprint based on the business description sections. Explain what the institution does in plain English.
        
        2. SECOND PARAGRAPH: Identify key financial trends over the 5-year period. Focus on the most significant changes in assets, revenue, net income, or other key metrics. Cite only the most compelling numbers (2-3 specific percentages or dollar amounts).
        
        3. THIRD PARAGRAPH (if data available): Highlight major strategic initiatives, business model changes, or market positioning shifts mentioned in the filings. Focus on factual statements made by management, not speculation.
        
        4. FOURTH PARAGRAPH (if data available): Note significant risk factors or regulatory challenges mentioned in the filings. Present these factually without speculation about implications.
        
        WRITING REQUIREMENTS:
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO personal opinions or subjective statements
        - NO speculation about strategic implications or underlying causes
        - Present ONLY factual patterns and observable data trends from the filings
        - Use professional, analytical tone
        - Write in PLAIN ENGLISH - avoid jargon and technical terms
        - If you must use an acronym, explain it in plain English the first time
        - DO NOT create a "wall of numbers" - cite at most 2-3 specific percentages or dollar amounts per paragraph
        - Focus on explaining what the data means, not just what it says
        - AT LEAST 2 PARAGRAPHS (minimum requirement)
        - If referencing NCRC reports, include hypertext links in markdown format: [link text](URL)
        """
        
        return self._call_ai(prompt, max_tokens=1200, temperature=0.3)
    
    def generate_branch_footprint_analysis(self, institution_name: str, branch_analysis: Dict[str, Any], report_focus: Optional[str] = None) -> str:
        """
        Generate analysis of branch network footprint and changes over time.
        
        Args:
            institution_name: Institution name
            branch_analysis: Branch network analysis results
            report_focus: Optional user-specified focus
            
        Returns:
            Branch footprint analysis text
        """
        focus_context = ""
        if report_focus:
            focus_context = f"""
    
    USER REPORT FOCUS: {report_focus}
    The user has requested that this report focus on: {report_focus}
    While maintaining objectivity, ensure branch analysis addresses this focus appropriately.
    """
        
        # Prepare branch data summary
        json_data = convert_numpy_types(branch_analysis)
        network_sizes = branch_analysis.get('total_branches_by_year', {})
        changes = branch_analysis.get('net_change_by_year', {})
        geographic_shifts = branch_analysis.get('geographic_shifts', {})
        trends = branch_analysis.get('trends', {})
        
        prompt = f"""
        Analyze the branch network footprint and changes over time for {institution_name}.
        
        INSTITUTION CONTEXT:
        - Institution: {institution_name}
        
        BRANCH NETWORK DATA:
        Network Size by Year:
        {json.dumps(network_sizes, indent=2)[:1000]}
        
        Year-over-Year Changes:
        {json.dumps(changes, indent=2)[:1000]}
        
        Geographic Patterns:
        {json.dumps(geographic_shifts, indent=2)[:1500]}
        
        Network Trends:
        {json.dumps(trends, indent=2)[:1000]}
        
        {focus_context}
        
        {self._get_ncrc_report_sources()}
        
        IMPORTANT DEFINITIONS:
        - Branch Network: Physical locations where the institution serves customers
        - CBSA: Core Based Statistical Area (metro area) - a geographic region defined by the Census Bureau
        - Branch Closure: A branch that existed in one year but not in the next
        - Branch Opening: A branch that did not exist in one year but appears in the next
        - Geographic Reallocation: Shifting branch locations from one area to another
        
        ANALYSIS REQUIREMENTS:
        1. FIRST PARAGRAPH: Describe the overall branch network size and trend over the analysis period. Explain how the network has changed in total size (grown, shrunk, or remained stable). Cite the most significant change (e.g., "The network grew from X branches in 2021 to Y branches in 2025, representing a Z% increase").
        
        2. SECOND PARAGRAPH: Analyze the pace and pattern of branch closures and openings. Identify the years with the most significant changes and whether closures or openings dominated. Focus on the most compelling numbers (e.g., "In 2023, the institution closed X branches while opening Y branches, resulting in a net decrease of Z branches").
        
        3. THIRD PARAGRAPH: Describe geographic patterns in branch changes. Identify which states, metro areas (CBSAs), or cities saw the most closures or openings. Explain any geographic reallocation patterns (e.g., "Branch closures were concentrated in State X and City Y, while new openings were focused in State Z and City W"). Cite only the most significant geographic patterns (2-3 specific locations).
        
        4. FOURTH PARAGRAPH (if data available): Note any notable trends in branch network strategy, such as shifts toward certain markets, withdrawal from others, or overall network optimization patterns. Present these factually based on the data patterns.
        
        WRITING REQUIREMENTS:
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO personal opinions or subjective statements
        - NO speculation about strategic implications or underlying causes
        - Present ONLY factual patterns and observable data trends
        - Use professional, analytical tone
        - Write in PLAIN ENGLISH - avoid jargon
        - If you must use an acronym, explain it in plain English the first time
        - DO NOT create a "wall of numbers" - cite at most 2-3 specific numbers per paragraph
        - Focus on explaining what the patterns mean, not just what they are
        - AT LEAST 2 PARAGRAPHS (minimum requirement)
        - If referencing NCRC reports, include hypertext links in markdown format: [link text](URL)
        """
        
        return self._call_ai(prompt, max_tokens=1000, temperature=0.3)
    
    def generate_seeking_alpha_analysis(self, institution_name: str, seeking_alpha_data: Dict[str, Any], report_focus: Optional[str] = None) -> str:
        """
        Generate analysis of Seeking Alpha financial data and analyst ratings.
        
        Args:
            institution_name: Institution name
            seeking_alpha_data: Seeking Alpha data dictionary
            report_focus: Optional user-specified focus
            
        Returns:
            Seeking Alpha analysis text
        """
        focus_context = ""
        if report_focus:
            focus_context = f"""
    
    USER REPORT FOCUS: {report_focus}
    The user has requested that this report focus on: {report_focus}
    While maintaining objectivity, ensure Seeking Alpha analysis addresses this focus appropriately.
    """
        
        # Extract key data
        ticker = seeking_alpha_data.get('ticker', 'N/A')
        financials = seeking_alpha_data.get('financials', [])
        ratings = seeking_alpha_data.get('ratings', {})
        leading_story = seeking_alpha_data.get('leading_story', {})
        
        # Prepare financial summary
        financial_summary = []
        if financials:
            for section in financials[:5]:  # Top 5 sections
                title = section.get('title', 'Unknown')
                rows = section.get('rows', [])[:3]  # Top 3 rows per section
                financial_summary.append(f"Section: {title}\nRows: {json.dumps(rows, indent=2)[:500]}")
        
        # Prepare ratings summary
        ratings_summary = {}
        if ratings and isinstance(ratings, dict):
            ratings_data = ratings.get('data', [])
            if ratings_data:
                latest_rating = ratings_data[0].get('attributes', {}).get('ratings', {})
                ratings_summary = {
                    'authors_rating': latest_rating.get('authorsRating'),
                    'sell_side_rating': latest_rating.get('sellSideRating'),
                    'quant_rating': latest_rating.get('quantRating'),
                    'buy_count': latest_rating.get('authorsRatingBuyCount'),
                    'hold_count': latest_rating.get('authorsRatingHoldCount'),
                    'sell_count': latest_rating.get('authorsRatingSellCount')
                }
        
        # Prepare leading story summary
        story_summary = []
        if leading_story:
            stories = leading_story.get('leading_news_story', [])[:3]  # Top 3 stories
            for story in stories:
                attrs = story.get('attributes', {})
                story_summary.append(f"Headline: {attrs.get('headline', 'N/A')}\nType: {attrs.get('type', 'N/A')}")
        
        prompt = f"""
        Analyze financial performance and market positioning for {institution_name} based on Seeking Alpha data.
        
        INSTITUTION CONTEXT:
        - Institution: {institution_name}
        - Ticker: {ticker}
        
        FINANCIAL DATA:
        {chr(10).join(financial_summary)[:2000] if financial_summary else 'No financial data available'}
        
        ANALYST RATINGS:
        {json.dumps(ratings_summary, indent=2)[:1000] if ratings_summary else 'No ratings data available'}
        
        RECENT NEWS/ARTICLES:
        {chr(10).join(story_summary)[:1000] if story_summary else 'No recent news available'}
        
        {focus_context}
        
        {self._get_ncrc_report_sources()}
        
        IMPORTANT DEFINITIONS:
        - Ticker Symbol: Stock market symbol used to identify the company (e.g., FITB for Fifth Third Bancorp)
        - Analyst Rating: Recommendation from financial analysts (Buy, Hold, Sell)
        - Quant Rating: Quantitative rating based on financial metrics and algorithms
        - Sell-Side Rating: Average rating from Wall Street analysts
        - Revenue: Total income from business operations
        - Net Income: Profit after all expenses
        
        ANALYSIS REQUIREMENTS:
        1. FIRST PARAGRAPH: Summarize the institution's financial performance based on the financial data provided. Focus on the most significant trends in revenue, income, or other key financial metrics. Explain what the financial data shows in plain English. Cite only the most compelling numbers (2-3 specific dollar amounts or percentages).
        
        2. SECOND PARAGRAPH: Analyze analyst ratings and market sentiment. Explain what the ratings indicate about how analysts view the institution. Note the distribution of Buy/Hold/Sell recommendations and what the quantitative rating suggests. Present this factually without speculation.
        
        3. THIRD PARAGRAPH (if leading stories available): Summarize recent news or articles about the institution. Focus on the most significant headlines or developments mentioned. Present these factually as reported information.
        
        4. FOURTH PARAGRAPH (if data available): Note any notable patterns in financial performance relative to industry trends or market conditions. Present these factually based on the data provided.
        
        WRITING REQUIREMENTS:
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO personal opinions or subjective statements
        - NO speculation about strategic implications or underlying causes
        - Present ONLY factual patterns and observable data trends
        - Use professional, analytical tone
        - Write in PLAIN ENGLISH - avoid jargon
        - If you must use an acronym, explain it in plain English the first time
        - DO NOT create a "wall of numbers" - cite at most 2-3 specific numbers per paragraph
        - Focus on explaining what the data means, not just what it says
        - AT LEAST 2 PARAGRAPHS (minimum requirement)
        - If referencing NCRC reports, include hypertext links in markdown format: [link text](URL)
        """
        
        return self._call_ai(prompt, max_tokens=1000, temperature=0.3)
    
    # ========== 5 Strategic AI Calls (Code-First Architecture) ==========
    
    def generate_strategy_from_item1(self, item1_text: str) -> Dict[str, Any]:
        """AI Call 1: Extract strategic priorities from Item 1 business description."""
        text = item1_text[:50000] if len(item1_text) > 50000 else item1_text
        prompt = f"""Analyze this business description section (Item 1) from a 10-K filing.

ITEM 1 TEXT:
{text}

Extract and structure as a JSON object:
1. Strategic priorities mentioned by management (array of strings)
2. Key performance drivers identified (array of strings)
3. Geographic expansion plans (array of strings)
4. Challenges or headwinds mentioned (array of strings)
5. Forward-looking statements about growth areas (array of strings)

Return ONLY a JSON object with these five arrays. No additional commentary.
Format: {{"strategic_priorities": [...], "performance_drivers": [...], "expansion_plans": [...], "challenges": [...], "growth_areas": [...]}}
"""
        response = self._call_ai(prompt, max_tokens=500, temperature=0.2)
        try:
            if '```json' in response:
                json_str = response.split('```json')[1].split('```')[0].strip()
            elif '```' in response:
                json_str = response.split('```')[1].split('```')[0].strip()
            else:
                json_str = response.strip()
            return json.loads(json_str)
        except:
            return {'strategic_priorities': [], 'performance_drivers': [], 'expansion_plans': [], 'challenges': [], 'growth_areas': [], 'raw_response': response}
    
    def generate_risks_from_item1a(self, item1a_text: str) -> List[Dict[str, Any]]:
        """AI Call 2: Extract top risk categories from Item 1A risk factors."""
        text = item1a_text[:50000] if len(item1a_text) > 50000 else item1a_text
        prompt = f"""Review these risk factors from Item 1A of a 10-K filing.

ITEM 1A RISK FACTORS:
{text}

Identify the top 5 most significant risk categories. For each: category_name, description (1 sentence), is_company_specific (true/false).

Return ONLY a JSON array. Format: [{{"category_name": "...", "description": "...", "is_company_specific": true}}, ...]
"""
        response = self._call_ai(prompt, max_tokens=800, temperature=0.2)
        try:
            if '```json' in response:
                json_str = response.split('```json')[1].split('```')[0].strip()
            elif '```' in response:
                json_str = response.split('```')[1].split('```')[0].strip()
            else:
                json_str = response.strip()
            return json.loads(json_str)
        except:
            return []
    
    def generate_mda_insights_from_item7(self, item7_text: str) -> Dict[str, Any]:
        """AI Call 3: Extract insights from Item 7 MD&A section."""
        text = item7_text[:50000] if len(item7_text) > 50000 else item7_text
        prompt = f"""Analyze this Management Discussion & Analysis section (Item 7) from a 10-K filing.

ITEM 7 MD&A:
{text}

Extract as JSON object: strategic_priorities, performance_drivers, expansion_plans, challenges, growth_areas (each an array of strings).

Return ONLY the JSON object. No preamble.
"""
        response = self._call_ai(prompt, max_tokens=800, temperature=0.2)
        try:
            if '```json' in response:
                json_str = response.split('```json')[1].split('```')[0].strip()
            elif '```' in response:
                json_str = response.split('```')[1].split('```')[0].strip()
            else:
                json_str = response.strip()
            return json.loads(json_str)
        except:
            return {'strategic_priorities': [], 'performance_drivers': [], 'expansion_plans': [], 'challenges': [], 'growth_areas': []}
    
    def generate_news_sentiment(self, news_processed: Dict[str, Any]) -> Dict[str, Any]:
        """AI Call 4: Analyze sentiment and categorize news articles."""
        categorized = news_processed.get('categorized', {})
        recent = news_processed.get('recent', [])[:20]
        article_summaries = [f"Title: {a.get('title', '')}\nDescription: {a.get('description', '')[:200]}" for a in recent]
        prompt = f"""Analyze sentiment of these news articles about a financial institution.

ARTICLES:
{chr(10).join(article_summaries)[:3000]}

CATEGORIZED: Executive: {len(categorized.get('executive', []))}, Strategy: {len(categorized.get('strategy', []))}, Regulatory: {len(categorized.get('regulatory', []))}, Financial: {len(categorized.get('financial', []))}, Controversy: {len(categorized.get('controversy', []))}

Return JSON: {{"overall_sentiment": "positive|negative|neutral|mixed", "key_themes": [...], "controversy_level": "low|medium|high", "regulatory_attention": "low|medium|high", "summary": "2-3 sentence summary"}}

Return ONLY the JSON object.
"""
        response = self._call_ai(prompt, max_tokens=400, temperature=0.2)
        try:
            if '```json' in response:
                json_str = response.split('```json')[1].split('```')[0].strip()
            elif '```' in response:
                json_str = response.split('```')[1].split('```')[0].strip()
            else:
                json_str = response.strip()
            return json.loads(json_str)
        except:
            return {'overall_sentiment': 'neutral', 'key_themes': [], 'controversy_level': 'low', 'regulatory_attention': 'low', 'summary': 'News sentiment analysis unavailable.'}
    
    def generate_executive_summary_final(self, structured_data: Dict[str, Any], report_focus: Optional[str] = None) -> str:
        """AI Call 5: Generate final executive summary from all structured data."""
        focus_context = f"\n\nUSER REPORT FOCUS: {report_focus}\n" if report_focus else ""
        data_summary = {
            'corporate': {'legal_name': structured_data.get('corporate', {}).get('legal_name'), 'headquarters': structured_data.get('corporate', {}).get('headquarters', {}), 'total_subsidiaries': len(structured_data.get('corporate', {}).get('subsidiaries', {}).get('direct', []))},
            'financial': {'assets': structured_data.get('financial', {}).get('metrics', {}).get('assets'), 'roa': structured_data.get('financial', {}).get('metrics', {}).get('roa'), 'roe': structured_data.get('financial', {}).get('metrics', {}).get('roe'), 'asset_growth': structured_data.get('financial', {}).get('growth', {}).get('asset_cagr')},
            'branch_network': {'total_branches': structured_data.get('branch_network', {}).get('total_branches_current'), 'trend': structured_data.get('branch_network', {}).get('trends', {}).get('overall_trend')},
            'analyst_ratings': {'distribution': structured_data.get('analyst_ratings', {}).get('distribution', {}), 'quant_rating': structured_data.get('analyst_ratings', {}).get('quant_rating')},
            'complaints': {'total': structured_data.get('complaints', {}).get('summary', {}).get('total'), 'top_issues': structured_data.get('complaints', {}).get('top_issues', [])[:3]},
            'litigation': {'total_cases': structured_data.get('litigation', {}).get('summary', {}).get('total_cases'), 'active_cases': structured_data.get('litigation', {}).get('summary', {}).get('active_cases')}
        }
        prompt = f"""Generate a 2-3 paragraph executive summary for this financial institution based on structured data:

{json.dumps(data_summary, indent=2)[:5000]}

{focus_context}

{self._get_ncrc_report_sources()}

Write as intelligence briefing for NCRC leadership. Focus on: what they do, how they make money, recent performance, strategic direction, key executives. Professional tone, 2-3 paragraphs.

WRITING REQUIREMENTS:
- Objective, third-person style
- NO first-person language
- NO personal opinions
- NO speculation
- Present ONLY factual patterns
- Professional, analytical tone
- PLAIN ENGLISH - avoid jargon
- If referencing NCRC reports, include hypertext links: [link text](URL)
"""
        return self._call_ai(prompt, max_tokens=600, temperature=0.3)
    
    def generate_combined_financial_overview(self, institution_name: str, sec_data: Dict[str, Any], seeking_alpha_data: Dict[str, Any], report_focus: Optional[str] = None) -> str:
        """
        Generate combined financial overview using both SEC and Seeking Alpha data.
        
        Args:
            institution_name: Institution name
            sec_data: SEC data dictionary
            seeking_alpha_data: Seeking Alpha data dictionary
            report_focus: Optional user-specified focus
            
        Returns:
            Combined financial overview text
        """
        focus_context = ""
        if report_focus:
            focus_context = f"""
    
    USER REPORT FOCUS: {report_focus}
    The user has requested that this report focus on: {report_focus}
    While maintaining objectivity, ensure financial overview addresses this focus appropriately.
    """
        
        # Extract key summaries
        sec_summary = {
            'ticker': sec_data.get('ticker'),
            'cik': sec_data.get('cik'),
            'filings_count': len(sec_data.get('filings', {}).get('10k', []))
        }
        
        sa_summary = {
            'ticker': seeking_alpha_data.get('ticker'),
            'has_financials': bool(seeking_alpha_data.get('financials')),
            'has_ratings': bool(seeking_alpha_data.get('ratings')),
            'ratings_data': seeking_alpha_data.get('ratings', {}).get('data', [{}])[0].get('attributes', {}).get('ratings', {}) if seeking_alpha_data.get('ratings', {}).get('data') else {}
        }
        
        prompt = f"""
        Generate a combined financial overview for {institution_name} synthesizing information from SEC filings and Seeking Alpha financial data.
        
        INSTITUTION CONTEXT:
        - Institution: {institution_name}
        - Ticker: {sec_summary.get('ticker') or sa_summary.get('ticker', 'N/A')}
        
        SEC FILINGS SUMMARY:
        - Number of 10-K filings analyzed: {sec_summary.get('filings_count', 0)}
        - CIK: {sec_summary.get('cik', 'N/A')}
        
        SEEKING ALPHA SUMMARY:
        - Financial data available: {sa_summary.get('has_financials', False)}
        - Analyst ratings available: {sa_summary.get('has_ratings', False)}
        - Key ratings: {json.dumps(sa_summary.get('ratings_data', {}), indent=2)[:500]}
        
        {focus_context}
        
        {self._get_ncrc_report_sources()}
        
        ANALYSIS REQUIREMENTS:
        1. FIRST PARAGRAPH: Provide an overview of the institution's financial position and performance. Synthesize information from both SEC filings (official regulatory filings) and Seeking Alpha (market analysis). Explain the institution's size, profitability, and financial health in plain English. Cite only the most compelling numbers (2-3 specific metrics).
        
        2. SECOND PARAGRAPH: Analyze how the institution is viewed by the market and analysts. Discuss analyst ratings, market sentiment, and any notable trends in how financial analysts assess the institution. Present this factually based on the ratings data.
        
        3. THIRD PARAGRAPH (if data available): Note any significant financial trends, strategic initiatives, or market positioning that emerges from the combined analysis. Focus on factual patterns observable in both data sources.
        
        WRITING REQUIREMENTS:
        - Write in objective, third-person style
        - NO first-person language (no "I", "we", "my", "our")
        - NO personal opinions or subjective statements
        - NO speculation about strategic implications or underlying causes
        - Present ONLY factual patterns and observable data trends
        - Use professional, analytical tone
        - Write in PLAIN ENGLISH - avoid jargon
        - If you must use an acronym, explain it in plain English the first time
        - DO NOT create a "wall of numbers" - cite at most 2-3 specific numbers per paragraph
        - Focus on explaining what the data means, not just what it says
        - AT LEAST 2 PARAGRAPHS (minimum requirement)
        - If referencing NCRC reports, include hypertext links in markdown format: [link text](URL)
        """
        
        return self._call_ai(prompt, max_tokens=1000, temperature=0.3)
    
    # ========== 5 Strategic AI Calls (Code-First Architecture) ==========
    
    def generate_strategy_from_item1(self, item1_text: str) -> Dict[str, Any]:
        """AI Call 1: Extract strategic priorities from Item 1 business description."""
        text = item1_text[:50000] if len(item1_text) > 50000 else item1_text
        prompt = f"""Analyze this business description section (Item 1) from a 10-K filing.

ITEM 1 TEXT:
{text}

Extract and structure as a JSON object:
1. Strategic priorities mentioned by management (array of strings)
2. Key performance drivers identified (array of strings)
3. Geographic expansion plans (array of strings)
4. Challenges or headwinds mentioned (array of strings)
5. Forward-looking statements about growth areas (array of strings)

Return ONLY a JSON object with these five arrays. No additional commentary.
Format: {{"strategic_priorities": [...], "performance_drivers": [...], "expansion_plans": [...], "challenges": [...], "growth_areas": [...]}}
"""
        response = self._call_ai(prompt, max_tokens=500, temperature=0.2)
        try:
            if '```json' in response:
                json_str = response.split('```json')[1].split('```')[0].strip()
            elif '```' in response:
                json_str = response.split('```')[1].split('```')[0].strip()
            else:
                json_str = response.strip()
            return json.loads(json_str)
        except:
            return {'strategic_priorities': [], 'performance_drivers': [], 'expansion_plans': [], 'challenges': [], 'growth_areas': [], 'raw_response': response}
    
    def generate_risks_from_item1a(self, item1a_text: str) -> List[Dict[str, Any]]:
        """AI Call 2: Extract top risk categories from Item 1A risk factors."""
        text = item1a_text[:50000] if len(item1a_text) > 50000 else item1a_text
        prompt = f"""Review these risk factors from Item 1A of a 10-K filing.

ITEM 1A RISK FACTORS:
{text}

Identify the top 5 most significant risk categories. For each: category_name, description (1 sentence), is_company_specific (true/false).

Return ONLY a JSON array. Format: [{{"category_name": "...", "description": "...", "is_company_specific": true}}, ...]
"""
        response = self._call_ai(prompt, max_tokens=800, temperature=0.2)
        try:
            if '```json' in response:
                json_str = response.split('```json')[1].split('```')[0].strip()
            elif '```' in response:
                json_str = response.split('```')[1].split('```')[0].strip()
            else:
                json_str = response.strip()
            return json.loads(json_str)
        except:
            return []
    
    def generate_mda_insights_from_item7(self, item7_text: str) -> Dict[str, Any]:
        """AI Call 3: Extract insights from Item 7 MD&A section."""
        text = item7_text[:50000] if len(item7_text) > 50000 else item7_text
        prompt = f"""Analyze this Management Discussion & Analysis section (Item 7) from a 10-K filing.

ITEM 7 MD&A:
{text}

Extract as JSON object: strategic_priorities, performance_drivers, expansion_plans, challenges, growth_areas (each an array of strings).

Return ONLY the JSON object. No preamble.
"""
        response = self._call_ai(prompt, max_tokens=800, temperature=0.2)
        try:
            if '```json' in response:
                json_str = response.split('```json')[1].split('```')[0].strip()
            elif '```' in response:
                json_str = response.split('```')[1].split('```')[0].strip()
            else:
                json_str = response.strip()
            return json.loads(json_str)
        except:
            return {'strategic_priorities': [], 'performance_drivers': [], 'expansion_plans': [], 'challenges': [], 'growth_areas': []}
    
    def generate_news_sentiment(self, news_processed: Dict[str, Any]) -> Dict[str, Any]:
        """AI Call 4: Analyze sentiment and categorize news articles."""
        categorized = news_processed.get('categorized', {})
        recent = news_processed.get('recent', [])[:20]
        article_summaries = [f"Title: {a.get('title', '')}\nDescription: {a.get('description', '')[:200]}" for a in recent]
        prompt = f"""Analyze sentiment of these news articles about a financial institution.

ARTICLES:
{chr(10).join(article_summaries)[:3000]}

CATEGORIZED: Executive: {len(categorized.get('executive', []))}, Strategy: {len(categorized.get('strategy', []))}, Regulatory: {len(categorized.get('regulatory', []))}, Financial: {len(categorized.get('financial', []))}, Controversy: {len(categorized.get('controversy', []))}

Return JSON: {{"overall_sentiment": "positive|negative|neutral|mixed", "key_themes": [...], "controversy_level": "low|medium|high", "regulatory_attention": "low|medium|high", "summary": "2-3 sentence summary"}}

Return ONLY the JSON object.
"""
        response = self._call_ai(prompt, max_tokens=400, temperature=0.2)
        try:
            if '```json' in response:
                json_str = response.split('```json')[1].split('```')[0].strip()
            elif '```' in response:
                json_str = response.split('```')[1].split('```')[0].strip()
            else:
                json_str = response.strip()
            return json.loads(json_str)
        except:
            return {'overall_sentiment': 'neutral', 'key_themes': [], 'controversy_level': 'low', 'regulatory_attention': 'low', 'summary': 'News sentiment analysis unavailable.'}
    
    def generate_executive_summary_final(self, structured_data: Dict[str, Any], report_focus: Optional[str] = None) -> str:
        """AI Call 5: Generate final executive summary from all structured data."""
        focus_context = f"\n\nUSER REPORT FOCUS: {report_focus}\n" if report_focus else ""
        data_summary = {
            'corporate': {'legal_name': structured_data.get('corporate', {}).get('legal_name'), 'headquarters': structured_data.get('corporate', {}).get('headquarters', {}), 'total_subsidiaries': len(structured_data.get('corporate', {}).get('subsidiaries', {}).get('direct', []))},
            'financial': {'assets': structured_data.get('financial', {}).get('metrics', {}).get('assets'), 'roa': structured_data.get('financial', {}).get('metrics', {}).get('roa'), 'roe': structured_data.get('financial', {}).get('metrics', {}).get('roe'), 'asset_growth': structured_data.get('financial', {}).get('growth', {}).get('asset_cagr')},
            'branch_network': {'total_branches': structured_data.get('branch_network', {}).get('total_branches_current'), 'trend': structured_data.get('branch_network', {}).get('trends', {}).get('overall_trend')},
            'analyst_ratings': {'distribution': structured_data.get('analyst_ratings', {}).get('distribution', {}), 'quant_rating': structured_data.get('analyst_ratings', {}).get('quant_rating')},
            'complaints': {'total': structured_data.get('complaints', {}).get('summary', {}).get('total'), 'top_issues': structured_data.get('complaints', {}).get('top_issues', [])[:3]},
            'litigation': {'total_cases': structured_data.get('litigation', {}).get('summary', {}).get('total_cases'), 'active_cases': structured_data.get('litigation', {}).get('summary', {}).get('active_cases')}
        }
        prompt = f"""Generate a 2-3 paragraph executive summary for this financial institution based on structured data:

{json.dumps(data_summary, indent=2)[:5000]}

{focus_context}

{self._get_ncrc_report_sources()}

Write as intelligence briefing for NCRC leadership. Focus on: what they do, how they make money, recent performance, strategic direction, key executives. Professional tone, 2-3 paragraphs.

WRITING REQUIREMENTS:
- Objective, third-person style
- NO first-person language
- NO personal opinions
- NO speculation
- Present ONLY factual patterns
- Professional, analytical tone
- PLAIN ENGLISH - avoid jargon
- If referencing NCRC reports, include hypertext links: [link text](URL)
"""
        return self._call_ai(prompt, max_tokens=600, temperature=0.3)

    def generate_executive_summary_from_analysts(
        self,
        institution_name: str,
        analyst_summaries: Dict[str, Any],
        entity_resolution: Dict[str, Any],
        report_focus: Optional[str] = None
    ) -> str:
        """
        Generate executive summary using Tier 1 analyst summaries (Tier 2 synthesis).

        This method uses the pre-analyzed summaries from the Haiku data source analysts
        to produce a comprehensive, well-structured executive summary.

        Args:
            institution_name: Institution name
            analyst_summaries: Compiled summaries from DataSourceAnalysts
            entity_resolution: AI entity resolution with corporate context
            report_focus: Optional user-specified focus

        Returns:
            Executive summary text
        """
        focus_context = ""
        if report_focus:
            focus_context = f"""
USER REPORT FOCUS: {report_focus}
The user has requested that this report focus on: {report_focus}
Prioritize information relevant to this focus.
"""

        # Extract pre-analyzed data
        all_findings = analyst_summaries.get('all_key_findings', [])
        ncrc_insights = analyst_summaries.get('all_ncrc_insights', [])
        risk_flags = analyst_summaries.get('all_risk_flags', [])
        positive_indicators = analyst_summaries.get('all_positive_indicators', [])
        data_quality = analyst_summaries.get('data_quality_summary', {})

        # Get individual analyst summaries
        sec_summary = analyst_summaries.get('analyst_summaries', {}).get('sec', {})
        hmda_summary = analyst_summaries.get('analyst_summaries', {}).get('hmda', {})
        branches_summary = analyst_summaries.get('analyst_summaries', {}).get('branches', {})
        cra_summary = analyst_summaries.get('analyst_summaries', {}).get('cra', {})
        cfpb_summary = analyst_summaries.get('analyst_summaries', {}).get('cfpb', {})
        news_summary = analyst_summaries.get('analyst_summaries', {}).get('news', {})
        seeking_alpha_summary = analyst_summaries.get('analyst_summaries', {}).get('seeking_alpha', {})
        congressional_summary = analyst_summaries.get('analyst_summaries', {}).get('congressional', {})

        # Get corporate context from entity resolution
        corporate_context = entity_resolution.get('corporate_context', {})
        institution_type = corporate_context.get('institution_type', 'Unknown')
        is_holding_company = corporate_context.get('is_holding_company', False)
        consumer_brands = corporate_context.get('consumer_brands', [])

        prompt = f"""Generate a comprehensive 4-6 paragraph executive summary for {institution_name} based on pre-analyzed data from multiple specialist analysts.

INSTITUTION CONTEXT:
- Name: {institution_name}
- Type: {institution_type}
- Is Holding Company: {is_holding_company}
- Consumer Brands: {', '.join(consumer_brands) if consumer_brands else 'N/A'}

{focus_context}

PRE-ANALYZED KEY FINDINGS (from 6 specialist analysts):
{chr(10).join(all_findings[:20])}

NCRC-RELEVANT INSIGHTS:
{chr(10).join(ncrc_insights[:10])}

RISK FLAGS:
{chr(10).join(risk_flags[:8])}

POSITIVE INDICATORS:
{chr(10).join(positive_indicators[:8])}

DATA QUALITY BY SOURCE:
{json.dumps(data_quality, indent=2)}

INDIVIDUAL ANALYST SUMMARIES:

SEC (Business/Financials):
{sec_summary.get('summary', 'No SEC data analyzed')[:500]}

HMDA (Mortgage Lending):
{hmda_summary.get('summary', 'No HMDA data analyzed')[:500]}

Branch Network:
{branches_summary.get('summary', 'No branch data analyzed')[:500]}

CRA/Small Business Lending:
{cra_summary.get('summary', 'No CRA data analyzed')[:500]}

Consumer Complaints:
{cfpb_summary.get('summary', 'No complaint data analyzed')[:500]}

Recent News:
{news_summary.get('summary', 'No news analyzed')[:500]}

Seeking Alpha (Market Analysis & Analyst Ratings):
{seeking_alpha_summary.get('summary', 'No Seeking Alpha data analyzed')[:500]}

Congressional Stock Trading:
{congressional_summary.get('summary', 'No congressional trading data analyzed')[:500]}

{self._get_ncrc_report_sources()}

SYNTHESIS REQUIREMENTS - ALL DATA SOURCES MUST BE COVERED:
You MUST include information from ALL available data sources. Do not omit any source that has data.

1. **Opening Paragraph**: Institution overview - size, type, geographic footprint, primary business lines. Use corporate context and SEC summary.

2. **Lending Activity Paragraph**: Mortgage lending trends (HMDA) and small business lending (CRA). Note geographic patterns, volume trends, and NCRC-relevant observations.

3. **Consumer Experience Paragraph**: Complaint patterns, response quality, and consumer satisfaction indicators. Highlight any concerning trends.

4. **Branch Network & Community Access**: Network size, expansion/contraction trends, geographic patterns. Note implications for community access to banking.

5. **Market Position & Financial Outlook**:
   - Seeking Alpha analyst ratings and market sentiment (include buy/hold/sell distribution if available)
   - Recent news headlines and themes (must mention key news stories)
   - Congressional stock trading activity (if any members of Congress have traded this stock)
   - Strategic direction indicators and regulatory attention

6. **NCRC Engagement Points**: Synthesize the key talking points and leverage areas for NCRC engagement.

CRITICAL DATA SOURCE CHECKLIST - Include each if data exists:
□ SEC filings - business description, financial metrics
□ HMDA - mortgage lending volumes and trends
□ Branch network - total branches, geographic changes
□ CRA/Small business lending - volumes and patterns
□ CFPB complaints - volumes and top categories
□ News articles - key headlines and themes
□ Seeking Alpha - analyst ratings, market sentiment
□ Congressional trading - any trades by members of Congress

IMPORTANT - FOCUS ON AVAILABLE DATA, NOT GAPS:
- DO NOT lead with or emphasize data limitations or what's "unavailable"
- DO NOT use phrases like "data gaps exist" or "no data available"
- INSTEAD: Present the data that IS available in a balanced, informative way
- If a source has no data, simply skip it - don't mention the absence
- Start each paragraph with substantive findings, not caveats
- The goal is to inform NCRC staff about what we KNOW, not what we don't know

WRITING REQUIREMENTS:
- Write as intelligence briefing for NCRC leadership preparing for meeting with this institution
- Write in objective, third-person style
- NO first-person language (no "I", "we", "my", "our")
- NO personal opinions or subjective statements
- Focus on TRENDS not raw numbers
- Use professional, analytical tone
- Write in PLAIN ENGLISH - avoid jargon
- If referencing NCRC reports, include hypertext links in markdown format: [link text](URL)
- IMPORTANT: After the first full mention of the company name, use the stock ticker (if available) as a shorthand. For example, "Rocket Companies, Inc." becomes "RKT" in subsequent mentions. If no ticker is available, use a sensible abbreviation.
"""

        return self._call_ai(prompt, max_tokens=4000, temperature=0.3)

    def generate_congressional_sentiment(self, ticker: str, congressional_data: Dict[str, Any]) -> str:
        """
        Generate a brief AI summary of congressional trading sentiment (bullish/bearish).

        Args:
            ticker: Stock ticker symbol
            congressional_data: Congressional trading data with trades, buy/sell counts

        Returns:
            2-3 sentence summary with (AI generated) disclaimer
        """
        if not congressional_data or not congressional_data.get('has_data'):
            return ""

        total_purchases = congressional_data.get('total_purchases', 0)
        total_sales = congressional_data.get('total_sales', 0)
        total_trades = congressional_data.get('total_trades', 0)
        unique_politicians = congressional_data.get('unique_politicians', 0)
        recent_trades = congressional_data.get('recent_trades', [])[:10]

        # Prepare trade summary for AI
        trade_summaries = []
        for trade in recent_trades:
            trade_summaries.append({
                'politician': trade.get('politician_name', 'Unknown'),
                'type': trade.get('transaction_type', ''),
                'date': trade.get('transaction_date', ''),
                'amount': trade.get('amount_range', '')
            })

        prompt = f"""Analyze congressional trading activity for {ticker} stock and determine if sentiment is bullish or bearish.

TRADING DATA:
- Total trades: {total_trades}
- Purchases: {total_purchases}
- Sales: {total_sales}
- Unique politicians trading: {unique_politicians}
- Buy/Sell Ratio: {total_purchases}:{total_sales}

RECENT TRADES:
{json.dumps(trade_summaries, indent=2)[:1500]}

Write exactly 2-3 sentences:
1. State whether congressional sentiment appears BULLISH (net buying), BEARISH (net selling), or MIXED
2. Briefly explain why based on the buy/sell ratio and trading patterns
3. Note any caveats (e.g., small sample size, recent timing)

REQUIREMENTS:
- Be objective and factual
- Use specific numbers from the data
- Do NOT add "(AI generated)" - this will be added automatically
- Keep it concise (2-3 sentences maximum)
"""

        # Use Haiku for cost efficiency - this is a simple sentiment task
        summary = self._call_ai(prompt, max_tokens=150, temperature=0, model='claude-3-5-haiku-20241022')

        # Add the AI generated disclaimer
        if summary and summary.strip():
            return f"{summary.strip()} *(AI generated)*"
        return ""

    # ========== Template-Based Executive Summary Assembly ==========

    def generate_executive_summary_assembled(
        self,
        institution_name: str,
        analyst_summaries: Dict[str, Any],
        entity_resolution: Dict[str, Any],
        report_focus: Optional[str] = None
    ) -> str:
        """
        Generate executive summary using template-based assembly.

        Each data source gets its own dedicated paragraph, ensuring all sources
        are represented in the final summary.

        Args:
            institution_name: Institution name
            analyst_summaries: Compiled summaries from DataSourceAnalysts
            entity_resolution: AI entity resolution with corporate context
            report_focus: Optional user-specified focus

        Returns:
            Assembled executive summary with all data sources
        """
        import logging
        logger = logging.getLogger(__name__)

        paragraphs = []
        summaries = analyst_summaries.get('analyst_summaries', {})

        # Get corporate context
        corporate_context = entity_resolution.get('corporate_context', {})
        ticker = corporate_context.get('ticker', '')

        # 1. Opening paragraph - Institution Overview (always included)
        opening = self._generate_opening_paragraph(institution_name, entity_resolution, summaries)
        if opening:
            paragraphs.append(opening)

        # 2. Branch Network paragraph
        branches = summaries.get('branches', {})
        if branches.get('summary') and branches.get('data_quality') != 'none':
            branch_para = self._generate_branch_paragraph(institution_name, branches)
            if branch_para:
                paragraphs.append(branch_para)

        # 3. HMDA Mortgage Lending paragraph
        hmda = summaries.get('hmda', {})
        if hmda.get('summary') and hmda.get('data_quality') != 'none':
            hmda_para = self._generate_hmda_paragraph(institution_name, hmda)
            if hmda_para:
                paragraphs.append(hmda_para)

        # 4. Small Business / CRA Lending paragraph
        cra = summaries.get('cra', {})
        if cra.get('summary') and cra.get('data_quality') != 'none':
            cra_para = self._generate_cra_paragraph(institution_name, cra)
            if cra_para:
                paragraphs.append(cra_para)

        # 5. Consumer Complaints paragraph
        cfpb = summaries.get('cfpb', {})
        if cfpb.get('summary') and cfpb.get('data_quality') != 'none':
            cfpb_para = self._generate_cfpb_paragraph(institution_name, cfpb)
            if cfpb_para:
                paragraphs.append(cfpb_para)

        # 6. News Coverage paragraph
        news = summaries.get('news', {})
        if news.get('summary') and news.get('data_quality') != 'none':
            news_para = self._generate_news_paragraph(institution_name, news)
            if news_para:
                paragraphs.append(news_para)

        # 7. Market Sentiment paragraph (Seeking Alpha) - ALWAYS if data exists
        seeking_alpha = summaries.get('seeking_alpha', {})
        if seeking_alpha.get('summary') and seeking_alpha.get('data_quality') != 'none':
            sa_para = self._generate_seeking_alpha_paragraph(institution_name, ticker, seeking_alpha)
            if sa_para:
                paragraphs.append(sa_para)

        # 8. Congressional Trading paragraph - ALWAYS if data exists
        congressional = summaries.get('congressional', {})
        if congressional.get('summary') and congressional.get('data_quality') != 'none':
            cong_para = self._generate_congressional_paragraph(institution_name, ticker, congressional)
            if cong_para:
                paragraphs.append(cong_para)

        # 9. Closing/NCRC Engagement paragraph
        closing = self._generate_closing_paragraph(institution_name, analyst_summaries)
        if closing:
            paragraphs.append(closing)

        # Assemble final summary
        if paragraphs:
            return "\n\n".join(paragraphs)
        else:
            return "Executive summary data unavailable."

    def _generate_opening_paragraph(
        self,
        institution_name: str,
        entity_resolution: Dict[str, Any],
        summaries: Dict[str, Any]
    ) -> str:
        """Generate opening paragraph with institution overview."""
        corporate = entity_resolution.get('corporate_context', {})
        sec = summaries.get('sec', {})

        prompt = f"""Write a single opening paragraph (3-4 sentences) for an executive summary about {institution_name}.

INSTITUTION CONTEXT:
- Type: {corporate.get('institution_type', 'Financial Institution')}
- Headquarters: {corporate.get('headquarters', 'N/A')}
- Consumer Brands: {', '.join(corporate.get('consumer_brands', [])) or 'N/A'}
- Is Holding Company: {corporate.get('is_holding_company', False)}

SEC SUMMARY (if available):
{sec.get('summary', 'No SEC data')[:500]}

REQUIREMENTS:
- Introduce the institution, its type, and headquarters
- Mention key business lines or brands if known
- Keep it factual and professional
- ONE paragraph only, 3-4 sentences
- Write in third person, objective tone
- Do NOT mention data limitations or what's missing"""

        return self._call_ai(prompt, max_tokens=300, temperature=0.2, model='claude-3-5-haiku-20241022')

    def _generate_branch_paragraph(self, institution_name: str, branches: Dict[str, Any]) -> str:
        """Generate paragraph about branch network."""
        prompt = f"""Write a single paragraph (3-4 sentences) about {institution_name}'s branch network.

BRANCH DATA:
{branches.get('summary', '')[:600]}

Key Findings:
{json.dumps(branches.get('key_findings', []), indent=2)[:400]}

REQUIREMENTS:
- Describe total branch count and geographic footprint
- Note any expansion/contraction trends
- Mention key states or markets
- ONE paragraph only, 3-4 sentences
- Be specific with numbers when available
- Do NOT mention data limitations"""

        return self._call_ai(prompt, max_tokens=250, temperature=0.2, model='claude-3-5-haiku-20241022')

    def _generate_hmda_paragraph(self, institution_name: str, hmda: Dict[str, Any]) -> str:
        """Generate paragraph about mortgage lending."""
        prompt = f"""Write a single paragraph (3-4 sentences) about {institution_name}'s mortgage lending activity.

HMDA DATA:
{hmda.get('summary', '')[:600]}

Key Findings:
{json.dumps(hmda.get('key_findings', []), indent=2)[:400]}

REQUIREMENTS:
- Describe mortgage lending volumes and trends
- Note geographic patterns or top markets
- Mention loan types (purchase, refinance, home equity)
- ONE paragraph only, 3-4 sentences
- Be specific with numbers when available
- Do NOT mention data limitations"""

        return self._call_ai(prompt, max_tokens=250, temperature=0.2, model='claude-3-5-haiku-20241022')

    def _generate_cra_paragraph(self, institution_name: str, cra: Dict[str, Any]) -> str:
        """Generate paragraph about small business lending."""
        prompt = f"""Write a single paragraph (3-4 sentences) about {institution_name}'s small business lending.

CRA/SMALL BUSINESS DATA:
{cra.get('summary', '')[:600]}

Key Findings:
{json.dumps(cra.get('key_findings', []), indent=2)[:400]}

REQUIREMENTS:
- Describe small business lending volumes and trends
- Note loan counts and dollar amounts if available
- Mention geographic patterns
- ONE paragraph only, 3-4 sentences
- Be specific with numbers when available
- Do NOT mention data limitations"""

        return self._call_ai(prompt, max_tokens=250, temperature=0.2, model='claude-3-5-haiku-20241022')

    def _generate_cfpb_paragraph(self, institution_name: str, cfpb: Dict[str, Any]) -> str:
        """Generate paragraph about consumer complaints."""
        prompt = f"""Write a single paragraph (3-4 sentences) about {institution_name}'s consumer complaint profile.

CFPB COMPLAINT DATA:
{cfpb.get('summary', '')[:600]}

Key Findings:
{json.dumps(cfpb.get('key_findings', []), indent=2)[:400]}

REQUIREMENTS:
- Describe complaint volumes and trends
- Note top complaint categories if available
- Mention company response patterns
- ONE paragraph only, 3-4 sentences
- Be specific with numbers when available
- Do NOT mention data limitations"""

        return self._call_ai(prompt, max_tokens=250, temperature=0.2, model='claude-3-5-haiku-20241022')

    def _generate_news_paragraph(self, institution_name: str, news: Dict[str, Any]) -> str:
        """Generate paragraph about recent news coverage."""
        prompt = f"""Write a single paragraph (3-4 sentences) about recent news coverage of {institution_name}.

NEWS DATA:
{news.get('summary', '')[:600]}

Key Findings:
{json.dumps(news.get('key_findings', []), indent=2)[:400]}

REQUIREMENTS:
- Summarize major news themes or stories
- Note any M&A activity, regulatory news, or strategic initiatives
- Mention sentiment if discernible
- ONE paragraph only, 3-4 sentences
- Do NOT mention data limitations"""

        return self._call_ai(prompt, max_tokens=250, temperature=0.2, model='claude-3-5-haiku-20241022')

    def _generate_seeking_alpha_paragraph(self, institution_name: str, ticker: str, seeking_alpha: Dict[str, Any]) -> str:
        """Generate paragraph about Seeking Alpha analyst sentiment."""
        prompt = f"""Write a single paragraph (3-4 sentences) about Wall Street analyst sentiment toward {institution_name} ({ticker or 'ticker N/A'}).

SEEKING ALPHA DATA:
{seeking_alpha.get('summary', '')[:600]}

Key Findings:
{json.dumps(seeking_alpha.get('key_findings', []), indent=2)[:400]}

Metrics:
{json.dumps(seeking_alpha.get('metrics', {}), indent=2)[:300]}

REQUIREMENTS:
- Describe analyst ratings (Buy/Hold/Sell distribution)
- Mention quantitative rating if available
- Note overall market sentiment (bullish/bearish/neutral)
- ONE paragraph only, 3-4 sentences
- Be specific: "X analysts rate Buy, Y rate Hold, Z rate Sell"
- This is REQUIRED content - do not skip it"""

        return self._call_ai(prompt, max_tokens=250, temperature=0.2, model='claude-3-5-haiku-20241022')

    def _generate_congressional_paragraph(self, institution_name: str, ticker: str, congressional: Dict[str, Any]) -> str:
        """Generate paragraph about congressional stock trading."""
        prompt = f"""Write a single paragraph (3-4 sentences) about congressional trading activity in {institution_name} ({ticker or 'ticker N/A'}) stock.

CONGRESSIONAL TRADING DATA:
{congressional.get('summary', '')[:600]}

Key Findings:
{json.dumps(congressional.get('key_findings', []), indent=2)[:400]}

Metrics:
{json.dumps(congressional.get('metrics', {}), indent=2)[:300]}

REQUIREMENTS:
- State whether sentiment is BULLISH (net buying), BEARISH (net selling), or MIXED
- Mention the buy/sell ratio (e.g., "5 purchases vs 2 sales")
- Name specific politicians if available
- ONE paragraph only, 3-4 sentences
- Be specific with numbers
- This is REQUIRED content - do not skip it"""

        return self._call_ai(prompt, max_tokens=250, temperature=0.2, model='claude-3-5-haiku-20241022')

    def _generate_closing_paragraph(self, institution_name: str, analyst_summaries: Dict[str, Any]) -> str:
        """Generate closing paragraph with NCRC engagement points."""
        ncrc_insights = analyst_summaries.get('all_ncrc_insights', [])[:5]
        risk_flags = analyst_summaries.get('all_risk_flags', [])[:3]
        positive_indicators = analyst_summaries.get('all_positive_indicators', [])[:3]

        prompt = f"""Write a closing paragraph (3-4 sentences) summarizing NCRC engagement opportunities with {institution_name}.

NCRC-RELEVANT INSIGHTS:
{json.dumps(ncrc_insights, indent=2)}

RISK FLAGS:
{json.dumps(risk_flags, indent=2)}

POSITIVE INDICATORS:
{json.dumps(positive_indicators, indent=2)}

REQUIREMENTS:
- Summarize the institution's community reinvestment profile
- Note key engagement opportunities or concerns
- Provide a balanced assessment
- ONE paragraph only, 3-4 sentences
- Professional, objective tone
- Do NOT mention data limitations"""

        return self._call_ai(prompt, max_tokens=300, temperature=0.2, model='claude-3-5-haiku-20241022')

