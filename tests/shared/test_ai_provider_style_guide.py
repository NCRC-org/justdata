"""BizSight's narrative prompts must keep their NCRC style guide.

BizSight used to own a private copy of AIAnalyzer/AIProvider whose
generate_text() prepended the style guide. Consolidating onto the shared
analyzer would silently drop that from every BizSight narrative unless the
style guide moved with it, so these tests pin the behaviour on both sides.
"""

from unittest.mock import patch

from justdata.shared.analysis.ai_provider import AIAnalyzer, NCRC_STYLE_GUIDE


def _analyzer(**kwargs):
    return AIAnalyzer(api_key="test-key", **kwargs)


def test_style_guide_is_prepended_when_configured():
    analyzer = _analyzer(style_guide=NCRC_STYLE_GUIDE)
    with patch.object(AIAnalyzer, "_call_ai", return_value="narrative") as call:
        analyzer.generate_text("Describe lending patterns.", max_tokens=300)

    sent = call.call_args.args[0]
    assert sent.startswith(NCRC_STYLE_GUIDE)
    assert sent.endswith("Describe lending patterns.")


def test_prompt_is_untouched_without_a_style_guide():
    """LendSight, BranchSight and MergerMeter must be unaffected by this change."""
    analyzer = _analyzer()
    with patch.object(AIAnalyzer, "_call_ai", return_value="narrative") as call:
        analyzer.generate_text("Describe lending patterns.")

    assert call.call_args.args[0] == "Describe lending patterns."


def test_generate_text_forwards_token_budget_and_app_name():
    analyzer = _analyzer(style_guide=NCRC_STYLE_GUIDE, app_name="bizsight")
    with patch.object(AIAnalyzer, "_call_ai", return_value="narrative") as call:
        analyzer.generate_text("prompt", max_tokens=600, temperature=0.3)

    assert call.call_args.kwargs["max_tokens"] == 600
    # app_name drives per-app AI cost attribution in log_ai_usage
    assert call.call_args.kwargs["app_name"] == "bizsight"


def test_bizsight_analyzer_keeps_the_style_guide(monkeypatch):
    monkeypatch.setenv("CLAUDE_API_KEY", "test-key")
    from justdata.apps.bizsight.ai_analysis import BizSightAnalyzer

    analyzer = BizSightAnalyzer()
    assert analyzer.ai.style_guide == NCRC_STYLE_GUIDE
    assert analyzer.ai.app_name == "bizsight"
