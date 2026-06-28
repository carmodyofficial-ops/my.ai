# DSA Quick Reference

## Pick the Right Structure
- **Dynamic array** — indexed access, append, iterate. Default container.
- **Hashmap** — O(1) lookup/insert by key. `seen[x]=i`.
- **Set** — dedup + membership. `if x in seen`.
- **Linked list** — O(1) splice mid-list; rare, avoid for random access.
- **Stack (LIFO)** — undo, DFS, matching parens, monotonic stack.
- **Queue/deque** — FIFO/BFS; deque = O(1) both ends, sliding window.
- **Heap/priority-queue** — repeated min/max; top-k, Dijkstra. `heappush/heappop`.
- **Tree/BST / sorted structure** — ordered iteration + range/nearest queries.
- **Graph adjacency-list** — `{node: [neighbors]}`; sparse graphs.
- **Trie** — prefix search, autocomplete, word dictionaries.

## Big-O of Common Ops
- Array: index O(1), search O(n), append O(1)*, insert-mid O(n).
- Hashmap/Set: get/put/contains O(1) avg.
- Heap: push/pop O(log n), peek O(1).
- BST/sorted: search/insert O(log n) balanced.
- Linked list: index O(n), splice O(1) w/ node.

## Algorithms
- **Sort**: use built-in (Timsort, stable, O(n log n)). Sort to enable binary search / two-pointer / grouping.
- **Binary search**: sorted data only -> O(log n). Also "search the answer".
- **BFS**: shortest path in unweighted graph; level-order. Queue.
- **DFS**: reachability, cycles, topo, backtracking. Stack/recursion.
- **DP**: overlapping subproblems -> memoize; define state + transition.
- **Two-pointer**: sorted array, pair-sum, in-place partition. O(n).
- **Sliding window**: contiguous subarray/substring under a constraint. O(n).
- **Hashing**: trade space for time — precompute counts/index.

## Decision Rules
- Fast lookup -> **hashmap**.
- Need ordering / range -> **tree/sorted**.
- Repeated min/max -> **heap**.
- Prefixes -> **trie**. Dedup -> **set**.

## Gotchas
- Nested loop O(n^2) where a hashmap gives O(n) (two-sum).
- Linear scan of sorted data — binary-search instead.
- Wrong DS for access pattern (list for membership tests).
- Premature optimization — clarity first, optimize hot paths.
