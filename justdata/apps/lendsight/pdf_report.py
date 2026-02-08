"""
LendSight magazine-style PDF report generator.

Builds a full ReportLab PDF story with:
  - Cover page
  - Census demographics chart + intro narrative
  - Key findings callout
  - Section 1: Race/Ethnicity (demographic_overview) + narrative
  - Section 2: Income & Neighborhood tables + narratives
  - Section 3: Top Lenders (landscape) + narrative
  - Section 4: Market Concentration / HHI + narrative
  - Trends analysis
  - Methods section (two-column)
  - Back matter
"""

from io import BytesIO
from datetime import datetime

import pandas as pd
from reportlab.platypus import (
    Spacer, NextPageTemplate, PageBreak, CondPageBreak, Paragraph,
)
from reportlab.lib.units import inch

from justdata.shared.pdf.base_report import (
    MagazineDocTemplate, build_cover_page, CONTENT_W, L_CONTENT_W,
)
from justdata.shared.pdf.styles import (
    HEADING_1, HEADING_2, BODY_TEXT, BODY_TEXT_SMALL, METHODS_TEXT,
    SOURCE_CAPTION, NAVY,
)
from justdata.shared.pdf.components import (
    section_header, build_styled_table, build_callout_box,
    build_source_caption, keep_together_block, narrative_paragraphs,
)
from justdata.apps.lendsight.pdf_charts import (
    render_census_demographics_chart, render_hhi_chart, chart_to_image,
)


# ---------------------------------------------------------------------------
# Data extraction helpers
# ---------------------------------------------------------------------------
def _df_to_rows(df_or_list):
    """Convert a DataFrame or list-of-dicts to (headers, rows) tuple."""
    if df_or_list is None:
        return [], []
    if isinstance(df_or_list, pd.DataFrame):
        if df_or_list.empty:
            return [], []
        headers = list(df_or_list.columns)
        rows = []
        for _, row in df_or_list.iterrows():
            rows.append([_fmt(row[c]) for c in headers])
        return headers, rows
    if isinstance(df_or_list, list) and df_or_list:
        if isinstance(df_or_list[0], dict):
            headers = list(df_or_list[0].keys())
            rows = [[_fmt(d.get(h, '')) for h in headers] for d in df_or_list]
            return headers, rows
    return [], []


def _fmt(val):
    """Format a value for table display."""
    if val is None:
        return ''
    if isinstance(val, float):
        if abs(val) >= 100:
            return f'{val:,.0f}'
        return f'{val:,.1f}' if val != int(val) else f'{int(val):,}'
    if isinstance(val, int):
        return f'{val:,}'
    return str(val)


def _safe_text(text):
    """Ensure text is a non-empty string; return empty string if not."""
    if not text or not isinstance(text, str):
        return ''
    return text.strip()


def _col_widths(headers, available_width, first_col_ratio=0.28):
    """Auto-calculate column widths giving the first col more space."""
    n = len(headers)
    if n == 0:
        return None
    first = available_width * first_col_ratio
    rest = (available_width - first) / max(n - 1, 1)
    return [first] + [rest] * (n - 1)


def _add_narrative(story, text, style=None):
    """Append narrative paragraphs to the story if text is non-empty."""
    text = _safe_text(text)
    if text:
        story.append(Spacer(1, 6))
        story.extend(narrative_paragraphs(text, style=style))


