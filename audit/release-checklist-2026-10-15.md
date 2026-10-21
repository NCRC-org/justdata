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
stream timed out; no restart or redeploy. Ticket draft 9 in the matrix.

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
| Error state | HELD | Not reached. A made-up job ID returns the page to idle (the page waits on a stream that never ends; ticket 9). To reach it without the live site: the local `/dev/app-states` route |
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
| Keyboard: tab order on a closed drawer | FIXED | The closed drawer was only moved off-screen, so Tab went through its 10 links (invisible) before reaching the page. Now `visibility: hidden` when closed (after the slide-out). Checked with the new CSS swapped in on the live page, both motion settings: the first six stops are menu, brand, account, breadcrumb, Reset, State; focus trap and Escape unchanged |
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
| `platform_version` 0.10.0 | FIXED | Bumped in `shared/utils/versions.py` (Jad, 2026-10-15). Shown in the footer, drawer and `/health` after deploy: recheck after merge |
| ARCHITECTURE.md coverage | FIXED | Added the registry and testing overlay, `hmda_years`/`sod_years`, `app.css`, the state partials, `app_choices.js`, `perf.py` and the opt-in network tests; corrected the CI branch list |
| README conformance dates | FIXED | LendSight and BizSight 2026-10-07 (#210, #211); BranchSight and MergerMeter 2026-10-13 (#212, #217). The MergerMeter README also called its small business data Section 1071; corrected to the CRA disclosure summary it reads |

## Part 2 (Jad: admin, in a browser)

Not started. The 17 lines and expected results are in spec 05. Line 12: the
`cache_testing` grant was in before MergerMeter run 1 (2026-10-20); the two
Pinnacle / UCB runs left one cache row, one result row and one usage row per
run. Lines 15 and 16 use the one test account, moved
to `public_registered` then `non_member_org` and back to member by Jad.
