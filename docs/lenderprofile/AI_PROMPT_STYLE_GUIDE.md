# LenderProfile AI Prompt Style Guide

This document captures the NCRC style guide and narrative prompt patterns used in LendSight for consistent AI-generated content in LenderProfile reports.

## Core Writing Requirements

### Style
- **Write in objective, third-person style**
- **NO first-person language** (no "I", "we", "my", "our")
- **NO personal opinions or subjective statements**
- **NO speculation about strategic implications or underlying causes**
- **Present ONLY factual patterns and observable data trends**
- **Use professional, analytical tone**

### Language
- **Write in PLAIN ENGLISH** - avoid jargon and technical terms
- **If you must use an acronym, explain it in plain English the first time**
- **Use simple, clear language accessible to non-technical readers**
- **Explain what the data means, not just what it says**
- **Focus on explaining HOW TO READ tables and WHAT TRENDS are visible**

### Data Presentation
- **DO NOT create a "wall of numbers"** - cite at most 2-3 specific percentages per paragraph
- **The reader can see all the numbers in the table** - your job is to explain trends and patterns
- **ONLY cite the MOST COMPELLING numbers**: biggest changes, largest gaps, or patterns that differ most from national trends
- **DO NOT list every single statistic** - focus on the most significant patterns
- **DO NOT recite all the data** - focus on explaining what the patterns mean

## NCRC Report Sources

### Reference Format
When referencing NCRC research reports, include hypertext links in markdown format:
```
[link text](URL)
```

Example:
```
As noted in NCRC's mortgage market analysis ([Part 1: Introduction to Mortgage Market Trends](https://ncrc.org/mortgage-market-report-series-part-1-introduction-to-mortgage-market-trends/)), non-bank lenders now dominate the market.
```

### Available NCRC Reports (for LenderProfile context)
- NCRC Mortgage Market Report Series (Parts 1-5)
- CRA performance research
- Fair lending analysis
- Community reinvestment studies

**Rule:** Only reference these sources if the information is directly relevant and supports your analysis.

## Prompt Structure Template

### Standard Prompt Structure

```python
prompt = f"""
Generate [section description]:

[Context Data]:
- Institution: {institution_name}
- Data: {json.dumps(data, indent=2)[:2000]}

{self._get_ncrc_report_sources()}  # If applicable

IMPORTANT DEFINITIONS:
- [Term 1]: [Definition in plain English]
- [Term 2]: [Definition in plain English]

ANALYSIS REQUIREMENTS:
1. FIRST PARAGRAPH: [Specific requirement]
2. SECOND PARAGRAPH: [Specific requirement]

WRITING REQUIREMENTS:
- Write in objective, third-person style
- NO first-person language (no "I", "we", "my", "our")
- NO personal opinions or subjective statements
- NO speculation about strategic implications or underlying causes
- Present ONLY factual patterns and observable data trends
- Use professional, analytical tone
- Write in PLAIN ENGLISH - avoid jargon
- AT LEAST 2 PARAGRAPHS (minimum requirement)
- If referencing NCRC reports, include hypertext links in markdown format: [link text](URL)
"""
```

## AI Configuration

### Temperature
- **Use `temperature=0.3`** for factual analysis (low temperature = more deterministic, factual)

### Max Tokens
- **Intro paragraphs:** 300 tokens
- **Key findings:** 400 tokens
- **Section discussions:** 600-1000 tokens
- **Comprehensive analysis:** 1200-3000 tokens

## Key Findings Format

### Structure
Each finding must be formatted as:
```
• **Title:** Sentence describing the finding
```

### Requirements
- Title should be a short, descriptive phrase (3-8 words)
- Sentence after colon should be ONE COMPLETE SENTENCE
- Include specific numbers/percentages when available
- Format as bullet points starting with "•"
- Focus on most significant and compelling statistics

### Example
```
• **Total Originations:** Mortgage originations in Hillsborough County, Florida declined by 38.5% from 25,510 loans in 2020 to 15,701 loans in 2024, representing a net decrease of 9,809 loans over the five-year period.
```

## Section-Specific Guidelines

### Executive Summary
- Single paragraph defining scope, years, geography
- Plain English explanation of filters
- No speculation, only factual statements

### Key Findings
- 3-5 findings maximum
- Bold titles with colons
- One complete sentence per finding
- Most compelling statistics only

### Analysis Sections
- **Minimum 2 paragraphs** per section
- First paragraph: Explain how to read the data and identify patterns
- Second paragraph: Explain trends over time
- Reference NCRC reports when patterns align with or differ from national trends

### Table Discussions
- Explain HOW TO READ the table
- Identify MOST COMPELLING patterns (not all patterns)
- Cite at most 1-2 specific numbers per paragraph
- Focus on what trends mean, not just what they are

## LenderProfile-Specific Considerations

### Report Focus Field
When user provides a report focus (optional 250-character field), incorporate it into prompts:
```
USER REPORT FOCUS: {report_focus}

The user has requested that this report focus on: {report_focus}
While maintaining objectivity and factual analysis, ensure that sections relevant to this focus receive appropriate attention in the analysis.
```

### Institution Context
- Always include institution name, type, location
- Reference identifiers (FDIC cert, RSSD, LEI) when relevant
- Note asset size and market position

### Regulatory Context
- Reference enforcement actions factually
- Note CRA ratings and exam dates
- Discuss litigation history objectively
- Avoid speculation about causes or implications

## Implementation Notes

### AI Provider
- Use `shared/analysis/ai_provider.py` base class
- Extend `AIAnalyzer` class
- Use `_call_ai()` method with proper temperature and max_tokens

### Data Preparation
- Use `convert_numpy_types()` for JSON serialization
- Limit data in prompts to 2000-3000 characters
- Include only relevant context

### Error Handling
- Gracefully handle AI API failures
- Return empty strings or fallback text
- Log errors for debugging

## Example Prompt for LenderProfile Executive Summary

```python
def generate_executive_summary(self, data: Dict[str, Any], report_focus: Optional[str] = None) -> str:
    """Generate executive summary for lender intelligence report."""
    institution = data.get('institution', {})
    identifiers = data.get('identifiers', {})
    
    focus_context = ""
    if report_focus:
        focus_context = f"""
    
    USER REPORT FOCUS: {report_focus}
    The user has requested that this report focus on: {report_focus}
    While maintaining objectivity, ensure relevant sections address this focus appropriately.
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
    """
    
    return self._call_ai(prompt, max_tokens=600, temperature=0.3)
```

## Key Principles Summary

1. **Objectivity First:** No opinions, only facts
2. **Plain English:** Accessible to non-experts
3. **Selective Citation:** Only most compelling numbers
4. **Pattern Focus:** Explain what data means, not just what it says
5. **NCRC Alignment:** Reference NCRC research when relevant
6. **Professional Tone:** Analytical, not advocacy-oriented
7. **Minimum Requirements:** Enforce paragraph/section minimums
8. **User Focus:** Incorporate optional report focus when provided

