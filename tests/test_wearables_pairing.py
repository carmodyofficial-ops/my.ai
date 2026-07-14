"""Wearables gateway enrollment: one-time pairing codes + device credentials.

Contract under test (services/wearables_gateway/pairing.py):
  - pairing codes are single-use, short-TTL, and stored only as sha256
  - the device credential is a standard ApiToken row: bcrypt hash + 8-char
    prefix at rest, raw token returned exactly once, scope "wearables"
  - minting invalidates the auth middleware token cache (works w/o restart)
  - revocation flips is_active and only touches wearables-scoped rows
"""

import contextlib
import os
import sys
import types
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_CAPTURED = {}


class _ApiToken:
    # Class-level column stand-ins so filter expressions like
    # `ApiToken.id == x` evaluate against the stub.
    id = owner = name = scopes = is_active = None

    def __init__(self, **kw):
        _CAPTURED.clear()
        _CAPTURED.update(kw)
        self.__dict__.update(kw)


@contextlib.contextmanager
def _get_db_session():
    yield MagicMock()


class _DBStub(types.ModuleType):
    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return MagicMock()


_db = _DBStub("core.database")
_db.get_db_session = _get_db_session
_db.ApiToken = _ApiToken


@pytest.fixture(autouse=True)
def _db_stub(monkeypatch):
    monkeypatch.setitem(sys.modules, "core.database", _db)
    parent = sys.modules.get("core")
    if parent is not None:
        monkeypatch.setattr(parent, "database", _db, raising=False)


from services.wearables_gateway import pairing as P  # noqa: E402


# --- pairing codes ----------------------------------------------------------

def test_pairing_code_single_use():
    store = P.PairingStore(ttl_seconds=60)
    code = store.mint("alice")
    assert code.startswith("wpair_")
    assert store.consume(code) == "alice"
    # Second redemption of the same code must fail (replay resistance).
    assert store.consume(code) is None


def test_pairing_code_expires(monkeypatch):
    store = P.PairingStore(ttl_seconds=60)
    code = store.mint("alice")
    real_monotonic = __import__("time").monotonic
    monkeypatch.setattr("services.wearables_gateway.pairing.time.monotonic",
                        lambda: real_monotonic() + 61)
    assert store.consume(code) is None


def test_pairing_code_stored_hashed_only():
    store = P.PairingStore()
    code = store.mint("alice")
    # The raw code must not appear anywhere in the store's internal state.
    assert code not in repr(store.__dict__)
    assert all(code != k for k in store._codes)


def test_pairing_rejects_garbage_and_wrong_prefix():
    store = P.PairingStore()
    store.mint("alice")
    assert store.consume("") is None
    assert store.consume(None) is None
    assert store.consume("ody_notapairingcode") is None
    assert store.consume("wpair_wrongcode") is None


def test_pending_codes_are_capped():
    store = P.PairingStore()
    codes = [store.mint("alice") for _ in range(P._MAX_PENDING_CODES + 5)]
    assert store.pending_count() == P._MAX_PENDING_CODES
    # The newest code always survives the cap eviction.
    assert store.consume(codes[-1]) == "alice"


def test_codes_do_not_cross_owners():
    store = P.PairingStore()
    code_a = store.mint("alice")
    code_b = store.mint("bob")
    assert store.consume(code_b) == "bob"
    assert store.consume(code_a) == "alice"


# --- device credential minting ---------------------------------------------

def test_mint_device_token_hashed_at_rest_and_scoped():
    token_id, raw = P.mint_device_token("alice", "Pixel 9")
    assert raw.startswith("ody_")
    assert _CAPTURED["token_hash"] != raw
    assert _CAPTURED["token_hash"].startswith("$2")  # bcrypt
    assert _CAPTURED["token_prefix"] == raw[:8]
    assert _CAPTURED["owner"] == "alice"
    assert _CAPTURED["scopes"] == "wearables"
    assert _CAPTURED["name"] == "wearable:Pixel 9"
    assert _CAPTURED["is_active"] is True
    assert _CAPTURED["id"] == token_id


def test_mint_device_token_invalidates_cache():
    invalidate = MagicMock()
    P.mint_device_token("alice", "glasses", invalidate=invalidate)
    invalidate.assert_called_once()


def test_mint_device_token_tolerates_no_invalidator():
    token_id, raw = P.mint_device_token("alice", "glasses", invalidate=None)
    assert raw.startswith("ody_")


def test_sanitize_device_name():
    assert P.sanitize_device_name(None) == "glasses-companion"
    assert P.sanitize_device_name("  ") == "glasses-companion"
    assert P.sanitize_device_name("<script>x</script>") == "scriptx/script"
    assert len(P.sanitize_device_name("a" * 500)) == 60
    assert P.sanitize_device_name("Pixel\n9\x00") == "Pixel9"


# --- listing / revocation ---------------------------------------------------

class _Row:
    def __init__(self, id, owner, name, scopes, is_active=True):
        self.id, self.owner, self.name = id, owner, name
        self.scopes, self.is_active = scopes, is_active
        self.created_at, self.last_used_at = None, None


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, *a):
        return self

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None


def _fake_db(rows):
    db = MagicMock()
    db.query.return_value = _FakeQuery(rows)
    return db


def test_list_devices_filters_to_wearables_scope(monkeypatch):
    rows = [
        _Row("w1", "alice", "wearable:Pixel", "wearables"),
        _Row("c1", "alice", "companion", "chat"),
        _Row("w2", "bob", "wearable:iPhone", "wearables", is_active=False),
    ]

    @contextlib.contextmanager
    def _sess():
        yield _fake_db(rows)

    monkeypatch.setattr(_db, "get_db_session", _sess, raising=False)
    devices = P.list_devices()
    assert {d["token_id"] for d in devices} == {"w1", "w2"}
    revoked = next(d for d in devices if d["token_id"] == "w2")
    assert revoked["active"] is False
    # No secret material in the listing.
    for d in devices:
        assert "token_hash" not in d and "token" not in d


def test_revoke_device_deactivates_only_wearables_rows(monkeypatch):
    wearable = _Row("w1", "alice", "wearable:Pixel", "wearables")
    chat_tok = _Row("c1", "alice", "companion", "chat")

    def _make_sess(row):
        @contextlib.contextmanager
        def _sess():
            yield _fake_db([row] if row else [])
        return _sess

    invalidate = MagicMock()
    monkeypatch.setattr(_db, "get_db_session", _make_sess(wearable), raising=False)
    assert P.revoke_device("w1", invalidate=invalidate) is True
    assert wearable.is_active is False
    invalidate.assert_called_once()

    # A non-wearables token must not be revocable through this surface.
    monkeypatch.setattr(_db, "get_db_session", _make_sess(chat_tok), raising=False)
    assert P.revoke_device("c1") is False
    assert chat_tok.is_active is True

    monkeypatch.setattr(_db, "get_db_session", _make_sess(None), raising=False)
    assert P.revoke_device("missing") is False
