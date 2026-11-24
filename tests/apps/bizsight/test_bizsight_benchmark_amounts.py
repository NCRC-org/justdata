"""BZ-005: the state and national "$100K-$250K" amount share was 0.0.

The benchmark JSON files carry it, but they are gitignored
(justdata/apps/bizsight/data/*.json), so the deployed services always take
the BigQuery path, and that path never selected amt_100k_250k or built
pct_amount_100k_250k. The three amount shares summed to about 83 percent.
"""
import inspect
import re
from pathlib import Path

from justdata.apps.bizsight import core
from justdata.apps.bizsight.generate_benchmarks import build_benchmark_dict
from justdata.apps.bizsight.utils.bigquery_client import BigQueryClient


def test_both_benchmark_queries_select_the_100k_250k_amount():
    for method in (BigQueryClient.get_state_benchmarks, BigQueryClient.get_national_benchmarks):
        assert "as amt_100k_250k" in inspect.getsource(method)


def test_the_bigquery_path_builds_the_share_for_state_and_national():
    source = Path(core.__file__).read_text()
    for who in ("state", "national"):
        assert f"{who}_amt_100k_250k = safe_float(row.get('amt_100k_250k'" in source
        assert re.search(rf"'pct_amount_100k_250k': \({who}_amt_100k_250k / {who}_amount \* 100\)", source)


def test_amount_shares_sum_to_100():
    row = {"total_loans": 100, "total_amount": 1000.0, "num_under_100k": 90, "num_100k_250k": 6,
           "num_250k_1m": 4, "amt_under_100k": 500.0, "amt_100k_250k": 150.0, "amt_250k_1m": 350.0}
    b = build_benchmark_dict(row)
    assert b["pct_amount_100k_250k"] == 15.0
    assert round(b["pct_amount_under_100k"] + b["pct_amount_100k_250k"] + b["pct_amount_250k_1m"], 6) == 100.0
