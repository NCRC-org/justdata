"""No data is an em dash, a missing year is a gap, and there is no change when
either end is missing (Jad, 2026-11-17; QA records BS-002, BS-018). A whole
year is dashed only when it has no rows at all; a real zero stays 0."""

from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

from justdata.apps.branchsight.pdf_charts import render_branch_trend_chart
from justdata.apps.branchsight.pdf_report import _fmt_change, _fmt_deposits, _fmt_int
from justdata.shared.reporting.report_builder import calculate_hhi_by_year, create_summary_table, save_excel_report
from justdata.shared.utils.no_data import NO_DATA

ROOT = Path(__file__).resolve().parents[3]
YEARS = [2022, 2023, 2024, 2025, 2026]


def _branches(skip_year=2023):
    """Two branches a year, neither in an LMI tract; no rows at all for skip_year."""
    rows = []
    for y in YEARS:
        if y == skip_year:
            continue
        for n, bank in ((1, 'Bank A'), (2, 'Bank B')):
            rows.append({'year': y, 'uninumbr': n, 'bank_name': bank, 'br_lmi': 0, 'br_minority': 0,
                         'total_deposits': 1_000_000.0 * n, 'county_state': 'Hartford County, Connecticut'})
    return pd.DataFrame(rows)


def test_a_year_with_no_rows_is_no_data():
    table = create_summary_table(_branches(), ['Hartford County, Connecticut'], YEARS).set_index('Variable')
    assert table['2023'].isna().all()


def test_a_real_zero_stays_zero():
    table = create_summary_table(_branches(), ['Hartford County, Connecticut'], YEARS).set_index('Variable')
    assert table.loc['LMI Only Branches', '2024'] == 0       # branches exist, none in LMI tracts
    assert table.loc['Total Branches', '2024'] == 2


def test_net_change_needs_both_ends():
    gap_first = create_summary_table(_branches(skip_year=2022), ['x'], YEARS).set_index('Variable')
    assert gap_first['Net Change'].isna().all()
    whole = create_summary_table(_branches(skip_year=None), ['x'], YEARS).set_index('Variable')
    assert whole.loc['Total Branches', 'Net Change'] == 0


def test_hhi_keeps_every_requested_year():
    hhi = calculate_hhi_by_year(_branches(), YEARS)
    assert [h['year'] for h in hhi] == YEARS
    assert next(h for h in hhi if h['year'] == 2023)['hhi_value'] is None
    assert next(h for h in hhi if h['year'] == 2024)['hhi_value'] is not None


def test_pdf_formatters_and_trend_chart():
    assert _fmt_int(float('nan')) == _fmt_int(None) == _fmt_change(float('nan')) == NO_DATA
    assert _fmt_deposits('N/A') == _fmt_deposits(NO_DATA) == NO_DATA
    assert _fmt_int(0) == '0' and _fmt_change(0) == '0'
    rows = create_summary_table(_branches(), ['x'], YEARS).to_dict('records')
    assert render_branch_trend_chart(rows) is not None


def test_excel_shows_the_em_dash(tmp_path):
    summary = create_summary_table(_branches(), ['x'], YEARS)
    path = tmp_path / 'br.xlsx'
    save_excel_report({'summary': summary, 'by_bank': pd.DataFrame(), 'by_county': pd.DataFrame(),
                       'raw_data': pd.DataFrame()}, str(path), metadata={})
    wb = load_workbook(path)
    sheet = wb[[n for n in wb.sheetnames if n.startswith('Section 1')][0]]
    head = [c.value for c in sheet[1]]
    rows = list(sheet.iter_rows(min_row=2, values_only=True))
    assert all(r[head.index('2023')] == NO_DATA for r in rows)
    assert [r for r in rows if r[0] == 'LMI Only Branches'][0][head.index('2024')] == 0


def test_screen_draws_gaps_and_dashes():
    js = (ROOT / 'justdata/shared/web/static/js/branchsight/br_report.js').read_text()
    assert "var NO_DATA = '\\u2014'" in js
    assert 'num(d.hhi_value) || 0' not in js
    assert "? '-'" not in js and "return '-'" not in js
