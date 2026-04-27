# JustData Structural Audit

**Branch:** staging  
**Date:** 2026-04-21  
**Method:** Read-only analysis. No files modified, no branch changes, no test runs, no BigQuery connections.

---

## 1. Repo Tree

```
.
├── audit/
├── data/
│   ├── logs/
│   ├── processed/
│   ├── raw/
│   └── reports/
│       ├── bizsight/
│       ├── branchmapper/
│       ├── branchseeker/
│       ├── branchsight/
│       ├── lendsight/
│       ├── loantrends/
│       └── mergermeter/
├── docs/
│   ├── dataexplorer/
│   ├── electwatch/
│   ├── lenderprofile/
│   └── loantrends/
├── justdata/
│   ├── app/                          ← HubSpot CMS project
│   │   └── src/
│   │       └── app.functions/
│   ├── apps/
│   │   ├── _base/
│   │   ├── analytics/
│   │   │   ├── static/ (css/, demo_data/, js/)
│   │   │   └── templates/analytics/
│   │   ├── bizsight/
│   │   │   ├── data/ (benchmarks/, cbsa/, reports/)
│   │   │   ├── docs/
│   │   │   ├── sql_templates/
│   │   │   ├── static/ (css/, img/, js/)
│   │   │   ├── templates/
│   │   │   └── utils/
│   │   ├── branchmapper/
│   │   │   ├── sql_templates/
│   │   │   ├── static/ (img/)
│   │   │   └── templates/
│   │   ├── branchsight/
│   │   │   ├── sql_templates/
│   │   │   ├── static/ (img/)
│   │   │   └── templates/
│   │   ├── credentials/
│   │   ├── data/reports/
│   │   ├── dataexplorer/
│   │   │   ├── scripts/
│   │   │   ├── static/ (css/, data/, img/, js/)
│   │   │   ├── templates/
│   │   │   └── utils/
│   │   ├── electwatch/
│   │   │   ├── data/ (admin/, cache/, current/)
│   │   │   ├── docs/
│   │   │   ├── processors/
│   │   │   ├── scripts/
│   │   │   ├── services/
│   │   │   ├── static/ (css/, img/, js/)
│   │   │   └── templates/
│   │   ├── hubspot/
│   │   ├── lenderprofile/
│   │   │   ├── cache/
│   │   │   ├── logs/
│   │   │   ├── processors/context/
│   │   │   ├── report_builder/
│   │   │   ├── scripts/
│   │   │   ├── services/
│   │   │   ├── static/ (css/, img/, js/)
│   │   │   └── templates/
│   │   ├── lendsight/
│   │   │   ├── sql_templates/
│   │   │   ├── static/ (css/, img/, js/)
│   │   │   └── templates/
│   │   ├── loantrends/
│   │   │   ├── static/ (css/, img/, js/)
│   │   │   ├── static_site/data/
│   │   │   └── templates/
│   │   ├── memberview/
│   │   │   ├── static/ (img/)
│   │   │   ├── templates/
│   │   │   ├── utils/
│   │   │   └── web/ (static/css/, static/js/, templates/)
│   │   └── mergermeter/
│   │       ├── static/ (img/, js/, js/components/)
│   │       └── templates/
│   ├── core/
│   │   └── config/
│   ├── data/cache/dataexplorer/
│   ├── main/                         ← Unified platform entry point
│   ├── shared/
│   │   ├── analysis/
│   │   ├── core/
│   │   ├── reporting/
│   │   ├── services/
│   │   ├── utils/
│   │   └── web/
│   │       ├── static/ (css/, img/, img/app-logos/, js/, js/components/)
│   │       └── templates/
│   └── tests/
├── node_modules/                     ← HubSpot CLI dependencies
├── scripts/
│   ├── migration/
│   ├── slack_bot/
│   │   └── handlers/, utils/
│   └── sync/
└── tests/
    └── apps/
        ├── dataexplorer/
        ├── electwatch/
        ├── lenderprofile/
        └── memberview/
    └── core/, shared/
```

---

## 2. File Size Inventory

Top 30 files by line count (excluding venv, node\_modules, .git, \_\_pycache\_\_, dist, build).

| Path | Lines | Extension |
|------|-------|-----------|
| `justdata/apps/electwatch/templates/electwatch_dashboard.html` | 7,104 | .html |
| `justdata/apps/branchmapper/templates/branch_mapper_template.html` | 4,597 | .html |
| `justdata/apps/dataexplorer/templates/area_report_template.html` | 4,330 | .html |
| `justdata/apps/dataexplorer/static/js/wizard-steps.js` | 4,188 | .js |
| `justdata/apps/mergermeter/app.py` | 4,035 | .py |
| `justdata/apps/lendsight/templates/lendsight_report.html` | 3,703 | .html |
| `justdata/apps/bizsight/templates/bizsight_report.html` | 3,601 | .html |
| `justdata/apps/electwatch/weekly_update.py` | 3,404 | .py |
| `justdata/apps/lendsight/mortgage_report_builder.py` | 3,315 | .py |
| `justdata/apps/electwatch/app.py` | 3,263 | .py |
| `justdata/shared/web/templates/justdata_landing_page.html` | 3,110 | .html |
| `justdata/shared/web/static/css/style.css` | 2,722 | .css |
| `justdata/apps/dataexplorer/templates/lender_report_template.html` | 2,700 | .html |
| `justdata/apps/lenderprofile/static/js/report_v2.js` | 2,690 | .js |
| `justdata/apps/analytics/static/css/analytics.css` | 2,585 | .css |
| `justdata/apps/dataexplorer/area_report_builder.py` | 2,550 | .py |
| `justdata/apps/mergermeter/templates/mergermeter_analysis.html` | 2,549 | .html |
| `justdata/apps/analytics/bigquery_client.py` | 2,525 | .py |
| `justdata/apps/lenderprofile/report_builder/section_builders_v2.py` | 2,348 | .py |
| `justdata/apps/mergermeter/templates/analysis_template.html` | 2,315 | .html |
| `justdata/apps/electwatch/blueprint.py` | 2,159 | .py |
| `justdata/main/auth.py` | 2,125 | .py |
| `justdata/apps/dataexplorer/lender_analysis_core.py` | 2,083 | .py |
| `justdata/apps/branchsight/templates/report_template.html` | 2,065 | .html |
| `justdata/apps/lenderprofile/processors/data_collector.py` | 2,034 | .py |
| `justdata/apps/mergermeter/excel_generator.py` | 1,971 | .py |
| `justdata/apps/loantrends/static_site/index.html` | 1,868 | .html |
| `justdata/apps/dataexplorer/app.py` | 1,863 | .py |
| `justdata/shared/reporting/merger_excel_generator.py` | 1,803 | .py |
| `justdata/apps/electwatch/templates/official_profile.html` | 1,787 | .html |

