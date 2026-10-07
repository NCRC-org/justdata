"""Copy for the /apps launcher (spec 03): card descriptions, "Analysis years"
labels and the header line per access level.

Descriptions were checked against each app's README and code and approved by
Jad on 2026-10-07 (spec 03 audit). Do not add a claim an app cannot back up;
a card that overstates what an app does is a false positive.

Analysis years are what each app runs today, not what the platform holds
(that is the landing page's "What's inside"). Omit an app rather than guess.
"""

from justdata.shared.core.hmda_years import EARLIEST_HMDA_YEAR, LATEST_HMDA_YEAR

APP_DESCRIPTIONS = {
    "lendsight": (
        "County- and tract-level reports on originated home loans by borrower "
        "income, race and ethnicity, and neighborhood income and minority share. "
        "Includes top lenders, market concentration and PDF and Excel exports."
    ),
    "bizsight": (
        "County-level small business lending under the Community Reinvestment Act, "
        "by lender and by tract income. Shows how much credit reaches low- and "
        "moderate-income areas, with PDF, Excel and PowerPoint exports."
    ),
    "branchsight": (
        "Branch counts by bank and county over time, with each network's presence "
        "in low- and moderate-income and majority-minority tracts. Includes "
        "deposit-based market concentration and PDF and Excel exports."
    ),
    "branchmapper": (
        "Interactive map of a bank's branches over census tract income and "
        "demographics, with branch changes from FDIC history."
    ),
    "mergermeter": (
        "Compares an acquiring and a target bank's mortgage lending, small business "
        "lending and branch networks across their assessment areas. Produces an "
        "Excel workbook for setting community benefit goals."
    ),
    "dataexplorer": (
        "Query the platform's datasets directly. Pick a dataset, filter by "
        "geography, lender and year, and export the result."
    ),
    "dotlender": "HMDA dot-density lending map with PDF canvas export.",
    "analytics": "Usage, performance and query volume across the platform.",
    "admin": "Manage users, access tiers and platform configuration.",
}

ANALYSIS_YEARS = {
    # Fixed in apps/lendsight/core.py although 2025 HMDA is loaded.
    # Workflow ticket 13229533844; update this label when it is fixed.
    "lendsight": "HMDA 2020 to 2024",
    # apps/bizsight/blueprint.py runs 2020 to 2024 (config says 2019 to 2023).
    # Workflow ticket 13229487819.
    "bizsight": "CRA 2020 to 2024",
    # Fixed in apps/branchsight/core.py.
    "branchsight": "FDIC SOD 2021 to 2025",
    # HMDA years are selectable (shared/core/hmda_years.py). Small business
    # years left off until verified.
    "mergermeter": f"HMDA {EARLIEST_HMDA_YEAR} to {LATEST_HMDA_YEAR}",
}

# Header line under "Apps", by the viewer's access level.
HEADER_LINES = {
    "staff": "You have staff access.",
    "tester": "Your account opens every tool below.",
    "free": ("You are signed in with free access. Tools marked Members open once "
             "your organization's membership is confirmed."),
}
