# BizSight

Small business lending analysis from FFIEC CRA small business disclosure data
(not Section 1071, which is not yet in force). Generates county-level
analyses with AI narrative, web report, and PDF/Excel exports.

## Blueprint

- URL prefix: `/bizsight`
- File: `blueprint.py` (`bizsight_bp`)
- Standard route shape: `/`, `/analyze`, `/progress/<job_id>`,
  `/report`, `/report-data`, `/download`, `/health`.

## Data sources

- BigQuery dataset: `justdata-ncrc.bizsight` (config: `DATASET_ID = 'sb'`
  for legacy refs)
- Primary table: `bizsight.sb_county_summary`
- SQL templates: `sql_templates/`

## Reports

`report_builder.py` (single module, not a package) builds the
multi-section report. Excel export via `excel_export.py`; PDF via
`pdf_report.py` and `pdf_charts.py`. AI narrative via
`ai_analysis.py`.

## Templates

`templates/` (spec 04 standard, see `shared/web/templates/app_page.html`):
- `bizsight_analysis.html` — extends `app_page.html`; rendered by `/` and by
  `/report?job_id=` (the shareable report URL), which loads that job's results
  into the results column
- `partials/bizsight_controls.html` — steps 1 Geography, 2 Years, 3 Options (staff)
- `partials/bizsight_report_template.html`, `bizsight_methods.html`,
  `bizsight_narrative.html` — the report body, cloned into the results column
- `pdf_report_template.html`

Page scripts live in `shared/web/static/js/bizsight/` (`bs_page.js`,
`bs_report.js`) on the shared AppRun and AppReport modules, and styles in
`shared/web/static/css/bizsight.css`.

## Notes

- Analysis years: `config.SB_YEARS` (2020 to 2024; ticket 13229487819).
- Benchmarks regenerated via `generate_benchmarks.py`.
