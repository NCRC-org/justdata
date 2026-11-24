"""BranchSight bank Net Change is matched on RSSD, with Acquired (T4, 2026-11-20).

The 2026 SOD table publishes bank names in title case and 2017 to 2025 in
upper case, so matching on the name found almost no bank in the first year
and Net Change equalled the bank's whole branch count (BS-001). Banks are now
matched on RSSD; Acquired counts latest-year branches another RSSD held in the
first year (same UNINUMBR).

The fixture is public FDIC SOD rows (2022 to 2026) for the deck's counties
and Charleston County, SC, where Synovus merged into Pinnacle (RSSD 395238
into 2925666) between the 2025 and 2026 SOD.
"""
from pathlib import Path

import pandas as pd
import pytest

from justdata.shared.reporting.report_builder import (
    BANK_CHANGE_NOTE, NEW_TO_COUNTY, bank_branch_changes, bank_changes_for_narrative,
    clean_data, create_bank_summary, create_summary_table,
)
from justdata.shared.utils.no_data import NO_DATA

FIXTURE = Path(__file__).parent / "fixtures" / "sod_t4_counties.csv"
YEARS = [2022, 2023, 2024, 2025, 2026]
DECK = ["Philadelphia County, Pennsylvania", "Perry County, Alabama", "Sequatchie County, Tennessee",
        "Hancock County, Georgia", "Grainger County, Tennessee"]
MERGER = "Charleston County, South Carolina"
PINNACLE, SYNOVUS = "2925666", "395238"


@pytest.fixture(scope="module")
def counties():
    df = pd.read_csv(FIXTURE, dtype={"rssd": str, "uninumbr": str, "geoid5": str})
    df["total_branches"] = 1
    return {name: clean_data(g.copy()) for name, g in df.groupby("county_state")}


def _net_as_count(row):
    """A bank new to the county changed by its whole count."""
    return row["Total Branches"] if row["Net Change"] == NEW_TO_COUNTY else row["Net Change"]


@pytest.mark.parametrize("county", DECK + [MERGER])
def test_bank_changes_sum_to_the_county_change(counties, county):
    df = counties[county]
    table = create_bank_summary(df, YEARS)
    changes = bank_branch_changes(df, 2022, 2026)
    left = sum(c["first"] for c in changes.values() if c["latest"] == 0)
    county_change = df[df.year == 2026].uninumbr.nunique() - df[df.year == 2022].uninumbr.nunique()

    assert sum(_net_as_count(r) for _, r in table.iterrows()) - left == county_change
    # The county tile (Section 1) is unchanged and agrees.
    summary = create_summary_table(df, [county], YEARS)
    assert summary.loc[summary.Variable == "Total Branches", "Net Change"].iloc[0] == county_change


@pytest.mark.parametrize("county", DECK + [MERGER])
def test_every_bank_change_adds_up(counties, county):
    for c in bank_branch_changes(counties[county], 2022, 2026).values():
        assert c["net"] == c["latest"] - c["first"]
        assert c["net"] == c["opened"] + c["acquired"] - c["closed"] - c["transferred_out"]


def test_the_name_case_change_no_longer_counts_every_branch_as_new(counties):
    """BS-001: under name matching, Net Change equalled Total Branches."""
    table = create_bank_summary(counties["Philadelphia County, Pennsylvania"], YEARS)
    pnc = table[table["Bank Name"] == "PNC Bank"].iloc[0]
    assert pnc["Total Branches"] == 34 and pnc["Net Change"] == 0
    numeric = table[table["Net Change"].apply(lambda v: isinstance(v, (int, float)))]
    assert (numeric["Net Change"] != numeric["Total Branches"]).mean() > 0.8


def test_merger_shows_as_acquired_not_opened(counties):
    df = counties[MERGER]
    table = create_bank_summary(df, YEARS)
    pinnacle = table[table["Bank Name"] == "Pinnacle Bank"].iloc[0]
    assert (pinnacle["Total Branches"], pinnacle["Net Change"], pinnacle["Acquired"], pinnacle["Transferred Out"]) == (12, 5, 5, 0)
    assert "SYNOVUS BANK" not in set(table["Bank Name"]) and "Synovus Bank" not in set(table["Bank Name"])

    changes = bank_branch_changes(df, 2022, 2026)
    assert changes[PINNACLE]["acquired"] == 5 and changes[PINNACLE]["opened"] == 1
    assert changes[SYNOVUS]["transferred_out"] == 5 and changes[SYNOVUS]["closed"] == 0


