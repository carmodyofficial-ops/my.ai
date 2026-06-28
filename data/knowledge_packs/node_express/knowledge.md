# Node.js + Express Reference

## Node Core
- **async/await**, never callbacks. Wrap awaits in `try/catch`; no floating promises (`void p` or `await`).
- Event loop is **single-threaded — never block it**: no `fs.readFileSync`, no tight CPU loops. Offload CPU to `worker_threads`; use async fs/`crypto`.
- **Streams** for large data — they handle backpressure: `pipeline(src, transform, dest)`.
- **ESM** `import` (`"type":"module"`) vs **CJS** `require`. Pick one per project.
- Config via `process.env` (validate at boot, fail fast). Never hardcode secrets.
- **Graceful shutdown**: `process.on('SIGTERM', () => server.close(done))`.

```js
process.on('unhandledRejection', e => { log(e); process.exit(1); });
```

## Express
- `app.use(express.json())` to parse JSON bodies (else `req.body` is undefined).
- **Middleware runs top-down — order matters.** Register routes after parsers, security before routes.
- Access `req.params`, `req.query`, `req.body`, `req.headers`.
- `helmet()` + `express-rate-limit` early. Validate/sanitize all input (zod/express-validator).
- **Always `return` after `res.send`/`res.json`** — else code continues -> "headers already sent".

## Async route errors
Express 4 does **not** catch async throws. Pass to `next` or wrap:
```js
const wrap = fn => (req,res,next) => Promise.resolve(fn(req,res,next)).catch(next);
app.get('/u/:id', wrap(async (req,res) => {
  const u = await db.find(req.params.id);
  if (!u) return res.status(404).json({error:'not found'});
  res.json(u);
}));
```

## Error middleware — register LAST, 4 args
```js
app.use((err, req, res, next) => {
  log(err);                                  // log full detail
  res.status(err.status||500).json({error:'Internal'}); // leak nothing
});
```

## Gotchas -> Fix
- Unhandled rejection crashes -> `try/catch` + handler.
- Blocking loop -> `worker_threads`/async.
- Callback hell -> async/await.
- Async err not caught -> `wrap`/`next(err)`.
- No `return` after response -> add `return`.
- No validation -> schema-validate.
- Leaking stack to client -> generic message, log internally.
