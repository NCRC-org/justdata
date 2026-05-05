"""Coordinator that assembles the mortgage report from its section builders."""
from typing import Any, Dict, List

import pandas as pd

from justdata.apps.lendsight.report_builder.formatting import clean_mortgage_data
from justdata.apps.lendsight.report_builder.sections.concentration import (
    calculate_mortgage_hhi,
    create_market_concentration_table,
)
from justdata.apps.lendsight.report_builder.sections.demographics import (
    create_demographic_overview_table,
)
from justdata.apps.lendsight.report_builder.sections.income_borrowers import (
    create_income_borrowers_table,
)
from justdata.apps.lendsight.report_builder.sections.income_tracts import (
    create_income_tracts_table,
)
from justdata.apps.lendsight.report_builder.sections.minority_tracts import (
    create_minority_tracts_table,
)
from justdata.apps.lendsight.report_builder.sections.summaries import (
    create_lender_summary,
    create_mortgage_county_summary,
    create_mortgage_summary_table,
    create_mortgage_trend_analysis,
)
from justdata.apps.lendsight.report_builder.sections.top_lenders import (
    create_top_lenders_detailed_table,
)


def build_mortgage_report(
    raw_data: List[Dict[str, Any]],
    counties: List[str],
    years: List[int],
    census_data: Dict = None,
    hud_data: Dict[str, Dict[str, float]] = None,
    progress_tracker=None,
) -> Dict[str, pd.DataFrame]:
    """
    Process raw BigQuery HMDA data and build comprehensive mortgage report dataframes.

    Args:
        raw_data: List of dictionaries from BigQuery results
        counties: List of counties in the report
        years: List of years in the report
        census_data: Optional dictionary of Census demographic data by county
        hud_data: Optional dictionary mapping GEOID5 to HUD income distribution data
        progress_tracker: Optional progress tracker for real-time progress updates

    Returns:
        Dictionary containing multiple dataframes for different report sections
    """
    if not raw_data:
        raise ValueError("No data provided for report building")

    # Convert to DataFrame
    df = pd.DataFrame(raw_data)

    # Ensure required columns exist (mortgage-specific)
    required_columns = ['lei', 'year', 'county_code', 'county_state', 'total_originations', 'lmict_originations', 'mmct_originations']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    # Clean and prepare data
    df = clean_mortgage_data(df)

    # Calculate HHI for loan amounts in latest year (similar to deposits for branches)
    hhi_data = calculate_mortgage_hhi(df)

    # Build different report sections (pass census_data to demographic overview)

    report_sections = [
        ('summary', 'Summary Table', lambda: create_mortgage_summary_table(df, counties, years)),
        ('demographic_overview', 'Demographic Overview', lambda: create_demographic_overview_table(df, years, census_data=census_data)),
        ('income_borrowers', 'Income Borrowers', lambda: create_income_borrowers_table(df, years, hud_data=hud_data)),
        ('income_tracts', 'Income Tracts', lambda: create_income_tracts_table(df, years, hud_data=hud_data, census_data=census_data)),
        ('minority_tracts', 'Minority Tracts', lambda: create_minority_tracts_table(df, years, census_data=census_data)),
        # REMOVED: income_neighborhood_tracts and income_neighborhood_indicators - consolidated into the three tables above
        ('top_lenders_detailed', 'Top Lenders Detailed', lambda: create_top_lenders_detailed_table(df, years)),
        ('market_concentration', 'Market Concentration', lambda: create_market_concentration_table(df, years, metadata={'counties': counties, 'years': years})),
        ('by_lender', 'Lender Summary', lambda: create_lender_summary(df, years)),
        ('by_county', 'County Summary', lambda: create_mortgage_county_summary(df, counties, years)),
        ('trends', 'Trends Analysis', lambda: create_mortgage_trend_analysis(df, years)),
    ]

    total_sections = len(report_sections)
    report_data = {}

    for idx, (key, section_name, create_func) in enumerate(report_sections, 1):
        if progress_tracker:
            progress_tracker.update_section_progress(idx, total_sections, section_name)
        report_data[key] = create_func()

    # Add non-section data
    report_data['raw_data'] = df
    report_data['hhi'] = hhi_data

    return report_data
