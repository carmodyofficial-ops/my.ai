# RAG Systems

## Pipeline
`ingest -> clean -> chunk -> embed -> store(index) -> [query transform] -> retrieve -> rerank -> assemble context -> generate -> cite`
- Retrieval quality caps answer quality: if the right chunk isn't retrieved, the LLM cannot answer. Optimize retrieval before prompt tuning.
- Two phases: **indexing** (offline: parse, chunk, embed, upsert) and **query** (online: embed query, search, rerank, generate). Keep them in separate code paths.

## Chunking
- Default: 256-512 tokens per chunk with 10-20% overlap. Smaller = precise retrieval but fragmented context; larger = more context but diluted embeddings and lost-in-middle.
- **Structure-aware**: split on document structure first (headings, sections, markdown, code blocks, tables) before size splitting. Never split mid-sentence or mid-table.
- **Recursive character splitting**: try paragraph -> sentence -> word separators, falling back only when a chunk exceeds max size.
- **Semantic chunking**: split where adjacent-sentence embedding similarity drops (topic boundaries). Better coherence, more compute at index time.
- Attach metadata to each chunk: `source`, `title`, `section`, `page`, `url`, timestamps. Enables filtering, citations, and dedup.
- Prepend context to chunks ("contextual retrieval"): a short doc/section summary before the chunk text improves standalone retrievability.
- Overlap prevents answers being split across a boundary; too much overlap bloats the index and returns near-duplicates.

## Embeddings
- Pick by: retrieval benchmark score (MTEB), dimension, max input length, cost, and domain fit. Common dims: 384, 768, 1024, 1536, 3072.
- Higher dims = more storage/compute, marginal recall gains. Some models support **Matryoshka** truncation (use first N dims) to trade recall for cost.
- Normalize vectors and use cosine (or inner product on normalized = cosine). Be consistent: same model + normalization for index and query.
- Use the model's asymmetric query/document instructions if provided ("query:" / "passage:" prefixes) — mismatching them tanks recall.
- Re-embed the WHOLE corpus when you change embedding models; you cannot mix embedding spaces.

## Vector stores + indexes
- Stores: pgvector, Qdrant, Weaviate, Milvus, Pinecone, FAISS, Chroma. Choose by scale, filtering needs, and ops burden.
- **HNSW** (graph): fast, high recall, high memory; tune `M` (edges, ~16-64) and `ef_construction` (build quality) / `ef_search` (query recall vs latency). Default for most.
- **IVF** (inverted-file/clustering): lower memory, needs training; tune `nlist` (clusters) and `nprobe` (clusters searched). Good for very large corpora.
- **PQ/quantization** (IVF-PQ, scalar quantization): compress vectors to cut memory ~4-32x with small recall loss; combine with HNSW/IVF at scale.
- Use **metadata filtering** (date, source, tenant) with search; prefer stores with efficient pre/post-filtering. Filter on `tenant_id` for multi-tenant isolation.
- ANN is approximate — measure recall vs exact; raise `ef_search`/`nprobe` if recall too low.

## Hybrid search + fusion
- Dense (embeddings) captures semantics; **BM25/sparse** (lexical) captures exact terms, IDs, codes, rare words, names. Each fails where the other wins.
- **Hybrid** = run both, fuse results. Fusion via **Reciprocal Rank Fusion (RRF)**: `score = Σ 1/(k + rank_i)`, `k≈60`. Rank-based, no score normalization needed — robust default.
- Alternative: weighted score fusion (needs normalized scores) or learned sparse (SPLADE). Hybrid consistently beats dense-only on keyword-heavy corpora (docs, legal, code).

## Reranking
- Retrieve broad (top 50-100) with cheap ANN, then **cross-encoder rerank** to top 3-8. Cross-encoders jointly encode (query, chunk) — far more accurate than bi-encoder similarity, but O(n) LLM-ish cost, so only on candidates.
- Rerankers fix ordering so the best chunk lands at the top of context (mitigates lost-in-middle). Big precision win per dollar.
- Cap final context: fewer, higher-quality chunks beat many mediocre ones (noise degrades generation).

## Query transformation
- **Multi-query**: LLM rewrites the query into N variants, retrieve each, union+dedup — improves recall for ambiguous queries.
- **HyDE**: LLM generates a hypothetical answer, embed THAT, and retrieve — the fake answer sits closer to real passages than a short question does.
- **Query decomposition**: break multi-hop questions into sub-questions, retrieve per sub-question.
- **Query rewriting/expansion**: add synonyms, expand acronyms, strip chit-chat, resolve pronouns from chat history before retrieval.
- **Routing**: classify the query to the right index/collection/filter.

