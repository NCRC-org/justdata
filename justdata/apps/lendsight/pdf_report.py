"""
LendSight magazine-style PDF report generator (v3 compact layout).

Generates a compact ~7-page PDF with:
  Page 1: Cover (gradient with logo)
  Page 2: Census chart + Key Findings + mini trend/gap charts
  Page 3: Section 1 table + inline AI narrative + Section 2a table
  Page 4: Section 2 AI + mini charts + Section 2b + 2c tables + AI
  Page 5: Top 25 Lenders (landscape)
  Page 6: Lender AI + mini charts + HHI table + narrative
  Page 7: Trends + Methods + About

Key technique: Inline two-column narratives via Table flowables
instead of switching to two_column PageTemplate (which forced page breaks).
"""

from io import BytesIO
from datetime import datetime

import pandas as pd
from reportlab.platypus import (
    Spacer, NextPageTemplate, PageBreak, CondPageBreak, Paragraph,
    KeepTogether, Table, TableStyle as TS, Image, HRFlowable,
)
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY, TA_CENTER

from justdata.shared.pdf.base_report import (
    MagazineDocTemplate, USABLE_WIDTH, L_USABLE_WIDTH,
)
from justdata.shared.pdf.styles import (
    HEADING_2, HEADING_3, BODY_TEXT, BODY_TEXT_SMALL,
    SOURCE_CAPTION, TABLE_CAPTION, LENDER_NAME_STYLE,
    TABLE_HEADER_TEXT, TABLE_CELL_TEXT,
    NAVY, RULE_COLOR, BODY_FONT, BODY_FONT_BOLD, BODY_FONT_ITALIC,
    HEADLINE_FONT_BOLD, HEADER_BG, ALT_ROW_BG, MEDIUM_GRAY,
    build_table_style, markdown_to_reportlab,
)
from justdata.shared.pdf.components import (
    build_data_table, build_key_findings,
    build_source_caption,
    ai_narrative_to_flowables,
)
from justdata.apps.lendsight.pdf_charts import (
    render_census_demographics_chart, render_hhi_chart,
    render_trend_line_chart, render_gap_chart,
    render_lender_bars_chart, render_income_share_chart,
    chart_to_image,
)


# ---------------------------------------------------------------------------
# Compact styles (local to this module for dense layout)
# ---------------------------------------------------------------------------
_COMPACT_BODY = ParagraphStyle(
    'CompactBody',
    fontName='Helvetica',
    fontSize=7.5,
    leading=11,
    textColor=HexColor('#333333'),
    alignment=TA_JUSTIFY,
    spaceAfter=5,
)

_AI_TAG = ParagraphStyle(
    'AITag',
    fontName='Helvetica-Oblique',
    fontSize=6,
    leading=8,
    textColor=HexColor('#aaaaaa'),
    spaceAfter=3,
)

_COMPACT_CAPTION = ParagraphStyle(
    'CompactCaption',
    fontName='Helvetica-Oblique',
    fontSize=6,
    leading=8,
    textColor=HexColor('#999999'),
    spaceAfter=4,
)

_COMPACT_FINDING = ParagraphStyle(
    'CompactFinding',
    fontName='Helvetica',
    fontSize=7,
    leading=10,
    textColor=HexColor('#333333'),
    alignment=TA_LEFT,
    spaceAfter=4,
    leftIndent=8,
)

_COMPACT_H1 = ParagraphStyle(
    'CompactH1',
    fontName=HEADLINE_FONT_BOLD,
    fontSize=15,
    leading=19,
    textColor=NAVY,
    spaceBefore=6,
    spaceAfter=6,
)

_COMPACT_H2 = ParagraphStyle(
    'CompactH2',
    fontName=HEADLINE_FONT_BOLD,
    fontSize=11,
    leading=14,
    textColor=NAVY,
    spaceBefore=6,
    spaceAfter=4,
)

_INLINE_NARRATIVE = ParagraphStyle(
    'InlineNarrative',
    fontName='Helvetica',
    fontSize=7,
    leading=10,
    textColor=HexColor('#333333'),
    alignment=TA_JUSTIFY,
    spaceAfter=4,
)

_METHODS_COMPACT = ParagraphStyle(
    'MethodsCompact',
    fontName='Helvetica',
    fontSize=7,
    leading=10,
    textColor=HexColor('#666666'),
    alignment=TA_JUSTIFY,
    spaceAfter=4,
)


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------
def _h1(text):
    """Compact section heading (15pt)."""
    return Paragraph(text, _COMPACT_H1)


