# Timing payloads (spec 04 reference geographies)

Each file is the JSON body the app's page posts to `/<app>/analyze` (captured
2026-10-07; LendSight's and BizSight's updated with their spec 04 PRs), for Cook County, IL (17031) and Lowndes County, AL (01085).
`scripts/time_analysis.py` adds `force_refresh`. County objects were read from
each app's own county endpoint on the testing site.

What the pages send today, and so what these payloads send:

| App | Years | Other fields |
|---|---|---|
| LendSight | none sent: the server analyses the five most recent HMDA years (2021 to 2025 since the spec 04 LendSight PR; ticket 13229533844). The page before that PR sent 2018 to 2024, which the server also ignored | `loan_purpose: ["purchase"]` (page default), `state_code` as FIPS |
| BizSight | none sent: the server uses `config.SB_YEARS`, 2020 to 2024 (since the spec 04 BizSight PR; the page before sent 2020 and 2024, which keys the cache the same way) | full county object as `county_data` |
| BranchSight | none sent: the server uses `config.SOD_YEARS`, 2021 to 2025 (since the spec 04 BranchSight PR; the page before sent the same five years, so the cache key is unchanged) | `state_code` is the state name (its state list uses names as codes); `counties` is the exact county name |

When a per-app PR changes what its page posts (for example LendSight moving
to 2025), update that app's two files in the same PR, so before-and-after runs
stay comparable.

## Uncached runs (staff)

Uncached runs send `force_refresh`, which the server honours only for staff,
and which now also turns off BigQuery's own result cache (`use_query_cache=False`,
label `refresh=forced`). The script signs in with Firebase email and password
from `TEST_EMAIL` / `TEST_PASSWORD`, so the account must have a password
(a Google-only sign-in will fail at "Firebase sign-in failed").

```bash
cd /Users/jadedlebi/justdata
set -a; source ~/.justdata-staff.env; set +a     # TEST_EMAIL / TEST_PASSWORD for a staff account
mkdir -p audit/timings

.venv/bin/python scripts/time_analysis.py run --app lendsight   --payload scripts/timing_payloads/lendsight-cook.json      --runs 2 --uncached --label cook-uncached    --out audit/timings/uncached.jsonl
.venv/bin/python scripts/time_analysis.py run --app lendsight   --payload scripts/timing_payloads/lendsight-lowndes.json   --runs 2 --uncached --label lowndes-uncached --out audit/timings/uncached.jsonl
.venv/bin/python scripts/time_analysis.py run --app bizsight    --payload scripts/timing_payloads/bizsight-cook.json       --runs 2 --uncached --label cook-uncached    --out audit/timings/uncached.jsonl
.venv/bin/python scripts/time_analysis.py run --app bizsight    --payload scripts/timing_payloads/bizsight-lowndes.json    --runs 2 --uncached --label lowndes-uncached --out audit/timings/uncached.jsonl
.venv/bin/python scripts/time_analysis.py run --app branchsight --payload scripts/timing_payloads/branchsight-cook.json    --runs 2 --uncached --label cook-uncached    --out audit/timings/uncached.jsonl
.venv/bin/python scripts/time_analysis.py run --app branchsight --payload scripts/timing_payloads/branchsight-lowndes.json --runs 2 --uncached --label lowndes-uncached --out audit/timings/uncached.jsonl

# Bytes billed per run, matched by the job label (needs bigquery.jobs.listAll on justdata-ncrc)
.venv/bin/python scripts/time_analysis.py bytes --in audit/timings/uncached.jsonl
```

That is 12 analyses with narratives. Check as they run:

- Each command prints `Signed in; role reported by /api/auth/login: staff`.
  Any other role prints a WARNING, and the runs may be cache hits.
- Each run line shows `cache_hit=False`.
- In the `bytes` output, `matched_by` reads `job label` and `bq_cache_hits`
  is 0. If it reads `service account + window`, the labels did not attach.

The JSONL holds job ids, timings and progress steps; no credentials or user
identity beyond the role.
