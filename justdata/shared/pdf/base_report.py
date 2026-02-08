"""
Magazine-style PDF document template.

Provides MagazineDocTemplate with four page templates:
  cover       — full-width, no header/footer
  two_column  — two-column text flow with header/footer
  full_width  — single-frame full-width with header/footer
  landscape   — 11×8.5 single-frame with header/footer
"""

from io import BytesIO
from datetime import datetime

from reportlab.lib.pagesizes import letter, landscape as landscape_size
from reportlab.lib.units import inch
from reportlab.lib.colors import white
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer,
    NextPageTemplate, PageBreak, CondPageBreak,
)
from reportlab.lib.enums import TA_LEFT

from justdata.shared.pdf.styles import (
    NAVY, DARK_NAVY, RULE_COLOR, SOURCE_COLOR, DARK_GRAY,
    COVER_TITLE, COVER_SUBTITLE, COVER_META,
    BODY_FONT, BODY_FONT_BOLD, HEADLINE_FONT_BOLD,
)

# ---------------------------------------------------------------------------
# Page geometry — letter portrait
# ---------------------------------------------------------------------------
PAGE_W, PAGE_H = letter  # 612 × 792
MARGIN_LEFT = 0.65 * inch
MARGIN_RIGHT = 0.65 * inch
MARGIN_TOP = 0.75 * inch
MARGIN_BOTTOM = 0.70 * inch
GUTTER = 0.30 * inch

CONTENT_W = PAGE_W - MARGIN_LEFT - MARGIN_RIGHT
COL_W = (CONTENT_W - GUTTER) / 2.0

HEADER_Y = PAGE_H - 0.50 * inch
FOOTER_Y = 0.45 * inch

# Landscape geometry
L_PAGE_W, L_PAGE_H = landscape_size(letter)  # 792 × 612
L_CONTENT_W = L_PAGE_W - MARGIN_LEFT - MARGIN_RIGHT


# ---------------------------------------------------------------------------
# Header / footer drawing
# ---------------------------------------------------------------------------
def _draw_header_footer(canvas, doc):
    """Draw running header and footer on non-cover pages."""
    canvas.saveState()

    page_w = canvas._pagesize[0]
    page_h = canvas._pagesize[1]
    m_left = MARGIN_LEFT
    m_right = MARGIN_RIGHT

    # Header rule
    header_y = page_h - 0.50 * inch
    canvas.setStrokeColor(RULE_COLOR)
    canvas.setLineWidth(0.5)
    canvas.line(m_left, header_y, page_w - m_right, header_y)

    # Header text
    canvas.setFont(BODY_FONT_BOLD, 8)
    canvas.setFillColor(DARK_GRAY)
    app_name = getattr(doc, 'app_name', 'LendSight')
    canvas.drawString(m_left, header_y + 4, app_name)

    canvas.setFont(BODY_FONT, 7)
    canvas.drawRightString(page_w - m_right, header_y + 4, 'NCRC')

    # Footer rule
    footer_y = 0.50 * inch
    canvas.line(m_left, footer_y, page_w - m_right, footer_y)

    # Footer text
    canvas.setFont(BODY_FONT, 7)
    canvas.setFillColor(SOURCE_COLOR)
    source = getattr(doc, 'footer_source', 'Source: HMDA, U.S. Census Bureau')
    canvas.drawString(m_left, footer_y - 10, source)

    page_num = canvas.getPageNumber()
    canvas.drawRightString(page_w - m_right, footer_y - 10, f'Page {page_num}')

    canvas.restoreState()


def _draw_cover(canvas, doc):
    """Draw cover page background — no running header/footer."""
    canvas.saveState()
    # Full navy band across top 45%
    band_height = PAGE_H * 0.50
    canvas.setFillColor(DARK_NAVY)
    canvas.rect(0, PAGE_H - band_height, PAGE_W, band_height, fill=1, stroke=0)

    # Thin accent line at bottom of band
    canvas.setStrokeColor(NAVY)
    canvas.setLineWidth(3)
    canvas.line(0, PAGE_H - band_height, PAGE_W, PAGE_H - band_height)

    # Footer on cover: just the date
    canvas.setFont(BODY_FONT, 7)
    canvas.setFillColor(SOURCE_COLOR)
    canvas.drawString(MARGIN_LEFT, 0.45 * inch,
                      f'Generated {datetime.now().strftime("%B %d, %Y")}')
    canvas.restoreState()


