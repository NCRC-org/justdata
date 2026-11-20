"""No data is an em dash, a missing year is a gap, and there is no percent
change on a zero or missing base (Jad, 2026-11-17; QA records LS-019, LS-043).
A whole year is dashed only when it has no rows at all; a real zero stays 0."""

from pathlib import Path

import pandas as pd

from justdata.apps.lendsight.pdf_charts import render_hhi_chart
from justdata.apps.lendsight.report_builder.sections.income_borrowers import create_income_borrowers_table
from justdata.apps.lendsight.report_builder.sections.income_indicators import create_income_neighborhood_indicators_table
from justdata.shared.utils.no_data import NO_DATA, fmt_pct_change, fmt_pp_change, fmt_share

ROOT = Path(__file__).resolve().parents[3]
YEARS = [2021, 2022, 2023, 2024, 2025]


def _row(year, total=10, lmib=4):
    return {'year': year, 'geoid5': '48301', 'total_originations': total, 'lmib_originations': lmib,
            'low_income_borrower_originations': lmib, 'moderate_income_borrower_originations': 0,
            'middle_income_borrower_originations': total - lmib, 'upper_income_borrower_originations': 0,
            'lmict_originations': 0, 'mmct_originations': 0}


def _df(skip_year=2023, zero_lmib_year=2024):
    """No rows at all for 2023; 2024 has loans but none to LMI borrowers."""
    rows = [_row(y, lmib=0 if y == zero_lmib_year else 4) for y in YEARS if y != skip_year]
    return pd.DataFrame(rows)


def test_text_formatters():
    assert fmt_share(None) == fmt_share(float('nan')) == NO_DATA
    assert fmt_share(0.0) == '0.0%' and fmt_share(12.34) == '12.3%'
    assert fmt_pp_change(None, 5) == fmt_pp_change(5, None) == NO_DATA
    assert fmt_pp_change(5, 5) == '0.0pp' and fmt_pp_change(1, 3.04) == '+2.0pp' and fmt_pp_change(3, 1) == '-2.0pp'
    assert fmt_pct_change(0, 5) == fmt_pct_change(None, 5) == NO_DATA
    assert fmt_pct_change(10, 15) == '+50.0%' and fmt_pct_change(10, 0) == '-100.0%'


def test_a_year_with_no_rows_is_dashed_in_every_cell():
    table = create_income_borrowers_table(_df(), YEARS).set_index('Metric')
    assert (table['2023'] == NO_DATA).all()
    assert table.loc['Total Loans', '2023'] == NO_DATA


def test_a_real_zero_stays_zero():
    table = create_income_borrowers_table(_df(), YEARS).set_index('Metric')
    lmi = [m for m in table.index if 'Low' in m and 'Moderate' in m][0]
    assert table.loc[lmi, '2024'] == '0.0%'          # loans exist, none to LMI borrowers
    assert table.loc['Total Loans', '2024'] == '10'


def test_change_needs_both_ends():
    table = create_income_borrowers_table(_df(skip_year=2021), YEARS).set_index('Metric')
    assert (table['Change'] == NO_DATA).all()        # first year has no data
    whole = create_income_borrowers_table(_df(skip_year=None), YEARS).set_index('Metric')
    assert NO_DATA not in whole['Change'].tolist()


def test_indicator_totals_and_changes():
    table = create_income_neighborhood_indicators_table(_df(skip_year=2021), YEARS)
    loans = table[table['Metric'].str.contains('Loans', case=False)].iloc[0]
    change_col = [c for c in table.columns if c.startswith('Change')][0]
    assert loans['2021'] == NO_DATA and loans[change_col] == NO_DATA


def test_pdf_hhi_chart_keeps_a_missing_year_as_a_gap():
    rows = [{'Loan Purpose': 'All Loans', '2021': 900.0, '2022': None, '2023': 950.0}]
    assert render_hhi_chart(rows) is not None
    assert render_hhi_chart([{'Loan Purpose': 'All Loans', '2021': None}]) is None


