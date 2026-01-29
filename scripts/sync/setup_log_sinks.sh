#!/bin/bash
# Setup BigQuery audit log sinks for change detection

SOURCE_PROJECT="hdma1-242116"
DEST_PROJECT="justdata-ncrc"

echo "Setting up log sinks for BigQuery change detection..."

# Map of datasets to monitor -> Pub/Sub topic
declare -A DATASET_TOPICS=(
    ["sb"]="justdata-sync-sb-lenders"
    ["hmda"]="justdata-sync-hmda-hmda"
    ["branches"]="justdata-sync-branches-sod"
    ["credit_unions"]="justdata-sync-cu-branches"
)

for dataset in "${!DATASET_TOPICS[@]}"; do
    SINK_NAME="justdata-sync-${dataset}-sink"
    TOPIC="${DATASET_TOPICS[$dataset]}"
    
    echo "Creating log sink: ${SINK_NAME}"
    
    # Create a log sink that triggers on BigQuery data changes
    gcloud logging sinks create ${SINK_NAME} \
        pubsub.googleapis.com/projects/${DEST_PROJECT}/topics/${TOPIC} \
        --project=${SOURCE_PROJECT} \
        --log-filter="
            resource.type=\"bigquery_dataset\"
            protoPayload.methodName=\"tableservice.insert\" OR
            protoPayload.methodName=\"tableservice.update\" OR
            protoPayload.methodName=\"jobservice.insert\"
            protoPayload.serviceData.jobCompletedEvent.job.jobConfiguration.load.destinationTable.datasetId=\"${dataset}\"
        " 2>/dev/null || echo "Sink ${SINK_NAME} already exists or failed"
done

echo ""
echo "Log sinks created. Grant the sink service accounts write access to Pub/Sub topics:"
echo ""
echo "For each sink, run:"
echo "  gcloud pubsub topics add-iam-policy-binding TOPIC_NAME \\"
echo "    --member=serviceAccount:SINK_WRITER_IDENTITY \\"
echo "    --role=roles/pubsub.publisher"
echo ""
echo "Get sink writer identities with:"
echo "  gcloud logging sinks describe SINK_NAME --project=${SOURCE_PROJECT}"
