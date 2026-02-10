# DataExplorer Docker Deployment Guide

**Version:** 2.0.0  
**Last Updated:** January 27, 2025

---

## Overview

This guide covers deploying DataExplorer 2.0 using Docker containers. The Dockerfile is production-ready and optimized for hosting services like AWS ECS, Google Cloud Run, Azure Container Instances, or any Docker-compatible platform.

---

## Quick Start

### Build the Image

```bash
# From repository root
docker build -f apps/dataexplorer/Dockerfile -t dataexplorer:2.0.0 .
```

### Run the Container

```bash
docker run -d \
  --name dataexplorer \
  -p 8085:8085 \
  -e GOOGLE_CLOUD_PROJECT=your-project-id \
  -e GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json \
  -e SECRET_KEY=your-secret-key \
  dataexplorer:2.0.0
```

### Using Docker Compose

```bash
# Copy example file
cp apps/dataexplorer/docker-compose.example.yml docker-compose.yml

# Edit docker-compose.yml with your environment variables
# Then run:
docker-compose up -d
```

---

## Dockerfile Details

### Base Image
- **Python 3.11-slim** - Lightweight Python image
- Includes essential system libraries

### System Dependencies
- `gcc`, `g++` - Required for compiling Python packages (pandas, numpy)
- `libffi-dev`, `libssl-dev` - Required for cryptography libraries

### Layer Optimization
1. **Shared directory copied first** - Better caching when shared code changes
2. **App files copied second** - App-specific changes don't invalidate shared layer
3. **Dependencies installed last** - Changes to code don't require re-installing packages

### Security
- **Non-root user** - Container runs as `dataexplorer` user (UID 1000)
- **Minimal base image** - Reduces attack surface
- **No cache in pip** - Reduces image size

### Health Check
- Checks `/health` endpoint every 30 seconds
- 10-second timeout
- 3 retries before marking unhealthy
- 40-second start period

---

## Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `GOOGLE_CLOUD_PROJECT` | GCP project ID | `hdma1-242116` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to credentials JSON | `/app/credentials.json` |
| `SECRET_KEY` | Flask secret key | `your-random-secret-key` |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_ENV` | Flask environment | `production` |
| `FLASK_DEBUG` | Debug mode | `false` |
| `PORT` | Port to bind | `8085` |
| `AI_PROVIDER` | AI provider | `claude` |
| `CLAUDE_API_KEY` | Claude API key | - |
| `DEBUG_MODE` | Debug mode flag | `false` |
| `LOG_QUERIES` | Log SQL queries | `false` |

---

## Deployment Options

### Option 1: Docker Compose (Recommended for Testing)

```bash
cd apps/dataexplorer
docker-compose -f docker-compose.example.yml up -d
```

### Option 2: Direct Docker Run

```bash
docker run -d \
  --name dataexplorer \
  -p 8085:8085 \
  --env-file .env \
  dataexplorer:2.0.0
```

### Option 3: Cloud Platforms

#### AWS ECS / Fargate
```bash
# Build and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com
docker build -f apps/dataexplorer/Dockerfile -t dataexplorer:2.0.0 .
docker tag dataexplorer:2.0.0 <account>.dkr.ecr.us-east-1.amazonaws.com/dataexplorer:2.0.0
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/dataexplorer:2.0.0
```

#### Google Cloud Run
```bash
# Build and push to GCR
gcloud builds submit --tag gcr.io/<project-id>/dataexplorer:2.0.0

# Deploy
gcloud run deploy dataexplorer \
  --image gcr.io/<project-id>/dataexplorer:2.0.0 \
  --platform managed \
  --region us-central1 \
  --port 8085 \
  --set-env-vars GOOGLE_CLOUD_PROJECT=<project-id>
```

#### Azure Container Instances
```bash
# Build and push to ACR
az acr build --registry <registry-name> --image dataexplorer:2.0.0 .

# Deploy
az container create \
  --resource-group <resource-group> \
  --name dataexplorer \
  --image <registry-name>.azurecr.io/dataexplorer:2.0.0 \
  --ports 8085 \
  --environment-variables GOOGLE_CLOUD_PROJECT=<project-id>
