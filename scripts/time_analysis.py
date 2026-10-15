#!/usr/bin/env python3
"""Time analysis runs on a deployed JustData site (spec 04 audit and budget).

Signs in the same way as scripts/check_tester_gate.py, posts one analysis to
/<app>/analyze N times, follows /<app>/progress/<job_id> (SSE) and records,
per run: wall-clock to the first event, to `done`, and to /report-data
returning 200 (BranchSight and LendSight can report `done` before the result
is stored), every progress step with its timestamp, whether the run was a
cache hit, and any error. Once the shared spec 04 PR adds a `perf` payload to
/report-data, its stage timings are recorded too.

BigQuery bytes billed are read afterwards from INFORMATION_SCHEMA.JOBS_BY_PROJECT
(the `bytes` subcommand). Every analysis job is labelled job=<job_id>
(shared/utils/query_context.py), so each run's bytes are matched exactly by
that label. Runs recorded before the labels existed fall back to the app's
service account and the run's UTC window, which would also count concurrent
traffic.

Sign-in is one of two ways, and neither is ever printed or written:
  - TEST_EMAIL and TEST_PASSWORD from the environment (accounts with a password);
  - --cookie-file PATH: the site's `session` cookie, copied from a signed-in
    browser, for accounts that sign in with Google or Microsoft only. The file
    must be chmod 600 and outside the repository; the script deletes it when
    the runs end, whether they completed or failed.
Uncached runs send force_refresh, which the server honours only for staff
roles; the script records whether each run was in fact a cache hit, so a
refused bypass is visible.

    set -a; source ~/.justdata-test.env; set +a
    python scripts/time_analysis.py run --app lendsight --payload payloads/cook.json \\
        --runs 3 --label cook-cached --out timings.jsonl
    python scripts/time_analysis.py run --app lendsight --payload payloads/cook.json \\
        --runs 2 --uncached --label cook-uncached --out timings.jsonl      # staff only
    python scripts/time_analysis.py run --batch scripts/timing_payloads/uncached-batch.json \
        --uncached --cookie-file ~/justdata-cookie.txt --out timings.jsonl  # staff, one cookie
    python scripts/time_analysis.py bytes --in timings.jsonl                # needs bq access

The payload file holds the fields the app's own page posts to /analyze (see
the spec 04 audit matrix for each app's fields): a JSON body for the Sight
apps, form fields for MergerMeter (list or object values are JSON-encoded, as
its page does for assessment areas). force_refresh is set by the script.

MergerMeter writes its runs to the analysis cache since #214 (a run whose
workbook reached GCS); cache_hit records whether a run was served from it.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

# This script times runs on a deployed site and must never call the AI
# itself or write AI usage from this machine (env_utils.ai_disabled).
os.environ["JUSTDATA_AI_DISABLED"] = "1"

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_tester_gate import DEFAULT_BASE_URL, signed_in_session  # noqa: E402

APPS = ("lendsight", "bizsight", "branchsight", "mergermeter")
# Service account each app's BigQuery jobs run under (justdata-ncrc).
SERVICE_ACCOUNTS = {app: f"{app}@justdata-ncrc.iam.gserviceaccount.com" for app in APPS}
CACHE_HIT_STEP = "(from cache)"
STAFF_ROLES = ("staff", "senior_executive", "admin")
COOKIE_NAME = "session"  # Flask's session cookie (justdata/main/app.py)
REPO = Path(__file__).resolve().parents[1]


def utc_now():
    return datetime.now(timezone.utc)


def follow_progress(session, base_url, app, job_id, t0, timeout):
    """Read the SSE stream until done/error or timeout. Returns (steps, final)."""
    steps, final = [], None
    url = f"{base_url}/{app}/progress/{job_id}"
    try:
        with session.get(url, stream=True, timeout=(30, timeout)) as resp:
            named = False
            for raw in resp.iter_lines(decode_unicode=True):
                if time.monotonic() - t0 > timeout:
                    break
                if not raw:
                    named = False   # blank line ends an SSE block
                    continue
                if raw.startswith("event:"):
                    named = True    # e.g. the 10 s heartbeat; not a progress event
                    continue
                if named or not raw.startswith("data:"):
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


def cookie_file_path(path):
    """The cookie file, checked before it is read: outside the repository (so
    it can never be committed) and readable by its owner only."""
    p = Path(path).expanduser().resolve()
    if p == REPO or REPO in p.parents:
        sys.exit(f"--cookie-file must be outside the repository ({REPO}). Move it and run again.")
    if not p.is_file():
        sys.exit(f"--cookie-file {p} does not exist.")
    if p.stat().st_mode & 0o077:
        sys.exit(f"--cookie-file {p} must be readable by you only. Run: chmod 600 {p}")
    return p


def cookie_session(base_url, path):
    """A requests.Session carrying the browser's session cookie, and the role
    /api/auth/status reports for it. The cookie value is never printed."""
    value = path.read_text().strip()
    if value.startswith(COOKIE_NAME + "="):
        value = value[len(COOKIE_NAME) + 1:]
    if not value:
        sys.exit("The cookie file is empty.")
    session = requests.Session()
    session.cookies.set(COOKIE_NAME, value, domain=urlparse(base_url).hostname, path="/")
    resp = session.get(f"{base_url}/api/auth/status", timeout=60)
    body = resp.json() if resp.headers.get("Content-Type", "").startswith("application/json") else {}
    if resp.status_code != 200 or not body.get("authenticated"):
        sys.exit("The site did not accept the session cookie (signed out, expired, or copied from "
                 "another site). Sign in again in the browser and copy a fresh value.")
    return session, body.get("user_type")


def load_jobs(args):
    """What to time: one --app/--payload/--label, or every entry of --batch."""
    if args.batch:
        if args.app or args.payload or args.label:
            sys.exit("Use --batch or --app/--payload/--label, not both.")
        with open(args.batch) as f:
            jobs = json.load(f)
    elif args.app and args.payload and args.label:
        jobs = [{"app": args.app, "payload": args.payload, "label": args.label}]
    else:
        sys.exit("Give --app, --payload and --label, or --batch.")
    for job in jobs:
        if job.get("app") not in APPS or not job.get("payload") or not job.get("label"):
            sys.exit(f"Each batch entry needs app (one of {', '.join(APPS)}), payload and label: {job}")
        with open(job["payload"]) as f:
            job["body"] = json.load(f)
    return jobs


def time_jobs(args, jobs, session, user_type, base_url):
    print(f"Signed in; role reported by the site: {user_type}")
    if args.uncached and user_type not in STAFF_ROLES:
        print("WARNING: force_refresh is honoured only for staff roles; these runs may hit the cache.")
    with open(args.out, "a") as out:
        for job in jobs:
            runs, timeout = job.get("runs", args.runs), job.get("timeout", args.timeout)
            for i in range(1, runs + 1):
                rec = one_run(session, base_url, job["app"], job["body"], args.uncached, timeout)
                rec.update(app=job["app"], label=job["label"], run=i, mode="uncached" if args.uncached else "cached",
                           role=user_type, base_url=base_url)
                out.write(json.dumps(rec) + "\n")
                out.flush()
                print(f"{job['app']} {job['label']} run {i}: done={rec.get('done_s')}s "
                      f"report={rec.get('report_ready_s')}s cache_hit={rec.get('cache_hit')} error={rec.get('error')}")


def cmd_run(args):
    jobs = load_jobs(args)
    base_url = args.base_url.rstrip("/")
    if args.cookie_file:
        path = cookie_file_path(args.cookie_file)
        try:
            session, user_type = cookie_session(base_url, path)
            time_jobs(args, jobs, session, user_type, base_url)
        finally:
            # Completed, failed or interrupted (Ctrl-C): the cookie does not outlive the run.
            path.unlink(missing_ok=True)
            print(f"Deleted the cookie file {path}.")
        return
    email, password = os.environ.get("TEST_EMAIL"), os.environ.get("TEST_PASSWORD")
    if not email or not password:
        sys.exit("Set TEST_EMAIL and TEST_PASSWORD in the environment, or pass --cookie-file.")
    session, user_type = signed_in_session(base_url, email, password)
    time_jobs(args, jobs, session, user_type, base_url)


def cmd_bytes(args):
    """Sum BigQuery bytes billed per run window, from INFORMATION_SCHEMA."""
    from google.cloud import bigquery  # requires credentials with bigquery.jobs.listAll
    client = bigquery.Client(project=args.project)
    # Match the run's own jobs by their job label; fall back to the service
    # account and time window when the label is absent (older runs).
    sql = f"""
        WITH jobs AS (
          SELECT total_bytes_billed, total_bytes_processed, cache_hit,
                 (SELECT value FROM UNNEST(labels) WHERE key = 'job') AS job_label
          FROM `{args.project}`.`region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
          WHERE job_type = 'QUERY' AND creation_time BETWEEN @start AND @end
            AND (user_email = @sa OR EXISTS (SELECT 1 FROM UNNEST(labels) WHERE key = 'job' AND value = @job))
        )
        SELECT COUNT(*) AS jobs, SUM(total_bytes_billed) AS bytes_billed,
               SUM(total_bytes_processed) AS bytes_processed,
               COUNTIF(cache_hit) AS bq_cache_hits,
               COUNTIF(job_label = @job) AS labelled_jobs
        FROM jobs
        WHERE job_label = @job OR NOT EXISTS (SELECT 1 FROM jobs WHERE job_label = @job)
    """
    with open(args.infile) as f:
        records = [json.loads(line) for line in f if line.strip()]
    print("app\tlabel\trun\tmode\tjobs\tbytes_billed\tbytes_processed\tbq_cache_hits\tmatched_by")
    for r in records:
        params = [
            bigquery.ScalarQueryParameter("sa", "STRING", SERVICE_ACCOUNTS[r["app"]]),
            bigquery.ScalarQueryParameter("start", "TIMESTAMP", r["started_utc"]),
            bigquery.ScalarQueryParameter("end", "TIMESTAMP", r["ended_utc"]),
            bigquery.ScalarQueryParameter("job", "STRING", (r.get("job_id") or "").lower()[:63]),
        ]
        row = list(client.query(sql, job_config=bigquery.QueryJobConfig(query_parameters=params)).result())[0]
        print(f"{r['app']}\t{r['label']}\t{r['run']}\t{r['mode']}\t{row.jobs}\t{row.bytes_billed}\t"
              f"{row.bytes_processed}\t{row.bq_cache_hits}\t{'job label' if row.labelled_jobs else 'service account + window'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="time N analysis runs")
    run.add_argument("--app", choices=APPS)
    run.add_argument("--payload", help="JSON file: the body the app's page posts to /analyze")
    run.add_argument("--label", help="e.g. cook-cached; ties rows to the matrix")
    run.add_argument("--batch", help="JSON list of {app, payload, label, runs?, timeout?}, run in order "
                                     "in place of --app/--payload/--label")
    run.add_argument("--runs", type=int, default=3)
    run.add_argument("--uncached", action="store_true", help="send force_refresh (staff only)")
    run.add_argument("--cookie-file", help="file holding the site's session cookie (chmod 600, outside the "
                                           "repository); deleted when the runs end")
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
