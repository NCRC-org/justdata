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
- `/report?job_id=` renders the same page as `/` and loads that run's
  workbook (spec 04 standard). The Goals Calculator is at
  `/goals-calculator?job_id=`.
- `/report-data` is a readiness check: the run's metadata and stage
  timings once its workbook exists (local or GCS), 202 while it runs.
  `/excel-data` serves the workbook for the page's preview; `/download`
  serves it as a file.

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

`templates/mergermeter_analysis.html` extends the shared `app_page.html`.
`templates/partials/`: `mergermeter_controls.html` (1 Geography / assessment
areas, 2 Acquirer and target, 3 Years, 4 Options) and
`mergermeter_report_template.html` (the workbook preview).
`goals_calculator.html` is the Goals Calculator page.

Scripts are in `justdata/shared/web/static/js/mergermeter/`: `mm_banks.js`
(bank search), `mm_areas.js` (assessment areas), `mm_page.js` (validation,
the form posted to `/analyze`, AppRun) and `mm_report.js` (SheetJS workbook
preview). Styles: `shared/web/static/css/mergermeter.css`.

The page posts exactly the form fields the former page did, so the
analysis, its cache key and the workbook are unchanged by the page.
`mergermeter_ops.py` still defines a standalone Flask app; it is not
served anywhere.

## Notes

- `parse_pnc_pdf.py`/`debug_pnc_pdf.py` are utilities for ingesting
  paper-style filings.
- `output_validator.py` runs sanity checks on the generated workbook
  before returning it to the user.
