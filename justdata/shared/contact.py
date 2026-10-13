"""NCRC contact details shown on JustData (Jad, 2026-10-13).

The one place they live: the footers and the contact page read NCRC_CONTACT
through the `ncrc_contact` Jinja global. Address and phone are NCRC's main
listing at https://ncrc.org/contact/ (checked 2026-10-13); research@ncrc.org
is the JustData contact Jad chose (the NCRC page lists department addresses).
"""

NCRC_CONTACT = {
    "email": "research@ncrc.org",
    "phone": "(202) 628-8866",
    "phone_tel": "+12026288866",
    "address_lines": ("740 15th Street NW, Suite 400", "Washington, DC 20005"),
    "source": "https://ncrc.org/contact/",
}
