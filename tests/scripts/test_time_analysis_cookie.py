"""scripts/time_analysis.py --cookie-file: the file must be chmod 600 and
outside the repository, its value is never printed, and the file is deleted
when the runs end, whether they completed or failed."""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
SECRET = "eyJmYWtlIjoiY29va2llIn0.not-a-real-session"


@pytest.fixture
def ta():
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("time_analysis", SCRIPTS / "time_analysis.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _cookie(tmp_path, text=SECRET, mode=0o600):
    p = tmp_path / "cookie.txt"
    p.write_text(text + "\n")
    p.chmod(mode)
    return p


def _args(cookie, **kw):
    base = dict(batch=None, app="lendsight", payload=str(SCRIPTS / "timing_payloads/lendsight-cook.json"),
                label="t", runs=1, uncached=True, out="/dev/null", timeout=5,
                base_url="https://example.test", cookie_file=str(cookie))
    base.update(kw)
    return argparse.Namespace(**base)


class _Status:
    def __init__(self, body, code=200):
        self.status_code, self._body = code, body
        self.headers = {"Content-Type": "application/json"}

    def json(self):
        return self._body


def test_refuses_a_file_others_can_read_and_leaves_it(ta, tmp_path, capsys):
    p = _cookie(tmp_path, mode=0o644)
    with pytest.raises(SystemExit, match="chmod 600"):
        ta.cmd_run(_args(p))
    assert p.exists()


def test_refuses_a_file_inside_the_repository(ta):
    with pytest.raises(SystemExit, match="outside the repository"):
        ta.cookie_file_path(str(ta.REPO / "scripts" / "time_analysis.py"))


def test_cookie_is_sent_and_the_file_deleted_after_a_completed_run(ta, tmp_path, monkeypatch, capsys):
    p = _cookie(tmp_path, text="session=" + SECRET)
    seen = {}

    def status(self, url, **kw):
        seen["cookie"] = self.cookies.get("session")
        return _Status({"authenticated": True, "user_type": "staff", "user": {"email": "x@example.org"}})

    monkeypatch.setattr(ta.requests.Session, "get", status)
    monkeypatch.setattr(ta, "one_run", lambda *a, **k: {"done_s": 1.0, "cache_hit": False})
    ta.cmd_run(_args(p))
    out = capsys.readouterr().out
    assert seen["cookie"] == SECRET
    assert not p.exists() and "Deleted the cookie file" in out
    assert SECRET not in out and "x@example.org" not in out and "role reported by the site: staff" in out


def test_file_is_deleted_when_the_cookie_is_refused(ta, tmp_path, monkeypatch, capsys):
    p = _cookie(tmp_path)
    monkeypatch.setattr(ta.requests.Session, "get", lambda self, url, **kw: _Status({"authenticated": False}))
    with pytest.raises(SystemExit, match="did not accept"):
        ta.cmd_run(_args(p))
    assert not p.exists() and SECRET not in capsys.readouterr().out


def test_file_is_deleted_when_a_run_fails(ta, tmp_path, monkeypatch, capsys):
    p = _cookie(tmp_path)
    monkeypatch.setattr(ta.requests.Session, "get",
                        lambda self, url, **kw: _Status({"authenticated": True, "user_type": "staff"}))

    def boom(*a, **k):
        raise RuntimeError("site down")

    monkeypatch.setattr(ta, "one_run", boom)
    with pytest.raises(RuntimeError):
        ta.cmd_run(_args(p))
    assert not p.exists()


def test_uncached_batch_lists_every_reference_payload(ta):
    batch = json.loads((SCRIPTS / "timing_payloads/uncached-batch.json").read_text())
    jobs = ta.load_jobs(argparse.Namespace(batch=str(SCRIPTS / "timing_payloads/uncached-batch.json"),
                                           app=None, payload=None, label=None))
    assert len(jobs) == len(batch) == 7
    assert sorted({j["app"] for j in jobs}) == sorted(ta.APPS)
    assert all(j["runs"] == 2 for j in jobs)
