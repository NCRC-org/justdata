"""
Acceptance tests for the JustData frontend buildout.

Spec: L5 "JustData -- Frontend buildout spec -- 2026-09-21" Part D. Each test
function is tagged with the buildout step that introduces it, matching Part D's
numbering. This file is created in step 1 and extended in later steps.

HISTORY: step 2 (PR #193, merged) claimed in its own PR body and L5 log to
have added items 2, 3, 4, 5, 8, 9 and 10 (e.g. "A test in Part D renders
base_app.html and asserts every ID above is present"). It did not --
`git show 5b9883b -- tests/shared/test_frontend_standards.py` touches only
the INLINE_STYLE_BUDGET dict. Step 3 flagged this gap without fixing it
(out of that step's file list). This commit backfills items 2, 3, 4, 5, 8,
9 and 10 at Jad's explicit request, on top of step 3's own PR #194.

Every item below is scoped to what has ACTUALLY been converted onto tokens
and the shell as of this commit -- not the full IN_SCOPE_TEMPLATES/CSS set,
which still includes plenty of steps-4-through-7 territory (LendSight/
BizSight/BranchSight/MergerMeter's own analysis templates, analytics.css,
the bulk of style.css) that still has Font Awesome, Inter, literal hex
colors, and non-token radii by design -- that is what those later steps
exist to fix, per Part D's own "ratchets per step" language for items 2,
3, 8 and 9. Scoping these checks to the converted set and widening them as
later steps land is the same pattern this file already uses for
INLINE_STYLE_BUDGET (a ratcheting per-file budget) and test_no_emoji_in_scope
(xfail until the step that fixes it).

UPDATE (same PR, same day): writing item 2's test found `shell.css` (step 2)
using 8 literal `rgba(255,255,255,...)` / `rgba(13,14,16,0.5)` overlay
values with no Part B3 token equivalent. Flagged to Jad rather than fixed
unilaterally, since Part B is locked and this meant a new color decision;
Jad approved adding an overlay token group. Part B3 now has
`--color-overlay-hover-subtle`, `--color-overlay-hover`,
`--color-overlay-border`, `--color-overlay-border-strong`,
`--color-fg-on-dark-muted` and `--color-scrim` (shell.css's own
pre-existing values, named by purpose -- nothing visually changed).
`shell.css` is now fully on tokens and is in item 2's enforced file set.

Implemented here: items 1, 6, 7, 13 (step 1); 11, 12-partial (step 3);
2, 3, 4, 5, 8, 9, 10 (backfilled this commit, scoped as described above).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
JUSTDATA_DIR = REPO_ROOT / "justdata"

# Apps explicitly out of scope for the frontend buildout (spec Part A2's
# do-not-touch list). Never read these for a "must fix" assertion -- only to
# exclude them from in-scope scans, since editing them is forbidden regardless
# of what a scan would find.
OUT_OF_SCOPE_APPS = {
    "branchmapper",
    "dataexplorer",
    "dotlender",
    "electwatch",
    "memberview",
    "redlining",
    "commentmaker",
    "justpolicy",
    "lenderprofile",
    "loantrends",
}

IN_SCOPE_APPS = {"lendsight", "bizsight", "branchsight", "mergermeter", "analytics"}


def _in_scope_templates() -> list[Path]:
    """Template paths under shared/web/templates/, plus the five in-scope
    apps' templates/**/*.html. Mirrors Part D's IN_SCOPE_TEMPLATES definition."""
    paths = list((JUSTDATA_DIR / "shared" / "web" / "templates").rglob("*.html"))
    for app in sorted(IN_SCOPE_APPS):
        app_templates = JUSTDATA_DIR / "apps" / app / "templates"
        if app_templates.is_dir():
            paths.extend(app_templates.rglob("*.html"))
    return sorted(paths)


def _in_scope_css() -> list[Path]:
    """shared/web/static/css/*.css plus the five in-scope apps' static/css/*.css.
    Mirrors Part D's IN_SCOPE_CSS definition."""
    paths = list((JUSTDATA_DIR / "shared" / "web" / "static" / "css").glob("*.css"))
    for app in sorted(IN_SCOPE_APPS):
        app_css = JUSTDATA_DIR / "apps" / app / "static" / "css"
        if app_css.is_dir():
            paths.extend(app_css.glob("*.css"))
    return sorted(paths)


def _all_repo_files() -> list[Path]:
    """Every file under justdata/, used only for test 1 (single :root), which
    must prove no OTHER file anywhere defines :root -- not just in-scope ones,
    since a second :root block anywhere would still shadow tokens.css. This is
    a read-only scan; finding a hit outside IN_SCOPE never implies we may
    edit it (see OUT_OF_SCOPE_APPS above)."""
    return [p for p in JUSTDATA_DIR.rglob("*") if p.is_file()]


def _is_out_of_scope_app_file(path: Path) -> bool:
    try:
        rel_parts = path.relative_to(JUSTDATA_DIR).parts
    except ValueError:
        return False
    return len(rel_parts) > 1 and rel_parts[0] == "apps" and rel_parts[1] in OUT_OF_SCOPE_APPS


ROOT_BLOCK_RE = re.compile(r"^\s*:root\s*\{", re.MULTILINE)


def test_single_root_block():
    """Part D item 1 (step 1): exactly one file under justdata/ defines a
    :root block, and it is tokens.css.

    Scoped as a read-only whole-repo scan (per the item's literal wording),
    but a hit inside an out-of-scope app (ElectWatch, DataExplorer, ...) is
    reported separately and does not fail this test -- those files are
    off-limits to edit per the spec's do-not-touch list (Part A2), so this
    test can only ever assert what is true of files we are allowed to change.
    """
    tokens_css = JUSTDATA_DIR / "shared" / "web" / "static" / "css" / "tokens.css"
    assert tokens_css.is_file(), "tokens.css must exist"

    in_scope_hits = []
    out_of_scope_hits = []
    for path in _all_repo_files():
        if path.suffix not in (".css", ".html"):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if ROOT_BLOCK_RE.search(text):
            if path == tokens_css:
                continue
            if _is_out_of_scope_app_file(path):
                out_of_scope_hits.append(path)
            else:
                in_scope_hits.append(path)

    assert not in_scope_hits, (
        "in-scope files defining a second :root block (must be deleted, "
        f"values come from tokens.css): {[str(p.relative_to(REPO_ROOT)) for p in in_scope_hits]}"
    )
    # out_of_scope_hits is intentionally not asserted on -- informational only.


EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF☀-➿⭐✅❌]"
)


@pytest.mark.xfail(strict=True, reason=(
    "4 in-scope templates still carry emoji as of step 1 (BizSight's "
    "analysis_template.html and three MergerMeter files) -- removed in "
    "step 6. Flip to a hard assertion once that step lands."
))
def test_no_emoji_in_scope():
    """Part D item 6 (step 1, scoped): no in-scope template or CSS file
    contains emoji or decorative unicode.

    Scoped to IN_SCOPE_TEMPLATES + IN_SCOPE_CSS, not literally every file
    under justdata/ -- the spec's own rationale ("the seven current hits")
    refers only to the emoji found in in-scope templates during the audit;
    a whole-repo scan also matches emoji in backend .py/.md/.sql files and
    in out-of-scope apps, which are not templates/stylesheets/scripts and
    are outside this buildout's do-not-touch boundary regardless.
    """
    hits = []
    for path in _in_scope_templates() + _in_scope_css():
        text = path.read_text(encoding="utf-8", errors="ignore")
        if EMOJI_RE.search(text):
            hits.append(str(path.relative_to(REPO_ROOT)))
    assert not hits, f"emoji found in in-scope files: {hits}"


# Part D item 7: per-file inline `style="` attribute budgets. Seeded at step 1
# with the EXACT current count for every in-scope template (computed, not
# copied from the audit, so this is accurate as of this commit). Each later
# step that converts a file's inline styles to CSS lowers that file's number;
# step 8 drives every budget to 0. A file exceeding its budget fails -- a file
# under budget is fine (it means a later step already improved it).
#
# Step 2 addendum: the three new shell partials below (_auth_modal.html,
# _banners.html, _header.html) carry a small, deliberate budget -- every
# entry is `style="display: none;"`, the JS-toggle initial state shell.js's
# verbatim-moved functions expect (they set `.style.display` directly, not
# a CSS class). This is the functional category the ratchet doesn't target;
# see the audit's finding 4 and the step 1/2 spec text for the distinction
# from decorative inline styling. _nav.html and _footer.html need none.
INLINE_STYLE_BUDGET: dict[str, int] = {
    "justdata/shared/web/templates/partials/_auth_modal.html": 8,
    "justdata/shared/web/templates/partials/_banners.html": 4,
    "justdata/shared/web/templates/partials/_header.html": 6,
    "justdata/apps/analytics/templates/analytics/coalitions.html": 3,
    "justdata/apps/analytics/templates/analytics/costs.html": 4,
    "justdata/apps/analytics/templates/analytics/dashboard.html": 7,
    "justdata/apps/analytics/templates/analytics/lender_detail.html": 2,
    "justdata/apps/analytics/templates/analytics/lender_map.html": 2,
    "justdata/apps/analytics/templates/analytics/research_map.html": 5,
    "justdata/apps/analytics/templates/analytics/user_map.html": 2,
    "justdata/apps/analytics/templates/analytics/users.html": 3,
    "justdata/apps/bizsight/templates/analysis_template.html": 47,
    "justdata/apps/bizsight/templates/bizsight_analysis.html": 20,
    "justdata/apps/bizsight/templates/bizsight_report.html": 1,
    "justdata/apps/bizsight/templates/partials/_bizsight_report_main.html": 116,
    "justdata/apps/bizsight/templates/partials/_bizsight_report_scripts.html": 93,
    "justdata/apps/branchsight/templates/branchsight_analysis.html": 17,
    "justdata/apps/branchsight/templates/partials/_branchsight_report_main.html": 75,
    "justdata/apps/branchsight/templates/partials/_branchsight_report_scripts.html": 12,
    "justdata/apps/lendsight/templates/analysis_template.html": 1,
    "justdata/apps/lendsight/templates/lendsight_report.html": 1,
    "justdata/apps/lendsight/templates/partials/_lendsight_analysis_content.html": 42,
    "justdata/apps/lendsight/templates/partials/_lendsight_analysis_extra_js.html": 2,
    "justdata/apps/lendsight/templates/partials/_lendsight_analysis_template_main.html": 43,
    "justdata/apps/lendsight/templates/partials/_lendsight_analysis_template_scripts.html": 2,
    "justdata/apps/lendsight/templates/partials/_lendsight_report_main.html": 89,
    "justdata/apps/lendsight/templates/partials/_lendsight_report_scripts.html": 51,
    "justdata/apps/mergermeter/templates/analysis_template.html": 1,
    "justdata/apps/mergermeter/templates/goals_calculator.html": 3,
    "justdata/apps/mergermeter/templates/mergermeter_analysis.html": 249,
    "justdata/apps/mergermeter/templates/mergermeter_report.html": 73,
    "justdata/apps/mergermeter/templates/partials/_analysis_main.html": 204,
    "justdata/apps/mergermeter/templates/partials/_analysis_scripts.html": 44,
    "justdata/apps/mergermeter/templates/partials/_analysis_template_footer.html": 15,
    "justdata/apps/mergermeter/templates/partials/_analysis_template_main.html": 175,
    "justdata/apps/mergermeter/templates/partials/_analysis_template_scripts.html": 27,
    "justdata/apps/mergermeter/templates/partials/_mergermeter_report_main.html": 7,
    "justdata/apps/mergermeter/templates/partials/_mergermeter_report_scripts.html": 65,
    "justdata/shared/web/templates/access_restricted.html": 2,
    "justdata/shared/web/templates/admin-dashboard.html": 4,
    "justdata/shared/web/templates/admin-users.html": 24,
    "justdata/shared/web/templates/analysis_template.html": 15,
    "justdata/shared/web/templates/about.html": 0,
    "justdata/shared/web/templates/base_app.html": 0,
    "justdata/shared/web/templates/contact.html": 1,
    "justdata/shared/web/templates/email_verified.html": 3,
    "justdata/shared/web/templates/home.html": 0,
    "justdata/shared/web/templates/member_request_modal.html": 4,
    "justdata/shared/web/templates/nav_menu.html": 7,
    "justdata/shared/web/templates/report_template.html": 33,
    "justdata/shared/web/templates/shared_header.html": 79,
    "justdata/shared/web/templates/status-dashboard.html": 1,
}

INLINE_STYLE_RE = re.compile(r'style="')


def test_inline_style_budget():
    """Part D item 7 (step 1): every in-scope template's inline `style="`
    count is at or under its budget. Files not in the dict, or with a
    template that no longer exists, are treated as budget 0 -- a new
    in-scope template must not introduce fresh inline styles, and a deleted
    template's budget entry should be removed in the step that deletes it."""
    over_budget = []
    seen = set()
    for path in _in_scope_templates():
        rel = str(path.relative_to(REPO_ROOT))
        seen.add(rel)
        text = path.read_text(encoding="utf-8", errors="ignore")
        count = len(INLINE_STYLE_RE.findall(text))
        budget = INLINE_STYLE_BUDGET.get(rel, 0)
        if count > budget:
            over_budget.append(f"{rel}: {count} > budget {budget}")

    assert not over_budget, "inline style= count exceeds budget:\n" + "\n".join(over_budget)

    stale_entries = sorted(set(INLINE_STYLE_BUDGET) - seen)
    assert not stale_entries, (
        "INLINE_STYLE_BUDGET has entries for files that no longer exist -- "
        f"remove them: {stale_entries}"
    )


# ---------------------------------------------------------------------------
# Part D item 13 (step 1): contrast. Pure-function WCAG relative-luminance
# check, parsed from tokens.css itself so the numbers are checked, not trusted.
# ---------------------------------------------------------------------------

TOKENS_CSS_PATH = JUSTDATA_DIR / "shared" / "web" / "static" / "css" / "tokens.css"

HEX_RE = re.compile(r"^#([0-9A-Fa-f]{6})$")
VAR_DECL_RE = re.compile(r"--([a-zA-Z0-9-]+)\s*:\s*([^;]+);")
VAR_REF_RE = re.compile(r"^var\(--([a-zA-Z0-9-]+)\)$")


def _parse_tokens_css() -> dict[str, str]:
    """Return {token-name: raw-value} for every custom property declared in
    tokens.css's :root block (first block only -- tokens.css must have
    exactly one, enforced by test_single_root_block)."""
    text = TOKENS_CSS_PATH.read_text(encoding="utf-8")
    match = re.search(r":root\s*\{(.*?)\n\}", text, re.DOTALL)
    assert match, "tokens.css must contain a :root { ... } block"
    body = match.group(1)
    raw: dict[str, str] = {}
    for m in VAR_DECL_RE.finditer(body):
        raw[m.group(1)] = m.group(2).strip()
    return raw


def _resolve_hex(name: str, raw: dict[str, str], _seen: frozenset[str] = frozenset()) -> str:
    """Resolve a token name to a #RRGGBB hex string, following var(--x)
    chains. Raises AssertionError on a cycle or an unresolvable/non-hex value
    (this file only ever resolves tokens whose final value is a plain hex
    color -- if that stops being true, the test needs a person to look, not
    a silent skip)."""
    assert name not in _seen, f"circular var() reference resolving --{name}"
    assert name in raw, f"tokens.css has no --{name}"
    value = raw[name]
    hex_match = HEX_RE.match(value)
    if hex_match:
        return "#" + hex_match.group(1)
    var_match = VAR_REF_RE.match(value)
    assert var_match, f"--{name}: {value!r} is neither a hex color nor a plain var() reference"
    return _resolve_hex(var_match.group(1), raw, _seen | {name})


def _srgb_channel_to_linear(c: float) -> float:
    c /= 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _relative_luminance(hex_color: str) -> float:
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
    r, g, b = (_srgb_channel_to_linear(v) for v in (r, g, b))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_ratio(hex_a: str, hex_b: str) -> float:
    la, lb = _relative_luminance(hex_a), _relative_luminance(hex_b)
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


# (token-a, token-b, minimum-ratio, label) -- see spec Part D item 13.
CONTRAST_PAIRS: list[tuple[str, str, float, str]] = [
    ("color-fg-on-dark", "color-bg-dark", 4.5, "header/footer text on dark surface"),
    ("color-fg-on-dark", "color-bg-dark-hover", 4.5, "header/footer text on dark-hover surface"),
    ("color-fg-on-accent", "color-bg-accent", 4.5, "text on cyan accent surface"),
    ("color-fg", "color-bg", 4.5, "body text on page background"),
    ("color-fg", "color-bg-muted", 4.5, "body text on muted background"),
    ("color-fg", "color-bg-alt", 4.5, "body text on alt background"),
    ("color-fg", "color-bg-brand-soft", 4.5, "body text on brand-soft background"),
    ("color-fg", "color-bg-accent-soft", 4.5, "body text on accent-soft background"),
    ("color-fg-muted", "color-bg", 4.5, "muted text on page background"),
    ("color-fg-subtle", "color-bg", 3.0, "subtle text (large/non-text only) on page background"),
    ("color-link", "color-bg", 4.5, "link text on page background"),
    ("color-success-text", "color-success-bg", 4.5, "success alert text on its background"),
    ("color-warning-text", "color-warning-bg", 4.5, "warning alert text on its background"),
    ("color-danger-text", "color-danger-bg", 4.5, "danger alert text on its background"),
    ("color-info-text", "color-info-bg", 4.5, "info alert text on its background"),
    ("ncrc-red-700", "color-bg", 4.5, "danger-text token on page background"),
    # NOTE: Part D item 13 also lists "each chart palette color on bg >= 3.0"
    # for the step-7 categorical palette (blue-500, cyan-500, gold, purple,
    # magenta, neutral-500). Deliberately NOT included here: no chart code
    # exists before step 7, so this would be testing an unimplemented
    # feature, not step 1's actual deliverable. Also, two of those six
    # literal values (cyan-500 on white = 2.56:1, gold on white = 1.61:1)
    # do NOT meet 3:1 as flat text/fill on white -- confirmed by running
    # this exact check during step 1. That is a real, unresolved conflict
    # between the step-7 palette instruction and this item's requirement;
    # step 7 must resolve it (e.g. outlined/bordered marks, or different
    # literal chart colors -- Jad's call, these are Part B literal values)
    # before adding this sub-check back as a hard assertion.
]


def test_contrast_pairs_meet_wcag():
    """Part D item 13 (step 1): every semantic color pairing tokens.css
    declares must meet its WCAG minimum. Parses tokens.css itself, so this
    fails the moment anyone edits a value below its required contrast."""
    raw = _parse_tokens_css()
    failures = []
    for name_a, name_b, minimum, label in CONTRAST_PAIRS:
        hex_a = _resolve_hex(name_a, raw)
        hex_b = _resolve_hex(name_b, raw)
        ratio = _contrast_ratio(hex_a, hex_b)
        if ratio < minimum:
            failures.append(
                f"{label} (--{name_a} {hex_a} on --{name_b} {hex_b}): "
                f"{ratio:.2f}:1 < required {minimum}:1"
            )
    assert not failures, "contrast failures:\n" + "\n".join(failures)


def test_color_fg_on_accent_is_black_not_white():
    """Regression guard for the specific finding that drove this rule: the
    brand kit's default --color-fg-on-brand is white, which fails WCAG on
    cyan (2.56:1). tokens.css must keep --color-fg-on-accent pointed at
    black."""
    raw = _parse_tokens_css()
    assert _resolve_hex("color-fg-on-accent", raw) == "#000000"


# ---------------------------------------------------------------------------
# Part D item 11 (step 3): home page gating. `/` is built server-side in
# landing() from ACCESS_MATRIX via get_app_access() -- no client-side
# filtering exists any more. This mirrors the grouping in main/app.py's
# landing() exactly (see that function's home_group_defs).
# ---------------------------------------------------------------------------

HOME_PAGE_APPS = [
    "lendsight", "bizsight", "branchsight",
    "branchmapper", "dataexplorer", "mergermeter",
    "analytics", "admin",
]

# Marker only ever present on the real home page (the stats bar section),
# never on the platform-wide access_restricted.html page a non-privileged
# user gets instead -- see main/app.py's check_privileged_access.
HOME_PAGE_MARKER = b'id="platformStats"'


def test_home_page_gating():
    """Part D item 11: for every VALID_USER_TYPE, `/` shows exactly the
    apps ACCESS_MATRIX grants (and nothing else), or -- for the five
    non-privileged types, which check_privileged_access blocks from every
    route including `/` regardless of ACCESS_MATRIX -- the platform-wide
    restricted page, unchanged by this step. This is the same pattern
    tests/apps/dotlender/test_dotlender_smoke.py already uses."""
    from justdata.main.app import create_app
    from justdata.main.auth import VALID_USER_TYPES, PRIVILEGED_ROLES, get_app_access

    app = create_app()
    app.config["TESTING"] = True

    for user_type in VALID_USER_TYPES:
        client = app.test_client()
        with client.session_transaction() as sess:
            sess["firebase_user"] = {
                "uid": f"test-{user_type}",
                "email": f"test-{user_type}@example.org",
                "email_verified": True,
            }
            sess["user_type"] = user_type

        resp = client.get("/")
        assert resp.status_code == 200, f"{user_type}: expected 200, got {resp.status_code}"
        body = resp.data

        if user_type not in PRIVILEGED_ROLES:
            assert HOME_PAGE_MARKER not in body, (
                f"{user_type}: non-privileged user reached the real home page "
                "(check_privileged_access should have blocked it)"
            )
            continue

        assert HOME_PAGE_MARKER in body, f"{user_type}: expected the real home page"

        for key in HOME_PAGE_APPS:
            access = get_app_access(key, user_type)
            marker = f'data-app="{key}"'.encode()
            if access == "hidden":
                assert marker not in body, f"{user_type}/{key}: expected hidden, but card is present"
            else:
                assert marker in body, f"{user_type}/{key}: expected visible ({access}), but card is missing"
                if access == "locked":
                    locked_marker = f'data-app="{key}"'.encode()
                    idx = body.find(locked_marker)
                    # the card div carries "is-locked" on the same element as data-app
                    line_start = body.rfind(b"<div", 0, idx)
                    line_end = body.find(b">", idx)
                    assert b"is-locked" in body[line_start:line_end], (
                        f"{user_type}/{key}: locked app card missing is-locked class"
                    )


# ---------------------------------------------------------------------------
# Part D item 12 (step 3 slice): surfaces render. Only the routes step 3
# actually converts to the shell -- '/', '/about', '/contact',
# '/email-verified' -- are covered here. Steps 4-7 add their own routes to
# this table as each converts; do not add rows here for routes that don't
# extend base_app.html yet (they will fail the data-shell="header" check).
# ---------------------------------------------------------------------------

STEP3_SHELL_ROUTES = ["/", "/about", "/contact", "/email-verified"]
SHELL_HEADER_MARKER = b'data-shell="header"'


def test_step3_surfaces_render():
    """Part D item 12 (partial): every step-3-converted route renders 200
    for admin and for public_registered (the latter via the unchanged
    platform-wide restricted page, itself now also on the shell), and both
    carry the shell header marker."""
    from justdata.main.app import create_app

    app = create_app()
    app.config["TESTING"] = True

    for user_type in ("admin", "public_registered"):
        client = app.test_client()
        with client.session_transaction() as sess:
            sess["firebase_user"] = {
                "uid": f"test-{user_type}",
                "email": f"test-{user_type}@example.org",
                "email_verified": True,
            }
            sess["user_type"] = user_type

        for path in STEP3_SHELL_ROUTES:
            resp = client.get(path)
            assert resp.status_code == 200, f"{user_type} {path}: expected 200, got {resp.status_code}"
            assert SHELL_HEADER_MARKER in resp.data, f"{user_type} {path}: missing shell header marker"
            if user_type == "public_registered":
                assert HOME_PAGE_MARKER not in resp.data, (
                    f"public_registered {path}: reached real page content, expected the restricted page"
                )


# ---------------------------------------------------------------------------
# Backfill (this commit): Part D items 2, 3, 4, 5, 8, 9, 10 -- see the module
# docstring's HISTORY note for why these are landing now instead of step 2.
#
# SHELL_PARTIALS / SHELL_ENTRY_TEMPLATES / SHELL_JS define "converted" for
# every item below: the base layout, its partials, the five step-3 entry
# templates, and the buildout's own JS files (shell-nav/auth/member.js,
# home.js). auth.js and analytics-events.js are do-not-touch per Part A2 and
# were never part of this buildout's icon/token conversion, so they're
# excluded from every check here, same as they're excluded from editing.
# ---------------------------------------------------------------------------

SHELL_PARTIALS = [
    "justdata/shared/web/templates/partials/_head.html",
    "justdata/shared/web/templates/partials/_header.html",
    "justdata/shared/web/templates/partials/_nav.html",
    "justdata/shared/web/templates/partials/_footer.html",
    "justdata/shared/web/templates/partials/_auth_modal.html",
    "justdata/shared/web/templates/partials/_banners.html",
]

SHELL_ENTRY_TEMPLATES = [
    "justdata/shared/web/templates/home.html",
    "justdata/shared/web/templates/about.html",
    "justdata/shared/web/templates/contact.html",
    "justdata/shared/web/templates/access_restricted.html",
    "justdata/shared/web/templates/email_verified.html",
]

SHELL_BASE_TEMPLATE = ["justdata/shared/web/templates/base_app.html"]

SHELL_JS = [
    "justdata/shared/web/static/js/shell-nav.js",
    "justdata/shared/web/static/js/shell-auth.js",
    "justdata/shared/web/static/js/shell-member.js",
    "justdata/shared/web/static/js/home.js",
]


def _read(rel_path: str) -> str:
    return (REPO_ROOT / rel_path).read_text(encoding="utf-8")


HEX_LITERAL_RE = re.compile(r"#[0-9A-Fa-f]{3,8}\b")
RGB_LITERAL_RE = re.compile(r"\brgba?\([0-9]")
FONT_FAMILY_LITERAL_RE = re.compile(r"font-family:\s*(['\"]?)(?!var\()[A-Za-z]")

# Part D item 2's own allowlist: tokens.css's shadow rgba values, plus
# currentColor/transparent/inherit (not literal colors).
TOKEN_ONLY_CSS_FILES = [
    "justdata/shared/web/static/css/home.css",
    "justdata/shared/web/static/css/shell.css",
]


def test_token_values_only_in_converted_css():
    """Part D item 2, scoped to CSS files fully converted onto tokens as of
    this commit (see module docstring). Every color must be var(--...);
    no hex literal, no literal rgb()/rgba() channels, no literal
    font-family name."""
    failures = []
    for rel in TOKEN_ONLY_CSS_FILES:
        text = _read(rel)
        if HEX_LITERAL_RE.search(text):
            failures.append(f"{rel}: contains a hex color literal")
        if RGB_LITERAL_RE.search(text):
            failures.append(f"{rel}: contains a literal rgb()/rgba()")
        if FONT_FAMILY_LITERAL_RE.search(text):
            failures.append(f"{rel}: contains a literal font-family name")
    assert not failures, "token-only violations:\n" + "\n".join(failures)


FORBIDDEN_CSS_RE = re.compile(
    r"linear-gradient|radial-gradient|backdrop-filter|filter:\s*blur|"
    r"transform:\s*scale|border-radius:\s*(6px|12px|15px|20px)\b"
)


def test_no_forbidden_css_in_converted_files():
    """Part D item 3, scoped to the converted shell templates/CSS (ratchets
    per step as later steps convert more files). No gradients,
    backdrop-filter, blur, transform:scale, or the specific banned radii."""
    files = (
        SHELL_BASE_TEMPLATE + SHELL_PARTIALS + SHELL_ENTRY_TEMPLATES
        + ["justdata/shared/web/static/css/shell.css", "justdata/shared/web/static/css/home.css"]
    )
    failures = []
    for rel in files:
        text = _read(rel)
        m = FORBIDDEN_CSS_RE.search(text)
        if m:
            failures.append(f"{rel}: forbidden pattern {m.group(0)!r}")
    assert not failures, "forbidden CSS found:\n" + "\n".join(failures)


INTER_LINK_RE = re.compile(r"fonts\.googleapis\.com/css2\?family=Inter")
BARLOW_LINK = (
    "https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600;700"
    "&family=Barlow+Condensed:wght@600;700;800&display=swap"
)


def test_fonts_no_inter_in_converted_templates():
    """Part D item 4, scoped to the converted shell templates. No Inter
    Google Fonts link; _head.html carries the exact Part B2 Barlow URL
    exactly once."""
    failures = []
    for rel in SHELL_BASE_TEMPLATE + SHELL_PARTIALS + SHELL_ENTRY_TEMPLATES:
        if INTER_LINK_RE.search(_read(rel)):
            failures.append(f"{rel}: still links the Inter font")
    assert not failures, "Inter font link found:\n" + "\n".join(failures)

    head_text = _read("justdata/shared/web/templates/partials/_head.html")
    assert head_text.count(BARLOW_LINK) == 1, (
        "_head.html must carry the exact Part B2 Barlow URL exactly once"
    )


FA_CLASS_RE = re.compile(r"\bfa[srlb]?\s+fa-|\bfa-[a-z]")
DATA_LUCIDE_RE = re.compile(r'data-lucide=\\?["\']([a-z0-9-]+)')
JS_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)


def _strip_js_block_comments(text: str) -> str:
    """shell-auth.js and shell-member.js both document, in their own header
    comments, that FA markup like `fas fa-spinner` used to be there and was
    swapped for Lucide -- real history, not a violation. Strip /* */ blocks
    before scanning .js files so that documentation doesn't trip the FA
    check meant for actual markup/code."""
    return JS_BLOCK_COMMENT_RE.sub("", text)

LUCIDE_ICONS_FIXTURE = (
    REPO_ROOT / "tests" / "shared" / "fixtures" / "lucide-1.47.0-icons.txt"
)


def _valid_lucide_names() -> set[str]:
    return set(LUCIDE_ICONS_FIXTURE.read_text(encoding="utf-8").split())


def test_icons_no_font_awesome_and_lucide_names_valid():
    """Part D item 5, scoped to the converted shell templates/JS. No
    font-awesome references or fa-* classes; every data-lucide value is a
    real icon name in the pinned Lucide 1.47.0 build (gate G7). The fixture
    is generated from the actual npm package's iconsAndAliases.mjs export
    list (canonical names + aliases, kebab-cased and cross-checked against
    each export's own file name) -- see the fixture's generation note below
    if it ever needs regenerating for a version bump."""
    valid_names = _valid_lucide_names()
    failures = []
    for rel in SHELL_BASE_TEMPLATE + SHELL_PARTIALS + SHELL_ENTRY_TEMPLATES + SHELL_JS:
        text = _read(rel)
        scan_text = _strip_js_block_comments(text) if rel.endswith(".js") else text
        if "font-awesome" in scan_text or FA_CLASS_RE.search(scan_text):
            failures.append(f"{rel}: still references Font Awesome")
        for name in DATA_LUCIDE_RE.findall(text):
            if name not in valid_names:
                failures.append(f"{rel}: data-lucide=\"{name}\" is not a valid Lucide 1.47.0 icon name")
    assert not failures, "icon violations:\n" + "\n".join(failures)


STYLE_BLOCK_RE = re.compile(r"<style[\s>]", re.IGNORECASE)


def test_no_style_blocks_in_converted_templates():
    """Part D item 8, scoped to the converted shell templates (ratchets per
    step)."""
    failures = [
        rel for rel in SHELL_BASE_TEMPLATE + SHELL_PARTIALS + SHELL_ENTRY_TEMPLATES
        if STYLE_BLOCK_RE.search(_read(rel))
    ]
    assert not failures, f"<style> block found in: {failures}"


def test_converted_entry_templates_extend_base_app():
    """Part D item 9, scoped to the entry templates this buildout has
    converted so far (ratchets per step as steps 4-7 convert their own)."""
    failures = []
    for rel in SHELL_ENTRY_TEMPLATES:
        text = _read(rel)
        if '{% extends "base_app.html" %}' not in text and "{% extends 'base_app.html' %}" not in text:
            failures.append(rel)
    assert not failures, f"entry template(s) not extending base_app.html: {failures}"


# Part D item 10: the DOM-ID contract. Spec's step-2 text lists 49 IDs as
# "must exist... because auth.js/shell.js read them." Verified against the
# actual rendered shell and the actual JS source before writing this list;
# 5 of the 49 are deliberately excluded, each for a specific, checked
# reason (not a guess):
#   - organization-prompt-modal, org-prompt-input, org-prompt-skip,
#     org-prompt-submit: auth.js (justdata/shared/web/static/js/auth.js,
#     ~line 498) creates this modal and its children itself with
#     document.createElement when needed -- it is never server-rendered,
#     so asserting it in static HTML would be testing something that is
#     never true by design.
#   - userInfo: auth.js reads it only behind `if (userInfo)` with an
#     explicit comment "Legacy userInfo (if present on older pages)" --
#     it is optional by auth.js's own contract, not required.
#   - registerName: does not appear in auth.js, shell-auth.js, or any
#     other JS in the repo (grepped) -- nothing reads it, so nothing
#     requires it to exist. Likely a stale reference in the spec from
#     before the first/last-name split (registerFirstName/registerLastName,
#     which auth.js does use).
DOM_ID_CONTRACT = [
    "loginBtn", "logoutBtn", "userMenuContainer", "userEmail", "userTypeBadge", "userAvatar",
    "loginModal", "signInTab", "registerTab", "signInView", "registerView",
    "loginEmail", "loginPassword", "loginError",
    "emailLoginBtn", "emailLoginSpinner", "emailLoginText",
    "googleLoginBtn", "googleLoginSpinner", "googleLoginText",
    "registerFirstName", "registerLastName", "registerEmail", "registerOrganization",
    "registerPassword", "registerPasswordConfirm", "registerError", "registerSuccess",
    "emailRegisterBtn", "emailRegisterSpinner", "emailRegisterText",
    "emailVerificationBanner", "resendVerificationBtn", "resendVerificationSpinner",
    "resendVerificationText", "userMenuToggle", "userDropdownMenu", "dropdownDivider",
    "requestMemberAccessLink", "menuToggle", "navSidebar", "navBackdrop", "navCloseBtn",
]


def test_dom_id_contract():
    """Part D item 10: render the shell (via /about, the simplest route
    that already extends base_app.html) as admin and assert every ID
    auth.js/shell-*.js need is present exactly once, and that auth.js and
    analytics-events.js are both loaded."""
    from justdata.main.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["firebase_user"] = {"uid": "test-admin", "email": "admin@example.org", "email_verified": True}
        sess["user_type"] = "admin"

    resp = client.get("/about")
    assert resp.status_code == 200
    body = resp.data.decode()

    failures = []
    for dom_id in DOM_ID_CONTRACT:
        count = len(re.findall(f'id="{re.escape(dom_id)}"', body))
        if count != 1:
            failures.append(f"{dom_id}: found {count} times, expected 1")
    assert not failures, "DOM-ID contract violations:\n" + "\n".join(failures)

    assert "js/auth.js" in body, "auth.js must be loaded"
    assert "js/analytics-events.js" in body, "analytics-events.js must be loaded"
