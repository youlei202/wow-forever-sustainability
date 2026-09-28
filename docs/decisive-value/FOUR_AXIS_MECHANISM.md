# Four native reward amplitudes across two equipment slots

The completed development calibration supports an affine response model for
four simultaneous weapon-amplitude interventions in 24 frozen task/policy
contexts. It does **not** establish positive decision gain for a future
release, successful continuous expansion, or a population-wide affine theorem.
This note records the mechanism and existing evidence before those claims.

## Physical design domain

The character is a Human Warrior with the frozen R4 body equipment and
talents. Main hand is native Blood Talon 12795; off hand is native Thunderfury
19019. The four coordinates are:

| Coordinate | Actual native intervention | Fixed properties |
|---|---|---|
| `d_M` | Blood Talon base weapon DPS, implemented by scaling its native 35–67 damage interval | Native 1.3-second speed, weapon type, stats |
| `t_M` | Blood Talon periodic damage per tick | 1 PPM, ten ticks, three-second tick spacing, refresh/application rules |
| `s_O` | Thunderfury base weapon-damage scale | Native 60–145 interval scaled together; 1.9-second speed, sword type, stats |
| `p_O` | Thunderfury primary Nature proc base damage | 6 PPM, hit/crit rules, slow and bounce behavior |

The proposed design box recorded with calibration is
`d_M ∈ [10,80]`, `t_M ∈ [0,150]`, `s_O ∈ [0.1,1.5]`,
`p_O ∈ [0,500]`. This is a declared search domain, not a claim that every
point in the box has been independently tested.

The initial library contains two research aliases per slot:

| Slot | Old alias parameters |
|---|---|
| Main hand | `(d_M,t_M)=(39,10)` and `(33,30)` |
| Off hand | `(s_O,p_O)=(0.75,300)` and `(1,150)` |

All four old main-hand/off-hand crosses are included. Each alias is a
declared parameter recipe attached to its real native base ID, not an invented
official game item. Source labels distinguish the experimental recipes and
are fixed before future release testing. Only one alias occupies each slot;
equipment remains fixed throughout combat. Native IDs and set memberships
are unchanged, and both libraries receive identical equipment and controller
permissions.

The remaining body IDs are head 12640, neck 18404, shoulder 12927, back 18541,
chest 11726, wrist 19146, hands 14551, waist 19137, legs 22385, feet 14616,
rings 17063/18821, trinkets 11815/13965, and ranged 17069. These fixed pieces
are part of the response context; the model is not a claim about arbitrary
partners or class builds.

## Why amplitudes can preserve native controls

The engine inspected is
`$WOWFS_WORK_ROOT/external/mythicsim-forever-engine-r3-variants`.
Its `sim/core/wowfs_r3_variants.go` supports both original IDs in the same
request, with one variant specification per ID. It changes reward magnitudes
without changing speed, stats, PPM, or effect timing in this experiment.

Blood Talon's callback in `sim/common/item_effects.go:684` applies its DoT on
a landed proc hit and reads the tick amount on each tick. Zero tick damage
does not remove application or ticking. Thunderfury's callback at line 2226
changes the damage of action 21992/tag 1 only. Its tag-2 spell still makes
zero-damage bounces over at most five targets, with flat threat and aura
application. **The fourth axis is not an AoE damage amplitude.** The primary
hit/crit checks, attack-speed slow activation, and bounces still execute when
the primary amount is zero. The existing Thunderfury aura-label collision
that prevents the intended Nature-resistance reduction is preserved; no
repair or resistance knob is part of this study.

Forever white-hit rage depends on weapon speed and landed outcomes rather
than outgoing damage (`sim/core/rage.go:52`). Unbridled Wrath, Flurry, and
Hand of Justice likewise use hit/outcome conditions. Deep Wounds reads the
selected hand's weapon damage, but its hand selection comes from the triggering
crit, not damage magnitude. Consequently its reward can change while the
event sequence remains fixed. Sweeping Strikes has a positive-damage branch,
but the frozen talent string does not enable that talent.

The incoming-attack task requires an additional check: Thunderfury's slow
changes enemy swing timing and therefore incoming rage. Its activation rule
is unchanged across this amplitude family. The calibration explicitly checked
enemy action controls, target auras, and per-seed enemy damage samples, so
this feedback was not silently omitted. These tasks use fixed duration,
fixed tank assignment, and policies without damage/threat-dependent choices.
Changed threat does not select a different tank in this native setup.

