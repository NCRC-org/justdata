"""Every report app sends its narrative prompts with the NCRC style guide.

The guide previously existed as three byte-identical copies (BizSight's private
provider, and _call_ai overrides in LendSightAnalyzer and BranchSightAnalyzer),
while MergerMeter had none. It now lives once in the shared module and is applied
in AIAnalyzer._call_ai, so these tests pin what actually reaches the API.
"""

from unittest.mock import MagicMock, patch

import pytest

from justdata.shared.analysis.ai_provider import AIAnalyzer, NCRC_STYLE_GUIDE


@pytest.fixture
def captured_prompt(monkeypatch):
    """Capture the prompt text handed to the Anthropic client."""
    monkeypatch.setenv("CLAUDE_API_KEY", "test-key")
    sent = {}

    def _fake_anthropic(api_key=None):
        client = MagicMock()

        def _create(model=None, max_tokens=None, messages=None):
            sent["prompt"] = messages[0]["content"]
            sent["model"] = model
            sent["max_tokens"] = max_tokens
            block = MagicMock()
            block.text = "narrative"
            response = MagicMock()
            response.content = [block]
            response.usage = None  # skip BigQuery usage logging
            return response

        client.messages.create.side_effect = _create
        return client

    with patch("anthropic.Anthropic", side_effect=_fake_anthropic):
        yield sent


def test_style_guide_applied_when_configured(captured_prompt):
    AIAnalyzer(style_guide=NCRC_STYLE_GUIDE)._call_ai("Describe lending patterns.")
    assert captured_prompt["prompt"] == NCRC_STYLE_GUIDE + "\n" + "Describe lending patterns."


def test_prompt_untouched_without_a_style_guide(captured_prompt):
    AIAnalyzer()._call_ai("Describe lending patterns.")
    assert captured_prompt["prompt"] == "Describe lending patterns."


def test_generate_text_does_not_double_apply(captured_prompt):
    """generate_text delegates to _call_ai; the guide must appear exactly once."""
    AIAnalyzer(style_guide=NCRC_STYLE_GUIDE).generate_text("prompt body")
    assert captured_prompt["prompt"].count("NCRC STYLE GUIDE") == 1


class TestEveryReportAppGetsTheGuide:
    """MergerMeter is the behaviour change here: it previously had no guide.

    LendSight and BranchSight must come out byte-identical to their old
    subclass overrides, which did style_guide + "\\n" + prompt.
    """

    def _analyzer(self, app):
        if app == "lendsight":
            from justdata.apps.lendsight.analysis import LendSightAnalyzer
            return LendSightAnalyzer()
        if app == "branchsight":
            from justdata.apps.branchsight.analysis import BranchSightAnalyzer
            return BranchSightAnalyzer()
        if app == "bizsight":
            from justdata.apps.bizsight.ai_analysis import BizSightAnalyzer
            return BizSightAnalyzer().ai
        return AIAnalyzer(ai_provider="claude", style_guide=NCRC_STYLE_GUIDE,
                          app_name="mergermeter")

    @pytest.mark.parametrize("app", ["lendsight", "branchsight", "bizsight", "mergermeter"])
    def test_prompt_carries_the_guide(self, app, captured_prompt):
        self._analyzer(app)._call_ai("Summarise the findings.")
        assert captured_prompt["prompt"] == NCRC_STYLE_GUIDE + "\n" + "Summarise the findings."

    @pytest.mark.parametrize("app", ["lendsight", "branchsight", "bizsight", "mergermeter"])
    def test_app_name_is_set_for_cost_attribution(self, app, captured_prompt):
        assert self._analyzer(app).app_name == app

    @pytest.mark.parametrize("app", ["lendsight", "branchsight"])
    def test_subclasses_no_longer_override_call_ai(self, app):
        """The duplicated overrides are gone; the base implementation is used."""
        analyzer = self._analyzer(app)
        assert type(analyzer)._call_ai is AIAnalyzer._call_ai
        assert not hasattr(type(analyzer), "_get_style_guide")


def test_style_guide_defined_exactly_once_in_the_repo():
    """Guards against a fourth copy drifting back in."""
    import subprocess

    hits = subprocess.run(
        ["grep", "-rln", "NCRC STYLE GUIDE", "--include=*.py", "justdata/"],
        capture_output=True, text=True,
    ).stdout.split()
    assert hits == ["justdata/shared/analysis/ai_provider.py"], hits
