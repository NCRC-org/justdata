# HMDA 2025 Sync Audit

**Date:** 2026-07-16
**Author:** Claude Code (verified locally against the repo + BigQuery via the `justdata@hdma1-242116` service account)
**Scope:** Determine whether an automation propagates raw HMDA updates in `hdma1-242116` into the enriched table the apps read (`justdata-ncrc.shared.de_hmda`), whether it fired for 2025, and if not, why.

---

## TL;DR

- **2025 is already present and fully enriched** in `justdata-ncrc.shared.de_hmda` (13,534,156 rows, 99.93% of raw), including NCRC race flags, county/tract geography, and pricing fields. The LendSight summary tables also carry 2025. **The data layer is not the blocker for apps showing 2025 — the app-side year config is (see Phase 2B).**
- `de_hmda` is a **materialized BASE TABLE**, not a view. There are two copies: `shared.de_hmda` and `dataexplorer.de_hmda` (identical).
- 2025 got there via a **manual migration rebuild on 2026-05-12**, not via an event-driven trigger. All the relevant tables share coordinated 2026-05-12 timestamps and have not been modified since.
- An **event-driven sync pipeline is designed in the repo** (`scripts/sync/`) but has a **fundamental architectural gap**: it triggers on the *raw* table but copies from an already-*enriched* intermediate that nothing automatically rebuilds. Whether it is even deployed could not be confirmed with the available credentials (needs the personal GCP account).
- **Net: future raw loads will not reliably propagate on their own.** Recommendations for durable automation are in the last section.

---

## 1. Is `de_hmda` a view or a materialized table?

**Materialized BASE TABLE** (confirmed via `INFORMATION_SCHEMA.TABLES`). Two copies exist:

| Table | Type | Created | Last modified | Rows |
|---|---|---|---|---|
| `justdata-ncrc.shared.de_hmda` | BASE TABLE | 2026-05-12 16:33:46 | 2026-05-12 16:33:46 | 145,246,665 |
| `justdata-ncrc.dataexplorer.de_hmda` | BASE TABLE | 2026-05-12 16:37:02 | 2026-05-12 16:37:09 | 145,246,665 |

Both are unpartitioned-by-modification (creation ≈ last-modified), i.e. built once and never touched since. There is **no `cbsa` or `derived_msa_md` column** — geography is county/tract based (`county_code`, `geoid5`, `census_tract`), so CBSA rollups happen at query time by joining `justdata-ncrc.shared.cbsa_to_county`. `activity_year` is **INT64** in `de_hmda` (it is STRING in the raw table).

---

## 2. What mechanism syncs it?

There are **two distinct chains**, and only the second one is (intended to be) automated:

### 2a. The raw → enriched build (MANUAL, in-source-project)

The enriched intermediate `hdma1-242116.justdata.de_hmda` is built from raw `hdma1-242116.hmda.hmda` by:

- `justdata/apps/dataexplorer/create_de_hmda_table.sql` — full build (`INSERT INTO`, all years ≥ 2018).
- `justdata/apps/dataexplorer/update_de_hmda_incremental.sql` — per-year append; header says "set up as a BigQuery Scheduled Query (monthly)".

This step computes the NCRC race booleans, income/tract flags, Connecticut planning-region normalization, and joins lender names. **It is a manual (or at best scheduled-query) step that is not wired to the event pipeline below.** Freshness of `hdma1-242116.justdata.de_hmda`: created 2025-12-24, last modified **2026-04-29** — i.e. 2025 was enriched by late April.

### 2b. The cross-project sync (event-driven, designed; deployment unconfirmed)

`scripts/sync/main.py` is a **Cloud Function triggered by Pub/Sub**, fed by **BigQuery audit-log sinks** in `hdma1-242116` (`scripts/sync/setup_log_sinks.sh`, `setup_pubsub.sh`, `deploy_functions.sh`). Its table mapping for HMDA:

```python
'hmda.hmda': ('shared.de_hmda', 'derived', ['lendsight.de_hmda_county_summary', 'lendsight.de_hmda_tract_summary']),
```

and the SQL it runs (main.py:73-76):

```sql
CREATE OR REPLACE TABLE `justdata-ncrc.shared.de_hmda` AS
SELECT * FROM `hdma1-242116.justdata.de_hmda`;   -- reads the ENRICHED intermediate, not raw
```

**Could not confirm whether this is deployed.** The available service account (`justdata@hdma1-242116`, data-access only) lacks `cloudfunctions.locations.list`, `pubsub.topics.list`, `logging.sinks.list`, `cloudscheduler.jobs.list`, and `bigquery.transfers.get`. Confirming deployment requires the personal GCP account (`jedlebi@ncrc.org`) — see "Open items."

