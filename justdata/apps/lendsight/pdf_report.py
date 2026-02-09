"""
LendSight magazine-style PDF report generator (v4 overhaul).

Generates a ~8-page PDF with:
  Page 1: Cover (gradient with logo)
  Page 2: About the NCRC Research Team
  Page 3: Census chart + Key Findings + mini trend/gap charts
  Page 4: Section 1 table + AI narrative + Section 2a table
  Page 5: Section 2 AI + income chart + Section 2b + 2c tables + AI
  Page N: Section 3: Top 20 Lenders (landscape, one page)
  Page N+1: Section 4: HHI chart + table + AI narrative (portrait)
  Page N+2: Methodology (comprehensive) + About

Key technique: Inline two-column narratives via Table flowables
instead of switching to two_column PageTemplate (which forced page breaks).
"""

import os
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
    get_heat_color, render_pop_vs_lending_bars, format_change_cell,
)
from justdata.apps.lendsight.pdf_charts import (
    render_census_demographics_chart, render_hhi_chart,
    render_trend_line_chart, render_gap_chart,
    render_lender_bars_chart, render_income_share_chart,
    render_sparkline, chart_to_image,
)
from justdata.apps.lendsight.version import __version__


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

# Change column color-coded styles
_CHANGE_POS = ParagraphStyle(
    'ChangePos', fontName=BODY_FONT, fontSize=7.5, leading=10,
    textColor=HexColor('#1a8fc9'), alignment=TA_CENTER,
)
_CHANGE_NEG = ParagraphStyle(
    'ChangeNeg', fontName=BODY_FONT, fontSize=7.5, leading=10,
    textColor=HexColor('#C62828'), alignment=TA_CENTER,
)

