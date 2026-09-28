# Findings from the completed abstract development run

The completed finite construction exhibits a strict obstruction for one additive
budget and a feasible solution using several budgets. Its hyperedge rules and
generic budgets with the same dimension admit exactly the same configurations.
It therefore supplies a constructive finite example and a scalar obstruction;
it does not establish a structural mechanism advantage over equally expressive
generic budgets.

This document independently audits frozen run `development-eea1a7084874`.
All 18 instance checkpoints completed: three interaction families, three final
equipment pools per family, and two revelation orders per pool. There are nine
pool units, not 18 independent pools. Each trajectory has six updates, eight
tasks, three policies, and at most 729 configurations. Every response is a
constructed deterministic abstract value. Native-engine executions and
stochastic combat samples both number zero. These are development findings,
not the requested 20-round main study or evidence about WoW classes or races.

## Achieved joint success

`S6` counts the consecutive jointly passing rounds before the first failure;
continuing diagnostics do not reset it. Means below give both orders equal
weight inside each pool and all nine pools equal weight. No population
confidence interval is claimed for these nine deliberately constructed pools.

| Method | Mean S6 | Pass all six | Pair: mean S6 | Triple: mean S6 | Mixed: mean S6 |
|---|---:|---:|---:|---:|---:|
| Initial-rule-only extension | 2.111 | 0/18 | 2.167 | 1.833 | 2.333 |
| Frozen scalar prices | 2.111 | 0/18 | 2.167 | 1.833 | 2.333 |
| Compatible scalar, registered history | 4.222 | 6/18 | 3.667 | 6.000 | 3.000 |
| Compatible scalar, all historical configurations | 4.222 | 6/18 | 3.667 | 6.000 | 3.000 |
| Generic two-budget search | 4.667 | 1/18 | 4.833 | 4.167 | 5.000 |
| Generic budgets, matched dimension and structural initialization | 6.000 | 18/18 | 6.000 | 6.000 | 6.000 |
| Forbidden hyperedge constraints | 6.000 | 18/18 | 6.000 | 6.000 | 6.000 |
| Arbitrary safe-set envelope diagnostic | 6.000 | 18/18 | 6.000 | 6.000 | 6.000 |

The last row evaluates the entire safe set. It is not an optimization over all
jointly feasible sequential policies, and its score is not `T*`. The matched
generic method receives the same visible interaction annotations as the
hyperedge method and uses their additive encoding as a feasible initialization.
It is not a generic search algorithm discovering those annotations unaided.

## What proves the scalar gap

All 12 first failures of the registered-history scalar method occur in the
pair and mixed families. Every one has failure reasons `N,D` and an exact
two-trade certificate. The six triple-family trajectories all pass six rounds;
the result therefore does not support a universal scalar failure claim.

For every safe configuration `p` using the item whose admission would be
required, the certificate identifies a protected historical configuration `h`
and two unsafe configurations `q,r` such that their item-incidence vectors obey

`a(p) + a(h) = a(q) + a(r)`.

An additive rule admitting `p,h` cannot exclude both `q,r`: summing their two
admission inequalities contradicts the sum of the two strict exclusion
inequalities. The audited certificates cover **every** safe current-new
configuration, so declining novelty is unavoidable for a safe scalar rule
respecting the specified history. This is a conditional `P + H + current-new
admission` obstruction, not an impossibility for `P + H` alone. Rejecting the
new item always provides the safe historical fallback used by the runner.

The independent audit verified 24 certificates across the two scalar methods,
containing 1,104 candidate witnesses in total, with 24–72 candidates per
certificate. It checked every incidence equality, the unsafe classification of
both crossed configurations, actual membership of `h` in that method's
protected history, and exhaustive coverage of safe new candidates. The two
scalar methods share pools and many witnesses; these 24 certificates are not
24 independent experiments. Unlike numerical MILP infeasibility, this
combinatorial check does not depend on the solver's exclusion tolerance.

The all-history scalar ablation has the same first-failure round as the
registered-history scalar in all 18 trajectories. It preserves every previously
admitted configuration, including every initially admitted configuration.
Weakening the history obligation did not improve achieved success prefixes in
this development construction.

## Equal-dimensional budgets recover all of the structural result

For a forbidden conjunction containing `r` items in distinct slots, assign each
of those items cost `1/(r-1)` in one budget and every other item cost zero.
The budget threshold one excludes precisely configurations containing all
`r` items. Applying one such budget per conjunction exactly reproduces the
hyperedge mechanism.

