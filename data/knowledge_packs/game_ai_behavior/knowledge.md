# Game AI & Behavior

## FSM vs Behavior Trees
- FSM: few states (idle/patrol/chase/attack/flee), transitions explicit. Best under ~8 states; beyond that transition count explodes (N² edges).
- Behavior tree: composable priorities. Selector (first child that succeeds), Sequence (all in order), Decorators (invert, repeat, cooldown). Best when behaviors share sub-actions or need clean priority ordering (flee > attack > patrol).
- Rule of thumb: enemy grunt = FSM; boss/companion with layered priorities = BT. Don't build a BT engine for three states.
- Tick BTs at 5–10 Hz, not every frame — cheaper and less twitchy. Cache the running node; re-evaluating from root each tick is correct BT semantics but gate expensive conditions (raycasts) behind cooldown decorators.

## Steering Behaviors
- Seek: `desired = normalize(target - pos) * maxSpeed; steer = desired - vel` (clamp steer to maxForce).
- Flee = negated seek. Arrive: scale desired speed down inside a slow radius to stop overshoot.
- Wander: project a point ahead, jitter it on a circle — smoother than random direction changes.
- Separation for crowds: sum of push-away vectors from neighbors within radius, weighted by 1/dist. Combine steering forces with weights; clamp final. Weighted sums beat hard switching for smooth motion.
- Cheap avoidance: single raycast in velocity direction; steer along the hit normal.

## Pathfinding: A* on Grids
- `f = g + h`; h = Manhattan for 4-dir grids, octile for 8-dir, Euclidean for any-angle. h must never overestimate (admissible) or paths go non-optimal.
- Use a binary heap for the open set; a `closed` set/flag per node. Re-open nodes only if you allow inconsistent heuristics — with the standard grid heuristics you don't need to.
- Diagonal corner-cutting: disallow diagonal moves when either adjacent cardinal cell is blocked, or agents clip walls.
- Path smoothing: string-pulling / line-of-sight raycasts to cut waypoints; grid paths look robotic otherwise.
- Weighted costs (mud=3, road=1) make paths look intelligent for free.
- Navmesh basics: polygons of walkable space; A* over polygon adjacency then funnel algorithm for the tight path. Prefer navmesh when the world isn't naturally tiled.
- Don't path every frame: repath on target-moved-past-threshold or timer (0.25–0.5s), stagger agents across frames.

## Decision-Making Patterns
- Utility AI: score each action (`attack = hp% * proximity * ammo`), pick the highest — smooth blends where FSMs thrash. Normalize scores 0–1 and tune with response curves.
- GOAP exists for planning chains of actions; almost always overkill below immersive-sim scope.
- Blackboard: shared dict per agent (target, lastKnownPos, alertLevel) that FSM/BT nodes read/write — keeps nodes stateless and testable.

## Aggro & Perception
- Sight = distance check + FOV cone (`dot(forward, toTarget) > cos(halfAngle)`) + line-of-sight raycast. All three, in that order (cheapest first).
- Store **last known position** on losing sight; search there, then give up on a timer. Instant omniscient tracking reads as cheating.
- Alert tiers: unaware -> suspicious (investigate) -> combat. Hysteresis on transitions (enter combat at 100 suspicion, drop out at 20) prevents flip-flapping.
- Aggro tables for group fights: threat = damage dealt + healing + taunt bonuses; target = top threat with a switch margin (~10%) to stop ping-ponging.

## Difficulty via AI Tuning
- Tune perception and reaction, not raw stats: reaction delay (0.2–0.6s), aim error cone, decision frequency. "Dumber senses" feels fairer than bullet sponges.
- Artificial stupidity is a feature: enemies miss the first shot, telegraph attacks, don't all attack at once (attack-token system: only N attackers hold a token simultaneously).
- Rubber-banding: bound it (e.g. max ±15% speed) or players notice and resent it.

## Debugging AI
- Render the AI's mind: current state/BT node as floating text, perception cones, chosen path, target lines. Most "AI is broken" reports resolve instantly once visible.
- Log transitions with cause (`patrol->chase: saw player at (x,y)`); ring buffer per agent, dump on anomaly.
- Determinism harness: fixed seed + recorded player inputs re-runs the exact scenario — turns heisenbug AI into a unit test.
- Isolate one agent: a debug key that despawns all but the selected agent removes crowd noise while diagnosing.

## Group Coordination Cheap Tricks
- Attack tokens (N concurrent attackers) create readable, movie-like combat from purely selfish agents.
- Shared blackboard per squad: one agent's spotted-player broadcast updates squad `lastKnownPos` — looks like communication, costs one write.
- Role assignment by index or auction (nearest takes flank-left) beats identical behavior clones; even random role jitter reads as tactics.
- Influence maps (grid of danger/presence scores, decayed each tick) give flanking and avoid-the-choke behavior without planning.

## Performance Budget
- AI budget rule: perception raycasts are the usual cost center — cooldown them (200–500ms), share results between checks, cull by distance bucket first.
- LOD the brain: full BT for on-screen/near agents, timer-based simplified logic for distant ones, pure schedule simulation for off-screen.

## Gotchas -> Fix
- **State thrashing**: chase<->flee flips every frame at the threshold. Fix: hysteresis (different enter/exit thresholds) or minimum state dwell time.
- **All enemies act in lockstep**: same tick, same RNG, same spawn timer. Fix: stagger update offsets, per-agent RNG jitter on timers.
- **A* freezes the frame**: huge map, unreachable target searches every node. Fix: cap explored nodes, spread search over frames (time-sliced), early-out to nearest-reachable.
- **Agents pile into one point**: all path to identical target coords. Fix: separation steering + assign offset arrival slots around the target.
- **Enemy sees through walls**: distance-only aggro. Fix: add the LOS raycast; it's the step most often skipped.
- **Pathing agent vibrates at waypoint**: overshoots waypoint, turns back, overshoots. Fix: waypoint reach radius ≥ agent speed * dt, advance to next waypoint early; arrive behavior at the final one.
- **BT node runs once and never again**: decorator/sequence left in stale `RUNNING` state after target died. Fix: propagate aborts/resets when conditions invalidate the running branch.
- **Perfect-aim frustration**: AI hits instantly at any range. Fix: reaction delay + first-shot miss + error cone scaled by target speed/distance.
- **Corner-cut diagonal through wall**: 8-dir grid allows diagonal past blocked cardinal. Fix: forbid diagonal when adjacent cardinals blocked.
- **Aggro ping-pong between tank and healer**: retarget on every threat change. Fix: switch margin + retarget cooldown.
