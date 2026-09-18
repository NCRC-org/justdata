"""Cache keys must survive the years parameter arriving in either shape.

BranchSight passes the parsed list of ints from parse_web_parameters, while the
other apps pass the raw comma-separated string from the form. normalize_parameters
called .strip() on it unconditionally, so BranchSight raised AttributeError inside
store_cached_result. Its caller swallows exceptions and falls back to in-memory
storage, so the failure was silent: BranchSight wrote 2 cache rows ever, the last
in January 2026, while LendSight wrote 68 and BizSight 41.
"""

import pytest

from justdata.shared.utils.analysis_cache import generate_cache_key, normalize_parameters


BRANCHSIGHT_PARAMS = {
    'counties': ['Montgomery County, Maryland'],
    'selection_type': 'county',
    'state_code': '24',
    'metro_code': '',
}


def test_branchsight_accepts_a_list_of_years():
    """The exact shape BranchSight's blueprint builds."""
    key = generate_cache_key('branchsight', {**BRANCHSIGHT_PARAMS, 'years': [2020, 2021, 2022]})
    assert key.startswith('branchsight_')


def test_list_and_equivalent_string_agree():
    as_list = normalize_parameters('branchsight', {**BRANCHSIGHT_PARAMS, 'years': [2020, 2021]})
    as_string = normalize_parameters('branchsight', {**BRANCHSIGHT_PARAMS, 'years': '2020,2021'})
    assert as_list['years'] == as_string['years'] == '2020,2021'


def test_the_same_request_is_stable_across_calls():
    """A cache that changes key per call would never hit."""
    params = {**BRANCHSIGHT_PARAMS, 'years': [2020, 2021, 2022]}
    assert generate_cache_key('branchsight', params) == generate_cache_key('branchsight', params)


@pytest.mark.parametrize('app,params', [
    ('lendsight', {'counties': 'Montgomery County, Maryland', 'years': '2020,2021'}),
    ('branchmapper', {'counties': 'Montgomery County, Maryland', 'years': '2020,2021'}),
    ('bizsight', {'county_data': {'geoid5': '24031'}, 'years': '2020,2021'}),
])
def test_string_years_are_unchanged(app, params):
    """Existing cache entries for the other apps must keep their keys."""
    assert normalize_parameters(app, params)['years'] == '2020,2021'


@pytest.mark.parametrize('value,expected', [
    (None, ''),
    ('', ''),
    ('  2020,2021  ', '2020,2021'),
    ([2020], '2020'),
    ((2020, 2021), '2020,2021'),
    (2020, '2020'),
])
def test_year_shapes(value, expected):
    params = {**BRANCHSIGHT_PARAMS, 'years': value}
    assert normalize_parameters('branchsight', params)['years'] == expected
