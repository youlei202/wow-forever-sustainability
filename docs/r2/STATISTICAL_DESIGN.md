# R2 native discovery and confirmation: analysis contract

This specification distinguishes the current mechanism-discovery study from
the proposed 20-round extension study. It does not declare unexecuted rounds,
reward counterfactuals, methods or contexts successful. The run's immutable
protocol and manifests, rather than this explanatory document, determine
which cases were frozen before their confirmation outputs were inspected.

## 1. Executable measurements verified in the recovered engine

Inspected source: the pinned checkout under
`WOWFS_WORK_ROOT/external/mythicsim-forever-engine-r2`, especially
`proto/api.proto`, `sim/core/sim.go`, `sim/core/rand.go`, and
`sim/core/metrics_aggregator.go`. This is evidence about that simulator
implementation, not validation of official server mechanics.

| Output | Meaning and permitted use |
|---|---|
| `raidMetrics.dps.allValues` and player `dps.allValues` | With `saveAllValues=true`, each iteration appends total damage divided by that iteration's simulation duration. Values remain in iteration order, not sorted order. These support paired DPS contrasts. Specify player or raid scope consistently. |
| `dps.avg`, `stdev`, histogram | Aggregate DPS summaries. A histogram is not a pairing key. Recompute sample standard deviation with `ddof=1` from the per-iteration contrast; do not infer its variance from the four separate marginal standard deviations. |
| Action-target damage, casts, hits, crits and related fields | Totals over all completed iterations. Divide by `iterationsDone` for per-fight means, and additionally by fixed duration for rates. They do not supply seed-level covariance or paired confidence intervals. `ActionID` includes spell/item/other ID plus tag; merging tags can erase hand/variant distinctions. |
| Resource `events`, `gain`, `actualGain` | Totals over completed iterations, grouped by action and resource type. Positive `gain-actualGain` records overcap loss for gain entries. Spending is negative; report gain, spend, refund and waste separately. These totals do not prove a global resource contract. |
| Aura `uptimeSecondsAvg`, `uptimeSecondsStdev`, `procsAvg` | Already averaged; do not divide again by iteration count. Aura activation counts need not equal damage-event or child-trigger counts. |
| Debug `logs` | Timestamped event evidence. `debugFirstIteration=true` with `debug=false` preserves only the first iteration's trace. Whole-fight action totals do not identify a maximum sliding-window burst. |
| DTPS, TMI, healing, time-to-OOM, death probability | Schema availability does not establish meaningful measurement in a particular encounter. The discovery template's `tankIndex=-1` does not target the player. High-armor DPS is an offensive-pressure task, not a survival task. |

Batching is valid for seed pairing: iteration zero uses the requested nonzero
integer seed `s`, then iteration `i` is reseeded with `s+i`. `SplitMix64`
records the starting seed. With `useLabeledRands=true`, labelled call sites
have separate seeded streams. This can preserve useful common random numbers
when effects change call counts; it does not guarantee event-by-event identity
or positive covariance. No variance reduction is assumed without observation.

Use `saveAllValues=true` and `useLabeledRands=true` throughout the present
discovery and confirmation panels. A batch of 128 iterations can replace
128 separate DPS calls. Before analysis require a successful engine exit, no
engine error, `iterationsDone=128`, 128 finite values in every factorial cell,
identical seed starts and task definitions, and the same metric scope. Never
truncate unequal arrays or pair sorted values. Retain the input and output
hashes. A rerun is a replacement computation, not additional independent data.

The current four tasks may use fixed-duration DPS, including a short encounter,
multiple targets and high target armor. A separate short encounter changes the
rotation horizon and cooldown decisions: call it short-encounter performance,
not the best short window inside the long fight. Sliding-window claims require
per-iteration timestamped damage accounting with boundary and overkill rules.

## 2. Discovery at 32; fixed-case confirmation at 128

**Discovery.** Use 32 iterations per declared configuration/task/policy/cell.
Aggregate means, action/resource totals and a first-seed trace can select
mechanisms, find controls, and identify a finite set of informative contrasts.
Save the complete search denominator, failures, selection rule and selected
case IDs. These results are exploratory, including apparently large effects.
They do not estimate the prevalence of amplification among all native items.

