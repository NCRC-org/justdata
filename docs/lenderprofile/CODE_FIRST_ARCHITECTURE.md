# LenderProfile Code-First Architecture

## Overview

This document describes the code-first data processing architecture for LenderProfile, which minimizes AI calls by using code to extract, structure, and quantify all data. AI is only used for narrative synthesis of pre-processed structured data.

## Architecture Principles

1. **Code-First Processing**: All data extraction, calculation, and structuring happens in code (Python)
2. **Minimal AI Usage**: Only 5 strategic AI calls per report for narrative synthesis
3. **Structured Data**: AI receives pre-processed, structured facts, not raw data
4. **Deterministic Calculations**: Financial metrics, trends, and aggregations are calculated programmatically

## Data Processing Flow

### Phase 1: Data Collection (No AI)
- Parallel API calls to fetch raw data
- All external APIs called simultaneously
- Raw data stored in `institution_data` dictionary

### Phase 2: Code-Based Processing (No AI)
- **FinancialDataProcessor**: Extracts trends, calculates metrics, growth rates
- **GLEIFDataProcessor**: Builds corporate hierarchy structure
- **ComplaintDataProcessor**: Aggregates complaints, identifies top issues/products
- **AnalystRatingsProcessor**: Structures analyst ratings and price targets
- **LitigationProcessor**: Filters material cases, categorizes by type
- **NewsProcessor**: Deduplicates and categorizes news articles
- **SECFilingParser**: Extracts sections from 10-K and DEF 14A filings

### Phase 3: Selective SEC Text Extraction (No AI)
- Extract Item 1 (Business Description)
- Extract Item 1A (Risk Factors)
- Extract Item 7 (MD&A)
- Extract Exhibit 21 (Subsidiaries)
- Extract Business Combinations notes
- Extract compensation tables from proxy statements

### Phase 4: Minimal AI Synthesis (5 Calls Total)
1. **Strategy Extraction** - From Item 1 business description
2. **Risk Analysis** - From Item 1A risk factors
3. **MD&A Insights** - From Item 7 management discussion
4. **News Sentiment** - Categorize tone of articles
5. **Executive Summary** - Combine all structured data into prose

### Phase 5: Report Assembly (No AI)
- Combine processed data with AI narratives
- Generate charts and visualizations
- Assemble final report structure

## Data Processors

### FinancialDataProcessor
**Location**: `apps/lenderprofile/processors/data_processors.py`

**Methods**:
- `process_fdic_financials()`: Extracts time series, calculates metrics, growth rates
- `calculate_roa()`: Return on Assets calculation
- `calculate_roe()`: Return on Equity calculation
- `calculate_efficiency_ratio()`: Efficiency ratio calculation

**Output Structure**:
```python
{
    'trends': {
        'assets': [values over time],
        'deposits': [values over time],
        'equity': [values over time],
        'net_income': [values over time],
        'dates': [date strings]
    },
    'metrics': {
        'roa': float,
        'roe': float,
        'assets': float,
        'deposits': float,
        'equity': float,
        'net_income': float,
        'report_date': str
    },
    'growth': {
        'asset_cagr': float,
        'deposit_cagr': float,
        'income_cagr': float,
        'asset_yoy': float
    }
}
```

### GLEIFDataProcessor
**Location**: `apps/lenderprofile/processors/data_processors.py`

**Methods**:
- `build_corporate_structure()`: Builds hierarchy from GLEIF data

**Output Structure**:
```python
{
    'legal_name': str,
    'lei': str,
    'headquarters': {'city': str, 'state': str, 'country': str},
    'direct_parent': {'lei': str, 'name': str},
    'ultimate_parent': {'lei': str, 'name': str},
    'subsidiaries': {
        'direct': [list],
        'ultimate': [list],
        'total_direct': int,
        'total_ultimate': int
    }
}
```

### ComplaintDataProcessor
**Location**: `apps/lenderprofile/processors/data_processors.py`

**Methods**:
- `analyze_complaints()`: Aggregates and analyzes complaint patterns

**Output Structure**:
```python
{
    'summary': {
        'total': int,
        'date_range': {'earliest': str, 'latest': str},
        'timely_response_rate': float,
        'disputed_rate': float
    },
    'top_issues': [{'issue': str, 'count': int, 'pct': float}],
    'top_products': [{'product': str, 'count': int, 'pct': float}],
    'geographic_distribution': {state: count},
    'trend_data': {month: count}
}
```

### AnalystRatingsProcessor
**Location**: `apps/lenderprofile/processors/data_processors.py`

**Methods**:
- `process_analyst_ratings()`: Structures analyst opinion data

**Output Structure**:
```python
{
    'distribution': {'buy': int, 'hold': int, 'sell': int, 'total': int},
    'quant_rating': str,
    'author_rating': str,
    'price_target': {
        'current': float,
        'average': float,
        'high': float,
        'low': float
    },
    'earnings': {...}
}
```

### LitigationProcessor
**Location**: `apps/lenderprofile/processors/data_processors.py`