### What actually populated the current tables

The coordinated 2026-05-12 timestamps across `shared.de_hmda` (16:33), `dataexplorer.de_hmda` (16:37), `lendsight.de_hmda_county_summary` (16:44), and `lendsight.de_hmda_tract_summary` (16:45) match a **manual run of the migration scripts** (`scripts/migration/17_copy_de_hmda.sql` and siblings), not an event trigger reacting to a single raw load. No table shows a July modification corresponding to a recent raw reload.

---

## 3. Did 2025 propagate?

**Yes — nearly completely and with full enrichment.**

Row counts by year (raw vs enriched):

| activity_year | raw `hmda.hmda` | enriched `shared.de_hmda` | delta |
|---|---|---|---|
| 2018 | 15,119,651 | 16,094,007 | +974,356 |
| 2019 | 17,545,457 | 18,697,972 | +1,152,515 |
| 2020 | 25,551,868 | 27,270,543 | +1,718,675 |
| 2021 | 26,192,390 | 28,104,927 | +1,912,537 |
| 2022 | 16,085,455 | 17,116,355 | +1,030,900 |
| 2023 | 11,483,889 | 12,199,407 | +715,518 |
| 2024 | 12,229,298 | 12,229,298 | 0 |
| **2025** | **13,543,606** | **13,534,156** | **−9,450** |

> Note on the pre-2024 rows where enriched > raw: the enriched intermediate was built from an earlier/larger raw snapshot than what raw currently holds for those years; the raw table appears to have been re-loaded with smaller snapshots since. This does not affect 2025 and is out of scope, but is worth a follow-up if historical counts matter.

**2025 enrichment completeness** (vs 2023/2024 as baselines):

| year | rows | null county | null tract | has_demographic_data | is_black | is_white | is_hispanic | has interest_rate | null lender_name |
|---|---|---|---|---|---|---|---|---|---|
| 2023 | 12,199,407 | 0 | 0 | 9,181,316 | 944,985 | 5,996,092 | 1,431,569 | 7,662,429 | 0 |
| 2024 | 12,229,298 | 0 | 0 | 9,287,605 | 960,599 | 5,966,039 | 1,501,246 | 7,716,346 | 0 |
| 2025 | 13,534,156 | 0 | 0 | 10,122,503 | 984,380 | 6,663,679 | 1,566,349 | 8,683,284 | **46,189** |

Race flags, geography, and pricing all populate for 2025 consistently with prior years. The one blemish is **46,189 rows (0.34%) with a null lender_name** (root cause below).

---

## 4. Root cause / gaps

Even though 2025 is present, the automation as designed will **not** reliably propagate future raw loads. Concrete issues found:

1. **Architectural gap (the big one).** The event trigger (2b) fires on the *raw* table `hmda.hmda`, but the sync copies from the *enriched* intermediate `justdata.de_hmda`. Nothing automatically rebuilds the enriched intermediate from raw. So a raw load, on its own, would at most copy a **stale** enriched table across projects. The raw→enriched step (2a) is the missing automated link.

2. **Non-idempotent incremental enrichment.** `update_de_hmda_incremental.sql` filters `WHERE activity_year > (SELECT MAX(activity_year) FROM justdata.de_hmda)`. Once a year exists it is **never re-processed**. This is exactly why the 9,450 additional raw 2025 rows (loaded after the April enrichment) are orphaned — a re-run would be a no-op. Re-loads of an existing year silently fail to propagate.

3. **Deprecated `lenders18` join → null lender names.** Both enrichment scripts join `hdma1-242116.hmda.lenders18` (deprecated). Of the distinct 2025 LEIs in `de_hmda`, **78 are missing from `lenders18`** but only **9 are missing from the current `hmda.lenders`** — so **76 LEIs (≈46k loans) would recover their lender name by switching the join to `hmda.lenders`.** The stale `sync/main.py` table mapping also still references `hmda.lenders18 → lendsight.lenders18`.

4. **Dependent summaries are not refreshed by the function.** `sync/main.py:227-229` explicitly **skips** `lendsight.de_hmda_county_summary` / `de_hmda_tract_summary` ("would need separate SQL"). Those summaries only exist today because the manual migration built them. An event-driven sync would leave them stale.

