# App standardization matrix (spec 04, Step 0)

Input to spec 04 Part B (L5 `Projects/JustData Frontend Specs/04-app-standardization`).
Scope: LendSight, BizSight, BranchSight, then MergerMeter last (MergerMeter is
staff-only on every deploy). Audited on `testing` at 4f9d8ee, 2026-10-07.

**Who produced each row** (the `Source` column):
- **Code (Claude):** read from templates, JS and blueprints. File:line references are in the per-app notes below.
- **Code (Claude), not observed:** what the code does, never seen rendered. The shared PR's `/dev/app-states` route (FLASK_DEBUG only) is where these states will be visible.
- **Timing, member (Claude):** cached runs on the testing site with the member tester account, via `scripts/time_analysis.py`.
- **Timing, staff (Jad):** uncached runs, plus all MergerMeter runs, run by Jad as staff with the same script.
- **Pending:** not produced yet; the reason is stated.

Paths are relative to `justdata/`.

| Column | LendSight | BizSight | BranchSight | MergerMeter | Source |
|---|---|---|---|---|---|
| Entry route and template | `/lendsight/` → `lendsight_analysis.html`, **extends `base_app.html`**. Report page `/report` is standalone + `shared_header.html` | `/bizsight/` → `bizsight_analysis.html`, standalone + `shared_header.html` | `/branchsight/` → `branchsight_analysis.html`, standalone + `shared_header.html`. `/report` renders via a raw jinja2 Environment | `/mergermeter/` → `mergermeter_analysis.html`, standalone + `shared_header.html`. `require_access('mergermeter','full')` | Code (Claude) |
| Page header (title, tagline, vintage) | Shell header app name; no tagline; hardcoded "2020 to 2024" info box | Legacy header h1; no tagline; "2020 to 2024" shown only after a county is picked (hardcoded) | Legacy header h1; no tagline; hardcoded "2021 to 2025" info box | Legacy header h1; card subtitle "Upload merger research ticket…"; no vintage shown (years only in selects) | Code (Claude) |
| Input pattern | Single form: state, county, 3 loan-purpose checkboxes, staff-only refresh. Inline + `alert`-free validation messages | Single card, progressive reveal (state → county → config card). Only an `alert()` for validation; no `<form>` | Single form `#analysisForm`: state (Select2), county. Custom validation messages | Single form, 3 sections: banks (search + LEI/RSSD/SB ID), assessment areas (upload / manual / from branches), 8 year selects + 5 HMDA filter multi-selects. `alert()` validation | Code (Claude) |
| Geography picker | State → one county (server allows ≤3). App-local inline JS + Select2 | State → one county. App-local inline JS. Planning-region endpoint unused | State → one county (server also accepts state/metro; UI never sends them). App-local inline jQuery + Select2 | Assessment areas: JSON/CSV upload, manual CBSA text, or generate from branches (hardcodes year 2025), or national. App-local | Code (Claude) |
| Lender picker | none | none | none | Debounced bank search `/api/search-banks` (GLEIF + HMDA + SB lenders), LEI/RSSD/SB ID; no FDIC cert. App-local | Code (Claude) |
| Run action | "Generate Analysis" (`fa-magic`), bottom; disabled + "Processing…" during run | "Generate Analysis" (`fa-magic`); card hidden until county chosen; never disabled | "Generate Analysis" (`fa-magic`); disabled + "Processing…" during run | "Generate Merger Analysis"; disabled on submit; "5-10 minutes" note | Code (Claude) |
| Loading state | Progress card: spinner, step list, bar, text. SSE `/progress/<job_id>`. No elapsed time, no cancel | Same pattern, 5-step list. SSE. No elapsed, no cancel | Same pattern, 10-step list (3 steps never light up). SSE. No elapsed, no cancel | Bar + percent + step text; "keep this window open". SSE with 2 s reconnect. No elapsed, no cancel | Code (Claude) |
| Results layout | Separate `/report`: one long page, intro, key findings, 4 sections + Methods. Chart.js (2 charts), 5 tables, no map | Separate `/report`: sections 1-6 incl. Methods. Chart.js + Plotly loaded; map code dead | Separate `/report`: summary, key findings, 3 sections + Methods. Chart.js HHI chart; map code dead | Same page: Excel workbook rendered as tabs with SheetJS + validation banner. No charts, no map. `/report` is the Goals Calculator | Code (Claude) |
| Report: narrative, font, exports | AI narrative (`analysis.py`). Inter on web, Georgia in PDF. `/download`: zip (xlsx+pdf), excel (=zip), pdf | AI narrative (`ai_analysis.py`). Inter. zip (xlsx+pdf), pdf; `powerpoint` returns 501 | AI narrative (`analysis.py`). Inter on web, Georgia in PDF. excel, csv, json, pdf, zip (UI exposes zip only) | No narrative in the UI flow (`/api/generate-ai-summary` exists, nothing calls it). Inter. Excel only | Code (Claude) |
| Disclaimers | 8× "Above text is AI generated…"; census-boundary note; **web AI Disclosure is placeholder: lorem ipsum + "[This disclosure text will be provided by Rose/Legal]"** | 4× AI caption; PPP and Section 1071 tooltips; limitations note. **Unbacked claims: "All AI-generated narratives are reviewed for accuracy", "systematic quality assurance"**; AI Disclosure names Sections 1 and 5 but narratives are in 1-5 | 4× AI caption; census note; merger caveat; data-validation claim. **Web AI Disclosure is "[LOREM IPSUM PLACEHOLDER - TO BE REPLACED]" + lorem ipsum** | No formal disclaimer in the live UI. Excel Notes sheet labels SB data "Section 1071" though it comes from CRA disclosure (`bizsight.sb_county_summary`) | Code (Claude) |
| Error and empty states | Exceptions: "Analysis Failed" + message + Try Again. **Zero rows: job never finishes** (stuck "in progress"). No analysis timeout | Raw error text shown ("Query error: …"). Zero rows: "No small business lending data found for {county}". No timeout | **Zero rows / all queries fail: job never finishes.** Otherwise "Analysis Failed". Empty tables return silently. No timeout | Exceptions → "Analysis Failed" + raw `str(e)`. BigQuery 120 s timeout message. Zero rows: sheets left without metrics | Code (Claude), not observed |
| Progress copy | Emoji jokes ("Let the AI work its magic! ✨"); 5 messages dropped (unknown step keys) | Emoji jokes on every step; ~8 messages dropped (unknown step keys) | **Random joke lines incl. "Russell hates this.", "Support the CFPB.", "Beep boop beep."**; 2 messages dropped | "Doing something cool..." at 98% | Code (Claude) |
| Inline styles (`style="` lines) | 226 | 276 | 104 | 851 | Code (Claude) |
| Icons | 0 `data-lucide`, 80 `fa-` | 0 `data-lucide`, 92 `fa-` | 0 `data-lucide`, 37 `fa-` | 0 `data-lucide`, 290 `fa-` | Code (Claude) |
| JS over 500 lines | `_lendsight_report_scripts.html` 2319 (inline); `_lendsight_analysis_extra_js.html` 772; shared `app.js` 1519 (**loaded twice** on the entry page) | `_bizsight_report_scripts.html` 2385 (inline); app `static/js/app.js` 1255 (mostly inert) | `_branchsight_report_scripts.html` 1207 (inline); shared `app.js` 1519 | inline script in `mergermeter_analysis.html` ~1694; `mergermeter_report.html` ~717 (unreachable); shared `app.js` 1519; `GoalsCalculator.js` 766 | Code (Claude) |
| Templates over 1000 lines | `_lendsight_report_scripts.html` 2319 | `_bizsight_report_scripts.html` 2385 | `_branchsight_report_scripts.html` 1207 | `mergermeter_analysis.html` 2529; orphan partials 1707 / 1570; `mergermeter_report.html` 1120 | Code (Claude) |
| BigQuery path | Shared client. Multi-line SQL f-strings (one interpolates an unescaped state code). Analysis cache + bypass (`force_refresh`, staff) | App wrapper calling `client.query` directly (no shared timeout). SQL f-strings. Cache + bypass (staff) | Shared client; SQL via string `.replace()` not query parameters. Cache + bypass (staff) | Shared client (120 s timeout). SQL f-strings in `query_builders.py`. **Never writes to the analysis cache** (`_perform_analysis` returns None). Bypass shown only to senior_executive/admin | Code (Claude) |
| Analysis years actually run | 2020 to 2024 fixed (`core.py:43`); client's years ignored but used in cache key. Ticket 13229533844 | 2020 to 2024 trends; summary, comparison, top lenders and HHI pinned to 2024. Ticket 13229487819 | 2021 to 2025 fixed (`branchsight.sod_legacy` + `sod`) | HMDA 2018 to 2025 selectable (default 2023-2025); SB 2018 to 2024 selectable (default 2023-2024) | Code (Claude) |
| In-report methodology anchor (`help_url`) | `/lendsight/report#methodsSection` | `/bizsight/report#section6` | `/branchsight/report#methodsSection` | none (`help_url` = None) | Code (Claude) |
| Timing: entry TTFB | | | | | Timing, member (Claude): see "Measurements" below |
| Timing: cached analysis (3 runs × 2 geographies) | see "Cached runs" | see "Cached runs" | never a hit (ticket 2) | staff only | Timing, member (Claude), 2026-10-20 |
| Timing: uncached analysis (2 runs × 2 geographies), BigQuery bytes billed | 229 to 285 s Cook, 139 to 151 s Lowndes; 11.5 to 12.7 GB | 58 to 70 s; 1.8 GB | 19 to 32 s; 181 MB | 37 to 42 s; 106.8 GB | Timing, staff (Jad), 2026-10-15; see "Analysis timings and bytes" |
| Lighthouse (entry page, desktop) | | | | | Timing, member (Claude): see "Measurements" below; MergerMeter by Jad as staff |
| Known bugs (Workflow board 18397384545, all Open) | 13229533844 stuck on 2024 HMDA (High) | 13229487819 year range (Medium) | none on the board (see audit findings) | 11534922159 CBA tool fails on parameter changes (Bug, High); 11535049086 SheetJS preview too narrow (Styling); 11535803754 Total column placement (Styling) | Workflow board, read by Claude 2026-10-07. Platform-wide: 11535494229 dynamic year detection (Critical); 13229522646 ACS vintage; 11223018140 version numbers inconsistent (Bug); 11108736907 final disclaimer language from Rose (Critical, Legal); 11108742102 mobile/tablet responsiveness |

