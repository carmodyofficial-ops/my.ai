"""Regression tests for bug-bash #1: a stuck-busy wearables session."""
import time

from services.wearables_gateway import sessions as S


def _fake_clock(monkeypatch, t):
    monkeypatch.setattr(S.time, "monotonic", lambda: t)


def test_second_claim_is_refused():
    s = S.WearableSession(id="t", owner="o")
    assert s.claim() is not None
    assert s.claim() is None
    assert s.is_busy()


def test_unstarted_claim_goes_stale(monkeypatch):
    s = S.WearableSession(id="t", owner="o")
    s.claim()
    _fake_clock(monkeypatch, s.busy_since + S.BUSY_UNSTARTED_GRACE_SECONDS + 1)
    assert not s.is_busy()
    assert s.claim() is not None


def test_started_stream_is_trusted_past_grace(monkeypatch):
    s = S.WearableSession(id="t", owner="o")
    s.mark_started(s.claim())
    _fake_clock(monkeypatch, s.busy_since + S.BUSY_UNSTARTED_GRACE_SECONDS + 1)
    assert s.is_busy()


def test_started_stream_expires_at_hard_ceiling(monkeypatch):
    s = S.WearableSession(id="t", owner="o")
    s.mark_started(s.claim())
    _fake_clock(monkeypatch, s.busy_since + S.BUSY_MAX_SECONDS + 1)
    assert not s.is_busy()


def test_superseded_release_does_not_clear_newer_claim(monkeypatch):
    s = S.WearableSession(id="t", owner="o")
    old = s.claim()
    _fake_clock(monkeypatch, s.busy_since + S.BUSY_UNSTARTED_GRACE_SECONDS + 1)
    new = s.claim()
    assert new is not None and new != old
    s.release(old)
    assert s.busy and s.busy_token == new
    s.release(new)
    assert not s.busy


def test_repeated_requests_no_longer_pin_a_stuck_session(monkeypatch):
    # The original bug: every rejected request touch()ed the session, so a
    # stuck one stayed alive AND busy forever.
    store = S.WearableSessionStore()
    s = store.get_or_create(None, "o")
    s.claim()
    _fake_clock(monkeypatch, time.monotonic() + S.BUSY_UNSTARTED_GRACE_SECONDS + 1)
    again = store.get_or_create(s.id, "o")
    assert again is s
    assert not again.is_busy()
    assert again.claim() is not None