5. **Audit-log dependency.** The log-sink trigger (2b) matches `tableservice.insert/update` and `jobservice.insert` events, which require BigQuery **Data-Access / job audit logs to be enabled** in `hdma1-242116` — an open "enable audit logging" horizon item. If those logs aren't enabled (and NCRC may not have admin on `hdma1-242116` to enable them), the sink never fires. The log filter's OR/AND precedence also looks malformed and should be reviewed if this path is kept.

---

## 5. Recommendation for Phase 2

**No emergency data fix is required for apps to show 2025** — the enriched data is already there. The app-visibility work is Phase 2B (year config), not a data problem.

For a correct and durable data pipeline (Phase 2A), in rough priority order:

1. **Switch the lender join from `lenders18` to `hmda.lenders`** in `create_de_hmda_table.sql`, `update_de_hmda_incremental.sql`, and the `sync/main.py` mapping. Recovers ~46k 2025 lender names.
2. **Make the incremental enrichment idempotent per year** — replace the `> MAX(year)` gate with a per-year `DELETE` + `INSERT` (or `MERGE`) so re-loads of an existing year (e.g. the 9,450 orphaned 2025 rows) propagate.
3. **Close the architectural gap**: either (a) trigger the *sync* off the *enriched* intermediate's update instead of the raw load, and schedule the raw→enriched rebuild; or (b) collapse the two steps so the cross-project object is rebuilt directly from raw with enrichment in one job. Whichever, the chain must be: raw load → enrich → cross-project copy → refresh summaries, with no manual step.
4. **Implement the skipped dependent-summary refresh** in `sync/main.py` (the `lendsight.de_hmda_*` branch) so summaries never go stale relative to `de_hmda`.
5. **Confirm/fix deployment & audit logs** using the personal GCP account (see open items). If the audit-log path is unavailable, prefer a **scheduled query / Cloud Run job on a cadence** over the event-driven sink.
6. **To fully correct 2025 now** (optional, once #1–#2 land): re-run enrichment for 2025 (delete + re-insert with the `lenders` join), re-copy to `shared` + `dataexplorer`, and rebuild the LendSight summaries. Requires write access to `hdma1-242116.justdata` — confirm the service account has it before attempting.

---

## Phase 2B pre-scan — app year configuration (for the rollout, not part of this audit's conclusion)

HMDA-reading apps: **dataexplorer, dotlender, lenderprofile, lendsight, loantrends, mergermeter** (bizsight is 1071 small-business, not HMDA). There is **no single source of truth** for available years; most are hardcoded and several clamp at 2024:

| Location | Current | Issue |
|---|---|---|
| `dataexplorer/config.py:40` | `HMDA_YEARS = list(range(2018, 2025))` | excludes 2025 |
| `dataexplorer/core.py:53` | `max_year = min(current_year, 2024)` | hard clamp to 2024 |
| `lendsight/config.py:53` | `DEFAULT_YEARS = list(range(2020, 2025))` | excludes 2025 |
| `lendsight/blueprint.py:960,966` | fallback `list(range(2017, 2025))` | excludes 2025 |
| `lendsight/report_builder/excel_export/writer.py:214` | `[y for y in years if 2020 <= y <= 2024]` | hard clamp excludes 2025 |
| `mergermeter/blueprint.py:198-206` | HMDA/SB defaults `'2023'`–`'2024'` | default range should be 2023–2025 |
| `mergermeter/mergermeter_ops.py:541-556` | fallbacks `or 2023` / `or 2024` | same |
| `dotlender/sql_templates/max_year.sql` | dynamic `MAX(activity_year)` | ✅ already 2025-ready |

**Open decision (flag to Jad/Jay):** dynamic available-years (`SELECT DISTINCT activity_year` / `MAX`) vs a curated shared config constant. `dotlender` already proves the dynamic pattern works; a reviewed shared constant is the more controlled/defensible option NCRC tends to prefer.

---

## Open items (require the personal GCP account `jedlebi@ncrc.org`)

The data-access service account cannot list deployment resources. To finish the audit, run (after `gcloud auth login`):

```bash
gcloud config set account jedlebi@ncrc.org
gcloud functions list --project=justdata-ncrc
gcloud pubsub topics list --project=justdata-ncrc
gcloud logging sinks list --project=hdma1-242116
bq ls --transfer_config --transfer_location=us --project_id=hdma1-242116   # scheduled queries
gcloud scheduler jobs list --project=justdata-ncrc --location=us-east1
```

This confirms (a) whether the Cloud Function / Pub/Sub / log sinks are actually deployed, and (b) whether a scheduled query runs `update_de_hmda_incremental.sql`. Those answers determine whether Phase 2A is "fix the existing scheduled query" vs "build the automation from scratch."
