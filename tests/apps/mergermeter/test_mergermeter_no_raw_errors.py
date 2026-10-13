"""MergerMeter never shows exception text (#208, carried into spec 04)."""

from pathlib import Path

import pandas as pd

APP = Path(__file__).resolve().parents[3] / "justdata" / "apps" / "mergermeter"


def test_failed_statistic_shows_a_reference_not_the_exception(monkeypatch):
    from justdata.apps.mergermeter import statistical_analysis as sa

    def boom(*a, **k):
        raise RuntimeError("SECRET table justdata-ncrc.x not found")
    monkeypatch.setattr(pd.DataFrame, "groupby", boom)
    df = pd.DataFrame({"cbsa_code": ["a", "b"], "sb_loans_count": [1, 2], "lmict_count": [1, 1]})
    out = sa.analyze_sb_lending_distribution(df)
    assert "SECRET" not in out["summary"]
    assert out["summary"].startswith(sa.STAT_UNAVAILABLE) and "Reference:" in out["summary"]


def test_no_exception_text_in_user_facing_strings():
    for name in ("mergermeter_ops.py", "statistical_analysis.py", "blueprint.py"):
        text = (APP / name).read_text()
        assert "Error analyzing data: {str(e)}" not in text, name
        assert "Progress tracking error: {str(e)}" not in text, name
