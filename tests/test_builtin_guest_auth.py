import importlib
import sys
import types
from pathlib import Path

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


def test_guest_not_seeded_before_admin_setup(tmp_path):
    mgr = _make_manager(tmp_path)
    assert mgr.is_configured is False
    assert "guest" not in mgr.users


def test_guest_seeded_after_admin_exists_and_login_works(tmp_path):
    mgr = _make_manager(tmp_path)
    assert mgr.create_user("admin", "admin-password", is_admin=True) is True

    changed = mgr.ensure_builtin_guest()
    assert changed is True
    assert "guest" in mgr.users
    assert mgr.verify_password("Guest", "Guest123") is True
    assert mgr.verify_password("guest", "wrong") is False
    assert mgr.is_admin("guest") is False


def test_guest_is_repaired_to_low_privilege_non_admin(tmp_path):
    mgr = _make_manager(tmp_path)
    assert mgr.create_user("admin", "admin-password", is_admin=True) is True
    mgr._config["users"]["guest"] = {
        "password_hash": "hash:bad",
        "created": 1,
        "is_admin": True,
        "privileges": {
            "can_use_agent": True,
            "can_use_bash": True,
            "can_manage_memory": True,
        },
    }

    assert mgr.ensure_builtin_guest() is True
    assert mgr.is_admin("guest") is False
    assert mgr.verify_password("guest", "Guest123") is True
    privs = mgr.get_privileges("guest")
    assert privs["can_use_agent"] is False
    assert privs["can_use_bash"] is False
    assert privs["can_manage_memory"] is False


def test_guest_cannot_be_manually_created_deleted_renamed_promoted_or_privilege_edited(tmp_path):
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


def test_guest_repairs_malformed_password_hash(tmp_path):
    mgr = _make_manager(tmp_path)
    assert mgr.create_user("admin", "admin-password", is_admin=True) is True
    mgr._config["users"]["guest"] = {
        "password_hash": "not-a-valid-bcrypt-hash",
        "created": 1,
        "is_admin": False,
        "privileges": {},
    }

    assert mgr.ensure_builtin_guest() is True
    assert mgr.verify_password("guest", "Guest123") is True