# Metric cell variants for parent-child hierarchy (7pt to match visual table rows)
_METRIC_AGG = ParagraphStyle(
    'MetricAgg', fontName=BODY_FONT_BOLD, fontSize=7,
    leading=9, textColor=HexColor('#1e3a5f'),
)
_METRIC_INDENT = ParagraphStyle(
    'MetricIndent', fontName=BODY_FONT, fontSize=7,
    leading=9, textColor=HexColor('#333333'),
)
_METRIC_CELL = ParagraphStyle(
    'MetricCell', fontName=BODY_FONT, fontSize=7,
    leading=9, textColor=HexColor('#333333'),
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

# Short display labels for PDF tables (matching web report)
SECTION2_T1_LABELS = {
    'Low to Moderate Income Borrowers': 'LMI Borrowers',
    'Low Income Borrowers': 'Low',
    'Moderate Income Borrowers': 'Moderate',
    'Middle Income Borrowers': 'Middle',
    'Upper Income Borrowers': 'Upper',
}
SECTION2_T2_LABELS = {
    'Low to Moderate Income Census Tracts': 'LMI Tracts',
    'Low Income Census Tracts': 'Low',
    'Moderate Income Census Tracts': 'Moderate',
    'Middle Income Census Tracts': 'Middle',
    'Upper Income Census Tracts': 'Upper',
}
SECTION2_T3_LABELS = {
    'Majority Minority Census Tracts': 'MMCT',
    'Low Minority Census Tracts': 'Low',
    'Moderate Minority Census Tracts': 'Moderate',
    'Middle Minority Census Tracts': 'Middle',
    'High Minority Census Tracts': 'High',
}


def _shorten_label(val, label_map):
    """Shorten a metric label using case-insensitive fuzzy matching."""
    if not label_map:
        return val
    v = val.strip()
    if v in label_map:
        return label_map[v]
    v_lower = v.lower()
    for full, short in label_map.items():
        if full.lower() in v_lower or v_lower in full.lower():
            return short
    return v


def _matches_patterns(val, patterns):
    """Case-insensitive fuzzy match against a list of patterns."""
    if not patterns:
        return False
    val_lower = val.lower().strip()
    for p in patterns:
        if p.lower() in val_lower or val_lower in p.lower():
            return True
    return False


def _parse_float(val):
    """Safely parse a value to float, returning None on failure."""
    if val is None or val == '':
        return None
    try:
        return float(str(val).replace(',', '').replace('%', '').strip())
    except (ValueError, TypeError):
        return None


def _build_visual_table(data, row_order, metric_label='Metric',
                        metric_width=90, pop_col_width=45, year_col_width=42,
                        trend_width=55, change_width=55,
                        shorten_labels=None, aggregate_metrics=None,
                        indent_metrics=None, show_pop_bars=False):
    """Build a section table with heat maps, sparklines, change arrows,
    and optional Pop vs Lending bars (Section 1 only).

    All widths are in points (not inches).
    """
    rows = _df_to_dicts(data)
    if not rows:
        return Spacer(1, 0), False

    sample = rows[0]
    year_cols = _get_year_cols(sample)
    change_col = _find_change_col(sample)
    pop_share_col = _find_pop_share_col(sample)
    n_years = len(year_cols)
    if not year_cols:
        return Spacer(1, 0), False

    sorted_rows = _sort_rows(rows, row_order)
    shorten = shorten_labels or {}
    agg_patterns = aggregate_metrics or []
    indent_patterns = indent_metrics or []

    # --- Gather raw numeric values for heat map + sparkline ---
    # Store raw floats per row per year (before formatting)
    raw_year_vals = []   # list of lists, one per sorted row
    for row in sorted_rows:
        vals = []
        for yc in year_cols:
            vals.append(_parse_float(row.get(yc, '')))
        raw_year_vals.append(vals)

    # Per-column min/max for heat map (exclude Total Loans row)
    col_min = [None] * n_years
    col_max = [None] * n_years
    for ri, row in enumerate(sorted_rows):
        metric = str(row.get('Metric', '')).lower()
        if 'total' in metric:
            continue  # skip totals for heat map range
        for ci in range(n_years):
            v = raw_year_vals[ri][ci]
            if v is not None:
                if col_min[ci] is None or v < col_min[ci]:
                    col_min[ci] = v
                if col_max[ci] is None or v > col_max[ci]:
                    col_max[ci] = v

    # Fill None mins/maxes with 0
    col_min = [m if m is not None else 0 for m in col_min]
    col_max = [m if m is not None else 1 for m in col_max]

    # --- Build header row ---
    header_labels = [metric_label]
    if show_pop_bars:
        header_labels.append('Pop. vs Lending')
    elif pop_share_col:
        header_labels.append('Pop.')
    header_labels.extend(year_cols)
    header_labels.append('Trend')
    if change_col:
        header_labels.append('Change')

    header_row = [Paragraph(str(h), TABLE_HEADER_TEXT) for h in header_labels]

    # --- Build column widths ---
    widths = [metric_width]
    if show_pop_bars:
        widths.append(100)
    elif pop_share_col:
        widths.append(pop_col_width)
    widths.extend([year_col_width] * n_years)
    widths.append(trend_width)
    if change_col:
        widths.append(change_width)

    # Track column index offsets for heat map styling
    year_start_col = len([metric_label]) + (1 if (show_pop_bars or pop_share_col) else 0)

    # --- Build data rows ---
    table_data = [header_row]
    agg_row_indices = []
    heat_map_commands = []   # (col, row, color) for per-cell heat map

    for ri, row_dict in enumerate(sorted_rows):
        cells = []
        metric_val = str(row_dict.get('Metric', ''))
        is_agg = _matches_patterns(metric_val, agg_patterns)
        is_indent = _matches_patterns(metric_val, indent_patterns)
        is_total = 'total' in metric_val.lower()
        display = _shorten_label(metric_val, shorten)

        # Metric column
        if is_agg:
            cells.append(Paragraph(display, _METRIC_AGG))
        elif is_indent:
            cells.append(Paragraph(display, _METRIC_INDENT))
        else:
            cells.append(Paragraph(display, _METRIC_CELL))

        # Pop column: bars (Section 1) or text (Section 2)
        if show_pop_bars and not is_total:
            pop_val = _parse_float(row_dict.get(pop_share_col, '')) if pop_share_col else None
            # Use latest year value as lending share
            lend_val = raw_year_vals[ri][-1] if raw_year_vals[ri] else None
            cells.append(render_pop_vs_lending_bars(pop_val, lend_val))
        elif show_pop_bars and is_total:
            cells.append('')   # no bars for total row
        elif pop_share_col:
            pv = _parse_float(row_dict.get(pop_share_col, ''))
            if pv is not None and not is_total:
                cells.append(f'{pv:.1f}%')
            else:
                cells.append(_fmt_val(row_dict.get(pop_share_col, ''), is_total_row=is_total))

        # Year columns (formatted text; heat map applied via style)
        for ci, yc in enumerate(year_cols):
            if is_total:
                v = _parse_float(row_dict.get(yc, ''))
                cells.append(f'{int(v):,}' if v is not None else '0')
            else:
                v = raw_year_vals[ri][ci]
                cells.append(f'{v:.1f}%' if v is not None else '\u2014')
            # Heat map color (skip total row)
            if not is_total:
                v = raw_year_vals[ri][ci]
                if v is not None:
                    bg = get_heat_color(v, col_min[ci], col_max[ci])
                    tbl_row = ri + 1   # +1 for header
                    tbl_col = year_start_col + ci
                    heat_map_commands.append((tbl_col, tbl_row, bg))

        # Sparkline column
        spark_vals = raw_year_vals[ri]
        if not is_total and any(v is not None for v in spark_vals):
            spark_buf = render_sparkline(
                [v if v is not None else 0 for v in spark_vals],
                width_inches=trend_width / 72 * 0.85,
                height_inches=0.2,
            )
            if spark_buf:
                cells.append(Image(spark_buf,
                                   width=trend_width * 0.85,
                                   height=0.2 * inch))
            else:
                cells.append('')
        else:
            # Total row: sparkline of counts
            count_vals = [_parse_float(row_dict.get(yc, '')) for yc in year_cols]
            if any(v is not None for v in count_vals):
                spark_buf = render_sparkline(
                    [v if v is not None else 0 for v in count_vals],
                    width_inches=trend_width / 72 * 0.85,
                    height_inches=0.2,
                    color='#666666',
                )
                if spark_buf:
                    cells.append(Image(spark_buf,
                                       width=trend_width * 0.85,
                                       height=0.2 * inch))
                else:
                    cells.append('')
            else:
                cells.append('')

        # Change column with colored arrows
        if change_col:
            change_val = row_dict.get(change_col, '')
            cells.append(format_change_cell(change_val, is_total_row=is_total))

        tbl_row_idx = len(table_data)
        if is_agg:
            agg_row_indices.append(tbl_row_idx)
        table_data.append(cells)

    # --- Create table ---
    num_rows = len(table_data)
    table = Table(table_data, colWidths=widths, repeatRows=1, hAlign='LEFT')

    # Custom visual table style (matches web report design)
    VT_HEADER = HexColor('#2C5F8A')
    style_cmds = [
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), VT_HEADER),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7),
        # Data rows
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        # Alignment
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        # Padding
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#E0E0E0')),
        ('LINEBELOW', (0, 0), (-1, 0), 1, VT_HEADER),
        # Total Loans row (first data row) — bold + separator
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('LINEBELOW', (0, 1), (-1, 1), 1.5, VT_HEADER),
    ]

    style = TS(style_cmds)

    # Apply heat map per-cell backgrounds
    for col_idx, row_idx, bg_color in heat_map_commands:
        style.add('BACKGROUND', (col_idx, row_idx), (col_idx, row_idx), bg_color)

    # Aggregate (parent) row styling
    agg_bg = HexColor('#EEF2F6')
    for idx in agg_row_indices:
        style.add('BACKGROUND', (0, idx), (-1, idx), agg_bg)
        style.add('FONTNAME', (0, idx), (-1, idx), BODY_FONT_BOLD)
        style.add('TEXTCOLOR', (0, idx), (-1, idx), HexColor('#1e3a5f'))

    # Child row left indent via cell padding
    for ri, row_dict in enumerate(sorted_rows):
        metric_val = str(row_dict.get('Metric', ''))
        if _matches_patterns(metric_val, indent_patterns):
            style.add('LEFTPADDING', (0, ri + 1), (0, ri + 1), 18)

    table.setStyle(style)
    return table, True


