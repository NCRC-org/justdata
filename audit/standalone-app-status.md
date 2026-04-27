# Standalone `app.py` Status Audit

**Scope:** Ten JustData sub-apps that maintain both a Flask blueprint (`blueprint.py`) and a standalone Flask app (`app.py` + `run.py`):
`analytics, bizsight, branchmapper, branchsight, dataexplorer, electwatch, lenderprofile, lendsight, loantrends, mergermeter`.

**Read-only investigation.** No branches changed, no code modified, no app started, no BigQuery contacted.

---

## Section 1 — Deploy wiring check

Searched `Dockerfile`, `Dockerfile.app`, `Dockerfile.electwatch-job`, `Dockerfile.hubspot-sync-job`, `cloudbuild.yaml`, `docker-compose.yml`, and `.github/workflows/*`.

The only hit for any app path was:
- `.github/workflows/ci.yml:31` — `pytest ... --ignore=tests/apps/lenderprofile --ignore=tests/apps/dataexplorer` (ignore list for test run, not a runtime reference)
- `.github/workflows/deploy-electwatch-job.yml:8` — path filter `justdata/apps/electwatch/**` (triggers on any change inside the electwatch dir; does not name `app.py`/`run.py`)

**No Dockerfile, no cloudbuild step, no docker-compose service, and no CI workflow references any of the ten standalone `app.py` or `run.py` files.** The production/test container entrypoint is `start.sh` → `gunicorn run_justdata:app`, which imports `justdata.main.app.create_app()` and registers all apps as blueprints at `/<app>/` URL prefixes.

| App | Dockerfile | cloudbuild.yaml | CI workflow | docker-compose | Notes |
|---|---|---|---|---|---|
| analytics | no | no | no | no | — |
| bizsight | no | no | no | no | — |
| branchmapper | no | no | no | no | — |
| branchsight | no | no | no | no | — |
| dataexplorer | no | no | no* | no | *ci.yml excludes `tests/apps/dataexplorer` from pytest collection; not a runtime ref |
| electwatch | no | no | no* | no | *`deploy-electwatch-job.yml` path filter matches `justdata/apps/electwatch/**` but does not invoke `app.py`/`run.py`; the job uses `Dockerfile.electwatch-job` (separate batch job) |
| lenderprofile | no | no | no* | no | *ci.yml excludes `tests/apps/lenderprofile` from pytest collection; not a runtime ref |
| lendsight | no | no | no | no | — |
| loantrends | no | no | no | no | — |
| mergermeter | no | no | no | no | — |

---

## Section 2 — Import graph check

```
rg -n "from justdata\.apps\.<app>\.app import|import justdata\.apps\.<app>\.app" --type py
```

| App | External imports of standalone `app.py`? | Importing files |
|---|---|---|
| analytics | no | — |
| bizsight | yes (tests only) | `tests/conftest.py:150` |
| branchmapper | no | — |
| branchsight | yes (tests only) | `tests/conftest.py:116` |
| dataexplorer | no | — |
| electwatch | no | — |
| lenderprofile | no | — |
| lendsight | yes (tests only) | `tests/conftest.py:133` |
| loantrends | no | — |
| mergermeter | no | — |

Note: the three `tests/conftest.py` imports are inside fixture bodies wrapped in `try/except` that `pytest.skip(...)` on failure, so removing the standalone files would degrade those fixtures gracefully rather than break the test collection.

---

## Section 3 — Commit recency check

Dates from `git log -1 --format='%ai %h %s'`.

| App | `app.py` last touched | `blueprint.py` last touched | Gap (days) | Newer side |
|---|---|---|---|---|
| analytics | 2026-01-22 (`5baa592`) | 2026-01-30 (`6a891c2`) | 8 | blueprint |
| bizsight | 2026-02-05 (`614fa99`) | 2026-03-13 (`bb57b32`) | 36 | blueprint |
| branchmapper | 2026-03-18 (`5aa5f8a`) | 2026-03-11 (`d459428`) | 7 | **app.py** ⚠ |
| branchsight | 2026-02-16 (`aaf233d`) | 2026-03-13 (`bb57b32`) | 25 | blueprint |
| dataexplorer | 2026-02-05 (`c774eeb`) | 2026-03-12 (`363e3b0`) | 35 | blueprint |
| electwatch | 2026-02-05 (`2d87431`) | 2026-02-06 (`55221b1`) | 1 | blueprint |
| lenderprofile | 2026-03-13 (`6e310f7`) | 2026-02-06 (`55221b1`) | 35 | **app.py** ⚠ |
| lendsight | 2026-02-16 (`aaf233d`) | 2026-03-13 (`bb57b32`) | 25 | blueprint |
| loantrends | 2026-01-12 (`0a0ec34`) | 2026-02-06 (`55221b1`) | 25 | blueprint |
| mergermeter | 2026-03-19 (`06ec53a`) | 2026-03-17 (`a7490c8`) | 2 | **app.py** ⚠ |

