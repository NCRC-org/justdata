# AI Prompts for SEC, Branch Footprint, and Seeking Alpha Analysis

Following LendSight style guide and NCRC narrative patterns.

## Prompt 1: SEC 10-K Filings Analysis

### Purpose
Analyze the last 5 years of 10-K filings to extract key business information, financial trends, strategic initiatives, and risk factors.

### Prompt Template

```python
def generate_sec_10k_analysis(self, institution_name: str, sec_data: Dict[str, Any], report_focus: Optional[str] = None) -> str:
    """
    Generate analysis of SEC 10-K filings for the institution.
    
    Args:
        institution_name: Institution name
        sec_data: SEC data dictionary with 10-K content
        report_focus: Optional user-specified focus
    """
    focus_context = ""
    if report_focus:
        focus_context = f"""
    
    USER REPORT FOCUS: {report_focus}
    The user has requested that this report focus on: {report_focus}
    While maintaining objectivity, ensure SEC analysis addresses this focus appropriately.
    """
    
    # Extract 10-K content (limit to avoid token limits)
    ten_k_content = sec_data.get('filings', {}).get('10k_content', [])
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
    {chr(10).join(content_summary)}
    
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
```

---

## Prompt 2: Branch Network Footprint Analysis

### Purpose
Analyze branch network changes over time, including growth, shrinkage, geographic reallocation, and market presence patterns.

### Prompt Template

```python
def generate_branch_footprint_analysis(self, institution_name: str, branch_analysis: Dict[str, Any], report_focus: Optional[str] = None) -> str:
    """
    Generate analysis of branch network footprint and changes over time.
    
    Args:
        institution_name: Institution name
        branch_analysis: Branch network analysis results
        report_focus: Optional user-specified focus
    """
    focus_context = ""
    if report_focus:
        focus_context = f"""
    
    USER REPORT FOCUS: {report_focus}
    The user has requested that this report focus on: {report_focus}
    While maintaining objectivity, ensure branch analysis addresses this focus appropriately.
    """
    
    # Prepare branch data summary
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
```

---

## Prompt 3: Seeking Alpha Financial Analysis

### Purpose
Analyze financial performance, analyst ratings, and market positioning based on Seeking Alpha data.

### Prompt Template

```python
def generate_seeking_alpha_analysis(self, institution_name: str, seeking_alpha_data: Dict[str, Any], report_focus: Optional[str] = None) -> str:
    """
    Generate analysis of Seeking Alpha financial data and analyst ratings.
    
    Args:
        institution_name: Institution name
        seeking_alpha_data: Seeking Alpha data dictionary
        report_focus: Optional user-specified focus
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
    {chr(10).join(financial_summary)[:2000]}
    
    ANALYST RATINGS:
    {json.dumps(ratings_summary, indent=2)[:1000]}
    
    RECENT NEWS/ARTICLES:
    {chr(10).join(story_summary)[:1000]}
    
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
```

---

## Prompt 4: Combined Financial Overview (SEC + Seeking Alpha)

### Purpose
Synthesize information from both SEC filings and Seeking Alpha to provide a comprehensive financial overview.

### Prompt Template

```python
def generate_combined_financial_overview(self, institution_name: str, sec_data: Dict[str, Any], seeking_alpha_data: Dict[str, Any], report_focus: Optional[str] = None) -> str:
    """
    Generate combined financial overview using both SEC and Seeking Alpha data.
    
    Args:
        institution_name: Institution name
        sec_data: SEC data dictionary
        seeking_alpha_data: Seeking Alpha data dictionary
        report_focus: Optional user-specified focus
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
```

---

## Implementation Notes

### Data Preparation
- Limit 10-K content to first 5,000 characters per filing (to stay within token limits)
- Include only most recent 5 filings
- Summarize financial data to key sections
- Extract key ratings metrics

### Token Limits
- SEC 10-K Analysis: 1200 tokens
- Branch Footprint: 1000 tokens
- Seeking Alpha: 1000 tokens
- Combined Overview: 1000 tokens

### Temperature
- All prompts use `temperature=0.3` for factual, deterministic analysis

### Error Handling
- If data is missing, return empty string or fallback message
- Log errors for debugging
- Gracefully handle partial data

### Integration
These prompts should be integrated into `LenderProfileAnalyzer` class in `apps/lenderprofile/processors/ai_summarizer.py`:

```python
# Add methods to LenderProfileAnalyzer class:
- generate_sec_10k_analysis()
- generate_branch_footprint_analysis()
- generate_seeking_alpha_analysis()
- generate_combined_financial_overview()
```

