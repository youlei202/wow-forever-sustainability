# Completion contract and encoding audit

The Phase 0 correctness gate passed. The new exact table oracle, the supplied
conflict-cover/support-deletion algorithm, direct CP-SAT, and persistent SAT/PB
agree on 1,200 frozen small instances: 28,800 decision comparisons and 7,200
complete-interface comparisons. Every compiled maximal set was compared with
the full feasible-subset family. These are synthetic implementation checks, not
native coverage or independent population confirmation.

## Mathematical basis and reproduced reference

Read the current paper's model, theory, inference, proofs and methods, and the
supplied completion implementation. The current paper and separate completion
theory contain byte-identical `completion.py`, `verify.py` and
`native_reanalysis.py` (the completion source SHA-256 is
`2a856a4ba1ecf06691a4acd651dff1ea796aeec1fc6ac3618e0361f1182b0909`).

The fixed-frontier argument is sound: an above-frontier physical row forbids its
entire support, even below the final cap. Conditioning on a bipartite conflict
cover leaves safe ambient sets. At a fixed comparison vector, source support is
monotone in available configurations, so justified deletion preserves every
supporting subset. Exact frontier attainment and retention of every selected
cover item are required after deletion. Enumerating every qualifying attained
frontier and removing contained kernels produces exactly the maximal feasible
sets. The proof does not imply a small output, fast variable-Q enumeration,
bounded-cardinality correctness, or single-item maximality.

The copied reference package was executed under
`$WOWFS_WORK_ROOT/artifacts/completion-oral-extension-2026-09-26/campaign-v1/audit/reference-paper-rerun`.
The original frozen extraction was not modified. Its exact checks passed,
including 500 fixed-frontier, 700 nontrivial conflict, 120 unknown-frontier,
100 interface, 77 hardness, 250 perturbation, and 200 interface-inclusion
instances. The all-width native certificate and mean interfaces were rebuilt
from unchanged moments. Both trinket bad histories still exclude all 8,192
supersets; the previously supported good paths persist. This is reproduction
of old evidence and spends no new alpha or combat samples.

The full `run_checks.sh` then failed at the manuscript display check because
`pdftotext` was absent from PATH. That infrastructure failure is retained in
`audit/reference-paper-rerun.log`; it does not turn the already completed
mathematical subchecks into a successful full script. No manuscript edits were
made by this work.

## Exact contract

`co_exact.Model` accepts integers, `Fraction`, or explicit decimal/rational
strings, and rejects Python float/bool inputs. A native adapter must explicitly
export its retained mean precision to strings, whose resulting finite table
is the deterministic object being compared. This is not a claim that sample
means equal population means. Weights sum exactly to one. Cap, tolerance,
gain, required source mass and gain mass have common task dimensions and
validated signs/ranges. A history without an active row or violating cap/source
retention returns `INVALID_INITIAL`, separately from infeasibility.

Every physical row is active iff all its items are published. Every selected
source, including targets and helpers, is checked. Missing physical rows are
part of the declared exact model and cannot stand in for missing measurements.
Policies sharing a support remain separate rows in the same weighted task.
The primary contract has positive gain thresholds and mass; rho=0 is accepted
only as the explicitly disabled-retention diagnostic.

Fixed-y decisions include the same cap and gain predicate as unknown-y
decisions, plus exact equality to y. An unattained y returns NO. Both tasks
first validate H; the fixed-y API does not silently solve a different
retention-only problem.

## Direct CP-SAT equivalence

For each item p and row z, both directions of z iff AND(p on support) are
encoded. In each task, all distinct exact response values are ranked. An
active row's score is its rank and an inactive row's score is -1. The max
equality therefore gives precisely the attained frontier rank, including
negative responses and ties. Cap is an exact rank bound. A row is useful iff
it is active and the frontier rank is no larger than the largest response
rank below `row_response + tolerance`. Source-task usefulness is the OR of
all incident useful rows. The weighted source predicate is imposed conditional
on publication. Gain ranks compare exactly with `F(H) + gain`.

Only rational task weights and masses are integerized by an exact common
denominator. A conservative int64 overflow guard rejects excessive
coefficients instead of rounding. All response threshold comparisons remain
Fractions, so no common denominator over response values is necessary.

Given a feasible publication, its activation, frontier, usefulness and gain
variables satisfy the encoding. Conversely, activation equivalence and the
maximum fix those variables to the contract's meanings, so any solver witness
is a valid publication. Every returned witness is independently checked by
`co_exact.evaluate`. CP-SAT FEASIBLE or OPTIMAL is YES; INFEASIBLE is NO;
UNKNOWN remains UNKNOWN_TIMEOUT; MODEL_INVALID raises an error.

## Persistent SAT/PB equivalence

