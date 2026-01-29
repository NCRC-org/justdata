#!/bin/bash
# Deploy Cloud Function for table sync

PROJECT_ID="justdata-ncrc"
REGION="us-east1"
FUNCTION_NAME="table-sync-function"
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"

echo "Deploying Cloud Function: ${FUNCTION_NAME}"

# Check for Slack webhook
if [ -z "$SLACK_WEBHOOK_URL" ]; then
    echo "WARNING: SLACK_WEBHOOK_URL not set. Notifications will be disabled."
    echo "Set it with: export SLACK_WEBHOOK_URL='https://hooks.slack.com/services/...'"
fi

# Deploy the function
gcloud functions deploy ${FUNCTION_NAME} \
    --project=${PROJECT_ID} \
    --region=${REGION} \
    --runtime=python311 \
    --trigger-http \
    --allow-unauthenticated \
    --entry-point=main \
    --source=. \
    --memory=512MB \
    --timeout=540s \
    --set-env-vars="SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL},SLACK_CHANNEL=#justdata-alerts"

echo ""
echo "Function deployed!"
echo "URL: https://${REGION}-${PROJECT_ID}.cloudfunctions.net/${FUNCTION_NAME}"
echo ""
echo "Test with:"
echo "  curl -X POST https://${REGION}-${PROJECT_ID}.cloudfunctions.net/${FUNCTION_NAME} \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"data\": \"c2IubGVuZGVycw==\"}'"  # base64 of "sb.lenders"