---

## 3. Flask App Inventory

The repo contains two parallel execution modes for each app:

1. **Unified platform** (`justdata/main/app.py`): All sub-apps mounted as blueprints under URL prefixes. This is the Cloud Run deployment target.
2. **Standalone mode**: Each app has its own `app.py` with direct `@app.route` decorators and its own `run.py` gunicorn entry point. These duplicate the blueprint routes and are used for isolated local development.

### Unified Platform Entry Point

| Module | Type | Routes | URL Prefix |
|--------|------|--------|------------|
| `justdata/main/app.py` | Direct `@app.route` on Flask instance | 11 | `/` |
| `justdata/main/auth.py` | Blueprint (`auth_bp`) | 17 | `/api/auth` |
| `justdata/shared/web/app_factory.py` | Direct `@app.route` in factory | 1 | `/health` |
| `justdata/shared/core/app_factory.py` | Direct `@app.route` in factory | 4 | `/health`, `/favicon.*` |
| `justdata/shared/web/dashboard_routes.py` | Blueprint (`dashboard_bp`) | 2 | `/admin`, `/status` |

### Sub-Application Blueprints (registered in `justdata/main/app.py`)

| App | Blueprint Module | Blueprint Name | Routes | URL Prefix |
|-----|-----------------|----------------|--------|------------|
| Analytics | `justdata/apps/analytics/blueprint.py` | `analytics_bp` | 25 | `/analytics` |
| BizSight | `justdata/apps/bizsight/blueprint.py` | `bizsight_bp` | 13 | `/bizsight` |
| BranchMapper | `justdata/apps/branchmapper/blueprint.py` | `branchmapper_bp` | 16 | `/branchmapper` |
| BranchSight | `justdata/apps/branchsight/blueprint.py` | `branchsight_bp` | 11 | `/branchsight` |
| DataExplorer | `justdata/apps/dataexplorer/blueprint.py` | `dataexplorer_bp` | 25 | `/dataexplorer` |
| ElectWatch | `justdata/apps/electwatch/blueprint.py` | `electwatch_bp` | 41 | `/electwatch` |
| LenderProfile | `justdata/apps/lenderprofile/blueprint.py` | `lenderprofile_bp` | 5 | `/lenderprofile` |
| LendSight | `justdata/apps/lendsight/blueprint.py` | `lendsight_bp` | 13 | `/lendsight` |
| LoanTrends | `justdata/apps/loantrends/blueprint.py` | `loantrends_bp` | 7 | `/loantrends` |
| MemberView | `justdata/apps/memberview/blueprint.py` | `memberview_bp` | 2 | `/memberview` |
| MergerMeter | `justdata/apps/mergermeter/blueprint.py` | `mergermeter_bp` | 19 | `/mergermeter` |

CommentMaker blueprint (`/commentmaker`) is referenced in `justdata/main/app.py` with a `try/except ImportError` guard — its blueprint module was not present on the audited branch.

### Standalone App Instances (not part of unified platform)

Each of the following files creates its own `Flask()` instance with direct `@app.route` decorators. Route counts for these standalone files:

| File | Lines | Direct Routes |
|------|-------|---------------|
| `justdata/apps/bizsight/app.py` | 1,139 | 19 |
| `justdata/apps/branchmapper/app.py` | 1,265 | 14 |
| `justdata/apps/branchsight/app.py` | 632 | 9 |
| `justdata/apps/dataexplorer/app.py` | 1,863 | 32 |
| `justdata/apps/electwatch/app.py` | 3,263 | — (see note) |
| `justdata/apps/lenderprofile/app.py` | 577 | 8 |
| `justdata/apps/lendsight/app.py` | 614 | — |
| `justdata/apps/loantrends/app.py` | 434 | — |
| `justdata/apps/mergermeter/app.py` | 4,035 | 11 |
| `justdata/apps/analytics/app.py` | 26 | 0 (factory only) |

Note: `electwatch/app.py` is 3,263 lines but all its routes go through the blueprint; the standalone `app.py` imports and registers the blueprint. `lendsight/app.py` and `loantrends/app.py` follow a similar pattern.

---

## 4. Route Inventory

The `rg '@(app|bp|blueprint|[a-z_]+_bp)\.route\(' --type py` scan returned **343 total matches** across all Python files. This count includes both the blueprint route definitions and the duplicated direct-route definitions in each app's standalone `app.py`. The unique route count for the deployed unified platform (blueprint paths only) is approximately **190**.

The table below is capped at 150 entries per the audit instructions. Routes from standalone `app.py` files that duplicate their corresponding `blueprint.py` are included in the total count of 343 but are not all listed here.