These are conditional mechanism explanations. Other talents, item effects,
health-based termination, changed timing, new policies, or unvalidated swaps
can invalidate the model. Native incoming/death limitations remain those in
[the control audit](NATIVE_CONTROL_AND_LUDUS.md); this is not a survival claim.

## Calibration result and its denominator

Run: `$WOWFS_WORK_ROOT/runs/decisive-value/four-axis-calibration-v1`.
The run completed 264 new native calls, 67,584 battles, zero failed calls,
and zero reused cells. Every cell contains 256 coupled native seed iterations,
starting at seed 720000001. Matching seeds across design points are not
independent experimental units.

Five fit anchors were
`(24,0,0.5,0)`, `(54,0,0.5,0)`, `(24,60,0.5,0)`,
`(24,0,1,0)`, and `(24,0,0.5,300)`.
Two four-coordinate validation points were `(43,25,0.85,220)` and
`(67,105,1.25,430)`. The four old crosses were also validation points, not
fit observations. Each of these eleven points was evaluated on all eight
tasks and all three policies.

| Check | Observed result |
|---|---:|
| Context-specific models | 24 |
| Fit cells | 120 |
| Non-fit validation cells | 144 |
| Held-out per-seed DPS predictions | 36,864 |
| Maximum held-out per-seed DPS residual | `6.821210263296962e-13` DPS |
| Maximum held-out behavior-numerator mean residual | `1.9895196601282805e-13` |
| Aggregate player action/resource/aura controls | Identical within each context |
| Incoming controls and damage samples | Identical within each context |
| Filtered first-seed event schedules | Identical within each context |

The seven behavior numerators are five action-channel DPS means—autoattacks,
Execute, Whirlwind/Cleave, Bloodthirst, and other damage—plus rage gain/second
and rage waste/second. They are not seven independent damage channels.
Normalized damage shares and the waste/gain ratio are computed from these
numerators; they are not asserted to be globally affine.

The trace comparison retains selected cast, aura, resource, and hit events,
with damage/threat amounts normalized away. It is a first-logged-seed schedule
check, not an archive of identical full traces for all 256 seeds. Aggregate
controls cover all iterations, while the DPS prediction check is per seed.
The result is a strong numerical consistency diagnostic at the tested points;
it is not a confidence interval for unknown population means or a proof over
the whole continuous box.

Receipts:

* Native binary SHA-256:
  `59f42b32e2c834321773188db482419238ae57556942f6f1825258722fc0aafe`.
* `FOUR_AXIS_CALIBRATION.json` SHA-256:
  `c85e34b797e01430b64cf2959ec4262df9315d63839449935f0909816d009cb5`.
* Frozen `RESULTS.json` SHA-256:
  `42bc193996149d456ebd9cb161ca37f7bd02dc03cba33b4eb7c009f8a59d0ea8`.

## Real tasks, not chosen damage-log weights

Utility is actual native full-fight DPS. The task family changes physical
inputs: durations 10/30/60/90/180/360 seconds, one/two/four targets, ordinary
or high armor, and a declared incoming-attack context. Each task retains the
20% Execute phase. The three allowed policies are `native_no_reck`,
`native_reck`, and `rage_conserve`; the last raises specified rage thresholds.
The same complete old gear and policy set is reoptimized for each comparison.

These changes can alter how much value arrives before the deadline, how
weapon-driven attacks interact with armor and target count, and how the rage
schedule supports actions. The response coefficients are measured consequences
of those native contexts, not freely selected weights that make a particular
damage channel desirable. A weighted distribution over actual encounters is
also distinct from relabeling damage logs, and from shared-resource stages
inside one encounter.

The armor contrast has an exact native path. Talon action 13318 is Physical
and calls `CalcAndDealPeriodicDamage` (`sim/common/item_effects.go:686–706`).
That passes `isPeriodic=true` (`sim/core/spell_result.go:357–368`), and
`sim/core/spell_resistances.go:23–31` returns an armor multiplier of one for
physical periodic damage. Its line-25 comment is: “All physical dots (Bleeds)
ignore armor.” Physical periodic effects also receive the target's
`BleedDamageTakenMultiplier` (`spell_result.go:674–675`). `SpellFlagPureDot`
means no initial damage component; it is not itself the armor-bypass rule.
Thunderfury's primary proc is Nature/Magic (`item_effects.go:2234–2246`) and
uses magic resistance instead of armor. Direct physical weapon attacks use
the nonperiodic armor path (`sim/core/attack.go:493–494`). Weapon-amplitude
coefficients nevertheless include some armor-bypassing damage through Deep
Wounds, so they should not be described as purely armor-reduced channels.
The physical explanation is a changed relative value of these contributions
under high armor; the net effect must come from measured task coefficients.

