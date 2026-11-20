"""Words on the account page (spec 14). Everything about access is generated
from the registry and the access matrix; nothing here lists apps by hand."""
from datetime import datetime, timezone
from typing import Iterable, List, Optional
from zoneinfo import ZoneInfo

from justdata.shared.web.registry import ALWAYS_AVAILABLE

ET = ZoneInfo("America/New_York")

# The role in plain words, with its article: "You have <this> account."
ROLE_NAMES = {
    "public_registered": "a registered",
    "tester": "a JustData tester",
    "member": "an NCRC member",
    "member_premium": "an NCRC premium member",
    "non_member_org": "a partner organization",
    "staff": "an NCRC staff",
    "senior_executive": "an NCRC senior executive",
    "admin": "a JustData administrator",
}

ROLE_TITLES = {
    "public_registered": "Registered account",
    "tester": "Tester",
    "member": "NCRC member",
    "member_premium": "NCRC premium member",
    "non_member_org": "Partner organization",
    "staff": "NCRC staff",
    "senior_executive": "NCRC senior executive",
    "admin": "Administrator",
}

PROVIDER_NAMES = {
    "password": "email and password",
    "google.com": "Google",
    "microsoft.com": "Microsoft",
}

# AP style: these months are abbreviated with a specific date.
_AP_MONTHS = {1: "Jan.", 2: "Feb.", 3: "March", 4: "April", 5: "May", 6: "June", 7: "July",
              8: "Aug.", 9: "Sept.", 10: "Oct.", 11: "Nov.", 12: "Dec."}


def role_title(user_type: str) -> str:
    return ROLE_TITLES.get(user_type, "Account")


def plain_list(names: List[str]) -> str:
    """"A", "A and B", "A, B and C" (NCRC style: no Oxford comma)."""
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def open_apps(nav_groups: Iterable[dict]) -> List[str]:
    """Names of the apps this role can open, in registry order."""
    return [item["name"] for group in nav_groups for item in group["items"]
            if item["state"] == "available" and item["key"] not in ALWAYS_AVAILABLE]


def role_sentence(user_type: str, apps: List[str]) -> str:
    first = f"You have {ROLE_NAMES.get(user_type, 'a JustData')} account."
    if not apps:
        return first + " It doesn't open any apps yet."
    return f"{first} It opens {plain_list(apps)}."


def ap_date(value) -> Optional[str]:
    """A date in ET, AP style: "Nov. 20, 2026"."""
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    local = value.astimezone(ET)
    return f"{_AP_MONTHS[local.month]} {local.day}, {local.year}"


def provider_names(provider_ids: Iterable[str]) -> List[str]:
    return [PROVIDER_NAMES.get(p, p) for p in provider_ids]


# Section 5 (phase 1: the statement only; "Download my data" is phase 2).
# It states what is collected today (audit in spec 13, part A). Update it when
# spec 13's event stream ships and when usage rows stop holding IP addresses.
RECORDED = (
    "Your account details: name, email address, organization, role and when you sign in.",
    "The reports you run: the app, the geography, when, and the IP address and "
    "browser the request came from.",
    "How pages are used: Google Analytics records the pages you visit, linked to "
    "your account ID, not your name or email.",
    "Feedback you send us.",
)
NOT_RECORDED = (
    "We don't record your screen or your keystrokes.",
)

STAFF_LINE = "Staff accounts are closed through NCRC offboarding."
