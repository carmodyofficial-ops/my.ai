#!/usr/bin/env python3
"""LAN proxy for my.ai / Odysseus — forwards LAN traffic to the loopback app.

Docker stays loopback-only (127.0.0.1:7000); this is the single LAN entry point.
It runs in two modes:

  * Plain (default): a raw TCP relay, LAN -> 127.0.0.1:7000. Matches the existing
    host-side proxy posture.
  * TLS: pass --tls-cert/--tls-key and it terminates HTTPS on the LAN side and
    forwards the decrypted stream to the loopback app, so session cookies and
    credentials never cross the network in clear text.

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


def _tls_context(cert: str, key: str) -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(certfile=cert, keyfile=key)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    return ctx


async def _run(args) -> None:
    if bool(args.tls_cert) ^ bool(args.tls_key):
        raise SystemExit("--tls-cert and --tls-key must be provided together")
    ctx = _tls_context(args.tls_cert, args.tls_key) if args.tls_cert else None

    server = await asyncio.start_server(
        lambda r, w: _handle(r, w, args.target_host, args.target_port),
        host=args.listen_host,
        port=args.listen_port,
        ssl=ctx,
    )
    addrs = ", ".join(str(s.getsockname()) for s in server.sockets)
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
    asyncio.run(_run(p.parse_args()))


if __name__ == "__main__":
    main()
