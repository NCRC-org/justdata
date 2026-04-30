# Test Baseline Capture

**Purpose:** Snapshot of the `tests/` suite state at the start of the refactor so behavioral regressions can be detected afterwards.

**Environment:** pytest 7.4.4 under anaconda Python 3.12 (`/Users/jadedlebi/anaconda3/bin/pytest`). Run from repo root. No credentials populated beyond whatever `tests/conftest.py::_mock_env` injects. No live BigQuery, no external API credentials in environment.

---

## Section 1 — Test inventory

`pytest --collect-only -q` — **31 tests collected in 7.10s. Zero collection errors.**

### Collected tests by app

| App / location | Test files collected | Tests collected |
|---|---|---|
| Root (`tests/`) | `test_full_stack.py` | 3 |
| dataexplorer | `test_aggregated_query.py`, `test_mortgage_template.py`, `test_simple_count.py` | 4 |
| electwatch | `test_data_sources.py` | 7 |
| lenderprofile | `test_all_apis.py`, `test_fdic_branches.py`, `test_fitb.py` | 16 |
| memberview | `test_propublica_matching.py` | 1 |
| **Total** | **9 files** | **31 tests** |

### Files present in `tests/` that were NOT collected

Nine files live under `tests/` that pytest did not collect. Three reasons:

1. **Five `*_standalone.py` files** — do not match `python_files = ["test_*.py", "*_test.py"]` in `pyproject.toml`:
   - `tests/apps/dataexplorer/connecticut_normalization_standalone.py`
   - `tests/apps/dataexplorer/ct_geo_census_standalone.py`
   - `tests/apps/dataexplorer/ct_tract_format_standalone.py`
   - `tests/apps/dataexplorer/ct_tract_to_county_standalone.py`
   - `tests/apps/memberview/propublica_simple_standalone.py`

2. **Three `test_*.py` files with no pytest-compatible test functions** — they match the collection pattern but contain only top-level script code (no `def test_*` / `class Test*`). pytest silently skips them with no error:
   - `tests/apps/lenderprofile/test_fifth_third_cached.py` — header docstring says "Test script for Fifth Third Bank with file-based caching. Usage: python test_fifth_third_cached.py".
   - `tests/apps/memberview/test_api.py` — hits `http://127.0.0.1:8082` with `requests.get(...)` at module level; needs a running MemberView server.
   - `tests/apps/electwatch/test_officials.py` — script that processes a hard-coded `TEST_OFFICIALS` list at module level.

3. **One `__init__.py` file per test directory** — expected.

### Collection errors

None. All 31 tests collected cleanly.

---

## Section 2 — Baseline run

```
pytest -v --tb=short -o faulthandler_timeout=60
```

**Result: 18 passed, 0 failed, 0 skipped, 13 errors. 20.08s wall time. Zero tests hung or timed out.**

| Outcome | Count |
|---|---|
| passed | 18 |
| failed | 0 |
| skipped | 0 |
| errors | 13 |
| total collected | 31 |
| runtime | 20.08 s |

### Passing tests (18)

```
tests/test_full_stack.py::test_backend                                        PASSED
tests/test_full_stack.py::test_frontend                                       PASSED
tests/test_full_stack.py::test_integration                                    PASSED
tests/apps/dataexplorer/test_aggregated_query.py::test_aggregated_query       PASSED
tests/apps/dataexplorer/test_mortgage_template.py::test_sql_template          PASSED
tests/apps/dataexplorer/test_mortgage_template.py::test_direct_query          PASSED
tests/apps/dataexplorer/test_simple_count.py::test_simple_count               PASSED
tests/apps/electwatch/test_data_sources.py::test_fec_api                      PASSED
tests/apps/electwatch/test_data_sources.py::test_congress_api                 PASSED
tests/apps/electwatch/test_data_sources.py::test_quiver_api                   PASSED
tests/apps/electwatch/test_data_sources.py::test_finnhub_api                  PASSED
tests/apps/electwatch/test_data_sources.py::test_fmp_api                      PASSED
tests/apps/electwatch/test_data_sources.py::test_sec_api                      PASSED
tests/apps/electwatch/test_data_sources.py::test_newsapi                      PASSED
tests/apps/lenderprofile/test_fitb.py::test_ticker_resolver                   PASSED
tests/apps/lenderprofile/test_fitb.py::test_identifier_resolution             PASSED
tests/apps/lenderprofile/test_fitb.py::test_section_builders_v2               PASSED
tests/apps/memberview/test_propublica_matching.py::test_propublica_matching   PASSED
```

### Failures

None.

### Errors (13) — all same failure mode, all in lenderprofile

