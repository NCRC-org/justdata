# LendSight

HMDA mortgage lending analysis. Generates county- and tract-level reports
covering income, demographic, and minority-tract lending patterns, with AI
narrative, web report, and PDF/Excel exports.

## Blueprint

- URL prefix: `/lendsight`
- File: `blueprint.py` (`lendsight_bp`)
- Standard route shape: `/`, `/analyze`, `/progress/<job_id>`,
  `/report`, `/report-data`, `/download`, `/health`.

## Data sources

- BigQuery (`config.DATASET_ID = "hmda"`):
  - `justdata-ncrc.lendsight.de_hmda_county_summary`
  - `justdata-ncrc.lendsight.de_hmda_tract_summary`
  - `justdata-ncrc.dataexplorer.de_hmda` (loan-level for the report query)
- HUD income limits via `hud_processor.py`; national benchmarks in
  `national_benchmarks.py`.
- SQL templates: `sql_templates/`.

## Reports

`report_builder/` package — the canonical example of the pattern:
- `coordinator.py` — assembles sections
- `queries.py`, `formatting.py`
- `sections/` — `concentration.py`, `demographics.py`, `income_borrowers.py`,
  `income_indicators.py`, `income_tracts.py`, `minority_tracts.py`,
  `summaries.py`, `top_lenders.py`
- `excel_export/` — multi-sheet Excel generation

`pdf_report.py` + `pdf_charts.py` build the PDF; `analysis.py` produces
the AI narrative.

## Templates

`templates/`:
- `lendsight_analysis.html`, `lendsight_report.html`,
  `analysis_template.html`, `pdf_report_template.html`
- `partials/` — `_lendsight_analysis_*.html` and report fragments