def _h2(text):
    """Compact sub-heading (11pt)."""
    return Paragraph(text, _COMPACT_H2)


def _caption(text):
    """Compact caption."""
    return Paragraph(text, _COMPACT_CAPTION)


def _ai_tag():
    """AI-generated narrative label."""
    return Paragraph('AI-generated narrative \u2014 Anthropic Claude', _AI_TAG)


def _inline_two_col(text, style=None):
    """
    Create an inline two-column layout from narrative text.
    Uses a Table with two cells instead of switching to two_column PageTemplate.
    """
    if not text or not isinstance(text, str) or not text.strip():
        return Spacer(1, 0)

    style = style or _COMPACT_BODY
    paras = ai_narrative_to_flowables(text, style=style)
    if not paras:
        return Spacer(1, 0)

    # Split paragraphs roughly in half by cumulative text length
    lengths = []
    for p in paras:
        txt = getattr(p, 'text', '') or ''
        lengths.append(len(txt))
    total = sum(lengths)
    target = total / 2
    cumulative = 0
    split_idx = 1
    for i, length in enumerate(lengths):
        cumulative += length
        if cumulative >= target:
            split_idx = i + 1
            break
    split_idx = max(1, min(split_idx, len(paras) - 1)) if len(paras) > 1 else len(paras)

    left_paras = paras[:split_idx]
    right_paras = paras[split_idx:]

    gap = 14  # points
    col_w = (USABLE_WIDTH - gap) / 2

    t = Table(
        [[left_paras, right_paras]],
        colWidths=[col_w, col_w],
    )
    t.setStyle(TS([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (0, 0), 0),
        ('RIGHTPADDING', (0, 0), (0, 0), gap // 2),
        ('LEFTPADDING', (1, 0), (1, 0), gap // 2),
        ('RIGHTPADDING', (1, 0), (1, 0), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    return t


def _side_by_side(left_flowables, right_flowables, gap=14):
    """Place two groups of flowables side by side using a Table."""
    col_w = (USABLE_WIDTH - gap) / 2
    t = Table(
        [[left_flowables, right_flowables]],
        colWidths=[col_w, col_w],
    )
    t.setStyle(TS([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (0, 0), 0),
        ('RIGHTPADDING', (0, 0), (0, 0), gap // 2),
        ('LEFTPADDING', (1, 0), (1, 0), gap // 2),
        ('RIGHTPADDING', (1, 0), (1, 0), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    return t


def _side_by_side_uneven(left_flowables, right_flowables, left_pct=0.55, gap=14):
    """Place flowable groups side by side with uneven column widths."""
    left_w = USABLE_WIDTH * left_pct - gap // 2
    right_w = USABLE_WIDTH * (1 - left_pct) - gap // 2
    t = Table(
        [[left_flowables, right_flowables]],
        colWidths=[left_w, right_w],
    )
    t.setStyle(TS([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    return t


def _mini_img(buf, aspect_w=3.3, aspect_h=1.8):
    """Create an Image flowable sized for half-width (side-by-side) layout."""
    if buf is None:
        return None
    gap = 14
    col_w = (USABLE_WIDTH - gap) / 2
    h = col_w * (aspect_h / aspect_w)
    return chart_to_image(buf, width=col_w, height=h)


def _compact_key_findings(findings_text):
    """Build compact key findings callout box with smaller text."""
    if not findings_text:
        return Spacer(1, 0)

    import re
    lines = findings_text.strip().split('\n')
    finding_flowables = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        line = re.sub(r'^[\-\*•]\s*', '', line)
        line = re.sub(r'^\d+\.\s*', '', line)
        line = markdown_to_reportlab(line)
        if line:
            finding_flowables.append(
                Paragraph(f'&bull; {line}', _COMPACT_FINDING)
            )

    if not finding_flowables:
        return Spacer(1, 0)

    callout = Table(
        [[finding_flowables]],
        colWidths=[USABLE_WIDTH - 16],
        style=TS([
            ('BACKGROUND', (0, 0), (-1, -1), HexColor('#f0f7ff')),
            ('LEFTPADDING', (0, 0), (-1, -1), 14),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LINEBEFORE', (0, 0), (0, -1), 3, NAVY),
        ]),
    )
    return callout


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
        if '(%)' in str(k) or 'Hispanic' in str(k) or 'Black' in str(k) or \
           'White' in str(k) or 'Asian' in str(k) or 'Native' in str(k) or \
           'Multi' in str(k):
            continue
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
        if 'change' in str(k).lower():
            return k
    return None


def _find_pop_share_col(row_dict):
    """Find the population share column name in a data row."""
    for k in row_dict.keys():
        kl = str(k).lower()
        if 'population' in kl and 'share' in kl:
            return k
    return None


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
    ordered.extend(remaining)
    return ordered


def _adaptive_year_col_width(n_years, base=0.65):
    """Adjust year column width based on number of years."""
    width_map = {2: 1.0, 3: 0.85, 4: 0.75, 5: 0.65, 6: 0.55}
    return width_map.get(n_years, base) * inch


# ---------------------------------------------------------------------------
# Per-table builders
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
    """Build a standard section table with hardcoded column order."""
    rows = _df_to_dicts(data)
    if not rows:
        return Spacer(1, 0), False

    sample = rows[0]
    year_cols = _get_year_cols(sample)
    change_col = _find_change_col(sample)
    pop_share_col = _find_pop_share_col(sample)
    n_years = len(year_cols)

    col_order = _build_col_order(year_cols, pop_share_col, change_col)

    header_labels = ['Metric']
    if pop_share_col:
        header_labels.append('Pop.')
    header_labels.extend(year_cols)
    if change_col:
        header_labels.append('Chg')

    year_w = _adaptive_year_col_width(n_years, year_col_default)
    widths = [metric_width_inches * inch]
    if pop_share_col:
        widths.append(pop_share_inches * inch)
    widths.extend([year_w] * n_years)
    if change_col:
        widths.append(change_inches * inch)

    sorted_rows = _sort_rows(rows, row_order)

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
    return _build_standard_table(data, SECTION1_ROW_ORDER, metric_width_inches=2.0)


def _build_section2_income_borrowers_table(data):
    return _build_standard_table(data, SECTION2_T1_ROW_ORDER,
                                 metric_width_inches=2.4, pop_share_inches=0.6,
                                 year_col_default=0.6, change_inches=0.6)


def _build_section2_income_tracts_table(data):
    return _build_standard_table(data, SECTION2_T2_ROW_ORDER,
                                 metric_width_inches=2.6, pop_share_inches=0.55,
                                 year_col_default=0.55, change_inches=0.55)


def _build_section2_minority_tracts_table(data):
    return _build_standard_table(data, SECTION2_T3_ROW_ORDER,
                                 metric_width_inches=2.6, pop_share_inches=0.55,
                                 year_col_default=0.55, change_inches=0.55)


def _build_top_lenders_table(data):
    """Build Section 3: Top 25 Lenders table (landscape)."""
    rows = _df_to_dicts(data)
    if not rows:
        return Spacer(1, 0), False

    rows = sorted(rows, key=lambda x: float(x.get('Total Loans', 0) or 0), reverse=True)[:25]

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

    header_row = [Paragraph(str(h), TABLE_HEADER_TEXT) for h in display_headers]
    table_data = [header_row]

    for row in rows:
        cells = []
        for col in col_order:
            val = row.get(col, '')
            if val is None:
                val = ''
            if col == 'Lender Name':
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
    year_cols = []
    for k in sorted(sample.keys()):
        if k in ('Loan Purpose', 'loan_purpose'):
            continue
        try:
            yr = int(str(k).strip())
            if 2000 <= yr <= 2030:
                year_cols.append(k)
        except (ValueError, TypeError):
            pass

    if not year_cols:
        return Spacer(1, 0), False

    col_order = ['Loan Purpose'] + year_cols
    header_labels = ['Loan Purpose'] + year_cols
    widths = [2.0 * inch] + [0.8 * inch] * len(year_cols)

    sorted_rows = _sort_rows(rows, HHI_ROW_ORDER)

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
# Main PDF generator (compact v3 layout)
# ---------------------------------------------------------------------------
def generate_lendsight_pdf(report_data, metadata, ai_insights=None):
    """Generate a compact magazine-style PDF report and return as BytesIO."""
    ai = ai_insights or {}
    buf = BytesIO()

    doc = MagazineDocTemplate(
        buf,
        app_name='LendSight',
        footer_source='Source: HMDA, U.S. Census Bureau, ACS',
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
        date_range = f'{year_strs[0]} \u2013 {year_strs[-1]}' if len(year_strs) > 1 else year_strs[0] if year_strs else ''
    else:
        date_range = str(years) if years else ''

    # Loan purpose for cover
    loan_purpose = metadata.get('loan_purpose', '')
    if isinstance(loan_purpose, list):
        loan_purpose = ', '.join(str(lp).replace('_', ' ').title() for lp in loan_purpose)
    loan_purpose_str = str(loan_purpose).replace('_', ' ').title() if loan_purpose else ''

    # Set cover attributes on the doc (read by _draw_cover canvas callback)
    doc.cover_title = 'Mortgage Lending\nAnalysis'
    doc.cover_subtitle = county_display
    doc.cover_date_range = date_range
    doc.cover_loan_purpose = loan_purpose_str

    # ==================================================================
    # PAGE 1: COVER
    # ==================================================================
    # Cover page background + text is drawn by _draw_cover callback.
    # We just need a minimal flowable to claim the page, then advance.
    story.append(Spacer(1, 1))
    story.append(NextPageTemplate('full_width'))
    story.append(PageBreak())

    # ==================================================================
    # PAGE 2: CENSUS CHART + KEY FINDINGS + MINI CHARTS
    # ==================================================================
    census_data = metadata.get('census_data', {}) or report_data.get('census_data', {})

    census_chart_buf = render_census_demographics_chart(census_data, counties)
    census_img = chart_to_image(census_chart_buf, width=USABLE_WIDTH, height_inches=2.8)

    if census_img:
        story.append(_h1('Population Demographics'))
        story.append(census_img)
        story.append(_caption(
            'Source: U.S. Census Bureau \u2014 2010 &amp; 2020 Decennial Census, American Community Survey'
        ))

    # Key findings
    key_findings = ai.get('key_findings', '')
    if key_findings and isinstance(key_findings, str) and key_findings.strip():
        story.append(Spacer(1, 4))
        story.append(_h1('Key Findings'))
        story.append(_compact_key_findings(key_findings))

    # Mini charts: Trend line and Gap chart side-by-side
    demo_df = report_data.get('demographic_overview')
    demo_data = _df_to_dicts(demo_df)

    trend_buf = render_trend_line_chart(demo_data)
    gap_buf = render_gap_chart(demo_data)

    trend_img = _mini_img(trend_buf)
    gap_img = _mini_img(gap_buf)

    if trend_img or gap_img:
        story.append(Spacer(1, 6))
        left = [trend_img] if trend_img else [Spacer(1, 1)]
        right = [gap_img] if gap_img else [Spacer(1, 1)]
        story.append(_side_by_side(left, right))

    # ==================================================================
    # PAGE 3: SECTION 1 TABLE + AI + SECTION 2A TABLE
    # ==================================================================
    story.append(CondPageBreak(3 * inch))

    # Section 1: Race & Ethnicity
    s1_table, s1_has_data = _build_section1_table(demo_df)
    if s1_has_data:
        story.append(_h1('Section 1: Race &amp; Ethnicity in Mortgage Lending'))
        story.append(s1_table)
        story.append(_caption('Source: Home Mortgage Disclosure Act (HMDA) data'))

    # Section 1 AI narrative (inline two-column)
    s1_narrative = ai.get('demographic_overview_discussion', '')
    if s1_narrative and isinstance(s1_narrative, str) and s1_narrative.strip():
        story.append(Spacer(1, 6))
        story.append(_ai_tag())
        story.append(_inline_two_col(s1_narrative))

    # Section 2 header + first sub-table (Borrower Income)
    income_borrowers = report_data.get('income_borrowers')
    s2t1, s2t1_has = _build_section2_income_borrowers_table(income_borrowers)

    if s2t1_has:
        story.append(Spacer(1, 8))
        story.append(_h2('Section 2: Income &amp; Neighborhood Analysis'))
        story.append(_h2('Lending by Borrower Income'))
        story.append(s2t1)
        story.append(_caption('Source: HMDA data'))

    # ==================================================================
    # PAGE 4: SECTION 2 AI + MINI CHARTS + SECTION 2B + 2C + AI
    # ==================================================================
    story.append(CondPageBreak(3 * inch))

    # Income borrowers AI narrative
    ib_narrative = ai.get('income_borrowers_discussion', '')
    if ib_narrative and isinstance(ib_narrative, str) and ib_narrative.strip():
        story.append(_ai_tag())
        story.append(_inline_two_col(ib_narrative))

    # Mini charts: Income Share and HHI side-by-side
    income_borrowers_data = _df_to_dicts(income_borrowers)
    income_share_buf = render_income_share_chart(income_borrowers_data)
    income_share_img = _mini_img(income_share_buf, aspect_w=3.3, aspect_h=1.5)

    market_conc = report_data.get('market_concentration', [])
    if isinstance(market_conc, pd.DataFrame):
        market_conc = market_conc.to_dict('records') if not market_conc.empty else []

    hhi_mini_buf = render_hhi_chart(market_conc)
    hhi_mini_img = _mini_img(hhi_mini_buf)

    if income_share_img or hhi_mini_img:
        story.append(Spacer(1, 6))
        left = [income_share_img] if income_share_img else [Spacer(1, 1)]
        right = [hhi_mini_img] if hhi_mini_img else [Spacer(1, 1)]
        story.append(_side_by_side(left, right))

    # Section 2b: Census Tract Income
    income_tracts = report_data.get('income_tracts')
    s2t2, s2t2_has = _build_section2_income_tracts_table(income_tracts)
    if s2t2_has:
        story.append(Spacer(1, 8))
        story.append(_h2('Lending to Census Tracts by Income'))
        story.append(s2t2)
        story.append(_caption('Source: HMDA data'))

    # Section 2c: Minority Tracts
    minority_tracts = report_data.get('minority_tracts')
    s2t3, s2t3_has = _build_section2_minority_tracts_table(minority_tracts)
    if s2t3_has:
        story.append(Spacer(1, 6))
        story.append(_h2('Lending to Census Tracts by Minority Population'))
        story.append(s2t3)
        story.append(_caption('Source: HMDA data'))

    # Combined Section 2 AI narrative
    s2_narrative_keys = ['income_tracts_discussion', 'minority_tracts_discussion',
                         'income_neighborhood_discussion']
    s2_narrative = ''
    for key in s2_narrative_keys:
        text = ai.get(key, '')
        if text and isinstance(text, str) and text.strip():
            s2_narrative = text
            break

    if s2_narrative:
        story.append(Spacer(1, 4))
        story.append(_ai_tag())
        story.append(_inline_two_col(s2_narrative))

    # ==================================================================
    # PAGE 5: TOP LENDERS (LANDSCAPE)
    # ==================================================================
    lenders_df = report_data.get('top_lenders_detailed')
    s3_table, s3_has = _build_top_lenders_table(lenders_df)

    if s3_has:
        story.append(NextPageTemplate('landscape'))
        story.append(PageBreak())
        story.append(_h1('Section 3: Top Mortgage Lenders'))
        story.append(Paragraph(
            'Top 25 lenders by total loan volume. Demographic columns show % of each '
            'lender\u2019s originations. Full lender list available in Excel export.',
            _COMPACT_CAPTION,
        ))
        story.append(Spacer(1, 4))
        story.append(s3_table)
        story.append(_caption('Source: HMDA data. Full lender list in Excel export.'))

    # ==================================================================
    # PAGE 6: LENDER AI + MINI CHARTS + HHI TABLE
    # ==================================================================
    story.append(NextPageTemplate('full_width'))
    story.append(PageBreak())

    # Lender AI narrative (inline two-column)
    lender_narrative = ai.get('top_lenders_detailed_discussion', '')
    if lender_narrative and isinstance(lender_narrative, str) and lender_narrative.strip():
        story.append(_ai_tag())
        story.append(_inline_two_col(lender_narrative))

    # Mini charts: Lender bars and HHI
    lender_data = _df_to_dicts(lenders_df)
    lender_bars_buf = render_lender_bars_chart(lender_data)
    lender_bars_img = _mini_img(lender_bars_buf, aspect_w=3.3, aspect_h=2.0)

    # Re-render HHI for this position (or reuse hhi_mini_img)
    hhi_chart_buf2 = render_hhi_chart(market_conc)
    hhi_img2 = _mini_img(hhi_chart_buf2)

    if lender_bars_img or hhi_img2:
        story.append(Spacer(1, 8))
        left = [lender_bars_img] if lender_bars_img else [Spacer(1, 1)]
        right = [hhi_img2] if hhi_img2 else [Spacer(1, 1)]
        story.append(_side_by_side(left, right))

    # HHI table + inline narrative
    s4_table, s4_has = _build_hhi_table(market_conc)
    hhi_narrative = ai.get('market_concentration_discussion', '')

    if s4_has or (hhi_narrative and isinstance(hhi_narrative, str) and hhi_narrative.strip()):
        story.append(Spacer(1, 8))
        story.append(_h2('Section 4: Market Concentration'))

    if s4_has and hhi_narrative and isinstance(hhi_narrative, str) and hhi_narrative.strip():
        # Side-by-side: table (55%) | narrative (45%)
        narrative_paras = ai_narrative_to_flowables(hhi_narrative, style=_INLINE_NARRATIVE)
        story.append(_side_by_side_uneven([s4_table], narrative_paras, left_pct=0.55))
        story.append(_caption(
            'Source: HMDA data. HHI &lt;1,500 = Competitive, '
            '1,500\u20132,500 = Moderate, &gt;2,500 = Concentrated'
        ))
    elif s4_has:
        story.append(s4_table)
        story.append(_caption('Source: HMDA data'))
    elif hhi_narrative:
        story.append(_ai_tag())
        story.append(_inline_two_col(hhi_narrative))

    # ==================================================================
    # PAGE 7: TRENDS + METHODS + ABOUT
    # ==================================================================
    story.append(CondPageBreak(3 * inch))

    # Trends Analysis
    trends_text = ai.get('trends_analysis', '')
    if trends_text and isinstance(trends_text, str) and trends_text.strip():
        story.append(_h1('Trends Analysis'))
        story.append(_ai_tag())
        story.append(_inline_two_col(trends_text))
        story.append(Spacer(1, 8))

    # Horizontal rule before Methods
    story.append(HRFlowable(
        width='100%', thickness=0.5, color=RULE_COLOR,
        spaceAfter=8, spaceBefore=4,
    ))

    # Methods
    story.append(_h1('Methodology'))

    methods_text = (
        "This report analyzes Home Mortgage Disclosure Act (HMDA) data "
        "collected under Regulation C. HMDA requires most mortgage lenders "
        "to report detailed information about lending activity, including "
        "loan disposition, amounts, borrower demographics, property location, "
        "and lender information.\n\n"

        "The Herfindahl-Hirschman Index (HHI) measures market concentration. "
        "Below 1,500 indicates competitive markets; 1,500\u20132,500 moderate "
        "concentration; above 2,500 high concentration. HHI equals the sum "
        "of squared market shares across all lenders.\n\n"

        "Census data is from the 2010 and 2020 Decennial Census and the "
        "American Community Survey 5-year estimates. Income classifications "
        "follow HUD definitions: LMI borrowers have income below 80% of area "
        "median income. LMI census tracts have median family income below 80% "
        "of area median. Majority-minority tracts have over 50% minority population.\n\n"

        "AI-generated narrative analysis is produced by Anthropic's Claude "
        "language model. All quantitative data is derived directly from HMDA "
        "and Census sources. AI narratives provide contextual interpretation "
        "and should be verified against source data."
    )
    story.append(_inline_two_col(methods_text, style=_METHODS_COMPACT))

    # Horizontal rule before About
    story.append(Spacer(1, 4))
    story.append(HRFlowable(
        width='100%', thickness=0.5, color=RULE_COLOR,
        spaceAfter=6, spaceBefore=4,
    ))

    # About (compact single line)
    gen_date = datetime.now().strftime('%B %d, %Y')
    about_style = ParagraphStyle(
        'AboutText', fontName='Helvetica', fontSize=8,
        leading=11, textColor=HexColor('#333333'),
    )
    about_meta = ParagraphStyle(
        'AboutMeta', fontName='Helvetica', fontSize=7,
        leading=10, textColor=HexColor('#666666'), spaceAfter=0,
    )
    story.append(Paragraph(
        f'<b><font color="#1e3a5f">About This Report</font></b> \u2014 '
        f'Generated by NCRC LendSight, {gen_date}. Part of the JustData platform.',
        about_style,
    ))
    story.append(Paragraph(
        'National Community Reinvestment Coalition \u00b7 '
        '740 15th St NW, Suite 400, Washington DC 20005 \u00b7 '
        'ncrc.org \u00b7 justdata.org',
        about_meta,
    ))

    # ------------------------------------------------------------------
    # Build the PDF
    # ------------------------------------------------------------------
    doc.build(story)
    buf.seek(0)
    return buf
