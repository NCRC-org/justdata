"""Stage timings survive the analysis cache for every app (spec 04 A5).

BizSight stores its metadata as a section; LendSight and BranchSight do not,
so perf and perf_ref ride in result_summary and come back in metadata."""

import json
from types import SimpleNamespace

import pytest

from justdata.shared.utils import analysis_cache as ac

STAGES = [{"stage": "bq:branch_report", "ms": 640}]


class FakeClient:
    def __init__(self):
        self.summary = None

    def query(self, sql, job_config=None):
        for p in getattr(job_config, "query_parameters", None) or []:
            if p.name == "result_summary":
                self.summary = p.value
        if "SELECT" in sql and "result_summary" in sql and self.summary:
            rows = [SimpleNamespace(result_summary=self.summary, section_name=None, section_type=None,
                                    section_category=None, section_data=None, section_metadata=None,
                                    display_order=None)]
        else:
            rows = []
        return SimpleNamespace(result=lambda *a, **k: rows)


@pytest.mark.parametrize("app", ["lendsight", "branchsight"])
def test_perf_round_trips_through_the_cache(monkeypatch, app):
    client = FakeClient()
    monkeypatch.setattr(ac, "get_bigquery_client", lambda *a, **k: client)
    result = {"success": True, "report_data": {}, "ai_insights": {},
              "metadata": {"perf": STAGES, "perf_ref": "beef1234"}}
    ac.store_cached_result(app, {"counties": ["Lowndes County, Alabama"]}, "job-1", result,
                           metadata={"counties": ["Lowndes County, Alabama"], "years": [2025]})
    assert json.loads(client.summary)["perf"] == STAGES
    back = ac.get_analysis_result_by_job_id("job-1")
    assert back["metadata"]["perf"] == STAGES and back["metadata"]["perf_ref"] == "beef1234"
