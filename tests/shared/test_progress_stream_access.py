"""A progress stream is never more permissive than the route that starts the run.

Jad, 2026-10-27 (#235): MergerMeter's and DataExplorer's streams only needed a
sign-in while their run routes were admin-only. Every app's /progress route
must carry the same require_access as its run route, so a role that cannot
start a run cannot follow one either.

Run routes are found, not listed: a POST route in an app's blueprint whose
handler creates a job id (new_job_id() or uuid4()). A new app or route is
covered without editing this file. Left out: apps not registered in
main/app.py (ElectWatch, archived) and MergerMeter's API-key endpoints, which
external callers use with a shared key instead of a session and return the
workbook in the response rather than through a stream.
"""

import ast
from pathlib import Path

import pytest

from justdata.main.auth import VALID_USER_TYPES, has_access

APPS_DIR = Path(__file__).resolve().parents[2] / "justdata/apps"
MAIN_APP = (APPS_DIR.parent / "main/app.py").read_text()
LEVELS = {"hidden": 0, "locked": 1, "limited": 2, "full": 3}


def _routes(path):
    """(rule, methods, require_access args or None, handler source) per route."""
    source = path.read_text()
    out = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.FunctionDef):
            continue
        rule, methods, access = None, ("GET",), None
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call):
                continue
            name = getattr(dec.func, "attr", getattr(dec.func, "id", ""))
            if name == "route" and dec.args and isinstance(dec.args[0], ast.Constant):
                rule = dec.args[0].value
                for kw in dec.keywords:
                    if kw.arg == "methods":
                        methods = tuple(ast.literal_eval(kw.value))
            elif name == "require_access":
                access = tuple(ast.literal_eval(a) for a in dec.args)
        if rule:
            out.append((rule, methods, access, ast.get_source_segment(source, node)))
    return out


def _cases():
    cases = []
    for bp in sorted(APPS_DIR.glob("*/blueprint.py")):
        if f"url_prefix='/{bp.parent.name}'" not in MAIN_APP:
            continue
        routes = _routes(bp)
        streams = [r for r in routes if r[0].startswith("/progress")]
        runs = [r for r in routes if "POST" in r[1]
                and ("new_job_id(" in r[3] or "uuid4()" in r[3])
                and "MERGERMETER_API_KEY" not in r[3]]
        if streams:
            cases.append(pytest.param(bp.parent.name, streams, runs, id=bp.parent.name))
    return cases


CASES = _cases()


def test_the_apps_with_streams_are_all_found():
    found = {c.values[0] for c in CASES}
    assert {"lendsight", "bizsight", "branchsight", "mergermeter", "dataexplorer"} <= found


@pytest.mark.parametrize("app_name,streams,runs", CASES)
def test_stream_is_gated_like_its_run_route(app_name, streams, runs):
    assert runs, f"{app_name}: no run route found for its progress stream"
    for run_rule, _, run_access, _ in runs:
        assert run_access, f"{app_name} {run_rule}: run route has no require_access"
        for rule, _, access, _ in streams:
            assert access, f"{app_name} {rule}: stream has no require_access (run route {run_rule} has {run_access})"
            assert access[0] == run_access[0], (app_name, rule, access, run_access)
            assert LEVELS[access[1]] >= LEVELS[run_access[1]], (app_name, rule, access, run_access)


@pytest.fixture(params=("testing", "staging"))
def client_for(request, monkeypatch):
    monkeypatch.setenv("JUSTDATA_ENV", request.param)
    from justdata.main.app import create_app
    app = create_app()
    app.config["TESTING"] = True

    def make(user_type):
        client = app.test_client()
        with client.session_transaction() as s:
            s["user_type"] = user_type
            s["firebase_user"] = {"uid": f"t-{user_type}", "email": "t@example.org", "email_verified": True}
        return client
    return make


@pytest.mark.parametrize("app_name,streams,runs", CASES)
def test_roles_refused_a_run_are_refused_the_stream(client_for, app_name, streams, runs):
    run_app, run_level = runs[0][2]
    for user_type in VALID_USER_TYPES:
        if has_access(run_app, run_level, user_type):
            continue
        client = client_for(user_type)
        for rule, _, _, _ in streams:
            path = f"/{app_name}" + rule.replace("<job_id>", "no-such-job")
            resp = client.get(path)
            assert resp.status_code in (302, 401, 403) or b"text/event-stream" not in resp.mimetype.encode(), \
                (app_name, user_type, path, resp.status_code)
            resp.close()
