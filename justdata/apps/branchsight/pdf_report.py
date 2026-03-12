"""
BranchSight magazine-style PDF report generator.

Matches the LendSight PDF style: Georgia fonts, navy headers, KeepTogether
for section blocks, AI narrative boxes, proper number formatting.

Layout: FLOW, DON'T PAGINATE.
Forced PageBreaks:
  #1 After cover
  #2 After team page
  #3 Before landscape bank table (if needed)
  #4 After landscape (return to portrait)
Everything else flows naturally with Spacer(1, 24) between sections.
"""

import os
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
    HEADING_2, BODY_TEXT, BODY_TEXT_SMALL,
    SOURCE_CAPTION, TABLE_CAPTION,
    TABLE_HEADER_TEXT, TABLE_CELL_TEXT, TABLE_CELL_NUMBER,
    NAVY, RULE_COLOR, BODY_FONT, BODY_FONT_BOLD, BODY_FONT_ITALIC,
    HEADLINE_FONT_BOLD, HEADER_BG, ALT_ROW_BG, MEDIUM_GRAY,
    build_table_style, markdown_to_reportlab,
)
from justdata.shared.pdf.components import (
    build_data_table, build_key_findings, build_source_caption,
    ai_narrative_to_flowables, format_change_cell,
)
from justdata.apps.branchsight.pdf_charts import (
    render_branch_trend_chart, render_hhi_chart, chart_to_image,
)
from justdata.apps.branchsight.version import __version__


# ---------------------------------------------------------------------------
# Compact styles (local to this module)
# ---------------------------------------------------------------------------
_COMPACT_BODY = ParagraphStyle(
    'BSCompactBody', fontName='Georgia', fontSize=12, leading=16,
    textColor=HexColor('#333333'), alignment=TA_JUSTIFY, spaceAfter=5,
)

_AI_TAG = ParagraphStyle(
    'BSAITag', fontName='Georgia-Italic', fontSize=9, leading=12,
    textColor=HexColor('#aaaaaa'), spaceAfter=3,
)

_COMPACT_CAPTION = ParagraphStyle(
    'BSCompactCaption', fontName='Georgia-Italic', fontSize=9, leading=12,
    textColor=HexColor('#999999'), spaceAfter=4,
)

_COMPACT_FINDING = ParagraphStyle(
    'BSCompactFinding', fontName='Georgia', fontSize=13, leading=17,
    textColor=HexColor('#333333'), alignment=TA_LEFT, spaceAfter=6,
    leftIndent=8,
)

_COMPACT_H1 = ParagraphStyle(
    'BSCompactH1', fontName=HEADLINE_FONT_BOLD, fontSize=20, leading=24,
    textColor=NAVY, spaceBefore=6, spaceAfter=6, keepWithNext=True,
)

_COMPACT_H2 = ParagraphStyle(
    'BSCompactH2', fontName=HEADLINE_FONT_BOLD, fontSize=15, leading=19,
    textColor=NAVY, spaceBefore=6, spaceAfter=4,
)

_INLINE_NARRATIVE = ParagraphStyle(
    'BSInlineNarrative', fontName='Georgia', fontSize=12, leading=16,
    textColor=HexColor('#333333'), alignment=TA_JUSTIFY, spaceAfter=4,
)

_TABLE_INTRO = ParagraphStyle(
    'BSTableIntro', fontName='Georgia', fontSize=12, leading=16,
    textColor=HexColor('#444444'), alignment=TA_JUSTIFY, spaceAfter=6,
)

_AI_DISCLAIMER = ParagraphStyle(
    'BSAIDisclaimer', fontName='Georgia-Italic', fontSize=9, leading=12,
    textColor=HexColor('#aaaaaa'), spaceBefore=4, spaceAfter=6,
)

_METHODS_COMPACT = ParagraphStyle(
    'BSMethodsCompact', fontName='Georgia', fontSize=10, leading=13.5,
    textColor=HexColor('#666666'), alignment=TA_JUSTIFY, spaceAfter=4,
)

