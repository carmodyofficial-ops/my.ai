# src/middleware.py
# Shared middleware, decorators, and request helpers

import json
import logging
import os
import secrets

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


class BodySizeLimitMiddleware:
    """Pure-ASGI guard that rejects an oversized request body BEFORE Starlette
    parses or spools it.

    Why this exists: FastAPI's ``UploadFile``/``Form`` params make Starlette parse
    the WHOLE multipart body and spool it to a temp file (past ~1 MB) before the
    route handler — and its per-route caps — ever run. So a body with no
    ``Content-Length`` (chunked) bypasses the handler's header check entirely, and
    a multi-GB body can exhaust disk before anything rejects it. This middleware
    closes both: a declared over-ceiling ``Content-Length`` is refused before a
    byte is read, and a chunked/streaming body is counted and cut off the moment it
    crosses the ceiling.

    It is a COARSE global backstop (default 128 MB). The tight per-route limits
    (``read_upload_limited`` / ``enforce_content_length``) remain the precise gates;
    this only stops egregious abuse the framework would otherwise let hit disk.

    Implementation note: on a streaming overflow we do NOT raise through the app —
    ``BaseHTTPMiddleware`` (the auth layer) runs the inner app in an anyio task
    group that would wrap our exception in an ``ExceptionGroup``. Instead we send
    the 413 ourselves and feed the inner app an ``http.disconnect`` so it unwinds,
    swallowing anything it tries to send afterward.
    """

    def __init__(self, app, max_body_bytes: int):
        self.app = app
        self.max_body_bytes = int(max_body_bytes)

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            # WebSocket/lifespan carry no large HTTP body — pass straight through.
            return await self.app(scope, receive, send)

        # Fast path: a declared Content-Length over the ceiling is refused before
        # a single body byte is read (covers every well-behaved client).
        for name, value in scope.get("headers") or ():
            if name == b"content-length":
                try:
                    if int(value) > self.max_body_bytes:
                        self._log(scope)
                        return await self._reject(send)
                except (ValueError, TypeError):
                    pass
                break

        total = 0
        rejected = False          # WE sent the 413
        app_responded = False     # the inner app started its own response

        async def limited_receive():
            nonlocal total, rejected
            message = await receive()
            if (message.get("type") == "http.request" and not rejected):
                total += len(message.get("body", b"") or b"")
                if total > self.max_body_bytes:
                    if app_responded:
                        # App already responded (unusual for an upload route); we
                        # can't inject a 413, so just cut the body off.
                        return {"type": "http.disconnect"}
                    rejected = True
                    self._log(scope)
                    await self._reject(send)          # raw send — the real 413
                    # Tell the inner app the client is gone so it stops reading and
                    # unwinds; its subsequent output is swallowed by guarded_send.
                    return {"type": "http.disconnect"}
            return message

        async def guarded_send(message):
            nonlocal app_responded
            if rejected:
                return                                 # 413 already sent — drop the rest
            if message.get("type") == "http.response.start":
                app_responded = True
            await send(message)

        try:
            await self.app(scope, limited_receive, guarded_send)
        except Exception:
            # The app unwound from our injected disconnect (ClientDisconnect, possibly
            # wrapped in an ExceptionGroup by BaseHTTPMiddleware). We already sent the
            # 413 — swallow. Anything else is a real error → re-raise.
            if rejected:
                return
            raise

    def _log(self, scope):
        logger.warning("Rejected oversized request body (> %d bytes) on %s %s",
                       self.max_body_bytes, scope.get("method", "?"),
                       scope.get("path", "?"))

    async def _reject(self, send):
        body = json.dumps(
            {"detail": {"code": "PAYLOAD_TOO_LARGE",
                        "message": "Request body too large"}}).encode()
        await send({
            "type": "http.response.start",
            "status": 413,
            "headers": [(b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode())],
        })
        await send({"type": "http.response.body", "body": body})


