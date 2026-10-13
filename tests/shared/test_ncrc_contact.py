"""NCRC contact details come from one config value (Jad, 2026-10-13)."""

import re
from pathlib import Path

from justdata.shared.contact import NCRC_CONTACT

ROOT = Path(__file__).resolve().parents[2]


def test_values():
    assert NCRC_CONTACT["phone"] == "(202) 628-8866" and NCRC_CONTACT["phone_tel"] == "+12026288866"
    assert NCRC_CONTACT["address_lines"] == ("740 15th Street NW, Suite 400", "Washington, DC 20005")
    assert NCRC_CONTACT["email"] == "research@ncrc.org"


def test_footer_and_contact_page_render_the_config():
    from justdata.main.app import create_app
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()
    with client.session_transaction() as s:
        s["user_type"] = "staff"
        s["firebase_user"] = {"uid": "t", "email": "t@example.org", "email_verified": True}
    html = client.get("/contact").get_data(as_text=True)
    assert "(202) 628-8866" in html and 'href="tel:+12026288866"' in html
    assert "740 15th Street NW, Suite 400<br>Washington, DC 20005" in html
    assert 'data-to="research@ncrc.org"' in html and "mailto:research@ncrc.org" in html
    assert "464-4600" not in html and "628-6270" not in html and "info@ncrc.org" not in html


def test_no_other_phone_number_or_address_in_templates():
    phone = re.compile(r"\(?\b202\)?[ .-]?\d{3}[ .-]\d{4}|\+1202\d{7}")
    stray = []
    for path in (ROOT / "justdata").rglob("*.html"):
        text = path.read_text(errors="ignore")
        if phone.search(text) or "15th Street" in text:
            stray.append(str(path.relative_to(ROOT)))
    assert not stray, stray