**Methods**:
- `process_litigation()`: Filters and categorizes material cases

**Output Structure**:
```python
{
    'summary': {
        'total_cases': int,
        'active_cases': int,
        'closed_cases': int
    },
    'by_type': {type: [cases]},
    'by_court': {court: [cases]},
    'recent_cases': [list],
    'significant_settlements': [list]
}
```

### NewsProcessor
**Location**: `apps/lenderprofile/processors/data_processors.py`

**Methods**:
- `process_news()`: Deduplicates and categorizes news articles
- `deduplicate_articles()`: Removes duplicates by URL
- `filter_by_keywords()`: Filters articles by keyword categories

**Output Structure**:
```python
{
    'summary': {
        'total': int,
        'date_range': {'earliest': str, 'latest': str},
        'sources': [list]
    },
    'categorized': {
        'executive': [articles],
        'strategy': [articles],
        'regulatory': [articles],
        'financial': [articles],
        'controversy': [articles]
    },
    'recent': [articles]
}
```

## SEC Filing Parser

### SECFilingParser
**Location**: `apps/lenderprofile/processors/sec_parser.py`

**Methods**:
- `parse_10k()`: Extracts key sections from 10-K filing
- `extract_section()`: Extracts text between two markers
- `extract_exhibit21()`: Extracts subsidiary list
- `extract_business_combinations()`: Extracts acquisition information
- `parse_proxy_statement()`: Extracts compensation and governance data
- `extract_compensation_table()`: Extracts executive compensation
- `extract_director_table()`: Extracts board composition

**Output Structure**:
```python
{
    'sections': {
        'item1_business': str,  # Limited to 50k chars
        'item1a_risks': str,     # Limited to 50k chars
        'item7_mda': str         # Limited to 50k chars
    },
    'subsidiaries': [{'name': str, 'state': str, 'ownership': str}],
    'business_combinations': [{'year': str, 'target': str, 'details': str}],
    'metadata': {
        'filing_date': str,
        'fiscal_year_end': str
    }
}
```

## AI Summarizer (5 Strategic Calls)

### LenderProfileAnalyzer
**Location**: `apps/lenderprofile/processors/ai_summarizer.py`

**AI Calls** (Only 5 per report):

1. **`generate_strategy_analysis()`**
   - Input: Item 1 business description (from SEC parser)
   - Output: Strategic priorities, performance drivers, expansion plans
   - Token usage: ~8K input → 500 output

2. **`generate_risk_analysis()`**
   - Input: Item 1A risk factors (from SEC parser)
   - Output: Top 5 risk categories with descriptions
   - Token usage: ~12K input → 800 output

3. **`generate_mda_insights()`**
   - Input: Item 7 MD&A section (from SEC parser)
   - Output: Strategic priorities, challenges, forward-looking statements
   - Token usage: ~15K input → 800 output

4. **`generate_news_sentiment()`**
   - Input: Categorized news articles (from NewsProcessor)
   - Output: Sentiment analysis and key themes
   - Token usage: ~3K input → 400 output

5. **`generate_executive_summary()`**
   - Input: All structured data (corporate, financial, strategy, risks, governance)
   - Output: 2-3 paragraph executive summary
   - Token usage: ~5K input → 600 output

**Total Token Usage**: ~43K input, ~3.1K output per report

## Integration Points

### Data Collector Integration
**File**: `apps/lenderprofile/processors/data_collector.py`

After collecting raw data, the collector now:
1. Processes financial data using `FinancialDataProcessor`
2. Processes GLEIF data using `GLEIFDataProcessor`
3. Processes complaints using `ComplaintDataProcessor`
4. Processes analyst ratings using `AnalystRatingsProcessor`
5. Processes litigation using `LitigationProcessor`
6. Processes news using `NewsProcessor`
7. Parses SEC filings using `SECFilingParser`

All processed data is stored in `institution_data` with `_processed` or `_parsed` suffixes.

### Section Builder Integration
**File**: `apps/lenderprofile/report_builder/section_builders.py`

Section builders now:
1. Use processed data from data collectors
2. Build narratives from structured data (code-based)
3. Only call AI for specific narrative synthesis tasks
4. Generate charts and visualizations from processed data

### Report Builder Integration
**File**: `apps/lenderprofile/report_builder/report_builder.py`

Report builder orchestrates:
1. Data collection (with processing)
2. Section building (using processed data)
3. AI synthesis (5 strategic calls)
4. Report assembly

## Benefits

1. **Cost Reduction**: ~90% reduction in AI token usage
2. **Deterministic Results**: Financial calculations are consistent and verifiable
3. **Faster Processing**: Code-based processing is faster than AI calls
4. **Better Structure**: Data is pre-structured before AI synthesis
5. **Maintainability**: Code is easier to maintain and update than AI prompts

## Migration Notes

- Old `_calculate_financial_trends()` method removed
- Old AI calls for data extraction removed
- New processors handle all data structuring
- AI summarizer reduced to 5 strategic calls only

