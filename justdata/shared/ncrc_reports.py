"""NCRC report links used in narratives, prompts and report templates.

The one place these URLs live (Workflow 13277128272). When NCRC publishes a new
edition of a report, update its entry here: URL, title and last_checked.
tests/shared/test_ncrc_reports.py requests every URL and fails on anything but
a direct 200, so a moved or dead link fails CI.
"""

from typing import NamedTuple


class NcrcReport(NamedTuple):
    key: str
    title: str
    url: str
    last_checked: str  # YYYY-MM-DD the URL last returned 200


NCRC_REPORTS = (
    NcrcReport("racial_wealth_gap", "The Racial Wealth Gap 1992 to 2022",
               "https://ncrc.org/the-racial-wealth-gap-1992-to-2022/", "2026-10-13"),
    NcrcReport("mortgage_market_series", "Mortgage Market Report Series",
               "https://ncrc.org/mortgage-market-report-series/", "2026-10-13"),
    NcrcReport("mortgage_market_part_1", "Part 1: Introduction to Mortgage Market Trends",
               "https://ncrc.org/mortgage-market-report-series-part-1-introduction-to-mortgage-market-trends/",
               "2026-10-13"),
    NcrcReport("mortgage_market_part_2", "Part 2: Lending Trends by Borrower and Neighborhood Characteristics",
               "https://ncrc.org/mortgage-market-report-series-part-2-lending-trends-by-borrower-and-neighborhood-characteristics/",
               "2026-10-13"),
    NcrcReport("mortgage_market_part_3", "Part 3: Native American and Hawaiian Lending",
               "https://ncrc.org/mortgage-market-report-series-part-3-native-american-and-hawaiian-lending/",
               "2026-10-13"),
    NcrcReport("mortgage_market_part_4", "Part 4: Mortgage Lending Across American Cities",
               "https://ncrc.org/mortgage-market-report-series-part-4-mortgage-lending-across-american-cities/",
               "2026-10-13"),
    NcrcReport("mortgage_market_part_5", "Part 5: Top 50 Home Purchase Lenders Analysis for 2024",
               "https://ncrc.org/mortgage-market-report-series-part-5-top-50-home-purchase-lenders-analysis-for-2024/",
               "2026-10-13"),
    NcrcReport("cra", "Community Reinvestment Act", "https://ncrc.org/cra/", "2026-10-13"),
)

_BY_KEY = {r.key: r for r in NCRC_REPORTS}


def ncrc_report(key: str) -> NcrcReport:
    """The entry for key; a KeyError names a link that is not in the list."""
    return _BY_KEY[key]


def ncrc_report_url(key: str) -> str:
    return _BY_KEY[key].url
