# JustData

A financial data analysis platform built for [NCRC](https://ncrc.org) (National Community Reinvestment Coalition). JustData provides AI-powered insights across banking, mortgage, small business, and congressional finance domains using data from FDIC, HMDA, SEC, FEC, and other regulatory sources.

**Production:** [justdata.org](https://justdata.org)

---

## Applications

JustData runs as a unified platform with 10 specialized applications:

| App | Domain | Data Sources | Status |
|-----|--------|-------------|--------|
| **BranchSight** | FDIC branch analysis | Summary of Deposits, Census ACS | Fully functional |
| **LendSight** | Mortgage lending analysis | HMDA, Census ACS | Fully functional |
| **BizSight** | Small business lending | Section 1071, Census ACS | Fully functional |
| **MergerMeter** | Bank merger analysis | FDIC, HMDA, SOD | Fully functional |
| **LenderProfile** | Lender corporate analysis | SEC EDGAR, GLEIF, FDIC | Fully functional |
| **DataExplorer** | Data exploration tool | HMDA, Census, FDIC | Fully functional |
| **ElectWatch** | Congressional financial tracking | FEC, Congress.gov, STOCK Act | Fully functional |
| **BranchMapper** | Branch network mapping | FDIC SOD, Mapbox | Fully functional |
| **MemberView** | Member dashboard | Internal data | In development |
| **LoanTrends** | Loan trend analysis | HMDA | In development |

All apps are accessible from the unified landing page at `http://localhost:8000` when running locally.

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/NCRC-org/justdata.git
cd justdata
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp env.example .env
# Edit .env with your API keys and credentials
```

Required environment variables:

- `CLAUDE_API_KEY` or `ANTHROPIC_API_KEY` -- Claude AI API key
- `GCP_PROJECT_ID` -- Google Cloud project ID
- `GOOGLE_APPLICATION_CREDENTIALS_JSON` -- BigQuery credentials (JSON string)
- `SECRET_KEY` -- Flask session secret

See [env.example](env.example) for the full list.

### 3. Run

```bash
python run_justdata.py
```

Open http://localhost:8000. All applications are available from the landing page.

To run individual apps:

```bash
python justdata/apps/branchsight/run.py   # Port 8080
python justdata/apps/lendsight/run.py      # Port 8082
python justdata/apps/bizsight/run.py       # Port 8081
python justdata/apps/mergermeter/run.py    # Port 8083
python justdata/apps/lenderprofile/run.py  # Port 8086
python justdata/apps/dataexplorer/run.py   # Port 8085
```

---

## Project Structure

```
justdata/
├── justdata/
│   ├── apps/                   # Flask applications
│   │   ├── branchsight/        # FDIC branch analysis
│   │   ├── lendsight/          # HMDA mortgage analysis
│   │   ├── bizsight/           # Small business lending
│   │   ├── mergermeter/        # Bank merger analysis
│   │   ├── lenderprofile/      # Lender corporate analysis
│   │   ├── dataexplorer/       # Data exploration
│   │   ├── electwatch/         # Congressional tracking
│   │   ├── branchmapper/       # Branch network mapping
│   │   ├── memberview/         # Member dashboard
│   │   └── loantrends/         # Loan trend analysis
│   ├── shared/                 # Shared modules
│   │   ├── analysis/           # AI integration (Claude, OpenAI)
│   │   ├── utils/              # BigQuery, env config, progress tracking
│   │   ├── reporting/          # Report generation (Excel, PDF, PowerPoint)
│   │   ├── services/           # Business logic services
│   │   ├── web/                # Web framework utilities
│   │   └── pdf/                # PDF report engine
│   └── core/                   # Core infrastructure and config
├── tests/                      # Test suite (pytest)
├── docs/                       # Internal documentation
├── scripts/                    # Deployment and utility scripts
├── .github/workflows/          # CI/CD pipelines
├── run_justdata.py             # Unified platform entry point
└── requirements.txt            # Python dependencies
```

### App Structure Pattern

Each app in `justdata/apps/` follows a consistent layout:

- `app.py` -- Flask application with routes
- `run.py` -- Entry point (exposes `application` for Gunicorn)
- `analysis.py` -- Data analysis and AI narrative generation
- `core.py` -- Core business logic
- `config.py` -- App-specific configuration
- `templates/` -- Jinja2 HTML templates
- `static/` -- CSS, JS, images

---

## API Endpoints

All apps use a consistent routing pattern:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main page with analysis form |
| `/analyze` | POST | Start new analysis |
| `/progress/<job_id>` | GET | Real-time progress updates (SSE) |
| `/report` | GET | View interactive web report |
| `/report-data` | GET | Report data as JSON |
| `/download` | GET | Download reports (Excel, CSV, JSON, ZIP) |
| `/health` | GET | Health check |

---

## Technology

- **Backend:** Python 3.11+, Flask, pandas
- **AI:** Anthropic Claude (primary), OpenAI GPT-4 (fallback)
- **Data:** Google BigQuery, Census API, FDIC API, HMDA, FEC
- **Frontend:** HTML5, CSS3, JavaScript, Server-Sent Events
- **PDF Reports:** ReportLab, Playwright
- **Infrastructure:** Docker, Google Cloud Run, GitHub Actions
- **Maps:** Mapbox GL JS

---

## Development

### Run tests

```bash
pytest tests/ -v --cov=justdata
pytest tests/ -m "not slow"           # Skip slow tests
```

### Lint and format

```bash
black justdata/ tests/
isort justdata/ tests/
flake8 justdata/ tests/
```

### Deploy

Deployments are managed via GitHub Actions. Pushing to `main` triggers a production deploy; pushing to `staging` triggers a test deploy.

For manual deploys:

```bash
bash scripts/deploy-cloudrun.sh
```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for full deployment documentation.

---

## Documentation

Detailed documentation lives in the [docs/](docs/) directory:

- [DEPLOYMENT.md](docs/DEPLOYMENT.md) -- Deployment guide
- [CACHE_IMPLEMENTATION.md](docs/CACHE_IMPLEMENTATION.md) -- BigQuery caching system
- [DEPENDENCIES.md](DEPENDENCIES.md) -- Dependencies and data source reference
- [docs/dataexplorer/](docs/dataexplorer/) -- DataExplorer implementation notes
- [docs/lenderprofile/](docs/lenderprofile/) -- LenderProfile implementation notes

Each app also has its own `README.md` with app-specific documentation.

---

## Contributing

### Branch Flow

```
jad_test / jay_test  -->  test  -->  staging  -->  main
         (1 approval)   (1 approval)  (2 approvals)
```

1. Create a feature branch from `test` (e.g., `jad_test`)
2. Open a PR to `test` -- requires 1 approval
3. PR from `test` to `staging` -- requires 1 approval; auto-deploys to test environment
4. PR from `staging` to `main` -- requires 2 approvals; auto-deploys to production

### Code Standards

- Format with [Black](https://github.com/psf/black) and [isort](https://pycqa.github.io/isort/)
- Type hints for function signatures
- Consistent error handling

---

## Team

- **Jad Edlebi** -- Lead Developer (jedlebi@ncrc.org)
- **Jason Richardson** -- Project Lead (jrichardson@ncrc.org)

---

## License

MIT License -- see [LICENSE](LICENSE) for details.
