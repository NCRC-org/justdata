"""Area report builder package (DataExplorer).

Public API:
    build_area_report             -- coordinator that assembles the per-lender / area report
    build_area_report_all_lenders -- coordinator variant that runs across all lenders
    filter_df_by_loan_purpose     -- shared filter (re-exported from dataexplorer.shared)

Section table builders are also re-exported for direct use.
"""
from justdata.apps.dataexplorer.report_builder.coordinator import build_area_report
from justdata.apps.dataexplorer.report_builder.coordinator_all_lenders import (
    build_area_report_all_lenders,
)
from justdata.apps.dataexplorer.report_builder.queries import fetch_acs_housing_data
from justdata.apps.dataexplorer.report_builder.sections.housing_costs import (
    create_housing_costs_table,
)
from justdata.apps.dataexplorer.report_builder.sections.housing_units import (
    create_housing_units_table,
)
from justdata.apps.dataexplorer.report_builder.sections.lender_borrower_income import (
    create_lender_borrower_income_table,
)
from justdata.apps.dataexplorer.report_builder.sections.lender_neighborhood_demographics import (
    create_lender_neighborhood_demographics_table,
)
from justdata.apps.dataexplorer.report_builder.sections.lender_neighborhood_income import (
    create_lender_neighborhood_income_table,
)
from justdata.apps.dataexplorer.report_builder.sections.lender_race_ethnicity import (
    create_lender_race_ethnicity_table,
)
from justdata.apps.dataexplorer.report_builder.sections.loan_costs import (
    create_lender_loan_costs_table,
    create_loan_costs_table,
)
from justdata.apps.dataexplorer.report_builder.sections.owner_occupancy import (
    create_owner_occupancy_table,
)
from justdata.apps.dataexplorer.shared.filters import filter_df_by_loan_purpose

__all__ = [
    "build_area_report",
    "build_area_report_all_lenders",
    "fetch_acs_housing_data",
    "filter_df_by_loan_purpose",
    "create_loan_costs_table",
    "create_lender_loan_costs_table",
    "create_housing_costs_table",
    "create_housing_units_table",
    "create_owner_occupancy_table",
    "create_lender_race_ethnicity_table",
    "create_lender_borrower_income_table",
    "create_lender_neighborhood_income_table",
    "create_lender_neighborhood_demographics_table",
]
