"""Mortgage report builder package (LendSight).

Public API:
    build_mortgage_report      -- assembles all report sections from raw HMDA rows
    save_mortgage_excel_report -- writes the multi-sheet Excel workbook

Section builders and helpers are also re-exported for backward
compatibility with internal callers in the dataexplorer app.
"""
from justdata.apps.lendsight.report_builder.coordinator import build_mortgage_report
from justdata.apps.lendsight.report_builder.excel_export import save_mortgage_excel_report
from justdata.apps.lendsight.report_builder.formatting import (
    clean_mortgage_data,
    map_lender_type,
)
from justdata.apps.lendsight.report_builder.sections.concentration import (
    calculate_mortgage_hhi_for_year,
)
from justdata.apps.lendsight.report_builder.sections.demographics import (
    create_demographic_overview_table,
)
from justdata.apps.lendsight.report_builder.sections.income_borrowers import (
    create_income_borrowers_table,
)
from justdata.apps.lendsight.report_builder.sections.income_indicators import (
    calculate_minority_quartiles,
    classify_tract_minority_quartile,
)
from justdata.apps.lendsight.report_builder.sections.income_tracts import (
    create_income_tracts_table,
    get_tract_population_data_for_counties,
)
from justdata.apps.lendsight.report_builder.sections.minority_tracts import (
    create_minority_tracts_table,
)
from justdata.apps.lendsight.report_builder.sections.top_lenders import (
    create_top_lenders_detailed_table,
)

__all__ = [
    "build_mortgage_report",
    "save_mortgage_excel_report",
    "clean_mortgage_data",
    "map_lender_type",
    "calculate_mortgage_hhi_for_year",
    "calculate_minority_quartiles",
    "classify_tract_minority_quartile",
    "create_demographic_overview_table",
    "create_income_borrowers_table",
    "create_income_tracts_table",
    "get_tract_population_data_for_counties",
    "create_minority_tracts_table",
    "create_top_lenders_detailed_table",
]
