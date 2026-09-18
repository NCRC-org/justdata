"""The external-testing deployment must not share cache tables with production.

JUSTDATA_ENV is set per Cloud Run service by the deploy pipeline; these tests
pin the dataset each value selects.
"""

import importlib

import pytest


def _reload_with_env(monkeypatch, value):
    """Re-import analysis_cache so its module-level DATASET_ID is recomputed."""
    if value is None:
        monkeypatch.delenv("JUSTDATA_ENV", raising=False)
    else:
        monkeypatch.setenv("JUSTDATA_ENV", value)

    from justdata.shared.utils import analysis_cache

    return importlib.reload(analysis_cache)


@pytest.fixture(autouse=True)
def _restore_module():
    """Leave the module as the rest of the suite expects to find it."""
    yield
    from justdata.shared.utils import analysis_cache

    importlib.reload(analysis_cache)


def test_testing_env_uses_isolated_dataset(monkeypatch):
    cache = _reload_with_env(monkeypatch, "testing")
    assert cache.DATASET_ID == "cache_testing"
    for table in (cache.CACHE_TABLE, cache.USAGE_TABLE,
                  cache.RESULTS_TABLE, cache.SECTIONS_TABLE):
        assert ".cache_testing." in table


@pytest.mark.parametrize("env", [None, "staging", "production"])
def test_every_other_env_uses_the_live_dataset(monkeypatch, env):
    cache = _reload_with_env(monkeypatch, env)
    assert cache.DATASET_ID == "cache"
    assert cache.USAGE_TABLE.endswith(".cache.usage_log")


def test_testing_and_live_tables_never_collide(monkeypatch):
    testing = _reload_with_env(monkeypatch, "testing").CACHE_TABLE
    live = _reload_with_env(monkeypatch, "production").CACHE_TABLE
    assert testing != live
