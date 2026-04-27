"""DataExplorer lender analysis package.

Public API:
    run_lender_analysis           -- orchestrator called by blueprint.py
    check_lender_has_data         -- pre-analysis data availability check
    apply_filters_to_sql_template -- SQL template helper (used by tests)
    parse_lender_wizard_parameters -- parameter parser
"""
from justdata.apps.dataexplorer.lender_analysis.core import run_lender_analysis
from justdata.apps.dataexplorer.lender_analysis.data_check import check_lender_has_data
from justdata.apps.dataexplorer.lender_analysis.filters import (
    apply_filters_to_sql_template,
    parse_lender_wizard_parameters,
)

__all__ = [
    "run_lender_analysis",
    "check_lender_has_data",
    "apply_filters_to_sql_template",
    "parse_lender_wizard_parameters",
]
