"""Organization type and state config (spec 15, Jad 2026-11-20).

HUBSPOT_COMPANY_TYPES is the company_type option list as HubSpot had it on
2026-11-20 (44 options). When HubSpot gains an option, add it here and to
ORG_TYPE_BY_COMPANY_TYPE; scripts/check_hubspot_company_types.py compares the
live list with the config.
"""
import pytest

from justdata.main.auth.services.organization import (
    ORG_TYPE_BY_COMPANY_TYPE, ORG_TYPES, OTHER, PHILANTHROPY, CDFI, UNKNOWN_STATE,
    org_type_for, state_code,
)

HUBSPOT_COMPANY_TYPES = [
    'Bank', 'Credit Union', 'Advocacy-Local or Statewide', 'Advocacy-National', 'Advocacy/Organizing',
    'Organizing', 'CDC', 'CDFI/Loan Fund', 'Community Action Agency',
    'Community Housing Development Organization (CHDO)', 'Community Land Trust', 'Fair Housing Center',
    'Fair Lending', 'Faith-based', 'Housing Counseling Agency', 'Legal Services Provider',
    'Small Business Development', 'Social Services Provider', 'Tenant Organizations', 'Workforce Development',
    'Government', 'Government-Local', 'Government-State', 'Government-National', 'Housing Authority',
    'State Housing Finance Agency', 'Special Service District', 'Research', 'Educational Institution',
    'Media', 'Other', 'Corporation', 'Consultant', 'Technology', 'Hospital/Health System', 'Foundation',
    'Foundation-Local', 'Foundation-State', 'Foundation-National', 'Housing Development', 'Arts/Cultural',
    'Union', 'Systems Change and Financial Reform', 'Urban Planning',
]


def test_every_hubspot_option_maps_to_a_category():
    assert len(HUBSPOT_COMPANY_TYPES) == 44
    assert set(ORG_TYPE_BY_COMPANY_TYPE) == set(HUBSPOT_COMPANY_TYPES)
    assert set(ORG_TYPE_BY_COMPANY_TYPE.values()) <= set(ORG_TYPES)
    assert len(ORG_TYPES) == 8 and set(ORG_TYPE_BY_COMPANY_TYPE.values()) == set(ORG_TYPES)


def test_jads_changes():
    assert org_type_for('CDFI/Loan Fund') == CDFI
    for option in ('Foundation', 'Foundation-Local', 'Foundation-State', 'Foundation-National'):
        assert org_type_for(option) == PHILANTHROPY
    assert org_type_for('Housing Development') == 'Community organization'


def test_no_or_unknown_type_is_left_to_the_admin():
    assert org_type_for(None) is None and org_type_for('') is None and org_type_for('Bakery') is None


# Spellings in HubSpot's company state field on 2026-11-20 (lowercased by HubSpot).
US_SPELLINGS = {
    'ca': 'CA', 'california': 'CA', 'dc': 'DC', 'dc ': 'DC', 'district of columbia': 'DC',
    'washington d.c.': 'DC', 'washington': 'WA', 'tx ': 'TX', 'pr': 'PR', 'vi': 'VI',
    'virgin islands': 'VI', 'new york': 'NY', 'NY': 'NY', 'West Virginia': 'WV', 'wy': 'WY',
}
NOT_A_STATE = ['ontario', 'on', 'sk', 'england', 'greater london', 'san juan', 'st. thomas', 'loiza',
               'victoria', 'tokyo', 'x', None, '']


@pytest.mark.parametrize('text,code', US_SPELLINGS.items())
def test_state_spellings(text, code):
    assert state_code(text) == code


@pytest.mark.parametrize('text', NOT_A_STATE)
def test_anything_else_is_unknown(text):
    assert state_code(text) == UNKNOWN_STATE