**Flags:**
- No app exceeds the >60-day divergence threshold. Maximum gap is 36 days (bizsight).
- Three apps have `app.py` touched more recently than `blueprint.py` — i.e., someone is still maintaining both surfaces:
  - `branchmapper/app.py` — commit `5aa5f8a` "BranchMapper: CBSA-based minority quartiles with percentage cutoffs in legend"
  - `lenderprofile/app.py` — commit `6e310f7` "Strip trailing commas and periods from FFIEC lender names"
  - `mergermeter/app.py` — commit `06ec53a` "fix: validation sheet always present, SheetJS tab layout, legend quartile %, Non-MSA by state, Notes SB IDs by year"

  These three warrant a look before deletion to confirm the functional change was also applied in `blueprint.py`.

---

## Section 4 — Route diff per app

Routes extracted via `rg -oN "@[a-z_]+\.route\(['\"]([^'\"]+)['\"]"`. URL converters (`<int:x>`, `<path:y>`) preserved in the strings below.

### analytics
- `app.py` total: 0, `blueprint.py` total: 25, overlap: 0
- **Unique to `app.py`:** (none)
- **Unique to `blueprint.py`:** all 25 routes (it is the only route-bearing surface)
- `analytics/app.py` is a 26-line factory that imports and registers `analytics_bp` — no `@app.route` decorators at all.

### bizsight
- `app.py` total: 19, `blueprint.py` total: 13, overlap: 13
- **Unique to `app.py` (6):**
  - `/api/planning-regions` — ⚠ looks like a real data endpoint not present on blueprint
  - `/favicon-16x16.png`, `/favicon-32x32.png`, `/favicon.ico` — favicon shims
  - `/shared/population_demographics.js` — static shim
  - `/static/img/ncrc-logo.png` — static shim
- **Unique to `blueprint.py` (0):** (none)

### branchmapper
- `app.py` total: 14, `blueprint.py` total: 16, overlap: 13
- **Unique to `app.py` (1):**
  - `/api/census-tracts/<path:county>` — ⚠ uses `path` converter; blueprint uses `<county>` (default string converter). Different matching behavior (`path` matches slashes).
- **Unique to `blueprint.py` (3):**
  - `/api/census-tracts/<county>`
  - `/export/methods-pdf`
  - `/health`

### branchsight
- `app.py` total: 8, `blueprint.py` total: 11, overlap: 6
- **Unique to `app.py` (2):**
  - `/shared/population_demographics.js` — static shim
  - `/static/img/ncrc-logo.png` — static shim
- **Unique to `blueprint.py` (5):**
  - `/`, `/analyze`, `/download`, `/health`, `/progress/<job_id>`

### dataexplorer
- `app.py` total: 32, `blueprint.py` total: 25, overlap: 23
- **Unique to `app.py` (9):**
  - `/api/bigquery/job-history` — ⚠ real API
  - `/api/config/data-types` — ⚠ real API
  - `/api/export-lender-report-excel` — ⚠ real API
  - `/api/search-lender` — ⚠ real API
  - `/api/test-lender-analysis` — ⚠ real API
  - `/test-lender-analysis` — ⚠ real page
  - `/shared/population_demographics.js` — static shim
  - `/static/img/ncrc-logo-black.png`, `/static/img/ncrc-logo.png` — static shims
- **Unique to `blueprint.py` (2):**
  - `/health`, `/no-data`

### electwatch
- `app.py` total: 23, `blueprint.py` total: 40, overlap: 12
- **Unique to `app.py` (11):** ⚠ largest functional divergence of any app
  - `/api/analyze`, `/api/bills/<bill_id>`, `/api/bills/search`, `/api/industry/<sector>`, `/api/result/<job_id>`, `/api/search`, `/download`, `/firm/<firm_name>`, `/industry/<sector>`, `/progress/<job_id>`
  - `/static/img/ncrc-logo.png` — static shim
