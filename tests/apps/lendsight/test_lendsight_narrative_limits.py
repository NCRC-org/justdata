"""LendSight narrative token ceilings leave room for the length each prompt
asks for (Hillsborough on testing, 2026-10-13: key findings stopped at 400 of
400 and failed; Section 2 and table narratives reached 91% to 97%)."""

import ast
import inspect

from justdata.apps.lendsight.analysis import LendSightAnalyzer

MINIMUMS = {
    "generate_key_findings": 800,
    "generate_income_borrowers_discussion": 500,
    "generate_income_tracts_discussion": 500,
    "generate_minority_tracts_discussion": 500,
    "generate_table_narrative": 900,
}


def test_ceilings():
    for name, minimum in MINIMUMS.items():
        tree = ast.parse(inspect.getsource(getattr(LendSightAnalyzer, name)).strip())
        limits = [kw.value.value for node in ast.walk(tree) if isinstance(node, ast.Call)
                  for kw in node.keywords if kw.arg == "max_tokens"]
        assert limits and min(limits) >= minimum, (name, limits)


def test_combined_reply_with_literal_newlines_parses():
    analyzer = object.__new__(LendSightAnalyzer)
    reply = ('{"demographic_overview_discussion": "First paragraph.\n\nSecond.",'
             ' "income_neighborhood_discussion": "A.\n\nB.",'
             ' "top_lenders_detailed_discussion": "C.\n\nD.",'
             ' "market_concentration_discussion": "E.\n\nF."}')
    analyzer._call_ai = lambda prompt, **k: reply
    out = analyzer.generate_all_table_discussions({"counties": ["Hillsborough County, Florida"], "years": [2025]})
    assert out["market_concentration_discussion"] == "E.\n\nF."
    assert out["demographic_overview_discussion"].startswith("First paragraph.")
