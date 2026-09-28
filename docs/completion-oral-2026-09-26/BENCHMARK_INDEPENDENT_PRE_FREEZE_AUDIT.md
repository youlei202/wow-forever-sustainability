# Independent benchmark audit before frozen testing

Reviewed `co_benchmark_design.py` and `co_benchmark.py` after the first 60-instance
development pilot, before the primary test freeze. The synthetic registry uses
fixed generation seeds and family/size positions, rather than solver results,
to select test cases, query histories and target streams. Actual item and row
counts are retained where the hardness construction differs from nominal N.
Fixed-y and unknown-y comparisons give identical exact tasks to each method.
The primary timing driver pins one process to each distinct physical core;
library thread limits and absence of native workload are recorded separately.

The initial pilot exposed no encoding disagreements. Its 2-second budgets are
development measurements, not substitutes for the frozen primary budgets.
Current code changes must be frozen under a new source identity; pilot source
snapshots were preserved before the changes below.

Issues identified and corrections requested before test freeze:

1. A zero above-cap conflict graph is not a zero residual graph at every
   intermediate frontier. The `frontier_grid_control` initially had future–future
   physical pairs, so it did not establish the requested k=0 control for unknown
   y. Restrict this explicitly synthetic physical domain to anchor-star pairs
   from its generation rule; each row then contains at most one optional item
   and residual k is zero for every frontier. This is a new construction, not
   outcome-based deletion of measured native rows.
2. The reference compiler originally saved kernels after completing all
   branches at one frontier. A timeout could discard valid kernels already
   found inside that call. A callback now stores each independently verified
   kernel immediately, and live counters survive timeout. A directed test
   interrupts immediately after saving a kernel and verifies the partial
   interface still answers YES for contained targets and cannot answer NO.
3. An invalid-history compiled result must propagate INVALID_INITIAL when
   queried, not UNKNOWN. The shared query adapter now does so.
4. Give the custom method the same legitimate YES-completion and NO-target
   cache opportunity as incremental SAT. Keep the required completely fresh
   reference workflow as a separate comparator; add a cached reference
   workflow rather than silently changing what “fresh” means.
5. Preserve memory-limit outcomes as UNKNOWN_MEMORY and keep partial prefix
   times/preparation/interface counts on whole-workflow timeout. Recorded
   partial query JSONL is authoritative; neither timeout nor memory exhaustion
   implies NO.
6. The initial import comment was inaccurate: generic constructors lazily
   import their native libraries. Either charge those imports explicitly as
   model startup or pre-import both common libraries before all method clocks.
   The external process receipt remains a separate startup-inclusive measure.
7. Spread randomized CP-SAT repetitions over size/Q strata; the initial
   index rule selected only the smallest size. Glucose repetitions are
   deterministic repeat labels because the chosen API has no configurable
   random seed. They are not independent ecosystems or randomized SAT runs.
8. A witness-validation error or disagreement among resolved exact answers
   invalidates speed interpretation until investigated. The runner should
   suspend subsequent jobs or retain a global correctness-failure flag, rather
   than silently aggregate an ERROR as an ordinary slow solve.

SAT target-core cache logic is sound for the current query workflow. Every
assumption is a positive required item; an empty UNSAT core establishes that
the base contract itself is infeasible. The strict-superset gate appears only
inside a separate compilation object, so it cannot be misread as a target
core in the repeated-query cache. An exact reference NO may cache the whole
target D as an excluding core even when no minimal core is available.

Generic maximality uses strict supersets, and its blocking clauses discard
subsets of already proved maximal sets. A feasible strict superset of any
current P cannot be removed by those older subset blocks, so the maximality
claim remains valid. Incomplete interfaces may still contain valid but not
proved maximal completions; this distinction is explicit in their metadata.

Query streams are deduplicated and generated without outcome labels. Short
prefixes after a shuffle need not preserve the final mixture exactly; retain
the actual query kinds and denominators. The selected streams test small
target sets, not every large subset of the future universe. Repeated queries,
CP seeds, paired fixed/unknown tasks and threshold variants must remain
clustered under the underlying generated history in summaries.

This audit records findings and required corrections; the root runner's final
source freeze and executed receipts determine which changes were applied.