| Method(s) | URL Pattern | Handler / Decorator Site | File:Line |
|-----------|-------------|--------------------------|-----------|
| GET | `/favicon.ico` | `@app.route` | `justdata/main/app.py:134` |
| GET | `/shared/<path:filename>` | `@app.route` | `justdata/main/app.py:144` |
| GET | `/` | `@app.route` | `justdata/main/app.py:154` |
| GET | `/about` | `@app.route` | `justdata/main/app.py:181` |
| GET | `/contact` | `@app.route` | `justdata/main/app.py:203` |
| GET | `/email-verified` | `@app.route` | `justdata/main/app.py:225` |
| POST | `/api/set-user-type` | `@app.route` | `justdata/main/app.py:258` |
| GET | `/api/access-info` | `@app.route` | `justdata/main/app.py:276` |
| GET | `/health` | `@app.route` | `justdata/main/app.py:299` |
| GET | `/api/platform-stats` | `@app.route` | `justdata/main/app.py:312` |
| GET | `/admin/users` | `@app.route` | `justdata/main/app.py:422` |
| GET | `/status` | `auth_bp` | `justdata/main/auth.py:1146` |
| POST | `/login` | `auth_bp` | `justdata/main/auth.py:1171` |
| POST | `/logout` | `auth_bp` | `justdata/main/auth.py:1263` |
| POST | `/set-user-type` | `auth_bp` | `justdata/main/auth.py:1273` |
| GET | `/users` | `auth_bp` | `justdata/main/auth.py:1311` |
| POST | `/users` | `auth_bp` | `justdata/main/auth.py:1393` |
| PUT | `/users/<uid>` | `auth_bp` | `justdata/main/auth.py:1464` |
| POST | `/resync` | `auth_bp` | `justdata/main/auth.py:1515` |
| GET | `/verification-status` | `auth_bp` | `justdata/main/auth.py:1572` |
| POST | `/email-verified` | `auth_bp` | `justdata/main/auth.py:1607` |
| POST | `/sync-all` | `auth_bp` | `justdata/main/auth.py:1672` |
| POST | `/users/delete` | `auth_bp` | `justdata/main/auth.py:1812` |
| PUT | `/users/<uid>/reset-password` | `auth_bp` | `justdata/main/auth.py:1904` |
| POST | `/set-organization` | `auth_bp` | `justdata/main/auth.py:1966` |
| GET | `/membership-status` | `auth_bp` | `justdata/main/auth.py:2014` |
| GET | `/member-request/status` | `auth_bp` | `justdata/main/auth.py:2056` |
| POST | `/member-request/dismiss-prompt` | `auth_bp` | `justdata/main/auth.py:2121` |
| GET | `/health` | `app_factory` | `justdata/shared/web/app_factory.py:72` |
| GET | `/admin` | `dashboard_bp` | `justdata/shared/web/dashboard_routes.py:23` |
| GET | `/status` | `dashboard_bp` | `justdata/shared/web/dashboard_routes.py:40` |
| GET | `/` | `analytics_bp` | `justdata/apps/analytics/blueprint.py:62` |
| GET | `/user-map` | `analytics_bp` | `justdata/apps/analytics/blueprint.py:79` |
| GET | `/research-map` | `analytics_bp` | `justdata/apps/analytics/blueprint.py:91` |
| GET | `/lender-map` | `analytics_bp` | `justdata/apps/analytics/blueprint.py:103` |
| GET | `/coalitions` | `analytics_bp` | `justdata/apps/analytics/blueprint.py:115` |
| GET | `/users` | `analytics_bp` | `justdata/apps/analytics/blueprint.py:127` |
| GET | `/costs` | `analytics_bp` | `justdata/apps/analytics/blueprint.py:139` |
| GET | `/api/summary` | `analytics_bp` | `justdata/apps/analytics/blueprint.py:155` |
| GET | `/api/user-locations` | `analytics_bp` | `justdata/apps/analytics/blueprint.py:168` |
| GET | `/api/research-activity` | `analytics_bp` | `justdata/apps/analytics/blueprint.py:190` |
| GET | `/api/lender-interest` | `analytics_bp` | `justdata/apps/analytics/blueprint.py:214` |
| GET | `/api/coalition-opportunities` | `analytics_bp` | `justdata/apps/analytics/blueprint.py:236` |
| GET | `/api/entity-users` | `analytics_bp` | `justdata/apps/analytics/blueprint.py:257` |
| GET | `/api/timeline` | `analytics_bp` | `justdata/apps/analytics/blueprint.py:281` |
| GET | `/lender-interest/<lender_id>` | `analytics_bp` | `justdata/apps/analytics/blueprint.py:294` |
| GET | `/api/lender-detail/<lender_id>` | `analytics_bp` | `justdata/apps/analytics/blueprint.py:307` |
| GET | `/api/users` | `analytics_bp` | `justdata/apps/analytics/blueprint.py:321` |
| GET | `/api/users/<user_id>/activity` | `analytics_bp` | `justdata/apps/analytics/blueprint.py:336` |
| GET | `/api/user-types` | `analytics_bp` | `justdata/apps/analytics/blueprint.py:350` |
| GET | `/health` | `analytics_bp` | `justdata/apps/analytics/blueprint.py:371` |
| GET | `/api/costs` | `analytics_bp` | `justdata/apps/analytics/blueprint.py:377` |
| GET | `/api/ai-costs` | `analytics_bp` | `justdata/apps/analytics/blueprint.py:402` |
| POST | `/api/force-sync` | `analytics_bp` | `justdata/apps/analytics/blueprint.py:426` |
| GET | `/api/lookup-county-fips` | `analytics_bp` | `justdata/apps/analytics/blueprint.py:457` |
| GET | `/api/export` | `analytics_bp` | `justdata/apps/analytics/blueprint.py:506` |
| GET | `/` | `bizsight_bp` | `justdata/apps/bizsight/blueprint.py:65` |
| GET | `/progress/<job_id>` | `bizsight_bp` | `justdata/apps/bizsight/blueprint.py:99` |
| POST | `/analyze` | `bizsight_bp` | `justdata/apps/bizsight/blueprint.py:128` |
| GET | `/data` | `bizsight_bp` | `justdata/apps/bizsight/blueprint.py:417` |
| GET | `/api/states` | `bizsight_bp` | `justdata/apps/bizsight/blueprint.py:434` |
| GET | `/api/counties-by-state/<state_code>` | `bizsight_bp` | `justdata/apps/bizsight/blueprint.py:449` |
| GET | `/api/county-boundaries` | `bizsight_bp` | `justdata/apps/bizsight/blueprint.py:561` |
| GET | `/api/state-boundaries` | `bizsight_bp` | `justdata/apps/bizsight/blueprint.py:577` |
| GET | `/api/tract-boundaries/<geoid5>` | `bizsight_bp` | `justdata/apps/bizsight/blueprint.py:593` |
| GET | `/report` | `bizsight_bp` | `justdata/apps/bizsight/blueprint.py:608` |
| GET | `/report-data` | `bizsight_bp` | `justdata/apps/bizsight/blueprint.py:634` |
| GET | `/download` | `bizsight_bp` | `justdata/apps/bizsight/blueprint.py:725` |
| GET | `/health` | `bizsight_bp` | `justdata/apps/bizsight/blueprint.py:836` |
| GET | `/` | `branchmapper_bp` | `justdata/apps/branchmapper/blueprint.py:66` |
| GET | `/counties` | `branchmapper_bp` | `justdata/apps/branchmapper/blueprint.py:90` |
| GET | `/states` | `branchmapper_bp` | `justdata/apps/branchmapper/blueprint.py:104` |
| GET | `/counties-by-state/<state_code>` | `branchmapper_bp` | `justdata/apps/branchmapper/blueprint.py:118` |
| GET | `/api/census-tracts/<county>` | `branchmapper_bp` | `justdata/apps/branchmapper/blueprint.py:132` |
| GET | `/api/census-tracts-by-state/<state_fips>` | `branchmapper_bp` | `justdata/apps/branchmapper/blueprint.py:329` |
| GET | `/api/branches` | `branchmapper_bp` | `justdata/apps/branchmapper/blueprint.py:553` |
| GET | `/api/oscr-events` | `branchmapper_bp` | `justdata/apps/branchmapper/blueprint.py:635` |
| GET | `/api/bank-list` | `branchmapper_bp` | `justdata/apps/branchmapper/blueprint.py:704` |
| GET | `/api/branches-by-bank` | `branchmapper_bp` | `justdata/apps/branchmapper/blueprint.py:716` |
| GET | `/api/branches-in-bounds` | `branchmapper_bp` | `justdata/apps/branchmapper/blueprint.py:768` |
| GET | `/api/counties-in-bounds` | `branchmapper_bp` | `justdata/apps/branchmapper/blueprint.py:823` |
| GET | `/api/oscr-events-by-bank` | `branchmapper_bp` | `justdata/apps/branchmapper/blueprint.py:843` |
| GET | `/api/oscr-events-in-bounds` | `branchmapper_bp` | `justdata/apps/branchmapper/blueprint.py:903` |
| GET | `/export/methods-pdf` | `branchmapper_bp` | `justdata/apps/branchmapper/blueprint.py:989` |
| GET | `/health` | `branchmapper_bp` | `justdata/apps/branchmapper/blueprint.py:1008` |
| GET | `/` | `branchsight_bp` | `justdata/apps/branchsight/blueprint.py:78` |
| GET | `/progress/<job_id>` | `branchsight_bp` | `justdata/apps/branchsight/blueprint.py:101` |
| POST | `/analyze` | `branchsight_bp` | `justdata/apps/branchsight/blueprint.py:130` |
| GET | `/report` | `branchsight_bp` | `justdata/apps/branchsight/blueprint.py:240` |
| GET | `/report-data` | `branchsight_bp` | `justdata/apps/branchsight/blueprint.py:261` |
| GET | `/download` | `branchsight_bp` | `justdata/apps/branchsight/blueprint.py:334` |
| GET | `/counties` | `branchsight_bp` | `justdata/apps/branchsight/blueprint.py:629` |
| GET | `/states` | `branchsight_bp` | `justdata/apps/branchsight/blueprint.py:646` |
| GET | `/metro-areas` | `branchsight_bp` | `justdata/apps/branchsight/blueprint.py:663` |
| GET | `/counties-by-state/<state_code>` | `branchsight_bp` | `justdata/apps/branchsight/blueprint.py:679` |
| GET | `/health` | `branchsight_bp` | `justdata/apps/branchsight/blueprint.py:777` |
| GET | `/` | `dataexplorer_bp` | `justdata/apps/dataexplorer/blueprint.py:60` |
| GET | `/dashboard` | `dataexplorer_bp` | `justdata/apps/dataexplorer/blueprint.py:69` |
| GET | `/wizard` | `dataexplorer_bp` | `justdata/apps/dataexplorer/blueprint.py:80` |
| GET | `/api/states` | `dataexplorer_bp` | `justdata/apps/dataexplorer/blueprint.py:88` |
| GET | `/api/metros` | `dataexplorer_bp` | `justdata/apps/dataexplorer/blueprint.py:101` |
| POST | `/api/get-counties` | `dataexplorer_bp` | `justdata/apps/dataexplorer/blueprint.py:114` |
| GET | `/api/metros/<cbsa_code>/counties` | `dataexplorer_bp` | `justdata/apps/dataexplorer/blueprint.py:136` |
| POST | `/api/area/hmda/analysis` | `dataexplorer_bp` | `justdata/apps/dataexplorer/blueprint.py:149` |
| POST | `/api/area/sb/analysis` | `dataexplorer_bp` | `justdata/apps/dataexplorer/blueprint.py:162` |
| POST | `/api/area/branches/analysis` | `dataexplorer_bp` | `justdata/apps/dataexplorer/blueprint.py:175` |
| POST | `/api/lender/analysis` | `dataexplorer_bp` | `justdata/apps/dataexplorer/blueprint.py:188` |
| POST | `/api/lender/lookup` | `dataexplorer_bp` | `justdata/apps/dataexplorer/blueprint.py:201` |
| GET | `/api/lenders` | `dataexplorer_bp` | `justdata/apps/dataexplorer/blueprint.py:215` |
| POST | `/api/lender/lookup-by-lei` | `dataexplorer_bp` | `justdata/apps/dataexplorer/blueprint.py:232` |
| POST | `/api/lender/gleif-data` | `dataexplorer_bp` | `justdata/apps/dataexplorer/blueprint.py:266` |
| POST | `/api/lender/verify-gleif` | `dataexplorer_bp` | `justdata/apps/dataexplorer/blueprint.py:296` |
| POST | `/api/lender/assets` | `dataexplorer_bp` | `justdata/apps/dataexplorer/blueprint.py:334` |
| POST | `/api/clear-cache` | `dataexplorer_bp` | `justdata/apps/dataexplorer/blueprint.py:392` |
| POST | `/api/generate-area-report` | `dataexplorer_bp` | `justdata/apps/dataexplorer/blueprint.py:404` |
| POST | `/api/generate-lender-report` | `dataexplorer_bp` | `justdata/apps/dataexplorer/blueprint.py:471` |
| GET | `/progress/<job_id>` | `dataexplorer_bp` | `justdata/apps/dataexplorer/blueprint.py:556` |
| GET | `/report/<job_id>` | `dataexplorer_bp` | `justdata/apps/dataexplorer/blueprint.py:667` |
| GET | `/no-data` | `dataexplorer_bp` | `justdata/apps/dataexplorer/blueprint.py:737` |
| POST | `/api/export-area-report-excel` | `dataexplorer_bp` | `justdata/apps/dataexplorer/blueprint.py:759` |
| GET | `/health` | `dataexplorer_bp` | `justdata/apps/dataexplorer/blueprint.py:823` |
| GET | `/` | `electwatch_bp` | `justdata/apps/electwatch/blueprint.py:161` |
| GET | `/official/<official_id>` | `electwatch_bp` | `justdata/apps/electwatch/blueprint.py:180` |
| GET | `/firm/<firm_id>` | `electwatch_bp` | `justdata/apps/electwatch/blueprint.py:198` |
| GET | `/industry/<industry_code>` | `electwatch_bp` | `justdata/apps/electwatch/blueprint.py:218` |
| GET | `/committee/<committee_id>` | `electwatch_bp` | `justdata/apps/electwatch/blueprint.py:243` |
| GET | `/bill/<bill_id>` | `electwatch_bp` | `justdata/apps/electwatch/blueprint.py:261` |
| GET | `/api/officials` | `electwatch_bp` | `justdata/apps/electwatch/blueprint.py:283` |
| GET | `/api/official/<official_id>` | `electwatch_bp` | `justdata/apps/electwatch/blueprint.py:346` |
| GET | `/api/official/<official_id>/trends` | `electwatch_bp` | `justdata/apps/electwatch/blueprint.py:361` |
| GET | `/api/firm/<firm_name>` | `electwatch_bp` | `justdata/apps/electwatch/blueprint.py:424` |
| GET | `/api/firms` | `electwatch_bp` | `justdata/apps/electwatch/blueprint.py:794` |
| GET | `/api/sectors` | `electwatch_bp` | `justdata/apps/electwatch/blueprint.py:811` |
| GET | `/api/industry/<industry_code>` | `electwatch_bp` | `justdata/apps/electwatch/blueprint.py:822` |
| GET | `/api/committees` | `electwatch_bp` | `justdata/apps/electwatch/blueprint.py:1136` |
| GET | `/api/committee/<committee_id>` | `electwatch_bp` | `justdata/apps/electwatch/blueprint.py:1149` |
| GET | `/api/freshness` | `electwatch_bp` | `justdata/apps/electwatch/blueprint.py:1406` |
| GET | `/api/trends/aggregate` | `electwatch_bp` | `justdata/apps/electwatch/blueprint.py:1419` |
| GET | `/api/insights` | `electwatch_bp` | `justdata/apps/electwatch/blueprint.py:1518` |
| POST | `/api/refresh-data` | `electwatch_bp` | `justdata/apps/electwatch/blueprint.py:1531` |
| GET | `/health` | `electwatch_bp` | `justdata/apps/electwatch/blueprint.py:1575` |
| GET | `/api/bill/search` | `electwatch_bp` | `justdata/apps/electwatch/blueprint.py:1681` |
| GET | `/api/key-bills` | `electwatch_bp` | `justdata/apps/electwatch/blueprint.py:1703` |
| POST | `/api/bill/save-key-bill` | `electwatch_bp` | `justdata/apps/electwatch/blueprint.py:1718` |
| POST | `/api/bill/remove-key-bill` | `electwatch_bp` | `justdata/apps/electwatch/blueprint.py:1774` |
| GET | `/api/admin/mappings/officials` | `electwatch_bp` | `justdata/apps/electwatch/blueprint.py:1811` |
| POST | `/api/admin/mappings/officials/merge` | `electwatch_bp` | `justdata/apps/electwatch/blueprint.py:1821` |
| POST | `/api/admin/mappings/officials/unmerge` | `electwatch_bp` | `justdata/apps/electwatch/blueprint.py:1839` |
| POST | `/api/admin/mappings/officials/delete` | `electwatch_bp` | `justdata/apps/electwatch/blueprint.py:1854` |
| GET | `/api/admin/mappings/officials/potential-duplicates` | `electwatch_bp` | `justdata/apps/electwatch/blueprint.py:1868` |
| POST | `/api/admin/mappings/officials/mark-distinct` | `electwatch_bp` | `justdata/apps/electwatch/blueprint.py:2000` |
| GET | `/api/admin/mappings/firms` | `electwatch_bp` | `justdata/apps/electwatch/blueprint.py:2021` |
| GET | `/api/admin/mappings/firms/all` | `electwatch_bp` | `justdata/apps/electwatch/blueprint.py:2031` |

