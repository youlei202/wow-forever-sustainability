# Native mechanism transfer: finite completion and capacity

This is a completed native transfer check for three different event or
resource mechanisms. It does **not** confirm the scalar completion-capacity
theorem for all three systems. The original prospective numeric-cap results
include failures, reversals, and empty predicted sequences. A separately
labelled population-reference sensitivity changes some mean classifications,
but neither analysis certifies a complete prospective path with simultaneous
approximate power, gain, and source-relevance bounds.

## Frozen native design

The maintained inputs are `configs/fc_mechanisms.json`,
`fc_mechanisms.py`, and `fc_mechanism_capacity.py` under
`src/wowfs/experiments/`. Source-level mechanism details and limitations are in
[CLASS_RACE_ONTOLOGY.md](CLASS_RACE_ONTOLOGY.md). Research variants retain
actual native base item IDs; they are not additional official game items.

| Family | Native primary mechanism and six values | Five calibration partners | Declared old primary | Contexts |
|---|---|---|---|---|
| Warrior | Vis'kag MH17075 speed: 1.3, 1.7, 2.1, 2.5, 2.9, 3.3 seconds; hold base weapon DPS | Brutality Blade OH18832 damage scale: .25, .5, .75, 1, 1.25 | 2.5 seconds | Human, Orc |
| Mage | Star of Mystaria neck12103 MP5: 0, 10, 25, 50, 100, 200 | Archivist Cape back13386 absolute SP: 0, 100, 200, 300, 400 | MP5 25 | Gnome, Undead |
| Rogue | Blood Talon MH12795 native proc PPM: 0, .25, .5, 1, 2, 4 | Dal'Rend's Tribal Guardian OH12939 damage scale: .25, .5, .75, 1, 1.25 | PPM 1 | Human, Orc |

All use the same eight tasks as the main study: sustained, high armor,
ten-second burst, cooldown window, cleave, endurance, elemental target, and
extended execute. The native policy is fixed per class. There are no incoming
attacks. Held-DPS weapon speed changes timing and rage; MP5 changes mana
availability and casts; Talon PPM changes the periodic proc process. Offhand
amplitudes remain positive. Rogue PPM zero is an explicit proc-off boundary.

The 1,440-cell development grid used 32 battles per cell. At every tested
primary/context/task, partner endpoint interpolation predicted all three
interior partner columns to at most 3.41e-13 DPS per seed, with unchanged
recursive control metrics. Primary event/resource metrics changed in all
48 context/task groups. This does not mean every primary change improved
utility or cast counts: the ten-second Gnome Mage task does not gain casts
from MP5, and Warrior/Rogue primary response is nonmonotone in this grid.
Partner slopes can depend on the primary. No globally additive or ordered
primary response was assumed.

After that calibration, both ecologies were frozen with five old partners,
the same declared old primary, and the **identical native maximum-partner
endpoint**. Partner width is the smaller of the calibrated domain width and
the width keeping the old response range within 4.4% of the old reference on
every task. Large-gap fractions are `[0, 1/440, 2/440, 3/440, 1]`; dense
fractions are `[0, .25, .5, .75, 1]`. All six primary choices, all five
partners, and all eight tasks were subsequently executed for both ecologies.

The original fixed numerical scale is the 32-battle calibration mean of the
old primary with the maximum old partner. The power cap is 1.05 times this
scale, meaningful gain is .01 times this scale on at least one of the eight
equally weighted tasks, and competitive relevance tolerance is .05 times
this scale. Every retained primary and each of the five partners must have
a competitive witness on task mass at least .05. Portfolio coverage is .95
with K at most 4. Admission masks, thresholds, candidate identities, and
predicted paths were frozen before confirmation and were not changed after
observing it. All crosses, including frozen-excluded crosses, were measured.

The exact finite oracle searches every release order among the five new
primary choices, retaining every admitted old cross. It checks power, gain,
all-source relevance, and exact finite portfolio cover at every state. Its
claim is finite-table optimality, not continuous-family or population
capacity. The generic finite baseline receives exactly the same table,
constraints, and masks and therefore has the same oracle; no algorithmic
advantage is claimed.

## Independent confirmation and primary results

Confirmation used 512 battles per unique input and seed 820000001. There
were 2,880 logical cells and 2,304 distinct successful native calls:
1,179,648 executed battles, zero failures, and zero previous-cache reuse.
The 576 duplicate endpoint cells are shared physical receipts, not additional
executions. The calibration seed 810200001 is disjoint from confirmation;
it was deliberately shared with the separate old-ecology development study.
Within each seed cohort, paired cells and contexts are coupled observations.

Each entry below is large-gap/dense. Capacity is empirical reoptimization of
the complete fresh mean table. The prospective prefix evaluates only the
path selected before confirmation.

| Context | Predicted finite capacity | Original native finite capacity | Frozen path successful prefix |
|---|---:|---:|---:|
| Human Warrior | 1 / 1 | 0 / 0 | 0 / 0 |
| Orc Warrior | 2 / 3 | 0 / 0 | 0 / 0 |
| Gnome Mage | 1 / 1 | 1 / 1 | 1 / 1 |
| Undead Mage | 1 / 1 | 1 / 0 | 1 / 0 |
| Human Rogue | 0 / 0 | 1 / 1 | 0 / 0; predicted paths empty |
| Orc Rogue | 0 / 0 | 1 / 1 | 0 / 0; predicted paths empty |

All 12 old baselines pass the empirical power, relevance, history, and
portfolio checks; all have K=1. The matched old frontiers are bit-identical
between ecologies. Warrior zero capacity is **not** caused by unsafe initial
libraries. Human Warrior's first planned release, speed2.9, gains 2.183% on
its best task but exceeds the original cap by 1.125 percentage points of
the calibrated scale in the burst task. Other new candidates also fail power
or gain. Orc Warrior's first planned speed1.3 release has zero gain; its
speed3.3 candidate has positive gain but exceeds the numeric cap by .3079
percentage points. Its old burst reference itself remains safe, with .7681
percentage points of headroom.