_METRIC_CELL = ParagraphStyle(
    'BSMetricCell', fontName=BODY_FONT, fontSize=9.5, leading=12,
    textColor=HexColor('#333333'),
)

_METRIC_BOLD = ParagraphStyle(
    'BSMetricBold', fontName=BODY_FONT_BOLD, fontSize=9.5, leading=12,
    textColor=HexColor('#1e3a5f'),
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

    import re
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
    """Format an integer with comma separators."""
    if val is None or val == '':
        return '\u2014'
    try:
        return f'{int(float(str(val).replace(",", ""))):,}'
    except (ValueError, TypeError):
        return str(val)


def _fmt_deposits(val):
    """Format deposits string (already in millions from report_builder)."""
    if val is None or val == '' or val == 'N/A':
        return 'N/A'
    return f'${val}M' if not str(val).startswith('$') else val


def _fmt_pct(val):
    """Format a percentage to 1 decimal place."""
    if val is None or val == '':
        return '\u2014'
    try:
        return f'{float(val):.1f}%'
    except (ValueError, TypeError):
        return str(val)


def _fmt_change(val):
    """Format a change value with sign."""
    if val is None or val == '':
        return '\u2014'
    try:
        v = int(float(str(val).replace(',', '')))
        if v > 0:
            return f'+{v:,}'
        elif v < 0:
            return f'{v:,}'
        else:
            return '0'
    except (ValueError, TypeError):
        return str(val)


# ---------------------------------------------------------------------------
# Section 1: Yearly Summary Table
# ---------------------------------------------------------------------------
def _build_summary_table(summary_data):
    """Build the yearly branch summary table.

    summary_data: DataFrame or list of dicts with 'Variable' key and year columns.
    """
    rows = _df_to_dicts(summary_data)
    if not rows:
        return Spacer(1, 0), False

    sample = rows[0]

    # Find year columns and special columns
    year_cols = []
    for k in sorted(sample.keys()):
        if k in ('Variable', 'Net Change'):
            continue
        try:
            yr = int(str(k).strip())
            if 2000 <= yr <= 2030:
                year_cols.append(str(k))
        except (ValueError, TypeError):
            pass

    if not year_cols:
        return Spacer(1, 0), False

    has_net_change = 'Net Change' in sample

    # Build header
    header_labels = ['Variable'] + year_cols
    if has_net_change:
        header_labels.append('Net Change')
    header_row = [Paragraph(str(h), TABLE_HEADER_TEXT) for h in header_labels]

    # Column widths
    var_width = 2.0 * inch
    year_width = 0.8 * inch
    change_width = 0.8 * inch
    widths = [var_width] + [year_width] * len(year_cols)
    if has_net_change:
        widths.append(change_width)

    # Build data rows
    table_data = [header_row]
    for row in rows:
        cells = []
        var_name = str(row.get('Variable', ''))
        is_total = 'total' in var_name.lower()

        # Variable name cell
        style = _METRIC_BOLD if is_total else _METRIC_CELL
        cells.append(Paragraph(var_name, style))

        # Year columns
        for yc in year_cols:
            cells.append(_fmt_int(row.get(yc, '')))

        # Net Change
        if has_net_change:
            cells.append(_fmt_change(row.get('Net Change', '')))

        table_data.append(cells)

    num_rows = len(table_data)
    table = Table(table_data, colWidths=widths, repeatRows=1, hAlign='LEFT')

    VT_HEADER = HexColor('#2C5F8A')
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
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#E0E0E0')),
        ('LINEBELOW', (0, 0), (-1, 0), 1, VT_HEADER),
        # Bold the Total Branches row (first data row)
        ('FONTNAME', (0, 1), (-1, 1), 'Georgia-Bold'),
        ('LINEBELOW', (0, 1), (-1, 1), 1.5, VT_HEADER),
    ]

    # Alternating row backgrounds
    for i in range(2, num_rows):
        if i % 2 == 0:
            style_cmds.append(('BACKGROUND', (0, i), (-1, i), HexColor('#F8FAFB')))

    table.setStyle(TS(style_cmds))
    return table, True


