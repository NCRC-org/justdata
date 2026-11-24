"""Organization type and state from the user's HubSpot company (spec 15).

Both are read from the company record at sign-in and stored on the Firestore
user record; analytics reads them from there. The state is never taken from
an IP address.

ORG_TYPE_BY_COMPANY_TYPE is the one place the HubSpot ``company_type``
options map to JustData's eight categories (Jad, 2026-11-20). Its keys are
the HubSpot option names exactly. A company with no type, or a type not in
the map, gets no category here; an admin sets it on /admin/users.
"""
import re
from typing import Optional

BANK = 'Bank or credit union'
CDFI = 'CDFI or loan fund'
COMMUNITY = 'Community organization'
GOVERNMENT = 'Government'
RESEARCH = 'Research or academic'
PHILANTHROPY = 'Philanthropy'
MEDIA = 'Media'
OTHER = 'Other'
ORG_TYPES = (BANK, CDFI, COMMUNITY, GOVERNMENT, RESEARCH, PHILANTHROPY, MEDIA, OTHER)

ORG_TYPE_BY_COMPANY_TYPE = {
    'Bank': BANK,
    'Credit Union': BANK,
    'CDFI/Loan Fund': CDFI,
    'Advocacy-Local or Statewide': COMMUNITY,
    'Advocacy-National': COMMUNITY,
    'Advocacy/Organizing': COMMUNITY,
    'Organizing': COMMUNITY,
    'CDC': COMMUNITY,
    'Community Action Agency': COMMUNITY,
    'Community Housing Development Organization (CHDO)': COMMUNITY,
    'Community Land Trust': COMMUNITY,
    'Fair Housing Center': COMMUNITY,
    'Fair Lending': COMMUNITY,
    'Faith-based': COMMUNITY,
    'Housing Counseling Agency': COMMUNITY,
    'Legal Services Provider': COMMUNITY,
    'Small Business Development': COMMUNITY,
    'Social Services Provider': COMMUNITY,
    'Tenant Organizations': COMMUNITY,
    'Workforce Development': COMMUNITY,
    'Housing Development': COMMUNITY,   # Jad, 2026-11-24
    'Government': GOVERNMENT,
    'Government-Local': GOVERNMENT,
    'Government-State': GOVERNMENT,
    'Government-National': GOVERNMENT,
    'Housing Authority': GOVERNMENT,
    'State Housing Finance Agency': GOVERNMENT,
    'Special Service District': GOVERNMENT,
    'Research': RESEARCH,
    'Educational Institution': RESEARCH,
    'Foundation': PHILANTHROPY,
    'Foundation-Local': PHILANTHROPY,
    'Foundation-State': PHILANTHROPY,
    'Foundation-National': PHILANTHROPY,
    'Media': MEDIA,
    'Other': OTHER,
    'Corporation': OTHER,
    'Consultant': OTHER,
    'Technology': OTHER,
    'Hospital/Health System': OTHER,
    'Arts/Cultural': OTHER,
    'Union': OTHER,
    'Systems Change and Financial Reform': OTHER,
    'Urban Planning': OTHER,
}


def org_type_for(company_type: Optional[str]) -> Optional[str]:
    """The category for a HubSpot company_type option, or None."""
    if not company_type:
        return None
    return ORG_TYPE_BY_COMPANY_TYPE.get(company_type.strip())


# ---- State --------------------------------------------------------------------

UNKNOWN_STATE = 'unknown'

# USPS codes: the 50 states, DC and the territories.
STATE_NAMES = {
    'AL': 'alabama', 'AK': 'alaska', 'AZ': 'arizona', 'AR': 'arkansas', 'CA': 'california',
    'CO': 'colorado', 'CT': 'connecticut', 'DE': 'delaware', 'DC': 'district of columbia',
    'FL': 'florida', 'GA': 'georgia', 'HI': 'hawaii', 'ID': 'idaho', 'IL': 'illinois',
    'IN': 'indiana', 'IA': 'iowa', 'KS': 'kansas', 'KY': 'kentucky', 'LA': 'louisiana',
    'ME': 'maine', 'MD': 'maryland', 'MA': 'massachusetts', 'MI': 'michigan', 'MN': 'minnesota',
    'MS': 'mississippi', 'MO': 'missouri', 'MT': 'montana', 'NE': 'nebraska', 'NV': 'nevada',
    'NH': 'new hampshire', 'NJ': 'new jersey', 'NM': 'new mexico', 'NY': 'new york',
    'NC': 'north carolina', 'ND': 'north dakota', 'OH': 'ohio', 'OK': 'oklahoma', 'OR': 'oregon',
    'PA': 'pennsylvania', 'RI': 'rhode island', 'SC': 'south carolina', 'SD': 'south dakota',
    'TN': 'tennessee', 'TX': 'texas', 'UT': 'utah', 'VT': 'vermont', 'VA': 'virginia',
    'WA': 'washington', 'WV': 'west virginia', 'WI': 'wisconsin', 'WY': 'wyoming',
    'PR': 'puerto rico', 'VI': 'virgin islands', 'GU': 'guam', 'AS': 'american samoa',
    'MP': 'northern mariana islands',
}
_BY_TEXT = {name: code for code, name in STATE_NAMES.items()}
_BY_TEXT.update({code.lower(): code for code in STATE_NAMES})
_BY_TEXT.update({
    'washington dc': 'DC', 'washington d c': 'DC', 'd c': 'DC',
    'us virgin islands': 'VI', 'u s virgin islands': 'VI',
})


def state_code(text: Optional[str]) -> str:
    """A USPS code from the HubSpot company ``state`` text, or "unknown".

    The field is free text (247 spellings, 2026-11-20): codes and full names
    in any case, with stray periods and spaces. Anything else, including
    places outside the US, is "unknown". A territory is never inferred from a
    city name ("san juan", "loiza", "st. thomas" stay unknown; Jad, 2026-11-24).
    """
    if not text:
        return UNKNOWN_STATE
    key = re.sub(r'\s+', ' ', re.sub(r'[.,]', ' ', text.lower())).strip()
    return _BY_TEXT.get(key, UNKNOWN_STATE)