Undead Mage's dense MP5 50 release exceeds the original endurance cap by
.1257 percentage points; its gap counterpart passes at the mean. Gnome Mage
passes in both ecologies at the mean. Rogue's finite positive results were
not predicted release paths and must not be presented as prospective
successes. The original utility-only and value-plus-legacy finite capacities
are equal in all 12 designs, so these results do not demonstrate an extra
capacity obstruction caused specifically by retaining old source uses.

There is one original empirical gap/dense separation, Undead Mage 1 versus
0. It is a near-cap effect, not a confirmed general ordering of the three
mechanism families. The Orc development prediction even had the opposite
granularity direction, 2 versus 3, and neither predicted path survived.

## Separate sensitivity to the cap estimand

`fc_mechanism_sensitivity.py` adds an explicitly post-confirmation analysis.
It preserves the physical outcomes, original masks, source identities,
candidates, old reference endpoint, and planned sequences. It compares the
original fixed numerical calibration cap with the population functional
`cap(q) = 1.05 E[U(old primary, maximum old partner, q)]`. In the latter,
gain and relevance thresholds are .01 and .05 times that same expected old
utility. Fresh old samples estimate this predetermined physical reference;
the reference is not a future frontier. Selecting this second estimand for
the mechanism study happened after confirmation and is a sensitivity
analysis, not the original preregistered result.

| Context | Original numeric-cap capacity | Population-reference sensitivity capacity | Sensitivity frozen path prefix |
|---|---:|---:|---:|
| Human Warrior | 0 / 0 | 2 / 2 | 1 / 1 |
| Orc Warrior | 0 / 0 | 1 / 1 | 0 / 0 |
| Gnome Mage | 1 / 1 | 1 / 0 | 1 / 0 |
| Undead Mage | 1 / 0 | 1 / 0 | 1 / 0 |
| Human Rogue | 1 / 1 | 1 / 1 | 0 / 0; paths empty |
| Orc Rogue | 1 / 1 | 1 / 1 | 0 / 0; paths empty |

The shift is materially bidirectional. Fresh Warrior burst old means are
3.943% and 4.232% above the calibration means, leaving less original numeric
headroom. Fresh Mage old means are lower; the population-reference cap is
therefore tighter and removes Gnome Mage's dense mean pass. These finite
sample differences explain why two legitimate fixed-cap definitions give
different outcomes. They do not justify replacing the original estimand.

Both estimands now have simultaneous approximate paired t bounds for the
linear margins `U_a - U_b - .01 S`, `U_a - U_b + .05 S`, and
`1.05 S - U_a`. Here S is either the original constant or the paired sample
of the same old endpoint. Bounds retain the full covariance with S; they
are propagated through the complete max/min definitions of optimized gain
and source relevance. The family includes both estimands, all 12 designs,
all eight tasks, and all pairwise configuration comparisons: 351,360
comparisons, critical t=5.3370204384 with 511 degrees of freedom. This is an
approximate finite-family inference, not a distribution-free certificate.
Dividing a margin bound by the estimated S is only a display normalization,
not a confidence interval for a ratio with random denominator.

Every planned stage passes the paired source-relevance lower-mass check.
Mage's planned gains pass their paired lower-mass check, but power remains
unresolved or fails. Warrior first steps fail gain inference; Human power
also remains unresolved under the population-reference sensitivity.
Consequently **no complete nonempty prospective prefix passes all paired
power, gain, novelty, and legacy lower-bound checks in either estimand**.
Orc's later speed3.3 stage can pass these sensitivity checks conditionally,
but the preceding planned release failed; it is a counterfactual later
stage, not a successful prospective path.

Behavioral novelty D was not evaluated in this transfer study. The seven
metric joint-success claim is therefore unavailable. Finer direct-primary
and fixed-budget escapes are `not_evaluated`: the event-changing parameters
have signed, nonmonotone task-vector responses and no validated scalar
increment lambda. An unrelated signed budget would not establish the
theorem's intervention. The separately frozen main scalar study owns its
two escape tests.

## Receipts and reproducibility

All generated outputs are under
`WORK_ROOT/artifacts/final-completion-capacity/`:

- `MECHANISM_CALIBRATION.json`: original development table and control checks.
- `MECHANISM_CAPACITY_DESIGN.json`: prospective masks, predictions and inputs.
- `MECHANISM_CAPACITY_CONFIRMATION.json`, `MECHANISM_CAPACITY_RESULTS.csv`,
  and `MECHANISM_DIVERSITY.csv`: preserved original numeric-cap results.
- `MECHANISM_CAPACITY_SENSITIVITY_V2.json` and `.csv`: separate paired analysis
  and estimand sensitivity, with zero new native calls.

Confirmation run:
`WORK_ROOT/runs/final-completion-capacity/mechanism-capacity-confirmation-v1`.
Its protocol SHA256 is
`18e5a95758f6f4dca542cb629c41f98714e071534d99d59de7db7303034f512e`;
frozen design SHA256 is
`7324e6aa12a4e2155e813b3722baa09258bbcfcce988bf1e0979e1fbdbc5fe36`;
native results SHA256 is
`972e0456dd4682b5ee796b95cd9e527eb3ba848b80db98124f8e86340d96504f`.
The 12 source snapshots and eight imported input hashes were checked against
the protocol. The paired covariance calculation was independently checked
against direct per-sample margins on 32 synthetic comparisons. No native
run, original result, admission rule, or predicted path was altered for V2.
