# Debugging Methodology
## Repro first
- No fix without a reproduction. An unreproduced "fix" is a guess wearing a commit message — you can't verify it worked.
- Minimal repro construction: start from the failing case and *delete* — halve the input, drop config, stub dependencies — re-running after each cut. Stop when any further deletion makes the bug vanish. A 5-line repro is worth an hour of log-reading.
- Pin everything the bug might depend on: seed RNG, freeze time (`freezegun`, fake timers), fix locale/TZ, record the exact input. "Sometimes fails" usually means an unpinned variable.
- Turn the repro into a failing test *before* fixing; the test is the proof and the regression guard.

## Bisect
- Input bisection: delete half the data/config; bug gone -> it was in the deleted half. O(log n) beats staring.
- Commit bisection: `git bisect start; git bisect bad; git bisect good <last-known-good>` then test each checkout; automate with `git bisect run pytest -x tests/test_repro.py`. Needs a deterministic repro and buildable intermediate commits — `git bisect skip` for broken ones.
- Code-path bisection: add one assert/log at the midpoint of the suspect flow ("is the data still correct HERE?"), then recurse into the bad half. Find *where* corruption enters, not where it explodes.
- One variable at a time; write down what you ruled out — re-testing ruled-out causes is the biggest time sink.

## Hypothesis loop
- Loop: observe -> form ONE falsifiable hypothesis -> design the cheapest experiment that could disprove it -> run -> record result -> repeat. If you can't state what output would disprove your hypothesis, it's not a hypothesis.
- Surprise is signal: when an experiment result confuses you, your mental model is wrong somewhere upstream — chase the confusion, don't dismiss it as a fluke.
- Rubber ducking: explain the bug out loud/in writing to no one, line by line, including "obviously correct" parts — the bug is usually in a sentence that starts with "obviously".

## Stack traces
- Python prints the trace with the *innermost* frame LAST — read Python traces bottom-up: last line = exception type + message, frames above = how you got there. `raise ... from e` chains show the root cause under "The above exception was the direct cause".
- JS/TS/JVM print the innermost frame FIRST — read top-down. First frame *in your code* (skip framework/node_modules frames) is where to look.
- The trace shows where the error *surfaced*, not where the bad state was *created* — for "NoneType has no attribute X" / "undefined is not a function", ask "who set this to None/undefined?" and bisect backwards.
- Async traces lose the causal chain at await points; enable long stack traces where available (`--async-stack-traces` is default in modern Node; Python `asyncio` debug mode: `PYTHONASYNCIODEBUG=1`).

## Print vs debugger vs tracing
- Prints/logs: best for time-distributed bugs (what happened across a whole run), concurrency, remote/prod. Print *values and identities* (`id(obj)`, timestamps), not "got here".
- Debugger: best for state-rich single moments — inspect everything at one breakpoint, walk up frames. `python -m pdb -c continue script.py` drops you at the crash; `breakpoint()` inline; VSCode/Chrome DevTools conditional breakpoints beat 20 prints.
- Tracing/instrumentation: best when you don't know where to look — `strace`/`ltrace` for syscalls, `py-spy dump` for a hung Python process's live stacks, `node --inspect` + CPU profile for "it's slow", DEBUG-level logging you can flip on via env var.
- Rule of thumb: unknown *where* -> tracing; known where, unknown *state* -> debugger; unknown *when/how often* -> logs.

## Gotchas -> Fix
- **Heisenbug vanishes with prints/debugger**: timing-dependent — race, uninitialized memory, or buffering change. Fix: log to an in-memory ring buffer flushed on crash; audit shared mutable state; try thread/race sanitizers.
- **Off-by-one**: signatures — last item missing, first item doubled, `IndexError`/`undefined` at boundary, infinite loop at n=0. Fix: check `<` vs `<=`, inclusive vs exclusive ends (Python slices are half-open), and test n=0, n=1, n=max explicitly.
- **Mutation aliasing**: "who changed my list?!" — two names, one object. Signatures: default mutable arg (`def f(x=[])`), dict/list shared across calls, `a = b` then mutating `b`. Fix: `copy.deepcopy` at the boundary, freeze (`tuple`, `frozenset`, `Object.freeze`, `readonly`), or find the alias with `id()`/reference-equality checks.
- **Async race**: signatures — passes alone, fails in suite; fails under load; order-dependent results; "works with sleep(1)". Fix: never fix with sleeps — await the actual condition; look for check-then-act gaps and unawaited promises (`no-floating-promises` lint; Python warns "coroutine was never awaited").
- **Stale cache/state**: signatures — fix deployed but old behavior persists; correct in incognito; works after restart. Fix: bust every layer deliberately (browser, CDN, memoization, `__pycache__`, Docker layer, `node_modules`); add a version/build stamp to output so staleness is visible.
- **Works on my machine**: env drift. Fix: diff env var dumps, lockfile-installed versions (`pip freeze`, `npm ls`), TZ/locale, CPU arch; reproduce inside the CI container.
- **Bug disappears after "unrelated" change**: it didn't — you shifted memory layout/timing. Treat as still live: find the mechanism before closing.
- **Fixed the symptom, not the cause**: null-check added where it crashed, corruption still upstream. Fix: apply "5 whys" until you reach a decision or invariant violation, and fix *there*; keep the downstream check as an assert.

## Discipline
- Change one thing per experiment; `git stash` speculative edits before testing a new hypothesis.
- Timebox: stuck 30+ min with no new information -> write the summary you'd post to ask for help; writing it usually finds the bug.
- After the fix: add the regression test, note the root cause in the commit body, and grep for the same pattern elsewhere — bugs travel in herds.
- Read the error message. All of it. Twice. The filename, line number, and offending value are usually right there; skimming past them to start guessing is the most common self-inflicted delay.
- Check the dumb things first, in order: is the file saved, is the right process running, are you on the branch/env you think, did the change actually deploy, is the cache cleared. Two minutes here saves two hours of sophisticated hypothesizing about code that isn't even executing.
- Differential debugging: when you have a working case and a broken case, diff *everything* between them — inputs, env, versions, logs side by side — and shrink the diff until one difference remains. Often faster than reasoning from first principles.
- Binary logging trick for prod-only bugs: log entry/exit + args of the suspect function behind an env-var flag; flip it on for one request, off again — targeted evidence without a redeploy of print statements.
