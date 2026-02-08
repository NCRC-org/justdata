"""
Magazine-style PDF document template.

Provides MagazineDocTemplate with four page templates:
  cover       — full-width, no header/footer
  two_column  — two-column text flow with header/footer
  full_width  — single-frame full-width with header/footer
  landscape   — 11x8.5 single-frame with header/footer
"""

import os
from io import BytesIO
from datetime import datetime

from reportlab.lib.pagesizes import letter, landscape as landscape_size
from reportlab.lib.units import inch
from reportlab.lib.colors import white, Color
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer,
    NextPageTemplate, PageBreak, CondPageBreak,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

from justdata.shared.pdf.styles import (
    NAVY, DARK_NAVY, RULE_COLOR, SOURCE_COLOR, DARK_GRAY,
    COVER_TITLE, COVER_SUBTITLE, COVER_DATE, COVER_META, COVER_DISCLAIMER,
    BODY_FONT, BODY_FONT_BOLD, HEADLINE_FONT_BOLD,
)

# Logo path
ASSETS_DIR = os.path.join(os.path.dirname(__file__), 'assets')
LOGO_WHITE_PATH = os.path.join(ASSETS_DIR, 'justdata_logo_white.png')

# ---------------------------------------------------------------------------
# Page geometry — letter portrait (per v2 spec Section 2)
# ---------------------------------------------------------------------------
PAGE_W, PAGE_H = letter  # 612 x 792 pt
MARGIN_LEFT = 0.65 * inch    # 46.8 pt
MARGIN_RIGHT = 0.65 * inch
MARGIN_TOP = 0.6 * inch      # 43.2 pt
MARGIN_BOTTOM = 0.6 * inch
HEADER_HEIGHT = 0.45 * inch  # 32.4 pt
FOOTER_HEIGHT = 0.35 * inch  # 25.2 pt
GUTTER = 0.25 * inch         # 18 pt

USABLE_WIDTH = PAGE_W - MARGIN_LEFT - MARGIN_RIGHT  # ~518.4 pt
CONTENT_W = USABLE_WIDTH  # alias for backward compat
CONTENT_HEIGHT = PAGE_H - MARGIN_TOP - MARGIN_BOTTOM - HEADER_HEIGHT - FOOTER_HEIGHT
COL_W = (USABLE_WIDTH - GUTTER) / 2.0  # ~250.2 pt

# Landscape geometry
L_PAGE_W, L_PAGE_H = landscape_size(letter)  # 792 x 612
L_CONTENT_W = L_PAGE_W - MARGIN_LEFT - MARGIN_RIGHT  # ~698.4 pt
L_USABLE_WIDTH = L_CONTENT_W  # alias


# ---------------------------------------------------------------------------
# Header / footer drawing (per v2 spec Section 4)
# ---------------------------------------------------------------------------
def _draw_header_footer(canvas, doc):
    """Draw running header and footer on non-cover pages."""
    canvas.saveState()

    page_w = canvas._pagesize[0]
    page_h = canvas._pagesize[1]
    m_left = MARGIN_LEFT
    m_right = MARGIN_RIGHT

    # --- Header ---
    header_text_y = page_h - MARGIN_TOP + 4
    header_rule_y = header_text_y - 6

    # Header text
    canvas.setFont(BODY_FONT, 8)
    canvas.setFillColor(DARK_GRAY)
    app_name = getattr(doc, 'app_name', 'LendSight')
    canvas.drawString(m_left, header_text_y, app_name)
    canvas.drawRightString(page_w - m_right, header_text_y, 'NCRC')

    # Header rule
    canvas.setStrokeColor(RULE_COLOR)
    canvas.setLineWidth(0.5)
    canvas.line(m_left, header_rule_y, page_w - m_right, header_rule_y)

    # --- Footer ---
    footer_rule_y = MARGIN_BOTTOM + FOOTER_HEIGHT - 12 + 14
    footer_text_y = MARGIN_BOTTOM + FOOTER_HEIGHT - 12

    # Footer rule
    canvas.line(m_left, footer_rule_y, page_w - m_right, footer_rule_y)

    # Footer text
    canvas.setFont(BODY_FONT, 8)
    canvas.setFillColor(DARK_GRAY)
    source = getattr(doc, 'footer_source', 'Source: HMDA, U.S. Census Bureau')
    canvas.drawString(m_left, footer_text_y, source)

    # Page number: doc.page - 1 so first content page shows "Page 1"
    page_num = doc.page - 1
    if page_num > 0:
        canvas.drawRightString(page_w - m_right, footer_text_y, f'Page {page_num}')

    canvas.restoreState()


