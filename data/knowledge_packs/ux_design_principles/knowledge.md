# UX Design Principles

## User-centered design (UCD) process
- Design for real users' goals, not assumptions. Iterative loop: research → define → ideate → prototype → test → repeat.
- Understand context of use before solutions: who, what goal, what environment, what constraints.
- Decisions backed by evidence (research/testing), not opinion or the loudest voice (HiPPO).
- Solve the user's problem, not the feature request; frame with jobs-to-be-done ("when [situation], I want to [motivation], so I can [outcome]").
- Test early and often with cheap artifacts (sketches, wireframes) before expensive build.

## Nielsen's 10 usability heuristics (evaluate any interface against these)
1. Visibility of system status — show what's happening (loading, saved, progress).
2. Match between system and real world — user's language and mental model, not jargon.
3. User control and freedom — undo/redo, clear exits, cancel.
4. Consistency and standards — follow platform conventions; same word = same thing.
5. Error prevention — constrain, confirm destructive actions, good defaults > good error messages.
6. Recognition rather than recall — show options; don't make users remember across screens.
7. Flexibility and efficiency — shortcuts/accelerators for experts, simple path for novices.
8. Aesthetic and minimalist design — every extra element competes with the relevant.
9. Help users recognize, diagnose, recover from errors — plain-language messages that say what and how to fix.
10. Help and documentation — searchable, task-focused, available when needed.

