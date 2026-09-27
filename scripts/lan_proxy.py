#!/usr/bin/env python3
"""LAN proxy for my.ai / Odysseus — forwards LAN traffic to the loopback app.

Docker stays loopback-only (127.0.0.1:7000); this is the single LAN entry point.
It runs in two modes:

  * Plain (default): a raw TCP relay, LAN -> 127.0.0.1:7000. Matches the existing
    host-side proxy posture.
  * TLS: pass --tls-cert/--tls-key and it terminates HTTPS on the LAN side and
    forwards the decrypted stream to the loopback app, so session cookies and
    credentials never cross the network in clear text.
  * Redirect: pass --redirect-to https://host and plain-HTTP page requests get
    a 308 to the same path on that HTTPS origin (API paths get a 403 naming
    it). Nothing is proxied. A client that already sent credentials over
    plain HTTP has exposed them, so point clients at HTTPS directly.

Examples:
    # plain
    python3 scripts/lan_proxy.py --listen-host 0.0.0.0 --listen-port 7000
    # TLS (generate a locally-trusted cert with mkcert first)
    python3 scripts/lan_proxy.py --listen-host 0.0.0.0 --listen-port 7443 \
        --tls-cert /path/cert.pem --tls-key /path/key.pem

Bind 0.0.0.0 so the proxy keeps working when DHCP changes the host's LAN IP; the
app's own auth/session layer remains the security boundary.

Note: this is an L4 proxy — in TLS mode it does not inject X-Forwarded-Proto. The
SPA uses same-origin relative requests, so that is fine; set SECURE_COOKIES=true
on the app so cookies are marked Secure (the browser<->proxy hop is HTTPS). If
you later need scheme-aware absolute redirects, front with a header-aware proxy
(e.g. Caddy) instead.
"""
import argparse
import asyncio
import logging
import signal
import ssl

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("lan-proxy")


async def _pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while True:
            data = await reader.read(65536)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except (ConnectionError, asyncio.IncompleteReadError, ssl.SSLError):
        pass
    finally:
        try:
            writer.close()
        except Exception:
            pass


async def _handle(client_reader, client_writer, target_host, target_port) -> None:
    try:
        server_reader, server_writer = await asyncio.open_connection(target_host, target_port)
    except OSError as exc:
        log.warning("backend connect failed (%s:%s): %s", target_host, target_port, exc)
        client_writer.close()
        return
    await asyncio.gather(
        _pipe(client_reader, server_writer),
        _pipe(server_reader, client_writer),
    )


_MAX_REQUEST_HEAD = 16384
_MAX_DRAIN_BYTES = 1 << 20
_HEAD_TIMEOUT_S = 10
_DRAIN_TIMEOUT_S = 5


def _normalize_redirect_base(value: str) -> str:
    """Validate --redirect-to: an absolute https origin (scheme + host[:port],
    no path/query). Anything else — a missing scheme, http://, a bare path —
    would redirect in circles or keep traffic in clear text."""
    from urllib.parse import urlsplit
    raw = (value or "").strip()
    parts = urlsplit(raw)
    if parts.scheme != "https" or not parts.hostname or parts.path not in ("", "/") \
            or parts.query or parts.fragment or parts.username or parts.password:
        raise SystemExit(f"--redirect-to must be an https origin like https://host.example (got {value!r})")
    return f"https://{parts.netloc}"


async def _read_request_head(reader) -> bytes:
    """Read header lines up to the blank line. Accepts CRLF and bare-LF line
    endings; bounded by _MAX_REQUEST_HEAD bytes and _HEAD_TIMEOUT_S."""
    lines, size = [], 0

    async def _read():
        nonlocal size
        while True:
            line = await reader.readline()
            if not line:
                raise asyncio.IncompleteReadError(b"", None)
            size += len(line)
            if size > _MAX_REQUEST_HEAD:
                raise asyncio.LimitOverrunError("request head too large", size)
            if line in (b"\r\n", b"\n"):
                return
            lines.append(line)

    await asyncio.wait_for(_read(), timeout=_HEAD_TIMEOUT_S)
    return b"".join(lines)


async def _drain_body(reader, head: bytes) -> None:
    """Consume a request body before replying. Closing a socket with unread
    input makes the kernel send RST, which can destroy the 308 before the
    client reads it (a real risk for POSTs over the LAN)."""
    length = 0
    chunked = False
    for line in head.split(b"\n")[1:]:
        name, _, value = line.partition(b":")
        name = name.strip().lower()
        if name == b"content-length" and value.strip().isdigit():
            length = int(value.strip())
        elif name == b"transfer-encoding" and b"chunked" in value.lower():
            chunked = True
    budget = min(length, _MAX_DRAIN_BYTES) if not chunked else _MAX_DRAIN_BYTES

    async def _drain():
        remaining = budget
        while remaining > 0:
            data = await reader.read(min(65536, remaining))
            if not data:
                return
            if chunked and data.endswith(b"0\r\n\r\n"):
                return
            if not chunked:
                remaining -= len(data)

    if budget:
        try:
            await asyncio.wait_for(_drain(), timeout=_DRAIN_TIMEOUT_S)
        except asyncio.TimeoutError:
            pass