**Total: 343 route decorator matches across all Python files (including standalone app.py duplicates). Routes from duplicate standalone app.py files beyond line 150 are not listed here. Blueprint-only unique routes: ~190.**

---

## 5. BigQuery Query Locations

BigQuery queries exist in two forms in this codebase: **inline Python string literals** (the dominant pattern) and **standalone `.sql` files** loaded at runtime.

### Inline String Literals in Python

| File | Lines | Approximate Query Count | Notes |
|------|-------|------------------------|-------|
| `justdata/apps/analytics/bigquery_client.py` | 2,525 | ~63 `SELECT`/`.query()` matches | Dedicated BQ client for analytics app; owns all analytics queries |
| `justdata/apps/mergermeter/query_builders.py` | — | ~49 | Dedicated query builder module |
| `justdata/apps/electwatch/services/bq_client.py` | — | ~36 | ElectWatch read client |
| `justdata/apps/lenderprofile/services/bq_hmda_client.py` | — | ~34 | LenderProfile HMDA queries |
| `justdata/apps/dataexplorer/lender_analysis_core.py` | 2,083 | ~21 | Lender analysis queries inline with logic |
| `justdata/apps/branchmapper/data_utils.py` | — | ~21 | Branch/census queries inline with data utilities |
| `justdata/apps/bizsight/utils/bigquery_client.py` | — | ~24 | Dedicated BQ client for BizSight |
| `justdata/apps/dataexplorer/data_utils.py` | — | ~18 | Area analysis queries |
| `justdata/apps/lendsight/data_utils.py` | — | ~14 | LendSight data fetch queries |
| `justdata/apps/lenderprofile/services/bq_cra_client.py` | — | ~13 | CRA data queries |
| `justdata/apps/branchsight/data_utils.py` | — | ~11 | Branch data queries |
| `justdata/apps/dataexplorer/query_builders.py` | — | ~4 | Area query builder |
| `justdata/apps/mergermeter/data_utils.py` | — | ~4 | Merger data fetch queries |
| `justdata/apps/lenderprofile/services/bq_branch_client.py` | — | ~2 | Branch data |
| `justdata/apps/lenderprofile/services/bq_credit_union_branch_client.py` | — | ~2 | CU branch data |
| `justdata/shared/utils/bigquery_client.py` | — | ~3 | Shared thin wrapper |
| `justdata/apps/lenderprofile/processors/data_collector.py` | 2,034 | ~1 | Primary data collection logic |
| `justdata/apps/electwatch/services/bq_writer.py` | — | — | BQ write operations |