def _draw_cover(canvas, doc):
    """Draw cover page with gradient background, centered text, and logo."""
    canvas.saveState()

    # --- Gradient background ---
    # Top 58%: teal → navy → dark navy gradient
    # Bottom 42%: solid dark navy
    teal = (0 / 255, 164 / 255, 214 / 255)
    navy_rgb = (30 / 255, 58 / 255, 95 / 255)
    dark_navy_rgb = (13 / 255, 31 / 255, 51 / 255)

    gradient_height = PAGE_H * 0.58
    gradient_bottom = PAGE_H - gradient_height

    # Bottom solid area (dark navy)
    canvas.setFillColor(Color(*dark_navy_rgb))
    canvas.rect(0, 0, PAGE_W, gradient_bottom, fill=1, stroke=0)

    # Gradient area with horizontal strips
    n_strips = 40
    strip_h = gradient_height / n_strips
    for i in range(n_strips):
        t = i / max(n_strips - 1, 1)  # 0 at top, 1 at bottom
        if t < 0.55:
            s = t / 0.55
            r = teal[0] + (navy_rgb[0] - teal[0]) * s
            g = teal[1] + (navy_rgb[1] - teal[1]) * s
            b = teal[2] + (navy_rgb[2] - teal[2]) * s
        else:
            s = (t - 0.55) / 0.45
            r = navy_rgb[0] + (dark_navy_rgb[0] - navy_rgb[0]) * s
            g = navy_rgb[1] + (dark_navy_rgb[1] - navy_rgb[1]) * s
            b = navy_rgb[2] + (dark_navy_rgb[2] - navy_rgb[2]) * s
        canvas.setFillColor(Color(r, g, b))
        y = PAGE_H - (i + 1) * strip_h
        canvas.rect(0, y, PAGE_W, strip_h + 0.5, fill=1, stroke=0)

    # --- Logo (top left) ---
    try:
        if os.path.exists(LOGO_WHITE_PATH):
            logo_w = 1.4 * inch
            logo_h = logo_w / 4.5  # approximate aspect ratio
            canvas.drawImage(
                LOGO_WHITE_PATH,
                MARGIN_LEFT, PAGE_H - 28 - logo_h,
                width=logo_w, height=logo_h,
                mask='auto',
            )
    except Exception:
        pass  # graceful fallback if logo missing

    # --- Centered cover text ---
    cx = PAGE_W / 2

    # "LendSight Report" label
    y = PAGE_H * 0.78
    canvas.setFont(BODY_FONT, 11)
    canvas.setFillColor(Color(1, 1, 1, 0.6))
    canvas.drawCentredString(cx, y, 'LendSight Report')

    # Main title
    title = getattr(doc, 'cover_title', 'Mortgage Lending Analysis')
    y -= 30
    canvas.setFont(HEADLINE_FONT_BOLD, 28)
    canvas.setFillColor(white)
    # Handle multi-line title
    for line in title.split('\n'):
        canvas.drawCentredString(cx, y, line)
        y -= 34

    # Subtitle (county/location)
    subtitle = getattr(doc, 'cover_subtitle', '')
    if subtitle:
        y -= 2
        canvas.setFont(HEADLINE_FONT_BOLD, 17)
        canvas.setFillColor(Color(1, 1, 1, 0.9))
        canvas.drawCentredString(cx, y, subtitle)
        y -= 24

    # Teal accent line
    canvas.setStrokeColor(Color(*teal))
    canvas.setLineWidth(2)
    canvas.line(cx - 25, y, cx + 25, y)
    y -= 18

    # Date range
    date_range = getattr(doc, 'cover_date_range', '')
    if date_range:
        canvas.setFont(BODY_FONT, 12)
        canvas.setFillColor(Color(1, 1, 1, 0.75))
        canvas.drawCentredString(cx, y, date_range)
        y -= 18

    # Loan purpose
    loan_purpose = getattr(doc, 'cover_loan_purpose', '')
    if loan_purpose:
        canvas.setFont(BODY_FONT, 10)
        canvas.setFillColor(Color(1, 1, 1, 0.55))
        canvas.drawCentredString(cx, y, f'Loan Purpose: {loan_purpose}')

    # --- Bottom metadata ---
    gen_date = datetime.now().strftime('%B %d, %Y')
    canvas.setFont(BODY_FONT, 8)
    canvas.setFillColor(Color(1, 1, 1, 0.4))
    canvas.drawCentredString(cx, 50, f'Generated {gen_date}')
    canvas.setFont(BODY_FONT, 7)
    canvas.setFillColor(Color(1, 1, 1, 0.3))
    canvas.drawCentredString(cx, 36, 'NCRC JustData Platform \u2014 justdata.org')

    canvas.restoreState()


