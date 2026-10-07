"""BranchSight years: one source (config.SOD_YEARS)."""

from justdata.apps.branchsight import config
from justdata.apps.branchsight.core import parse_web_parameters


def test_five_most_recent_sod_years():
    assert config.SOD_YEARS == list(range(config.SOD_LATEST_YEAR - 4, config.SOD_LATEST_YEAR + 1))
    assert config.SOD_LATEST_YEAR == 2025  # latest year in branchsight.sod (checked 2026-10-07)


def test_all_means_sod_years():
    _, years = parse_web_parameters("Lowndes County, Alabama", "all")
    assert years == config.SOD_YEARS
