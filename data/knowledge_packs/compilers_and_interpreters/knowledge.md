# Compilers and Interpreters

## Pipeline
- Front end: source → lexer → parser → AST → semantic analysis (name/type resolution). Middle: AST/IR → optimization. Back end: IR → codegen → register allocation → target (machine code / bytecode).
- Phases separated by IR boundaries; front end is language-specific, back end target-specific — LLVM/GCC reuse back end across languages.
- Passes: single-pass (fast, limited — Pascal) vs multi-pass (needed for forward references, whole-program opt).

## Lexer (Scanner)
- Input chars → tokens: `(type, lexeme, source-location)`. Discards whitespace/comments; tracks line/column for diagnostics.
- Token classes described by regular expressions → compiled to DFA (via NFA + subset construction) for O(n) scanning. Maximal munch: longest match wins (`>=` not `>` `=`).
- Keywords vs identifiers: lex as identifier, then look up in keyword table. Handle string/number literals, escapes, nested comments (not regular — needs counter).
- Tools: lex/flex, or hand-written for control/error quality.

## Parsing
- Grammar = CFG (terminals, nonterminals, productions, start symbol). Ambiguous grammars have >1 parse tree — resolve with precedence/associativity rules.
- Recursive descent: hand-written, one function per nonterminal; top-down, predictive with lookahead. Simple, great errors; cannot handle left recursion directly.
- LL(k): top-down, leftmost derivation, k-token lookahead; needs FIRST/FOLLOW sets, no left recursion, must be left-factored. Table-driven or recursive descent.
- LR(k) / LALR(1) / SLR: bottom-up, rightmost derivation reversed; shift-reduce via parse table + stack. Handles left recursion, larger grammar class; harder errors. yacc/bison/GNU. Conflicts: shift/reduce, reduce/reduce.
- PEG / packrat: ordered choice, no ambiguity, memoized linear time; `|` is prioritized not symmetric.
- Precedence climbing / Pratt parsing: elegant for expressions with binding powers (prefix/infix/postfix) — avoids one grammar rule per precedence level.
- Error recovery: panic mode (skip to sync token), phrase-level, error productions.

## AST & Semantic Analysis
- AST = condensed parse tree keeping semantically relevant nodes (drops punctuation/single-child chains). Nodes typed per construct (BinaryExpr, IfStmt, FuncDecl).
- Visitor pattern traverses AST; separates operations (typecheck, codegen, pretty-print) from node structure. Double dispatch or pattern matching.
- Symbol table: maps names → declarations (type, kind, storage, scope). Scoping via stack of scopes / chained hash tables; lexical (static) scope resolves at compile time by nesting, dynamic scope by call stack (rare).
- Name resolution binds identifiers to declarations; handles shadowing, forward references, overloading.
- Type checking: infer/verify types, insert coercions, check assignability/arity. Static (compile-time) vs dynamic (runtime). Inference (Hindley-Milner: unification, let-polymorphism) for ML/Haskell-family.

## Intermediate Representation
- Levels: high (AST-like), mid (three-address code, CFG of basic blocks), low (near-machine). Three-address: `t = a op b`, one op per instruction.
- Basic block: maximal straight-line code, single entry/exit. CFG: blocks + control-flow edges. Dominator tree underpins many analyses.
- SSA (static single assignment): each variable assigned exactly once; φ-functions merge values at control-flow joins. Simplifies def-use chains, enables constant propagation, GVN, DCE. Convert via dominance frontiers; deconstruct before codegen.

## Optimization
- Local (within block): constant folding (`3*4`→`12`), constant propagation, common subexpression elimination, copy propagation, peephole.
- Global (across CFG via dataflow analysis — lattices, fixpoint): dead code elimination (DCE), reachability, liveness, available expressions, reaching definitions.
- Loop: invariant code motion, strength reduction (`i*4`→add), induction-variable simplification, unrolling, vectorization.
- Interprocedural: inlining (removes call overhead, exposes further opt; size/compile-time tradeoff), tail-call elimination, escape analysis (stack-allocate non-escaping objects), devirtualization.
- Ordering matters (phase-ordering problem); passes iterate to fixpoint.

## Code Generation & Register Allocation
- Instruction selection: map IR to target ops (tree pattern matching / BURS / maximal munch).
- Instruction scheduling: reorder to hide latency, fill pipeline slots (respect data deps).
- Register allocation: map unbounded virtual regs → finite physical regs. Graph coloring (Chaitin-Briggs: interference graph, spill high-degree nodes) or linear scan (fast, JIT-friendly). Spilling stores to stack when regs exhausted; calling conventions fix caller/callee-saved.

## Interpreters & VMs
- Tree-walking: directly evaluate AST via visitor. Simplest, slowest (pointer chasing, dispatch overhead).
- Bytecode VM: compile AST → compact bytecode, execute in dispatch loop. Stack-based (JVM/CPython — implicit operand stack, dense) vs register-based (Lua/Dalvik — fewer instructions, less stack traffic).
- Dispatch: switch (predictable but branch-mispredict-heavy), direct/indirect threading (computed goto, better prediction), subroutine threading.
- JIT: profile hot paths, compile bytecode→native at runtime. Tiers: interpreter → baseline JIT → optimizing JIT (speculative, deopt on assumption failure — inline caches for dynamic dispatch). Trace-based vs method-based.

