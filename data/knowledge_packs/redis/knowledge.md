# Redis

In-memory data-structure store. Single-threaded command execution (atomic per command). Sub-ms latency. Use as cache, queue, lock, counter, session store, leaderboard.

## Data types
- **String** (binary-safe, ≤512 MB): `SET k v EX 60`, `GET`, `INCR/DECRBY`, `SETNX`, `GETSET`, `APPEND`, `SETRANGE`. Counters, cache blobs, flags.
- **Hash** (field→value map): `HSET k f v`, `HGET`, `HGETALL`, `HINCRBY`, `HDEL`. Store objects (user:123 → {name,age}). Memory-efficient for many fields.
- **List** (linked list): `LPUSH/RPUSH`, `LPOP/RPOP`, `LRANGE`, `BLPOP` (blocking). Queues, stacks, recent items.
- **Set** (unique unordered): `SADD`, `SISMEMBER`, `SINTER/SUNION/SDIFF`, `SCARD`. Tags, unique visitors, relations.
- **Sorted set (zset)** (member+score, ordered): `ZADD k score m`, `ZRANGE k 0 -1 WITHSCORES`, `ZRANGEBYSCORE`, `ZRANK`, `ZINCRBY`, `ZREVRANGE`. Leaderboards, priority queues, time-ordered feeds, rate limiting.
- **Stream** (append-only log w/ IDs): `XADD s * field v`, `XREAD`, consumer groups `XGROUP`/`XREADGROUP`/`XACK`. Durable event queue with replay + at-least-once delivery.
- **Bitmap**: `SETBIT`, `GETBIT`, `BITCOUNT`. Compact boolean per-id (daily active users).
- **HyperLogLog**: `PFADD`, `PFCOUNT`. Approx cardinality, ~0.81% error, 12 KB fixed for billions. Unique counts cheaply.
- **Geo**: `GEOADD`, `GEOSEARCH` (zset-backed). Bitfield, Bloom (module).

## Caching patterns
- **Cache-aside (lazy)**: app checks cache → miss → read DB → `SET` with TTL. Most common. Stale until TTL/invalidation.
- **Write-through**: write DB + cache together (cache always fresh, write latency +). **Write-behind**: write cache, async flush DB (fast, risk loss).
- **Invalidation**: `DEL key` on update, or short TTL. Cache invalidation is the hard part — prefer TTL + explicit delete on write.
- Set TTL on almost every cache key: `SET k v EX 300` / `EXPIRE k 300`.

## TTL & eviction
- `TTL k` (secs left), `PERSIST k` (remove expiry). Lazy + periodic active expiration.
- `maxmemory` + `maxmemory-policy`: `allkeys-lru`, `allkeys-lfu` (best for cache), `volatile-lru/ttl`, `noeviction` (errors on write — use for non-cache/DB roles), `allkeys-random`.

## Pub/Sub & Streams
- **Pub/Sub**: `SUBSCRIBE ch` / `PUBLISH ch msg`. Fire-and-forget, **no persistence**, no replay — offline subscribers miss messages.
- **Streams**: durable, consumer groups, ACK, pending-entries list, replay by ID. Use for reliable queues; Pub/Sub only for ephemeral fan-out.

## Atomicity & scripting
- **MULTI/EXEC**: queue commands, execute atomically (no rollback; not conditional mid-transaction). `WATCH k` = optimistic lock (EXEC aborts if key changed) → CAS retry loop.
- **Lua** `EVAL`/`EVALSHA`: atomic multi-step logic server-side (check-then-set). Keep scripts fast (blocks everything). `FUNCTION` (Redis 7+).
- Pipelining ≠ atomic; just batches round-trips.

