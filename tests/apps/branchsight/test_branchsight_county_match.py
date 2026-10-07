"""BranchSight resolves the picked county exactly (substring matches were wrong
for 35 counties, e.g. Johnson County, Kansas ran as Johnson County, Arkansas)."""

from unittest import mock

from justdata.apps.branchsight import data_utils

COUNTIES = ["Johnson County, Arkansas", "Johnson County, Kansas",
            "Deaf Smith County, Texas", "Smith County, Texas"]


class FakeClient:
    """Answers the equality query from COUNTIES; the substring query too."""
    def __init__(self):
        self.queries = []

    def query(self, sql, job_config=None):
        self.queries.append(sql)
        if "@county" in sql:
            want = job_config.query_parameters[0].value.lower()
            rows = [c for c in COUNTIES if c.lower() == want]
        else:
            rows = [c for c in COUNTIES if "johnson county" in c.lower() and "kansas" in c.lower()]
        result = mock.Mock()
        result.result.return_value = [mock.Mock(county_state=c) for c in sorted(rows)]
        return result


def _match(county):
    client = FakeClient()
    with mock.patch.object(data_utils, "get_bigquery_client", return_value=client):
        return data_utils.find_exact_county_match(county), client


def test_kansas_is_not_arkansas():
    found, client = _match("Johnson County, Kansas")
    assert found == ["Johnson County, Kansas"]
    assert len(client.queries) == 1 and "LIKE" not in client.queries[0]


def test_smith_is_not_deaf_smith():
    assert _match("Smith County, Texas")[0] == ["Smith County, Texas"]


def test_county_name_is_a_query_parameter_not_sql_text():
    _, client = _match("O'Brien County, Iowa")
    assert "O'Brien" not in client.queries[0]


def test_ambiguous_free_text_is_not_a_match():
    # No exact row: the fallback substring search finds two, so no match.
    assert _match("Johnson County, Kans")[0] == []
