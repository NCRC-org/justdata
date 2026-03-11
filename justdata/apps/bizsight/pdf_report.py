"""
BizSight magazine-style PDF report generator.

Modeled after LendSight's PDF report. Layout philosophy: FLOW, DON'T PAGINATE.
Only forced PageBreaks:
  #1 After cover
  #2 After team page
  #3 Before landscape lender table
  #4 After landscape (return to portrait)
Everything else flows naturally with Spacer(1, 24) between sections.

Generates a PDF with:
  Cover -> Team -> Key Findings -> Section 1: Market Overview ->
  Section 2: Lending by Tract Income -> Section 3: Small Business Lending ->
  Section 4: Geographic Comparison -> [landscape] Section 5: Top Lenders ->
  [portrait] Section 6: Market Concentration (HHI) -> Section 7: Methodology
"""

import os
import re
from io import BytesIO
from datetime import datetime

import pandas as pd
from reportlab.platypus import (
    Spacer, NextPageTemplate, PageBreak, Paragraph,
    KeepTogether, Table, TableStyle as TS, Image, HRFlowable,
)
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY, TA_CENTER

from justdata.shared.pdf.base_report import (
    MagazineDocTemplate, USABLE_WIDTH, L_USABLE_WIDTH, build_team_page,
)
from justdata.shared.pdf.styles import (
    HEADING_2, HEADING_3, BODY_TEXT, BODY_TEXT_SMALL,
    SOURCE_CAPTION, TABLE_CAPTION, LENDER_NAME_STYLE,
    TABLE_HEADER_TEXT,
    NAVY, RULE_COLOR, BODY_FONT, BODY_FONT_BOLD, BODY_FONT_ITALIC,
    HEADLINE_FONT_BOLD, HEADER_BG, ALT_ROW_BG, MEDIUM_GRAY,
    build_table_style, markdown_to_reportlab,
)
from justdata.shared.pdf.components import (
    build_data_table, build_key_findings,
    build_source_caption,
    ai_narrative_to_flowables,
    format_change_cell,
)
from justdata.apps.bizsight.pdf_charts import render_hhi_chart, chart_to_image


# ---------------------------------------------------------------------------
# Compact styles (local to this module)
# ---------------------------------------------------------------------------
_COMPACT_BODY = ParagraphStyle(
    'BZCompactBody',
    fontName='Georgia',
    fontSize=12,
    leading=16,
    textColor=HexColor('#333333'),
    alignment=TA_JUSTIFY,
    spaceAfter=5,
)

_AI_TAG = ParagraphStyle(
    'BZAITag',
    fontName='Georgia-Italic',
    fontSize=9,
    leading=12,
    textColor=HexColor('#aaaaaa'),
    spaceAfter=3,
)

_COMPACT_CAPTION = ParagraphStyle(
    'BZCompactCaption',
    fontName='Georgia-Italic',
    fontSize=9,
    leading=12,
    textColor=HexColor('#999999'),
    spaceAfter=4,
)

_COMPACT_FINDING = ParagraphStyle(
    'BZCompactFinding',
    fontName='Georgia',
    fontSize=13,
    leading=17,
    textColor=HexColor('#333333'),
    alignment=TA_LEFT,
    spaceAfter=6,
    leftIndent=8,
)

_COMPACT_H1 = ParagraphStyle(
    'BZCompactH1',
    fontName=HEADLINE_FONT_BOLD,
    fontSize=20,
    leading=24,
    textColor=NAVY,
    spaceBefore=6,
    spaceAfter=6,
    keepWithNext=True,
)

_COMPACT_H2 = ParagraphStyle(
    'BZCompactH2',
    fontName=HEADLINE_FONT_BOLD,
    fontSize=15,
    leading=19,
    textColor=NAVY,
    spaceBefore=6,
    spaceAfter=4,
)

_INLINE_NARRATIVE = ParagraphStyle(
    'BZInlineNarrative',
    fontName='Georgia',
    fontSize=12,
    leading=16,
    textColor=HexColor('#333333'),
    alignment=TA_JUSTIFY,
    spaceAfter=4,
)

_TABLE_INTRO = ParagraphStyle(
    'BZTableIntro',
    fontName='Georgia',
    fontSize=12,
    leading=16,
    textColor=HexColor('#444444'),
    alignment=TA_JUSTIFY,
    spaceAfter=6,
)

_AI_DISCLAIMER = ParagraphStyle(
    'BZAIDisclaimer',
    fontName='Georgia-Italic',
    fontSize=9,
    leading=12,
    textColor=HexColor('#aaaaaa'),
    spaceBefore=4,
    spaceAfter=6,
)

