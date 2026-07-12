# Coding Interview Patterns

## Pattern -> When to use -> Complexity
- **Two pointers**: sorted array/string, pair-sum, dedupe, palindrome, partition. Opposite ends or same-direction. `O(n)` time, `O(1)` space. Trigger: "sorted" + "pair/triplet/target". Ex: two-sum-sorted, 3sum (sort + fix i + two-pointer), remove-dups in place, container-with-most-water.
- **Sliding window**: contiguous subarray/substring, "longest/shortest/max/min ... with constraint". Fixed window (size k) or variable (expand right, shrink left while invalid). `O(n)`. Ex: longest-substring-no-repeat (window + `seen` map), max-sum-subarray-size-k, min-window-substring, longest-with-at-most-k-distinct.
- **Fast & slow pointers (Floyd)**: linked-list cycle, cycle start, middle node, happy number, find duplicate (array-as-linked-list). `O(n)`/`O(1)`. Cycle start: after meet, reset one to head, advance both by 1.
- **Merge intervals**: overlapping intervals, meeting rooms, insert interval. Sort by start `O(n log n)`; merge if `cur.start <= prev.end`. Meeting-rooms-II = min heap of end times, or sweep line.
- **Cyclic sort**: array of `1..n` or `0..n-1`, find missing/duplicate/first-missing-positive. Place each value at index `val-1`; `O(n)`, `O(1)`. Swap while `nums[i] != nums[nums[i]-1]`.
- **In-place linked-list reversal**: reverse list/sublist/k-groups, rotate. Track `prev,cur,next`. `O(n)`/`O(1)`.
- **Tree BFS**: level-order, level averages, zigzag, min-depth, right-side view, connect-level-siblings. Queue, process `len=q.size()` per level. `O(n)`.
- **Tree DFS**: root-to-leaf paths, path-sum, diameter, LCA, subtree checks. Recursion/stack; return value bubbles up (e.g. diameter = max over nodes of `L+R`). `O(n)`/`O(h)` stack.
- **Topological sort (Kahn)**: dependency order, course-schedule, task/build order, cycle detect in DAG. Compute in-degrees, queue zero-in-degree, pop + decrement. If output < N -> cycle. `O(V+E)`.
- **Binary search**: sorted lookup, first/last occurrence, rotated array, search-in-2D. `lo<=hi`, `mid=lo+(hi-lo)/2` (avoid overflow). `O(log n)`.
- **Binary search on answer**: "min/max feasible X" with monotonic predicate — koko-bananas, ship-within-days, split-array-largest-sum, min-days. Search value space, `feasible(mid)` check. `O(n log(range))`.
- **Top-K / heap**: k largest/smallest/closest, k-frequent, merge-k-lists, median stream (two heaps). Min-heap of size k for k-largest (`O(n log k)`). K-frequent: bucket sort `O(n)`.
- **Backtracking**: permutations, combinations, subsets, N-queens, sudoku, word-search, generate-parentheses, combination-sum. Choose -> recurse -> undo. Prune early. Exponential (`O(2^n)`, `O(n!)`).
- **Monotonic stack**: next-greater/smaller element, daily-temperatures, largest-rectangle-histogram, stock-span, trapping-rain-water. Stack keeps increasing/decreasing indices. `O(n)`.
- **Union-Find (DSU)**: connected components, number-of-islands (dynamic), redundant-connection, accounts-merge, cycle in undirected graph. Path compression + union by rank -> near `O(1)` amortized.
- **Trie**: prefix search, autocomplete, word-dictionary, word-search-II, replace-words. Node = children map + `isEnd`. Insert/search `O(L)`.
- **Bit manipulation**: single-number (XOR all), counting bits, subsets via bitmask, power-of-two (`n&(n-1)==0`), swap without temp. `x & -x` = lowest set bit; `x ^= (1<<i)` toggle.
- **Greedy**: jump-game, gas-station, task-scheduler, activity-selection, assign-cookies, non-overlapping-intervals. Prove local choice is safe (exchange argument). Often sort first. `O(n log n)`.

## Dynamic Programming
- **When**: overlapping subproblems + optimal substructure; "count ways", "min/max cost", "can we reach", "longest/shortest". Define state, recurrence, base case, order; memoize (top-down) or tabulate (bottom-up).
- **0/1 knapsack**: each item once. `dp[w] = max(dp[w], dp[w-wt]+val)`, iterate weights **descending**. Variants: subset-sum, partition-equal-subset, target-sum, last-stone-weight-II. `O(n*W)`.
- **Unbounded knapsack**: items reusable — coin-change (min coins / count ways), rod-cutting. Iterate weights **ascending**. Coin-change ways: loop coins outer, amount inner (order matters to avoid perms).
- **LCS (longest common subseq)**: 2D `dp[i][j]`; match -> `dp[i-1][j-1]+1` else `max(dp[i-1][j],dp[i][j-1])`. Basis for edit-distance, min-delete, longest-palindromic-subseq (LCS of s and reverse). `O(m*n)`.
- **LIS (longest increasing subseq)**: DP `O(n^2)`; patience/binary-search (`bisect` into tails) `O(n log n)`.
- **Matrix paths**: unique-paths, min-path-sum, dungeon-game, maximal-square. `dp[i][j]` from top/left. `O(m*n)`; roll to 1D row for `O(n)` space.
- **Other classics**: house-robber (`dp[i]=max(dp[i-1],dp[i-2]+a[i])`), word-break (`dp[i]=any dp[j] & dict[j:i]`), decode-ways, longest-palindromic-substring (expand-around-center or DP), matrix-chain, stock with cooldown/fees (state machine).
- **Optimization**: reduce dimensions (rolling array), memo with `@lru_cache` for top-down clarity.

