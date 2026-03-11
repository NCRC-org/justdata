"""
BranchMapper Methods & Definitions PDF.

Short branded document (3-5 pages) explaining data sources, definitions,
map symbology, and data limitations. Uses NCRC brand guidelines:
Helvetica (built-in ReportLab stand-in for Helvetica Neue), NCRC Blue headings.
"""
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image as RLImage
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from io import BytesIO
from datetime import datetime
import os

# NCRC brand colors
NCRC_BLUE = HexColor('#2fade3')
BLACK = HexColor('#000000')
GRAY = HexColor('#818390')

# Fonts — Helvetica is built into ReportLab (stand-in for Helvetica Neue)
HEADING_FONT = 'Helvetica-Bold'
BODY_FONT = 'Helvetica'

# Styles
_title = ParagraphStyle(
    'BMTitle', fontName=HEADING_FONT, fontSize=24, leading=28,
    textColor=BLACK, spaceAfter=8
)
_subtitle = ParagraphStyle(
    'BMSubtitle', fontName=BODY_FONT, fontSize=14, leading=18,
    textColor=GRAY, spaceAfter=4
)
_heading = ParagraphStyle(
    'BMHeading', fontName=HEADING_FONT, fontSize=16, leading=20,
    textColor=NCRC_BLUE, spaceBefore=16, spaceAfter=8
)
_subheading = ParagraphStyle(
    'BMSubheading', fontName=HEADING_FONT, fontSize=12, leading=15,
    textColor=BLACK, spaceBefore=10, spaceAfter=4
)
_body = ParagraphStyle(
    'BMBody', fontName=BODY_FONT, fontSize=11, leading=15,
    textColor=BLACK, alignment=TA_JUSTIFY, spaceAfter=6
)
_caption = ParagraphStyle(
    'BMCaption', fontName=BODY_FONT, fontSize=9, leading=12,
    textColor=GRAY, spaceAfter=4
)
_bullet = ParagraphStyle(
    'BMBullet', fontName=BODY_FONT, fontSize=11, leading=15,
    textColor=BLACK, leftIndent=18, bulletIndent=6, spaceAfter=4,
    alignment=TA_LEFT
)


def _find_logo():
    """Find the NCRC logo image file."""
    base = os.path.dirname(__file__)
    candidates = [
        os.path.join(base, '..', '..', 'shared', 'web', 'static', 'img', 'ncrc-logo-color.png'),
        os.path.join(base, '..', '..', 'shared', 'web', 'static', 'img', 'ncrc-logo.png'),
        os.path.join(base, 'static', 'img', 'branchmapper-logo.png'),
    ]
    for p in candidates:
        p = os.path.normpath(p)
        if os.path.exists(p):
            return p
    return None