# ---------------------------------------------------------------------------
# Main PDF generator
# ---------------------------------------------------------------------------
def generate_lendsight_pdf(report_data, metadata, ai_insights=None):
    """
    Generate a magazine-style PDF report and return it as a BytesIO buffer.

    Parameters
    ----------
    report_data : dict
        Contains DataFrames/lists: demographic_overview, income_borrowers,
        income_tracts, minority_tracts, top_lenders_detailed,
        market_concentration, census_data, etc.
    metadata : dict
        Contains counties, years, loan_purpose, census_data, hhi, etc.
    ai_insights : dict or None
        AI-generated narrative text keyed by section.

    Returns
    -------
    BytesIO — the PDF file contents.
    """
    ai = ai_insights or {}
    buf = BytesIO()

    doc = MagazineDocTemplate(
        buf,
        app_name='LendSight',
        footer_source='Source: HMDA, U.S. Census Bureau, American Community Survey',
    )

    story = []

    # ------------------------------------------------------------------
    # 1. Cover page
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
        date_range = f'{year_strs[0]} – {year_strs[-1]}' if len(year_strs) > 1 else year_strs[0] if year_strs else ''
    else:
        date_range = str(years) if years else ''

    story.extend(build_cover_page(
        title='Mortgage Lending Analysis',
        subtitle=county_display,
        date_range=date_range,
        metadata=metadata,
    ))

    # ------------------------------------------------------------------
    # 2. Census demographics chart (full-width) + intro narrative
    # ------------------------------------------------------------------
    # Cover page already sets NextPageTemplate('full_width')
    census_data = metadata.get('census_data', {}) or report_data.get('census_data', {})

    census_chart_buf = render_census_demographics_chart(census_data, counties)
    census_img = chart_to_image(census_chart_buf, width_inches=6.5, height_inches=3.0)

    if census_img:
        story.append(section_header('Population Demographics'))
        story.append(census_img)
        story.append(build_source_caption(
            'Source: U.S. Census Bureau — 2010 Decennial Census, 2020 Decennial Census, American Community Survey'
        ))

    # Intro narrative on same page below chart
    intro_text = _safe_text(ai.get('intro_paragraph', ''))
    demo_intro = _safe_text(ai.get('demographic_overview_intro', ''))
    narrative_text = intro_text or demo_intro
    _add_narrative(story, narrative_text)

    # ------------------------------------------------------------------
    # 3. Key findings callout + Section 1 table (full-width)
    # ------------------------------------------------------------------
    key_findings = _safe_text(ai.get('key_findings', ''))
    demo_df = report_data.get('demographic_overview')
    demo_headers, demo_rows = _df_to_rows(demo_df)

    # Start a new full-width page for key findings + Section 1
    story.append(NextPageTemplate('full_width'))
    story.append(PageBreak())

    if key_findings:
        story.append(section_header('Key Findings'))
        story.append(build_callout_box(key_findings, title='Key Findings', style='findings'))
        story.append(Spacer(1, 14))

    # Section 1 table immediately after key findings on same page
    if demo_rows:
        story.append(section_header('Section 1: Race & Ethnicity in Mortgage Lending'))
        widths = _col_widths(demo_headers, CONTENT_W)
        story.append(build_styled_table(demo_headers, demo_rows, col_widths=widths))
        story.append(build_source_caption('Source: Home Mortgage Disclosure Act (HMDA) data'))

    # Section 1 narrative below table
    _add_narrative(story, ai.get('demographic_overview_discussion', ''))

    # ------------------------------------------------------------------
    # 4. Section 2: Income & Neighborhood tables (full-width)
    #    Each table + narrative on its own page
    # ------------------------------------------------------------------
    section2_tables = [
        ('income_borrowers', 'Lending by Borrower Income',
         'income_borrowers_discussion'),
        ('income_tracts', 'Lending to Census Tracts by Income',
         'income_tracts_discussion'),
        ('minority_tracts', 'Lending to Census Tracts by Minority Population',
         'minority_tracts_discussion'),
    ]

    first_s2 = True
    for data_key, table_title, narrative_key in section2_tables:
        df = report_data.get(data_key)
        headers, rows = _df_to_rows(df)
        if not rows:
            continue

        # Force a new full-width page for each table
        story.append(NextPageTemplate('full_width'))
        story.append(PageBreak())

        if first_s2:
            story.append(section_header('Section 2: Income & Neighborhood Analysis'))
            first_s2 = False

        story.append(section_header(table_title, level=2))
        widths = _col_widths(headers, CONTENT_W)
        story.append(build_styled_table(headers, rows, col_widths=widths))
        story.append(build_source_caption('Source: HMDA data'))

        # Narrative below table on same page
        _add_narrative(story, ai.get(narrative_key, ''))

    # Income neighborhood overview discussion
    income_neigh_disc = _safe_text(ai.get('income_neighborhood_discussion', ''))
    if income_neigh_disc:
        story.append(Spacer(1, 10))
        story.append(section_header('Income & Neighborhood Overview', level=2))
        story.extend(narrative_paragraphs(income_neigh_disc))

    # ------------------------------------------------------------------
    # 5. Section 3: Top Lenders (landscape)
    # ------------------------------------------------------------------
    lenders_df = report_data.get('top_lenders_detailed')
    lenders_headers, lenders_rows = _df_to_rows(lenders_df)
    if lenders_rows:
        story.append(NextPageTemplate('landscape'))
        story.append(PageBreak())
        story.append(section_header('Section 3: Top Mortgage Lenders'))

        # For landscape, use wider available width
        widths = _col_widths(lenders_headers, L_CONTENT_W, first_col_ratio=0.22)
        story.append(build_styled_table(lenders_headers, lenders_rows, col_widths=widths))
        story.append(build_source_caption('Source: HMDA data'))

        # Narrative below table on same landscape page
        _add_narrative(story, ai.get('top_lenders_detailed_discussion', ''))

    # ------------------------------------------------------------------
    # 6. Section 4: Market Concentration / HHI (full-width)
    # ------------------------------------------------------------------
    market_conc = report_data.get('market_concentration', [])
    if isinstance(market_conc, pd.DataFrame):
        market_conc = market_conc.to_dict('records') if not market_conc.empty else []

    hhi_chart_buf = render_hhi_chart(market_conc)
    hhi_img = chart_to_image(hhi_chart_buf, width_inches=6.0, height_inches=3.0)

    if hhi_img or market_conc:
        story.append(NextPageTemplate('full_width'))
        story.append(PageBreak())
        story.append(section_header('Section 4: Market Concentration'))

        if hhi_img:
            story.append(hhi_img)
            story.append(build_source_caption(
                'Source: HMDA data. HHI thresholds: <1500 = Competitive, 1500-2500 = Moderate, >2500 = Concentrated'
            ))
            story.append(Spacer(1, 8))

        # HHI table
        hhi_headers, hhi_rows = _df_to_rows(market_conc)
        if hhi_rows:
            widths = _col_widths(hhi_headers, CONTENT_W)
            story.append(build_styled_table(hhi_headers, hhi_rows, col_widths=widths))
            story.append(build_source_caption('Source: HMDA data'))

        # Narrative below chart/table
        _add_narrative(story, ai.get('market_concentration_discussion', ''))

    # ------------------------------------------------------------------
    # 7. Trends analysis (full-width, continues from previous page)
    # ------------------------------------------------------------------
    trends_disc = _safe_text(ai.get('trends_analysis', ''))
    if trends_disc:
        story.append(Spacer(1, 10))
        story.append(section_header('Trends Analysis', level=2))
        story.extend(narrative_paragraphs(trends_disc))

    # ------------------------------------------------------------------
    # 8. Methods section (two-column — has enough text to fill well)
    # ------------------------------------------------------------------
    story.append(NextPageTemplate('two_column'))
    story.append(PageBreak())
    story.append(section_header('Methodology'))

    methods_text = (
        "This report analyzes Home Mortgage Disclosure Act (HMDA) data "
        "collected under Regulation C. HMDA requires most mortgage lenders "
        "to report detailed information about their lending activity, "
        "including the disposition of loan applications, loan amounts, "
        "borrower demographics, property location, and lender information."
        "\n\n"
        "The Herfindahl-Hirschman Index (HHI) measures market concentration. "
        "An HHI below 1,500 indicates a competitive market, 1,500 to 2,500 "
        "indicates moderate concentration, and above 2,500 indicates high "
        "concentration. HHI is calculated as the sum of squared market "
        "shares of all lenders in the market."
        "\n\n"
        "Census demographic data is drawn from the U.S. Census Bureau's "
        "2010 and 2020 Decennial Census programs and the American Community "
        "Survey (ACS) 5-year estimates. Population percentages are calculated "
        "as shares of total population for each geographic area."
        "\n\n"
        "Income classifications follow HUD definitions: Low-to-Moderate "
        "Income (LMI) borrowers have income below 80% of area median income. "
        "LMI census tracts have median family income below 80% of the area "
        "median. Majority-minority census tracts have more than 50% "
        "minority population."
        "\n\n"
        "AI-generated narrative analysis is produced by Anthropic's Claude "
        "language model to provide contextual interpretation of the data. "
        "All quantitative data in tables and charts is derived directly from "
        "HMDA and Census source data."
    )
    story.extend(narrative_paragraphs(methods_text, style=METHODS_TEXT))

    # ------------------------------------------------------------------
    # 9. Back matter (full-width)
    # ------------------------------------------------------------------
    story.append(NextPageTemplate('full_width'))
    story.append(PageBreak())
    story.append(section_header('About This Report'))

    about_text = (
        f"This report was generated by NCRC LendSight on "
        f"{datetime.now().strftime('%B %d, %Y')}. "
        f"LendSight is part of the JustData platform developed by the "
        f"National Community Reinvestment Coalition (NCRC) to provide "
        f"data-driven insights into mortgage lending patterns and "
        f"community investment."
    )
    story.extend(narrative_paragraphs(about_text))

    story.append(Spacer(1, 12))
    story.append(Paragraph(
        'National Community Reinvestment Coalition (NCRC)<br/>'
        '740 15th Street NW, Suite 400, Washington, DC 20005<br/>'
        'www.ncrc.org',
        BODY_TEXT_SMALL,
    ))

    # ------------------------------------------------------------------
    # Build the PDF
    # ------------------------------------------------------------------
    doc.build(story)
    buf.seek(0)
    return buf
