# AI / LLM Engineering Cheat-Sheet

Building LLM-backed systems. For depth see packs: **llm_engineering** (API/streaming/tokens), **rag_systems** (retrieval), **ai_agents** (tool loops/planning).

## Model selection
- Match model to task tier: cheap/fast small model for classify/extract/route; frontier model for reasoning/code/long-context. Route by difficulty (small model first, escalate on low confidence).
- Axes: capability, context window, latency, $/1M tokens (in vs out — output often 3-5x pricier), tool/JSON support, hosting/privacy. Benchmark on **your** eval set, not public leaderboards.
- Prefer the smallest model that passes evals; re-test on every model/version change (behavior drifts silently).

## Prompting
- Structure: system (role + rules + output contract) / user (task + data). Never let user/retrieved content override system.
- Be specific: give the format, constraints, and 1-3 few-shot examples for shape. Put long/reference data **after** instructions; label untrusted data.
- Reasoning: ask for step-by-step / think-then-answer for hard tasks; for extraction keep it terse. Decouple reasoning from the final structured field.
- Version prompts like code (store, diff, eval). Small wording changes shift behavior — treat as a change requiring re-eval.

## Structured output
- Request strict JSON via schema / json_mode / native tool-calling — not "reply in JSON please".
- Validate every field against a schema (Pydantic). On parse/validation fail, send the error back and ask for repair — **don't** regex-patch the output.
- `temperature=0` for extraction/classification/deterministic tasks. Assume non-determinism otherwise; never trust one lucky run.

## RAG (overview)
- Pipeline: chunk -> embed -> store -> retrieve top-k -> rerank -> stuff context -> generate with citations.
- Chunk 200-500 tokens, ~10-15% overlap, on semantic boundaries. Embed query AND docs with the **same** model.
- Retrieve top-k (3-8) by cosine (or hybrid dense+BM25); rerank for precision. Pass only retrieved text + `[source]` cites; never stuff the whole corpus.
- If nothing relevant retrieved, say so — don't hallucinate. RAG cuts (not eliminates) hallucination and adds fresh/private knowledge without fine-tuning.

## Embeddings / vector search
- Normalize vectors; cosine = dot on normalized. Store id + text + metadata for filtering. Re-embed everything when you switch models (dims/space differ, not comparable).
- ANN index (HNSW/IVF) for scale; exact for small sets. Metadata filters narrow before/after ANN.

## Agents (overview)
- Loop: model picks a tool -> you execute -> feed result back -> repeat until done. Define tools as JSON Schema; validate args before executing; make tools idempotent.
- Cap iterations (max steps) and cost/token budget per run — unbounded loops burn money and spiral. Add a stop condition + human-in-loop for irreversible actions.
- Prefer a simple workflow (fixed steps) over an autonomous agent when the flow is known — cheaper, more reliable.

## Evals (do this first)
- Build an eval set **before** shipping: real inputs + expected outputs/graders. No evals = you're flying blind; you can't tell a prompt change helped or hurt.
- Grading: exact/regex for structured; LLM-as-judge for open-ended (validate the judge against human labels, watch its bias); human spot-check the tail.
- Track a scoreboard across prompt/model versions. Include adversarial + edge cases (empty, huge, injection, ambiguous). Regression-test on every change.

## Cost / latency / caching
- Cost ≈ tokens × price; trim prompts, cap `max_tokens`, retrieve less, route to smaller models. Log token usage per call.
- **Prompt caching** (reuse a stable long prefix — system/RAG context) cuts input cost + latency; order prompts prefix-stable to hit the cache.
- Cache identical (or semantically near) requests. Stream tokens to cut perceived latency. Parallelize independent calls. Batch where the API supports it.

## Guardrails, injection, observability
- **Prompt injection**: retrieved/tool/web/user content is DATA, not instructions. Fence + label it; instruct the model to ignore embedded commands; never auto-execute tool calls derived from untrusted text without checks/allow-lists. Least-privilege tools.
- Guardrails: validate inputs (length, PII, moderation) and outputs (schema, policy, moderation) on both ends. Add refusal paths for out-of-scope asks.
- Observability: log prompt, model+version, tokens, latency, cost, tool calls, and (redacted) output per request; trace multi-step chains; sample for eval. Alert on error rate, latency, cost, and refusal spikes.
- Fallbacks: on 429/5xx retry with exponential backoff+jitter; on repeated failure degrade to a smaller model / cached / canned response — never hard-fail the user.

## When to fine-tune
- Try **prompting -> few-shot -> RAG -> tool use** first; fine-tune only when you need a consistent style/format/tone, latency/cost from a smaller model, or a narrow task where prompting plateaus.
- Fine-tuning does **not** add fresh facts (use RAG) and needs a maintained labeled dataset + re-tune on drift. Start from measured eval gaps, not vibes.

## Gotchas -> Fix
- No eval set -> can't measure regressions; build one before optimizing prompts/models.
- Prompt brittleness -> tiny wording/model changes break output; version + re-eval, don't hand-tune blindly.
- Hallucination / confident wrong answers -> ground with RAG + citations, ask "say if unknown", validate factual claims, LLM-judge for faithfulness.
- Cost blowup -> unbounded context/agent loops/retries; cap tokens+steps, cache prefixes, route to small models, log spend.
- Unbounded context -> costs+latency climb, quality drops in the middle ("lost in the middle"); trim/summarize history, retrieve less, keep system+recent.
- Trusting one run -> non-determinism; `temperature=0` + validate + retry-on-invalid.
- Prompt injection via retrieved/tool data -> treat as untrusted data, least-privilege tools, human gate for irreversible actions.
- No fallback / single provider -> retries + backoff + degraded path + timeouts (30-60s); treat empty/`finish_reason:length` as failure and raise `max_tokens`/retry.
- Regex-patching bad JSON -> validate against schema and ask the model to repair instead.
