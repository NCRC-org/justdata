"""scripts/time_analysis.py reads progress events and ignores named SSE
events such as the 10 s heartbeat."""

import importlib.util
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"


def _load():
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("time_analysis", SCRIPTS / "time_analysis.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Resp:
    def __init__(self, lines):
        self.lines = lines

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def iter_lines(self, decode_unicode=True):
        return iter(self.lines)


class _Session:
    def __init__(self, lines):
        self.lines = lines

    def get(self, *a, **k):
        return _Resp(self.lines)


def test_heartbeats_are_not_recorded_as_steps():
    ta = _load()
    lines = [": connected", "",
             'data: {"percent": 88, "step": "Building charts and narrative", "done": false, "error": null}', "",
             "event: heartbeat", "data: {}", "",
             'data: {"percent": 100, "step": "Analysis completed!", "done": true, "error": null}', ""]
    steps, final = ta.follow_progress(_Session(lines), "http://x", "lendsight", "job", 0, 10**9)
    assert [s["percent"] for s in steps] == [88, 100]
    assert final["done"] is True
