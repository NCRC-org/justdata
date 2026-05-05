"""Shared merger-Excel report generator package.

Public API:
    create_merger_excel  -- builds the merger analysis Excel workbook used by
                            mergermeter (and any future shared callers).

Worksheet builders are also re-exported for direct use.
"""
from justdata.shared.reporting.excel.generator import create_merger_excel
from justdata.shared.reporting.excel.worksheets.assessment_areas import (
    _create_assessment_areas_sheet,
)
from justdata.shared.reporting.excel.worksheets.branch_data import _create_branch_data_sheet
from justdata.shared.reporting.excel.worksheets.mortgage_data import _create_mortgage_data_sheet
from justdata.shared.reporting.excel.worksheets.mortgage_goals import _create_mortgage_goals_sheet
from justdata.shared.reporting.excel.worksheets.notes import _create_notes_sheet
from justdata.shared.reporting.excel.worksheets.sb_data import _create_sb_data_sheet
from justdata.shared.reporting.excel.worksheets.sb_goals import _create_sb_goals_sheet

__all__ = [
    "create_merger_excel",
    "_create_assessment_areas_sheet",
    "_create_branch_data_sheet",
    "_create_mortgage_data_sheet",
    "_create_mortgage_goals_sheet",
    "_create_notes_sheet",
    "_create_sb_data_sheet",
    "_create_sb_goals_sheet",
]
