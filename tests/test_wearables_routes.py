"""Wearables gateway routes — auth/scope gates, enrollment exchange, streaming
conversation (meta → deltas → spoken → done), cancellation, media endpoints,
capability discovery, rate limiting, and log redaction.

Endpoints are exercised directly (companion-tests style): the global
AuthMiddleware is out of frame, so these tests assert the ROUTE-LAYER
contracts — the wearables scope gate, the pairing-code exchange, and
owner-scoped session behavior.
"""

import asyncio
import contextlib
import json
import os
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException  # noqa: E402

import routes.wearables_routes as W  # noqa: E402
from services.wearables_gateway import pairing as P  # noqa: E402
from services.wearables_gateway.sessions import WearableSessionStore  # noqa: E402
from src.rate_limiter import RateLimiter  # noqa: E402

# The model the respond path pins glasses chat to (fast "simple" tier).
SPOKEN_FAST_MODEL = "gpt-oss:20b"


# --- helpers -----------------------------------------------------------------

def _req(*, user=None, api_token=False, token_owner=None, scopes=None,
         body=None, is_admin=False, ip="10.0.0.5", port=7001):
    r = SimpleNamespace(
        state=SimpleNamespace(
            current_user=user,
            api_token=api_token,
            api_token_owner=token_owner,
            api_token_scopes=scopes,
        ),
        headers={},
        client=SimpleNamespace(host=ip),
        url=SimpleNamespace(port=port),
        query_params={},
        app=SimpleNamespace(state=SimpleNamespace(
            auth_manager=SimpleNamespace(
                is_admin=lambda u: is_admin, is_configured=True),
            invalidate_token_cache=MagicMock(),
        )),
    )

    # Encode the body the way a real client would, so _read_json_object's
    # streaming + Content-Length path is exercised (not a mocked .json()).
    raw = b"" if body is None else json.dumps(body).encode()
    r.headers = {"content-length": str(len(raw))} if body is not None else {}

    async def _json():
        if body is None:
            raise ValueError("no body")
        return body

    async def _stream():
        yield raw

    async def _body():
        return raw

    r.json = _json
    r.stream = _stream
    r.body = _body
    return r


def _device_req(owner="alice", **kw):
    """A request authenticated as a paired wearable (bearer, wearables scope)."""
    return _req(user="api", api_token=True, token_owner=owner,
                scopes="wearables", **kw)


def _endpoints():
    router = W.setup_wearables_routes(_STT(), _TTS())
    table = {}
    for r in router.routes:
        for m in getattr(r, "methods", set()) or set():
            table[(m, r.path.replace("/api/wearables/v1", ""))] = r.endpoint
    return table


class _STT:
    def __init__(self, available=True, result="hello glasses"):
        self.available = available
        self._result = result

    def transcribe(self, audio_bytes):
        return self._result


class _TTS:
    def __init__(self, available=True, audio=b"ID3fakeaudio"):
        self.available = available
        self._audio = audio

    def synthesize(self, text, use_cache=True):
        # The gateway passes use_cache=False so spoken answers aren't persisted
        # to the on-disk TTS cache (privacy: audio is transient).
        self.last_use_cache = use_cache
        return self._audio


class _Upload:
    def __init__(self, data=b"x" * 100, content_type="audio/wav"):
        self._data = data
        self.content_type = content_type

    async def read(self, n=-1):
        return self._data if n < 0 else self._data[:n]


async def _collect_sse(resp):
    frames = []
    async for chunk in resp.body_iterator:
        if isinstance(chunk, bytes):
            chunk = chunk.decode()
        frames.append(chunk)
    return frames


def _events(frames):
    out = []
    for f in frames:
        for line in f.splitlines():
            if line.startswith("data: ") and line[6:].strip() != "[DONE]":
                try:
                    out.append(json.loads(line[6:]))
                except ValueError:
                    pass
    return out


