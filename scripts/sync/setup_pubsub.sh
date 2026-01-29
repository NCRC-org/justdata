#!/bin/bash
# Setup Pub/Sub topics and subscriptions for JustData table sync

PROJECT_ID="justdata-ncrc"
REGION="us-east1"

echo "Setting up Pub/Sub for JustData sync..."

# Create topics for each source table
TABLES=(
    "sb-lenders"
    "sb-disclosure"
    "hmda-lenders18"
    "hmda-gleif"
    "hmda-hmda"
    "branches-sod"
    "cu-branches"
    "cu-call-reports"
)

for table in "${TABLES[@]}"; do
    TOPIC="justdata-sync-${table}"
    
    echo "Creating topic: ${TOPIC}"
    gcloud pubsub topics create ${TOPIC} --project=${PROJECT_ID} 2>/dev/null || echo "Topic ${TOPIC} already exists"
    
    # Create a push subscription to the Cloud Function
    SUBSCRIPTION="${TOPIC}-sub"
    FUNCTION_URL="https://${REGION}-${PROJECT_ID}.cloudfunctions.net/table-sync-function"
    
    echo "Creating subscription: ${SUBSCRIPTION}"
    gcloud pubsub subscriptions create ${SUBSCRIPTION} \
        --topic=${TOPIC} \
        --push-endpoint=${FUNCTION_URL} \
        --ack-deadline=600 \
        --project=${PROJECT_ID} 2>/dev/null || echo "Subscription ${SUBSCRIPTION} already exists"
done

echo ""
echo "Pub/Sub setup complete!"
echo ""
echo "To manually trigger a sync, publish a message:"
echo "  gcloud pubsub topics publish justdata-sync-sb-lenders --message='{\"source_table\": \"sb.lenders\"}'"
