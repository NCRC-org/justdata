"""No data is an em dash, a missing year is a gap, and there is no percent
change on a zero or missing base (Jad, 2026-11-17; QA records BZ-026, BZ-037,
BZ-038, BZ-041, BZ-042)."""

from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

from justdata.apps.bizsight.pdf_charts import render_hhi_chart
from justdata.apps.bizsight.pdf_report import _build_county_summary_table, _fmt_int, _fmt_millions, _fmt_pct
from justdata.apps.bizsight.report_builder import create_comparison_table, create_county_summary_table, create_top_lenders_table
from justdata.shared.utils.no_data import NO_DATA, dash_missing, pct_change, share
from tests.apps.bizsight.test_bizsight_denominator import ROW

ROOT = Path(__file__).resolve().parents[3]
YEARS = [2020, 2021, 2022, 2023, 2024]


def _loving_like():
    """One loan a year, except 2023 with none reported (Loving County, TX)."""
    one = dict(ROW, num_under_100k=1, amt_under_100k=25.0, numsbrev_under_1m=1, amtsbrev_under_1m=25.0,
               low_income_loans=0, moderate_income_loans=0, midu_income_loans=0,
               low_income_amount=0.0, moderate_income_amount=0.0, midu_income_amount=0.0)
    return pd.DataFrame([dict(one, year=y) for y in YEARS if y != 2023])


def test_helpers():
    assert NO_DATA == '—'
    assert share(1, 0) is None and share(None, 4) is None and share(1, 4) == 25.0
    assert pct_change(5, 0) is None and pct_change(None, 5) is None and pct_change(5, None) is None
    assert pct_change(15, 10) == 50.0
    assert dash_missing(pd.DataFrame({'a': [1, None]}))['a'].tolist() == [1, NO_DATA]
    # A real zero is kept; only a missing cell becomes the em dash.
    assert dash_missing(pd.DataFrame({'a': [0, 0.0, None]}))['a'].tolist() == [0, 0.0, NO_DATA]
    assert share(0, 10) == 0.0 and pct_change(0, 10) == -100.0


def test_missing_year_is_none_not_zero():
    table = create_county_summary_table(_loving_like(), YEARS).set_index('Variable')
    assert table.loc['Total Loans', '2023'] is None
    assert table.loc['Loans Under $100K (% of Total)', '2023'] is None
    assert table.loc['Total Loans', '2024'] == 1


def test_share_with_no_classified_loans_is_none():
    table = create_county_summary_table(_loving_like(), YEARS).set_index('Variable')
    # No loan has a tract classification: no LMI share, not 0.0 percent.
    assert pd.isna(table.loc['Loans to LMI Tracts (% of Classified Loans)', '2024'])
    comparison = create_comparison_table(_loving_like(), {}, {}).set_index('Metric')['County (2024)']
    assert pd.isna(comparison['Loans to Low Income Tracts (% of Classified Loans)'])
    lender = create_top_lenders_table(_loving_like().assign(lender_name='Bank A'), year=2024).iloc[0]
    assert pd.isna(lender['Low Income %'])


def test_missing_benchmark_share_is_none_not_zero():
    """A benchmark that lacks a share shows the em dash, never 0.0 percent
    (BZ-005 until the benchmark builders compute that share)."""
    comparison = create_comparison_table(pd.DataFrame([ROW]), {}, {}).set_index('Metric')
    state_col = [c for c in comparison.columns if c.startswith('State (')][0]
    assert pd.isna(comparison.loc['Amount $100K-$250K (% of Total)', state_col])


def test_pdf_cells_show_the_em_dash():
    assert _fmt_int(None) == _fmt_pct(None) == _fmt_millions(None) == _fmt_pct(float('nan')) == NO_DATA
    rows = create_county_summary_table(_loving_like(), YEARS).to_dict('records')
    table, built = _build_county_summary_table(rows)
    assert built
    cells = [c for row in table._cellvalues[1:] for c in row[1:]]   # skip header and labels
    assert NO_DATA in cells and 'None' not in cells and '' not in cells


def test_pdf_hhi_chart_keeps_a_missing_year_as_a_gap():
    hhi = [{'year': y, 'hhi_value': (None if y == 2023 else 10000.0)} for y in YEARS]
    assert render_hhi_chart(hhi) is not None
    assert render_hhi_chart([{'year': 2023, 'hhi_value': None}]) is None