@pytest.fixture(autouse=True)
def _fresh_state(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setattr(W, "PAIRING_STORE", P.PairingStore())
    monkeypatch.setattr(W, "SESSION_STORE", WearableSessionStore())
    monkeypatch.setattr(W, "_pair_limiter", RateLimiter(1000, 60))
    monkeypatch.setattr(W, "_respond_limiter", RateLimiter(1000, 60))
    monkeypatch.setattr(W, "_media_limiter", RateLimiter(1000, 60))


def _stub_llm(monkeypatch, deltas=("Hello ", "world."), hang_event=None):
    """Point the respond path at a fake agent loop + endpoint."""
    import src.endpoint_resolver as ep
    import src.model_router as mr
    import src.agent_loop as al
    import src.settings as _settings

    monkeypatch.setattr(ep, "resolve_endpoint",
                        lambda prefix, owner=None: ("http://fake:11434/v1", "fake-model", {}))

    async def _same_model(text, **kw):
        return kw.get("current_model", "fake-model")

    monkeypatch.setattr(mr, "select_model_for_turn", _same_model)

    # The endpoint above is local (:11434), so the respond path pins the model
    # to the configured "simple" tier for snappy spoken replies. Fix that setting
    # so the test asserts the deterministic pinned model rather than pass-through.
    monkeypatch.setattr(_settings, "get_setting",
                        lambda key, default=None:
                            SPOKEN_FAST_MODEL if key == "auto_model_simple" else default)

    async def _fake_loop(*a, **kw):
        for d in deltas:
            yield "data: " + json.dumps({"delta": d}) + "\n\n"
        if hang_event is not None:
            await hang_event.wait()
        yield "data: [DONE]\n\n"

    monkeypatch.setattr(al, "stream_agent_loop", _fake_loop)


# --- scope gate ---------------------------------------------------------------

def test_bearer_without_wearables_scope_rejected():
    with pytest.raises(HTTPException) as exc:
        W.require_wearables(_req(user="api", api_token=True,
                                 token_owner="alice", scopes="chat"))
    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "FORBIDDEN_SCOPE"


def test_bearer_with_wearables_scope_resolves_real_owner():
    assert W.require_wearables(_device_req("alice")) == "alice"


def test_unauthenticated_request_rejected():
    with pytest.raises(HTTPException) as exc:
        W.require_wearables(_req())
    assert exc.value.status_code == 401
    assert exc.value.detail["code"] == "AUTHENTICATION_REQUIRED"


def test_cookie_session_passes():
    assert W.require_wearables(_req(user="carmody")) == "carmody"


async def test_health_reports_auth_kind():
    ep = _endpoints()[("GET", "/health")]
    out = await ep(_device_req("alice"))
    assert out["ok"] is True and out["auth"] == "token" and out["owner"] == "alice"


# --- enrollment ----------------------------------------------------------------

async def test_pairing_mint_requires_admin():
    ep = _endpoints()[("POST", "/pairings")]
    with pytest.raises(HTTPException) as exc:
        await ep(_req(user="bob", is_admin=False))
    assert exc.value.status_code == 403


async def test_pair_exchange_happy_path(monkeypatch):
    minted = {}

    def _fake_mint(owner, device_name=None, invalidate=None):
        minted.update(owner=owner, device_name=device_name)
        if callable(invalidate):
            invalidate()
        return "tok12345", "ody_rawsecret"

    monkeypatch.setattr(P, "mint_device_token", _fake_mint)
    code = W.PAIRING_STORE.mint("carmody")
    ep = _endpoints()[("POST", "/pair")]
    req = _req(body={"code": code, "device_name": "Pixel 9"})
    out = await ep(req)
    assert out["token"] == "ody_rawsecret"
    assert out["owner"] == "carmody"
    assert out["scope"] == "wearables"
    assert minted == {"owner": "carmody", "device_name": "Pixel 9"}
    req.app.state.invalidate_token_cache.assert_called_once()
    # The code is single-use: replaying the exchange fails.
    with pytest.raises(HTTPException) as exc:
        await ep(_req(body={"code": code}))
    assert exc.value.status_code == 401
    assert exc.value.detail["code"] == "PAIRING_CODE_INVALID"


async def test_pair_rejects_bad_code():
    ep = _endpoints()[("POST", "/pair")]
    with pytest.raises(HTTPException) as exc:
        await ep(_req(body={"code": "wpair_bogus"}))
    assert exc.value.detail["code"] == "PAIRING_CODE_INVALID"


async def test_pair_is_rate_limited(monkeypatch):
    monkeypatch.setattr(W, "_pair_limiter", RateLimiter(2, 60))
    ep = _endpoints()[("POST", "/pair")]
    for _ in range(2):
        with pytest.raises(HTTPException) as exc:
            await ep(_req(body={"code": "wpair_x"}, ip="9.9.9.9"))
        assert exc.value.status_code == 401
    with pytest.raises(HTTPException) as exc:
        await ep(_req(body={"code": "wpair_x"}, ip="9.9.9.9"))
    assert exc.value.status_code == 429
    assert exc.value.detail["code"] == "RATE_LIMITED"


async def test_pairing_payload_advertises_tls_endpoint(monkeypatch):
    """Operators front the app with the TLS lan_proxy; the QR payload must
    dial that (host/port/tls from env), not the in-container address."""
    monkeypatch.setenv("MYAI_WEARABLES_ADVERTISE_HOST", "192.168.1.50")
    monkeypatch.setenv("MYAI_WEARABLES_ADVERTISE_PORT", "7443")
    monkeypatch.setenv("MYAI_WEARABLES_ADVERTISE_TLS", "true")
    ep = _endpoints()[("POST", "/pairings")]
    out = await ep(_req(user="carmody", is_admin=True))
    assert out["payload"]["host"] == "192.168.1.50"
    assert out["payload"]["port"] == 7443
    assert out["payload"]["tls"] is True
    assert out["payload"]["code"].startswith("wpair_")


async def test_devices_list_and_revoke_require_admin(monkeypatch):
    eps = _endpoints()
    for key, kwargs in ((("GET", "/devices"), {}),
                        (("DELETE", "/devices/{token_id}"), {"token_id": "x"})):
        with pytest.raises(HTTPException) as exc:
            await eps[key](_req(user="bob", is_admin=False), **kwargs)
        assert exc.value.status_code == 403


async def test_revoke_unknown_device_404(monkeypatch):
    monkeypatch.setattr(P, "revoke_device", lambda tid, invalidate=None: False)
    ep = _endpoints()[("DELETE", "/devices/{token_id}")]
    with pytest.raises(HTTPException) as exc:
        await ep(_req(user="carmody", is_admin=True), token_id="nope")
    assert exc.value.status_code == 404


# --- conversation streaming -----------------------------------------------------

async def test_respond_streams_meta_deltas_spoken_done(monkeypatch):
    _stub_llm(monkeypatch, deltas=("The answer ", "is 42."))
    ep = _endpoints()[("POST", "/respond")]
    resp = await ep(_device_req("alice", body={"text": "what is the answer?"}))
    frames = await _collect_sse(resp)
    events = _events(frames)

    assert events[0]["type"] == "wearables_meta"
    assert events[0]["model"] == SPOKEN_FAST_MODEL
    sid = events[0]["session_id"]
    deltas = [e["delta"] for e in events if "delta" in e]
    assert "".join(deltas) == "The answer is 42."
    spoken = next(e for e in events if e.get("type") == "spoken")
    assert spoken["text"] == "The answer is 42."
    assert events[-1]["type"] == "done"
    assert frames[-1] == "data: [DONE]\n\n"
    # Exactly one terminal frame (the upstream [DONE] was swallowed).
    assert sum(1 for f in frames if "[DONE]" in f) == 1
    # Follow-up context was recorded in the transient session.
    sess = W.SESSION_STORE.get(sid, "alice")
    assert sess.messages[-1]["content"] == "The answer is 42."


async def test_respond_excludes_thinking_from_spoken(monkeypatch):
    """Chain-of-thought deltas ("thinking": true) must never be spoken or
    stored as the assistant's answer (found live against gpt-oss:20b)."""
    _stub_llm(monkeypatch)
    import src.agent_loop as al

    async def _cot_loop(*a, **kw):
        yield "data: " + json.dumps({"delta": "secret reasoning. ", "thinking": True}) + "\n\n"
        yield "data: " + json.dumps({"delta": "Final answer."}) + "\n\n"

    monkeypatch.setattr(al, "stream_agent_loop", _cot_loop)
    ep = _endpoints()[("POST", "/respond")]
    frames = await _collect_sse(await ep(_device_req("alice", body={"text": "q"})))
    events = _events(frames)
    spoken = next(e for e in events if e.get("type") == "spoken")
    assert spoken["text"] == "Final answer."
    assert "secret reasoning" not in spoken["text"]
    sid = events[0]["session_id"]
    sess = W.SESSION_STORE.get(sid, "alice")
    assert sess.messages[-1]["content"] == "Final answer."


async def test_respond_followup_carries_context(monkeypatch):
    captured = {}
    _stub_llm(monkeypatch)
    import src.agent_loop as al

    async def _capture_loop(url, model, messages, **kw):
        captured["messages"] = messages
        yield "data: " + json.dumps({"delta": "ok"}) + "\n\n"

    monkeypatch.setattr(al, "stream_agent_loop", _capture_loop)
    ep = _endpoints()[("POST", "/respond")]
    r1 = await ep(_device_req("alice", body={"text": "first question"}))
    sid = _events(await _collect_sse(r1))[0]["session_id"]
    r2 = await ep(_device_req("alice", body={"text": "and then?", "session_id": sid}))
    await _collect_sse(r2)
    contents = [m["content"] for m in captured["messages"]]
    assert "first question" in contents  # history threaded into turn 2
    assert contents[-1] == "and then?"
    assert captured["messages"][0]["role"] == "system"


async def test_respond_validation():
    ep = _endpoints()[("POST", "/respond")]
    with pytest.raises(HTTPException) as exc:
        await ep(_device_req("alice", body={"text": "   "}))
    assert exc.value.detail["code"] == "BAD_REQUEST"
    with pytest.raises(HTTPException) as exc:
        await ep(_device_req("alice", body={"text": "x" * (W.MAX_TEXT_CHARS + 1)}))
    assert exc.value.status_code == 413
    with pytest.raises(HTTPException) as exc:
        await ep(_device_req("alice"))  # no JSON body at all
    assert exc.value.detail["code"] == "BAD_REQUEST"


async def test_respond_no_endpoint_is_llm_unavailable(monkeypatch):
    import src.endpoint_resolver as epr
    monkeypatch.setattr(epr, "resolve_endpoint",
                        lambda prefix, owner=None: (None, None, None))
    ep = _endpoints()[("POST", "/respond")]
    with pytest.raises(HTTPException) as exc:
        await ep(_device_req("alice", body={"text": "hi"}))
    assert exc.value.status_code == 503
    assert exc.value.detail["code"] == "LLM_UNAVAILABLE"


async def test_respond_rate_limited(monkeypatch):
    monkeypatch.setattr(W, "_respond_limiter", RateLimiter(1, 60))
    _stub_llm(monkeypatch)
    ep = _endpoints()[("POST", "/respond")]
    await _collect_sse(await ep(_device_req("alice", body={"text": "one"})))
    with pytest.raises(HTTPException) as exc:
        await ep(_device_req("alice", body={"text": "two"}))
    assert exc.value.status_code == 429


async def test_respond_error_becomes_sse_error_event(monkeypatch):
    _stub_llm(monkeypatch)
    import src.agent_loop as al

    async def _boom(*a, **kw):
        yield "data: " + json.dumps({"delta": "part"}) + "\n\n"
        raise RuntimeError("upstream exploded")

    monkeypatch.setattr(al, "stream_agent_loop", _boom)
    ep = _endpoints()[("POST", "/respond")]
    frames = await _collect_sse(await ep(_device_req("alice", body={"text": "hi"})))
    assert any(f.startswith("event: error") for f in frames)
    assert frames[-1] == "data: [DONE]\n\n"  # stream still terminates cleanly


async def test_cancellation_mid_stream(monkeypatch):
    hang = asyncio.Event()
    _stub_llm(monkeypatch, deltas=("partial ",), hang_event=hang)
    ep = _endpoints()[("POST", "/respond")]
    resp = await ep(_device_req("alice", body={"text": "long question"}))

    frames = []
    it = resp.body_iterator.__aiter__()
    # meta + first delta
    frames.append(await it.__anext__())
    frames.append(await it.__anext__())
    sid = _events(frames)[0]["session_id"]
    assert W.SESSION_STORE.cancel(sid, "alice") is True
    async for chunk in it:
        frames.append(chunk if isinstance(chunk, str) else chunk.decode())
    events = _events(frames)
    assert any(e.get("type") == "cancelled" and e.get("code") == "SESSION_CANCELLED"
               for e in events)
    # No spoken event after a cancel, and the session is no longer busy.
    assert not any(e.get("type") == "spoken" for e in events)
    assert W.SESSION_STORE.get(sid, "alice").busy is False


async def test_cancel_endpoint_owner_scoped(monkeypatch):
    _stub_llm(monkeypatch)
    eps = _endpoints()
    resp = await eps[("POST", "/respond")](_device_req("alice", body={"text": "hi"}))
    frames = await _collect_sse(resp)
    sid = _events(frames)[0]["session_id"]
    with pytest.raises(HTTPException) as exc:
        await eps[("POST", "/session/{session_id}/cancel")](
            _device_req("mallory"), session_id=sid)
    assert exc.value.status_code == 404
    out = await eps[("POST", "/session/{session_id}/cancel")](
        _device_req("alice"), session_id=sid)
    assert out["ok"] is True


async def test_delete_session(monkeypatch):
    _stub_llm(monkeypatch)
    eps = _endpoints()
    resp = await eps[("POST", "/respond")](_device_req("alice", body={"text": "hi"}))
    sid = _events(await _collect_sse(resp))[0]["session_id"]
    out = await eps[("DELETE", "/session/{session_id}")](
        _device_req("alice"), session_id=sid)
    assert out["ok"] is True
    assert W.SESSION_STORE.get(sid, "alice") is None
    with pytest.raises(HTTPException) as exc:
        await eps[("DELETE", "/session/{session_id}")](
            _device_req("alice"), session_id=sid)
    assert exc.value.status_code == 404


# --- media endpoints -------------------------------------------------------------

async def test_transcribe_unavailable_is_typed():
    router = W.setup_wearables_routes(_STT(available=False), _TTS())
    ep = {(m, r.path): r.endpoint for r in router.routes
          for m in (getattr(r, "methods", set()) or set())}[
        ("POST", "/api/wearables/v1/transcribe")]
    with pytest.raises(HTTPException) as exc:
        await ep(_device_req("alice"), file=_Upload())
    assert exc.value.status_code == 503
    assert exc.value.detail["code"] == "STT_UNAVAILABLE"


async def test_transcribe_happy_path():
    ep = _endpoints()[("POST", "/transcribe")]
    out = await ep(_device_req("alice"), file=_Upload(b"RIFFdata"))
    assert out == {"text": "hello glasses", "empty": False,
                   "request_id": out["request_id"]}


async def test_transcribe_enforces_size_cap(monkeypatch):
    import src.upload_limits as ul
    monkeypatch.setattr(W, "STT_MAX_AUDIO_BYTES", 10)
    ep = _endpoints()[("POST", "/transcribe")]
    with pytest.raises(HTTPException) as exc:
        await ep(_device_req("alice"), file=_Upload(b"x" * 11))
    assert exc.value.status_code == 413


async def test_speech_unavailable_and_happy_path():
    router = W.setup_wearables_routes(_STT(), _TTS(available=False))
    ep = {(m, r.path): r.endpoint for r in router.routes
          for m in (getattr(r, "methods", set()) or set())}[
        ("POST", "/api/wearables/v1/speech")]
    with pytest.raises(HTTPException) as exc:
        await ep(_device_req("alice", body={"text": "hi"}))
    assert exc.value.detail["code"] == "TTS_UNAVAILABLE"

    ep_ok = _endpoints()[("POST", "/speech")]
    resp = await ep_ok(_device_req("alice", body={"text": "# md **here**"}))
    assert resp.media_type == "audio/mpeg"  # _TTS returns ID3-magic bytes
    assert resp.body == b"ID3fakeaudio"


# --- vision -----------------------------------------------------------------------

async def test_vision_not_configured_is_explicit(monkeypatch):
    import services.wearables_gateway.capabilities as C
    monkeypatch.setattr(C, "resolve_vision_model", lambda force_refresh=False: None)
    ep = _endpoints()[("POST", "/vision/query")]
    with pytest.raises(HTTPException) as exc:
        await ep(_device_req("alice"),
                 image=_Upload(b"\xff\xd8jpeg", content_type="image/jpeg"),
                 question="what is this?")
    assert exc.value.status_code == 503
    assert exc.value.detail["code"] == "VISION_MODEL_NOT_CONFIGURED"


async def test_vision_rejects_non_image(monkeypatch):
    import services.wearables_gateway.capabilities as C
    monkeypatch.setattr(C, "resolve_vision_model",
                        lambda force_refresh=False: {"model": "m", "chat_url": "u"})
    ep = _endpoints()[("POST", "/vision/query")]
    with pytest.raises(HTTPException) as exc:
        await ep(_device_req("alice"),
                 image=_Upload(b"GIF89a", content_type="image/gif"),
                 question="?")
    assert exc.value.status_code == 400


async def test_vision_happy_path_sends_data_uri(monkeypatch):
    import services.wearables_gateway.capabilities as C
    import src.llm_core as llm
    monkeypatch.setattr(C, "resolve_vision_model",
                        lambda force_refresh=False: {
                            "model": "qwen3.6:27b",
                            "chat_url": "http://fake/v1/chat/completions"})
    captured = {}

    async def _fake_call(url, model, messages, temperature, max_tokens, **kw):
        captured.update(url=url, model=model, messages=messages)
        return "That is a **coffee cup** on a desk."

    monkeypatch.setattr(llm, "llm_call_async", _fake_call)
    ep = _endpoints()[("POST", "/vision/query")]
    out = await ep(_device_req("alice"),
                   image=_Upload(b"\xff\xd8fakejpeg", content_type="image/jpeg"),
                   question="what am I looking at?")
    assert out["model"] == "qwen3.6:27b"
    assert "coffee cup" in out["text"]
    assert "**" not in out["spoken"]
    content = captured["messages"][-1]["content"]
    kinds = {c["type"] for c in content}
    assert kinds == {"text", "image_url"}
    img = next(c for c in content if c["type"] == "image_url")
    assert img["image_url"]["url"].startswith("data:image/jpeg;base64,")


async def test_vision_stream_grounds_and_streams(monkeypatch):
    """Streaming Look-and-Ask: same SSE vocabulary as /respond, driven by the
    dedicated grounding prompt, with the spoken question passed through."""
    import services.wearables_gateway.capabilities as C
    import src.llm_core as llm
    monkeypatch.setattr(C, "resolve_vision_model",
                        lambda force_refresh=False: {
                            "model": "qwen3.6:27b",
                            "chat_url": "http://fake/v1/chat/completions"})
    captured = {}

    async def _fake_stream(url, model, messages, **kw):
        captured.update(url=url, model=model, messages=messages, kw=kw)
        for d in ("That is a red ", "octagonal stop sign."):
            yield "data: " + json.dumps({"delta": d}) + "\n\n"
        yield "data: [DONE]\n\n"

    monkeypatch.setattr(llm, "stream_llm", _fake_stream)
    ep = _endpoints()[("POST", "/vision/stream")]
    resp = await ep(_device_req("alice"),
                    image=_Upload(b"\xff\xd8fakejpeg", content_type="image/jpeg"),
                    question="what does this sign say?")
    frames = await _collect_sse(resp)
    events = _events(frames)

    assert events[0]["type"] == "wearables_meta"
    assert events[0]["model"] == "qwen3.6:27b"
    deltas = [e["delta"] for e in events if "delta" in e]
    assert "".join(deltas) == "That is a red octagonal stop sign."
    assert any(e.get("type") == "spoken" and "stop sign" in e["text"] for e in events)
    assert events[-1]["type"] == "done"
    assert frames[-1] == "data: [DONE]\n\n"
    assert sum(1 for f in frames if "[DONE]" in f) == 1   # upstream [DONE] swallowed
    # The GROUNDING system prompt (not the chat one) drives it, and the spoken
    # question + the image both reach the model.
    assert captured["messages"][0]["content"] == W.VISION_SYSTEM_PROMPT
    user = captured["messages"][-1]["content"]
    assert next(c for c in user if c["type"] == "text")["text"] == "what does this sign say?"
    assert next(c for c in user if c["type"] == "image_url"
                )["image_url"]["url"].startswith("data:image/jpeg;base64,")
    # A look refreshes the model's warm window (keep_alive passthrough).
    assert captured["kw"].get("extra_payload", {}).get("keep_alive")


async def test_vision_warm_preloads_model(monkeypatch):
    """POST /vision/warm delegates to the capabilities preload and returns its
    result verbatim (best-effort — never raises to the device)."""
    import services.wearables_gateway.capabilities as C

    async def _fake_warm(keep_alive="20m"):
        return {"warmed": True, "model": "qwen3.6:27b", "keep_alive": keep_alive}

    monkeypatch.setattr(C, "warm_vision_model", _fake_warm)
    ep = _endpoints()[("POST", "/vision/warm")]
    out = await ep(_device_req("alice"))
    assert out == {"warmed": True, "model": "qwen3.6:27b", "keep_alive": "20m"}


async def test_vision_warm_rate_limited_is_soft(monkeypatch):
    """Warming is an optimization: a rate-limit returns a 200 soft flag, never an
    error the app has to handle."""
    monkeypatch.setattr(W, "_media_limiter", RateLimiter(1, 60))
    import services.wearables_gateway.capabilities as C

    async def _fake_warm(keep_alive="20m"):
        return {"warmed": True, "model": "m", "keep_alive": keep_alive}

    monkeypatch.setattr(C, "warm_vision_model", _fake_warm)
    ep = _endpoints()[("POST", "/vision/warm")]
    assert (await ep(_device_req("alice")))["warmed"] is True    # first passes
    assert (await ep(_device_req("alice"))) == {"warmed": False, "reason": "RATE_LIMITED"}


async def test_vision_stream_empty_answer_emits_error_not_silent_done(monkeypatch):
    """An empty stream is a failure (parity with /vision/query's 502), not a silent
    'done' — the wearer must get an error cue, and nothing is logged to history."""
    import services.wearables_gateway.capabilities as C
    import src.llm_core as llm
    import services.wearables_gateway.productivity as _PROD
    monkeypatch.setattr(C, "resolve_vision_model",
                        lambda force_refresh=False: {
                            "model": "m", "chat_url": "http://fake/v1/chat/completions"})
    logged = []
    monkeypatch.setattr(_PROD, "log_vision",
                        lambda owner, q, a: logged.append((owner, q, a)))

    async def _empty_stream(url, model, messages, **kw):
        yield "data: [DONE]\n\n"      # model produced nothing usable

    monkeypatch.setattr(llm, "stream_llm", _empty_stream)
    ep = _endpoints()[("POST", "/vision/stream")]
    resp = await ep(_device_req("alice"),
                    image=_Upload(b"\xff\xd8x", content_type="image/jpeg"),
                    question="what is this?")
    frames = await _collect_sse(resp)
    assert any(f.startswith("event: error") for f in frames)          # cue emitted
    assert not any('"type": "spoken"' in f for f in frames)           # no fake success
    assert logged == []                                               # nothing persisted


async def test_vision_stream_upstream_error_doesnt_log_partial_or_leak(monkeypatch):
    """A mid-stream upstream error must NOT persist the truncated partial to history,
    must NOT follow with a 'truncated:False' spoken frame, and must NOT forward the
    raw upstream text (internal URLs) to the device."""
    import services.wearables_gateway.capabilities as C
    import src.llm_core as llm
    import services.wearables_gateway.productivity as _PROD
    monkeypatch.setattr(C, "resolve_vision_model",
                        lambda force_refresh=False: {
                            "model": "m", "chat_url": "http://fake/v1/chat/completions"})
    logged = []
    monkeypatch.setattr(_PROD, "log_vision",
                        lambda owner, q, a: logged.append((owner, q, a)))

    async def _err_stream(url, model, messages, **kw):
        yield "data: " + json.dumps({"delta": "The temperature is 72 degrees."}) + "\n\n"
        yield "event: error\ndata: " + json.dumps(
            {"status": 502, "text": "boom at http://internal-ollama:11434"}) + "\n\n"
        yield "data: [DONE]\n\n"

    monkeypatch.setattr(llm, "stream_llm", _err_stream)
    ep = _endpoints()[("POST", "/vision/stream")]
    resp = await ep(_device_req("alice"),
                    image=_Upload(b"\xff\xd8x", content_type="image/jpeg"),
                    question="temp?")
    frames = await _collect_sse(resp)
    assert any(f.startswith("event: error") for f in frames)
    assert logged == []                                              # no partial persisted
    assert not any("internal-ollama" in f for f in frames)           # raw upstream text curated
    assert not any('"truncated": false' in f.lower() and '"partial": false' in f.lower()
                   for f in frames)                                  # no clean terminal after error


async def test_warm_disabled_short_circuits(monkeypatch):
    """keep_alive="0" (opt-out) must skip the load entirely, not load-then-evict."""
    import services.wearables_gateway.capabilities as C
    resolved = []
    monkeypatch.setattr(C, "resolve_vision_model",
                        lambda force_refresh=False: resolved.append(1) or {
                            "model": "m", "chat_url": "x"})
    out = await C.warm_vision_model("0")
    assert out == {"warmed": False, "reason": "disabled"}
    assert resolved == []    # never even resolved the model → no cold-load


async def test_vision_stream_blank_question_uses_grounded_default(monkeypatch):
    """A plain tap (no spoken question) falls back to the specific-subject prompt,
    not a vague 'what am I looking at'."""
    import services.wearables_gateway.capabilities as C
    import src.llm_core as llm
    monkeypatch.setattr(C, "resolve_vision_model",
                        lambda force_refresh=False: {
                            "model": "qwen3.6:27b",
                            "chat_url": "http://fake/v1/chat/completions"})
    captured = {}

    async def _fake_stream(url, model, messages, **kw):
        captured.update(messages=messages)
        yield "data: " + json.dumps({"delta": "A ceramic mug."}) + "\n\n"
        yield "data: [DONE]\n\n"

    monkeypatch.setattr(llm, "stream_llm", _fake_stream)
    ep = _endpoints()[("POST", "/vision/stream")]
    resp = await ep(_device_req("alice"),
                    image=_Upload(b"\xff\xd8fakejpeg", content_type="image/jpeg"),
                    question="")
    await _collect_sse(resp)
    user = captured["messages"][-1]["content"]
    assert next(c for c in user if c["type"] == "text")["text"] == W.VISION_DEFAULT_QUESTION


# --- capabilities ------------------------------------------------------------------

async def test_capabilities_honest_reporting(monkeypatch):
    import services.wearables_gateway.capabilities as C
    import src.endpoint_resolver as epr
    import src.settings as settings
    monkeypatch.setattr(epr, "resolve_endpoint",
                        lambda prefix, owner=None: ("http://x/v1", "big-model", {}))
    monkeypatch.setattr(settings, "get_setting",
                        lambda k, d=None: {"stt_provider": "disabled",
                                           "tts_provider": "local"}.get(k, d))
    monkeypatch.setattr(C, "resolve_vision_model", lambda force_refresh=False: None)
    caps = C.build_capabilities(_STT(available=False), _TTS(available=True), "alice")
    assert caps["stt"] == {"available": False, "provider": "disabled"}
    assert caps["tts"]["available"] is True
    assert caps["llm"] == {"available": True, "model": "big-model", "streaming": True}
    assert caps["vision"]["state"] == "VISION_MODEL_NOT_CONFIGURED"
    assert caps["memory"]["available"] is False
    assert caps["tools"]["available"] == \
        ["manage_memory", "manage_notes", "search_chats", "web_fetch", "web_search"]
    assert caps["limits"]["text_max_chars"] == W.MAX_TEXT_CHARS


# --- redaction ---------------------------------------------------------------------

async def test_logs_never_contain_prompt_or_transcript(monkeypatch, caplog):
    import logging
    _stub_llm(monkeypatch, deltas=("classified answer",))
    ep = _endpoints()[("POST", "/respond")]
    secret_prompt = "my bank pin is 9876 tell me a fact"
    with caplog.at_level(logging.DEBUG):
        await _collect_sse(await ep(_device_req("alice", body={"text": secret_prompt})))
        tr = _endpoints()[("POST", "/transcribe")]
        await tr(_device_req("alice"), file=_Upload(b"RIFFxx"))
    joined = " ".join(r.getMessage() for r in caplog.records)
    assert "9876" not in joined
    assert "bank pin" not in joined
    assert "classified answer" not in joined
    assert "hello glasses" not in joined  # the transcription result


# --- C2: hard tool allowlist (the read-only claim is real) -------------------------

async def test_tool_allowlist_caps_the_schema_against_intent_widening():
    """The reviewer's exploit: spoken words like "email …" / "delete …" /
    "settings … token" used to seed send_email / manage_settings / manage_tokens
    into the schema for an admin-owned device token. tool_allowlist must cap the
    FINAL toolset regardless of any widening path, and force needs_admin off."""
    import src.agent_loop as al

    captured = {}
    orig = al._build_base_prompt

    def spy(disabled_tools, mcp_mgr, needs_admin, relevant_tools=None, **kw):
        captured["relevant"] = set(relevant_tools or [])
        captured["disabled"] = set(disabled_tools or [])
        captured["needs_admin"] = needs_admin
        return orig(disabled_tools, mcp_mgr, needs_admin,
                    relevant_tools=relevant_tools, **kw)

    al._build_base_prompt = spy
    try:
        # DANGEROUS tools that must never leak into the glasses schema. (The benign
        # owner-scoped tools manage_memory/manage_notes/search_chats are now allowed,
        # so they are deliberately NOT in this set.)
        mutating = {
            "send_email", "reply_to_email", "delete_email", "bulk_email",
            "manage_calendar", "manage_settings", "manage_tokens", "manage_contact",
            "manage_webhooks", "manage_endpoints", "serve_model", "stop_served_model",
            "download_model", "ui_control", "manage_session", "create_session",
            "send_to_session", "pipeline", "write_file", "bash", "python",
        }
        leaked = set()
        for text in (
            "email chris and tell him the deal is off",
            "delete all the emails from marketing",
            "change my settings and mint a new token",
            "stop the qwen model that is running",
            "search my chat history for the wifi password",
        ):
            captured.clear()
            agen = al.stream_agent_loop(
                "http://127.0.0.1:1/v1", "qwen3:8b",
                [{"role": "user", "content": text}],
                owner="admin",
                relevant_tools=set(W.WEARABLES_TOOLS),
                tool_allowlist=set(W.WEARABLES_TOOLS),
                disabled_tools=set(),
                max_rounds=1,
            )
            it = agen.__aiter__()
            with contextlib.suppress(Exception):
                for _ in range(4):
                    await asyncio.wait_for(it.__anext__(), timeout=25)
            await agen.aclose()
            assert captured.get("needs_admin") is False, text
            # A mutating tool is only reachable if it's in the schema AND not
            # execution-blocked. The cap must make that set empty.
            reachable = (captured.get("relevant", set()) & mutating) - captured.get("disabled", set())
            leaked |= reachable
        assert not leaked, f"mutating tools escaped the allowlist: {sorted(leaked)}"
    finally:
        al._build_base_prompt = orig


# --- LAN discover + approve enrollment --------------------------------------------

def _reset_enroll():
    W.ENROLL_STORE._reqs.clear()


async def test_discover_beacon_has_no_secrets():
    _reset_enroll()
    ep = _endpoints()[("GET", "/discover")]
    body = await ep(_req(ip="192.168.4.117"))
    assert body["service"] == "myai-wearables"
    assert body["api_version"] == 1
    assert body["enroll"] == "discover"
    # Identity + how to reach it only — never a code, token, or request_id.
    flat = json.dumps(body).lower()
    assert "token" not in flat and "code" not in flat and "request_id" not in flat


async def test_enroll_request_then_admin_approve_delivers_token_once(monkeypatch):
    _reset_enroll()
    # Don't touch the DB — stub the token mint.
    monkeypatch.setattr(W.gw_pairing, "mint_device_token",
                        lambda owner, name=None, invalidate=None: ("tid9", "ody_SECRET"))
    eps = _endpoints()

    # 1. App requests enrollment (unauthenticated).
    req = await eps[("POST", "/enroll/request")](
        _req(ip="192.168.4.117", body={"device_name": "SM-F966U1"}))
    request_id, code = req["request_id"], req["verify_code"]
    assert len(code) == 4 and request_id

    # 2. Poll is pending before approval; no token leaks.
    st = await eps[("GET", "/enroll/status/{request_id}")](_req(), request_id=request_id)
    assert st == {"status": "pending"}

    # 3. Admin sees it with the SAME verify code, approves by approval_id.
    pend = await eps[("GET", "/enroll/pending")](_req(user="carmody", is_admin=True))
    entry = pend["pending"][0]
    assert entry["verify_code"] == code and entry["device_name"] == "SM-F966U1"
    assert "request_id" not in entry  # admin never sees the app's secret
    res = await eps[("POST", "/enroll/{approval_id}/approve")](
        _req(user="carmody", is_admin=True), approval_id=entry["approval_id"])
    assert res["ok"] and res["token_id"] == "tid9"

    # 4. App's next poll gets the token exactly once.
    got = await eps[("GET", "/enroll/status/{request_id}")](_req(), request_id=request_id)
    assert got["status"] == "approved" and got["token"] == "ody_SECRET"
    assert got["scope"] == "wearables"
    again = await eps[("GET", "/enroll/status/{request_id}")](_req(), request_id=request_id)
    assert again["status"] == "denied_or_expired"  # single delivery


async def test_enroll_admin_endpoints_reject_non_admin_and_device_tokens():
    _reset_enroll()
    eps = _endpoints()
    # Seed a pending request to act on.
    req = await eps[("POST", "/enroll/request")](_req(ip="10.0.0.9", body={"device_name": "d"}))
    pend_ep = eps[("GET", "/enroll/pending")]
    approve_ep = eps[("POST", "/enroll/{approval_id}/approve")]

    # A wearables DEVICE token must not reach the approval surface (it's under
    # /api/wearables/ so the scope confinement passes it, but require_admin must
    # still refuse — a device can't approve itself or anyone else).
    for r in (_device_req("alice"), _req(user="bob", is_admin=False)):
        with pytest.raises(HTTPException) as exc:
            await pend_ep(r)
        assert exc.value.status_code == 403
        with pytest.raises(HTTPException) as exc:
            await approve_ep(r, approval_id="whatever")
        assert exc.value.status_code == 403


async def test_enroll_unknown_request_id_is_indistinguishable():
    _reset_enroll()
    ep = _endpoints()[("GET", "/enroll/status/{request_id}")]
    # An unknown/guessed id yields the same shape as a never-approved one — no
    # oracle for whether a request_id exists.
    assert await ep(_req(), request_id="totally-made-up") == {"status": "denied_or_expired"}


# --- productivity + history (owner-scoped) -----------------------------------------

import services.wearables_gateway.productivity as PROD  # noqa: E402


async def test_notes_list_and_add_are_owner_scoped(monkeypatch):
    seen = {}
    monkeypatch.setattr(PROD, "list_notes", lambda owner, limit=6: [{"id": "n1", "title": "hi"}] if owner == "alice" else [])
    def _create(owner, title, content="", date_iso=None):
        seen.update(owner=owner, title=title, content=content, date=date_iso)
        return {"id": "n9", "title": title}
    monkeypatch.setattr(PROD, "create_note", _create)
    eps = _endpoints()

    got = await eps[("GET", "/notes")](_device_req("alice"))
    assert got == {"notes": [{"id": "n1", "title": "hi"}]}

    added = await eps[("POST", "/notes")](_device_req("alice", body={"title": "milk", "content": "2%", "date": "2026-08-01"}))
    assert added["id"] == "n9"
    assert seen == {"owner": "alice", "title": "milk", "content": "2%", "date": "2026-08-01"}

    # A bearer without the wearables scope is refused before any DB call.
    with pytest.raises(HTTPException) as exc:
        await eps[("GET", "/notes")](_req(user="api", api_token=True, token_owner="alice", scopes="chat"))
    assert exc.value.status_code == 403


async def test_task_add_requires_text(monkeypatch):
    def _create(owner, text, due_date=None):
        if not text:
            raise ValueError("empty")
        return {"id": "t1", "title": text}
    monkeypatch.setattr(PROD, "create_task", _create)
    ep = _endpoints()[("POST", "/tasks")]
    with pytest.raises(HTTPException) as exc:
        await ep(_device_req("alice", body={"text": ""}))
    assert exc.value.status_code == 400
    ok = await ep(_device_req("alice", body={"text": "call vet"}))
    assert ok["title"] == "call vet"


async def test_item_done_toggles_owner_scoped(monkeypatch):
    seen = {}
    def _complete(owner, item_id):
        seen.update(owner=owner, id=item_id)
        # Toggle contract: None = not found, else the new done state (bool).
        if item_id == "missing":
            return None
        return item_id == "n1"   # n1 -> completed, others -> re-activated
    monkeypatch.setattr(PROD, "complete_item", _complete)
    ep = _endpoints()[("POST", "/items/{item_id}/done")]
    done = await ep(_device_req("alice"), item_id="n1")
    assert done == {"ok": True, "id": "n1", "done": True} and \
        seen == {"owner": "alice", "id": "n1"}
    # Un-completing returns done=False (a valid result, NOT a 404).
    reactivated = await ep(_device_req("alice"), item_id="n2")
    assert reactivated == {"ok": True, "id": "n2", "done": False}
    with pytest.raises(HTTPException) as exc:
        await ep(_device_req("alice"), item_id="missing")
    assert exc.value.status_code == 404


async def test_history_wire_to_owner(monkeypatch):
    monkeypatch.setattr(PROD, "list_chats", lambda owner, limit=20: [{"id": "c1", "name": "About X", "owner_seen": owner}])
    monkeypatch.setattr(PROD, "list_vision", lambda owner, limit=20: [{"id": "v1", "question": "what's this?", "owner_seen": owner}])
    eps = _endpoints()
    assert (await eps[("GET", "/history/chats")](_device_req("bob")))["chats"][0]["owner_seen"] == "bob"
    assert (await eps[("GET", "/history/vision")](_device_req("bob")))["vision"][0]["owner_seen"] == "bob"
