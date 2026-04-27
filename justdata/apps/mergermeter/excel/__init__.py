"""Mergermeter Excel report generator package.

Public API:
    create_merger_excel  -- builds the merger analysis Excel workbook

Worksheet builders are also re-exported for direct use.
"""
from justdata.apps.mergermeter.excel.generator import create_merger_excel
from justdata.apps.mergermeter.excel.worksheets.assessment_areas import (
    create_simple_assessment_areas_sheet,
)
from justdata.apps.mergermeter.excel.worksheets.branch import create_simple_branch_sheet
from justdata.apps.mergermeter.excel.worksheets.mortgage import create_simple_mortgage_sheet
from justdata.apps.mergermeter.excel.worksheets.notes import create_simple_notes_sheet
from justdata.apps.mergermeter.excel.worksheets.sb import create_simple_sb_sheet

__all__ = [
    "create_merger_excel",
    "create_simple_assessment_areas_sheet",
    "create_simple_branch_sheet",
    "create_simple_mortgage_sheet",
    "create_simple_notes_sheet",
    "create_simple_sb_sheet",
]