# ---------------------------------------------------------------------------
# MagazineDocTemplate
# ---------------------------------------------------------------------------
class MagazineDocTemplate(BaseDocTemplate):
    """
    Multi-template document for magazine-style PDF reports.

    Usage:
        buf = BytesIO()
        doc = MagazineDocTemplate(buf, app_name='LendSight')
        doc.build(story)
        pdf_bytes = buf.getvalue()
    """

    def __init__(self, filename_or_buf, app_name='LendSight',
                 footer_source='Source: HMDA, U.S. Census Bureau', **kw):
        self.app_name = app_name
        self.footer_source = footer_source

        kw.setdefault('pagesize', letter)
        kw.setdefault('leftMargin', MARGIN_LEFT)
        kw.setdefault('rightMargin', MARGIN_RIGHT)
        kw.setdefault('topMargin', MARGIN_TOP)
        kw.setdefault('bottomMargin', MARGIN_BOTTOM)
        kw.setdefault('title', f'{app_name} Report')
        kw.setdefault('author', 'NCRC')

        super().__init__(filename_or_buf, **kw)
        self._build_templates()

    def _build_templates(self):
        """Create the four page templates."""
        # Frame IDs help debugging
        # --- Cover (single full-width frame, placed in the navy band area) ---
        cover_frame = Frame(
            MARGIN_LEFT, MARGIN_BOTTOM,
            CONTENT_W, PAGE_H - MARGIN_TOP - MARGIN_BOTTOM,
            id='cover_frame',
            leftPadding=0, rightPadding=0,
            topPadding=0, bottomPadding=0,
        )
        cover_tpl = PageTemplate(
            id='cover',
            frames=[cover_frame],
            onPage=_draw_cover,
            pagesize=letter,
        )

        # --- Two-column ---
        frame_top = PAGE_H - MARGIN_TOP - 14  # leave room below header rule
        frame_h = frame_top - MARGIN_BOTTOM

        left_frame = Frame(
            MARGIN_LEFT, MARGIN_BOTTOM,
            COL_W, frame_h,
            id='left_col',
            leftPadding=0, rightPadding=4,
            topPadding=0, bottomPadding=0,
        )
        right_frame = Frame(
            MARGIN_LEFT + COL_W + GUTTER, MARGIN_BOTTOM,
            COL_W, frame_h,
            id='right_col',
            leftPadding=4, rightPadding=0,
            topPadding=0, bottomPadding=0,
        )
        two_col_tpl = PageTemplate(
            id='two_column',
            frames=[left_frame, right_frame],
            onPage=_draw_header_footer,
            pagesize=letter,
        )

        # --- Full-width ---
        full_frame = Frame(
            MARGIN_LEFT, MARGIN_BOTTOM,
            CONTENT_W, frame_h,
            id='full_frame',
            leftPadding=0, rightPadding=0,
            topPadding=0, bottomPadding=0,
        )
        full_tpl = PageTemplate(
            id='full_width',
            frames=[full_frame],
            onPage=_draw_header_footer,
            pagesize=letter,
        )

        # --- Landscape ---
        l_frame_top = L_PAGE_H - MARGIN_TOP - 14
        l_frame_h = l_frame_top - MARGIN_BOTTOM
        landscape_frame = Frame(
            MARGIN_LEFT, MARGIN_BOTTOM,
            L_CONTENT_W, l_frame_h,
            id='landscape_frame',
            leftPadding=0, rightPadding=0,
            topPadding=0, bottomPadding=0,
        )
        landscape_tpl = PageTemplate(
            id='landscape',
            frames=[landscape_frame],
            onPage=_draw_header_footer,
            pagesize=landscape_size(letter),
        )

        self.addPageTemplates([cover_tpl, two_col_tpl, full_tpl, landscape_tpl])


# ---------------------------------------------------------------------------
# Cover page flowables builder
# ---------------------------------------------------------------------------
def build_cover_page(title, subtitle='', date_range='', metadata=None):
    """
    Return a list of flowables for the cover page.

    Parameters
    ----------
    title : str — main report title (e.g. "Mortgage Lending Analysis")
    subtitle : str — e.g. county names
    date_range : str — e.g. "2019 – 2023"
    metadata : dict — optional extra info (loan_purpose, etc.)
    """
    story = []

    # Push content down into the navy band area
    story.append(Spacer(1, PAGE_H * 0.15))

    story.append(Paragraph(title, COVER_TITLE))
    if subtitle:
        story.append(Spacer(1, 6))
        story.append(Paragraph(subtitle, COVER_SUBTITLE))
    if date_range:
        story.append(Spacer(1, 8))
        story.append(Paragraph(date_range, COVER_META))

    if metadata:
        story.append(Spacer(1, 12))
        loan_purpose = metadata.get('loan_purpose', '')
        if isinstance(loan_purpose, list):
            loan_purpose = ', '.join(str(lp).replace('_', ' ').title() for lp in loan_purpose)
        if loan_purpose:
            story.append(Paragraph(f'Loan Purpose: {loan_purpose}', COVER_META))

        counties = metadata.get('counties', [])
        if isinstance(counties, list) and len(counties) > 1:
            story.append(Paragraph(f'Counties: {len(counties)}', COVER_META))

    # Push to next page after cover
    story.append(NextPageTemplate('full_width'))
    story.append(PageBreak())

    return story
