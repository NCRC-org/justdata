# JustData Deployment Guide

This guide covers deploying LendSight, BranchSeeker, BranchMapper, and MergerMeter applications for testing and production.

## Table of Contents
1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Deployment Options](#deployment-options)
3. [Step-by-Step Deployment](#step-by-step-deployment)
4. [Security Considerations](#security-considerations)
5. [Testing After Deployment](#testing-after-deployment)
6. [Monitoring and Maintenance](#monitoring-and-maintenance)

## Pre-Deployment Checklist

### 1. Code Cleanup
- [ ] Remove duplicate files (env.template, copy_credentials.py, test files)
- [ ] Standardize application names (LendSight, BranchSeeker, BranchMapper, MergerMeter)
- [ ] Remove sensitive data from code
- [ ] Review and update README files
- [ ] Clean up unused dependencies

### 2. Environment Configuration
- [ ] Create production `.env` file (never commit this!)
- [ ] Set `DEBUG=False` in production
- [ ] Generate secure `SECRET_KEY`
- [ ] Configure production database credentials
- [ ] Set up BigQuery service account with proper permissions
- [ ] Configure API keys (Census, OpenAI, Anthropic if needed)
- [ ] Set appropriate CORS origins

### 3. Security Review
- [ ] Remove any hardcoded credentials
- [ ] Review file permissions
- [ ] Set up proper firewall rules
- [ ] Configure HTTPS/SSL certificates
- [ ] Set up rate limiting
- [ ] Review access controls

## Deployment Options

### Option 1: Cloud Platform (Recommended for Testing)

#### A. Google Cloud Platform (GCP) - App Engine
**Pros:**
- Easy integration with BigQuery
- Automatic scaling
- Built-in security
- Free tier available

**Steps:**
1. Create GCP project
2. Enable App Engine
3. Deploy using `gcloud` CLI
4. Configure environment variables in GCP Console

#### B. Heroku
**Pros:**
- Simple deployment
- Free tier for testing
- Easy environment variable management

**Steps:**
1. Create Heroku account
2. Install Heroku CLI
3. Create app: `heroku create justdata-test`
4. Set environment variables
5. Deploy: `git push heroku main`

#### C. Railway
**Pros:**
- Very simple setup
- Automatic deployments from Git
- Free tier available

**Steps:**
1. Connect GitHub repository
2. Configure environment variables
3. Deploy automatically

### Option 2: Virtual Private Server (VPS)

#### Recommended Providers:
- DigitalOcean ($6/month droplet)
- Linode ($5/month)
- AWS EC2 (pay-as-you-go)

**Steps:**
1. Create VPS instance (Ubuntu 22.04 recommended)
2. Set up firewall (UFW)
3. Install Python, PostgreSQL (if needed), Nginx
4. Clone repository
5. Set up systemd service
6. Configure Nginx reverse proxy
7. Set up SSL with Let's Encrypt

### Option 3: Docker Container

**Pros:**
- Consistent environment
- Easy to scale
- Works on any platform

**Steps:**
1. Build Docker image
2. Push to container registry (Docker Hub, GCR)
3. Deploy to container platform (GKE, ECS, etc.)

## Step-by-Step Deployment (GCP App Engine Example)

### Phase 1: Preparation

1. **Install Google Cloud SDK**
   ```bash
   # Download and install from: https://cloud.google.com/sdk/docs/install
   gcloud init
   gcloud auth login
   ```

2. **Create GCP Project**
   ```bash
   gcloud projects create justdata-test --name="JustData Test"
   gcloud config set project justdata-test
   ```

3. **Enable Required APIs**
   ```bash
   gcloud services enable appengine.googleapis.com
   gcloud services enable bigquery.googleapis.com
   ```

### Phase 2: Application Configuration

1. **Create `app.yaml` for App Engine**
   ```yaml
   runtime: python39
   env: standard
   
   instance_class: F2
   
   env_variables:
     DEBUG: 'False'
     LOG_LEVEL: 'INFO'
     # Add other non-sensitive variables here
   
   # Sensitive variables should be set via:
   # gcloud app deploy --set-env-vars KEY=value
   ```

2. **Create `.gcloudignore`**
   ```
   .env
   .git
   __pycache__
   *.pyc
   .pytest_cache
   data/reports/*
   *.log
   ```

3. **Update `requirements.txt`** (ensure all dependencies are listed)

### Phase 3: Environment Variables Setup

**IMPORTANT: Never commit `.env` file!**

1. **Set environment variables in GCP Console:**
   ```bash
   gcloud app deploy --set-env-vars \
     SECRET_KEY=your-secret-key-here \
     BIGQUERY_PROJECT_ID=your-project-id \
     CENSUS_API_KEY=your-census-key
   ```

2. **For BigQuery credentials:**
   - Create service account in GCP Console
   - Download JSON key file
   - Store securely (use Secret Manager for production)
   - Set `GOOGLE_APPLICATION_CREDENTIALS` environment variable

### Phase 4: Database Setup (if using PostgreSQL)

1. **Create Cloud SQL instance:**
   ```bash
   gcloud sql instances create justdata-db \
     --database-version=POSTGRES_14 \
     --tier=db-f1-micro \
     --region=us-central1
   ```

2. **Create database and user:**
   ```bash
   gcloud sql databases create justdata --instance=justdata-db
   gcloud sql users create justdata --instance=justdata-db --password=your-secure-password
   ```

3. **Get connection name:**
   ```bash
   gcloud sql instances describe justdata-db --format="value(connectionName)"
   ```

4. **Update DATABASE_URL in environment variables**

### Phase 5: Deployment

1. **Test locally first:**
   ```bash
   python run_branchseeker.py
   # Test all three apps
   ```

2. **Deploy to App Engine:**
   ```bash
   gcloud app deploy
   ```

3. **Deploy specific service (if using multiple services):**
   ```bash
   gcloud app deploy app.yaml --version=v1
   ```

4. **View logs:**
   ```bash
   gcloud app logs tail -s default
   ```

### Phase 6: Domain and SSL

1. **Map custom domain (optional):**
   ```bash
   gcloud app domain-mappings create yourdomain.com
   ```

2. **SSL is automatically handled by App Engine**

## Security Considerations

### 1. Environment Variables
- ✅ Use Secret Manager for sensitive data (production)
- ✅ Never commit `.env` files
- ✅ Rotate API keys regularly
- ✅ Use different keys for test/production

### 2. Application Security
- ✅ Set `DEBUG=False` in production
- ✅ Use strong `SECRET_KEY` (generate with: `python -c "import secrets; print(secrets.token_hex(32))"`)
- ✅ Configure CORS properly (limit origins)
- ✅ Enable rate limiting
- ✅ Use HTTPS only

### 3. Database Security
- ✅ Use connection pooling
- ✅ Limit database user permissions
- ✅ Enable SSL for database connections
- ✅ Regular backups

### 4. API Security
- ✅ Validate all inputs
- ✅ Sanitize outputs
- ✅ Use parameterized queries (prevent SQL injection)
- ✅ Implement authentication if needed

### 5. File Permissions
```bash
# Set proper permissions
chmod 600 .env  # Only owner can read/write
chmod 755 run_*.py  # Executable
```

## Testing After Deployment

### 1. Health Checks
- [ ] Test each application endpoint
- [ ] Verify BigQuery connections
- [ ] Test Census API calls
- [ ] Check file uploads/downloads
- [ ] Verify map functionality (BranchMapper)

### 2. Performance Testing
- [ ] Load test with multiple concurrent users
- [ ] Monitor response times
- [ ] Check memory usage
- [ ] Verify database query performance

### 3. Security Testing
- [ ] Test CORS configuration
- [ ] Verify HTTPS redirect
- [ ] Test input validation
- [ ] Check for exposed sensitive data

## Monitoring and Maintenance

### 1. Logging
- Set up centralized logging (Cloud Logging, Papertrail, etc.)
- Monitor error rates
- Track API usage

### 2. Alerts
- Set up alerts for:
  - High error rates
  - Slow response times
  - Database connection issues
  - API quota limits

### 3. Backups
- Regular database backups
- Code repository backups
- Environment variable backups (encrypted)

### 4. Updates
- Regular dependency updates
- Security patches
- Feature updates

## Quick Start: Heroku Deployment (Easiest for Testing)

### 1. Install Heroku CLI
```bash
# Download from: https://devcenter.heroku.com/articles/heroku-cli
```

### 2. Login and Create App
```bash
heroku login
heroku create justdata-test
```

### 3. Set Environment Variables
```bash
heroku config:set DEBUG=False
heroku config:set SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
heroku config:set BIGQUERY_PROJECT_ID=your-project-id
heroku config:set CENSUS_API_KEY=your-key
# Add all other required variables
```

### 4. Create Procfile
```
web: python run_branchseeker.py
```

### 5. Deploy
```bash
git push heroku main
```

### 6. Open Application
```bash
heroku open
```

## Troubleshooting

### Common Issues:

1. **Import Errors**
   - Check `requirements.txt` includes all dependencies
   - Verify Python version matches

2. **Database Connection Issues**
   - Check connection string format
   - Verify firewall rules allow connections
   - Check credentials

3. **BigQuery Authentication**
   - Verify service account has proper permissions
   - Check JSON key file path
   - Ensure project ID is correct

4. **CORS Errors**
   - Update CORS_ORIGINS environment variable
   - Check browser console for specific errors

5. **Memory Issues**
   - Increase instance size
   - Optimize queries
   - Add caching

## Next Steps

1. Set up CI/CD pipeline (GitHub Actions)
2. Configure automated backups
3. Set up monitoring dashboards
4. Plan for scaling
5. Document API endpoints
6. Create user documentation

## Support

For issues or questions:
- Check application logs
- Review error messages
- Consult this guide
- Review application-specific documentation

