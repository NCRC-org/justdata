#!/usr/bin/env python3
"""Time analysis runs on a deployed JustData site (spec 04 audit and budget).

Signs in the same way as scripts/check_tester_gate.py, posts one analysis to
/<app>/analyze N times, follows /<app>/progress/<job_id> (SSE) and records,
per run: wall-clock to the first event, to `done`, and to /report-data
returning 200 (BranchSight and LendSight can report `done` before the result
is stored), every progress step with its timestamp, whether the run was a
cache hit, and any error. Once the shared spec 04 PR adds a `perf` payload to
/report-data, its stage timings are recorded too.

Each run's UTC start/end window is written out so BigQuery bytes billed can be
read afterwards from INFORMATION_SCHEMA.JOBS_BY_PROJECT (the `bytes`
subcommand), filtered by the app's service account. The client sets no job
labels yet, so concurrent traffic under the same service account in a window
would be counted too; keep windows short and note it.

Credentials come only from the environment (TEST_EMAIL, TEST_PASSWORD) and
are never printed or written. Uncached runs send force_refresh, which the
server honours only for staff roles; the script records whether each run was
in fact a cache hit, so a refused bypass is visible.

    set -a; source ~/.justdata-test.env; set +a
    python scripts/time_analysis.py run --app lendsight --payload payloads/cook.json \\
        --runs 3 --label cook-cached --out timings.jsonl
    python scripts/time_analysis.py run --app lendsight --payload payloads/cook.json \\
        --runs 2 --uncached --label cook-uncached --out timings.jsonl      # staff only
    python scripts/time_analysis.py bytes --in timings.jsonl                # needs bq access

The payload file holds the fields the app's own page posts to /analyze (see
the spec 04 audit matrix for each app's fields): a JSON body for the Sight
apps, form fields for MergerMeter (list or object values are JSON-encoded, as
its page does for assessment areas). force_refresh is set by the script.

MergerMeter currently never writes results to the analysis cache (audit
finding), so its "cached" runs are recomputed; cache_hit records that.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_tester_gate import DEFAULT_BASE_URL, signed_in_session  # noqa: E402

APPS = ("lendsight", "bizsight", "branchsight", "mergermeter")
# Service account each app's BigQuery jobs run under (justdata-ncrc).
SERVICE_ACCOUNTS = {app: f"{app}@justdata-ncrc.iam.gserviceaccount.com" for app in APPS}
CACHE_HIT_STEP = "(from cache)"


def utc_now():
    return datetime.now(timezone.utc)


def follow_progress(session, base_url, app, job_id, t0, timeout):
    """Read the SSE stream until done/error or timeout. Returns (steps, final)."""
    steps, final = [], None
    url = f"{base_url}/{app}/progress/{job_id}"
    try:
        with session.get(url, stream=True, timeout=(30, timeout)) as resp:
            for raw in resp.iter_lines(decode_unicode=True):
                if time.monotonic() - t0 > timeout:
                    break
                if not raw or not raw.startswith("data:"):
                    continue
                event = json.loads(raw[5:].strip())
                event["t"] = round(time.monotonic() - t0, 3)
                steps.append(event)
                if event.get("done") or event.get("error"):
                    final = event
                    break
    except requests.exceptions.RequestException as e:
        final = {"error": f"stream: {type(e).__name__}", "t": round(time.monotonic() - t0, 3)}
    return steps, final


def wait_for_report(session, base_url, app, job_id, t0, timeout):
    """Poll /report-data until 200. Returns (seconds, perf payload or None, status)."""
    status = None
    while time.monotonic() - t0 < timeout:
        resp = session.get(f"{base_url}/{app}/report-data", params={"job_id": job_id}, timeout=60)
        status = resp.status_code
        if status == 200:
            body = resp.json()
            return round(time.monotonic() - t0, 3), body.get("perf"), status
        if status not in (202, 404):
            break
        time.sleep(1)
    return None, None, status


# MergerMeter's /analyze reads a multipart form (request.form) and expects
# force_refresh as '1'/'0'; the Sight apps read a JSON body with a boolean.
FORM_APPS = ("mergermeter",)


def one_run(session, base_url, app, payload, uncached, timeout):
    started = utc_now()
    t0 = time.monotonic()
    if app in FORM_APPS:
        form = {k: (v if isinstance(v, str) else json.dumps(v)) for k, v in payload.items()}
        form["force_refresh"] = "1" if uncached else "0"
        resp = session.post(f"{base_url}/{app}/analyze", data=form, timeout=60)
    else:
        resp = session.post(f"{base_url}/{app}/analyze", json=dict(payload, force_refresh=bool(uncached)),
                            timeout=60)
    record = {"started_utc": started.isoformat(), "http_status": resp.status_code}
    try:
        data = resp.json()
    except ValueError:
        data = {}
    job_id = data.get("job_id")
    record.update(job_id=job_id, cached_response=bool(data.get("cached")))
    if not job_id:
        record.update(error=data.get("error") or f"no job_id (HTTP {resp.status_code})",
                      ended_utc=utc_now().isoformat())
        return record

    steps, final = follow_progress(session, base_url, app, job_id, t0, timeout)
    record["steps"] = steps
    record["first_event_s"] = steps[0]["t"] if steps else None
    record["done_s"] = final["t"] if final and final.get("done") and not final.get("error") else None
    record["error"] = (final or {}).get("error") or (None if final else "timeout: no done/error event")
    record["cache_hit"] = record["cached_response"] or any(CACHE_HIT_STEP in (s.get("step") or "") for s in steps)
    if record["done_s"] is not None:
        report_s, perf, status = wait_for_report(session, base_url, app, job_id, t0, timeout)
        record.update(report_ready_s=report_s, report_status=status, perf=perf)
    record["ended_utc"] = utc_now().isoformat()
    return record


def cmd_run(args):
    email, password = os.environ.get("TEST_EMAIL"), os.environ.get("TEST_PASSWORD")
    if not email or not password:
        sys.exit("TEST_EMAIL and TEST_PASSWORD must both be set in the environment.")
    with open(args.payload) as f:
        payload = json.load(f)
    base_url = args.base_url.rstrip("/")
    session, user_type = signed_in_session(base_url, email, password)
    print(f"Signed in; role reported by /api/auth/login: {user_type}")
    if args.uncached and user_type not in ("staff", "senior_executive", "admin"):
        print("WARNING: force_refresh is honoured only for staff roles; these runs may hit the cache.")

    with open(args.out, "a") as out:
        for i in range(1, args.runs + 1):
            rec = one_run(session, base_url, args.app, payload, args.uncached, args.timeout)
            rec.update(app=args.app, label=args.label, run=i, mode="uncached" if args.uncached else "cached",
                       role=user_type, base_url=base_url)
            out.write(json.dumps(rec) + "\n")
            print(f"run {i}: done={rec.get('done_s')}s report={rec.get('report_ready_s')}s "
                  f"cache_hit={rec.get('cache_hit')} error={rec.get('error')}")


def cmd_bytes(args):
    """Sum BigQuery bytes billed per run window, from INFORMATION_SCHEMA."""
    from google.cloud import bigquery  # requires credentials with bigquery.jobs.listAll
    client = bigquery.Client(project=args.project)
    sql = f"""
        SELECT COUNT(*) AS jobs, SUM(total_bytes_billed) AS bytes_billed,
               SUM(total_bytes_processed) AS bytes_processed,
               COUNTIF(cache_hit) AS bq_cache_hits
        FROM `{args.project}`.`region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
        WHERE job_type = 'QUERY' AND user_email = @sa
          AND creation_time BETWEEN @start AND @end
    """
    with open(args.infile) as f:
        records = [json.loads(line) for line in f if line.strip()]
    print("app\tlabel\trun\tmode\tjobs\tbytes_billed\tbytes_processed\tbq_cache_hits")
    for r in records:
        params = [
            bigquery.ScalarQueryParameter("sa", "STRING", SERVICE_ACCOUNTS[r["app"]]),
            bigquery.ScalarQueryParameter("start", "TIMESTAMP", r["started_utc"]),
            bigquery.ScalarQueryParameter("end", "TIMESTAMP", r["ended_utc"]),
        ]
        row = list(client.query(sql, job_config=bigquery.QueryJobConfig(query_parameters=params)).result())[0]
        print(f"{r['app']}\t{r['label']}\t{r['run']}\t{r['mode']}\t{row.jobs}\t{row.bytes_billed}\t"
              f"{row.bytes_processed}\t{row.bq_cache_hits}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="time N analysis runs")
    run.add_argument("--app", choices=APPS, required=True)
    run.add_argument("--payload", required=True, help="JSON file: the body the app's page posts to /analyze")
    run.add_argument("--runs", type=int, default=3)
    run.add_argument("--uncached", action="store_true", help="send force_refresh (staff only)")
    run.add_argument("--label", required=True, help="e.g. cook-cached; ties rows to the matrix")
    run.add_argument("--out", default="timings.jsonl")
    run.add_argument("--timeout", type=int, default=600, help="seconds per run before giving up")
    run.add_argument("--base-url", default=DEFAULT_BASE_URL)
    run.set_defaults(func=cmd_run)
    b = sub.add_parser("bytes", help="BigQuery bytes billed per recorded run window")
    b.add_argument("--in", dest="infile", default="timings.jsonl")
    b.add_argument("--project", default="justdata-ncrc")
    b.set_defaults(func=cmd_bytes)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
