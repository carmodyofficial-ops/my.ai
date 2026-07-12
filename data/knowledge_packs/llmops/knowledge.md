# LLMOps

## What it is / vs MLOps
- Operating **LLM-powered apps** in production. Differs from MLOps: you rarely train the model; the "model" is often a 3rd-party API; behavior is **non-deterministic**, **prompt-driven**, **token-priced**, and evaluated on **open-ended quality** not a single metric.
- Core surfaces: **serving**, **prompt/version mgmt**, **evals**, **observability**, **cost**, **guardrails**, **RAG index ops**, **reliability (fallbacks/retries)**.

## Serving (self-hosted inference)
- **vLLM**: high-throughput engine; **continuous (in-flight) batching** — schedule requests token-by-token, not fixed batches; **PagedAttention** for KV-cache memory efficiency; prefix caching. De facto default for OSS serving.
- **TGI** (HF Text Generation Inference), **TensorRT-LLM** (NVIDIA, fastest on their HW), **SGLang** (RadixAttention prefix cache), **LMDeploy**, **Ollama** (local/dev).
- **Continuous batching**: massively raises throughput vs static batching by filling GPU as requests finish.
- **KV cache** dominates GPU memory at long context; grows O(batch × seq_len × layers). PagedAttention reduces fragmentation. **KV-cache quantization** (fp8/int8) saves memory.
- **Quantization for inference**: AWQ, GPTQ, fp8, int4 — cut memory/latency; validate quality. Weight-only vs weight+activation.
- **GPU memory budget** ≈ weights + KV cache + activations; OOM is the #1 serving failure. Tune `max_model_len`, `gpu_memory_utilization`, `max_num_seqs`.
- Metrics: **TTFT** (time to first token / prefill), **TPOT/ITL** (inter-token latency / decode), throughput (tokens/s, req/s). Prefill is compute-bound, decode is memory-bandwidth-bound.

## Prompt & version management
- Treat prompts as **versioned artifacts** (git or a prompt registry), not hardcoded strings. Pin prompt version + model version together.
- Decouple prompt from code so it can be updated/rolled back; log which prompt+model produced each output.
- Templating with typed variables; separate system/developer/user layers.

## Evaluation (the heart of LLMOps)
- **Golden/eval sets**: curated input→expected (or rubric) pairs covering key cases + past failures. Grow from production incidents.
- **Metrics**: exact/regex for structured; semantic similarity; task metrics (retrieval recall, faithfulness/groundedness for RAG); **LLM-as-judge** for open-ended (pairwise or rubric scoring). Calibrate judge against human labels; beware judge bias (position, verbosity, self-preference).
- **Regression testing in CI**: run eval suite on every prompt/model change; block deploy on score drop. This is the single highest-leverage LLMOps practice.
- Offline eval (pre-deploy) + online eval (production sampling, user feedback, thumbs).

## Observability
- **Tracing**: capture full request tree — prompt, retrieved docs, tool calls, model, params, response, latency, token counts, cost — per request. Tools: LangSmith, Langfuse, Arize/Phoenix, Helicone, OpenTelemetry GenAI.
- Track **cost per request** (input+output tokens × price), p50/p95 latency, error/refusal rates, token usage.
- Sessions/threads for multi-turn; link user feedback to traces; enable drilldown on bad outputs.

## Pipeline / orchestration
- Frameworks: LangChain/LangGraph, LlamaIndex, Haystack, DSPy (for compiled prompts). Keep orchestration thin and observable; each step traced.
- Treat the app as **prompt + retrieval + tools + control flow**; version and eval the whole pipeline, not just the model call.
- Idempotent, resumable steps for multi-step agents; bound loop/tool-call counts to cap cost and runaway.

## Caching
- **Exact-prompt cache**: identical request → stored response (cheap, safe).
- **Semantic cache**: embed query, return cached answer for near-duplicates (threshold-tuned; risk of wrong hit).
- **Provider prompt caching / KV prefix caching**: cache long static prefixes (system prompt, docs) to cut cost+TTFT; vLLM/SGLang prefix cache; Anthropic/OpenAI prompt caching.

## Guardrails (production)
- **Input**: prompt-injection/jailbreak detection, PII redaction, topic/policy filters, length caps.
- **Output**: moderation (toxicity, policy), PII leak detection, schema/format validation, groundedness/hallucination checks, blocklists.
- Tools: NeMo Guardrails, Llama Guard, provider moderation endpoints. Fail closed on high-risk; log all blocks.

## Deployment strategy
- **Canary / shadow**: route small % to new prompt/model; compare quality+cost before full rollout. **Shadow** = run new in parallel, don't serve, compare.
- **A/B testing** prompts/models on live traffic with metrics + guardrails.
- Feature-flag prompts/models for instant rollback.

## Cost management
- **Token budgets** per request/user; cap context and output length.
- **Model routing / cascade**: cheap small model first, escalate to large only when needed (or by task class).
- Caching (above) is the biggest cost lever. Trim/compress prompts; drop redundant few-shot; RAG only relevant chunks.
- Monitor cost per feature; alert on spend anomalies.

