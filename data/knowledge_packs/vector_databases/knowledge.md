# Vector Databases

Store + search high-dimensional **embeddings** by similarity for semantic search, RAG, recommendations, dedup.

## Embeddings & similarity
- Embedding = fixed-length float vector (e.g. 384/768/1536/3072 dims) from a model; semantically similar text → nearby vectors.
- **Cosine similarity** (angle, magnitude-invariant): default for text embeddings. **Dot product** = cosine when vectors L2-normalized (faster). **Euclidean (L2)** = straight-line distance.
- Normalize vectors → cosine ≡ dot; pick the metric the embedding model was **trained with** (mismatched metric wrecks recall).
- Distance vs similarity: many DBs return distance (smaller = closer); cosine distance = `1 - cosine_sim`.

## ANN indexes (approximate nearest neighbor)
Exact kNN = O(N) brute force; ANN trades a little recall for huge speed.
- **HNSW** (graph): best recall/latency, high memory, slow build; params `M` (neighbors/node, 16–64), `ef_construction` (build quality), `ef_search` (query breadth ↑ = recall↑, speed↓). Default choice.
- **IVF** (inverted file, clustering): partition into `nlist` cells, search `nprobe` nearest cells. Lower memory, needs training on sample; `nprobe` tunes recall/speed. Good for very large sets.
- **PQ (product quantization)**: compress vectors into codes → big memory savings, some recall loss. Often `IVF+PQ`. **SQ** (scalar quant) 8-bit.
- **Flat**: exact brute force — small data / ground-truth baseline.
- Tradeoff triangle: **recall ↔ latency/QPS ↔ memory** — you get two; tune per SLA.

## Metadata filtering & hybrid search
- Store payload/metadata (tenant, date, category) alongside vectors → filter `WHERE category='x'` + vector search.
- **Pre-filter** (filter then ANN over subset): accurate, but can break ANN graph traversal / be slow on tiny selective subsets. **Post-filter** (ANN then drop non-matching): fast but may return < k or miss valid results. Modern DBs do filtered-HNSW; check the mode.
- **Hybrid search**: combine dense (vector) + sparse (BM25/keyword) via **RRF** (reciprocal rank fusion) or weighted scores → better than either alone for exact terms + semantics.

## Options
- **pgvector**: Postgres extension; `vector`/`halfvec` type, `hnsw`/`ivfflat` index, `<=>` cosine, `<#>` neg-dot, `<->` L2. Best when you already run Postgres + need joins/transactions/filters.
- **Pinecone**: managed serverless, easy scaling, namespaces, metadata filter. **Qdrant**: OSS/managed, rich filtering, quantization, Rust. **Weaviate**: OSS, hybrid + modules. **Milvus**: OSS, massive scale, many index types. **Chroma**: lightweight, local/dev, prototyping. **Redis** vector, Elasticsearch/OpenSearch kNN, FAISS (library, no persistence/metadata).

## Chunking & upserts
- Chunk documents (~200–800 tokens, overlap 10–20%) before embedding; chunk = retrieval unit. Too big → diluted relevance; too small → lost context.
- Store `id`, `vector`, `text`, `metadata`. **Upsert** by stable id (idempotent) so re-embeds overwrite, not duplicate.
- Batch upserts (100s–1000s) for throughput. Keep embedding **model + dimension** consistent across the whole index.

