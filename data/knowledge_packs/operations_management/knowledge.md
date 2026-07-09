# Operations Management

## Process design + optimization
- A process = inputs -> transformation -> outputs, with defined steps, owners, and handoffs.
- **Cycle time** = time to complete one unit; **lead time** = order to delivery; **throughput** = units per period; **takt time** = available time / customer demand (the pace you must produce to meet demand).
- **Little's Law**: WIP = throughput x lead time — cut WIP or raise throughput to shorten lead time.
- Map before you optimize: **value stream map** distinguishes value-added vs non-value-added time (VA time is often < 10% of lead time).
- Optimize the whole flow, not isolated steps; standardize before automating (automating a broken process scales the mess).

## Lean + Six Sigma
- **Lean** = maximize customer value, eliminate waste, improve flow, pull not push, pursue perfection (kaizen).
- **8 wastes (DOWNTIME)**: Defects, Overproduction, Waiting, Non-utilized talent, Transportation, Inventory, Motion, Extra-processing.
- **Six Sigma** = reduce variation + defects (target 3.4 defects per million opportunities); data-driven.
- **DMAIC** (improve existing process): **Define** (problem, scope, CTQ) -> **Measure** (baseline, data collection) -> **Analyze** (root cause) -> **Improve** (solutions, pilot) -> **Control** (sustain via SOPs, control charts).
- Tools: 5 Whys, fishbone (Ishikawa), Pareto (80/20), control charts (common vs special-cause variation), 5S (Sort/Set/Shine/Standardize/Sustain), poka-yoke (mistake-proofing), kanban.

## Supply chain
- **Procurement**: sourcing, supplier selection, POs, contracts, three-way match (PO + receipt + invoice). Total cost of ownership > unit price alone.
- **Logistics**: inbound + outbound transport, warehousing, distribution, last-mile; balance cost vs speed vs reliability.
- **Suppliers**: single vs multi-source (resilience vs price/volume), lead-time reliability, quality, financial stability; qualify + audit.
- **Bullwhip effect**: demand-signal distortion amplifies upstream as small demand changes cause large order swings; dampen with shared demand data, smaller batches, shorter lead times.

## Inventory management
- **EOQ** (economic order quantity) = √(2DS/H), where D = annual demand, S = order cost, H = holding cost/unit/yr — the order size minimizing total order + holding cost.
- **JIT** (just-in-time): inventory arrives as needed; minimizes holding cost + waste but fragile to disruption; needs reliable suppliers.
- **Safety stock** = buffer against demand/lead-time variability ≈ Z x σ_demand x √lead-time (Z from target service level).
- **Reorder point** = (avg daily demand x lead time) + safety stock.
- **ABC analysis**: A items (~80% of value, ~20% of SKUs) tight control; B moderate; C loose/bulk — focus effort by value.
- **Turnover** = COGS / avg inventory; higher = less capital tied up but watch stockout risk.

## Capacity + demand planning
- **Capacity** = max output achievable; **utilization** = actual / max; running near 100% kills flexibility + spikes queue time.
- Match supply to demand: **level** (steady output, absorb with inventory) vs **chase** (flex capacity to demand) strategies; often a hybrid.
- **Demand forecasting**: qualitative (expert, Delphi) + quantitative (moving average, exponential smoothing, seasonal decomposition); track forecast error (MAPE) + bias.
- **S&OP** (sales & operations planning): monthly cross-functional reconciliation of demand plan, supply plan, and finances.

## Quality management
- **Prevention > inspection**: build quality in; cost of quality = prevention + appraisal + internal failure + external failure (external is costliest).
- **SPC** (statistical process control): control charts separate common-cause (in-control) from special-cause (investigate) variation; don't tamper with a stable process.
- **Cp/Cpk** capability indices measure process spread vs spec limits (Cpk ≥ 1.33 commonly targeted).
- Standards: ISO 9001 (QMS); root-cause + corrective/preventive action (CAPA) for failures.

