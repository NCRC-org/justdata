# JustData GCP Migration Scripts

This folder contains scripts to migrate JustData from `hdma1-242116` to `justdata-ncrc` GCP project using tiered aggregation for ~99% cost reduction.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    justdata-ncrc GCP Project                        │
├─────────────────────────────────────────────────────────────────────┤
│  shared dataset                                                     │
│  ├── cbsa_to_county (reference)                                     │
│  ├── census (reference)                                             │
│  ├── ct_tract_crosswalk (CT planning region mapping)                │
│  ├── de_hmda (derived HMDA table, ~50M rows)                        │
│  ├── lender_names_gleif (LEI -> name mapping)                       │
│  ├── county_centroids (map coordinates)                             │
│  └── cbsa_centroids (map coordinates)                               │
├─────────────────────────────────────────────────────────────────────┤
│  lendsight dataset                                                  │
│  ├── de_hmda_county_summary (~10K rows) ← LendSight, DataExplorer   │
│  ├── de_hmda_tract_summary (~500K rows) ← Minority/Income tables    │
│  └── lenders18 (LEI/respondent mapping)                             │
├─────────────────────────────────────────────────────────────────────┤
│  bizsight dataset                                                   │
│  ├── sb_county_summary (~5K rows) ← BizSight, MergerMeter           │
│  └── sb_lenders (respondent -> lender name mapping)                 │
├─────────────────────────────────────────────────────────────────────┤
│  branchsight dataset                                                │
│  ├── sod (current year branch data) ← BranchSight, BranchMapper     │
│  ├── sod_legacy (historical years)                                  │
│  └── branch_hhi_summary (HHI calculations) ← MergerMeter            │
├─────────────────────────────────────────────────────────────────────┤
│  lenderprofile dataset                                              │
│  ├── cu_branches (credit union branch locations)                    │
│  └── cu_call_reports (credit union financial data)                  │
├─────────────────────────────────────────────────────────────────────┤
│  cache dataset                                                      │
│  ├── analysis_cache (cached AI responses)                           │
│  ├── analysis_results (completed analysis jobs)                     │
│  └── usage_log (API request logging)                                │
├─────────────────────────────────────────────────────────────────────┤
│  firebase_analytics dataset                                         │
│  ├── all_events (unified analytics view)                            │
│  └── backfilled_events (historical events pre-Firebase)             │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Sync Architecture

