"""Writing an analysis to the cache (store_cached_result)."""

import json
from types import SimpleNamespace

import numpy as np
import pandas as pd

from justdata.shared.utils import analysis_cache as ac


class RecordingClient:
    """Keeps every statement and its parameters; returns no rows."""

    def __init__(self):
        self.calls = []

    def query(self, sql, job_config=None):
        params = {p.name: p for p in getattr(job_config, "query_parameters", None) or []}
        self.calls.append((sql, params))
        return SimpleNamespace(result=lambda *a, **k: [])


def _strict(text):
    """json.loads that refuses NaN and Infinity, as BigQuery's PARSE_JSON does."""
    def refuse(token):
        raise ValueError(f"non-JSON number {token}")
    return json.loads(text, parse_constant=refuse)


def _section_json(client):
    """(section_data, section_metadata) JSON text for every stored section."""
    out = []
    for sql, params in client.calls:
        if "analysis_result_sections" in sql and "INSERT" in sql:
            out.append((params["section_data"].value, params["section_metadata"].value))
    return out


def test_branchsight_raw_data_with_nan_is_stored_as_valid_json(monkeypatch):
    """The raw_data frame was the one BranchSight section not cleaned of NaN;
    BigQuery rejected it and BranchSight never reached the cache on testing."""
    client = RecordingClient()
    monkeypatch.setattr(ac, "get_bigquery_client", lambda *a, **k: client)
    raw = pd.DataFrame({"state": [np.nan, "AL"], "deposits": [1.5, float("inf")]})
    result = {"report_data": {"raw_data": raw, "summary": pd.DataFrame({"x": [np.nan]})},
              "ai_insights": {}}
    ac.store_cached_result("branchsight", {"counties": ["Lowndes County, Alabama"]}, "job-1", result,
                           metadata={"census_data": {"median": float("nan")}})
    stored = _section_json(client)
    assert stored, "no sections written"
    for data, metadata in stored:
        _strict(data)
        _strict(metadata)
    raw_rows = next(_strict(d) for d, _ in stored if '"deposits"' in d)
    assert raw_rows == [{"state": None, "deposits": 1.5}, {"state": "AL", "deposits": None}]
    summary = next(p["result_summary"].value for _, p in client.calls if "result_summary" in p)
    assert _strict(summary)["census_data"] == {"median": None}


def test_finite_values_are_not_rounded():
    assert ac._json_for_bigquery({"share": 0.123456789}) == '{"share": 0.123456789}'
