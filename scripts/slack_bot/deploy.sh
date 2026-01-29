#!/bin/bash
# Deploy JustData Slack Bot to Cloud Run

PROJECT_ID="justdata-ncrc"
REGION="us-east1"
SERVICE_NAME="justdata-slack-bot"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "Building container image..."
gcloud builds submit --tag ${IMAGE} --project=${PROJECT_ID}

echo "Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image=${IMAGE} \
    --platform=managed \
    --region=${REGION} \
    --project=${PROJECT_ID} \
    --memory=512Mi \
    --cpu=1 \
    --min-instances=0 \
    --max-instances=3 \
    --timeout=60 \
    --allow-unauthenticated \
    --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID}" \
    --set-env-vars="SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}" \
    --set-env-vars="SLACK_SIGNING_SECRET=${SLACK_SIGNING_SECRET}" \
    --set-env-vars="SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL}"

echo ""
echo "Deployment complete!"
echo ""
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --project=${PROJECT_ID} --format='value(status.url)')
echo "Service URL: ${SERVICE_URL}"
echo ""
echo "Configure your Slack app:"
echo "1. Slash Commands URL: ${SERVICE_URL}/slack/commands"
echo "2. Event Subscriptions URL: ${SERVICE_URL}/slack/events"
echo "3. Interactivity URL: ${SERVICE_URL}/slack/events"