Real-time synchronization from `hdma1-242116` (source) to `justdata-ncrc` (destination):

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│  hdma1-242116       │     │    Cloud Pub/Sub    │     │   Cloud Function    │
│  (Source Tables)    │────>│  (Change Events)    │────>│  (Sync Handler)     │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
                                                                  │
                                                                  ▼
                            ┌─────────────────────┐     ┌─────────────────────┐
                            │   Slack Alerts      │<────│   justdata-ncrc     │
                            │  (#justdata-alerts) │     │  (Destination)      │
                            └─────────────────────┘     └─────────────────────┘
```

### Sync Mapping

| Source Table (hdma1) | Destination Table | Sync Type |
|---------------------|-------------------|-----------|
| `sb.lenders` | `bizsight.sb_lenders` | Full Copy |
| `sb.disclosure` | `bizsight.sb_county_summary` | Aggregated |
| `hmda.hmda` | `shared.de_hmda` | Derived |
| `hmda.lenders18` | `lendsight.lenders18` | Full Copy |
| `hmda.lender_names_gleif` | `shared.lender_names_gleif` | Full Copy |
| `branches.sod` | `branchsight.sod` | Full Copy |
| `credit_unions.cu_branches` | `lenderprofile.cu_branches` | Full Copy |
| `credit_unions.cu_call_reports` | `lenderprofile.cu_call_reports` | Full Copy |

### Cascading Dependencies

When `shared.de_hmda` is refreshed, these dependent tables are automatically updated:
- `lendsight.de_hmda_county_summary`
- `lendsight.de_hmda_tract_summary`

When `branchsight.sod` is refreshed:
- `branchsight.branch_hhi_summary` is automatically updated

## MergerMeter Hybrid Routing

MergerMeter allows users to select non-default HMDA filters (applications, manufactured homes, etc.).
The strategy is:

- **Default filters** (originations, owner-occupied, site-built, no reverse) → Query summary tables (~99% cost reduction)
- **Non-default filters** → Query raw `dataexplorer.de_hmda` (full flexibility)

This achieves ~95-98% overall cost reduction while maintaining full functionality.

## Prerequisites

1. **GCP Project Created**: Create a new project named `justdata` in GCP Console
2. **APIs Enabled**: BigQuery, Secret Manager, IAM
3. **gcloud CLI**: Authenticated with owner permissions on both projects

## Execution Order

### Phase 1: GCP Infrastructure (Run in GCP Console / gcloud)

```bash
# 1. Create the project (if not done via Console)
gcloud projects create justdata-ncrc --name="JustData"

# 2. Enable required APIs
gcloud services enable bigquery.googleapis.com --project=justdata-ncrc
gcloud services enable secretmanager.googleapis.com --project=justdata-ncrc
gcloud services enable iam.googleapis.com --project=justdata-ncrc

# 3. Create service accounts
./01_create_service_accounts.sh

# 4. Create datasets
./02_create_datasets.sh
```

### Phase 2: Data Migration (Run SQL in BigQuery Console)

Execute these SQL files in BigQuery Console (connected to `justdata` project):

1. `03_copy_shared_tables.sql` - Copy reference tables
2. `04_create_ct_crosswalk.sql` - Create Connecticut tract crosswalk
3. `05_create_hmda_county_summary.sql` - Create county-level HMDA summary
4. `06_create_hmda_tract_summary.sql` - Create tract-level HMDA summary
5. `07_create_sb_county_summary.sql` - Create SB county summary
6. `08_copy_branch_tables.sql` - Copy SOD tables
7. `09_copy_raw_hmda.sql` - Copy raw HMDA for edge cases

### Phase 3: Verification

```bash
# Run validation queries to compare old vs new data
./10_validate_migration.sql
```

## Service Accounts

| App | Service Account |
|-----|----------------|
| LendSight | lendsight@justdata-ncrc.iam.gserviceaccount.com |
| BizSight | bizsight@justdata-ncrc.iam.gserviceaccount.com |
| BranchSight | branchsight@justdata-ncrc.iam.gserviceaccount.com |
| BranchMapper | branchmapper@justdata-ncrc.iam.gserviceaccount.com |
| MergerMeter | mergermeter@justdata-ncrc.iam.gserviceaccount.com |
| DataExplorer | dataexplorer@justdata-ncrc.iam.gserviceaccount.com |
| LenderProfile | lenderprofile@justdata-ncrc.iam.gserviceaccount.com |
| Analytics | analytics@justdata-ncrc.iam.gserviceaccount.com |
| ElectWatch | electwatch@justdata-ncrc.iam.gserviceaccount.com |

## Dataset Permissions

Each service account gets `roles/bigquery.dataViewer` on its app-specific dataset plus the `shared` dataset.

## Validation

Run the validation script to verify migration completeness:

```bash
cd /path/to/justdata
python scripts/migration/validate_migration.py
```

This checks:
- All destination tables exist
- Row counts match source tables (where applicable)
- No null values in critical columns
- Code references are updated

## Slack Bot Commands

The Slack bot provides operational commands via `/jd`:

| Command | Description |
|---------|-------------|
| `/jd refresh <table>` | Manually refresh a specific table |
| `/jd status` | Show sync status and last refresh times |
| `/jd cache clear` | Clear analysis cache |
| `/jd analytics [days]` | Show usage analytics |
| `/jd validate` | Run migration validation |
| `/jd alerts [on/off]` | Configure alert preferences |
| `/jd help` | Show all available commands |

## Deployment

### Sync Infrastructure

```bash
# Deploy Cloud Function for sync
cd scripts/sync
./deploy_functions.sh

# Set up Pub/Sub topics and log sinks
./setup_pubsub.sh
./setup_log_sinks.sh
```

### Slack Bot

The Slack bot auto-deploys via GitHub Actions when `scripts/slack_bot/` files are changed on the `main` branch. Manual deployment:

```bash
cd scripts/slack_bot
./deploy.sh
```

Required GCP Secret Manager secrets:
- `slack-bot-token`: Slack Bot User OAuth Token
- `slack-signing-secret`: Slack App Signing Secret
- `slack-webhook-url`: Webhook URL for #justdata-alerts

## Safety Notes

- **hdma1-242116 is READ-ONLY**: All scripts only SELECT from the old project
- **Rollback**: Delete datasets in `justdata-ncrc` to start over
- **Validation**: Always run validation queries before switching production
- **Alerts**: Sync failures automatically notify #justdata-alerts channel