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
| MergerMeter | the page defaults: HMDA 2023 to 2025, small business 2023 to 2024, and the same goal-baseline years | form fields, not JSON (`mergermeter-atlantic-union-synovus.json`, Jad's pair, 2026-10-13). Assessment areas are generated from branches (FDIC SOD 2025) for both banks with every county kept: 21 areas / 84 counties for Atlantic Union, 57 / 100 for Synovus. This matches a page run that uses "From branches" for both banks and keeps every county, so the two share a cache key. Other fields are the page defaults (all loan purposes, 50% to 200% peer group, originations, owner-occupied, 1 to 4 units, site-built and manufactured, not reverse) |

When a per-app PR changes what its page posts (for example LendSight moving
to 2025), update that app's two files in the same PR, so before-and-after runs
stay comparable.

## Uncached runs (staff)

Uncached runs send `force_refresh`, which the server honours only for staff,
and which now also turns off BigQuery's own result cache (`use_query_cache=False`,
label `refresh=forced`). `uncached-batch.json` lists all seven payloads (two
runs each; MergerMeter with a 30 minute limit), so one command does them all.

The script signs in one of two ways:

- **Password accounts:** `TEST_EMAIL` / `TEST_PASSWORD` in the environment.
- **Google or Microsoft sign-in (no password):** `--cookie-file`, holding the
  site's `session` cookie copied from a signed-in browser. The file must be
  `chmod 600` and outside the repository, or the script refuses it. The value
  is never printed or written anywhere else, and the script deletes the file
  when the runs end, whether they completed, failed or were stopped with
  Ctrl-C. Deleting the file does not sign the browser out. The copied value
  works until the browser session expires, so never paste it anywhere else.

### Copying the session cookie (Chrome or Edge)

1. Open the testing site
   (https://justdata-testing-854699313651.us-east1.run.app/) and sign in
   with the staff account.
2. Open the developer tools: on a Mac, press Cmd+Option+I. On Windows, press
   F12.
3. In the row of tabs at the top of the panel, click **Application**. If you
   can't see it, click **»** to show the hidden tabs.
4. In the left column, under **Storage**, open **Cookies** and click the
   site's address (`https://justdata-testing-854699313651.us-east1.run.app`).
5. In the table, click the row whose **Name** is `session`. Its value appears
   under the table as **Cookie Value**. Don't tick "Show URL-decoded".
6. Double-click the value in the table's **Value** column. Press Cmd+A
   (Ctrl+A on Windows), then Cmd+C (Ctrl+C) to copy it.
7. In Terminal, write the clipboard to a file only you can read, then clear
   the clipboard. The value never appears on screen or in your shell history:

```bash
( umask 077; pbpaste > ~/justdata-cookie.txt ); pbcopy < /dev/null
```

Then run the batch straight away, from the repository:

```bash
cd /Users/jadedlebi/justdata
mkdir -p audit/timings
.venv/bin/python scripts/time_analysis.py run --batch scripts/timing_payloads/uncached-batch.json --uncached --cookie-file ~/justdata-cookie.txt --out audit/timings/uncached.jsonl

# Bytes billed per run, matched by the job label (needs bigquery.jobs.listAll on justdata-ncrc)
.venv/bin/python scripts/time_analysis.py bytes --in audit/timings/uncached.jsonl
```

With a password account, use `set -a; source ~/.justdata-staff.env; set +a`
and leave out `--cookie-file`. A single payload still runs with
`--app`, `--payload` and `--label` in place of `--batch`.

That is 14 analyses (12 with narratives, plus two MergerMeter workbooks). Check as they run:

- The command prints `Signed in; role reported by the site: staff`.
  Any other role prints a WARNING, and the runs may be cache hits.
- Each run line shows `cache_hit=False`.
- The last line is `Deleted the cookie file …`.
- In the `bytes` output, `matched_by` reads `job label` and `bq_cache_hits`
  is 0. If it reads `service account + window`, the labels did not attach.

The JSONL holds job ids, timings and progress steps; no credentials or user
identity beyond the role.