# ---------------------------------------------------------------------------
# Section 2: Bank Networks Table
# ---------------------------------------------------------------------------
def _build_bank_table(bank_data, max_rows=20):
    """Build the top banks table.

    bank_data: DataFrame or list of dicts from create_bank_summary.
    Columns: Bank Name, Total Branches, Deposits ($ Millions),
             LMI Only Branches, MMCT Only Branches, Both LMICT\\MMCT Branches,
             Net Change
    """
    rows = _df_to_dicts(bank_data)
    if not rows:
        return Spacer(1, 0), False, False

    # Sort by total branches descending, take top N
    rows = sorted(rows, key=lambda x: int(str(x.get('_total_branches', x.get('Total Branches', 0))).replace(',', '') or 0),
                  reverse=True)[:max_rows]

    # Column definitions: (data_key, header_label, width_pt)
    _COL_DEFS = [
        ('Bank Name', 'Bank Name', 180),
        ('Total Branches', 'Branches', 60),
        ('Deposits ($ Millions)', 'Deposits ($M)', 72),
        ('LMI Only Branches', 'LMI Only', 72),
        ('MMCT Only Branches', 'MMCT Only', 72),
        ('Both LMICT\\MMCT Branches', 'Both', 60),
        ('Net Change', 'Net Chg.', 52),
    ]

    # Filter to columns that exist in data
    sample = rows[0]
    col_order, display_headers, widths = [], [], []
    for key, header, w in _COL_DEFS:
        if key in sample:
            col_order.append(key)
            display_headers.append(header)
            widths.append(w)

    if not col_order:
        return Spacer(1, 0), False, False

    # Check if this needs landscape (7+ columns with many rows)
    needs_landscape = len(col_order) >= 7 and len(rows) > 15

    # Lender-name paragraph style
    _bank_name = ParagraphStyle(
        'BankNameCompact', fontName='Georgia', fontSize=9.5,
        leading=12, textColor=HexColor('#333333'),
    )
    _hdr = ParagraphStyle(
        'BankHeader', fontName='Georgia-Bold', fontSize=10,
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
            if col == 'Bank Name':
                cells.append(Paragraph(str(val), _bank_name))
            elif col == 'Net Change':
                cells.append(_fmt_change(val))
            else:
                cells.append(str(val))
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
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.4, HexColor('#E0E0E0')),
        ('LINEBELOW', (0, 0), (-1, 0), 1, VT_HEADER),
    ]

    # Alternating row backgrounds
    for i in range(1, num_rows):
        if i % 2 == 0:
            style_cmds.append(('BACKGROUND', (0, i), (-1, i), HexColor('#F8FAFB')))

    table = Table(table_data, colWidths=widths, repeatRows=1, hAlign='LEFT')
    table.setStyle(TS(style_cmds))

    return table, True, needs_landscape