def test_latest_name_is_shown(counties):
    names = set(create_bank_summary(counties[MERGER], YEARS)["Bank Name"])
    assert "Wells Fargo Bank" in names and "WELLS FARGO BANK" not in names


def test_new_to_county_and_no_first_year_data():
    rows = pd.DataFrame([
        # Bank 1 keeps a branch; bank 2 arrives with a new branch; bank 3
        # buys bank 4's branch.
        dict(year=2022, rssd="1", bank_name="ONE BANK", uninumbr="a"),
        dict(year=2022, rssd="4", bank_name="FOUR BANK", uninumbr="d"),
        dict(year=2026, rssd="1", bank_name="One Bank", uninumbr="a"),
        dict(year=2026, rssd="2", bank_name="Two Bank", uninumbr="b"),
        dict(year=2026, rssd="3", bank_name="Three Bank", uninumbr="d"),
    ]).assign(geoid5="00001", county_state="X", total_branches=1, lmict=0, mmct=0)
    table = create_bank_summary(clean_data(rows.copy()), [2022, 2026]).set_index("Bank Name")
    assert table.loc["Two Bank", "Net Change"] == NEW_TO_COUNTY and table.loc["Two Bank", "Acquired"] == 0
    assert table.loc["Three Bank", "Net Change"] == 1 and table.loc["Three Bank", "Acquired"] == 1
    assert table.loc["One Bank", "Net Change"] == 0

    latest_only = create_bank_summary(clean_data(rows[rows.year == 2026].copy()), [2022, 2026])
    assert set(latest_only["Net Change"]) == {NO_DATA} and set(latest_only["Acquired"]) == {NO_DATA}


def test_narrative_gets_opened_closed_and_acquired_separately(counties):
    figures = bank_changes_for_narrative(counties[MERGER], YEARS)
    pinnacle = next(b for b in figures["banks"] if b["bank_name"] == "Pinnacle Bank")
    assert (pinnacle["opened"], pinnacle["closed"], pinnacle["acquired"]) == (1, 1, 5)
    assert any(b["bank_name"] == "SYNOVUS BANK" for b in figures["banks_that_left"])
    totals = figures["county_totals"]
    assert totals["latest"] - totals["first"] == 133 - 120


def test_narrative_prompt_forbids_calling_acquired_opened():
    from justdata.apps.branchsight import analysis
    source = Path(analysis.__file__).read_text()
    assert "Never describe acquired branches as opened" in source
    assert "bank_changes" in source


def test_note_is_on_screen_in_excel_and_in_the_pdf(tmp_path, counties):
    from justdata.shared.reporting.report_builder import save_excel_report
    from openpyxl import load_workbook
    root = Path(__file__).resolve().parents[3] / "justdata"
    js = (root / "shared/web/static/js/branchsight/br_report.js").read_text()
    assert "'Acquired'" in js and "'Transferred Out'" in js
    assert "Acquired shows how many came from another institution." in js
    assert "Acquired and transferred show branches that moved between institutions." in js
    assert "BANK_CHANGE_NOTE" in (root / "apps/branchsight/pdf_report.py").read_text()

    df = counties["Grainger County, Tennessee"]
    report = {"by_bank": create_bank_summary(df, YEARS), "summary": pd.DataFrame(), "by_county": pd.DataFrame(),
              "raw_data": pd.DataFrame(), "trends": pd.DataFrame()}
    out = tmp_path / "t.xlsx"
    save_excel_report(report, str(out), metadata={"years": YEARS, "counties": ["Grainger County, Tennessee"]})
    sheet = next(ws for ws in load_workbook(out).worksheets if ws.title.startswith("Section 2"))
    values = [c.value for row in sheet.iter_rows() for c in row]
    assert "Acquired" in values and "Transferred Out" in values and BANK_CHANGE_NOTE in values
    assert "Acquired and transferred show branches that moved between institutions." in BANK_CHANGE_NOTE


@pytest.mark.parametrize("county", DECK + [MERGER])
def test_table_figures_reconcile_with_the_bank_changes(counties, county):
    """Every shown bank's Net Change, Acquired and Transferred Out match its
    reconciled figures (net = opened + acquired - closed - transferred out)."""
    df = counties[county]
    changes = bank_branch_changes(df, 2022, 2026)
    by_name = {c["bank_name"]: c for c in changes.values() if c["latest"] > 0}
    for _, row in create_bank_summary(df, YEARS).iterrows():
        c = by_name[row["Bank Name"]]
        if row["Net Change"] != NEW_TO_COUNTY:
            assert row["Net Change"] == c["opened"] + row["Acquired"] - c["closed"] - row["Transferred Out"]
