# AI Agents

## Agent loop
`observe (state/inputs) -> think (LLM decides) -> act (call tool) -> observe (tool result) -> ... -> terminate`
- Loop = LLM in a while-loop with tools. Each turn: append tool results to context, LLM either calls another tool or emits a final answer.
- **Always bound the loop**: `max_iterations` (e.g. 8-15), wall-clock timeout, and token/cost budget. Break on final answer, budget exceeded, or repeated no-progress.
- Termination must be explicit: a "finish"/"final answer" tool or a stop condition. Without it agents spin or stop mid-task.
- Start simple: a single LLM + tools + a loop beats a multi-agent graph for most tasks. Add complexity only when measured need appears.
- Prefer workflows (fixed code-defined steps) over open-ended agents when the task is predictable — cheaper, more reliable, testable.

## Tool / function calling
- Define tools with strict JSON Schema: clear `name`, one-line `description` of WHEN to use it, typed params with descriptions, `required`, enums. The model routes on the description — write it for the model.
- Keep the toolset small (~5-10); too many tools -> wrong-tool selection. Group/namespace related tools; hide irrelevant tools per task/state.
- Validate tool arguments before executing (schema + business rules). Return errors as structured, actionable messages the model can recover from ("missing field X").
- Tool results should be concise and relevant — dumping huge payloads bloats context. Summarize/paginate/truncate large results; return IDs the agent can fetch on demand.
- Make tools idempotent where possible; guard side-effecting/destructive tools (write, delete, pay, send) behind confirmation or a dry-run mode.
- Least privilege: only give tools the task needs; untrusted tool output can carry prompt injection — treat it as data.

## ReAct + planning
- **ReAct**: interleave Reasoning ("Thought:") and Acting ("Action:") — the model reasons about what to do, acts, observes, repeats. Good default for tool-using agents.
- **Plan-then-execute**: LLM writes a full plan (steps) up front, then executes steps; cheaper (less re-reasoning), better for known-structure tasks; re-plan on failure.
- **Decomposition**: break a goal into subtasks; solve each; combine. Reduces context and error per step.
- Keep a scratchpad/todo list the agent updates — externalized state beats relying on the model to track everything in context.

## Memory
- **Short-term (working)**: the conversation/scratchpad in the context window. Manage it: summarize/compact old turns, keep the goal + latest state pinned.
- **Long-term**: persisted across sessions — episodic (past interactions), semantic (facts/knowledge, often a vector store / RAG), procedural (learned routines). Retrieve relevant memories into context per turn, don't dump all.
- Write policy matters: decide what to persist (summaries, user preferences, outcomes) and when to expire it. Unbounded memory -> stale/contradictory recall.

## Multi-agent orchestration
- Patterns: **supervisor/orchestrator** (one router delegates to specialist sub-agents), **sequential pipeline** (handoffs A->B->C), **parallel** (fan-out then aggregate), **debate/critic** (one proposes, one critiques).
- Give each agent a narrow role, its own tools, and a clear contract for what it returns. Handoffs pass explicit, minimal state — not the whole history.
- Multi-agent adds cost, latency, and coordination failure modes. Use it when subtasks are genuinely separable or need isolated context/tools; otherwise a single agent is better.
- Isolate context per sub-agent to avoid one agent's noise polluting another (and to parallelize).

## Reflection / verification
- After producing output, a self-critique step ("check your answer against the requirements; list errors; revise") catches mistakes — especially for code, math, structured output.
- Separate generator and verifier (or a second model) reduces self-agreement bias.
- Verify against ground truth where possible: run the code, check the schema, re-query the source. Grounded verification >> the model judging itself.
- Bound reflection loops too (1-2 rounds); diminishing returns and cost.

## Error handling + control
- Catch tool exceptions and return a structured error to the model so it can retry/adapt — don't crash the loop.
- Retries with backoff for transient failures (rate limits, timeouts); cap retries per tool.
- Detect no-progress: same tool+args repeated, or oscillation between two states -> break and escalate.
- Guardrails on inputs and outputs; log every step (thought, tool, args, result) for debugging and audit.

