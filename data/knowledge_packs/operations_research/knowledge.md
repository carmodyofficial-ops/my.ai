# Operations Research

## Model-the-problem cheat sheet
- Every optimization model = **decision variables** (what you choose) + **objective** (min/max, one scalar) + **constraints** (feasible region) + parameters (data).
- Continuous, linear obj + linear constraints -> **LP** (solve exactly, polynomial). Some vars integer -> **MILP** (NP-hard). Nonlinear -> NLP; if **convex**, global optimum is tractable, else only local.
- Sequential decisions with overlapping subproblems -> **dynamic programming**. Flow on a graph -> **network models** (often integral for free). Uncertainty/complex logic -> **simulation**. Big/messy, "good enough fast" -> **heuristics/metaheuristics**.
- Tools: **Gurobi/CPLEX** (commercial, fastest MILP), **HiGHS/CBC/GLPK/SCIP** (open), modeling: **PuLP**, **Pyomo**, **OR-Tools** (Google: CP-SAT, routing, flows), **JuMP** (Julia), **AMPL/GAMS**.

## Linear programming
- Standard form: `min cᵀx s.t. Ax ≤ b, x ≥ 0`. Feasible region = convex polytope; **optimum at a vertex** (or an edge/face). 
- **Simplex** (Dantzig): walks vertex-to-vertex improving the objective; exponential worst case but fast in practice. **Interior-point/barrier**: polynomial, better for very large/dense problems.
- **Duality**: every LP (primal) has a **dual**; `max` dual ≤ `min` primal, and at optimum they're **equal (strong duality)**. Dual variables = **shadow prices** (marginal value of relaxing a constraint by one unit). **Complementary slackness**: a non-binding constraint has zero shadow price, and vice versa.
- **Sensitivity analysis**: how far can `c` or `b` change before the optimal basis/solution changes (reduced costs, RHS ranging). Use for "what-if" without re-solving.

## Integer / MILP
- Integer vars model indivisible/logical decisions: binary `x∈{0,1}` for yes/no, assignment, fixed charges, either-or (big-M), counts.
- **LP relaxation** (drop integrality) gives a bound; its objective bounds the MILP optimum. **Integrality gap** = distance between relaxation and true integer optimum.
- Solved by **branch-and-bound** (branch on fractional var, prune by bounds) + **cutting planes** (add valid inequalities: Gomory, cover) = **branch-and-cut**. **MIP gap** = (best bound − incumbent)/incumbent; stop at a tolerance.
- Modeling tips: tight formulations (small integrality gap) solve far faster; avoid huge **big-M**; use logical constraints/indicator vars; symmetry-breaking. Classic: knapsack, set cover, facility location, TSP, scheduling, bin packing.

## Network flows
- **Shortest path**: **Dijkstra** (nonneg weights, O(E log V)), **Bellman-Ford** (handles negative edges, detects negative cycles), **A\*** (heuristic), Floyd-Warshall (all-pairs).
- **Max flow**: Ford-Fulkerson / **Edmonds-Karp** (BFS, O(VE²)), Dinic, push-relabel. **Max-flow = min-cut** (duality). Min-cost flow generalizes.
- **Assignment problem** (n workers to n tasks, min cost): **Hungarian algorithm** O(n³), or as an LP/min-cost-flow. **Transportation/transshipment** problems.
- Network LPs have a **totally unimodular** structure -> the LP relaxation is **naturally integral** (no branching needed) — exploit it.

## Nonlinear & convex optimization
- **Convex**: convex objective over a convex set -> any local min is **global**; efficiently solvable (interior-point). Recognize: linear, quadratic (PSD Hessian), norms, log/exp forms (LP/QP/SOCP/SDP hierarchy). Tools: **CVXPY**, Mosek.
- Non-convex NLP -> multiple local optima; solvers (IPOPT, SNOPT, gradient descent, SQP) find **local** optima -> multi-start or global solvers (BARON, Couenne).
- **KKT conditions** generalize Lagrange multipliers (stationarity, primal/dual feasibility, complementary slackness) — necessary for optimality, sufficient if convex. Lagrangian relaxation/duality for bounds and decomposition.

## Dynamic programming
- Applies with **optimal substructure** + **overlapping subproblems**. Define stages, states, a recurrence (Bellman equation `V(s)=min_a [cost(s,a)+V(s')]`), boundary, then solve backward/forward with memoization.
- Curse of dimensionality: state space explodes -> approximate DP / value iteration. Classics: knapsack, shortest path, inventory, sequence alignment, Markov Decision Processes.

## Queueing theory
- Kendall notation `A/S/c`: arrival/service dist, servers. **M/M/1**: Poisson arrivals rate `λ`, exponential service rate `μ`, 1 server. Utilization `ρ=λ/μ` (**must be <1** for stability).
- M/M/1 results: avg in system `L=ρ/(1−ρ)`, avg wait `W=1/(μ−λ)`. As `ρ→1`, queues **blow up nonlinearly** (not linearly). M/M/c for multiple servers (Erlang C). Variability increases waiting.
- **Little's Law** (very general, any stable system): `L = λ·W` (avg number in system = arrival rate × avg time in system). Also `Lq = λ·Wq` for the queue.

