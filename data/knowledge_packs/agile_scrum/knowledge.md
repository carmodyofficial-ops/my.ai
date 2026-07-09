# Agile Scrum
## Roles
- Product Owner: owns Product Backlog + ordering + "what/why"; single decision-maker on priority; maximizes product value. Scrum Master: process coach + servant leader, removes impediments, protects team from scope injection, facilitates events. Developers (3-9): own "how" + the Sprint commitment; cross-functional, self-managing. One accountable PO, one SM per team.

## Events (time-boxed)
- Sprint: container, fixed length 1-4 wk (usually 2), no scope change that endangers the Sprint Goal. Next starts immediately after prior ends.
- Sprint Planning (<=8h/mo sprint): produces Sprint Goal + selected backlog + plan. Answers why (goal), what (items), how (tasks).
- Daily Scrum (15 min): devs re-plan toward the Sprint Goal; peer sync, not status-to-boss.
- Sprint Review (<=4h/mo): inspect Increment with stakeholders, adapt backlog. Working software demo, not slides.
- Sprint Retrospective (<=3h/mo): inspect people/process/tools; produce concrete improvement actions.

## Artifacts + commitments
- Product Backlog (commitment: Product Goal) — ordered, refined, emergent list of everything.
- Sprint Backlog (commitment: Sprint Goal) — selected items + plan; owned by Developers.
- Increment (commitment: Definition of Done) — usable, Done sum of completed items; can release any time.

## Backlog refinement
- Ongoing (~<=10% of capacity): split, estimate, clarify, order top items. Keeps top of backlog "ready".
- User story format: "As a <role>, I want <goal>, so that <benefit>." INVEST criteria: Independent, Negotiable, Valuable, Estimable, Small, Testable. Acceptance criteria (often Given/When/Then) define done-for-this-story. Split vertically (thin end-to-end slices), not by layer.
- Epic -> Story -> Task hierarchy: epics are large multi-sprint themes, split into stories that fit a sprint, decomposed into tasks in the Sprint Backlog.

## Estimation + flow metrics
- Story points: relative size (effort+complexity+uncertainty), often Fibonacci 1,2,3,5,8,13,21 (gaps grow to force coarser buckets on big items). Planning Poker to estimate; reveal simultaneously to avoid anchoring, discuss outliers.
- Techniques: reference/anchor story (peg a well-understood 3 or 5 as the baseline), triangulation (compare an item to several already-sized ones), affinity estimation (silently sort a large backlog into size groups fast), t-shirt sizes (S/M/L/XL) for epic-level/coarse work. Re-estimating already-Done items is waste. Points are team-relative — never an individual metric.
- Velocity: avg points completed/sprint (use last 3-6, or a range); use for that team's own forecasting, never as a cross-team productivity target (Goodhart — teams inflate points).
- Metrics beyond velocity: say-do ratio (committed vs actually delivered, aim ~0.8-1.0 and stable, not gamed high), sprint-goal success rate, escaped-defect rate, cycle time/throughput, team health/happiness. #NoEstimates: forecast from throughput (item count) when estimation adds no planning value.
- Burndown: remaining work vs time within a sprint. Burnup: done + scope over time (shows scope creep).
- Capacity planning: available person-days minus leave/meetings/support/on-call; select backlog to fit capacity + a buffer, not just historical velocity. Commit to the Sprint Goal + a realistic item set, not a point quota.

## Definition of Done / Ready
- DoD: shared quality gate an increment must meet (coded, reviewed, tested, integrated, docs) — not-Done work stays in backlog.
- DoR: entry criteria for pulling an item into a sprint (clear, estimated, testable, no blocking dependency).

## Sprint Goal
- Single coherent objective giving the sprint purpose + flexibility on exact scope. Enables saying "we can drop item X but still meet the goal."

## Values + pillars
- Empiricism pillars: Transparency, Inspection, Adaptation — every event is an inspect-and-adapt point. Scrum values: Commitment, Focus, Openness, Respect, Courage.

## Forecasting
- Release burnup / burndown across sprints projects a completion range from velocity trend. Prefer a range (optimistic/pessimistic velocity) over a single date. Re-forecast each sprint as backlog + velocity change.

