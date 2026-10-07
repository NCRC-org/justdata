"""LendSight Methods text makes only claims the code backs (spec 04 decision 2)."""


def test_no_unbacked_outlier_claim():
    """Methods (web and PDF) claimed 1st/99th percentile loan-amount trimming
    that no code performs; the claim must not come back without the code."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[3] / "justdata" / "apps" / "lendsight"
    for path in list(root.rglob("*.html")) + list(root.rglob("*.py")):
        assert "99th percentile" not in path.read_text(errors="ignore"), path
