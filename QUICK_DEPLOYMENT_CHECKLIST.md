# Quick Deployment Checklist

## Pre-Deployment (5 minutes)

### 1. Clean Up Code
```bash
# Remove unnecessary files
rm -f env.template copy_credentials.py Untitled-1
rm -f justdata/apps/branchseeker/map_test.html  # Duplicate
rm -f justdata/apps/lendsight/test_*.py  # Move to tests/ if needed
```

### 2. Create Production .env
```bash
# Copy example and fill in real values
cp env.example .env
# Edit .env with production values
# NEVER commit .env to git!
```

### 3. Security Check
- [ ] `DEBUG=False` in production
- [ ] Strong `SECRET_KEY` generated
- [ ] All API keys set
- [ ] CORS origins limited to your domain
- [ ] No hardcoded credentials in code

## Deployment Options (Choose One)

### Option A: Heroku (Easiest - 10 minutes)

**Prerequisites:**
- Heroku account (free tier available)
- Heroku CLI installed

**Steps:**
```bash
# 1. Login
heroku login

# 2. Create app
heroku create justdata-test

# 3. Set environment variables
heroku config:set DEBUG=False
heroku config:set SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
heroku config:set BIGQUERY_PROJECT_ID=your-project-id
heroku config:set CENSUS_API_KEY=your-key
# ... add all other variables from .env

# 4. Create Procfile
echo "web: python run_branchseeker.py" > Procfile

# 5. Deploy
git push heroku JasonEdits:main

# 6. Open
heroku open
```

**Access:**
- LendSight: `https://justdata-test.herokuapp.com` (deploy separately or use different port)
- BranchSeeker: `https://justdata-test.herokuapp.com` (deploy separately or use different port)
- BranchMapper: `https://justdata-test.herokuapp.com/branch-mapper` (same server as BranchSeeker)
- MergerMeter: `https://justdata-test.herokuapp.com` (deploy separately or use different port)

### Option B: Railway (Very Easy - 5 minutes)

**Steps:**
1. Go to https://railway.app
2. Click "New Project" → "Deploy from GitHub"
3. Select your repository and branch (JasonEdits)
4. Add environment variables in Railway dashboard
5. Railway auto-detects Python and deploys
6. Get your URL: `https://your-app.railway.app`

**Note:** Railway auto-detects `run_branchseeker.py` as entry point

### Option C: Google Cloud App Engine (15 minutes)

**Prerequisites:**
- Google Cloud account
- gcloud CLI installed

**Steps:**
```bash
# 1. Create app.yaml
cat > app.yaml << EOF
runtime: python39
env: standard
instance_class: F2

env_variables:
  DEBUG: 'False'
  PORT: '8080'
EOF

# 2. Set sensitive variables
gcloud app deploy --set-env-vars \
  SECRET_KEY=your-secret-key \
  BIGQUERY_PROJECT_ID=your-project-id \
  CENSUS_API_KEY=your-key

# 3. Deploy
gcloud app deploy

# 4. Open
gcloud app browse
```

### Option D: DigitalOcean Droplet (VPS - 30 minutes)

**Steps:**
1. Create Ubuntu 22.04 droplet ($6/month)
2. SSH into server
3. Install dependencies:
   ```bash
   sudo apt update
   sudo apt install python3-pip python3-venv nginx
   ```
4. Clone repository
5. Set up virtual environment
6. Install dependencies
7. Create systemd service
8. Configure Nginx reverse proxy
9. Set up SSL with Let's Encrypt

## Post-Deployment Testing

### 1. Test Each Application
```bash
# BranchSeeker
curl https://your-app.com/

# BranchMapper
curl https://your-app.com/branch-mapper

# API endpoints
curl https://your-app.com/api/branches?county=Hillsborough%20County,%20Florida&year=2025
```

### 2. Verify Functionality
- [ ] LendSight loads and displays form
- [ ] BranchSeeker loads and displays form
- [ ] BranchMapper loads and shows map
- [ ] MergerMeter loads and displays form
- [ ] API endpoints return data
- [ ] BigQuery connections work
- [ ] Census API calls succeed
- [ ] File exports work

### 3. Check Logs
```bash
# Heroku
heroku logs --tail

# Railway
# View in dashboard

# GCP
gcloud app logs tail

# VPS
journalctl -u justdata -f
```

## Security Checklist

- [ ] HTTPS enabled (automatic on Heroku/Railway/GCP)
- [ ] DEBUG=False
- [ ] Strong SECRET_KEY
- [ ] CORS origins limited
- [ ] No credentials in code
- [ ] Environment variables secured
- [ ] Database credentials secure
- [ ] API keys rotated if needed

## Monitoring

### Set Up Alerts For:
- High error rates (>5%)
- Slow response times (>2 seconds)
- Database connection failures
- API quota limits

### Tools:
- Heroku: Built-in metrics
- Railway: Built-in monitoring
- GCP: Cloud Monitoring
- VPS: Set up UptimeRobot or similar

## Rollback Plan

If something goes wrong:

```bash
# Heroku
heroku rollback

# Railway
# Use dashboard to rollback

# GCP
gcloud app versions list
gcloud app versions migrate v1

# VPS
git checkout previous-commit
# Restart service
```

## Cost Estimates (Monthly)

- **Heroku**: Free tier (limited), $7/month for hobby
- **Railway**: $5/month (500 hours free)
- **GCP App Engine**: Free tier (limited), ~$10-20/month
- **DigitalOcean**: $6/month (droplet) + $12/month (managed database if needed)

## Recommended for Testing

**Best Option: Railway**
- Easiest setup
- Free tier available
- Auto-deploys from Git
- Built-in monitoring
- HTTPS included

## Next Steps After Deployment

1. Set up custom domain (optional)
2. Configure monitoring alerts
3. Set up automated backups
4. Document API endpoints
5. Create user guide
6. Plan for scaling

