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
python justdata/apps/branchsight/run.py    # Port 8080 - FDIC branch analysis (BranchSight)
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
pytest tests/apps/test_branchsight/ -v  # Test BranchSight app
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
│   ├── branchsight/         # BranchSight - FDIC branch analysis (fully functional)
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

Required (set in `.env` for local dev, or Cloud Run environment for production):
- `CLAUDE_API_KEY` or `ANTHROPIC_API_KEY` - Claude AI API key
- `GCP_PROJECT_ID` - Google Cloud project (default: hdma1-242116)
- `GOOGLE_APPLICATION_CREDENTIALS_JSON` - BigQuery credentials as JSON string
- `CENSUS_API_KEY` - US Census API key
- **Firebase Auth (Google sign-in):** `FIREBASE_CREDENTIALS_JSON` (service account JSON string) or `FIREBASE_CREDENTIALS` (path to JSON file). Get from Firebase Console → Project settings → Service accounts → Generate new private key. If unset, backend returns 503 and login fails with "Firebase credentials not set."

Optional:
- `OPENAI_API_KEY` - OpenAI API key (fallback)
- `DEBUG` / `FLASK_DEBUG` - Debug mode
- `SECRET_KEY` - Flask session secret
- `PORT` - Server port (defaults vary by app)

### Firebase Auth (Google sign-in)
Google sign-in requires the app’s domain to be **authorized** in Firebase:
1. [Firebase Console](https://console.firebase.google.com) → project **justdata-ncrc**
2. **Authentication** → **Settings** → **Authorized domains**
3. **Add domain** with the **hostname only** (no `https://` or port), e.g.:
   - `localhost` (for http://localhost:8000)
   - `127.0.0.1` (for http://127.0.0.1:8000)
   - `justdata.org` (for production)
If the domain is missing, users see "Domain not authorized" or "The requested action is invalid."

## Data Sources

- **FDIC Summary of Deposits (SOD)** - Bank branch data (BigQuery: `fdic_data`)
- **HMDA** - Mortgage lending data (BigQuery)
- **Section 1071** - Small business lending data
- **Census ACS** - Demographic data via Census API
- **SEC EDGAR** - Company filings
- **GLEIF** - Legal Entity Identifiers

## ElectWatch Data Architecture

ElectWatch tracks congressional financial activity. Data is stored in BigQuery (`justdata-ncrc.electwatch`).

### External APIs
| API | Data | Update Frequency |
|-----|------|------------------|
| FEC OpenFEC | PAC/individual contributions | Weekly |
| FMP/Quiver | STOCK Act trade disclosures | Weekly |
| Congress.gov | Officials, committees | Weekly |
| Finnhub | Stock quotes | Weekly |
| Claude AI | Pattern insights | Weekly |

### BigQuery Tables
```
electwatch/
├── officials               # Congress members with stats
├── official_trades         # Individual stock trades
├── official_pac_contributions
├── official_individual_contributions
├── firms                   # Companies/stocks
├── industries              # Sector aggregations
├── committees              # Congressional committees
├── insights                # AI-generated patterns
├── trend_snapshots         # Historical time-series
├── summaries               # AI summaries
└── metadata                # Update status
```

### Weekly Update
```bash
# Run the weekly data update manually (fetches APIs, writes to BigQuery)
python -c "from dotenv import load_dotenv; load_dotenv(); from justdata.apps.electwatch.weekly_update import WeeklyDataUpdate; WeeklyDataUpdate().run()"
```

### Automated Scheduling (Cloud Run Job)
The weekly update runs automatically via Cloud Scheduler + Cloud Run Job:
- **Schedule:** Every Sunday at 5:00 AM EST
- **Job Name:** `electwatch-weekly-update`
- **Trigger:** `electwatch-weekly-trigger`

```bash
# Deploy the scheduled job
./scripts/deploy-electwatch-job.sh

# Run manually
gcloud run jobs execute electwatch-weekly-update --region=us-east1 --project=justdata-ncrc

# View logs
gcloud logging read 'resource.type=cloud_run_job AND resource.labels.job_name=electwatch-weekly-update' --limit=100
```

### Required Credentials
- `ELECTWATCH_CREDENTIALS_JSON` - BigQuery service account with write access
- `FEC_API_KEY` - FEC OpenFEC API key
- `CONGRESS_GOV_API_KEY` - Congress.gov API key
- `CLAUDE_API_KEY` - For AI insights generation

### Required Secrets (in Secret Manager for Cloud Run Job)
- `electwatch-credentials` - BigQuery credentials JSON
- `fec-api-key` - FEC API key
- `congress-gov-api-key` - Congress.gov API key  
- `claude-api-key` - Claude API key

## Deployment

### Google Cloud Run

**Environments:**
- **Production:** `justdata` service at https://justdata-892833260112.us-east1.run.app
- **Test:** `justdata-test` service at https://justdata-test-892833260112.us-east1.run.app

**Deploy commands:**
```bash
# Build and deploy to test
bash scripts/deploy-cloudrun.sh
gcloud run deploy justdata-test --image us-east1-docker.pkg.dev/hdma1-242116/justdata-repo/justdata:latest --region us-east1

# Deploy to production (after testing)
gcloud run deploy justdata --image us-east1-docker.pkg.dev/hdma1-242116/justdata-repo/justdata:latest --region us-east1
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
| BranchSight | 8080 | FDIC branch analysis |
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
- **Branch Report** = BranchSight

**Note:** BranchSight was formerly called BranchSeeker. The codebase has been fully renamed to BranchSight.

## Terminal Note

Use **cmd.exe** or **Git Bash** instead of PowerShell for git commands on Windows to avoid parsing errors.
