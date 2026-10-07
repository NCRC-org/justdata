"""Nav registry and testing-site access overlay (spec 01).

On JUSTDATA_ENV=testing every non-staff role sees exactly the four tester
apps in the drawer, and the route gate (get_app_access) agrees with it.
Staff roles, and every role on other deploys, read ACCESS_MATRIX unchanged.
"""

import pytest

from justdata.main.auth import (
    ACCESS_MATRIX,
    PRIVILEGED_ROLES,
    VALID_USER_TYPES,
    get_access_row,
    get_app_access,
)
from justdata.main.auth.access_overlay import TESTER_APPS, TESTER_ROLES
from justdata.shared.web.registry import NAV_GROUPS, resolve_registry

NON_STAFF_ROLES = [r for r in VALID_USER_TYPES if r not in PRIVILEGED_ROLES]
REGISTRY_APP_KEYS = [
    e.key for g in NAV_GROUPS for e in g.items if e.key not in ("home", "apps")
]


def test_staff_only_groups_hold_the_consolidation_and_staff_tools():
    groups = {g.label: [e.key for e in g.items] for g in NAV_GROUPS if g.staff_only}
    assert groups == {
        "Staff tools": ["mergermeter", "analytics", "admin"],
        "In consolidation": ["branchmapper", "dotlender", "dataexplorer"],
    }


def _drawer(user_type):
    """{key: state} for every app item the drawer renders."""
    return {
        item["key"]: item["state"]
        for group in resolve_registry(get_access_row, user_type, is_staff=user_type in PRIVILEGED_ROLES)
        for item in group["items"]
        if item["key"] not in ("home", "apps")
    }


def _expected_from_matrix(user_type):
    """What the drawer shows with no overlay: straight from ACCESS_MATRIX,
    minus staff_only groups for non-staff roles (presentation only)."""
    states = {"full": "available", "limited": "available", "locked": "locked"}
    staff = user_type in PRIVILEGED_ROLES
    keys = [e.key for g in NAV_GROUPS if staff or not g.staff_only
            for e in g.items if e.key not in ("home", "apps")]
    out = {}
    for key in keys:
        level = ACCESS_MATRIX.get(key, {}).get(user_type, "hidden")
        if level in states:
            out[key] = states[level]
    return out


@pytest.fixture
def testing_env(monkeypatch):
    monkeypatch.setenv("JUSTDATA_ENV", "testing")


def test_tester_apps_are_exactly_the_three_sight_apps():
    assert set(TESTER_APPS) == {"lendsight", "bizsight", "branchsight"}


@pytest.mark.parametrize("user_type", NON_STAFF_ROLES)
def test_testing_env_non_staff_see_exactly_the_three_tester_apps(testing_env, user_type):
    drawer = _drawer(user_type)
    assert set(drawer) == set(TESTER_APPS)
    expected = "available" if user_type in TESTER_ROLES else "locked"
    assert set(drawer.values()) == {expected}


@pytest.mark.parametrize("user_type", NON_STAFF_ROLES)
def test_testing_env_no_other_app_is_available_or_locked_for_non_staff(testing_env, user_type):
    for key in ACCESS_MATRIX:
        if key not in TESTER_APPS:
            assert get_app_access(key, user_type) == "hidden", key


@pytest.mark.parametrize("user_type", NON_STAFF_ROLES)
def test_mergermeter_is_staff_only_on_every_deploy(monkeypatch, user_type):
    for env in ("testing", "staging", "production"):
        monkeypatch.setenv("JUSTDATA_ENV", env)
        assert get_app_access("mergermeter", user_type) == "hidden", env


@pytest.mark.parametrize("user_type", NON_STAFF_ROLES)
def test_testing_env_route_gate_matches_drawer(testing_env, user_type):
    drawer = _drawer(user_type)
    for key in REGISTRY_APP_KEYS:
        level = get_app_access(key, user_type)
        if key in drawer:
            assert level != "hidden", key
        else:
            assert level == "hidden", key


@pytest.mark.parametrize("user_type", PRIVILEGED_ROLES)
def test_testing_env_staff_unchanged_from_matrix(testing_env, user_type):
    assert _drawer(user_type) == _expected_from_matrix(user_type)
    for key in ACCESS_MATRIX:
        assert get_app_access(key, user_type) == ACCESS_MATRIX[key].get(user_type, "hidden")


@pytest.mark.parametrize("env", [None, "staging", "production"])
@pytest.mark.parametrize("user_type", VALID_USER_TYPES)
def test_other_envs_read_matrix_unchanged(monkeypatch, env, user_type):
    if env is None:
        monkeypatch.delenv("JUSTDATA_ENV", raising=False)
    else:
        monkeypatch.setenv("JUSTDATA_ENV", env)
    assert _drawer(user_type) == _expected_from_matrix(user_type)
    for key in ACCESS_MATRIX:
        assert get_access_row(key) == ACCESS_MATRIX[key]


def test_overlay_does_not_mutate_access_matrix(testing_env):
    before = {k: dict(v) for k, v in ACCESS_MATRIX.items()}
    for key in ACCESS_MATRIX:
        get_access_row(key)
    assert ACCESS_MATRIX == before
