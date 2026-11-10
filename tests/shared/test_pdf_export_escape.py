"""PDF exports print names and AI narrative as text (2026-11-10).

ReportLab's Paragraph reads its own HTML-like tags. LendSight, BizSight and
BranchSight passed lender, bank and county names and AI narrative to it
unescaped, so a name or narrative with <, " or a tag broke the build or
rendered as markup, and a markdown link could carry any scheme. These tests
build each app's real PDF with such text and check that it builds and that
every value comes out literally.
"""

import pytest
from reportlab.platypus import paragraph

from justdata.apps.bizsight.pdf_report import generate_bizsight_pdf
from justdata.apps.branchsight.pdf_report import generate_branchsight_pdf
from justdata.apps.lendsight.pdf_report import generate_lendsight_pdf
from justdata.shared.pdf.styles import markdown_to_reportlab, pdf_text

NAME = 'Smith & Sons <Bank> "Trust" <img src="x.png"/>'
COUNTY = 'Prince <George> County, "MD"'
NARRATIVE = ('Lending rose 5% where income < 80% of AMI. <img src="x.png"/> '
             '[click here](javascript:alert(1)) and [the HMDA guide](https://example.org/hmda).')
NARRATIVE_TEXT = ('Lending rose 5% where income < 80% of AMI. <img src="x.png"/> '
                  'click here and the HMDA guide.')


@pytest.fixture
def printed(monkeypatch):
    """Plain text of every Paragraph laid out while a PDF builds."""
    texts = []
    wrap = paragraph.Paragraph.wrap

    def recording_wrap(self, *args):
        texts.append(self.getPlainText())
        return wrap(self, *args)

    monkeypatch.setattr(paragraph.Paragraph, "wrap", recording_wrap)
    return texts


def _lendsight():
    report = {"top_lenders_detailed": [{"Lender Name": NAME, "Lender Type": "Bank", "Total Loans": 120}]}
    ai = {"key_findings": f"- {NARRATIVE}", "top_lenders_detailed_discussion": NARRATIVE}
    return generate_lendsight_pdf(report, {"counties": [COUNTY], "years": [2023, 2024]}, ai)


def _bizsight():
    result = {"top_lenders_table": [{"Lender Name": NAME, "Num Total": 12, "Amt Total (in $000s)": 340}],
              "ai_insights": {"top_lenders_number_discussion": NARRATIVE}}
    return generate_bizsight_pdf(result, {"county_data": {"name": COUNTY}, "years": [2023, 2024]})


def _branchsight():
    report = {"by_bank": [{"Bank Name": NAME, "Total Branches": 4}],
              "by_county": [{"County": COUNTY, "Total Branches": 4}]}
    ai = {"key_findings": f"- {NARRATIVE}", "table_narratives": {"table1": NARRATIVE}}
    return generate_branchsight_pdf(report, {"counties": [COUNTY], "years": [2023, 2024]}, ai)


@pytest.mark.parametrize("build", [_lendsight, _bizsight, _branchsight], ids=["lendsight", "bizsight", "branchsight"])
def test_pdf_builds_and_prints_names_and_narrative_literally(build, printed):
    pdf = build().getvalue()
    assert pdf.startswith(b"%PDF")

    assert any(NAME in t for t in printed), "lender or bank name missing or altered"
    assert any(NARRATIVE_TEXT in t for t in printed), "narrative missing or altered"
    # The https link stays a link; the javascript: one is only words
    assert b"https://example.org/hmda" in pdf
    assert b"javascript" not in pdf


def test_bizsight_prints_the_county_literally(printed):
    _bizsight()
    assert sum(COUNTY in t for t in printed) >= 2  # introduction and citation


def test_pdf_text_escapes_markup():
    assert pdf_text(NAME) == ('Smith &amp; Sons &lt;Bank&gt; &quot;Trust&quot; '
                              '&lt;img src=&quot;x.png&quot;/&gt;')
    assert pdf_text(None) == ""
    assert pdf_text(0) == "0"


@pytest.mark.parametrize("link, expected", [
    ("[guide](https://example.org/a?b=1&c=2)", '<a href="https://example.org/a?b=1&amp;c=2" color="#1a8fc9">guide</a>'),
    ("[x](javascript:alert(1))", "x"),
    ("[x](http://example.org)", "x"),
    ("[x](data:text/html,hi)", "x"),
    ('[x](https://example.org" onclick="y)', 'x'),
])
def test_converter_links_https_only(link, expected):
    assert markdown_to_reportlab(link) == expected


def test_converter_keeps_its_own_markup():
    assert markdown_to_reportlab("**Bold** and *italic* <b>not bold</b>") == (
        "<b>Bold</b> and <i>italic</i> &lt;b&gt;not bold&lt;/b&gt;")
