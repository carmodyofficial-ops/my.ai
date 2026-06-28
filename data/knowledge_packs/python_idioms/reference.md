# Python Idioms & Gotchas

## Core idioms
- Loop with `for i, x in enumerate(seq):`; pair via `for a, b in zip(xs, ys):`.
- Unpack: `a, b = b, a`; `first, *rest = items`; `name, _ = pair`.
- f-strings: `f"{x=}"` debug, `f"{n:,.2f}"` format. Build strings with `"".join(parts)`, not `+=`.
- `if x is None:` / `is not None` — never `== None`. Empty check: `if not seq:`.
- Comprehension over `map`/`filter`: `[f(x) for x in xs if p(x)]`; `{k: v for ...}`; `{x for ...}`. Use a `(... for ...)` generator for large/streamed data.
- EAFP: `try: v = d[k] except KeyError:` beats pre-checking. Catch specific exceptions, never bare `except:`.
- `with open(p) as f:` always; closes on error.
- `pathlib`: `Path(p).read_text()`, `p / "sub"`, `p.glob("*.py")` over `os.path`.
- `@dataclass` for plain data: `@dataclass` / `class P: x: int; y: int = 0`.
- Types: `list[int]`, `dict[str, int]`, `int | None`, `Optional[X]`.
- `collections`: `defaultdict(list)`, `Counter(xs).most_common(3)`, `deque(maxlen=n)`.
- `d.get(k, default)`; `d.setdefault(k, []).append(v)`.
- `sorted(xs, key=lambda r: (r.a, -r.b))`.
- `def f(*args, **kwargs):` to forward; call with `f(*lst, **dct)`.
- Walrus: `while (line := f.readline()):` / `if (m := re.match(...)):`.

## Gotchas → fix
- Mutable default: `def f(x=[])` shares list across calls → `def f(x=None): x = x or []`.
- Late-binding closure: `[lambda: i for i in r]` all see last `i` → `lambda i=i: i`.
- `is` vs `==`: `is` checks identity; use `==` for values (`x == 3`, not `x is 3`).
- Mutating while iterating: `for x in lst: lst.remove(x)` skips items → iterate `lst[:]` or build a new list.
- Division: `/` always float; use `//` for floor int, `%` remainder.
- Copy: `b = a[:]`/`a.copy()` is shallow; nested needs `copy.deepcopy(a)`.
- Bare `except:` hides bugs/Ctrl-C → `except Exception as e:` and log `e`.
- Logging: `log.info("got %s", x)` (lazy), not `log.info(f"got {x}")`.
- `0.1 + 0.2 != 0.3` → use `math.isclose`.
