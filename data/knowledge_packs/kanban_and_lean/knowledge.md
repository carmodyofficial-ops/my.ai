# Kanban and Lean
## Kanban board
- Visualize the workflow as columns = process states. Example flow:
```
Backlog | Ready | Dev (WIP<=3) | Review (WIP<=2) | Test (WIP<=2) | Done
```
- Cards = work items; move left->right as a pull system. Board must mirror the real process, including handoffs + queues.

## Core practices
- Visualize work. Limit WIP. Manage flow. Make policies explicit. Implement feedback loops. Improve collaboratively (evolutionary, start where you are — no prescribed roles).

## WIP limits (pull, not push)
- Cap items per column/state. A downstream pull frees a slot; only then does upstream pull new work. Prevents overload, exposes bottlenecks (work piles before the constrained column).
- Lower WIP -> shorter cycle time, faster feedback, less context-switching. Too-low WIP starves flow.

## Flow metrics
- Lead time: customer request -> delivered (clock the customer feels).
- Cycle time: work started -> finished (team's active time).
- Throughput: items completed per unit time (e.g. 12 items/wk).
- WIP: items in progress now.
- Aging WIP: how long in-progress items have been open — flags stuck work.
- Cumulative Flow Diagram (CFD): stacked area of items per state over time. Band width = WIP; horizontal gap = approx lead time; widening band = growing WIP/bottleneck; parallel bands = stable flow.

## Little's Law
- Average WIP = Throughput x Cycle time -> Cycle time = WIP / Throughput. Lever: cut WIP to cut cycle time at fixed throughput. Basis for why WIP limits speed delivery.
- Worked example:
```
WIP=20, throughput=5 items/wk -> cycle time = 20/5 = 4 wk.
Halve WIP to 10 (same throughput)  -> 10/5 = 2 wk.  (2x faster, no extra people)
```
- Holds only for a stable system (arrivals ≈ departures, consistent units); don't apply mid-explosion when WIP is climbing.

## Flow efficiency
- Flow efficiency % = active/touch time ÷ total lead time × 100. Knowledge work is often 5-40% — most elapsed time is waiting in queues, not being worked.
- Biggest lever is usually removing wait (queues, handoffs, blockers), not making people type faster. Low efficiency + long lead time = attack queues; measuring it exposes hidden waiting states.

## Lean principles (Poppendieck / TPS)
- Eliminate waste (muda: partially-done work, extra features, relearning, handoffs, delays, task-switching, defects). Amplify learning. Decide as late as possible (defer commitment). Deliver as fast as possible. Empower the team. Build integrity in. See the whole (optimize the system, not local parts).
- Related: pull, one-piece flow, kaizen (continuous improvement), reduce batch size, limit queues.

## Blockers + swarming
- Mark blocked cards explicitly (flag/color); track blocker clustering (Pareto) to attack recurring causes. Swarm: multiple people finish the highest-priority/oldest in-progress item before starting new work.

## Service Level Expectation (SLE)
- SLE = forecast like "85% of items finish within 8 days," derived from the cycle-time distribution (percentiles). Communicates predictability without estimating each item.

## Classes of service
- Prioritize by cost-of-delay/policy: Expedite (drop-everything, own swimlane), Fixed Date (deadline-driven), Standard (FIFO/value order), Intangible (low urgency now, e.g. tech debt). Explicit policies per class.

## Explicit policies (examples)
- Written, visible on/beside the board — the rules for pull, done, and prioritization. Ambiguity kills pull systems.
```
Pull into Dev: only if column WIP<3 AND item meets Ready (DoR).
Done (per column): merged to main + tests green + deployed to staging.
Expedite: max 1 system-wide; bypasses WIP; requires a note on why + post-hoc review.
Aging: item past its SLE gets a red flag and is discussed first at standup.
```

## Upstream / discovery kanban
- Upstream (discovery) kanban manages ideas/options BEFORE the commitment point; delivery kanban starts at commitment (where the team pledges to deliver).
- Options are "real options": keep them open, commit at the last responsible moment, discard freely. Abandoning an un-committed option is cheap; abandoning committed work is waste. Feed delivery from a small, curated Ready buffer via replenishment.

## Kanban Maturity Model (brief)
- Evolve, don't install: visualize (start where you are) -> WIP limits + explicit policies -> manage flow with SLEs + fit-for-purpose classes -> data-driven improvement/forecasting. Institutionalize a level before optimizing the next; skipping steps regresses under pressure.

## Queueing theory (why WIP hurts)
- Utilization near 100% makes queue length + wait time explode nonlinearly (Kingman's formula intuition). High utilization != high throughput of finished work. Variability amplifies the effect — reduce it (smaller items, fewer priorities) and leave slack.

## Cost of delay + WSJF
- Cost of Delay: value lost per unit time an item is not delivered. WSJF (Weighted Shortest Job First) = Cost of Delay / job size — sequence by highest WSJF to maximize value delivered. Drives class-of-service + ordering decisions.

## Kanban cadences / feedback loops
- Daily standup (flow-focused: walk the board right-to-left, unblock aging items), replenishment meeting (pull into Ready), delivery/release cadence, service-delivery + operations reviews, risk review. Decouple these cadences instead of one sprint boundary.

## Kanban vs Scrum
- Cadence: Scrum = fixed timeboxed sprints; Kanban = continuous flow, no required iterations.
- Commitment: Scrum commits sprint scope; Kanban pulls on capacity.
- Change: Scrum discourages mid-sprint change; Kanban re-prioritizes anytime (next pull).
- Roles: Scrum prescribes 3 roles; Kanban prescribes none.
- Metrics: Scrum velocity/burndown; Kanban lead/cycle time, throughput, CFD.
- Board: Scrum board resets per sprint; Kanban board persists.
- Scrumban: Scrum structure + Kanban pull/WIP limits.

## Pitfalls -> Fix
- **No WIP limits ("Kanban board" = just a Trello)**: everything in-progress, nothing finishing. Fix: set + enforce per-column WIP caps; block pulling when full.
- **Board doesn't match reality**: hidden queues/handoffs invisible, so bottlenecks stay hidden. Fix: model actual states incl. waiting/queue columns; add explicit policies.
- **Starting new work instead of finishing**: high WIP, long cycle time, context-switch tax. Fix: "stop starting, start finishing"; swarm on the blocked/oldest item.
- **Ignoring aging WIP**: old cards silently rot mid-board. Fix: track item age; act when it exceeds the service-level expectation.
- **Bottleneck ignored, upstream keeps pushing**: queue balloons before the constraint. Fix: subordinate to the constraint (Theory of Constraints); rebalance capacity, don't feed it.
- **Local optimization**: one column hyper-efficient, system slow. Fix: optimize end-to-end flow (see the whole), measure lead time.
- **Everything is "expedite"**: class of service loses meaning, flow thrashes. Fix: cap expedite lane (e.g. 1 at a time); enforce class policies.
- **Measuring utilization not flow**: 100% busy people = long queues (queueing theory). Fix: manage for flow + short cycle time, leave slack.
- **Estimating heavily in Kanban**: wasted effort. Fix: forecast probabilistically from throughput/cycle-time distribution (e.g. Monte Carlo), not point estimates.
- **Big batches / large stories**: long cycle times, lumpy CFD. Fix: reduce batch size; split items to flow smoothly.
- **No feedback loops / no kaizen**: WIP limits set once, never tuned. Fix: regular flow reviews; adjust limits + policies from CFD + metrics.
- **WIP limits set but routinely breached**: no real pull; overload returns silently. Fix: make a breach visible + blocking; treat it as a signal to swarm/unblock, not an excuse to raise the limit.
- **Per-person WIP limits**: rewards individual busyness, not system flow. Fix: limit the column/system; idle time that protects flow is fine.
- **Replenishing only on a fixed sprint boundary**: options go stale, Ready starves or bloats. Fix: replenish on demand / short cadence when Ready runs low; decouple replenishment from delivery cadence.
- **Implicit / unwritten policies**: pull + priority decisions are inconsistent and personal. Fix: write explicit policies on the board; review them in flow reviews.
- **Optimizing touch time, ignoring wait**: tiny gains while queues dominate. Fix: measure flow efficiency; attack waiting states (queues, handoffs, blockers) first.
