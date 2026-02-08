"""
LendSight magazine-style PDF report generator (v2).

Builds a full ReportLab PDF story with:
  - Cover page (navy band + disclaimer)
  - Census demographics chart (full-width) + intro narrative (two-column)
  - Key findings callout (full-width)
  - Section 1: Race/Ethnicity table (full-width) + narrative (two-column)
  - Section 2: Income & Neighborhood 3 sub-tables + narratives
  - Section 3: Top 25 Lenders (landscape) + narrative (two-column)
  - Section 4: Market Concentration / HHI chart + table + narrative
  - Trends analysis (two-column)
  - Methods section (two-column)
  - Back matter (full-width)

All table column orders and widths are HARDCODED per the v2 spec.
"""

from io import BytesIO
from datetime import datetime

import pandas as pd
from reportlab.platypus import (
    Spacer, NextPageTemplate, PageBreak, CondPageBreak, Paragraph,
    KeepTogether,
)
from reportlab.lib.units import inch

from justdata.shared.pdf.base_report import (
    MagazineDocTemplate, build_cover_page, USABLE_WIDTH, L_USABLE_WIDTH,
)
from justdata.shared.pdf.styles import (
    HEADING_1, HEADING_2, BODY_TEXT, BODY_TEXT_SMALL, METHODS_TEXT,
    SOURCE_CAPTION, TABLE_CAPTION, AI_LABEL, LENDER_NAME_STYLE,
    TABLE_HEADER_TEXT, TABLE_CELL_TEXT,
    NAVY,
)
from justdata.shared.pdf.components import (
    section_header, build_data_table, build_key_findings,
    build_source_caption, keep_together_block,
    ai_narrative_to_flowables, narrative_paragraphs,
)
from justdata.apps.lendsight.pdf_charts import (
    render_census_demographics_chart, render_hhi_chart, chart_to_image,
)


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------
def _df_to_dicts(df_or_list):
    """Convert DataFrame or list-of-dicts to list of dicts."""
    if df_or_list is None:
        return []
    if isinstance(df_or_list, pd.DataFrame):
        if df_or_list.empty:
            return []
        return df_or_list.to_dict('records')
    if isinstance(df_or_list, list):
        return df_or_list
    return []


def _fmt_val(val, is_total_row=False):
    """Format a value for table display."""
    if val is None or val == '':
        return ''
    if isinstance(val, (int, float)):
        if is_total_row or abs(val) >= 1000:
            return f'{int(val):,}' if val == int(val) else f'{val:,.0f}'
        if isinstance(val, float):
            return f'{val:.1f}' if val != int(val) else str(int(val))
        return f'{val:,}'
    return str(val)


def _get_year_cols(row_dict):
    """Extract year column names from a data row, sorted ascending."""
    skip_keys = {'Metric', 'Population Share (%)', 'Change', 'Change Over Time',
                 'Loan Purpose', 'loan_purpose', 'Lender Name', 'Lender Type',
                 'Total Loans', 'LMIB', 'LMICT', 'MMCT', 'LMIB (%)', 'LMICT (%)', 'MMCT (%)'}
    year_cols = []
    for k in row_dict.keys():
        if k in skip_keys:
            continue
        # Also skip race % columns
        if '(%)' in str(k) or 'Hispanic' in str(k) or 'Black' in str(k) or \
           'White' in str(k) or 'Asian' in str(k) or 'Native' in str(k) or \
           'Multi' in str(k):
            continue
        # Check if it looks like a year
        try:
            yr = int(str(k).strip())
            if 2000 <= yr <= 2030:
                year_cols.append(str(k))
        except (ValueError, TypeError):
            pass
    return sorted(year_cols)


def _find_change_col(row_dict):
    """Find the change column name in a data row."""
    for k in row_dict.keys():
        kl = str(k).lower()
        if 'change' in kl:
            return k
    return None


def _find_pop_share_col(row_dict):
    """Find the population share column name in a data row."""
    for k in row_dict.keys():
        kl = str(k).lower()
        if 'population' in kl and 'share' in kl:
            return k
    return None


def _compute_col_widths(metric_width, pop_share_width, year_col_width, change_width, n_years):
    """Compute column widths list for standard section tables."""
    widths = [metric_width, pop_share_width]
    widths.extend([year_col_width] * n_years)
    widths.append(change_width)
    return widths


