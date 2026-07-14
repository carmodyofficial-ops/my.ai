"""Wearables Gateway routes — /api/wearables/v1/*.

The narrow, authenticated surface a glasses companion app talks to. Auth is
enforced globally by AuthMiddleware (app.py) for every route EXCEPT
POST /pair, which is auth-exempt (the phone has no credential yet) and instead
requires a single-use, short-TTL pairing code minted by an admin — see
services/wearables_gateway/pairing.py for the enrollment contract.

Bearer callers must hold the "wearables" scope; device tokens carry ONLY that
scope, so a stolen glasses credential cannot drive the general chat/admin API.
Conversation streaming reuses the standard agent-loop runtime with a
read-only toolset and safe-abstention left active (trusted_execution=False).

Logging policy: request ids, owners, byte/char lengths, and error codes only —
never prompt text, transcripts, audio, or image content.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import uuid

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response, StreamingResponse

from core.middleware import require_admin
from services.wearables_gateway import errors as gw
from services.wearables_gateway import pairing as gw_pairing
from services.wearables_gateway.errors import gw_error
from services.wearables_gateway.sessions import WearableSessionStore
from services.wearables_gateway.spoken import (
    spoken_text, last_sentence_end, DEFAULT_MAX_SPOKEN_CHARS)
from src.auth_helpers import effective_user, get_current_user
from src.rate_limiter import RateLimiter
from src.upload_limits import (
    STT_MAX_AUDIO_BYTES,
    WEARABLES_IMAGE_MAX_BYTES,
    enforce_content_length,
    read_upload_limited,
)

logger = logging.getLogger(__name__)

MAX_TEXT_CHARS = 4000
MAX_QUESTION_CHARS = 500
MAX_SPEECH_CHARS = 2000
MAX_AGENT_ROUNDS = 6
# Don't speak a streamed segment until it's at least this long: merges tiny
# fragments an abbreviation boundary produces ("Dr.", "e.g.") into the next real
# sentence so the glasses TTS isn't choppy. The final flush emits any short tail.
MIN_STREAM_SEGMENT_CHARS = 24

# Toolset for the glasses channel. Beyond web search, the assistant can use the
# BENIGN, OWNER-SCOPED memory/productivity tools by voice — remember facts
# ("remember I'm allergic to X"), manage notes/todos/reminders ("remind me to call
# mom at 5"), and recall past chats. These touch only the caller's OWN data. Note a
# reminder CAN fire an outbound alert on the owner's OWN configured channel
# (email/ntfy/webhook) — that is the reminder's whole point and is self-directed,
# but it is not strictly side-effect-free. There is no way to message a THIRD PARTY
# or reach arbitrary destinations. Everything dangerous (shell/files/email/tokens/settings/
# ui_control/contacts write) stays OUT — relevant_tools + tool_allowlist are the
# HARD cap (see agent_loop), and the deny set below is belt-and-braces.
WEARABLES_TOOLS = {
    "web_search", "web_fetch",
    "manage_memory", "manage_notes", "search_chats",
}
WEARABLES_DISABLED_TOOLS = {
    "bash", "python", "shell", "terminal", "git",
    "write_file", "edit_file", "read_file", "grep", "glob", "ls", "get_workspace",
    "multi_edit", "delete_file", "move_file", "apply_patch", "run_tests",
    "lint_format", "code_sandbox", "http_request",
    "create_document", "update_document",
    "edit_document", "manage_documents", "manage_skills", "manage_mcp", "app_api",
    "dispatch_subagents", "request_sandbox_build",
    "send_email", "reply_to_email", "manage_settings", "manage_tokens",
    "manage_webhooks", "manage_endpoints", "ui_control", "manage_contact",
}

SPOKEN_SYSTEM_PROMPT = (
    "You are my.ai speaking through smart glasses. The user HEARS your answer. "
    "Lead with the direct answer in the first sentence. Keep it to 2-4 short "
    "sentences unless the user asks for more. Plain conversational prose only: "
    "no markdown, no bullet lists, no tables, no code blocks, never read a URL "
    "aloud. If a lot more detail exists, end with a brief offer like 'Want more "
    "detail?'. Never speak passwords, tokens, keys, or other secrets. "
    "You can remember facts about the user, manage their notes/to-dos/reminders, "
    "and search past chats when asked (e.g. 'remember I'm allergic to peanuts', "
    "'remind me to call mom at 5'); after doing so, confirm in ONE short sentence."
)

# Look-and-Ask uses a DEDICATED vision prompt (not the chat one): the chat prompt
# optimizes for brevity and produces vague scene summaries. This one forces CONCRETE,
# grounded answers — read text verbatim, give counts/colors/brands/prices, identify
# the single main subject — which is the whole point of pointing the glasses at
# something. Still spoken-friendly (short, no markdown).
VISION_SYSTEM_PROMPT = (
    "You are my.ai, seeing through the wearer's smart glasses and speaking aloud. "
    "You are given ONE photo of what they are looking at, plus their question. "
    "Answer the question DIRECTLY and CONCRETELY from what is actually visible. "
    "Be specific: identify the exact object (not the whole scene), read any text, "
    "numbers, or labels VERBATIM, and state colors, counts, brands, prices, and "
    "readings you can actually see. Do NOT hedge with 'appears to be' or 'likely' "
    "when it is clear — only flag uncertainty when the photo genuinely doesn't show "
    "it, and if the answer isn't visible, say so in one sentence. Keep it to 1-3 "
    "short spoken sentences: plain conversational prose, no markdown, no lists, "
    "never spell out a URL. Lead with the answer."
)
# What we ask the model when the wearer just taps Look & Ask without speaking a
# question — steer it to name the specific primary subject, not describe everything.
VISION_DEFAULT_QUESTION = (
    "What is the main thing I'm looking at? Identify it specifically and note the "
    "most important detail.")


def _vision_keep_alive() -> str:
    """How long Ollama keeps the vision model resident after a look/warm. Default
    20m so it survives a normal session; set `wearables_vision_keep_alive` to "0"
    to opt out (unload immediately — for a VRAM-tight host sharing the chat model)."""
    from src import settings
    val = settings.get_setting("wearables_vision_keep_alive", "20m")
    return (str(val).strip() if val is not None else "") or "20m"


def _vision_messages(mime: str, data: bytes, question: str):
    """Build the (question, chat-messages) pair for a Look-and-Ask. A blank question
    (plain tap) falls back to the specific-subject default. Shared by the one-shot
    and streaming vision endpoints so the grounding prompt lives in ONE place."""
    import base64
    q = (question or "").strip()[:MAX_QUESTION_CHARS] or VISION_DEFAULT_QUESTION
    data_uri = f"data:{mime};base64," + base64.b64encode(data).decode()
    return q, [
        {"role": "system", "content": VISION_SYSTEM_PROMPT},
        {"role": "user", "content": [
            {"type": "text", "text": q},
            {"type": "image_url", "image_url": {"url": data_uri}},
        ]},
    ]

# Module-level singletons (same pattern as cowork's approval registry) so
# tests can import and drive them directly.
PAIRING_STORE = gw_pairing.PairingStore()
ENROLL_STORE = gw_pairing.EnrollmentStore()
SESSION_STORE = WearableSessionStore()

_pair_limiter = RateLimiter(max_requests=5, window_seconds=60)
_respond_limiter = RateLimiter(max_requests=30, window_seconds=60)
_media_limiter = RateLimiter(max_requests=20, window_seconds=60)
# LAN discovery + enrollment: discovery is cheap/read-only (looser); enroll
# requests and polls are per-IP capped in the store too.
_discover_limiter = RateLimiter(max_requests=30, window_seconds=60)
_enroll_limiter = RateLimiter(max_requests=10, window_seconds=60)
_enroll_poll_limiter = RateLimiter(max_requests=60, window_seconds=60)


def _host_label() -> str:
    """Human name for this host, shown in the app's discovery list and the
    admin approval prompt. Overridable; falls back to the hostname."""
    import os as _os
    import socket as _socket
    name = (_os.environ.get("MYAI_WEARABLES_HOST_NAME") or "").strip()
    if name:
        return name[:60]
    try:
        return (_socket.gethostname() or "my.ai host")[:60]
    except Exception:
        return "my.ai host"

_ALLOWED_IMAGE_TYPES = {"image/jpeg": "jpeg", "image/png": "png", "image/webp": "webp"}


def require_wearables(request: Request) -> str:
    """Owner for a wearables call. Bearer tokens need the wearables scope;
    cookie sessions (browser user testing the gateway) pass through."""
    if getattr(request.state, "api_token", False):
        scopes = getattr(request.state, "api_token_scopes", None) or []
        if isinstance(scopes, str):
            scopes = [s.strip() for s in scopes.split(",")]
        if gw_pairing.DEVICE_SCOPE not in {str(s).strip() for s in scopes}:
            raise gw_error(403, gw.FORBIDDEN_SCOPE,
                           "This credential lacks the wearables scope")
    owner = effective_user(request)
    if not owner and owner != "":
        raise gw_error(401, gw.AUTHENTICATION_REQUIRED, "Authentication required")
    return owner


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _new_request_id() -> str:
    return uuid.uuid4().hex[:12]


# Generous ceiling for the JSON control bodies (/pair, /respond, /speech). The
# per-field char caps are far smaller; this only stops a body from being read
# wholesale into memory before those caps apply. /pair is auth-exempt, so an
# uncapped request.json() there is an UNAUTHENTICATED memory-exhaustion lever.
MAX_JSON_BODY_BYTES = 256 * 1024


async def _read_json_object(request: Request) -> dict:
    # Reject on declared size first (cheap, no bytes read)…
    clen = request.headers.get("content-length")
    if clen is not None:
        try:
            if int(clen) > MAX_JSON_BODY_BYTES:
                raise gw_error(413, gw.PAYLOAD_TOO_LARGE, "Request body too large")
        except ValueError:
            pass
    # …then bound the actual read, in case Content-Length was absent or lied
    # (a chunked body has no Content-Length, so stream and abort past the cap
    # rather than letting request.body() buffer it all).
    chunks = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > MAX_JSON_BODY_BYTES:
            raise gw_error(413, gw.PAYLOAD_TOO_LARGE, "Request body too large")
        chunks.append(chunk)
    raw = b"".join(chunks)
    try:
        body = json.loads(raw)
    except Exception:
        raise gw_error(400, gw.BAD_REQUEST, "JSON body required")
    if not isinstance(body, dict):
        raise gw_error(400, gw.BAD_REQUEST, "JSON object required")
    return body


def _advertised_cert_sha256() -> str | None:
    """SHA-256 (hex) of the DER form of the advertised TLS cert, for pinning
    in the pairing payload. Path overridable for non-default proxies."""
    import base64
    import hashlib
    import os
    import re

    path = os.environ.get("MYAI_WEARABLES_TLS_CERT") or "data/lan-cert.pem"
    try:
        with open(path) as f:
            pem = f.read()
        m = re.search(
            r"-----BEGIN CERTIFICATE-----(.*?)-----END CERTIFICATE-----",
            pem, re.S,
        )
        if not m:
            return None
        der = base64.b64decode("".join(m.group(1).split()))
        return hashlib.sha256(der).hexdigest()
    except OSError:
        return None


def setup_wearables_routes(stt_service, tts_service) -> APIRouter:
    router = APIRouter(prefix="/api/wearables/v1", tags=["wearables"])

    # ── Health & capabilities ────────────────────────────────────────────

    @router.get("/health")
    async def health(request: Request):
        """Cheap, auth-validated liveness: a 200 proves host, port, and
        credential. Component detail lives in /capabilities."""
        owner = require_wearables(request)
        return {
            "ok": True,
            "service": "wearables_gateway",
            "api_version": 1,
            "auth": "token" if getattr(request.state, "api_token", False) else "session",
            "owner": owner,
        }

    @router.get("/capabilities")
    async def capabilities(request: Request):
        owner = require_wearables(request)
        from services.wearables_gateway.capabilities import build_capabilities
        # build_capabilities → resolve_vision_model uses a SYNC httpx.Client
        # (GET /api/tags + up to 8× POST /api/show @5s) — on a cache miss that
        # blocks the whole event loop for tens of seconds. Run it off-loop.
        return await asyncio.to_thread(
            build_capabilities, stt_service, tts_service, owner)

    # ── Enrollment ───────────────────────────────────────────────────────

    @router.post("/pairings")
    async def create_pairing(request: Request):
        """Mint a one-time pairing code (admin cookie only; CSRF-safe because
        the SameSite=Lax session cookie is not sent cross-site on POST — the
        same posture as companion/ and POST /api/tokens)."""
        require_admin(request)
        owner = get_current_user(request)
        if not owner:
            raise gw_error(401, gw.AUTHENTICATION_REQUIRED, "Session required")
        code = PAIRING_STORE.mint(owner)
        from companion import pairing as companion_pairing
        hosts = companion_pairing.lan_ip_candidates()
        # Inside Docker, lan_ip_candidates() sees the container network, not
        # the address a phone can reach — let the operator advertise the real
        # host LAN IP/port (usually the TLS lan_proxy on 7443, see
        # docs/wearables/PAIRING_AND_AUTH.md).
        import os as _os
        advertised = (_os.environ.get("MYAI_WEARABLES_ADVERTISE_HOST") or "").strip()
        host = advertised or (hosts[0] if hosts else "127.0.0.1")
        if advertised and advertised not in hosts:
            hosts = [advertised] + hosts
        try:
            adv_port = int(_os.environ.get("MYAI_WEARABLES_ADVERTISE_PORT") or 0)
        except ValueError:
            adv_port = 0
        tls = (_os.environ.get("MYAI_WEARABLES_ADVERTISE_TLS") or "").lower() in ("1", "true", "yes")
        port = adv_port or request.url.port or companion_pairing.default_port()
        payload = {"v": 1, "kind": "wearables", "host": host, "port": port,
                   "tls": tls, "code": code}
        # Self-signed LAN cert: ship its SHA-256 in the payload so the app can
        # pin exactly this certificate (the QR is the trust bootstrap; Android
        # otherwise rejects the handshake with no trust anchor).
        if tls:
            fp = _advertised_cert_sha256()
            if fp:
                payload["cert_sha256"] = fp
        qr = companion_pairing.pairing_qr_png_data_uri(payload)
        logger.info(f"[wearables] pairing code minted by owner={owner} "
                    f"(pending={PAIRING_STORE.pending_count()})")
        return {
            "code": code,
            "expires_in": PAIRING_STORE.ttl,
            "host": host,
            "hosts": hosts,
            "port": port,
            "payload": payload,
            "qr": qr if (qr or "").startswith("data:image/png;base64,") else None,
        }

    @router.post("/pair")
    async def pair(request: Request):
        """Exchange a one-time pairing code for a revocable device credential.
        AUTH-EXEMPT (app.py) — the phone has no credential yet. Protected by:
        single-use hashed codes, short TTL, and a per-IP rate limit."""
        ip = _client_ip(request)
        if not _pair_limiter.check(f"pair:{ip}"):
            raise gw_error(429, gw.RATE_LIMITED, "Too many pairing attempts")
        body = await _read_json_object(request)
        code = str(body.get("code") or "")
        device_name = body.get("device_name")
        owner = PAIRING_STORE.consume(code)
        if owner is None:
            logger.info(f"[wearables] pairing rejected from {ip} (invalid/expired code)")
            raise gw_error(401, gw.PAIRING_CODE_INVALID,
                           "Pairing code is invalid, expired, or already used")
        invalidate = getattr(request.app.state, "invalidate_token_cache", None)
        # bcrypt (~180ms) + a DB insert — off the event loop so an (auth-exempt)
        # /pair flood can't stall the whole app.
        token_id, raw_token = await asyncio.to_thread(
            gw_pairing.mint_device_token,
            owner, device_name if isinstance(device_name, str) else None,
            invalidate,
        )
        logger.info(f"[wearables] device enrolled token_id={token_id} owner={owner}")
        return {
            "token": raw_token,  # shown once; only a bcrypt hash is stored
            "token_id": token_id,
            "owner": owner,
            "scope": gw_pairing.DEVICE_SCOPE,
            "api_base": "/api/wearables/v1",
        }

    # ── LAN discovery + approve enrollment ───────────────────────────────
    # An alternative to the admin-minted pairing code: the app finds the host on
    # the LAN, requests enrollment, and the admin approves on the host with a
    # matching verify code. No QR/JSON to copy, no admin creds on the phone.

    @router.get("/discover")
    async def discover(request: Request):
        """Unauthenticated identity beacon for LAN discovery. Holds NO secrets —
        just what the app needs to decide it found a my.ai host and how to reach
        it over TLS (the cert fingerprint is the same public value already in the
        pairing payload). AUTH-EXEMPT + rate-limited."""
        if not _discover_limiter.check(f"discover:{_client_ip(request)}"):
            raise gw_error(429, gw.RATE_LIMITED, "Too many requests")
        import os as _os
        adv_tls = (_os.environ.get("MYAI_WEARABLES_ADVERTISE_TLS") or "").lower() in ("1", "true", "yes")
        try:
            adv_port = int(_os.environ.get("MYAI_WEARABLES_ADVERTISE_PORT") or 0)
        except ValueError:
            adv_port = 0
        body = {
            "service": "myai-wearables",
            "api_version": 1,
            "name": _host_label(),
            "tls": adv_tls,
            "port": adv_port or request.url.port or 0,
            "enroll": "discover",  # this host supports the discover+approve flow
        }
        # A stable address the phone should PERSIST for access from any network —
        # e.g. the host's Tailscale IP. Found on the LAN, but reachable over the
        # tailnet after pairing, so Wi-Fi drops (and being away from home) stop
        # mattering. The pinned cert is IP-agnostic, so it validates there too.
        adv_host = (_os.environ.get("MYAI_WEARABLES_ADVERTISE_HOST") or "").strip()
        if adv_host:
            body["persist_host"] = adv_host
            body["persist_port"] = adv_port or body["port"]
        if adv_tls:
            fp = _advertised_cert_sha256()
            if fp:
                body["cert_sha256"] = fp
        return body

    @router.post("/enroll/request")
    async def enroll_request(request: Request):
        """The app asks to enroll. Creates a PENDING request an admin must
        approve; returns a secret request_id (to poll) and a verify code (shown
        to the user and the admin so they confirm the same device). AUTH-EXEMPT,
        rate-limited + per-IP capped in the store."""
        ip = _client_ip(request)
        if not _enroll_limiter.check(f"enroll:{ip}"):
            raise gw_error(429, gw.RATE_LIMITED, "Too many enrollment attempts")
        body = await _read_json_object(request)
        device_name = body.get("device_name") if isinstance(body.get("device_name"), str) else None
        out = ENROLL_STORE.request(device_name, ip)
        if not out:
            raise gw_error(429, gw.RATE_LIMITED, "Too many pending requests from this device")
        logger.info(f"[wearables] enroll requested from {ip} "
                    f"(pending={ENROLL_STORE.pending_count()})")
        return out

    @router.get("/enroll/status/{request_id}")
    async def enroll_status(request: Request, request_id: str):
        """The app polls with its secret request_id. Returns pending until the
        admin approves, then delivers the device token ONCE. AUTH-EXEMPT (the
        request_id IS the credential — high entropy, unguessable)."""
        if not _enroll_poll_limiter.check(f"enrollpoll:{_client_ip(request)}"):
            raise gw_error(429, gw.RATE_LIMITED, "Too many requests")
        result = ENROLL_STORE.poll(request_id)
        if result.get("status") == "approved":
            logger.info(f"[wearables] enroll token delivered token_id={result.get('token_id')}")
        return result

    @router.get("/enroll/pending")
    async def enroll_pending(request: Request):
        """Admin view of devices awaiting approval (for the host's approval UI)."""
        require_admin(request)
        return {"pending": ENROLL_STORE.list_pending()}

    @router.post("/enroll/{approval_id}/approve")
    async def enroll_approve(request: Request, approval_id: str):
        """Admin approves a pending device by its public approval_id. Mints the
        wearables token; the app retrieves it via its own request_id."""
        require_admin(request)
        owner = get_current_user(request)
        if not owner:
            raise gw_error(401, gw.AUTHENTICATION_REQUIRED, "Session required")
        invalidate = getattr(request.app.state, "invalidate_token_cache", None)
        # approve() mints a device token (bcrypt + DB) — off the event loop.
        result = await asyncio.to_thread(
            ENROLL_STORE.approve, approval_id, owner, invalidate)
        if result is None:
            raise gw_error(404, gw.BAD_REQUEST, "No such pending enrollment")
        logger.info(f"[wearables] enroll approved token_id={result['token_id']} owner={owner}")
        return {"ok": True, **result}

    @router.post("/enroll/{approval_id}/deny")
    async def enroll_deny(request: Request, approval_id: str):
        require_admin(request)
        if not ENROLL_STORE.deny(approval_id):
            raise gw_error(404, gw.BAD_REQUEST, "No such pending enrollment")
        return {"ok": True, "approval_id": approval_id}

    @router.get("/devices")
    async def devices(request: Request):
        require_admin(request)
        # Full ApiToken table scan — off the event loop.
        return {"devices": await asyncio.to_thread(gw_pairing.list_devices)}

    # ── Productivity (owner-scoped notes / tasks / calendar) ──────────────
    # Purpose-built for the companion's home cards + quick-add. Every call is
    # scoped to the device's own owner via require_wearables; DB work runs off
    # the event loop.

    from services.wearables_gateway import productivity as prod

    def _date(body):
        d = body.get("date") or body.get("due_date")
        return d if isinstance(d, str) and d.strip() else None

    @router.get("/notes")
    async def notes_list(request: Request):
        owner = require_wearables(request)
        return {"notes": await asyncio.to_thread(prod.list_notes, owner)}

    @router.post("/notes")
    async def notes_add(request: Request):
        owner = require_wearables(request)
        body = await _read_json_object(request)
        try:
            note = await asyncio.to_thread(
                prod.create_note, owner, str(body.get("title") or ""),
                str(body.get("content") or ""), _date(body))
        except ValueError:
            raise gw_error(400, gw.BAD_REQUEST, "Note needs a title or content")
        return note

    @router.get("/tasks")
    async def tasks_list(request: Request):
        owner = require_wearables(request)
        return {"tasks": await asyncio.to_thread(prod.list_tasks, owner)}

    @router.post("/tasks")
    async def tasks_add(request: Request):
        owner = require_wearables(request)
        body = await _read_json_object(request)
        try:
            task = await asyncio.to_thread(
                prod.create_task, owner, str(body.get("text") or ""), _date(body))
        except ValueError:
            raise gw_error(400, gw.BAD_REQUEST, "Task text is required")
        return task

    @router.post("/items/{item_id}/done")
    async def item_done(request: Request, item_id: str):
        """Toggle a single-item checklist TASK between completed and active
        (owner-scoped); completed tasks stay visible (greyed). No-op for notes and
        multi-item checklists (returns done=false). 404 only if no such item."""
        owner = require_wearables(request)
        done = await asyncio.to_thread(prod.complete_item, owner, item_id)
        if done is None:   # None = not found; False is a valid "now active" result
            raise gw_error(404, gw.BAD_REQUEST, "No such item")
        return {"ok": True, "id": item_id, "done": done}

    # ── History (chats + Look-and-Ask) ────────────────────────────────────

    @router.get("/history/chats")
    async def history_chats(request: Request):
        owner = require_wearables(request)
        return {"chats": await asyncio.to_thread(prod.list_chats, owner)}

    @router.get("/history/vision")
    async def history_vision(request: Request):
        owner = require_wearables(request)
        return {"vision": await asyncio.to_thread(prod.list_vision, owner)}

    @router.delete("/devices/{token_id}")
    async def revoke(request: Request, token_id: str):
        require_admin(request)
        invalidate = getattr(request.app.state, "invalidate_token_cache", None)
        # DB write — off the event loop.
        if not await asyncio.to_thread(gw_pairing.revoke_device, token_id, invalidate):
            raise gw_error(404, gw.BAD_REQUEST, "No such wearable device credential")
        logger.info(f"[wearables] device revoked token_id={token_id}")
        return {"ok": True, "token_id": token_id, "active": False}

    # ── Conversation ─────────────────────────────────────────────────────

    @router.post("/respond")
    async def respond(request: Request):
        """Text in → SSE stream out (meta → deltas → spoken → done). This is
        the conversation runtime path: stream_agent_loop with the read-only
        wearables toolset. Cancellation: POST /session/{id}/cancel, or just
        drop the SSE connection."""
        owner = require_wearables(request)
        if not _respond_limiter.check(f"respond:{owner or _client_ip(request)}"):
            raise gw_error(429, gw.RATE_LIMITED, "Too many requests")
        body = await _read_json_object(request)

        text = body.get("text")
        if not isinstance(text, str) or not text.strip():
            raise gw_error(400, gw.BAD_REQUEST, "text (non-empty string) required")
        text = text.strip()
        if len(text) > MAX_TEXT_CHARS:
            raise gw_error(413, gw.PAYLOAD_TOO_LARGE,
                           f"text exceeds {MAX_TEXT_CHARS} characters")
        store_transcript = bool(body.get("store_transcript", True))
        session = SESSION_STORE.get_or_create(
            body.get("session_id") if isinstance(body.get("session_id"), str) else None,
            owner, store_transcript=store_transcript,
        )
        # One in-flight response per session: a second concurrent /respond on the
        # same session would clobber cancel_event (making the first uncancellable)
        # and interleave into session.messages. The session store's BUSY_MAX_SECONDS
        # backstop clears a stuck-busy flag from a crashed stream.
        if session.busy:
            raise gw_error(409, gw.RATE_LIMITED,
                           "A response is already in progress for this session")

        from src.endpoint_resolver import resolve_endpoint
        try:
            endpoint_url, model, headers = resolve_endpoint("default", owner=owner)
        except Exception:
            endpoint_url, model, headers = None, None, None
        if not (endpoint_url and model):
            raise gw_error(503, gw.LLM_UNAVAILABLE, "No model endpoint configured")

        # Glasses chat runs on the fast 20b ("simple" tier) for snappy spoken
        # replies — no per-turn routing. Vision is the only path that uses the
        # larger qwen3.6:27b, and only because it needs vision. Respects the
        # admin's configured simple model; falls back to gpt-oss:20b.
        try:
            from src import settings as _s
            from src.model_router import _is_local
            if _is_local(endpoint_url):
                fast = _s.get_setting("auto_model_simple", "gpt-oss:20b")
                fast = (str(fast).strip() if fast is not None else "")
                if fast:
                    model = fast
        except Exception:
            pass

        request_id = _new_request_id()
        messages = ([{"role": "system", "content": SPOKEN_SYSTEM_PROMPT}]
                    + list(session.messages)
                    + [{"role": "user", "content": text}])

        cancel_event = asyncio.Event()
        session.cancel_event = cancel_event
        session.busy = True
        logger.info(f"[wearables] respond start req={request_id} owner={owner} "
                    f"session={session.id} model={model} chars={len(text)}")

        async def gen():
            yield "data: " + json.dumps({
                "type": "wearables_meta",
                "session_id": session.id,
                "model": model,
                "request_id": request_id,
            }) + "\n\n"
            full_parts: list[str] = []
            spoken_cursor = 0   # chars of the answer already emitted as spoken
            spoken_chars = 0    # total spoken chars emitted (caps run-on TTS)
            spoken_capped = False
            cancelled = False
            try:
                from src.agent_loop import stream_agent_loop
                agen = stream_agent_loop(
                    endpoint_url, model, messages,
                    headers=headers or {}, owner=owner,
                    relevant_tools=set(WEARABLES_TOOLS),
                    # Hard cap: nothing outside this set can be armed by intent
                    # widening or admin detection, even though the device owner
                    # is an admin. This is the real enforcement; the deny-set
                    # below is now redundant belt-and-braces.
                    tool_allowlist=set(WEARABLES_TOOLS),
                    disabled_tools=set(WEARABLES_DISABLED_TOOLS),
                    # ALWAYS redact user text from host logs on the wearables path —
                    # the gateway's logging policy is "lengths only, never prompt
                    # text/transcripts". (store_transcript only governs the rolling
                    # in-memory context, NOT logging; tying redaction to it meant the
                    # default store_transcript=True leaked spoken prompts to app.log.)
                    redact_user_text=True,
                    max_rounds=MAX_AGENT_ROUNDS,
                )
                it = agen.__aiter__()
                cancel_t = asyncio.ensure_future(cancel_event.wait())
                try:
                    while True:
                        next_t = asyncio.ensure_future(it.__anext__())
                        await asyncio.wait(
                            {next_t, cancel_t}, return_when=asyncio.FIRST_COMPLETED)
                        if cancel_event.is_set():
                            next_t.cancel()
                            with contextlib.suppress(BaseException):
                                await next_t
                            with contextlib.suppress(Exception):
                                await agen.aclose()
                            cancelled = True
                            break
                        try:
                            chunk = next_t.result()
                        except StopAsyncIteration:
                            break
                        if isinstance(chunk, str) and chunk.startswith("data: "):
                            payload = chunk[6:].strip()
                            if payload == "[DONE]":
                                continue  # we emit our own terminal frame below
                            try:
                                d = json.loads(payload)
                                # Chain-of-thought deltas carry "thinking":
                                # they may show on the phone but must never
                                # reach the spoken answer or session history.
                                if (isinstance(d, dict)
                                        and isinstance(d.get("delta"), str)
                                        and not d.get("thinking")):
                                    full_parts.append(d["delta"])
                                    # Stream spoken sentences as they complete so
                                    # the FIRST sentence's TTS starts ~1s in instead
                                    # of after the whole reply. The client plays them
                                    # in order (its TTS queue).
                                    if not spoken_capped:
                                        joined = "".join(full_parts)
                                        end = last_sentence_end(joined, spoken_cursor)
                                        if end > spoken_cursor:
                                            seg = spoken_text(
                                                joined[spoken_cursor:end])["spoken"]
                                            # Buffer short fragments (abbreviations)
                                            # until they grow into a real sentence.
                                            if len(seg) >= MIN_STREAM_SEGMENT_CHARS:
                                                spoken_cursor = end
                                                spoken_chars += len(seg)
                                                if seg:
                                                    yield "data: " + json.dumps({
                                                        "type": "spoken", "text": seg,
                                                        "partial": True,
                                                        "truncated": False,
                                                        "request_id": request_id}) + "\n\n"
                                                # Stop speaking once we've said a
                                                # screenful; the rest stays on the
                                                # phone (final frame flags it).
                                                if spoken_chars >= DEFAULT_MAX_SPOKEN_CHARS:
                                                    spoken_capped = True
                            except (ValueError, TypeError):
                                pass
                        yield chunk
                finally:
                    cancel_t.cancel()
                    # Close the inner agent-loop generator on EVERY exit —
                    # normal completion, client disconnect (GeneratorExit at the
                    # yield), or a raised exception — not just the explicit
                    # cancel branch above. Otherwise the underlying streaming
                    # httpx connection leaks until GC. Idempotent if already
                    # closed on the cancel path.
                    with contextlib.suppress(Exception):
                        await agen.aclose()
            except Exception as exc:
                # Log the real detail host-side; send the DEVICE only a fixed,
                # curated message — str(exc) can carry internal detail (endpoint
                # URLs, backend error strings) and every other error frame here is
                # already curated via gw_error.
                logger.error(f"[wearables] respond stream error req={request_id}: {exc}")
                yield "event: error\ndata: " + json.dumps(
                    {"code": gw.LLM_UNAVAILABLE,
                     "message": "The model stream failed. Please try again."}) + "\n\n"
            finally:
                session.busy = False
                session.cancel_event = None
                session.touch()

            full_text = "".join(full_parts)
            if cancelled:
                logger.info(f"[wearables] respond cancelled req={request_id}")
                yield "data: " + json.dumps(
                    {"type": "cancelled", "code": gw.SESSION_CANCELLED,
                     "request_id": request_id}) + "\n\n"
            else:
                if full_text:
                    session.append_turn(text, full_text)
                if spoken_capped:
                    # We already spoke a screenful; don't dump the rest to TTS.
                    # The full answer is on the phone; flag the spoken side as
                    # truncated so the client can cue "more on your phone".
                    sp = {"spoken": "", "truncated": True}
                else:
                    # Flush the trailing partial sentence (everything up to the last
                    # sentence boundary was already streamed as spoken above), but
                    # still bound its length so a single run-on final sentence can't
                    # blow past the spoken cap.
                    remainder = full_text[spoken_cursor:]
                    sp = (spoken_text(remainder, max_chars=DEFAULT_MAX_SPOKEN_CHARS)
                          if remainder.strip()
                          else {"spoken": "", "truncated": False})
                yield "data: " + json.dumps({
                    "type": "spoken",
                    "text": sp["spoken"],
                    "partial": False,
                    "truncated": sp["truncated"],
                    "request_id": request_id,
                }) + "\n\n"
                logger.info(f"[wearables] respond done req={request_id} "
                            f"chars={len(full_text)}")
            yield "data: " + json.dumps(
                {"type": "done", "request_id": request_id,
                 "session_id": session.id}) + "\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(gen(), media_type="text/event-stream")

    @router.post("/session/{session_id}/cancel")
    async def cancel_session(request: Request, session_id: str):
        owner = require_wearables(request)
        if SESSION_STORE.get(session_id, owner) is None:
            raise gw_error(404, gw.SESSION_NOT_FOUND, "No such session")
        cancelled = SESSION_STORE.cancel(session_id, owner)
        return {"ok": True, "cancelled": cancelled, "session_id": session_id}

    @router.delete("/session/{session_id}")
    async def delete_session(request: Request, session_id: str):
        owner = require_wearables(request)
        if not SESSION_STORE.delete(session_id, owner):
            raise gw_error(404, gw.SESSION_NOT_FOUND, "No such session")
        logger.info(f"[wearables] session deleted owner={owner}")
        return {"ok": True, "deleted": session_id}

    # ── Speech ───────────────────────────────────────────────────────────

    @router.post("/transcribe")
    async def transcribe(request: Request, file: UploadFile = File(...)):
        enforce_content_length(request, STT_MAX_AUDIO_BYTES, "Audio")
        owner = require_wearables(request)
        if not _media_limiter.check(f"stt:{owner or _client_ip(request)}"):
            raise gw_error(429, gw.RATE_LIMITED, "Too many requests")
        try:
            available = bool(stt_service is not None and stt_service.available)
        except Exception:
            available = False
        if not available:
            raise gw_error(503, gw.STT_UNAVAILABLE,
                           "Speech-to-text is not configured on the host")
        audio = await read_upload_limited(file, STT_MAX_AUDIO_BYTES, "Audio")
        if not audio:
            raise gw_error(400, gw.BAD_REQUEST, "Empty audio")
        request_id = _new_request_id()
        text = await asyncio.to_thread(stt_service.transcribe, audio)
        if text is None:
            logger.error(f"[wearables] transcribe failed req={request_id} "
                         f"bytes={len(audio)}")
            raise gw_error(502, gw.STT_FAILED, "Transcription failed")
        logger.info(f"[wearables] transcribe ok req={request_id} "
                    f"bytes={len(audio)} chars={len(text)}")
        return {"text": text, "empty": not text.strip(), "request_id": request_id}

    @router.post("/speech")
    async def speech(request: Request):
        owner = require_wearables(request)
        if not _media_limiter.check(f"tts:{owner or _client_ip(request)}"):
            raise gw_error(429, gw.RATE_LIMITED, "Too many requests")
        body = await _read_json_object(request)
        text = body.get("text")
        if not isinstance(text, str) or not text.strip():
            raise gw_error(400, gw.BAD_REQUEST, "text (non-empty string) required")
        if bool(body.get("transform", True)):
            text = spoken_text(text, max_chars=MAX_SPEECH_CHARS)["spoken"]
        if len(text) > MAX_SPEECH_CHARS:
            raise gw_error(413, gw.PAYLOAD_TOO_LARGE,
                           f"text exceeds {MAX_SPEECH_CHARS} characters")
        try:
            available = bool(tts_service is not None and tts_service.available)
        except Exception:
            available = False
        if not available:
            raise gw_error(503, gw.TTS_UNAVAILABLE,
                           "Text-to-speech is not configured on the host")
        request_id = _new_request_id()
        # use_cache=False: the assistant's spoken answer can contain private
        # content the user asked about, and the retention policy says audio is
        # transient. The default on-disk SHA-keyed cache would persist it.
        audio = await asyncio.to_thread(tts_service.synthesize, text, False)
        if not audio:
            logger.error(f"[wearables] speech synthesis failed req={request_id}")
            raise gw_error(502, gw.TTS_FAILED, "Speech synthesis failed")
        is_mp3 = audio[:3] == b"ID3" or (
            len(audio) >= 2 and audio[0] == 0xFF and (audio[1] & 0xE0) == 0xE0)
        logger.info(f"[wearables] speech ok req={request_id} bytes={len(audio)}")
        return Response(
            content=audio,
            media_type="audio/mpeg" if is_mp3 else "audio/wav",
            headers={"X-Request-Id": request_id},
        )

    # ── Vision (Look and Ask) ────────────────────────────────────────────

    @router.post("/vision/query")
    async def vision_query(request: Request,
                           image: UploadFile = File(...),
                           question: str = Form("What am I looking at?"),
                           store_transcript: bool = Form(True)):
        """Image + question → concise local-model answer. The image lives only for
        the duration of the request and is never persisted or logged (retention
        policy: transient, dropped when the request ends). Note: a frame larger than
        Starlette's ~1 MB multipart threshold transits a short-lived temp file that
        the framework unlinks at request end — it is never durably stored."""
        enforce_content_length(request, WEARABLES_IMAGE_MAX_BYTES, "Image")
        owner = require_wearables(request)
        if not _media_limiter.check(f"vision:{owner or _client_ip(request)}"):
            raise gw_error(429, gw.RATE_LIMITED, "Too many requests")
        from services.wearables_gateway.capabilities import resolve_vision_model
        # SYNC httpx on a cache miss — keep it off the event loop (see /capabilities).
        vision = await asyncio.to_thread(resolve_vision_model)
        if not vision:
            raise gw_error(503, gw.VISION_MODEL_NOT_CONFIGURED,
                           "No local vision-capable model is configured")
        mime = (image.content_type or "").lower().split(";")[0].strip()
        if mime not in _ALLOWED_IMAGE_TYPES:
            raise gw_error(400, gw.BAD_REQUEST,
                           "Image must be JPEG, PNG, or WebP")
        data = await read_upload_limited(image, WEARABLES_IMAGE_MAX_BYTES, "Image")
        if not data:
            raise gw_error(400, gw.BAD_REQUEST, "Empty image")
        request_id = _new_request_id()
        question, messages = _vision_messages(mime, data, question)
        logger.info(f"[wearables] vision query req={request_id} owner={owner} "
                    f"model={vision['model']} bytes={len(data)}")
        try:
            from src.llm_core import llm_call_async
            answer = await llm_call_async(
                vision["chat_url"], vision["model"], messages, 0.2, 700,
                headers={}, timeout=120,
                # Refresh the warm window so back-to-back looks stay fast.
                extra_payload={"keep_alive": _vision_keep_alive()},
            )
        except Exception as exc:
            logger.error(f"[wearables] vision failed req={request_id}: "
                         f"{type(exc).__name__}")
            raise gw_error(502, gw.VISION_FAILED, "Vision query failed")
        finally:
            # Transient-image policy: drop all references before returning.
            data = None
            messages = None
        if not isinstance(answer, str) or not answer.strip():
            raise gw_error(502, gw.VISION_FAILED, "Vision model returned no answer")
        sp = spoken_text(answer)
        # Persist the exchange (text only — the image is never stored) so the
        # companion can show a Look-and-Ask history. Gated on store_transcript so
        # it matches the conversation path's privacy-by-default: store_transcript=
        # false → nothing retained. Best-effort.
        if store_transcript:
            try:
                from services.wearables_gateway import productivity as prod
                await asyncio.to_thread(prod.log_vision, owner, question, answer)
            except Exception as e:
                logger.debug(f"[wearables] vision log skipped: {e}")
        return {
            "text": answer,
            "spoken": sp["spoken"],
            "truncated": sp["truncated"],
            "model": vision["model"],
            "request_id": request_id,
        }

    @router.post("/vision/warm")
    async def vision_warm(request: Request):
        """Preload + pin the vision model warm so the FIRST Look-and-Ask after idle
        doesn't pay Ollama's cold-load. The app calls this (fire-and-forget) when
        Look-and-Ask becomes available. Best-effort: always 200 with a `warmed`
        flag — warming is an optimization, never a hard dependency for a look."""
        owner = require_wearables(request)
        if not _media_limiter.check(f"warm:{owner or _client_ip(request)}"):
            # Warming is cheap when already loaded, but don't let it be spammed.
            return {"warmed": False, "reason": "RATE_LIMITED"}
        from services.wearables_gateway.capabilities import warm_vision_model
        result = await warm_vision_model(_vision_keep_alive())
        logger.info(f"[wearables] vision warm owner={owner} "
                    f"warmed={result.get('warmed')} model={result.get('model')}")
        return result

    @router.post("/vision/stream")
    async def vision_stream(request: Request,
                            image: UploadFile = File(...),
                            question: str = Form(""),
                            store_transcript: bool = Form(True)):
        """Streaming Look-and-Ask: image (+ optional spoken question) → SSE
        (meta → deltas → spoken → done), the SAME frame vocabulary as /respond so
        the first spoken sentence's TTS starts ~1-2s in instead of after the whole
        answer is generated. Image is transient (memory-only, never disk/logs)."""
        enforce_content_length(request, WEARABLES_IMAGE_MAX_BYTES, "Image")
        owner = require_wearables(request)
        if not _media_limiter.check(f"vision:{owner or _client_ip(request)}"):
            raise gw_error(429, gw.RATE_LIMITED, "Too many requests")
        from services.wearables_gateway.capabilities import resolve_vision_model
        vision = await asyncio.to_thread(resolve_vision_model)
        if not vision:
            raise gw_error(503, gw.VISION_MODEL_NOT_CONFIGURED,
                           "No local vision-capable model is configured")
        mime = (image.content_type or "").lower().split(";")[0].strip()
        if mime not in _ALLOWED_IMAGE_TYPES:
            raise gw_error(400, gw.BAD_REQUEST, "Image must be JPEG, PNG, or WebP")
        data = await read_upload_limited(image, WEARABLES_IMAGE_MAX_BYTES, "Image")
        if not data:
            raise gw_error(400, gw.BAD_REQUEST, "Empty image")
        request_id = _new_request_id()
        question, messages = _vision_messages(mime, data, question)
        data = None   # the data_uri inside `messages` is now the only copy
        logger.info(f"[wearables] vision stream req={request_id} owner={owner} "
                    f"model={vision['model']}")

        async def gen():
            yield "data: " + json.dumps({
                "type": "wearables_meta",
                "session_id": "",
                "model": vision["model"],
                "request_id": request_id,
            }) + "\n\n"
            full_parts: list[str] = []
            spoken_cursor = 0
            spoken_chars = 0
            spoken_capped = False
            errored = False
            agen = None
            try:
                from src.llm_core import stream_llm
                agen = stream_llm(vision["chat_url"], vision["model"], messages,
                                  temperature=0.2, max_tokens=700,
                                  headers={}, timeout=120,
                                  # Refresh the warm window (see /vision/warm).
                                  extra_payload={"keep_alive": _vision_keep_alive()})
                async for chunk in agen:
                    if isinstance(chunk, str) and chunk.startswith("event: error"):
                        # Curate upstream errors: raw frames can carry endpoint URLs
                        # / backend strings. Send the device a fixed message only, and
                        # DON'T log the raw frame (host-log policy: codes only).
                        logger.warning("[wearables] vision stream upstream error "
                                       f"req={request_id}")
                        yield "event: error\ndata: " + json.dumps(
                            {"code": gw.VISION_FAILED,
                             "message": "The vision model stream failed. "
                                        "Please try again."}) + "\n\n"
                        errored = True
                        break
                    if not (isinstance(chunk, str) and chunk.startswith("data: ")):
                        yield chunk
                        continue
                    payload = chunk[6:].strip()
                    if payload == "[DONE]":
                        continue   # we emit our own terminal frames below
                    try:
                        d = json.loads(payload)
                    except (ValueError, TypeError):
                        yield chunk
                        continue
                    if (isinstance(d, dict) and isinstance(d.get("delta"), str)
                            and not d.get("thinking")):
                        full_parts.append(d["delta"])
                        # Same per-sentence spoken streaming as /respond: buffer
                        # short fragments, cap total spoken length.
                        if not spoken_capped:
                            joined = "".join(full_parts)
                            end = last_sentence_end(joined, spoken_cursor)
                            if end > spoken_cursor:
                                seg = spoken_text(joined[spoken_cursor:end])["spoken"]
                                if len(seg) >= MIN_STREAM_SEGMENT_CHARS:
                                    spoken_cursor = end
                                    spoken_chars += len(seg)
                                    if seg:
                                        yield "data: " + json.dumps({
                                            "type": "spoken", "text": seg,
                                            "partial": True, "truncated": False,
                                            "request_id": request_id}) + "\n\n"
                                    if spoken_chars >= DEFAULT_MAX_SPOKEN_CHARS:
                                        spoken_capped = True
                    yield chunk
            except Exception as exc:
                logger.error(f"[wearables] vision stream error req={request_id}: "
                             f"{type(exc).__name__}")
                yield "event: error\ndata: " + json.dumps(
                    {"code": gw.VISION_FAILED,
                     "message": "The vision model stream failed. "
                                "Please try again."}) + "\n\n"
                errored = True
            finally:
                if agen is not None:
                    with contextlib.suppress(Exception):
                        await agen.aclose()
                # (The base64 image in `messages` is freed when this generator is
                # closed/collected at end-of-response; not nil'd here because
                # rebinding a closure var would shadow the earlier read.)

            full_text = "".join(full_parts)
            if not errored and not full_text.strip():
                # Parity with /vision/query (which raises 502 on an empty answer):
                # an empty stream is a FAILURE, not a silent completion — otherwise
                # the wearer hears nothing and gets no cue. Emit a curated error.
                yield "event: error\ndata: " + json.dumps(
                    {"code": gw.VISION_FAILED,
                     "message": "The vision model returned no answer. "
                                "Please try again."}) + "\n\n"
                errored = True
            if not errored:
                # Only persist + emit the terminal spoken frame on a CLEAN finish —
                # a mid-stream error already sent its own error frame, so we must not
                # log the truncated partial to Look-and-Ask history or follow the
                # error with a "truncated:False" spoken frame that contradicts it.
                if store_transcript:
                    try:
                        from services.wearables_gateway import productivity as prod
                        await asyncio.to_thread(
                            prod.log_vision, owner, question, full_text)
                    except Exception as e:
                        logger.debug(f"[wearables] vision log skipped: {e}")
                if spoken_capped:
                    sp = {"spoken": "", "truncated": True}
                else:
                    remainder = full_text[spoken_cursor:]
                    sp = (spoken_text(remainder, max_chars=DEFAULT_MAX_SPOKEN_CHARS)
                          if remainder.strip()
                          else {"spoken": "", "truncated": False})
                yield "data: " + json.dumps({
                    "type": "spoken", "text": sp["spoken"],
                    "partial": False, "truncated": sp["truncated"],
                    "request_id": request_id}) + "\n\n"
                logger.info(f"[wearables] vision stream done req={request_id} "
                            f"chars={len(full_text)}")
            yield "data: " + json.dumps(
                {"type": "done", "request_id": request_id, "session_id": ""}) + "\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(gen(), media_type="text/event-stream")

    return router
