#!/bin/bash
# Create BigQuery datasets in the justdata project

PROJECT_ID="justdata-ncrc"
LOCATION="US"

echo "Creating BigQuery datasets in project: $PROJECT_ID"

# Create datasets
DATASETS=(
    "shared"
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

for DATASET in "${DATASETS[@]}"; do
    echo "Creating dataset: $DATASET"
    bq --project_id="$PROJECT_ID" mk \
        --dataset \
        --location="$LOCATION" \
        --description="JustData $DATASET dataset" \
        "$PROJECT_ID:$DATASET"
done

echo ""
echo "Datasets created:"
bq --project_id="$PROJECT_ID" ls

# Grant permissions to service accounts
echo ""
echo "Granting dataset permissions..."

# Each app gets access to shared + its own dataset
declare -A APP_DATASETS
APP_DATASETS["lendsight"]="shared lendsight"
APP_DATASETS["bizsight"]="shared bizsight"
APP_DATASETS["branchsight"]="shared branchsight"
APP_DATASETS["branchmapper"]="shared branchsight"  # Uses same data as branchsight
APP_DATASETS["mergermeter"]="shared lendsight bizsight"
APP_DATASETS["dataexplorer"]="shared lendsight dataexplorer"
APP_DATASETS["lenderprofile"]="shared lenderprofile"
APP_DATASETS["analytics"]="shared analytics"
APP_DATASETS["electwatch"]="shared electwatch"

for APP in "${!APP_DATASETS[@]}"; do
    SA_EMAIL="$APP@$PROJECT_ID.iam.gserviceaccount.com"
    DATASETS_LIST="${APP_DATASETS[$APP]}"
    
    for DS in $DATASETS_LIST; do
        echo "Granting $SA_EMAIL access to $DS"
        bq --project_id="$PROJECT_ID" update \
            --source /dev/stdin \
            "$PROJECT_ID:$DS" << EOF
{
  "access": [
    {"role": "READER", "userByEmail": "$SA_EMAIL"}
  ]
}
EOF
    done
done

echo ""
echo "Dataset setup complete!"
