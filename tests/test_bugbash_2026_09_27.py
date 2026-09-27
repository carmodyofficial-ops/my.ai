"""Regression tests for fixes from the 2026-09-27 bug bash."""
import gzip
import http.server
import threading

import pytest

import services.search.content as content
from src.settings_scrub import is_secret_key, scrub_settings


# --- ntfy topic is a credential --------------------------------------------

def test_ntfy_topic_is_scrubbed_for_non_admins():
    assert is_secret_key("reminder_ntfy_topic")
    scrubbed = scrub_settings({"reminder_ntfy_topic": "my-private-topic", "keybinds": {"a": 1}})
    assert scrubbed["reminder_ntfy_topic"] != "my-private-topic"
    assert scrubbed["keybinds"] == {"a": 1}


# --- web_fetch: bounded decompression when identity is ignored --------------

def _serve(body: bytes, encoding: str):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Encoding", encoding)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_port}/"


def _fetch(url, cap):
    r = content._get_public_url(url, {}, 10, max_bytes=cap)
    return r.content, r.truncated


@pytest.fixture(autouse=True)
def _allow_loopback(monkeypatch):
    monkeypatch.setattr(content, "_public_http_url", lambda u: True)


def test_gzip_response_is_decoded_when_server_ignores_identity():
    page = b"<html><title>ok</title>" + b"x" * 5000 + b"</html>"
    srv, url = _serve(gzip.compress(page), "gzip")
    try:
        body, truncated = _fetch(url, 1_000_000)
    finally:
        srv.shutdown()
    assert body == page and truncated is False


def test_gzip_bomb_stops_at_cap():
    srv, url = _serve(gzip.compress(b"\0" * (64 << 20), 9), "gzip")  # 64 MiB decoded
    try:
        body, truncated = _fetch(url, 100_000)
    finally:
        srv.shutdown()
    assert len(body) == 100_000 and truncated is True


def test_unbounded_encodings_are_still_refused():
    srv, url = _serve(b"not really brotli", "br")
    try:
        with pytest.raises(Exception, match="Refusing compressed response"):
            _fetch(url, 100_000)
    finally:
        srv.shutdown()


# --- image-model chats: questions get a text answer -------------------------

@pytest.mark.parametrize("msg,expected", [
    ("What is the next role for a senior product manager?", True),
    ("how do I reset my router", True),
    ("Should I take the job", True),
    ("explain quantum tunneling", True),
    ("a red barn in a snowy field at dusk", False),
    ("draw a cat wearing a hat?", False),          # explicit picture word wins
    ("can you make a picture of a lighthouse", False),
    ("", False),
])
def test_wants_text_answer(msg, expected):
    from routes.chat_routes import _wants_text_answer
    assert _wants_text_answer(msg) is expected


def test_text_turn_session_overrides_only_model_fields():
    from types import SimpleNamespace
    from routes.chat_routes import _TextTurnSession
    inner = SimpleNamespace(id="s1", model="sdxl-lightning-8step", endpoint_url="http://img/v1", headers={}, name="x")
    view = _TextTurnSession(inner, "http://llm/v1/chat/completions", "qwen", {"a": "b"})
    assert (view.model, view.endpoint_url, view.headers, view.id) == ("qwen", "http://llm/v1/chat/completions", {"a": "b"}, "s1")
    view.name = "renamed"                     # non-model writes reach the real session
    assert inner.name == "renamed"
    assert inner.model == "sdxl-lightning-8step"  # the chat keeps its image model


# --- lan_proxy redirect mode ------------------------------------------------

import asyncio
import importlib.util
import pathlib
import socket

_spec = importlib.util.spec_from_file_location(
    "lan_proxy", pathlib.Path(__file__).resolve().parent.parent / "scripts" / "lan_proxy.py")
lan_proxy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lan_proxy)
BASE = "https://host.example.ts.net"


def _exchange(raw: bytes, read_timeout=5.0) -> bytes:
    async def run():
        srv = await asyncio.start_server(lambda r, w: lan_proxy._redirect(r, w, BASE), "127.0.0.1", 0,
                                         limit=lan_proxy._MAX_REQUEST_HEAD)
        port = srv.sockets[0].getsockname()[1]
        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", port)
            writer.write(raw)
            await writer.drain()
            data = await asyncio.wait_for(reader.read(), timeout=read_timeout)
            writer.close()
            return data
        finally:
            srv.close()
    return asyncio.run(run())


def test_redirect_get_keeps_path():
    out = _exchange(b"GET /chat?x=1 HTTP/1.1\r\nHost: h\r\n\r\n")
    assert out.startswith(b"HTTP/1.1 308") and b"Location: " + BASE.encode() + b"/chat?x=1\r\n" in out


def test_redirect_accepts_bare_lf_heads():
    out = _exchange(b"GET /x HTTP/1.1\nHost: h\n\n")
    assert out.startswith(b"HTTP/1.1 308")


def test_redirect_head_has_no_body():
    out = _exchange(b"HEAD /x HTTP/1.1\r\nHost: h\r\n\r\n")
    head, _, body = out.partition(b"\r\n\r\n")
    assert head.startswith(b"HTTP/1.1 308") and body == b""


