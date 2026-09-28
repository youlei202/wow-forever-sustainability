# Source-defined native mechanisms for R2 discovery

These are executable hypotheses read from community engine commit
`17d75ccc8c67d027ae0088243ea3ee806d406847`, not combat findings or live-server
validation. The upstream checkout is at
`$WOWFS_WORK_ROOT/external/mythicsim-forever-engine-r2`; every source location
below is relative to that checkout. Measured results belong in the generated
R2 artifacts. Existing items are introduced counterfactually; an upstream item
`phase` field alone is not a verified release-history label.

The bounded grid is maintained in `configs/r2_discovery.yaml`. It contains 12
source-defined domains, each with four binary variable slots. Validation against
the native item database found 192 domain incidences and 173 distinct equipment
configurations, with no incompatible slot, hand type, class restriction, or
duplicate unique item. Domains overlap and are not 12 independent random draws
from the game. Human and Orc scans of the same domain are matched contexts,
not new equipment ecologies.

## Relevant engine semantics

| Mechanism | Native source | Consequence for the experiment |
|---|---|---|
| Forever white-hit rage | `sim/core/rage.go:77` and `sim/core/ruleset.go:87` | Landed white swings earn a flat amount determined by base weapon speed, not damage or critical-hit damage. One-hand MH earns `3.46 * base_speed`; OH has a `0.5` factor before talent modifiers. |
| Haste-to-rage assumption | `sim/core/ruleset.go:98` | The engine explicitly uses base speed, so haste raises rage per time. The source flags this choice as needing an in-game measurement; the result can be native-engine evidence without validating that assumption against the live game. |
| Resource saturation | `sim/core/rage.go:196` | `AddRage` records attempted and actual gain separately and clamps at the rage maximum. It also invokes the APL, so resource events can change action timing immediately. |
| PPM implementation | `sim/core/attack.go:962` | Per-event proc chance is base hand speed times PPM / 60. More eligible special attacks, targets, or hasted swings can raise realized procs per minute. Nominal PPM is not a universal rate cap. |
| Proc-mask and exclusion filters | `sim/core/aura_helpers.go:63`, `sim/common/itemhelpers/weaponprocs.go:102` | The source identifies which events enter a proc; do not infer eligibility merely from a damage label. Weapon-proc helpers exclude `SpellFlagSuppressWeaponProcs`; equipment effects can use a different exclusion. |
| Extra MH attack dispatch | `sim/core/attack.go:304`, `sim/core/attack.go:767` | Extra-attack requests advance the MH swing timer and accumulate pending attacks. The next batch casts actual attack spells; subsequent procs may create later batches. There is no inspected global prohibition on every recursive extra attack. |
| Queued attacks | `sim/warrior/heroic_strike_cleave.go:24`, `sim/core/rage.go:84` | Heroic Strike and Cleave have a hybrid auto/special mask. The base rage handler requires exact equality to the pure auto mask, so replacing a white swing can forgo its base rage. Other procs use mask intersection and may still trigger. |
| Multi-target Whirlwind | `sim/warrior/whirlwind.go:7` | At most four target results per hand. The fixed Raging Blows talent adds OH results, yielding up to eight eligible hit results per cast. This is a native target-count interaction. |

The selected upstream talent string is
`30305013-050520035150310051`. Its pertinent talents are Unbridled Wrath 5/5,
Boundless Rage 3/3, Dual Wield Specialization 5/5, Raging Blows, Flurry 5/5,
Death Wish, and Bloodthirst. **Weaponmaster is absent**, so this study cannot
attribute any extra attacks to its sword specialization. Boundless Rage raises
the cap from 100 to 130 (`sim/warrior/talents.go:24`). Dual Wield Specialization
doubles OH rage and supplies 10 percentage points of OH hit
(`sim/warrior/talents.go:204`). Unbridled Wrath has a 60% chance to grant one rage
for a landed event matching its white-hit mask (`sim/warrior/talents.go:176`);
that mask test differs from the exact base-rage mask test.

Flurry grants a 25% melee-speed multiplier with three charges when any melee
event crits. Charge removal is limited by a 500 ms internal cooldown, and its
exclusive-effect family does not stack with a second Flurry aura
(`sim/warrior/talents.go:269`). Consequently, increasing critical chance can
mainly refresh an already active buff instead of producing an unbounded new
multiplier. Felstriker also raises hit chance, so an observed interaction cannot
automatically be assigned entirely to critical damage or Flurry.

