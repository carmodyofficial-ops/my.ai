# Prototyping
## Fidelity ladder
- **Paper/sketch** — minutes, near-zero cost. Test flow, IA, concept. No visual/interaction bias; cheapest to throw away.
- **Lo-fi wireframe** — grayscale boxes, layout/hierarchy/structure. No color/copy polish (avoids bikeshedding on aesthetics).
- **Hi-fi mockup** — pixel-accurate visuals, real copy, brand. Static; tests look/feel, visual hierarchy.
- **Interactive prototype** — clickable flows, transitions, states. Tests usability, findability, task completion. Figma/ProtoPie/framer.
- **Code spike / functional prototype** — real code, throwaway. Tests technical feasibility, performance, integration risk.
- Rule: use the *lowest* fidelity that answers your question. Higher fidelity = more sunk cost + more "looks done" bias in feedback.
## Wireframe vs mockup vs prototype
- **Wireframe** = static skeleton (structure). **Mockup** = static visual design (looks). **Prototype** = interactive (behaves). Ascending fidelity/effort.
## POC vs prototype vs MVP vs pilot
- **PoC** — "can this work at all?" Feasibility, one risky assumption, internal, disposable. Answers technical/viability question.
- **Prototype** — "how should it work / do users get it?" Design+UX exploration, not production-quality, disposable.
- **MVP** — smallest *shippable* product that delivers value + generates validated learning from real users. Production-quality (narrow scope), NOT disposable.
- **Pilot** — full product to a limited real audience/segment before broad rollout. Operational validation.
- Progression: PoC → prototype → MVP → pilot → GA. Don't skip risk retirement.
## Throwaway vs evolutionary
- **Throwaway/rapid** — build to learn, then discard. Optimize for speed, hardcode, fake backends. Best for requirements/UX clarity.
- **Evolutionary** — refine a solid core into production. Only when architecture is sound and requirements stable.
- Default to throwaway. Evolutionary is where "prototype-becomes-production" tech debt is born.
## What to test
- **Riskiest assumption first** (RAT before MVP). Identify the assumption that kills the product if wrong; design the cheapest prototype to test *only* that.
- Categories of risk: desirability (do they want it?), usability (can they use it?), feasibility (can we build it?), viability (should we, business-wise?).
- One prototype ≈ one or few learning goals. State the hypothesis and pass/fail criteria before building.
## User testing a prototype
- 5 users surfaces ~85% of usability issues (Nielsen). Test task-based, not opinion-based ("show me how you'd…").
- Don't lead; let silence work. Watch behavior over stated preference. Wizard-of-Oz: human fakes the backend/AI to test the experience before building it.
- Fake-door / smoke test: measure demand (clicks/signups) before building.
## Code spikes & tracer bullets
- **Spike** (XP) — timeboxed throwaway code to answer a technical question / reduce estimate uncertainty. Delete after; keep only the learning.
- **Tracer bullet** (Pragmatic Programmer) — thin end-to-end slice through all layers (UI→API→DB), kept and fleshed out. Validates architecture/integration; NOT throwaway.
- Spike = disposable probe; tracer bullet = permanent skeleton.
## Rapid techniques
- **Wizard-of-Oz**: human simulates the system (AI, matchmaking, recommendations) behind a real-looking UI. Test experience before building the engine.
- **Fake-door / painted-door**: ship a button/landing for a not-yet-built feature; measure click-through/signups as demand signal.
- **Concierge**: manually deliver the service to a few users (no product) to learn the workflow before automating.
- **Paper prototyping session**: facilitator swaps paper screens as the user "taps"; catches flow gaps in minutes.
- **Design sprint** (GV, 5 days): map → sketch → decide → prototype (Thu) → test (Fri). Prototype is a facade, thrown away.
- **Spike solution** in code: timebox (e.g. 1 day), answer one technical unknown, delete.

## Tools
- Pen/paper, whiteboard (fastest). Figma/Sketch/Adobe XD (design+clickable). Framer/ProtoPie (advanced interaction). Balsamiq (deliberately lo-fi). Code: v0/bolt, Streamlit, HTML/JS spike, feature flags for in-product experiments.
- Choose by question: demand → fake-door; usability → interactive Figma; feasibility → code spike; workflow → concierge/Wizard-of-Oz.

## Deciding fidelity fast
- Ask: what's the cheapest artifact that produces a *decision*? If a sketch settles it, don't open Figma.
- Fidelity dimensions are independent: visual, functional, content, interaction. Raise only the dimension your question needs (e.g. real content + gray boxes to test comprehension).
- Time-box every prototype; the goal is a decision, not an artifact. "Build to think," then discard.

## Pitfalls -> Fix
- **Polishing too early**: hi-fi visuals before validating the concept; wastes effort + biases feedback toward pixels. Fix: start paper/lo-fi; raise fidelity only as questions narrow.
- **Prototype becomes production**: throwaway code shipped under deadline pressure → permanent tech debt. Fix: label it disposable, timebox, plan the real build; or deliberately choose tracer-bullet from the start.
- **No hypothesis**: prototype built with no clear learning goal → "looks nice" feedback, no decision. Fix: write the assumption + pass/fail criteria first.
- **Testing opinions not behavior**: asking "would you use this?" (people lie/predict poorly). Fix: task-based observation; fake-door for real demand signal.
- **Gold-plating the prototype**: adding edge cases, error handling, real auth to a throwaway. Fix: fake/hardcode everything not under test.
- **Over-fidelity invites nitpicking**: stakeholders debate button color instead of the flow. Fix: grayscale lo-fi to keep feedback on structure.
- **Skipping riskiest assumption**: building the easy parts first, deferring the make-or-break unknown. Fix: RAT — attack the highest-risk assumption first.
- **Confirmation-seeking demos**: showing the prototype to fans, leading them to praise it. Fix: neutral facilitation, recruit target users, count failures as wins (learning).
- **One giant prototype**: tries to test everything, answers nothing cleanly. Fix: several small focused probes, one question each.
- **Feasibility ignored**: beautiful design prototype that can't be built/scaled. Fix: run a parallel code spike on the technical risk.