def _build_col_order(year_cols, pop_share_col, change_col):
    """Build column order: Metric | Pop Share | years... | Change."""
    order = ['Metric']
    if pop_share_col:
        order.append(pop_share_col)
    order.extend(year_cols)
    if change_col:
        order.append(change_col)
    return order


def _sort_rows(data_rows, row_order):
    """Sort data rows according to specified row order by Metric column."""
    if not row_order or not data_rows:
        return data_rows

    ordered = []
    remaining = list(data_rows)

    for target in row_order:
        target_lower = target.lower()
        for row in remaining:
            metric = str(row.get('Metric', '')).lower()
            if target_lower in metric or metric in target_lower:
                ordered.append(row)
                remaining.remove(row)
                break

    # Append any remaining rows not in the order
    ordered.extend(remaining)
    return ordered


def _adaptive_year_col_width(n_years, base=0.65):
    """Adjust year column width based on number of years (spec Section 6.1)."""
    width_map = {2: 1.0, 3: 0.85, 4: 0.75, 5: 0.65, 6: 0.55}
    return width_map.get(n_years, base) * inch


# ---------------------------------------------------------------------------
# Per-table builders (v2 spec Section 6)
# ---------------------------------------------------------------------------
SECTION1_ROW_ORDER = [
    'Total Loans', 'Hispanic', 'Black', 'White', 'Asian',
    'Native American', 'Hawaiian/Pacific Islander', 'Multi-Racial',
]

SECTION2_T1_ROW_ORDER = [
    'Total Loans', 'Low to Moderate Income Borrowers',
    'Low Income Borrowers', 'Moderate Income Borrowers',
    'Middle Income Borrowers', 'Upper Income Borrowers',
]

SECTION2_T2_ROW_ORDER = [
    'Total Loans', 'Low to Moderate Income Census Tracts',
    'Low Income Census Tracts', 'Moderate Income Census Tracts',
    'Middle Income Census Tracts', 'Upper Income Census Tracts',
]

SECTION2_T3_ROW_ORDER = [
    'Total Loans', 'Majority Minority Census Tracts',
    'Low Minority Census Tracts', 'Moderate Minority Census Tracts',
    'Middle Minority Census Tracts', 'High Minority Census Tracts',
]

HHI_ROW_ORDER = ['All Loans', 'Home Purchase', 'Refinance', 'Home Equity']


def _build_standard_table(data, row_order, metric_width_inches,
                          pop_share_inches=0.7, year_col_default=0.65,
                          change_inches=0.65):
    """
    Build a standard section table (Sections 1, 2) with hardcoded column order.
    Returns (table_flowable, has_data).
    """
    rows = _df_to_dicts(data)
    if not rows:
        return Spacer(1, 0), False

    # Detect columns from data
    sample = rows[0]
    year_cols = _get_year_cols(sample)
    change_col = _find_change_col(sample)
    pop_share_col = _find_pop_share_col(sample)
    n_years = len(year_cols)

    # Build column order
    col_order = _build_col_order(year_cols, pop_share_col, change_col)

    # Build display headers
    header_labels = ['Metric']
    if pop_share_col:
        header_labels.append('Pop Share (%)')
    header_labels.extend(year_cols)
    if change_col:
        header_labels.append('Change')

    # Calculate widths
    year_w = _adaptive_year_col_width(n_years, year_col_default)
    widths = [metric_width_inches * inch]
    if pop_share_col:
        widths.append(pop_share_inches * inch)
    widths.extend([year_w] * n_years)
    if change_col:
        widths.append(change_inches * inch)

    # Sort rows per spec
    sorted_rows = _sort_rows(rows, row_order)

    # Format values
    for row in sorted_rows:
        metric = str(row.get('Metric', '')).lower()
        is_total = 'total' in metric
        for col in col_order:
            if col == 'Metric':
                continue
            val = row.get(col, '')
            row[col] = _fmt_val(val, is_total_row=is_total)

    table = build_data_table(
        sorted_rows, col_order, widths,
        header_labels=header_labels,
        use_paragraph_col0=True,
        has_total_row=True,
    )

    return table, True


def _build_section1_table(data):
    """Build Section 1: Race & Ethnicity table."""
    return _build_standard_table(data, SECTION1_ROW_ORDER, metric_width_inches=2.0)


