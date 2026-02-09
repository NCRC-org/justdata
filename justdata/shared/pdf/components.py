"""
Reusable PDF flowable components for magazine-style reports.

Provides styled tables, callout boxes, source captions,
keep-together wrappers, section headers, data tables with
explicit column ordering, key findings, and AI narrative rendering.
"""

import re
from reportlab.platypus import (
    Table, Paragraph, Spacer, KeepTogether, Flowable, Image,
)
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white, Color
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.graphics.shapes import Drawing, Rect, String

from justdata.shared.pdf.styles import (
    HEADING_1, HEADING_2, HEADING_3,
    BODY_TEXT, BODY_TEXT_SMALL, SOURCE_CAPTION, TABLE_CAPTION,
    CALLOUT_TEXT, CALLOUT_TITLE,
    TABLE_HEADER_TEXT, TABLE_CELL_TEXT, TABLE_CELL_NUMBER,
    KEY_FINDING, AI_LABEL, LENDER_NAME_STYLE,
    NAVY, CALLOUT_BG, CALLOUT_BORDER,
    CENSUS_CALLOUT_BG, CENSUS_CALLOUT_BORDER,
    LIGHT_GRAY, MEDIUM_GRAY,
    BODY_FONT, BODY_FONT_BOLD,
    build_table_style, markdown_to_reportlab,
)
from justdata.shared.pdf.base_report import USABLE_WIDTH


# ---------------------------------------------------------------------------
# Heat map cell backgrounds
# ---------------------------------------------------------------------------
def get_heat_color(value, min_val, max_val):
    """Return a ReportLab Color for heat map background.

    Lighter values (low %) -> white/very light blue
    Higher values (high %) -> deeper blue
    """
    if value is None or max_val == min_val:
        return white
    try:
        v = float(value)
    except (ValueError, TypeError):
        return white

    intensity = (v - min_val) / (max_val - min_val)
    intensity = max(0.0, min(1.0, intensity))

    # Interpolate white -> soft blue (#B8D9EC)
    r = 1.0 - (intensity * 0.28)
    g = 1.0 - (intensity * 0.15)
    b = 1.0 - (intensity * 0.07)
    return Color(r, g, b)


# ---------------------------------------------------------------------------
# Pop vs Lending dual bars (Section 1 only)
# ---------------------------------------------------------------------------
def render_pop_vs_lending_bars(pop_share, lending_share, width=100, height=26):
    """Create a Drawing with two horizontal bars: orange=pop, blue=lending.

    Returns a ReportLab Drawing that can be placed in a Table cell.
    """
    d = Drawing(width, height)

    max_val = max(pop_share or 0, lending_share or 0, 1)
    bar_max_w = width - 32
    bar_h = 9

    # Orange bar (population) — top
    pop_w = (pop_share / max_val) * bar_max_w if pop_share else 0
    if pop_w > 0:
        d.add(Rect(0, height - bar_h - 2, pop_w, bar_h,
                    fillColor=HexColor('#E8883C'), strokeColor=None))
    if pop_share is not None:
        d.add(String(max(pop_w + 2, 0), height - bar_h - 1,
                      f'{pop_share:.1f}', fontSize=5.5,
                      fillColor=HexColor('#E8883C')))

    # Blue bar (lending) — bottom
    lend_w = (lending_share / max_val) * bar_max_w if lending_share else 0
    if lend_w > 0:
        d.add(Rect(0, 2, lend_w, bar_h,
                    fillColor=HexColor('#1a8fc9'), strokeColor=None))
    if lending_share is not None:
        d.add(String(max(lend_w + 2, 0), 3,
                      f'{lending_share:.1f}', fontSize=5.5,
                      fillColor=HexColor('#1a8fc9')))

    return d


# ---------------------------------------------------------------------------
# Change column with colored arrows
# ---------------------------------------------------------------------------
_CHANGE_STYLE = ParagraphStyle(
    'ChangeCell', fontName='Helvetica', fontSize=7, leading=9,
    alignment=TA_CENTER,
)