_METHODS_COMPACT = ParagraphStyle(
    'BZMethodsCompact',
    fontName='Georgia',
    fontSize=10,
    leading=13.5,
    textColor=HexColor('#666666'),
    alignment=TA_JUSTIFY,
    spaceAfter=4,
)

_METRIC_AGG = ParagraphStyle(
    'BZMetricAgg', fontName=BODY_FONT_BOLD, fontSize=9.5,
    leading=12, textColor=HexColor('#1e3a5f'),
)
_METRIC_INDENT = ParagraphStyle(
    'BZMetricIndent', fontName=BODY_FONT, fontSize=9.5,
    leading=12, textColor=HexColor('#333333'),
)
_METRIC_CELL = ParagraphStyle(
    'BZMetricCell', fontName=BODY_FONT, fontSize=9.5,
    leading=12, textColor=HexColor('#333333'),
)


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------
def _h1(text):
    return Paragraph(text, _COMPACT_H1)


def _h2(text):
    return Paragraph(text, _COMPACT_H2)


def _caption(text):
    return Paragraph(text, _COMPACT_CAPTION)


def _ai_tag():
    return Paragraph('AI-generated narrative \u2014 Anthropic Claude', _AI_TAG)


def _ai_narrative_block(narrative_text):
    """Wrap AI narrative in a light gray background box."""
    if not narrative_text or not isinstance(narrative_text, str) or not narrative_text.strip():
        return []

    inner = [_ai_tag()]
    inner.extend(ai_narrative_to_flowables(narrative_text, style=_INLINE_NARRATIVE))
    inner.append(Paragraph(
        'Above text is AI generated from NCRC data and analysis.',
        _AI_DISCLAIMER,
    ))

    box = Table(
        [[inner]],
        colWidths=[USABLE_WIDTH - 8],
        style=TS([
            ('BACKGROUND', (0, 0), (-1, -1), HexColor('#F0F0F0')),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]),
    )
    return [box]


def _compact_key_findings(findings_text):
    """Build compact key findings callout box."""
    if not findings_text:
        return Spacer(1, 0)

    lines = findings_text.strip().split('\n')
    finding_flowables = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        line = re.sub(r'^[\-\*\u2022]\s*', '', line)
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
        colWidths=[USABLE_WIDTH],
        style=TS([
            ('BACKGROUND', (0, 0), (-1, -1), HexColor('#f0f7ff')),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
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


def _fmt_int(val):
    """Format an integer value with commas."""
    try:
        v = int(float(val))
        return f'{v:,}'
    except (ValueError, TypeError):
        return str(val) if val else ''


def _fmt_pct(val):
    """Format a percentage value to one decimal place."""
    try:
        v = float(val)
        return f'{v:.1f}%'
    except (ValueError, TypeError):
        return str(val) if val else '\u2014'


def _fmt_dollars(val):
    """Format dollar amounts (in thousands) with comma separators."""
    try:
        v = float(val)
        if v >= 1000:
            return f'${v:,.0f}'
        return f'${v:,.0f}'
    except (ValueError, TypeError):
        return str(val) if val else ''


def _fmt_millions(val):
    """Format dollar amount (in thousands) as millions."""
    try:
        v = float(val) / 1000.0  # Convert from thousands to millions
        return f'${v:,.1f}M'
    except (ValueError, TypeError):
        return str(val) if val else ''


def _safe_float(val, default=0.0):
    """Safely convert to float."""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


# ---------------------------------------------------------------------------
# Table builders
# ---------------------------------------------------------------------------
def _build_county_summary_table(data_rows):
    """Build the county summary table (Section 1: Market Overview).

    data_rows: list of dicts from county_summary_table with 'Variable' key
    and year columns.
    """
    if not data_rows:
        return Spacer(1, 0), False

    sample = data_rows[0]
    year_cols = sorted([k for k in sample.keys()
                        if k not in ('Variable',) and str(k).strip().isdigit()])
    if not year_cols:
        return Spacer(1, 0), False

    VT_HEADER = HexColor('#2C5F8A')

    # Build header row
    header_labels = ['Metric'] + [str(y) for y in year_cols]
    header_row = [Paragraph(str(h), TABLE_HEADER_TEXT) for h in header_labels]

    # Column widths
    metric_w = 200
    year_w = (USABLE_WIDTH - metric_w) / len(year_cols)
    widths = [metric_w] + [year_w] * len(year_cols)

    table_data = [header_row]
    for row in data_rows:
        variable = str(row.get('Variable', ''))
        cells = [Paragraph(variable, _METRIC_CELL)]

        is_total = 'total loans' in variable.lower()
        is_amount = 'total loan amount' in variable.lower()
        is_pct = '(% of total)' in variable.lower() or '% of total' in variable.lower()

        for yc in year_cols:
            val = row.get(yc, 0)
            if is_total:
                cells.append(_fmt_int(val))
            elif is_amount:
                cells.append(_fmt_millions(val))
            elif is_pct:
                cells.append(_fmt_pct(val))
            else:
                try:
                    cells.append(f'{float(val):,.1f}')
                except (ValueError, TypeError):
                    cells.append(str(val))

        table_data.append(cells)

    num_rows = len(table_data)
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), VT_HEADER),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Georgia-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTNAME', (0, 1), (-1, -1), 'Georgia'),
        ('FONTSIZE', (0, 1), (-1, -1), 9.5),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#E0E0E0')),
        ('LINEBELOW', (0, 0), (-1, 0), 1, VT_HEADER),
        # Bold the Total Loans row (first data row)
        ('FONTNAME', (0, 1), (-1, 1), 'Georgia-Bold'),
        ('LINEBELOW', (0, 1), (-1, 1), 1.5, VT_HEADER),
    ]

    # Alternating row backgrounds
    for i in range(2, num_rows):
        if i % 2 == 0:
            style_cmds.append(('BACKGROUND', (0, i), (-1, i), HexColor('#F8FAFB')))

    # Bold amount section header rows
    for ri, row in enumerate(data_rows):
        variable = str(row.get('Variable', '')).lower()
        if 'total loan amount' in variable:
            tbl_row = ri + 1
            style_cmds.append(('FONTNAME', (0, tbl_row), (-1, tbl_row), 'Georgia-Bold'))
            style_cmds.append(('LINEBELOW', (0, tbl_row), (-1, tbl_row), 1.5, VT_HEADER))

    table = Table(table_data, colWidths=widths, repeatRows=1, hAlign='LEFT')
    table.setStyle(TS(style_cmds))

    return table, True


