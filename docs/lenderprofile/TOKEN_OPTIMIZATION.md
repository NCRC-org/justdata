# Token Optimization Strategy

## Overview
The LenderProfile report uses a **client-side rendering approach** to minimize AI token usage. JavaScript handles all data visualization and formatting, while AI is reserved only for data interpretation and narrative generation.

## Architecture

### Client-Side (JavaScript) - No AI Tokens
- **Data Visualization**: All charts, graphs, tables rendered with Chart.js, D3.js
- **Data Formatting**: Numbers, dates, percentages formatted in JavaScript
- **HTML Generation**: All HTML structure generated client-side
- **Static Text**: Section headers, labels, descriptions in JavaScript templates

### Server-Side (Python + AI) - Minimal AI Tokens
- **Data Collection**: Raw data from APIs (no formatting)
- **Data Interpretation**: AI analyzes patterns, trends, insights
- **Narrative Generation**: AI writes summaries, key findings, advocacy intelligence
- **Structured Data**: Return raw JSON, not formatted HTML

## AI Usage Guidelines

### ✅ Use AI For:
1. **Executive Summary** - Narrative interpretation of key data points
2. **Key Findings** - Insight extraction from multiple data sources
3. **Section Summaries** - Interpretation of regulatory, CRA, strategic data
4. **Advocacy Intelligence** - Synthesis and recommendations
5. **Trend Analysis** - Explaining what trends mean, not calculating them

### ❌ Don't Use AI For:
1. **Data Formatting** - Numbers, dates, percentages (JavaScript)
2. **Table Generation** - HTML tables from data (JavaScript)
3. **Chart Data** - Preparing chart datasets (JavaScript)
4. **Static Text** - Headers, labels, descriptions (JavaScript templates)
5. **Data Aggregation** - Counting, summing, averaging (Python, no AI)

## Implementation

### Report Renderer (`report-renderer.js`)
- `ReportRenderer` class handles all client-side rendering
- Methods for each section: `renderExecutiveSummary()`, `renderFinancialProfile()`, etc.
- Chart rendering: `renderFinancialChart()`, `renderComplaintsTrendChart()`, etc.
- Utility functions: `formatNumber()`, `formatDate()`, `escapeHtml()`, `formatMarkdown()`

### Section Builders (`section_builders.py`)
- Return **raw structured data** (dicts, lists, numbers)
- Only call AI for interpretation/narrative
- Pass minimal data to AI (key insights, not full datasets)
- Example: Pass top 3 strengths/weaknesses to AI, not entire examiner findings

### Data Flow
```
1. Data Collection (Python) → Raw JSON
2. Section Builders (Python) → Structured Data + AI Summaries
3. Report Builder (Python) → Complete JSON Report
4. Template (HTML) → Pass JSON to JavaScript
5. Report Renderer (JavaScript) → Generate HTML, Charts, Visualizations
```

## Token Savings

### Before Optimization:
- AI generated full HTML for each section
- AI formatted all numbers, dates, percentages
- AI created table structures
- Estimated: ~50,000-100,000 tokens per report

### After Optimization:
- AI only generates narrative summaries
- JavaScript handles all formatting and visualization
- Estimated: ~5,000-15,000 tokens per report
- **Savings: 70-85% reduction in AI token usage**

## Example: Consumer Complaints Section

### Server-Side (Python):
```python
# Return raw data - no formatting
return {
    'total': 29593,
    'trends': {
        'recent_trend': 'increasing',
        'by_year': {'2021': 500, '2022': 600, '2023': 700},
        'year_over_year_changes': {...}
    },
    'main_topics': [
        {'issue': 'Managing an account', 'count': 6561, 'percentage': 36.7},
        ...
    ],
    'ai_summary': '...'  # Only AI-generated narrative
}
```

### Client-Side (JavaScript):
```javascript
// All formatting and visualization in JavaScript
renderConsumerComplaints(complaints) {
    // Format numbers: formatNumber(complaints.total)
    // Generate HTML tables
    // Render Chart.js charts
    // Format percentages
    // Display AI summary (already formatted)
}
```

## Best Practices

1. **Keep AI prompts focused** - Only send key insights, not full datasets
2. **Use JavaScript for all formatting** - Numbers, dates, percentages, currency
3. **Generate HTML client-side** - Templates in JavaScript, not AI
4. **Cache AI summaries** - If data hasn't changed, reuse AI output
5. **Batch AI calls** - Generate multiple summaries in one prompt when possible

## Future Optimizations

1. **Template Caching** - Cache AI summaries for similar institutions
2. **Incremental Updates** - Only regenerate changed sections
3. **Prompt Optimization** - Further reduce prompt size while maintaining quality
4. **Client-Side AI** - Consider using client-side models for simple formatting tasks




