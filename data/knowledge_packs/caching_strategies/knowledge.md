# Caching Strategies

## Cache patterns
- **Cache-aside (lazy loading)**: app checks cache; miss → read DB, populate cache, return. Most common. Cache only holds requested data; stale until TTL/invalidation; first request per key pays the miss. App owns cache logic.
```
v = cache.get(k)
if v is None:
    v = db.get(k); cache.set(k, v, ttl=300)
return v
```
- **Read-through**: app reads the cache library; the cache itself loads from DB on miss (loader function). Same effect as cache-aside but the cache owns the fetch; consistent access path.
- **Write-through**: writes go to cache **and** DB synchronously before returning. Cache always fresh; write latency = cache + DB; wastes cache on write-heavy/rarely-read keys.
- **Write-behind (write-back)**: write to cache, ack immediately, **async** flush to DB (batched). Low write latency + absorbs bursts; **risk of data loss** if cache dies before flush; complex ordering/consistency.
- **Write-around**: writes go straight to DB, bypassing cache; cache populated only on read. Avoids polluting cache with write-once data; first read is a miss.
- **Refresh-ahead**: proactively refresh popular keys before expiry so hot keys never miss.

## Invalidation
- Hardest problem in caching. Three levers: **TTL**, **event-based**, **versioned keys**.
- **TTL (expiry)**: simplest; bounds staleness to the TTL window. Pick TTL from tolerance for stale data. Add **jitter** so keys don't all expire together.
- **Event-based (write-invalidate)**: on DB write, delete/update the key (or publish an invalidation event to all cache nodes). Fresher, but the dual-write cache+DB is racy — prefer **delete-on-write** (next read repopulates) over update-on-write.
- **Versioned / immutable keys**: bake a version/hash into the key (`user:42:v7`, `asset:sha256`); "invalidate" by bumping the version → old keys age out via LRU. No explicit delete; great for CDNs/content hashing.
- **Delete, don't update**, on write: deleting is idempotent and avoids writing a stale value; the next read fills from source of truth.

## Cache levels
- **Client/browser**: HTTP `Cache-Control`, `ETag`/`If-None-Match`, `Last-Modified`. Zero server load on hit.
- **CDN / edge**: cache static + cacheable dynamic responses near users; huge offload; invalidate via purge or versioned URLs.
- **Application / in-memory**: local process cache (fast, per-instance, inconsistent across instances) or shared **distributed cache** (Redis/Memcached — consistent across instances, network hop).
- **Database**: query/result cache, buffer pool. Materialized views for expensive aggregates.
- Layer them; each level should have a coherent invalidation story or you get stacked staleness.

## Cache stampede / thundering herd
- **Stampede**: a hot key expires (or cold cache) → many concurrent requests all miss and hammer the DB simultaneously → overload/cascade.
- **Fixes**:
  - **Locking / single-flight**: first miss acquires a lock and recomputes; others wait or serve stale. One DB hit per key.
  - **Early/probabilistic recomputation** (XFetch): refresh **before** expiry with a probability that rises as TTL nears, so one request refreshes while others still hit the cache.
  - **Jittered TTLs**: randomize expiry so keys don't expire in lockstep (avoids synchronized stampedes).
  - **Serve-stale-while-revalidate**: return the stale value and refresh in the background.
  - **Request coalescing**: dedupe concurrent identical loads into one in-flight fetch.

## Consistency & staleness
- Cache = a **replica** → inherently eventually consistent with the source. Choose the acceptable **staleness window** per data type (prices seconds, catalog minutes, config longer).
- TTL bounds max staleness; event invalidation shrinks it; nothing makes a cache perfectly consistent without killing its value.
- **Read-your-writes**: after a user's write, bypass cache or write-through their view so they don't see stale data.
- Never treat the cache as the **source of truth** — it can be evicted/flushed/lost at any moment; the DB must be authoritative and reconstructable.

## Eviction
- Cache is bounded → an eviction policy decides what to drop when full.
- **LRU** (least-recently-used): default, good for temporal locality. **LFU** (least-frequently-used): keeps hot keys, better when frequency ≠ recency (Redis `allkeys-lfu`). **FIFO**, **random**, **TTL-based**.
- **Redis maxmemory-policy**: `noeviction` (errors on full), `allkeys-lru/lfu`, `volatile-lru/lfu/ttl` (only keys with a TTL). Set an eviction policy + `maxmemory` explicitly.
- Undersized cache → high eviction/churn → low hit rate (thrashing). Track **hit ratio**; it's the primary health metric.

