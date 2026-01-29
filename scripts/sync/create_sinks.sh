#!/bin/bash
# Create log sinks for each source table

SOURCE_PROJECT="hdma1-242116"
DEST_PROJECT="justdata-ncrc"

# Create sinks for each table
gcloud logging sinks create justdata-sync-sb-lenders \
    "pubsub.googleapis.com/projects/${DEST_PROJECT}/topics/justdata-sync-sb-lenders" \
    --project=${SOURCE_PROJECT} \
    --log-filter='resource.type="bigquery_dataset" AND protoPayload.methodName=~"tabledata.insertAll|tables.insert|tables.update|jobs.insert" AND protoPayload.resourceName=~"sb.*lenders"' \
    2>/dev/null || echo "Sink justdata-sync-sb-lenders already exists or error"

gcloud logging sinks create justdata-sync-sb-disclosure \
    "pubsub.googleapis.com/projects/${DEST_PROJECT}/topics/justdata-sync-sb-disclosure" \
    --project=${SOURCE_PROJECT} \
    --log-filter='resource.type="bigquery_dataset" AND protoPayload.methodName=~"tabledata.insertAll|tables.insert|tables.update|jobs.insert" AND protoPayload.resourceName=~"sb.*disclosure"' \
    2>/dev/null || echo "Sink justdata-sync-sb-disclosure already exists or error"

gcloud logging sinks create justdata-sync-hmda-lenders18 \
    "pubsub.googleapis.com/projects/${DEST_PROJECT}/topics/justdata-sync-hmda-lenders18" \
    --project=${SOURCE_PROJECT} \
    --log-filter='resource.type="bigquery_dataset" AND protoPayload.methodName=~"tabledata.insertAll|tables.insert|tables.update|jobs.insert" AND protoPayload.resourceName=~"hmda.*lenders18"' \
    2>/dev/null || echo "Sink justdata-sync-hmda-lenders18 already exists or error"

gcloud logging sinks create justdata-sync-hmda-gleif \
    "pubsub.googleapis.com/projects/${DEST_PROJECT}/topics/justdata-sync-hmda-gleif" \
    --project=${SOURCE_PROJECT} \
    --log-filter='resource.type="bigquery_dataset" AND protoPayload.methodName=~"tabledata.insertAll|tables.insert|tables.update|jobs.insert" AND protoPayload.resourceName=~"hmda.*lender_names_gleif"' \
    2>/dev/null || echo "Sink justdata-sync-hmda-gleif already exists or error"

gcloud logging sinks create justdata-sync-hmda-hmda \
    "pubsub.googleapis.com/projects/${DEST_PROJECT}/topics/justdata-sync-hmda-hmda" \
    --project=${SOURCE_PROJECT} \
    --log-filter='resource.type="bigquery_dataset" AND protoPayload.methodName=~"tabledata.insertAll|tables.insert|tables.update|jobs.insert" AND protoPayload.resourceName=~"justdata.*de_hmda"' \
    2>/dev/null || echo "Sink justdata-sync-hmda-hmda already exists or error"

gcloud logging sinks create justdata-sync-branches-sod \
    "pubsub.googleapis.com/projects/${DEST_PROJECT}/topics/justdata-sync-branches-sod" \
    --project=${SOURCE_PROJECT} \
    --log-filter='resource.type="bigquery_dataset" AND protoPayload.methodName=~"tabledata.insertAll|tables.insert|tables.update|jobs.insert" AND protoPayload.resourceName=~"branches.*sod"' \
    2>/dev/null || echo "Sink justdata-sync-branches-sod already exists or error"

gcloud logging sinks create justdata-sync-cu-branches \
    "pubsub.googleapis.com/projects/${DEST_PROJECT}/topics/justdata-sync-cu-branches" \
    --project=${SOURCE_PROJECT} \
    --log-filter='resource.type="bigquery_dataset" AND protoPayload.methodName=~"tabledata.insertAll|tables.insert|tables.update|jobs.insert" AND protoPayload.resourceName=~"credit_unions.*cu_branches"' \
    2>/dev/null || echo "Sink justdata-sync-cu-branches already exists or error"

gcloud logging sinks create justdata-sync-cu-call-reports \
    "pubsub.googleapis.com/projects/${DEST_PROJECT}/topics/justdata-sync-cu-call-reports" \
    --project=${SOURCE_PROJECT} \
    --log-filter='resource.type="bigquery_dataset" AND protoPayload.methodName=~"tabledata.insertAll|tables.insert|tables.update|jobs.insert" AND protoPayload.resourceName=~"credit_unions.*cu_call_reports"' \
    2>/dev/null || echo "Sink justdata-sync-cu-call-reports already exists or error"

echo "Log sinks created!"
