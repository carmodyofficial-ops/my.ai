"""Wearables gateway: transient session store + spoken-text transform.

Sessions: owner-scoped, in-memory only, idle-pruned, cancellable — privacy by
default (nothing persists). Spoken transform: markdown/URLs/code never read
aloud, bounded length with sentence truncation and a "tell me more" offer.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.wearables_gateway import sessions as S  # noqa: E402
from services.wearables_gateway.spoken import spoken_text  # noqa: E402


# --- sessions: owner scoping ------------------------------------------------

def test_session_ids_do_not_cross_owners():
    store = S.WearableSessionStore()
    a = store.get_or_create("shared-id", "alice")
    assert a.id == "shared-id"
    # Bob asking for alice's session id must get a DIFFERENT fresh session.
    b = store.get_or_create("shared-id", "bob")
    assert b.id != "shared-id"
    assert b.owner == "bob"
    # And direct lookup is owner-checked.
    assert store.get("shared-id", "bob") is None
    assert store.get("shared-id", "alice") is a


def test_get_or_create_rejects_hostile_session_ids():
    store = S.WearableSessionStore()
    s = store.get_or_create("../../etc/passwd", "alice")
    assert s.id != "../../etc/passwd"
    s2 = store.get_or_create("a" * 65, "alice")
    assert s2.id != "a" * 65


def test_delete_and_cancel_are_owner_scoped():
    store = S.WearableSessionStore()
    s = store.get_or_create(None, "alice")
    assert store.delete(s.id, "bob") is False
    assert store.cancel(s.id, "bob") is False
    assert store.delete(s.id, "alice") is True
    assert store.get(s.id, "alice") is None


def test_cancel_sets_the_event():
    import asyncio

    store = S.WearableSessionStore()
    s = store.get_or_create(None, "alice")
    assert store.cancel(s.id, "alice") is False  # nothing streaming yet
    ev = asyncio.Event()
    s.cancel_event = ev
    assert store.cancel(s.id, "alice") is True
    assert ev.is_set()


def test_delete_cancels_active_stream():
    import asyncio

    store = S.WearableSessionStore()
    s = store.get_or_create(None, "alice")
    ev = asyncio.Event()
    s.cancel_event = ev
    assert store.delete(s.id, "alice") is True
    assert ev.is_set()


# --- sessions: transcript policy & bounds ------------------------------------

def test_rolling_context_is_trimmed():
    s = S.WearableSession(id="x", owner="alice")
    for i in range(20):
        s.append_turn(f"q{i}", f"a{i}")
    assert len(s.messages) == S.MAX_TURNS_KEPT
    assert s.messages[-1]["content"] == "a19"
    assert s.messages[0]["content"].startswith(("q", "a"))


def test_no_storage_privacy_mode():
    s = S.WearableSession(id="x", owner="alice", store_transcript=False)
    s.append_turn("secret question", "secret answer")
    assert s.messages == []


def test_idle_sessions_are_pruned():
    store = S.WearableSessionStore(idle_ttl=0)
    s = store.get_or_create(None, "alice")
    s.last_active = time.monotonic() - 1
    assert store.count() == 0


def test_busy_sessions_survive_prune():
    store = S.WearableSessionStore(idle_ttl=0)
    s = store.get_or_create(None, "alice")
    s.busy = True
    s.last_active = time.monotonic() - 1
    assert store.count() == 1


def test_per_owner_session_cap():
    store = S.WearableSessionStore()
    for _ in range(S.MAX_SESSIONS_PER_OWNER + 5):
        store.get_or_create(None, "alice")
    assert store.count() <= S.MAX_SESSIONS_PER_OWNER + 1


# --- spoken transform ---------------------------------------------------------

def test_spoken_strips_markdown():
    md = ("# Title\n\n**Bold** and *italic* and `inline code`.\n"
          "- bullet one\n- bullet two\n\n> a quote\n\n---\n")
    out = spoken_text(md)
    s = out["spoken"]
    for marker in ("#", "**", "`", "- ", ">", "---"):
        assert marker not in s
    assert "Bold" in s and "italic" in s and "inline code" in s
    assert "bullet one" in s


def test_spoken_never_reads_code_blocks():
    md = "Here you go:\n```python\nimport os\nos.system('rm -rf /')\n```\nDone."
    out = spoken_text(md)
    assert "import os" not in out["spoken"]
    assert "rm -rf" not in out["spoken"]
    assert "phone" in out["spoken"].lower()  # points user at the phone screen


def test_spoken_never_reads_urls():
    md = "See [the docs](https://example.com/x?y=1) or https://raw.example.com/z."
    out = spoken_text(md)
    assert "http" not in out["spoken"]
    assert "example.com" not in out["spoken"]
    assert "the docs" in out["spoken"]


def test_spoken_truncates_at_sentence_boundary():
    long = " ".join(f"Sentence number {i} is here." for i in range(200))
    out = spoken_text(long, max_chars=300)
    assert out["truncated"] is True
    assert len(out["spoken"]) < 400
    assert "Want to hear more?" in out["spoken"]
    # Cut lands after a sentence end, not mid-word.
    body = out["spoken"].replace(" Want to hear more?", "")
    assert body.rstrip().endswith(".")


def test_spoken_short_text_untouched():
    out = spoken_text("It is 72 degrees and sunny.")
    assert out == {"spoken": "It is 72 degrees and sunny.", "truncated": False}


def test_spoken_tables_become_a_notice():
    md = "| a | b |\n|---|---|\n| 1 | 2 |\nSummary line."
    out = spoken_text(md)
    assert "|" not in out["spoken"]
    assert "Summary line." in out["spoken"]
    assert "table" in out["spoken"].lower()


def test_spoken_empty_input():
    assert spoken_text("")["spoken"] == ""
    assert spoken_text(None)["spoken"] == ""