### Standalone .sql Files Loaded at Runtime

These files live in `sql_templates/` subdirectories and are read from disk by the app at query time using `pathlib.Path` joins (confirmed in `justdata/apps/lendsight/core.py`).

| File | Lines | App |
|------|-------|-----|
| `justdata/apps/bizsight/sql_templates/sb_county_summary_query.sql` | 40 | BizSight |
| `justdata/apps/branchmapper/sql_templates/branch_report.sql` | 57 | BranchMapper |
| `justdata/apps/branchsight/sql_templates/branch_report.sql` | 58 | BranchSight |
| `justdata/apps/lendsight/sql_templates/county_summary_query.sql` | 65 | LendSight |
| `justdata/apps/lendsight/sql_templates/mortgage_report.sql` | 110 | LendSight |
| `justdata/apps/lendsight/sql_templates/tract_summary_query.sql` | 56 | LendSight |

### Reference / Development .sql Files (Not Loaded at Runtime)

These are standalone SQL files in app roots or `scripts/` directories — used for schema setup, migrations, and ad-hoc analysis. Not loaded by the running application.

- `justdata/apps/analytics/bigquery_views.sql`
- `justdata/apps/dataexplorer/` — 9 .sql files (multiracial analysis, de_hmda table definitions, Tableau query references, test queries)
- `scripts/create_cache_tables.sql`
- `scripts/migration/` — 29 numbered migration .sql files (`03_copy_shared_tables.sql` through `29_hubspot_companies_address_geo.sql`)