Reference geographies (Jad, 2026-10-07): **Cook County, IL (17031)** as the
large metro and **Lowndes County, AL (01085)** as the rural county.
MergerMeter acquirer/target pair and assessment-area mode: **pending Jad**.

## Measurements (testing site, member account, 2026-10-07)

Produced by Claude (Timing, member). Desktop Lighthouse 12, signed in, entry
page only. TTFB is 10 requests per app, time to the first body byte.
MergerMeter is staff-only, so its rows are Jad's.

| App | TTFB median / p95 (budget p95 <= 600 ms) | Lighthouse performance (budget >= 85) | Accessibility (>= 95) | Time to interactive (budget <= 1.5 s) | LCP / TBT / CLS |
|---|---|---|---|---|---|
| LendSight | 230 / 388 ms | 94 | 96 | 1.3 s | 1.3 s / 0 ms / 0.001 |
| BizSight | 174 / 178 ms | 96 | 96 | 1.2 s | 1.2 s / 0 ms / 0.001 |
| BranchSight | 191 / 239 ms | 89 | 96 | **2.1 s (over budget)** | 2.1 s / 0 ms / 0.001 |
| MergerMeter | pending (Jad, staff) | pending | pending | pending | pending |

The analysis timings are in "Analysis timings and bytes" below.

## Analysis timings and bytes (testing site)

### Uncached runs (Jad, admin, 2026-10-15, 22:00 to 22:30 UTC)

