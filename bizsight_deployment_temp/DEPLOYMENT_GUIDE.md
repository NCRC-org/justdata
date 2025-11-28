# BizSight Deployment Guide

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Deployment Options](#deployment-options)
5. [Production Considerations](#production-considerations)
6. [Troubleshooting](#troubleshooting)

## System Requirements

### Minimum Requirements
- **Python:** 3.8 or higher (3.9+ recommended)
- **RAM:** 4GB minimum (8GB+ recommended)
- **Disk Space:** 500MB for application + data storage
- **OS:** Windows 10+, macOS 10.14+, or Linux

### Required Software
1. **Python 3.8+** with pip
2. **Google Cloud SDK** (for BigQuery access)
3. **Playwright** (installed via pip for PDF generation)

## Installation

### Step 1: Extract Package

Extract the deployment package to your desired location:
```bash
unzip bizsight_deployment_YYYYMMDD_HHMMSS.zip
cd bizsight_deployment
```

### Step 2: Create Virtual Environment (Recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

#### Using Installation Scripts:

**Windows:**
```bash
install.bat
```

**macOS/Linux:**
```bash
chmod +x install.sh
./install.sh
```

#### Manual Installation:
```bash
pip install --upgrade pip
pip install -r apps/bizsight/requirements.txt
playwright install chromium
```

### Step 4: Set Up Credentials

1. **BigQuery Credentials:**
   - Download service account JSON from Google Cloud Console
   - Place in `credentials/bigquery_service_account.json`

2. **Environment Configuration:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and add your API keys and configuration.

## Configuration

### Environment Variables

Create a `.env` file in the package root:

```env
# AI Provider
AI_PROVIDER=claude
CLAUDE_API_KEY=your_key_here

# Google Cloud
GCP_PROJECT_ID=hdma1-242116

# Flask
SECRET_KEY=your_secret_key_here
DEBUG=False
PORT=8081
HOST=0.0.0.0
```

### Generate Secure Secret Key

```python
import secrets
print(secrets.token_hex(32))
```

## Deployment Options

### Option 1: Development Server

```bash
python -m apps.bizsight.app
```

Access at: `http://localhost:8081`

### Option 2: Production with Gunicorn

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8081 "apps.bizsight.app:app"
```

### Option 3: Docker (if Dockerfile provided)

```bash
docker build -t bizsight .
docker run -p 8081:8081 bizsight
```

### Option 4: Cloud Platform Deployment

#### Google Cloud Run:
```bash
gcloud run deploy bizsight --source .
```

#### AWS Elastic Beanstalk:
- Create `Procfile`: `web: gunicorn -w 4 -b 0.0.0.0:8081 "apps.bizsight.app:app"`
- Deploy via EB CLI

#### Heroku:
- Create `Procfile`: `web: gunicorn -w 4 -b 0.0.0.0:$PORT "apps.bizsight.app:app"`
- Set environment variables in Heroku dashboard

## Production Considerations

### Security

1. **Change Secret Key:** Never use default secret key in production
2. **HTTPS:** Use reverse proxy (nginx/Apache) with SSL certificate
3. **Environment Variables:** Never commit `.env` file to version control
4. **API Keys:** Rotate API keys regularly
5. **Credentials:** Store BigQuery credentials securely

### Performance

1. **Caching:** Enable caching for static files
2. **Database Connection Pooling:** Configure BigQuery connection pooling
3. **Load Balancing:** Use multiple workers with Gunicorn
4. **CDN:** Serve static files via CDN

### Monitoring

1. **Logging:** Configure application logging
2. **Error Tracking:** Set up error tracking (Sentry, etc.)
3. **Health Checks:** Implement health check endpoints
4. **Metrics:** Monitor API usage and performance

## Troubleshooting

### Common Issues

#### Import Errors
- **Solution:** Ensure all dependencies installed and Python path correct

#### BigQuery Connection Failed
- **Solution:** Verify credentials file path and permissions

#### AI API Errors
- **Solution:** Check API key validity and quota

#### PDF Export Fails
- **Solution:** Ensure Playwright Chromium is installed

### Logs

Check application logs for detailed error messages:
- Console output (development)
- Log files (production)
- Cloud platform logs (if deployed)

## Support

For additional support, refer to:
- Application logs
- Google Cloud Console
- AI provider documentation
- Development team
