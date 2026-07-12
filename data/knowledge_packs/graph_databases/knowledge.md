# Graph Databases

Store data as **nodes + edges (relationships) + properties**; optimized for traversing connections, not set operations. Win when relationships are first-class and queries are multi-hop.

## When a graph DB
- **Relationships-first**: recommendations, fraud rings, social networks, knowledge graphs, network/IT topology, supply chain, access/entitlement graphs, lineage.
- Queries are **variable-depth traversals** ("friends of friends", "all paths", "shortest route", "who can reach X"): relational needs recursive/self joins that blow up; graph does **index-free adjacency** (each node points directly to its neighbors → O(neighbors) hop, independent of total rows).
- **Don't** use for: aggregations over huge flat tables (use OLAP), simple CRUD with few joins (use RDBMS), high-write timeseries. Graphs shine on connectedness, not scans.

## Property graph vs RDF/triple
- **Property graph** (Neo4j, Memgraph, TigerGraph, Neptune, JanusGraph): nodes & relationships both carry key/value **properties**; relationships are typed + directed + can hold props (`:RATED {stars:5}`). Query: **Cypher/GQL** or **Gremlin**.
- **RDF triple store** (Blazegraph, GraphDB, Stardog, Neptune): everything is `(subject, predicate, object)` triples; no props on edges (must reify); global URIs; **SPARQL**; strong for standards, ontologies (OWL/RDFS), inference, data integration/linked data. Edges can't hold attributes directly.
- Rule: attributes-on-relationships + app graphs → property graph. Interop/ontology/reasoning/web-of-data → RDF.

## Neo4j + Cypher
```cypher
// pattern: (node)-[:REL]->(node); () nodes, [] rels
MATCH (u:User {id:$id})-[:FOLLOWS]->(f)-[:POSTED]->(p:Post)
WHERE p.created > date('2026-01-01')
RETURN f.name, count(p) AS posts ORDER BY posts DESC LIMIT 10;

MERGE (u:User {id:$id})              // upsert node by key, then set
  ON CREATE SET u.created = timestamp()
  ON MATCH  SET u.seen = timestamp();
MATCH (a:User{id:1}),(b:User{id:2})
MERGE (a)-[r:FOLLOWS]->(b) SET r.since = date();

WITH ... // pipe/chain, aggregate, filter between MATCHes (like SQL subquery)
```
- **Clauses**: `MATCH` (read pattern), `OPTIONAL MATCH` (left-join, nulls if absent), `WHERE`, `WITH` (pipe results, aggregate mid-query), `RETURN`, `CREATE`, `MERGE` (match-or-create), `SET`/`REMOVE`, `DETACH DELETE` (node + its rels), `UNWIND` (list→rows), `CALL {}` subqueries.
- **Variable-length**: `(a)-[:KNOWS*1..3]->(b)` = 1–3 hops; `*` unbounded (dangerous). Shortest: `shortestPath((a)-[:KNOWS*]-(b))`, `allShortestPaths`.
- **Indexes/constraints**: `CREATE CONSTRAINT FOR (u:User) REQUIRE u.id IS UNIQUE` (also creates index + enforces uniqueness); `CREATE INDEX FOR (u:User) ON (u.email)`; range/text/point/full-text/vector indexes. Constraints back `MERGE` performance.
- **EXPLAIN/PROFILE** to see `db hits` + whether an index or `AllNodesScan` (bad) is used.

## Gremlin (Apache TinkerPop)
- Imperative traversal DSL, portable across TinkerPop-enabled DBs (JanusGraph, Neptune, etc).
```groovy
g.V().has('User','id',1).out('follows').out('posted')
 .has('created', gt('2026-01-01')).groupCount().by('lang')
```
- Steps: `V()/E()` start, `out()/in()/both()` traverse by edge label, `has()` filter, `values()`, `path()`, `repeat().times()/until()` loops, `dedup`, `order().by()`, `limit`. Declarative option: `match()`.

## Traversals & graph algorithms (Neo4j GDS)
- **BFS** = level-by-level (shortest unweighted path, nearest neighbors); **DFS** = deep-first (path existence, cycles). Weighted shortest: **Dijkstra**; heuristic: **A***.
- **GDS library**: `gds.pageRank` (influence), `gds.louvain`/`gds.labelPropagation` (community detection), `gds.betweenness`/`gds.degree` (centrality), `gds.nodeSimilarity`, `gds.wcc` (connected components), Node2Vec/FastRP embeddings. Run on a **projected in-memory graph** (`gds.graph.project`), not live store.

