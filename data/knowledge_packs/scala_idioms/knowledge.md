# Scala Idioms

## Values, immutability, basics you reach for first
- `val` = immutable binding (default; prefer always), `var` = mutable (avoid). `def` = method, `lazy val` = computed once on first access.
- Type inference: `val x = 5` infers `Int`; annotate public API return types. Everything is an expression — `if`/`match`/blocks return values; last expression is the result.
- Unified types: `Any` (root), `AnyVal` (`Int`, `Boolean`...), `AnyRef` (objects), `Nothing` (bottom, subtype of all — type of `throw`), `Unit` (`()`, like void).
- String interpolation `s"$x ${a+b}"`, `f"$pi%.2f"` (typed/format), `raw"..."`. Multiline `"""..."""`.

## Case classes & pattern matching
- `case class Point(x: Int, y: Int)` — auto: immutable `val` fields, `equals`/`hashCode` (structural), `toString`, `copy`, companion `apply` (no `new`), pattern-match support (`unapply`).
- `p.copy(y = 3)` for modified copies. `sealed trait Shape` + case classes/objects = exhaustive ADT; `match` warns on non-exhaustive.
```scala
result match {
  case Point(0, 0)        => "origin"
  case Point(x, _) if x>0 => "right"
  case Point(x, y)        => s"$x,$y"
  case _                  => "other"
}
```
- Match on type, tuples, lists (`case head :: tail`, `case Nil`), extract with `@` binding (`case p @ Point(_, 0)`), guards with `if`.

## Option / Either / Try (no nulls)
- `Option[A]` = `Some(a)` | `None` — replaces null. `opt.getOrElse(default)`, `.map`, `.flatMap`, `.fold(ifEmpty)(f)`, `.filter`, `.foreach`. `Option(maybeNull)` wraps nullable Java. Never `.get` (throws on None).
- `Either[L, R]` — `Left` (error) / `Right` (success, right-biased `map`/`flatMap`). For typed errors.
- `Try[A]` = `Success` | `Failure(ex)` — `Try(riskyCall())` captures exceptions functionally; `.recover`, `.toOption`, `.toEither`.
- Chain with `for`-comprehension (below) across the same monad.

## Collections & transformations
- Immutable by default (`scala.collection.immutable`): `List` (linked, prepend O(1)), `Vector` (indexed, balanced), `Map`, `Set`, `Seq`, `LazyList` (lazy). Mutable ones need explicit `import scala.collection.mutable`.
- `map`, `filter`, `flatMap`, `collect` (map+filter with partial fn), `fold`/`foldLeft`/`reduce`, `groupBy`, `partition`, `zip`, `take`/`drop`, `sortBy`, `distinct`, `flatten`, `find`, `exists`, `forall`, `mkString`.
- `xs.foldLeft(0)(_ + _)`; underscore for positional params: `_ + _` == `(a,b) => a+b`. `collect { case Some(x) => x }` filters+unwraps.
- Prepend `x :: list`, append `list :+ x` (O(n) — avoid in loops), concat `a ++ b`.

## for-comprehension (monadic sugar)
- `for { a <- optA; b <- optB if a > 0 } yield a + b` desugars to `flatMap`/`map`/`withFilter`. Works uniformly for `Option`, `Either`, `Try`, `List`, `Future` — anything with `map`/`flatMap`.
- Mixing monad types in one `for` fails to compile — all generators must be the same type constructor.

## Traits (mixin composition)
- `trait` = interface + concrete methods + fields; mix multiple with `extends A with B with C`. Linearization determines `super` order (right-to-left). Stackable modifications via `abstract override`.
- Self-types `this: Dep =>` require a dependency. Traits can't take constructor params before Scala 3 (Scala 3 allows).