Two runs per app and geography with `force_refresh`, so BigQuery's result
cache was off (`bq_cache_hits` 0 or blank on every row). Every run matched its
own jobs by job label. Raw output: `audit/timings/uncached.jsonl` (Jad's file,
not committed). Bytes are bytes billed. Cost is at the on-demand rate of $6.25
per TiB ([BigQuery pricing](https://cloud.google.com/bigquery/pricing)),
before the free tier.

| App | Geography | Run | Done (s) | Report ready (s) | Jobs | Bytes billed | Cost per run |
|---|---|---|--:|--:|--:|--:|--:|
| LendSight | Cook | 1 | 285.3 | 286.9 | 40 | 11.55 GB | $0.066 |
| LendSight | Cook | 2 | 228.9 | 230.5 | 43 | 11.58 GB | $0.066 |
| LendSight | Lowndes | 1 | 138.9 | 140.4 | 40 | 12.66 GB | $0.072 |
| LendSight | Lowndes | 2 | 150.9 | 152.2 | 43 | 12.69 GB | $0.072 |
| BizSight | Cook | 1 | 59.8 | 62.3 | 26 | 1.82 GB | $0.010 |
| BizSight | Cook | 2 | 70.4 | 73.2 | 29 | 1.85 GB | $0.011 |
| BizSight | Lowndes | 1 | 58.2 | 60.0 | 26 | 1.82 GB | $0.010 |
| BizSight | Lowndes | 2 | 59.3 | 60.8 | 29 | 1.85 GB | $0.011 |
| BranchSight | Cook | 1 | 31.8 | 34.0 | 11 | 181 MB | $0.001 |
| BranchSight | Cook | 2 | 30.8 | 33.6 | 11 | 181 MB | $0.001 |
| BranchSight | Lowndes | 1 | 19.3 | 20.7 | 11 | 181 MB | $0.001 |
| BranchSight | Lowndes | 2 | 24.3 | 25.5 | 11 | 181 MB | $0.001 |
| MergerMeter | Pinnacle / UCB | 1 | 42.1 | 42.6 | 32 | 106.85 GB | $0.607 |
| MergerMeter | Pinnacle / UCB | 2 | 37.2 | 37.8 | 31 | 106.85 GB | $0.607 |

Run 2 has three more jobs than run 1 in the Sight apps: the delete of run 1's
cache entry, which `force_refresh` replaces. BranchSight has no such jobs,
because its cache entry is never written (finding 2 below).

### Where the time goes, per run

From each run's `perf` payload, plus the cache-write jobs read from
`INFORMATION_SCHEMA.JOBS_BY_PROJECT` by job label (the cache write happens
after the app returns its stages, so `perf` does not include it). Seconds.

| App | Run | Done | BigQuery stages | Census / HUD APIs | Build report | Narrative (wall) | AI calls | Cache write | Rest |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|
| LendSight | Cook 1 | 285 | 85.2 | 8.6 | 7.4 | 114.1 | 12 | 67.3 | 2.6 |
| LendSight | Cook 2 | 229 | 68.7 | 3.3 | 8.8 | 63.8 | 8 | 82.2 | 2.0 |
| LendSight | Lowndes 1 | 139 | 9.9 | 3.2 | 0.3 | 61.4 | 8 | 62.4 | 1.7 |
| LendSight | Lowndes 2 | 151 | 9.8 | 3.3 | 0.5 | 59.6 | 8 | 75.8 | 2.0 |
| BizSight | Cook 1 | 60 | 6.0 | | | 6.8 | 7 | 40.5 | 6.5 |
| BizSight | Cook 2 | 70 | 7.4 | | | 5.9 | 7 | 48.5 | 8.6 |
| BizSight | Lowndes 1 | 58 | 5.3 | | | 6.6 | 7 | 42.6 | 3.7 |
| BizSight | Lowndes 2 | 59 | 6.3 | | | 6.8 | 7 | 42.7 | 3.6 |
| BranchSight | Cook 1 | 32 | 4.0 | | 0.8 | 6.3 | 4 | 20.0 | 0.7 |
| BranchSight | Cook 2 | 31 | 3.4 | | 0.9 | 6.5 | 4 | 19.3 | 0.7 |
| BranchSight | Lowndes 1 | 19 | 1.6 | | 0.1 | 6.8 | 4 | 10.1 | 0.8 |
| BranchSight | Lowndes 2 | 24 | 2.3 | | 0.1 | 6.8 | 4 | 14.7 | 0.4 |
| MergerMeter | Pinnacle / UCB 1 | 42 | 30.4 | | 5.8 (Excel) | none | 0 | 3.1 | 2.8 |
| MergerMeter | Pinnacle / UCB 2 | 37 | 29.6 | | 6.2 (Excel) | none | 0 | not separable | |

Notes on the columns:
- **BigQuery stages** are the app's `bq:*` stages (MergerMeter: its query
  steps). In LendSight Cook they are mostly not BigQuery work: the six jobs ran
  for 7 to 9 s in all, and the rest is downloading about 24,000 grouped rows
  per year (tract × lender × loan purpose) into Python. Lowndes returns 22 rows
  per year.
- **Narrative (wall)**: LendSight makes its calls one after another, so this is
  their sum. BizSight (7 threads) and BranchSight (4) run theirs in parallel.
  BizSight's AI calls are missing from `perf`: its threads start without the
  run's context, so their stages go nowhere (BranchSight copies the context and
  records them). The count of 7 is from the code.
- **LendSight Cook run 1** made 12 calls: the combined table-discussion call
  stopped at its 3,000-token limit (`max_tokens`, 45 s), so the four sections
  were written by their own calls (33 s more). In the other three runs that
  call used 2,406 to 2,590 of 3,000 tokens.
- **Cache write** is the analysis-cache store: one `INSERT` per report section,
  one after another (LendSight 24, BizSight 15, BranchSight 7), then the result
  row and the cache row. Each statement takes 1 to 2.5 s.
- **Rest** is done minus the columns before it: progress bookkeeping,
  aggregation and, in BizSight, chart data.

**Answer to "how much is BigQuery and how much is narrative":**
- **LendSight:** narrative is 25 to 45% of each run and the cache write 25 to
  50%.
  - Cook: BigQuery 69 to 85 s (mostly row download), narrative 64 s (114 s in
    run 1), cache write 67 to 82 s.
  - Lowndes: BigQuery 10 s, narrative 60 to 61 s, cache write 62 to 76 s.
- **BizSight:** BigQuery 5 to 7 s and narrative 6 to 7 s. The cache write is
  41 to 49 s, about 70% of the run.
- **BranchSight:** BigQuery 2 to 4 s, narrative 6 to 7 s, cache write 10 to
  20 s.
- **MergerMeter:** BigQuery 30 s (HMDA peer queries and the goals queries are
  the largest), Excel 6 s, no narrative.

### What the analyses read

Partitioning and clustering are from the table metadata (2026-10-20).

| Table | Size | Partitioned | Clustered | Read by |
|---|--:|---|---|---|
| `dataexplorer.de_hmda` | 33.5 GB, 145.3M rows | `activity_year` (integer range) | `geoid5`, `lei`, `loan_purpose` | LendSight |
| `shared.de_hmda` | 33.5 GB, 145.3M rows | no | no | MergerMeter |
| `bizsight.sb_county_summary` | 342 MB, 1.78M rows | no | no | BizSight, MergerMeter |
| `bizsight.sb_lenders` | 0.6 MB | no | no | BizSight, MergerMeter |
| `branchsight.sod` | 22 MB | no | no | BranchSight, MergerMeter |
| `branchsight.sod_legacy` | 200 MB | no | no | BranchSight, MergerMeter |
| `shared.cbsa_to_county` | 0.4 MB | no | no | all four (each query bills the 10 MB minimum) |

`shared.de_hmda` and `dataexplorer.de_hmda` hold the same rows. Checked
2026-10-20: rows, the sum of `loan_amount` and the count of `is_lmict` match
for every year from 2018 to 2025.

**Why bytes don't scale with geography:**
- **LendSight:** `mortgage_report.sql` filters on `county_state`, which is not
  a clustering column, so each year's query reads the whole year
  (1.8 to 2.9 GB). Partition pruning on `activity_year` works. The statewide
  HHI query filters on `SUBSTR(geoid5, 1, 2)`, which blocks cluster pruning
  (0.33 GB).
- **BizSight:** `sb_county_summary` has no partitions or clusters, so all seven
  queries read every row of the columns they use (0.26 to 0.34 GB each). The
  county is also filtered on the crosswalk side of a join
  (`LPAD(CAST(g.geoid5 AS STRING), 5, '0') = '17031'`) and the year through
  `CAST(a.year AS INT64)`. Neither would prune on a clustered table.
- **BranchSight:** `sod` and `sod_legacy` have no clusters. The one branch
  query filters on the crosswalk's `county_state`, so it reads both tables in
  full (160 MB).
