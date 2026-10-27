# Release checklist, testing site, 2026-10-15

Spec 05 (L5: Projects/JustData Frontend Specs/05-qa-and-release.md, revised
2026-10-15). Site: https://justdata-testing-854699313651.us-east1.run.app,
serving `testing` at 5ea2248 (#226) during these checks. Accounts by role only:
"signed out", "member" (the test account in `~/.justdata-test.env`), "admin"
(Jad, Part 2).

Status: **in progress.** Analysis lines run 2026-10-20 as member on Cook
County, IL and Lowndes County, GA (BranchSight also Alpine County, CA for the
empty state). Timings, bytes and nine ticket drafts are in
`audit/app-standardization-matrix.md` ("Analysis timings and bytes" and
"Ticket drafts: analysis speed and cost"). Still open in Part 1: the error
state (see below). Part 2 is Jad's.

**Outage caused by these checks, 2026-10-20.** Opening report pages for a job
ID that does not exist (to reach the error state) left four `/progress`
streams open for the full 3,600 s request timeout. With gunicorn at 1 worker
and 4 threads, and Cloud Run concurrency at 160, the testing site answered
nothing from about 17:40 to 18:35 UTC. It recovered by itself when the first
stream timed out; no restart or redeploy. Ticket draft 9 in the matrix
(Workflow 13360099262); hotfix #227.

**Open PRs from this pass (2026-10-22), all into `testing`:** #227 progress
stream ends for an unknown job; #229 BranchSight reaches the analysis cache and
the cache write is one statement (gate work for the login build); #230
`/admin/users` 500 (Jay round 2 #1); #231 every lender table names its year
(Jay round 2 #11).

Key: PASS, FAIL, FIXED (failed, fixed in this PR), HELD (not run yet), NOTE.

## Part 1 (Claude: signed out and member)

### Access and wayfinding

| Line | Result | Evidence |
|---|---|---|
| `check_tester_gate.py` signed out and `--role member` | PASS | 17 of 17 rows, including the https redirect row (308 to `https://…/analytics/`) |
| Drawer, `/apps` and landing roster list exactly the three Sight apps for member | PASS | All three: bizsight, branchsight, lendsight. No "Staff tools", no "In consolidation", no MergerMeter |
| Member is blocked from the seven staff and consolidation routes | PASS | `/mergermeter/`, `/branchmapper/`, `/dataexplorer/`, `/dotlender/`, `/status`, `/analytics/`, `/admin/users`: each 302 to `/` |
| Signed out sees only `/`, `/about`, `/contact` | PASS | Those three open; the seven above plus `/apps` and the three apps return the restricted page (200 with its logo marker) |
| Link crawl as member, internal links | PASS | Every internal href on `/`, `/apps`, `/about`, `/contact` and the three app pages: 200 open, or a 308 that only adds a trailing slash. No link to `/privacy` or `/terms` |
| External links | NOTE | Five: ncrc.org, ncrc.org/cra/, census.gov developers, consumerfinance.gov HMDA, ffiec.gov craproducts. The ncrc.org ones are covered by the network tests. ffiec.gov answers scripts with 403 (Cloudflare), so it is checked by hand in Part 2 or left as is |
| `make test-network` | PASS | Run once: 10 passed (8 report links, 2 SOD year checks). Whether any link needed the retry is unknown: the retry was silent. Retries now print a warning naming the link (this PR) |
| Active nav item | PASS | `/`, `/apps`, `/lendsight`, `/bizsight` and `/branchsight` each highlight their own item. `/about` and `/contact` have no drawer item, so nothing is highlighted (expected) |
| Header shows the app name on app routes | PASS | LendSight, BizSight, BranchSight; "Apps" on `/apps`; none on `/`, `/about`, `/contact` |
| Only the shell header on member-reachable templates | PASS | `rg "<header"`: the shell's `partials/_header.html` is the only one a member reaches |
| Own headers on staff pages | NOTE | Not the shell header: `/status` (`status-dashboard.html`) and the admin dashboard (`admin-dashboard.html`) have their own; the MergerMeter Goals Calculator, BranchMapper and DataExplorer include the old `shared_header.html`. Staff only; a ticket, not a fix here. `analysis_template.html` has one too but no route renders it |

### Landing (`/`)

| Line | Result | Evidence |
|---|---|---|
| Signed out, full page renders | PASS | Eight sections, hero to closing band |
| Sign in opens the modal | PASS | Modal shown, Sign In tab active, focus in the email field; Escape closes it |
| Create an account opens the register tab | PASS | Modal shown with the register view and tab active |
| Member CTA reads "Open the apps" | PASS | |
| Figures traced to source | PASS | Inventory: HMDA 2018 to 2025 (`hmda_years.py`; `shared.de_hmda` holds 2018 to 2025); FDIC SOD 2017 to 2026 (`sod_years.py`); CRA small business 2020 to 2024 (`landing_content.py`, the range BizSight uses; `bizsight.sb_county_summary` holds 2007 to 2024); Census ACS "5-year estimates" (no year, ticket 13229522646). Strip: 8 years of mortgage records, 10 years of branch records (computed from the same settings); "50 states, DC and Puerto Rico" (`shared.cbsa_to_county` has 52 state values); 4 federal datasets. No placeholder |
| Methodology link resolves | NOTE | "How each tool is built →" goes to `/apps` (approved 2026-10-07 while no methodology page exists). Signed out, that link shows the restricted page. A decision for Jad, not a defect |
| Hero within 100vh at 1366x768; no horizontal scroll at 390 | PASS | Hero bottom at 711 px; no horizontal scroll at 390 |
| Lighthouse desktop, signed out (>= 90 / 95 / 95) | PASS | Three runs: Performance 96, 96, 96; Accessibility 100; Best Practices 96. LCP 1.1 to 1.2 s, TBT 0 ms, CLS 0 |
| Console errors, signed out | NOTE | One: a 401 from `/api/auth/verification-status`, which `shell-auth.js` requests 1.5 s after load even when signed out. The only Best Practices deduction. Not changed here: skipping it client-side risks hiding the verification banner from a signed-in user whose Firebase state loads late |

### Launcher (`/apps`, member)

| Line | Result | Evidence |
|---|---|---|
| No locks, no request panel; the three apps in their two groups | PASS | 0 locked items; no request-access panel |
| BranchSight card reads "FDIC SOD 2022 to 2026" | PASS | |
| Featured cards: two columns at >= 1000 px, collapse at 640 px | PASS | Grid 3 columns at 1200, 2 at 1000 and 641, 1 at 640; featured cards span 2, then 1 |

### LendSight, BizSight, BranchSight (member)

| Line | Result | Evidence |
|---|---|---|
| Header band: name, purpose, chips, vintage | PASS | LendSight "HMDA 2021 to 2025" (HMDA, Census ACS); BizSight "CRA small business 2020 to 2024" (CRA small business, Census ACS); BranchSight "FDIC Summary of Deposits 2022 to 2026" (FDIC SOD, FFIEC census) |
| Numbered steps, Run analysis and Reset, inline validation | PASS | LendSight 1 Geography, 2 Years, 3 Options; BizSight and BranchSight 1 Geography, 2 Years. Run with nothing chosen shows "Choose a state." and "Choose a county." inline; no alert, no `/analyze` request |
| Idle state | PASS | "Set up an analysis to begin. Choose a geography on the left, then run the analysis." |
| Georgia only in `.report-prose` | PASS | Idle page and all six results pages (three apps, Cook and Lowndes): no element outside `.report-prose` computes to Georgia |
| Loading state | PASS | All six runs: stage text, elapsed time and Cancel shown; `#results` `aria-busy="true"` |
| Success state | PASS | `aria-busy="false"` after; summary strip is the first element; reloading the report URL brings the report back |
| Empty state | PASS | BranchSight, Alpine County, CA: "No bank branches are reported for this county in 2022 to 2026." LendSight with a county code that has no records (the test rewrote the request): "No loan originations match…" |
| Error state (local) | PASS | Local `/dev/app-states` with debug on, staff session (the page is debug-only and the testing gate admits no member to `/dev`; the component does not vary by role), 2026-10-22. Shows "We couldn't complete this analysis", the message, "Reference: devref01", Try again and Report a problem; `aria-busy="false"`; export bar hidden; no horizontal scroll at 1024 or 390; no page errors. Report a problem opens `/contact?ref=devref01`, which shows the reference. Accepted as the local line by Jad, 2026-10-22 |
| Error state (live) | PASS | 2026-10-22 after #227 deployed, member, one tab at a time: `/<app>/report?job_id=<new random UUID>` shows the error state in 2.6 s (LendSight), 1.6 s (BizSight) and 2.1 s (BranchSight) from navigation: "This report is no longer available. Run the analysis again to rebuild it.", a reference, Try again and Report a problem (`/contact?ref=<ref>`); `aria-busy="false"`; no page errors |
| Error reference to `/contact?ref=` | PASS | `/contact?ref=qa1234ab` shows "Reference: qa1234ab" |
| Summary strip, tables, chart colors | PASS | Summary strip on all six; numeric `.app-table` cells use tabular numerals; charts present |
| Sources block, juxtaposition note, "Methods →" | PASS | Sources block present with "Correlation is not causation"; "Methods →" resolves to its section on the page |
| Exports produce files | PASS | Excel and PDF from all six runs download, non-empty, with the right file signatures (PDFs about 5.4 MB) |
| Copy citation format | PASS | For example "NCRC JustData, LendSight. HMDA 2021 to 2025; Cook County, Illinois. Generated 2026-10-20." followed by the report URL |
| No missing-narrative text | PASS | "A written summary was not generated for this run" appears on none of the six |
| Narrative log: every section, none near its limit | FAIL (LendSight, once) | Cloud Logging `[narrative]` lines on testing, 2026-10-15 to 2026-10-20. BranchSight 56 calls and BizSight 42 calls (6 fresh runs each): all `end_turn`, none flagged near the limit (highest 87% and 89%). LendSight 64 calls: 63 `end_turn`; the combined table call in Jad's Cook run 1 (2026-10-15 22:03 UTC) stopped at 3,000 of 3,000 tokens and the fallback filled the sections. Ticket draft 7 |
| Jay round 1: "originated" wording | PASS | LendSight results say "originated"; "applications" appears only in Methods, describing what HMDA covers |
| Jay round 1: statewide HHI | PASS | On the page, in Excel and in the PDF, LendSight and BizSight |
| Jay round 1: BizSight PDF matches the web | PASS, NOTE | Sections 1 to 5 match. The PDF has no Methods section, only the AI disclosure |
| Jay round 2 #1: `/admin/users` renders | FIXED (#230, merged 2026-10-22) | 500 reproduced locally as admin: the page rendered through a bare Jinja environment without the `ncrc_contact` global the footer has read since #217. Now `render_template`; admin 200, staff and member still refused. Admin view on testing and the page's function are Part 2 line 3 (Jad; no staff account here) |
| Jay round 2 #11: lender tables name their year | FIXED (#231, merged 2026-10-22) | Web titles (LendSight, BranchSight; BizSight already did), PDF headings and intros, and Excel sheet names. Live on testing, member, Wake County, NC runs: LendSight "Section 3: Top Lenders by Total Loans (2025)" and "Table 1: … (2025)"; BranchSight "Table 1: Top Banks by Branch Count (2026)" |
| Jay round 2 #10: minority-borrower summary card | NOTE | Not a bug (Jad, 2026-10-22): LendSight never had one (the pre-standard `populateSummaryCards` was BranchSight's branch-count code, never called). Moved to the feature backlog (L5 item 9, after the gate); the content questions, which groups and which denominator, are Jay's (Workflow 13360195998, now Low) |
| Analysis cache after #229 | PASS | 2026-10-22, member, Wake County, NC (never cached before). Cache write (sections, result row, cache row, one statement each): LendSight 4.9 s with 24 sections, BranchSight 6.5 s with 11 sections including `raw_data`; was 62 to 82 s and 10 to 20 s (and BranchSight always failed). BranchSight repeat run: cache hit, done in 6.7 s (uncached run 21.3 s). LendSight run total 120 s: BigQuery 27.4 s, narrative about 70 s in sequence (Workflow 13360117162). 96 orphaned BranchSight section rows deleted from `cache_testing` (Jad approved); 0 remain |
| Outage scenario after #232 | PASS | 2026-10-22 17:42 to 17:44 UTC on revision `justdata-testing-00042-psz` (image fd1cff4, 100% traffic; concurrency 16, timeout 1,920 s, session affinity on, `GUNICORN_THREADS=16`, 2 GiB; `justdata-test` and `justdata` unchanged at 160 and 3,600 s). Four report tabs on unknown job IDs opened at once (LendSight twice, BizSight, BranchSight): each showed the error state 2.5 s after opening; the request log shows each `/progress` stream closing in 10 to 19 ms (3,601 s on 2026-10-20). `/health` polled once a second: 52 of 52 returned 200, median 166 ms, max 233 ms |
| TTFB, member (app pages) | PASS | Median / p95: LendSight 156 / 174 ms, BizSight 147 / 155 ms, BranchSight 155 / 176 ms |
| Lighthouse desktop, member | PASS | Performance / Accessibility / Best Practices: LendSight 97 / 100 / 100, BizSight 97 to 98 / 100 / 100, BranchSight 98 / 100 / 100 |
| Time to interactive | PASS | 0.94 to 1.04 s on the three app pages |
| Cached re-run within 2 s | FAIL | LendSight 4.7 to 5.8 s, BizSight 4.6 to 5.9 s (all cache hits, 12 runs); BranchSight never hits the cache, 25.9 to 36.0 s. Ticket drafts 8 and 2 |
| Uncached, query portion within 20 s | FAIL (LendSight Cook, MergerMeter) | Query portion: LendSight Cook 69 to 85 s, Lowndes about 10 s; BizSight 5 to 7 s; BranchSight 2 to 4 s; MergerMeter about 30 s. Narrative and cache write are separate lines in the matrix budget table. Ticket drafts 1, 3, 4 and 7 |
| Three widths, before a run | PASS | No horizontal page scroll at 1440, 1024 or 390 on `/`, `/apps`, `/about`, `/contact` and the three app pages; no console errors as member |
| Three widths, after a run | PASS | No horizontal page scroll at 1440, 1024 or 390 on all six results pages; no console errors |

### Accessibility (member pages)

| Line | Result | Evidence |
|---|---|---|
| Keyboard: drawer opens, traps focus, closes on Escape; modals close on Escape | PASS | Focus moves to the first drawer item on open; 25 Tabs stay inside; Escape closes and returns focus to the menu button. The auth modal closes on Escape |
| Keyboard: tab order on a closed drawer | FIXED (#233) | The closed drawer was only moved off-screen, so Tab went through its 10 links (invisible) before reaching the page. Now `visibility: hidden` when closed (after the slide-out). Split into #233, live 2026-10-22, both motion settings: closed drawer `visibility: hidden`; the first six stops are menu, brand, account, breadcrumb (Home), Reset, State; with the drawer open, 25 Tabs stay inside it; Escape closes it and returns focus to the menu button |
| Keyboard: controls and Run in order | PASS | LendSight: Reset, State, County, years, Options, Run analysis, then the footer links |
| Focus ring on every interactive element reached | PASS | Every element reached in 40 Tabs on LendSight shows an outline or ring |
| Contrast | PASS | Lighthouse accessibility 100 on `/` and on the three app pages |
| Images have alt or are hidden; motif SVGs hidden | PASS | No `<img>` without alt and no exposed decorative SVG on the seven member pages |
| Reduced motion | PASS | With `prefers-reduced-motion: reduce`, the drawer transition is 0 s and the progress bar has no animation |
| Results region live | PASS | `#results` has `aria-live="polite"`; `aria-busy` is true while loading and false after, on all six runs |

### Hygiene (repo)

| Line | Result | Evidence |
|---|---|---|
| CI green; pytest | PASS | #226 CI: test and file-size-check pass. Local at this branch's base: 904 passed, 10 skipped, exit 0 |
| No `fa-` or decorative `data-lucide` in the four app template trees | PASS | None, also none in `app_page.html` and the `app_*` partials |
| `style="` in the four app template trees | PASS | None |
| lorem / TODO / FIXME / placeholder | PASS | Remaining hits are template comments, the Analytics "--" loading placeholders (staff page, filled on load) and archived ElectWatch |
| Secrets in templates and static JS | PASS | Only the Firebase web API key in `auth.js` (public by design) |
| Line limits | PASS | CI file-size-check passes; every file over a limit is on CI's existing allowlist |
| `platform_version` 0.10.0 | FIXED (#233) | Bumped in `shared/utils/versions.py` (Jad, 2026-10-15); split out of this PR into #233 at Jad's request, merged and deployed 2026-10-22 (7f2a15b). Live: `/health` reports 0.10.0, and the footer and drawer show 0.10.0 (member, LendSight) |
| ARCHITECTURE.md coverage | FIXED | Added the registry and testing overlay, `hmda_years`/`sod_years`, `app.css`, the state partials, `app_choices.js`, `perf.py` and the opt-in network tests; corrected the CI branch list |
| README conformance dates | FIXED | LendSight and BizSight 2026-10-07 (#210, #211); BranchSight and MergerMeter 2026-10-13 (#212, #217). The MergerMeter README also called its small business data Section 1071; corrected to the CRA disclosure summary it reads |

## Part 2 (Jad: admin, in a browser)

Lines 15 and 16 run from this session on 2026-10-22 with the one test account, which Jad switched in the admin page (labels: Registered = `public_registered`, Institutional = `non_member_org`):

| Line | Result | Evidence |
|---|---|---|
| 15, `public_registered` | PASS (request not submitted) | `check_tester_gate.py --role public_registered`: 16 of 16 PASS (redirect row skipped by design for this role). `/apps`: LendSight, BizSight and BranchSight locked and tagged "Members", request-access panel with "Request member access"; only the two analysis groups. Drawer: the three apps locked with "Members". Landing CTA "Request member access". The request was not submitted, because that creates a real member request; Jad checks the pending state in Part 2 if wanted |
| 16, `non_member_org` | PASS | `check_tester_gate.py --role non_member_org`: 17 of 17 PASS including the https redirect row. The three app pages render with Run analysis; `/mergermeter/`, `/branchmapper/`, `/dataexplorer/`, `/dotlender/`, `/status`, `/analytics/` and `/admin/users` redirect to `/`. `/apps` and the drawer: the three apps unlocked, no request panel, no Staff tools or In consolidation. Landing CTA "Open the apps" |
| Back to member | PASS | `check_tester_gate.py --role member`: 17 of 17 PASS |

Jad's browser pass, admin account, 2026-10-22 (results as Jad reported them):

| Line | Result | Evidence |
|---|---|---|
| 1, drawer | PASS | Groups and order as expected; no locks |
| 2, `/apps` | PASS, NOTE | Same groups and order as the drawer; In consolidation note present; no request panel. Jad: Staff tools and In consolidation "should only be available to admin". Decision (Jad, 2026-10-27): both groups admin-only before sign-off. #235 hides MergerMeter, Analytics, BranchMapper, DotLender and DataExplorer from staff and senior_executive in `ACCESS_MATRIX` (Administration already was) and moves the DotLender and Analytics routes from `staff_required` to `require_access`. Added on Jad's review: every progress stream is gated like its run route, and Staff tools is renamed Admin tools. This is the second deliberate access change in this workstream, after MergerMeter went staff-only (D2, 2026-10-07) |
| 2, role table after #235 | PENDING | Jad switches the test account to Staff, Senior Executive and Administrator; drawer, `/apps`, landing roster and the six routes checked live for each |
| 3, `/status`, `/analytics/`, `/admin/users` | PASS | All three open for admin (first admin view of `/admin/users` on testing since #230). Chrome hides the scheme in the address bar and shows the connection as secure; the gate script's redirect row confirms https |
| 4, `/admin/users` at three widths | PASS | |
| 5, `/analytics/` at three widths | PASS | Data and charts, no console errors |
| 6, MergerMeter page | PASS | Steps and the SOD 2026 hint as expected |
| 7, Pinnacle and UCB from branches | PASS | About 76 areas / 142 counties and 48 / 103, collapsed with Change |
| 8, controls column scroll | PASS | |
| 9, run analysis | FAIL | `/analyze` returned a cache hit, job `b823163c` (Pinnacle / UCB from Jad's 2026-10-15 batch), so no loading stages ran; `/report-data` then returned 404 eight times. Cause from the testing request log (revision 00043): every read of that job's metadata and workbook in `gs://justdata-mergermeter-output` got **403 Forbidden**. The objects exist (created 2026-10-15 22:21 UTC). The bucket's only non-project binding is `roles/storage.objectCreator` for `firebase-adminsdk-fbsvc@justdata-ncrc.iam.gserviceaccount.com`, so the service can write workbooks but not read them back; a MergerMeter cache hit can only load on the instance that wrote the file. Second issue: the bucket deletes objects after 7 days, while the cache row has no expiry, so after 7 days a cache hit points at a deleted workbook. The browser console's `contentscript.js` warnings come from an extension, not the site |
| 9, fix | DONE | Jad granted `roles/storage.objectViewer` on `gs://justdata-mergermeter-output` to `firebase-adminsdk-fbsvc@justdata-ncrc.iam.gserviceaccount.com` (2026-10-22). The cached report then loaded for Jad; the request log shows `/mergermeter/report-data` 200 at 18:08:57 UTC with the metadata and workbook downloaded from GCS. With Jad's approval the stale Pinnacle / UCB entry (`b823163c`, files due for the bucket's 7-day deletion) was removed from `cache_testing`: 1 cache row and 1 result row (no section rows; usage rows kept), so the re-run of line 9 is fresh |
| 9, re-run | PASS | Jad, admin, Pinnacle / UCB from branches: fresh run with stage text, elapsed counter and Cancel, no raw error. Server-recorded response time 70.4 s (`cache_testing.usage_log`, job `13d14420`, 18:12 UTC) |
| 10, results | PASS | |
| 11, report URL in a new tab | PASS | |
| 12, identical run again | PASS | Cache hit, server-recorded 5.3 s (18:15 UTC). `cache_testing`: one MergerMeter cache row (`13d14420`, access count 1) and one usage row per run (cache_hit false, then true). Expiry fix (Jad's decision 1, 2026-10-22): #234. On a MergerMeter cache hit the workbook must still be in storage, or the hit counts as a miss and the analysis reruns; new entries expire one hour before the bucket's 7-day deletion. MergerMeter is the only app that stores files outside BigQuery. Workflow 13361333217 |
| 13, three widths | PASS | |
| 14, BranchMapper, DotLender, DataExplorer | PASS | Old footer known and out of scope |
| 17, VoiceOver | SKIPPED | Jad's choice |
| 15, 16 | PASS | See gate runs above |

The 17 lines and expected results are in spec 05. Line 12: the
`cache_testing` grant was in before MergerMeter run 1 (2026-10-20); the two
Pinnacle / UCB runs left one cache row, one result row and one usage row per
run. Lines 15 and 16 use the one test account, moved
to `public_registered` then `non_member_org` and back to member by Jad.
