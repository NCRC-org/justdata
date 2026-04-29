# LenderProfile

Long-form lender intelligence reports combining corporate structure,
financials, regulatory history, branch network, CRA performance,
litigation, and news coverage.

## Blueprint

- URL prefix: `/lenderprofile`
- File: `blueprint.py` (`lenderprofile_bp`)
- Routes cover the lender search, async report generation, and report
  rendering (`report_v2.html`).

## Data sources

BigQuery:
- `justdata-ncrc.hmda.hmda` — HMDA loan-level data
- `justdata-ncrc.lenderprofile.cu_branches`, `cu_call_reports` — credit
  unions
- `justdata-ncrc.shared.lender_names_gleif`, `cbsa_to_county`
- `justdata-ncrc.lendsight.lenders18`

External APIs: FDIC (Financial Data, OSCR History), SEC EDGAR, GLEIF,
CourtListener, NewsAPI, TheOrg, Candid, Claude. API clients in
`services/`; identifier resolution in `processors/identifier_resolver.py`;
data collection in `processors/collector/`.

## Reports

`report_builder/` package:
- `coordinator.py` — section orchestration
- `helpers.py` — shared report helpers
- `sections/` — per-section builders

`report_builder.py` (top-level module) and `report_generator.py` are
legacy entry points retained for current callers.

## Templates

`templates/`:
- `index.html` (search/landing)
- `report_v2.html` (the rendered report)
- `report_progress.html` (async progress)

No `partials/` directory at present.

## Notes

- Upstream API keys come from environment variables.