## Context assembly + citations
- Order chunks best-first (post-rerank); dedup near-identical chunks; include source metadata inline so the model can cite.
- Wrap each chunk with an id: `[1] (source: X) <text>` and instruct "cite the [id] for each claim; answer only from context."
- Fit within token budget: drop lowest-ranked chunks, not the top ones. Leave room for the answer.
- Verify grounding: optionally check each generated claim maps to a cited chunk (faithfulness check).

## Evaluation
- **Retrieval metrics**: recall@k (is the gold chunk in top-k — most important), precision@k, MRR, nDCG. Build a labeled query->relevant-chunk set.
- **Generation metrics**: faithfulness/groundedness (answer supported by retrieved context, no fabrication), answer relevance, context precision/recall. Tools: Ragas, custom LLM-judge.
- Evaluate the pipeline end-to-end AND each stage — a good answer with bad retrieval is luck; low recall caps everything downstream.
- Track over time; RAG quality drifts as the corpus grows and queries shift.

## Ingestion + preprocessing
- Parse robustly: PDFs (layout, columns, tables), HTML (strip nav/boilerplate), Office docs, code. Bad parsing = garbage chunks in = garbage retrieval.
- Clean: remove headers/footers/watermarks, normalize whitespace/unicode, keep tables and lists structured (markdown), OCR scanned pages.
- Extract and keep metadata at ingest (author, date, section, url, permissions) — you can't recover it later.
- Incremental ingest: track source hashes; upsert changed docs, delete removed ones, so the index stays fresh. Full re-index only on schema/model change.
- Deduplicate source content before chunking to avoid near-identical chunks flooding results.

## Advanced retrieval patterns
- **Parent-document / small-to-big**: embed small child chunks for precise matching but return the larger parent chunk for context. Best of both.
- **Sentence-window**: retrieve on a sentence, expand to a window of surrounding sentences at generation time.
- **Auto-merging**: if many sibling child chunks match, return the merged parent.
- **Metadata/self-query**: LLM extracts filters from the query (date, author) and applies them alongside vector search.
- **MMR** (maximal marginal relevance): balance relevance with diversity to avoid redundant chunks.
- **Contextual retrieval**: prepend LLM-generated chunk context + build a BM25 index over contextualized chunks; strong recall gains.
- **Agentic/iterative RAG**: retrieve, assess sufficiency, retrieve again for gaps (multi-hop) before answering.

## Operational concerns
- Latency budget: embed query (10-50ms) + ANN search + rerank (the expensive part) + generation. Rerank on a small candidate set; parallelize dense+sparse.
- Cache: query embeddings, and full answers for repeated queries (semantic cache).
- Cost: embeddings are cheap at index time but scale with corpus size + re-index frequency; rerankers and generation dominate query cost.
- Access control: filter by user/tenant permissions at query time; never retrieve documents the user can't see. Test isolation.
- Index maintenance: monitor recall over time, re-embed on model upgrade, rebuild/compact indexes, watch memory as the corpus grows.

## Failure modes -> Fix
- Right doc never retrieved (low recall) -> add hybrid+BM25, rerank, multi-query/HyDE, revisit chunking, raise ef_search/nprobe.
- Answer ignores a retrieved fact in the middle -> rerank to top, fewer chunks, put best first (lost-in-middle).
- Chunks split answers across boundaries -> add overlap, structure-aware splitting, larger chunks.
- Exact IDs/codes/names not found -> dense-only misses lexical; add BM25/sparse hybrid.
- Stale/incorrect answers -> index is stale; add incremental re-index, TTL, upsert-on-change, timestamp filtering.
- Query/document embedding mismatch -> use the model's query/passage prefixes; same model+normalization both sides.
- Model fabricates beyond context -> "answer only from context, say unknown", require citations, faithfulness check.
- Duplicate/near-duplicate chunks crowd out diversity -> dedup by hash/similarity, MMR for diversity.
- Changed embedding model, recall dropped -> must re-embed entire corpus; cannot mix spaces.
- Multi-tenant leakage -> enforce metadata filter (tenant_id) at query time, test it.
- Great retrieval metrics, bad answers -> generation/prompt issue, not retrieval; evaluate stages separately.
- Latency too high -> smaller ANN candidate set + rerank, cache embeddings, quantize index, async parallel retrieval.
