# BranchSight

FDIC bank branch analysis. Counts branches by geography, computes
demographic exposure of each bank's network, and produces an AI-narrated
web report plus PDF/Excel exports.

## Blueprint

- URL prefix: `/branchsight`
- File: `blueprint.py` (`branchsight_bp`) — 11 routes
- Standard route shape: `/`, `/analyze`, `/progress/<job_id>`,
  `/report`, `/report-data`, `/download`, `/health`.

## Data sources

- BigQuery: `justdata-ncrc.branchsight` (FDIC Summary of Deposits)
- Crosswalks: `justdata-ncrc.shared.cbsa_to_county`
- SQL templates: `sql_templates/`

## Reports

Report assembly is split across the top-level modules:
- `core.run_analysis` — orchestrates the run
- `analysis.py` — AI narrative
- `pdf_report.py` + `pdf_charts.py` — PDF export

(BranchSight predates the `report_builder/` package pattern used by
LendSight/DataExplorer/LenderProfile.)

## Templates

`templates/`:
- `branchsight_analysis.html`, `report_template.html`,
  `report_interstitial.html`
- `partials/` — `_branchsight_report_head.html`,
  `_branchsight_report_main.html`, `_branchsight_report_scripts.html`

## Notes

- `census_tract_utils.py` provides demographic enrichment of branch
  locations.
- Legacy `app.py` and `run.py` exist for the standalone-app workflow but
  the unified platform mounts the blueprint directly.