def format_change_cell(value, is_total_row=False):
    """Return a Paragraph with colored arrow + value for the Change column.

    For percentage rows: shows ▲/▼ +X.Xpp
    For total rows: shows ▲/▼ +X.X%
    """
    if value is None or value == '':
        return Paragraph('\u2014', _CHANGE_STYLE)  # em dash

    val_str = str(value).strip()
    cleaned = val_str.replace('%', '').replace('pp', '').replace('+', '').strip()
    try:
        num = float(cleaned)
    except (ValueError, TypeError):
        return Paragraph(val_str, _CHANGE_STYLE)

    suffix = '%' if is_total_row else 'pp'

    if abs(num) < 0.05:
        return Paragraph('0.0' + suffix, _CHANGE_STYLE)
    elif num > 0:
        text = f'<font color="#2196F3"><b>\u25b2</b> +{num:.1f}{suffix}</font>'
    else:
        text = f'<font color="#F44336"><b>\u25bc</b> \u2212{abs(num):.1f}{suffix}</font>'

    return Paragraph(text, _CHANGE_STYLE)


# ---------------------------------------------------------------------------
# Section headers
# ---------------------------------------------------------------------------
def section_header(text, level=1):
    """Return a Paragraph styled as a section heading."""
    style_map = {1: HEADING_1, 2: HEADING_2, 3: HEADING_3}
    style = style_map.get(level, HEADING_1)
    return Paragraph(text, style)


# ---------------------------------------------------------------------------
# Data table with explicit column ordering (v2 spec Section 7)
# ---------------------------------------------------------------------------
def build_data_table(data_rows, col_order, col_widths, header_labels=None,
                     use_paragraph_col0=False, repeat_header=True,
                     has_total_row=False):
    """
    Build a ReportLab Table with explicit column order and widths.

    Args:
        data_rows: list of dicts (keys match col_order entries)
        col_order: list of column key names in display order
        col_widths: list of floats (points) matching col_order length
        header_labels: optional list of display names (if different from col_order)
        use_paragraph_col0: if True, wrap first column values in Paragraph() for word wrap
        repeat_header: if True, repeat header row on page splits
        has_total_row: if True, bold the first data row and add bottom border
    """
    if not data_rows:
        return Spacer(1, 0)

    headers = header_labels or col_order

    # Build header row
    header_row = [Paragraph(str(h), TABLE_HEADER_TEXT) for h in headers]

    # Build data rows IN THE ORDER SPECIFIED
    table_data = [header_row]
    for row_dict in data_rows:
        row = []
        for i, col_key in enumerate(col_order):
            value = row_dict.get(col_key, '')
            if value is None:
                value = ''
            if i == 0 and use_paragraph_col0:
                row.append(Paragraph(str(value), TABLE_CELL_TEXT))
            else:
                row.append(str(value))
        table_data.append(row)

    num_rows = len(table_data)

    table = Table(
        table_data,
        colWidths=col_widths,
        repeatRows=1 if repeat_header else 0,
        hAlign='LEFT',
    )
    table.setStyle(build_table_style(
        has_total_row=has_total_row,
        num_rows=num_rows,
    ))

    return table


# ---------------------------------------------------------------------------
# Legacy styled table (kept for backward compat)
# ---------------------------------------------------------------------------
def build_styled_table(headers, rows, col_widths=None, has_total_row=False,
                       number_cols=None, right_align_from=1):
    """Build a ReportLab Table with magazine-style formatting."""
    if not rows:
        return Spacer(1, 0)

    header_cells = [Paragraph(str(h), TABLE_HEADER_TEXT) for h in headers]

    if number_cols is None:
        number_cols = set(range(right_align_from, len(headers)))

    data_rows = []
    for row in rows:
        cells = []
        for ci, val in enumerate(row):
            style = TABLE_CELL_NUMBER if ci in number_cols else TABLE_CELL_TEXT
            cells.append(Paragraph(str(val) if val is not None else '', style))
        data_rows.append(cells)

    table_data = [header_cells] + data_rows
    num_rows = len(table_data)

    tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(build_table_style(
        has_total_row=has_total_row,
        num_rows=num_rows,
    ))

    return tbl


