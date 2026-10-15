"""The SOD year setting matches the tables (opt-in: make test-network).

branchsight.sod holds the latest SOD year only and sod_legacy every earlier
year. SOD_LATEST_YEAR must be MAX(year) in sod, or the apps ask for a year that
is not there. Run after a promotion and before the config change is merged.
"""
import pytest

from justdata.shared.core.sod_years import SOD_EARLIEST_YEAR, SOD_LATEST_YEAR, sod_all_years

pytestmark = pytest.mark.network


@pytest.fixture(scope='module')
def client():
    from justdata.shared.utils.bigquery_client import get_bigquery_client
    return get_bigquery_client('justdata-ncrc', app_name='TESTS')


def _years(client, sql):
    return sorted(int(r.year) for r in client.query(sql).result())


def test_sod_holds_the_latest_year_only(client):
    years = _years(client, 'SELECT DISTINCT year FROM `justdata-ncrc.branchsight.sod`')
    assert years == [SOD_LATEST_YEAR]


def test_every_sod_year_is_readable(client):
    years = _years(client, f'SELECT DISTINCT year FROM {sod_all_years("justdata-ncrc")}')
    assert years == list(range(SOD_EARLIEST_YEAR, SOD_LATEST_YEAR + 1))
