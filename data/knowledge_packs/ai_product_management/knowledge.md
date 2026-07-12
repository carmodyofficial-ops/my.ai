# AI Product Management

## What's different from traditional PM
- **Probabilistic, not deterministic** — same input can yield different outputs. You ship a *distribution of behaviors*, not a spec that's either met or not. Acceptance = statistical thresholds, not pass/fail on one case.
- **Evals replace/augment specs** — you can't enumerate every case; you define quality via a graded eval set. "The spec is the eval set."
- **The product surface = model + prompt + data + UX**, all tunable post-launch. Prompt and model choice are product decisions, not just eng details.
- **Data flywheel** — usage -> logs/feedback -> better evals/fine-tuning/prompts -> better product. Instrument for this from day one; it's the moat.
- **Non-stationary foundation** — underlying models change under you (new versions, deprecations, price cuts). Roadmap must absorb model churn.
- **Cost & latency are first-class product constraints**, not afterthoughts — tokens cost money and add seconds; they shape which features are viable.
- **Behavior emerges** — you discover capabilities/failures empirically by testing, not by reading a design doc.

## Is AI even needed? (feasibility gate — do this first)
- Would a rule, heuristic, lookup, or classic ML solve it cheaper/more reliably? Don't use an LLM for deterministic logic (math, routing, validation).
- Does the task tolerate *some* error? If a single wrong output is catastrophic and unrecoverable (irreversible financial/medical/legal action) without human review, reconsider or add a human gate.
- Is there a clear notion of "good output" you can evaluate? If you can't judge quality, you can't ship or improve it.
- Is the value in the *hard/fuzzy* part (language, summarization, extraction, ranking, generation) where LLMs excel? Use AI there; wrap it in deterministic code for the rest.
- Cost/latency/quality must clear the bar for the use case at expected volume.

## Defining success (metrics & evals)
- **Task success metric** tied to user outcome (task completion, deflection rate, time saved, acceptance/edit rate of AI output), not "model accuracy" in a vacuum.
- **Quality dimensions**: correctness/factuality, relevance, completeness, format adherence, tone/safety, latency. Weight by what the use case needs.
- **Eval set**: curated representative inputs + expected/graded outputs, including edge cases and known failure modes. Version it; grow it from production failures.
- **Graders**: exact/regex/schema checks where possible; LLM-as-judge for subjective quality (validate the judge against human labels, watch its bias); human review for high-stakes samples.
- **Acceptance threshold**: define the pass bar *before* building (e.g. ">=90% on eval set, p95 latency <3s, <1% policy violations"). Track regressions per prompt/model change.

## Measuring in production (three layers)
1. **Offline evals** — gate every prompt/model change against the eval set in CI. Prevents silent regressions.
2. **Online metrics** — real usage: acceptance/thumbs, edit distance from suggestion, retry/abandon rate, escalation-to-human rate, latency/cost per request, containment.
3. **User feedback** — explicit (thumbs up/down + reason) and implicit (did they use/edit/discard the output). Route flagged cases back into the eval set (the flywheel).
- A/B or shadow-test model/prompt changes; don't ship on vibes from a demo.

## UX for AI (managing uncertainty)
- **Set expectations** — signal it's AI-generated and may err; avoid implying certainty.
- **Show confidence / provenance** — citations, sources, "based on X"; let users verify. Don't fake precision.
- **Human-in-the-loop** for consequential actions — draft-then-approve, edit-before-send, suggest-don't-execute. Reversibility and undo.
- **Graceful failure** — when unsure, say "I don't know" / ask a clarifying question / hand off to a human, rather than confidently hallucinating. Design the fallback path explicitly.
- **Trust calibration** — early wins build trust; visible errors destroy it. Progressive autonomy: start assistive, earn more automation with proven quality.
- **Steerability & recovery** — easy to correct, regenerate, refine; keep the user in control.

## Scoping & guardrails
- Scope narrow first: a well-defined sub-task beats an open-ended "AI assistant." Constrain inputs/outputs (structured output, allowed actions).
- **Guardrails as requirements**, not polish: input validation, output filtering/moderation, PII handling, prompt-injection defense, jailbreak resistance, allowed-tool/action limits, rate limits, refusal policy. Write them into acceptance criteria.
- **Safety/policy** — define disallowed content and behaviors, red-team before launch, log for audit. Treat hallucination and misuse as risks with mitigations, not surprises.

## Data strategy
- Instrument inputs, outputs, feedback, and outcomes from launch (privacy/consent-compliant). Logs are the raw material for evals and fine-tuning.
- Build a labeled/curated eval + golden set; keep a held-out set. Source hard cases from production.
- Consider retrieval (RAG) to ground outputs in your proprietary/current data before reaching for fine-tuning.

