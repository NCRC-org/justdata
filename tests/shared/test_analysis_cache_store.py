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


def _section_statements(client):
    return [params for sql, params in client.calls
            if "analysis_result_sections" in sql and "INSERT" in sql]


def _stored_sections(client):
    """Every stored section's STRUCT values, in the order written."""
    return [dict(struct.struct_values)
            for params in _section_statements(client)
            for struct in params["sections"].values]


def _section_json(client):
    """(section_data, section_metadata) JSON text for every stored section."""
    return [(s["section_data"], s["section_metadata"]) for s in _stored_sections(client)]


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


def _sections(n):
    return [{"section_name": f"s{i}", "section_type": "ai_narrative", "section_category": "ai_insights",
             "section_data": {"text": "x" * 100}, "section_metadata": {}, "display_order": i + 1}
            for i in range(n)]


def test_all_sections_go_in_one_statement_before_the_result_and_cache_rows(monkeypatch):
    """One DML statement per section made the cache write 10 to 82 s per run."""
    client = RecordingClient()
    monkeypatch.setattr(ac, "get_bigquery_client", lambda *a, **k: client)
    monkeypatch.setattr(ac, "extract_sections", lambda app, result: _sections(24))
    ac.store_cached_result("lendsight", {"counties": ["Cook County, Illinois"]}, "job-1", {}, metadata={})
    inserts = [sql for sql, _ in client.calls if "INSERT" in sql]
    assert len(inserts) == 3
    assert "analysis_result_sections" in inserts[0]
    assert "analysis_results`" in inserts[1] and "analysis_cache`" in inserts[2]
    stored = _stored_sections(client)
    assert [s["section_name"] for s in stored] == [f"s{i}" for i in range(24)]
    assert [s["display_order"] for s in stored] == list(range(1, 25))
    assert len({s["section_id"] for s in stored}) == 24


def test_large_runs_are_split_by_size_and_keep_their_order(monkeypatch):
    client = RecordingClient()
    monkeypatch.setattr(ac, "get_bigquery_client", lambda *a, **k: client)
    monkeypatch.setattr(ac, "extract_sections", lambda app, result: _sections(10))
    monkeypatch.setattr(ac, "_SECTION_BATCH_CHARS", 350)  # three ~115-char sections per batch
    ac.store_cached_result("lendsight", {"counties": ["Cook County, Illinois"]}, "job-1", {}, metadata={})
    assert [len(p["sections"].values) for p in _section_statements(client)] == [3, 3, 3, 1]
    assert [s["section_name"] for s in _stored_sections(client)] == [f"s{i}" for i in range(10)]


def test_a_failed_section_write_stops_before_the_result_row(monkeypatch):
    """The result row marks the job complete; it must not be written over
    missing sections."""
    class Failing(RecordingClient):
        def query(self, sql, job_config=None):
            if "analysis_result_sections" in sql and "INSERT" in sql:
                raise RuntimeError("PARSE_JSON failed")
            return super().query(sql, job_config)
    client = Failing()
    monkeypatch.setattr(ac, "get_bigquery_client", lambda *a, **k: client)
    monkeypatch.setattr(ac, "extract_sections", lambda app, result: _sections(3))
    try:
        ac.store_cached_result("lendsight", {"counties": ["Cook County, Illinois"]}, "job-1", {}, metadata={})
    except RuntimeError:
        pass
    else:
        raise AssertionError("the failure was swallowed")
    assert not [sql for sql, _ in client.calls if "INSERT" in sql]
