"""Tract income shares divide by loans with a tract classification (the state
and national basis), and Section 3 states how many loans that leaves out."""

from pathlib import Path

import pandas as pd

from justdata.apps.bizsight.report_builder import (
    classified_totals, create_comparison_table, create_county_summary_table, create_top_lenders_table)

ROOT = Path(__file__).resolve().parents[3]

# 100 loans: 10 low, 20 moderate, 60 middle-or-upper, 10 with no classification.
ROW = {
    'year': 2024, 'num_under_100k': 100, 'num_100k_250k': 0, 'num_250k_1m': 0,
    'amt_under_100k': 1000.0, 'amt_100k_250k': 0.0, 'amt_250k_1m': 0.0,
    'numsbrev_under_1m': 50, 'amtsbrev_under_1m': 500.0,
    'low_income_loans': 10, 'moderate_income_loans': 20, 'midu_income_loans': 60,
    'low_income_amount': 100.0, 'moderate_income_amount': 200.0, 'midu_income_amount': 500.0,
}


def test_classified_totals_leave_out_unclassified_loans():
    assert classified_totals(pd.DataFrame([ROW])) == (90, 800.0)


def test_county_summary_lmi_share_uses_classified_loans():
    rows = create_county_summary_table(pd.DataFrame([ROW]), [2024]).set_index('Variable')['2024']
    assert round(rows['Loans to LMI Tracts (% of Classified Loans)'], 4) == round(30 / 90 * 100, 4)
    assert round(rows['Amount to LMI Tracts (% of Classified Amount)'], 4) == round(300 / 800 * 100, 4)


def test_comparison_county_shares_use_classified_loans():
    table = create_comparison_table(pd.DataFrame([ROW]), {}, {}).set_index('Metric')['County (2024)']
    assert round(table['Loans to Low Income Tracts (% of Classified Loans)'], 4) == round(10 / 90 * 100, 4)
    assert round(table['Amount to Moderate Income Tracts (% of Classified Amount)'], 4) == 25.0


def test_lender_shares_use_classified_loans():
    lender = dict(ROW, lender_name='Bank A', year=2024)
    row = create_top_lenders_table(pd.DataFrame([lender]), year=2024).iloc[0]
    assert round(row['Lmi Tract'], 4) == round(30 / 90 * 100, 4)
    assert round(row['Low Income %'], 4) == round(10 / 90 * 100, 4)


def test_section3_shows_the_excluded_count_and_methods_states_the_basis():
    tpl = (ROOT / 'justdata/apps/bizsight/templates/partials/bizsight_report_template.html').read_text()
    js = (ROOT / 'justdata/shared/web/static/js/bizsight/bs_report.js').read_text()
    methods = (ROOT / 'justdata/apps/bizsight/templates/partials/bizsight_methods.html').read_text()
    section3 = tpl[tpl.index('id="section3"'):tpl.index('id="section4"')]
    assert 'id="bsUnclassifiedNote"' in section3
    assert "'Excludes ' + fmtInt(unclassified)" in js and 'with no tract classification' in js
    assert 'leaving out loans with none' in methods
    assert 'LMI Tracts (% of Total)' not in js