Every one of the 13 errors is a **setup-phase `fixture '<name>' not found`** error. The test functions are annotated with positional parameters (`lender_name: str`, `identifiers: Dict[str, Any]`, `institution_name: str`) that are treated as pytest fixture requests. Those fixtures do not exist in `tests/conftest.py` or any local `conftest.py`, so pytest aborts each test before invocation.

| Test | Missing fixture |
|---|---|
| `tests/apps/lenderprofile/test_all_apis.py::test_identifier_resolution` | `lender_name` |
| `tests/apps/lenderprofile/test_all_apis.py::test_fdic_apis` | `identifiers` |
| `tests/apps/lenderprofile/test_all_apis.py::test_gleif_api` | `identifiers` |
| `tests/apps/lenderprofile/test_all_apis.py::test_sec_api` | `institution_name` |
| `tests/apps/lenderprofile/test_all_apis.py::test_courtlistener_api` | `institution_name` |
| `tests/apps/lenderprofile/test_all_apis.py::test_newsapi` | `institution_name` |
| `tests/apps/lenderprofile/test_all_apis.py::test_theorg_api` | `institution_name` |
| `tests/apps/lenderprofile/test_all_apis.py::test_cfpb_apis` | `institution_name` |
| `tests/apps/lenderprofile/test_all_apis.py::test_ffiec_api` | `identifiers` |
| `tests/apps/lenderprofile/test_all_apis.py::test_federal_reserve_api` | `identifiers` |
| `tests/apps/lenderprofile/test_all_apis.py::test_seeking_alpha_api` | `institution_name` |
| `tests/apps/lenderprofile/test_fdic_branches.py::test_branch_footprint` | `lender_name` |
| `tests/apps/lenderprofile/test_fitb.py::test_data_collection` | `identifiers` |

All 13 errors land in `tests/apps/lenderprofile/`. The CI workflow (`.github/workflows/ci.yml:31`) ignores `tests/apps/lenderprofile` and `tests/apps/dataexplorer` via `--ignore` flags, so the same suite passes green on CI despite these errors. Locally, running the full suite makes them visible.

### Skipped tests

None.

### Run blockers

None. No missing dependencies, no config errors, no hangs, no BigQuery timeouts. The suite completes in 20 seconds without credentials because every test either mocks external calls or exercises pure-Python logic.

---

## Section 3 — Test coverage by app

Legend: ✅ collected and passes, ⚠️ collected but errors at setup, ⛔ file present but not collected, ✖ no tests present at all.

### analytics
- **Test files:** none
- **Coverage:** ✖ no tests present
- **Gaps:** every route, every data function, every chart.

### bizsight
- **Test files:** none (only fixtures for it in `tests/conftest.py:150-158`, which make the test app importable)
- **Coverage:** ✖ no tests present
- **Gaps:** every route, every data function, report generation.

### branchmapper
- **Test files:** none
- **Coverage:** ✖ no tests present
- **Gaps:** every route, Census tract overlay generation, bank data queries, XLSX export.

### branchsight
- **Test files:** none (only fixtures for it in `tests/conftest.py:116-124`)
- **Coverage:** ✖ no tests present
- **Gaps:** every route, report generation, FDIC SOD data handling.

### dataexplorer
- **Test files:** `test_aggregated_query.py`, `test_mortgage_template.py`, `test_simple_count.py`. Plus four `*_standalone.py` Connecticut-related scripts not collected by pytest.
- **Coverage:** ✅ 4 passing tests covering SQL template rendering and simple BigQuery mock-backed counts.
- **Areas covered:** BigQuery query construction (via mocks), mortgage SQL template assembly.
- **Gaps:** no route tests, no wizard flow tests, no lender analysis tests, no export tests. The four CT `*_standalone.py` files cover tract normalization/format logic but are not wired into pytest.
- **CI note:** `ci.yml` passes `--ignore=tests/apps/dataexplorer`, so even the 4 passing tests here do not run on CI.

### electwatch
- **Test files:** `test_data_sources.py` (collected, all 7 pass), `test_officials.py` (present but collects zero tests — script-style).
- **Coverage:** ✅ 7 passing tests — one per external data source (FEC, Congress, Quiver, Finnhub, FMP, SEC, NewsAPI). These exercise source-client wiring, presumably with mocked HTTP.
- **Gaps:** no route tests, no BigQuery-write tests, no AI insights tests, no tests on `weekly_update.py` (the Cloud Run Job entry point), no tests on the admin / mapping endpoints.