- **MergerMeter:** see ticket 4 below.

### Cached runs (Claude, member)

Three runs per app and geography, 2026-10-20, 17:18 to 17:23 UTC, member account. Seconds to `done` and to `/report-data` 200.

| App | Geography | Runs: done (report) | Cache hit |
|---|---|---|---|
| LendSight | Cook | 5.8 (7.1); 5.7 (6.7); 4.7 (5.7) | yes |
| LendSight | Lowndes | 5.4 (6.6); 5.2 (6.1); 5.0 (5.8) | yes |
| BizSight | Cook | 5.8 (8.0); 5.1 (6.7); 5.9 (27.5) | yes |
| BizSight | Lowndes | 5.0 (6.2); 4.9 (5.7); 4.6 (5.6) | yes |
| BranchSight | Cook | 36.0 (38.0); 33.5 (35.8); 33.0 (34.9) | no (ticket 2) |
| BranchSight | Lowndes | 28.6 (29.8); 25.9 (27.1); 28.3 (30.0) | no (ticket 2) |

- **LendSight and BizSight hit the cache every time, but take 4.6 to 5.9 s to `done`, over the 2 s budget.** Ticket 8 has the breakdown.
- BizSight Cook run 3 took 21.6 s from `done` to `/report-data` 200. The other 17 runs took 0.7 to 2.2 s. The server took 21.2 s on that request (request log). Its BigQuery job ran in 183 ms and ended at 17:19:17.954 (`INFORMATION_SCHEMA.JOBS_BY_PROJECT`); the app logged "Reconstructing from 15 rows" at 17:19:38.7. So about 21 s went between the query ending and the rows reaching the app. Another fresh analysis (LendSight, El Paso County, TX) was running on the same instance at the time. The cause is not established; watch for it after ticket 8.
- **BranchSight never hit the cache** (ticket 2): all six runs were full runs, 26 to 36 s.

### Budget

The query budget stays 20 s uncached. Narrative and the cache write get lines of
their own. Their budget figures are for Jad to set; the figures below are only
a proposal.

| Line | Budget | LendSight Cook / Lowndes | BizSight | BranchSight | MergerMeter |
|---|---|---|---|---|---|
| Query portion, uncached | <= 20 s | **69 to 85 s** / 10 s | 5 to 7 s | 2 to 4 s | **30 s** |
| Narrative, wall | proposed <= 15 s | **60 to 114 s** | 6 to 7 s | 6 to 7 s | n/a |
| Cache write | proposed <= 5 s | **62 to 82 s** | **41 to 49 s** | **10 to 20 s** (fails) | 3 s |
| Cached re-run | <= 2 s | see cached runs | see cached runs | see cached runs | n/a (staff) |

## Pending fixes (scope for the shared PR or the named per-app PR)

| Fix | Where | Status |
|---|---|---|
| BigQuery job labels per app and run (app, environment, job id) so bytes billed attribute exactly | Shared PR (A5 performance) | Done in the shared PR (a71a843) |
| Disable BigQuery's result cache (`use_query_cache=False`) for the duration of an uncached (force-refresh) run, so uncached timings and bytes are real | Shared PR (A5) | Done in the shared PR (a71a843); live once it deploys to testing |
| MergerMeter writes to the analysis cache: `_perform_analysis` must return its result | Shared PR | Done in the shared PR (803dc35); the workbook is also stored in GCS so a cache hit on another instance can serve it |
| MergerMeter AI narrative | none | Out of scope until Jad says otherwise |
| LendSight loads shared `app.js` twice: verify in a browser, then fix | LendSight per-app PR | Pending |
| Placeholder AI disclosures; joke and policy progress lines; jobs that never end on error; BizSight unbacked QA claims; raw exception text in BizSight and MergerMeter | Hygiene PR #208 | Merged 2026-10-07 |

## Part B progress

### Exclusion sentence (spec 04 decision 2, Jad 2026-10-07)

The shared sources block no longer says "Records that cannot be matched with
confidence are excluded". An app may add an exclusion sentence only when it
can name the code that does the excluding.

| App | Outcome | Basis |
|---|---|---|
| LendSight | Dropped | No matching-confidence exclusion in the code. `mortgage_report.sql` applies scope filters only (originations, owner-occupied, 1-4 units, site-built, not reverse), already listed in Methods. Methods' "Data Cleaning" claim (1st/99th percentile loan-amount trimming) had no code behind it and was removed from the web report and PDF. |
| BizSight | Dropped | No matching-confidence exclusion in the code. Related finding for Jad (not changed): Methods says tract-income percentages exclude loans with no tract income classification. That holds for the state and national benchmarks (`generate_benchmarks.py:58`, known-income denominators) but not for the county column (`report_builder.py:292`, `core.py:954`, total-loan denominators), so Section 3 compares county figures against state and national figures built on different denominators. |
| BranchSight | Dropped | No matching-confidence exclusion in the code. `branch_report.sql` keeps every SOD row whose geoid5 maps to the chosen county (no service-type or other filter, as Methods says). The workbook's "Branch Count ... excludes ATMs and loan production offices" described a filter the code does not apply and was replaced. |
| MergerMeter | Dropped | No matching-confidence exclusion in the code. The HMDA scope filters are the ones the user picks in step 4 (action taken, occupancy, units, construction, reverse mortgage), shown with their codes. |

### LendSight (refactor/lendsight-standard)

- On the standard: `lendsight_analysis.html` extends `app_page.html`; the
  report renders in the results column; `/lendsight/report?job_id=` is the
  shareable URL.
- Ticket 13229533844 fixed: the analysis runs 2021 to 2025 from
  `hmda_years` (it was hardcoded to 2020 to 2024); the Years step and the
  header vintage show it.
- Double `app.js` load resolved: the shared `app.js`, jQuery and Select2
  are no longer loaded on the LendSight page.
- `rg 'style="' justdata/apps/lendsight/templates` and `rg "fa-"
  justdata/apps/lendsight` return nothing.
- Raw exception text removed from `/report-data`, `/download`, `/progress`,
  `/analyze` and from `run_analysis` failures.
- Stage timings recorded (`bq:tiered_summary`, `bq:mortgage_report`,
  `census_api`, `hud`, `build_report`, `narrative:*`) and returned by
  `/report-data`.
- Before/after timings on the testing site: after the PR deploys (see the
  PR).

### BizSight (refactor/bizsight-standard)

- On the standard: `bizsight_analysis.html` extends `app_page.html`; the
  report renders in the results column; `/bizsight/report?job_id=` is the
  shareable URL. Built on the shared AppRun and AppReport modules, which
  LendSight now also uses.
- Ticket 13229487819: `config.SB_YEARS` (2020 to 2024) is the single
  source for the page, header vintage, default request and validation;
  2024 is the latest year loaded (2025 is not). About 300 year literals
  remain in core.py, report_builder.py and ai_analysis.py (platform ticket
  11535494229); a test pins them to SB_LATEST_YEAR.
