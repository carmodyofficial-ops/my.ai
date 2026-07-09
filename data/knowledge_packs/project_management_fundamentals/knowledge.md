# Project Management Fundamentals
## Triple constraint (iron triangle)
- Scope + Time + Cost, bounded by Quality in the center; change one, at least one other moves.
- Fixed-scope projects flex time/cost; fixed-date projects flex scope. You cannot fix all three.
- Add "resources" and "risk" for the six-constraint model.
## Lifecycle (process groups)
- Initiate -> Plan -> Execute -> Monitor & Control -> Close. Monitor & Control runs concurrently with Execute, not after.
- Initiate: charter, stakeholder register, high-level scope, business case.
- Plan: WBS, schedule, budget, baselines, management plans (scope/schedule/cost/quality/risk/comms/procurement/resource).
- Execute: build deliverables, manage team, run comms plan.
- Monitor: measure vs baselines, integrated change control, EVM, status reporting.
- Close: formal acceptance, lessons learned, release resources, archive, close contracts.
## Project charter
- Authorizes project + names PM + grants authority. Signed by sponsor, not PM.
- Contents: purpose/justification, measurable objectives, high-level requirements, milestone schedule, budget summary, key stakeholders, assumptions/constraints, success criteria, PM authority level.
## WBS (work breakdown structure)
- Deliverable-oriented hierarchical decomposition of 100% of project scope (100% rule — no more, no less).
- Lowest level = work package; below that = activities (in schedule, not WBS).
- 8/80 rule of thumb: work package = 8 to 80 labor hours. Each element has a unique WBS code.
- WBS dictionary defines each package: scope, owner, acceptance, cost/duration estimate.
## Scheduling: critical path & Gantt
- CPM: longest path of dependent activities = shortest possible project duration. Zero-float activities are critical.
- Forward pass -> Early Start/Early Finish; backward pass -> Late Start/Late Finish. Float = LS-ES = LF-EF.
- Total float: delay without slipping project end. Free float: delay without slipping any successor.
- Dependencies: FS (default), SS, FF, SF; leads (-) and lags (+).
- Gantt chart = bars on a timeline; shows dependencies, milestones, progress; weak at showing float/critical path vs a network diagram.
- Crash (add cost to shorten) vs fast-track (parallelize, adds risk) to compress schedule.
## Baselines
- Approved scope + schedule + cost baselines = the performance measurement baseline (PMB).
- Change only via approved change requests through integrated change control. Never silently re-baseline to hide slippage.
## Earned Value Management (EVM)
- PV (planned value) = budgeted cost of work scheduled. EV (earned value) = budgeted cost of work performed. AC = actual cost.
- SV = EV - PV; CV = EV - AC. SPI = EV/PV; CPI = EV/AC. <1 = behind/over.
- EAC = BAC/CPI (typical). VAC = BAC - EAC. TCPI = (BAC-EV)/(BAC-AC).
- Example: BAC $100k, EV $40k, PV $50k, AC $45k -> SPI 0.80 (behind), CPI 0.89 (over budget), EAC ~$112k.
## PMBOK knowledge areas (overview)
- Integration, Scope, Schedule, Cost, Quality, Resource, Communications, Risk, Procurement, Stakeholder. (10 areas.)
- PMBOK 7 shifted to 12 principles + 8 performance domains + tailoring (outcome-focused vs process-focused).
## Predictive vs adaptive
- Predictive (waterfall): scope fixed up front, sequential, plan-driven; fits stable, well-understood work; change is expensive.
- Adaptive (agile): scope evolves, iterative, value-driven; fits high uncertainty/change; embraces change cheaply.
- Iterative/incremental: iterative refines the same deliverable over passes; incremental delivers usable slices; agile does both.
- Hybrid: predictive envelope (budget/milestones/governance) with adaptive delivery inside.
- Choose by the Stacey/Cynefin fit: clear/obvious -> predictive; complex/uncertain -> adaptive.
## Roles & governance
- Sponsor: funds, champions, signs charter, owns the business case, decides on major changes/escalations.
- Project manager: plans, coordinates, controls, reports; owns the "how", accountable for delivery within constraints.
- PMO: standards, templates, governance, portfolio oversight; supportive/controlling/directive types.
- Steering committee: cross-functional decision body for scope/budget/priority beyond PM authority.
- Stage gates (phase gates): go/no-go checkpoints between phases; kill or continue based on business case + deliverables.
## Change control
- Integrated change control: every change assessed for scope/schedule/cost/quality/risk impact before approval.
- Change request -> impact analysis -> CCB (change control board) decision -> update baselines + plans -> communicate.
- Reject silent changes; log all requests (approved + rejected) with rationale.
## Quality
- Quality (conformance to requirements) vs grade (feature richness); low quality is always a problem, low grade may be fine.
- Prevention over inspection; cost of quality = prevention + appraisal + internal/external failure. Failure cost rises the later a defect is found.
## Pitfalls -> Fix
- **Fixing scope, time, AND cost simultaneously**: guarantees quality collapse or death march. Fix: negotiate one flex variable up front; make the trade explicit to the sponsor.
- **No charter / unsigned charter**: PM has responsibility without authority. Fix: get sponsor signature granting authority before executing.
- **Activity list masquerading as a WBS**: verb-based task dump, gaps in scope. Fix: decompose deliverables (nouns) to 100%; validate with the 100% rule.
- **Gold-plating**: team adds unrequested features. Fix: deliver to scope; route extras through change control.
- **Scope creep**: uncontrolled incremental additions. Fix: baseline scope; every change gets a change request with cost/schedule impact.
- **Reporting % complete by gut feel**: hides overruns until too late. Fix: use EVM (EV/AC) or 0/50/100 rules; measure against baseline.
- **Padding every estimate secretly**: buffers vanish (Parkinson's Law, student syndrome). Fix: aggregate contingency into a visible reserve; use critical chain buffers.
- **Milestones with no acceptance criteria**: "done" is ambiguous, disputes at handover. Fix: define measurable acceptance per deliverable in the WBS dictionary.
- **Critical path ignored**: team optimizes non-critical work while the project slips. Fix: identify zero-float path; protect and manage it; watch near-critical paths for float erosion.
- **Skipping lessons learned / close**: repeat the same failures next project. Fix: run a retrospective, archive, and feed an org knowledge base at close.
- **Treating Monitor & Control as a phase after Execute**: control happens too late. Fix: measure continuously during execution.
- **Re-baselining to hide slippage**: destroys the ability to measure variance. Fix: baselines change only via approved change control; track original vs current.
