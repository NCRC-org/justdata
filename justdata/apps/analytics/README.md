# Analytics

Internal staff dashboard for JustData usage patterns, research activity maps,
and coalition-building opportunities. Admin/staff only.

## Blueprint

- URL prefix: `/analytics`
- File: `blueprint.py` (`analytics_bp`)
- Routes include: `/`, `/user-map`, `/research-map`, `/lender-map`,
  `/coalitions`, `/users`, `/costs`, plus `/api/...` JSON endpoints.

## Data sources

Reads from BigQuery and the Cloud Logging-backed cost data:

- `justdata-ncrc.firebase_analytics.*` (Firebase Analytics export — see
  `config.ANALYTICS_DATASET = 'firebase_analytics'`)
- `justdata-ncrc.cache.usage_log` — JustData usage events
- `INFORMATION_SCHEMA.JOBS_BY_PROJECT` — BigQuery cost summary

SQL templates live in `sql_templates/` and are loaded via `sql_loader.py`.
The BigQuery accessors are in `bq/` (called by `blueprint.py`).

## Reports

No long-form report builder. Endpoints return JSON for Mapbox/Chart.js
front-ends; CSV/Excel exports are generated inline in route handlers.

## Templates

Located in `templates/analytics/`. No `partials/` directory — page
templates are self-contained.

## Notes

- Mapbox config comes from `MAPBOX_ACCESS_TOKEN` and `MAPBOX_STYLE` env vars.
- `backfill_analytics.py` and `process_gazetteer.py` are one-off scripts
  used during initial data load.
