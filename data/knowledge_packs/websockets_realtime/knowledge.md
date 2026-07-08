# WebSockets & Realtime

## WebSocket lifecycle
- `const ws = new WebSocket('wss://...')` — events: `open`, `message`, `error`, `close`. `error` gives almost no detail (security); the useful info is `close.code`/`close.reason`.
- Close codes: 1000 normal, 1001 going away, 1006 abnormal (no close frame — network drop, most common in the wild), 1008 policy violation, 1011 server error, 4000-4999 app-defined.
- Check `ws.readyState === WebSocket.OPEN` before `send()`; sending on CONNECTING throws. Queue messages until `open`.
- `ws.bufferedAmount` = bytes queued but unsent — backpressure signal; stop producing if it grows (slow consumer).
- Always `wss://` in production; browsers block `ws://` from HTTPS pages (mixed content).

## Reconnect: backoff + jitter
- Exponential backoff with full jitter: `delay = random(0, min(cap, base * 2**attempt))`, e.g. base 500ms, cap 30s. Jitter prevents thundering herd after a server restart.
- Reset the attempt counter only after a connection has stayed healthy (e.g., open ≥ N seconds or first message received), not on `open` alone.
- Do NOT reconnect on close codes that mean "stop": 1008 (auth/policy) or your own 4xxx "unauthorized" code — surface a re-login instead.
- On reconnect, re-establish state: re-subscribe to channels, request a snapshot or replay from `lastSeenId` — the socket has no memory.
- Pause reconnection when `document.visibilityState === 'hidden'` or `navigator.onLine === false`; reconnect immediately on `online`/`visibilitychange`.

## Heartbeat
- Browsers can't send protocol-level pings; use app-level: client sends `{"type":"ping"}` every 25-30s, expects `pong` within a timeout (e.g., 5-10s), else `ws.close()` and reconnect. Detects half-open connections that `close` never fires for.
- Server side: `ws.ping()` (protocol ping, e.g. Node `ws` lib) + terminate clients that miss N pongs. Keep the interval under LB idle timeouts (AWS ALB default 60s, nginx `proxy_read_timeout` 60s).

## socket.io vs raw WS
- socket.io adds: auto-reconnect w/ backoff, heartbeats, rooms, namespaces, acks (`socket.emit('ev', data, cb)`), fallback to HTTP long-polling, and message buffering. Cost: its own protocol (server and client must both be socket.io), bigger payload overhead.
- Raw WS + a small wrapper (or `partysocket`/`reconnecting-websocket`) is fine when you control both ends and don't need rooms/fallback.
- socket.io multi-node needs the Redis adapter (`@socket.io/redis-adapter`) so `io.to(room).emit` reaches sockets on other nodes.

## SSE vs WebSocket
- SSE (`EventSource`): server→client only, plain HTTP (works through more proxies), auto-reconnect built in with `Last-Event-ID` resume, text-only (UTF-8). Ideal: notifications, feeds, LLM token streams.
- Over HTTP/1.1 SSE eats one of ~6 connections per origin; HTTP/2 multiplexing removes that limit.
- WS: bidirectional, binary support, lower per-message overhead. Ideal: chat, games, collaborative editing, high-frequency telemetry up and down.
- If client→server messages are rare, SSE down + `fetch` POST up is simpler and infra-friendlier than WS.

## Message schemas & versioning
- Envelope every message: `{"type":"chat.message","v":1,"id":"ulid","ts":...,"payload":{...}}` — route on `type`, validate payload (zod/JSON Schema) at the boundary.
- Version the protocol at handshake (query param or first message: `{"type":"hello","protocol":2}`), not per-message, unless types evolve independently.
- Evolve additively (new optional fields, new types); unknown `type` must be ignored+logged, never crash the client.
- Include monotonic `seq` per channel so clients detect gaps and request replay/snapshot.

## Auth over WS
- The browser WebSocket API cannot set custom headers — options: short-lived one-time ticket in the query string (`wss://host/ws?ticket=...`, issued via authenticated HTTP, expires in seconds; long-lived tokens in URLs leak into logs), cookie auth (sent automatically on the upgrade request — validate `Origin` to stop cross-site WebSocket hijacking), or first-message auth (`{"type":"auth","token":...}` with a server timeout that closes unauthenticated sockets).
- JWT expiry mid-connection: either close with a custom code prompting re-auth, or support a `token.refresh` message.
- Authorize per-subscription/per-message, not just at connect.

## Scaling
- WS connections are stateful/long-lived: LB must support them (upgrade headers; nginx: `proxy_set_header Upgrade $http_upgrade; Connection "upgrade"; proxy_http_version 1.1`).
- Sticky sessions: required for socket.io when long-polling fallback is enabled (session state per node); pure-WS setups need stickiness only if you keep per-connection state you can't rebuild.
- Fan-out across nodes: pub/sub backbone (Redis pub/sub, NATS, Kafka) — node receives publish, broadcasts to its local sockets.
- Deploys drain connections: send a "reconnect" message, close gracefully (1001), rely on client backoff+resume. Expect mass reconnects — jitter matters.
- Capacity: file-descriptor limits (`ulimit -n`), memory per socket, and heartbeat CPU dominate; measure before assuming 10k+ per node.

## Delivery semantics & client patterns
- WebSocket guarantees ordered delivery per connection while it lives — but nothing across reconnects; idempotency keys (client-generated `id`) let the server dedupe retried sends.
- At-least-once by default when you add retries: make handlers idempotent or dedupe by message `id` on both ends.
- Ack pattern for critical sends: client keeps an outbox keyed by `id`, removes on server ack, retries on reconnect.
- Throttle high-frequency streams client-side: coalesce to one render per `requestAnimationFrame`; for price/telemetry keep only the latest value per key, not a queue.
- SSE resume: server sends `id:` lines; browser auto-reconnects with `Last-Event-ID` header; set `retry: 5000` to control the reconnect delay.
- WebTransport (HTTP/3, Chromium+Firefox): datagrams + multiple streams, no head-of-line blocking — promising, but WS remains the universally supported default; feature-detect before relying on it.

## Gotchas -> Fix
- **Silent dead connection (no `close` event)**: half-open TCP; add heartbeat timeout that force-closes and reconnects.
- **Reconnect storm after deploy**: add full jitter to backoff; stagger server-initiated disconnects.
- **Messages lost during reconnect**: queue outbound while disconnected + server-side replay from `lastSeenId`/`seq`; otherwise fetch a fresh snapshot on reconnect.
- **Works locally, 502/upgrade fails behind proxy**: missing `Upgrade`/`Connection` headers or HTTP/1.0 proxying; fix proxy config (see nginx lines above).
- **Connection drops every 60s exactly**: LB idle timeout; heartbeat interval below it or raise the timeout.
- **`JSON.parse` throws on binary frame**: check `typeof event.data === 'string'` (or `ws.binaryType`) before parsing.
- **Multiple tabs each holding a socket**: share one via `SharedWorker` or elect a leader with `BroadcastChannel` + Web Locks.
- **socket.io rooms empty across nodes**: missing Redis adapter — local-only broadcast.
- **iOS Safari kills sockets in background**: reconnect on `visibilitychange` to visible; don't trust timers in background tabs (throttled to ≥1/min).
