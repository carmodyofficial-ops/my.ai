# Clojure

A Lisp on the JVM: dynamic, functional, immutable-by-default, with strong Java interop and a REPL-driven workflow. Everything is data (homoiconic). Build/deps: `deps.edn` (tools.deps) or Leiningen (`lein`). ClojureScript compiles to JS.

## Syntax (s-expressions)
- Code is lists: `(fn arg1 arg2)` — operator first (prefix). `(+ 1 2 3)` -> 6.
- Literals: `[1 2 3]` vector, `{:a 1 :b 2}` map, `#{1 2}` set, `'(1 2)` list, `:kw` keyword, `"str"`, `nil`, `\c` char.
- `defn` defines a function, `def` a var, `let` local bindings `(let [x 1 y 2] ...)`, `fn`/`#(...)` anonymous (`%` `%1` args).
- Commas are whitespace (optional). `;` line comment, `#_` skip next form, `(comment ...)`.

## Immutable persistent data structures
- Lists, vectors, maps, sets are **immutable**; "updates" (`conj`, `assoc`, `dissoc`, `update`, `into`) return new structures sharing structure (persistent, O(log32 n)) — cheap, thread-safe.
- Value equality by default (`=`), structural. Data is the interface — pass maps, not objects.

## Functions & higher-order
- First-class: `map`, `filter`, `reduce`, `apply`, `comp`, `partial`, `juxt`, `->>`/`->` (threading macros). `(->> coll (map f) (filter g) (reduce +))` reads top-to-bottom.
- Multi-arity: `(defn f ([x] ...) ([x y] ...))`. Variadic `[& args]`. Multimethods `defmulti`/`defmethod` (dispatch on any fn); protocols `defprotocol`/`defrecord` (fast polymorphism, Java-interface-like).

## Seq abstraction & laziness
- Uniform `seq` interface over all collections; `first`/`rest`/`cons`/`next`. Most seq fns (`map`/`filter`/`range`/`iterate`) are **lazy** — realized on demand, chunked in ~32-element batches.
- Force: `doall` (realize + retain), `dorun` (realize, discard), `into`/`vec`, `reduce`. `(take 5 (map inc (range)))` works on infinite seqs.
- **Transducers**: composable, collection-agnostic transformations (`(comp (map inc) (filter odd?))`) via `transduce`/`into` — no intermediate seqs.

## Destructuring
- Vector: `(let [[a b & rest] coll] ...)`. Map: `(let [{:keys [x y] :or {y 0}} m] ...)`, `{name :name}`, `:as whole`. Works in `defn` params too.

## State: atoms / refs / agents
- **Values are immutable; identities are managed reference types.**
- `atom`: uncoordinated sync state. `(swap! a inc)`, `(reset! a v)`, deref `@a`. CAS-based.
- `ref` + **STM**: coordinated sync change of multiple refs in `(dosync (alter r1 ...) (alter r2 ...))` — transactional, retries automatically. `commute` for commutative ops.
- `agent`: async, uncoordinated. `(send a f)` / `send-off`; state applied on a thread pool.
- `var` with `binding` for dynamic (thread-local) rebinding of `^:dynamic` vars.

## Java interop
- `(.method obj args)` instance call; `(Classname/staticMethod)` static; `(Classname. args)` constructor (== `(new Classname ...)`). `(.-field obj)` field. `(doto obj (.a) (.b))`. `import`/`:import`. `(instance? String x)`. Exceptions: `(try ... (catch Exception e ...) (finally ...))`, `throw`.

## REPL-driven development
- Primary workflow: connect editor to a running REPL (nREPL/CIDER/Calva), evaluate forms in place, redefine functions live, inspect state. Fast feedback loop; keep the process running.

## Macros & spec
- Macros run at compile time, receive unevaluated forms, return code: `defmacro`, `` ` `` (syntax-quote), `~` unquote, `~@` splice, `gensym`/`x#` for hygiene. Only for new syntax/control flow — prefer functions.
- **clojure.spec**: describe data/function shapes with predicates: `(s/def ::age pos-int?)`, `s/valid?`, `s/conform`, `s/fdef` + instrumentation, and generative testing via `test.check`.

## namespaces
- `(ns my.app (:require [clojure.string :as str] [clojure.set :refer [union]] [clojure.java.io :as io]))`. `require`/`refer`/`alias`/`import` (Java classes). One namespace per file; path mirrors name (`my/app.clj`, hyphens -> underscores in filenames).

