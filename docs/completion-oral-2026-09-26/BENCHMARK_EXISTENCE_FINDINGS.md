# Frozen decision benchmark findings

These findings use `campaign-v1/benchmark/test-existence-v2` and the compact,
independently checked `benchmark/report-existence-v1`. The initial NAS-stalled
v1 is wholly excluded from comparative timing. The two repeated-query panels
and native tables are separate experiments, not inferred from these results.

The primary seed-0 denominator is 240 exact synthetic questions: 120 histories,
each with one given-frontier and one unknown-frontier question. Additional
repeat labels bring the execution count to 1,080, not 1,080 independent worlds.
All 240 questions receive consistent exact decisions from CP-SAT and SAT/PB.
The supplied Python reference resolves 205; 35 return UNKNOWN_TIMEOUT at the
same 60-second wall limit. Independently checking 428 distinct returned YES
witnesses found no invalid completion. NO remains solver-issued evidence,
not an independently checked proof trace.

| Workflow | Reference solved / 120 | CP-SAT solved / 120 | SAT/PB solved / 120 | PAR-2 seconds: reference / CP-SAT / SAT |
|---|---:|---:|---:|---:|
| Given frontier | 112 | 120 | 120 | 8.463 / 0.2181 / 0.04633 |
| Unknown frontier | 93 | 120 | 120 | 27.608 / 0.3003 / 0.04724 |

The reference is often very fast on its easy cases. On jointly solved
given-frontier questions, its geometric time ratio to SAT is 0.673; on jointly
solved unknown-frontier questions it is 1.798. Reporting only solved medians
would hide the reference's unresolved tail. The measured result rejects a
blanket speed advantage for this implementation; it does not invalidate the
completion characterization or establish an asymptotic separation.

An exact diagnostic excludes an easy alternative explanation: 31 of the 35
reference timeouts occur when the mandatory history plus target is within
the global cap. Four unknown-frontier timeouts do have an immediate global-cap
obstruction. Those four show an avoidable presolve omission in the readable
reference and should not be presented as evidence of intrinsic frontier
complexity. No post-test optimization or selective rerun was applied.

The sparse physical-star control gives a more specific diagnostic. Every
registered configuration contains at most one item outside the history. Thus
the residual optional-item conflict graph has no edge at every frontier, so
its conflict cover is exactly zero, independently of missing runtime counters.
All 20 given-frontier controls finish; eight unknown-frontier controls time
out, with response-grid Cartesian upper counts from 1,048,576 to
4,347,792,138,496. Both generic encodings solve those eight in milliseconds to
fractions of a second. The control has explicit sparse physical configurations
and is not a claim that native equipment permits the same sparsity. It shows
that small conflict cover alone does not predict total unknown-frontier cost;
the representation and enumeration of frontier candidates matter separately.
The Cartesian counts are upper bounds on enumerated candidates, not counts
of jointly attainable frontier vectors.

The matching-source family causes eight reference timeouts in each workflow.
This is a distinct source/branch difficulty, beyond merely searching the
frontier grid. Recorded reference counters are only encountered maxima;
the outer deadline preempts their return on timed-out attempts. Missing
timeout counters remain unavailable rather than zero or global maxima.

All timing claims concern an in-memory service with common libraries already
loaded. Parsing, construction, solving and exact witness checks are timed.
Common startup and durable NAS archival are recorded separately; neither cold
deployment throughput nor durable-storage performance follows from this table.
Whether complete interfaces repay their preparation cost, and whether a strong
generic maximal-witness cache already captures their practical benefit, must
be decided by the separately frozen six-method repeated-query comparison.