# ---------------------------------------------------------------------------
# County-by-County Table (unused — single-county only app)
# ---------------------------------------------------------------------------
def _build_county_table(county_data):
    """Build the county-by-county comparison table."""
    rows = _df_to_dicts(county_data)
    if not rows or len(rows) < 2:
        return Spacer(1, 0), False

    _COL_DEFS = [
        ('County', 'County', 150),
        ('Total Branches', 'Branches', 65),
        ('LMI Only Branches', 'LMI Only', 75),
        ('MMCT Only Branches', 'MMCT Only', 75),
        ('Both LMICT/MMCT Branches', 'Both LMI/MMCT', 80),
        ('Number of Banks', 'Banks', 55),
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

    _hdr = ParagraphStyle(
        'CountyHeader', fontName='Georgia-Bold', fontSize=10,
        leading=12, textColor=white, alignment=TA_CENTER,
    )

    header_row = [Paragraph(str(h), _hdr) for h in display_headers]
    table_data = [header_row]

    for row in rows:
        cells = []
        for col in col_order:
            val = row.get(col, '')
            if col == 'County':
                cells.append(Paragraph(str(val), _METRIC_CELL))
            else:
                cells.append(str(val) if val is not None else '')
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
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#E0E0E0')),
        ('LINEBELOW', (0, 0), (-1, 0), 1, VT_HEADER),
    ]

    for i in range(2, num_rows):
        if i % 2 == 0:
            style_cmds.append(('BACKGROUND', (0, i), (-1, i), HexColor('#F8FAFB')))

    table = Table(table_data, colWidths=widths, repeatRows=1, hAlign='LEFT')
    table.setStyle(TS(style_cmds))
    return table, True


# ---------------------------------------------------------------------------
# Section: HHI Table
# ---------------------------------------------------------------------------
def _build_hhi_table(hhi_by_year_data):
    """Build a simple HHI by year table."""
    if not hhi_by_year_data:
        return Spacer(1, 0), False

    years = []
    values = []
    for item in hhi_by_year_data:
        try:
            yr = int(item.get('year', 0))
            hhi = float(item.get('hhi', 0))
            if yr:
                years.append(str(yr))
                values.append(f'{int(hhi):,}' if hhi > 0 else '\u2014')
        except (ValueError, TypeError):
            continue

    if not years:
        return Spacer(1, 0), False

    header_labels = ['Year'] + years
    data_row = ['HHI'] + values
    header_row = [Paragraph(str(h), TABLE_HEADER_TEXT) for h in header_labels]

    widths = [1.2 * inch] + [0.8 * inch] * len(years)
    table_data = [header_row, data_row]

    table = Table(table_data, colWidths=widths, hAlign='LEFT')
    table.setStyle(build_table_style(num_rows=2))
    return table, True


