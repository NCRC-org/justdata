# Architecture

This document describes the structure of the JustData codebase as of the
post-refactor state on `staging`. It is intended to give new contributors
(human or agent) enough context to navigate the repo without reading every
file. Per-app details live in each app's `README.md`.

## 1. Platform overview

JustData is NCRC's internal Flask + BigQuery application suite. It bundles
several sub-apps (BranchSight, LendSight, BizSight, MergerMeter, BranchMapper,
DataExplorer, LenderProfile, LoanTrends, ElectWatch, MemberView, Analytics)
behind a single unified entry point.

- **Process model:** one Flask app (`justdata/main/app.py`) registers each
  sub-app as a Flask Blueprint under its own URL prefix. There is no
  per-app web server in production — only the unified app.
- **Data plane:** most apps query BigQuery directly via a shared client.
  External APIs (FEC, Congress.gov, FDIC OSCR, CFPB Quarterly) are used by
  specific apps.
- **AI:** narrative generation routes through `justdata/shared/analysis/ai_provider.py`,
  which wraps Claude (default) and OpenAI.
- **Deploys:** GitHub Actions builds and deploys to Cloud Run in GCP project
  `justdata-ncrc`, region `us-east1`.
  - `staging` branch → `justdata-test` service
  - `main` branch → `justdata` service
- **Branching:** feature/fix/refactor/chore branches → `staging` (1 approval) →
  `main` (2 approvals).

## 2. Directory structure

```
justdata/
├── main/             Unified platform: app factory, blueprint registration, auth
├── apps/             Per-app blueprints (one directory per sub-app)
├── shared/           Cross-app utilities, analysis, reporting, web templates, JS
├── core/             Core config (currently just app_config.py for legacy callers)
└── deployment/       Reserved for deploy-related modules (currently empty)
audit/                Pre-refactor structural audit documents
tests/                pytest suite (apps/, shared/, core/, full-stack)
scripts/              Manual deploy and maintenance scripts
docs/                 Reference docs (Candid API, executive user type, etc.)
.github/workflows/    CI and deploy workflows
```

Top-level files of note: `Dockerfile`, `Dockerfile.app`,
`Dockerfile.electwatch-job`, `Dockerfile.hubspot-sync-job`, `Makefile`,
`requirements.txt`, `CLAUDE.md`.

## 3. The blueprint pattern

Every sub-app under `justdata/apps/` follows the same shape:

```
justdata/apps/<app>/
├── blueprint.py          Flask Blueprint and all routes for the app
├── config.py             App-specific config (paths, BigQuery dataset IDs)
├── version.py            __version__ string
├── templates/            Jinja2 templates; reusable fragments in templates/partials/
├── static/               CSS, JS, images served under the app's URL prefix
├── sql_templates/        .sql files loaded at runtime (where applicable)
├── core.py / data_utils.py / analysis.py   Business logic and BQ access
└── (per-concern packages, e.g. report_builder/, services/, processors/)
```

Blueprint registration happens in `justdata/main/app.py::register_blueprints`,
which mounts each blueprint at its URL prefix:

| App           | URL prefix        |
|---------------|-------------------|
| branchsight   | `/branchsight`    |
| bizsight      | `/bizsight`       |
| lendsight     | `/lendsight`      |
| mergermeter   | `/mergermeter`    |
| branchmapper  | `/branchmapper`   |
| dataexplorer  | `/dataexplorer`   |
| lenderprofile | `/lenderprofile`  |
| loantrends    | `/loantrends`     |
| memberview    | `/memberview`     |
| electwatch    | `/electwatch`     |
| analytics     | `/analytics`      |

Each blueprint uses `record_once` to install a `ChoiceLoader` so its own
templates resolve before shared ones.

## 4. The report builder pattern

Three apps build long-form reports through a `report_builder/` package that
isolates section-by-section logic from the route handlers:

- `justdata/apps/lendsight/report_builder/`
- `justdata/apps/dataexplorer/report_builder/`
- `justdata/apps/lenderprofile/report_builder/`

Common shape:

