"""
Magazine-style PDF report styles.

Defines all ParagraphStyle, TableStyle, color constants, and font constants
used by the shared PDF report framework.
"""

import re
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.units import inch
from reportlab.platypus import TableStyle

# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------
NAVY = HexColor('#1e3a5f')
DARK_NAVY = HexColor('#0f2440')
BODY_COLOR = HexColor('#333333')
DARK_GRAY = HexColor('#666666')
LIGHT_GRAY = HexColor('#f5f6f8')
MEDIUM_GRAY = HexColor('#e0e0e0')
ACCENT_BLUE = HexColor('#1a8fc9')
MUTED_GREEN = HexColor('#2d8659')
HEADER_BG = HexColor('#1e3a5f')
ALT_ROW_BG = HexColor('#f7f8fa')
CALLOUT_BG = HexColor('#eef4fa')
CALLOUT_BORDER = HexColor('#1e3a5f')
CENSUS_CALLOUT_BG = HexColor('#f0f7ee')
CENSUS_CALLOUT_BORDER = HexColor('#2d8659')
RULE_COLOR = HexColor('#cccccc')
SOURCE_COLOR = HexColor('#999999')

# ---------------------------------------------------------------------------
# Font constants
# ---------------------------------------------------------------------------
HEADLINE_FONT = 'Times-Roman'
HEADLINE_FONT_BOLD = 'Times-Bold'
BODY_FONT = 'Helvetica'
BODY_FONT_BOLD = 'Helvetica-Bold'
BODY_FONT_ITALIC = 'Helvetica-Oblique'
BODY_FONT_BOLD_ITALIC = 'Helvetica-BoldOblique'

# ---------------------------------------------------------------------------
# Paragraph styles
# ---------------------------------------------------------------------------
_base = getSampleStyleSheet()


def _style(name, **kw):
    """Create a ParagraphStyle with sensible defaults."""
    defaults = dict(
        fontName=BODY_FONT,
        fontSize=10,
        leading=14,
        textColor=BODY_COLOR,
        spaceAfter=6,
    )
    defaults.update(kw)
    return ParagraphStyle(name, **defaults)


# ---------------------------------------------------------------------------
# Cover page styles
# ---------------------------------------------------------------------------
COVER_TITLE = _style(
    'CoverTitle',
    fontName=HEADLINE_FONT_BOLD,
    fontSize=32,
    leading=38,
    textColor=white,
    alignment=TA_LEFT,
    spaceAfter=12,
)

COVER_SUBTITLE = _style(
    'CoverSubtitle',
    fontName=BODY_FONT,
    fontSize=16,
    leading=22,
    textColor=HexColor('#c0d0e0'),
    alignment=TA_LEFT,
    spaceAfter=8,
)

COVER_DATE = _style(
    'CoverDate',
    fontName=BODY_FONT,
    fontSize=12,
    leading=16,
    textColor=HexColor('#a0b8d0'),
    alignment=TA_LEFT,
    spaceAfter=4,
)

COVER_META = _style(
    'CoverMeta',
    fontName=BODY_FONT,
    fontSize=10,
    leading=14,
    textColor=DARK_GRAY,
    alignment=TA_CENTER,
    spaceAfter=4,
)

COVER_DISCLAIMER = _style(
    'CoverDisclaimer',
    fontName=BODY_FONT,
    fontSize=8,
    leading=10,
    textColor=HexColor('#888888'),
    alignment=TA_CENTER,
    spaceAfter=0,
)

# ---------------------------------------------------------------------------
# Section headings
# ---------------------------------------------------------------------------
HEADING_1 = _style(
    'MagHeading1',
    fontName=HEADLINE_FONT_BOLD,
    fontSize=20,
    leading=24,
    textColor=NAVY,
    spaceBefore=18,
    spaceAfter=10,
)

HEADING_2 = _style(
    'MagHeading2',
    fontName=HEADLINE_FONT_BOLD,
    fontSize=15,
    leading=19,
    textColor=NAVY,
    spaceBefore=14,
    spaceAfter=8,
)

HEADING_3 = _style(
    'MagHeading3',
    fontName=BODY_FONT_BOLD,
    fontSize=12,
    leading=16,
    textColor=NAVY,
    spaceBefore=10,
    spaceAfter=6,
)

# ---------------------------------------------------------------------------
# Body text
# ---------------------------------------------------------------------------
BODY_TEXT = _style(
    'MagBody',
    fontName=BODY_FONT,
    fontSize=12,
    leading=16,
    textColor=BODY_COLOR,
    alignment=TA_JUSTIFY,
    spaceAfter=6,
)

BODY_TEXT_SMALL = _style(
    'MagBodySmall',
    fontName=BODY_FONT,
    fontSize=10,
    leading=13.5,
    textColor=BODY_COLOR,
    alignment=TA_JUSTIFY,
    spaceAfter=4,
)

# ---------------------------------------------------------------------------
# AI narrative label
# ---------------------------------------------------------------------------
AI_LABEL = _style(
    'AILabel',
    fontName=BODY_FONT_BOLD,
    fontSize=9,
    leading=12,
    textColor=ACCENT_BLUE,
    spaceAfter=6,
    spaceBefore=4,
)

# ---------------------------------------------------------------------------
# Key findings style
# ---------------------------------------------------------------------------
KEY_FINDING = _style(
    'KeyFinding',
    fontName=BODY_FONT,
    fontSize=13,
    leading=17,
    textColor=BODY_COLOR,
    alignment=TA_LEFT,
    spaceAfter=4,
    leftIndent=12,
)