## Reliability
- **Retries** with backoff + jitter on 429/5xx; **timeouts**; **fallback** model/provider on outage or rate limit.
- **Rate limits**: client-side throttling, queueing, per-tenant quotas; respect provider RPM/TPM.
- Idempotency keys; circuit breakers; graceful degradation (cached/simpler answer).

## RAG index ops
- **Ingestion pipeline**: chunk → embed → upsert to vector DB; version the index + embedding model (re-embed on model change).
- **Freshness**: incremental updates, TTL, re-index on source change; monitor stale docs.
- **Retrieval quality metrics**: recall@k, hit rate, context precision; eval retrieval separately from generation.
- Embedding-model change = full re-index (vectors incompatible).

## Drift & monitoring
- Watch **input drift** (new query distributions), **output-quality drift** (rising bad-judge scores, feedback decline), provider **silent model updates** (a versionless endpoint can change behavior overnight — pin versions).
- Alert on latency, cost, error, refusal-rate, guardrail-trigger spikes.

## Deployment topology & scaling
- **Autoscaling on GPU** is coarse (cold start = model load, tens of seconds to minutes); keep warm pool, scale on queue depth / TTFT SLO not CPU.
- **Separate prefill/decode** (disaggregated serving) at scale — different HW profiles. Route by expected length.
- **Multi-LoRA serving**: one base model + many adapters (S-LoRA/vLLM) → serve many fine-tunes cheaply.
- Batch offline/async jobs separately from interactive; use provider **batch APIs** (50% cheaper) for non-latency-sensitive work.

## Fine-tuning ops (when used)
- Prefer prompt/RAG first; fine-tune for format/style/latency, not for knowledge. Version datasets + adapters; eval fine-tune vs base on the golden set before promoting.
- LoRA/QLoRA adapters are cheap to store/swap; keep base pinned.

## Structured output & tool reliability
- Enforce schemas (JSON mode / tool calling / constrained decoding); validate + retry with error fed back.
- Log tool-call success rate, arg-validation failures, and retry counts as first-class metrics.

## Security/compliance
- Prompt-injection is the top OWASP LLM risk; treat retrieved/tool content as untrusted; instruction hierarchy; output filtering.
- Data governance: redact PII pre-send and pre-log; data-retention + provider zero-retention/enterprise terms; audit trail of prompts+outputs for regulated use.
- Secrets never in prompts; scope API keys per service; rate-limit per tenant to contain abuse/cost.

## Key metrics to dashboard
- Quality: eval-set score trend, LLM-judge pass rate, user thumbs, refusal rate, hallucination/groundedness rate.
- Performance: TTFT p50/p95, end-to-end latency, tokens/sec, throughput (req/s), queue depth.
- Cost: cost/request, cost/feature, tokens in/out, cache hit rate, spend anomaly alerts.
- Reliability: error rate, retry rate, fallback rate, rate-limit hits, timeout rate, tool-call success rate.

## Pitfalls -> Fix
- **No evals in CI** → prompt/model change silently regresses. **Fix**: golden set + LLM-judge gate on every change; block on score drop.
- **Cost blowup** → long contexts, huge outputs, no caching, everything on the biggest model. **Fix**: token budgets, output caps, caching, model routing/cascade, cost dashboards + alerts.
- **No caching** → paying repeatedly for identical/similar/static-prefix calls. **Fix**: exact + semantic + prompt-prefix caching.
- **Prompt changes untested** → "small wording tweak" breaks structured output for 10% of inputs. **Fix**: version prompts, run eval suite, canary.
- **No fallback / retries** → provider blip = full outage. **Fix**: retries+backoff, secondary provider/model, timeouts, circuit breaker.
- **Unbounded context** → cost + latency + "lost in the middle" quality loss + OOM. **Fix**: cap context, rerank/trim retrieved docs, summarize history.
- **Silent quality regression** → users notice before you do. **Fix**: online eval sampling, feedback capture, quality dashboards, pin provider model version.
- **Non-deterministic tests** → flaky CI. **Fix**: temperature 0 where possible, seed, judge with tolerance, multiple samples + threshold.
- **KV cache / GPU OOM** under load. **Fix**: tune max_model_len, gpu_memory_utilization, max_num_seqs; KV-cache quant; autoscale.
- **LLM-judge trusted blindly** → biased/inconsistent scores. **Fix**: calibrate against human labels, control position/verbosity bias, use pairwise + rubrics.
- **Embedding model swapped without re-index** → garbage retrieval. **Fix**: version index+embedder, full re-embed on change.
- **Guardrails only on input** → toxic/PII/hallucinated output ships. **Fix**: output moderation + schema + groundedness checks, fail closed.
- **PII in prompts/logs** → compliance breach. **Fix**: redact before send + before logging; retention policy.
