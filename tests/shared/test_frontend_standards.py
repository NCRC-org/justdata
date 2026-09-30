"""
Acceptance tests for the JustData frontend buildout.

Spec: L5 "JustData -- Frontend buildout spec -- 2026-09-21" Part D. Each test
function is tagged with the buildout step that introduces it, matching Part D's
numbering. This file is created in step 1 and extended in later steps -- do not
add a step-N+ test before that step's PR, since some of them depend on things
that don't exist yet (e.g. the pinned Lucide version from step 2's gate G7, the
shell's DOM-ID contract from step 2, ACCESS_MATRIX-driven home page from step 3).

Part D items NOT yet implemented here, and the step that adds them:
  2  Token values only (color literals banned outside tokens.css)   -- step 2
  3  No forbidden CSS (gradients/backdrop-filter/blur/scale/radii) -- step 2 (ratchets per step)
  4  Fonts (no Inter link; _head.html carries the Barlow link)      -- step 2
  5  Icons (no Font Awesome; every data-lucide name is valid)       -- step 2
  8  No <style> blocks in converted templates                       -- step 2 (ratchets per step)
  9  Every converted entry template extends base_app.html           -- step 2 (ratchets per step)
  10 DOM-ID contract (shell renders every ID auth.js/shell.js need) -- step 2

NOTE added in step 3: items 2, 3, 4, 5, 8, 9 and 10 above are still not
implemented in this file even though step 2 (PR #193, merged) is the step
that was supposed to add them, and both step 2's PR acceptance checklist and
its L5 log state they pass. They do not exist anywhere in the repo as of
this commit (confirmed: `git show 5b9883b -- tests/shared/test_frontend_standards.py`
touches only the INLINE_STYLE_BUDGET dict). This is a real gap between what
step 2 claimed was verified and what actually landed on `testing` -- not
something step 3 fixes (out of this step's file list/scope), but flagged
here, in the step 3 PR body, and in the step 3 L5 log for Jad. Items 11 and
12 below are implemented now because step 3 is explicitly their step.

Implemented here: items 1, 6, 7, 13 (step 1); 11, 12-partial (step 3, scoped
to the routes step 3 actually converts -- '/', '/about', '/contact',
'/email-verified'; the rest of item 12's table is added as steps 4-7 convert
their routes).
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
