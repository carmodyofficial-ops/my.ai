# Product Management: Request -> Buildable Spec

## 1. Start with the problem, not the solution
Define the **job to be done**: *who* (specific user), *what pain*, *what outcome*. No solution yet.
> User: on-call eng. Pain: misses alerts at night. Outcome: never miss a SEV1.

## 2. User stories + acceptance criteria
`As a <role>, I want <goal> so that <benefit>.`
Acceptance = **Given/When/Then**, testable, unambiguous.
> Given a SEV1 fires, When I'm on-call, Then I get a push within 30s.
"Fast" / "easy" / "intuitive" aren't criteria. Numbers and states are.

## 3. Scope / MVP
Smallest thing that delivers core value **and lets you learn**. Cut the rest to "later", don't delete it. Write **non-goals** explicitly so scope can't drift silently.

## 4. Prioritize
- **Impact x Effort 2x2** -> do high-impact/low-effort first.
- **MoSCoW**: Must / Should / Could / Won't (Won't = on record).
- **RICE** = Reach·Impact·Confidence / Effort.

## 5. Requirements quality
Specific, measurable, testable. Capture the **why** (it survives when details change). Spec edge cases + **error states**, not just happy path: empty, offline, duplicate, denied, timeout.

## 6. Success metrics
State up front *how you'll know it worked*. Leading (signups today) vs lagging (retention in 90d). No metric = you can't tell ship from fail later.

## 7. Question the request
Is the literal ask the real need? Trace it to the JTBD; offer the better thing.
> Ask: "add CSV export." Need: "see totals" -> a dashboard beats export.
Give stakeholders **tradeoffs**, not a flat yes/no.

## Gotchas
- Solutioning before understanding the problem.
- Vague/untestable requirements.
- Scope creep & gold-plating (polishing what doesn't matter).
- No defined success metric.
- Ignoring non-happy-path.
- Building what's asked vs what's needed.