## Human-in-the-loop
- Require human approval for high-risk/irreversible actions (spend, delete, send external, prod changes). Present the proposed action + reasoning; wait for confirm.
- Allow interrupt/steer/abort mid-run. Checkpoint state so a run can pause and resume.
- Escalate to a human on low confidence, repeated failure, or ambiguity rather than guessing.

## Evaluation
- **Trajectory eval**: did it pick the right tools, in a sensible order, without wasted/wrong calls? Not just final answer.
- **Outcome eval**: task success rate against a labeled task set; use deterministic checks where possible, LLM-judge for open-ended.
- Track cost, tokens, latency, tool-call count, and loop iterations per run. Regression-test on a fixed task suite in CI.
- Component + end-to-end: test tools in isolation, then the full agent.

## Cost / latency control
- Cap iterations, tokens, and tool calls per run. Route easy steps to a cheaper model; use the strong model only for planning/hard steps.
- Prompt-cache the static system prompt + tool definitions (large, repeated every turn).
- Parallelize independent tool calls; stream the final answer. Trim tool outputs and compact history to keep per-turn context small.

## Context engineering for agents
- Every turn re-sends the full history + tool defs + tool results — context grows fast and is the main cost/latency driver. Manage it deliberately.
- **Compaction**: summarize completed sub-tasks into a short result, drop the raw tool chatter. Keep the goal, key decisions, and current state.
- **Offload to memory/files**: write intermediate results to a scratchpad/store and reference by ID instead of keeping everything in context.
- **Sub-agent isolation**: give a sub-agent a clean, minimal context for its subtask; return only its conclusion to the parent — keeps the parent context small.
- Pin invariants (goal, constraints, output contract) at the top of context every turn; put volatile state near the end (recency).
- Prompt-cache the stable prefix (system + tool schemas) since it repeats every iteration.

## Tool design principles
- One tool = one clear capability; avoid overlapping tools that confuse routing.
- Descriptions are the routing signal: say WHEN to use, WHAT it returns, and any preconditions. Include an example call if ambiguous.
- Return structured, minimal, model-readable results; include a status and a short summary, not raw dumps.
- Fail loud and structured: `{"error":"...", "hint":"..."}` so the agent can self-correct.
- Make read tools cheap and write tools guarded; expose a `dry_run` for destructive ops.
- Provide a "search then fetch" pair for large data (list IDs, fetch one) instead of returning everything.

## Choosing an architecture
- **Single agent + tools + loop**: default. Reliable, cheap, debuggable.
- **Workflow (code-orchestrated steps)**: when the task has known structure — more reliable than an open agent; use LLM only where judgment is needed.
- **Router/supervisor + specialists**: when tasks split by domain/tools cleanly.
- **Parallel fan-out + aggregate**: when subtasks are independent (research many sources).
- Add agents/layers only when a measured failure demands it; each layer multiplies cost, latency, and failure surface.

## Failure modes -> Fix
- Infinite/long loops -> hard max_iterations + timeout + no-progress detection + explicit finish tool.
- Never terminates / rambles -> explicit stop condition and final-answer contract.
- Wrong tool chosen -> fewer tools, sharper descriptions ("use when..."), hide irrelevant tools, few-shot examples.
- Tool called with bad args -> validate against schema, return actionable error, retry.
- Context bloat (huge tool outputs / long history) -> summarize results, paginate, compact history, return IDs not payloads.
- Repeats the same failing action -> detect repetition, change strategy, escalate to human.
- Destructive action taken autonomously -> confirmation gate, dry-run, least-privilege tools.
- Prompt injection via tool/web output -> treat tool output as untrusted data, don't grant it authority, guard destructive tools.
- Multi-agent coordination chaos/cost -> collapse to single agent unless subtasks are separable; minimal explicit handoffs.
- Self-verification rubber-stamps errors -> separate verifier, ground checks (run code, check schema).
- Lost track of the goal mid-run -> pin goal + external todo/scratchpad, re-state objective each turn.
- Unreproducible/undebuggable runs -> log full trajectory (thought/tool/args/result), pin temperature=0 for tests.