- Fixed: /download failed for cached or cross-instance reports (it required
  the in-process progress record) and wrote "Unknown County" into
  workbooks; the summary's LMI change was an estimate; Methods' Suggested
  Citation had "[County Name], [State]" placeholders; five progress step
  names were silently dropped by the tracker.
- `rg 'style="' justdata/apps/bizsight/templates` and `rg "fa-"
  justdata/apps/bizsight` return nothing.
- Stage timings recorded and returned by `/report-data`.
- Follow-ups (fix/bizsight-branchsight-followups, Jad 2026-10-13): every
  tract income share, on the page and in the workbook, divides by loans
  with a tract classification (the state and national basis); Section 3
  notes the excluded count; the cache key carries report revision 2 so
  older results are not served. Section 3's state and national
  middle-or-upper shares were 0.0% (wrong benchmark key) and are fixed.
  Section 1 says CRA data covers loans originated or purchased (12 CFR
  228.42). The workbook's change column and year notes said 2018.

### MergerMeter (refactor/mergermeter-page-standard; staff only)

- On the standard: `mergermeter_analysis.html` extends `app_page.html` (32
  lines; it was 2,529 with inline CSS and jQuery). Steps: 1 Geography
  (assessment areas or national), 2 Acquirer and target, 3 Years, 4 Options.
  Built on AppRun (FormData body, 30-minute run limit) and AppReport.
- Analysis and outputs unchanged: the page posts the former page's form
  fields and values; checked locally by capturing the form `/analyze`
  received, and by a full run whose workbook previews as before.
- `/report?job_id=` is the shareable URL (it used to render the Goals
  Calculator, still at `/goals-calculator?job_id=`); `/report-data` is a
  readiness check with the run's metadata and stage timings.
- `rg 'style="' justdata/apps/mergermeter` and `rg "fa-"
  justdata/apps/mergermeter` return nothing; 14 unreachable templates were
  deleted.
- Stage timings (step clock around the progress updates): locally the
  Mortgage Goals query is the slowest step (10.1 s of a 42 s run), the one
  to note for a later optimization ticket.
- Cache and usage writes (found 2026-10-15): every MergerMeter write to
  `analysis_cache` and `usage_log` failed with 403 `bigquery.tables.updateData`,
  on testing (`cache_testing`, since at least 2026-10-08) and on production
  (`cache.usage_log`, runs on 09-17, 09-23 and 09-28).
  `mergermeter@justdata-ncrc.iam.gserviceaccount.com` had `dataViewer` and
  `jobUser` only. Jad is granting `roles/bigquery.dataEditor` on the `cache` and
  `cache_testing` datasets only; staging (`JUSTDATA_ENV=staging`) and
  production both write `cache`, so no third dataset needs it.
- Correction: the 15-second second MergerMeter run on 2026-10-13 was not an
  analysis-cache hit. No MergerMeter cache row could be written, and the
  10/13 logs show the store failing.

### BranchSight (refactor/branchsight-standard)

- On the standard: `branchsight_analysis.html` extends `app_page.html`; the
  report renders in the results column; `/branchsight/report?job_id=` is the
  shareable URL. Built on AppRun and AppReport.
- Time to interactive (entry page, required item): before, 5 Lighthouse
  runs on testing 2026-10-07: 1.9, 1.2, 1.5, 1.2, 1.9 s (audit run: 2.1 s).
  After: see the PR (measured after deploy).
- Years: `config.SOD_YEARS` (2021 to 2025; 2025 is the latest year in
  `branchsight.sod`) is the single source.
- Fixed: 35 counties ran as a different county (substring county match,
  e.g. Johnson County, Kansas ran as Johnson County, Arkansas); every
  Excel, ZIP and CSV download of a stored result failed; the Geography
  Context section never showed (keyless Census API calls); "done" could
  reach the page before the result was stored; five per-year queries plus
  five repeat county lookups became one parameterised query; the
  narratives run in parallel; exception text no longer reaches users.
- `rg 'style="' justdata/apps/branchsight/templates` and `rg "fa-"
  justdata/apps/branchsight/templates` return nothing.
- Stage timings recorded and returned by `/report-data` (and, from this PR,
  kept through the analysis cache for LendSight and BranchSight).
- Follow-up (Jad 2026-10-13): Geography Context counts tracts from the
  FFIEC census data (`shared.census`) on the branch flags' definitions
  (income level low or moderate; minority share 50% or more), replacing the
  ACS county-median basis. Methods' MMCT definition says "50% or more",
  which is what the flags do.

### FDIC SOD 2026 and FFIEC census 2026 (Workflow ticket 13277163649)

- Promoted 2026-10-15 (hdma1-242116 at 20:21 UTC, justdata-ncrc at 20:23 UTC),
  one transaction per project. `sod` holds 2026 only (75,859); `sod_legacy`
  2017 to 2025 (740,974). `geo.census` and `shared.census` hold the FFIEC 2026
  file only (87,276); `geo.census_legacy` and the new `shared.census_legacy`
  2018 to 2025 (652,634). Each justdata-ncrc table matches its hdma1 twin by
  fingerprint. Record: L5 Projects/JustData Frontend Specs/06-sod-2026-load.md.
- Years: `shared/core/sod_years.py` (`SOD_LATEST_YEAR = 2026`) is the single
  source. BranchSight runs 2022 to 2026; MergerMeter, BranchMapper and
  DataExplorer read 2026. First run per county (BranchSight) or bank pair
  (MergerMeter) after the deploy is uncached.
- MergerMeter reference pair from 2026: Pinnacle Bank / United Community Bank
  (Synovus merged into Pinnacle Bank 2026-01-02).
- Staging tables, drop on 2026-10-22 (promotion + 7 days):
  `hdma1-242116.branches.sod_stg_2026`, `hdma1-242116.branches.sod_stg_2026_raw`,
  `hdma1-242116.geo.census_stg_2026`, `justdata-ncrc.branchsight.sod_stg_2026`,
  `justdata-ncrc.shared.census_stg_2026`. Kept permanently:
  `sod_2026_tract_method` in both projects.
- `justdata-ncrc.branchsight.branch_hhi_summary` still holds 2025 aggregates.
  Nothing reads it; whether to delete it is a decision for the consolidation
  work, not this load.

## Findings that matter before testers

These were live on the testing site at audit time. Items 1 to 5 are fixed in
the hygiene PR #208 (merged 2026-10-07); the rest are tracked above or in the defect list.

