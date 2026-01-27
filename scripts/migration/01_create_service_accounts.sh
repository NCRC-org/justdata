#!/bin/bash
# Create service accounts for JustData apps in the justdata project

PROJECT_ID="justdata-ncrc"

echo "Creating service accounts in project: $PROJECT_ID"

# List of apps that need service accounts
APPS=(
    "lendsight"
    "bizsight"
    "branchsight"
    "branchmapper"
    "mergermeter"
    "dataexplorer"
    "lenderprofile"
    "analytics"
    "electwatch"
)

for APP in "${APPS[@]}"; do
    echo "Creating service account: $APP"
    gcloud iam service-accounts create "$APP" \
        --project="$PROJECT_ID" \
        --display-name="$APP service account" \
        --description="Service account for $APP app"
done

echo ""
echo "Service accounts created:"
gcloud iam service-accounts list --project="$PROJECT_ID"
