"""MergerMeter writes its results to the analysis cache (spec 04 pending fix).

_perform_analysis used to return None, so the blueprint's
`if result and result.get('success')` cache write never ran and every
MergerMeter run was recomputed. Its workbook was also only on the local disk
of the instance that ran it, so a cache hit served elsewhere would 404.
"""

from pathlib import Path

import pytest


def test_successful_run_is_stored_in_the_analysis_cache(monkeypatch):
    from justdata.main.app import create_app
    import justdata.apps.mergermeter.blueprint as bp
    import justdata.apps.mergermeter.mergermeter_ops as ops

    stored = {}
    monkeypatch.setattr(bp, "run_in_background", lambda work, **kw: work())
    monkeypatch.setattr(bp, "lookup_cached_analysis", lambda *a, **k: None)
    monkeypatch.setattr(bp, "record_completion", lambda *a, **k: None)
    monkeypatch.setattr(bp, "store_cached_result", lambda **kw: stored.update(kw))
    monkeypatch.setattr(ops, "_perform_analysis",
                        lambda job_id, form: {"success": True, "job_id": job_id, "excel_filename": f"x_{job_id}.xlsx",
                                              "workbook_in_gcs": True})

    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()
    with client.session_transaction() as s:
        s["user_type"] = "staff"
        s["firebase_user"] = {"uid": "t", "email": "t@example.org", "email_verified": True}
    resp = client.post("/mergermeter/analyze", data={"acquirer_lei": "A" * 20, "target_lei": "B" * 20})
    assert resp.status_code == 200, resp.get_data(as_text=True)
    job_id = resp.get_json()["job_id"]
    assert stored.get("app_name") == "mergermeter"
    assert stored.get("job_id") == job_id
    assert stored["result_data"]["success"] is True


def test_workbook_missing_locally_is_fetched_from_gcs(tmp_path, monkeypatch):
    import justdata.apps.mergermeter.mergermeter_ops as ops

    monkeypatch.setattr(ops, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(ops, "get_excel_filename", lambda job_id: f"merger_analysis_{job_id}.xlsx")
    fetched = []

    def fake_download(blob, local):
        fetched.append(blob)
        Path(local).write_bytes(b"xlsx")
        return True

    monkeypatch.setattr(ops, "download_file", fake_download)
    path = ops.ensure_local_excel("job-9")
    assert path == tmp_path / "merger_analysis_job-9.xlsx" and path.exists()
    assert fetched == ["mergermeter/merger_analysis_job-9.xlsx"]

    monkeypatch.setattr(ops, "download_file", lambda blob, local: False)
    assert ops.ensure_local_excel("job-missing") is None


def test_perform_analysis_returns_a_success_result():
    """Guard against the original defect: the pipeline must return its result
    (the full pipeline is too heavy to run here, so check the code shape)."""
    import ast
    import inspect
    import justdata.apps.mergermeter.mergermeter_ops as ops

    tree = ast.parse(inspect.getsource(ops._perform_analysis))
    success_returns = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict)
        and any(isinstance(k, ast.Constant) and k.value == "success" and isinstance(v, ast.Constant) and v.value is True
                for k, v in zip(node.value.keys, node.value.values))
    ]
    assert success_returns, "_perform_analysis must return {'success': True, ...} so the result is cached"


def _client(monkeypatch):
    from justdata.main.app import create_app
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()
    with client.session_transaction() as s:
        s["user_type"] = "staff"
        s["firebase_user"] = {"uid": "t", "email": "t@example.org", "email_verified": True}
    return client


def test_run_whose_workbook_missed_gcs_is_not_cached(monkeypatch):
    """A cache hit is served by job_id from GCS; without the workbook there it
    would 404 on another instance, so such a run is not stored."""
    import justdata.apps.mergermeter.blueprint as bp
    import justdata.apps.mergermeter.mergermeter_ops as ops

    stored = {}
    monkeypatch.setattr(bp, "run_in_background", lambda work, **kw: work())
    monkeypatch.setattr(bp, "lookup_cached_analysis", lambda *a, **k: None)
    monkeypatch.setattr(bp, "record_completion", lambda *a, **k: None)
    monkeypatch.setattr(bp, "store_cached_result", lambda **kw: stored.update(kw))
    monkeypatch.setattr(ops, "_perform_analysis",
                        lambda job_id, form: {"success": True, "job_id": job_id, "excel_filename": "x.xlsx",
                                              "workbook_in_gcs": False})
    resp = _client(monkeypatch).post("/mergermeter/analyze", data={"acquirer_lei": "A" * 20, "target_lei": "B" * 20})
    assert resp.status_code == 200
    assert stored == {}


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def result(self):
        return self._rows


def test_stored_mergermeter_entry_is_found_again(monkeypatch):
    """End to end through the cache code: what store_cached_result writes for a
    MergerMeter run (no sections) is accepted by get_cached_result. It used to
    require two sections, so no MergerMeter entry was ever served."""
    from types import SimpleNamespace
    import justdata.shared.utils.analysis_cache as ac

    result = {"success": True, "job_id": "mm-1", "excel_filename": "x.xlsx", "workbook_in_gcs": True}
    assert ac.extract_sections("mergermeter", result) == []

    class Client:
        def query(self, sql, job_config=None):
            if "FROM `" + ac.CACHE_TABLE + "` c" in sql:
                return _Rows([SimpleNamespace(job_id="mm-1", cache_key="k", access_count=0, status="completed")])
            if "FROM `" + ac.SECTIONS_TABLE + "`" in sql:
                return _Rows([])
            return _Rows([])
    monkeypatch.setattr(ac, "get_bigquery_client", lambda *a, **k: Client())
    hit = ac.get_cached_result("mergermeter", {"acquirer_lei": "A" * 20, "target_lei": "B" * 20}, "staff")
    assert hit and hit["job_id"] == "mm-1"


