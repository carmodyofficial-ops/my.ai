"""Phase 3 auth hardening: per-account login lockout + invite-token signup."""

import asyncio
import importlib
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, Response

from tests.helpers.import_state import clear_module
from src.rate_limiter import AccountLockout


# ── helpers (mirror tests/test_auth_policy.py) ────────────────────────────
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


def _endpoint(auth_manager, path, model_name):
    sys.modules.pop("routes.auth_routes", None)
    _real_core_package()
    import routes.auth_routes as ar
    router = ar.setup_auth_routes(auth_manager)
    for route in router.routes:
        if getattr(route, "path", None) == path:
            return route.endpoint, getattr(ar, model_name)
    raise AssertionError(f"route not found: {path}")


# ── AccountLockout ────────────────────────────────────────────────────────
def test_lockout_triggers_after_threshold_and_clears_on_success():
    lock = AccountLockout(max_failures=3, lockout_seconds=900, window_seconds=900)
    assert lock.locked_for("alice") == 0
    assert lock.record_failure("alice") == 0
    assert lock.record_failure("alice") == 0
    assert lock.record_failure("alice") > 0          # 3rd failure -> lock
    assert lock.locked_for("alice") > 0
    lock.record_success("alice")                     # success clears
    assert lock.locked_for("alice") == 0


def test_lockout_is_per_account():
    lock = AccountLockout(max_failures=2, lockout_seconds=900)
    lock.record_failure("alice")
    lock.record_failure("alice")
    assert lock.locked_for("alice") > 0
    assert lock.locked_for("bob") == 0


# ── Invite tokens (AuthManager) ───────────────────────────────────────────
def test_invite_lifecycle(tmp_path):
    mgr = _make_manager(tmp_path)
    mgr.create_user("admin", "admin-password", is_admin=True)
    token = mgr.create_invite(created_by="admin", ttl_hours=168)
    assert token and mgr.validate_invite(token)
    assert any(i["token"] == token and i["status"] == "active" for i in mgr.list_invites())
    assert mgr.consume_invite(token, "newuser") is True
    assert mgr.validate_invite(token) is False        # single-use
    assert mgr.consume_invite(token, "other") is False
    assert any(i["token"] == token and i["status"] == "used" for i in mgr.list_invites())


def test_invite_expiry_and_revoke(tmp_path):
    mgr = _make_manager(tmp_path)
    assert mgr.validate_invite(mgr.create_invite("admin", ttl_hours=-1)) is False  # expired
    tok = mgr.create_invite("admin", ttl_hours=168)
    assert mgr.revoke_invite(tok) is True
    assert mgr.validate_invite(tok) is False
    used = mgr.create_invite("admin")
    mgr.consume_invite(used, "u")
    assert mgr.revoke_invite(used) is False            # can't revoke a used invite


# ── Signup via invite (endpoint) ──────────────────────────────────────────
def test_signup_with_valid_invite_succeeds_when_open_signup_off(tmp_path, monkeypatch):
    monkeypatch.delenv("ODYSSEUS_OPEN_SIGNUP", raising=False)
    mgr = _make_manager(tmp_path)
    mgr.create_user("admin", "admin-password", is_admin=True)
    token = mgr.create_invite("admin")
    signup, SignupRequest = _endpoint(mgr, "/api/auth/signup", "SignupRequest")
    request = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))

    result = asyncio.run(signup(
        body=SignupRequest(username="invitee", password="a-valid-password", invite_token=token),
        request=request,
    ))
    assert result["ok"] is True and "invitee" in mgr.users

    with pytest.raises(HTTPException) as exc:   # token now used -> reuse rejected
        asyncio.run(signup(
            body=SignupRequest(username="invitee2", password="a-valid-password", invite_token=token),
            request=request,
        ))
    assert exc.value.status_code == 403


def test_signup_without_invite_rejected_when_open_signup_off(tmp_path, monkeypatch):
    monkeypatch.delenv("ODYSSEUS_OPEN_SIGNUP", raising=False)
    mgr = _make_manager(tmp_path)
    mgr.create_user("admin", "admin-password", is_admin=True)
    signup, SignupRequest = _endpoint(mgr, "/api/auth/signup", "SignupRequest")
    request = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(signup(
            body=SignupRequest(username="nope", password="a-valid-password"),
            request=request,
        ))
    assert exc.value.status_code == 403


# ── Login lockout (endpoint) ──────────────────────────────────────────────
def test_login_locks_account_then_refuses_even_correct_password(tmp_path):
    mgr = _make_manager(tmp_path)
    mgr.create_user("alice", "correct-password")
    login, LoginRequest = _endpoint(mgr, "/api/auth/login", "LoginRequest")
    request = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))

    for _ in range(8):  # default max_failures=8
        with pytest.raises(HTTPException) as exc:
            asyncio.run(login(
                body=LoginRequest(username="alice", password="wrong"),
                request=request, response=Response(),
            ))
        assert exc.value.status_code == 401

    with pytest.raises(HTTPException) as exc:  # now locked: correct pw still refused
        asyncio.run(login(
            body=LoginRequest(username="alice", password="correct-password"),
            request=request, response=Response(),
        ))
    assert exc.value.status_code == 429
