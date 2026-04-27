"""Smoke tests for lenderprofile blueprint.

Blueprint has no /health; only ``/`` is a GET with no path parameters.
``/report/<id>`` and ``/progress/<id>`` smoke the parameterized GETs.
"""
import uuid


def test_lenderprofile_index(unified_client):
    resp = unified_client.get("/lenderprofile/")
    assert resp.status_code in (200, 302, 401, 403)


def test_lenderprofile_report_get(unified_client):
    rid = str(uuid.UUID(int=0))
    resp = unified_client.get(f"/lenderprofile/report/{rid}")
    assert resp.status_code in (200, 302, 401, 403, 404)


def test_lenderprofile_progress_get(unified_client):
    jid = str(uuid.UUID(int=1))
    resp = unified_client.get(f"/lenderprofile/progress/{jid}")
    assert resp.status_code in (200, 302, 401, 403)
