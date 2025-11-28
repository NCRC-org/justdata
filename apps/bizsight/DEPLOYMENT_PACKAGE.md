# BizSight Deployment Package Guide

This document provides complete instructions for packaging and deploying the BizSight application.

## Table of Contents
1. [Package Contents](#package-contents)
2. [Prerequisites](#prerequisites)
3. [Required Credentials & API Keys](#required-credentials--api-keys)
4. [Installation Steps](#installation-steps)
5. [Configuration](#configuration)
6. [Running the Application](#running-the-application)
7. [Troubleshooting](#troubleshooting)

---

## Package Contents

The deployment package should include:

### Core Application Files
```
bizsight/
├── __init__.py
├── app.py                    # Main Flask application
├── core.py                   # Core analysis logic
├── config.py                 # Configuration settings
├── data_utils.py             # Data utilities
├── report_builder.py         # Report generation
├── ai_analysis.py            # AI narrative generation
├── excel_export.py           # Excel export functionality
├── requirements.txt          # Python dependencies
├── templates/
│   ├── analysis_template.html
│   └── report_template.html
├── utils/
│   ├── __init__.py
│   ├── bigquery_client.py
│   ├── progress_tracker.py
│   ├── ai_provider.py
│   └── tract_boundaries.py
└── data/
    └── reports/              # Output directory (empty initially)
```

### Required Shared Modules
```
core/
└── config/
    └── app_config.py         # Shared configuration (if needed)
```

### Configuration Files
- `.env.example` - Template for environment variables
- `DEPLOYMENT_PACKAGE.md` - This file
- `INSTALLATION.md` - Installation instructions
- `package_bizsight.py` - Packaging script

---

## Prerequisites

### System Requirements
- **Python**: 3.8 or higher (3.9+ recommended)
- **Operating System**: Windows 10+, macOS 10.14+, or Linux
- **RAM**: Minimum 4GB (8GB+ recommended)
- **Disk Space**: 500MB for application + data storage

### Required Software
1. **Python 3.8+** with pip
2. **Google Cloud SDK** (for BigQuery access)
3. **Playwright** (for PDF generation - installed via pip)

### Python Packages
All dependencies are listed in `requirements.txt` and will be installed automatically.

---

## Required Credentials & API Keys

### 1. Google Cloud / BigQuery Credentials

**Required**: BigQuery service account JSON key file

**Location**: Place in `#JustData_Repo/credentials/bigquery_service_account.json`

**How to Obtain**:
1. Go to Google Cloud Console
2. Navigate to IAM & Admin > Service Accounts
3. Create or select a service account
4. Create a JSON key and download it
5. Ensure the service account has BigQuery Data Viewer and Job User roles

**Environment Variable Alternative**:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/bigquery_service_account.json"
```

### 2. AI Provider API Key

**Choose ONE of the following:**

#### Option A: Claude (Anthropic) - Recommended
- **Environment Variable**: `CLAUDE_API_KEY` or `ANTHROPIC_API_KEY` or `CLAUDE_AI_API_KEY`
- **How to Obtain**: 
  1. Sign up at https://console.anthropic.com/
  2. Navigate to API Keys
  3. Create a new API key
  4. Copy the key

#### Option B: OpenAI
- **Environment Variable**: `OPENAI_API_KEY`
- **How to Obtain**:
  1. Sign up at https://platform.openai.com/
  2. Navigate to API Keys
  3. Create a new secret key
  4. Copy the key

**Configuration**:
Set `AI_PROVIDER=claude` (default) or `AI_PROVIDER=openai` in your `.env` file.

### 3. Flask Secret Key (Optional)

**Environment Variable**: `SECRET_KEY`

**Default**: Auto-generated (change in production!)

**Generate a secure key**:
```python
import secrets
print(secrets.token_hex(32))
```

### 4. Google Cloud Project ID

**Environment Variable**: `GCP_PROJECT_ID`

**Default**: `hdma1-242116`

**Change if using a different project**: Set in `.env` file

---

## Installation Steps

### Step 1: Extract Package

Extract the deployment package to your desired location:
```bash
unzip bizsight_deployment.zip
cd bizsight_deployment
```

### Step 2: Set Up Python Environment (Recommended)

Create a virtual environment:
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install --upgrade pip
pip install -r apps/bizsight/requirements.txt
```

**Note**: Playwright requires additional setup:
```bash
playwright install chromium
```

### Step 4: Set Up Credentials

1. **BigQuery Credentials**:
   - Place your `bigquery_service_account.json` in `#JustData_Repo/credentials/`
   - OR set `GOOGLE_APPLICATION_CREDENTIALS` environment variable

2. **Create `.env` file**:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add:
   ```env
   # AI Provider (claude or openai)
   AI_PROVIDER=claude
   
   # Claude API Key (if using Claude)
   CLAUDE_API_KEY=your_claude_api_key_here
   
   # OR OpenAI API Key (if using OpenAI)
   # OPENAI_API_KEY=your_openai_api_key_here
   
   # Google Cloud Project
   GCP_PROJECT_ID=hdma1-242116
   
   # Flask Configuration
   SECRET_KEY=your_secret_key_here
   DEBUG=False
   PORT=8081
   HOST=0.0.0.0
   ```

### Step 5: Verify Installation

Run the configuration validator:
```bash
cd "#JustData_Repo"
python -c "from apps.bizsight.config import BizSightConfig; BizSightConfig.validate(); print('✓ Configuration valid')"
```

---

## Configuration

### Environment Variables

All configuration can be set via environment variables or `.env` file:

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `AI_PROVIDER` | AI provider: 'claude' or 'openai' | 'claude' | Yes |
| `CLAUDE_API_KEY` | Claude API key | None | If using Claude |
| `OPENAI_API_KEY` | OpenAI API key | None | If using OpenAI |
| `GCP_PROJECT_ID` | Google Cloud Project ID | 'hdma1-242116' | Yes |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to BigQuery credentials JSON | `credentials/bigquery_service_account.json` | Yes |
| `SECRET_KEY` | Flask secret key | Auto-generated | No |
| `DEBUG` | Enable debug mode | 'False' | No |
| `PORT` | Server port | 8081 | No |
| `HOST` | Server host | '0.0.0.0' | No |
| `CLAUDE_MODEL` | Claude model name | 'claude-sonnet-4-20250514' | No |
| `GPT_MODEL` | OpenAI model name | 'gpt-4' | No |

### Directory Structure

The application expects this directory structure:
```
#JustData_Repo/
├── apps/
│   └── bizsight/
│       ├── app.py
│       ├── core.py
│       ├── config.py
│       ├── templates/
│       ├── utils/
│       └── data/
│           └── reports/
├── core/
│   └── config/
│       └── app_config.py
└── credentials/
    └── bigquery_service_account.json
```

---

## Running the Application

### Development Mode

```bash
cd "#JustData_Repo"
python -m apps.bizsight.app
```

The server will start on `http://localhost:8081` (or the port specified in `PORT`).

### Production Mode

**Using Gunicorn (Linux/macOS)**:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8081 "apps.bizsight.app:app"
```

**Using Waitress (Windows)**:
```bash
pip install waitress
waitress-serve --host=0.0.0.0 --port=8081 "apps.bizsight.app:app"
```

### Running as a Service

**Windows (using NSSM)**:
```bash
nssm install BizSight "C:\Python39\python.exe" "-m" "apps.bizsight.app"
nssm set BizSight AppDirectory "C:\path\to\#JustData_Repo"
nssm start BizSight
```

**Linux (using systemd)**:
Create `/etc/systemd/system/bizsight.service`:
```ini
[Unit]
Description=BizSight Application
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/#JustData_Repo
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python -m apps.bizsight.app
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable bizsight
sudo systemctl start bizsight
```

---

## Troubleshooting

### Common Issues

#### 1. Import Errors
**Error**: `ModuleNotFoundError: No module named 'apps'`

**Solution**: Ensure you're running from the `#JustData_Repo` directory:
```bash
cd "#JustData_Repo"
python -m apps.bizsight.app
```

#### 2. BigQuery Authentication Error
**Error**: `google.auth.exceptions.DefaultCredentialsError`

**Solution**: 
- Verify `bigquery_service_account.json` exists in `credentials/` directory
- OR set `GOOGLE_APPLICATION_CREDENTIALS` environment variable
- Verify the service account has proper permissions

#### 3. Missing AI API Key
**Error**: `CLAUDE_API_KEY not set`

**Solution**: 
- Add `CLAUDE_API_KEY=your_key` to `.env` file
- OR set environment variable: `export CLAUDE_API_KEY=your_key`

#### 4. Playwright Browser Not Found
**Error**: `playwright._impl._api_types.Error: Executable doesn't exist`

**Solution**:
```bash
playwright install chromium
```

#### 5. Port Already in Use
**Error**: `Address already in use`

**Solution**: 
- Change `PORT` in `.env` file
- OR kill the process using the port:
  ```bash
  # Windows
  netstat -ano | findstr :8081
  taskkill /PID <PID> /F
  
  # Linux/macOS
  lsof -ti:8081 | xargs kill
  ```

#### 6. Template Not Found
**Error**: `jinja2.exceptions.TemplateNotFound`

**Solution**: Verify `templates/` directory exists in `apps/bizsight/`

### Getting Help

1. Check application logs in the console output
2. Enable debug mode: Set `DEBUG=True` in `.env`
3. Verify all dependencies: `pip list`
4. Check Python version: `python --version` (should be 3.8+)

---

## Additional Notes

### Data Storage
- Reports are saved to `apps/bizsight/data/reports/`
- Ensure this directory has write permissions

### Performance
- First analysis may be slow (downloading Playwright browsers, etc.)
- Subsequent analyses will be faster
- BigQuery queries may take 10-30 seconds depending on county size

### Security
- **Never commit** `.env` file or credentials to version control
- Change `SECRET_KEY` in production
- Use environment variables for sensitive data in production
- Restrict access to BigQuery service account credentials

### Updates
To update the application:
1. Backup your `.env` file and credentials
2. Extract new package
3. Restore `.env` and credentials
4. Reinstall dependencies: `pip install -r apps/bizsight/requirements.txt --upgrade`

---

## Support

For issues or questions, contact the development team or refer to the project documentation.

