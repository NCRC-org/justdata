# BranchSight

FDIC bank branch analysis. Counts branches by geography, computes
demographic exposure of each bank's network, and produces an AI-narrated
web report plus PDF/Excel exports.

## Blueprint

- URL prefix: `/branchsight`
- File: `blueprint.py` (`branchsight_bp`) — 12 routes
- Standard route shape: `/`, `/analyze`, `/progress/<job_id>`,
  `/report`, `/report-data`, `/download`, `/health`.
- `/report?job_id=` renders the same page as `/`; the page loads that job's
  results into its results column (spec 04 standard).
- `/geography-context/<geoid5>`: Census ACS tract context for the report
  (`data_utils.tract_context`; the Census API needs `CENSUS_API_KEY`).

## Data sources

- BigQuery: `justdata-ncrc.branchsight` (FDIC Summary of Deposits):
  `sod` for the latest year, `sod_legacy` for earlier years. The years run
  are `config.SOD_YEARS` (2021 to 2025).
- Crosswalks: `justdata-ncrc.shared.cbsa_to_county`
- SQL templates: `sql_templates/`

## Reports

Report assembly is split across the top-level modules:
- `core.run_analysis` — orchestrates the run
- `analysis.py` — AI narrative
- `pdf_report.py` + `pdf_charts.py` — PDF export

(BranchSight predates the `report_builder/` package pattern used by
LendSight/DataExplorer/LenderProfile.)

## Templates and scripts

`templates/branchsight_analysis.html` extends the shared `app_page.html`.
`templates/partials/`: `branchsight_controls.html`,
`branchsight_report_template.html` (the report body),
`branchsight_methods.html` and `branchsight_narrative.html`.

Scripts are in `justdata/shared/web/static/js/branchsight/`: `br_page.js`
(controls and run, on the shared AppRun) and `br_report.js` (report body, on
AppReport). Styles: `shared/web/static/css/branchsight.css`.

## Notes

- `census_tract_utils.py` is not used by the BranchSight report.
- Legacy `app.py` and `run.py` exist for the standalone-app workflow but
  the unified platform mounts the blueprint directly.
