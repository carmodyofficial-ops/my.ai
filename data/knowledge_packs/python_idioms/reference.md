# Python Idioms & Gotchas

## Stdlib reach-for
- `enumerate`, `zip`, `sorted`, `reversed`, `any`/`all`, `sum(xs, start)`, `min`/`max(xs, key=, default=)`, `filter`/`map` (prefer comprehensions).
- `collections`: `defaultdict`, `Counter`, `deque`, `namedtuple`/`OrderedDict` (mostly superseded). `itertools`, `functools`, `heapq` (priority queue: `heappush`/`heappop`, min-heap), `bisect` (sorted insert/search O(log n)), `statistics`, `datetime`/`zoneinfo`, `json`, `dataclasses`, `enum` (`class Color(Enum): RED = 1`).

## Core idioms
- Loop with `for i, x in enumerate(seq):`; pair via `for a, b in zip(xs, ys):` (use `zip(..., strict=True)` 3.10+ to catch length mismatch); lockstep dict: `for k, v in d.items():`.
- Unpack: `a, b = b, a`; `first, *rest = items`; `*init, last = items`; `name, _ = pair`.
- f-strings: `f"{x=}"` debug repr, `f"{n:,.2f}"` thousands+2dp, `f"{n:>8}"` pad, `f"{x!r}"` repr. Build strings with `"".join(parts)`, not `+=` in a loop (O(n²)).
- `if x is None:` / `is not None` — never `== None`. Empty check: `if not seq:` (works for `""`, `[]`, `{}`, `0`).
- Comprehension over `map`/`filter`: `[f(x) for x in xs if p(x)]`; `{k: v for ...}`; `{x for ...}`. Use `(... for ...)` generator for large/streamed data (lazy, O(1) memory). Nested order matches for-loop order: `[y for row in grid for y in row]`.
- EAFP: `try: v = d[k] except KeyError:` beats pre-checking (LBYL races). Catch specific exceptions, never bare `except:`.
- `with open(p) as f:` always; closes on error. Multiple: `with a() as x, b() as y:` or `contextlib.ExitStack` for dynamic N.
- `pathlib`: `Path(p).read_text()`, `p / "sub"`, `p.glob("*.py")`, `p.stem`, `p.with_suffix(".bak")` over `os.path`.
- `@dataclass` for plain data; `collections`: `defaultdict(list)`, `Counter(xs).most_common(3)`, `deque(maxlen=n)` (ring buffer, O(1) both ends).
- `d.get(k, default)`; `d.setdefault(k, []).append(v)`; merge `d1 | d2` (3.9+), update `d1 |= d2`.
- `sorted(xs, key=lambda r: (r.a, -r.b))` — stable sort; decorate with tuple keys for multi-field.

## Data model / dunders
- `__repr__` (unambiguous, dev) always; `__str__` (readable) optional. `__eq__` + `__hash__` together (define both or neither; `@dataclass(frozen=True)` gives both).
- `__iter__`/`__next__` make an iterator; `__getitem__`+`__len__` enable indexing/`in`. `__contains__` for custom `in`.
- `__enter__`/`__exit__` = context manager; `__call__` = callable instance. `__slots__ = ("x","y")` drops `__dict__` → less memory, faster attr access, blocks new attrs.
- Ordering: define `__lt__` + `@functools.total_ordering` to derive the rest.

## Iterators / itertools / generators
- Generator: `def gen(): yield x` — lazy, resumable. `yield from sub()` delegates. Generators are single-use (exhausted after one pass).
- `itertools`: `chain(a, b)`, `islice(it, 5)`, `groupby(sorted(xs, key=k), key=k)` (requires pre-sort!), `product`, `combinations`, `count`, `cycle`, `accumulate`, `pairwise` (3.10+).
- `next(it, default)` avoids `StopIteration`. `any(...)`/`all(...)` short-circuit over generators.

## Typing
- `list[int]`, `dict[str, int]`, `int | None` (3.10+; else `Optional[int]`), `tuple[int, ...]` (variadic), `Callable[[int], str]`.
- `Protocol` = structural/duck typing: `class Reader(Protocol): def read(self) -> bytes: ...` — no inheritance needed.
- `TypedDict` for dict shapes; `NewType("UserId", int)` for nominal ints; `Literal["r","w"]`; `Final`; `TypeVar("T")` + `Generic[T]`; `Self` (3.11+) for fluent returns.
- Runtime checks: `if TYPE_CHECKING:` for import-only-for-typing; `typing.cast(T, x)` is a no-op hint.

## Concurrency (GIL)
- CPython GIL serializes bytecode → threads don't speed up CPU work. Use **threads** for blocking I/O, **asyncio** for many concurrent I/O tasks (single thread), **multiprocessing** for CPU-bound (separate interpreters, real parallelism). (3.13+ has experimental free-threaded build.)
- `concurrent.futures.ThreadPoolExecutor` / `ProcessPoolExecutor` + `.map`/`.submit` for pools.

## asyncio
- `async def` coroutine; `await` yields control. `asyncio.run(main())` at top level.
- Concurrency: `await asyncio.gather(*tasks)` (all, fails fast), `asyncio.TaskGroup` (3.11+, structured, cancels siblings on error). Fire-and-track: `t = asyncio.create_task(coro())`.
- `asyncio.wait_for(coro, timeout)`; `async with`, `async for`.
- Pitfalls: never call blocking/CPU code in a coroutine — it stalls the loop; offload via `await asyncio.to_thread(fn, ...)`. A bare `create_task` whose result is never awaited can swallow exceptions and be GC'd — hold a reference.

