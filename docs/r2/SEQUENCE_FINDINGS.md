# Native 20-round sequence evaluation: power control did not retain novel rewards

**All ten methods completed the native 20-round evaluation, but none passed
the full sequence in either headroom panel: `S20=0`, `Pass20=0/16` per method
and panel.** Every trajectory failed the fixed novelty requirement in round
one; most also failed new-reward competitiveness. Continuing all 20 rounds
revealed a useful distinction: the response-informed scalar baseline controlled
point-estimate power throughout, while the frozen source rules admitted a
large later violation. Neither outcome solved the joint reward problem.

These are completed native simulator results, not an abstract substitute.
The held-out run executed **35,928 cells / 4,598,784 physical fights**, all
successfully: 1,497 unique loadouts, four tasks, three policies, Human and Orc,
128 iterations each. An independently sampled set of 185 initial loadouts
anchors the power boundaries. Eight source-defined arrival sequences per
race give 16 matched native trajectories per method. The ten methods and two
headroom panels produce 6,400 evaluated round decisions using shared combat
outputs; they do not imply ten times as many physical simulations.

## Outcomes at the 5% cumulative working point

Each row below represents 16 trajectories and 320 rounds. Means and behavior
profiles are estimated from combat samples; the table is an empirical finite
catalogue result.

| Method | Power-violating rounds | New-competitive rounds | Novel-competitive rounds | Legacy-failing rounds | Maximum power growth |
|---|---:|---:|---:|---:|---:|
| No new control | 32/320 | 124/320 | 2/320 | 36/320 | 20.467% |
| Compatible scalar repricing | 0/320 | 131/320 | 2/320 | 36/320 | 4.891% |
| Exact configuration exceptions | 0/320 | 131/320 | 2/320 | 36/320 | 4.891% |
| Measured safe-set envelope reference | 0/320 | 131/320 | 2/320 | 36/320 | 4.891% |
| Frozen semantic 2 rows | 32/320 | 131/320 | 2/320 | 7/320 | 18.391% |
| Frozen semantic 4 rows | 32/320 | 131/320 | 2/320 | 7/320 | 18.391% |
| Frozen semantic 8 rows | 32/320 | 125/320 | 2/320 | 7/320 | 18.391% |

Each same-dimension generic method reproduces its semantic counterpart in
**every reported round metric**. The generic class was given the same
features and semantic initialization; that initialization already attained
the frozen training objective's maximum of 185/185 initial admissions. No
expressivity, optimization or query advantage over that baseline is claimed.

The legacy denominator here contains previously competitive **released-item
sources**, registered separately by each method. It does not include every
initial item, and can differ between methods. Consequently the smaller
legacy-failure count for semantic rules is not a standalone fair comparison
of retention for an identical source set. Initial-item deletion results are
separately reported at round 20. Every method retained all its registered
historical loadouts and the initial task-quality floor throughout this run.

The 2- and 4-row templates admit 1,491 of the 1,497 loadouts in the final
union; the 8-row template admits 1,187. Its **304 additional rejections do
not improve the peak envelope** and reduce competitive new-reward rounds
from 131 to 125. Initially absent periodic-damage and armor-reduction rows
have frozen zero thresholds, so their rejection of newly introduced effects
is a conservative policy consequence, not proof that those effects are
dangerous. The unrepresented-component marker is a ninth feature and is not
a hidden ninth rejection rule.

The semantic power failures occur in `expanded_interleaved_0` after
Thunderfury (`19019`) arrives at round 5. They affect both contexts and
persist through round 20: 32 violated round decisions. The fixed-grammar,
expanded-late and other expanded-interleaved sequences did not produce a 5%
semantic power violation. The proposal families also change item-strength
distributions, so this is **not a causal estimate of the cost of adding an
independent semantic dimension**.

All 32 semantic and no-control violations have a positive lower bound on
power excess under the declared simultaneous mean-interval calculation.
However, **none of the point-estimate power passes is a statistically
certified pass**: the conservative intervals leave them unresolved. These
are approximate Bonferroni Student-t bounds over all physical cells within
one race, including the initial reference. They support adaptive maxima over
those cells but do not establish distribution-free or global-game safety.

## Zero headroom, reward value and actual complexity

At zero extra headroom, scalar repricing, exceptions and the envelope
reference keep the measured maximum at the initial boundary for all
320 rounds. They retain competitive use for 137/320 arriving-item decisions
but have **zero novel-competitive rounds** at the frozen behavior resolution.
All their registered released sources remain competitive. This result does
not establish useful horizontal expansion: the retained new choices are
behaviorally substitutable by the declared old catalogue at that resolution.

