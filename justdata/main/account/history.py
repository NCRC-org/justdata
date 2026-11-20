"""Section 4, "Your reports": the user's own runs from usage_log, by UID.

Only runs whose stored result still exists are listed (joined to
analysis_results), so every Open link opens a report. Runs that failed are
left out. One row per job, latest first.
"""
import json
import logging
from typing import Dict, List
from urllib.parse import quote

from justdata.main.account.content import ap_date
from justdata.shared.utils.no_data import NO_DATA

logger = logging.getLogger(__name__)

LIMIT = 25
APP_NAMES = {"lendsight": "LendSight", "bizsight": "BizSight",
             "branchsight": "BranchSight", "mergermeter": "MergerMeter"}

QUERY = """
SELECT u.job_id, u.app_name, ANY_VALUE(u.parameters_json) AS parameters_json,
       MAX(u.timestamp) AS ran_at
FROM `{usage}` u
JOIN (SELECT DISTINCT job_id FROM `{results}`) r ON r.job_id = u.job_id
WHERE u.user_id = @uid AND u.error_message IS NULL AND u.job_id IS NOT NULL
GROUP BY u.job_id, u.app_name
ORDER BY ran_at DESC
LIMIT {limit}
"""


def geography(app: str, params: Dict) -> str:
    """The place a run covered, from its logged parameters."""
    if not isinstance(params, dict):
        return NO_DATA
    if app == "bizsight":
        county = params.get("county_data")
        if isinstance(county, dict):
            return county.get("county_name") or county.get("name") or NO_DATA
        return NO_DATA
    counties = params.get("counties")
    if isinstance(counties, str) and counties.strip():
        return "; ".join(c.strip() for c in counties.split(";") if c.strip())
    if isinstance(counties, list) and counties:
        return "; ".join(str(c) for c in counties)
    return NO_DATA


def fetch_rows(uid: str) -> List[Dict]:
    """Raw rows from BigQuery. Separate so tests can replace it."""
    from google.cloud import bigquery
    from justdata.shared.utils import analysis_cache
    from justdata.shared.utils.bigquery_client import get_bigquery_client

    client = get_bigquery_client(analysis_cache.PROJECT_ID, app_name="cache")
    sql = QUERY.format(usage=analysis_cache.USAGE_TABLE, results=analysis_cache.RESULTS_TABLE, limit=LIMIT)
    job = client.query(sql, job_config=bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("uid", "STRING", uid)]))
    return [dict(row) for row in job.result()]


def report_history(uid: str, openable_apps) -> List[Dict]:
    """[{app, app_name, geography, ran_at, url}], or [] if it can't be read.
    `openable_apps` is the set of app keys the user can open now; a run in an
    app they can no longer open is left out, since its link would not work."""
    if not uid:
        return []
    try:
        rows = fetch_rows(uid)
    except Exception as e:
        logger.warning("Account page: report history unavailable: %s", type(e).__name__)
        return []
    out = []
    for row in rows:
        app = row.get("app_name")
        if app not in APP_NAMES or app not in openable_apps:
            continue
        try:
            params = json.loads(row.get("parameters_json") or "{}")
        except (TypeError, ValueError):
            params = {}
        out.append({
            "app": app,
            "app_name": APP_NAMES[app],
            "geography": geography(app, params),
            "ran_at": row.get("ran_at"),
            "ran_on": ap_date(row.get("ran_at")) or NO_DATA,
            "url": f"/{app}/report?job_id={quote(str(row['job_id']), safe='')}",
        })
    return out