def test_redirect_drains_large_post_body_before_replying():
    body = b"x" * 300_000
    out = _exchange(b"POST /login HTTP/1.1\r\nHost: h\r\nContent-Length: %d\r\n\r\n" % len(body) + body)
    assert out.startswith(b"HTTP/1.1 308")


def test_api_paths_get_403_not_redirect():
    out = _exchange(b"POST /api/chat HTTP/1.1\r\nHost: h\r\nContent-Length: 2\r\n\r\n{}")
    assert out.startswith(b"HTTP/1.1 403") and b"Location:" not in out and BASE.encode() in out


@pytest.mark.parametrize("value", ["host.ts.net", "http://host.ts.net", "/", "https://host/path", "https://u:p@host"])
def test_redirect_target_must_be_https_origin(value):
    with pytest.raises(SystemExit):
        lan_proxy._normalize_redirect_base(value)


def test_redirect_target_normalized():
    assert lan_proxy._normalize_redirect_base("https://host.ts.net/") == "https://host.ts.net"


# --- web_fetch decoding edge cases ------------------------------------------

import zlib


def test_raw_deflate_is_decoded():
    page = b"<html>raw deflate body</html>"
    comp = zlib.compressobj(wbits=-zlib.MAX_WBITS)
    srv, url = _serve(comp.compress(page) + comp.flush(), "deflate")
    try:
        body, truncated = _fetch(url, 1_000_000)
    finally:
        srv.shutdown()
    assert body == page and truncated is False


def test_multi_member_gzip_is_fully_decoded():
    srv, url = _serve(gzip.compress(b"part one, ") + gzip.compress(b"part two"), "gzip")
    try:
        body, truncated = _fetch(url, 1_000_000)
    finally:
        srv.shutdown()
    assert body == b"part one, part two" and truncated is False


def test_corrupt_gzip_is_a_clean_fetch_error():
    import httpx
    srv, url = _serve(b"\x1f\x8b\x08\x00this is not gzip data at all", "gzip")
    try:
        with pytest.raises(httpx.RequestError):
            _fetch(url, 1_000_000)
    finally:
        srv.shutdown()


# --- prompt cache: stable, smaller agent prompts ----------------------------

@pytest.mark.parametrize("text,expected", [
    ("What is the next role for a senior product manager?", False),  # 'manage' inside 'manager'
    ("my doctor said to rest", False),                                # 'doc' inside 'doctor'
    ("open my notebook", False),                                      # 'note' inside 'notebook'
    ("rename this chat", True),
    ("show my notes", True),
    ("add an api key for openrouter", True),
])
def test_admin_intent_matches_whole_words(text, expected):
    import src.agent_loop as al
    assert al._detect_admin_intent([{"role": "user", "content": text}]) is expected


def test_sticky_session_tools_carry_forward_and_reset():
    import src.agent_loop as al
    al._sticky_tools_by_session.clear()
    assert al._sticky_session_tools("s", {"a", "b"}) == {"a", "b"}
    assert al._sticky_session_tools("s", {"c"}) == {"a", "b", "c"}     # carried forward
    assert al._sticky_session_tools("other", {"z"}) == {"z"}           # per chat
    big = {f"t{i}" for i in range(al._STICKY_TOOLS_MAX + 1)}
    assert al._sticky_session_tools("s", big) == big                   # over the cap -> start over
    al._sticky_tools_by_session.clear()


def test_retrieve_min_score_drops_weak_matches():
    from types import SimpleNamespace
    from src.tool_index import ToolIndex
    lane = SimpleNamespace(
        name="fastembed", count=lambda: 3, encode=lambda q: [[0.0]],
        collection=SimpleNamespace(query=lambda **kw: {
            "metadatas": [[{"tool_name": "web_search"}, {"tool_name": "manage_skills"}, {"tool_name": "bash"}]],
            "distances": [[0.45, 0.72, 0.80]]}))            # scores 0.55, 0.28, 0.20
    ti = ToolIndex.__new__(ToolIndex)
    ti._lanes = [lane]
    assert ti.retrieve("q", k=8) == ["web_search", "manage_skills", "bash"]
    assert ti.retrieve("q", k=8, min_score=0.30) == ["web_search"]


def test_chat_stream_generator_does_not_shadow_sess():
    """stream_with_save rebinds `sess` (image chat answering a question). If that
    ever becomes a plain local again, every read before the assignment raises
    UnboundLocalError and EVERY chat fails — which shipped once."""
    import pathlib
    import symtable
    src = (pathlib.Path(__file__).resolve().parent.parent / "routes" / "chat_routes.py").read_text()

    def find(table, name):
        for ch in table.get_children():
            if ch.get_name() == name:
                return ch
            hit = find(ch, name)
            if hit:
                return hit

    gen = find(symtable.symtable(src, "chat_routes.py", "exec"), "stream_with_save")
    assert gen is not None
    assert not gen.lookup("sess").is_local(), "sess must be nonlocal/free in stream_with_save"
