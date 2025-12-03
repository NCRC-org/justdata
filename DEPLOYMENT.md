# JustData Cloud Run Deployment Guide

This guide covers deploying the unified JustData application to Google Cloud Run.

## Prerequisites

1. **Google Cloud Project**: Ensure you have a GCP project set up
2. **gcloud CLI**: Install and configure the [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
3. **Authentication**: Authenticate with `gcloud auth login`
4. **Required APIs**: Enable the following APIs in your GCP project:
   - Cloud Run API
   - Cloud Build API
   - Artifact Registry API
   - Secret Manager API (if using secrets)

## GCP Resources Setup

### 1. Artifact Registry Repository

Create an Artifact Registry repository for Docker images:

```bash
gcloud artifacts repositories create justdata-repo \
    --repository-format=docker \
    --location=us-east1 \
    --description="JustData Docker images"
```

### 2. Service Account

Create a service account for Cloud Run (if it doesn't exist):

```bash
gcloud iam service-accounts create justdata \
    --display-name="JustData Service Account" \
    --project=YOUR_PROJECT_ID
```

Grant necessary permissions to the service account:

```bash
PROJECT_ID="your-project-id"
SERVICE_ACCOUNT="justdata@${PROJECT_ID}.iam.gserviceaccount.com"

# BigQuery access
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/bigquery.dataViewer"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/bigquery.jobUser"

# Cloud Run invoker (if needed for authenticated access)
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/run.invoker"

# Secret Manager access (if using secrets)
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"
```

### 3. Secret Manager (Optional but Recommended)

For sensitive environment variables, use Google Secret Manager:

```bash
# Create secrets
echo -n "your-secret-key" | gcloud secrets create SECRET_KEY --data-file=-
echo -n "your-api-key" | gcloud secrets create ANTHROPIC_API_KEY --data-file=-
echo -n "your-openai-key" | gcloud secrets create OPENAI_API_KEY --data-file=-

# Grant access to service account
gcloud secrets add-iam-policy-binding SECRET_KEY \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"
```

## Environment Variables

### Required Variables

Create a `.env` file in the project root with the following variables:

```bash
# Application Settings
SECRET_KEY=your-secret-key-here
DEBUG=false
LOG_LEVEL=INFO

# BigQuery Configuration
BIGQUERY_PROJECT_ID=your-bigquery-project-id
BIGQUERY_DATASET=your-bigquery-dataset

# AI Services (if using AI features)
ANTHROPIC_API_KEY=your-claude-api-key
OPENAI_API_KEY=your-openai-api-key

# HubSpot Integration (if enabled)
HUBSPOT_ACCESS_TOKEN=your-hubspot-access-token
HUBSPOT_PORTAL_ID=your-portal-id
HUBSPOT_API_KEY=your-hubspot-api-key
HUBSPOT_SYNC_ENABLED=True

# Database (if using PostgreSQL)
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Redis (if using Redis)
REDIS_URL=redis://host:6379
```

### Using Secret Manager

For production, use Secret Manager instead of plain environment variables:

```bash
# Reference secrets in Cloud Run deployment
gcloud run services update justdata \
    --update-secrets=SECRET_KEY=SECRET_KEY:latest,ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest \
    --region=us-east1
```

## Deployment

### Quick Deployment

Use the provided deployment script:

```bash
./scripts/deploy-cloudrun.sh
```

### Manual Deployment

1. **Build and push image using Cloud Build**:

```bash
PROJECT_ID="your-project-id"
IMAGE_URI="us-east1-docker.pkg.dev/${PROJECT_ID}/justdata-repo/justdata:latest"

gcloud builds submit \
    --substitutions=_APP_NAME=,_IMAGE_URI=${IMAGE_URI} \
    --config=cloudbuild.yaml
```

2. **Deploy to Cloud Run**:

```bash
gcloud run deploy justdata \
    --image ${IMAGE_URI} \
    --platform managed \
    --region us-east1 \
    --allow-unauthenticated \
    --service-account justdata@${PROJECT_ID}.iam.gserviceaccount.com \
    --port 8080 \
    --memory 2Gi \
    --cpu 2 \
    --timeout 3600 \
    --max-instances 10 \
    --min-instances 0 \
    --set-env-vars="PROJECT_ID=${PROJECT_ID},DEBUG=false,LOG_LEVEL=INFO"
```

### Configuration Options

The deployment script supports the following environment variables:

- `GCP_PROJECT_ID`: GCP project ID (default: `hdma1-242116`)
- `GCP_REGION`: Deployment region (default: `us-east1`)
- `SERVICE_NAME`: Cloud Run service name (default: `justdata`)
- `IMAGE_TAG`: Docker image tag (default: `latest`)
- `SERVICE_ACCOUNT`: Service account email (default: `justdata@${PROJECT_ID}.iam.gserviceaccount.com`)

Example:

```bash
GCP_PROJECT_ID=my-project \
GCP_REGION=us-central1 \
SERVICE_NAME=justdata-prod \
./scripts/deploy-cloudrun.sh
```

## Cloud Run Service Configuration

### Resource Allocation

- **Memory**: 2Gi (adjust based on workload)
- **CPU**: 2 (adjust based on workload)
- **Timeout**: 3600s (1 hour, for long-running analyses)
- **Min Instances**: 0 (cost optimization, scales to zero)
- **Max Instances**: 10 (adjust based on expected traffic)

### Scaling

Cloud Run automatically scales based on traffic. Adjust `--max-instances` based on your needs:

```bash
gcloud run services update justdata \
    --max-instances 20 \
    --region us-east1
```

### Port Configuration

The application listens on port 8080 (Cloud Run default). The `PORT` environment variable is automatically set by Cloud Run.

## Health Checks

The application provides a health check endpoint at `/health`. Cloud Run uses this for service health monitoring.

Test the health endpoint:

```bash
SERVICE_URL=$(gcloud run services describe justdata --region=us-east1 --format="value(status.url)")
curl ${SERVICE_URL}/health
```

## Monitoring and Logging

### View Logs

```bash
gcloud run services logs read justdata --region=us-east1
```

### Monitor Metrics

View metrics in the [Cloud Console](https://console.cloud.google.com/run) or use:

```bash
gcloud run services describe justdata --region=us-east1
```

## Troubleshooting

### Common Issues

1. **Build fails**: Check Cloud Build logs in the GCP Console
2. **Deployment fails**: Verify service account permissions
3. **Application errors**: Check Cloud Run logs
4. **BigQuery access denied**: Ensure service account has BigQuery permissions
5. **Port binding errors**: Ensure application listens on `0.0.0.0:${PORT}`

### Debugging

Enable debug mode temporarily:

```bash
gcloud run services update justdata \
    --update-env-vars="DEBUG=true" \
    --region us-east1
```

### View Service Details

```bash
gcloud run services describe justdata --region=us-east1
```

## Updating the Deployment

To update the service with new code:

```bash
./scripts/deploy-cloudrun.sh
```

Or manually:

```bash
# Rebuild and push
gcloud builds submit --config=cloudbuild.yaml

# Update service
gcloud run services update justdata \
    --image us-east1-docker.pkg.dev/${PROJECT_ID}/justdata-repo/justdata:latest \
    --region us-east1
```

## Cost Optimization

1. **Min instances = 0**: Service scales to zero when not in use
2. **Right-size resources**: Adjust memory/CPU based on actual usage
3. **Use caching**: Implement result caching to reduce BigQuery costs
4. **Monitor usage**: Review Cloud Run metrics regularly

## Security Best Practices

1. **Use Secret Manager** for sensitive data
2. **Enable authentication** if needed: `--no-allow-unauthenticated`
3. **Use VPC connector** for private resources (if needed)
4. **Regularly rotate** API keys and secrets
5. **Enable audit logs** for compliance

## Next Steps

- Set up CI/CD pipeline for automated deployments
- Configure custom domain mapping
- Set up monitoring alerts
- Implement backup strategies for data
- Configure VPC connector for private resources

## Support

For issues or questions:
- Check Cloud Run logs
- Review application logs
- Consult GCP documentation
- Contact your DevOps team


