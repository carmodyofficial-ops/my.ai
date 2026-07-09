# Implementable Development Stories

## What "implementable" means
- A dev OR autonomous coding agent can pick it up and **build it to done with zero clarifying questions** — every decision needed to write code is already answered or bounded.
- **Ambiguity test**: for each AC and note, ask "could two competent engineers build materially different things and both claim they satisfied this?" If yes → underspecified; pin it down.
- **Clarifying-question count = the quality metric**. Great story → 0 questions. 1–2 → refine. 3+ → not ready; it's a draft or an epic. Track questions asked in refinement; recurring ones reveal template gaps.
- Implementable ≠ over-specified. Specify **WHAT + constraints + interfaces/contracts + verification**; leave **HOW** (algorithm, local naming, internal structure) to the implementer where reversible/safe.
- Litmus: title, value, in/out scope, testable AC, affected components + contracts, deps, NFRs, "done when" checks. Missing any → expect questions.

## Anatomy + full template
```md
# [Story] <outcome-oriented title: capability + object, no solution>
_ID:_ PROJ-123  _Type:_ Story  _Size:_ 3 pts (~½ day)  _Epic:_ PROJ-90

## Value narrative
As a <named persona>, I want <capability>, so that <measurable benefit>.
Value test: if the "so that" is empty or circular ("so that it works"), stop.

## Context / background
- Why now: <driver — bug, OKR, dependency unblocked>.
- Links: design <url>, related PROJ-88, ADR-14, API spec §3.
- Current behavior: <what happens today> → Desired: <what should happen>.

## Scope
IN:  <explicit list of what this story delivers>
OUT: <explicit non-goals — the boundary that prevents scope creep & gold-plating>

## Acceptance criteria (testable)
1. Given <state>, When <action>, Then <observable outcome>.
2. Rule: <invariant that must hold> (e.g., "email unique, case-insensitive").
3. Edge: <empty / max / concurrent / offline / permission-denied>.
4. Negative: <invalid input> → <specific error + code/message>.

## Technical notes / approach
- Affected: `src/api/users.ts`, `src/db/migrations/`, `POST /v1/users`.
- Contract: request/response schema, status codes, error shape.
- Data: new column `users.verified_at TIMESTAMPTZ NULL`; migration + rollback.
- Constraints: reuse `AuthService`; don't add deps; follow repo error pattern.

## Dependencies / blockers
- Needs PROJ-88 (email service) merged. Feature-flag `signup_v2`.

## Non-functional
- p95 < 200ms; rate-limit 5/min/IP; log audit event; a11y AA; no PII in logs.

## Done when (verification)
- [ ] `npm test users` green (new tests cover AC 1–4).
- [ ] `curl POST /v1/users` returns 201 + body per contract (example below).
- [ ] Migration up+down run clean on a fresh DB.
- [ ] Flag off = old path unchanged.

## Risks / assumptions
- Assumes SMTP creds in vault. Risk: email provider quota — mitigate w/ retry queue.
```

## Field-by-field rules
- **Title**: outcome + object, not solution. "Persist wishlist across sessions" not "Add Redis wishlist cache". No "and" (compound = split).
- **Value narrative**: named persona (not "user"); capability = a verb the persona does; benefit measurable/checkable. Apply the value test.
- **Context**: enough for someone with no meeting history to know *why now* + *where to look*. Link, don't inline, large docs.
- **Scope IN/OUT**: OUT is the highest-leverage field — it kills ambiguity and gold-plating. List tempting-but-excluded work explicitly ("OUT: bulk import; social login").
- **AC**: see quality section. Mix Given/When/Then (behavior) + Rule-based (invariants). Every AC independently testable.
- **Technical notes**: name real files/modules/endpoints, contracts (schemas, status codes, error shapes), data changes (columns, migrations, indexes), and constraints (reuse X, no new deps, follow pattern Y). This is what removes the "figure it out" gap — without prescribing every line.
- **Dependencies**: hard blockers + flags + env/secrets. If blocked, say so; don't ship a story that can't start.
- **NFR**: perf budget, security, a11y, observability, i18n, limits — as concrete numbers, not "fast".
- **Done when**: *observable* checks — commands to run, endpoints to hit, states to see. Distinct from AC (AC = behavior contract; Done-when = how to confirm it + DoD hygiene).
- **Estimate/size**: right-sized (below). **Risks/assumptions**: surface unknowns so the implementer isn't blindsided.

## INVEST → implementability
- **I**ndependent: buildable without waiting on a sibling story; declare deps if not.
- **N**egotiable: card states WHAT + constraints; HOW stays open where safe.
- **V**aluable: thin **vertical slice** (DB→API→UI), demoable on its own.
- **E**stimable: enough tech detail to size — unsizable = missing info = not implementable.
- **S**mall: fits **one iteration / one agent session** (see right-sizing).
- **T**estable: every AC has a pass/fail check; if you can't test it, you can't accept it.

