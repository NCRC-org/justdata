"""LendSight fills every section the combined call leaves empty, Section 4
included, each with its own call (Workflow 13277127143)."""

import inspect


def test_each_empty_section_has_its_own_call():
    import justdata.apps.lendsight.core as core
    src = inspect.getsource(core.run_analysis)
    for key, method in (("demographic_overview_discussion", "generate_demographic_overview_discussion"),
                        ("income_neighborhood_discussion", "generate_income_neighborhood_discussion"),
                        ("top_lenders_detailed_discussion", "generate_top_lenders_detailed_discussion"),
                        ("market_concentration_discussion", "generate_market_concentration_discussion")):
        assert f"'{key}': analyzer.{method}" in src, key
    assert "market_concentration_discussion not available in fallback mode" not in src


def test_market_concentration_has_a_single_section_prompt():
    from justdata.apps.lendsight.analysis import LendSightAnalyzer
    analyzer = object.__new__(LendSightAnalyzer)
    sent = {}
    analyzer._call_ai = lambda prompt, **k: sent.setdefault("prompt", prompt) and "Text."
    data = {"counties": ["Cook County, Illinois"], "years": [2021, 2025],
            "market_concentration": [{"year": 2025, "loan_purpose": "All Loans", "hhi": 812}]}
    assert analyzer.generate_market_concentration_discussion(data) == "Text."
    assert "Herfindahl-Hirschman" in sent["prompt"] and '"hhi": 812' in sent["prompt"]
    # The combined call uses the same block
    combined = {}
    analyzer._call_ai = lambda prompt, **k: combined.setdefault("prompt", prompt) and "{}"
    analyzer.generate_all_table_discussions(data)
    assert analyzer._market_concentration_block(data["market_concentration"]).strip() in combined["prompt"]
