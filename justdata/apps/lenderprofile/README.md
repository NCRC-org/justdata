# LenderProfile

Comprehensive lender intelligence reporting platform for NCRC leadership.

## Overview

LenderProfile generates comprehensive intelligence reports on lenders combining:
- Corporate structure and legal entity information
- Financial performance and trends
- Regulatory compliance and enforcement history
- Strategic positioning and executive profiles
- Branch network and market presence
- CRA performance evaluations
- Litigation history
- Recent developments and news coverage

## Features

- **Multi-API Integration**: Combines data from FDIC, SEC, GLEIF, CourtListener, NewsAPI, TheOrg, and more
- **AI Summarization**: Uses Claude API to generate executive summaries and insights
- **Comprehensive Reports**: 13-section reports covering all aspects of lender intelligence
- **Caching**: Redis-backed caching with in-memory fallback for performance
- **Rate Limiting**: Intelligent rate limiting for APIs with daily limits (e.g., NewsAPI)

## Installation

### Requirements

```bash
pip install -r requirements.txt
```

### Environment Variables

Add to your `.env` file or environment:

```bash
# Required API Keys
COURTLISTENER_API_KEY=faf1fd4f57c7d694d2080dc6bc1f03650e429656
NEWSAPI_API_KEY=d5bbbca939c9442dae6c4ff8f1e7a716
THEORG_API_KEY=206bd062350b4bb6aac28ac140590d58

# Optional API Keys
REGULATIONS_GOV_API_KEY=your-key-here
FRED_API_KEY=your-key-here

# Already configured (via unified_env)
CENSUS_API_KEY=your-census-key
CLAUDE_API_KEY=your-claude-key
```

## Running Locally

```bash
python apps/lenderprofile/run.py
```

Then open: http://localhost:8086

## API Endpoints

- `GET /` - Search interface
- `POST /api/search` - Search for institution by name
- `POST /api/generate-report` - Generate comprehensive intelligence report
- `GET /health` - Health check

## Architecture

- **services/**: API client services for external APIs
- **processors/**: Data processing and analysis modules
- **report_builder/**: Report generation and section builders
- **cache/**: Caching layer (Redis + in-memory fallback)

## Development Status

Phase 1: Core Infrastructure ✅
- App structure created
- Flask app configured
- Identifier resolution implemented
- Basic search interface
- Core API clients (FDIC, GLEIF, SEC, etc.)
- Keyed API clients (CourtListener, NewsAPI, TheOrg)
- Caching layer

Next Steps:
- Implement report generation
- Add section builders
- Integrate AI summarization
- Add PDF export
- Update landing page