**Freeze.** Before examining confirmation outputs, freeze each selected case's
items, static attributes, target settings, task, policy, effect switches,
effect-family interpretation, endpoint, sign convention and seed interval.
Also freeze the number of primary contrasts. The present conservative
confirmation family is **six scalar contrasts**. Extra task/policy/pairwise
views are descriptive unless they were included in that family before data.
There must be one recorded target per family member; six cases times four
tasks is 24 tests, not six tests.

**Confirm.** Use 128 new iterations per factorial cell. Discovery and
confirmation seed intervals must be disjoint, including the full intervals
`[s,s+n-1]`, not merely different starting integers. Use the same interval
within all cells of one contrast. Common seeds across cases permit paired
comparisons; the six-case multiplicity correction does not require cases to
be independent. Contexts remain contexts, not independent equipment pools.

For two effects, retain the same equipped items and static attributes in all
four cells; switch only the named registered effects. For seed index `i`,

\[
d_i=Y_{11,i}-Y_{10,i}-Y_{01,i}+Y_{00,i},\qquad
\widehat\Delta_{AB}=\frac1n\sum_i d_i.
\]

The three-effect contrast uses all eight cells with coefficients
`(-1)^(3-|S|)`. It cannot be recovered by switching only the full combination
and individual effects. The exact switch semantics, including retained set
membership or other thresholds, are part of the causal estimand. A factorial
of three effects with 128 iterations requires 1,024 physical fights even
when only eight engine processes are launched.

Compute `s_d^2=sum((d_i-mean(d))^2)/(n-1)`, `SE=s_d/sqrt(n)`, and the
two-sided family-adjusted interval

\[
\bar d\;\pm\;t_{n-1,\,1-0.05/(2\times6)}\,SE.
\]

This uses the exact Student-t quantile, not `1.96`. Exact coverage requires
independent normally distributed seed-level contrasts; with general simulator
outcomes it is an approximate large-sample interval. Bonferroni supplies
simultaneous 95% coverage for the declared six contrasts if the underlying
individual coverage assumption holds. Do not label it a distribution-free
certificate. Display the effect in raw DPS and relative to a specified
reference; treating an estimated reference as fixed does not supply a valid
ratio confidence interval. A positive interval establishes mean synergy for
that frozen case, not a mechanism-independent hard power bound.

Do not repeatedly inspect ordinary fixed-sample intervals at 128, 256 and
512 and stop when significance appears. A later mechanistic follow-up may
use another frozen, fresh-seed confirmation; adaptive repeated testing needs
an explicitly allocated error budget or an appropriate sequential method.
Constant contrasts have zero observed sample variance, which is not proof
that the simulator's population variance is zero. Preserve that degeneracy
instead of automatically calling the result significant.

## 3. Fixed-configuration causes and reoptimized consequences

Report both whenever available, with different names:

1. **Fixed configuration and policy:** the factorial contrast above identifies
   how the specified effects combine in that exact state of the experiment.
2. **Reoptimized consequence:** for each mechanism/cell, search the same
   permitted gear and policy domain with the same discovery budget. Freeze
   each selected winner, then evaluate those winners on fresh common seeds.
   Contrasts between these winners measure selected-policy performance, not
   necessarily the global optimized interaction.

Taking the maximum of noisy confirmation means reintroduces selection bias.
Do not choose winners from the same confirmation samples used for ordinary
confidence intervals. With exhaustive finite-domain mean evaluation, report
the scope and simultaneous uncertainty; with search, each achieved objective
is a lower bound on the true maximum. Failure to find a bypass is not a proof
that none exists. Timeouts and unresolved optimizer states remain visible.

## 4. Definitions required before a 20-round study

The extension study must freeze tasks `x`, task weights `w_x` summing to one,
allowed strategy class, initial rule/mechanism, positive initial scales `s_x`,
initial capacity references, behavior features/resolution, source labels and
history registration. They cannot be inferred from favorable discovery DPS
alone. Existing R1 thresholds are retained: 5% near-optimality, 5% minimum
task mass, 5% initial quality floor, at most four loadouts, and 95% task
coverage. The 5% power allowance is **cumulative relative to initialization**.
Run zero-extra-headroom separately; 2%/10% are declared sensitivity panels.

Let `F_t` be the current allowed loadouts, let `V_t(x)` maximize expected task
utility over those loadouts and the fixed strategy class, and let `z` include
the strategy actually used for a behavior witness. Let `F_t^-` delete all
current-batch rewards while preserving the same current rule and mechanism.
Per-source deletion similarly removes that source and fully reoptimizes.