The second generic encoding uses the same activation equivalence but different
frontier machinery. A suffix chain represents `frontier >= response_rank_j`
as the OR of all active rows at that rank or higher. This chain includes an
attainment implication, not just one-way upper bounds. A row's useful bit is
its active bit AND the negation of the first forbidden frontier threshold.
Incident source ORs and exact PB weighted sums encode retention and gain.
The rank equivalence gives both soundness and completeness by the preceding
argument without Cartesian frontier enumeration.

One `Glucose4(incr=True)` object is kept for the entire contract. Each query
provides a fresh deduplicated list of positive target assumptions; absent
candidates remain optional. A smoke test asks an impossible isolated target
and then a feasible target on the same solver, confirms the answer changes,
the object identity persists, and cumulative solver statistics persist.
Learned-clause reuse is supplied by that persistent incremental backend;
CP-SAT model reuse is not described as learned-clause reuse. The installed
Glucose4 API has no portable random-seed option: its `seed` argument is
metadata only, and repeated SAT trials must not be called independent
randomized seeds.

Time-limited calls use `solve_limited(expect_interrupt=True)` and a timer.
The interrupt is cleared before/after each query. Timeout is UNKNOWN, never
UNSAT. A NO records solver status and target core where available.
`proof_checked=false` is explicit: these are solver-issued UNSAT results,
cross-checked on finite instances, not independently DRUP-checked proofs.

The documented API basis is [OR-Tools CP-SAT statuses and integer model](https://developers.google.com/optimization/cp/cp_solver),
[PySAT persistent assumptions, incrementality and interrupt handling](https://pysathq.github.io/docs/html/api/solvers.html),
and [PySAT PB encodings](https://pysathq.github.io/docs/html/api/pb.html).
Runtime versions are OR-Tools 9.14.6206, python-sat 1.8.dev24, and pypblib 0.0.4,
installed only in the external research environment. Online documentation
may describe a later version; the actual installed API was smoke-tested.

## Complete versus partial interfaces

The generic compiler repeatedly finds a feasible publication P, requires all
of P and at least one item outside P, and asks for a strict feasible superset.
It may add several mutually supporting helpers simultaneously. Once strict
superset UNSAT proves maximality, it stores K and blocks every subset of K
with `OR(p_i for i outside K)`. That block cannot remove any other maximal
set. UNSAT of the outer search proves completeness. This enumeration is
distinct from requiring all-solution enumeration for a single target query.

The cyclic-helper fixture has a feasible target publication, neither helper
can be added alone, but both together are feasible. Both generic compilers
correctly return the larger unique maximal set. A partial compiler retains
valid witnesses, potentially not proven maximal, and reports `complete=false`.
Those witnesses can answer YES for contained targets; absence answers UNKNOWN.
The reference compiler likewise retains each kernel immediately through a
verified callback, including timeout inside a frontier's unfinished branch
enumeration. End-to-end costs include build, verification, antichain
processing and query execution; the campaign runner supplies aggregate budgets.

## New correctness battery and artifacts

Frozen seed rule: `random.Random(926270000 + index)`, with the first three
models replaced by directed cyclic and latent good/bad examples. All 1,200
models were written before solver outputs. Input SHA-256:
`5753f8ba73b2f56f72e82f02bee2e9461eb29fbda328a733293835befdcf923a`.
There are 1,069 valid and 131 invalid initial histories, 1,159 tables with
negative responses, 171 with multiple policies, and 268 with zero-weight
tasks. Directed tests also cover float rejection, bad gain mass, partial
interfaces (including forced interruption immediately after saving a kernel),
assumption clearing and the failure of policy-expansion
monotonicity. All output sets were compared with exhaustive subset results.

The 700 metamorphic checks cover consistent renaming, relaxed thresholds,
required-target enlargement and optional-candidate enlargement with old rows
unchanged. Missing pairs, several old sources per slot, equalities, fractional
weights/masses, unsafe joint pairs, obsolete helpers and unattained prescribed
frontiers occur in the exact seeded battery and directed supplied reference
checks. No finite test battery replaces the equivalence proof.

Artifacts are under `campaign-v1/audit/exact-solvers/` and the repeated post-fix
gate `campaign-v1/audit/exact-solvers-v2/`: complete input JSONL,
result JSONL, progress receipt and `CORRECTNESS_REPORT.json`. A mismatch would
write a retained `COUNTEREXAMPLE.json` and abort. No mismatch was observed.
Recompute with `source scripts/env.sh` followed by
`python tests/test_co_exact.py --audit-out <new external audit directory> --count 1200`.

`co_reference.py` vendors the supplied readable Python method with one declared
contract extension (rho=0 diagnostic) and wrappers for exact validation,
timing/status handling and partial interfaces. It is labelled reference Python;
timing comparisons cannot attribute a Python/C++ implementation gap solely to
the mathematics. No frozen `oe_*` module or previous campaign run was changed.