## Dataflow & Analysis Foundations
- Dataflow analysis: propagate facts over the CFG to a fixpoint on a lattice; forward (reaching defs, available exprs, constant prop) vs backward (liveness, very-busy exprs); may (union) vs must (intersection) meet. Monotone framework guarantees termination.
- Def-use / use-def chains connect definitions to uses; SSA makes them explicit (single def per name). Alias analysis bounds what pointers may reference (limits optimization safety). Dominance: block A dominates B if every path to B passes A — foundation for loop detection and SSA φ-placement.
- Value numbering / GVN dedups equivalent computations; partial redundancy elimination hoists.

## Error Handling & Diagnostics
- Lexical, syntactic, semantic, and link errors reported at distinct phases; good compilers continue past the first error (recovery) to batch diagnostics with precise source spans, caret underlines, and fix-it hints.
- Warnings vs errors; `-Werror`. Undefined behavior in the source lets optimizers assume it can't happen — a frequent source of "the optimizer broke my code" surprises.

## Garbage Collection
- Reachability from roots (stacks, globals, registers). Reference counting: immediate reclaim, cheap latency, but cycles leak (need cycle collector) and count updates cost.
- Tracing: mark-sweep (mark reachable, sweep rest — fragmentation), mark-compact (relocate to defragment), copying/semi-space (copy live to new space — fast alloc via bump pointer, halves heap).
- Generational: most objects die young → collect young gen frequently (minor GC), old gen rarely; write barriers track old→young refs. Incremental/concurrent GC (tri-color marking: white/gray/black, barriers preserve invariant) reduces pause times.

## Runtime & ABI
- Calling convention (ABI): argument passing (registers vs stack), return values, caller/callee-saved registers, stack alignment, name mangling (C++ encodes types into symbol names; `extern "C"` disables). Cross-compiler linking requires matching ABI.
- Activation record / stack frame per call: return address, saved frame pointer, locals, spilled temporaries, callee-saved regs. Tail calls reuse the frame.
- Closures capture free variables (by value/reference) → heap-allocated environment when they escape. Exceptions unwind the stack via landing pads + unwind tables (`.eh_frame`/DWARF CFI); zero-cost model pays only on throw.
- Name resolution of externals via linker: static (archive `.a`) vs dynamic (`.so`/`.dll` via PLT/GOT, lazy binding). Link-time optimization (LTO) defers codegen to see across translation units.

## Front-End Extras
- Macro/preprocessing (textual C macros vs hygienic Scheme/Rust macros that avoid variable capture). Desugaring lowers syntactic sugar to core forms early.
- Constant expression evaluation (`constexpr`/comptime) runs a sub-interpreter at compile time. Diagnostics quality depends on preserving source spans and recovering after errors to report multiple problems per compile.

## LLVM
- LLVM IR: typed, SSA-form, RISC-like; three forms (in-memory, bitcode, textual `.ll`). Language-independent middle end + target back ends.
- Flow: Clang/frontend → LLVM IR → opt passes (PassManager) → SelectionDAG/GlobalISel → target asm/object. Reusable optimizer; enables new-language back ends cheaply.
- IR structure: Module → Functions → BasicBlocks → Instructions; `phi` nodes for SSA merges; intrinsics for target/runtime ops; metadata (debug info, TBAA aliasing). Target datalayout describes pointer size/alignment/endianness.

## Gotchas -> Fix
- Left recursion breaks recursive-descent/LL (infinite loop) -> eliminate/left-factor, or use Pratt/precedence climbing or an LR parser.
- Ambiguous expression grammar / wrong precedence & associativity -> encode precedence levels in grammar or assign Pratt binding powers; declare `%left`/`%right` in bison.
- Dangling-else ambiguity -> bind `else` to nearest `if` (grammar disambiguation or explicit rule).
- Shift/reduce & reduce/reduce conflicts in LALR -> refactor grammar or add precedence declarations; inspect generated tables, don't ignore warnings.
- Not left-factoring common prefixes -> factor so predictive parser has unique lookahead.
- Scope/shadowing bugs -> enter/exit scopes symmetrically; resolve names against the scope active at that AST point, not globally.
- Using `float`/int constant folding that changes semantics (NaN, overflow, rounding) -> fold only when result is bit-identical to runtime; respect IEEE, don't fold signaling ops.
- Deleting code with side effects during DCE -> only eliminate truly pure/unreachable code; model volatile/IO as live.
- Register allocator ignoring calling convention -> spill/save caller-saved across calls; pin argument/return regs.
- Recursive tree-walk stack overflow on deep AST -> explicit worklist/iterative traversal for deeply nested input.
- GC moving objects while native code holds raw pointers -> use handles/safepoints; pin or update via read/write barriers.
- Off-by-one in source spans -> track byte and line/col consistently from the lexer for accurate diagnostics.