def _build_section1_table(data):
    """Section 1: Race/Ethnicity with Pop vs Lending bars."""
    return _build_visual_table(
        data, SECTION1_ROW_ORDER,
        metric_label='Race / Ethnicity',
        metric_width=90, year_col_width=42,
        trend_width=55, change_width=55,
        show_pop_bars=True,
    )


def _build_section2_income_borrowers_table(data):
    return _build_visual_table(
        data, SECTION2_T1_ROW_ORDER,
        metric_label='Borrower Income',
        metric_width=110, pop_col_width=45, year_col_width=50,
        trend_width=55, change_width=55,
        shorten_labels=SECTION2_T1_LABELS,
        aggregate_metrics=['Low to Moderate Income Borrowers'],
        indent_metrics=['Low Income Borrowers', 'Moderate Income Borrowers'],
    )


def _build_section2_income_tracts_table(data):
    return _build_visual_table(
        data, SECTION2_T2_ROW_ORDER,
        metric_label='Tract Median Income',
        metric_width=110, pop_col_width=45, year_col_width=50,
        trend_width=55, change_width=55,
        shorten_labels=SECTION2_T2_LABELS,
        aggregate_metrics=['Low to Moderate Income Census Tracts'],
        indent_metrics=['Low Income Census Tracts', 'Moderate Income Census Tracts'],
    )


