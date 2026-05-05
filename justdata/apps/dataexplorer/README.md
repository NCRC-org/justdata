# DataExplorer

Interactive dashboard over HMDA mortgage, Section 1071 small business,
and FDIC branch data. Two analysis modes: area analysis (lending by
geography) and lender targeting (lender + peer comparison).

## Blueprint

- URL prefix: `/dataexplorer`
- File: `blueprint.py` (`dataexplorer_bp`)
- Routes cover the dashboard, area-analysis flows (HMDA, SB, branches),
  lender analysis, and async progress/result endpoints.

## Data sources

`config.py` defines:
- `HMDA_DATASET = "dataexplorer"` — `justdata-ncrc.dataexplorer.de_hmda`
- `SB_DATASET = "bizsight"` — `justdata-ncrc.bizsight.*`
- `BRANCHES_DATASET = "branchsight"` — `justdata-ncrc.branchsight.*`

Crosswalk: `justdata-ncrc.shared.de_hmda` (denormalized HMDA),
`shared.cbsa_to_county`. SQL templates in `sql_templates/`.

## Reports

`report_builder/` package:
- `coordinator.py` — primary orchestrator
- `coordinator_all_lenders.py` — all-lenders variant
- `queries.py`, `formatting.py`, `sections/`, `excel_export/`

Top-level helpers:
- `area_analysis_processor.py`, `lender_analysis_processor.py`,
  `lender_report_builder.py`, `lender_analysis/` (package).

## Templates

`templates/`:
- `dashboard.html`, `area_analysis_test.html`,
  `area_report_template.html`, `area_report_progress.html`,
  `error_template.html`
- `partials/` — `_dataexplorer_head.html`, `_dataexplorer_scripts*.html`,
  `_export_controls.html`, `_lender_report_head.html`, etc.

## Notes

- `lender_analysis/core.py` is the largest single module in the codebase
  (~1.5k lines, allowlisted in CI as orchestrator-bound).
- Connecticut-specific helpers: `connecticut_census_normalizer.py`,
  `connecticut_mapper.py`.