## Hot keys, negative caching, key design
- **Hot key**: one key gets disproportionate traffic → overloads its shard/node. Fixes: **replicate** the key across nodes, add a small **local (L1) cache** in front of the distributed cache, or split/shard the value.
- **Negative caching**: cache "not found"/empty results (short TTL) to stop repeated misses hammering the DB — also blunts **cache-penetration** attacks (queries for nonexistent keys). Use a bloom filter to reject known-absent keys.
- **Key design**: stable, namespaced, versioned — `svc:entity:id:v` (`orders:order:42:v3`). Include all inputs that change the value (locale, tenant). Avoid unbounded/user-input keys that never repeat (near-zero hit rate + unbounded growth).
- Set a **TTL on every key** unless deliberately immutable; TTL-less keys accumulate forever.

## Distributed cache mechanics
- **Local (in-process) vs distributed**: local (Caffeine/Guava/`lru_cache`) is nanoseconds but per-instance → inconsistent across a fleet and duplicated; distributed (Redis/Memcached) is a network hop but shared/consistent. Common pattern: **L1 local + L2 distributed** (near-cache) — L1 absorbs hot reads, L2 backs it.
- **Sharding**: partition keys across cache nodes via consistent hashing so adding/removing a node remaps only ~1/N of keys (see distributed-systems pack). Memcached is client-sharded; Redis Cluster hashes to 16384 slots.
- **Write invalidation across nodes**: publish invalidation events (Redis pub/sub, a topic) so every instance drops the stale key from its L1; TTL alone leaves L1 stale until expiry.
- **Serialization cost**: cache stores bytes — (de)serialization can dominate; pick a compact/fast format (protobuf/msgpack) for large values; compress big blobs.

## HTTP caching semantics
- `Cache-Control: max-age=N` (fresh window), `s-maxage` (shared/CDN override), `no-cache` (revalidate every time), `no-store` (never cache), `private` (browser only, never CDN), `public`.
- **Validators**: `ETag` + `If-None-Match` or `Last-Modified` + `If-Modified-Since` → `304 Not Modified` saves bandwidth on unchanged resources.
- `stale-while-revalidate` / `stale-if-error`: serve stale while refreshing in the background / when origin is down.

## Gotchas -> Fix
- **Cache stampede / thundering herd** (mass expiry → DB overload) -> jittered TTLs + single-flight lock + early/probabilistic refresh + stale-while-revalidate.
- **Stale data after write** (cache not invalidated) -> delete-on-write (not update), event-based invalidation, or shorter TTL; read-your-writes bypass for the writer.
- **Cache + DB inconsistency** on concurrent write+read (race between DB update and cache set) -> delete the key instead of writing it; write DB then invalidate; consider versioned keys.
- **Unbounded key growth / TTL-less keys** -> set TTL on every key, set `maxmemory` + eviction policy, avoid caching by unique per-request keys.
- **Cache-as-source-of-truth** (data only in cache, lost on flush/eviction) -> DB is authoritative; cache must be fully rebuildable; never persist critical state only in cache.
- **Low hit ratio / thrashing** (cache too small, poor key design, over-granular keys) -> right-size memory, coarsen keys, monitor hit ratio, use LFU for skewed access.
- **Hot key overload** -> replicate the key, add L1 in-process cache, or shard the value.
- **Cache penetration** (floods of misses for nonexistent keys) -> negative-cache empties (short TTL) + bloom filter guard.
- **Cache avalanche** (whole cache expires/restarts cold at once) -> stagger TTLs, warm/pre-load on startup, layer an L1, rate-limit backfill.
- **Write-behind data loss** (cache dies before async flush) -> use only for loss-tolerant data, or add durable buffering/WAL and bounded flush lag.
- **Caching per-user private data in a shared/CDN cache** -> key by user or mark `Cache-Control: private`; never serve one user's data to another.
- **No invalidation strategy at all** ("just add caching") -> decide TTL vs event vs versioned per data type before shipping; undefined invalidation = permanent stale bugs.
