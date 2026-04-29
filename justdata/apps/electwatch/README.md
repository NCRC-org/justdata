# ElectWatch

Tracks congressional financial activity: PAC contributions, individual
contributions, STOCK Act trade disclosures, and AI-generated pattern
insights. Powers the public ElectWatch site.

## Blueprint

- URL prefix: `/electwatch`
- File: `blueprint.py` (`electwatch_bp`)
- Routes for officials, firms, industries, committees, bills, and search,
  plus admin/analysis endpoints. Service modules in `services/` back
  most routes.

## Data sources

BigQuery dataset: `justdata-ncrc.electwatch` (`config.DATASET_ID = 'electwatch'`).
Tables: `officials`, `official_trades`, `official_pac_contributions`,
`official_individual_contributions`, `firms`, `industries`, `committees`,
`insights`, `trend_snapshots`, `summaries`, `metadata`.

Upstream APIs: FEC OpenFEC, FMP, Quiver, Congress.gov, Finnhub, SEC,
News API, Claude (insights).

## Pipeline

The weekly refresh runs as a Cloud Run Job (`electwatch-weekly-update`,
Sundays 5:00 AM EST). Code lives in `pipeline/`:

- `pipeline/coordinator.py` — `WeeklyDataUpdate` entry point
- `pipeline/fetchers/` — one file per source API
- `pipeline/transformers/` — per-source normalizers
  (`electwatch_transform_congress.py`, `_donors.py`, `_firms.py`,
  `_industries.py`, `_committees.py`, `_scores.py`)
- `pipeline/loaders/bigquery.py` — BQ writes
- `pipeline/insights.py` — AI insights step

Manual trigger: `python -c "from dotenv import load_dotenv; load_dotenv(); from justdata.apps.electwatch.weekly_update import WeeklyDataUpdate; WeeklyDataUpdate().run()"`.

## Templates

`templates/` includes `electwatch_dashboard.html`, `committee_view.html`,
`bill_view.html`, `association_view.html`, etc., with per-page
`partials/` (e.g., `_electwatch_head.html`, `_committee_main.html`).