## Information architecture + navigation
- Organize content by user mental model; validate with card sorting + tree testing.
- Clear labels (user's words), predictable, shallow hierarchy.
- Persistent, visible navigation with "you are here" cues (active state, breadcrumbs).
- One primary action per screen; obvious next step.

## Interaction patterns, affordances, signifiers
- Affordance: what an object allows (a button can be pressed). Signifier: the cue that reveals it (it looks pressable).
- Make interactive elements look interactive; non-interactive elements not.
- Feedback for every action (hover, active, loading, success, error) within perceptible time.
- Reuse established patterns (search bar, tabs, modals) — don't reinvent; novelty costs learnability.
- Mapping: control layout mirrors real-world/spatial relationships.

## Cognitive load + laws
- Minimize extraneous cognitive load; chunk information; progressive disclosure (reveal complexity on demand).
- **Hick's Law**: decision time grows with number/complexity of choices → reduce options, group, set defaults.
- **Fitts's Law**: time to hit a target ∝ distance / size → make important/frequent targets big and near; edges/corners are effectively infinite size.
- **Miller's ~7±2**: limit simultaneous items in working memory; group into chunks.
- **Jakob's Law**: users expect your site to work like the others they know → honor conventions.
- **Law of proximity / Gestalt**: group related controls spatially.

## User research
- **Interviews**: open-ended, understand goals/context/pain; ask about past behavior, not hypotheticals.
- **Usability testing**: watch real users attempt real tasks; measure success, errors, time; ~5 users surface ~85% of issues per round; test iteratively.
- **Surveys**: quantitative scale (many users, shallow); good for validation, bad for "why".
- **Analytics/field studies**: what users actually do vs. say.
- Separate generative research (discover problems) from evaluative research (test solutions).
- Don't lead the witness; observe more than you prompt.

## Personas + journey maps
- **Persona**: research-based archetype (goals, context, frustrations) to align the team on who you serve — not demographic fluff.
- **Journey map**: stages a user moves through with actions, thoughts, emotions, and pain points across touchpoints; reveals gaps and moments that matter.
- **Empathy map / JTBD**: complementary tools to keep the user's need central.

## Wireframing + prototyping fidelity
- **Sketch / low-fi wireframe**: fast, cheap, structure + flow, no visual design; ideal for early exploration and rapid iteration.
- **Mid-fi**: layout, hierarchy, real content, grayscale.
- **Hi-fi prototype**: visual design + interactivity; for realistic usability tests and stakeholder buy-in.
- Match fidelity to the question: test flow/IA with low-fi; test visual/detail with hi-fi. Higher fidelity attracts nitpicks on the wrong things too early.

## Accessibility (WCAG basics)
- POUR: Perceivable, Operable, Understandable, Robust.
- Text contrast ≥ 4.5:1 (normal), 3:1 (large text/UI components).
- Full keyboard operability; visible focus indicators; logical tab order.
- Alt text for meaningful images; labels tied to every form field.
- Don't convey meaning by color alone; provide text/icon too.
- Semantic HTML / correct roles for screen readers; captions for media; respect reduced-motion.
- Accessibility is a baseline requirement, not a feature; it helps everyone.

## Forms + error handling UX
- Ask only what you need; group logically; one column; clear labels above fields (not placeholder-as-label).
- Inline validation with specific, polite messages that say how to fix ("Password needs 8+ characters").
- Preserve entered data on error; mark required fields; sensible defaults and input types (keyboard, autofill).
- Confirm before destructive/irreversible actions; show progress on multi-step; clear success feedback.

## Mobile / responsive UX
- Touch targets ≥ ~44px; adequate spacing; thumb-reachable primary actions.
- Content-first, progressive enhancement; reflow, not horizontal scroll.
- Respect platform conventions (iOS vs Android); handle offline/slow networks; performance is UX.
- Don't hide critical actions behind gestures with no signifier.

## Pitfalls -> Fix
- Designing for yourself -> Do user research; test with real target users, not colleagues.
- No usability testing -> Test 5 users per round, iterate; cheap prototypes early.
- Feature bloat / everything visible -> Prioritize by user goals; progressive disclosure; kill low-value features (Hick's Law).
- Jargon / system language -> Use the user's words; match their mental model (heuristic 2).
- No feedback on actions -> Show status for every action: loading, success, error (heuristic 1).
- Blocking/vague errors -> Prevent errors first; plain-language, specific, recoverable messages (heuristics 5, 9).
- Placeholder text as labels -> Persistent labels above fields; placeholders only for hints/examples.
- Tiny/crowded tap targets -> ≥44px targets, spacing, place frequent actions near thumb (Fitts's Law).
- Color-only meaning / low contrast -> Add text/icon; meet WCAG contrast (4.5:1); test with a contrast checker.
- No undo, easy to lose work -> Provide undo, confirm destructive actions, preserve input.
- Novel controls that look non-interactive -> Use conventional patterns; clear signifiers (Jakob's Law).
- Deep/confusing navigation -> Card-sort-validated IA; shallow hierarchy; visible "you are here".
- Dark patterns (forced continuity, confirmshaming, hidden costs, sneak-into-basket) -> Never use; erode trust and increasingly illegal; make opt-out as easy as opt-in.
- Hi-fi mockups too early -> Start low-fi to test structure; raise fidelity as questions narrow.
- Deciding by opinion (HiPPO) -> Ground decisions in research/test data.

## Onboarding + empty states
- First-run experience should get the user to first value fast; defer setup that isn't needed yet.
- Empty states are teaching moments: explain what goes here and give a primary action to fill it, not a blank void.
- Progressive onboarding (tooltips in context, when needed) beats an upfront wall of tour modals.
- Sensible defaults reduce required decisions; pre-fill what you can infer.

## Feedback, timing, and perceived performance
- Response < 0.1s feels instant; < 1s keeps flow (may show a subtle indicator); > 1s needs a spinner; > ~10s needs progress + a way to keep working.
- Optimistic UI (assume success, reconcile on error) makes actions feel immediate.
- Skeleton screens beat spinners for content loads (perceived speed).
- Always confirm completion; never leave the user guessing whether an action worked.

## Content + microcopy
- UI text is design: labels, buttons, errors, and empty states guide behavior more than graphics.
- Button labels name the action/outcome ("Save changes", "Delete account"), not vague "OK/Submit".
- Write errors in plain language: what happened + how to fix, never codes alone or blame ("You entered…").
- Consistent voice and terminology across the product; one word per concept.

## Measuring UX
- Task success rate, time-on-task, error rate (usability metrics from testing).
- SUS (System Usability Scale) for perceived usability; SEQ (single ease question) per task.
- Behavioral analytics: funnels, drop-off, rage clicks; pair "what" (analytics) with "why" (research).
- HEART framework (Happiness, Engagement, Adoption, Retention, Task success) to pick product metrics.

## Heuristics
- If users can't complete the task in a test, the design is wrong, not the users.
- Reduce choices, reduce steps, reduce memory demands — in that order.
- The best error message is the one the design made impossible.
- Conventions are free usability; break them only with strong reason.