## Simulation
- **Discrete-event simulation (DES)**: model as events changing state at discrete times (arrivals, service completions), event queue advances the clock. Use when analytical queueing assumptions break (general distributions, complex routing). Tools: SimPy, AnyLogic, Arena.
- **Monte Carlo**: sample random inputs -> distribution of outputs; risk/uncertainty. Error `~1/√N`; use **common random numbers** to compare scenarios, enough replications + confidence intervals, warm-up (discard transient).

## Heuristics & metaheuristics
- **Greedy**: locally best choice each step — fast, optimal only for special structure (matroids); else approximate.
- **Local search**: iteratively improve a neighbor (2-opt for TSP) -> stuck at **local optima**.
- **Metaheuristics** escape local optima: **simulated annealing** (accept worse moves w.p. `e^{−Δ/T}`, cool `T`), **genetic algorithms** (population, crossover, mutation, selection), **tabu search** (forbid recent moves), **ant colony/PSO**. No optimality guarantee; tune parameters; use when exact methods are too slow.

## Classic problems & formulations
- **TSP/vehicle routing (VRP)**: visit nodes at min cost; TSP is NP-hard. Exact (MTZ/subtour-elimination MILP) small; heuristics (Christofides, 2-opt/LKH, OR-Tools routing) at scale. VRP adds capacity/time windows.
- **Scheduling**: job-shop/flow-shop, machine assignment, project scheduling (critical path / **CPM**, PERT with uncertainty, resource-constrained RCPSP). Minimize makespan/tardiness. Often MILP or constraint programming (**CP-SAT**).
- **Facility location / set covering / p-median**: where to open facilities to serve demand at min cost (binary open vars + assignment).
- **Knapsack / bin packing / cutting stock**: capacity-constrained selection/packing — DP (knapsack), column generation (cutting stock).
- **Blending/diet, production planning, transportation** — canonical LPs.

## Optimization under uncertainty & multi-objective
- **Stochastic programming**: decisions before uncertainty resolves; two-stage (here-and-now + recourse), scenario trees, expected cost. Sample average approximation.
- **Robust optimization**: optimize against worst case within an uncertainty set — no distribution needed, conservative.
- **Chance constraints**: satisfy a constraint with probability ≥ 1−α.
- **Multi-objective**: no single optimum -> **Pareto frontier** (non-dominated solutions). Methods: weighted sum (misses non-convex regions), **ε-constraint** (optimize one, bound others), goal programming. Present tradeoffs, don't collapse prematurely.
- Decision analysis: expected value, decision trees, value of information; MDP/reinforcement learning for sequential stochastic control.

## Modeling & solver workflow
- Formulate on paper (sets, params, vars, obj, constraints) -> code in a modeling layer (Pyomo/PuLP/OR-Tools) -> hand to a solver -> inspect status (optimal/infeasible/unbounded/time-limit) -> validate solution against reality -> sensitivity/what-if.
- **CP (constraint programming)** (OR-Tools CP-SAT) excels at scheduling, all-different, feasibility, combinatorial logic; complements MILP.
- Warm starts, presolve, tuning (gap, threads, cuts) speed large models. Log the model size (vars/constraints/nonzeros).

## Pitfalls -> Fix
- **Wrong/misaligned objective** (optimizing a proxy) -> mathematically optimal but useless answer -> validate the objective encodes real goals; watch multi-objective tradeoffs (weight/Pareto, ε-constraint).
- **Infeasible model** (over-constrained/contradictory) -> no solution -> relax/soft-constrain (slack + penalty), inspect **IIS** (irreducible infeasible set) from the solver.
- **Unbounded model** (missing constraint, wrong sign, free var) -> objective -> ±∞ -> add bounds; check variable domains and min-vs-max direction.
- **Large integrality gap / weak formulation** -> branch-and-bound crawls -> tighten formulation, add cuts, avoid huge big-M, break symmetry.
- **Assuming LP-optimal is integer** -> fractional "half a truck" -> declare integer vars (MILP); exploit total unimodularity only where it holds.
- **Local optimum reported as global** (non-convex NLP or metaheuristic) -> suboptimal -> check convexity; multi-start, global solver, or accept heuristic with a bound.
- **Queue at ρ ≥ 1** or ignoring variability -> unstable/underestimated waits -> ensure `ρ<1`; remember waiting explodes near capacity and grows with variability.
- **Too few simulation replications / no CI / no warm-up** -> conclusions from noise -> enough runs, report confidence intervals, discard transient, common random numbers to compare.
- **Numerical scaling** (coefficients spanning many orders of magnitude, big-M huge) -> solver instability/ill-conditioning -> scale data, keep big-M tight.
- **Over-tight solver gap on huge MILP** -> never finishes -> set a MIP gap tolerance / time limit; accept a good incumbent with a bound.
