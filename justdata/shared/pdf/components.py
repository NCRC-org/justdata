"""
Reusable PDF flowable components for magazine-style reports.

Provides styled tables, callout boxes, source captions,
keep-together wrappers, and section headers.
"""

from reportlab.platypus import (
    Table, Paragraph, Spacer, KeepTogether, Flowable,
)
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor

from justdata.shared.pdf.styles import (
    HEADING_1, HEADING_2, HEADING_3,
    BODY_TEXT, BODY_TEXT_SMALL, SOURCE_CAPTION,
    CALLOUT_TEXT, CALLOUT_TITLE,
    TABLE_HEADER_TEXT, TABLE_CELL_TEXT, TABLE_CELL_NUMBER,
    NAVY, CALLOUT_BG, CALLOUT_BORDER,
    CENSUS_CALLOUT_BG, CENSUS_CALLOUT_BORDER,
    LIGHT_GRAY, MEDIUM_GRAY,
    BODY_FONT, BODY_FONT_BOLD,
    build_table_style,
)


# ---------------------------------------------------------------------------
# Section headers
# ---------------------------------------------------------------------------
def section_header(text, level=1):
    """Return a Paragraph styled as a section heading."""
    style_map = {1: HEADING_1, 2: HEADING_2, 3: HEADING_3}
    style = style_map.get(level, HEADING_1)
    return Paragraph(text, style)


# ---------------------------------------------------------------------------
# Styled data table
# ---------------------------------------------------------------------------
def build_styled_table(headers, rows, col_widths=None, has_total_row=False,
                       number_cols=None, right_align_from=1):
    """
    Build a ReportLab Table with magazine-style formatting.

    Parameters
    ----------
    headers : list[str]
    rows : list[list[str]]
    col_widths : list[float] or None — explicit column widths in points
    has_total_row : bool — if True, bold/separate the last row
    number_cols : set[int] or None — column indices to right-align
    right_align_from : int — auto right-align columns from this index onward
                       (ignored if number_cols is provided)
    """
    if not rows:
        return Spacer(1, 0)

    # Wrap header text
    header_cells = [Paragraph(str(h), TABLE_HEADER_TEXT) for h in headers]

    # Determine which columns are numeric
    if number_cols is None:
        number_cols = set(range(right_align_from, len(headers)))

    # Wrap data cells
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
    """
    A flowable that renders a colored box with a left accent border.

    Styles: 'findings' (blue) or 'census' (green).
    """

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

        # Wrap each flowable to compute height
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
    """
    Build a callout box from text content.

    Parameters
    ----------
    content : str — the text body (may contain simple HTML tags)
    title : str or None — optional bold title
    style : 'findings' or 'census'
    width : float or None — explicit width; defaults to available frame width
    """
    flowables = []
    if title:
        flowables.append(Paragraph(title, CALLOUT_TITLE))
    if content:
        # Split on double newlines to create paragraphs
        for para in str(content).split('\n\n'):
            para = para.strip()
            if para:
                flowables.append(Paragraph(para, CALLOUT_TEXT))

    return CalloutBox(flowables, style=style, width=width)


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
# Narrative text helper
# ---------------------------------------------------------------------------
def narrative_paragraphs(text, style=None):
    """
    Convert a block of text (possibly with newlines) into a list
    of Paragraph flowables.
    """
    if not text:
        return []
    style = style or BODY_TEXT
    paragraphs = []
    for para in str(text).split('\n\n'):
        para = para.strip()
        if para:
            # Convert single newlines to <br/> for readability
            para = para.replace('\n', '<br/>')
            paragraphs.append(Paragraph(para, style))
    return paragraphs
