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
| Timing: cached analysis (3 runs × 2 geographies) | | | | | Timing, member (Claude): **pending** Jad's uncached runs, which populate the cache |
| Timing: uncached analysis (2 runs × 2 geographies), BigQuery bytes billed | | | | | Timing, staff (Jad): **pending** the shared PR's query-cache switch (see Timing method) |
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

The analysis timings (cached runs by Claude, uncached by Jad) are pending; see
the Timing method section.

## Pending fixes (scope for the shared PR or the named per-app PR)

| Fix | Where | Status |
|---|---|---|
| BigQuery job labels per app and run (app, environment, job id) so bytes billed attribute exactly | Shared PR (A5 performance) | Done in the shared PR (a71a843) |
| Disable BigQuery's result cache (`use_query_cache=False`) for the duration of an uncached (force-refresh) run, so uncached timings and bytes are real | Shared PR (A5) | Done in the shared PR (a71a843); live once it deploys to testing |
| MergerMeter writes to the analysis cache: `_perform_analysis` must return its result | Shared PR | Done in the shared PR (803dc35); the workbook is also stored in GCS so a cache hit on another instance can serve it |
| MergerMeter AI narrative | none | Out of scope until Jad says otherwise |
| LendSight loads shared `app.js` twice: verify in a browser, then fix | LendSight per-app PR | Pending |
| Placeholder AI disclosures; joke and policy progress lines; jobs that never end on error; BizSight unbacked QA claims; raw exception text in BizSight and MergerMeter | Hygiene PR #208 | Merged 2026-10-07 |

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
- **BranchSight:**
  - `done` can fire before the result is stored, so `/report-data` returns 404 in that gap. The front end retries to cover it.
  - Map and population-chart code is never called.
- **BizSight:**
  - `/download` ignores the in-memory fallback, so export returns 404 when the cache write failed.
  - Map code is dead.
- **MergerMeter:**
  - It never writes results to the analysis cache, because `_perform_analysis` returns None. Fixed in the shared PR (803dc35).
  - `single_bank_mode` is sent by the UI but dropped by the blueprint.
  - The assessment-area template link is missing the `/mergermeter` prefix.
  - The upload help text says "PDF or Text" but only JSON/CSV is accepted.
  - The Goals Calculator posts to `/api/save-goals-config`, which exists only in the standalone app.
  - `/progress/<job_id>` has `login_required` but no `require_access`.
  - Orphan partials: `_analysis_*` and `_mergermeter_report_*`.
- **Dead templates:** `analysis_template.html` in LendSight, BizSight and MergerMeter. Only MergerMeter's standalone ops app renders the name.

## Timing method (`scripts/time_analysis.py`)

- **What it records:** the time to the first progress event, to `done`, and to `/report-data` returning 200. It also records every progress step with its time, whether the run was a cache hit, any error, and each run's UTC window. Once the shared PR adds a `perf` payload, the per-stage timings come from that.
- **Uncached runs:** these run with BigQuery's result cache disabled for the duration of the run, via the shared PR's switch above. Until that lands, uncached timings and bytes would be understated, so Jad's uncached runs wait for it.
- **Bytes billed:** the `bytes` subcommand sums `total_bytes_billed` from `region-us.INFORMATION_SCHEMA.JOBS_BY_PROJECT` for the app's service account (`<app>@justdata-ncrc`) inside each run window.
  - The client sets no job labels, so concurrent traffic under the same service account would also be counted. The shared PR should add job labels (app, environment, job id) so bytes can be attributed exactly.
  - The client sets `use_query_cache=True`. A second "uncached" app run within 24 hours can still hit BigQuery's own result cache and bill 0 bytes. The `bq_cache_hits` column shows this.
- **Plan, per app and geography:** 2 uncached runs (Jad, staff) and 3 cached runs (Claude, member). MergerMeter is all Jad's, and because it never writes the analysis cache, its "cached" runs are recomputed.
