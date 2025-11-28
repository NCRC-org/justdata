# BizSight - Small Business Lending Analysis Application

## Overview

BizSight is a web-based application for analyzing small business lending data at the county level. It provides comprehensive reports with interactive maps, tables, and AI-generated insights.

## Quick Start Guide

### 1. Prerequisites

- **Python 3.8+** (3.9+ recommended)
- **pip** (Python package manager)
- **Google Cloud Account** with BigQuery access
- **AI API Key** (Claude or OpenAI)

### 2. Installation

#### Windows:
```bash
# Run the installation script
install.bat
```

#### macOS/Linux:
```bash
# Make script executable and run
chmod +x install.sh
./install.sh
```

#### Manual Installation:
```bash
# Install Python dependencies
pip install -r apps/bizsight/requirements.txt

# Install Playwright browser (required for PDF export)
playwright install chromium
```

### 3. Configuration

1. **Copy the environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` file** and add your credentials:
   - `CLAUDE_API_KEY` or `OPENAI_API_KEY`
   - `GCP_PROJECT_ID` (if different from default)
   - `SECRET_KEY` (generate a secure random key)

3. **Place BigQuery credentials:**
   - Download your service account JSON key from Google Cloud Console
   - Place it in `credentials/bigquery_service_account.json`

4. **Generate Benchmark Data (if not included):**
   - If benchmark files (state and national) are not in `apps/data/`, generate them:
   ```bash
   python apps/bizsight/generate_benchmarks.py
   ```
   - This will create 52 state benchmark files plus a national benchmark file
   - The application can also query BigQuery directly if benchmarks are missing

### 4. Run the Application

#### Windows:
```bash
run_bizsight.bat
```

#### macOS/Linux:
```bash
./run_bizsight.sh
```

#### Manual:
```bash
cd "#JustData_Repo"
python -m apps.bizsight.app
```

### 5. Access the Application

Open your browser to: `http://localhost:8081`

## Required Credentials

### 1. BigQuery Service Account

**Location:** `credentials/bigquery_service_account.json`

**Required Permissions:**
- BigQuery Data Viewer
- BigQuery Job User

**How to Obtain:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **IAM & Admin > Service Accounts**
3. Create or select a service account
4. Click **Keys > Add Key > Create new key > JSON**
5. Download the JSON file
6. Place it in the `credentials/` directory

### 2. AI API Key

Choose ONE of the following:

#### Option A: Claude (Anthropic) - Recommended
- **Environment Variable:** `CLAUDE_API_KEY`
- **Get from:** [Anthropic Console](https://console.anthropic.com/)
- **Set in:** `.env` file

#### Option B: OpenAI
- **Environment Variable:** `OPENAI_API_KEY`
- **Get from:** [OpenAI Platform](https://platform.openai.com/)
- **Set in:** `.env` file

## Project Structure

```
bizsight_deployment/
├── apps/
│   └── bizsight/
│       ├── __init__.py
│       ├── app.py              # Main Flask application
│       ├── core.py              # Analysis logic
│       ├── config.py            # Configuration
│       ├── report_builder.py    # Report generation
│       ├── ai_analysis.py       # AI narrative generation
│       ├── excel_export.py      # Excel export functionality
│       ├── templates/           # HTML templates
│       ├── static/              # CSS, JS, images
│       ├── utils/               # Utility modules
│       └── requirements.txt     # Python dependencies
├── credentials/                 # Place BigQuery JSON here
├── .env.example                 # Environment template
├── README.md                    # This file
├── DEPLOYMENT_GUIDE.md          # Detailed deployment guide
├── install.bat                  # Windows installation script
├── install.sh                   # Unix installation script
├── run_bizsight.bat             # Windows run script
└── run_bizsight.sh              # Unix run script
```

## Configuration Options

All configuration is done via environment variables or the `.env` file:

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `AI_PROVIDER` | AI provider: 'claude' or 'openai' | 'claude' | Yes |
| `CLAUDE_API_KEY` | Claude API key | - | If using Claude |
| `OPENAI_API_KEY` | OpenAI API key | - | If using OpenAI |
| `GCP_PROJECT_ID` | Google Cloud Project ID | 'hdma1-242116' | Yes |
| `SECRET_KEY` | Flask secret key | Auto-generated | Recommended |
| `DEBUG` | Debug mode | False | No |
| `PORT` | Server port | 8081 | No |
| `HOST` | Server host | '0.0.0.0' | No |

## Features

- **Interactive Maps:** Visualize lending data by census tract
- **Comprehensive Tables:** County, state, and national comparisons
- **AI-Generated Insights:** Automated narrative analysis
- **Excel Export:** Download data in Excel format with multiple sheets
- **PDF Export:** Generate PDF reports with maps
- **Market Concentration Analysis:** HHI calculations and trends

## Troubleshooting

### Import Errors
- Ensure all dependencies are installed: `pip install -r apps/bizsight/requirements.txt`
- Check that Python version is 3.8 or higher

### BigQuery Connection Issues
- Verify credentials file is in `credentials/bigquery_service_account.json`
- Check that service account has required permissions
- Verify `GCP_PROJECT_ID` is correct

### AI API Errors
- Verify API key is set correctly in `.env` file
- Check API key has sufficient credits/quota
- Ensure `AI_PROVIDER` matches the API key type

### PDF Export Not Working
- Ensure Playwright is installed: `playwright install chromium`
- Check that Chromium browser is available

## Support

For detailed deployment instructions, see `DEPLOYMENT_GUIDE.md`.

For issues or questions, contact the development team.
