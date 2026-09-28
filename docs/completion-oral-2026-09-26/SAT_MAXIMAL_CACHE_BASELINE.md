# Query-driven maximal SAT completion cache

Before freezing the repeated-query experiment, add `sat_maximal_cache` as a
sixth workflow. The original persistent SAT baseline finds arbitrary valid
publications, which can be small. The reference algorithm naturally returns
large supporting kernels. Granting the generic solver a target-driven route
to larger reusable witnesses is therefore a material strong-baseline check;
it does not require compiling the entire completion interface.

For an uncached target D, the method first asks the existing exact persistent
SAT model for a completion. If that query is UNSAT, its target-assumption core
can enter the NO cache. If it returns a verified publication P, the method
repeatedly asks for a strict feasible superset while keeping all of P selected.
The remaining time in the same per-query budget bounds this optional growth.
Every successful enlargement remains valid and includes D. A later UNSAT
proves inclusion maximality; it never becomes a target NO or a cached target
core. The solver uses assumption-gated strict-superset clauses, so later
queries remain free to choose any permitted publication.

An optional growth timeout retains the largest already verified YES witness.
If the whole-history alarm interrupts growth, the driver records that verified
YES and immediately stops; it cannot continue after swallowing the alarm.
The first query's UNSAT core is the only kind of NO certificate stored by this
method. A cached valid K proves YES for any target D contained in K regardless
of whether maximality was proved. The protocol records successful and timed-out
maximization separately from the target decision, including solver-call count,
initial-decision duration and maximality status.

The driver is an attributed copy of the audited IPC harness in
`co_query_benchmark.py`, with common warmup in `co_query_preload.py`. The active
existence driver and all three frozen core solvers remain unchanged. All six
query workflows receive the same unique target order, 60-second per-query
allowance, 900-second whole-history budget and isolated single CPU; interface
methods use the same predeclared 80% compilation allowance. These values are
arguments and must be recorded in the actual freeze, not inferred from this
document. No test-history outcome selects a workflow.

Five directed tests passed, including 300 tiny models with 900 exact queries
against independent all-subset enumeration. Every returned proved maximal
publication was checked against every feasible superset. Additional checks
cover mutually supporting helpers, changing assumptions after growth, retaining
YES on growth timeout, enforcing the whole-history stop, and preserving only
initial target cores. The receipt is
`campaign-v1/audit/query-maximal-cache-dev/TEST_RECEIPT.json`.
Cold test imports experienced filesystem stalls; their elapsed duration is
explicitly not a benchmark result.

This addition tests an ordinary exact generic reuse strategy. It is not a new
theorem or a novelty claim. It may win or lose to both full compilation and the
original incremental baseline. The final report retains those alternatives,
their actual costs, cache hits, witness sizes and unresolved maximization.
