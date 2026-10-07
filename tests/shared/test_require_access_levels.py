"""Every require_access(app, level) call names an app and a level ACCESS_MATRIX defines.

has_access() maps an unknown level to 0, so a typo such as 'partial' silently
admits every role, including roles the matrix marks 'hidden'. BranchMapper
shipped that way. This guards every call site in the repo except ElectWatch,
which is archived (not registered) and whose app key left ACCESS_MATRIX.
"""

import re
from pathlib import Path

import pytest

from justdata.main.auth import ACCESS_MATRIX

ROOT = Path(__file__).resolve().parents[2] / "justdata"
CALL_RE = re.compile(r"""require_access\(\s*['"]([^'"]+)['"]\s*(?:,\s*['"]([^'"]+)['"])?""")
DEFINED_LEVELS = {level for row in ACCESS_MATRIX.values() for level in row.values()}

CALLS = []
for path in sorted(ROOT.rglob("*.py")):
    if "electwatch" in path.parts:
        continue
    for lineno, line in enumerate(path.read_text(errors="ignore").splitlines(), 1):
        if line.lstrip().startswith(("def require_access", "#")):
            continue
        for app_name, level in CALL_RE.findall(line):
            CALLS.append(pytest.param(app_name, level or "limited",
                                      id=f"{path.relative_to(ROOT)}:{lineno}"))


def test_call_sites_found():
    assert len(CALLS) > 40


@pytest.mark.parametrize("app_name,level", CALLS)
def test_require_access_uses_a_defined_app_and_level(app_name, level):
    assert app_name in ACCESS_MATRIX, f"unknown app {app_name!r}"
    assert level in DEFINED_LEVELS, f"{level!r} is not an ACCESS_MATRIX level {sorted(DEFINED_LEVELS)}"
