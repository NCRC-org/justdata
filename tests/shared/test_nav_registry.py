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


def _drawer(user_type):
    """{key: state} for every app item the drawer renders."""
    return {
        item["key"]: item["state"]
        for group in resolve_registry(get_access_row, user_type)
        for item in group["items"]
        if item["key"] not in ("home", "apps")
    }


def _expected_from_matrix(user_type):
    """What the drawer shows with no overlay: straight from ACCESS_MATRIX."""
    states = {"full": "available", "limited": "available", "locked": "locked"}
    out = {}
    for key in REGISTRY_APP_KEYS:
        level = ACCESS_MATRIX.get(key, {}).get(user_type, "hidden")
        if level in states:
            out[key] = states[level]
    return out


@pytest.fixture
def testing_env(monkeypatch):
    monkeypatch.setenv("JUSTDATA_ENV", "testing")


@pytest.mark.parametrize("user_type", NON_STAFF_ROLES)
def test_testing_env_non_staff_see_exactly_the_four_tester_apps(testing_env, user_type):
    drawer = _drawer(user_type)
    assert set(drawer) == set(TESTER_APPS)
    expected_mm = "available" if user_type in TESTER_ROLES else "locked"
    assert drawer["mergermeter"] == expected_mm


@pytest.mark.parametrize("user_type", TESTER_ROLES)
def test_testing_env_testers_can_open_mergermeter(testing_env, user_type):
    assert _drawer(user_type)["mergermeter"] == "available"
    assert get_app_access("mergermeter", user_type) == "full"


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
