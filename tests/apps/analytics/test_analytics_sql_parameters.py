"""Analytics SQL takes every value as a query parameter, never as SQL text.

bq/queries/users.py built SQL by pasting the user id and the search box into
the query string, and the other query modules did the same with state, app,
lender id, entity id and type, and the user-type lists (2026-11-20, High).
Each input below gets a quote and a semicolon: it must reach BigQuery only as
a parameter, the query must be a SELECT, and the function returns no rows.
"""
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from justdata.apps.analytics.bq import client as bq_client
from justdata.apps.analytics.bq.queries import lenders, orgs, usage, users
from justdata.apps.analytics.bq import transforms

EVIL = "x'; DELETE FROM `justdata-ncrc.cache.usage_log` WHERE TRUE; --"
ROOT = Path(__file__).resolve().parents[3] / "justdata" / "apps" / "analytics"


class FakeJob:
    def result(self):
        return []


class FakeClient:
    def __init__(self):
        self.calls = []

    def query(self, sql, job_config=None):
        params = {}
        for p in (job_config.query_parameters if job_config else []):
            params[p.name] = list(p.values) if hasattr(p, "values") else p.value
        self.calls.append((sql, params))
        return FakeJob()


@pytest.fixture
def fake(monkeypatch):
    client = FakeClient()
    for module in (users, usage, lenders, orgs, transforms):
        monkeypatch.setattr(module, "get_bigquery_client", lambda: client)
    monkeypatch.setattr(users, "_enrich_users_from_firestore", lambda data: data)
    bq_client.clear_analytics_cache()
    return client


def _check(fake, *evil_params):
    assert fake.calls, "no query was run"
    for sql, params in fake.calls:
        assert EVIL not in sql and "DELETE" not in sql.upper().replace("DELETED", "")
        assert re.match(r"\s*(WITH|SELECT)\b", sql, re.I), sql[:80]
    seen = [v for _, params in fake.calls for v in params.values()]
    flat = [x for v in seen for x in (v if isinstance(v, list) else [v])]
    for name in evil_params:
        assert any(params.get(name) in (EVIL, [EVIL]) for _, params in fake.calls), name
    assert EVIL in flat


CASES = [
    ("get_users", lambda: users.get_users(days=30, search=EVIL), ["search"]),
    ("get_user_activity", lambda: users.get_user_activity(user_id=EVIL, days=30), ["user_id"]),
    ("get_entity_users county", lambda: users.get_entity_users("county", EVIL, days=30), ["entity_id"]),
    ("get_entity_users lender", lambda: users.get_entity_users("lender", EVIL, days=30), ["entity_id"]),
    ("get_user_locations", lambda: usage.get_user_locations(days=30, state=EVIL, user_types=[EVIL]),
     ["state", "user_types"]),
    ("get_user_locations exclude", lambda: usage.get_user_locations(days=30, exclude_user_types=[EVIL], state=EVIL),
     ["state", "user_types"]),
    ("get_research_activity", lambda: usage.get_research_activity(days=30, app=EVIL, state=EVIL, user_types=[EVIL]),
     ["app", "state", "user_types"]),
    ("get_lender_interest", lambda: lenders.get_lender_interest(days=30, user_types=[EVIL]), ["user_types"]),
    ("get_lender_detail", lambda: lenders.get_lender_detail(lender_id=EVIL, days=30), ["lender_id"]),
    ("get_coalition_opportunities", lambda: orgs.get_coalition_opportunities(days=30, entity_type=EVIL, state=EVIL),
     ["state", "entity_type"]),
]


@pytest.mark.parametrize("name,call,evil_params", CASES, ids=[c[0] for c in CASES])
def test_hostile_input_is_only_ever_a_parameter(fake, name, call, evil_params):
    result = call()
    _check(fake, *evil_params)
    # No rows come back: the fake returns none, and nothing is interpreted.
    if isinstance(result, list):
        assert result == []


def test_lender_name_lookups_bind_their_values(fake):
    transforms._lender_names_cache.clear()
    transforms._enrich_lender_names([{"lender_id": EVIL}])
    transforms._lookup_single_lender_name(EVIL + "2")
    transforms._enrich_with_county_names(fake, [{"county_fips": EVIL}])
    for sql, params in fake.calls:
        assert EVIL not in sql
    names = {k for _, params in fake.calls for k in params}
    assert {"leis", "lender_id", "fips"} <= names


def test_days_is_bound_as_an_integer(fake):
    users.get_users(days=45)
    sql, params = fake.calls[0]
    assert "INTERVAL @days DAY" in sql and params["days"] == 45


def test_parameter_scan_ignores_literals_and_requires_values():
    sql = "SELECT 1 FROM `p.d.t` WHERE e LIKE 'lendsight@%' AND s = @state -- @note\n"
    assert [p.name for p in bq_client.query_parameters(sql, {"state": "MD"})] == ["state"]
    with pytest.raises(KeyError):
        bq_client.query_parameters("SELECT @missing", {})


def test_no_value_is_pasted_into_analytics_sql():
    """Drift guard: every query goes through run_query, and no f-string or
    template puts a quoted placeholder into SQL."""
    for path in list(ROOT.rglob("*.py")) + list((ROOT / "sql_templates").glob("*.sql")):
        text = path.read_text()
        assert not re.search(r"'\{[A-Za-z_][A-Za-z0-9_\[\]]*\}'", text), path
        assert not re.search(r"IN \(\s*'\{", text), path
        if path.name != "client.py" and path.suffix == ".py":
            assert "client.query(" not in text.replace("source_client.query(", ""), path
