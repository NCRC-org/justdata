# MergerMeter Deployment Package

This document describes the complete deployment package for MergerMeter, including all files, dependencies, and configuration needed for web server deployment.

## 📦 Package Contents

### Core Application Files
```
mergermeter/
├── apps/
│   └── mergermeter/
│       ├── __init__.py
│       ├── app.py                    # Main Flask application
│       ├── config.py                 # Configuration settings
│       ├── query_builders.py         # BigQuery query construction
│       ├── excel_generator.py        # Excel report generation
│       ├── hhi_calculator.py         # HHI concentration calculations
│       ├── branch_assessment_area_generator.py  # Branch and AA analysis
│       ├── county_mapper.py          # County/GEOID mapping utilities
│       ├── statistical_analysis.py  # Statistical analysis utilities
│       ├── version.py                # Version information
│       ├── templates/                # HTML templates
│       │   ├── analysis_template.html
│       │   └── report_template.html
│       ├── static/                   # Static assets (CSS, JS)
│       │   ├── css/
│       │   └── js/
│       └── output/                   # Generated reports (created automatically)
│
├── shared/                           # Shared dependencies
│   ├── __init__.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── bigquery_client.py        # BigQuery client wrapper
│   │   └── progress_tracker.py      # Progress tracking utilities
│   ├── web/
│   │   ├── __init__.py
│   │   ├── app_factory.py            # Flask app factory
│   │   └── static/                   # Shared static files
│   │       ├── css/
│   │       ├── js/
│   │       └── img/
│   └── analysis/
│       ├── __init__.py
│       └── ai_provider.py            # AI utilities (optional)
│
├── run_mergermeter.py                # Application entry point
├── requirements.txt                  # Python dependencies
├── .env.example                      # Environment variables template
├── setup_config.py                   # Interactive configuration setup
├── check_config.py                   # Configuration validation
└── DEPLOYMENT_README.md              # This file
```

### Documentation Files
- `README.md` - Application overview and usage
- `ASSESSMENT_AREA_FORMAT.md` - Assessment area format documentation
- `BIGQUERY_DATASETS.md` - BigQuery dataset information
- `HHI_CALCULATION_GUIDE.md` - HHI calculation documentation
- `DEPLOYMENT_README.md` - Deployment instructions (this file)

## 🔧 Required Dependencies

### Python Version
- **Python 3.8 or higher** (Python 3.9+ recommended)

### Python Packages (see requirements.txt)
- Flask >= 2.3.0 (web framework)
- pandas >= 1.5.0 (data processing)
- numpy >= 1.21.0 (numerical operations)
- google-cloud-bigquery >= 3.0.0 (BigQuery access)
- openpyxl >= 3.0.0 (Excel file generation)
- python-dotenv >= 1.0.0 (environment variables)
- anthropic >= 0.7.0 (optional - for AI features)

### External Services
- **Google Cloud Platform (GCP)** account with:
  - BigQuery API enabled
  - Service account with BigQuery access
  - Credentials JSON file downloaded

### Optional Services
- **Anthropic Claude API** (for AI-powered insights - optional)
- **OpenAI API** (alternative AI provider - optional)

## 🔐 Configuration Requirements

### Required Environment Variables

Create a `.env` file in the root directory (copy from `.env.example`):

```bash
# REQUIRED - BigQuery Configuration
GCP_PROJECT_ID=your-gcp-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/gcp-credentials.json

# OPTIONAL - Server Configuration
PORT=8083
SECRET_KEY=your-secret-key-here

# OPTIONAL - AI Features
AI_PROVIDER=claude
CLAUDE_API_KEY=your-claude-api-key
OPENAI_API_KEY=your-openai-api-key

# OPTIONAL - Advanced Configuration
DEBUG=False
LOG_LEVEL=INFO
MAX_CONTENT_LENGTH=10485760
```

### GCP Credentials Setup

1. **Create GCP Project** (if not already created)
   - Go to https://console.cloud.google.com
   - Create a new project or select existing one
   - Note the Project ID

2. **Enable BigQuery API**
   - Navigate to APIs & Services > Library
   - Search for "BigQuery API"
   - Click "Enable"

3. **Create Service Account**
   - Go to IAM & Admin > Service Accounts
   - Click "Create Service Account"
   - Name: `mergermeter-service`
   - Grant role: "BigQuery Data Viewer" and "BigQuery Job User"
   - Click "Done"

4. **Download Credentials**
   - Click on the service account
   - Go to "Keys" tab
   - Click "Add Key" > "Create new key"
   - Select JSON format
   - Download the JSON file
   - Save it securely (e.g., `credentials/gcp-credentials.json`)

5. **Set Environment Variable**
   - Update `.env` file with full path to credentials file:
   - `GOOGLE_APPLICATION_CREDENTIALS=/full/path/to/credentials.json`

## 🚀 Quick Start (Development)