# Per-process token that lets the in-app tool layer hit admin-gated
# routes via HTTP loopback (the agent's tool calls don't carry the
# admin user's session cookie). Set once at import; tools read the
# same value from this module. Never persisted or exposed externally.
INTERNAL_TOOL_TOKEN = os.environ.get("ODYSSEUS_INTERNAL_TOKEN") or secrets.token_hex(32)
INTERNAL_TOOL_HEADER = "X-Odysseus-Internal-Token"
# Pseudo-username on in-process tool-loopback requests; require_admin trusts it and it is reserved.
INTERNAL_TOOL_USER = "internal-tool"


def is_cors_preflight(method: str, headers) -> bool:
    """True for a genuine CORS preflight: an OPTIONS request carrying the
    Access-Control-Request-Method header. Such requests are credential-less by
    design and must reach CORSMiddleware to be answered -- gating them on auth
    401s the preflight and breaks every cross-origin browser/WebView client.
    Pure so it can be unit-tested without standing up the app."""
    return method == "OPTIONS" and "access-control-request-method" in headers


def require_admin(request: Request):
    """Raise 403 if the current user isn't an admin.
    Allows access when auth is explicitly disabled, or when the request carries
    the in-process internal-tool token used by loopback agent tools.
    """
    # In-process bypass for tool-layer loopback calls. Two paths:
    # (a) header-direct (caller set X-Odysseus-Internal-Token), or
    # (b) the auth middleware already validated the token and stamped
    #     request.state.current_user = "internal-tool".
    try:
        hdr = request.headers.get(INTERNAL_TOOL_HEADER)
        if hdr and secrets.compare_digest(hdr, INTERNAL_TOOL_TOKEN):
            return
        if getattr(request.state, "current_user", None) == INTERNAL_TOOL_USER:
            return
    except Exception:
        pass

    auth_mgr = getattr(request.app.state, "auth_manager", None)
    if os.getenv("AUTH_ENABLED", "true").lower() == "false":
        return
    if not auth_mgr or not auth_mgr.is_configured:
        raise HTTPException(403, "Admin only")
    user = getattr(request.state, "current_user", None)
    if not user or not auth_mgr.is_admin(user):
        raise HTTPException(403, "Admin only")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add standard security headers to all responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Generate a per-request nonce for inline scripts
        nonce = secrets.token_hex(16)
        request.state.csp_nonce = nonce

        response = await call_next(request)
        path = request.url.path

        # Tool render endpoints are served inside iframes — allow framing by self
        is_tool_render = path.startswith("/api/tools/") and path.endswith("/render")
        # PDF previews are embedded by the in-app document library. Keep the
        # exception route-scoped so normal app pages remain unframeable.
        is_document_pdf_preview = path.startswith("/api/document/") and path.endswith("/render-pdf")
        # Visual report pages are self-contained HTML — need inline scripts + external images
        is_report = path.startswith("/api/research/report/")

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(self), geolocation=()"

        is_https = (
            request.url.scheme == "https"
            or request.headers.get("X-Forwarded-Proto") == "https"
        )
        if is_https:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        if is_report:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "font-src 'self'; "
                "img-src 'self' data: blob: https:; "
                "connect-src 'self'; "
                "frame-ancestors 'none'"
            )
        elif is_tool_render:
            # Tool iframe content: skip all framing headers — the iframe's
            # sandbox="allow-scripts" attribute provides isolation.
            # Don't overwrite the route's own restrictive CSP either.
            pass
        elif is_document_pdf_preview:
            response.headers["X-Frame-Options"] = "SAMEORIGIN"
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; "
                "frame-ancestors 'self'"
            )
        else:
            response.headers["X-Frame-Options"] = "DENY"
            # NOTE: `style-src 'unsafe-inline'` is intentionally retained.
            # `static/index.html` and `static/login.html` ship inline <style>
            # blocks, and several JS modules build runtime `style=""` attrs.
            # Migrating to nonce-only requires templating the HTML files +
            # auditing every JS-set style attribute. Since inline styles
            # don't execute script, the residual risk is visual-only.
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                f"script-src 'self' 'nonce-{nonce}' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "font-src 'self' https://cdn.jsdelivr.net; "
                "img-src 'self' data: blob:; "
                "media-src 'self' blob:; "
                "connect-src 'self'; "
                "frame-src 'self'; "
                "frame-ancestors 'none'"
            )
        return response
