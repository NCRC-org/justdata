"""A run that finds no data must end, not hang (hygiene PR, item 3).

LendSight and BranchSight report a failed run (for example a county with no
data) with progress_tracker.update_progress('error', ...). That step used to
be ignored because 'error' was not a known step, so the job never reached
done and the page waited forever. It is now terminal and carries a
reference id (spec 04 A3 error state).
"""

import re
import uuid

import pytest

from justdata.shared.utils.progress_tracker import create_progress_tracker, get_progress

NO_DATA = "No data found for the specified parameters"
REF_RE = re.compile(r"Reference: [0-9a-f]{8}$")


def _job_id():
    # Unique per run: the progress store also persists to disk, so a fixed id
    # could read a previous run's result.
    return f"test-{uuid.uuid4().hex}"


def test_error_step_is_terminal_with_a_reference():
    job_id = _job_id()
    tracker = create_progress_tracker(job_id)
    tracker.update_progress("error", message=NO_DATA)
    progress = get_progress(job_id)
    assert progress["done"] is True
    assert progress["error"].startswith(NO_DATA)
    assert REF_RE.search(progress["error"])


def test_error_step_accepts_the_old_positional_message():
    job_id = _job_id()
    tracker = create_progress_tracker(job_id)
    tracker.update_progress("error", NO_DATA)
    progress = get_progress(job_id)
    assert progress["done"] is True and progress["error"].startswith(NO_DATA)


@pytest.fixture
def platform_app():
    from justdata.main.app import create_app
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.mark.parametrize("app_key,payload", [
    ("lendsight", {
        "selection_type": "county", "state_code": "01", "loan_purpose": ["purchase"],
        "counties": "Lowndes County, Alabama",
        "counties_data": [{"name": "Lowndes County, Alabama", "geoid5": "01085",
                           "state_fips": "01", "county_fips": "085"}],
    }),
    ("branchsight", {
        "selection_type": "county", "state_code": "01",
        "counties": "Lowndes County, Alabama", "years": "2021,2022,2023,2024,2025",
    }),
])
def test_county_with_no_data_ends_the_job(platform_app, monkeypatch, app_key, payload):
    blueprint = __import__(f"justdata.apps.{app_key}.blueprint", fromlist=["x"])
    monkeypatch.setattr(blueprint, "run_in_background", lambda work: work())
    monkeypatch.setattr(blueprint, "lookup_cached_analysis", lambda *a, **k: None)
    monkeypatch.setattr(blueprint, "parse_web_parameters",
                        lambda *a, **k: (["Lowndes County, Alabama"], [2021, 2022, 2023, 2024, 2025]))
    monkeypatch.setattr(blueprint, "run_analysis", lambda *a, **k: {"success": False, "error": NO_DATA})
    if hasattr(blueprint, "record_completion"):
        monkeypatch.setattr(blueprint, "record_completion", lambda *a, **k: None)

    client = platform_app.test_client()
    with client.session_transaction() as s:
        s["user_type"] = "staff"
        s["firebase_user"] = {"uid": "t", "email": "t@example.org", "email_verified": True}
    resp = client.post(f"/{app_key}/analyze", json=payload)
    assert resp.status_code == 200, resp.get_data(as_text=True)
    job_id = resp.get_json()["job_id"]

    progress = get_progress(job_id)
    assert progress["done"] is True
    assert progress["error"].startswith(NO_DATA)
    assert REF_RE.search(progress["error"])