```
report_builder/
├── __init__.py        Public API (build functions imported by blueprint.py)
├── coordinator.py     Orchestrates section assembly
├── sections/          One file per report section (lendsight only — others
│                      use a flatter layout with helpers.py / queries.py)
├── queries.py         Shared SQL helpers for the report
└── formatting.py      Number/string formatting helpers
```

`dataexplorer` additionally has `coordinator_all_lenders.py` for the
all-lenders variant. `lenderprofile` keeps a top-level `report_builder.py`
alongside the package for legacy entry points.

## 5. The pipeline pattern

ElectWatch is the only app with a batch pipeline. It runs as a Cloud Run
Job triggered by Cloud Scheduler weekly. The package layout under
`justdata/apps/electwatch/pipeline/` is:

```
pipeline/
├── coordinator.py             WeeklyDataUpdate class — entry point for the job
├── insights.py                AI insights generation step
├── fetchers/                  One file per external API (FEC, Congress.gov,
│                              Finnhub, FMP, Quiver, SEC, news)
├── transformers/              Per-source normalizers
│                              (electwatch_transform_congress.py,
│                              electwatch_transform_donors.py,
│                              electwatch_transform_firms.py, etc.)
└── loaders/
    └── bigquery.py            BigQuery write operations
```

Trigger: `python -m justdata.apps.electwatch.weekly_update` (or via
`scripts/deploy-electwatch-job.sh`).

## 6. Shared infrastructure

**BigQuery client** — `justdata/shared/utils/bigquery_client.py`. Use
`get_bigquery_client(project_id, app_name)` everywhere that needs BQ
access. Per-app service accounts are wired up in Cloud Run; locally,
credentials come from `GOOGLE_APPLICATION_CREDENTIALS_JSON`.

**SQL templates** — each app keeps its queries under `sql_templates/` and
loads them through a small `_load_sql()` / `sql_loader.py` helper. About
95% of queries elsewhere in the codebase are still inline f-strings; see
follow-up `chore/externalize-sql-fstrings`.

**Shared web templates** — `justdata/shared/web/templates/` holds the
chrome used by every app: `shared_header.html`, `shared_footer.html`,
`base_app.html`, `nav_menu.html`, plus the generic landing, admin, and
report templates. Apps use `ChoiceLoader` so their own templates win on
name collision.

**Shared JS** — `justdata/shared/web/static/js/` includes the global
`app.js`, `auth.js`, and a `components/` directory (currently
`GoalsCalculator.js`).

**Auth** — `justdata/main/auth/` provides `login_required`,
`require_access`, `admin_required`, and `staff_required` decorators on top
of Firebase. All blueprints import from there.

**Environment** — `justdata/shared/utils/unified_env.py` exposes
`get_unified_config()` for unified env loading across apps.

## 7. Testing

- Run all tests: `pytest tests/ -v`
- Skip slow/integration tests: `pytest tests/ -v -m "not integration and not slow"`
  (this is what CI runs)
- Smoke-only: `pytest tests/ -v -k smoke`
- Per-app: `pytest tests/apps/test_branchsight/ -v`

The test tree mirrors the app tree under `tests/apps/`. As of Phase 6:
**58 tests passing, zero pyflakes errors.**

CI runs on PRs targeting `test`, `staging`, and `main` via
`.github/workflows/ci.yml`.

## 8. Known follow-up items

The refactor closed out with the structural changes shipped, but several
debt items were carried forward as named branches/tickets:

- `chore/fix-blueprint-static-url-paths` — 8 apps register a
  `static_url_path` that doubles the prefix; lenderprofile is fixed,
  the rest still need cleanup.
- `refactor/split-shared-templates` — four shared templates remain over
  1,000 lines: `shared_header.html`, `justdata_landing_page.html`,
  `admin-users.html`, `report_template.html`.
- `refactor/split-shared-app-js` — the `app.js` trio in `shared/web`,
  `lendsight/`, and `bizsight/` is still oversized.
- `refactor/modularize-analytics-pages` — analytics page JS still ships
  as monolithic per-page bundles.
- `chore/externalize-sql-fstrings` — most SQL outside `sql_templates/`
  directories is still built as inline f-strings.

Phase 6 added a CI guardrail (`file-size-check` job) that allowlists the
files above and fails new violations.
