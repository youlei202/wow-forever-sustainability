# Native held-out arrival design

`configs/r2_unseen.yaml` fixes a source-only catalogue and eight explicit
20-round item sequences before their combat responses are opened. Its current
SHA-256 is
`2a5b03d641c321699b9fec20339ee6cdf23c8799faf54941ee34654e64a487c1`.
The public source is the same native community engine commit used in discovery,
`17d75ccc8c67d027ae0088243ea3ee806d406847`. Numeric rule thresholds, the decision
algorithm, and the intervention parameter must be frozen in the execution
manifest before any held-out combat. A frozen catalogue alone is not a frozen
method or a completed unseen experiment.

## What is new and what is held fixed

The descriptor catalogue contains the 38 distinct item IDs used in development
and 40 additional native item IDs. Their sets are disjoint. Eight sequences
sample 35 distinct additional IDs in total. Every trajectory receives exactly
one previously unavailable item each round, with ten MH arrivals and ten OH
arrivals over twenty rounds. No item is copied or renamed, and no two arrivals
within a sequence have the same ID. One item per round is below the requested
6–12-item target and is reported as such.

All new items were checked against the native database: they are weapons with
valid hand restrictions, no faction restriction, and no incompatible Warrior
class restriction. Human and Orc therefore receive the same item definitions,
tasks, policy choices, and arrival order. Race is fixed throughout a trajectory.
These are matched Warrior contexts, not evidence for another class. Native
database release labels do not establish the items' historical availability;
the sequences are counterfactual arrivals of existing native items.

The experiment preserves the four development tasks, three policies, talent
string, and controlled external environment from `r2_discovery.yaml`. Four
equipment slots vary in the new finite domain: MH, OH, trinket 1, and trinket 2.
The other slots use the same explicit phase-1 equipment mapping, with Titanic
Leggings 22385 fixed. The initial slot alternatives are:

| Slot | Existing alternatives |
|---|---|
| MH | Ironfoe 11684; Empyrean Demolisher 17112 |
| OH | Flurry Axe 871; Felstriker 12590 |
| Trinket 1 | Hand of Justice 11815; Gri'lek's Charm of Might 19951 |
| Trinket 2 | Blackhand's Breadth 13965; Diamond Flask 20130 |

All 173 distinct development configurations remain in the reference catalogue.
Adding the sixteen initial combinations yields **185 distinct initial physical
configurations** because four combinations already occur in development. Each
arrival expands the corresponding weapon-slot alternatives, and every legal
cross-slot combination is included. At round 20 the new Cartesian domain has
`12 * 12 * 2 * 2 = 576` configurations; its union with the preserved development
catalogue has **745** configurations per sequence. The union over all eight
final catalogues has **1497** distinct physical configurations.

The complete two-race, four-task, three-policy matrix consequently contains
35,928 physical cells per mechanism, before failures or new-seed confirmation.
An identical cached native input may serve multiple sequence prefixes. These
are counts of proposed/evaluable cells, not completed run receipts. A method
must receive only responses authorized at its current prefix even if a shared
evaluation cache already holds a future cell.

## Source-defined sequence families

| Family | Two sequences each | Rule for the twenty arrivals |
|---|---|---|
| Fixed grammar, random | Independent declared source RNG seeds | Ten MH and ten OH items sampled without replacement from the 24-item fixed grammar library, then shuffled. |
| Fixed grammar, proc first | Independent declared source RNG seeds | The same source-only sampling, then descending nominal PPM, with shuffled tie order. |
| Expanded grammar, interleaved | Independent declared source RNG seeds | Eight fixed and two expanded items per hand; one expanded item after each group of four fixed items. |
| Expanded grammar, late | Independent declared source RNG seeds | Eight fixed and two expanded items per hand; the four expanded items arrive last. |

The YAML stores actual item IDs, slots, and rounds, so execution need not
reimplement random sampling. Sorting by PPM uses public code constants and is
not a sort by measured danger or measured reward value. All source RNG seeds
are recorded. Families share portions of the same item library; the eight
sequences are not eight independent draws from the entire game. Paired
sequence summaries must preserve that dependence, and combat repetitions must
not become independent equipment-ecology observations.

The fixed grammar library varies actual weapon speed, base damage, physical
versus magical proc damage, proc probability, extra MH requests, and temporary
self buffs. It includes Thrash Blade, Deathbringer, Perdition's Blade, Alcor's
Sunrazor, Ebon Hand, Lord General's Sword, Argent Avenger, and source-defined
weaker alternatives. These are not single-item performance matched. In
particular, weak items may fail reward usefulness against the strong initial
archive, and that failure must remain in the denominator.