## Right-sizing
- Human: ≤ one sprint, ideally 1–3 days; ≤ ~5–6 AC. >13 pts or >6 AC → split (SPIDR: Spike, Paths, Interfaces, Data, Rules).
- Agent: fits one context/session — bounded file set, single coherent change, verifiable end-to-end in one run. If it needs >~5–8 files touched across unrelated concerns, split.
- "And" in the title, multiple personas, or golden-path-only-plus-later = split signals.

## Story vs task vs epic vs spike vs bug
- **Story**: user-visible vertical slice of value. Full anatomy above.
- **Task**: sub-work of a story, no standalone user value ("write migration", "add index"). Format: action + target + done-check; no As-a narrative.
- **Epic**: multi-sprint container; not directly implementable — decompose to stories first. Format: goal + success metric + child stories.
- **Spike**: time-boxed research to *remove* unknowns so a story becomes implementable. Format: question(s) to answer + timebox + deliverable (decision/doc/prototype). Output feeds a real story; spike itself ships no feature.
- **Bug**: repro + expected vs actual + environment/version + severity. Format: steps to reproduce → observed → expected → scope of fix. AC = "no longer reproduces" + regression test.
- Rule: force a Story onto research → underestimated; force it onto internal-only work → fake value. Label honestly.

## Detail balance (specify what, not every line)
- SPECIFY: behavior, inputs/outputs, contracts/schemas, error handling, edge cases, NFR budgets, affected components, reuse/pattern constraints, verification.
- LEAVE OPEN: internal algorithm choice, private helper naming, code layout within a module, micro-optimizations — *where the choice is reversible and low-risk*.
- PIN DOWN even normally-open things when they're externally observable or hard to change: public API shape, DB schema, wire format, user-facing copy, security-relevant logic.
- Heuristic: over-specify irreversible/interface decisions; under-specify reversible/internal ones. Ambiguity that can't produce two divergent *observable* results is fine to leave.

## Human dev vs autonomous coding agent
- Human: more business narrative + why; can infer conventions, ask in standup, read tribal context. Lighter on repro/paths.
- Agent: **explicit file paths**, exact commands to run/verify, repro steps as literal commands, contracts as copy-pasteable schemas, less prose "why", no reliance on hallway conversation. State the branch, the flag, the test command. Assume no memory of prior meetings.
- Both share the same skeleton; agent stories just push everything toward *executable specificity*. Deep dive → **agent_ready_work_items** pack.

## Acceptance criteria quality
- Testable (objective pass/fail), complete (happy + edge + negative), atomic (one behavior each), observable (checks state/output, not implementation).
- Cover: empty/zero, max/overflow, boundary, concurrent, permission-denied, offline/timeout, duplicate, invalid-type. Golden-path-only = incomplete.
- Prefer Given/When/Then for flows; Rule lists for invariants/validation. Deep dive → **acceptance_criteria_and_bdd** pack.

## Slicing an epic into implementable stories
- Start from the **story map** backbone; pick the thinnest walking-skeleton path first (one persona, happy path, one data type).
- Cut on SPIDR seams; each cut must still yield a demoable vertical slice, not a layer.
- Example — Epic "AUTH-90 Account security" → stories: `signup + email-verify` (AUTH-212, above); `password reset via email` (Paths); `login lockout after N fails` (Rules); `remember-this-device` (Data/Interfaces); `admin manual-verify` (deferred, was scope-OUT of 212).
- Each child inherits the epic link (traceability), owns its own AC ≤ ~6, and is independently pullable. Sequence only true blockers; keep the rest parallelizable.
- Anti-pattern: horizontal cuts ("DB story", "API story", "UI story") — none is demoable and none is independently valuable.

## Estimation as an implementability signal
- If you **can't size it**, it's missing information — treat unsizability as a not-ready flag, not a math problem.
- Wide spread in planning poker (2 vs 8) = hidden ambiguity or scope disagreement → discuss, then re-scope or spike; don't average.
- Points measure effort + complexity + uncertainty, not hours. High uncertainty → spike to convert unknowns into a sizable story.
- A story that keeps growing during refinement was an epic; stop padding it and split.

## Refinement flow (draft → ready)
- Draft (PO/author) → refine w/ dev + QA (Three Amigos) → add AC + tech notes + Done-when → size → meets DoR → pull.
- Keep ~1–2 iterations of ready stories at the top of the backlog; refine top-down, don't groom the whole list.
- Every clarifying question raised in refinement is a defect in the story — answer it *in the card*, then note if the template should change to prevent recurrence.

## Traceability & story mapping
- Chain: **Epic → Feature → Story → AC → Test**. Link IDs both ways so a failing test traces to the story to the business goal.
- Story map (Patton): activity backbone left→right, stories by priority top→down; slices = releases. Locates each story in the whole so scope-IN/OUT is defensible and gaps surface.
- Put the epic link + related-story links in Context; put test names in Done-when → full traceability without a separate tool.