def generate_methods_pdf(geography='Selected area'):
    """Generate a branded methods & definitions PDF and return a BytesIO buffer."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch
    )

    story = []

    # --- Cover page ---
    logo_path = _find_logo()
    if logo_path:
        try:
            story.append(RLImage(logo_path, width=2 * inch, height=0.6 * inch))
        except Exception:
            pass
    story.append(Spacer(1, 24))

    story.append(Paragraph('BranchMapper', _title))
    story.append(Spacer(1, 4))
    story.append(Paragraph('Data sources and definitions', _subtitle))
    story.append(Spacer(1, 16))
    story.append(Paragraph(f'Geography: {geography}', _body))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        f'Generated: {datetime.now().strftime("%B %d, %Y")}', _caption
    ))
    story.append(Paragraph('Powered by JustData', _caption))

    story.append(PageBreak())

    # --- Data sources ---
    story.append(Paragraph('Data sources', _heading))

    story.append(Paragraph('<b>FDIC Summary of Deposits (SOD)</b>', _subheading))
    story.append(Paragraph(
        'Branch location and deposit data is sourced from the Federal Deposit Insurance '
        "Corporation's annual Summary of Deposits survey, conducted as of June 30 each year. "
        'This survey covers all FDIC-insured depository institutions and their branch offices.',
        _body
    ))

    story.append(Paragraph('<b>Census tract demographics</b>', _subheading))
    story.append(Paragraph(
        'Census tract characteristics including median family income, population by race and '
        'ethnicity and tract income classifications are sourced from the Federal Financial '
        'Institutions Examination Council (FFIEC) Census file, which incorporates American '
        'Community Survey (ACS) 5-year estimates.',
        _body
    ))

    story.append(Paragraph('<b>FDIC OSCR (Office of Supervisory Changes Report)</b>', _subheading))
    story.append(Paragraph(
        'Branch openings, closings and relocations are sourced from the FDIC OSCR history '
        'endpoint, which records structural changes reported by FDIC-insured institutions. '
        'Change codes 711/713 represent branch openings; 721/722 represent closings.',
        _body
    ))

    # --- Definitions ---
    story.append(Paragraph('Definitions', _heading))

    defs = [
        ('Branch', 'A unique physical branch location of an FDIC-insured depository '
         'institution, identified by the FDIC unique institution number (UNINUMBR).'),
        ('Low-to-moderate income (LMI) census tract', 'A census tract where the median '
         'family income is less than 80% of the area median family income (AMFI). Low income '
         'tracts have MFI below 50% of AMFI; moderate income tracts have MFI between 50% and '
         '80% of AMFI.'),
        ('Majority-minority census tract (MMCT)', 'A census tract where more than 50% of '
         'the population identifies as a racial or ethnic minority.'),
        ('Deposits', 'Total deposits held at each branch location as reported in the FDIC '
         'Summary of Deposits, expressed in dollars.'),
        ('Census tract income overlay', 'When the Income overlay is active on the map, '
         'census tracts are shaded by their FFIEC income classification: Low (dark), '
         'Moderate (orange), Middle (light blue) and Upper (light/green).'),
        ('Census tract minority overlay', 'When the Race overlay is active, census tracts '
         'are shaded by minority population percentage, from light (low minority %) to dark '
         '(high minority %).'),
    ]
    for term, definition in defs:
        story.append(Paragraph(f'<b>{term}:</b> {definition}', _body))

    # --- Map symbology ---
    story.append(Paragraph('Map symbology', _heading))

    story.append(Paragraph(
        '<b>Branch markers:</b> Each colored dot represents a single branch location. When '
        'multiple banks are displayed, each bank is assigned a distinct color. In metro view '
        'with "Show All Banks," non-selected banks appear as gray dots.',
        _body
    ))
    story.append(Paragraph(
        '<b>OSCR event markers (Recent Changes mode):</b> Green circles indicate branch '
        'openings. Red X markers indicate branch closings. Orange dotted lines connect '
        'relocated branches from their old location to their new location.',
        _body
    ))

    # --- Data limitations ---
    story.append(Paragraph('Data limitations', _heading))

    limitations = [
        'SOD data reflects a single snapshot date (June 30) each year and may not capture '
        'intra-year changes.',
        'Branch geocoding uses addresses reported to the FDIC, which may contain minor '
        'positional inaccuracies.',
        'Census tract demographics reflect ACS 5-year estimates and may lag current conditions.',
        'OSCR structural change data has a processing delay of approximately 2-4 weeks from '
        'the effective date of the change.',
    ]
    for lim in limitations:
        story.append(Paragraph(lim, _bullet, bulletText='\u2022'))

    # --- Suggested citation ---
    story.append(Paragraph('Suggested citation', _heading))
    story.append(Paragraph(
        'National Community Reinvestment Coalition. (2026). BranchMapper: Interactive Branch '
        'Mapping Tool. Washington, DC: NCRC. Data sources: FDIC Summary of Deposits; FFIEC '
        'Census File.',
        _body
    ))

    # --- Copyright ---
    story.append(Spacer(1, 24))
    story.append(Paragraph(
        '\u00a9 2026 National Community Reinvestment Coalition', _caption
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer
