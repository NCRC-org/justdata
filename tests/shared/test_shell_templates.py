"""Template guards for the shell nav (retire-shared-header PR).

1. shell-nav.js and shared_header.html's inline script both declare top-level
   `const menuToggle`/`navSidebar`, so no page may load both (the second throws
   a redeclaration SyntaxError). Checked over each template's full
   include/extends closure.
2. The nav registry (shared/web/registry.py) is the only app list: no
   template outside partials/_nav.html may hardcode an app link list.

ElectWatch is archived (not registered) and excluded.
"""

import re
from pathlib import Path

import pytest

from justdata.shared.web.registry import NAV_GROUPS

ROOT = Path(__file__).resolve().parents[2] / "justdata"
TEMPLATE_DIRS = [p for p in ROOT.rglob("templates") if p.is_dir() and "electwatch" not in p.parts]

# name -> files. Names are what {% include %}/{% extends %} use, relative to a
# templates/ dir. A name that exists in several apps maps to all of them, so
# the closure is conservative (it can only over-report).
TEMPLATES = {}
for d in TEMPLATE_DIRS:
    for f in d.rglob("*.html"):
        TEMPLATES.setdefault(f.relative_to(d).as_posix(), []).append(f)

SHELL_NAV_SCRIPT_RE = re.compile(r"<script[^>]+src=[^>]*shell-nav\.js")
REF_RE = re.compile(r"{%-?\s*(?:include|extends|import|from)\s+['\"]([^'\"]+)['\"]")


def _closure(name, seen=None):
    seen = set() if seen is None else seen
    for f in TEMPLATES.get(name, []):
        if f in seen:
            continue
        seen.add(f)
        for ref in REF_RE.findall(f.read_text(errors="ignore")):
            _closure(ref, seen)
    return seen


@pytest.mark.parametrize("name", sorted(TEMPLATES))
def test_no_template_loads_shell_nav_js_and_shared_header(name):
    files = _closure(name)
    has_shared_header = any(f.name == "shared_header.html" for f in files)
    has_shell_nav_js = any(SHELL_NAV_SCRIPT_RE.search(f.read_text(errors="ignore")) for f in files)
    assert not (has_shared_header and has_shell_nav_js), (
        f"{name} pulls in both shared_header.html and shell-nav.js"
    )


APP_ROOTS = sorted({
    e.url for g in NAV_GROUPS for e in g.items if e.url not in ("/", "/apps")
} | {"/redlining", "/memberview"})
APP_HREF_RE = re.compile(r'href="(' + "|".join(re.escape(u) for u in APP_ROOTS) + r')/?"')
DATA_APP_RE = re.compile(r'data-app="([a-z]+)"')

# TODO(spec 04): delete nav_menu.html and shared analysis_template.html, then
# remove this allowlist entirely. It must not outlive that removal.
# Dead legacy markup, not rendered by any route.
# nav_menu.html is only included by shared analysis_template.html, which the
# MergerMeter template loader shadows with its own analysis_template.html.
HARDCODED_NAV_ALLOWLIST = {"nav_menu.html"}


def _guarded_templates():
    for name, files in sorted(TEMPLATES.items()):
        if name == "partials/_nav.html" or name in HARDCODED_NAV_ALLOWLIST:
            continue
        for f in files:
            yield pytest.param(f, id=f.relative_to(ROOT).as_posix())


@pytest.mark.parametrize("path", list(_guarded_templates()))
def test_no_hardcoded_app_link_list(path):
    text = path.read_text(errors="ignore")
    data_apps = set(DATA_APP_RE.findall(text))
    app_hrefs = set(APP_HREF_RE.findall(text))
    assert len(data_apps) <= 1 and len(app_hrefs) <= 1, (
        f"{path.name} hardcodes an app list (data-app={sorted(data_apps)}, "
        f"hrefs={sorted(app_hrefs)}); render it from nav_groups instead"
    )