1. **Placeholder text in reports testers can open.** The web AI Disclosure in LendSight is lorem ipsum plus "[This disclosure text will be provided by Rose/Legal]". In BranchSight it is "[LOREM IPSUM PLACEHOLDER - TO BE REPLACED]" plus lorem ipsum.
2. **Joke progress messages.** BranchSight picks one at random while building, from a list that includes "Russell hates this.", "Support the CFPB.", "Beep boop beep." and "I know it's awesome, right?". "Support the CFPB" is a policy statement. LendSight and BizSight progress text is emoji-laden throughout.
3. **Jobs that never finish.** In LendSight and BranchSight, a run with zero rows, or with every query failing, never reaches "done" or "error". The tracker drops the `'error'` step because it isn't one of its known step names, so the page waits indefinitely.
4. **Unbacked claims in the BizSight report.** "All AI-generated narratives are reviewed for accuracy against the source data" and "NCRC performs systematic quality assurance" have no code behind them. The AI disclosure names Sections 1 and 5, but narratives appear in Sections 1 to 5.
5. **Raw error text shown to users.** BizSight and MergerMeter show raw exception text, for example "Query error: …".

## Other defects (for tickets)

- **Shared progress tracker** (`shared/utils/progress_tracker.py:42`) silently ignores step names outside its fixed list. Messages lost:
  - LendSight: `fetching_data`, `saving`
  - BizSight: `fetching_data`, `section_1`, `section_3`, `section_4`, `saving`
  - BranchSight: `fetching_data`, `doing_something_cool`
- **LendSight:**
  - `shared/web/static/js/app.js` loads twice on the entry page. Its top-level `const` declarations should make the second load throw. Inferred from code, not run.
  - The app's own `static/js/app.js` and `style.css` are never served: `url_for('static')` resolves to `shared/web/static`.
- **BranchSight:** (both fixed in the BranchSight PR)
  - `done` can fire before the result is stored, so `/report-data` returns 404 in that gap. The front end retries to cover it.
  - Map and population-chart code is never called.
- **BranchMapper** (not a tester app; found in the BranchSight PR, not changed): `data_utils.find_exact_county_match` has the same substring county match that ran 35 BranchSight counties as a different county. Ticket draft below (Jad creates it).
- **BizSight:**
  - `/download` ignores the in-memory fallback, so export returns 404 when the cache write failed.
  - The in-memory fallback itself fails: when the cache write fails, `run_job` stores the raw result, and `/report-data` returns 500 on its DataFrames ("The truth value of a DataFrame is ambiguous", `clean_for_json`). Found in a local check 2026-10-13; fixed in #215 (LendSight had the same failure; also fixed there).
  - Map code is dead.
- **MergerMeter:**
  - It never writes results to the analysis cache, because `_perform_analysis` returns None. Fixed in the shared PR (803dc35); stored entries could not be served until #214.
  - `single_bank_mode` is sent by the UI but dropped by the blueprint. Not changed: the page rebuild keeps the analysis as it is.
  - The assessment-area template link is missing the `/mergermeter` prefix. Fixed in the page rebuild.
  - The upload help text says "PDF or Text" but only JSON/CSV is accepted. Fixed in the page rebuild.
  - The Goals Calculator posts to `/api/save-goals-config`, which exists only in the standalone app.
  - `/progress/<job_id>` has `login_required` but no `require_access`.
  - Orphan partials: `_analysis_*` and `_mergermeter_report_*`. Deleted in the page rebuild, with `analysis_template.html` and `mergermeter_report.html`.
- **Dead templates:** `analysis_template.html` in LendSight, BizSight and MergerMeter. Only MergerMeter's standalone ops app renders the name.

## Ticket drafts: analysis speed and cost (2026-10-20, for the Workflow board)

From the uncached batch above. Created on the Workflow board 2026-10-22:
1 = 13360124454, 2 = 13360117509, 3 = 13360118475, 4 = 13360119798,
5 = 13360117507, 6 = 13360117255, 7 = 13360117162, 8 = 13360119391,
9 = 13360099262, plus 13360117508 for the gunicorn and Cloud Run settings.
Fixes in review: 1 and 2 in #229, 9 in #227. All three merged 2026-10-22.
Measured on testing after #229 (member, Wake County, NC, never cached): the
cache write took 4.9 s for LendSight (24 sections) and 6.5 s for BranchSight
(11 sections, `raw_data` included), from the BigQuery job history; the
BranchSight repeat run was a cache hit, done in 6.7 s. Ticket 10's settings
(13360117508) are in #232: memory stays 2 GiB, as the peak hourly p99 on
testing from 2026-10-15 to 2026-10-20 was 59.0% (the uncached batch), under
Jad's 60% line. These are cost and speed
findings, except ticket 2, which is a defect. Spec 05 changes no queries. Byte
estimates marked "measured" come from one query run on 2026-10-20 with the
proposed filter (label `purpose=spec05-bytes-estimate`). The rest are estimates
to confirm after the fix.

**1. Analysis cache write takes 10 to 82 s per run (all Sight apps). Priority
High.**
- `store_cached_result` (`shared/utils/analysis_cache.py`) writes each report
  section with its own `INSERT` statement, one after another, then the result
  row and the cache row. LendSight has 24 sections, BizSight 15 and
  BranchSight 7, and each DML statement takes 1 to 2.5 s.
- The user waits for this, because the job is marked done only after the
  write.
- Fix: write all sections in one statement (one multi-row `INSERT`, or an
  `UNNEST` of an array parameter). Keep the order: sections, then the result
  row, then the cache row.
- Expected: about 3 to 5 s per run in place of 62 to 82 s (LendSight), 41 to
  49 s (BizSight) and 10 to 20 s (BranchSight). That takes BizSight from about
  60 s to about 20 s.

**2. BranchSight results are never stored in the analysis cache on testing.
Bug, priority High.**
- The seventh section `INSERT` (`raw_data`, the only frame not cleaned of NaN)
  fails with "syntax error while parsing value - invalid literal; last read:
  '"state": N'; error in PARSE_JSON expression".
- `store_cached_result` raises, so no result row and no cache row are written.
  The six sections already written stay behind as orphans.
- `run_job` then keeps the result in its in-memory fallback.
- Consequences:
  - Every BranchSight run is a full run; the cached re-run never hits.
  - `/report-data` works only if the same Cloud Run instance serves it.
  - Usage rows record no cache.
- Seen in `INFORMATION_SCHEMA.JOBS_BY_PROJECT` on `cache_testing` only:
  2026-10-08 (1), 2026-10-15 (5), 2026-10-20 (2). Not seen on `cache`
  (staging, production) in 60 days.
- Fix:
  - Pass every section through `sanitize_nan_values`.
  - Consider not storing `raw_data` at all: `/download` rebuilds the frames.
  - Delete the orphaned section rows (`analysis_result_sections` rows whose
    `job_id` has no `analysis_results` row) once the fix is live.
- Done 2026-10-22 (Jad approved): fixed in #229. The cleanup `DELETE` on
  `cache_testing.analysis_result_sections` (BranchSight rows with no result
  row, older than one hour) removed **96 rows from 16 jobs**, created
  2026-10-08 to 2026-10-20. A recount afterwards found 0 orphaned rows.

**3. LendSight HMDA query reads a whole year per county. Priority Medium.**
- Tables: `dataexplorer.de_hmda` (partitioned on `activity_year`, clustered
  on `geoid5`, `lei`, `loan_purpose`) and `shared.cbsa_to_county`.