## Reindexing & scaling
- Reindex when: changing embedding model, dimension, or metric — **all vectors must be re-embedded** (can't mix models in one index).
- HNSW build is memory+CPU heavy; IVF needs retraining if distribution shifts. Rebuild offline → swap alias.
- Scale: shard by namespace/tenant; replicas for QPS; quantization to fit RAM; separate hot/cold.

## pgvector specifics
```sql
CREATE EXTENSION vector;
ALTER TABLE items ADD COLUMN emb vector(768);
CREATE INDEX ON items USING hnsw (emb vector_cosine_ops) WITH (m=16, ef_construction=64);
SET hnsw.ef_search = 100;                          -- recall/speed knob per query
SELECT id FROM items WHERE tenant='x' ORDER BY emb <=> $1 LIMIT 10;  -- filtered ANN
```
- Operators: `<=>` cosine dist, `<#>` negative dot, `<->` L2, `<+>` L1. Index op-class must match (`vector_cosine_ops` etc.).
- `ivfflat` needs `lists` ≈ rows/1000 and data loaded before build; `hnsw` no training. `halfvec` (fp16) halves memory. Combine with normal Postgres `WHERE` + partial indexes.

## Evaluation & RAG quality
- Measure **recall@k** (ANN vs exact) and end-task metrics (nDCG, MRR, hit-rate) on a labeled query set before/after tuning.
- Improve retrieval: better chunking, hybrid search, **reranker** (cross-encoder) over top-50 → top-5, query rewriting, MMR for diversity.
- Track latency budget: embed + search + rerank; cache embeddings for repeated queries.

## Storage & operations
- Vectors are large: 1536-dim fp32 = 6 KB/vector → 6 GB per million. Quantize (int8/PQ/binary) or `halfvec` to cut RAM.
- Persist metadata + raw text alongside so you can re-embed without re-sourcing.
- Blue/green reindex: build new index/collection → validate recall → switch alias → drop old.

## Gotchas -> Fix
- **Dimension mismatch** (index=768, query=1536, or wrong model) → error or garbage results. Fix: pin one embedding model+dim; validate vector length on upsert.
- **Wrong distance metric** vs model (L2 on cosine-trained model) → poor recall. Fix: match model's training metric; L2-normalize + use cosine/dot.
- **Filter-then-search vs search-then-filter** returns too few or wrong results. Fix: use DB's native filtered-ANN; over-fetch `k*` then filter; verify recall with a labeled set.
- **Stale vectors** (source updated, embedding not) → wrong answers. Fix: re-embed + upsert by id on source change; track content hash / version; TTL or reconcile job.
- **Low recall from default ANN params**. Fix: raise `ef_search`/`nprobe`; measure recall@k against exact kNN; tune per latency budget.
- **Duplicate entries** from non-idempotent inserts (new id each run). Fix: deterministic id (hash of source+chunk), upsert.
- **Unnormalized vectors with dot product** → magnitude dominates, bad ranking. Fix: L2-normalize before insert+query.
- **Cross-model index mixing** (old + new embeddings together) → incomparable space. Fix: full reindex on model change; version the index.
- **Pure vector search misses exact keywords/IDs/codes**. Fix: hybrid (vector + BM25) with RRF.
- **Semantic dupes / near-identical chunks** flood top-k. Fix: dedup, MMR (max marginal relevance) for diversity.
- **Everything in one namespace** → noisy cross-tenant results + slow. Fix: per-tenant namespace/collection + metadata filter.
- **IVFFlat built on empty/tiny table** → bad centroids. Fix: build index after loading representative data; retrain on growth.
- **Chunk too large** → one embedding averages many topics, poor match; **too small** → context lost. Fix: 200-800 tokens, semantic/structural splitting, small overlap; store parent-doc pointer.
- **Top-k too small** hides correct answer below cutoff. Fix: over-retrieve (k=20-50) then rerank/filter to final few.
- **No reranker** → embedding-only ranking imprecise on subtle queries. Fix: cross-encoder rerank of candidates.
- **HNSW memory blows RAM** on large sets → swapping/OOM. Fix: quantize (int8/PQ/binary), `halfvec`, IVF+PQ, shard, or disk-based index.
- **Building HNSW while heavily writing** → slow, inconsistent. Fix: batch load then index; or accept incremental build cost.
- **Query embedding not normalized like stored ones** → skewed scores. Fix: identical preprocessing (normalize, same model, same prompt/instruction prefix) at index + query time.

## Choosing index/metric
- Small (<100k) or need exact → Flat/brute force. Large + latency-critical → HNSW. Very large + memory-bound → IVF+PQ.
- Text semantic search → cosine (normalized) almost always. Recommendations/dot-trained → dot product. Spatial/raw magnitude matters → L2.
- Recall knobs: HNSW `ef_search`/`M`, IVF `nprobe`/`nlist`. Always A/B against exact kNN on a sample.