1. **Extract Package**
   ```bash
   unzip mergermeter-deployment.zip
   cd mergermeter
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**
   ```bash
   # Option 1: Interactive setup
   python setup_config.py
   
   # Option 2: Manual setup
   cp .env.example .env
   # Edit .env with your credentials
   ```

4. **Verify Configuration**
   ```bash
   python check_config.py
   ```

5. **Start Application**
   ```bash
   python run_mergermeter.py
   ```

6. **Access Application**
   - Open browser: http://127.0.0.1:8083

## 🌐 Production Deployment

### Option 1: Using Gunicorn (Recommended)

1. **Install Gunicorn**
   ```bash
   pip install gunicorn
   ```

2. **Create Gunicorn Config** (`gunicorn_config.py`):
   ```python
   bind = "0.0.0.0:8083"
   workers = 4
   worker_class = "sync"
   timeout = 120
   keepalive = 5
   max_requests = 1000
   max_requests_jitter = 50
   ```

3. **Start with Gunicorn**
   ```bash
   gunicorn -c gunicorn_config.py "apps.mergermeter.app:app"
   ```

### Option 2: Using uWSGI

1. **Install uWSGI**
   ```bash
   pip install uwsgi
   ```

2. **Create uWSGI Config** (`uwsgi.ini`):
   ```ini
   [uwsgi]
   module = apps.mergermeter.app:app
   http = 0.0.0.0:8083
   processes = 4
   threads = 2
   master = true
   vacuum = true
   die-on-term = true
   ```

3. **Start with uWSGI**
   ```bash
   uwsgi --ini uwsgi.ini
   ```

### Option 3: Using Systemd Service

1. **Create Service File** (`/etc/systemd/system/mergermeter.service`):
   ```ini
   [Unit]
   Description=MergerMeter Web Application
   After=network.target

   [Service]
   User=www-data
   Group=www-data
   WorkingDirectory=/path/to/mergermeter
   Environment="PATH=/path/to/venv/bin"
   ExecStart=/path/to/venv/bin/gunicorn -c gunicorn_config.py "apps.mergermeter.app:app"
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

2. **Enable and Start Service**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable mergermeter
   sudo systemctl start mergermeter
   sudo systemctl status mergermeter
   ```

### Option 4: Using Docker

1. **Create Dockerfile**:
   ```dockerfile
   FROM python:3.9-slim

   WORKDIR /app

   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   COPY . .

   EXPOSE 8083

   CMD ["gunicorn", "-c", "gunicorn_config.py", "apps.mergermeter.app:app"]
   ```

2. **Create docker-compose.yml**:
   ```yaml
   version: '3.8'
   services:
     mergermeter:
       build: .
       ports:
         - "8083:8083"
       env_file:
         - .env
       volumes:
         - ./output:/app/apps/mergermeter/output
         - ./credentials:/app/credentials
   ```

3. **Build and Run**
   ```bash
   docker-compose up -d
   ```

### Option 5: Using Nginx Reverse Proxy

1. **Install Nginx**
   ```bash
   sudo apt-get install nginx
   ```

2. **Create Nginx Config** (`/etc/nginx/sites-available/mergermeter`):
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://127.0.0.1:8083;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

3. **Enable Site**
   ```bash
   sudo ln -s /etc/nginx/sites-available/mergermeter /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl reload nginx
   ```

## 📋 Pre-Deployment Checklist

- [ ] Python 3.8+ installed
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file created and configured
- [ ] GCP credentials JSON file downloaded and path set
- [ ] GCP Project ID configured
- [ ] BigQuery API enabled in GCP
- [ ] Service account has BigQuery permissions
- [ ] `output/` directory exists and is writable
- [ ] Configuration validated (`python check_config.py`)
- [ ] Application starts successfully (`python run_mergermeter.py`)
- [ ] Can access web interface at http://127.0.0.1:8083
- [ ] Test analysis completes successfully

## 🔍 Troubleshooting

### "Cannot connect to BigQuery"
- Verify `GOOGLE_APPLICATION_CREDENTIALS` path is correct
- Check that credentials file exists and is readable
- Verify `GCP_PROJECT_ID` is set correctly
- Ensure service account has BigQuery permissions
- Check GCP project billing is enabled

### "Module not found" errors
- Ensure you're in the correct directory
- Verify `shared/` directory exists
- Check that all dependencies are installed
- Verify Python path includes project root

### "Port already in use"
- Change PORT in `.env` file
- Or stop the process using the port:
  ```bash
  # Find process
  lsof -i :8083
  # Kill process
  kill <PID>
  ```

### "Permission denied" errors
- Ensure `output/` directory is writable:
  ```bash
  chmod 755 apps/mergermeter/output
  ```

### Production deployment issues
- Check application logs
- Verify environment variables are set
- Ensure firewall allows port 8083
- Check reverse proxy configuration (if using)

## 📞 Support

For deployment issues:
1. Check this deployment guide
2. Review `README.md` for application usage
3. Check `BIGQUERY_DATASETS.md` for data requirements
4. Verify all configuration in `.env` file

## 🔒 Security Notes

- **Never commit `.env` file** with real credentials to version control
- Store GCP credentials file securely with restricted permissions:
  ```bash
  chmod 600 credentials/gcp-credentials.json
  ```
- Use strong `SECRET_KEY` for production
- Set `DEBUG=False` in production
- Use HTTPS in production (via reverse proxy)
- Restrict file system access to necessary directories only

## 📝 License

Part of the JustData platform. See main repository for license information.

