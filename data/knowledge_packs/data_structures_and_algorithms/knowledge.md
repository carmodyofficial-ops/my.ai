# DSA Quick Reference

## Pick the right structure
- **Dynamic array** — indexed access, append, iterate. Default container. Contiguous -> cache-friendly.
- **Hashmap** — O(1) avg lookup/insert by key. `seen[x]=i`. Unordered; needs hashable keys.
- **Set** — dedup + membership. `if x in seen`.
- **Linked list** — O(1) splice given the node; O(n) index/search. Rare; avoid for random access. Pointer-chasing = cache misses.
- **Stack (LIFO)** — undo, DFS, matching parens, monotonic stack (next-greater in O(n)).
- **Queue / deque** — FIFO/BFS; deque = O(1) both ends, sliding-window buffer.
- **Heap / priority queue** — repeated min/max; top-k, Dijkstra, merge-k. `heappush/heappop` O(log n). Binary heap = array, not sorted.
- **Balanced BST / sorted structure** (`TreeMap`, red-black, AVL, B-tree) — ordered iteration + range/nearest/floor/ceil queries in O(log n).
- **Graph adjacency-list** `{node:[neighbors]}` — sparse graphs, O(V+E) space. **Adjacency-matrix** — dense / O(1) edge test, O(V^2) space.
- **Trie** — prefix search, autocomplete, dictionaries. O(len) ops, memory-heavy.
- **Union-Find (DSU)** — connectivity/merging; near-O(1) amortized with path compression + union by rank.

## Big-O of common ops
- Array: index O(1), search O(n), append amortized O(1), insert/delete-mid O(n).
- Hashmap/Set: get/put/contains O(1) avg, O(n) worst (collisions/resize).
- Heap: push/pop O(log n), peek O(1), build-heap O(n).
- Balanced BST: search/insert/delete O(log n); in-order = sorted.
- Linked list: index/search O(n), splice O(1) with node ref.
- Trie: insert/lookup O(key length).

## Complexity
- **Time + space**, worst/avg/amortized. **Amortized**: dynamic-array append is O(1) amortized (doubling), O(n) on the resize. **Big-O** hides constants — for small n a "worse" O with tiny constant can win.
- Recursion cost = states x work/state; recursion uses **O(depth) stack**.

## Sorting
- **Comparison sorts floor = O(n log n)**. Built-in **Timsort** (Python/Java objects) is stable, adaptive, O(n log n).
- **Quicksort** O(n log n) avg / **O(n^2) worst** (bad pivot), in-place, unstable, great cache behavior.
- **Merge sort** O(n log n) guaranteed, **stable**, O(n) extra space; good for linked lists / external sort.
- **Heapsort** O(n log n), in-place, unstable.
- **Non-comparison**: counting/radix/bucket O(n+k) for bounded integer/keyed data.
- **Stability** = equal keys keep input order; needed for multi-key sorts. Sort to enable binary search / two-pointer / grouping / dedup.

## Searching
- **Binary search**: sorted data only -> O(log n). Also **"binary search the answer"** on a monotonic predicate (min feasible value). Watch bounds: `lo<=hi`, `mid=lo+(hi-lo)//2` (avoid overflow), correct half update.

## Graph algorithms
- **BFS** (queue): shortest path in **unweighted** graph, level-order. O(V+E).
- **DFS** (stack/recursion): reachability, cycle detection, topological sort, backtracking. O(V+E). Mark visited or you loop forever.
- **Dijkstra** (min-heap): shortest path, **non-negative** weights, O((V+E)log V). Negative edges -> **Bellman-Ford** O(VE) (detects negative cycles).
- **Topological sort**: DAG ordering via Kahn's (in-degree queue) or DFS post-order; cycle -> no valid order.
- **Union-Find**: connected components, cycle detection in undirected, **Kruskal's** MST. **Prim's** MST via heap.
- A* = Dijkstra + admissible heuristic.

## Recursion & DP
- **DP** = overlapping subproblems + optimal substructure. Define **state + transition + base case + order**.
  - **Memoization** (top-down): recursion + cache; computes only needed states, recursion-depth risk.
  - **Tabulation** (bottom-up): fill a table iteratively; often O(1)-row space-optimizable.
