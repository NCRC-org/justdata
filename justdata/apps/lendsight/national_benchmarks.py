#!/usr/bin/env python3
"""
National benchmark data for mortgage lending trends.
Updated annually with new HMDA data.
"""

NATIONAL_BENCHMARKS = {
    '2024': {
        'home_purchase_lmib_pct': 25.8,
        'home_purchase_black_pct': 8.9,
        'home_purchase_hispanic_pct': 17.7,
        'home_purchase_asian_pct': 9.4,
        'home_purchase_white_pct': 13.0,
        'home_purchase_mmct_pct': 26.7,
        'home_purchase_lmict_pct': 21.3,
        'black_adult_population_pct': 11.7,
        'hispanic_adult_population_pct': 16.8,
        'asian_adult_population_pct': 7.0,
        # Lender type breakdowns
        'mortgage_co_mmct_pct': 29.2,
        'mortgage_co_hispanic_pct': 20.4,
        'bank_mmct_pct': 22.2,
        'bank_hispanic_pct': 12.7,
        'bank_lmib_pct': 15.6,
        'credit_union_lmib_pct': 14.7,
        'mortgage_co_lmib_pct': 14.0
    },
    '2023': {
        'home_purchase_lmib_pct': 26.4,
        'home_purchase_black_pct': 8.7,
        'home_purchase_hispanic_pct': 16.6,
        'home_purchase_asian_pct': 9.1,
        'home_purchase_white_pct': 12.8,
        'home_purchase_mmct_pct': 26.2,
        'home_purchase_lmict_pct': 21.0,
        'black_adult_population_pct': 11.7,
        'hispanic_adult_population_pct': 16.8,
        'asian_adult_population_pct': 7.0,
        # Lender type breakdowns
        'mortgage_co_mmct_pct': 28.9,
        'mortgage_co_hispanic_pct': 19.8,
        'bank_mmct_pct': 21.9,
        'bank_hispanic_pct': 12.4,
        'bank_lmib_pct': 15.8,
        'credit_union_lmib_pct': 14.9,
        'mortgage_co_lmib_pct': 14.2
    }
}

# URLs from the shared list (justdata/shared/ncrc_reports.py)
from justdata.shared.ncrc_reports import ncrc_report_url

NATIONAL_REPORT_LINKS = {
    'series_home': ncrc_report_url('mortgage_market_series'),
    'part_2_demographics': ncrc_report_url('mortgage_market_part_2'),
    'part_1_overview': ncrc_report_url('mortgage_market_part_1'),
}

def get_national_benchmarks(year: str) -> dict:
    """Get national benchmarks for a given year."""
    return NATIONAL_BENCHMARKS.get(str(year), {})

def get_national_report_link(key: str) -> str:
    """Get a national report hyperlink."""
    return NATIONAL_REPORT_LINKS.get(key, '')