The audit compared admitted configuration IDs, not only aggregate metrics.
Matched generic budgets, hyperedge constraints, and the arbitrary safe-set
envelope are identical in **all 108 instance-rounds**. The number of constraint
rows grows from one initially visible row to at most five; initial constraints
are included in the count. This is a finite six-update complexity result, not a
constant bound over arbitrary expansion horizons.

Across the 108 hyperedge rounds:

| Quantity | Observed range |
|---|---:|
| Largest task power divided by its initial anchor | 1.028457–1.035279 |
| Fixed cap divided by the initial anchor | 1.050000 |
| Current-new task coverage `N` | 1.000 |
| Novel near-optimal task coverage `D` | 1.000 |
| Useful new-item fraction | 1.000 |
| Legacy retention fraction and worst-source task coverage | 1.000 |
| Registered and all-historical admission retention | 1.000 |
| Exact minimum portfolio size `K` | 1 |
| Minimum task performance divided by its initial anchor | 1.000 |

`D` uses the same current rule for the old-item counterfactual and also compares
against all configurations admitted in any preceding round. Its behavior
vector is normalized performance across the eight fixed tasks, after exact
maximization over the three declared policies. Source usefulness is
competitive use; it is not a claim of irreplaceability or player retention.
The archive, task scales, cap, and thresholds remain fixed as prescribed.

The portfolio requirement is easy in this construction: `K=1` throughout these
three methods. This run does not establish a benefit under difficult portfolio
management constraints. Its joint feasibility is an existence demonstration
with substantial near-optimality tolerance, not a general capacity estimate.

## Search limitations and negative findings

The two-budget search reaches a time limit on 29 of 108 solves and uses a safe
reject-new fallback on 22 rounds. **All 17 first failing trajectories fail on a
time-limited solve**: 15 first fail `N,D`; two first fail legacy retention using
a partial incumbent. Therefore the observed two-budget deficit is not evidence
that no feasible two-budget rule exists. This run confounds achieved search
performance with the fixed one-second search allowance. It provides no proved
two-budget capacity gap.

The registered scalar solver reports 75 optimal count-surrogate solves, 21
time limits, and 12 exact trade certificates; the all-history scalar reports
81 optimal solves, 15 time limits, and 12 certificates. Later time limits do
not explain the scalar first failures, which all have the combinatorial
certificates above. An optimal solver status concerns its declared coverage
and admission-count surrogate, not optimization of the complete joint
sequential objective. Later legacy failures retain rejected releases in the
source denominator rather than silently deleting them.

Initial-rule-only extension and frozen prices have the same achieved success
prefix in every trajectory. Seventeen first failures violate power alone and
one violates both power and legacy use. Their equal prefix scores do not
establish equality of all admitted configuration sets or all later metrics.

The initial anchor is defined using the declared initial scalar admission
rule. The unrestricted Cartesian product of old choices already contains an
unsafe combination. The extension comparator retains the initial rule and
assigns zero cost to newly revealed choices; it does not obtain its first
power failure by deregulating the initial system. This initialization is a
substantive assumption of the constructed example.

## Same-pool revelation-order effects

Both scalar methods change `S6` between the two orders in five of nine pools.
The largest absolute difference is four rounds in a mixed-family pool. The
three paired mixed-family scalar scores are `(5,3)`, `(3,1)`, and `(5,1)`;
the first-failure mechanism remains the certified new-item obstruction.
The two orders have identical final response-table hashes in every pool.
Thus ordering changes achieved lifespan without changing the final equipment
pool in these examples.

Initial-rule-only and frozen-price scores change in six of nine pools, by at
most two rounds. Two-budget search changes in four of nine pools, by at most
three rounds; its order comparison also includes possible effects of
time-limited optimization. Matched budgets, hyperedge rules, and the safe-set
diagnostic pass both orders in all nine pools. Passing both orders through the
sixth round demonstrates performance through the finite study endpoint only.

## Audit trail and supported claim

The independent audit regenerated every response table using the frozen source
snapshot and verified its hash against the checkpoint. Machine-readable
counts, first failures, order pairs, and certificate totals are in
`runs/development-eea1a7084874/INDEPENDENT_ABSTRACT_AUDIT.json` under the configured
work root; original instance records are in that run's `checkpoints/` directory.
No scientific source was changed during this audit.

A supported paper claim is: **in a declared finite equipment construction,
historical compatibility and mandatory useful new admission can produce an
exact scalar-budget obstruction, while a finite family of interaction
constraints—and equivalently the same number of generic additive
budgets—satisfies the declared joint requirements through six updates.**

The result does not establish novelty of the additive separation argument,
strict superiority over equal-dimensional budgets, a statistical learning
advantage, 20-round sustainability, native Forever performance, class/faction
robustness, or infinite expansion capacity. Those require separate evidence.
