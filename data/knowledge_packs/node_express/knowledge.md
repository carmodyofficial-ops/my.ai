# Node.js + Express

## Middleware order (top-down — order is the program)
- Register in order: `helmet()` → CORS → rate limit → `express.json({limit:'1mb'})` / `express.urlencoded({extended:true})` → auth → routes → 404 handler → **error handler LAST**.
- `app.use(express.json())` or `req.body` is `undefined`. Set an explicit body `limit` (default 100kb) — unlimited bodies are a DoS vector.
- **Always `return` after `res.send`/`res.json`** — else code keeps running → "Cannot set headers after they are sent".
- Middleware must call `next()` or respond; doing neither hangs the request forever.
- `req.params` (route `:id`), `req.query` (strings/arrays — never trust types), `req.body`, `req.headers` (lowercased keys).

## Async route errors
- Express 4 does **not** catch async throws — request hangs or process dies. Express 5 forwards rejected promises to the error handler automatically. On 4, wrap:
```js
const wrap = fn => (req,res,next) => Promise.resolve(fn(req,res,next)).catch(next);
app.get('/u/:id', wrap(async (req,res) => {
  const u = await db.find(req.params.id);
  if (!u) return res.status(404).json({error:'not found'});
  res.json(u);
}));
```
- Error middleware = exactly **4 args**, registered last:
```js
app.use((err, req, res, next) => {
  log(err);                                              // full detail internally
  res.status(err.status || 500).json({error:'internal'}); // leak nothing
});
```
- Sync throws in middleware are caught by Express; `next(err)` skips to error handlers.

## Routers & structure
- `const r = express.Router(); r.get('/', list); app.use('/users', r)` — mount per resource; paths inside the router are relative to the mount.
- Router-level middleware: `r.use(requireAuth)` applies to that router only. `mergeParams: true` to read parent `:params` in nested routers.
- Route order matters: `/users/me` must be declared **before** `/users/:id`.
- Validate input at the edge (zod/express-validator) before handlers; coerce `req.query` strings explicitly (`Number(req.query.page)` + `Number.isFinite` check).

## Node core rules
- Event loop is single-threaded — **never block**: no `fs.readFileSync`/`execSync`/`JSON.parse` of huge payloads in handlers; CPU work → `worker_threads`; use `crypto`'s async forms.
- **Streams** for large data (they handle backpressure): `await pipeline(req, transform, res)` from `stream/promises` — never `.pipe()` chains without error handling (they leak on error).
- `res` is a writable stream: stream files with `pipeline(createReadStream(p), res)`, not `readFile` into memory.
- ESM (`"type":"module"`, `import`) vs CJS (`require`) — pick one per project; ESM needs file extensions in relative imports.
- `async/await` everywhere; no floating promises — `await` it, `.catch()` it, or explicitly `void` with a comment.

## Config & env
- Read config once at boot into a validated object; **fail fast** on missing vars: `const PORT = Number(process.env.PORT); if (!Number.isFinite(PORT)) throw ...` (zod `envSchema.parse(process.env)` is the clean version).
- `process.env` values are always **strings**: `"false"` is truthy — parse booleans/numbers explicitly.
- Never hardcode secrets; never log the env object. `.env` via `dotenv` for dev only; real env in prod.
- `NODE_ENV=production` enables Express perf paths (view cache etc.); set it in prod.

## Security middleware
- `helmet()` sets safe headers (CSP, noSniff, frameguard). Configure CSP explicitly for real apps.
- CORS: `cors({origin: ['https://app.example.com'], credentials: true})` — never `origin: '*'` with credentials (browsers reject; wildcard also over-exposes).
- `express-rate-limit` on auth + expensive routes. `app.set('trust proxy', 1)` behind a proxy or `req.ip`/secure cookies/rate limits key on the proxy IP.
- Disable fingerprinting: `app.disable('x-powered-by')` (helmet does this).

## Production gotchas
- **Unhandled rejection** kills the process (Node ≥15). Last-resort logging then exit:
```js
process.on('unhandledRejection', e => { log(e); process.exit(1); });
process.on('uncaughtException', e => { log(e); process.exit(1); }); // state is corrupt — restart
```
- **EADDRINUSE** → old process still bound: `lsof -i :3000` / `fuser -k 3000/tcp`; in tests, use port `0` (ephemeral) and read `server.address().port`.
- **Graceful shutdown**: `process.on('SIGTERM', () => server.close(() => process.exit(0)))`; also close DB pools; add a hard-exit timeout.
- Timeouts: Node's `server.headersTimeout`/`requestTimeout` guard slowloris; set client timeouts on outbound `fetch`/HTTP (default is none/very long).
- One Node process = one core: use a process manager (systemd, pm2, container orchestrator) + `cluster` or N replicas behind a load balancer.
- Health endpoint (`GET /healthz` returning 200 + dependency checks) for orchestrators; keep it unauthenticated but cheap.
- Log JSON lines to stdout (pino); never `console.log` objects in hot paths (sync + slow).
- DB connections: one pool created at boot, shared via module import — never a new connection per request; size the pool below the DB's max; release/close on shutdown.
- Memory: watch RSS + heap in metrics; `--max-old-space-size` must fit the container limit or the OOM killer strikes before V8 GC pressure shows.

## Serving, uploads, cookies
- Static files: `app.use(express.static('public', {maxAge: '1d', etag: true}))`; behind a CDN in prod. `compression()` for dynamic responses (CDN/proxy can also do it).
- Multipart uploads: `multer({limits: {fileSize: 5*1024*1024, files: 1}})` — always set limits; store to disk/S3, not memory, for large files.
- Cookies: `res.cookie('sid', v, {httpOnly: true, secure: true, sameSite: 'lax', signed: true})` with `cookie-parser` secret; session state in Redis (`connect-redis`), not default MemoryStore (leaks, single-process).
- `res.status(302).redirect(url)` — allowlist targets; never redirect to raw `req.query.next`.

## Testing & debugging
- `supertest(app)` hits the app without binding a port: `await request(app).get('/u/1').expect(200)`.
- Export `app` separately from the `listen` call so tests import the app, not the server.
- Debug: `NODE_OPTIONS=--inspect`, `node --inspect-brk`; `DEBUG=express:*` traces routing/middleware order.
- Catch leaks in CI: `--detect-open-handles` (jest) for unclosed servers/pools/timers.

## Gotchas -> Fix
- **Async throw hangs request (Express 4)** → `wrap()` every async handler or upgrade to Express 5.
- **Headers already sent** → `return` after every response; one response per request path.
- **Error handler never runs** → it must have 4 params `(err, req, res, next)` and be registered after routes.
- **`req.body` undefined** → `express.json()` before routes; check `Content-Type: application/json` on the client.
- **Blocking the loop** (sync fs/crypto/big JSON) → async APIs, `worker_threads`, streaming parse.
- **Floating promise swallows error** → always await/catch; enable `no-floating-promises` lint.
- **Memory balloon on uploads/downloads** → stream with `pipeline`, set body limits, use `busboy`/`multer` limits for multipart.
- **Stale process on port (EADDRINUSE)** → kill old PID; ephemeral port in tests; idempotent start scripts.
- **Wrong client IP / rate-limit useless behind proxy** → `trust proxy` set correctly (and only when actually behind one).
- **Secrets in logs** → redact (pino `redact`), never log headers/env wholesale.
- **`.pipe()` without error handling leaks fds** → `stream/promises` `pipeline`.
- **Leaking stack traces to clients** → generic message out, full error to logs only.