# ---------------------------------------------------------------------------
# MagazineDocTemplate
# ---------------------------------------------------------------------------
class MagazineDocTemplate(BaseDocTemplate):
    """
    Multi-template document for magazine-style PDF reports.
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
        # --- Cover (single full-width frame) ---
        cover_frame = Frame(
            MARGIN_LEFT, MARGIN_BOTTOM,
            USABLE_WIDTH, PAGE_H - MARGIN_TOP - MARGIN_BOTTOM,
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
        # Frame starts below header, ends above footer
        frame_top = PAGE_H - MARGIN_TOP - HEADER_HEIGHT
        frame_bottom = MARGIN_BOTTOM + FOOTER_HEIGHT
        frame_h = frame_top - frame_bottom

        left_frame = Frame(
            MARGIN_LEFT, frame_bottom,
            COL_W, frame_h,
            id='left_col',
            leftPadding=0, rightPadding=4,
            topPadding=0, bottomPadding=0,
        )
        right_frame = Frame(
            MARGIN_LEFT + COL_W + GUTTER, frame_bottom,
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
            MARGIN_LEFT, frame_bottom,
            USABLE_WIDTH, frame_h,
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
        l_frame_top = L_PAGE_H - MARGIN_TOP - HEADER_HEIGHT
        l_frame_bottom = MARGIN_BOTTOM + FOOTER_HEIGHT
        l_frame_h = l_frame_top - l_frame_bottom
        landscape_frame = Frame(
            MARGIN_LEFT, l_frame_bottom,
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
# Cover page flowables builder (per v2 spec Section 5)
# ---------------------------------------------------------------------------
def build_cover_page(title, subtitle='', date_range='', metadata=None):
    """
    Return a list of flowables for the cover page.
    """
    story = []

    # Push content down into the navy band area
    story.append(Spacer(1, 2.8 * inch))

    story.append(Paragraph(title, COVER_TITLE))
    if subtitle:
        story.append(Paragraph(subtitle, COVER_SUBTITLE))
    if date_range:
        story.append(Spacer(1, 8))
        story.append(Paragraph(date_range, COVER_DATE))

    if metadata:
        loan_purpose = metadata.get('loan_purpose', '')
        if isinstance(loan_purpose, list):
            loan_purpose = ', '.join(str(lp).replace('_', ' ').title() for lp in loan_purpose)
        if loan_purpose:
            story.append(Paragraph(f'Loan Purpose: {loan_purpose}', COVER_DATE))

    # White area below the navy band
    story.append(Spacer(1, 2.0 * inch))
    gen_date = datetime.now().strftime('%B %d, %Y')
    story.append(Paragraph(f'Generated {gen_date}', COVER_META))
    story.append(Paragraph('NCRC JustData Platform — justdata.org', COVER_META))

    story.append(Spacer(1, 0.5 * inch))
    disclaimer = (
        "This report was generated by NCRC's JustData platform using publicly available "
        "Home Mortgage Disclosure Act (HMDA) data. AI-generated narrative analysis is produced "
        "by Anthropic's Claude. All quantitative data is derived directly from federal sources."
    )
    story.append(Paragraph(disclaimer, COVER_DISCLAIMER))

    # Push to next page after cover
    story.append(NextPageTemplate('full_width'))
    story.append(PageBreak())

    return story
