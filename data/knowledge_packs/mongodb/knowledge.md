# MongoDB

Document database: BSON docs in collections; flexible schema; `_id` primary key (auto ObjectId).

## Data model & schema design
- **Embed** (nest sub-docs) when: 1:1, 1:few, data read together, child has no independent lifecycle. One read, atomic single-doc update.
- **Reference** (store `_id`, join at app or `$lookup`) when: 1:many/many:many large, child queried independently, unbounded growth, data duplicated widely.
- Rule of thumb: **1:few embed, 1:many reference, 1:squillions reference + never embed**.
- Denormalize hot read fields (e.g. store `authorName` on post) to avoid joins; accept update fan-out.
- BSON doc **hard limit 16 MB**. Design so no single doc grows unbounded.
- `ObjectId` = 12 bytes (4 timestamp + 5 random + 3 counter); roughly time-sortable, embeds creation time.

## CRUD & query operators
```js
db.users.insertOne({name:"a", age:30, tags:["x"]})
db.users.find({age:{$gte:18}, tags:"x"}).sort({age:-1}).limit(10)
db.users.updateOne({_id:id}, {$set:{age:31}, $inc:{visits:1}, $push:{tags:"y"}})
db.users.updateMany({active:false},{$set:{active:true}})
db.users.deleteOne({_id:id})
db.users.findOneAndUpdate({_id:id},{$set:{...}},{returnDocument:"after"})
```
- Comparison: `$eq $ne $gt $gte $lt $lte $in $nin`. Logical: `$and $or $not $nor`.
- Element: `$exists $type`. Array: `$all $elemMatch $size`. Eval: `$regex $expr $mod`.
- Update ops: `$set $unset $inc $mul $min $max $rename $push $pull $addToSet $pop $each $slice`.
- Upsert: `{upsert:true}` inserts if no match. Use `$setOnInsert` for insert-only fields.
- Projection: `.find(q,{name:1,_id:0})`.

## Aggregation pipeline
Ordered stages; each transforms the stream.
```js
db.orders.aggregate([
  {$match:{status:"paid"}},                 // filter EARLY (uses index)
  {$group:{_id:"$custId", total:{$sum:"$amt"}, n:{$sum:1}}},
  {$sort:{total:-1}},
  {$lookup:{from:"customers", localField:"_id", foreignField:"_id", as:"cust"}},
  {$unwind:"$cust"},                        // flatten array -> one doc each
  {$project:{name:"$cust.name", total:1}}
])
```
- Key stages: `$match $group $project $sort $limit $skip $lookup $unwind $addFields $set $bucket $facet $count $out $merge $replaceRoot $group`.
- Accumulators: `$sum $avg $min $max $push $addToSet $first $last`.
- `$match`/`$sort` before `$group` to use indexes; after `$group` they run in memory.
- `$facet` = multiple sub-pipelines in one pass. `$merge`/`$out` write results to a collection.

