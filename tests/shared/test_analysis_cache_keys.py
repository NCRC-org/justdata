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


def test_bizsight_key_carries_its_report_revision():
    """BizSight results cached before the classified-loan denominator are not reused."""
    from justdata.shared.utils import analysis_cache
    params = {'county_data': {'geoid5': '17031'}, 'years': '2020,2021,2022,2023,2024'}
    assert normalize_parameters('bizsight', params)['revision'] == 2
    current = generate_cache_key('bizsight', params)
    old = dict(analysis_cache.REPORT_REVISIONS)
    try:
        analysis_cache.REPORT_REVISIONS['bizsight'] = 1
        assert generate_cache_key('bizsight', params) != current
    finally:
        analysis_cache.REPORT_REVISIONS.clear()
        analysis_cache.REPORT_REVISIONS.update(old)


def test_lendsight_key_carries_its_report_revision():
    """LendSight results stored before the narrative fixes are not reused."""
    params = {'counties': 'Hillsborough County, Florida', 'years': '2021,2022,2023,2024,2025',
              'loan_purpose': ['purchase'], 'selection_type': 'county', 'state_code': '12'}
    assert normalize_parameters('lendsight', params)['revision'] == 3


MERGERMETER_FORM = {
    'acquirer_lei': '549300ZTT08EKQRVTR15', 'acquirer_rssd': '693224', 'acquirer_sb_id': '0000693224',
    'target_lei': 'DX0JX77PRMOELF7VG772', 'target_rssd': '395238', 'target_sb_id': '0000395238',
    'acquirer_assessment_areas': '[{"cbsa_name": "A", "counties": ["X County, Virginia"]}]',
    'target_assessment_areas': '[]', 'use_national_data': '0', 'loan_purpose': '', 'peer_group': 'volume_50_200',
    'hmda_start_year': '2023', 'hmda_end_year': '2025', 'sb_start_year': '2023', 'sb_end_year': '2024',
    'baseline_hmda_start_year': '2023', 'baseline_hmda_end_year': '2025',
    'baseline_sb_start_year': '2023', 'baseline_sb_end_year': '2024',
    'action_taken': '1', 'occupancy_type': '1', 'total_units': '1,2,3,4', 'construction_method': '1,2', 'not_reverse': '1',
}


def test_mergermeter_key_covers_every_setting_that_changes_the_workbook():
    base = generate_cache_key('mergermeter', MERGERMETER_FORM)
    assert generate_cache_key('mergermeter', dict(MERGERMETER_FORM)) == base
    for field, value in (('hmda_start_year', '2021'), ('sb_end_year', '2023'), ('baseline_hmda_end_year', '2024'),
                         ('peer_group', 'all_banks'), ('use_national_data', '1'), ('loan_purpose', '1'),
                         ('target_sb_id', '0000000001')):
        assert generate_cache_key('mergermeter', dict(MERGERMETER_FORM, **{field: value})) != base, field