## Implicits / givens (Scala 3)
- Scala 3: `given` instances + `using` params replace Scala 2 `implicit`. Type-class pattern:
```scala
trait Show[A] { def show(a: A): String }
given Show[Int] with { def show(a: Int) = a.toString }
def print[A](a: A)(using s: Show[A]) = println(s.show(a))
```
- Extension methods (Scala 3): `extension (s: String) def shout = s.toUpperCase`. Scala 2 used implicit classes.
- `summon[Show[Int]]` fetches a given. Context bounds `def f[A: Show](a: A)` = `(using Show[A])`. Implicit conversions now opt-in (`import scala.language.implicitConversions` / `given Conversion`).

## Future & effects
- `Future[A]` — async, needs `given ExecutionContext`. `.map`/`.flatMap`/`for`, `.recover`, `Future.sequence(list)` to invert `List[Future]`→`Future[List]`. Eager (starts on creation), not referentially transparent.
- Effect systems for pure/lazy async + resource safety: **ZIO** (`ZIO[R, E, A]` — env, typed error, value) and **Cats Effect** `IO`. **Akka** (actor model, `ActorSystem`, message passing, Akka Streams) for concurrency/distribution; Pekko is the open-source fork.

## Functions, methods, classes
- Methods `def add(a: Int, b: Int): Int = a + b`; default + named args `def f(x: Int = 0)`. Multiple param lists (currying) `def f(a: Int)(b: Int)`; last list can be `(using ...)` or a block.
- First-class functions: `val inc = (x: Int) => x + 1`; `list.map(inc)`. Eta-expansion `list.map(f)` lifts a method to a function. Partial application `f(1, _)`.
- `object` = singleton (module/companion); companion object holds "static" members + `apply`/`unapply`. `case object` for singleton ADT cases.
- Scala 3 syntax: optional braces (significant indentation), `enum Color { case Red, Green }` (real enums + ADTs), `given`/`using`, top-level definitions (no wrapping object needed), `extension` methods.

## Scala 3 highlights
- `enum` unifies Java enums + sealed ADTs: `enum Tree[+A] { case Leaf(a: A); case Node(l: Tree[A], r: Tree[A]) }`.
- Union `Int | String` and intersection `A & B` types. Opaque types `opaque type Meters = Double` (zero-cost newtype). `inline` defs + metaprogramming. Match types, `Tuple` improvements.

## Gotchas -> Fix
- `var` in closures / shared mutable state -> prefer `val` + immutable transforms; concurrency bugs otherwise.
- `Option.get` / `head` / `Left.get` throw -> use `getOrElse`/`fold`/pattern match; `headOption`.
- Non-exhaustive `match` (esp. non-`sealed`) fails at runtime with `MatchError` -> seal your ADTs, handle `case _`.
- `==` in Scala calls `equals` (value equality — good, unlike Java `==`); `eq` is reference identity. Case classes get structural `equals` free; regular classes don't (reference equality).
- `List` append `:+` and index access are O(n) — use `Vector` for random access, prepend `::` for lists, or build reversed.
- Integer division `5 / 2 == 2`; `/` truncates. `5.0 / 2`. Watch `Int` overflow (silent wraparound) — use `Long`/`BigInt`.
- `for` without `yield` runs `foreach` (side effects, returns `Unit`) — `yield` builds a collection.
- Implicit resolution ambiguity / not-found errors are cryptic -> import givens explicitly, limit scope, use context bounds.
- `Future` is eager and memoized — creating it starts work immediately; `def` vs `val` for a Future changes when it runs. For laziness/purity use `IO`/`ZIO`.
- Auto-tupling / `apply` overload confusion: `List(1,2,3)` vs `List((1,2))`. Be explicit with tuples.
- Overriding `equals` without `hashCode` breaks `Set`/`Map` — override both (or use case class).
- `null` still exists (Java interop) — wrap boundaries with `Option(...)`; enable explicit-nulls in Scala 3 if desired.
- `map` on `Map` yields tuples; `mapValues` (Scala 2.13 `view.mapValues`) is lazy — force with `.toMap`.
- Type erasure: `case l: List[String]` can't check the type param at runtime (warns) — match structure, not erased generics.
