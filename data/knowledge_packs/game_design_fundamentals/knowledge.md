# Game Design Fundamentals

## Core Loop
- Define the 5–60 second loop first: action -> reward -> upgrade/choice -> stronger action. If this loop isn't fun with placeholder art, no amount of content fixes it.
- Each loop pass must change something (resources, position, knowledge, power) — loops with no delta are grind.
- Nest loops: moment (dodge/shoot, seconds) -> session (clear level, minutes) -> meta (unlock/build, hours). Weak moment loop kills everything above it.
- Prototype test: strip to the loop, play 10 minutes. Bored at 3 -> fix the verb, not the content.

## Difficulty Curves
- Sawtooth beats slope: rise tension, spike (boss/challenge), relief valley (reward, easy section), repeat higher. Flat ramps exhaust players.
- Introduce one mechanic at a time: teach in safety, test lightly, then combine with known mechanics. The combination IS the difficulty ramp.
- Fail states must teach: player should articulate what to do differently. Random-feeling deaths -> quit.
- Cheap difficulty knobs that respect players: enemy count/mix, timing windows, resource scarcity. Disrespectful: HP sponges, damage spikes, input reading.
- Death cost tuning: quick retry (<5s to re-attempt) enables high difficulty; long retry loops force easier design.

## Onboarding / Tutorialization
- Teach by doing in level design, not text walls: a pit you must jump teaches jump; the "first room is safe to experiment" pattern.
- Sequence: show (environment hints) -> do (forced use in safe context) -> test (must use under light pressure). Only prompt with text if the player fails.
- First session goals: player experiences the core loop and one "wow" moment within ~5 minutes; defer systems (crafting, skill trees) until the base verbs are internalized.
- Watch a new player without speaking. Every place they stall or misread is your bug, not theirs.

## Economy Design (sources/sinks)
- List every source (earn) and sink (spend) in a spreadsheet before coding. Faucets > drains = inflation, rewards become meaningless; drains > faucets = starvation, frustration.
- Sinks must be desirable, recurring, and scale with wealth (consumables, repair, cosmetics, gambling-for-rerolls), not one-time purchases that leave endgame players rich and bored.
- Separate currencies by loop: session currency (spent constantly) vs meta currency (progression) vs premium — mixing them makes tuning one break the others.
- Playtest metric: track average wallet over time; a rising curve that never dips means missing sinks.

## Progression Systems
- Two axes: player power (stats, gear) and player skill (knowledge, execution). Best games grow both; power-only progression invalidates skill and trivializes content.
- Unlock cadence: something new every session early (first hours), stretching later. Long droughts churn players.
- Horizontal (options, builds) beats vertical (numbers up) for longevity — vertical requires endless content re-tuning.
- Gate content by ability/knowledge (metroidvania keys) rather than raw stat checks when possible; stat gates read as time-walls.

## Juice / Game Feel
- Every player action gets acknowledgment within ~100ms: sound + visual minimum. Silent-and-static input feels broken even when functional.
- Cheap high-impact stack for hits: screenshake (small! 2–4px, 100–200ms), hitstop/freeze-frame (30–80ms on big hits), particles, flash the target white 1–2 frames, pitch-varied sound (±10% random), number pop.
- Tween everything that appears/moves: scale-in with easeOutBack, never teleport UI. Anticipation (squash before jump) and follow-through (stretch on land) sell weight.
- Juice multiplies a fun loop; it cannot rescue a boring one. Add juice after the loop works, not instead.
- Overdone shake/flash causes motion sickness — always include an intensity/accessibility toggle.

## Playtesting Method
- Test with strangers, not friends (friends are polite and share your context). 5 testers per iteration finds most issues.
- Say nothing during the test. Never explain controls or goals — the game must. Take notes on where they stall, die, or quit.
- Ask afterwards: "what was frustrating?", "when did you feel clever?", "describe the goal in your own words" — not "did you like it?" (everyone says yes).
- Watch behavior over opinions: testers misdiagnose causes but accurately feel symptoms. They say "make my gun stronger" when the real issue is unreadable enemy telegraphs.
- Test early and ugly; polish hides design flaws from you and testers.

## Scope Control (solo devs)
- Estimate honestly, then halve features and double the timeline — solo projects reliably run 2–4x initial estimates.
- One innovation per project: novel mechanic OR novel art OR novel tech. Two novelties multiplies risk beyond solo capacity.
- Cut list from day one: rank every feature core/important/nice. Anything not core must be cuttable without redesign.
- Vertical slice first (one polished level proving the loop), then content breadth. Content-first projects die at 30%.
- Multiplayer, procedural everything, and open worlds are each a project-scale multiplier — pick zero of them for a first game.

## Reward Psychology Quick Notes
- Variable-ratio rewards (random drops) drive engagement harder than fixed schedules — use deliberately and ethically; pair with pity timers so the tail isn't punishing.
- Reward announcements need contrast: rare drops deserve unique sound/color/pause; if everything celebrates, nothing does.
- Losses hurt ~2x wins feel good (loss aversion): avoid taking away earned items/progress; frame setbacks as missed gains where possible.
- Near-miss feedback ("boss at 5% HP") motivates retry; hide information that would demoralize ("wave 3 of 40").

## Gotchas -> Fix
- **"It'll be fun once X is in"**: perpetually deferred fun. Fix: the core loop must be fun with rectangles; if not, redesign now.
- **Tutorial dump then quit**: 10 mechanics in 5 minutes. Fix: one mechanic per beat, spaced across the first hour.
- **Economy inflation by mid-game**: sinks are one-time, sources repeat. Fix: recurring proportional sinks; wallet-over-time telemetry.
- **Difficulty tuned by the dev**: you have 500 hours of practice. Fix: your "medium" is players' "hard" — tune against fresh testers, add one difficulty notch easier than feels right.
- **Progression invalidates content**: +stats make old areas trivial and new areas mandatory sponges. Fix: cap vertical growth, expand horizontally (options, builds).
- **Feedback so juicy the game lies**: big effects on weak hits. Fix: scale juice to gameplay significance or players mis-learn what matters.
- **Playtest feedback whiplash**: implementing every suggestion. Fix: treat feedback as symptom data; diagnose cause yourself; look for repeated symptoms across testers.
- **Scope creep via "small" additions**: each costs integration, UI, saves, balance, bugs. Fix: cost every idea in full; park in an ideas file for the sequel.
- **Silent failure states**: player doesn't know why they died. Fix: telegraph attacks, distinct death causes, kill-cam or damage log.