## Worked example (complete, implementable)
```md
# [Story] Email-verify new signups before first login
_ID:_ AUTH-212  _Type:_ Story  _Size:_ 3 pts  _Epic:_ AUTH-90 (Account security)

## Value narrative
As a new self-serve user, I want to confirm my email via a link,
so that I can access my account and we block typo'd/fake addresses.
Value test: reduces bounced onboarding emails + fake accounts (tracked KPI).

## Context
- Why now: 8% of signups use unreachable emails (support ticket #4471).
- Links: flow design figma.com/x, API spec §Auth, ADR-14 (token strategy).
- Today: account active immediately. Desired: inactive until verified.

## Scope
IN:  send verification email on signup; verify-link endpoint; block login
     until verified; resend link (rate-limited).
OUT: social login, admin manual-verify, changing existing accounts,
     email template redesign.

## Acceptance criteria
1. Given a valid new signup, When the account is created, Then a verification
   email is queued and the account is `status=pending`.
2. Given a valid unexpired token, When user hits GET /v1/auth/verify?token=,
   Then account → `active`, token invalidated, redirect to /welcome.
3. Rule: token expires after 24h and is single-use.
4. Edge: expired/used/unknown token → 410 + "link expired, request a new one".
5. Negative: login attempt while `pending` → 403 `EMAIL_UNVERIFIED`.
6. Rule: resend limited to 3/hour/account; 4th → 429.

## Technical notes
- Affected: `src/auth/signup.ts`, new `src/auth/verify.ts`,
  `POST /v1/auth/signup`, new `GET /v1/auth/verify`, `POST /v1/auth/resend`.
- Data: `users.status ENUM('pending','active')` default 'pending';
  `email_tokens(token PK, user_id FK, expires_at, used_at NULL)`. Migration+rollback.
- Contract: verify success → 302 /welcome; failures → JSON {code,message}.
- Reuse: `EmailService.send()`, existing `RateLimiter`, repo error middleware.
- Constraints: token = 32-byte URL-safe random (not JWT); no new deps.

## Dependencies
- EmailService live (AUTH-201, merged). Flag `email_verify`.

## Non-functional
- Token compare constant-time. Verify endpoint p95 < 150ms. Audit-log verify
  + resend. No token value in logs. Links a11y (real <a>, descriptive text).

## Done when
- [ ] `npm test auth/verify` green — covers AC 1–6.
- [ ] `curl "/v1/auth/verify?token=BAD"` → 410 + JSON body.
- [ ] Fresh-DB migration up+down clean; existing users unaffected (stay active).
- [ ] Flag off → signup path unchanged (account active immediately).

## Risks / assumptions
- Assumes SMTP quota headroom. Risk: email delay frustrates users →
  show "check your inbox / resend" state (covered by resend AC).
```

## Pitfalls -> Fix
- **Vague value** ("improve UX", "so that it works"): unfalsifiable benefit. Fix: state a measurable/observable outcome or a tracked KPI; if none exists, question the story.
- **No scope-OUT**: implementer guesses the boundary → scope creep or gold-plating. Fix: always list explicit non-goals, including tempting adjacent work.
- **Untestable AC** ("should be fast", "user-friendly"): no pass/fail. Fix: numbers + Given/When/Then; every AC gets a check in Done-when.
- **Hidden complexity**: looks 2 pts, hides auth/migration/integration. Fix: spike first, or split; surface in Risks; re-size after tech notes.
- **Tech-free story**: no files, contracts, or data — reads like a PRD line. Fix: add Technical notes naming components + contracts; if unknown → spike.
- **Over-prescription / every-line spec**: dictates private helpers & algorithm. Fix: specify WHAT + interfaces + constraints; leave reversible HOW to implementer.
- **Gold-plating**: builds beyond scope ("added dark mode too"). Fix: enforce scope-OUT; extra ideas → new backlog items, not this story.
- **"Developer will figure it out"**: pushes decisions downstream → wrong guess or a question. Fix: answer it in the story; that's the whole point of implementable.
- **Story is really an epic**: 15 AC, multiple personas, "and". Fix: split on a SPIDR seam; each child a thin vertical slice ≤ ~6 AC.
- **Missing verification**: no way to confirm done → disputes at review. Fix: Done-when with runnable checks (commands, endpoints, observable states).
- **Golden-path only**: no edge/negative AC. Fix: add empty/max/concurrent/permission/invalid cases.
- **Unresolved dependency**: story can't start (blocked on unmerged work). Fix: mark blocked, sequence it, or spike the unknown; don't pull it into the iteration.
- **AC written after coding**: story judged by what was built, not intended. Fix: AC + Done-when agreed in refinement (Definition of Ready gate).
- **Solution in the title**: "Add Redis cache" prescribes HOW as the goal. Fix: title the outcome ("Serve wishlist reads <50ms"); let approach be negotiable in tech notes.
- **Stale context links**: dead figma/spec URLs → questions. Fix: verify links at refinement; inline the load-bearing decisions so the story survives link rot.

## Definition of Ready (gate before pull)
- [ ] Outcome title, value narrative w/ passing value test.
- [ ] Scope IN + OUT explicit. AC testable, cover edge+negative.
- [ ] Tech notes name components/contracts/data. Deps/blockers resolved or flagged.
- [ ] NFRs quantified. Done-when has runnable checks. Sized, fits one iteration/session.
- [ ] Predicted clarifying-question count = 0.
