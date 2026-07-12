# System Design Interviews

## Framework (drive it in this order, ~45 min)
1. **Requirements (5 min)** — pin scope before anything.
   - *Functional*: core use cases only ("post tweet, follow, view feed"). Explicitly defer nice-to-haves.
   - *Non-functional*: scale (DAU, QPS, data size), read:write ratio, latency target (p99), availability (99.9% vs 99.99%), consistency needs, durability. Ask, don't assume.
2. **Back-of-envelope estimation (5 min)** — QPS, storage/yr, bandwidth, memory for cache. Shows you'll size components.
3. **API design (3 min)** — a few endpoints: `POST /tweet {text}`, `GET /feed?userId&cursor`. Note auth, pagination (cursor not offset), idempotency keys for writes.
4. **High-level design (10 min)** — boxes + arrows: client -> LB -> stateless app servers -> cache/DB, plus queue/CDN/blob as needed. Data flow for the main read and the main write path.
5. **Data model (5 min)** — key tables/collections, primary + partition keys, indexes. SQL vs NoSQL choice with reason.
6. **Deep dives (10 min)** — go deep where interviewer steers or where the hard problem lives (feed fan-out, hot keys, dedupe, consistency).
7. **Bottlenecks & tradeoffs (5 min)** — single points of failure, hot partitions, cache stampede, thundering herd; state mitigations.

## Estimation numbers (memorize)
- 1 day ≈ **86,400 s ≈ 10^5 s**. QPS = total daily requests / 10^5.
- Peak QPS ≈ 2-3x average.
- Powers: KB 10^3, MB 10^6, GB 10^9, TB 10^12, PB 10^15.
- Read:write often 100:1 (social/feed) -> optimize reads (cache, replicas, fan-out-on-write).
- Latencies: memory ref ~100 ns, SSD read ~100 µs, disk seek ~10 ms, same-DC round trip ~0.5 ms, cross-continent ~100-150 ms.
- One commodity box: ~1000s of QPS for simple ops; ~tens of GB RAM. Scale count from there.
- Storage sizing: `records/day * bytes/record * 365 * retention_years`; add replication factor (x3) and index overhead.
- Bandwidth: `QPS * avg_response_bytes`.

## Building blocks
- **Load balancer**: L4 (TCP) vs L7 (HTTP, path/host routing). Algorithms: round-robin, least-conn, consistent-hashing (sticky/cache affinity). Health checks; deploy in pairs (HA).
- **Cache**: Redis/Memcached. Patterns: cache-aside (lazy load on miss), write-through, write-behind. Eviction LRU/LFU/TTL. Place: client, CDN, app-tier, DB-tier. Watch hot keys, stampede, staleness.
- **CDN**: static/media + edge caching near users; pull vs push; cache-control/TTL, invalidation on deploy.
- **DB — SQL vs NoSQL**: SQL (Postgres/MySQL) for relations, transactions, strong consistency, ad-hoc queries. NoSQL: key-value (DynamoDB/Redis) for lookups; document (Mongo) for flexible schema; wide-column (Cassandra) for huge write volume + time-series; graph (Neo4j) for relationship traversal. Pick by access pattern, not hype.
- **Sharding/partitioning**: split by key. Strategies: range (hot-spot risk), hash (even, no range scans), consistent hashing (minimal reshuffle on add/remove), geo. Choose a shard key with high cardinality + even access. Cross-shard joins/txns are painful.
- **Replication**: leader-follower (reads scale on followers, replica lag = eventual reads), multi-leader (write anywhere, conflict resolution), leaderless/quorum (`R+W>N` for consistency, Dynamo/Cassandra).
- **Message queue / log**: Kafka (durable log, replay, high throughput), RabbitMQ/SQS (task queues). Decouple producers/consumers, absorb spikes, async work, retries + DLQ. At-least-once default -> consumers must be idempotent.
- **Search**: Elasticsearch/OpenSearch inverted index for full-text; keep it in sync via CDC/queue; it's not your source of truth.
- **Blob store**: S3/GCS for images/video/files; store URL/metadata in DB, object in blob + CDN. Pre-signed URLs for direct up/download.
- **Object metadata/coordination**: ZooKeeper/etcd for leader election, config, service discovery.

## Scaling patterns
- **Stateless app tier** -> horizontal scale behind LB; push session state to Redis/token.
- **Vertical then horizontal**: bigger box is quick but capped; horizontal is the real answer.
- **Caching layers** at every tier; measure hit ratio; TTL + explicit invalidation.
- **Read replicas / CQRS**: separate read model (denormalized, replicas, cache) from write model; async projection. Great for read-heavy.
- **Fan-out**: on-write (precompute feeds into per-user lists — fast reads, heavy writes; handle celebrities as pull/hybrid) vs on-read (compute at query time — cheap writes, slow reads).
- **Database scaling ladder**: index -> read replicas -> cache -> vertical -> shard -> denormalize.
- **Rate limiting**: token bucket (burst + refill), leaky bucket (smooth), fixed/sliding window, sliding-window-log. Store counters in Redis (atomic INCR + TTL); distributed limiter must be shared across nodes.
- **Idempotency**: client-supplied idempotency key + dedupe store to make retried writes safe.