- Classics: knapsack, LCS/edit-distance, coin change, LIS (O(n log n) with patience), interval DP, grid paths.
- **Greedy**: local optimum -> global — only when the problem has the greedy-choice property (interval scheduling, Huffman, Dijkstra). Prove it; otherwise DP.

## Patterns
- **Two-pointer**: sorted array pair-sum, in-place partition/dedup, merge. O(n).
- **Sliding window**: contiguous subarray/substring under a constraint (longest/shortest/at-most-k). O(n); expand right, shrink left.
- **Fast/slow pointers**: cycle detection (Floyd), middle of list.
- **Prefix sums / difference arrays**: range-sum/range-update in O(1) after O(n) precompute.
- **Hashing**: trade space for time — precompute counts/index (two-sum O(n)).
- **Backtracking**: build candidate, prune invalid, undo (permutations, N-queens, subsets).

## Hashing internals
- Hashmap = array of buckets + hash function. **Collisions** resolved by chaining (linked/tree buckets) or **open addressing** (linear/quadratic probing). Load factor triggers **resize + rehash** (amortized O(1), one slow op).
- Keys must be **immutable + consistent hash/eq**; mutating a key after insert corrupts lookup. Adversarial keys -> worst-case O(n) (hash-flooding); use randomized/keyed hashing for untrusted input.

## Trees & heaps detail
- **BST**: left < node < right; in-order traversal = sorted. Unbalanced (sorted inserts) degrades to a list.
- **Self-balancing**: AVL (strict balance, faster reads), red-black (looser, faster writes — `TreeMap`/`std::map`). **B-tree/B+tree**: high fan-out, disk/DB indexes (fewer seeks).
- **Binary heap**: complete tree in an array; parent `(i-1)/2`, children `2i+1/2i+2`. Not sorted — only root ordering guaranteed.
- **Traversals**: pre/in/post-order (DFS) recursive or with a stack; level-order (BFS) with a queue.

## Decision rules
- Fast lookup -> **hashmap**. Ordering/range -> **balanced tree/sorted**. Repeated min/max -> **heap**. Prefixes -> **trie**. Dedup -> **set**. Connectivity/merge -> **union-find**. Shortest unweighted -> **BFS**; weighted non-negative -> **Dijkstra**; negative -> **Bellman-Ford**. Overlapping subproblems -> **DP**. Contiguous window -> **sliding window**.

## Strings & bits
- **String algorithms**: substring search KMP/Rabin-Karp O(n+m); anagram/frequency via counts; palindrome via two-pointer; use a **rolling hash** for many comparisons. Strings often immutable -> mutation is O(n); build with a list/`StringBuilder`.
- **Bit manipulation**: `x & (x-1)` clears lowest set bit; `x & -x` isolates it; `x ^ y` swap/toggle; check bit `x >> i & 1`; bitmask = compact set for small universes (subset/DP-over-subsets).

## Gotchas -> Fix
- **Off-by-one** at loop/array bounds -> pin inclusive/exclusive; test empty, single, two-element inputs.
- **Nested O(n^2)** where a hashmap gives O(n) (two-sum) -> hash it.
- **Linear scan of sorted data** -> binary-search instead.
- **Wrong DS for access pattern** (list for membership, array for mid-insert) -> match structure to operation.
- **Integer overflow** in sums/products/`mid`/hash -> use wider type or `lo+(hi-lo)/2`; mod arithmetic.
- **Mutating a collection while iterating** -> iterate a copy, build a new collection, or collect indices then delete descending.
- **Recursion too deep** -> stack overflow -> convert to iteration/explicit stack, or increase limit.
- **Unbalanced BST** degrades to O(n) (sorted inserts) -> use a self-balancing tree or a heap/hashmap.
- **Assuming hashmap is ordered / stable-iteration** -> use an ordered map if order matters.
- **Forgetting visited set** in graph traversal -> infinite loop -> mark on enqueue/visit.
- **Dijkstra with negative edges** gives wrong answer -> Bellman-Ford.
- **Unstable sort where stability needed** -> pick a stable sort or add a tiebreaker key.
- **Claimed vs real complexity** (hidden O(n) `in`/slice/`+string` inside a loop) -> know your language's op costs.
- **Floating-point equality / precision** -> compare with epsilon; use integers/decimals for money.
