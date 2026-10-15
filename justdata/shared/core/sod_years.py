"""Single source of truth for the FDIC Summary of Deposits (SOD) years.

BranchSight, MergerMeter, BranchMapper, DataExplorer and the landing page read
the SOD year from here instead of typing it in, so rolling forward to a new SOD
year is a one-line change to ``SOD_LATEST_YEAR``.

Table convention (both projects): ``branchsight.sod`` holds the latest year
only and ``branchsight.sod_legacy`` holds every earlier year. Queries read
``SOD_ALL_YEARS`` filtered by year, so a year stays readable when the yearly
load moves it from ``sod`` to ``sod_legacy``.

Rollout rule: bump ``SOD_LATEST_YEAR`` only after that year has been promoted
into ``branchsight.sod`` and validated (L5: Projects/JustData Frontend
Specs/06-sod-2026-load.md).
"""

from typing import List

# Earliest SOD year loaded (branchsight.sod_legacy).
SOD_EARLIEST_YEAR = 2017

# The year in branchsight.sod: June 30 branch locations and deposits.
# 2026: ticket 13277163649 (L5: Projects/JustData Frontend Specs/06-sod-2026-load.md).
SOD_LATEST_YEAR = 2026

# BranchSight's analysis window: the most recent five years.
SOD_ANALYSIS_SPAN = 5

# Every SOD year, for a FROM clause; filter it by year.
SOD_ALL_YEARS = ("(SELECT * FROM `{project}.branchsight.sod` "
                 "UNION ALL SELECT * FROM `{project}.branchsight.sod_legacy`)")


def sod_all_years(project: str = 'justdata-ncrc') -> str:
    """``SOD_ALL_YEARS`` for a project, ready to follow FROM."""
    return SOD_ALL_YEARS.format(project=project)


def sod_analysis_years() -> List[int]:
    """BranchSight's years, ascending: the last SOD_ANALYSIS_SPAN years."""
    return list(range(SOD_LATEST_YEAR - SOD_ANALYSIS_SPAN + 1, SOD_LATEST_YEAR + 1))


def sod_available_years() -> List[int]:
    """Every loaded SOD year, ascending."""
    return list(range(SOD_EARLIEST_YEAR, SOD_LATEST_YEAR + 1))
