"""SECRET_KEY is required (Codex review finding 1, 2026-11-09).

The session cookie carries the user's role, so a key anyone can read lets
anyone sign a cookie as admin. Outside FLASK_DEBUG the app refuses to start
without SECRET_KEY or with a default this repo once shipped.
"""

import pytest

from justdata.shared.web import app_factory
from justdata.shared.web.app_factory import resolve_secret_key


def test_set_key_is_used(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "a-private-key")
    assert resolve_secret_key() == "a-private-key"


@pytest.mark.parametrize("debug", ["false", ""])
def test_unset_key_refuses_to_start(monkeypatch, debug):
    monkeypatch.delenv("SECRET_KEY")
    monkeypatch.setenv("FLASK_DEBUG", debug)
    with pytest.raises(RuntimeError, match="SECRET_KEY is not set"):
        resolve_secret_key()


@pytest.mark.parametrize("default", sorted(app_factory._PUBLIC_DEFAULT_KEYS))
def test_public_defaults_are_refused(monkeypatch, default):
    monkeypatch.setenv("SECRET_KEY", default)
    with pytest.raises(RuntimeError, match="public default"):
        resolve_secret_key()


@pytest.mark.parametrize("debug", ["1", "true", "True"])
def test_debug_uses_a_random_key(monkeypatch, debug):
    monkeypatch.delenv("SECRET_KEY")
    monkeypatch.setenv("FLASK_DEBUG", debug)
    first, second = resolve_secret_key(), resolve_secret_key()
    assert len(first) == 64 and first != second


def test_platform_app_refuses_to_start_without_a_key(monkeypatch):
    from justdata.main.app import create_app
    monkeypatch.delenv("SECRET_KEY")
    with pytest.raises(RuntimeError):
        create_app()


def test_shared_factory_refuses_to_start_without_a_key(monkeypatch):
    monkeypatch.delenv("SECRET_KEY")
    with pytest.raises(RuntimeError):
        app_factory.create_app("anyapp")


def test_platform_app_refuses_the_old_default_key(monkeypatch):
    """The live hole: every service ran on this default, so anyone could sign
    a session cookie as admin."""
    from justdata.main.app import create_app
    monkeypatch.setenv("SECRET_KEY", "justdata-secret-key-change-in-production")
    with pytest.raises(RuntimeError, match="public default"):
        create_app()