## Three intervention families

| Existing item / set | Exact native effect | Source and relevant output ID |
|---|---|---|
| Empyrean Demolisher, 17112 | 1 PPM on eligible equipped-hand hits; 20% attack speed for 10 s | `sim/common/item_effects.go:871`; aura spell 21165 |
| Eskhandar's Right Claw, 18203 | 1 PPM; 10% attack speed for 6 s | `sim/common/item_effects.go:922`; aura spell 22640 |
| Hand of Justice, 11815 | 1% on landed melee events, excluding equipment-suppressed events; one extra MH request; 2 s internal cooldown | `sim/common/item_effects.go:2615`; extra spell 15600; retains static 20 AP when disabled |
| Ironfoe, 11684 | 0.8 PPM on eligible MH events; two extra MH requests | `sim/common/item_effects.go:1453`; extra spell 15494 |
| Flurry Axe, 871 | 1.9 PPM on eligible equipped-hand events; one extra MH request | `sim/common/item_effects.go:1099`; extra spell 18797 |
| Felstriker, 12590 | 1 PPM on eligible equipped-hand hits; +100 percentage points melee hit and crit for 3 s; excludes weapon-suppressed events | `sim/common/item_effects.go:962`; aura spell 16551 |
| Battlegear of Heroism, four pieces | 1 PPM on landed melee hits; heal for 88–132 and gain 10 rage; no specified ICD or suppression exclusion | `sim/warrior/item_sets_pve.go:174`; trigger 450587, resource/heal 450589 |
| Gri'lek's Charm of Might, 19951 | Active 30 rage; 3 min cooldown; no shared offensive cooldown in this implementation | `sim/warrior/items.go:64`; item action 19951 |
| Rage of Mugamba, 19577 | Reduce Hamstring rage cost by two | `sim/warrior/items.go:93`; alters spell 7373 |
| Diamond Flask, 20130 | Active 75 Strength for 60 s; 6 min personal cooldown; shared offensive cooldown for 60 s | `sim/warrior/items.go:20`; aura/cast spell 24427 |
| Cloudkeeper Legplates, 14554 | Active 100 AP for 30 s; 15 min personal cooldown; shared offensive cooldown for 30 s | `sim/common/item_effects.go:2854`, `sim/core/item_effects.go:132`; item action 14554 |

**Family 1: eligible-event frequency and extra attacks.** The first fixed
configuration combines Empyrean in MH, Felstriker in OH, and Hand of Justice.
The primary factorial toggles Empyrean and Hand of Justice; Felstriker is the
third-order diagnostic. Haste can add eligible events and flat rage, while HoJ's
ICD can reduce the marginal value of clustered triggers. The signs of the
second- and third-order performance contrasts are unknown before combat.
For Ironfoe, a 2.4 s base speed gives a 0.032 trigger probability per eligible
MH event before hit outcomes; its two requests imply 0.064 direct requested
offspring in that conditional description. This is not a complete reproduction
coefficient for the full APL, nor an engine-wide safety certificate.

**Family 2: event-resource feedback and saturation.** The fixed configuration
uses Heroism head 21999, shoulder 22001, wrist 21996, and chest 21997, with
Ironfoe, Flurry Axe, HoJ, and Gri'lek's Charm. The primary factorial toggles
Ironfoe and the Heroism four-piece callback, with HoJ as an optional third
effect. A plausible path is melee events → set rage → paid special attacks →
additional eligible events. The native rage cap, action costs, GCD, action
priorities, queued-white replacement, and ability cooldowns may limit or reverse
the marginal performance gain. A heal in an encounter with no incoming damage
is not evidence of a useful defensive reward. Four-target combat directly tests
whether a per-hit semantic description transfers when a cast generates more
hit results.

**Family 3: native shared cooldown and burst scheduling.** Diamond Flask and
Cloudkeeper Legplates use the *same* offensive timer, although they occupy
different slots. An active effect locks that resource for its duration.
Their stat buffs therefore cannot overlap through the native on-use helper.
The fixed factorial toggles only these two effect callbacks, preserving all
equipped static stats. This supplies a possible bounded or antagonistic case
and a test of a reusable resource rule that is already implemented in this
native engine. We must not label the common-timer mechanism as our invention.
The upstream APL explicitly schedules Flask during the final 60 seconds and
controls other cooldowns by time remaining, so short versus long encounters can
produce a real schedule tradeoff.

