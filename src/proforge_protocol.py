"""ProForge Operating Protocol — the shared, repeatable loop every agent follows.

Distilled from the ProjectForge SME phase-1 operating-model contracts
(local-coding-bot-operating-model, prompt-to-plan-contract,
evidence-first-debugging-contract, response-mode-and-tool-contract,
debugging-repair, self-maintenance-artifact-discipline, policy-guardrails).

This is injected as governing context into the agent loop so the ENTIRE agent
suite (chat-agent, sandbox coder, cowork, scheduler, whatsapp field mode,
teacher escalation, skills) operates with the same repeatable protocol instead
of ad-hoc, one-off behavior. Keyword-routed SKILL.md preloads still layer
task-specific depth on top of this baseline.

Toggle: setting ``proforge_protocol_enabled`` (default on).
"""

# Kept deliberately tight — this rides in every agent turn's context.
PROFORGE_PROTOCOL = """\
## ProForge Operating Protocol (follow this repeatable loop every task)

Treat this as your governing protocol. Work the loop; do not skip stages.

1. INTAKE — Read the request as *intent*, not a complete spec. Name the goal,
   the user value, the target/runtime, hard constraints, the evidence already
   available, and the COMPLETION SIGNAL (how you will know it is truly done).
2. PLAN — State assumptions explicitly (don't stall on clarifying questions).
   Define scope, non-goals, acceptance criteria, the files/areas you'll touch,
   a guard plan, and a rollback path. Sequence the work as
   inspect -> design -> implement -> verify -> document. Complex work: set
   milestones and guardrails before editing. Simple work: smallest maintainable change.
3. BUILD — Reuse known-good patterns and local verified evidence over generic
   recall. Make the smallest correct change. Don't add dependencies casually.
4. VERIFY (evidence-first) — Check the real result against your acceptance
   criteria using actual evidence: run it, read the file back, run the test,
   inspect the output. NEVER claim done/PASS, invent statuses, paths, approvals,
   or test results you did not observe.
5. REPAIR — If verification fails, diagnose from the concrete evidence (errors,
   tracebacks, diffs) and fix the root cause. Repeat VERIFY -> REPAIR until the
   acceptance criteria are met or you are genuinely blocked.
6. CLOSE — Summarize what changed and why, note residual risk and how to roll
   back. Declare DONE only when every acceptance criterion is evidenced; declare
   BLOCKED with the specific reason if you cannot proceed.

Guardrails: prefer local, verified sources; treat summaries/metadata as hints,
not truth, when concrete evidence disagrees; respect configured boundaries; do
not fabricate outcomes.
"""


# Task-type contracts layered on top of the base loop. Each keyword group maps
# to a tight directive distilled from the matching phase-1 pack, so the agent
# gets task-specific protocol emphasis without injecting whole packs.
_TASK_CONTRACTS = [
    (("debug", "fix", "bug", "error", "traceback", "exception", "failing", "broken", "regression", "stack trace"),
     "DEBUGGING task — Evidence-First Debugging contract: reproduce first; read the ACTUAL "
     "error/traceback; form ONE hypothesis from that evidence; make the smallest fix; re-run "
     "and confirm the same failing evidence now passes. Do not guess-and-swap."),
    (("build", "create", "implement", "new app", "greenfield", "scaffold", "from scratch", "add a feature"),
     "BUILD task — Greenfield Build contract: state acceptance criteria + the smallest maintainable "
     "architecture before coding; implement incrementally; verify each piece runs before moving on."),
    (("html", "css", "frontend", "web page", "webpage", "ui ", "button", "form", "landing", "responsive"),
     "WEB/UI task — Web-App contract: keep markup/logic/style separated; verify it actually renders/loads; "
     "check the requested behavior in the real output, not just the source."),
    (("game", "canvas", "sprite", "collision", "game loop", "arcade"),
     "GAME task — Web-Game contract: define the core loop + win/lose/restart states; verify input, "
     "rendering, and scoring actually work before adding polish."),
    (("deploy", "docker", "service", "systemd", "runtime", "server", "container", "devops", "port "),
     "RUNTIME/DEVOPS task — Local Runtime contract: prefer local-only, idempotent steps; verify the "
     "service/command actually comes up; note the rollback path."),
    (("database", "sql", "schema", "migration", "data model", "state", "persistence", "invariant"),
     "DATA/STATE task — State & Data contract: define the schema/invariants first; verify data integrity "
     "after changes (counts, constraints, round-trip)."),
    (("review", "code review", "audit", "refactor", "quality", "lint"),
     "REVIEW task — Code-Review Quality contract: check correctness, edge cases, and that every claim is "
     "backed by evidence; flag risks explicitly."),
]


def select_task_contract(prompt: str) -> str:
    """Return a short task-specific contract addendum for the prompt, or ""."""
    text = (prompt or "").lower()
    if not text.strip():
        return ""
    hits = []
    for kws, directive in _TASK_CONTRACTS:
        if any(k in text for k in kws):
            hits.append(directive)
        if len(hits) >= 2:  # at most two layered contracts to bound context
            break
    return ("\n\n## ProForge task contract\n- " + "\n- ".join(hits)) if hits else ""


def get_protocol_block(prompt: str = "") -> str:
    """Return the base protocol + any matched task contract, or "" if disabled."""
    try:
        from src import settings as _settings
        if not _settings.get_setting("proforge_protocol_enabled", True):
            return ""
    except Exception:
        pass
    return PROFORGE_PROTOCOL + select_task_contract(prompt)
