"""BranchSight HHI, market share and top-bank lists aggregate by RSSD (2026-11-24).

They grouped deposits by bank name, so unrelated banks that share a name were
added together as one bank: nine different RSSDs are called "Pinnacle Bank",
and two of them (288376, Jasper AL, and 2925666, Nashville TN) both have
branches in Jefferson County, AL in 2023 to 2026.

The fixture is public FDIC SOD deposits by county, year and RSSD, 2022 to
2026. "Before" is the old name grouping; "after" is by RSSD.
"""
from pathlib import Path

import pandas as pd
import pytest

from justdata.shared.reporting import report_builder as rb
from justdata.shared.utils import fdic_institutions

FIXTURE = Path(__file__).parent / "fixtures" / "sod_hhi_counties.csv"
YEARS = [2022, 2023, 2024, 2025, 2026]
JEFFERSON = "Jefferson County, Alabama"
HQ = {"288376": "Jasper, AL", "2925666": "Nashville, TN"}

# HHI by year (0 to 10,000), before and after.
EXPECTED = {
    "Philadelphia County, Pennsylvania": (
        {2022: 1461.42, 2023: 1514.61, 2024: 1463.97, 2025: 1463.66, 2026: 1445.04},
        {2022: 1461.42, 2023: 1514.61, 2024: 1463.97, 2025: 1463.66, 2026: 1445.04}),
    "Charleston County, South Carolina": (
        {2022: 1151.35, 2023: 1024.58, 2024: 942.5, 2025: 963.94, 2026: 1068.57},
        {2022: 1151.35, 2023: 1024.58, 2024: 942.5, 2025: 963.94, 2026: 1068.57}),
    JEFFERSON: (
        {2022: 1783.82, 2023: 1833.98, 2024: 1681.57, 2025: 1538.3, 2026: 1400.95},
        {2022: 1783.82, 2023: 1833.81, 2024: 1681.39, 2025: 1538.09, 2026: 1399.62}),
}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    calls = []

    def fake(rssds):
        calls.append(sorted(rssds))
        return {r: HQ[r] for r in rssds if r in HQ}
    monkeypatch.setattr(fdic_institutions, "headquarters", fake)
    return calls


@pytest.fixture(scope="module")
def counties():
    df = pd.read_csv(FIXTURE, dtype={"rssd": str, "year": str})
    df["total_deposits"] = df["deposits_000s"] * 1000
    df["uninumbr"] = df["rssd"] + "_" + df["year"]
    df = df.assign(total_branches=1, lmict=0, mmct=0, geoid5="x")
    return {name: rb.clean_data(g.copy()) for name, g in df.groupby("county_state")}


def _by_name_hhi(df):
    out = {}
    for year, g in df.groupby("year"):
        deposits = g.groupby("bank_name")["total_deposits"].sum()
        out[int(year)] = round(float(((deposits / deposits.sum() * 100) ** 2).sum()), 2)
    return out


@pytest.mark.parametrize("county", list(EXPECTED))
def test_hhi_before_and_after(counties, county):
    before, after = EXPECTED[county]
    df = counties[county]
    assert _by_name_hhi(df) == before
    got = {r["year"]: float(r["hhi_value"]) for r in rb.calculate_hhi_by_year(df, YEARS)}
    assert got == after
    assert float(rb.calculate_hhi(df)["hhi"]) == after[2026]


def test_same_named_banks_stay_separate_and_are_labelled(counties, no_network):
    df = counties[JEFFERSON]
    names = rb.bank_display_names(df)
    assert names["288376"] == "Pinnacle Bank (Jasper, AL)"
    assert names["2925666"] == "Pinnacle Bank (Nashville, TN)"
    assert no_network == [["288376", "2925666"]]   # only the colliding banks are looked up

    hhi = rb.calculate_hhi(df, names)
    top = {b["bank_name"] for b in hhi["top_banks"]}
    assert "Pinnacle Bank (Nashville, TN)" in top and "Pinnacle Bank" not in top
    nashville = next(b for b in hhi["top_banks"] if b["rssd"] == "2925666")
    jasper_deposits = df[(df.year == 2026) & (df.rssd == "288376")].total_deposits.sum()
    combined = df[(df.year == 2026) & (df.bank_name == "Pinnacle Bank")].total_deposits.sum()
    assert nashville["total_deposits"] == combined - jasper_deposits


def test_bank_table_uses_the_same_names(counties):
    table = rb.create_bank_summary(counties[JEFFERSON], YEARS)
    assert {"Pinnacle Bank (Jasper, AL)", "Pinnacle Bank (Nashville, TN)"} <= set(table["Bank Name"])
    assert table["Bank Name"].is_unique


def test_lookup_failure_falls_back_to_the_rssd(counties, monkeypatch):
    monkeypatch.setattr(fdic_institutions, "headquarters", lambda rssds: {})
    names = rb.bank_display_names(counties[JEFFERSON])
    assert names["288376"] == "Pinnacle Bank (RSSD 288376)"


def test_no_lookup_when_names_are_unique(counties, no_network):
    rb.bank_display_names(counties["Philadelphia County, Pennsylvania"])
    assert no_network == []


def test_latest_years_name_is_shown(counties):
    names = rb.bank_display_names(counties["Philadelphia County, Pennsylvania"])
    assert "PNC Bank" in names.values() and "PNC BANK" not in names.values()
