# Deployment Summary for JustData Applications

## Current Application Structure

You have **four applications** in the JustData platform:

1. **LendSight** - Mortgage lending analysis
   - Route: `/` (root)
   - Port: 8082 (default)
   - Entry: `run_lendsight.py`

2. **BranchSeeker** - Bank branch analysis tool
   - Route: `/` (root)
   - Port: 8080 (default)
   - Entry: `run_branchseeker.py`

3. **BranchMapper** - Interactive branch location map
   - Route: `/branch-mapper`
   - Same server as BranchSeeker
   - Entry: `run_branchseeker.py` (shared Flask app)

4. **MergerMeter** - Two-bank merger impact analyzer
   - Route: `/` (root)
   - Port: 8083 (default)
   - Entry: `run_mergermeter.py`

## Recommended Deployment Strategy

### For Testing: Railway (Easiest)

**Why Railway:**
- ✅ Free tier (500 hours/month)
- ✅ Auto-deploys from Git
- ✅ Automatic HTTPS
- ✅ Built-in monitoring
- ✅ Easy environment variable management
- ✅ No credit card required for testing

**Time to Deploy:** ~5 minutes

**Steps:**
1. Go to https://railway.app
2. Sign up with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your repository and `JasonEdits` branch
5. Add environment variables in Railway dashboard
6. Railway auto-detects Python and deploys
7. Get your URL: `https://your-app.railway.app`

**Environment Variables Needed:**
```
DEBUG=False
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
BIGQUERY_PROJECT_ID=<your-project-id>
CENSUS_API_KEY=<your-census-key>
# Plus all BigQuery credentials (BQ_TYPE, BQ_PROJECT_ID, etc.)
```

**Access After Deployment:**
- LendSight: `https://your-app.railway.app/` (deploy separately or configure different port)
- BranchSeeker: `https://your-app.railway.app/` (deploy separately or configure different port)
- BranchMapper: `https://your-app.railway.app/branch-mapper` (same server as BranchSeeker)
- MergerMeter: `https://your-app.railway.app/` (deploy separately or configure different port)

### For Production: Google Cloud App Engine

**Why GCP:**
- ✅ Native BigQuery integration
- ✅ Automatic scaling
- ✅ Enterprise-grade security
- ✅ Free tier available
- ✅ Easy to add custom domain

**Time to Deploy:** ~15 minutes

See `DEPLOYMENT_GUIDE.md` for detailed steps.

## Critical Security Steps

### 1. Before Deployment
```bash
# Generate secure secret key
python -c "import secrets; print(secrets.token_hex(32))"

# Review .env file - ensure no secrets in code
# Check for hardcoded credentials
grep -r "password\|api_key\|secret" --include="*.py" | grep -v ".env"
```

### 2. Environment Variables
- ✅ Never commit `.env` file
- ✅ Use platform's secret management (Railway, GCP Secret Manager)
- ✅ Rotate keys regularly
- ✅ Use different keys for test/production

### 3. Application Settings
- ✅ `DEBUG=False` in production
- ✅ Strong `SECRET_KEY`
- ✅ Limited `CORS_ORIGINS` (only your domain)
- ✅ Rate limiting enabled

## Deployment Checklist

### Pre-Deployment
- [ ] Code cleanup completed
- [ ] All tests pass locally
- [ ] `.env` file created (not committed)
- [ ] `DEBUG=False` set
- [ ] Strong `SECRET_KEY` generated
- [ ] All API keys configured
- [ ] BigQuery credentials set up
- [ ] CORS origins configured

### Deployment
- [ ] Platform account created
- [ ] Repository connected
- [ ] Environment variables set
- [ ] Application deployed
- [ ] HTTPS enabled (automatic on most platforms)

### Post-Deployment
- [ ] All three apps accessible
- [ ] API endpoints working
- [ ] BigQuery connections successful
- [ ] Census API calls working
- [ ] File exports functional
- [ ] Monitoring set up
- [ ] Logs accessible

## Testing URLs After Deployment

Replace `your-app.railway.app` with your actual URL:

```
# BranchSeeker
https://your-app.railway.app/

# BranchMapper
https://your-app.railway.app/branch-mapper

# BranchSeeker API
https://your-app.railway.app/api/branches?county=Hillsborough%20County,%20Florida&year=2025

# LendSight (if deployed separately)
https://your-lendsight-app.railway.app/
```

## Troubleshooting

### Common Issues:

1. **"Module not found" errors**
   - Check `requirements.txt` includes all dependencies
   - Verify Python version matches

2. **BigQuery authentication fails**
   - Verify service account JSON key is set correctly
   - Check `GOOGLE_APPLICATION_CREDENTIALS` environment variable
   - Ensure service account has BigQuery permissions

3. **Census API errors**
   - Verify `CENSUS_API_KEY` is set
   - Check API key is valid and not expired
   - Review rate limits

4. **CORS errors**
   - Update `CORS_ORIGINS` environment variable
   - Include your deployment URL

5. **Port conflicts**
   - Railway/GCP auto-assign ports
   - Use `PORT` environment variable if needed
   - Check platform documentation

## Cost Comparison

| Platform | Free Tier | Paid Tier | Best For |
|----------|-----------|-----------|----------|
| Railway | 500 hrs/month | $5/month | Testing |
| Heroku | Limited | $7/month | Quick testing |
| GCP App Engine | Limited | ~$10-20/month | Production |
| DigitalOcean | None | $6/month | Full control |

## Next Steps

1. **Choose deployment platform** (Railway recommended for testing)
2. **Set up environment variables**
3. **Deploy application**
4. **Test all functionality**
5. **Set up monitoring**
6. **Document for team**

## Support Resources

- Railway Docs: https://docs.railway.app
- GCP App Engine: https://cloud.google.com/appengine/docs
- Heroku: https://devcenter.heroku.com
- See `DEPLOYMENT_GUIDE.md` for detailed instructions