# ---------------------------------------------------------------------------
# Callout box
# ---------------------------------------------------------------------------
class CalloutBox(Flowable):
    """A flowable that renders a colored box with a left accent border."""

    def __init__(self, content_flowables, style='findings', width=None):
        super().__init__()
        if style == 'census':
            self.bg_color = CENSUS_CALLOUT_BG
            self.border_color = CENSUS_CALLOUT_BORDER
        else:
            self.bg_color = CALLOUT_BG
            self.border_color = CALLOUT_BORDER

        self.content_flowables = content_flowables
        self._width = width
        self._frame_width = None

    def wrap(self, availWidth, availHeight):
        self._frame_width = self._width or availWidth
        inner_w = self._frame_width - 18  # 4px border + 14px padding

        total_h = 16  # top + bottom padding
        for f in self.content_flowables:
            w, h = f.wrap(inner_w, availHeight)
            total_h += h
        self.height = total_h
        self.width = self._frame_width
        return self.width, self.height

    def draw(self):
        canvas = self.canv
        canvas.saveState()

        # Background
        canvas.setFillColor(self.bg_color)
        canvas.rect(0, 0, self.width, self.height, fill=1, stroke=0)

        # Left border
        canvas.setFillColor(self.border_color)
        canvas.rect(0, 0, 4, self.height, fill=1, stroke=0)

        # Draw content flowables top-down
        y = self.height - 8  # top padding
        for f in self.content_flowables:
            inner_w = self.width - 18
            w, h = f.wrap(inner_w, self.height)
            y -= h
            f.drawOn(canvas, 14, y)

        canvas.restoreState()


def build_callout_box(content, title=None, style='findings', width=None):
    """Build a callout box from text content."""
    flowables = []
    if title:
        flowables.append(Paragraph(title, CALLOUT_TITLE))
    if content:
        for para in str(content).split('\n\n'):
            para = para.strip()
            if para:
                flowables.append(Paragraph(para, CALLOUT_TEXT))

    return CalloutBox(flowables, style=style, width=width)


# ---------------------------------------------------------------------------
# Key Findings rendering (v2 spec Section 9)
# ---------------------------------------------------------------------------
def build_key_findings(findings_text):
    """Build Key Findings callout box with proper markdown rendering."""
    if not findings_text:
        return Spacer(1, 0)

    lines = findings_text.strip().split('\n')
    finding_flowables = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Strip bullet markers
        line = re.sub(r'^[\-\*•]\s*', '', line)
        # Strip numbered list markers (1. 2. etc.)
        line = re.sub(r'^\d+\.\s*', '', line)
        # Convert markdown
        line = markdown_to_reportlab(line)
        if line:
            finding_flowables.append(
                Paragraph(f'&bull; {line}', KEY_FINDING)
            )

    if not finding_flowables:
        return Spacer(1, 0)

    from reportlab.platypus import TableStyle as TS
    callout = Table(
        [[finding_flowables]],
        colWidths=[USABLE_WIDTH - 18],
        style=TS([
            ('BACKGROUND', (0, 0), (-1, -1), CALLOUT_BG),
            ('LEFTPADDING', (0, 0), (-1, -1), 16),
            ('RIGHTPADDING', (0, 0), (-1, -1), 14),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('LINEBEFORE', (0, 0), (0, -1), 4, NAVY),
        ])
    )
    return callout


# ---------------------------------------------------------------------------
# AI narrative rendering (v2 spec Section 8)
# ---------------------------------------------------------------------------
def ai_narrative_to_flowables(narrative_text, style=None):
    """Convert AI narrative text into list of Paragraph flowables."""
    if not narrative_text:
        return []

    style = style or BODY_TEXT
    flowables = []

    # Split on double newline (paragraph breaks)
    paragraphs = re.split(r'\n\s*\n', narrative_text)

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        converted = markdown_to_reportlab(para)
        if converted:
            # Convert single newlines to <br/> for readability
            converted = converted.replace('\n', '<br/>')
            flowables.append(Paragraph(converted, style))

    return flowables


# ---------------------------------------------------------------------------
# Source caption
# ---------------------------------------------------------------------------
def build_source_caption(text):
    """Return a small italic caption paragraph."""
    return Paragraph(text, SOURCE_CAPTION)


# ---------------------------------------------------------------------------
# Keep-together wrapper
# ---------------------------------------------------------------------------
def keep_together_block(elements):
    """Wrap a list of flowables in KeepTogether to avoid page splits."""
    return KeepTogether(elements)


# ---------------------------------------------------------------------------
# Narrative text helper (legacy, uses markdown conversion now)
# ---------------------------------------------------------------------------
def narrative_paragraphs(text, style=None):
    """Convert a block of text into a list of Paragraph flowables."""
    if not text:
        return []
    style = style or BODY_TEXT
    paragraphs = []
    for para in str(text).split('\n\n'):
        para = para.strip()
        if para:
            converted = markdown_to_reportlab(para)
            converted = converted.replace('\n', '<br/>')
            paragraphs.append(Paragraph(converted, style))
    return paragraphs
