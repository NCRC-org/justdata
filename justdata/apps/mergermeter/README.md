# MergerMeter

Two-bank merger impact analyzer. Compares an acquiring and target bank's
HMDA mortgage lending, Section 1071 small business lending, branch
networks, and assessment-area overlap. Produces a multi-tab Excel
goal-setting report.

## Blueprint

- URL prefix: `/mergermeter`
- File: `blueprint.py` (`mergermeter_bp`)
- Standard route shape: `/`, `/analyze`, `/progress/<job_id>`,
  `/report`, `/report-data`, `/download`, `/health`, plus the
  goals-calculator page.

## Data sources

BigQuery (`justdata-ncrc.*`):
- `branchsight.sod` — FDIC Summary of Deposits
- `shared.de_hmda` — denormalized HMDA
- `bizsight.sb_county_summary` — Section 1071
- `shared.cbsa_to_county` — geography crosswalk

SQL templates in `sql_templates/`. `query_builders.py` and
`sql_loader.py` compose the queries; `branch_assessment_area_generator.py`
derives assessment areas from a bank's branch footprint.

## Reports

No `report_builder/` package — the report is an Excel workbook built by
the `excel/` package and post-processed by `excel_postprocessor.py`.
`hhi_calculator.py` and `statistical_analysis.py` provide market-
concentration math.

## Templates

`templates/`:
- `mergermeter_analysis.html`, `mergermeter_report.html`,
  `analysis_template.html`, `goals_calculator.html`
- `partials/` — `_analysis_head.html`, `_analysis_main.html`,
  `_analysis_scripts.html`, `_analysis_scripts_footer.html`,
  `_analysis_template_footer.html`, etc.

## Notes

- `parse_pnc_pdf.py`/`debug_pnc_pdf.py` are utilities for ingesting
  paper-style filings.
- `output_validator.py` runs sanity checks on the generated workbook
  before returning it to the user.
