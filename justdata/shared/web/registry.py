"""Single source of truth for platform navigation.

Every surface that lists apps or pages (nav drawer, /apps launcher, landing
roster, footer) renders from NAV_GROUPS. Access policy is NOT decided here:
each item's state and lock tag are read at request time through
get_access_row() (main/auth), passed in by inject_shell() in main/app.py.
Do not add access rules to this file; change the matrix instead.

Testing-site overlay: on JUSTDATA_ENV=testing, get_access_row() applies
main/auth/access_overlay.py, which limits non-staff users to the three Sight
apps (LendSight, BizSight, BranchSight). MergerMeter is staff-only on every
deploy (D2, resolved 2026-10-07). This file does not special-case either;
it just reads the overlaid rows.

`sources` names only datasets the app's code actually queries (checked
against each app's sql_templates/ and query builders, 2026-10-06).
"""

from dataclasses import asdict, dataclass, field
from typing import Optional


@dataclass(frozen=True)
class AppEntry:
    key: str            # ACCESS_MATRIX key, also the data-app attribute
    name: str           # display name
    url: str            # matches the blueprint url_prefix in main/app.py
    purpose: str        # one line, <= 90 chars
    sources: tuple = field(default_factory=tuple)  # dataset chips
    # Landing page "What you can ask" question, worded to match what the app
    # actually computes (spec 02 audit, 2026-10-07). Empty = not shown.
    question: str = ""


@dataclass(frozen=True)
class NavGroup:
    label: Optional[str]  # None renders no group heading
    items: tuple


NAV_GROUPS = (
    NavGroup(None, (
        AppEntry("home", "Home", "/", "Platform overview"),
        AppEntry("apps", "All apps", "/apps", "Open any tool you have access to"),
    )),
    NavGroup("Analyze lending", (
        AppEntry("lendsight", "LendSight", "/lendsight",
                 "Mortgage lending by lender, geography and borrower.",
                 ("HMDA", "Census ACS"),
                 "Which lenders are making home loans to Black and Latino borrowers in my county?"),
        AppEntry("bizsight", "BizSight", "/bizsight",
                 "Small business lending under CRA.",
                 ("CRA small business", "Census ACS"),
                 "How much small business credit reaches low- and moderate-income neighborhoods in a county?"),
    )),
    NavGroup("Analyze branches", (
        AppEntry("branchsight", "BranchSight", "/branchsight",
                 "Branch openings, closures and deposit share over time.",
                 ("FDIC SOD", "Census ACS"),
                 "Where are banks opening and closing branches, and how many serve "
                 "low- and moderate-income and majority-minority neighborhoods?"),
        AppEntry("branchmapper", "BranchMapper", "/branchmapper",
                 "Map a bank's branch network against neighborhood data.",
                 ("FDIC SOD", "Census")),
    )),
    NavGroup("Investigate", (
        AppEntry("mergermeter", "MergerMeter", "/mergermeter",
                 "What a proposed merger means for the markets it touches.",
                 ("HMDA", "CRA small business", "FDIC SOD"),
                 "What does a proposed merger mean for lending and branches in the communities it touches?"),
        AppEntry("dataexplorer", "DataExplorer", "/dataexplorer",
                 "Build your own query across platform datasets.",
                 ("HMDA", "CRA small business", "FDIC SOD", "Census ACS")),
    )),
    NavGroup("Staff", (
        AppEntry("dotlender", "DotLender", "/dotlender",
                 "HMDA dot-density lending map with PDF export.",
                 ("HMDA",)),
        AppEntry("analytics", "Analytics", "/analytics",
                 "Platform usage and performance."),
        AppEntry("admin", "Administration", "/admin/users",
                 "Users, access and configuration."),
    )),
)

# /privacy and /terms are left out until their content exists (they 404).
SECONDARY_PAGES = (
    ("about", "About", "/about"),
    ("contact", "Contact", "/contact"),
)

# Entries that are not in ACCESS_MATRIX and are always reachable.
ALWAYS_AVAILABLE = frozenset({"home", "apps"})

# ACCESS_MATRIX levels: hidden < locked < limited < full.
OPEN_LEVELS = ("full", "limited")
STAFF_ROLES = ("staff", "senior_executive", "admin")


def item_state(level):
    """Map one ACCESS_MATRIX level to a render state.

    full or limited -> "available" (link works)
    locked          -> "locked" (lock + tag, links to /apps#request-access)
    hidden/missing  -> None (not rendered)
    """
    if level in OPEN_LEVELS:
        return "available"
    if level == "locked":
        return "locked"
    return None


def locked_tag(matrix_row):
    """Tag text for a locked item: the lowest role that unlocks it.

    Read from the item's access row (matrix plus overlay), in this order:
      "Members"          the plain `member` role opens it
      "Premium members"  `member` does not, `member_premium` does
      "Staff"            only staff roles (staff, senior_executive, admin) do
    Anything else (for example only `non_member_org` opens it) gets no tag
    rather than a wrong one; the lock icon still renders.
    """
    if matrix_row.get("member") in OPEN_LEVELS:
        return "Members"
    if matrix_row.get("member_premium") in OPEN_LEVELS:
        return "Premium members"
    opened_by = {role for role, level in matrix_row.items() if level in OPEN_LEVELS}
    if opened_by and opened_by <= set(STAFF_ROLES):
        return "Staff"
    return None


def resolve_registry(get_access_row, user_type):
    """Return NAV_GROUPS as plain dicts with per-item `state` and `tag`.

    `get_access_row(key)` is main.auth.get_access_row: the item's matrix row
    with any environment overlay applied, the same row get_app_access()
    reads (default "hidden"). Hidden items are dropped, and so is any group
    left with no items, which is how the Staff group disappears for
    non-staff users.
    """
    groups = []
    for group in NAV_GROUPS:
        items = []
        for entry in group.items:
            row = {} if entry.key in ALWAYS_AVAILABLE else get_access_row(entry.key)
            if entry.key in ALWAYS_AVAILABLE:
                state = "available"
            else:
                state = item_state(row.get(user_type, "hidden"))
            if state is None:
                continue
            tag = locked_tag(row) if state == "locked" else None
            items.append({**asdict(entry), "state": state, "tag": tag})
        if items:
            groups.append({"label": group.label, "items": items})
    return groups
