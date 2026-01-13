# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

JustData is a financial data analysis platform built for NCRC (National Community Reinvestment Coalition). It provides AI-powered insights across banking, mortgage, and small business domains using data from FDIC, HMDA, and other regulatory sources.

## Build and Run Commands

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Run Unified Platform
```bash
python run_justdata.py  # All apps at localhost:8000
```

### Run Individual Apps
```bash
python justdata/apps/branchseeker/run.py    # Port 8080 - FDIC branch analysis
python justdata/apps/lendsight/run.py       # Port 8082 - HMDA mortgage analysis
python justdata/apps/lenderprofile/run.py   # Port 8086 - Lender corporate analysis
python justdata/apps/dataexplorer/run.py    # Port 8085 - Data exploration
python justdata/apps/bizsight/run.py        # Port 8081 - Small business lending
python justdata/apps/mergermeter/run.py     # Port 8083 - Bank merger analysis
```

### Run with Gunicorn (Production)
```bash
gunicorn --bind 0.0.0.0:8082 justdata.apps.lendsight.run:application
```

### Run Tests
```bash
pytest tests/ -v --cov=justdata
pytest tests/ -m "not slow"              # Skip slow tests
pytest tests/apps/test_branchseeker/ -v  # Test specific app
```

### Linting and Formatting
```bash
black justdata/ tests/
isort justdata/ tests/
flake8 justdata/ tests/
mypy justdata/
```

### Makefile Commands
```bash
make help          # Show all available commands
make install       # Install dependencies
make test          # Run tests with coverage
make lint          # Run all linters
make format        # Format code with black/isort
make docker-up     # Start all services
make deploy-all    # Deploy all services to Cloud Run
```

## Architecture

### Directory Structure
```
justdata/
├── apps/                    # Flask applications
│   ├── branchseeker/        # FDIC branch analysis (fully functional)
│   ├── lendsight/           # HMDA mortgage analysis
│   ├── lenderprofile/       # Lender corporate structure analysis
│   ├── dataexplorer/        # Data exploration tool
│   ├── bizsight/            # Small business lending
│   ├── mergermeter/         # Bank merger analysis
│   ├── electwatch/          # Congressional financial tracking
│   ├── branchmapper/        # Branch network mapping
│   ├── loantrends/          # Loan trend analysis
│   └── memberview/          # Member dashboard
├── shared/                  # Shared modules used by all apps
│   ├── analysis/            # AI analysis (Claude/OpenAI)
│   ├── utils/               # Utilities (BigQuery, env, progress)
│   ├── reporting/           # Report generation (Excel, PDF, PowerPoint)
│   ├── services/            # Business logic services
│   └── web/                 # Web framework utilities
└── core/                    # Core infrastructure
```

### App Structure Pattern
Each app in `justdata/apps/` follows a consistent structure:
- `app.py` - Flask application with routes
- `run.py` - Entry point (exposes `application` for gunicorn)
- `analysis.py` - Data analysis and AI narrative generation
- `core.py` - Core business logic
- `config.py` - App-specific configuration
- `templates/` - Jinja2 HTML templates
- `static/` - CSS, JS, images
- `requirements.txt` - App-specific dependencies (optional)

### Shared Module Organization
- `shared/analysis/ai_provider.py` - AI integration with `ask_ai()` function
- `shared/utils/bigquery_client.py` - BigQuery data access with credential management
- `shared/utils/unified_env.py` - Centralized environment configuration
- `shared/utils/progress_tracker.py` - Server-Sent Events for real-time progress
- `shared/reporting/` - Report generation (Excel via openpyxl, PDF via reportlab/Playwright)

## Key Patterns

### AI Integration
```python
from justdata.shared.analysis.ai_provider import ask_ai
response = ask_ai("prompt", ai_provider="claude")  # or "openai"
```

### Environment Config
```python
from justdata.shared.utils.unified_env import get_unified_config
config = get_unified_config()  # Unified config for all apps
```

### BigQuery Access
```python
from justdata.shared.utils.bigquery_client import get_bigquery_client
client = get_bigquery_client()
```

### Progress Tracking
Apps use Server-Sent Events (SSE) via `/progress/<job_id>` endpoints for real-time updates.

### API Route Pattern
All apps use consistent routing:
- `GET /` - Main page with analysis form
- `POST /analyze` - Start new analysis
- `GET /progress/<job_id>` - Real-time progress updates (SSE)
- `GET /report` - View interactive web report
- `GET /report-data` - Get report data (JSON)
- `GET /download` - Download reports (Excel, CSV, JSON, ZIP)
- `GET /health` - Health check

## Environment Variables

Required (set in `.env` for local dev, or Render/Cloud Run environment for production):
- `CLAUDE_API_KEY` or `ANTHROPIC_API_KEY` - Claude AI API key
- `GCP_PROJECT_ID` - Google Cloud project (default: hdma1-242116)
- `GOOGLE_APPLICATION_CREDENTIALS_JSON` - BigQuery credentials as JSON string
- `CENSUS_API_KEY` - US Census API key

Optional:
- `OPENAI_API_KEY` - OpenAI API key (fallback)
- `DEBUG` / `FLASK_DEBUG` - Debug mode
- `SECRET_KEY` - Flask session secret
- `PORT` - Server port (defaults vary by app)

## Data Sources

- **FDIC Summary of Deposits (SOD)** - Bank branch data (BigQuery: `fdic_data`)
- **HMDA** - Mortgage lending data (BigQuery)
- **Section 1071** - Small business lending data
- **Census ACS** - Demographic data via Census API
- **SEC EDGAR** - Company filings
- **GLEIF** - Legal Entity Identifiers

## Deployment

### Google Cloud Run
```bash
make deploy-all                    # Deploy all services
make deploy-branchseeker           # Deploy single service
bash scripts/deploy-all.sh bizsight lendsight  # Deploy specific services
```

### Render
Apps deploy via `render.yaml`. Each app uses gunicorn with PYTHONPATH set:
```bash
PYTHONPATH=/opt/render/project/src gunicorn --bind 0.0.0.0:$PORT justdata.apps.<appname>.run:application
```

### Docker
```bash
docker-compose up                  # Local development
docker build -f Dockerfile.app .   # Build single app image
```

## Application Ports

| App | Port | Description |
|-----|------|-------------|
| Unified Platform | 8000 | All apps via run_justdata.py |
| BranchSeeker | 8080 | FDIC branch analysis |
| BizSight | 8081 | Small business lending |
| LendSight | 8082 | HMDA mortgage analysis |
| MergerMeter | 8083 | Bank merger analysis |
| ElectWatch | 8084 | Congressional tracking |
| DataExplorer | 8085 | Data exploration |
| LenderProfile | 8086 | Lender corporate analysis |

## App Name Aliases

When using speech-to-text, these shorthand names may be used:
- **Mortgage Report** = LendSight
- **Business Report** = BizSight
- **Branch Report** = BranchSeeker/BranchSight

## Terminal Note

Use **cmd.exe** or **Git Bash** instead of PowerShell for git commands on Windows to avoid parsing errors.