## Decorators / functools
- `@functools.wraps(fn)` inside a decorator preserves `__name__`/`__doc__`. `@functools.lru_cache(maxsize=None)` / `@cache` (3.9+) memoize (args must be hashable). `@cached_property` per-instance lazy value.
- `functools.partial(fn, arg)` pre-binds; `functools.reduce(op, xs, init)`; `@singledispatch` for type-dispatched functions.

## Pattern matching (3.10+)
```python
match cmd:
    case ["go", ("n"|"s") as d]: move(d)
    case {"type": "pt", "x": x, "y": y}: ...
    case Point(x=0, y=y): ...          # class patterns
    case [first, *rest]: ...
    case _: ...                        # default
```
- Bare names bind (capture); use dotted `Color.RED` or guards `case n if n>0:` to match values.

## Context managers
- Custom: implement `__enter__`/`__exit__`, or `@contextlib.contextmanager` on a generator (`yield` the resource; code after `yield` is teardown, wrap in `try/finally`).
- `contextlib.suppress(FileNotFoundError)` swallows chosen exceptions; `contextlib.closing(x)` calls `.close()`; `ExitStack` composes a dynamic number of CMs. `__exit__` returning truthy suppresses the exception.

## Dataclasses / attrs
- `@dataclass` auto-generates `__init__`/`__repr__`/`__eq__`. `field(default_factory=list)` for mutable defaults (never `= []` in a dataclass — same trap). `@dataclass(frozen=True)` → immutable + hashable; `(slots=True)` (3.10+) → `__slots__`; `(order=True)` → comparison dunders; `(kw_only=True)` forces keyword args.
- `__post_init__(self)` for derived/validated fields. `attrs`/`pydantic` add validation and coercion beyond stdlib dataclasses.

## Packaging
- `pyproject.toml` `[project]` table is the standard (PEP 621) — name, version, dependencies, `[project.scripts]` entry points. `python -m venv .venv` + `source .venv/bin/activate`. Prefer `uv`/`pip install -e .` for editable dev installs. Pin transitive deps with a lockfile (`uv.lock`/`requirements.txt`). `python -m module` runs a package's `__main__.py`.

## Strings / bytes
- `str` is Unicode text; `bytes` is raw octets — never mix. Encode/decode at I/O boundaries: `s.encode("utf-8")`, `b.decode("utf-8")`. `str.format_map`, `str.translate`, `str.removeprefix`/`removesuffix` (3.9+). Slicing is by code point, not byte.
- Regex: compile once `re.compile(...)`; use raw strings `r"\d+"`. `re.finditer` for streaming matches.

## Performance idioms
- Local var lookup beats attribute/global (hoist `m = obj.method` out of hot loops). Prefer built-ins (`sum`, `map`, `any`) and comprehensions — they run in C. `set`/`dict` membership is O(1) vs list O(n). `bytes`/`bytearray` for binary; `array`/`memoryview` to avoid copies. Generators keep memory O(1) for pipelines. `functools.lru_cache` for pure repeated calls. Profile with `cProfile`/`timeit` before optimizing — don't guess.
- `__slots__` cuts per-instance memory dramatically for many small objects. `sys.intern(s)` for many repeated string keys.

## Gotchas → fix
- **Mutable default**: `def f(x=[])` shares one list across all calls (default evaluated once at def time) → `def f(x=None): x = [] if x is None else x`.
- **Late-binding closure**: `[lambda: i for i in r]` all return last `i` → bind now: `lambda i=i: i`.
- **`is` vs `==`**: `is` checks identity; use `==` for value. `x is 3` is a bug (works only via CPython small-int cache -5..256; fails for larger ints/strings).
- **Mutating while iterating**: `for x in lst: lst.remove(x)` skips items → iterate `lst[:]` copy or build a new list. Same for dict — don't add/del keys mid-iteration.
- **Shallow copy**: `b = a[:]` / `a.copy()` / `dict(d)` copy one level; nested objects still shared → `copy.deepcopy(a)`.
- **Bare `except:`** hides bugs and swallows `KeyboardInterrupt`/`SystemExit` → `except Exception as e:` and log `e`. Preserve cause with `raise New() from e`; `raise ... from None` suppresses chaining.
- **Integer/float**: `/` always float; use `//` floor, `%` remainder. `0.1 + 0.2 != 0.3` → `math.isclose(a, b)` or `decimal.Decimal` for money.
- **Truthiness trap**: `if x:` is false for `0`, `0.0`, `""`, `[]` — use `if x is not None:` when 0/empty are valid.
- **Default `dict`/`Counter` mutation**: `defaultdict` creates keys on read access (`d[k]` inserts) — use `.get` to peek without inserting.
- **Logging**: `log.info("got %s", x)` (lazy %-format), not `log.info(f"got {x}")` (always formats even when suppressed).
- **`==` on floats/`nan`**: `nan != nan`; `x is nan` is False — test with `math.isnan(x)`.
- **Chained comparison**: `a < b < c` is fine, but `a == b == c` means `a==b and b==c`, not `(a==b)==c`.
- **`+= ` on shared list**: `a = b = []` then `a += [1]` mutates both (same object); `a = a + [1]` rebinds.
