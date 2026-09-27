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