```

---

## Production Considerations

### Resource Limits

**Recommended:**
- **CPU:** 1-2 cores
- **Memory:** 1-2 GB
- **Storage:** 10 GB (for logs and temp files)

**Minimum:**
- **CPU:** 0.5 cores
- **Memory:** 512 MB
- **Storage:** 5 GB

### Scaling

**Horizontal Scaling:**
- Run multiple container instances behind a load balancer
- Use sticky sessions if needed (not required for stateless app)
- Share BigQuery credentials across instances

**Vertical Scaling:**
- Increase CPU/memory for heavy query workloads
- Monitor BigQuery quota limits

### Monitoring

**Health Checks:**
- Endpoint: `/health`
- Interval: 30 seconds
- Timeout: 10 seconds

**Logs:**
- Gunicorn access logs: stdout
- Gunicorn error logs: stderr
- Application logs: Use structured logging

**Metrics to Monitor:**
- Request rate
- Response times
- Error rates
- BigQuery query duration
- Memory usage
- CPU usage

---

## Troubleshooting

### Container Won't Start

**Check logs:**
```bash
docker logs dataexplorer
```

**Common issues:**
1. Missing environment variables
2. Invalid BigQuery credentials
3. Port already in use
4. Insufficient resources

### Health Check Failing

**Test health endpoint:**
```bash
curl http://localhost:8085/health
```

**Common issues:**
1. App not starting properly
2. Port binding issues
3. Dependencies not installed

### BigQuery Connection Issues

**Verify credentials:**
```bash
docker exec dataexplorer python -c "from google.cloud import bigquery; print(bigquery.Client().project)"
```

**Common issues:**
1. Credentials file not mounted
2. Invalid JSON credentials
3. Missing project ID
4. Insufficient permissions

---

## Updating the Image

### Build New Version

```bash
# Update version tag
docker build -f apps/dataexplorer/Dockerfile -t dataexplorer:2.0.1 .

# Tag as latest
docker tag dataexplorer:2.0.1 dataexplorer:latest
```

### Rolling Update

```bash
# Pull new image
docker pull dataexplorer:2.0.1

# Stop old container
docker stop dataexplorer

# Remove old container
docker rm dataexplorer

# Start new container
docker run -d --name dataexplorer -p 8085:8085 dataexplorer:2.0.1
```

---

## Security Best Practices

1. **Never commit credentials** - Use environment variables or secrets management
2. **Use non-root user** - Already configured in Dockerfile
3. **Keep base image updated** - Regularly rebuild with latest Python 3.11-slim
4. **Scan for vulnerabilities** - Use `docker scan` or similar tools
5. **Limit network exposure** - Only expose necessary ports
6. **Use secrets management** - AWS Secrets Manager, GCP Secret Manager, etc.

---

## File Structure

```
apps/dataexplorer/
├── Dockerfile                 # Production Dockerfile
├── .dockerignore             # Files to exclude from build
├── docker-compose.example.yml # Example compose file
├── DOCKER_DEPLOYMENT.md      # This file
├── requirements.txt          # Python dependencies
├── app.py                    # Flask application
├── run.py                    # Development runner
└── ...                       # Other app files
```

---

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Build and Push DataExplorer

on:
  push:
    branches: [main]
    paths:
      - 'apps/dataexplorer/**'
      - 'shared/**'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker image
        run: docker build -f apps/dataexplorer/Dockerfile -t dataexplorer:${{ github.sha }} .
      
      - name: Push to registry
        run: |
          echo "${{ secrets.REGISTRY_PASSWORD }}" | docker login -u "${{ secrets.REGISTRY_USERNAME }}" --password-stdin
          docker push dataexplorer:${{ github.sha }}
```

---

## Next Steps After Render Testing

1. **Test on Render** - Verify all functionality works
2. **Build Docker image** - Create production image
3. **Push to registry** - Store in container registry
4. **Deploy to cloud** - Choose hosting platform
5. **Set up monitoring** - Configure logging and alerts
6. **Set up CI/CD** - Automate deployments

---

## Support

For issues or questions:
- Check logs: `docker logs dataexplorer`
- Review health endpoint: `curl http://localhost:8085/health`
- Check environment variables: `docker exec dataexplorer env`

---

**Ready for production deployment after Render testing!** 🚀