The two novelty-passing decisions under the unconstrained/semantic methods
are the same Thunderfury arrival in Human and Orc contexts; they coincide
with power violations. Under the 5% response-informed baselines, the two
novelty-passing decisions instead concern Blood Talon (`12795`) at round 20
of that sequence. Growth is 4.891% for Human and 4.219% for Orc. The Human
round passes every joint component in isolation, while the Orc round fails
legacy retention. The earlier sequence failures remain; neither isolated
round constitutes a successful 20-round extension.

**Exact equipment-cover `K=1` in all 6,400 evaluated rounds.** The four
offensive tasks and the permitted task-specific policy switches do not make
portfolio complexity a binding constraint. The initial equipment catalogue
still covers all four tasks near-optimally at round 20 in 14/16 uncontrolled
or semantic trajectories. It covers none of the four tasks within tolerance
in the two Thunderfury trajectories, yet a single current loadout covers all
four. This is replacement by stronger gear, not evidence of a difficult
multi-loadout tradeoff. Response-informed baselines preserve full initial
catalogue coverage in every trajectory.

The output field `distinct_new_choices` counts a **greedy packing of
task-conditioned mean behavior profiles**; the same gear can contribute on
different tasks. It is a lower bound on observed separated profiles, not a
count of globally distinct loadouts or a proof that randomized old strategies
cannot substitute. Source deletion fully reoptimizes the finite current
catalogue and all three policies. It separately reports optimal performance
loss and nearest-profile loss, including unfillable-catalogue outcomes.

## Implementation and reproducibility

Implementation supplement recorded before inspecting held-out sequence outputs:

* The frozen experiment is `runs/r2-discovery/unseen-v1` under the work root.
* Scalar repricing considers current-new witnesses competitive against the
  current point-safe envelope, then evaluates actual N against its own admitted
  set. This stronger full-information reference is available only to the
  declared response-informed methods. Prices start at zero. Numerical rejection
  margin is `1e-6`; price admission tolerance is `1e-8`. Semantic row comparisons
  use `1e-10` only for floating-point equality.
* The scalar program first checks whether its unconstrained-new-witness problem
  has a positive margin. If not, no added witness constraint could make it
  feasible. Otherwise new witnesses are tried in descending best normalized
  DPS, with gear ID breaking ties; a successful margin-maximizing solution is
  retained. Solver limits are reported as unresolved rather than infeasible.
* Behavior counts concern task-conditioned mean profiles. Greedy, fixed-order
  separation within an arrival removes duplicates; counts are lower bounds on
  the packing of observed novel profiles, not a count of unique player builds.
  All competitive profiles, not just counted representatives, enter the archive.
* Initial-item deletion counterfactuals are reported at round 20; released-item
  counterfactuals are reported in every applicable round. Deletion does not
  introduce a replacement item outside the frozen catalogue.

The frozen nine source features and 185 initial loadouts give the semantic
initialization all 185 training admissions. A generic nonnegative rule class
with the same number of rows can use these rows and already attains that
training objective's exact upper bound. Generic/semantic equality is an
expected baseline property, not an expressivity advantage.

All results will concern the declared finite catalogue, three listed policies,
four damage tasks, one Warrior class and Human/Orc contexts. Mean-profile
novelty does not exclude randomized strategy mixtures or unsearched loadouts.
Source-only rules do not use future combat responses. The full-response
methods may inspect only currently arrived loadouts. The same simulation
cache can serve multiple rules and overlapping deterministic sequences.

Run the maintained evaluator after sourcing the external-cache environment:

```bash
source scripts/env.sh
python -m wowfs.experiments.r2_sequence_analysis
```

It writes `ROUND_RESULTS.csv`, `SEQUENCE_RESULTS.csv`, `RULE_REUSE.csv`,
`REWARD_COUNTERFACTUALS.csv`, `FACTION_SUMMARY.csv`,
`SEQUENCE_ANALYSIS_PROTOCOL.json` and `SEQUENCE_ANALYSIS_SUMMARY.json` under
`WOWFS_WORK_ROOT/artifacts/r2-discovery/latest/`. The five CSVs contain 6,400,
320, 6,400, 40,163 and 40 rows, respectively. The protocol records exact
frozen-design, raw-result and evaluator hashes. Source-only rules never use
response labels for admission; response-informed comparators use current
arrivals only. Marginal evaluation costs are labelled as shared cache usage
and must not be summed as independent engine calls across methods.

The scalar programs resolved all 640 round decisions: 502 all-current-safe
solutions, 88 positive-margin solutions with a required new witness, and
50 positive-margin solutions without one. There were no solver timeouts or
infeasibility fallbacks in this native run. Exception tables reached at most
44 rows in the 5% panel and 56 in the zero-headroom panel. Both their growth
and scalar parameter changes remain in the rule records.

The study uses one native existing item per round, below the proposed 6–12
target, with no marginal-power matching. The eight sequences share source
catalogues and are not independent random game ecosystems. Only one class
and one race per faction were executed. This is a completed, informative
negative result for the frozen candidate rules and reward definition; it is
not an impossibility theorem for sustainable native equipment design.