The earlier cached `LINE_A_SUMMARY.json` supplies exploratory motivation,
not validation of this new family. For example, Human `static_skill` releasing
17068 under the all-cap-safe diagnostic has zero sustained-task gain but
qualifies on two of eight actual tasks. Across 392 correlated release/method
rows, 14 satisfy D without G and 142 satisfy G without D. These are unchanged
16-seed R4 table reanalyses with zero new calls. They show that behavioral
distance and decision gain are different tests; they do not establish a new
four-axis release.

## Joint admission can matter without superadditive physics

For fixed task `q`, policy `pi`, and the calibrated control process, the model
has the form

`U(q,pi;d_M,t_M,s_O,p_O) = b(q,pi) + a_M d_M + c_M t_M + a_O s_O + c_O p_O`.

Thus the mixed finite difference between changing main hand and off hand is
zero in this model. Reoptimizing over policies or admitting only cap-safe
combinations introduces maxima and constraints; nonadditivity of the resulting
library value does not imply a new nonlinear combat interaction.

A stronger component may be inadmissible beside a strong old partner while
remaining useful beside a weaker one. A joint release can supply that partner
or preserve an old source's competitive use. Conversely two individually safe
improvements can exceed the shared cap when combined. These are compensation
and shared-cap effects. Testing them requires the complete legal old/old,
old/new, and new/new cross-product, not a chosen matching diagram.

The cached combination study illustrates why this distinction matters.
`LINE_B_COMBINATIONS.json` and [NATIVE_COMBINATIONS.md](NATIVE_COMBINATIONS.md)
contain ten development-selected release/race cases: natural composition
passes no strict joint test, while a fitted one-row generic item budget and
the arbitrary-subset reference both pass six. The singleton-increment rule
passes none. Human Gri'lek/22000 has a 4.740% cap-safe gain on the 10-second
task while its cap-safe singleton gains are zero; deleting either source
removes that gain. This demonstrates a finite-table joint-admission effect.
It does not identify a superadditive damage mechanism. Confirmation of the new
four-axis family is a separate experiment, summarized below.

## Fair comparison and remaining claim

A generic affine model with the same four primitive coordinates, intercept,
five anchors, and validation information makes the same predictions. No
estimator or optimizer advantage follows from naming the coordinates by
mechanism. A structured admission rule must be compared with a generic rule
of the same feature dimension and rule complexity on identical responses.
For example, enforcing every task/policy cap through this model uses up to
24 affine inequalities; that must not be reported as one inequality merely
because there are only four design coordinates.

The calibration establishes a concrete two-slot design language. Model searches
are development results; their selected catalog requires a separately frozen
complete-combination native evaluation.

## Subsequent frozen native confirmation

`PROSPECTIVE_CONFIRMATION.json` reports 600 native cells with 1,024 battles each
for all 25 final gear pairs, eight tasks, and three policies. The catalog,
sequence, caps, and admission masks were fixed before these tests, whose seeds
are disjoint from calibration. All three rounds pass the seven empirical
criteria on that finite table. The largest per-round normalized decision gains
are 1.01382% on high armor, 1.34969% on the 10-second task, and 2.18109% on high
armor, respectively. Each gain compares complete admitted old and expanded
libraries with all three policies reoptimized; its denominator is the fixed
initial development scale.

The first round's 1% threshold remains statistically unresolved: its approximate
simultaneous paired-t lower bound is 0.44955%, and its simultaneous bootstrap
lower bound is 0.70309%. Corresponding paired-t lower bounds for the strongest
second- and third-round gains are 1.27384% and 1.50041%. All approximate
simultaneous cell-t power-cap checks pass. These are finite-domain measurements
with approximate inference, not a population joint certificate or an unbounded
release-capacity result.

Deleting either first-round source removes that round's gain. In later rounds,
deleting OH3 or MH4, respectively, has zero gain loss despite those sources
meeting the stated competitive-use criterion. The minimum finite-table
portfolio size remains one in every round. The evidence therefore supports a
first-round shared-cap compensation effect and three measured release rounds;
it does not establish six independent utility directions, rising management
burden, or superadditive combat physics.
