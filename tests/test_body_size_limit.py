"""Unit tests for BodySizeLimitMiddleware — the ASGI guard that rejects an
oversized request body BEFORE Starlette parses/spools it (closing the chunked-
encoding bypass + multi-GB disk-exhaustion DoS that the per-route header checks
can't). Drives the middleware directly at the ASGI layer with a scripted
receive/send, so no app server is needed.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.middleware import BodySizeLimitMiddleware  # noqa: E402


def _make_inner():
    """A minimal ASGI app that reads the WHOLE body, then 200s. Records how many
    body bytes it actually read (0 means the middleware rejected before it ran)."""
    state = {"read": 0, "responded": False}

    async def inner(scope, receive, send):
        while True:
            m = await receive()
            state["read"] += len(m.get("body", b"") or b"")
            if not m.get("more_body"):
                break
        state["responded"] = True
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    return inner, state


async def _drive(app, scope, chunks):
    """Feed `chunks` through the app's receive; capture sent messages."""
    sent = []
    i = {"n": 0}

    async def receive():
        n = i["n"]
        i["n"] += 1
        if n < len(chunks):
            return {"type": "http.request", "body": chunks[n],
                    "more_body": n < len(chunks) - 1}
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    await app(scope, receive, send)
    return sent


def _status(sent):
    start = next(m for m in sent if m["type"] == "http.response.start")
    return start["status"]


def _scope(headers=None, path="/upload"):
    return {"type": "http", "method": "POST", "path": path,
            "headers": headers or []}


async def test_rejects_on_content_length_header():
    inner, state = _make_inner()
    app = BodySizeLimitMiddleware(inner, max_body_bytes=100)
    sent = await _drive(app, _scope([(b"content-length", b"1000")]), [b"x" * 10])
    assert _status(sent) == 413
    assert state["read"] == 0          # inner never saw the body
    assert state["responded"] is False


async def test_rejects_streaming_body_over_cap_without_content_length():
    # The real bypass: no Content-Length (chunked) — only a streaming count catches it.
    inner, state = _make_inner()
    app = BodySizeLimitMiddleware(inner, max_body_bytes=100)
    sent = await _drive(app, _scope([]), [b"x" * 60, b"x" * 60])   # 120 > 100
    assert _status(sent) == 413


async def test_passes_body_under_cap():
    inner, state = _make_inner()
    app = BodySizeLimitMiddleware(inner, max_body_bytes=100)
    sent = await _drive(app, _scope([(b"content-length", b"50")]), [b"x" * 50])
    assert _status(sent) == 200
    assert state["read"] == 50         # full body delivered to the route
    assert state["responded"] is True


async def test_exactly_at_cap_passes():
    inner, state = _make_inner()
    app = BodySizeLimitMiddleware(inner, max_body_bytes=100)
    sent = await _drive(app, _scope([(b"content-length", b"100")]), [b"x" * 100])
    assert _status(sent) == 200        # boundary is inclusive (reject only when > cap)
    assert state["read"] == 100


async def test_path_override_applies_tighter_cap():
    # A low-cap upload prefix is rejected below the global ceiling, so a chunked
    # body can't spool to the global 128 MB on a 10 MB route.
    inner, state = _make_inner()
    app = BodySizeLimitMiddleware(inner, max_body_bytes=1000,
                                  path_overrides={"/tight": 100})
    sent = await _drive(app, _scope([(b"content-length", b"500")], path="/tight/x"),
                        [b"z" * 500])
    assert _status(sent) == 413          # 500 > /tight cap of 100
    assert state["read"] == 0


async def test_path_override_does_not_affect_other_paths():
    inner, state = _make_inner()
    app = BodySizeLimitMiddleware(inner, max_body_bytes=1000,
                                  path_overrides={"/tight": 100})
    sent = await _drive(app, _scope([(b"content-length", b"500")], path="/other"),
                        [b"z" * 500])
    assert _status(sent) == 200          # 500 < the 1000 global ceiling
    assert state["read"] == 500


async def test_reject_echoes_origin_for_cross_origin_413():
    inner, _ = _make_inner()
    app = BodySizeLimitMiddleware(inner, max_body_bytes=100)
    sent = await _drive(
        app, _scope([(b"content-length", b"999"), (b"origin", b"https://my.ai")]),
        [b"x" * 5])
    start = next(m for m in sent if m["type"] == "http.response.start")
    assert start["status"] == 413
    hdrs = dict(start["headers"])
    assert hdrs.get(b"access-control-allow-origin") == b"https://my.ai"   # readable cross-origin


async def test_non_http_scope_passes_through_untouched():
    called = {"v": False}

    async def inner(scope, receive, send):
        called["v"] = True

    app = BodySizeLimitMiddleware(inner, max_body_bytes=100)
    await app({"type": "lifespan"}, None, None)
    assert called["v"] is True


# ── Integration: the full Starlette stack, with a BaseHTTPMiddleware (like the
#    real AuthMiddleware) sitting between the body limiter and the route. This is
#    the decisive check that _BodyTooLarge propagates cleanly to a 413 and isn't
#    swallowed/mangled by BaseHTTPMiddleware. ─────────────────────────────────

def _pass_through_auth():
    from starlette.middleware.base import BaseHTTPMiddleware

    class PassThroughAuth(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            return await call_next(request)   # reads headers, not the body — like auth

    return PassThroughAuth


def test_integration_multipart_content_length_reject():
    from fastapi import FastAPI, UploadFile, File
    from fastapi.testclient import TestClient

    app = FastAPI()

    @app.post("/up")
    async def up(f: UploadFile = File(...)):
        return {"n": len(await f.read())}

    app.add_middleware(_pass_through_auth())                              # inner
    app.add_middleware(BodySizeLimitMiddleware, max_body_bytes=1000)     # outermost
    client = TestClient(app)
    r = client.post("/up", files={"f": ("big.bin", b"x" * 5000,
                                        "application/octet-stream")})
    assert r.status_code == 413
    assert r.json()["detail"]["code"] == "PAYLOAD_TOO_LARGE"


def test_integration_chunked_streaming_reject_through_basehttp():
    # The bypass case: a chunked body (no Content-Length) must be caught by the
    # streaming count and surface as 413 THROUGH the BaseHTTPMiddleware layer.
    from fastapi import FastAPI, Request
    from fastapi.testclient import TestClient

    app = FastAPI()

    @app.post("/raw")
    async def raw(request: Request):
        return {"n": len(await request.body())}

    app.add_middleware(_pass_through_auth())
    app.add_middleware(BodySizeLimitMiddleware, max_body_bytes=1000)
    client = TestClient(app)

    def gen():
        for _ in range(5):
            yield b"x" * 400          # 2000 bytes total, sent chunked

    r = client.post("/raw", content=gen())
    assert r.status_code == 413
    assert r.json()["detail"]["code"] == "PAYLOAD_TOO_LARGE"


def test_integration_small_upload_passes():
    from fastapi import FastAPI, UploadFile, File
    from fastapi.testclient import TestClient

    app = FastAPI()

    @app.post("/up")
    async def up(f: UploadFile = File(...)):
        return {"n": len(await f.read())}

    app.add_middleware(_pass_through_auth())
    app.add_middleware(BodySizeLimitMiddleware, max_body_bytes=1_000_000)
    client = TestClient(app)
    r = client.post("/up", files={"f": ("s.bin", b"y" * 500,
                                        "application/octet-stream")})
    assert r.status_code == 200
    assert r.json()["n"] == 500
