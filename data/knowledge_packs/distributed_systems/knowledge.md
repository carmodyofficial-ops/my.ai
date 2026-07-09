# Distributed Systems

## CAP & PACELC
- **CAP**: under a network **P**artition, you must choose **C** (consistency: every read sees the latest write or errors) or **A** (availability: every request gets a non-error response, possibly stale). You cannot have both **during a partition**.
- CAP is only about behavior **during a partition**; when the network is healthy you can have both C and A. "CA systems" don't exist in a distributed setting (partitions will happen).
- **PACELC** extends it: if **P**artition → **A** vs **C**; **E**lse (normal operation) → **L**atency vs **C**onsistency. Real systems trade latency for consistency even without partitions (e.g. wait for quorum acks).
- Examples: Dynamo/Cassandra = PA/EL (available, low-latency, eventual); HBase/Spanner-ish = PC/EC (consistent, pay latency); Spanner uses TrueTime to get strong consistency at a latency cost.

## Consistency models (strong → weak)
- **Linearizable (atomic)**: operations appear to take effect instantly at some point between invocation and response; there's a single, real-time-respecting global order. Strongest, most expensive (needs consensus/coordination).
- **Sequential**: all nodes see operations in the **same order**, consistent with each process's program order, but **not** tied to real time.
- **Causal**: operations that are causally related (happens-before) are seen in order by everyone; concurrent ops may be seen in different orders. Cheap-ish, no global clock needed; a strong practical default.
- **Eventual**: absent new writes, replicas **converge**; no ordering guarantee in the interim. Read-your-writes, monotonic-reads, monotonic-writes are useful **session** guarantees layered on top.
- Stronger = more coordination = higher latency + lower availability. Pick the weakest model the use case tolerates.

## Consensus (Paxos / Raft)
- **Consensus**: get a set of nodes to agree on a single value / an ordered log despite failures. Basis for replicated state machines, leader election, config, locks.
- **Raft** (understandable): one **leader** per term; leader takes all writes, appends to its log, replicates to followers; an entry **commits** once a **majority** persist it; followers apply committed entries in order. **Leader election** by randomized timeouts + votes; split votes retry with new random timeouts.
- **Quorum**: need a **majority** (⌊N/2⌋+1) to commit/elect → tolerates **⌊(N−1)/2⌋** failures. Use **odd** cluster sizes (3,5,7); even sizes add cost without more fault tolerance.
- **Paxos**: the classic (proposers/acceptors/learners, prepare/promise/accept phases); Multi-Paxos ≈ Raft's steady state. Correct but famously hard; Raft/ZAB (ZooKeeper) are the practical implementations.
- Consensus needs a majority **alive and connected** → a partition without a majority stalls writes (chooses C over A).

## Replication
- **Leader-follower (single-leader)**: all writes to leader, replicated to followers; reads can hit followers (stale). Simple, no write conflicts. **Sync** replication (durable, slower) vs **async** (fast, can lose the tail on leader failure). Failover needs election + risks lost/duplicated writes.
- **Multi-leader**: multiple writable leaders (multi-region, offline clients) → **write conflicts** requiring resolution (LWW, version vectors, CRDTs, app merge). Better write availability/locality, harder correctness.
- **Leaderless (Dynamo-style)**: client writes to N replicas, reads from several. Use **quorum** `W + R > N` to overlap read & write sets for consistency. Repair via **read-repair** + **anti-entropy** (Merkle trees). Conflicts resolved by version vectors.
- **Quorum reads/writes**: `W + R > N` guarantees a read intersects the latest write; `W=N,R=1` fast reads/slow writes; `W=1,R=N` opposite. Sloppy quorums + hinted handoff trade consistency for availability.

## Partitioning / sharding
- Split data across nodes for scale. **Range partitioning** (ordered, good for scans, risks hotspots on sequential keys) vs **hash partitioning** (even spread, kills range scans).
- **Consistent hashing** (hash ring + **virtual nodes**): adding/removing a node remaps only ~1/N of keys, not everything → cheap rebalancing. Virtual nodes even out load.
- **Rebalancing**: move partitions when nodes are added/removed; do it gradually, avoid moving more than necessary; keep serving during moves. Fixed partition count (>> nodes) simplifies rebalancing.
- **Hotspots/skew**: a hot key/shard bottlenecks; mitigate with key salting, splitting, or dedicated replicas. Secondary indexes: local (scatter-gather reads) vs global (scatter writes).