## Distributed locks
- Simple: `SET lock:x token NX EX 30` (NX = only if absent, token = unique). Release via Lua compare-token-then-DEL (never plain DEL — you may delete someone else's lock).
- **Redlock** (multi-node): quorum across N masters. **Caveats**: Martin Kleppmann critique — clock drift, GC/STW pauses can violate mutual exclusion; not safe for correctness-critical mutual exclusion. Use fencing tokens; treat as best-effort. Prefer a single lock + short TTL + idempotent work for most cases.

## Persistence
- **RDB**: point-in-time snapshot fork (`SAVE`/`BGSAVE`); compact, fast restart, but loses writes since last snapshot.
- **AOF**: append every write; `appendfsync everysec` (default, ≤1s loss) / `always` (durable, slow) / `no`. Rewrite compacts. Best durability = AOF; best backups/restart = RDB; run both.

## Cluster
- Hash-slot sharding: 16384 slots via `CRC16(key) mod 16384`. Multi-key ops must share a slot → use **hash tags** `{userid}` to co-locate. No cross-slot transactions. Min 3 masters + replicas.

## Rate limiting
- **Fixed window**: `INCR key` + `EXPIRE key 60`; reject if > N. Bursty at edges.
- **Sliding window**: zset of timestamps, `ZREMRANGEBYSCORE` old, `ZCARD` count.
- **Token bucket**: Lua script with tokens + last-refill timestamp.

## Replication & availability
- **Async replication** primary→replicas; `replicaof host port`. Replicas serve reads (may be slightly stale).
- **Sentinel**: monitors, automatic failover + promotion, client discovery — for HA without cluster sharding.
- Cluster gives sharding + HA (replicas per master), auto failover on master loss.

## Keyspace, memory & introspection
- **Key naming**: `object-type:id:field` (`user:1000:sessions`); colon convention groups keys.
- `OBJECT ENCODING k` — ziplist/listpack/intset/embstr → small collections use compact encodings (tune `hash-max-listpack-entries` etc.).
- `MEMORY USAGE k`, `INFO memory`, `--bigkeys`, `--memkeys`, `DBSIZE`, `TYPE k`, `TTL k`.
- **Keyspace notifications**: `notify-keyspace-events` → pub/sub on expiry/eviction (e.g. delayed-job on key expire).
- `EXPIRE`/`PEXPIRE`/`EXPIREAT`; `SET ... KEEPTTL` to preserve TTL on overwrite.

## Common use patterns
- **Session store**: hash per session + TTL sliding on access.
- **Leaderboard**: zset by score, `ZREVRANGE 0 9 WITHSCORES` top-10, `ZRANK` for player rank.
- **Job queue**: list + `BRPOPLPUSH` (reliable) or Streams consumer groups.
- **Counters/analytics**: `INCR`, HyperLogLog uniques, bitmaps for DAU.
- **Feature flags / config**: hash; **dedup**: set / Bloom; **geospatial**: `GEOSEARCH`.
- Redis 7: `FUNCTION` libraries, sharded pub/sub (`SPUBLISH`), `OBJECT FREQ` (LFU).

## Gotchas -> Fix
- **Big keys** (huge list/hash/set) → slow ops, blocking, uneven cluster memory, `DEL` blocks. Fix: `UNLINK` (async del), shard the key, cap size, `redis-cli --bigkeys` to find.
- **`KEYS *` in prod** blocks the server (O(N)). Fix: use `SCAN` (cursor, non-blocking) always.
- **Blocking commands** (`SORT` big, `SMEMBERS` huge, Lua loops, `FLUSHALL`, `SAVE`) freeze single thread. Fix: avoid O(N) on big data; use `SCAN`/`SSCAN`/`HSCAN`, `BGSAVE`.
- **Cache stampede/thundering herd**: many misses on same hot key at TTL expiry hammer DB. Fix: lock/mutex on rebuild (`SET NX`), probabilistic early expiration, stale-while-revalidate, jittered TTLs.
- **No TTL → memory fills, eviction/OOM**. Fix: TTL every cache key; set `maxmemory` + LRU/LFU policy.
- **Plain `DEL` for lock release** deletes another holder's lock after your TTL expired. Fix: Lua check-token-then-del; keep work < TTL; fencing tokens.
- **Pub/Sub message loss** (no persistence, offline miss). Fix: use Streams + consumer groups for reliability.
- **Storing large blobs / using Redis as primary DB** without persistence tuning → data loss on crash. Fix: enable AOF, replicas; treat as cache unless durability configured.
- **Hot key** overloads one shard/thread. Fix: local client cache, replicate reads, split key.
- **Unbounded `INCR` without expire** as rate limiter never resets. Fix: pair `INCR` with `EXPIRE` (set on first hit).
- **MULTI/EXEC assumed to rollback** — it doesn't; errors don't undo prior queued cmds. Fix: validate before, use Lua for conditional atomic logic.
- **Connection churn** (new conn per request) exhausts limits. Fix: connection pool.
- **Multi-key op across cluster slots** errors (`CROSSSLOT`). Fix: hash tags `{user:1}:x`/`{user:1}:y` to co-locate; or split logic client-side.
- **`EXPIRE` on write forgotten after `SET` overwrite** resets/loses TTL semantics. Fix: `SET k v KEEPTTL` or re-set EXPIRE atomically.
- **Lua script too slow / infinite loop** blocks all clients. Fix: keep scripts O(small); no unbounded loops; `SCRIPT KILL` (only if no write yet).
- **Replica stale reads** treated as authoritative. Fix: read from primary for read-your-writes; `WAIT` for replication ack on critical writes.
- **Fork on `BGSAVE`/AOF-rewrite doubles memory** (copy-on-write) → OOM under high write. Fix: headroom, `maxmemory` < 50-60% RAM, disable transparent huge pages.
- **No eviction policy on a cache role** → writes fail (`noeviction`) when full. Fix: set `allkeys-lru`/`lfu` for caches.

## Performance & safety notes
- Prefer `SET k v NX EX n` (single atomic call) over `SETNX`+`EXPIRE` (two ops, race).
- `SCAN`/`HSCAN`/`SSCAN`/`ZSCAN` cursor-iterate without blocking; `COUNT` hints batch size.
- Pipeline to cut RTT; use `MGET`/`MSET`/`HMGET` for batching same-type keys.
- Client-side caching (RESP3 tracking / `CLIENT TRACKING`) for hot read-mostly keys.