## Cost & latency as constraints
- Cost drivers: tokens (input + output), model tier, calls per task (agents/chains multiply), retries, context size. Estimate cost/request * volume before committing.
- Latency drivers: model size, output length, sequential chain/agent steps, tool calls. Techniques: **stream** tokens (perceived latency), smaller/faster model for easy cases (routing/cascade), cache, shorten prompts/outputs, parallelize.
- Explicit **quality vs cost vs latency** budget per feature; revisit as prices drop.

## Buy vs build vs fine-tune (decision order)
1. **Prompt engineering + a strong base model** — fastest, cheapest, most flexible. Exhaust this first.
2. **RAG** — when the gap is *knowledge/freshness/grounding*, not behavior.
3. **Fine-tuning** — when you need consistent format/style/tone or a narrow task at lower cost/latency, and you have quality labeled data. Not a fix for missing knowledge or reasoning.
4. **Buy** (API/vendor) vs **build** — default to buying foundation models; build differentiators (data, UX, workflow, evals), not the LLM.

## Roadmapping under model churn
- Decouple product from any one model behind an abstraction; keep an eval harness to re-qualify new models quickly.
- Assume capabilities improve and costs fall — don't over-invest engineering to patch a limitation the next model release removes ("the model will eat it").
- Track deprecations/version changes; regression-test on upgrade. Plan for behavior shifts, not just API changes.

## Prompt / model iteration loop
- Treat it as an experiment loop: hypothesis -> change prompt/model/retrieval -> run eval set -> compare vs baseline -> ship or revert. Keep changes isolated so you know what moved the metric.
- Version prompts (source control), tag each with its eval score; keep a changelog of what improved/regressed.
- Techniques in order of leverage: clearer instructions + examples (few-shot) -> structured output/schema -> retrieval grounding -> decomposition/chaining -> tool use -> fine-tune. Escalate only when the cheaper lever plateaus.
- Guard against overfitting the prompt to the eval set; keep a held-out set and periodically refresh from production.

## Stakeholders & delivery
- Educate stakeholders that outputs are probabilistic — reset expectations away from "100% accurate."
- Align on the acceptance threshold and risk tolerance up front; get sign-off on the fallback/human-review policy for high-stakes flows.
- Legal/privacy/security are partners from day one (data usage, PII, model/data residency, IP, consent).
- Communicate in ranges and confidence, not guarantees; report eval scores and online metrics, not demo anecdotes.

## Roles & artifacts unique to AI PM
- **Eval set + rubric** is a core PM deliverable (owned with eng/DS), not an afterthought.
- **Golden dataset** of ideal input->output examples for regression + few-shot.
- **Prompt spec / system prompt** as a versioned product artifact.
- **Risk register**: hallucination, bias, misuse, injection, privacy — each with mitigation + owner.
- **Model card / capability doc**: what it can/can't do, known failure modes, cost/latency profile.

## Pitfalls -> Fix
- **AI for AI's sake** (feature chasing hype) -> start from user problem; prove AI is the *right* tool via the feasibility gate; ship a heuristic if it wins.
- **No evals / "it looked good in the demo"** -> build a versioned eval set + threshold before launch; gate changes in CI.
- **Demo-to-prod gap** -> demos are curated happy paths; test the long tail, adversarial/edge inputs, and real user messiness before shipping.
- **Ignoring cost/latency** -> model per-request cost * volume and p95 latency as hard requirements; route/cache/stream to hit them.
- **Over-promising accuracy** ("it's always right") -> communicate probabilistic limits in UX and marketing; set honest expectations; show confidence/sources.
- **No fallback UX** -> design explicit "unsure/error/handoff" states; never let confident hallucination be the only output.
- **Unmanaged hallucination risk** -> ground with RAG/citations, constrain outputs, add verification/human review for high-stakes, monitor factuality in evals.
- **No feedback loop** -> instrument feedback + outcomes from day one; funnel failures into evals (the flywheel is the moat).
- **Fine-tuning to fix knowledge gaps** -> use RAG for knowledge; fine-tune for behavior/format/cost.
- **Treating prompt as static/eng-only** -> version prompts as product; A/B and eval-gate every change.
- **Guardrails bolted on late** -> safety, PII, injection defense, refusal policy are acceptance criteria; red-team pre-launch.
- **Building the model instead of the moat** -> differentiate on data/UX/workflow/evals; rent the foundation model.
- **Roadmap frozen to today's model** -> abstract the model, keep a re-qualification harness, plan for churn and improving capability.
- **One global quality bar** -> set thresholds per use case by stakes; a brainstorm tool and a medical summarizer need different bars and gates.
