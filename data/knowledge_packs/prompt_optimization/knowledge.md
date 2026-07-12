# Prompt Optimization

## Principle
- Move from ad-hoc "guess-and-check" prompting to **systematic, eval-driven** optimization: define a metric + eval set, iterate measurably, and where possible **automate** the search.
- Optimize the whole pipeline (instructions + examples + format + control flow), not just wording.

## Core reasoning techniques
- **Few-shot / in-context learning**: 2-8 demonstrations; quality + coverage > quantity; order matters (recency bias — put strongest last). Match distribution of real inputs.
- **Chain-of-thought (CoT)**: elicit step-by-step reasoning ("think step by step") → big gains on math/logic/multi-step. Zero-shot CoT vs few-shot CoT with worked examples.
- **Decomposition**: break a hard task into sub-prompts / a pipeline (least-to-most, plan-then-solve). Each step simpler, more reliable, testable.
- **Self-consistency**: sample N CoT paths, **majority-vote** the answer → accuracy > single greedy path (costs N×).
- **ReAct**: interleave Reasoning + Action (tool calls) + Observation; for agentic/tool use.
- **Reflection / self-critique**: model reviews and revises its own output (verify claims, check constraints).
- **Role/persona + explicit constraints**: set expertise, audience, do/don't lists.

## Advanced reasoning patterns
- **Least-to-most**: solve simpler subproblems first, feed answers forward.
- **Tree/graph-of-thought**: explore + score multiple reasoning branches (costly; for search-like tasks).
- **Program-aided (PAL)**: model emits code, execute it for the answer — offloads arithmetic/logic to an interpreter (more reliable than mental math).
- **Verifier / critic model**: separate pass checks the answer against constraints; reject-and-retry.
- **Ensembling**: multiple prompts/models vote — trades cost for accuracy/robustness.

## Structured output
- Demand **strict schemas**: JSON Schema, function/tool calling, or grammar-constrained decoding (outlines, JSON mode, structured outputs). Enforced decoding beats "please return JSON".
- Validate output against schema; retry with the validation error fed back on failure.
- Use delimiters/XML tags to separate sections; ask for one field at a time for complex extraction.

## Templates & variables
- Parameterize prompts: typed variables, separate static instructions from dynamic context.
- Version templates; keep a system/developer/user separation. Libraries: Jinja, LangChain/LlamaIndex prompt templates, DSPy signatures.

## Automatic prompt optimization
- **DSPy**: program with **Signatures** (`question -> answer` typed I/O) + **Modules** (Predict, ChainOfThought, ReAct); **compilers/optimizers** ("teleprompters") tune prompts against a metric on a trainset:
  - **BootstrapFewShot** — auto-generate & select demonstrations from your data.
  - **MIPROv2** — jointly optimize instructions + few-shot examples (Bayesian search over proposals).
  - **BootstrapFinetune**, **COPRO** (instruction search). You write code + metric, DSPy searches prompts.
- **OPRO** (Optimization by PROmpting): LLM proposes better instructions from a trajectory of (prompt, score) pairs; iterate.
- **APE** (Automatic Prompt Engineer): LLM generates candidate instructions, score on eval, keep best.
- **Evolutionary / EvoPrompt**: mutate+crossover prompt population, select by fitness (metric).
- **TextGrad**: "backprop" natural-language feedback through the pipeline to edit prompts.
- All require a **metric + validation set** — automation optimizes what you measure.

## Example selection / retrieval for few-shot
- **Dynamic (RAG) few-shot**: retrieve the k most similar examples to the current input (embedding kNN) instead of a fixed static set → better than random fixed examples.
- Selection strategies: diversity (cover input space), difficulty, kNN by embedding, class balance. Avoid label leakage from the eval set.

## Eval-driven iteration
- Build a **golden set** (representative + adversarial + past failures). Define metric (exact match, F1, task metric, LLM-judge rubric, pairwise).
- Change one variable at a time; measure delta on the set; keep a leaderboard of prompt versions.
- Hold out a **test set** never used during optimization to detect overfitting.
- Online: A/B prompts in prod with guardrails + feedback.

## Prompt compression / cost reduction
- Cut tokens while holding quality: remove redundant instructions, trim/rerank retrieved context, fewer/shorter few-shot, summarize history.
- **LLMLingua**-style compression: drop low-information tokens from prompts.
- Exploit **prompt caching** for static prefixes (system + docs) — reorder so the cacheable, stable part is first.
- Distill a long optimized prompt into a shorter one; verify on eval.

