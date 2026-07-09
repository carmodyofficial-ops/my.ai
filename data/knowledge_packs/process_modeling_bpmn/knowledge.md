# Process Modeling & BPMN
## BPMN core elements
- **Events** (circles): thin ring = **start**, double ring = **intermediate**, thick ring = **end**. Typed by icon: message, timer, error, signal, terminate.
- **Activities** (rounded rectangles): **task** (atomic) or **sub-process** (collapsed, marked with +). Markers: user, service, script, send/receive, manual.
- **Gateways** (diamonds): decision/merge points.
  - **XOR** (X, exclusive): one path — mutually exclusive conditions.
  - **AND** (+, parallel): all paths simultaneously; both split and join required.
  - **OR** (O, inclusive): one or more paths.
  - **Event-based**: path chosen by which event fires first.
  - Gateways route flow; they don't "do work" and shouldn't hold text like tasks.
- **Flows**: **sequence flow** (solid arrow, within a pool), **message flow** (dashed arrow, across pools), **association** (dotted, to artifacts).
- **Pools & lanes (swimlanes)**: pool = a participant/organization; lanes = roles/departments within it. Activities sit in the lane of whoever performs them. Cross-pool communication = message flow only.
- **Artifacts**: data objects, data store, group, text annotation.
## Swimlane discipline
- Every task lives in exactly one lane = clear ownership. Handoffs = flow crossing a lane boundary (common failure/delay points). Two pools when parties are independent orgs (e.g., Customer vs Company); lanes when same org.
## As-is vs to-be
- **As-is**: model the current process exactly as it runs (including workarounds). Baseline for pain points, cycle time, handoffs, rework loops.
- **To-be**: redesigned target process. Diff reveals removed steps, automation, new controls. Don't skip as-is — you can't improve what you haven't mapped.
## Happy path + exceptions
- Draw the **happy path** (normal successful flow) as the spine, left-to-right.
- Then add **exception/alternate flows**: rejections, timeouts, errors, retries, escalations, cancellations via boundary events or XOR gateways. Unmodeled exceptions are where real processes break.
## Use case modeling (complementary)
- **Use case**: actor achieves a goal via the system. Diagram shows actors, use cases (ovals), `<<include>>` (mandatory sub-behavior), `<<extend>>` (optional/conditional), generalization.
- **Use case spec**: name, actors, preconditions, **main success scenario** (numbered steps), **alternate/exception flows**, postconditions. Text carries the detail; the diagram just maps scope.
- BPMN = how the process flows across roles/time; use case = what goal an actor gets from the system.
## Choosing the notation
- **BPMN**: multi-role business processes, handoffs, orchestration, need a standard/executable model. Use when swimlanes and gateways matter.
- **Flowchart**: simple linear/decision logic, single actor, quick sketch. No standard semantics.
- **User-journey map**: experience-focused — stages, actions, thoughts, emotions, pain points, touchpoints across time. Use for UX/CX, not system logic.
- **Use case diagram**: scope of system functionality and actor goals.
- **Value stream map**: lean/manufacturing flow with cycle time, wait time, and value-add vs waste per step.
- Match fidelity to audience: executives want high-level; implementers want detail.
## Level of detail / decomposition
- **Level 0**: end-to-end value chain on one page (5–8 high-level steps).
- **Level 1**: each step expanded into a sub-process with roles and decisions.
- **Level 2+**: task-level detail only where it drives implementation or automation.
- Keep any single diagram to roughly one screen / ~10 activities; collapse the rest into sub-processes.
## Analyzing a process (not just drawing)
- Measure per step: **cycle time**, **wait/queue time**, **rework rate**, **handoff count**, **cost**. Handoffs and queues are the usual bottlenecks.
- Find waste: duplicate data entry, unnecessary approvals, loop-backs, waiting, manual steps ripe for automation.
- To-be redesign levers: eliminate steps, parallelize (AND gateway), automate, self-service, remove approvals, reduce handoffs.
## Use case relationships (detail)
- `<<include>>`: base use case always invokes shared behavior (e.g., "Place order" includes "Authenticate").
- `<<extend>>`: optional/conditional behavior triggered at an extension point (e.g., "Apply coupon" extends "Checkout").
- **Generalization**: a specialized actor/use case inherits from a general one.
- Keep the diagram for scope; put the numbered main/alternate flows in the use-case text.
## Worked flow shape
- Start event -> validate -> XOR gateway (valid? no -> reject end event; yes -> continue) -> perform work (possibly parallel via AND) -> notify -> end event. Boundary timer/error events hang off long-running tasks for escalation.
## Naming conventions
- **Tasks**: verb + object ("Approve invoice", "Send confirmation"). Never a bare noun or a system name.
- **Events**: past-participle state ("Order received", "Payment failed").
- **Gateways**: phrase the decision as a question ("Credit approved?") with each outgoing flow labeled by the answer.
- **Pools/lanes**: participant or role names, not activities.
## Reading a model / review checklist
- Exactly one start trigger; every path reaches an explicit end event; no dangling activities.
- Every AND-split has a matching join; every XOR branch condition is labeled and mutually exclusive.
- Cross-pool arrows are dashed message flows; intra-pool arrows are solid sequence flows.
- Each task sits in the correct performer's lane; handoffs (lane crossings) are intentional, not accidental.
- Exceptions modeled for long-running or failure-prone steps; no infinite loops without an exit.
## Common process patterns
- **Approval loop**: submit -> review -> XOR (approve/reject-back-for-rework); cap rework iterations.
- **Escalation**: boundary timer event fires if a task isn't done in time -> route to supervisor.
- **Parallel fork-join**: AND gateway splits independent work, AND gateway joins before the next step.
- **Compensation**: undo a completed step (refund a charge) when a later step fails.
## Pitfalls -> Fix
- **Over-detail / boiling the ocean**: modeling every click at level 0. Fix: decompose in layers — high-level first, sub-processes for detail; hide what the audience doesn't need.
- **Missing exception paths**: only the happy path drawn. Fix: for each activity ask "what if it fails/times out/is rejected?"; add boundary/error events.
- **Gateway misuse**: a diamond that both decides and does work; unlabeled XOR branches; split without a merge. Fix: gateways only route; label every condition; pair splits with joins (esp. AND).
- **No swimlanes / unclear ownership**: who does what is invisible. Fix: use pools/lanes; place each task in the performer's lane.
- **Sequence flow across pools**: solid arrow between organizations. Fix: use message flow (dashed) between pools; sequence flow stays within one pool.
- **Dangling flows / no end event**: activities with no clear start or terminus. Fix: exactly one start trigger per process, explicit end event(s) for each outcome.
- **Modeling to-be without as-is**: redesign on assumptions. Fix: baseline current state first; quantify (cycle time, rework rate).
- **Ambiguous labels**: activities named with nouns ("Invoice") not verb+object ("Send invoice"). Fix: name tasks verb-object; name events as states.
- **Wrong notation for purpose**: BPMN for a UX emotion map, or a flowchart for a 5-role process. Fix: pick notation by audience and intent.
- **Deep nesting hidden**: everything crammed on one page. Fix: collapse into sub-processes; keep one diagram to ~one screen / ~10 activities.