### lenderprofile
- **Test files:** `test_all_apis.py`, `test_fdic_branches.py`, `test_fitb.py`, `test_fifth_third_cached.py` (not collected — script-style).
- **Coverage:** ⚠️ 3 passing tests in `test_fitb.py` (ticker resolver, identifier resolution, section builders) + 13 erroring tests due to missing fixtures.
- **Areas covered:** ticker-symbol resolution, identifier resolution for Fifth Third, section-builder v2 smoke test.
- **Gaps:** all 13 erroring tests are effectively non-functional until someone provides `lender_name`, `institution_name`, `identifiers` fixtures (likely was `@pytest.mark.parametrize` at some point). No route tests.
- **CI note:** `ci.yml` passes `--ignore=tests/apps/lenderprofile`, hiding the 13 errors.

### lendsight
- **Test files:** none (only fixtures for it in `tests/conftest.py:133-141`)
- **Coverage:** ✖ no tests present
- **Gaps:** every route, every data function, HMDA query construction, report rendering.

### loantrends
- **Test files:** none
- **Coverage:** ✖ no tests present
- **Gaps:** every route.

### memberview
- **Test files:** `test_propublica_matching.py` (collected, passes), `test_api.py` (present but collects zero tests — module-level `requests.get` hits localhost), `propublica_simple_standalone.py` (not collected).
- **Coverage:** ✅ 1 passing test — ProPublica member matching logic.
- **Gaps:** `test_api.py` is unusable in CI because it requires a live server at `127.0.0.1:8082`. No route tests that actually invoke the Flask app via the test client.

### mergermeter
- **Test files:** none
- **Coverage:** ✖ no tests present
- **Gaps:** every route, bank-merger calculation, assessment-area generation, XLSX export.

---

## Section 4 — Smoke-test target inventory

Routes surfaced from each app's `blueprint.py`. Scope: Flask default-method (GET) routes whose URL path takes no `<param>` captures. These are the routes that a smoke test can hit as `client.get(url)` with no setup beyond importing the app.

Excluded: routes with `methods=['POST']`, routes with `<x>` path captures (need fixture data), routes that render a saved report (depend on prior `/analyze` job state).

Blueprint file paths reference the line number of the `@<bp>.route(...)` decorator.

### analytics — suggested smoke targets

| Route | Method | Line |
|---|---|---|
| `/` | GET | `justdata/apps/analytics/blueprint.py:62` |
| `/health` | GET | `justdata/apps/analytics/blueprint.py:371` |
| `/api/summary` | GET | `justdata/apps/analytics/blueprint.py:155` |
| `/api/users` | GET | `justdata/apps/analytics/blueprint.py:321` |
| `/api/user-types` | GET | `justdata/apps/analytics/blueprint.py:350` |

(Other GET-no-param candidates also available: `/user-map`, `/research-map`, `/lender-map`, `/coalitions`, `/users`, `/costs`, `/api/user-locations`, `/api/research-activity`, `/api/lender-interest`, `/api/coalition-opportunities`, `/api/entity-users`, `/api/timeline`, `/api/costs`, `/api/ai-costs`, `/api/export`.)

### bizsight — suggested smoke targets

| Route | Method | Line |
|---|---|---|
| `/` | GET | `justdata/apps/bizsight/blueprint.py:65` |
| `/health` | GET | `justdata/apps/bizsight/blueprint.py:836` |
| `/data` | GET | `justdata/apps/bizsight/blueprint.py:417` |
| `/api/states` | GET | `justdata/apps/bizsight/blueprint.py:434` |
| `/api/state-boundaries` | GET | `justdata/apps/bizsight/blueprint.py:577` |

### branchmapper — suggested smoke targets

| Route | Method | Line |
|---|---|---|
| `/` | GET | `justdata/apps/branchmapper/blueprint.py:66` |
| `/health` | GET | `justdata/apps/branchmapper/blueprint.py:1008` |
| `/counties` | GET | `justdata/apps/branchmapper/blueprint.py:90` |
| `/states` | GET | `justdata/apps/branchmapper/blueprint.py:104` |
| `/api/bank-list` | GET | `justdata/apps/branchmapper/blueprint.py:704` |

### branchsight — suggested smoke targets

| Route | Method | Line |
|---|---|---|
| `/` | GET | `justdata/apps/branchsight/blueprint.py:78` |
| `/health` | GET | `justdata/apps/branchsight/blueprint.py:777` |
| `/counties` | GET | `justdata/apps/branchsight/blueprint.py:629` |
| `/states` | GET | `justdata/apps/branchsight/blueprint.py:646` |
| `/metro-areas` | GET | `justdata/apps/branchsight/blueprint.py:663` |

### lendsight — suggested smoke targets

