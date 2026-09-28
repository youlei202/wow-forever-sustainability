# C/E: competitive witnesses and subset admission

Status: exact finite-table analysis and conditional characterization. Native
cross-ecology conclusions require the R4 physics tables. None of the claims
below is presented as an originality determination or a population-mean
guarantee.

## Extracted operating point

The actual R3 protocol is the `science` object in
`runs/r3-gold/sequences-v1/PROTOCOL.json`, with implementation in
`src/wowfs/experiments/r3_sequences.py`. It uses:

* Competitive tolerance: 0.05 times the independently frozen initial task
  optimum, in raw DPS units for each task.
* Behavior: seven physical coordinates, task-conditioned L-infinity distance
  at least 0.05 from **all legal old-only policies** and the historical archive.
* New and legacy useful task mass: at least 0.05; original four tasks have
  weights 0.25 each. Eight equal-weight R4 tasks still require at least one
  task; the weights and new initial anchors must be explicitly frozen.
* H: every previously legal loadout stays legal, with unchanged physics in
  permission track A.
* L: initially useful sources and subsequently registered useful releases
  remain useful. Reactivation of previously inactive sources is separate.
* C: an equipment portfolio of at most four loadouts covers at least 0.95 task
  mass, allowing the same native strategy choices for old and new gear.
* Primary R3 power cap: 1.05 times its independent 185-loadout initial task
  anchors. A new R4 ecology needs its own explicitly recorded initial state;
  retaining the four old task conditions does not make different equipment
  pools share the same numerical initial anchor.

The brief references `INDEPENDENT_CHECKS.json`, but it was not found in the
maintained source or work artifact tree. Its claims must be reconstructed from
the archived records rather than quoted as a read file.

## A conditional witness-frontier characterization

Let H be the fixed set of protected old loadouts. Let B be the selectable new
loadouts, each containing at least one item in the current release. Every
allowed policy and task is in a complete frozen finite table. Write
`v[g,t]=max_policy value[g,policy,t]`, cap `c[t]`, competitive tolerance `e[t]`,
and choose A⊆B. The admitted frontier is
`F[t]=max_{g in H union A} v[g,t]`.

A competitive witness is a gear/policy/task triple with value at least
`F[t]-e[t]`. A joint certificate consists of enough witnesses to:

1. give every protected source the required task mass;
2. give every newly released item the required task mass;
3. give the new release the required task mass of behaviorally distinct
   competitive witnesses (or every item separately if that stronger option is
   explicitly enabled);
4. cover the required task mass with at most K equipment choices.

Multiple sources may be present in the same witness. Witnesses may share tasks
and configurations. There is no one-source-per-task or matching hypothesis.
Behavior eligibility is computed before choosing A against the fixed H-only
policy domain and the fixed archive. Power means every policy/task response of
every admitted gear is below c; it is not merely a condition on its favorable
witness policy.

**Conditional characterization.** A joint-feasible subset exists if and only
if there is a finite witness certificate W whose induced frontier box

`U[t] = min(c[t], min_{w in W on task t}(value[w]+e[t]))`

admits H and all witness gears, with the inner minimum omitted when no witness
uses task t. Given such W, opening every new gear satisfying
`v[g,t] <= U[t]` on every task preserves the certificate.

**Proof.** Starting from a feasible subset, choose witnesses from its N, D, L
and portfolio requirements. Each admitted value is at most F. Competitiveness
gives `F[t] <= value[w]+e[t]` for each task witness, and power gives F≤c.
Consequently H and every witness gear lie in the box. Opening the entire new
box may raise F, but the new frontier is still at most U. Each chosen witness
therefore remains competitive. Its source membership and fixed-reference
behavior eligibility are unchanged. The same portfolio still covers the same
tasks. Conversely the stated box and witnesses directly satisfy all six
conditions. H is retained throughout, and its original performance is unchanged
because this is an admission-only statement. ∎

This characterizes a maximal opening *conditional on selected witnesses*.
The all-power-safe closure corresponds to U=c and can lose useful old sources
or competitive novelty by raising the frontier. Therefore it is not a joint
objective oracle. A feasible arbitrary subset can be completed to a box in the
full task-response space without losing its certificate.

This uses at most T response thresholds, but does **not** establish a reusable
source-feature rule. The response table itself may require a combat probe for
every new gear; rule coefficients can change with the chosen certificate; the
physics may have many contexts and policies. A generic method with the same
response features can express the same box. No additive/generic advantage is
claimed. If newly optional old-only loadouts were added, D's reference set could
grow and the proof would fail: that permission is deliberately excluded.