def _build_section2_income_borrowers_table(data):
    """Build Section 2, Table 1: Lending by Borrower Income."""
    return _build_standard_table(data, SECTION2_T1_ROW_ORDER,
                                 metric_width_inches=2.4, pop_share_inches=0.6,
                                 year_col_default=0.6, change_inches=0.6)


def _build_section2_income_tracts_table(data):
    """Build Section 2, Table 2: Lending to Census Tracts by Income."""
    return _build_standard_table(data, SECTION2_T2_ROW_ORDER,
                                 metric_width_inches=2.6, pop_share_inches=0.55,
                                 year_col_default=0.55, change_inches=0.55)


def _build_section2_minority_tracts_table(data):
    """Build Section 2, Table 3: Lending to Census Tracts by Minority Population."""
    return _build_standard_table(data, SECTION2_T3_ROW_ORDER,
                                 metric_width_inches=2.6, pop_share_inches=0.55,
                                 year_col_default=0.55, change_inches=0.55)


def _build_top_lenders_table(data):
    """
    Build Section 3: Top 25 Lenders table (landscape).
    CRITICAL: Cap at 25 lenders, hardcoded column order.
    """
    rows = _df_to_dicts(data)
    if not rows:
        return Spacer(1, 0), False

    # Sort by Total Loans descending, cap at 25
    rows = sorted(rows, key=lambda x: float(x.get('Total Loans', 0) or 0), reverse=True)[:25]

    # Detect which columns exist in data
    # Hardcoded column order per v2 spec Section 6.5
    all_possible_cols = [
        'Lender Name', 'Lender Type', 'Total Loans',
        'Hispanic (%)', 'Black (%)', 'White (%)', 'Asian (%)',
        'Native American (%)', 'Multi-Racial (%)',
        'LMIB (%)', 'LMICT (%)', 'MMCT (%)',
    ]
    all_display_headers = [
        'Lender Name', 'Type', 'Total', 'Hispanic', 'Black', 'White',
        'Asian', 'Native Am.', 'Multi-Racial', 'LMIB', 'LMICT', 'MMCT',
    ]
    all_widths = [
        2.2 * inch, 0.6 * inch, 0.5 * inch,
        0.6 * inch, 0.55 * inch, 0.55 * inch, 0.55 * inch,
        0.6 * inch, 0.7 * inch,
        0.5 * inch, 0.5 * inch, 0.5 * inch,
    ]

    # Filter to columns that actually exist in data
    sample = rows[0]
    col_order = []
    display_headers = []
    widths = []
    for col, header, w in zip(all_possible_cols, all_display_headers, all_widths):
        if col in sample:
            col_order.append(col)
            display_headers.append(header)
            widths.append(w)

    if not col_order:
        return Spacer(1, 0), False

    # Format values and use Paragraph for lender names
    from reportlab.platypus import Table
    from justdata.shared.pdf.styles import build_table_style

    header_row = [Paragraph(str(h), TABLE_HEADER_TEXT) for h in display_headers]
    table_data = [header_row]

    for row in rows:
        cells = []
        for i, col in enumerate(col_order):
            val = row.get(col, '')
            if val is None:
                val = ''
            if col == 'Lender Name':
                # Use Paragraph for word wrapping
                cells.append(Paragraph(str(val), LENDER_NAME_STYLE))
            elif col == 'Total Loans':
                cells.append(_fmt_val(val, is_total_row=True))
            else:
                cells.append(str(val))
        table_data.append(cells)

    num_rows = len(table_data)
    table = Table(table_data, colWidths=widths, repeatRows=1, hAlign='LEFT')
    table.setStyle(build_table_style(num_rows=num_rows))

    return table, True


def _build_hhi_table(data):
    """Build Section 4: HHI table."""
    rows = _df_to_dicts(data)
    if not rows:
        return Spacer(1, 0), False

    sample = rows[0]
    year_cols = sorted([k for k in sample.keys()
                        if k not in ('Loan Purpose', 'loan_purpose')])

    # Filter to only year-like columns
    filtered_years = []
    for k in year_cols:
        try:
            yr = int(str(k).strip())
            if 2000 <= yr <= 2030:
                filtered_years.append(k)
        except (ValueError, TypeError):
            pass
    year_cols = filtered_years

    if not year_cols:
        return Spacer(1, 0), False

    col_order = ['Loan Purpose'] + year_cols
    header_labels = ['Loan Purpose'] + year_cols
    widths = [2.0 * inch] + [0.8 * inch] * len(year_cols)

    # Sort rows
    sorted_rows = _sort_rows(rows, HHI_ROW_ORDER)

    # Format HHI values as integers
    for row in sorted_rows:
        for col in year_cols:
            val = row.get(col, '')
            try:
                row[col] = f'{int(float(val)):,}' if val else ''
            except (ValueError, TypeError):
                row[col] = str(val) if val else ''

    table = build_data_table(
        sorted_rows, col_order, widths,
        header_labels=header_labels,
        use_paragraph_col0=True,
    )

    return table, True


