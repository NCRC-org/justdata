"""BigQuery job labels and the query-cache switch (spec 04 A5 pending fixes)."""

import threading

from flask import Flask, g
from google.cloud.bigquery import QueryJobConfig

from justdata.backend import jobs
from justdata.shared.utils import query_context
from justdata.shared.utils.perf import perf_stages, request_id, start_perf, timed


class FakeClient:
    def __init__(self):
        self.calls = []

    def query(self, sql, job_config=None, *args, **kwargs):
        self.calls.append((sql, job_config))
        return "job"


def _run_in_worker(app_name, bypass, job_id, monkeypatch):
    """Run a query through run_in_background exactly as an app would."""
    monkeypatch.setenv("JUSTDATA_ENV", "testing")
    client = query_context.instrument_client(FakeClient())
    done = threading.Event()
    flask_app = Flask(__name__)
    with flask_app.test_request_context("/"):
        g.bq_app, g.bq_bypass_cache = app_name, bypass

        def work():
            client.query("SELECT 1")
            done.set()

        jobs.run_in_background(work, job_id=job_id)
    assert done.wait(5)
    return client.calls[0][1]


def test_worker_queries_carry_app_env_and_job_labels(monkeypatch):
    cfg = _run_in_worker("lendsight", False, "3F2b-ABC_def", monkeypatch)
    assert cfg.labels == {"env": "testing", "app": "lendsight", "job": "3f2b-abc_def"}
    assert cfg.use_query_cache is not False


def test_forced_refresh_turns_off_bigquery_result_cache(monkeypatch):
    cfg = _run_in_worker("bizsight", True, "job-1", monkeypatch)
    assert cfg.use_query_cache is False
    assert cfg.labels["refresh"] == "forced"


def test_query_outside_an_analysis_gets_only_env(monkeypatch):
    monkeypatch.setenv("JUSTDATA_ENV", "testing")
    client = query_context.instrument_client(FakeClient())
    done = threading.Event()

    def other_thread():
        client.query("SELECT 1")
        done.set()

    threading.Thread(target=other_thread).start()
    assert done.wait(5)
    assert client.calls[0][1].labels == {"env": "testing"}


def test_existing_labels_and_parameters_are_kept(monkeypatch):
    monkeypatch.setenv("JUSTDATA_ENV", "testing")
    client = query_context.instrument_client(FakeClient())
    cfg = QueryJobConfig(labels={"purpose": "lookup"})
    client.query("SELECT 1", job_config=cfg)
    assert client.calls[0][1].labels["purpose"] == "lookup"


def test_instrumenting_twice_wraps_once():
    client = FakeClient()
    assert query_context.instrument_client(query_context.instrument_client(client)) is client
    client.query("SELECT 1")
    assert len(client.calls) == 1


def test_shared_client_is_instrumented(monkeypatch):
    from justdata.shared.utils import bigquery_client
    monkeypatch.setattr(bigquery_client, "_build_bigquery_client", lambda *a, **k: FakeClient())
    assert getattr(bigquery_client.get_bigquery_client("p", app_name="x"), "_justdata_instrumented", False)


def test_perf_timed_records_stages_per_run():
    ref = start_perf("lendsight")
    with timed("bq:summary"):
        pass
    with timed("narrative"):
        pass
    assert [s["stage"] for s in perf_stages()] == ["bq:summary", "narrative"]
    assert request_id() == ref
    start_perf("lendsight")
    assert perf_stages() == []
