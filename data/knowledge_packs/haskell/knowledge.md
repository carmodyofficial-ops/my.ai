# Haskell

Pure, lazy, statically-typed functional language. Compiler: **GHC** (via `ghc`, `runghc`, `ghci` REPL). Build: **Cabal** or **Stack**. Formatter: `ormolu`/`fourmolu`; linter: `hlint`.

## Core model
- **Purity**: functions have no side effects; same input -> same output. Effects live in `IO`.
- **Laziness (non-strict)**: expressions evaluated only when forced (WHNF). Enables infinite structures: `take 5 [1..]`, `fibs = 0:1:zipWith (+) fibs (tail fibs)`.
- **Immutability**: no mutation; "update" returns new value. `let x = 5` binds, never reassigns.
- **Referential transparency**: any expression replaceable by its value.
- Function application is space, binds tightest: `f x y` = `(f x) y`. Curried by default: `a -> b -> c` = `a -> (b -> c)`.
- **Partial application**: `add x y = x+y`; `add 3` is a function `Int -> Int`.
- `$` = low-precedence application (drops parens): `print $ 1 + 2`. `.` = composition: `(f . g) x = f (g x)`.

## Types & type classes
- Strong static inference (Hindley–Milner). Annotate top level: `name :: Type`.
- **ADTs**: `data Shape = Circle Double | Rect Double Double`. **Records**: `data P = P { name :: String, age :: Int }` (auto accessor funcs; update `p { age = 30 }`).
- `type` = alias; `newtype` = zero-cost single-field wrapper (distinct type, one constructor).
- **Type classes** = ad-hoc polymorphism (interfaces): `class Eq a where (==) :: a -> a -> Bool`. `instance Eq Bool where ...`. `deriving (Eq, Show, Ord, Enum, Bounded)` auto-generates.
- Constraints in signatures: `sort :: Ord a => [a] -> [a]`.
- Key classes: `Eq`, `Ord`, `Show`/`Read`, `Num`, `Semigroup`/`Monoid` (`<>`, `mempty`), `Foldable`, `Traversable`.

## Maybe / Either — no null, no exceptions for expected failure
- `Maybe a = Nothing | Just a` for optional. `Either e a = Left e | Right a` for error+value (`Left`=error).
- `maybe def f m`, `fromMaybe def m`, `either fe fa`. `lookup k xs :: Maybe v`.

## Functor / Applicative / Monad
- `Functor`: `fmap :: (a->b) -> f a -> f b`, infix `<$>`. Maps inside a context.
- `Applicative`: `pure`, `(<*>) :: f (a->b) -> f a -> f b`. Combine independent effects: `(+) <$> Just 1 <*> Just 2`.
- `Monad`: `(>>=) :: m a -> (a -> m b) -> m b` (bind), `return = pure`. Sequence dependent effects.
- **do-notation** desugars binds:
```haskell
readAge :: IO Int
readAge = do
  putStrLn "age?"      -- IO ()
  line <- getLine      -- x <- m  ==  m >>= \x ->
  pure (read line)
```
- Common monads: `Maybe` (short-circuit on `Nothing`), `Either e`, `[]` (nondeterminism), `IO`, `State`, `Reader`, `Writer`.

## IO monad
- `IO a` = a recipe for an effect producing `a`; nothing runs until in `main`. `main :: IO ()`.
- Sequence with `do`/`>>`. `mapM_ print xs`, `forM_`, `when`, `unless`. There is **no** safe `IO a -> a` (except `unsafePerformIO` — avoid).

## Pattern matching & guards
- Match constructors/literals: `f 0 = ...; f n = ...`. Wildcard `_`. As-patterns `all@(x:xs)`.
- Guards: `f n | n>0 = ...| otherwise = ...`. `case e of {...}`. Non-exhaustive match -> runtime crash.

## Typeclasses vs OOP
- No inheritance/subtyping of data; polymorphism via constraints, not class hierarchies. Dispatch on **return type** possible (`read`, `mempty`) — impossible in most OOP. No mutable object state.

