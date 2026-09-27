import importlib
import sys
import types
from pathlib import Path

import pytest

from tests.helpers.import_state import clear_module


def _real_core_package():
    root = Path(__file__).resolve().parent.parent
    core = sys.modules.get("core") or types.ModuleType("core")
    sys.modules["core"] = core
    core.__path__ = [str(root / "core")]
    clear_module("core.auth")
    return core


def _make_manager(tmp_path):
    _real_core_package()
    auth_mod = importlib.import_module("core.auth")
    auth_mod._hash_password = lambda password: f"hash:{password}"
    auth_mod._verify_password = lambda password, hashed: hashed == f"hash:{password}"
    return auth_mod.AuthManager(str(tmp_path / "auth.json"))


@pytest.fixture
def guest_on(monkeypatch):
    monkeypatch.setenv("MYAI_GUEST_ENABLED", "true")
    monkeypatch.setenv("MYAI_GUEST_PASSWORD", "operator-guest-pw")


@pytest.fixture(autouse=True)
def _clean_guest_env(monkeypatch):
    monkeypatch.delenv("MYAI_GUEST_ENABLED", raising=False)
    monkeypatch.delenv("MYAI_GUEST_PASSWORD", raising=False)


def test_guest_disabled_by_default(tmp_path):
    mgr = _make_manager(tmp_path)
    assert mgr.create_user("admin", "admin-password", is_admin=True) is True
    mgr.ensure_builtin_guest()
    assert "guest" not in mgr.users
    assert mgr.verify_password("guest", "Guest123") is False


def test_disabling_guest_removes_account_and_revokes_sessions(tmp_path, monkeypatch):
    monkeypatch.setenv("MYAI_GUEST_ENABLED", "true")
    monkeypatch.setenv("MYAI_GUEST_PASSWORD", "operator-guest-pw")
    mgr = _make_manager(tmp_path)
    assert mgr.create_user("admin", "admin-password", is_admin=True) is True
    assert mgr.ensure_builtin_guest() is True
    token = mgr.create_session_trusted("guest")
    assert mgr.validate_token(token) is True

    monkeypatch.delenv("MYAI_GUEST_ENABLED")
    assert mgr.ensure_builtin_guest() is True
    assert "guest" not in mgr.users
    assert mgr.validate_token(token) is False


def test_guest_not_seeded_before_admin_setup(tmp_path, guest_on):
    mgr = _make_manager(tmp_path)
    assert mgr.is_configured is False
    assert "guest" not in mgr.users


def test_enabled_guest_uses_operator_password(tmp_path, guest_on):
    mgr = _make_manager(tmp_path)
    assert mgr.create_user("admin", "admin-password", is_admin=True) is True
    assert mgr.ensure_builtin_guest() is True
    assert "guest" in mgr.users
    assert mgr.verify_password("Guest", "operator-guest-pw") is True
    assert mgr.verify_password("guest", "Guest123") is False
    assert mgr.is_admin("guest") is False


def test_enabled_guest_without_password_gets_a_random_one(tmp_path, monkeypatch):
    monkeypatch.setenv("MYAI_GUEST_ENABLED", "true")
    mgr = _make_manager(tmp_path)
    assert mgr.create_user("admin", "admin-password", is_admin=True) is True
    assert mgr.ensure_builtin_guest() is True
    stored = mgr.users["guest"]["password_hash"]
    assert stored.startswith("hash:") and stored != "hash:Guest123"
    assert len(stored) - len("hash:") >= 12


def test_short_operator_password_is_ignored(tmp_path, monkeypatch):
    monkeypatch.setenv("MYAI_GUEST_ENABLED", "true")
    monkeypatch.setenv("MYAI_GUEST_PASSWORD", "short")
    mgr = _make_manager(tmp_path)
    assert mgr.create_user("admin", "admin-password", is_admin=True) is True
    mgr.ensure_builtin_guest()
    assert mgr.verify_password("guest", "short") is False


def test_guest_is_repaired_to_canonical_privileges_non_admin(tmp_path, guest_on):
    from core.auth import BUILTIN_GUEST_PRIVILEGES

    mgr = _make_manager(tmp_path)
    assert mgr.create_user("admin", "admin-password", is_admin=True) is True
    mgr._config["users"]["guest"] = {
        "password_hash": "hash:operator-guest-pw",
        "created": 1,
        "is_admin": True,
        "builtin": True,
        "privileges": {"can_use_agent": True, "totally_bogus_privilege": True},
    }

    assert mgr.ensure_builtin_guest() is True
    assert mgr.is_admin("guest") is False
    privs = mgr.get_privileges("guest")
    for key, want in BUILTIN_GUEST_PRIVILEGES.items():
        assert privs.get(key) == want, f"privilege {key!r} not repaired to canonical"
    assert "totally_bogus_privilege" not in privs
    assert privs.get("can_use_bash") is False and privs.get("can_use_agent") is False


def test_guest_cannot_be_manually_created_deleted_renamed_promoted_or_privilege_edited(tmp_path, guest_on):
    mgr = _make_manager(tmp_path)
    assert mgr.create_user("admin", "admin-password", is_admin=True) is True
    assert mgr.ensure_builtin_guest() is True

    assert mgr.create_user("Guest", "some-password", is_admin=False) is False
    assert mgr.delete_user("guest", "admin") is False
    assert "guest" in mgr.users
    assert mgr.rename_user("guest", "visitor", "admin") is False
    assert mgr.rename_user("admin", "guest", "admin") is False
    assert mgr.set_privileges("guest", {"can_use_bash": True}) is False

    from core.auth import SetAdminResult
    assert mgr.set_admin("guest", True, "admin") == SetAdminResult.NOT_AUTHORIZED
    assert mgr.is_admin("guest") is False


def test_operator_password_change_is_applied(tmp_path, guest_on, monkeypatch):
    mgr = _make_manager(tmp_path)
    assert mgr.create_user("admin", "admin-password", is_admin=True) is True
    mgr._config["users"]["guest"] = {
        "password_hash": "not-a-valid-bcrypt-hash", "created": 1, "is_admin": False,
        "builtin": True, "privileges": {},
    }
    assert mgr.ensure_builtin_guest() is True
    assert mgr.verify_password("guest", "operator-guest-pw") is True

    monkeypatch.setenv("MYAI_GUEST_PASSWORD", "a-new-guest-password")
    assert mgr.ensure_builtin_guest() is True
    assert mgr.verify_password("guest", "a-new-guest-password") is True
    assert mgr.verify_password("guest", "operator-guest-pw") is False