---

## 6. Template Organization

### Counts (excluding node\_modules)

- **Total .html files in project directories:** 76
- **Total .jinja / .j2 files:** 0

### Directory Layout (two levels under templates/)

```
justdata/apps/analytics/templates/
└── analytics/
    ├── coalitions.html
    ├── costs.html
    ├── dashboard.html
    ├── lender_detail.html
    ├── lender_map.html
    ├── research_map.html
    ├── user_map.html
    └── users.html

justdata/apps/bizsight/templates/
    ├── analysis_template.html
    ├── bizsight_analysis.html
    ├── bizsight_report.html
    └── pdf_report_template.html

justdata/apps/branchmapper/templates/
    └── branch_mapper_template.html

justdata/apps/branchsight/templates/
    ├── branchsight_analysis.html
    ├── report_interstitial.html
    └── report_template.html

justdata/apps/dataexplorer/templates/
    ├── area_analysis_test.html
    ├── area_report_progress.html
    ├── area_report_template.html
    ├── dashboard.html
    ├── error_template.html
    ├── lender_report_template.html
    ├── no_data_template.html
    ├── report_progress.html
    └── wizard.html

justdata/apps/electwatch/templates/
    ├── association_view.html
    ├── bill_view.html
    ├── committee_list.html
    ├── committee_view.html
    ├── dashboard.html
    ├── electwatch_dashboard.html
    ├── electwatch_subnav.html
    ├── firm_view.html
    ├── industry_list.html
    ├── industry_view.html
    ├── official_profile.html
    └── pacs.html

justdata/apps/lenderprofile/templates/
    ├── index.html
    ├── report.html
    ├── report_progress.html
    └── report_v2.html

justdata/apps/lendsight/templates/
    ├── analysis_template.html
    ├── lendsight_analysis.html
    ├── lendsight_report.html
    └── pdf_report_template.html

justdata/apps/loantrends/templates/
    ├── analysis_template.html
    ├── dashboard.html
    ├── loantrends_analysis.html
    └── report_template.html

justdata/apps/memberview/web/templates/
    └── member_search.html

justdata/apps/mergermeter/templates/
    ├── analysis_template.html
    ├── goals_calculator.html
    ├── mergermeter_analysis.html
    └── mergermeter_report.html

justdata/shared/web/templates/
    ├── about.html
    ├── access_restricted.html
    ├── admin-dashboard.html
    ├── admin-users.html
    ├── analysis_template.html
    ├── base_app.html
    ├── bizsight_template.html
    ├── branchsight_template.html
    ├── contact.html
    ├── email_verified.html
    ├── justdata_landing_page.html
    ├── lendsight_template.html
    ├── member_request_modal.html
    ├── nav_menu.html
    ├── report_interstitial.html
    ├── report_template.html
    ├── shared_footer.html
    ├── shared_header.html
    ├── shared_header_js.html
    └── status-dashboard.html
```

### Template Sharing vs App-Specific

- `justdata/shared/web/templates/` contains the base layout templates (`base_app.html`, `shared_header.html`, `nav_menu.html`, `shared_footer.html`) used across all apps in the unified platform.
- Each app under `justdata/apps/*/templates/` maintains its own templates; there is no cross-app template inheritance other than extending the shared base.

### Templates Over 500 Lines

| File | Lines |
|------|-------|
| `justdata/apps/electwatch/templates/electwatch_dashboard.html` | 7,104 |
| `justdata/apps/branchmapper/templates/branch_mapper_template.html` | 4,597 |
| `justdata/apps/dataexplorer/templates/area_report_template.html` | 4,330 |
| `justdata/apps/lendsight/templates/lendsight_report.html` | 3,703 |
| `justdata/apps/bizsight/templates/bizsight_report.html` | 3,601 |
| `justdata/apps/electwatch/templates/dashboard.html` | 3,270 |
| `justdata/shared/web/templates/justdata_landing_page.html` | 3,110 |
| `justdata/apps/dataexplorer/templates/lender_report_template.html` | 2,700 |
| `justdata/apps/mergermeter/templates/mergermeter_analysis.html` | 2,549 |
| `justdata/apps/mergermeter/templates/analysis_template.html` | 2,315 |
| `justdata/apps/branchsight/templates/report_template.html` | 2,065 |
| `justdata/apps/loantrends/static_site/index.html` | 1,868 |
| `justdata/apps/electwatch/templates/official_profile.html` | 1,787 |
| `justdata/apps/dataexplorer/templates/wizard.html` | 1,714 |
| `justdata/shared/web/templates/admin-users.html` | 1,622 |
| `justdata/shared/web/templates/report_template.html` | 1,511 |
| `justdata/apps/electwatch/templates/firm_view.html` | 1,266 |
| `justdata/shared/web/templates/shared_header.html` | 1,152 |
| `justdata/apps/mergermeter/templates/mergermeter_report.html` | 1,120 |
| `justdata/apps/lendsight/templates/analysis_template.html` | 1,106 |
| `justdata/apps/lendsight/templates/lendsight_analysis.html` | 1,049 |
| `justdata/apps/electwatch/templates/committee_view.html` | 1,037 |
| `justdata/apps/loantrends/templates/report_template.html` | 1,035 |
| `justdata/apps/electwatch/templates/industry_view.html` | 964 |
| `justdata/shared/web/templates/status-dashboard.html` | 939 |
| `justdata/apps/electwatch/templates/bill_view.html` | 937 |
| `justdata/apps/bizsight/templates/analysis_template.html` | 895 |
| `justdata/apps/analytics/templates/analytics/costs.html` | 875 |

28 templates exceed 500 lines. 13 of those exceed 1,000 lines. 3 exceed 3,000 lines.

---

## 7. Static Assets and Front-End JS

### Directory Layout (two levels under static/)

**Shared (`justdata/shared/web/static/`):**
```
css/
    style.css (2,722 lines)
img/
    app-logos/
js/
    analytics-events.js
    app.js (1,519 lines)
    auth.js (740 lines)
    population_demographics.js
    components/
        GoalsCalculator.js (766 lines)
```

**Per-app static directories** (each app under `justdata/apps/<app>/static/`):

| App | Subdirs Present |
|-----|----------------|
| analytics | css/, demo\_data/, js/ |
| bizsight | css/, img/, js/ |
| branchmapper | img/ (no js/) |
| branchsight | img/ (no js/) |
| dataexplorer | css/, data/, img/, js/ |
| electwatch | css/, img/, js/ |
| lenderprofile | css/, img/, js/ |
| lendsight | css/, img/, js/ |
| loantrends | css/, img/, js/ |
| memberview | img/ (main), web/static/css/, web/static/js/ |
| mergermeter | img/, js/, js/components/ |

