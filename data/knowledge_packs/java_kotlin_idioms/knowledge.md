# Java + Kotlin Idioms

## Java
- **Streams**: `list.stream().filter(x->x.ok()).map(X::name).collect(toList())`. Don't reuse a consumed stream.
- **Optional**: return `Optional<T>`, never null. `opt.map(..).orElse(default)`; avoid `.get()`. Don't use as a field/param.
- **Records**: `record Point(int x,int y){}` for immutable data; auto equals/hashCode/toString.
- **try-with-resources**: `try(var in=open()){...}` auto-closes; replaces finally.
- **Generics**: `List<? extends T>` to read, `List<? super T>` to write (PECS).
- **var**: locals only, when RHS type is obvious. Not for fields/returns.
- **switch**: `switch(s){case A,B -> 1; default -> 0;}` arrow form, exhaustive, yields.
- **equals/hashCode**: always override both together, or neither.
- **Immutability**: `final` fields, `List.copyOf()`, no leaking internal collections.
- **Concurrency**: `ExecutorService` + `submit`; always `shutdown()`. Never `new Thread` per task.

## Kotlin
- **Null safety**: `String?`, `a?.b`, `a ?: default`. `!!` is a code smell—refactor instead.
- **Data classes**: `data class User(val id:Int, val name:String)`.
- **val over var**: default immutable; `var` only when reassigned.
- **when**: `when(x){is A->..; in 1..9->..; else->..}` as expression.
- **Extensions**: `fun String.slug()=lowercase()...` over util classes.
- **Scope fns**: `let`(nullable map), `apply`(config, returns receiver), `also`(side-effect), `run`(block result).
- **Coroutines**: `suspend fun`; `launch{}` fire-forget, `async{}.await()` for results. Use structured `coroutineScope`.
- **Sealed**: `sealed interface Result` → exhaustive `when`, no else.
- **Default args**: `fun f(a:Int, b:Int=0)` over overloads.

## Gotchas
- Java NPE: prefer Optional/`Objects.requireNonNull`.
- Don't share mutable collections; copy at boundaries.
- `==` compares refs (Java) / calls `equals` (Kotlin); use `.equals`/`equals` deliberately.
- Autoboxing in loops kills perf—use primitives.
- Kotlin **platform types** from Java are unchecked-null; annotate or assert at the seam.
- Avoid `!!` and capturing mutable vars in lambdas.
