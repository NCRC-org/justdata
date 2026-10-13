"""JUSTDATA_AI_DISABLED=1 must make a real AI key unreachable (2026-10-13).

Local runs once wrote 88 rows to firebase_analytics.ai_usage although the key
variables had been unset: the shared env loader read the key back from .env.
With the switch set, every AI client refuses before reading a key, the key
lookups return nothing, a .env load leaves no AI key in the environment, and
usage is never written. conftest sets the switch for the whole suite.
"""

import ast
from pathlib import Path

import pytest

from justdata.shared.utils import env_utils
from justdata.shared.utils.env_utils import AIDisabledError

ROOT = Path(__file__).resolve().parents[2]
SENTINEL = "sk-ant-sentinel-must-not-be-read"


@pytest.fixture
def real_looking_key(monkeypatch):
    """A key in the environment, as a developer's shell or .env would have,
    and an Anthropic class that fails the test if anything constructs it."""
    import anthropic
    assert env_utils.ai_disabled()
    for name in env_utils.AI_KEY_NAMES:
        monkeypatch.setenv(name, SENTINEL)

    def construct(*a, **k):
        raise AssertionError("an AI client was created while JUSTDATA_AI_DISABLED=1")
    monkeypatch.setattr(anthropic, "Anthropic", construct)


def test_shared_clients_refuse(real_looking_key):
    from justdata.shared.analysis import ai_provider
    with pytest.raises(AIDisabledError):
        ai_provider.ask_ai("prompt", api_key=SENTINEL)
    with pytest.raises(AIDisabledError):
        ai_provider.AIAnalyzer(api_key=SENTINEL)
    analyzer = object.__new__(ai_provider.AIAnalyzer)   # built before the switch was set
    analyzer.style_guide, analyzer.model, analyzer.api_key, analyzer.provider, analyzer.app_name = None, "m", SENTINEL, "claude", None
    with pytest.raises(AIDisabledError):
        analyzer._call_ai("prompt")
    with pytest.raises(AIDisabledError):
        analyzer.generate_text("prompt")


def test_every_app_analyzer_refuses(real_looking_key):
    from justdata.apps.lendsight.analysis import LendSightAnalyzer
    from justdata.apps.branchsight.analysis import BranchSightAnalyzer
    from justdata.apps.bizsight.ai_analysis import BizSightAnalyzer
    from justdata.apps.memberview.utils.claude_html_parser import ClaudeHTMLParser
    for make in (LendSightAnalyzer, BranchSightAnalyzer, BizSightAnalyzer, ClaudeHTMLParser):
        with pytest.raises(AIDisabledError):
            make()


def test_key_lookups_return_nothing(real_looking_key):
    from justdata.shared.utils.unified_env import get_unified_config
    assert env_utils.get_api_key("CLAUDE_API_KEY", "ANTHROPIC_API_KEY") is None
    assert get_unified_config(load_env=False).get("CLAUDE_API_KEY") is None


def test_env_file_load_leaves_no_ai_key(tmp_path, monkeypatch):
    """The path that caused the 88 rows: keys unset, then .env read back."""
    from justdata.shared.utils import unified_env
    env_file = tmp_path / ".env"
    env_file.write_text(f"CLAUDE_API_KEY={SENTINEL}\nANTHROPIC_API_KEY={SENTINEL}\nOTHER_SETTING=kept\n")
    for name in env_utils.AI_KEY_NAMES + ("OTHER_SETTING",):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(unified_env, "is_local_development", lambda: True)
    monkeypatch.setattr(unified_env, "find_shared_env_file", lambda: env_file)
    unified_env.load_shared_env()
    import os
    assert all(name not in os.environ for name in env_utils.AI_KEY_NAMES)
    assert os.environ.get("OTHER_SETTING") == "kept"
    monkeypatch.delenv("OTHER_SETTING", raising=False)


def test_usage_is_never_written(monkeypatch):
    from justdata.shared.analysis import ai_provider
    import google.cloud.bigquery as bq

    def client(*a, **k):
        raise AssertionError("ai_usage write attempted while JUSTDATA_AI_DISABLED=1")
    monkeypatch.setattr(bq, "Client", client)
    monkeypatch.setattr(ai_provider, "_ai_usage_buffer", [{"provider": "claude"}])
    ai_provider._flush_ai_usage_to_bigquery()


def _client_constructions():
    """(file, function node, call node) for every Anthropic(...) or OpenAI(...)
    call in the application code and scripts."""
    for base in ("justdata", "scripts"):
        for path in (ROOT / base).rglob("*.py"):
            tree = ast.parse(path.read_text(), filename=str(path))
            for fn in ast.walk(tree):
                if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for node in ast.walk(fn):
                    if isinstance(node, ast.Call):
                        name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
                        if name in ("Anthropic", "OpenAI"):
                            yield path, fn, node


def test_every_client_construction_checks_the_switch_first():
    """A new AI client anywhere in the code fails this test unless the
    function creating it checks the switch on an earlier line."""
    found = list(_client_constructions())
    assert found, "expected to find the existing AI clients"
    for path, fn, call in found:
        guards = [n.lineno for n in ast.walk(fn) if isinstance(n, ast.Call)
                  and (getattr(n.func, "id", None) or getattr(n.func, "attr", None))
                  in ("refuse_if_ai_disabled", "ai_disabled")]
        assert guards and min(guards) < call.lineno, f"{path.relative_to(ROOT)}:{call.lineno} ({fn.name})"


def test_local_timing_script_sets_the_switch():
    text = (ROOT / "scripts" / "time_analysis.py").read_text()
    assert 'os.environ["JUSTDATA_AI_DISABLED"] = "1"' in text
