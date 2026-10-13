"""Narrative prompts describe what each app analyses (Workflow 13277084655).

LendSight and the MergerMeter loans method count originated loans only
(action_taken = '1'), so prompts and labels must not call them approvals,
applications or denials."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_lendsight_prompts_say_originations():
    text = (ROOT / "justdata/apps/lendsight/analysis.py").read_text()
    for wrong in ("mortgage approvals", "MORTGAGE APPROVALS", "approval gap", "population-to-approval",
                  "higher denial rates"):
        assert wrong not in text, wrong
    assert "originated mortgage loans" in text


def test_mergermeter_loans_method_says_originations():
    for rel in ("justdata/apps/mergermeter/mergermeter_ops.py",
                "justdata/apps/mergermeter/branch_assessment_area_generator.py",
                "justdata/apps/mergermeter/templates/partials/mergermeter_controls.html"):
        assert "loan applications" not in (ROOT / rel).read_text(), rel