def _build_comparison_table(data_rows):
    """Build the geographic comparison table (Section 4).

    data_rows: list of dicts with 'Metric', 'County (2024)', 'State (2024)',
    'National (2024)', and '% Change Since 20XX' keys.
    """
    if not data_rows:
        return Spacer(1, 0), False

    sample = data_rows[0]
    # Find columns dynamically
    col_order = ['Metric']
    for k in sample.keys():
        if k != 'Metric' and k not in col_order:
            col_order.append(k)

    VT_HEADER = HexColor('#2C5F8A')

    header_row = [Paragraph(str(h), TABLE_HEADER_TEXT) for h in col_order]

    # Column widths
    metric_w = 180
    other_w = (USABLE_WIDTH - metric_w) / max(1, len(col_order) - 1)
    widths = [metric_w] + [other_w] * (len(col_order) - 1)

    table_data = [header_row]
    for row in data_rows:
        metric = str(row.get('Metric', ''))
        cells = [Paragraph(metric, _METRIC_CELL)]

        is_total = 'total loans' in metric.lower()
        is_amount = 'total loan amount' in metric.lower()

        for col in col_order[1:]:
            val = row.get(col, '')
            if 'change' in col.lower():
                # Format % change
                if val is None:
                    cells.append('\u2014')
                else:
                    try:
                        v = float(val)
                        sign = '+' if v > 0 else ''
                        cells.append(f'{sign}{v:.1f}%')
                    except (ValueError, TypeError):
                        cells.append(str(val) if val else '\u2014')
            elif is_total:
                cells.append(_fmt_int(val))
            elif is_amount:
                cells.append(_fmt_millions(val))
            else:
                cells.append(_fmt_pct(val))

        table_data.append(cells)

    num_rows = len(table_data)
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), VT_HEADER),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Georgia-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTNAME', (0, 1), (-1, -1), 'Georgia'),
        ('FONTSIZE', (0, 1), (-1, -1), 9.5),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#E0E0E0')),
        ('LINEBELOW', (0, 0), (-1, 0), 1, VT_HEADER),
        # Bold Total Loans row
        ('FONTNAME', (0, 1), (-1, 1), 'Georgia-Bold'),
        ('LINEBELOW', (0, 1), (-1, 1), 1.5, VT_HEADER),
    ]

    for i in range(2, num_rows):
        if i % 2 == 0:
            style_cmds.append(('BACKGROUND', (0, i), (-1, i), HexColor('#F8FAFB')))

    table = Table(table_data, colWidths=widths, repeatRows=1, hAlign='LEFT')
    table.setStyle(TS(style_cmds))

    return table, True