def _build_section2_minority_tracts_table(data):
    return _build_visual_table(
        data, SECTION2_T3_ROW_ORDER,
        metric_label='Tract Minority Pop.',
        metric_width=110, pop_col_width=45, year_col_width=50,
        trend_width=55, change_width=55,
        shorten_labels=SECTION2_T3_LABELS,
        aggregate_metrics=['Majority Minority Census Tracts'],
        indent_metrics=['Low Minority Census Tracts', 'Moderate Minority Census Tracts',
                        'Middle Minority Census Tracts', 'High Minority Census Tracts'],
    )


def _build_top_lenders_table(data):
    """Build Section 3: Top 20 Lenders table (landscape, fits one page)."""
    rows = _df_to_dicts(data)
    if not rows:
        return Spacer(1, 0), False

    rows = sorted(rows, key=lambda x: float(x.get('Total Loans', 0) or 0), reverse=True)[:20]

    all_possible_cols = [
        'Lender Name', 'Lender Type', 'Total Loans',
        'Hispanic (%)', 'Black (%)', 'White (%)', 'Asian (%)',
        'Native American (%)', 'Multi-Racial (%)',
        'LMIB (%)', 'LMICT (%)', 'MMCT (%)',
    ]
    all_display_headers = [
        'Lender Name', 'Type', 'Total', 'Hisp.', 'Black', 'White',
        'Asian', 'Nat. Am.', 'Multi-R.', 'LMIB', 'LMICT', 'MMCT',
    ]
    all_widths = [
        2.4 * inch, 0.55 * inch, 0.55 * inch,
        0.5 * inch, 0.5 * inch, 0.5 * inch, 0.5 * inch,
        0.55 * inch, 0.55 * inch,
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
    """Build Section 4: HHI table. Filters out rows with all-zero values."""
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

    # Filter out rows where all year values are 0 or empty
    filtered_rows = []
    for row in rows:
        has_data = False
        for col in year_cols:
            val = row.get(col, '')
            try:
                if val and float(val) > 0:
                    has_data = True
                    break
            except (ValueError, TypeError):
                pass
        if has_data:
            filtered_rows.append(row)

    if not filtered_rows:
        return Spacer(1, 0), False

    col_order = ['Loan Purpose'] + year_cols
    header_labels = ['Loan Purpose'] + year_cols
    widths = [2.0 * inch] + [0.8 * inch] * len(year_cols)

    sorted_rows = _sort_rows(filtered_rows, HHI_ROW_ORDER)

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
# Main PDF generator (v4 overhaul)
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
    # PAGE 2: ABOUT THE NCRC RESEARCH TEAM
    # ==================================================================
    story.extend(build_team_page())
    story.append(NextPageTemplate('full_width'))
    story.append(PageBreak())

    # ==================================================================
    # PAGE 3: CENSUS CHART + KEY FINDINGS + MINI CHARTS
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
    # PAGE 4: SECTION 1 TABLE + AI + SECTION 2A TABLE
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
    # PAGE 5: SECTION 2 AI + INCOME CHART + SECTION 2B + 2C + AI
    # ==================================================================
    story.append(CondPageBreak(3 * inch))

    # Income borrowers AI narrative
    ib_narrative = ai.get('income_borrowers_discussion', '')
    if ib_narrative and isinstance(ib_narrative, str) and ib_narrative.strip():
        story.append(_ai_tag())
        story.append(_inline_two_col(ib_narrative))

    # Mini chart: Income Share (full-width)
    income_borrowers_data = _df_to_dicts(income_borrowers)
    income_share_buf = render_income_share_chart(income_borrowers_data)
    income_share_img = _mini_img(income_share_buf, aspect_w=3.3, aspect_h=1.5)

    market_conc = report_data.get('market_concentration', [])
    if isinstance(market_conc, pd.DataFrame):
        market_conc = market_conc.to_dict('records') if not market_conc.empty else []

    if income_share_img:
        story.append(Spacer(1, 6))
        story.append(income_share_img)

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
    # PAGE N: SECTION 3 — TOP LENDERS (LANDSCAPE)
    # ==================================================================
    lenders_df = report_data.get('top_lenders_detailed')
    s3_table, s3_has = _build_top_lenders_table(lenders_df)

    if s3_has:
        story.append(NextPageTemplate('landscape'))
        story.append(PageBreak())
        story.append(_h1('Section 3: Top Mortgage Lenders'))
        story.append(Paragraph(
            'Top 20 lenders by total loan volume. Demographic columns show % of each '
            'lender\u2019s originations. Full lender list available in Excel export.',
            _COMPACT_CAPTION,
        ))
        story.append(Spacer(1, 4))
        story.append(s3_table)
        story.append(_caption('Source: HMDA data. Complete lender list available in Excel export.'))

        # Lender AI narrative (immediately after lender table)
        lender_narrative = ai.get('top_lenders_detailed_discussion', '')
        if lender_narrative and isinstance(lender_narrative, str) and lender_narrative.strip():
            story.append(Spacer(1, 8))
            story.append(_h2('Lender Analysis'))
            story.append(_ai_tag())
            story.append(_inline_two_col(lender_narrative))

    # ==================================================================
    # PAGE N+1: SECTION 4 — MARKET CONCENTRATION (PORTRAIT)
    # ==================================================================
    story.append(NextPageTemplate('full_width'))
    story.append(PageBreak())

    story.append(_h1('Section 4: Market Concentration'))

    # Full-width HHI chart
    hhi_full_buf = render_hhi_chart(market_conc)
    hhi_full_img = chart_to_image(hhi_full_buf, width=USABLE_WIDTH, height_inches=2.8)
    if hhi_full_img:
        story.append(hhi_full_img)
        story.append(_caption(
            'Source: HMDA data. HHI &lt;1,500 = Competitive, '
            '1,500\u20132,500 = Moderate, &gt;2,500 = Concentrated'
        ))
        story.append(Spacer(1, 8))

    # HHI table
    s4_table, s4_has = _build_hhi_table(market_conc)
    if s4_has:
        story.append(s4_table)
        story.append(_caption('Source: HMDA data'))
        story.append(Spacer(1, 12))

    # HHI AI narrative (inline two-column)
    hhi_narrative = ai.get('market_concentration_discussion', '')
    if hhi_narrative and isinstance(hhi_narrative, str) and hhi_narrative.strip():
        story.append(_ai_tag())
        story.append(_inline_two_col(hhi_narrative))

    # ==================================================================
    # METHODOLOGY PAGE
    # ==================================================================
    story.append(NextPageTemplate('full_width'))
    story.append(PageBreak())

    # Trends Analysis (if available, placed before methodology)
    trends_text = ai.get('trends_analysis', '')
    if trends_text and isinstance(trends_text, str) and trends_text.strip():
        story.append(_h1('Trends Analysis'))
        story.append(_ai_tag())
        story.append(_inline_two_col(trends_text))
        story.append(Spacer(1, 8))
        story.append(HRFlowable(
            width='100%', thickness=0.5, color=RULE_COLOR,
            spaceAfter=8, spaceBefore=4,
        ))

    # Methods — comprehensive methodology matching web report
    story.append(_h1('Methodology'))

    _meth_h3 = ParagraphStyle(
        'MethH3', fontName=BODY_FONT_BOLD, fontSize=8, leading=11,
        textColor=NAVY, spaceBefore=6, spaceAfter=3,
    )
    _meth_h4 = ParagraphStyle(
        'MethH4', fontName=BODY_FONT_BOLD, fontSize=7, leading=10,
        textColor=HexColor('#333333'), spaceBefore=4, spaceAfter=2,
    )
    _meth_bullet = ParagraphStyle(
        'MethBullet', fontName='Helvetica', fontSize=6.5, leading=9,
        textColor=HexColor('#666666'), leftIndent=10, spaceAfter=1,
    )

    meth_elements = []

    # Data Sources
    meth_elements.append(Paragraph('Data Sources', _meth_h3))
    meth_elements.append(Paragraph(
        '<b>HMDA Data:</b> This report uses data from the Home Mortgage Disclosure Act '
        '(HMDA), which requires financial institutions to report information about mortgage '
        'loan applications and originations. HMDA data is collected and made publicly available '
        'by the Consumer Financial Protection Bureau (CFPB). The data used in this report is '
        'sourced from NCRC\u2019s curated HMDA databases, compiled and maintained by NCRC '
        'Research staff.',
        _METHODS_COMPACT))
    meth_elements.append(Paragraph(
        '<b>HMDA Data Coverage:</b> This analysis includes mortgage loan originations '
        '(action taken = 1) for owner-occupied, site-built, 1\u20134 unit properties. '
        'Reverse mortgages are excluded from the analysis.',
        _METHODS_COMPACT))
    meth_elements.append(Paragraph(
        '<b>Census Data:</b> Population demographic data is sourced from the U.S. Census '
        'Bureau, including the 2010 Decennial Census, 2020 Decennial Census, and American '
        'Community Survey (ACS) 5-year estimates.',
        _METHODS_COMPACT))
    meth_elements.append(Paragraph(
        '<b>HUD Data:</b> Income category population shares are sourced from the U.S. '
        'Department of Housing and Urban Development (HUD) Low-Mod Summary Data, which shows '
        'the percentage of county residents in each income bracket based on 2020 ACS data.',
        _METHODS_COMPACT))
    meth_elements.append(Paragraph(
        '<b>Data Filters Applied:</b> Originations only (action taken = 1); Site-built '
        'properties (construction method = 1); Owner-occupied (occupancy type = 1); '
        'Forward loans (excludes reverse mortgages); 1\u20134 unit properties.',
        _METHODS_COMPACT))
    meth_elements.append(Paragraph(
        '<b>Data Cleaning:</b> Loan amounts below the 1st percentile and above the 99th '
        'percentile within each county-year are excluded (&lt;1% of records). This outlier '
        'removal prevents extreme values from distorting market share and HHI calculations.',
        _METHODS_COMPACT))

    # Definitions
    meth_elements.append(Paragraph('Definitions', _meth_h3))
    meth_elements.append(Paragraph(
        '<b>Loan Originations:</b> Completed mortgage loans where action taken = 1. '
        'Excludes applications, denials, and withdrawn/incomplete applications.',
        _METHODS_COMPACT))
    meth_elements.append(Paragraph(
        '<b>Low-to-Moderate Income Borrower (LMIB):</b> Borrowers whose income is at or '
        'below 80% of Area Median Family Income (AMFI) for the MSA or MD where the '
        'property is located.',
        _METHODS_COMPACT))

    meth_elements.append(Paragraph('Borrower Income Categories', _meth_h4))
    for line in [
        'Low Income: \u226450% of AMFI',
        'Moderate Income: &gt;50% to \u226480% of AMFI',
        'Middle Income: &gt;80% to \u2264120% of AMFI',
        'Upper Income: &gt;120% of AMFI',
    ]:
        meth_elements.append(Paragraph(f'&bull; {line}', _meth_bullet))

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
        '<b>Majority-Minority Census Tract (MMCT):</b> Tracts where minority populations '
        'represent more than 50% of the total population.',
        _METHODS_COMPACT))

    # Calculations
    meth_elements.append(Paragraph('Calculations', _meth_h3))
    meth_elements.append(Paragraph(
        '<b>Race/Ethnicity Classification:</b> Hispanic if any ethnicity field indicates '
        'Hispanic (codes 1, 11\u201314), regardless of race. Non-Hispanic race determined '
        'from the first valid race code.',
        _METHODS_COMPACT))
    meth_elements.append(Paragraph(
        '<b>Percentages:</b> Race/ethnicity = group loans / loans with demographic data '
        '\u00d7 100. Income and neighborhood indicators use total loans as the denominator. '
        'Only groups representing \u22651% of loans are displayed.',
        _METHODS_COMPACT))
    meth_elements.append(Paragraph(
        '<b>Change Over Time:</b> For shares: Last Year \u2212 First Year, expressed in '
        'percentage points (pp). For counts: ((Last \u2212 First) / First) \u00d7 100. '
        'Positive changes shown in blue; negative in red.',
        _METHODS_COMPACT))

    meth_elements.append(Paragraph('Herfindahl-Hirschman Index (HHI)', _meth_h4))
    meth_elements.append(Paragraph(
        'A standard measure of market concentration. HHI = \u03a3(market share)<sup>2</sup>. '
        'Based on total loan origination amounts. Ranges 0\u201310,000. '
        '&lt;1,500 = Competitive; 1,500\u20132,500 = Moderate; &gt;2,500 = Concentrated.',
        _METHODS_COMPACT))

    # Abbreviations
    meth_elements.append(Paragraph('Abbreviations', _meth_h3))
    abbrevs = [
        'ACS: American Community Survey',
        'AMFI: Area Median Family Income',
        'CBSA: Core Based Statistical Area',
        'CFPB: Consumer Financial Protection Bureau',
        'HHI: Herfindahl-Hirschman Index',
        'HMDA: Home Mortgage Disclosure Act',
        'HUD: U.S. Dept. of Housing and Urban Development',
        'LMIB: Low-to-Moderate Income Borrower',
        'LMICT: Low-to-Moderate Income Census Tract',
        'MMCT: Majority-Minority Census Tract',
    ]
    for a in abbrevs:
        meth_elements.append(Paragraph(f'&bull; {a}', _meth_bullet))

    # AI Disclosure
    meth_elements.append(Paragraph('AI Disclosure', _meth_h3))
    meth_elements.append(Paragraph(
        'AI-generated narrative analysis is produced by Anthropic\u2019s Claude language '
        'model. All quantitative data is derived directly from HMDA and Census sources. '
        'AI narratives provide contextual interpretation and should be verified against '
        'source data.',
        _METHODS_COMPACT))

    # Render as two-column layout
    half = len(meth_elements) // 2
    left_col = meth_elements[:half]
    right_col = meth_elements[half:]
    gap = 14
    col_w = (USABLE_WIDTH - gap) / 2
    meth_table = Table(
        [[left_col, right_col]],
        colWidths=[col_w, col_w],
    )
    meth_table.setStyle(TS([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (0, 0), 0),
        ('RIGHTPADDING', (0, 0), (0, 0), gap // 2),
        ('LEFTPADDING', (1, 0), (1, 0), gap // 2),
        ('RIGHTPADDING', (1, 0), (1, 0), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(meth_table)

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
        f'Generated by NCRC LendSight v{__version__}, {gen_date}. Part of the JustData platform.',
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