# ---- A cache hit needs its workbook (spec 05 line 9, 2026-10-22) ----------
# The bucket deletes workbooks after WORKBOOK_RETENTION_DAYS, while cache rows
# had no expiry, so a hit could point at a deleted file and the report 404ed.

def _analyze_with_cached_hit(monkeypatch, workbook_there):
    import justdata.apps.mergermeter.blueprint as bp
    import justdata.apps.mergermeter.mergermeter_ops as ops
    import justdata.backend.reports as reports

    stored, hits = {}, []
    monkeypatch.setattr(reports, "get_cached_result",
                        lambda *a, **k: {"job_id": "old-job", "cache_key": "k", "result_data": {}})
    monkeypatch.setattr(ops, "workbook_in_storage", lambda job_id: workbook_there)
    monkeypatch.setattr(bp, "record_cache_hit", lambda *a, **k: hits.append(a[3].job_id))
    monkeypatch.setattr(bp, "run_in_background", lambda work, **kw: work())
    monkeypatch.setattr(bp, "record_completion", lambda *a, **k: None)
    monkeypatch.setattr(bp, "store_cached_result", lambda **kw: stored.update(kw))
    monkeypatch.setattr(ops, "_perform_analysis",
                        lambda job_id, form: {"success": True, "job_id": job_id, "excel_filename": "x.xlsx",
                                              "workbook_in_gcs": True})
    resp = _client(monkeypatch).post("/mergermeter/analyze", data={"acquirer_lei": "A" * 20, "target_lei": "B" * 20})
    assert resp.status_code == 200, resp.get_data(as_text=True)
    return resp.get_json(), stored, hits


def test_hit_whose_workbook_is_gone_runs_again(monkeypatch):
    body, stored, hits = _analyze_with_cached_hit(monkeypatch, workbook_there=False)
    assert not body.get("cached") and body["job_id"] != "old-job"
    assert hits == []
    assert stored["job_id"] == body["job_id"]


def test_hit_whose_workbook_is_there_is_served(monkeypatch):
    body, stored, hits = _analyze_with_cached_hit(monkeypatch, workbook_there=True)
    assert body == {"success": True, "job_id": "old-job", "cached": True}
    assert hits == ["old-job"] and stored == {}


def test_new_entries_expire_before_their_workbook(monkeypatch):
    from datetime import timedelta
    from justdata.apps.mergermeter.config import WORKBOOK_RETENTION_DAYS
    _body, stored, _hits = _analyze_with_cached_hit(monkeypatch, workbook_there=False)
    assert timedelta(0) < stored["expires_in"] < timedelta(days=WORKBOOK_RETENTION_DAYS)


def test_workbook_check_treats_an_unanswered_check_as_missing(monkeypatch):
    import justdata.apps.mergermeter.mergermeter_ops as ops
    monkeypatch.setattr(ops, "get_excel_filename", lambda job_id: f"merger_analysis_{job_id}.xlsx")
    asked = []
    for answer, expected in ((True, True), (False, False), (None, False)):
        monkeypatch.setattr(ops, "blob_exists", lambda path, a=answer: asked.append(path) or a)
        assert ops.workbook_in_storage("job-1") is expected
    assert set(asked) == {"mergermeter/merger_analysis_job-1.xlsx"}


def test_cache_row_carries_the_expiry(monkeypatch):
    """store_cached_result writes expires_at only when given a lifetime."""
    from datetime import datetime, timedelta, timezone
    from types import SimpleNamespace
    import justdata.shared.utils.analysis_cache as ac

    for lifetime in (timedelta(days=6, hours=23), None):
        seen = {}

        class Client:
            def query(self, sql, job_config=None):
                if "analysis_cache`" in sql and "INSERT" in sql:
                    seen.update({p.name: p.value for p in job_config.query_parameters})
                return SimpleNamespace(result=lambda *a, **k: [])
        monkeypatch.setattr(ac, "get_bigquery_client", lambda *a, **k: Client())
        ac.store_cached_result("mergermeter", {"acquirer_lei": "A" * 20}, "job-1", {"success": True},
                               metadata={}, expires_in=lifetime)
        if lifetime is None:
            assert seen["expires_at"] is None
        else:
            left = seen["expires_at"] - datetime.now(timezone.utc)
            assert timedelta(days=6, hours=22) < left <= lifetime


def test_lookup_turns_an_unavailable_hit_into_a_miss(monkeypatch):
    import justdata.backend.reports as reports
    monkeypatch.setattr(reports, "get_cached_result", lambda *a, **k: {"job_id": "j", "cache_key": "k"})
    caller = reports.Caller(user_type="staff")
    assert reports.lookup_cached_analysis("mergermeter", {}, caller, still_available=lambda j: False) is None
    assert reports.lookup_cached_analysis("mergermeter", {}, caller, still_available=lambda j: True).job_id == "j"
    assert reports.lookup_cached_analysis("lendsight", {}, caller).job_id == "j"


@pytest.mark.network
def test_bucket_lifecycle_matches_the_cache_expiry():
    """The bucket's delete rule is set outside this repo; this catches drift."""
    from justdata.apps.mergermeter.config import WORKBOOK_RETENTION_DAYS
    from justdata.shared.utils.gcs_storage import get_bucket
    try:
        bucket = get_bucket()
        bucket.reload()
    except Exception as e:  # credentials without bucket metadata access
        pytest.skip(f"cannot read the bucket's lifecycle: {type(e).__name__}")
    ages = [r["condition"].get("age") for r in bucket.lifecycle_rules
            if r.get("action", {}).get("type") == "Delete"]
    assert ages == [WORKBOOK_RETENTION_DAYS]