- Queries without a pushdown geography filter:
  - `mortgage_report.sql` filters `h.county_state = @county`, which is not
    clustered, so each of the five yearly queries reads the full year (1.8 to
    2.9 GB). The year filter prunes partitions correctly.
  - `state_hhi` filters `SUBSTR(h.geoid5, 1, 2) = @state_fips`, which blocks
    cluster pruning (0.33 GB).
- Fix:
  - `mortgage_report.sql`: filter `h.geoid5 = @geoid5`.
  - `state_hhi`: filter `h.geoid5 BETWEEN '<ss>000' AND '<ss>999'`.
  - Use query parameters in place of `.replace()`.
- Expected bytes, measured:
  - Cook, 2025: 53 MB per year in place of 2.2 GB.
  - Lowndes, 2025: 25 MB per year.
  - Illinois statewide HHI: 218 MB in place of 327 MB.
- Expected bytes per run: about 0.55 GB (Cook) and 0.3 to 0.4 GB (Lowndes), in
  place of 11.5 and 12.7 GB. Cost about $0.003 per run in place of $0.07.
- Speed, a separate item: the BigQuery stage in Cook is 69 to 85 s, of which
  BigQuery itself is 7 to 9 s. The rest is downloading about 120,000 grouped
  rows through the row iterator. Fix by using the BigQuery Storage Read API
  for the download (`google-cloud-bigquery-storage`), or by grouping less
  finely in SQL. Expected: the query portion within the 20 s budget. That is
  not measured; confirm it after the fix.

**4. MergerMeter scans 105 GB of HMDA per run. Priority High.**
- Tables:
  - `shared.de_hmda`: not partitioned, not clustered. Read by 10 queries,
    105.1 GB.
  - `bizsight.sb_county_summary`: 6 queries, 1.15 GB.
  - `branchsight.sod` and `sod_legacy`: 7 queries, 0.49 GB.
  - `bizsight.sb_lenders` and `shared.cbsa_to_county`.
- Queries without a pushdown filter: every HMDA query filters on year, LEI and
  county list, but nothing prunes.
  - The table has no partitions or clusters.
  - The year filter is `CAST(h.activity_year AS STRING) IN ('2023', ...)` and
    the lender filter is `CAST(h.lei AS STRING) = ...`. Those casts would also
    block pruning on a partitioned table.
- Fix:
  - Read `dataexplorer.de_hmda`, which holds the same rows (checked by year,
    see above) and is partitioned and clustered. Or partition and cluster
    `shared.de_hmda` the same way.
  - Filter `h.activity_year IN (2023, 2024, 2025)` and `h.lei = '...'`
    without casts.
- Expected bytes:
  - Measured: the peer query for United Community Bank's 103 counties,
    2023 to 2025, reads 0.83 GB in place of 11.1 GB.
  - Estimated per run: 5 to 8 GB of HMDA, plus the small business and SOD
    reads. Cost about $0.04 to $0.06 per run in place of $0.61.
- The HMDA step also takes about 10 s of the 30 s query portion (MergerMeter
  query steps above); expect it to fall with the bytes.

**5. BizSight reads the whole small business summary table on every query.
Priority Medium.**
- Tables: `bizsight.sb_county_summary` (no partitions, no clusters),
  `bizsight.sb_lenders` and `shared.cbsa_to_county`.
- Queries without a pushdown filter: all seven.
  - The county filter is on the crosswalk:
    `LPAD(CAST(g.geoid5 AS STRING), 5, '0') = '17031'`.
  - The state filter uses `SUBSTR(...)`.
  - The year filter is `CAST(a.year AS INT64)`.
- Fix:
  - Rebuild `sb_county_summary` partitioned on `year` (integer range) and
    clustered on `geoid5`. That is a table change in `justdata-ncrc`; the
    yearly load (Step E) must keep the layout.
  - Filter `a.geoid5` and `a.year` directly.
  - The same table serves MergerMeter's small business queries (ticket 4).
- Expected: about 0.1 to 0.15 GB per run in place of 1.8 GB (most queries at
  the 10 MB minimum; the national benchmark reads one year). An estimate. Speed
  barely changes: BizSight's BigQuery stages are already 5 to 7 s.
- Also: BizSight's AI-call stages never reach `perf`, because its
  `threading.Thread` workers start without the run's context. Start them with
  `contextvars.copy_context().run`, as BranchSight does. Their `[narrative]`
  log lines do print, with no app or job, and two threads printing at once can
  land in one log entry.

**6. BranchSight reads both SOD tables in full. Priority Low.**
- Tables: `branchsight.sod`, `branchsight.sod_legacy` (no clusters; `year` is
  a STRING) and `shared.cbsa_to_county`.
- The one branch query filters on the crosswalk's `county_state`, so it reads
  160 MB.
- Fix: cluster both tables on `geoid5` and `year`, and filter `s.geoid5`
  directly. The yearly SOD load must keep the layout.
- Expected: 30 to 60 MB per run in place of 181 MB (an estimate). It costs
  $0.001 a run now, so this is for consistency, not money.

**7. LendSight narrative: eight calls in a row, 60 to 114 s. Priority
Medium.**
- LendSight makes its AI calls one after another: the combined table
  discussions (26 to 45 s), three Section 2 discussions (3 to 5 s each), key
  findings, trends and two table narratives.
- None of them depends on another's output (all take `ai_data`).
- The combined call stopped at its 3,000-token limit in one of four runs. The
  four fallback calls then added 33 s, and that run's narrative took 114 s. In
  the other runs the combined call used 80 to 86% of its limit.
- Fix, in order of saving:
  1. Run the calls in parallel, as BizSight and BranchSight do, copying the
     context so their stages are recorded. The narrative then takes as long as
     the longest call, 26 to 29 s. That saves about 33 s.
  2. Also replace the combined call with its four single-section calls, which
     already exist as the fallback (7 to 10 s each). The narrative then takes
     about 10 s, which saves about 50 s and removes the cut-off risk.
- Shorter prompts would save little: input is 1,300 to 10,800 tokens, and time
  follows output length.
- Check the Anthropic rate limit for 11 calls at once per run with several
  users.
- Expected LendSight Lowndes after tickets 1 and 7: about 28 s in place of 139
  to 151 s. Cook also needs the download fix in ticket 3.

**8. A cache hit takes 4.6 to 5.9 s; the budget is 2 s. Priority Medium.**
- On a hit, `/analyze` makes four BigQuery calls before it answers:
  - it reads the cache row (about 0.25 s);
  - it reads every stored section to count them, against `min_sections`
    (0.3 to 0.8 s);
  - it runs an `UPDATE` of `access_count` (DML, 1.5 s on average);
  - it inserts the usage row (DML, 1.1 s).
- `/report-data` then reads the sections again.
- Figures are from the 12 member cached runs, 2026-10-20.
- Fix:
  - Count the sections in SQL, not by downloading them.
  - Do the `UPDATE` and the usage insert after answering (a background task),
    or drop the `UPDATE` and count hits from `usage_log`.
