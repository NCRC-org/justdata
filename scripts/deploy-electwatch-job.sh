#!/bin/bash
# =============================================================================
# Deploy ElectWatch Weekly Update Job
# 
# This script creates:
# 1. A Cloud Run Job for the weekly update
# 2. A Cloud Scheduler trigger to run it every Sunday at midnight EST
#
# Prerequisites:
# - gcloud CLI installed and authenticated
# - Required secrets in Secret Manager (see below)
#
# Usage:
#   ./scripts/deploy-electwatch-job.sh
# =============================================================================

set -e

# Configuration
PROJECT_ID="justdata-ncrc"
REGION="us-east1"
JOB_NAME="electwatch-weekly-update"
SCHEDULER_NAME="electwatch-weekly-trigger"
IMAGE_NAME="us-east1-docker.pkg.dev/hdma1-242116/justdata-repo/electwatch-job:latest"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Deploying ElectWatch Weekly Update Job ===${NC}"
echo ""

# Check if gcloud is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1 > /dev/null 2>&1; then
    echo -e "${RED}Error: Not authenticated with gcloud. Run 'gcloud auth login' first.${NC}"
    exit 1
fi

# Set the project
echo -e "${YELLOW}Setting project to ${PROJECT_ID}...${NC}"
gcloud config set project $PROJECT_ID

# =============================================================================
# Step 1: Create required secrets (if not exists)
# =============================================================================
echo ""
echo -e "${YELLOW}Step 1: Checking required secrets...${NC}"

REQUIRED_SECRETS=(
    "electwatch-bq-credentials"
    "fec-api-key"
    "congress-gov-api-key"
    "claude-api-key"
    "fmp-api-key"
    "quiver-api-key"
    "finnhub-api-key"
)

for secret in "${REQUIRED_SECRETS[@]}"; do
    if gcloud secrets describe $secret --project=$PROJECT_ID > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} Secret '$secret' exists"
    else
        echo -e "  ${RED}✗${NC} Secret '$secret' NOT FOUND"
        echo ""
        echo -e "${YELLOW}To create this secret, run:${NC}"
        echo "  gcloud secrets create $secret --project=$PROJECT_ID"
        echo "  echo -n 'YOUR_VALUE' | gcloud secrets versions add $secret --data-file=- --project=$PROJECT_ID"
        echo ""
        echo -e "${RED}Please create all required secrets before deploying.${NC}"
        exit 1
    fi
done

# =============================================================================
# Step 2: Build and push Docker image using Cloud Build
# =============================================================================
echo ""
echo -e "${YELLOW}Step 2: Building and pushing Docker image (Cloud Build)...${NC}"

# Create a temporary cloudbuild.yaml
cat > /tmp/cloudbuild-electwatch.yaml << 'EOF'
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-f', 'Dockerfile.electwatch-job', '-t', 'us-east1-docker.pkg.dev/hdma1-242116/justdata-repo/electwatch-job:latest', '.']
images:
  - 'us-east1-docker.pkg.dev/hdma1-242116/justdata-repo/electwatch-job:latest'
timeout: '1200s'
EOF

# Use Cloud Build to build and push (no local Docker needed)
echo "Submitting build to Cloud Build..."
gcloud builds submit \
    --project=hdma1-242116 \
    --config=/tmp/cloudbuild-electwatch.yaml \
    .

echo -e "  ${GREEN}✓${NC} Image pushed to $IMAGE_NAME"

# =============================================================================
# Step 3: Create or update Cloud Run Job
# =============================================================================
echo ""
echo -e "${YELLOW}Step 3: Creating/updating Cloud Run Job...${NC}"

# Check if job exists
if gcloud run jobs describe $JOB_NAME --region=$REGION --project=$PROJECT_ID > /dev/null 2>&1; then
    echo "Updating existing job..."
    ACTION="update"
else
    echo "Creating new job..."
    ACTION="create"
fi

gcloud run jobs $ACTION $JOB_NAME \
    --image=$IMAGE_NAME \
    --region=$REGION \
    --project=$PROJECT_ID \
    --memory=2Gi \
    --cpu=2 \
    --task-timeout=30m \
    --max-retries=1 \
    --set-env-vars="PYTHONPATH=/app" \
    --set-env-vars="JUSTDATA_PROJECT_ID=justdata-ncrc" \
    --set-secrets="ELECTWATCH_CREDENTIALS_JSON=electwatch-bq-credentials:latest,FEC_API_KEY=fec-api-key:latest,CONGRESS_GOV_API_KEY=congress-gov-api-key:latest,CLAUDE_API_KEY=claude-api-key:latest,FMP_API_KEY=fmp-api-key:latest,QUIVER_API_KEY=quiver-api-key:latest,FINNHUB_API_KEY=finnhub-api-key:latest"

echo -e "  ${GREEN}✓${NC} Cloud Run Job '$JOB_NAME' ${ACTION}d"

# =============================================================================
# Step 4: Create Cloud Scheduler trigger
# =============================================================================
echo ""
echo -e "${YELLOW}Step 4: Creating Cloud Scheduler trigger...${NC}"

# Get the service account for Cloud Run invoker
SERVICE_ACCOUNT="electwatch@justdata-ncrc.iam.gserviceaccount.com"

# Check if scheduler job exists
if gcloud scheduler jobs describe $SCHEDULER_NAME --location=$REGION --project=$PROJECT_ID > /dev/null 2>&1; then
    echo "Updating existing scheduler..."
    gcloud scheduler jobs update http $SCHEDULER_NAME \
        --location=$REGION \
        --project=$PROJECT_ID \
        --schedule="0 5 * * 0" \
        --time-zone="America/New_York" \
        --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run" \
        --http-method=POST \
        --oauth-service-account-email=$SERVICE_ACCOUNT
else
    echo "Creating new scheduler..."
    gcloud scheduler jobs create http $SCHEDULER_NAME \
        --location=$REGION \
        --project=$PROJECT_ID \
        --schedule="0 5 * * 0" \
        --time-zone="America/New_York" \
        --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run" \
        --http-method=POST \
        --oauth-service-account-email=$SERVICE_ACCOUNT
fi

echo -e "  ${GREEN}✓${NC} Cloud Scheduler '$SCHEDULER_NAME' configured"
echo "     Schedule: Every Sunday at 5:00 AM EST (0 5 * * 0)"

# =============================================================================
# Step 5: Grant necessary permissions
# =============================================================================
echo ""
echo -e "${YELLOW}Step 5: Granting permissions...${NC}"

# Grant Cloud Run Invoker role to the service account
gcloud run jobs add-iam-policy-binding $JOB_NAME \
    --region=$REGION \
    --project=$PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/run.invoker" \
    --quiet 2>/dev/null || true

echo -e "  ${GREEN}✓${NC} Permissions granted"

# =============================================================================
# Summary
# =============================================================================
echo ""
echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo ""
echo "Cloud Run Job: $JOB_NAME"
echo "Scheduler: $SCHEDULER_NAME"
echo "Schedule: Every Sunday at 5:00 AM EST"
echo ""
echo "To run manually:"
echo "  gcloud run jobs execute $JOB_NAME --region=$REGION --project=$PROJECT_ID"
echo ""
echo "To view logs:"
echo "  gcloud logging read 'resource.type=cloud_run_job AND resource.labels.job_name=$JOB_NAME' --limit=100 --project=$PROJECT_ID"
echo ""
