# Independent audit of the six-method query workflow

The pre-query gate passed on 2026-09-26. This review was performed by the native
catalogue analyst, independently of the exact-solver agent who implemented the
new driver. No frozen primary scientific module was modified. The receipt is
`campaign-v1/checks/SIX_METHOD_INDEPENDENT_AUDIT.json`; the reproducible gate is
`scripts/audit_completion_query_driver.py`.

The reviewed `co_query_benchmark.py` SHA-256 is
`df64a1307716f864786091b7b90b9c2ee1257e2f4d69b47ed9c94d8613525745`.
The reviewed native registry design SHA-256 is
`5c46daf3f851ad5a8bb94737e3ad641e37ca67d9ad75119b6c074b93268d50f8`.

## Answer direction and persistent state

The maximal-cache baseline first solves the requested target. Its optional
growth queries force every item of the last verified completion and at least
one further item. Growth UNSAT proves maximality and leaves the target answer
YES. A growth timeout leaves a valid, possibly nonmaximal YES. If the common
history alarm interrupts growth, the driver records this YES and immediately
ends the history: catching the alarm does not grant another history budget.
Only an initial target UNSAT core enters the negative cache.

The strict-superset clause has a fresh selector and is enabled by an assumption.
In subsequent queries the selector can be false. Therefore an exhausted growth
branch cannot exclude a later, incompatible publication. A verified cached
publication proves YES for every target it contains. A previously unsatisfiable
target core proves NO for every target containing that core. Neither rule reads
the future query stream to choose a publication.

The independent small gate used eight separately constructed exact models,
including incompatible optional diagonal pairs, all 16 optional target subsets,
and reversed repeats after growth. Across all six workflows it checked 1,536
answers against independent all-publication enumeration: 432 YES witnesses
passed the exact verifier and 1,104 NO answers agreed; 665 records exercised a
cache hit. A separate persistent solver sequence checked 256 target decisions
and every claimed maximal completion against all feasible strict supersets.
Three scripted cases isolated growth UNSAT, local timeout and whole-history
alarm. This is a correctness gate, not test performance evidence.

## Equal task and measured costs

All six workflows receive the same exact table, source obligations, history,
gain contract and target order. Every isolated job begins with fresh problem
state. All have the same whole-history wall budget and per-query allowance;
the two complete-interface methods share the same 80% compilation allocation.
Generic maximal growth spends the current query's remaining allowance. Its
unresolved growth does not turn a solved target into UNKNOWN or a later query
into NO. Partial interfaces can answer YES from stored witnesses; uncovered
queries remain UNKNOWN unless interface enumeration is complete.

The method clock includes exact parsing, construction, solving, successful
witness checks, interface JSON serialization/reload, validation of its stored
kernels, cache lookup and JSON query recording. Common library startup is
reported separately and performed for all methods. Durable network archive I/O
and final solver destruction are outside the recorded method interval. Archive
duration and outer process receipts remain available; consequently these
results describe reuse in an already running process, not total user latency
including durable export. CPU limits and process wall/memory termination apply
equally. Infrastructure errors stop the suite and are never solver NO.

## Native registry contract

The gate checked every one of 48 native workflow records: eight inherited and
16 new histories, each with fixed-y and unknown-y versions. Both versions
preserve the same model and target. The fixed y is the coordinatewise largest
physical response between the current frontier and the cap. It need not be
jointly attainable; fixed-y solvers must enforce exact attainment. This is an
explicit common question, not a claim that its answer is YES.

Every new model is an unchanged exact decimal encoding of its registered
confirmation table, and its first registered target is copied without outcome
selection. Every inherited model was checked directly against the compact
moments and original bounds: tolerance, cap and gain increments scale with the
original reference S; H includes the selected first release, and the next gain
is relative to F(H), as implemented by all exact solvers. Replacing this current
frontier by the original S would ask a different question. All 24 query streams
contain unique, valid optional targets.

No blocking issue was found. These gates support exact answer consistency and
matching contracts; they do not establish algorithmic superiority, population
coverage, or a new theorem.