### JS/TS Files Over 300 Lines

| File | Lines |
|------|-------|
| `justdata/apps/dataexplorer/static/js/wizard-steps.js` | 4,188 |
| `justdata/apps/lenderprofile/static/js/report_v2.js` | 2,690 |
| `justdata/shared/web/static/js/app.js` | 1,519 |
| `justdata/apps/lendsight/static/js/app.js` | 1,500 |
| `justdata/apps/lenderprofile/static/js/report-renderer.js` | 1,402 |
| `justdata/apps/bizsight/static/js/app.js` | 1,255 |
| `justdata/apps/analytics/static/js/analytics-lender.js` | 937 |
| `justdata/apps/analytics/static/js/analytics-dashboard.js` | 918 |
| `justdata/apps/analytics/static/js/analytics-coalitions.js` | 864 |
| `justdata/apps/analytics/static/js/analytics-users.js` | 844 |
| `justdata/apps/analytics/static/js/analytics-maps.js` | 826 |
| `justdata/apps/electwatch/static/js/electwatch-sponsors.js` | 789 |
| `justdata/shared/web/static/js/components/GoalsCalculator.js` | 766 |
| `justdata/apps/dataexplorer/static/js/wizard.js` | 746 |
| `justdata/shared/web/static/js/auth.js` | 740 |
| `justdata/apps/memberview/web/static/js/member_search.js` | 634 |
| `justdata/apps/analytics/static/js/analytics-user-map.js` | 508 |
| `justdata/apps/lenderprofile/static/js/app.js` | 481 |
| `justdata/apps/mergermeter/static/js/components/GoalsCalculator.js` | 443 |

19 JS files exceed 300 lines. No TypeScript files (`.ts`, `.tsx`) are present.

### Build Tooling

- **Root `package.json`**: Present. `devDependencies`: `@hubspot/cli ^7.7.0` only. Scripts are HubSpot CMS CLI wrappers (`hs`, `hs:project:create`, etc.).
- **`justdata/app/package.json`** and **`justdata/app/src/app.functions/package.json`**: Present. Part of a HubSpot CMS project under `justdata/app/`.
- **webpack, vite, esbuild, rollup**: Not present.
- All JS served as plain static files. No front-end build pipeline.

---

## 8. Configuration and Entry Points

### Entry Point Files

| File | Role |
|------|------|
| `justdata/main/app.py` | Unified platform Flask app; registers all sub-app blueprints |
| `run_justdata.py` | Top-level run script; starts unified platform on port 8000 |
| `justdata/apps/analytics/run.py` | Standalone gunicorn entry (`application`) |
| `justdata/apps/bizsight/run.py` | Standalone gunicorn entry |
| `justdata/apps/branchmapper/run.py` | Standalone gunicorn entry |
| `justdata/apps/branchsight/run.py` | Standalone gunicorn entry |
| `justdata/apps/dataexplorer/run.py` | Standalone gunicorn entry |
| `justdata/apps/electwatch/run.py` | Standalone gunicorn entry |
| `justdata/apps/lenderprofile/run.py` | Standalone gunicorn entry |
| `justdata/apps/lendsight/run.py` | Standalone gunicorn entry |
| `justdata/apps/loantrends/run.py` | Standalone gunicorn entry |
| `justdata/apps/mergermeter/run.py` | Standalone gunicorn entry |
| `scripts/slack_bot/app.py` | Slack bot Flask app |
| `scripts/sync/main.py` | Data sync script entry point |

### Config Files

| File | Scope |
|------|-------|
| `justdata/main/config.py` | Unified platform config |
| `justdata/shared/core/config.py` | Shared core config |
| `justdata/apps/analytics/config.py` | Analytics app config |
| `justdata/apps/bizsight/config.py` | BizSight config |
| `justdata/apps/branchmapper/config.py` | BranchMapper config |
| `justdata/apps/branchsight/config.py` | BranchSight config |
| `justdata/apps/dataexplorer/config.py` | DataExplorer config |
| `justdata/apps/electwatch/config.py` | ElectWatch config |
| `justdata/apps/lenderprofile/config.py` | LenderProfile config |
| `justdata/apps/lendsight/config.py` | LendSight config |
| `justdata/apps/loantrends/config.py` | LoanTrends config |
| `justdata/apps/memberview/config.py` | MemberView config |
| `justdata/apps/mergermeter/config.py` | MergerMeter config |
| `pyproject.toml` | Python project metadata, dependencies, pytest config |

`.env.example`: Not present in repo.

### CI/CD Workflows

| File | Trigger Event |
|------|--------------|
| `.github/workflows/ci.yml` | `pull_request` on branches: `test`, `staging`, `main` |
| `.github/workflows/deploy-cloudrun.yml` | `push` on branches: `main`, `staging`; also `workflow_dispatch` |
| `.github/workflows/deploy-electwatch-job.yml` | `push` on branch: `main`, path filter: `justdata/apps/electwatch/**` |
| `.github/workflows/deploy-slack-bot.yml` | `push` on branch: `main`, path filter: `scripts/slack_bot/**` |

### Deployment Config

| File | Present |
|------|---------|
| `Dockerfile` | Yes |
| `Dockerfile.app` | Yes |
| `Dockerfile.electwatch-job` | Yes |
| `Dockerfile.hubspot-sync-job` | Yes |
| `docker-compose.yml` | Yes |
| `cloudbuild.yaml` | Yes |
| `Procfile` | No |

---

## 9. Tests

### Test Directory Locations

- `./tests/` — primary test tree (26 Python files)
- `./justdata/tests/` — contains only `__init__.py`; no test files

### Test File List (`./tests/`)

```
tests/
├── __init__.py
├── conftest.py
├── test_full_stack.py
├── apps/
│   ├── __init__.py
│   ├── dataexplorer/
│   │   ├── __init__.py
│   │   ├── connecticut_normalization_standalone.py
│   │   ├── ct_geo_census_standalone.py
│   │   ├── ct_tract_format_standalone.py
│   │   ├── ct_tract_to_county_standalone.py
│   │   ├── test_aggregated_query.py
│   │   ├── test_mortgage_template.py
│   │   └── test_simple_count.py
│   ├── electwatch/
│   │   ├── __init__.py
│   │   ├── test_data_sources.py
│   │   └── test_officials.py
│   ├── lenderprofile/
│   │   ├── __init__.py
│   │   ├── test_all_apis.py
│   │   ├── test_fdic_branches.py
│   │   ├── test_fifth_third_cached.py
│   │   └── test_fitb.py
│   └── memberview/
│       ├── __init__.py
│       ├── propublica_simple_standalone.py
│       ├── test_api.py
│       └── test_propublica_matching.py
└── core/
    └── __init__.py
└── shared/
    └── __init__.py
```

