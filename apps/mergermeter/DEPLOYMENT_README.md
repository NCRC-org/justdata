# MergerMeter Deployment Guide

Complete guide for deploying MergerMeter to a web server.

## Quick Start

1. **Extract Package**
   ```bash
   unzip mergermeter-deployment.zip
   cd mergermeter-deployment-*
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**
   ```bash
   # Copy template
   cp apps/mergermeter/.env.example .env
   
   # Edit .env with your credentials
   nano .env  # or use your preferred editor
   ```

4. **Verify Configuration**
   ```bash
   python apps/mergermeter/check_config.py
   ```

5. **Start Application**
   ```bash
   python run_mergermeter.py
   ```

6. **Access Application**
   - Open browser: http://127.0.0.1:8083

## Detailed Setup

See `apps/mergermeter/DEPLOYMENT_PACKAGE.md` for complete documentation.

## Production Deployment

See `apps/mergermeter/DEPLOYMENT_PACKAGE.md` for production deployment options including:
- Gunicorn
- uWSGI
- Systemd service
- Docker
- Nginx reverse proxy