| Joint component | Round-level definition and reporting requirement |
|---|---|
| **P** | Every designated power endpoint on every fixed task stays within its initial boundary plus the chosen cumulative allowance. Do not average DPS and defense to cancel a violation. Initial-reference error is propagated. A searched maximum is a lower bound, so being below the cap is only an empirical searched-domain result; a found exceedance is evidence of failure. |
| **N** | The task mass on which some current-new witness is within `0.05*s_x` of `V_t(x)` is at least 0.05. Also report this mass for **each proposed item**, and the useful-item numerator over the full proposed batch. A single successful item does not imply every proposal is useful. |
| **D** | The same competitive new witnesses must have at least the frozen behavior distance from every allowed old-only alternative under the current mechanism and from the historical behavior archive. Their covered task mass must be at least 0.05. Distance cannot use item IDs, irrelevant noise, or a resolution that shrinks over rounds. |
| **L** | Every registered legacy source retains at least 0.05 task mass with a witness within `0.05*s_x` of the current optimum. Report all-source fractions and the worst-source mass. Presence in a competitive loadout alone does not show a substantive contribution. |
| **H** | Every previously registered configuration stays legal. Track its original and current raw performance against the common baseline. A frozen mechanism does not authorize retroactive weakening or silently replacing old witnesses. Report all-history retention separately if registration uses only representative witnesses. |
| **C** | A portfolio of at most four loadouts covers at least 95% task weight within `0.05*s_x` of current optima. If task-specific strategy changes are allowed, specify whether they count toward complexity. An achieved portfolio proves `K<=4`; failed search does not prove `K>4`. Report carried items, rule rows, exceptions, descriptors, total metadata and rule changes separately. |
| **Floor** | On each fixed task, the best allowed utility remains at least its initial reference minus `0.05*s_x`. Banning most of the game must not manufacture power-control success. |

Meaningful behavior candidates available from this engine include declared
time-window damage shares, target damage allocation, resource spending versus
recovery/waste, and cooldown occupancy. Select physically interpretable
coordinates and scales from development, then freeze them. For means, use
normalized infinity distance with a fixed threshold. If the claim concerns
within-fight reliability or split timing, a distributional feature is needed:
old randomized strategies may reproduce an apparent mean-profile novelty.

For every claimed new/legacy source, report two deletion losses separately:
task-optimum loss after source deletion and distance from the removed
competitive behavior to the nearest source-free behavior. These can disagree.
Computing distance only to the best-DPS old loadout is invalid: behavior
substitution requires searching **all** competitive relevant old alternatives.
Search supplies an **upper bound** on the true minimum behavioral distance;
a positive searched distance alone does not certify novelty. Exhaustive small
domains or valid lower bounds are needed for a global exclusion statement.

Source deletion can leave a mandatory slot unfillable. Record that outcome
as structural infeasibility with the source's slot role; do not turn it into
an infinite performance benefit. Introducing a neutral replacement changes
the comparison and must be defined in advance.

## 5. Sequence inference and honest completion accounting

For a fully executed sequence, a round passes only when P/N/D/L/H/C/Floor all
pass under the declared empirical or certified interpretation. `S20` is the
number of consecutive passing rounds before the first failure; `Pass20` is
one only if all 20 rounds pass. Missing, crashed or unresolved rounds are not
zero performance and cannot be counted as passing. An incomplete trajectory
has an observed passing prefix with a censoring flag, not an invented exact
`S20` or `Pass20=0` performance claim. Keep planned, completed, failed and
unresolved denominators alongside any success fraction.

Compare methods on matched proposal sequences and contexts. Aggregate by
equipment pool or complete sequence, not by the thousands of seed-level
fights. Within a class, weight races equally, then weight completed classes
equally for a faction summary; preserve matched pairs. A shared equipment
pool scanned over races is not multiple independent ecological discoveries.
Report the actual completed subset and all missing strata.

At zero extra headroom, an empirical boundary estimate may remain statistically
unresolved. This is not a reason to prevent all zero-headroom exploration or
to claim exact equality from a non-significant test. Separate empirical
trajectories, confidence-qualified conclusions and structural bounds. No
theoretical `T*`, native class coverage or 20-round success follows merely
from the existence of a configuration file or this analysis contract.