## Modeling
- Node = entity/noun (User, Product). Relationship = verb (BOUGHT, FOLLOWS), typed + directed; store **properties on the relationship** when the fact belongs to the connection (rating, weight, timestamp, quantity).
- **Property vs relationship**: use a **relationship** when you'll traverse/filter/aggregate on it or connect to many others (e.g. `Order-[:CONTAINS]->Product`); use a **property** for a scalar attribute you only read with its node (name, price). Rule: if a value is shared/queried across entities, make it a node (e.g. `City` node vs `city:"NYC"` string).
- **Intermediate/hyper-nodes** to model n-ary facts (an `Order` node connecting user+products+payment) instead of edge props overload.
- Direction: store one direction; Cypher can traverse either way `-[:R]-` (undirected match).

## vs Relational
- A relationship in RDBMS = FK + JOIN; multi-hop = **recursive self-join / recursive CTE** (`WITH RECURSIVE`), cost grows with table size per hop → exponential slowdown for deep/variable traversals.
- Graph: `(a)-[:R*1..5]->(b)` hops via stored pointers, cost ~ size of touched subgraph. **Break-even**: ≥3–4 join hops, variable depth, or path/reachability queries → graph wins clearly; shallow fixed joins → RDBMS is fine and simpler.
- Many-to-many + evolving schema (add a rel type without migration) favors graph; heavy aggregation/reporting favors relational/OLAP.

## Loading & writing
- Bulk import: `neo4j-admin database import` (offline, fastest for initial load), `LOAD CSV WITH HEADERS` for incremental, `apoc.load.json`.
- Batch large writes to avoid one giant transaction: `CALL { ... } IN TRANSACTIONS OF 10000 ROWS` or `apoc.periodic.iterate`.
- Create constraints **before** bulk `MERGE` so lookups are indexed and dupes impossible.

## Performance
- **Index-free adjacency** → traversal cost scales with subgraph touched, not DB size (relational recursive joins scale with table size).
- **Supernodes** (a node with millions of edges: a celebrity, "USA" country, "true" flag) kill traversals — every hop fans out hugely. Fix: partition edges by type/time, add intermediate nodes, filter by relationship type early, or denormalize.
- Anchor queries on an **indexed start node**, then traverse; never start with a full label scan.

## Gotchas -> Fix
- **Cartesian product** from disconnected `MATCH` patterns (two patterns with no shared variable) → row explosion. Fix: connect patterns, or split with `WITH`, or use `CALL{}` subquery.
- **Unbounded variable-length** `[*]` / `[*..]` → exponential path blowup, OOM. Fix: cap depth `[*..4]`, use `shortestPath`, prune with `WHERE`, use GDS for global algos.
- **Missing unique constraint before `MERGE`** → duplicate nodes created concurrently + full scan per merge. Fix: `CREATE CONSTRAINT ... IS UNIQUE` on the merge key first.
- **`MERGE` on a full pattern** with unset props matches too narrowly/broadly → dupes. Fix: `MERGE` on the identifying node/key only, then `SET` the rest.
- **Supernode** traversals slow/timeout. Fix: split by rel type/time, intermediate nodes, filter rel type, avoid modeling booleans/categories as shared nodes.
- **Modeling everything as a graph** (flat entities, no real traversal) → worse than RDBMS. Fix: only edges you actually traverse belong as relationships; keep pure attributes as properties.
- **Storing high-cardinality scalars as nodes** (every timestamp/email a node) → supernodes + clutter. Fix: keep as property; make a node only if traversed/shared.
- **No index on start-node lookup** → `AllNodesScan`. Fix: index the anchor property; verify with `PROFILE`.
- **Deleting node with relationships** errors. Fix: `DETACH DELETE`.
- **Direction assumptions** miss data (stored one way, queried the other). Fix: undirected match `-[:R]-` when direction is semantic-only.
- **Huge write in one transaction** → heap/lock pressure. Fix: batch (`apoc.periodic.iterate`, `CALL{} IN TRANSACTIONS OF 10000 ROWS`).
- **Using graph for analytical aggregation** over all nodes → slow. Fix: OLAP/warehouse for scans; graph for connectedness.
- **RDF edge attributes** attempted directly → impossible without reification. Fix: reify (make the statement a resource) or use a property graph.
```
