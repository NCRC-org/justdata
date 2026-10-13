"""Per-section narrative log (Workflow 13277127143): every AI call records its
section, duration, stop reason, token counts and failure reason, keyed to the
job, in stdout and in the run's perf list (kept by the cache, returned by
/report-data)."""

from types import SimpleNamespace

import pytest

from justdata.shared.analysis.ai_provider import AIAnalyzer
from justdata.shared.utils.perf import perf_stages, start_perf
from justdata.shared.utils.query_context import set_query_context


class Analyzer(AIAnalyzer):
    def generate_market_concentration_discussion(self):
        return self.generate_text("prompt", max_tokens=900)


def _reply(stop_reason, text="Narrative.", output_tokens=120):
    return SimpleNamespace(stop_reason=stop_reason,
                           content=[SimpleNamespace(type="text", text=text)],
                           usage=SimpleNamespace(input_tokens=2000, output_tokens=output_tokens))


@pytest.fixture
def run(mocked_ai_client, monkeypatch):
    start_perf("lendsight")
    set_query_context(app="lendsight", job_id="job-123")
    yield mocked_ai_client
    set_query_context()


def test_successful_call_is_logged_with_its_section(run, capsys):
    run.return_value.messages.create.return_value = _reply("end_turn")
    assert Analyzer().generate_market_concentration_discussion() == "Narrative."
    entry = [s for s in perf_stages() if s["stage"].startswith("ai:")][-1]
    assert entry["stage"] == "ai:market_concentration_discussion"
    assert entry["job"] == "job-123" and entry["app"] == "lendsight"
    assert entry["stop_reason"] == "end_turn" and entry["ok"] is True and entry["failure"] is None
    assert (entry["input_tokens"], entry["output_tokens"], entry["max_tokens"]) == (2000, 120, 900)
    assert isinstance(entry["ms"], int)
    assert '[narrative] {"stage": "ai:market_concentration_discussion"' in capsys.readouterr().out


def test_cut_off_reply_is_logged_as_max_tokens(run):
    run.return_value.messages.create.return_value = _reply("max_tokens", output_tokens=900)
    with pytest.raises(Exception):
        Analyzer().generate_market_concentration_discussion()
    entry = perf_stages()[-1]
    assert entry["ok"] is False and entry["failure"] == "max_tokens" and entry["output_tokens"] == 900


def test_rate_limit_is_named_not_quoted(run):
    class RateLimitError(Exception):
        pass
    run.return_value.messages.create.side_effect = RateLimitError("429 secret org id")
    with pytest.raises(Exception):
        Analyzer().generate_market_concentration_discussion()
    entry = perf_stages()[-1]
    assert entry["failure"] == "rate_limit"
    assert "secret" not in str(entry)
