"""MergerMeter's progress steps use neutral text (spec 04 A3)."""

from pathlib import Path

OPS = Path(__file__).resolve().parents[3] / "justdata" / "apps" / "mergermeter" / "mergermeter_ops.py"


def test_no_joke_progress_line():
    text = OPS.read_text()
    assert "Doing something cool" not in text
    assert "'step': 'Building charts and narrative'" in text