- Expected: about 1 s to done.

**9. A progress stream for an unknown job never ends, and four of them stop
the site. Bug, priority High.**
- What happened on testing, 2026-10-20 (Cloud Logging, request logs):
  - During the spec 05 error-state checks, four report pages were opened with
    a job ID that does not exist (LendSight 17:35, BizSight 17:36,
    BranchSight 17:37 and 17:39 UTC).
  - Each page's `/progress/<job_id>` stream stayed open for 3,601 s, which is
    the service's request timeout (3,600 s).
  - With those four open, every other request waited. `/health` requests sent
    from 17:42 were answered at 18:35:38, when the first stream timed out. The
    site was unusable from about 17:40 to 18:35 UTC.
  - No restart or redeploy was needed; the instance shut down idle at 18:54.
- Why:
  - `get_progress` (`shared/utils/progress_tracker.py`) returns
    `{'step': 'Processing...', 'done': False}` for a job it does not know, on
    purpose, in case progress was lost.
  - `sse_response` (`backend/jobs.py`) loops until `done` or `error`, so for
    an unknown job it never stops. A browser leaving does not end it: Cloud
    Run kept each stream open to the container until its timeout.
  - `/report-data` answers 202 (still running) for an unknown job, so the page
    opens the stream instead of showing the error state.
  - gunicorn runs 1 worker with 4 threads (`start.sh`). Each stream holds a
    thread.
  - The service's concurrency is 160, so Cloud Run keeps sending requests to
    the busy instance instead of starting another. `justdata-test` and
    `justdata` have the same settings (timeout 3,600 s, concurrency 160).
- Real-world trigger, not only a test: a report link opened after the
  instance that ran the job has restarted, when the job is not in the
  analysis cache (every BranchSight job on testing, ticket 2). Four such tabs
  stop the site for an hour.
- Fix:
  - `/report-data` and the stream tell an unknown job from a running one.
    Unknown means not in the progress store, the progress file or the
    analysis cache. Answer 404, and send an error event, so the page shows the
    error state with its reference.
  - Cap any stream's life: end it with an error event after a set time with
    no change (for example 10 minutes; the longest run seen is under 5).
  - Set Cloud Run concurrency to the number of threads, or raise the threads,
    so a busy instance does not queue requests. That is a service setting,
    Jad's to change.
- Expected: an unknown job's page shows the error state within a second, and
  no stream outlives its job.

## Ticket draft: BranchMapper wrong-county lookup (for the Workflow board)

Ready to paste; Jad creates the item.

**Title:** BranchMapper: county lookup matches part of the name, so some counties show another county's branches

**Description:**
`/branchmapper/api/branches` resolves the requested county with
`find_exact_county_match` (`justdata/apps/branchmapper/data_utils.py:118`),
called from `execute_branch_query` (line 331). The lookup selects
`county_state` values that contain the county name and contain the state
name (`LIKE '%name%' AND LIKE '%state%'`), then uses the first row in
alphabetical order. When another county's name or state contains the
requested one, BranchMapper shows the wrong county's branches with no
warning. Examples from the same lookup in BranchSight: Johnson County,
Kansas returns Johnson County, Arkansas ("Kansas" is inside "Arkansas");
Smith County, Texas returns Deaf Smith County, Texas. A read-only check of
`shared.cbsa_to_county` found 35 counties affected in BranchSight. The
query is also built by string interpolation rather than query parameters.

**Who it affects:** staff using BranchMapper (it is not a tester app).

**Fix:** use the exact match BranchSight now uses
(`branchsight.data_utils.exact_county_matches`: a parameterised
`LOWER(county_state) = LOWER(@county)` query), fall back to a substring
match only when it returns exactly one row, and pass the county and year
to the branch query as query parameters (BranchSight PR #212, commits
399d40b and efda23a).

**Acceptance:** Johnson County, Kansas and Smith County, Texas each return
their own branches; a test covers both names; no county or year value is
interpolated into SQL.

## Unintended writes to `firebase_analytics.ai_usage` (exclude from analytics)

Not deleted (Jad, 2026-10-13). The table has no id column, so the rows are
identified by timestamp (as stored, UTC), app and model. All are
`provider = 'claude'`, `model = 'claude-sonnet-5'`, `report_type = 'unknown'`.

1. **BranchSight, 4 rows**, local fixture run for PR #212, 2026-10-07:
   | timestamp | input tokens | output tokens | cost (USD) |
   |---|---|---|---|
   | 2026-10-07T21:44:04.490019 | 1,791 | 275 | 0.009498 |
   | 2026-10-07T21:44:10.819346 | 1,469 | 391 | 0.010272 |
   | 2026-10-07T21:44:16.783582 | 1,520 | 427 | 0.010965 |
   | 2026-10-07T21:44:23.656974 | 1,333 | 455 | 0.010824 |
2. **BizSight, 88 rows**, local before/after runs of the Section 3
   denominator (Cook and Lowndes, three runs), 2026-10-13: every
   `app_name = 'bizsight'` row with timestamp from 2026-10-13T14:42:39.372547
   to 2026-10-13T14:51:40.702860 (22 rows at 14:42, 29 at 14:45, 37 at
   14:51; $0.65 in total). The runs unset the AI key variables, but the
   app found its key another way; later local runs stub `ai_provider`.

Filter for analytics:

```sql
WHERE NOT (app_name = 'branchsight' AND timestamp BETWEEN '2026-10-07T21:44:04' AND '2026-10-07T21:44:24')
  AND NOT (app_name = 'bizsight' AND timestamp BETWEEN '2026-10-13T14:42:39' AND '2026-10-13T14:51:41')
```

The four BranchSight rows from 2026-10-08T15:02 are not from this work.

## Timing method (`scripts/time_analysis.py`)

- **What it records:** the time to the first progress event, to `done`, and to `/report-data` returning 200. It also records every progress step with its time, whether the run was a cache hit, any error, and each run's UTC window. Once the shared PR adds a `perf` payload, the per-stage timings come from that.
- **Uncached runs:** these run with BigQuery's result cache disabled for the duration of the run, via the shared PR's switch above. Until that lands, uncached timings and bytes would be understated, so Jad's uncached runs wait for it.
- **Bytes billed:** the `bytes` subcommand sums `total_bytes_billed` from `region-us.INFORMATION_SCHEMA.JOBS_BY_PROJECT` for the app's service account (`<app>@justdata-ncrc`) inside each run window.
  - Since the shared PR (a71a843), every analysis job carries a `job=<job_id>` label, and the subcommand matches on it. Runs from before the labels fall back to the service account and time window.
  - Since the same PR, an uncached (force-refresh) run turns BigQuery's result cache off. The `bq_cache_hits` column shows any hit.
- **Plan, per app and geography:** 2 uncached runs (Jad, staff) and 3 cached runs (Claude, member). MergerMeter is all Jad's (staff only). It has written the analysis cache since the shared PR (803dc35); on `cache_testing` since the dataset grant of 2026-10-15.