## KPIs + dashboards
- Ops KPIs: OTIF (on-time-in-full), throughput, cycle/lead time, first-pass yield, defect rate/PPM, OEE, inventory turns, capacity utilization, cost per unit, backorder rate.
- **OEE** = Availability x Performance x Quality (world-class ≈ 85%).
- Dashboard rules: tie metrics to objectives, mix leading + lagging indicators, show trend + target, avoid vanity metrics + metric overload; make owners accountable.

## Theory of Constraints (bottlenecks)
- System throughput is limited by its single tightest constraint (bottleneck); improvements elsewhere don't raise output.
- **5 focusing steps**: 1) **Identify** the constraint, 2) **Exploit** it (max its output, never starve/idle it), 3) **Subordinate** everything else to it, 4) **Elevate** it (add capacity), 5) **Repeat** (constraint moves — avoid inertia).
- Only a bottleneck's throughput = the system's throughput; time lost at the bottleneck is lost forever, time saved at a non-bottleneck is a mirage.

## SOPs + vendor management
- **SOPs**: documented, versioned, step-by-step procedures; reduce variation + training time + key-person risk; review + update on change.
- **Vendor management**: SLAs (uptime, lead time, quality), scorecards + QBRs, risk assessment (concentration, geo, financial), contracts + exit plans, relationship tiering by spend + criticality.

## Pitfalls -> Fix
- **Local optimization** (improving a step that isn't the constraint) -> apply Theory of Constraints; optimize the bottleneck + subordinate the rest to it.
- **No bottleneck focus** -> identify + exploit the constraint before adding capacity or automating anywhere.
- **Stockouts vs overstock whipsaw** -> compute reorder point + safety stock from demand/lead-time variability; use ABC to prioritize; share demand data to dampen bullwhip.
- **Running capacity at ~100%** -> queue time explodes (Little's Law); hold buffer capacity for variability + flexibility.
- **Automating a broken process** -> map + standardize + remove waste first; then automate the good process.
- **Inspecting quality in at the end** -> shift to prevention + poka-yoke + SPC; catch defects at the source (cheapest).
- **Vanity/too many KPIs** -> pick a few objective-linked metrics with owners, targets, and leading indicators.
- **Single-sourcing critical inputs for price** -> weigh TCO + resilience; dual-source or qualify backups for critical items.
- **Tribal knowledge, no SOPs** -> document + version procedures; reduces key-person risk + variation.
- **Chasing utilization as the goal** -> throughput + flow + on-time delivery matter; high utilization on a non-bottleneck just builds WIP.
- **Reacting to every data point** -> use control charts; don't tamper with common-cause variation (over-adjusting adds variation).
- **Forecast without measuring error** -> track MAPE + bias; feed error back into safety stock + planning.

## Continuous improvement
- **Kaizen**: small, frequent, front-line-driven improvements compound; make problems visible + safe to raise.
- **PDCA** (Plan-Do-Check-Act / Deming cycle): iterate improvements as controlled experiments.
- **Gemba**: go to where the work happens + observe reality; don't manage the process from a spreadsheet.
- **Standard work + visual management** (kanban boards, andon signals) expose deviations fast so problems surface early.

## Scheduling + flow
- **Push** (produce to forecast) risks overproduction + inventory; **pull** (produce to actual demand signal, e.g. kanban) limits WIP + surfaces problems.
- **Batch size**: smaller batches -> shorter lead time + faster feedback + less WIP, at higher changeover cost; reduce setup time (SMED) to enable small batches.
- **Level the load** (heijunka): smooth production to reduce the peaks/troughs that create firefighting + idle time.
- Queues form wherever arrival rate approaches service rate; variability + high utilization together explode wait time.

## Resilience + risk
- Map single points of failure (sole suppliers, one facility, key person); build redundancy for critical nodes.
- Buffer strategies: inventory, capacity, or time — choose deliberately per constraint + cost of stockout/downtime.
- Business continuity + contingency plans for supply disruption, demand shocks, and quality escapes.

Scale rigor to context: heavy Six Sigma suits high-volume repeatable processes; lightweight kaizen + SOPs suit small/variable operations.