## Graph patterns
- **Grid BFS/DFS**: number-of-islands, flood-fill, rotting-oranges (multi-source BFS), surrounded-regions, walls-and-gates. Treat cells as nodes, 4/8 neighbors as edges; mark visited to avoid revisits. `O(rows*cols)`.
- **Multi-source BFS**: start queue seeded with all sources (rotting oranges, 0/1-matrix distance) -> shortest distance from nearest source in one sweep.
- **Dijkstra**: shortest path, non-negative weights — network-delay, cheapest-flights (with stops), path-with-min-effort. Min-heap of `(dist,node)`; relax neighbors. `O(E log V)`.
- **BFS = shortest path on unweighted** graph; DFS for connectivity/paths/cycle detection.
- **Bidirectional BFS / word-ladder**: BFS layer by layer transforming states; bidirectional halves the frontier.
- **Bellman-Ford** for negative edges; **Floyd-Warshall** all-pairs `O(V^3)`.

## String & misc patterns
- **Hash map frequency**: anagrams (group by sorted key or count vector), first-unique-char, valid-anagram, ransom-note. `O(n)`.
- **Prefix sum**: subarray-sum-equals-k (map of running sum), range-sum-query, product-except-self. Turns `O(n^2)` range work into `O(n)`.
- **Two heaps**: median-of-stream (max-heap low half, min-heap high half), sliding-window-median, IPO. Balance sizes.
- **Interval + sweep line**: meeting-rooms, employee-free-time, min-arrows; sort events, sweep counting active.
- **Kadane** (max-subarray): running `cur=max(a[i],cur+a[i])`, track global max. `O(n)`.
- **Reservoir sampling / Fisher-Yates shuffle** for streaming/random.

## Problem-solving approach
1. **Clarify**: input types, size/ranges, sorted?, duplicates?, negatives?, empty/null, return value, in-place?, unicode/ASCII. Restate the problem back.
2. **Examples**: walk 1-2 concrete cases + an edge case by hand.
3. **Brute force first**: state it, give its complexity, *then* optimize — never stay silent.
4. **Identify pattern** from cues above; pick data structure (hash map for O(1) lookup, heap for order, stack for LIFO/nesting).
5. **Pseudocode / narrate** before coding; confirm approach with interviewer.
6. **Code** cleanly, meaningful names, handle edges.
7. **Test**: dry-run normal + edge (empty, single, all-same, max) + trace a small input line by line.
8. **State complexity** time & space and whether it can improve.

## Complexity cues
- Nested loops over n -> `O(n^2)`; halving -> `log n`; sort dominates -> `n log n`; recursion tree branch^depth.
- Hash map/set trades `O(n)` space for `O(1)` lookup (many two-sum-style optimizations).
- Recursion space = max stack depth (`O(h)` for balanced tree, `O(n)` skewed).
- Target from constraints: `n<=20` -> exponential/bitmask OK; `n<=10^3` -> `O(n^2)`; `n<=10^5..10^6` -> `O(n log n)`/`O(n)`.

## Data structure -> use
- **Hash map/set**: `O(1)` lookup/insert/dedupe; two-sum, frequency, seen-before.
- **Stack**: LIFO, nesting/matching (valid-parens), monotonic, DFS iteration, undo.
- **Queue/deque**: BFS, level-order, sliding-window-max (monotonic deque). Deque = both ends `O(1)`.
- **Heap (priority queue)**: repeatedly get min/max; top-K, scheduling, Dijkstra. Insert/pop `O(log n)`.
- **Balanced BST / sorted structure (TreeMap)**: ordered queries, floor/ceil, range; `O(log n)`.
- **Trie**: prefix sets. **DSU**: dynamic connectivity. **Segment tree / Fenwick (BIT)**: range query + point update `O(log n)`.
- **Linked list**: `O(1)` insert/delete at known node; no random access.

## Communication
- Think out loud continuously; interviewer scores reasoning, not just the final answer.
- Announce the pattern and *why*. Discuss tradeoffs (time vs space, readability vs micro-opt).
- If stuck, verbalize: reduce to smaller case, try brute force, look for repeated work, sort, add a hash map.

## Pitfalls -> Fix
- **Jumping straight to code** -> restate problem + confirm approach before typing.
- **Not clarifying** (ranges, dups, empty, negatives) -> ask upfront; assumptions cost you.
- **No edge cases** (empty, single element, all-equal, overflow, one-node list, cycle) -> keep a mental checklist; test them.
- **Silent solving** -> narrate; a good idea unheard scores nothing.
- **Off-by-one** in loops/binary-search/windows -> fix boundaries (`<=` vs `<`), decide inclusive/exclusive, dry-run len 0/1/2.
- **Wrong complexity claim** -> count nested loops honestly; hidden costs (`in` on list is `O(n)`, string concat in loop `O(n^2)`, slicing copies).
- **Binary-search infinite loop** -> ensure the search space shrinks each iteration; standard `mid` and correct `lo=mid+1`/`hi=mid-1`.
- **Mutating while iterating** a list/dict -> iterate a copy or build a new collection.
- **Global/shared mutable state in backtracking** -> undo the choice (pop) after recursion; append a copy of the path, not the reference.
- **Recursion depth / stack overflow** on large n -> convert to iterative with explicit stack, or note the limit.
- **Integer overflow** (other languages) -> `lo+(hi-lo)/2`; use `long` where products/sums grow.
- **Using `key=index` mental model / reusing pointers** in linked lists -> save `next` before rewiring.
- **Ignoring the sorted hint** -> sorted input almost always means two-pointer or binary search, not a hash map.
- **Premature optimization** -> get a correct brute force compiling first; optimize only if asked/time allows.
