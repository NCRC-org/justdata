# Release checklist, testing site, 2026-10-15

Spec 05 (L5: Projects/JustData Frontend Specs/05-qa-and-release.md, revised
2026-10-15). Site: https://justdata-testing-854699313651.us-east1.run.app,
serving `testing` at 5ea2248 (#226) during these checks. Accounts by role only:
"signed out", "member" (the test account in `~/.justdata-test.env`), "admin"
(Jad, Part 2).

Status: **in progress.** Part 1 lines that start an analysis are held until
Jad's uncached timing batch (running 2026-10-15 from about 22:00 UTC) ends, so
they don't share the service with it. Performance lines wait for the batch
output. Part 2 is Jad's.

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
| Georgia only in `.report-prose` | PASS (idle page) | No element outside `.report-prose` computes to Georgia. Recheck on a results page: HELD |
| Loading, success, empty and error states; error reference to `/contact?ref=` | HELD | Starts analyses |
| Summary strip, tables, chart colors | HELD | Starts analyses |
| Sources block, juxtaposition note, "Methods →" | HELD | Starts analyses |
| Exports produce files | HELD | Starts analyses |
| Copy citation format | HELD | Starts analyses |
| Narrative log: every section, none near its limit | HELD | Starts analyses |
| Jay round 1 on the live site | HELD | Starts analyses |
| Performance (TTFB, Lighthouse, TTI, cached re-run, uncached) | HELD | Waits for the batch output |
| Three widths, before a run | PASS | No horizontal page scroll at 1440, 1024 or 390 on `/`, `/apps`, `/about`, `/contact` and the three app pages; no console errors as member |
| Three widths, after a run | HELD | Starts analyses |

### Accessibility (member pages)

| Line | Result | Evidence |
|---|---|---|
| Keyboard: drawer opens, traps focus, closes on Escape; modals close on Escape | PASS | Focus moves to the first drawer item on open; 25 Tabs stay inside; Escape closes and returns focus to the menu button. The auth modal closes on Escape |
| Keyboard: tab order on a closed drawer | FIXED | The closed drawer was only moved off-screen, so Tab went through its 10 links (invisible) before reaching the page. Now `visibility: hidden` when closed (after the slide-out). Checked with the new CSS swapped in on the live page, both motion settings: the first six stops are menu, brand, account, breadcrumb, Reset, State; focus trap and Escape unchanged |
| Keyboard: controls and Run in order | PASS | LendSight: Reset, State, County, years, Options, Run analysis, then the footer links |
| Focus ring on every interactive element reached | PASS | Every element reached in 40 Tabs on LendSight shows an outline or ring |
| Contrast | PASS (landing) | Lighthouse accessibility 100 on `/`. App pages: with the performance lines (HELD) |
| Images have alt or are hidden; motif SVGs hidden | PASS | No `<img>` without alt and no exposed decorative SVG on the seven member pages |
| Reduced motion | PASS | With `prefers-reduced-motion: reduce`, the drawer transition is 0 s and the progress bar has no animation |
| Results region live | PASS | `#results` has `aria-live="polite"` and `aria-busy="false"` at idle. Toggling during a run: HELD |

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

Not started. The 17 lines and expected results are in spec 05. Line 12 waits
on the `cache_testing` grant. Lines 15 and 16 use the one test account, moved
to `public_registered` then `non_member_org` and back to member by Jad.