## Indexes
- `db.c.createIndex({a:1,b:-1})` compound. Follows **ESR**: Equality, Sort, Range field order.
- Prefix rule: `{a:1,b:1,c:1}` serves `a`, `a,b`, `a,b,c` — not `b` alone.
- **Multikey**: index on array field; one entry per element (can't compound two array fields).
- **Text**: `createIndex({body:"text"})` + `find({$text:{$search:"foo"}})`; one text index/collection.
- **TTL**: `createIndex({createdAt:1},{expireAfterSeconds:3600})` — auto-delete; date field only, ~60s sweep.
- **Partial**: `{partialFilterExpression:{active:true}}`. **Unique**: `{unique:true}`. **Sparse** skips missing.
- **Hashed** for sharding even distribution. **2dsphere** geo.
- `explain("executionStats")` → want `IXSCAN` not `COLLSCAN`; check `totalDocsExamined` vs `nReturned`.

## Schema design patterns
- **Bucket**: group many small time-ordered docs (readings) into a doc per hour/day with an array + count → fewer docs, bounded arrays. Basis of time-series collections.
- **Computed**: precompute + store aggregates (sums, averages) on write to avoid read-time aggregation.
- **Subset**: embed the hot few (last 10 reviews) inline, keep the rest in a separate collection.
- **Extended reference**: copy the few frequently-needed fields of a referenced doc (name, thumbnail) to avoid joins.
- **Polymorphic**: heterogeneous docs in one collection with a `type` discriminator field.
- **Outlier**: handle the rare huge doc (celebrity with millions of followers) with an overflow flag + spill collection.
- **Schema versioning**: `schemaVersion` field; app handles multiple versions; migrate lazily on write.
- **Time-series collections** (5.0+): `timeseries:{timeField, metaField, granularity}` — auto-bucketing + compression for metrics.

## Special collections & features
- **Capped collection**: fixed size, insertion-order, auto-overwrites oldest (logs). `createCollection("c",{capped:true,size:1e6})`.
- **Change streams**: `db.c.watch([...])` — subscribe to inserts/updates/deletes (needs replica set); CDC / real-time. Resumable via `resumeToken`.
- **GridFS**: store files > 16 MB split into chunks.
- **Views**: read-only saved aggregation pipelines.
- **Collation**: locale-aware / case-insensitive comparison + sorting.

## Transactions
- Multi-doc ACID within a replica set/sharded cluster: `session.startTransaction()` / `commitTransaction()` / `abortTransaction()`.
- Prefer single-doc atomicity (always atomic) — transactions are costly, 60s default limit.
- Retryable across transient errors; keep short, touch few docs; watch for write conflicts (`WriteConflict` → retry).

## Replication & sharding
- **Replica set**: 1 primary (writes) + secondaries (async replicate). Automatic election on primary failure (needs majority; use odd members or an arbiter). Read from secondaries via read preference.
- **Sharding**: horizontal scale by **shard key**. Choose high-cardinality, low-frequency, monotonic-avoiding key (or hashed) for even distribution + write spread. `mongos` router, config servers store metadata. Ranged vs hashed sharding.

## Read/write concern
- **Write concern** `w`: `1` (primary ack), `majority` (durable, survives failover), `0` (fire-forget). `j:true` = journaled.
- **Read concern**: `local`, `majority` (no rollback), `linearizable`, `snapshot` (txns).
- **Read preference**: `primary`, `primaryPreferred`, `secondary`, `nearest`.

## Mongoose / validation
```js
const S = new Schema({email:{type:String, required:true, unique:true, lowercase:true},
  age:{type:Number, min:0, max:120}, role:{type:String, enum:["a","b"], default:"a"}},
  {timestamps:true});
S.index({email:1});
```
- Native JSON Schema validation: `db.createCollection("c",{validator:{$jsonSchema:{...}}})`, `validationLevel`/`validationAction`.
- Mongoose: pre/post hooks, virtuals, `.lean()` for plain JS objects (faster reads), `populate()` = app-side join, discriminators for polymorphism, `strict` mode drops unknown fields.

## Ops & performance
- **Profiler**: `db.setProfilingLevel(1, {slowms:100})` → logs slow ops to `system.profile`. `db.currentOp()` / `db.killOp()`.
- **Working set** (indexes + hot docs) should fit RAM; WiredTiger cache ≈ 50% RAM by default; compression (snappy) on disk.
- `getIndexes()`, `$indexStats` to find unused indexes; drop them (write cost).
- **Connection pooling** via driver (`maxPoolSize`); `mongos` for sharded routing.
- Bulk ops: `bulkWrite([...])` unordered for throughput.

## Gotchas -> Fix
- **Unbounded array growth** (comments pushed forever) → hits 16 MB, slow. Fix: reference into separate collection ("bucket"/"outlier" pattern), cap with `$slice`.
- **Missing index → COLLSCAN** on prod-size data. Fix: `explain()`, add compound index per ESR; index every query filter+sort.
- **`$lookup` is expensive** (nested loop, no index on foreign unless `_id`) at scale. Fix: denormalize/embed, or ensure foreignField indexed; avoid in hot paths.
- **Index not used because query field order/regex-not-anchored**. Fix: anchor regex `^foo`; match compound prefix; put equality before range (ESR).
- **Large skip pagination** `.skip(10000)` scans skipped docs. Fix: range/cursor pagination `find({_id:{$gt:last}})`.
- **Default `w:1` data loss on failover**. Fix: `w:"majority"` for critical writes.
- **`updateMany` without index locks/scans whole collection**. Fix: index the filter.
- **Case-sensitive uniqueness** duplicates. Fix: store normalized (lowercase) + unique index, or collation.
- **Working set > RAM** → page faults, slow. Fix: index size + hot data must fit RAM; scale/shard.
- **`null` matches `$exists:false` in queries** confusion. Fix: use `$type` / explicit `$ne:null`.
- **Retryable writes off → duplicate on network retry**. Fix: enable `retryWrites=true` (default in URI) + idempotent upserts.
- **Aggregation `$group` on unindexed unsorted large data spills to disk**. Fix: `$match` first, `allowDiskUse`, pre-aggregate.
- **Sort without index exceeds 100 MB memory limit** → error. Fix: index the sort key(s) (ESR), or `allowDiskUse`.
- **Fetching whole docs for a few fields**. Fix: projection + covering index (query fields all in index) → index-only.
- **Storing dates as strings** breaks range/sort. Fix: real `Date`/`ISODate`; store UTC.
- **Fan-out denormalized copies drift** when source changes. Fix: change streams / app updates all copies; extended-reference pattern with periodic reconcile.
- **Unindexed `$regex` / negation (`$ne`,`$nin`,`$not`)** → collection scan. Fix: anchored `^` prefix regex; restructure to positive indexable predicates.
- **Shard key immutable + poorly chosen** → hard to fix later, jumbo chunks. Fix: pick compound/hashed high-cardinality key up front; enable balancer.

## Query & aggregation extras
- `$regex` with `^prefix` uses index; `$geoNear` must be first stage; `$sample` random docs.
- `$facet` for multi-metric dashboards in one pass; `$bucket`/`$bucketAuto` histograms; `$setWindowFields` (5.0+) for running totals / moving averages / rank.
- `explain` verbosity: `queryPlanner`, `executionStats`, `allPlansExecution`. Watch `stage`, `keysExamined`, `docsExamined`, `nReturned` — ratio near 1 is ideal.