## Monad transformers & effects
- Stack monads to combine effects: `mtl` (`StateT`, `ReaderT`, `ExceptT`, `MaybeT` over a base like `IO`). `ReaderT r IO` is the common app-monad pattern. `lift`/`liftIO` to run a base action inside the stack.
- `MonadIO m => m a` constraints let library code stay base-agnostic.
- Alternatives: `mtl` (type-class based) vs `transformers` (concrete) vs effect systems (`effectful`, `polysemy`, `fused-effects`).

## Records, lenses, deriving
- Classic record fields share a namespace (name clashes across records) -> `DuplicateRecordFields`, `OverloadedRecordDot` (`x.field`, GHC 9.2+), or `lens`/`optics` (`view`, `set`, `over`, `^.`, `.~`, `%~`) for nested access/update.
- `deriving` strategies: `stock` (built-in), `newtype`/`GeneralizedNewtypeDeriving` (reuse wrapped type's instances), `anyclass`, `via` (`DerivingVia`). `StandaloneDeriving`.

## Useful language extensions (`{-# LANGUAGE ... #-}`)
- `OverloadedStrings`, `LambdaCase`, `TupleSections`, `RecordWildCards` (`P{..}`), `ScopedTypeVariables`, `GADTs`, `TypeApplications` (`read @Int s`), `DeriveFunctor`, `BangPatterns`, `MultiParamTypeClasses`, `FlexibleInstances`. Many enabled by `GHC2021`/`GHC2024` defaults.

## Common libraries
- `base`, `containers` (`Map`, `Set`, `Seq`), `unordered-containers` (`HashMap`), `text`/`bytestring` (use over `String`!), `vector`, `mtl` (monad transformers), `aeson` (JSON), `lens`/`optics`, `async`, `stm`, `QuickCheck` (property tests), `hspec`/`tasty`, `servant`/`warp` (web), `conduit`/`streaming` (streaming I/O).

## Tooling & idioms
- `ghcup` installs GHC/cabal/stack/HLS. **HLS** (Haskell Language Server) for IDE. Warnings: `-Wall -Wextra`; treat as errors in CI. `:t`/`:i`/`:k` in GHCi inspect type/info/kind.
- Point-free style with `.`/`<$>` reads well up to a point; don't over-golf. `where` clauses for local helpers. `guard`/`when`/`unless` for conditional effects.
- `Traversable`: `traverse :: (a -> f b) -> t a -> f (t b)`, `mapM = traverse`, `sequenceA` flips `[f a] -> f [a]`.

## Gotchas -> Fix
- **Space leaks from laziness**: unforced thunks accumulate (esp. lazy `foldl`, lazy accumulators) -> use `foldl'` (Data.List), `$!`, `seq`, or `BangPatterns` (`\!acc`); use strict fields `data S = S !Int`.
- **`sum`/`length` on huge lazy lists** blow the heap -> strict fold or `Data.Foldable.foldl'`.
- **Partial functions crash**: `head []`, `fromJust Nothing`, `!!` out of range, non-exhaustive patterns -> use `Maybe`-returning `listToMaybe`, `safe`/`Data.Maybe`, total pattern matches; enable `-Wincomplete-patterns`.
- **`String = [Char]`** is a linked list, slow -> use `Text` (`OverloadedStrings` pragma).
- **Type-inference surprises**: monomorphism restriction gives a top-level binding a fixed type -> add a signature. Ambiguous `Num`/`Show` -> annotate (`(read s :: Int)`).
- **`return` ≠ control flow**: it just wraps a value; code after it still runs in `do`.
- **`<-` vs `let` in do**: `<-` extracts from monad; `let` binds pure value (no `in`).
- **Lazy IO** (`readFile`, `getContents`) can close handles before data is read / hold files open -> use strict `Text.IO`/`ByteString`/conduit/streaming.
- **`show`/`print` require `Show`**; forgetting `deriving Show` -> compile error, not silent.
- **Integer overflow**: `Int` is fixed-width (wraps); `Integer` is arbitrary-precision (slower). Choose deliberately.
- **`==` on `Double`**: floating error; avoid exact equality.
- **`ghci` defaults `Integer`/`Double`** differently than compiled defaults; test with real signatures.
- **Tabs/indentation**: layout rule is whitespace-sensitive; mixing tabs breaks it -> spaces only.