## Spillover / carryover
- Unfinished item returns to the Product Backlog un-Done (no partial credit / no partial points); PO re-orders it — it is NOT automatically top of next sprint. Re-estimate only if understanding of scope changed, not for time already spent.
- Chronic carryover = over-commitment or stories too large. Fix: commit to the Sprint Goal (not an item count), split stories smaller, leave slack.

## Distributed / remote Scrum
- Single shared digital board as source of truth; camera-on for Review/Retro to build trust/safety. Async-friendly Daily (written update + short live sync) when timezones split.
- Concentrate synchronous events (Planning/Review/Retro) in overlap hours; record decisions + demos for absent members; keep teams small and, where possible, timezone-cohesive. Beware timezone handoffs degrading into a mini-waterfall.

## Scaling
- Add only when multi-team coordination on one product is real; don't scale a process a single team hasn't mastered. Prefer fewer dependencies (feature teams that slice vertically) over more coordination machinery.
- Scrum of Scrums: reps from each team meet 2-3x/wk to surface cross-team dependencies + integration risk (not status-to-boss).
- Nexus (Scrum.org): 3-9 teams, one Product Backlog + Product Owner, a Nexus Integration Team; Nexus events (Sprint Planning/Review/Retro, Nexus Daily) target the integrated Increment every sprint.
- LeSS: one PO, one backlog, cross-component feature teams, minimal added process. SAFe: heavier — ART, PI planning, cadence sync; powerful for large orgs but risks re-bureaucratizing (guard against command-and-control creep). Scrum@Scale: scale-free network of Scrums of Scrums.

## Scrum vs Kanban note
- Scrum = timeboxed batches + commitment to a Sprint Goal; Kanban = continuous flow + WIP limits, no sprint. Scrumban blends: Scrum cadence with Kanban pull + WIP limits.

## Pitfalls -> Fix
- **Daily standup = status report to manager**: kills team ownership. Fix: devs talk to each other about the Sprint Goal + blockers, not to the SM/manager.
- **Scrumfall (Water-Scrum-fall)**: big up-front design + late testing wearing Scrum labels. Fix: each sprint delivers a Done, potentially shippable increment slice-wise.
- **Retro with no action / same complaints monthly**: ceremony theater. Fix: pick 1-2 actionable improvements, assign owners, track next retro.
- **Chronic over-commitment**: pulling more than velocity supports; carryover every sprint. Fix: commit to a Sprint Goal + capacity-based selection; leave slack.
- **Velocity as a KPI across teams**: teams inflate points; comparison is meaningless (points are team-relative). Fix: use velocity only for that team's own forecasting.
- **PO absent / by committee**: ambiguous priorities, thrash. Fix: one empowered PO, available to the team, owns the ordered backlog.
- **Scope injected mid-sprint by managers**: destroys the commitment. Fix: SM shields the team; new work enters next sprint or via explicit re-planning.
- **No / vague Definition of Done**: "done" hides untested, un-integrated work -> debt. Fix: explicit, enforced DoD; not-Done items don't count.
- **Undefined-ready items pulled in**: sprint stalls on clarification. Fix: refine to DoR before planning.
- **Sprint Review as a status meeting, not a demo**: no real feedback. Fix: show working software, gather stakeholder input, adapt backlog.
- **Scrum Master as project manager assigning tasks**: recreates command-and-control. Fix: SM coaches + removes impediments; Developers self-organize task assignment.
- **Estimating in hours then treating points as hours**: false precision + pressure. Fix: keep points relative; forecast with velocity, not hour-summing.
- **No slack / 100% utilization**: no capacity to absorb surprises or improve. Fix: plan buffer + refinement + learning time.
- **Story points as a delivery target / individual score**: Goodhart — points inflate, quality drops, trust erodes. Fix: velocity is a team forecasting aid, not a KPI or per-person measure.
- **Same retro format + same complaints, low safety**: staleness, no candor. Fix: vary formats (Start/Stop/Continue, 4Ls, sailboat, timeline); set psychological safety first; act on 1-2 items.
- **Component teams handing off per feature**: every feature crosses team boundaries -> queues + integration lag. Fix: cross-functional feature teams that own a vertical slice end-to-end.
- **No refinement / all clarification in Planning**: Planning overruns, items enter unready. Fix: ongoing refinement (~<=10% capacity) keeps a Ready top-of-backlog.
- **Coordinating many teams before mastering one**: framework theater. Fix: prove single-team Scrum first; scale only for real cross-team dependencies, minimizing them.