def test_excel_shows_the_em_dash(tmp_path):
    from justdata.apps.bizsight.excel_export import save_bizsight_excel_report
    county = create_county_summary_table(_loving_like(), YEARS).to_dict('records')
    path = tmp_path / 'bs.xlsx'
    save_bizsight_excel_report({'county_summary_table': county}, str(path),
                               {'county_name': 'Loving County', 'state_name': 'Texas', 'years': YEARS})
    sheet = load_workbook(path)['County Summary - Number']
    header = [c.value for c in sheet[1]]
    col = header.index('2023') + 1
    values = [sheet.cell(row=r, column=col).value for r in range(2, sheet.max_row + 1)]
    assert values and all(v == NO_DATA for v in values)


def test_screen_draws_gaps_and_dashes():
    js = (ROOT / 'justdata/shared/web/static/js/bizsight/bs_report.js').read_text()
    assert "var NO_DATA = '\\u2014'" in js
    assert 'spanGaps: false' in js
    assert 'num(d.hhi_value) || 0' not in js
    assert "? '-'" not in js and "return '-'" not in js
    assert 'No LMI tracts in county' not in js


# ---- A whole year is dashed only when it has no data at all -----------------

def _with_a_zero_year():
    """2023 has a reported row with zero loans; 2021 has no row at all."""
    df = _loving_like()
    zero = dict(df.iloc[0].to_dict(), year=2023, num_under_100k=0, amt_under_100k=0.0,
                numsbrev_under_1m=0, amtsbrev_under_1m=0.0)
    return pd.concat([df[df['year'] != 2021], pd.DataFrame([zero])], ignore_index=True)


def test_a_year_with_no_data_at_all_is_dashed_in_every_cell():
    table = create_county_summary_table(_with_a_zero_year(), YEARS)
    assert table['2021'].isna().all()


def test_a_year_with_data_and_a_zero_count_shows_zero():
    table = create_county_summary_table(_with_a_zero_year(), YEARS).set_index('Variable')
    # Counts and amounts that exist are shown, zero included.
    assert table.loc['Total Loans', '2023'] == 0
    assert table.loc['Total Loan Amount (in millions)', '2023'] == 0
    # Only a share of zero (0 of 0) has no value.
    assert pd.isna(table.loc['Loans Under $100K (% of Total)', '2023'])
    # A zero numerator over a real total is a real 0.0 percent.
    assert share(0, 10) == 0.0
    assert table.loc['Loans $100K-$250K (% of Total)', '2024'] == 0.0


def test_zero_counts_stay_zero_in_pdf_and_excel(tmp_path):
    from justdata.apps.bizsight.excel_export import save_bizsight_excel_report
    rows = create_county_summary_table(_with_a_zero_year(), YEARS).to_dict('records')
    assert _fmt_int(0) == '0' and _fmt_pct(0.0) == '0.0%'
    table, _ = _build_county_summary_table(rows)
    header = [str(getattr(c, 'text', c)) for c in table._cellvalues[0]]
    total_loans = [r for r in table._cellvalues if 'Total Loans' in str(getattr(r[0], 'text', r[0]))][0]
    assert total_loans[header.index('2023')] == '0'
    assert total_loans[header.index('2021')] == NO_DATA

    path = tmp_path / 'bs.xlsx'
    save_bizsight_excel_report({'county_summary_table': rows}, str(path),
                               {'county_name': 'Loving County', 'state_name': 'Texas', 'years': YEARS})
    sheet = load_workbook(path)['County Summary - Number']
    head = [c.value for c in sheet[1]]
    total = [r for r in sheet.iter_rows(min_row=2, values_only=True) if r[0] == 'Total Loans'][0]
    assert total[head.index('2023')] == 0
    assert total[head.index('2021')] == NO_DATA


def test_screen_formatters_keep_zero():
    js = (ROOT / 'justdata/shared/web/static/js/bizsight/bs_report.js').read_text()
    # num() returns null only for missing values, so 0 formats as "0" and "0.0%".
    assert "function num(v) { var n = parseFloat(v); return isNaN(n) ? null : n; }" in js
    assert "function fmtInt(v) { var n = num(v); return n === null ? NO_DATA" in js