def _build_top_lenders_table(data_rows, max_rows=20):
    """Build Top Lenders table (landscape).

    data_rows: list of dicts from top_lenders_table.
    """
    if not data_rows:
        return Spacer(1, 0), False

    rows = sorted(data_rows,
                  key=lambda x: _safe_float(x.get('Num Total', 0)),
                  reverse=True)[:max_rows]

    # Column definitions: (data_key, header_label, width_pt)
    _COL_DEFS = [
        ('Lender Name',     'Lender Name',    200),
        ('Num Total',       'Total Loans',     65),
        ('Amt Total (in $000s)', 'Amt ($000s)', 70),
        ('Num Under 100K %', '<$100K %',       55),
        ('Num 100K 250K %',  '$100-250K %',    60),
        ('Num 250K 1M %',    '$250K-1M %',     60),
        ('Numsb Under 1M %', 'Rev<$1M %',      55),
        ('Lmi Tract',        'LMI Tract %',    60),
        ('Low Income %',     'Low Inc %',      55),
        ('Moderate Income %', 'Mod Inc %',     55),
    ]

    sample = rows[0]
    col_order, display_headers, widths = [], [], []
    for key, header, w in _COL_DEFS:
        if key in sample:
            col_order.append(key)
            display_headers.append(header)
            widths.append(w)

    if not col_order:
        return Spacer(1, 0), False

    # Lender name paragraph style
    _lender_name = ParagraphStyle(
        'BZLenderName', fontName='Georgia', fontSize=9.5,
        leading=12, textColor=HexColor('#333333'),
    )
    _hdr = ParagraphStyle(
        'BZLenderHeader', fontName='Georgia-Bold', fontSize=10,
        leading=12, textColor=white, alignment=TA_CENTER,
    )

    header_row = [Paragraph(str(h), _hdr) for h in display_headers]
    table_data = [header_row]

    for row in rows:
        cells = []
        for col in col_order:
            val = row.get(col, '')
            if val is None:
                val = ''
            if col == 'Lender Name':
                cells.append(Paragraph(str(val), _lender_name))
            elif col == 'Num Total':
                cells.append(_fmt_int(val))
            elif col == 'Amt Total (in $000s)':
                cells.append(_fmt_dollars(val))
            else:
                cells.append(_fmt_pct(val))
        table_data.append(cells)

    num_rows = len(table_data)
    VT_HEADER = HexColor('#2C5F8A')

    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), VT_HEADER),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Georgia-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9.5),
        ('FONTNAME', (0, 1), (-1, -1), 'Georgia'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.4, HexColor('#E0E0E0')),
        ('LINEBELOW', (0, 0), (-1, 0), 1, VT_HEADER),
    ]

    for i in range(1, num_rows):
        if i % 2 == 0:
            style_cmds.append(('BACKGROUND', (0, i), (-1, i), HexColor('#F8FAFB')))

    table = Table(table_data, colWidths=widths, repeatRows=1, hAlign='LEFT')
    table.setStyle(TS(style_cmds))

    return table, True