async def _redirect(client_reader, client_writer, base: str) -> None:
    """Answer one plain-HTTP request without proxying it.

    Pages get a 308 to the same path on the HTTPS origin. API paths get a
    403 naming the HTTPS origin instead: API clients (OkHttp, requests) drop
    Authorization on cross-host redirects, so following a 308 would turn into
    a confusing 401 rather than a visible "use HTTPS" error.

    Note: whatever the client already sent (cookies, a bearer token, a login
    body) has crossed the network in clear text by the time we answer; this
    listener just refuses to act on it. Point clients at the HTTPS origin."""
    try:
        head = await _read_request_head(client_reader)
    except (asyncio.TimeoutError, asyncio.IncompleteReadError, asyncio.LimitOverrunError,
            ValueError, ConnectionError):
        client_writer.close()
        return
    request_line = head.split(b"\n", 1)[0].strip()
    parts = request_line.split(b" ")
    method = parts[0].decode("latin-1").upper() if parts else "GET"
    path = parts[1].decode("latin-1") if len(parts) >= 2 else "/"
    # Only redirect origin-form paths; anything else (absolute-form, CR/LF
    # smuggling, oversized) goes to the root.
    if not path.startswith("/") or any(c in path for c in "\r\n") or len(path) > 4096:
        path = "/"
    await _drain_body(client_reader, head)

    if path.startswith("/api/"):
        status = b"403 Forbidden"
        body = f"Plain HTTP is disabled. Use {base}{path}\n".encode("latin-1", "replace")
        location = b""
    else:
        status = b"308 Permanent Redirect"
        body = b"Moved to HTTPS\n"
        location = f"Location: {base}{path}\r\n".encode("latin-1")
    client_writer.write(
        b"HTTP/1.1 " + status + b"\r\n" + location
        + b"Content-Type: text/plain\r\nContent-Length: " + str(len(body)).encode()
        + b"\r\nConnection: close\r\n\r\n"
        + (b"" if method == "HEAD" else body)
    )
    try:
        await client_writer.drain()
        # Half-close so the client sees a clean FIN after the response, not a
        # reset racing it.
        if client_writer.can_write_eof():
            client_writer.write_eof()
    except (ConnectionError, OSError):
        pass
    finally:
        client_writer.close()


def _tls_context(cert: str, key: str) -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(certfile=cert, keyfile=key)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    return ctx


async def _run(args) -> None:
    if bool(args.tls_cert) ^ bool(args.tls_key):
        raise SystemExit("--tls-cert and --tls-key must be provided together")
    ctx = _tls_context(args.tls_cert, args.tls_key) if args.tls_cert else None
    base = _normalize_redirect_base(args.redirect_to) if args.redirect_to else ""
    if base and ctx:
        raise SystemExit("--redirect-to is for the plain listener; don't combine it with TLS")

    if base:
        handler = lambda r, w: _redirect(r, w, base)  # noqa: E731
    else:
        handler = lambda r, w: _handle(r, w, args.target_host, args.target_port)  # noqa: E731
    server = await asyncio.start_server(
        handler,
        host=args.listen_host,
        port=args.listen_port,
        ssl=ctx,
        # Only the redirect handler needs a small head cap; the relays keep
        # asyncio's default buffer so uploads aren't throttled.
        **({"limit": _MAX_REQUEST_HEAD} if base else {}),
    )
    addrs = ", ".join(str(s.getsockname()) for s in server.sockets)
    if base:
        log.info("redirect listener on %s -> 308 %s", addrs, base)
    else:
        log.info(
            "%s proxy listening on %s -> %s:%s",
            "TLS" if ctx else "plain",
            addrs,
            args.target_host,
            args.target_port,
        )

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            pass
    async with server:
        await stop.wait()
    log.info("shutting down")


def main() -> None:
    p = argparse.ArgumentParser(description="LAN proxy for Odysseus (plain or TLS)")
    p.add_argument("--listen-host", default="0.0.0.0")
    p.add_argument("--listen-port", type=int, default=7000)
    p.add_argument("--target-host", default="127.0.0.1")
    p.add_argument("--target-port", type=int, default=7000)
    p.add_argument("--tls-cert", default="", help="PEM certificate (chain) file; enables TLS")
    p.add_argument("--tls-key", default="", help="PEM private key file; enables TLS")
    p.add_argument("--redirect-to", default="",
                   help="HTTPS origin (e.g. https://host.tailnet.ts.net); plain requests get a 308 there")
    asyncio.run(_run(p.parse_args()))


if __name__ == "__main__":
    main()
