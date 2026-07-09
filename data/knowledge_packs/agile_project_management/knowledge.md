# Agile Project Management
## Managing adaptive delivery
- Value-driven, not plan-driven: fixed time+cost, flexible scope (inverted triangle vs waterfall).
- PM role shifts to servant leader / flow manager: remove impediments, protect the team, manage stakeholders, not assign tasks.
- Progressive elaboration: plan at multiple horizons — vision -> roadmap -> release -> iteration -> daily.
## Planning horizons (planning onion)
- Product vision -> product roadmap (quarters/themes) -> release plan (features across N sprints) -> iteration/sprint plan (stories) -> daily plan.
- Release planning: prioritized backlog + team velocity -> sprints needed = remaining points / velocity.
- Iteration planning: pull top backlog items into sprint up to capacity; define sprint goal.
## Velocity-based forecasting
- Velocity = story points completed per iteration (only DONE items count). Use a 3-sprint rolling average.
- Forecast date range: use min/max recent velocity to bound optimistic/pessimistic completion.
- Example: 120 points left, velocity 15-25/sprint -> 5 to 8 sprints remaining.
- Yesterday's Weather: assume next sprint ~ last sprint's velocity.
## Agile metrics
- Velocity: capacity/forecasting only — NOT a productivity target or cross-team comparison.
- Cycle time: work start -> done (lower = faster flow). Lead time: request -> done.
- Throughput: items completed per period. WIP: items in progress (cap it — Little's Law: cycle time = WIP / throughput).
- Burn-down: work remaining vs time. Burn-up: work done + scope line (reveals scope change; superior for stakeholders).
- Cumulative flow diagram (CFD): band widths show WIP and bottlenecks.
- Escaped defects, deployment frequency, DORA metrics for delivery health.
## Scaling frameworks (overview)
- SAFe (Scaled Agile Framework): most prescriptive; ART (Agile Release Train) of 50-125 people, PI (Program Increment) ~8-12 wks, PI Planning big-room event; levels: Team/Program/Large Solution/Portfolio.
- LeSS (Large-Scale Scrum): minimalist; one product backlog, one PO, multiple teams, one shared sprint; scales Scrum with fewest additions.
- Scrum@Scale: scale-free; Scrum of Scrums + Executive Action Team; separate scaling of "what" (PO org) and "how" (Scrum Master org).
- Nexus: 3-9 Scrum teams, Nexus Integration Team, integrated increment.
- Spotify model (tribes/squads/chapters/guilds) = an org culture snapshot, not a framework to copy.
## Hybrid / "wagile"
- Hybrid: predictive governance (fixed milestones, stage gates, budget) wrapping agile delivery inside phases.
- Water-scrum-fall: waterfall requirements + waterfall release, agile only in the middle — common, often an anti-pattern.
- Use hybrid when compliance/hardware/fixed-bid contracts require upfront commitments.
## Distributed / remote teams
- Overlap hours for ceremonies; async-first for the rest; shared digital board as single source of truth.
- Reduce handoffs; write decisions down; explicit definition of done + working agreements.
- Follow-the-sun handoffs need crisp interfaces; timezone spread raises cycle time — co-locate a feature within one team.
- Invest in relationship/trust building; camera-on ceremonies; document tribal knowledge for async members.
## Ceremonies the agile PM enables
- Backlog refinement: keep 1-2 sprints of ready, estimated, sliced stories ahead.
- Sprint/iteration planning, daily standup (coordination not status), review/demo (stakeholder feedback), retrospective (process improvement).
- Definition of Ready (entry) and Definition of Done (exit) gate stories; enforce to prevent carryover.
## Prioritization & backlog
- Ordered backlog is single source of truth; PO owns order, team owns estimates.
- Frameworks: WSJF (SAFe: Cost of Delay / job size), MoSCoW (Must/Should/Could/Won't), Kano, value vs effort.
- WSJF = (user-business value + time criticality + risk reduction/opportunity) / job duration — do highest first.
## Forecasting with Monte Carlo
- Simulate from historical throughput/velocity distribution -> "85% chance done by sprint N" instead of a single date.
- More honest than a point estimate; communicates uncertainty to stakeholders.
## Kanban for flow-based delivery
- Visualize work, limit WIP, manage flow, make policies explicit, improve collaboratively.
- Pull system: new work starts only when capacity frees; classes of service (expedite/standard/fixed-date) prioritize.
- Metrics: cycle time distribution, throughput, flow efficiency (touch time / total time), aging WIP.
## Definition of Done & technical health
- Shared DoD (tested, reviewed, integrated, documented, deployable) prevents hidden carryover and false velocity.
- Manage technical debt as a first-class backlog concern; unmanaged debt slows velocity over time.
## Value & outcomes
- Track outcomes (adoption, business KPIs) over output (features shipped); tie roadmap to measurable value.
- Fast feedback loops: demo to real users each iteration; pivot on evidence, not opinion.
## Pitfalls -> Fix
- **Velocity as a productivity KPI**: teams inflate points (point inflation), quality drops. Fix: use velocity only for the team's own forecasting; never compare teams or set point targets.
- **Comparing velocity across teams**: points are team-relative and meaningless across teams. Fix: compare outcomes/throughput, not points.
- **Fixed scope + fixed date + fixed team**: it's waterfall in agile costume. Fix: make scope the flex variable; prioritize the backlog ruthlessly.
- **Dark/fake agile (mechanical ceremonies, no empowerment)**: standups become status reports to a manager. Fix: team owns the "how"; standups coordinate the team, not report upward.
- **No product owner / proxy PO with no authority**: backlog decisions stall. Fix: empower a single decision-making PO available to the team.
- **Skipping retrospectives or never acting on them**: same impediments recur. Fix: end each with 1-2 committed, owned improvement actions; track them.
- **Carrying unfinished work as partial velocity**: corrupts forecasting. Fix: only 100%-done items count toward velocity.
- **Scaling framework adopted whole before basic agile works**: amplifies dysfunction. Fix: get single-team flow healthy first; adopt the minimum scaling needed.
- **Unbounded WIP**: everything in progress, nothing finishing; long cycle times. Fix: set WIP limits; pull, don't push; finish before starting.
- **PM assigning tasks and micromanaging**: kills self-organization. Fix: servant leadership — surface impediments, let the team pull work.
- **Utilization maximized to 100%**: no slack, cycle time explodes, no innovation. Fix: leave buffer capacity; optimize flow, not busyness.
- **Big-bang release after many "done" sprints**: integration/UAT surprises. Fix: keep increments potentially shippable; integrate continuously.
