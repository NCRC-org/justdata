"""Mergermeter Excel report generator package.

Public API:
    build_mergermeter_workbook -- mergermeter-specific adapter that
        transforms raw query DataFrames + metadata into the shape the
        shared generator expects, delegates to
        justdata.shared.reporting.excel.create_merger_excel, and
        post-processes the resulting workbook with the mergermeter-only
        HHI sheet.

Worksheet builders are also re-exported for direct use.
"""
from justdata.apps.mergermeter.excel.generator import build_mergermeter_workbook
from justdata.apps.mergermeter.excel.worksheets.assessment_areas import (
    create_simple_assessment_areas_sheet,
)
from justdata.apps.mergermeter.excel.worksheets.branch import create_simple_branch_sheet
from justdata.apps.mergermeter.excel.worksheets.mortgage import create_simple_mortgage_sheet
from justdata.apps.mergermeter.excel.worksheets.notes import create_simple_notes_sheet
from justdata.apps.mergermeter.excel.worksheets.sb import create_simple_sb_sheet

__all__ = [
    "build_mergermeter_workbook",
    "create_simple_assessment_areas_sheet",
    "create_simple_branch_sheet",
    "create_simple_mortgage_sheet",
    "create_simple_notes_sheet",
    "create_simple_sb_sheet",
]
