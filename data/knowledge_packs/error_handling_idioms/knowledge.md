# Error Handling Idioms
## Errors vs expected absence
- "User not found" on a lookup endpoint is a *domain outcome*; "DB connection refused" is an *error*. Model the first in the return type (`Optional`/`Result`/`null`), reserve exceptions for the second. Exceptions for expected outcomes make callers write control flow in `catch` blocks.
- Python: return `None` (typed `X | None`) for expected absence; `dict.get(k)` vs `d[k]`'s `KeyError` is the canonical pair — pick per whether absence is expected at that call site.
- TypeScript: discriminated result unions make failure explicit and exhaustive: `type Result<T,E> = {ok: true; value: T} | {ok: false; error: E}` — `if (!r.ok)` narrows automatically. Throw only for programmer errors and truly exceptional I/O.
- Programmer errors (violated invariants, bad arguments to internal code) should *crash loudly* (assert, `throw new Error`) — never convert them to Result values or retry them.

## Fail fast at boundaries, validate once
- Validate at system edges (HTTP handler, CLI arg parse, message consumer, file load) and convert raw input into typed, validated objects there. Interior code assumes validity — no re-checking the same field in five layers.
- Python: pydantic models / dataclasses at the boundary; interior functions take `User`, not `dict`. TypeScript: zod/valibot `parse()` at the edge; interior takes the inferred type, not `unknown`/`any`.
- Parse, don't validate: prefer functions that *return a narrower type* over ones that return bool — `parse_port(s) -> Port` beats `is_valid_port(s)` because the type system remembers the check.
- Constructors/factories should make invalid states unrepresentable; if `Order` can exist with negative quantity, every reader must re-check it forever.

## Wrap with context when crossing layers
- Each layer catches lower-level errors and rethrows its own vocabulary with the original attached: repository catches `psycopg.OperationalError`, raises `StorageError("fetching user 42") from e`. Callers depend on your abstraction, not your DB driver.
- Python: `raise NewError(msg) from e` preserves the chain (`__cause__`); bare `raise` inside `except` re-raises with the original traceback intact. Never `raise NewError(str(e))` — you lose the traceback.
- TypeScript: `throw new Error("fetching user 42", { cause: e })` (ES2022); log `err.cause` chains recursively. In `catch (e)`, `e` is `unknown` under `useUnknownInCatchVariables`/strict — narrow with `e instanceof Error` before touching `.message`.
- Add *dynamic* context (ids, keys, attempt number) when wrapping; "query failed" tells you nothing, "query failed for tenant=acme id=42" is half the debugging done.

## Gotchas -> Fix
- **Swallowed exception** (`except Exception: pass`, empty `catch {}`): the #1 error-handling bug — failures vanish, corruption proceeds. Fix: handle it, or log-with-traceback *and rethrow*; catching only to log at every layer produces the same trace 5 times — log at the top-level handler, wrap below.
- **`except Exception` catches too much**: also nets `KeyboardInterrupt`? No — but it does net bugs like `TypeError`/`AttributeError`, hiding programmer errors. Fix: catch the *specific* exceptions the operation documents; keep one broad handler only at the process top level.
- **Retry storm makes outage worse**: naive retry loops amplify load. Fix: exponential backoff with jitter (`sleep(min(cap, base*2**attempt) * random())`), a max-attempt budget, and retry only *retryable* classes (timeouts, 429/503 — never 400/422).
- **Retried a non-idempotent operation, charged customer twice**: retries REQUIRE idempotency. Fix: idempotency keys on writes, or make the operation naturally idempotent (PUT semantics, upsert) before adding any retry.
- **`finally` swallows the real error**: a `return` or `raise` inside `finally` replaces the in-flight exception. Fix: never `return`/`raise` in `finally`; cleanup only.
- **Stack trace leaked to end user**: internal messages expose paths, SQL, versions. Fix: two-message discipline — user-facing text is stable, actionable, no internals ("Payment failed, try another card. Ref: 7f3a"), with a correlation id linking to the full internal log line.
- **Error message without inputs**: "invalid value" — which value? Fix: message template = what failed + offending value (repr, truncated/redacted) + expected shape.
- **Async error escapes**: unawaited promise / fire-and-forget task drops its exception. Fix: `no-floating-promises` lint; `process.on('unhandledRejection')` as a backstop that crashes; in Python, keep task references and `task.add_done_callback` that logs, or use `asyncio.TaskGroup`.

## Python specifics
- Custom exceptions: one module-level base (`class AppError(Exception)`) with subclasses per category (`ConfigError`, `StorageError`); callers can catch broad or narrow. Give them structured fields, not just a message string.
- `try/except/else/finally`: put only the risky statement in `try`; success-path code goes in `else` so its own exceptions aren't miscaught; `finally` for cleanup (or better, a context manager / `contextlib.ExitStack`).
- `ExceptionGroup` (3.11+): concurrent branches can fail together; `except*` matches inside groups — `except* ValueError as eg:` handles those members and re-raises the rest. `asyncio.TaskGroup` raises these natively.
- `logging.exception(msg)` inside an `except` block logs message + traceback in one call — use it, not `logging.error(str(e))`.

## TypeScript specifics
- `Error.cause` chains + a small `toErrorChain(e)` logger; `AggregateError` from `Promise.any`.
- `Promise.allSettled` when partial failure is acceptable; `Promise.all` rejects on first failure and *abandons* (does not cancel) the rest.
- Narrowing helper for `catch (e: unknown)`: `const err = e instanceof Error ? e : new Error(String(e))` — third-party code throws strings and objects.
- `AbortController` for timeout/cancellation; treat `AbortError` as expected outcome, not failure.
- `fetch` does NOT reject on HTTP 4xx/5xx — only on network failure; check `res.ok` explicitly or every handler silently treats a 500 body as data.

## Patterns worth naming
- Circuit breaker in front of flaky dependencies: after N consecutive failures, fail fast for a cooldown window instead of stacking timeouts; half-open probe restores traffic. Retries handle blips; breakers handle outages.
- Timeout everything that crosses a network: unbounded waits are the default in most clients (`requests` has NO default timeout — always pass `timeout=`); a hung dependency without timeouts becomes your outage.
- Error taxonomy for services: 4xx = caller's fault (don't retry, don't page), 5xx = your fault (retryable, alert); map internal exception classes to this split in ONE top-level handler, not per-route.
- Cleanup belongs to context managers/RAII, not scattered try/finally: `with open(...)`, `async with client:`, `using`/`await using` (TS 5.2 explicit resource management) — the resource can't leak on an exception path you forgot.
- Partial failure reporting for batch operations: return per-item results (`succeeded: [...], failed: [{id, reason}]`), never all-or-nothing silence — callers need to know *which* items to retry.
- Assertions vs error handling: `assert` documents invariants and may be stripped (`python -O` removes them) — never use assert for input validation or security checks; raise a real exception.
- Log once rule: an error should produce exactly one ERROR-level line with full context and traceback at the layer that *handles* it; layers that merely pass it upward add context via wrapping, not logging.
