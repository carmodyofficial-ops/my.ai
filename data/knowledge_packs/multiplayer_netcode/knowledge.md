# Multiplayer Netcode

## Client-Server Authority
- Server is authoritative over gameplay state; clients send INPUTS/intents ("move left", "fire"), never results ("I hit him for 40"). Anything the client computes and reports is a cheat vector.
- Client renders a prediction of authoritative state; server's word is final. Design every mechanic asking "what does the server verify?"
- Full trust-the-client is acceptable only for co-op/friends-only; still validate ranges (position deltas, fire rates) to catch bugs.

## Client Prediction + Reconciliation
- Predict locally: apply your own input immediately; otherwise controls feel like RTT-worth of mud.
- Tag each input with a sequence number; keep a buffer of unacknowledged inputs.
- Server echoes last processed sequence with each state snapshot. On receipt: snap to server state, then REPLAY all inputs after that sequence through the same movement code. If replayed result ≈ predicted, the player sees nothing.
- Requires deterministic, shared movement simulation between client and server — share the code module; divergence = constant rubber-banding.
- Smooth small corrections over ~100ms instead of snapping; snap only past a threshold (teleport, big desync).

## Interpolation Buffers (remote entities)
- Render OTHER players in the past: buffer snapshots, render at `now - interpDelay` (typically 2–3 snapshot intervals, e.g. 100ms at 20 snapshots/s), interpolating between the two snapshots bracketing that time.
- Never extrapolate by default — overshoot on direction changes looks worse than 100ms of delay. Extrapolate only briefly (≤ ~250ms) to mask packet loss, then hold.
- Adaptive delay: grow the buffer under jitter, shrink when stable.

## Lag Compensation
- Problem: shooter aimed at where the target WAS (interp delay + RTT). Server-side rewind: keep a ring buffer of entity positions (~1s); on a fire event, rewind targets to `fireTime - client interp offset`, do the hit test, restore.
- This is why "I was behind the wall" happens to the victim — the shooter's view was authoritative for that shot. Cap rewind window (200–400ms) to bound the injustice.
- Only rewind hitscan/hit tests; projectiles simulate forward in real time.

## Tickrate & Bandwidth
- Server tick 20–64 Hz typical (fighting/shooters high, MMOs low). Snapshot send rate can be lower than tick rate.
- Delta-compress snapshots against the last ACKed one; quantize floats (position to cm, rotation to ~1°); send full state periodically as a keyframe.
- UDP-like transport for state (latest matters, old is garbage): WebRTC DataChannel (unordered/unreliable) in browsers; WebSocket is TCP — one lost packet head-of-line-blocks everything behind it. Use reliable channel only for events (chat, purchases).

## State Sync vs Lockstep vs Rollback (when each)
- **Snapshot/state sync** (server-auth, prediction + interp): default for shooters, action, MMOs, anything >4 players. Bandwidth scales with visible entities, tolerant of nondeterminism.
- **Deterministic lockstep**: send only inputs, all peers simulate identically; tiny bandwidth, huge unit counts (RTS). Requires PERFECT determinism (fixed-point or bit-stable float, no unordered iteration) and stalls on the slowest peer's input (input delay).
- **Rollback (GGPO-style)**: lockstep + predict remote inputs, roll back and resimulate on mispredict. Gold standard for fighting games / 1v1 low-entity-count. Needs determinism plus fast state save/restore and resim of up to ~7–10 frames per frame.
- Rule: many entities or can't guarantee determinism -> state sync. Few entities + determinism + latency-critical -> rollback. Massive armies -> lockstep.

## Interest Management
- Don't send what a client can't see: spatial partition (grid/quadtree) + area-of-interest radius per client; also priority-scale update frequency by distance/relevance.
- This is anti-cheat too: wallhacks can't read positions the server never sent. Balance against pop-in at AOI edges (hysteresis on enter/leave).

## Cheat Surface Checklist
- Speed/teleport: server clamps per-tick displacement. Fire rate/cooldowns: server-side timers, ignore early inputs. Wallhack: interest management. Aimbot: statistical detection only — can't prevent client-side input synthesis.
- Never send secret state (enemy positions through walls, opponent hands in card games) "for smoothness."
- All randomness that matters (crits, loot) rolls on the server.

## Practical Web Stack Notes
- Browser reality: raw UDP unavailable. Options: WebSocket (TCP, simplest, fine for turn-based/casual/co-op), WebRTC DataChannel (configurable unreliable/unordered, fiddly signaling — libraries like geckos.io wrap it), WebTransport (datagrams over HTTP/3, the modern answer where supported).
- Host with authority even in "P2P": pick one peer as host-server, or you're writing lockstep whether you meant to or not.
- Serialize binary (ArrayBuffer/DataView, flatbuffers-style layouts), not JSON, for per-tick state — JSON is 5–10x the bytes and GC-heavy.

## Clock Sync & Timestamps
- Never compare raw client clocks. Estimate offset: client sends `t0`, server replies with `ts`, client receives at `t1`; offset ≈ `ts - (t0+t1)/2`, RTT = `t1 - t0`. Refresh periodically with smoothing; discard high-RTT samples.
- Schedule client simulation slightly AHEAD of server time (half RTT + input buffer) so inputs arrive just before the tick that needs them.

## Join/Leave & Late State
- Late joiners need a full snapshot (keyframe) before deltas make sense; queue deltas during snapshot transfer and apply after.
- Disconnects: keep the entity for a grace window (5–30s) for reconnect; despawn cleanly after — half the "ghost player" bugs are missed leave-cleanup on one code path (crash vs clean quit).

## Gotchas -> Fix
- **Player rubber-bands constantly**: client and server movement code differ (dt handling, collision order). Fix: single shared simulation module; log predicted-vs-authoritative divergence per tick.
- **Remote players stutter every ~50ms**: rendering latest snapshot directly. Fix: interpolation buffer at now-100ms between bracketing snapshots.
- **Everything freezes on one dropped packet**: TCP/WebSocket head-of-line blocking. Fix: unreliable channel (WebRTC/UDP) for state; reliable only for events.
- **Own shots feel delayed**: waiting for server confirmation to show effects. Fix: predict cosmetics (muzzle flash, tracer, sound) instantly; only damage numbers wait.
- **Desync in lockstep after minutes**: float nondeterminism (FMA, trig, cross-platform), unordered map iteration, or an unseeded RNG call. Fix: fixed-point math or strict float settings, ordered containers, checksum state per tick and compare early.
- **Reconciliation replays feel like micro-teleports**: snapping corrections. Fix: blend corrections over ~100ms below a threshold.
- **Jump/fire inputs occasionally eaten**: input events sent unreliably and dropped. Fix: send input as redundant sliding window (last N inputs per packet).
- **Hit registration favors laggers too much**: unbounded rewind. Fix: cap lag comp window (~250ms); beyond that, the lagger misses.
- **Bandwidth blows up with player count**: full snapshots to everyone. Fix: delta compression + quantization + interest management; measure bytes/client/sec from day one.
- **Works on localhost, awful on real networks**: zero latency/jitter/loss in dev. Fix: test under simulated 80–150ms RTT, 30ms jitter, 2–5% loss (tc/netem, clumsy) continuously, not at the end.