## Tasks, policies, and controls

The controlled common environment has no consumables, enchants, raid/party/
individual buffs, or externally supplied target debuffs. Battle Shout and the
APL's own Sunder Armor remain native actions. All tasks use a level-63 target,
fixed duration, and 20% execute phase: 180 s / one target / 3731 armor;
30 s / one target / 3731 armor; 90 s / four targets / 3731 armor;
180 s / one target / 10000 armor. High armor is a damage/resistance task,
not a resource-pressure or defensive-survival task. Since Forever white rage
is not proportional to damage, armor need not lower base rage per landed swing.

Three policies have identical talents and action availability: upstream
`dps_no_reck`, upstream `dps_reck`, and a conservative derivative of
`dps_no_reck` that raises queued Heroic Strike/Cleave rage thresholds from
40 to 70 and Hamstring's filler threshold from 80 to 95. These are finite
available-policy alternatives, not a globally optimal player. The configuration
records changes by action ID, so a blanket numeric substitution cannot alter
unrelated timing constants.

Native equipment IDs are resolved by the runner, and the final request must be
saved. The upstream `launch.gear.json` has a ranged item, Blackcrow 12651, at
array position 14 and a melee item at position 16; positional use without
native slot resolution would be unsafe. R2 therefore uses the explicit,
validated phase-1 slot mapping in the maintained configuration. Neither this
choice nor the source inspection itself is an executed combat result.

## Causal ablation and event checks

The native runner envelope supports `disable_item_effects: [item_id, ...]`
and `disable_set_bonuses: [{name: "Battlegear of Heroism", pieces: 4}]`.
It substitutes a no-op only for the chosen registration callback. Equipment
IDs, base weapon damage/speed, raw stats, and unrelated set tiers remain in the
request; the two-piece resistance bonus and any six-piece stat bonus remain
active. The change is a research intervention in native simulation and must be
identified by runner/patch hashes.

For every representative case, save all four pair masks, and all eight masks
for a triple when run. Compute `mu_AB - mu_A - mu_B + mu_0` and the standard
eight-cell inclusion-exclusion triple contrast. Pair the independent integer
seeds across masks, retain individual outcomes and failures, and do not present
development-selected contrasts as prespecified confirmations. A same-seed
native RNG coupling can still diverge in event count when an effect changes;
it does not justify pretending that every downstream draw was identical.

Useful raw measurements are damage by action/target, pure white versus extra
MH actions (native metrics tags), queue attacks, Whirlwind and Bloodthirst
casts, aura uptime, attempted/actual rage by source, rage refunds/spending,
the action time series, and cooldown activation times. The engine logs the
origin of extra attacks in `sim/core/attack.go:782`. For the shared-timer case,
directly check that Flask and Cloudkeeper active intervals do not intersect.
For the resource case, confirm that disabled Heroism has no 450589 rage/heal
events, while the same raw equipment remains equipped.

The reoptimization panel enumerates the same physical domain and three
policies under each mechanism intervention. It must be distinguished from
the fixed-configuration factorial: averaging locally selected factorials is
not equivalent to taking a factorial contrast of independently optimized
envelopes. Any policy or build that bypasses a mechanism is a result to retain.

## Candidate reusable descriptions and current boundaries

At most two templates are initially justified for study: an eligible-event
and resource conversion constraint, and a shared active-window occupancy
constraint. Features can include input mask, per-event probability, output
event count/rage, haste duration/multiplier, ICD, cooldown-resource identity,
and target-count cap. These are permitted public source features for all
methods. Item IDs cannot be used as learned exception labels disguised as
semantic rules.

The engine already supplies exact effect parameters in this information
setting. Estimating a quantity directly given by source is not a new learning
result. A statistical contribution would require a clearly unknown quantity
and held-out update decisions with equal source/log/query access for a generic
estimator. Any finite-domain optimized safety reference is an envelope over
that domain; simulated maxima are not global combat upper bounds.

No full 20-round rule has been frozen in this source inspection. No positive
interaction, zero-inflation reward growth, class/faction advantage, or AISTATS
novelty is claimed here. In particular, a damage-proportional rage loop would
be the wrong mechanism for these native Forever runs.