## Core function vocabulary
- Collections: `conj cons into assoc assoc-in update update-in dissoc get get-in select-keys merge merge-with keys vals contains? peek pop`.
- Seqs: `map mapv filter remove reduce reductions for doseq take drop take-while drop-while partition partition-by group-by frequencies sort sort-by distinct dedupe interleave interpose flatten mapcat keep some every? count nth first second last butlast concat`.
- Predicates: `nil? some? empty? seq? coll? even? pos? zero? contains?`. `some` returns first truthy, not boolean.
- Control: `when when-not if-let when-let cond condp case ->`/`->>`/`as->`/`some->`/`cond->`, `doto`, `let`, `letfn`, `loop`/`recur`, `try`/`catch`.

## Data notation & literals
- **EDN** (Extensible Data Notation): the data subset of Clojure syntax used for config/`deps.edn`/messages — maps, vectors, keywords, `#inst`, `#uuid`, tagged literals. `read-string`/`clojure.edn/read-string` (edn is safe; `read` is not).
- Keywords are interned, fast map keys, and callable: `(:name m)` == `(get m :name)`. Namespaced keywords `::local` / `:my.ns/k`. Symbols `'sym`.

## Concurrency & polymorphism notes
- Four reference types by axis: coordinated? sync? — `atom` (uncoordinated/sync), `ref`+STM (coordinated/sync), `agent` (uncoordinated/async), `var` (thread-local via `binding`). Values inside are always immutable.
- `future`/`promise`/`delay`/`deref` (`@`) with optional timeout. `pmap` parallel map. core.async `chan`/`go`/`<!`/`>!` for CSP-style channels.
- Polymorphism: `defprotocol`+`defrecord`/`extend-protocol`/`extend-type` (fast, à-la-carte interfaces) vs `defmulti`/`defmethod` (open dispatch on arbitrary function of args).

## Tooling
- `clojure`/`clj` (tools.deps, `deps.edn` with `:deps`/`:aliases`/`:paths`) or `lein`. REPL clients: CIDER (Emacs), Calva (VS Code), nREPL. `tap>`/`add-tap` for debugging. Babashka (`bb`) = fast-start Clojure scripting (native, no JVM warmup).

## Gotchas -> Fix
- **Laziness + side effects**: `(map println coll)` at the REPL may not run (unrealized) or run late; side effects in lazy seqs fire unpredictably -> use `doseq`/`run!`/`dorun`/`doall`; keep lazy seqs pure.
- **Holding the head**: retaining a reference to the head of a huge/infinite lazy seq while consuming prevents GC -> don't bind the whole seq; consume in a fn that lets the head go.
- **Lazy realization escaping scope**: returning a lazy seq built inside `with-open`/`binding` — realized after the resource closed -> `doall` inside the scope.
- **nil punning**: empty seq `()` is truthy but `(seq x)` is `nil` when empty; `(first nil)`/`(rest nil)` are `nil`/`()` not errors -> test emptiness with `(seq x)` / `empty?`, not `(if coll ...)`.
- **`nil` swallowed**: many fns treat `nil` as empty, hiding bugs; `(get m :missing)` -> `nil` -> use `:or` defaults, spec.
- **`=` vs `==` vs `identical?`**: `=` value equality; `==` numeric across types (`(== 1 1.0)` true, `(= 1 1.0)` false); `identical?` reference.
- **Integer/`Long` overflow**: `+` throws on overflow -> use `+'` (auto-promote to BigInt) or `unchecked-add`.
- **Cryptic Java stack traces**: errors surface as JVM exceptions deep in Clojure internals -> read bottom-up, use `*e`, `clojure.repl/pst`; wrap for context.
- **JVM startup latency** (~1s+): bad for CLI/scripts -> use a persistent REPL, or GraalVM `native-image`/Babashka for fast scripts.
- **`recur` for recursion**: no TCO by default; deep self-recursion blows the stack -> use `loop`/`recur` (must be tail position) or `trampoline`.
- **Chunked seqs realize ~32 ahead**: side effects/laziness assumptions off by a batch -> don't rely on exact realization count.
- **Reader vs eval**: `'` quotes (list stays data); forgetting it evaluates. `#(...)` can't nest.