# ---------------------------------------------------------------------------
# Main PDF generator
# ---------------------------------------------------------------------------
def generate_branchsight_pdf(report_data, metadata, ai_insights=None):
    """Generate a magazine-style PDF report and return as BytesIO."""
    ai = ai_insights or {}
    buf = BytesIO()

    doc = MagazineDocTemplate(
        buf,
        app_name='BranchSight \u2014 Branch Access Analysis',
        footer_source='Source: FDIC Summary of Deposits compiled by NCRC',
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

    # Set cover attributes (read by _draw_cover canvas callback)
    doc.cover_title = 'Branch Access\nAnalysis'
    doc.cover_subtitle = county_display
    doc.cover_date_range = date_range
    doc.cover_loan_purpose = ''  # Not applicable for BranchSight

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
    key_findings = ai.get('key_findings', '')
    if key_findings and isinstance(key_findings, str) and key_findings.strip():
        story.append(_h1('Key Findings'))
        story.append(_compact_key_findings(key_findings))
        story.append(Spacer(1, 12))

    # ==================================================================
    # SECTION 1: YEARLY BREAKDOWN
    # ==================================================================
    summary_df = report_data.get('summary')
    s1_table, s1_has = _build_summary_table(summary_df)

    if s1_has:
        story.append(Spacer(1, 24))
        story.append(KeepTogether([
            _h1('Section 1: Yearly Breakdown'),
            Paragraph(
                'This table shows the annual branch counts for the selected geography '
                'from the FDIC Summary of Deposits. Branch categories are mutually exclusive: '
                'LMI Only branches are in low-to-moderate income census tracts that are not '
                'majority-minority; MMCT Only branches are in majority-minority tracts that '
                'are not LMI; Both LMICT/MMCT are in tracts that meet both criteria. '
                'Net Change is calculated from the first to last year of the analysis period.',
                _TABLE_INTRO,
            ),
        ]))
        story.append(s1_table)
        story.append(_caption('Source: FDIC Summary of Deposits (SOD), compiled by NCRC'))

    # Section 1 AI narrative
    table_narratives = ai.get('table_narratives', {})
    s1_narrative = table_narratives.get('table1', '')
    if s1_narrative and isinstance(s1_narrative, str) and s1_narrative.strip():
        story.append(Spacer(1, 6))
        story.extend(_ai_narrative_block(s1_narrative))

    # ==================================================================
    # BRANCH TREND CHART
    # ==================================================================
    summary_rows = _df_to_dicts(summary_df)
    trend_buf = render_branch_trend_chart(summary_rows)
    if trend_buf:
        story.append(Spacer(1, 16))
        trend_img = chart_to_image(trend_buf, width=USABLE_WIDTH * 0.7,
                                   height_inches=2.5)
        if trend_img:
            story.append(trend_img)
            story.append(_caption(
                'Source: FDIC Summary of Deposits. Shows total unique branch locations per year.'
            ))

    # ==================================================================
    # SECTION 2: BANK NETWORKS
    # ==================================================================
    bank_df = report_data.get('by_bank')
    s2_table, s2_has, s2_landscape = _build_bank_table(bank_df)

    if s2_has:
        if s2_landscape:
            story.append(NextPageTemplate('landscape'))
            story.append(PageBreak())
        else:
            story.append(Spacer(1, 24))

        bank_count = min(20, len(_df_to_dicts(bank_df)))
        story.append(KeepTogether([
            _h1('Section 2: Bank Networks'),
            Paragraph(
                f'Top {bank_count} banks by branch count in the selected geography. '
                'Deposits are in millions of dollars. LMI Only, MMCT Only, and Both '
                'columns show counts with percentages in parentheses. Net Change is '
                'the difference in total branches between the first and last year.',
                _TABLE_INTRO,
            ),
        ]))
        story.append(s2_table)
        story.append(_caption(
            'Source: FDIC Summary of Deposits. Full bank list available in Excel export.'
        ))

        if s2_landscape:
            story.append(NextPageTemplate('full_width'))
            story.append(PageBreak())

    # Section 2 AI narrative
    s2_narrative = table_narratives.get('table2', '')
    if s2_narrative and isinstance(s2_narrative, str) and s2_narrative.strip():
        story.append(Spacer(1, 6))
        story.extend(_ai_narrative_block(s2_narrative))

    # ==================================================================
    # SECTION 3: MARKET CONCENTRATION (HHI)
    # ==================================================================
    hhi_by_year = report_data.get('hhi_by_year', [])
    if hhi_by_year:
        story.append(Spacer(1, 24))
        story.append(_h1('Section 3: Market Concentration'))

        # HHI info box + chart side by side
        hhi_info_text = (
            '<b>Herfindahl-Hirschman Index (HHI)</b><br/><br/>'
            'The HHI measures market concentration by summing the squares of '
            'each bank\u2019s deposit market share.<br/><br/>'
            '<b>How to read:</b><br/>'
            '&bull; &lt;1,500 = Competitive market<br/>'
            '&bull; 1,500\u20132,500 = Moderately concentrated<br/>'
            '&bull; &gt;2,500 = Highly concentrated<br/><br/>'
            'Based on total deposit amounts. Range: 0\u201310,000.'
        )
        _hhi_info_style = ParagraphStyle(
            'BSHHIInfo', fontName='Georgia', fontSize=10, leading=13.5,
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

        hhi_chart_buf = render_hhi_chart(hhi_by_year)
        chart_w = USABLE_WIDTH * 0.63
        hhi_chart_img = chart_to_image(hhi_chart_buf, width=chart_w, height_inches=2.5)

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
            'Source: FDIC Summary of Deposits. HHI &lt;1,500 = Competitive, '
            '1,500\u20132,500 = Moderate, &gt;2,500 = Concentrated'
        ))

        # HHI table
        hhi_table, hhi_has = _build_hhi_table(hhi_by_year)
        if hhi_has:
            story.append(Spacer(1, 8))
            story.append(hhi_table)

        # HHI AI narrative
        hhi_narrative = ai.get('hhi_trends_discussion', '')
        if hhi_narrative and isinstance(hhi_narrative, str) and hhi_narrative.strip():
            story.append(Spacer(1, 6))
            story.extend(_ai_narrative_block(hhi_narrative))

    # ==================================================================
    # METHODOLOGY
    # ==================================================================
    story.append(Spacer(1, 24))
    story.append(HRFlowable(
        width='100%', thickness=0.5, color=RULE_COLOR,
        spaceAfter=8, spaceBefore=4,
    ))

    _meth_h3 = ParagraphStyle(
        'BSMethH3', fontName=BODY_FONT_BOLD, fontSize=12, leading=15,
        textColor=NAVY, spaceBefore=6, spaceAfter=3,
    )
    _meth_h4 = ParagraphStyle(
        'BSMethH4', fontName=BODY_FONT_BOLD, fontSize=10, leading=13,
        textColor=HexColor('#333333'), spaceBefore=4, spaceAfter=2,
    )
    _meth_bullet = ParagraphStyle(
        'BSMethBullet', fontName='Georgia', fontSize=9.5, leading=12.5,
        textColor=HexColor('#666666'), leftIndent=10, spaceAfter=1,
    )

    meth_heading = _h1('Methodology')
    meth_elements = []

    # Data Sources
    meth_elements.append(Paragraph('Data Sources', _meth_h3))
    meth_elements.append(Paragraph(
        '<b>FDIC Summary of Deposits:</b> This report uses data from the Federal Deposit '
        'Insurance Corporation (FDIC) Summary of Deposits (SOD). Branch-level data is '
        'sourced from the FDIC\u2019s annual survey of all FDIC-insured institutions, '
        'compiled and maintained in NCRC\u2019s curated databases.',
        _METHODS_COMPACT))
    meth_elements.append(Paragraph(
        '<b>Branch Service Types:</b> This analysis includes all branch service types '
        'reported in the FDIC Summary of Deposits, including Full Service Branches, '
        'Limited Service Branches, Drive-Through Branches, and other service types.',
        _METHODS_COMPACT))
    meth_elements.append(Paragraph(
        '<b>Census Data:</b> Census tract characteristics are sourced from the U.S. Census '
        'Bureau American Community Survey (ACS) 5-year estimates.',
        _METHODS_COMPACT))

    # Definitions
    meth_elements.append(Paragraph('Definitions', _meth_h3))
    meth_elements.append(Paragraph(
        '<b>Branch:</b> A unique physical branch location identified using the FDIC unique '
        'institution number (uninumbr). Branch counts represent distinct physical locations.',
        _METHODS_COMPACT))

    meth_elements.append(Paragraph('Census Tract Income Categories', _meth_h4))
    for line in [
        'Low Income Tract: Median family income \u226450% of AMFI',
        'Moderate Income Tract: &gt;50% to \u226480% of AMFI',
        'Middle Income Tract: &gt;80% to \u2264120% of AMFI',
        'Upper Income Tract: &gt;120% of AMFI',
        'LMI Census Tract (LMICT): \u226480% of AMFI (Low + Moderate combined)',
    ]:
        meth_elements.append(Paragraph(f'&bull; {line}', _meth_bullet))

    meth_elements.append(Paragraph(
        '<b>Majority-Minority Census Tract (MMCT):</b> Census tracts where minority '
        'populations represent more than 50% of the total population.',
        _METHODS_COMPACT))

    meth_elements.append(Paragraph('Branch Category Classifications (Mutually Exclusive)', _meth_h4))
    for line in [
        'LMI Only Branches: In LMI tracts that are not MMCT',
        'MMCT Only Branches: In MMCT that are not LMI tracts',
        'Both LMICT/MMCT Branches: In tracts that are both LMI and MMCT',
        'Other Branches: Neither LMICT nor MMCT',
    ]:
        meth_elements.append(Paragraph(f'&bull; {line}', _meth_bullet))

    meth_elements.append(Paragraph(
        '<b>2020 Census Boundary Changes:</b> The 2020 census boundaries that took effect '
        'in 2022 resulted in a 30% increase in the number of majority-minority census tracts '
        'nationally. Large changes in MMCT branch counts between 2021 and 2022 may reflect '
        'statistical reclassification rather than actual branch movements.',
        _METHODS_COMPACT))

    # Calculations
    meth_elements.append(Paragraph('Calculations', _meth_h3))
    meth_elements.append(Paragraph(
        '<b>Branch Counts:</b> Unique branches identified using uninumbr. '
        'Counts represent distinct physical branch locations.',
        _METHODS_COMPACT))
    meth_elements.append(Paragraph(
        '<b>Net Change:</b> Difference between branch counts in the first year and '
        'the final year of the analysis period.',
        _METHODS_COMPACT))

    meth_elements.append(Paragraph('Herfindahl-Hirschman Index (HHI)', _meth_h4))
    meth_elements.append(Paragraph(
        'HHI = \u03a3(market share)<sup>2</sup>. Based on total deposit amounts. '
        'Ranges 0\u201310,000. &lt;1,500 = Competitive; 1,500\u20132,500 = Moderate; '
        '&gt;2,500 = Concentrated.',
        _METHODS_COMPACT))

    # Abbreviations
    meth_elements.append(Paragraph('Abbreviations', _meth_h3))
    for a in [
        'AMFI: Area Median Family Income',
        'FDIC: Federal Deposit Insurance Corporation',
        'FIPS: Federal Information Processing Standards',
        'HHI: Herfindahl-Hirschman Index',
        'LMI: Low-to-Moderate Income',
        'LMICT: Low-to-Moderate Income Census Tract',
        'MMCT: Majority-Minority Census Tract',
        'SOD: Summary of Deposits',
    ]:
        meth_elements.append(Paragraph(f'&bull; {a}', _meth_bullet))

    # AI Disclosure
    meth_elements.append(Paragraph('AI Disclosure', _meth_h3))
    meth_elements.append(Paragraph(
        'AI-generated narrative analysis is produced by Anthropic\u2019s Claude language '
        'model. All quantitative data is derived directly from FDIC and Census sources. '
        'AI narratives provide contextual interpretation and should be verified against '
        'source data.',
        _METHODS_COMPACT))

    # KeepTogether on heading + first subsection
    story.append(KeepTogether([
        meth_heading,
        Spacer(1, 4),
        Paragraph('Data Sources', _meth_h3),
    ]))

    # Remove duplicate "Data Sources" heading
    meth_elements = meth_elements[1:]
    story.extend(meth_elements)

    # About
    story.append(Spacer(1, 4))
    story.append(HRFlowable(
        width='100%', thickness=0.5, color=RULE_COLOR,
        spaceAfter=6, spaceBefore=4,
    ))

    gen_date = datetime.now().strftime('%B %d, %Y')
    about_style = ParagraphStyle(
        'BSAboutText', fontName='Georgia', fontSize=10,
        leading=13.5, textColor=HexColor('#333333'),
    )
    about_meta = ParagraphStyle(
        'BSAboutMeta', fontName='Georgia', fontSize=9,
        leading=12, textColor=HexColor('#666666'), spaceAfter=0,
    )
    story.append(Paragraph(
        f'<b><font color="#1e3a5f">About This Report</font></b> \u2014 '
        f'Generated by NCRC BranchSight v{__version__}, {gen_date}. Part of the JustData platform.',
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
