# JustData - Deployment & Cleanup Guide

## Quick Start: Deploy to Railway (Recommended for Testing)

### Step 1: Prepare Your Code (5 minutes)

1. **Remove unnecessary files:**
   ```bash
   rm env.template copy_credentials.py Untitled-1
   rm justdata/apps/branchseeker/map_test.html  # Keep the one in shared/web/static/
   ```

2. **Create production .env file** (locally, never commit):
   ```bash
   cp env.example .env
   # Edit .env with your actual credentials
   ```

3. **Verify security:**
   - Set `DEBUG=False` in production
   - Generate strong `SECRET_KEY`: `python -c "import secrets; print(secrets.token_hex(32))"`
   - Ensure no credentials are hardcoded in code

### Step 2: Deploy to Railway (5 minutes)

1. **Sign up:** Go to https://railway.app and sign up with GitHub

2. **Create project:**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository and `JasonEdits` branch

3. **Set environment variables:**
   In Railway dashboard → Variables tab, add:
   ```
   DEBUG=False
   SECRET_KEY=<your-generated-secret-key>
   BIGQUERY_PROJECT_ID=<your-project-id>
   CENSUS_API_KEY=<your-census-api-key>
   BQ_TYPE=service_account
   BQ_PROJECT_ID=<your-project-id>
   BQ_PRIVATE_KEY_ID=<from-service-account-json>
   BQ_PRIVATE_KEY=<from-service-account-json>
   BQ_CLIENT_EMAIL=<from-service-account-json>
   BQ_CLIENT_ID=<from-service-account-json>
   BQ_AUTH_URI=https://accounts.google.com/o/oauth2/auth
   BQ_TOKEN_URI=https://oauth2.googleapis.com/token
   BQ_AUTH_PROVIDER_X509_CERT_URL=https://www.googleapis.com/oauth2/v1/certs
   BQ_CLIENT_X509_CERT_URL=<from-service-account-json>
   BIGQUERY_DATASET=<your-dataset-name>
   CORS_ORIGINS=https://your-app.railway.app
   ```

4. **Railway auto-deploys** - Your app will be live in ~2 minutes!

5. **Access your apps:**
   - LendSight: `https://your-app.railway.app/` (deploy separately or configure different port)
   - BranchSeeker: `https://your-app.railway.app/` (deploy separately or configure different port)
   - BranchMapper: `https://your-app.railway.app/branch-mapper` (same server as BranchSeeker)
   - MergerMeter: `https://your-app.railway.app/` (deploy separately or configure different port)

### Step 3: Test Everything

1. **Test BranchSeeker:**
   - Visit root URL
   - Fill out form and run analysis
   - Verify report displays

2. **Test BranchMapper:**
   - Visit `/branch-mapper`
   - Select state/county
   - Load map and verify markers appear
   - Test export functionality

3. **Test API endpoints:**
   ```bash
   curl https://your-app.railway.app/api/branches?county=Hillsborough%20County,%20Florida&year=2025
   ```

## Application Structure

### Four Applications:

1. **LendSight** (`run_lendsight.py`)
   - Mortgage lending analysis
   - Routes: `/`, `/report`
   - Port: 8082 (default)
   - Deploy separately or configure different port

2. **BranchSeeker** (`run_branchseeker.py`)
   - Bank branch analysis and reporting
   - Routes: `/`, `/report`, `/api/*`
   - Port: 8080 (default)

3. **BranchMapper** (in same Flask app as BranchSeeker)
   - Interactive branch location map
   - Route: `/branch-mapper`
   - Uses same server as BranchSeeker

4. **MergerMeter** (`run_mergermeter.py`)
   - Two-bank merger impact analyzer
   - Routes: `/`, `/report`
   - Port: 8083 (default)
   - Deploy separately or configure different port

## Security Checklist

Before deploying, ensure:

- [ ] `DEBUG=False` in production environment
- [ ] Strong `SECRET_KEY` generated and set
- [ ] All API keys configured (never hardcoded)
- [ ] BigQuery service account JSON credentials set
- [ ] CORS origins limited to your domain
- [ ] `.env` file is in `.gitignore` (already done)
- [ ] No credentials in code (search for hardcoded values)

## Cleanup Tasks

### Files to Remove:
- `env.template` (keep `env.example`)
- `copy_credentials.py` (no longer needed)
- `Untitled-1` (temporary file)
- `justdata/apps/branchseeker/map_test.html` (duplicate)

### Documentation Organization:
- Keep deployment docs in root: `DEPLOYMENT_GUIDE.md`, `DEPLOYMENT_SUMMARY.md`
- Move development guides to `docs/` folder
- Move app-specific docs to `justdata/apps/{app}/docs/`

See `CLEANUP_PLAN.md` for detailed cleanup steps.

## Alternative Deployment Options

### Heroku
- Similar to Railway
- Free tier available
- See `QUICK_DEPLOYMENT_CHECKLIST.md`

### Google Cloud App Engine
- Best for production
- Native BigQuery integration
- See `DEPLOYMENT_GUIDE.md` for detailed steps

### DigitalOcean VPS
- Full control
- $6/month
- Requires more setup
- See `DEPLOYMENT_GUIDE.md`

## Troubleshooting

### Common Issues:

**"Module not found"**
- Check `requirements.txt` has all dependencies
- Verify Python version (3.9+)

**BigQuery authentication fails**
- Verify service account JSON credentials are set correctly
- Check all `BQ_*` environment variables are present
- Ensure service account has BigQuery permissions

**Census API errors**
- Verify `CENSUS_API_KEY` is set
- Check API key is valid
- Review rate limits

**CORS errors**
- Update `CORS_ORIGINS` to include your deployment URL
- Check browser console for specific errors

## Monitoring

After deployment:

1. **Check logs:**
   - Railway: Dashboard → Deployments → View Logs
   - Monitor for errors

2. **Test functionality:**
   - All three apps accessible
   - API endpoints working
   - File exports functional

3. **Set up alerts:**
   - High error rates
   - Slow response times
   - API quota limits

## Cost Estimates

| Platform | Free Tier | Paid | Best For |
|----------|-----------|------|----------|
| Railway | 500 hrs/month | $5/month | Testing |
| Heroku | Limited | $7/month | Quick test |
| GCP | Limited | ~$10-20/month | Production |
| DigitalOcean | None | $6/month | Full control |

## Next Steps

1. ✅ Deploy to Railway for testing
2. ✅ Test all three applications
3. ✅ Set up monitoring
4. ✅ Plan for production deployment
5. ✅ Document for team

## Support

- **Deployment Guide:** `DEPLOYMENT_GUIDE.md` (comprehensive)
- **Quick Checklist:** `QUICK_DEPLOYMENT_CHECKLIST.md`
- **Cleanup Plan:** `CLEANUP_PLAN.md`