| Route | Method | Line |
|---|---|---|
| `/` | GET | `justdata/apps/lendsight/blueprint.py:131` |
| `/health` | GET | `justdata/apps/lendsight/blueprint.py:941` |
| `/counties` | GET | `justdata/apps/lendsight/blueprint.py:747` |
| `/states` | GET | `justdata/apps/lendsight/blueprint.py:781` |
| `/years` | GET | `justdata/apps/lendsight/blueprint.py:911` |

### loantrends — suggested smoke targets

Only three GET routes with no path parameters exist. All three fit the criteria.

| Route | Method | Line |
|---|---|---|
| `/` | GET | `justdata/apps/loantrends/blueprint.py:53` |
| `/api/dashboard-data` | GET | `justdata/apps/loantrends/blueprint.py:61` |
| `/api/available-graphs` | GET | `justdata/apps/loantrends/blueprint.py:133` |

### mergermeter — suggested smoke targets

| Route | Method | Line |
|---|---|---|
| `/` | GET | `justdata/apps/mergermeter/blueprint.py:64` |
| `/health` | GET | `justdata/apps/mergermeter/blueprint.py:1093` |
| `/goals-calculator` | GET | `justdata/apps/mergermeter/blueprint.py:94` |
| `/report-data` | GET | `justdata/apps/mergermeter/blueprint.py:696` |
| `/report` | GET | `justdata/apps/mergermeter/blueprint.py:79` |

(Note: `/report` and `/report-data` may return empty / redirect payloads without a job context; they're fine as smoke targets if the assertion is "returns 200 or a 4xx that is not 500".)

---

## Section 5 — pytest configuration

From `pyproject.toml`, `[tool.pytest.ini_options]`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--strict-markers",
    "--strict-config",
]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
]
```

Observations:
- **Three custom markers registered**: `slow`, `integration`, `unit`. `--strict-markers` is on, so unrecognized markers fail.
- **Discovery patterns are pytest defaults** (`test_*.py`/`*_test.py`, `Test*`, `test_*`). This explains why `*_standalone.py` files are not collected.
- **No plugins pinned in config**. `pytest-cov` is used in CI (`--cov=justdata --cov-report=term-missing`) and is available at runtime. `pytest-timeout` is **not** installed in the local environment — a per-test timeout had to be approximated with `-o faulthandler_timeout=60` for this baseline run.
- **No `minversion` set.** Local run used pytest 7.4.4.

---

## Section 6 — Observations

Factual observations only.

1. **Baseline is 18 pass / 0 fail / 0 skip / 13 error.** Every error is a fixture-injection failure in `tests/apps/lenderprofile/`. There are no assertion failures and no runtime failures in the collected suite.

2. **The 13 lenderprofile errors are hidden in CI** because `.github/workflows/ci.yml:31` passes `--ignore=tests/apps/lenderprofile --ignore=tests/apps/dataexplorer`. CI reports green while the test files in those directories are not exercised.

3. **Three files named `test_*.py` collect zero tests** because they are module-level scripts, not pytest test modules: `tests/apps/lenderprofile/test_fifth_third_cached.py`, `tests/apps/memberview/test_api.py`, `tests/apps/electwatch/test_officials.py`. pytest does not warn about this.

4. **Five `*_standalone.py` files are never executed by pytest.** They exist as runnable ad-hoc scripts inside `tests/` but do not match `python_files`.

5. **No tests exist for seven of the ten sub-apps targeted by Phase 1:** analytics, bizsight, branchmapper, branchsight, lendsight, loantrends, mergermeter. Phase 1 PRs will need to add smoke-test scaffolding on each of these.

6. **Existing fixtures in `tests/conftest.py` already support bizsight, branchsight, and lendsight** via `bizsight_app`, `branchsight_app`, `lendsight_app` client fixtures (each wrapped in `try/except pytest.skip`). No route tests use them yet, but the scaffolding is there.

7. **Total local runtime is ~20 seconds** — fast enough to run on every commit if wired into CI.

8. **No test hit BigQuery, a live API, or any external service during this run.** `conftest.py::_mock_env` (autouse=True) injects fake credentials and `mock_bigquery_client` / `mock_ai_provider` fixtures mock the shared AI/BigQuery accessors. Any existing test that requires live credentials would have failed here; none did.

9. **The `slow`/`integration`/`unit` markers are declared in `pyproject.toml` but not applied to any test file in the collected set.** Grepping `tests/` for `@pytest.mark.slow|@pytest.mark.integration|@pytest.mark.unit` returned no matches in the 9 collected files. CI filters on `-m "not integration and not slow"`, which is a no-op today.

10. **Per-test timeout enforcement is not in place.** `pytest-timeout` is absent from the local env and is not listed in `requirements.txt`. This run used `faulthandler_timeout=60` (best-effort diagnostic dump, not a kill), so a hung test could still stall the baseline. None did in this run.