## Consistency vs availability (CAP / PACELC)
- Partition happens -> choose **C or A**. Payments/inventory -> CP (reject on partition). Feeds/likes/counts -> AP (serve possibly-stale, converge).
- **Strong** (linearizable): read sees latest write — costlier, cross-region latency. **Eventual**: converges; fine for social. **Causal / read-your-writes**: middle ground.
- PACELC: even without partition, tradeoff **latency vs consistency**.
- Distributed txns: 2PC (blocking, slow) vs **Saga** (local txns + compensating actions) — prefer Saga in microservices.

## Common designs — key ideas
- **URL shortener**: hash/base62 of an auto-increment ID (7 chars = 62^7 ≈ 3.5T); KV store `short->long`; cache hot links; 301 vs 302; read-heavy; custom-alias collision check.
- **News feed**: fan-out-on-write to per-user feed cache; pull for celebrities (hybrid); rank; paginate by cursor; store posts in blob/DB.
- **Chat/messaging**: WebSocket (persistent) via connection servers; presence in Redis; message queue + DB per conversation; sequence IDs for ordering; delivery/read receipts; offline push.
- **Rate limiter**: token bucket in Redis, keyed by user/IP; return `429` + `Retry-After`; sidecar or gateway.
- **Notification system**: producers -> queue -> per-channel workers (push/email/SMS) with provider adapters; user prefs + templates; retries, DLQ, rate limits; idempotent sends; fan-out at scale.
- **Typeahead/autocomplete**: trie + top-k per prefix, cached; update async.

## Reliability, availability, observability
- **Availability math**: 99% = 3.65 days/yr down; 99.9% ("three nines") = 8.8 h; 99.99% = 52 min; 99.999% = 5 min. Adding a dependency multiplies failure probability.
- **Redundancy**: no SPOF — LB pairs, multi-AZ, replicas, N+1 capacity. Active-active vs active-passive failover.
- **Resilience**: timeouts, retries with exponential backoff + jitter, circuit breakers, bulkheads, graceful degradation (serve stale cache/partial results), load shedding, backpressure.
- **Observability**: metrics (RED — rate/errors/duration; USE — util/sat/errors), structured logs, distributed tracing (request IDs), alerting on SLO burn.
- **Health**: liveness vs readiness probes; drain before deploy; blue-green/canary rollouts.

## Data & storage details
- **Indexing**: B-tree for range/point; hash for equality; composite indexes; covering indexes. Index every hot query, but writes pay index cost.
- **Denormalization** trades storage + write complexity for fast reads (precompute, materialized views).
- **Change Data Capture (CDC)**: stream DB changes (Debezium/binlog) to keep search/cache/derived stores in sync.
- **Write-ahead log / event sourcing**: durability + replay; the log is source of truth.
- **Time-series / analytics**: columnar (ClickHouse, BigQuery) for OLAP; separate from OLTP.
- **Consistent hashing** for cache/shard placement: nodes + keys on a ring, virtual nodes for balance; adding a node moves only `1/N` of keys.
- **Bloom filter**: probabilistic membership to skip expensive lookups (no false negatives).

## Communication & data-flow tips
- Walk the **write path** then the **read path** end to end for the primary use case.
- Number every component you add ("this cache holds hot tweets, ~X GB at 90% hit ratio").
- Draw clean boxes; label protocols (HTTP/gRPC/WebSocket) and sync vs async edges.

## Tradeoff articulation
- Always name the alternative and *why you chose this*: "SQL for transactional integrity of orders; NoSQL for the high-write event log."
- Cite the cost of your choice (fan-out-on-write = fast reads but expensive celebrity writes -> hybrid).
- Tie every component back to a requirement/number you established.

## Pitfalls -> Fix
- **No requirements gathering** -> spend 5 min pinning functional + scale first; write assumptions on the board.
- **Jumping to component details** (which DB, which cache) before the high-level flow -> boxes-and-arrows first, deep-dive later.
- **Skipping estimation** -> do QPS + storage math; it justifies every capacity decision.
- **Ignoring tradeoffs / one "right" answer** -> present options, pick with reasons, acknowledge downsides.
- **Over-engineering** (microservices/Kafka/k8s for a 10-QPS app) -> match complexity to scale; start simple, note when you'd add it.
- **Hand-waving bottlenecks** -> explicitly find SPOFs, hot keys/partitions, cache stampede, replica lag; give a concrete mitigation.
- **Vague "just add a cache"** -> specify what, where, TTL, invalidation, hit-ratio target, stampede handling.
- **Forgetting non-functional** (latency, availability, consistency) -> they drive the whole design; ask early.
- **Not managing time** -> timebox each phase; don't sink all time in the data model.
- **Ignoring the read:write ratio** -> it decides replicas vs sharding vs fan-out direction.
- **Assuming exactly-once** -> queues are at-least-once; make consumers idempotent.
- **No failure handling** -> discuss retries, timeouts, circuit breakers, DLQ, graceful degradation.
- **Single global DB with no partition plan** -> state the shard key and how you'd migrate when it grows.