**Total .py files in `./tests/`:** 26

### Test Framework

pytest, confirmed by:
- `pyproject.toml` `[tool.pytest.ini_options]` block specifying `testpaths = ["tests"]`, `python_files`, `python_classes`, `python_functions`, and `markers`
- CI workflow uses Python 3.11

### Coverage Config

`pytest-cov` is listed in `pyproject.toml` optional dependencies under `[project.optional-dependencies] dev`. No `.coveragerc` file found; coverage settings are not explicitly configured in `pyproject.toml` beyond the dependency declaration.

---

## 10. Dependency Surface

### `requirements.txt`

```
# Core web framework
flask>=2.3.0
Werkzeug>=2.3.0
gunicorn>=21.2.0
python-dotenv
requests

# Data processing
pandas>=1.5.0
numpy>=1.23.0
scipy>=1.9.0

# Google Cloud / BigQuery
google-cloud-bigquery>=3.0.0
google-cloud-storage>=2.0.0
db-dtypes>=1.0.0
google-auth>=2.0.0
google-auth-oauthlib>=1.0.0
google-auth-httplib2>=0.1.0

# Reporting / Excel / PDF
openpyxl>=3.0.0
reportlab>=3.6.0
Pillow>=10.0.0
matplotlib>=3.5.0
seaborn>=0.11.0

# AI
anthropic>=0.7.0
openai>=1.0.0

# PDF Generation (BizSight)
playwright>=1.40.0

# Census
census>=0.8.0
us>=3.0.0

# LenderProfile
beautifulsoup4>=4.12.0
lxml>=4.9.0

# Firebase Authentication
firebase-admin>=6.0.0

# ElectWatch
PyYAML>=6.0
python-dateutil>=2.8.0

# HTTP client
httpx>=0.27.0

# Misc
user-agents>=2.2.0
pydantic>=2.5.0

# Testing
pytest>=7.4.0
pytest-asyncio
pytest-cov
```

`pyproject.toml` additionally declares optional dev dependencies: `pytest-cov>=4.1.0`, `black>=23.9.0`, `isort>=5.12.0`, `ruff>=0.9.0`, `mypy>=1.6.0`, `pre-commit>=3.5.0`, `factory-boy>=3.3.0`, `faker>=20.1.0`. `pyproject.toml` classifiers list Python 3.9, 3.10, 3.11, 3.12 as supported.

### `package.json` (root)

```json
{
  "devDependencies": {
    "@hubspot/cli": "^7.7.0"
  }
}
```

No `dependencies` section. The `package.json` under `justdata/app/` is a separate HubSpot CMS project.

### Python Version Pin

- **Dockerfiles** (`Dockerfile`, `Dockerfile.app`, `Dockerfile.electwatch-job`): `FROM python:3.11-slim`
- **CI workflow** (`.github/workflows/ci.yml`): `python-version: "3.11"`
- `pyproject.toml` does not specify `python_requires`.

---

## 11. Observations

- `justdata/apps/mergermeter/app.py` is 4,035 lines with 11 direct `@app.route` decorators. The file contains significant inline business logic beyond routing.

- `justdata/apps/electwatch/blueprint.py` is 2,159 lines and contains 41 route decorators — the largest single blueprint by route count. Route handlers contain substantial inline data processing code rather than delegating to service modules.

- `justdata/main/auth.py` is 2,125 lines and contains 17 route decorators. The file handles Firebase authentication, user management, organization association, membership status, and BigQuery analytics sync logic in a single module.

- Every app has two parallel route surfaces: a `blueprint.py` (used by the unified platform) and an `app.py` (standalone Flask instance with direct `@app.route` decorators). The `rg` route scan returns 343 total matches; approximately half are duplicates between these two surfaces.

- `justdata/apps/dataexplorer/app.py` is 1,863 lines and contains 32 direct `@app.route` decorators. Its blueprint counterpart (`blueprint.py`) defines 25 routes. The two files define overlapping but not identical route sets.

- BigQuery queries are stored predominantly as inline Python string literals. Only 4 apps (BizSight, BranchMapper, BranchSight, LendSight) use separate `.sql` files in `sql_templates/` directories. The remaining apps embed SQL directly in `data_utils.py`, `query_builders.py`, `bq_client.py`, or analysis modules.

- `justdata/apps/analytics/bigquery_client.py` is 2,525 lines and is a self-contained BigQuery client for the analytics app. It has no dependency on `justdata/shared/utils/bigquery_client.py`. BizSight, ElectWatch, and LenderProfile also maintain their own separate BigQuery client modules.

- `justdata/shared/utils/bigquery_client.py` exists as a shared client but is a thin wrapper; the majority of BigQuery client code is not consolidated through it.

- 28 HTML templates exceed 500 lines. 13 exceed 1,000 lines. 3 exceed 3,000 lines (`electwatch_dashboard.html` at 7,104, `branch_mapper_template.html` at 4,597, `area_report_template.html` at 4,330).

- 19 JS files exceed 300 lines. The two largest are `wizard-steps.js` (4,188 lines) and `report_v2.js` (2,690 lines). All JS is served as plain static files with no build tooling.

- `justdata/apps/electwatch/weekly_update.py` is 3,404 lines and contains the full weekly data pipeline (API fetches, BigQuery writes, AI insight generation) in a single file.

- `justdata/apps/lendsight/mortgage_report_builder.py` is 3,315 lines and contains report assembly logic for the LendSight app.

- `justdata/apps/dataexplorer/area_report_builder.py` is 2,550 lines and contains area report assembly logic.

- `justdata/apps/lenderprofile/report_builder/section_builders_v2.py` is 2,348 lines. LenderProfile is the only app with a dedicated `report_builder/` subdirectory.

- Tests exist only for `dataexplorer`, `electwatch`, `lenderprofile`, and `memberview`. There are no test files for `bizsight`, `branchmapper`, `branchsight`, `lendsight`, `loantrends`, `mergermeter`, `analytics`, or the shared modules.

- The `GoalsCalculator.js` component exists in two separate locations: `justdata/shared/web/static/js/components/GoalsCalculator.js` (766 lines) and `justdata/apps/mergermeter/static/js/components/GoalsCalculator.js` (443 lines).

- `node_modules/` is present in the repo root (HubSpot CLI dependency) and is checked into git or present locally. It contains 109 `.html` files that appear in any unfiltered file searches.