# ---------------------------------------------------------------------------
# Main PDF generator
# ---------------------------------------------------------------------------
def generate_bizsight_pdf(result_data, metadata):
    """Generate a magazine-style PDF report for BizSight and return as BytesIO.

    Args:
        result_data: Full analysis result dict from core.py run_analysis()
        metadata: Dict with 'county_data', 'years', 'job_id', etc.

    Returns:
        BytesIO containing the PDF.
    """
    ai = result_data.get('ai_insights', {}) or {}
    buf = BytesIO()

    doc = MagazineDocTemplate(
        buf,
        app_name='BizSight \u2014 Small Business Lending Analysis',
        footer_source='Source: FFIEC CRA Data compiled by NCRC',
    )

    story = []

    # ------------------------------------------------------------------
    # Prepare metadata
    # ------------------------------------------------------------------
    county_data = metadata.get('county_data', {})
    if isinstance(county_data, dict):
        county_display = county_data.get('name', 'Unknown County')
    elif isinstance(county_data, str):
        county_display = county_data
    else:
        county_display = str(county_data) if county_data else 'Unknown County'

    years = metadata.get('years', '')
    if isinstance(years, str) and ',' in years:
        year_list = sorted(years.split(','))
        date_range = f'{year_list[0]} \u2013 {year_list[-1]}' if len(year_list) > 1 else year_list[0]
    elif isinstance(years, (list, tuple)):
        year_strs = sorted(str(y) for y in years)
        date_range = f'{year_strs[0]} \u2013 {year_strs[-1]}' if len(year_strs) > 1 else year_strs[0] if year_strs else ''
    else:
        date_range = str(years) if years else ''

    # Set cover attributes on the doc (read by _draw_cover canvas callback)
    doc.cover_title = 'Small Business\nLending Analysis'
    doc.cover_subtitle = county_display
    doc.cover_date_range = date_range

    # ==================================================================
    # PAGE 1: COVER
    # ==================================================================
    story.append(Spacer(1, 1))
    story.append(NextPageTemplate('full_width'))
    story.append(PageBreak())

    # ==================================================================
    # PAGE 2: ABOUT THE NCRC RESEARCH TEAM
    # ==================================================================
    story.extend(build_team_page())
    story.append(NextPageTemplate('full_width'))
    story.append(PageBreak())

    # ==================================================================
    # KEY FINDINGS
    # ==================================================================
    # Build key findings from available AI insights
    key_findings_parts = []
    county_summary_data = _df_to_dicts(result_data.get('county_summary_table', []))
    comparison_data = _df_to_dicts(result_data.get('comparison_table', []))
    top_lenders_data = _df_to_dicts(result_data.get('top_lenders_table', []))
    hhi_by_year = result_data.get('hhi_by_year', [])
    hhi_current = result_data.get('hhi', {})

    # Auto-generate key findings from data
    if county_summary_data:
        for row in county_summary_data:
            var = str(row.get('Variable', ''))
            if 'total loans' == var.lower().strip():
                # Get latest year value
                year_cols = sorted([k for k in row.keys()
                                    if k != 'Variable' and str(k).strip().isdigit()])
                if year_cols:
                    latest = row.get(year_cols[-1], 0)
                    key_findings_parts.append(
                        f'**{_fmt_int(latest)}** total small business loans reported in {year_cols[-1]}'
                    )
            elif 'lmi tracts' in var.lower():
                year_cols = sorted([k for k in row.keys()
                                    if k != 'Variable' and str(k).strip().isdigit()])
                if year_cols:
                    latest = row.get(year_cols[-1], 0)
                    key_findings_parts.append(
                        f'**{_fmt_pct(latest)}** of loans went to LMI census tracts in {year_cols[-1]}'
                    )

    if top_lenders_data:
        top = top_lenders_data[0]
        name = top.get('Lender Name', 'Unknown')
        total = top.get('Num Total', 0)
        market_total = sum(_safe_float(r.get('Num Total', 0)) for r in top_lenders_data)
        share = (_safe_float(total) / market_total * 100) if market_total > 0 else 0
        key_findings_parts.append(
            f'**{name}** is the top lender with {_fmt_int(total)} loans ({share:.1f}% market share)'
        )

    if hhi_by_year:
        latest_hhi = hhi_by_year[-1]
        hhi_val = latest_hhi.get('hhi_value')
        hhi_level = latest_hhi.get('concentration_level', '')
        if hhi_val is not None:
            key_findings_parts.append(
                f'Market concentration HHI: **{int(hhi_val):,}** ({hhi_level})'
            )

    if key_findings_parts:
        findings_text = '\n'.join(f'- {f}' for f in key_findings_parts[:6])
        story.append(_h1('Key Findings'))
        story.append(_compact_key_findings(findings_text))
        story.append(Spacer(1, 12))

    # ==================================================================
    # SECTION 1: MARKET OVERVIEW
    # ==================================================================
    story.append(Spacer(1, 8))

    s1_table, s1_has = _build_county_summary_table(county_summary_data)
    if s1_has:
        story.append(KeepTogether([
            _h1('Section 1: Market Overview'),
            Paragraph(
                'This table shows aggregate small business lending activity in the county '
                'using Community Reinvestment Act (CRA) data reported by financial institutions '
                'to the FFIEC. Data includes loan counts and amounts by loan size category, '
                'lending to businesses with revenue under $1 million, and lending in '
                'low-to-moderate income (LMI) census tracts.',
                _TABLE_INTRO,
            ),
        ]))
        story.append(s1_table)
        story.append(_caption('Source: FFIEC CRA Small Business Lending Data'))

    # Section 1 AI narratives
    for key in ['county_summary_number_discussion', 'county_summary_amount_discussion']:
        narrative = ai.get(key, '')
        if narrative and isinstance(narrative, str) and narrative.strip():
            story.append(Spacer(1, 6))
            story.extend(_ai_narrative_block(narrative))
            break  # Only show one narrative per section

    # ==================================================================
    # SECTION 2: LENDING BY CENSUS TRACT INCOME LEVEL
    # ==================================================================
    # Extract tract income data from county summary
    tract_income_rows = []
    if county_summary_data:
        for row in county_summary_data:
            var = str(row.get('Variable', '')).lower()
            if any(k in var for k in ['lmi tract', 'low income', 'moderate income']):
                tract_income_rows.append(row)

    if tract_income_rows:
        story.append(Spacer(1, 24))
        story.append(KeepTogether([
            _h1('Section 2: Lending by Census Tract Income Level'),
            Paragraph(
                'Census tracts are classified by their median family income relative to the '
                'area median. Low-to-moderate income (LMI) tracts have median family incomes '
                'at or below 80% of the area median. This section examines small business '
                'lending patterns across different tract income levels.',
                _TABLE_INTRO,
            ),
        ]))

        # Build a focused table from the summary data
        # (The county summary already contains LMI tract % rows)
        for row in tract_income_rows:
            variable = str(row.get('Variable', ''))
            year_cols = sorted([k for k in row.keys()
                                if k != 'Variable' and str(k).strip().isdigit()])
            if year_cols:
                vals = [f'{year_cols[-1]}: {_fmt_pct(row.get(year_cols[-1], 0))}']
                if len(year_cols) > 1:
                    vals.append(f'{year_cols[0]}: {_fmt_pct(row.get(year_cols[0], 0))}')
                story.append(Paragraph(
                    f'<b>{variable}:</b> {", ".join(vals)}',
                    _COMPACT_BODY
                ))

        story.append(_caption('Source: FFIEC CRA Small Business Lending Data'))

    # ==================================================================
    # SECTION 3: LENDING TO SMALL BUSINESSES
    # ==================================================================
    sb_rows = []
    if county_summary_data:
        for row in county_summary_data:
            var = str(row.get('Variable', '')).lower()
            if 'revenue' in var or 'under $1m' in var:
                sb_rows.append(row)

    if sb_rows:
        story.append(Spacer(1, 24))
        story.append(KeepTogether([
            _h1('Section 3: Lending to Small Businesses'),
            Paragraph(
                'CRA data includes information on loans to businesses with gross annual '
                'revenues of less than $1 million. This is a key indicator of lending to truly '
                'small businesses, as opposed to larger companies that also receive small-dollar '
                'loans. A higher percentage of lending to businesses with revenues under $1 million '
                'may indicate stronger support for small enterprises.',
                _TABLE_INTRO,
            ),
        ]))

        for row in sb_rows:
            variable = str(row.get('Variable', ''))
            year_cols = sorted([k for k in row.keys()
                                if k != 'Variable' and str(k).strip().isdigit()])
            if year_cols:
                vals = [f'{year_cols[-1]}: {_fmt_pct(row.get(year_cols[-1], 0))}']
                if len(year_cols) > 1:
                    vals.append(f'{year_cols[0]}: {_fmt_pct(row.get(year_cols[0], 0))}')
                story.append(Paragraph(
                    f'<b>{variable}:</b> {", ".join(vals)}',
                    _COMPACT_BODY
                ))

        story.append(_caption('Source: FFIEC CRA Small Business Lending Data'))

    # ==================================================================
    # SECTION 4: GEOGRAPHIC COMPARISON
    # ==================================================================
    s4_table, s4_has = _build_comparison_table(comparison_data)
    if s4_has:
        story.append(Spacer(1, 24))
        story.append(KeepTogether([
            _h1('Section 4: Geographic Comparison'),
            Paragraph(
                'This table compares the county\u2019s small business lending metrics against '
                'state and national benchmarks for the most recent year. It shows how the local '
                'market compares in terms of loan sizes, lending to small businesses, and lending '
                'in low-to-moderate income census tracts.',
                _TABLE_INTRO,
            ),
        ]))
        story.append(s4_table)
        story.append(_caption('Source: FFIEC CRA Small Business Lending Data, NCRC Benchmarks'))

    # Section 4 AI narratives
    for key in ['comparison_number_discussion', 'comparison_amount_discussion']:
        narrative = ai.get(key, '')
        if narrative and isinstance(narrative, str) and narrative.strip():
            story.append(Spacer(1, 6))
            story.extend(_ai_narrative_block(narrative))
            break

    # ==================================================================
    # SECTION 5: TOP LENDERS (LANDSCAPE)
    # ==================================================================
    lender_count = min(20, len(top_lenders_data)) if top_lenders_data else 0
    s5_table, s5_has = _build_top_lenders_table(top_lenders_data, max_rows=lender_count)

    if s5_has:
        story.append(NextPageTemplate('landscape'))
        story.append(PageBreak())  # PageBreak #3
        story.append(_h1('Section 5: Top Lenders'))
        story.append(Paragraph(
            f'Top {lender_count} lenders by total loan volume. Percentage columns show the share '
            'of each lender\u2019s lending in that category. Full lender list available in Excel export.',
            _COMPACT_CAPTION,
        ))
        story.append(Spacer(1, 4))
        story.append(s5_table)
        story.append(_caption('Source: FFIEC CRA Small Business Lending Data'))

    # Return to portrait — PageBreak #4
    story.append(NextPageTemplate('full_width'))
    story.append(PageBreak())

    # Lender AI narrative
    for key in ['top_lenders_number_discussion', 'top_lenders_amount_discussion']:
        narrative = ai.get(key, '')
        if narrative and isinstance(narrative, str) and narrative.strip():
            story.append(_h2('Lender Analysis'))
            story.extend(_ai_narrative_block(narrative))
            break

    # ==================================================================
    # SECTION 6: MARKET CONCENTRATION (HHI)
    # ==================================================================
    story.append(Spacer(1, 12))
    story.append(_h1('Section 6: Market Concentration'))

    # HHI info box
    hhi_info_text = (
        '<b>Herfindahl-Hirschman Index (HHI)</b><br/><br/>'
        'The HHI is a standard measure of market concentration calculated by '
        'summing the squares of each lender\u2019s market share.<br/><br/>'
        '<b>How to read:</b><br/>'
        '&bull; &lt;1,500 = Competitive market<br/>'
        '&bull; 1,500\u20132,500 = Moderately concentrated<br/>'
        '&bull; &gt;2,500 = Highly concentrated<br/><br/>'
        'Based on total loan amounts (dollars). Range: 0\u201310,000.'
    )
    _hhi_info_style = ParagraphStyle(
        'BZHHIInfo', fontName='Georgia', fontSize=10, leading=13.5,
        textColor=HexColor('#444444'),
    )
    hhi_info_box = Table(
        [[[Paragraph(hhi_info_text, _hhi_info_style)]]],
        colWidths=[USABLE_WIDTH * 0.34 - 7],
        style=TS([
            ('BACKGROUND', (0, 0), (-1, -1), HexColor('#f5f5f5')),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]),
    )

    # HHI chart
    hhi_chart_buf = render_hhi_chart(hhi_by_year)
    chart_w = USABLE_WIDTH * 0.63
    hhi_chart_img = chart_to_image(hhi_chart_buf, width=chart_w, height_inches=2.6)

    if hhi_chart_img:
        gap = 14
        left_w = USABLE_WIDTH * 0.34 - gap // 2
        right_w = USABLE_WIDTH * 0.66 - gap // 2
        hhi_layout = Table(
            [[[hhi_info_box], [hhi_chart_img]]],
            colWidths=[left_w, right_w],
        )
        hhi_layout.setStyle(TS([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(hhi_layout)
    else:
        story.append(hhi_info_box)

    story.append(_caption(
        'Source: FFIEC CRA Data. HHI &lt;1,500 = Competitive, '
        '1,500\u20132,500 = Moderate, &gt;2,500 = Concentrated'
    ))

    # HHI AI narrative
    hhi_narrative = ai.get('hhi_trends_discussion', '')
    if hhi_narrative and isinstance(hhi_narrative, str) and hhi_narrative.strip():
        story.append(Spacer(1, 4))
        story.extend(_ai_narrative_block(hhi_narrative))

    # ==================================================================
    # SECTION 7: METHODOLOGY
    # ==================================================================
    story.append(Spacer(1, 24))
    story.append(HRFlowable(
        width='100%', thickness=0.5, color=RULE_COLOR,
        spaceAfter=8, spaceBefore=4,
    ))
    meth_heading = _h1('Methodology')

    _meth_h3 = ParagraphStyle(
        'BZMethH3', fontName=BODY_FONT_BOLD, fontSize=12, leading=15,
        textColor=NAVY, spaceBefore=6, spaceAfter=3,
    )
    _meth_h4 = ParagraphStyle(
        'BZMethH4', fontName=BODY_FONT_BOLD, fontSize=10, leading=13,
        textColor=HexColor('#333333'), spaceBefore=4, spaceAfter=2,
    )
    _meth_bullet = ParagraphStyle(
        'BZMethBullet', fontName='Georgia', fontSize=9.5, leading=12.5,
        textColor=HexColor('#666666'), leftIndent=10, spaceAfter=1,
    )

    meth_elements = []

    # Data Sources
    meth_elements.append(Paragraph('Data Sources', _meth_h3))
    meth_elements.append(Paragraph(
        '<b>CRA Data:</b> This report uses data from the Community Reinvestment Act (CRA) '
        'small business lending data collected by the Federal Financial Institutions Examination '
        'Council (FFIEC). Financial institutions with assets above specified thresholds report '
        'the number and dollar amount of small business loans (loans with original amounts of '
        '$1 million or less) originated in each census tract.',
        _METHODS_COMPACT))
    meth_elements.append(Paragraph(
        '<b>Data Coverage:</b> CRA data captures loans from banks and thrifts subject to CRA '
        'reporting requirements. Credit unions and non-depository lenders are generally not '
        'included. The data represents a significant but not comprehensive view of all small '
        'business lending activity.',
        _METHODS_COMPACT))

    # Definitions
    meth_elements.append(Paragraph('Definitions', _meth_h3))
    meth_elements.append(Paragraph(
        '<b>Small Business Loan:</b> A loan with an original amount of $1 million or less '
        'to a business. CRA data reports these in three size categories: under $100,000, '
        '$100,000\u2013$250,000, and $250,000\u2013$1,000,000.',
        _METHODS_COMPACT))
    meth_elements.append(Paragraph(
        '<b>Revenue Under $1 Million:</b> Loans to businesses with gross annual revenues '
        'of less than $1 million. This helps distinguish lending to truly small businesses '
        'from larger companies receiving small-dollar loans.',
        _METHODS_COMPACT))
    meth_elements.append(Paragraph(
        '<b>Low-to-Moderate Income (LMI) Census Tract:</b> A census tract where the median '
        'family income is at or below 80% of the area median family income for the MSA or '
        'nonmetropolitan area.',
        _METHODS_COMPACT))

    meth_elements.append(Paragraph('Census Tract Income Categories', _meth_h4))
    for line in [
        'Low Income Tract: Median family income \u226450% of area median',
        'Moderate Income Tract: >50% to \u226480% of area median',
        'Middle Income Tract: >80% to \u2264120% of area median',
        'Upper Income Tract: >120% of area median',
    ]:
        meth_elements.append(Paragraph(f'&bull; {line}', _meth_bullet))

    # Calculations
    meth_elements.append(Paragraph('Calculations', _meth_h3))
    meth_elements.append(Paragraph(
        '<b>Herfindahl-Hirschman Index (HHI):</b> A standard measure of market concentration. '
        'HHI = \u03a3(market share)<sup>2</sup>. Based on total loan origination amounts. '
        'Ranges 0\u201310,000. '
        '&lt;1,500 = Competitive; 1,500\u20132,500 = Moderate; &gt;2,500 = Concentrated.',
        _METHODS_COMPACT))
    meth_elements.append(Paragraph(
        '<b>Percentages:</b> Calculated as the count or amount for a category divided by '
        'the total count or amount, multiplied by 100. Shown to one decimal place.',
        _METHODS_COMPACT))

    # AI Disclosure
    meth_elements.append(Paragraph('AI Disclosure', _meth_h3))
    meth_elements.append(Paragraph(
        'AI-generated narrative analysis is produced by Anthropic\u2019s Claude language '
        'model. All quantitative data is derived directly from FFIEC CRA and Census sources. '
        'AI narratives provide contextual interpretation and should be verified against '
        'source data.',
        _METHODS_COMPACT))

    # Suggested Citation
    meth_elements.append(Paragraph('Suggested Citation', _meth_h3))
    gen_date = datetime.now().strftime('%B %d, %Y')
    meth_elements.append(Paragraph(
        f'National Community Reinvestment Coalition. "Small Business Lending Analysis: '
        f'{county_display}." BizSight Report, NCRC JustData Platform, {gen_date}.',
        _METHODS_COMPACT))

    # Abbreviations
    meth_elements.append(Paragraph('Abbreviations', _meth_h3))
    abbrevs = [
        'CRA: Community Reinvestment Act',
        'FFIEC: Federal Financial Institutions Examination Council',
        'HHI: Herfindahl-Hirschman Index',
        'LMI: Low-to-Moderate Income',
        'MSA: Metropolitan Statistical Area',
    ]
    for a in abbrevs:
        meth_elements.append(Paragraph(f'&bull; {a}', _meth_bullet))

    # KeepTogether on heading + first subsection
    story.append(KeepTogether([
        meth_heading,
        Spacer(1, 4),
        Paragraph('Data Sources', _meth_h3),
    ]))

    # Strip duplicate "Data Sources" heading
    meth_elements = meth_elements[1:]
    story.extend(meth_elements)

    # Horizontal rule before About
    story.append(Spacer(1, 4))
    story.append(HRFlowable(
        width='100%', thickness=0.5, color=RULE_COLOR,
        spaceAfter=6, spaceBefore=4,
    ))

    # About section
    about_style = ParagraphStyle(
        'BZAboutText', fontName='Georgia', fontSize=10,
        leading=13.5, textColor=HexColor('#333333'),
    )
    about_meta = ParagraphStyle(
        'BZAboutMeta', fontName='Georgia', fontSize=9,
        leading=12, textColor=HexColor('#666666'), spaceAfter=0,
    )
    story.append(Paragraph(
        f'<b><font color="#1e3a5f">About This Report</font></b> \u2014 '
        f'Generated by NCRC BizSight, {gen_date}. Part of the JustData platform.',
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
