# Testing site sign-off, 2026-11-05

The frontend rebuild (specs 01 to 05, L5: Projects/JustData Frontend Specs) is
signed off on the `testing` branch. Every checklist line passed, was fixed and
re-checked, or was skipped by Jad's choice (line 17, VoiceOver). Nothing in
this plan left `testing`; promotion to `staging` or `main` is a separate
decision for Jad.

- Site: https://justdata-testing-854699313651.us-east1.run.app (Cloud Run
  service `justdata-testing`, `JUSTDATA_ENV=testing`).
- Code signed off: `testing` at e333d89 (#228 merged). The last code change,
  #235 (6e3eac6), was checked live on revision `justdata-testing-00045-zgk`.
- Checklist: [`audit/release-checklist-2026-10-15.md`](release-checklist-2026-10-15.md).
  Timings, bytes and ticket drafts: [`audit/app-standardization-matrix.md`](app-standardization-matrix.md).
- Items on the Rollout board stay open; Jay closes them.

## Two deliberate access changes

These are the only changes in this plan to who can see or open what. Every
other PR changed presentation only.

1. **MergerMeter is staff-only on every deploy** (D2, Jad, 2026-10-07, in
   [#206](https://github.com/NCRC-org/justdata/pull/206)). Testers get three
   apps: LendSight, BizSight and BranchSight. MergerMeter was briefly
   tester-facing on testing through the overlay in #198.
2. **Admin tools and In consolidation are admin-only** (Jad, 2026-10-27, spec
   05 Part 2 line 2, [#235](https://github.com/NCRC-org/justdata/pull/235)).
   `ACCESS_MATRIX` hides MergerMeter, Analytics, BranchMapper, DotLender and
   DataExplorer from `staff` and `senior_executive` (Administration already
   was admin-only). The DotLender and Analytics routes now read the matrix,
   every app's progress stream is gated like its run route, and the Staff
   tools group is renamed Admin tools. Checked live for all three roles
   (checklist, "Line 2 role table").

## Merged PRs, #192 onward

All into `testing`. #205 was closed unmerged and replaced by #206.

| PR | Merged | Spec | What it did |
|---|---|---|---|
| [#192](https://github.com/NCRC-org/justdata/pull/192) | 2026-09-21 | Buildout step 1 | Single design-token source |
| [#193](https://github.com/NCRC-org/justdata/pull/193) | 2026-09-21 | Buildout step 2 | Shared shell: header, nav, footer, auth modal |
| [#194](https://github.com/NCRC-org/justdata/pull/194) | 2026-09-30 | Buildout step 3 | Server-rendered home page on the shell |
| [#195](https://github.com/NCRC-org/justdata/pull/195) | 2026-09-30 | Buildout | Overlay tokens; shell.css on tokens |
| [#196](https://github.com/NCRC-org/justdata/pull/196) | 2026-09-30 | Buildout | Landing page and app launcher split |
| [#197](https://github.com/NCRC-org/justdata/pull/197) | 2026-10-06 | Buildout | Head blocks moved out of an include |
| [#198](https://github.com/NCRC-org/justdata/pull/198) | 2026-10-06 | 01 | Registry-driven nav drawer and footer; testing tester overlay |
| [#199](https://github.com/NCRC-org/justdata/pull/199) | 2026-10-06 | 01 | Registry drawer on legacy shared_header pages |
| [#200](https://github.com/NCRC-org/justdata/pull/200) | 2026-10-07 | 02 | Testing site open to tester roles; BranchMapper and `/status` access checks |
| [#201](https://github.com/NCRC-org/justdata/pull/201) | 2026-10-07 | 01 | `require_access` levels validated by test (docs) |
| [#202](https://github.com/NCRC-org/justdata/pull/202) | 2026-10-07 | 02 | Live gate check script, per role |
| [#203](https://github.com/NCRC-org/justdata/pull/203) | 2026-10-07 | 02 | Gate check: `--role non_member_org` |
| [#204](https://github.com/NCRC-org/justdata/pull/204) | 2026-10-07 | 02 | Public landing page at `/` |
| [#206](https://github.com/NCRC-org/justdata/pull/206) | 2026-10-07 | 03 | Registry-driven `/apps` launcher; three tester apps; staff-only groups (**access change 1**) |
| [#207](https://github.com/NCRC-org/justdata/pull/207) | 2026-10-07 | 03 | Gate check: redirect-scheme row |
| [#208](https://github.com/NCRC-org/justdata/pull/208) | 2026-10-07 | 04 | Report hygiene: placeholders, progress text, stuck jobs, unbacked claims, raw errors |
| [#209](https://github.com/NCRC-org/justdata/pull/209) | 2026-10-07 | 04 Part A | Shared analysis-app standard, job labels, query-cache switch, MergerMeter cache |
| [#210](https://github.com/NCRC-org/justdata/pull/210) | 2026-10-07 | 04 Part B | LendSight on the standard |
| [#211](https://github.com/NCRC-org/justdata/pull/211) | 2026-10-07 | 04 Part B | BizSight on the standard; shared AppReport and AppRun |
| [#212](https://github.com/NCRC-org/justdata/pull/212) | 2026-10-13 | 04 Part B | BranchSight on the standard; county, export and narrative fixes |
| [#213](https://github.com/NCRC-org/justdata/pull/213) | 2026-10-13 | 04 | BizSight and BranchSight follow-ups |
| [#214](https://github.com/NCRC-org/justdata/pull/214) | 2026-10-13 | 04 | MergerMeter: neutral progress line, reusable cache entries |
| [#215](https://github.com/NCRC-org/justdata/pull/215) | 2026-10-13 | 04 | Jay feedback round 1 |
| [#216](https://github.com/NCRC-org/justdata/pull/216) | 2026-10-13 | 04 | LendSight key findings ceiling and combined-call parse |
| [#217](https://github.com/NCRC-org/justdata/pull/217) | 2026-10-13 | 04 Part B | MergerMeter on the standard page; contact details from one value |
| [#218](https://github.com/NCRC-org/justdata/pull/218) | 2026-10-13 | 04 | Round 1 follow-ups |
| [#219](https://github.com/NCRC-org/justdata/pull/219) | 2026-10-15 | 04 | Report-link tests run only on request |
| [#220](https://github.com/NCRC-org/justdata/pull/220) | 2026-10-15 | 04 | Timing script signs in with a browser session cookie |
| [#221](https://github.com/NCRC-org/justdata/pull/221) | 2026-10-15 | 04 | Controls column scrolls inside itself |
| [#222](https://github.com/NCRC-org/justdata/pull/222) | 2026-10-15 | 04 | SOD year from one setting; MergerMeter reads every SOD year |
| [#223](https://github.com/NCRC-org/justdata/pull/223) | 2026-10-15 | 04 | `SOD_LATEST_YEAR = 2026` |
| [#224](https://github.com/NCRC-org/justdata/pull/224) | 2026-10-15 | 04 | Report-link check retries once after a server error |
| [#225](https://github.com/NCRC-org/justdata/pull/225) | 2026-10-15 | 04 | MergerMeter timing pair: Pinnacle Bank / United Community Bank |
| [#226](https://github.com/NCRC-org/justdata/pull/226) | 2026-10-15 | 04 | MergerMeter cache permission gap (docs) |
| [#227](https://github.com/NCRC-org/justdata/pull/227) | 2026-10-22 | 05 | Progress stream ends for an unknown job and at a hard cap |
| [#229](https://github.com/NCRC-org/justdata/pull/229) | 2026-10-22 | 05 | BranchSight reaches the cache; sections written in one statement |
| [#230](https://github.com/NCRC-org/justdata/pull/230) | 2026-10-22 | 05 | `/admin/users` renders instead of returning 500 |
| [#231](https://github.com/NCRC-org/justdata/pull/231) | 2026-10-22 | 05 | Every lender and bank table names its year |
| [#232](https://github.com/NCRC-org/justdata/pull/232) | 2026-10-22 | 05 | `justdata-testing` at 16 threads and concurrency 16 |
| [#233](https://github.com/NCRC-org/justdata/pull/233) | 2026-10-22 | 05 | Platform version 0.10.0; closed drawer leaves the tab order |
| [#234](https://github.com/NCRC-org/justdata/pull/234) | 2026-11-05 | 05 | MergerMeter cache hit needs its workbook; entries expire with it |
| [#235](https://github.com/NCRC-org/justdata/pull/235) | 2026-11-05 | 05 | Admin tools and In consolidation admin-only; streams gated like runs (**access change 2**) |
| [#228](https://github.com/NCRC-org/justdata/pull/228) | 2026-11-05 | 05 | QA pass: checklist, matrix, fixes found in the pass |

## Checklist

Full evidence is in the checklist file. In short:

- **Part 1** (Claude; signed out and member): access and wayfinding,
  landing, launcher, the three Sight apps, accessibility and repo hygiene all
  pass. The error state passes locally and live after #227. Two performance
  lines fail and are ticketed (below): cached re-runs over 2 s, and the
  uncached query portion over 20 s for LendSight Cook County and MergerMeter.
- **Part 2** (Jad, admin, 2026-10-22): lines 1 to 16 pass. Line 9 failed on a
  403 reading MergerMeter workbooks from storage and passed after Jad's
  `roles/storage.objectViewer` grant; the expiry gap it exposed is #234.
  Line 17 (VoiceOver) was skipped by Jad's choice.
- **Line 2 role table** (2026-11-05, revision 00045): Staff and Senior
  Executive see only the three Sight apps in the drawer, on `/apps` and in
  the landing roster; the six admin-only routes and the MergerMeter and
  DataExplorer progress streams send them to `/`. Administrator sees all four
  groups and nine apps and opens every route and stream. 14 of 14 checks pass
  per role.
- **Gate script** (`scripts/check_tester_gate.py`): signed out,
  `public_registered`, `non_member_org` and member all pass.

## Lighthouse and page performance

Desktop Lighthouse, testing site.

| Page | Account | Performance | Accessibility | Best Practices | Date |
|---|---|--:|--:|--:|---|
| `/` | Signed out | 96 (three runs) | 100 | 96 | Spec 05 pass |
| LendSight | Member | 97 | 100 | 100 | Spec 05 pass |
| BizSight | Member | 97 to 98 | 100 | 100 | Spec 05 pass |
| BranchSight | Member | 98 | 100 | 100 | Spec 05 pass |

The single Best Practices deduction on `/` is a 401 from
`/api/auth/verification-status` when signed out (checklist, "Console errors").
MergerMeter has no Lighthouse figure; it was staff-only when measured.

| Page (member) | TTFB median / p95 (budget p95 <= 600 ms) | Time to interactive (budget <= 1.5 s) |
|---|---|---|
| LendSight | 156 / 174 ms | 0.94 to 1.04 s across the three pages |
| BizSight | 147 / 155 ms | |
| BranchSight | 155 / 176 ms | |

## Analysis performance

Uncached runs, Jad, admin, 2026-10-15, two runs per row with BigQuery's result
cache off. Cost is bytes billed at the on-demand rate of $6.25 per TiB
([BigQuery pricing](https://cloud.google.com/bigquery/pricing)), before the
free tier.

| App | Geography | Seconds to done | Bytes billed | Cost per run |
|---|---|---|--:|--:|
| LendSight | Cook County, IL | 228.9 to 285.3 | 11.6 GB | $0.066 |
| LendSight | Lowndes County, GA | 138.9 to 150.9 | 12.7 GB | $0.072 |
| BizSight | Cook | 59.8 to 70.4 | 1.8 GB | $0.010 to $0.011 |
| BizSight | Lowndes | 58.2 to 59.3 | 1.8 GB | $0.010 to $0.011 |
| BranchSight | Cook | 30.8 to 31.8 | 181 MB | $0.001 |
| BranchSight | Lowndes | 19.3 to 24.3 | 181 MB | $0.001 |
| MergerMeter | Pinnacle / UCB | 37.2 to 42.1 | 106.85 GB | $0.607 |

Cached runs and fixes:

| Line | Budget | Measured | Status |
|---|---|---|---|
| Cached re-run, LendSight and BizSight | <= 2 s | 4.6 to 5.9 s (12 runs, member, 2026-10-20) | Over budget; ticket 13360119391 |
| Cached re-run, BranchSight | <= 2 s | Never cached before #229; 6.7 s after (Wake County, NC) | Reaches the cache; same ticket for speed |
| Cached re-run, MergerMeter | <= 2 s | 5.3 s (Jad, admin, 2026-10-22) | Recorded only; the budget table leaves MergerMeter out (staff-only) |
| Cache write | proposed <= 5 s | 10 to 82 s before #229; 4.9 s LendSight, 6.5 s BranchSight after | Fixed in #229 |
| Uncached query portion | <= 20 s | LendSight Cook 69 to 85 s; MergerMeter about 30 s; others within | Tickets 13360118475, 13360119798 |
| LendSight narrative | proposed <= 15 s | 60 to 114 s | Ticket 13360117162 |

## Tickets

Workflow board (18397384545). Every item below reads Open on the board; Jay
closes them. "Fixed" means the fix is merged and live on testing.

| Ticket | Title | Priority | State |
|---|---|---|---|
| 13360124454 | Analysis cache write takes 10 to 82 s per run | High | Fixed, #229 |
| 13360117509 | BranchSight results never stored in the analysis cache | High | Fixed, #229 |
| 13360099262 | Progress stream for an unknown job never ends | High | Fixed, #227 |
| 13361333217 | MergerMeter cache hits outlive their 7-day workbook | High | Fixed, #234 |
| 13360117508 | gunicorn threads and Cloud Run concurrency for `justdata-testing` | Medium | Fixed on testing only, #232; staging and production are a separate decision |
| 13229533844 | LendSight stuck on 2024 HMDA | High | Fixed, #210 (runs 2021 to 2025) |
| 13229487819 | BizSight year range | Medium | Fixed, #211 (one setting, 2020 to 2024) |
| 13277163649 | Load 2026 FDIC SOD | High | Fixed, #222 and #223 |
| 13360119798 | MergerMeter scans 105 GB of HMDA per run | High | Open |
| 13360118475 | LendSight HMDA query reads a whole year per county | Medium | Open |
| 13360117507 | BizSight reads the whole small business summary table | Medium | Open |
| 13360117162 | LendSight narrative: eight AI calls in a row | Medium | Open |
| 13360119391 | Cache hit takes 4.6 to 5.9 s; budget is 2 s | Medium | Open |
| 13229522646 | ACS vintage hardcoded differently in each app | Medium | Open |
| 13360117255 | BranchSight reads both SOD tables in full | Low | Open |
| 13360195998 | LendSight: no minority-borrower card | Low | Not a bug (Jad, 2026-10-22); moved to the feature backlog |

Jay round 2 (Rollout 13360003401): #1 fixed in #230, #4 and #5 in #229, #11 in
#231, #10 is a backlog feature. #2, #3, #6 and #8 are Low, after the gate
(Jay's call); #9 and the narrative review are Jay's; #7 needs Jay's
clarification.

## Decisions D1 to D5, as decided

| ID | Question | As decided |
|---|---|---|
| D1 | Is `/` public? | Yes. Signed-out visitors reach `/`, `/about` and `/contact` only (exact paths). The landing page has descriptions, no data; the launcher and every app stay gated (#200, #204). |
| D2 | MergerMeter tester-facing or staff-only? | Staff-only on every deploy (Jad, 2026-10-07, #206), then admin-only with both staff groups (Jad, 2026-10-27, #235). |
| D3 | Do locked apps show? | Member-tier apps show locked with a "Members" tag and the request-access panel. The Admin tools and In consolidation groups never render for anyone who can't open them; since #235 that is everyone except admin. On testing, nothing shows as open that won't open. |
| D4 | Landing scale-strip figures | Phase 1 shipped: four figures true by construction from code settings (8 years of mortgage records, 10 years of branch records, 50 states, DC and Puerto Rico, 4 federal datasets). "100% public" and "no licensed data" were dropped. Phase 2 (live counts from a nightly table) is not built. |
| D5 | One-line purpose per app | Drafts used, then trimmed to what each app's README and code support (#204, #206). Claims of denial rates, pricing and "which it skips" were dropped. |

## Screenshot branches deleted, 2026-11-05

Images only, never merged; Jad decided on 2026-10-07 to keep them until this
sign-off. PR descriptions that linked these images by commit no longer show
them. The last commit of each is listed so a branch can be restored if needed.

| Branch | Last commit |
|---|---|
| `docs/app-shell-standard-screenshots` | 7d7a88dcfc2e2f710909119c0ea5f272f34503b2 |
| `docs/apps-launcher-screenshots` | f19731a5371c10f8ec8bc904b447270e23bde35d |
| `docs/lendsight-standard-screenshots` | c68bbcacc4598a0e57b9e15199df9a01859e15d2 |
| `docs/bizsight-standard-screenshots` | c4a623498177b4072371493c3032eeeaa3c9ee1f |
| `docs/branchsight-standard-screenshots` | 29ce822baf3abaccc4d52a7b97b611e8719aa723 |
| `docs/mergermeter-standard-screenshots` | 4d57a45ef292377573fe2fc73b7e817c020dd7f2 |
| `docs/followups-screenshots` | 77777143c842645be66a0e339614faba82a88d62 |
| `docs/controls-scroll-screenshots` | 2ef92077d80af395ad7acafc20b322b9515a6c92 |
| `docs/release-qa-screenshots` | 6b5e3d1d6d9c69faff0fd15605cbd549e621c227 |

## Next

Infrastructure before features (Jad with Jay, 2026-10-20): spec 08, test-user
sign-up and login; then spec 09, user data deletion; then backlog features;
then spec 07, annual data release automation.