# ---------------------------------------------------------------------------
# Callout / findings
# ---------------------------------------------------------------------------
CALLOUT_TEXT = _style(
    'CalloutText',
    fontName=BODY_FONT,
    fontSize=10,
    leading=14,
    textColor=BODY_COLOR,
    alignment=TA_LEFT,
    spaceAfter=4,
)

CALLOUT_TITLE = _style(
    'CalloutTitle',
    fontName=BODY_FONT_BOLD,
    fontSize=11,
    leading=15,
    textColor=NAVY,
    spaceAfter=4,
)

# ---------------------------------------------------------------------------
# Source / caption
# ---------------------------------------------------------------------------
SOURCE_CAPTION = _style(
    'SourceCaption',
    fontName=BODY_FONT_ITALIC,
    fontSize=9,
    leading=12,
    textColor=SOURCE_COLOR,
    spaceAfter=8,
)

TABLE_CAPTION = _style(
    'TableCaption',
    fontName=BODY_FONT_ITALIC,
    fontSize=9,
    leading=12,
    textColor=SOURCE_COLOR,
    spaceAfter=8,
)

# ---------------------------------------------------------------------------
# Table header / cell text
# ---------------------------------------------------------------------------
TABLE_HEADER_TEXT = _style(
    'TableHeaderText',
    fontName=BODY_FONT_BOLD,
    fontSize=10,
    leading=12,
    textColor=white,
    alignment=TA_CENTER,
)

TABLE_CELL_TEXT = _style(
    'TableCellText',
    fontName=BODY_FONT,
    fontSize=9.5,
    leading=12,
    textColor=BODY_COLOR,
    alignment=TA_LEFT,
)

TABLE_CELL_NUMBER = _style(
    'TableCellNumber',
    fontName=BODY_FONT,
    fontSize=9.5,
    leading=12,
    textColor=BODY_COLOR,
    alignment=TA_RIGHT,
)

LENDER_NAME_STYLE = _style(
    'LenderName',
    fontName=BODY_FONT_BOLD,
    fontSize=9.5,
    leading=12,
    textColor=DARK_GRAY,
    alignment=TA_LEFT,
)

# ---------------------------------------------------------------------------
# Footer / header
# ---------------------------------------------------------------------------
RUNNING_HEADER = _style(
    'RunningHeader',
    fontName=BODY_FONT,
    fontSize=8,
    leading=10,
    textColor=DARK_GRAY,
)

RUNNING_FOOTER = _style(
    'RunningFooter',
    fontName=BODY_FONT,
    fontSize=8.5,
    leading=11,
    textColor=SOURCE_COLOR,
)

# ---------------------------------------------------------------------------
# Methods section
# ---------------------------------------------------------------------------
METHODS_TEXT = _style(
    'MethodsText',
    fontName=BODY_FONT,
    fontSize=10,
    leading=13.5,
    textColor=DARK_GRAY,
    alignment=TA_JUSTIFY,
    spaceAfter=4,
)


# ---------------------------------------------------------------------------
# Table style builder
# ---------------------------------------------------------------------------
def build_table_style(
    header_bg=HEADER_BG,
    header_text=white,
    alt_row_bg=ALT_ROW_BG,
    grid_color=MEDIUM_GRAY,
    has_total_row=False,
    num_rows=0,
):
    """
    Build a ReportLab TableStyle for magazine-style tables.
    """
    cmds = [
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), header_bg),
        ('TEXTCOLOR', (0, 0), (-1, 0), header_text),
        ('FONTNAME', (0, 0), (-1, 0), BODY_FONT_BOLD),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),

        # Data rows
        ('FONTNAME', (0, 1), (-1, -1), BODY_FONT),
        ('FONTSIZE', (0, 1), (-1, -1), 9.5),
        ('TOPPADDING', (0, 1), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),

        # Grid
        ('LINEBELOW', (0, 0), (-1, 0), 1.0, header_bg),
        ('LINEBELOW', (0, 1), (-1, -2), 0.4, grid_color),
        ('LINEBELOW', (0, -1), (-1, -1), 0.8, grid_color),

        # Alignment — first column left, rest center
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]

    # Alternating row colors — only up to actual row count
    if num_rows > 1:
        for i in range(2, num_rows, 2):
            cmds.append(('BACKGROUND', (0, i), (-1, i), alt_row_bg))

    # Total row (first data row after header, typically row index 1)
    if has_total_row and num_rows > 1:
        cmds.extend([
            ('FONTNAME', (0, 1), (-1, 1), BODY_FONT_BOLD),
            ('LINEBELOW', (0, 1), (-1, 1), 2.0, header_bg),
        ])

    return TableStyle(cmds)


# ---------------------------------------------------------------------------
# Markdown to ReportLab markup converter
# ---------------------------------------------------------------------------
def markdown_to_reportlab(text):
    """
    Convert basic markdown to ReportLab paragraph markup.
    Handles: **bold**, *italic*, bullet lists, ## headers, [links](url)
    """
    if not text:
        return ''

    # Remove ## headers (we add section titles separately)
    text = re.sub(r'^##\s+.*', '', text, flags=re.MULTILINE)

    # Bold: **text** → <b>text</b>
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)

    # Italic: *text* → <i>text</i>
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)

    # Links: [text](url) → <a href="url">text</a>
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" color="#1a8fc9">\1</a>', text)

    # Bullet points: lines starting with "• " or "- " or "* "
    text = re.sub(r'^[\-\*•]\s+', '&bull; ', text, flags=re.MULTILINE)

    # Clean up extra whitespace
    text = text.strip()

    return text