## Clocks & time
- **No reliable global wall clock.** NTP drifts, jumps, and skews across machines by ms–seconds. **Never order distributed events by `now()`** or use wall-clock timestamps for correctness (e.g. LWW can silently lose writes on clock skew).
- **Logical clocks (Lamport)**: a counter that captures **happens-before** (a→b ⇒ L(a)<L(b)); gives a total order but **can't tell causality from concurrency** (L(a)<L(b) doesn't imply a→b).
- **Vector clocks**: per-node counter vector; can **detect concurrency** (neither ≤ the other) and true causality. Cost: size grows with nodes.
- **Hybrid Logical Clocks (HLC)**: combine physical + logical to get causally-consistent, roughly-wall-clock timestamps. Spanner's **TrueTime** uses GPS/atomic clocks + a bounded uncertainty interval and **waits out** the uncertainty to get external consistency.

## Failure detection
- Networks give you **partial failure**: you can't distinguish a slow node, a dead node, and a partition — only "no response yet."
- **Timeouts** are the only detector; too short → false positives (healthy node declared dead → unnecessary failover, duplicate work); too long → slow detection. Tune to observed RTT distributions.
- **Heartbeats** + **phi-accrual** detectors give a suspicion level instead of a binary. **Gossip** spreads membership/failure info in large clusters.
- A "dead" node may be alive and still acting (zombie/GC pause) → **fencing tokens** (monotonic ids) prevent a resurrected old leader/holder from doing damage.

## Idempotency & the exactly-once myth
- **Exactly-once delivery is impossible** over an unreliable network (the two-generals problem). What's achievable: **at-least-once delivery + idempotent processing = exactly-once *effect*.**
- Make operations idempotent: dedup by request/idempotency id, conditional writes (compare-and-set on version), natural idempotency (set vs increment).
- Retries are mandatory and cause duplicates → every retried operation must be safe to apply more than once.

## Distributed transactions
- **2PC (two-phase commit)**: coordinator → prepare (all vote) → commit/abort. Gives atomicity but is a **blocking** protocol: if the coordinator dies after prepare, participants hold locks indefinitely. Poor availability, doesn't scale; avoid across services.
- **Saga**: sequence of local transactions + **compensating actions**; eventual consistency, no distributed locks. Choreography (events) or orchestration (coordinator). Preferred for cross-service workflows.
- **TCC (Try-Confirm-Cancel)**: reserve resources, then confirm or cancel — a saga variant with explicit reservation.

## Gotchas -> Fix
- **Split brain** (partition → two leaders both accept writes → divergent state) -> require majority quorum to elect/commit; use fencing tokens so a stale leader's writes are rejected; odd cluster sizes.
- **Clock skew corrupts ordering** (LWW drops writes, TTLs misfire) -> never order events by wall clock; use logical/vector/hybrid clocks or version numbers; bound and wait out uncertainty (TrueTime style).
- **Network partition assumed away** -> partitions are inevitable; decide C-vs-A per operation up front; test with fault injection.
- **Retry amplification / storms** (every layer retries → self-inflicted DDoS on a struggling dependency) -> exponential backoff + **jitter**, retry budgets/caps, circuit breakers, idempotency so retries are safe.
- **Exactly-once assumed** -> design at-least-once + idempotent consumers (dedup keys, CAS); no protocol gives true exactly-once delivery.
- **2PC across services** -> blocking + lock-holding on coordinator failure; use sagas/TCC with compensation instead.
- **Two-generals / commit ambiguity** (did the write land? timeout ≠ failure) -> make writes idempotent and retry; use a unique request id so the retry is deduped, not double-applied.
- **False failure detection** (timeout too aggressive → needless failover, duplicate processing) -> tune timeouts to RTT distribution, use phi-accrual/heartbeats, add fencing to survive zombie nodes.
- **Even-numbered quorum** -> same fault tolerance as N−1, extra cost/tie risk; use odd sizes (3/5/7).
- **Rebalancing storms** (naive hashing remaps all keys on membership change) -> consistent hashing + virtual nodes; move data gradually while serving.
- **Reads from async followers surprise users** (stale/nonmonotonic) -> read-your-writes + monotonic-read session guarantees, or route critical reads to the leader/quorum.
- **Hot shard/key skew** -> salt/split keys, add replicas for hot keys, monitor per-shard load.
- **Choosing strong consistency everywhere** -> pays latency/availability you may not need; pick the weakest model (often causal + session guarantees) the use case allows.