# ---------------------------------------------------------------------------
# Narrative helper
# ---------------------------------------------------------------------------
def _add_ai_narrative(story, ai, key):
    """Add AI narrative section with label, switching to two-column."""
    text = ai.get(key, '')
    if not text or not isinstance(text, str) or not text.strip():
        return
    story.append(NextPageTemplate('two_column'))
    story.append(PageBreak())
    story.append(Paragraph('AI Analysis', AI_LABEL))
    story.extend(ai_narrative_to_flowables(text))


# ---------------------------------------------------------------------------
# Main PDF generator (v2 spec Section 11 story assembly)
# ---------------------------------------------------------------------------
def generate_lendsight_pdf(report_data, metadata, ai_insights=None):
    """
    Generate a magazine-style PDF report and return it as a BytesIO buffer.
    """
    ai = ai_insights or {}
    buf = BytesIO()

    doc = MagazineDocTemplate(
        buf,
        app_name='LendSight',
        footer_source='Source: HMDA, U.S. Census Bureau, American Community Survey',
    )

    story = []

    # ------------------------------------------------------------------
    # Prepare metadata
    # ------------------------------------------------------------------
    counties = metadata.get('counties', [])
    if isinstance(counties, dict):
        counties = list(counties.values()) or list(counties.keys())
    elif not isinstance(counties, (list, tuple)):
        counties = [counties] if counties else []

    county_display = ', '.join(str(c) for c in counties[:3])
    if len(counties) > 3:
        county_display += f' (+{len(counties) - 3} more)'

    years = metadata.get('years', '')
    if isinstance(years, (list, tuple)):
        year_strs = sorted(str(y) for y in years)
        date_range = f'{year_strs[0]} – {year_strs[-1]}' if len(year_strs) > 1 else year_strs[0] if year_strs else ''
    else:
        date_range = str(years) if years else ''

    # ==================================================================
    # PAGE 1: COVER
    # ==================================================================
    story.extend(build_cover_page(
        title='Mortgage Lending Analysis',
        subtitle=county_display,
        date_range=date_range,
        metadata=metadata,
    ))

    # ==================================================================
    # PAGES 2-3: DEMOGRAPHICS CHART + INTRO NARRATIVE
    # ==================================================================
    # Cover already sets NextPageTemplate('full_width') + PageBreak
    census_data = metadata.get('census_data', {}) or report_data.get('census_data', {})

    census_chart_buf = render_census_demographics_chart(census_data, counties)
    census_img = chart_to_image(census_chart_buf, width=USABLE_WIDTH, height_inches=3.5)

    if census_img:
        story.append(section_header('Population Demographics'))
        story.append(Spacer(1, 6))
        story.append(census_img)
        story.append(Spacer(1, 4))
        story.append(build_source_caption(
            'Source: U.S. Census Bureau — 2010 Decennial Census, 2020 Decennial Census, American Community Survey'
        ))

    # Intro narrative (two-column)
    intro_text = ai.get('intro_paragraph', '') or ai.get('demographic_overview_intro', '') or ai.get('introduction', '')
    if intro_text and isinstance(intro_text, str) and intro_text.strip():
        story.append(NextPageTemplate('two_column'))
        story.append(PageBreak())
        story.append(Paragraph('AI Analysis', AI_LABEL))
        story.extend(ai_narrative_to_flowables(intro_text))

    # ==================================================================
    # KEY FINDINGS (full-width)
    # ==================================================================
    key_findings = ai.get('key_findings', '')
    if key_findings and isinstance(key_findings, str) and key_findings.strip():
        story.append(NextPageTemplate('full_width'))
        story.append(PageBreak())
        story.append(section_header('Key Findings'))
        story.append(Spacer(1, 6))
        story.append(build_key_findings(key_findings))

    # ==================================================================
    # SECTION 1: RACE & ETHNICITY
    # ==================================================================
    demo_df = report_data.get('demographic_overview')
    s1_table, s1_has_data = _build_section1_table(demo_df)

    if s1_has_data:
        story.append(NextPageTemplate('full_width'))
        story.append(PageBreak())
        story.append(section_header('Section 1: Loans by Race and Ethnicity'))
        story.append(Spacer(1, 6))
        story.append(s1_table)
        story.append(Paragraph('Source: Home Mortgage Disclosure Act (HMDA) data', TABLE_CAPTION))

    # Section 1 narrative
    _add_ai_narrative(story, ai, 'demographic_overview_discussion')

    # ==================================================================
    # SECTION 2: INCOME & NEIGHBORHOOD (3 sub-tables)
    # ==================================================================

    # --- Sub-table 1: Borrower Income ---
    income_borrowers = report_data.get('income_borrowers')
    s2t1, s2t1_has = _build_section2_income_borrowers_table(income_borrowers)

    if s2t1_has:
        story.append(NextPageTemplate('full_width'))
        story.append(PageBreak())
        story.append(section_header('Section 2: Income & Neighborhood Analysis'))
        story.append(Spacer(1, 8))
        story.append(section_header('Lending by Borrower Income', level=2))
        story.append(Spacer(1, 4))
        story.append(s2t1)
        story.append(Paragraph('Source: HMDA data', TABLE_CAPTION))

    _add_ai_narrative(story, ai, 'income_borrowers_discussion')

    # --- Sub-table 2: Census Tract Income ---
    income_tracts = report_data.get('income_tracts')
    s2t2, s2t2_has = _build_section2_income_tracts_table(income_tracts)

    if s2t2_has:
        story.append(NextPageTemplate('full_width'))
        story.append(PageBreak())
        story.append(section_header('Lending to Census Tracts by Income', level=2))
        story.append(Spacer(1, 4))
        story.append(s2t2)
        story.append(Paragraph('Source: HMDA data', TABLE_CAPTION))

    _add_ai_narrative(story, ai, 'income_tracts_discussion')

    # --- Sub-table 3: Minority Tracts ---
    minority_tracts = report_data.get('minority_tracts')
    s2t3, s2t3_has = _build_section2_minority_tracts_table(minority_tracts)

    if s2t3_has:
        story.append(NextPageTemplate('full_width'))
        story.append(PageBreak())
        story.append(section_header('Lending to Census Tracts by Minority Population', level=2))
        story.append(Spacer(1, 4))
        story.append(s2t3)
        story.append(Paragraph('Source: HMDA data', TABLE_CAPTION))

    _add_ai_narrative(story, ai, 'minority_tracts_discussion')

    # Combined Section 2 overview (if present, stays in two-column)
    income_neigh_disc = ai.get('income_neighborhood_discussion', '')
    if income_neigh_disc and isinstance(income_neigh_disc, str) and income_neigh_disc.strip():
        story.append(Spacer(1, 8))
        story.append(section_header('Income & Neighborhood Overview', level=2))
        story.extend(ai_narrative_to_flowables(income_neigh_disc))

    # ==================================================================
    # SECTION 3: TOP LENDERS (LANDSCAPE)
    # ==================================================================
    lenders_df = report_data.get('top_lenders_detailed')
    s3_table, s3_has = _build_top_lenders_table(lenders_df)

    if s3_has:
        story.append(NextPageTemplate('landscape'))
        story.append(PageBreak())
        story.append(section_header('Section 3: Top Mortgage Lenders'))
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            'The table below shows the top 25 lenders by total loan volume. '
            'The full lender list is available in the Excel export.',
            BODY_TEXT_SMALL,
        ))
        story.append(Spacer(1, 6))
        story.append(s3_table)
        story.append(Paragraph(
            'Source: HMDA data. Full lender list available in Excel export.',
            TABLE_CAPTION,
        ))

    # Section 3 narrative — back to portrait two-column
    _add_ai_narrative(story, ai, 'top_lenders_detailed_discussion')

    # ==================================================================
    # SECTION 4: MARKET CONCENTRATION
    # ==================================================================
    market_conc = report_data.get('market_concentration', [])
    if isinstance(market_conc, pd.DataFrame):
        market_conc = market_conc.to_dict('records') if not market_conc.empty else []

    hhi_chart_buf = render_hhi_chart(market_conc)
    hhi_img = chart_to_image(hhi_chart_buf, width_inches=6.0, height_inches=3.0)

    s4_table, s4_has = _build_hhi_table(market_conc)

    if hhi_img or s4_has:
        story.append(NextPageTemplate('full_width'))
        story.append(PageBreak())
        story.append(section_header('Section 4: Market Concentration'))
        story.append(Spacer(1, 6))

        if hhi_img:
            story.append(hhi_img)
            story.append(Spacer(1, 4))
            story.append(Paragraph(
                'Source: HMDA data. HHI thresholds: &lt;1500 = Competitive, '
                '1500-2500 = Moderate, &gt;2500 = Concentrated',
                TABLE_CAPTION,
            ))

        if s4_has:
            story.append(Spacer(1, 8))
            story.append(s4_table)
            story.append(Paragraph('Source: HMDA data', TABLE_CAPTION))

    # Section 4 narrative
    _add_ai_narrative(story, ai, 'market_concentration_discussion')

    # ==================================================================
    # TRENDS ANALYSIS (stays in two-column if already there)
    # ==================================================================
    trends_text = ai.get('trends_analysis', '')
    if trends_text and isinstance(trends_text, str) and trends_text.strip():
        story.append(CondPageBreak(2 * inch))
        story.append(section_header('Trends Analysis'))
        story.append(Spacer(1, 6))
        story.extend(ai_narrative_to_flowables(trends_text))

    # ==================================================================
    # METHODS (two-column)
    # ==================================================================
    story.append(CondPageBreak(2 * inch))
    story.append(section_header('Methodology'))
    story.append(Spacer(1, 6))

    methods_paras = [
        "This report analyzes Home Mortgage Disclosure Act (HMDA) data "
        "collected under Regulation C. HMDA requires most mortgage lenders "
        "to report detailed information about their lending activity, "
        "including the disposition of loan applications, loan amounts, "
        "borrower demographics, property location, and lender information.",

        "The Herfindahl-Hirschman Index (HHI) measures market concentration. "
        "An HHI below 1,500 indicates a competitive market, 1,500 to 2,500 "
        "indicates moderate concentration, and above 2,500 indicates high "
        "concentration. HHI is calculated as the sum of squared market "
        "shares of all lenders in the market.",

        "Census demographic data is drawn from the U.S. Census Bureau's "
        "2010 and 2020 Decennial Census programs and the American Community "
        "Survey (ACS) 5-year estimates. Population percentages are calculated "
        "as shares of total population for each geographic area.",

        "Income classifications follow HUD definitions: Low-to-Moderate "
        "Income (LMI) borrowers have income below 80% of area median income. "
        "LMI census tracts have median family income below 80% of the area "
        "median. Majority-minority census tracts have more than 50% "
        "minority population.",

        "AI-generated narrative analysis is produced by Anthropic's Claude "
        "language model to provide contextual interpretation of the data. "
        "All quantitative data in tables and charts is derived directly from "
        "HMDA and Census source data.",
    ]
    for para in methods_paras:
        story.append(Paragraph(para, BODY_TEXT))

    # ==================================================================
    # ABOUT / BACK MATTER (full-width)
    # ==================================================================
    story.append(NextPageTemplate('full_width'))
    story.append(PageBreak())
    story.append(section_header('About This Report'))
    story.append(Spacer(1, 6))

    about_text = (
        f"This report was generated by NCRC LendSight on "
        f"{datetime.now().strftime('%B %d, %Y')}. "
        f"LendSight is part of the JustData platform developed by the "
        f"National Community Reinvestment Coalition (NCRC) to provide "
        f"data-driven insights into mortgage lending patterns and "
        f"community investment."
    )
    story.append(Paragraph(about_text, BODY_TEXT))

    story.append(Spacer(1, 12))
    story.append(Paragraph(
        'National Community Reinvestment Coalition (NCRC)', HEADING_2,
    ))
    story.append(Paragraph(
        '740 15th Street NW, Suite 400, Washington, DC 20005', BODY_TEXT,
    ))
    story.append(Paragraph(
        'www.ncrc.org | justdata.org', BODY_TEXT,
    ))

    # ------------------------------------------------------------------
    # Build the PDF
    # ------------------------------------------------------------------
    doc.build(story)
    buf.seek(0)
    return buf
