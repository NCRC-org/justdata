"""Facts shown on the public landing page ("/"): the hero's data inventory
and the figures strip.

Every value here was checked against the code and BigQuery on 2026-10-07
(spec 02 audit, L5 Projects/JustData Frontend Specs/02-landing-page). Do not
add a row or a figure that has not been verified the same way; if a value
cannot be confirmed, leave it out. HMDA years are read from
shared/core/hmda_years.py so they move with the platform's own setting.
"""

from justdata.shared.core.hmda_years import EARLIEST_HMDA_YEAR, LATEST_HMDA_YEAR

# FDIC Summary of Deposits as BranchSight queries it: branchsight.sod_legacy
# (2017 to 2024) plus branchsight.sod (2025). DataExplorer reads only the
# 2025 table; see Workflow ticket 13229492694.
SOD_FIRST_YEAR, SOD_LAST_YEAR = 2017, 2025

# CRA small business years BizSight's analysis actually runs (blueprint.py
# hardcodes 2020 to 2024; its config says 2019 to 2023). Ticket 13229487819.
CRA_SB_FIRST_YEAR, CRA_SB_LAST_YEAR = 2020, 2024


def _span(first, last):
    return f"{first} to {last}"


DATA_INVENTORY = (
    {"name": "HMDA mortgage records", "vintage": _span(EARLIEST_HMDA_YEAR, LATEST_HMDA_YEAR)},
    {"name": "FDIC Summary of Deposits", "vintage": _span(SOD_FIRST_YEAR, SOD_LAST_YEAR)},
    {"name": "CRA small business lending", "vintage": _span(CRA_SB_FIRST_YEAR, CRA_SB_LAST_YEAR)},
    # No year: the apps use different ACS vintages today. Ticket 13229522646.
    {"name": "Census ACS tract demographics", "vintage": "5-year estimates"},
)

PLATFORM_STATS = (
    {"figure": str(LATEST_HMDA_YEAR - EARLIEST_HMDA_YEAR + 1),
     "label": "years of mortgage records", "source": "HMDA"},
    {"figure": str(SOD_LAST_YEAR - SOD_FIRST_YEAR + 1),
     "label": "years of branch records", "source": "FDIC SOD"},
    # The state pickers (shared.cbsa_to_county) cover 50 states, DC and Puerto Rico.
    {"figure": "50", "label": "states, DC and Puerto Rico", "source": "Selectable geographies"},
    {"figure": "4", "label": "federal datasets", "source": "HMDA, FDIC SOD, CRA, Census"},
)

NUMBER_WORDS = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine")


def count_words(n):
    """NCRC style: spell out one to nine, figures for 10 and up."""
    return NUMBER_WORDS[n] if 0 <= n < 10 else str(n)