## Robustness
- **Against injection**: separate untrusted input with delimiters/tags, instruct model to treat data as data, don't let retrieved/tool content override system instructions; add output validation.
- **Against format drift**: constrained decoding + schema validation + retry; test formatting across temperatures.
- **Prompt sensitivity**: outputs can swing with trivial rewording/example order → test paraphrase and order robustness.

## Model-specific tuning
- Prompts don't transfer cleanly across models/versions — re-tune per model (different formatting, system-prompt handling, CoT need, tool-call syntax). Reasoning models often need *less* explicit CoT; smaller models need *more* structure and examples.
- Respect provider conventions (system vs developer role, tool schema format, stop tokens).

## Decoding params (often overlooked)
- **Temperature/top-p**: 0 for deterministic extraction/classification; higher for creative. Tune alongside the prompt — a prompt "fix" may just be a temperature issue.
- **Max tokens / stop sequences**: cap output; use stop tokens to end cleanly and cut cost.
- **Seed** (where supported) for reproducible evals. Self-consistency needs temperature > 0.

## Instruction design specifics
- Put the **task + constraints up front**, context in the middle, the **question/output-format last** (recency helps).
- Be explicit: state what to do, not just what to avoid; give the output schema; specify tie-breaks and edge cases.
- **Positive + few negative** examples; show the exact format you want (including for refusals / "unknown").
- Prefer showing over telling for format; prefer telling for policy/constraints.

## Workflow / process
- Keep a **prompt changelog** + versioned templates in git; tie each prod output to prompt+model+params.
- Build the eval set from real + failed production cases; grow it every time a bug ships.
- Optimize in a loop: baseline metric → hypothesis → single change → measure on val → keep/revert → re-check on held-out test.
- Automate once the eval + metric are stable (DSPy/OPRO); manual first to understand the task.

## Metrics catalog
- Deterministic: exact match, F1, BLEU/ROUGE (weak), regex/schema-valid rate, retrieval recall@k, groundedness.
- Model-graded: LLM-judge rubric score, pairwise win-rate, reference-based grading. Calibrate to human labels; measure judge agreement (Cohen's κ).

## Tooling
- **DSPy** (declarative + optimizers), **promptfoo** / **OpenAI Evals** / **Langfuse** (eval + comparison), **guidance** / **outlines** / **Instructor** (structured/constrained output), **LLMLingua** (compression), **TextGrad** (NL-gradient optimization).
- Version prompts in git; run eval as a CI gate on prompt changes.

## Pitfalls -> Fix
- **Overfitting prompts to the eval set** → great offline, fails in prod. **Fix**: held-out test set, diverse/adversarial data, cap optimizer iterations, check generalization.
- **Brittle formatting** → one weird input breaks JSON parsing. **Fix**: constrained decoding / tool calling, schema validation + retry with error, robust parser.
- **No eval loop** → "seems better" is anecdote. **Fix**: golden set + metric before any prompt change; measure deltas.
- **Prompt bloat** → ever-growing instructions, redundant few-shot, high cost/latency, "lost in the middle". **Fix**: prune, compress, dynamic few-shot, prompt caching; ablate each addition.
- **Ignoring model differences** → copy prompt to new model, quality drops. **Fix**: re-optimize per model/version; pin versions.
- **Manual guess-and-check** → slow, unrepeatable, undocumented. **Fix**: DSPy/OPRO/APE automated search with a metric; version prompts.
- **Too many / poorly chosen few-shot** → example order bias, distribution mismatch, label leakage. **Fix**: retrieval-based selection, balance classes, strongest example last, exclude eval instances.
- **Self-consistency/CoT cost ignored** → N× tokens. **Fix**: use only where accuracy justifies; cap N; reserve for hard queries via routing.
- **Optimizing the wrong metric** → e.g. exact-match on a generative task. **Fix**: pick a metric that matches the goal (LLM-judge/rubric for open-ended), calibrate judge to humans.
- **Untested injection surface** → retrieved/tool text hijacks the prompt. **Fix**: delimit untrusted input, instruction hierarchy, output moderation, adversarial eval cases.
- **Changing prompt + model + examples at once** → can't attribute the change. **Fix**: one variable at a time; keep a changelog.
- **CoT reasoning trusted as ground truth** → rationalization ≠ real cause. **Fix**: verify final answers, don't parse the "reasoning" as a guarantee.