- **Unique to `blueprint.py` (28):** mostly admin/mapping endpoints (`/api/admin/...`), plus `/firm/<firm_id>` and `/industry/<industry_code>` — note the path-parameter name disagreements (`<firm_name>` vs `<firm_id>`; `<sector>` vs `<industry_code>`).

### lenderprofile
- `app.py` total: 8, `blueprint.py` total: 5, overlap: 5
- **Unique to `app.py` (3):**
  - `/api/test` — scaffold
  - `/test-route` — scaffold
  - `/static/img/ncrc-logo.png` — static shim
- **Unique to `blueprint.py` (0):** (none)

### lendsight
- `app.py` total: 7, `blueprint.py` total: 13, overlap: 4
- **Unique to `app.py` (3):**
  - `/counties-by-state/<state_identifier>` — ⚠ parameter-name collision vs blueprint's `/counties-by-state/<state_code>`; same URL shape, different converter var name
  - `/progress` — ⚠ shape mismatch vs blueprint's `/progress/<job_id>`
  - `/shared/population_demographics.js` — static shim
- **Unique to `blueprint.py` (9):**
  - `/`, `/analyze`, `/counties-by-state/<state_code>`, `/data`, `/download`, `/health`, `/metro-areas`, `/progress/<job_id>`, `/years`

### loantrends
- `app.py` total: 9, `blueprint.py` total: 7, overlap: 7
- **Unique to `app.py` (2):**
  - `/progress` — not paired with `<job_id>` on either side
  - `/static/img/ncrc-logo.png` — static shim
- **Unique to `blueprint.py` (0):** (none)

### mergermeter
- `app.py` total: 10, `blueprint.py` total: 19, overlap: 9
- **Unique to `app.py` (1):**
  - `/api/save-goals-config` — ⚠ real config endpoint not present on blueprint
- **Unique to `blueprint.py` (10):**
  - `/`, `/analyze`, `/api/generate`, `/api/search-banks`, `/api/search-banks-ext`, `/download`, `/excel-data`, `/health`, `/progress/<job_id>`, `/report`

---

## Section 5 — Preliminary verdict per app

| App | Verdict | Reasoning |
|---|---|---|
| analytics | **Safe to delete** | `app.py` is a 26-line factory shim with no `@route` decorators; `run.py` is a 23-line launcher. No deploy refs, no external imports, no unique routes. Nothing to merge. |
| bizsight | **Needs merge first** | `/api/planning-regions` is unique to `app.py`. Also imported by `tests/conftest.py` (test-only, optional). Favicon/static shims should move to shared infra. |
| branchmapper | **Needs merge first** | `/api/census-tracts/<path:county>` uses a different URL converter than blueprint's `/api/census-tracts/<county>` — this is a semantic difference in routing, not just a naming one. Also `app.py` is newer (commit `5aa5f8a`, 2026-03-18); confirm the CBSA quartile change is present in `blueprint.py` before deletion. |
| branchsight | **Keep as thin wrapper OR safe to delete** | Only `app.py`-unique routes are two static shims. `blueprint.py` is the complete surface. Imported by `tests/conftest.py` (test-only). Can likely be reduced to an analytics-style factory, or deleted if no developer workflow depends on `run.py`. |
| dataexplorer | **Needs merge first** | Seven genuine API/page routes exist only in `app.py` (`/api/search-lender`, `/api/export-lender-report-excel`, `/api/bigquery/job-history`, `/api/config/data-types`, `/api/test-lender-analysis`, `/test-lender-analysis`). These must be ported to `blueprint.py` (or confirmed deprecated) before deletion. |
| electwatch | **Needs merge first** | The largest functional divergence. Core user-facing routes (`/api/search`, `/api/analyze`, `/api/bills/*`, `/firm/<firm_name>`, `/industry/<sector>`, `/download`, `/progress/<job_id>`) live only on `app.py`, while admin/mapping endpoints live only on `blueprint.py`. Parameter names also disagree (`<firm_name>` vs `<firm_id>`, `<sector>` vs `<industry_code>`). Biggest merge job of the set. |
| lenderprofile | **Keep as thin wrapper OR safe to delete** | `app.py`-unique routes are only `/api/test`, `/test-route`, and a static logo shim — all scaffolds, no production behavior. However, `app.py` is 35 days newer than `blueprint.py` (commit `6e310f7` "Strip trailing commas and periods from FFIEC lender names") — confirm the functional change landed in `blueprint.py` or shared code before deletion. |
| lendsight | **Needs merge first** | `/counties-by-state/<state_identifier>` vs blueprint's `/counties-by-state/<state_code>` — same URL shape but divergent handler parameter name (handlers likely have different signatures). `/progress` (no job_id) is shape-mismatched against blueprint's `/progress/<job_id>`. Resolve these URL/handler disagreements before deletion. Imported by `tests/conftest.py`. |
| loantrends | **Safe to delete** (with caveat) | Blueprint covers all 7 of its routes. `app.py`-unique items are `/progress` (non-parametrized, no analog on blueprint — could be dead or could be an unguarded endpoint) and a static logo shim. Worth a 5-minute look at what `/progress` actually does before removal. |
| mergermeter | **Needs merge first** | `/api/save-goals-config` is unique to `app.py`. `app.py` is 2 days newer (commit `06ec53a` added validation sheet handling and Non-MSA state logic) — confirm that delta is also in the blueprint/shared-core before deletion. |