## A checkable necessary exclusion quantity

In the present equal-weight regime a single task meets minimum useful mass.
For protected source s, let `b[s,t]` be its largest response on task t among
all individually safe gear. If the protected old frontier exceeds
`b[s,t]+e[t]`, task t can never support s without breaking H. Otherwise every
optional gear with `v[g,t] > b[s,t]+e[t]` must be excluded to use task t as s's
retention witness. Choose the task requiring the fewest such exclusions.

This gives the **exact minimum number of exclusions for that source alone**:
the upper bound is attained by opening all safe gear under that one task
ceiling, including the gear realizing b. The maximum of the per-source minima
is a lower bound on joint necessary exclusions. It is not generally exact for
several sources: their required blocker sets may overlap or conflict, and N,
D and K can impose additional constraints. This is a source/configuration/task
incidence calculation, not one-to-one niche allocation.

The diagnostic can distinguish missing combinations from frontier competition:
an absent source witness gives no possible task, whereas existing source
witnesses may require excluding a small set of otherwise safe strong gear.
Whether these quantities predict an unseen ecology from cheaper source-level
observations remains an empirical and learning question.

## Executable analysis

`src/wowfs/experiments/r4_feasibility.py` provides `FiniteProblem`,
`eval_all_safe`, `evaluate_admission`, `solve_subset`, and `frontier_closure`.
The solver has binary admission, source-task witness, novel witness and
portfolio variables plus continuous task-frontier upper bounds. Frontier
equality is unnecessary: lowering any feasible frontier variable to the actual
admitted maximum can only improve competitiveness. Constraints check whole-gear
power, per-new-item usefulness, all registered sources, fixed-reference D,
protected H and exact finite portfolio coverage.

The primary objective maximizes admitted configurations, minimizing the number
of excluded individually safe new configurations. Optional objectives find a
small constructive subset or any feasible subset. Solver limits are reported
as limits, not impossibility; every incumbent is checked again by a separate
direct metric implementation. Dual bounds retain the solver's minimization
direction. This is an arbitrary-subset full-information reference. It must not
be relabeled as an optimized scalar-price or fixed-feature rule.

The same MILP optionally adds one, two or four nonnegative item-incidence
budgets, each with bound 1 and coefficients in [0,100]. Gear admission is then
the **entire induced intersection** of those budgets: every excluded gear must
violate at least one row by the frozen numerical margin 1e-6. N, D, L, H, power
and portfolio witnesses are optimized jointly with prices. There is no free
blacklist after pricing. Scalar and generic baselines therefore receive the
same current native response table and joint constraints as the subset solver;
they differ in rule representation. Returned rule parameters are checked by
reconstructing the complete opening. Numerical invalid incumbents and timeouts
remain unresolved. Infeasibility for these models is restricted to the declared
coefficient domain and positive rejection margin.

`r4_coexistence.py` records all source uses, overlapping source/configuration/task
supports, and deletion followed by policy reoptimization with admission held
fixed. It also compares the all-safe and exact-subset openings and computes the
individual source exclusion lower bounds.

Eight tests pass, including exhaustive enumeration of all subsets in twelve
random small domains. A deliberately non-native four-gear test exhibits
all-safe L failure repaired by excluding one safe new competitor. Another test
retains three protected sources in one gear on one task with K=1, preventing an
accidental exclusive-matching interpretation. These are software/logic tests,
not native mechanism findings.

## Selection gates for native C/E research

The first native comparisons use eight predeclared ecologies and the same
complete physical tables under both openings. Record a separation only when
the same H and source denominator are protected and the exact subset has an
independently verified joint certificate. Full-safe success is a valid negative
result for the claim that exclusion is needed; solver timeout is unresolved.

For C, compare complete old/new mixing with an explicitly labeled restricted
template domain. Retain all protected legacy-source columns, including sources
that have no legal configuration in the restricted domain; missing opportunity
must be visible rather than removed from L's denominator. For E, report both
minimal necessary exclusion and representability by scalar or matched generic
rules before claiming a practical admission intervention.

Promote this line only if the complete-domain evidence yields a meaningful
same-physics joint-feasibility separation, a causal intervention in source
connections or competitor frontiers, and a prospective prediction beyond this
identity. The characterization itself is currently a useful exact formulation,
not a certified foundational novelty claim.