The expanded library contains periodic damage, damage-linked healing, target
armor reduction, target primary-stat changes, resistance changes, and attack
slows. Examples include Annihilator, Bashguuder, Rivenspike, Barman Shanker,
Skullforge Reaver, Gutgore Ripper, and Thunderfury. These are new equipment
effect relationships relative to the development item grammar; some underlying
event classes already exist in Warrior abilities. This is not a claim that the
entire engine acquires a previously absent event class. New native semantics
also change weapon strength and other parameters, so comparing these families
does not identify a clean causal effect of semantic dimension alone.

Two source details matter for mechanism interpretation. Annihilator and the
Puncture Armor effects share the exclusive `MinorArmorReduction` resource, so
adding maximum reductions is a deliberately loose descriptor. Thunderfury's
native primary hit deals 300 Nature damage; its bounce spell deals zero damage
and applies a resistance debuff to up to five targets. A five-target description
must not be misread as 1500 damage per proc. Dragon's Call was excluded from
this first held-out catalogue because its guardian source explicitly contains
guessed combat parameters and would require separate pet-output validation.

## Frozen features and rule-row accounting

Each old and new item has an eight-coordinate source descriptor plus raw effect
parameters and source location. Static-only items have zero effect coordinates;
static stats are supplied separately from the native item database. Heroism's
four-piece resource callback is added only when its set threshold is active.
It is not charged once per set piece. A missing or unparsed effect is unresolved,
not a zero vector.

The rule feature order is the following nine-dimensional basis:

1. A fixed static strike proxy: MH weapon DPS + half OH weapon DPS + item AP/14
   + twice item Strength/14. It is an explicit heuristic and omits accuracy,
   crit, target armor, and dynamic state.
2. Expected extra MH requests per eligible landed event. For a PPM weapon this
   is native PPM times base weapon speed / 60 times the requested batch size.
   HoJ uses its fixed 0.01 probability; its ICD remains a separate raw field.
3. Peak native attack-speed increase.
4. Maximum direct damage per proc before mitigation or crit, accounting for
   the native damage-target cap and including both physical and magic schools.
5. Count of temporary physical-stat, hit/crit, or flat-damage buff families.
   A count avoids inventing a conversion between AP, Strength, and flat damage;
   exact magnitudes and durations remain available to all methods.
6. Maximum flat rage returned or saved per activation. Active generation,
   set generation, and cost reduction retain distinct raw modes.
7. Full nominal periodic damage if one application completes all its ticks.
8. Maximum raw target armor reduction.
9. Marker for additional semantic components not summarized by these numeric
   coordinates, with the component names preserved.

The structured q=2, q=4, and q=8 rules use the first q coordinate unit rows.
**The static proxy counts toward q.** Every active threshold is the maximum
score of that row over the exact common t=0 reference catalogue. Those numeric
values are frozen before held-out combat; no threshold is raised for a later
item. All methods receive the same full feature basis and source/log permissions.
The same-q generic method receives the structured rows as an initial feasible
solution and may choose arbitrary nonnegative row weights under the declared
optimization budget. Exact ties are expected and do not imply that the generic
class is weaker.

The unsupported-component marker is feature nine, so it is **not an additional
rejection condition at q=2/4/8**. Configurations with such components must be
evaluated when the active rows admit them. A separate experimental rejection
of all unknown components would consume another explicit rule row and would
be a different method. If an active feature has an initial maximum of zero,
rejecting its first positive arrival is a declared conservative policy;
it does not establish that the rejected item was dangerous in combat.

None of these aggregate coordinates is asserted to be a certified damage
bound. Their sum can overcount exclusive auras, miss state-dependent trigger
eligibility, and fail to capture physical-spell proc descendants. In particular,
the native physical damage proc helper produces `MeleeSpecial` events with
`SuppressEquipProcs`, while weapon proc registration tests a different
`SuppressWeaponProcs` flag. This permits further weapon-proc opportunities.
The shared extra-MH-request gate does not by itself suppress those direct
special-damage descendants. Native held-out performance can therefore expose
a concrete failure of an incomplete interaction description.

## Decision and reporting boundaries

Freeze novelty resolution, task weights, the success-prefix definition,
reward/source deletion tests, query budget, and the actual update policy before
the first held-out response. A rule that admits a configuration is not a
prediction that all joint goals pass. Evaluate P/N/D/L/H/C and retain which
component fails. The new-item usefulness denominator is one proposed native
item each round, not the count of hand-picked witnesses.

The mechanism panel deploys its fixed gate at t=0 and records both the common
native reference and the intervention's old-witness performance. A changed
mechanism requires new simulation; admission-only rules may reuse the same
physical fights. Source parameters are public in this setting, so this panel
does not claim to learn unknown effect constants. Any limited-data estimation
result needs a separate unknown quantity and an equal-information generic
measurement baseline.

This file defines a practical native unseen test, including ways it can fail.
It does not report any completed twentieth-round trajectory, certify a power
envelope beyond the finite catalogues, or establish matched-strength causality
for the two semantic-growth families.
