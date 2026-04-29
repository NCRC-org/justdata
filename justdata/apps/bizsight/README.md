# BizSight

Small Business (Section 1071) lending analysis. Generates county-level
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

`templates/`:
- `bizsight_analysis.html`, `bizsight_report.html`,
  `analysis_template.html`, `pdf_report_template.html`
- `partials/` — `_bizsight_report_head.html`, `_bizsight_report_main.html`,
  `_bizsight_report_scripts.html`, `_bizsight_report_scripts_footer.html`

## Notes

- Static assets under `static/`, served at `/bizsight/static`.
- Benchmarks regenerated via `generate_benchmarks.py`.