def test_screen_draws_gaps_and_dashes():
    tables = (ROOT / 'justdata/shared/web/static/js/lendsight/ls_tables.js').read_text()
    charts = (ROOT / 'justdata/shared/web/static/js/lendsight/ls_charts.js').read_text()
    assert "var NO_DATA = '\\u2014'" in tables
    assert "if (!m) return null;" in tables                      # the em dash is never read as 0.0pp
    assert "val = total ? '0' : '0.0%'" not in tables
    assert "v = isNaN(v) ? 0 : v;" not in charts and "if (isNaN(v)) return null;" in charts


# Found by the 2026-11-20 run on real data (Loving County, TX, purchase loans):
# the Excel-only builders and the PDF total rows still wrote 0 for a year with
# no rows, and missing HHI cells were blank.

RACE = ['hispanic_originations', 'black_originations', 'white_originations', 'asian_originations',
        'native_american_originations', 'hopi_originations', 'multi_racial_originations']


def _demo_df():
    """No rows for 2023; 2024 has loans but none with demographic data."""
    rows = []
    for y in YEARS:
        if y == 2023:
            continue
        r = {c: 0 for c in RACE}
        r.update(year=y, total_originations=10, loans_with_demographic_data=0 if y == 2024 else 10,
                 lender_name='FIRST BANK', lei='LEI0000000000000001', lender_type='Bank', geoid5='48301',
                 county_state='Loving County, Texas', lmib_originations=0, lmict_originations=0,
                 mmct_originations=0, total_loan_amount=1000000)
        if y != 2024:
            r['white_originations'] = 10
        rows.append(r)
    return pd.DataFrame(rows)


def test_excel_demographic_overview_dashes_only_the_empty_year():
    from justdata.apps.lendsight.report_builder.excel_export.demographic import (
        create_demographic_overview_table_for_excel)
    from justdata.shared.utils.no_data import dash_missing
    table = dash_missing(create_demographic_overview_table_for_excel(_demo_df(), YEARS)).set_index('Metric')
    assert (table['2023'] == NO_DATA).all()               # no rows at all
    assert table.loc['Total Loans', '2024'] == 10          # loans exist
    assert table.loc['White', '2024'] == NO_DATA           # 0 of 0 with demographic data
    assert table.loc['White', '2022'] == 100.0
    assert table.loc['Black', '2022'] == 0.0               # a real zero stays 0


def test_excel_workbook_writes_the_dash(tmp_path):
    from openpyxl import load_workbook
    from justdata.apps.lendsight.report_builder.excel_export.writer import save_mortgage_excel_report
    out = tmp_path / 'ls.xlsx'
    conc = [{'Loan Purpose': 'All Loans', **{str(y): (None if y == 2023 else 2500.0) for y in YEARS}}]
    save_mortgage_excel_report({'raw_data': _demo_df(), 'market_concentration': conc}, str(out),
                               {'years': YEARS, 'counties': ['Loving County, Texas']})
    wb = load_workbook(out)
    demo = [s for s in wb.sheetnames if s.startswith('Section 1')][0]
    rows = list(wb[demo].iter_rows(values_only=True))
    col = rows[0].index('2023')
    assert all(r[col] == NO_DATA for r in rows[1:])
    hhi = [s for s in wb.sheetnames if 'HHI' in s][0]
    rows = list(wb[hhi].iter_rows(values_only=True))
    assert rows[1][rows[0].index('2023')] == NO_DATA


def test_pdf_total_row_and_hhi_cells_dash_an_empty_year():
    source = (ROOT / 'justdata/apps/lendsight/pdf_report.py').read_text()
    assert "if v is not None else '0'" not in source
    from justdata.apps.lendsight import pdf_report
    from reportlab.platypus import Table
    data = [{'Loan Purpose': 'All Loans', **{str(y): (None if y == 2023 else 2500.0) for y in YEARS}}]
    table = pdf_report._build_hhi_table(data)
    tables = [table] if isinstance(table, Table) else [t for t in table if isinstance(t, Table)]
    assert tables, 'the HHI table was not built'
    cells = [str(getattr(c, 'text', c)) for row in tables[0]._cellvalues for c in row]
    assert NO_DATA in cells and 'nan' not in cells