---

## Section 6 — Additional findings

**Not recommendations; just factual observations that may matter in Phase 1.**

1. **Production container uses only the blueprint path.** `start.sh` runs `gunicorn run_justdata:app`, which calls `justdata.main.app.create_app()`. That function (`justdata/main/app.py:459-545`) imports `...<app>.blueprint` for every one of the ten apps and mounts each under `/<app>/`. The standalone `app.py`/`run.py` files are not reachable in Cloud Run.

2. **All 10 `run.py` files are near-duplicates.** They do `sys.path.insert(...)`, optionally `load_dotenv`, then `from justdata.apps.<app>.app import app` and expose `application = app`. The ElectWatch variant prints an ASCII banner; the BranchMapper and ElectWatch variants also load `.env`. Otherwise they are essentially the same 25–70 line boilerplate. If the standalones go, the `run.py` files go with them.

3. **Developer-facing docs still advertise the standalone runners.** `README.md:67-72` lists six of them as the way to "Run Individual Apps" locally. Any dedup that removes `run.py` files will need a README update.

4. **Two developer docs reference `apps/<x>/app.py` in prose.** `docs/dataexplorer/AREA_ANALYSIS_INTEGRATION_CHECKLIST.md:113` and `docs/dataexplorer/DATAEXPLORER_WIZARD_DATA_STRUCTURE.md:141` both name `apps/dataexplorer/app.py` as the Flask routes file. Outdated pointers after a move.

5. **`docs/lenderprofile/IMPLEMENTATION_STATUS.md:124` mentions `apps/lenderintel/run.py`** — a path that no longer exists (the app was renamed to `lenderprofile`). Pre-existing doc drift, unrelated to this dedup but worth catching.

6. **Three standalone `app.py` files have been touched more recently than their blueprint counterparts** (see Section 3 flags): `branchmapper`, `lenderprofile`, `mergermeter`. The commit subjects suggest functional changes (quartile binning, lender-name cleanup, validation sheet logic). Verify each change was mirrored into `blueprint.py` or into a shared module that blueprint imports before deletion.

7. **Standalone `app.py` files are large and contain non-route code.** Line counts: `mergermeter` 4035, `electwatch` 3263, `dataexplorer` 1863, `branchmapper` 1265, `bizsight` 1139, `lendsight` 614, `branchsight` 632, `lenderprofile` 577, `loantrends` 434, `analytics` 26. Whatever helper functions, threading setup, and module-level globals live in those files will need a destination — either into the blueprint, into a per-app helpers module, or into `shared/`. The route-count-only view in Section 4 does not capture that surface area.

8. **`tests/conftest.py` is the only production-tree code that imports any standalone `app.py`** (fixtures for bizsight, branchsight, lendsight). Those fixtures are `try/except` + `pytest.skip`, so deletion degrades gracefully. CI already skips `tests/apps/lenderprofile` and `tests/apps/dataexplorer` in `ci.yml`, and dataexplorer/lenderprofile do not have conftest fixtures pointing at their standalones.

9. **`docker-compose.yml` is stale infrastructure.** It references a Postgres/Redis/Celery topology (`celery -A justdata.shared.services.celery_app worker`) that does not match the Cloud Run deploy and is unrelated to the Flask app surface. Not a dedup blocker; just noting it does not constrain the decision.

10. **No shell script, Makefile target, or deploy artifact invokes any of the ten `run.py` files.** The `Makefile` `run` target (line 48) and the deploy scripts all target the unified `run_justdata` entrypoint or use `Dockerfile.app`.
