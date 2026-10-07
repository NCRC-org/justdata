"""MergerMeter writes its results to the analysis cache (spec 04 pending fix).

_perform_analysis used to return None, so the blueprint's
`if result and result.get('success')` cache write never ran and every
MergerMeter run was recomputed. Its workbook was also only on the local disk
of the instance that ran it, so a cache hit served elsewhere would 404.
"""

from pathlib import Path


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
                        lambda job_id, form: {"success": True, "job_id": job_id, "excel_filename": f"x_{job_id}.xlsx"})

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
