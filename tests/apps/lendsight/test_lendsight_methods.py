"""LendSight Methods text makes only claims the code backs (spec 04 decision 2)."""


def test_no_unbacked_outlier_claim():
    """Methods (web and PDF) claimed 1st/99th percentile loan-amount trimming
    that no code performs; the claim must not come back without the code."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[3] / "justdata" / "apps" / "lendsight"
    for path in list(root.rglob("*.html")) + list(root.rglob("*.py")):
        assert "99th percentile" not in path.read_text(errors="ignore"), path


def test_unverified_multiracial_shares_are_held_out():
    """Held out of the page until verified against source and year (Jad,
    2026-10-07): not in Methods, and not in the narrative prompt, which would
    otherwise put them into the AI text on the page."""
    from pathlib import Path
    app = Path(__file__).resolve().parents[3] / "justdata" / "apps" / "lendsight"
    methods = (app / "templates" / "partials" / "lendsight_methods.html").read_text()
    for figure in ("38%", "22%", "17%", "86%"):
        assert figure not in methods, figure
    prompt = (app / "analysis.py").read_text()
    for figure in ("38.01%", "21.80%", "17.47%", "86% of all multi-racial"):
        assert figure not in prompt, figure
