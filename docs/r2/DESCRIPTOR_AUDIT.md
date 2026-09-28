# Frozen descriptor audit

The initial sections are a source-only audit of `configs/r2_unseen.yaml` and
the feature construction in `src/wowfs/experiments/r2_sequences.py`. No held-out
combat response was read for that source audit. The final addendum was added
after the frozen run completed and explicitly inspects its measured maxima.
No new experiment was run and no frozen configuration was changed. The
configuration still has SHA-256
`2a5b03d641c321699b9fec20339ee6cdf23c8799faf54941ee34654e64a487c1`.
Native source references below are relative to engine commit
`17d75ccc8c67d027ae0088243ea3ee806d406847`.

**Finding:** the ten sampled numerical descriptors agree with the executable
native definitions. No discovered numeric transcription error requires
changing the frozen run. The compact features omit real interaction details,
and the family-growth comparison has strength and representation confounding.
Those are material limits on scientific interpretation, not grounds to relabel
the completed simulation inputs.

## Ten reproducibly selected active items

Selection used Python `random.Random(9242027).sample` on the sorted IDs whose
descriptor kind is not `static_only`, without consulting combat performance.
The selected IDs, in order, were 12531, 11744, 6622, 15814, 8190, 14487, 17705,
18203, 20130, and 17111.

| Item | Frozen nonzero coordinate / raw parameter | Independent source check |
|---|---|---|
| Searing Needle 12531 | Direct damage 60; 1 PPM | Matches `sim/common/item_effects.go:1842`. The preceding TODO says a target fire-damage buff is not implemented. The descriptor correctly follows this engine, which is not full live-game validation. |
| Bloodfist 11744 | Direct damage 20; 4 PPM | Matches `sim/common/item_effects.go:647`; physical defense causes an eligible `MeleeSpecial` output, verified separately in the helper. |
| Sword of Zeal 6622 | One temporary physical-buff family; +10 flat physical damage, +150 armor, 15 s, 1 PPM | Matches executable `sim/common/item_effects.go:2111`. The adjacent comment says 1.8 PPM; the frozen descriptor correctly uses code rather than that comment. |
| Hameya's Slayer 15814 | Full periodic damage 80 | `sim/common/item_effects.go:1321` defines ten ticks of eight at three-second intervals. Application requires a landed melee-special outcome; 80 is nominal full duration, not guaranteed realized damage. |
| Hanzo Sword 8190 | Direct damage 75; 1 PPM | Matches `sim/common/item_effects.go:1372`; physical special output is retained in raw metadata. |
| Bonechill Hammer 14487 | Direct damage 90; 1 PPM | Matches `sim/common/item_effects.go:715`, Frost school with magic hit/crit outcome. |
| Thrash Blade 17705 | Expected extra-MH requests 0.045 | `sim/common/item_effects.go:2208` requests one extra MH attack at 1 PPM; base speed 2.7 from native DB gives `1 * 2.7 / 60`. This is conditional per eligible landed event, not requests per second. |
| Eskhandar's Right Claw 18203 | Peak attack-speed increase 0.10; 6 s | Matches the 1.1 multiplier and six-second aura at `sim/common/item_effects.go:922`. |
| Diamond Flask 20130 | One temporary physical-buff family; +75 Strength, 60 s, 360 s personal cooldown, 60 s shared lock | Matches `sim/warrior/items.go:21`. The source locator in YAML points one line before the registration, which is harmless. |
| Blazefury Medallion 17111 | Direct damage two; every eligible landed melee event | Matches `sim/common/item_effects.go:2819`. The raw output-mask note correctly distinguishes special input from other melee input; direct damage can crit. |

The words maximum damage in coordinate names mean source magnitude before
mitigation and crit. They do not bound final damage after critical multipliers,
damage modifiers, target effects, or repeated proc events.

## Metadata and set thresholds

All 78 descriptor names and set names match `assets/database/db.json`; all
coordinate vectors have length eight. Catalogue enumeration was repeated from
source and yielded the same 185 initial and 1497 total physical configurations.
Maximum equipped counts over that full catalogue are:

| Native set | Largest count | Consequence |
|---|---:|---|
| Battlegear of Heroism | 4 | Its four-piece ten-rage callback is added once by the feature builder. Two-piece resistances remain native; three-piece vitality is a native no-op. No six-piece Strength bonus is reachable. |
| Vindicator's Battlegear | 2 | The native two-piece block bonus is reachable and omitted from the eight effect coordinates. The four declared tasks have no incoming attacks and this bonus does not increase their damage objective. This omission would matter in a defensive task. |
| Bloodmail Regalia | 1 | No set bonus reached. |
| Primal Batskin | 1 | No set bonus reached. |
| Spider's Kiss | 1 | No set bonus reached. |
| Spirit of Eskhandar | 1 | No set bonus reached; new left claw is not combined with the old right claw by this finite catalogue construction. |
| The Gladiator | 1 | No set bonus reached. |

The native character applies raw item stats, weapon skills, individual item
effects, and set effects separately (`sim/core/character.go:329`). Marking an
item `static_only` means it has no separately encoded item callback, not that
its native armor, hit, crit, skill, or Strength vanished. Those attributes are
still simulated. The static rule proxy intentionally omits several of them,
including weapon skill, accuracy, crit, and armor; it is not an exact mapping
to native damage. All future uses of the same descriptor must keep that
distinction.

The following row maxima were independently recomputed over the initial
catalogue, without combat output:

```text
static strike proxy       111.13516483516483
extra MH request intensity  0.1215
peak haste increase         0.2
direct damage per proc    737
temporary buff families     3
rage return/discount       42
full periodic damage        0
maximum armor reduction     0
unsupported marker          0
```

The q=8 prefix activates the first eight rows, including static power. Thus its
zero periodic-damage and zero armor-reduction thresholds reject the first
positive values in those coordinates by construction. That is evidence about
the frozen policy's conservatism, not evidence that native DoTs or armor
reduction are unsafe. The ninth marker is not an uncounted rejection condition.

## Representation limits that must remain in the report

The extra-MH coordinate measures only requests entering the extra-MH
scheduler. It does not count direct physical weapon-proc spells that can
generate more proc opportunities. In `sim/common/itemhelpers/weaponprocs.go:39`,
the physical-damage helper assigns `ProcMaskMeleeSpecial` and
`SpellFlagSuppressEquipProcs`. In the same file at lines 67 and 83, a
chance-on-hit weapon callback excludes `SpellFlagSuppressWeaponProcs`, a
different flag. `ProcMaskMeleeSpecial` includes both MH-special and OH-special
bits (`sim/core/flags.go:66`). A landed physical proc can consequently enter
eligible callbacks on either weapon, including its own chance-on-hit callback.
The source comment explicitly anticipates self-triggering. This path does not
require an `ExtraMHAttack` call, and a gate at that scheduler cannot close all
such edges.

Raw masks and PPM are present for direct-damage entries, but the eight scalar
coordinates do not form a complete causal event matrix. In particular:

- The direct-damage coordinate uses damage per proc, not expected damage per
  triggering event or per time; PPM and attack rate still matter.
- A physical proc's child can crit, affect Flurry, or trigger another permitted
  weapon callback. The input/output graph and target/state dependence are not
  reconstructed from the additive scalar sum.
- Buff-family count omits differences in magnitude, duration, uptime, and
  synchronization. Raw data remain available, so generic baselines are entitled
  to use them under the declared information permissions.
- Summing armor-reduction maxima ignores the native exclusive
  `MinorArmorReduction` resource shared by Annihilator, Bashguuder, and
  Rivenspike (`sim/common/item_effects.go:3040`).
- Some new target slows and health-return effects have no useful defensive
  consequence in the declared damage-only tasks. Their implementation does not
  create measured survival coverage.

An unsupported marker of zero therefore means a primitive family was
classified by the source grammar; it does not prove that every causal edge or
state dependence was retained in the numeric feature vector. The term fixed
grammar is also coarse: new proc AP or flat-damage auras combine trigger and
payload primitives that were present separately in old haste procs and active
physical buffs. It does not establish that causal graph rank or independent
interaction count stayed identical.

The expanded native library simultaneously changes weapon DPS, speed, damage
school, proc magnitude, and effect semantics. The fixed library itself includes
both weak and strong native items without single-item marginal matching.
Therefore a fixed-versus-expanded comparison is descriptive, with source-known
mechanisms to investigate. It is not a matched causal estimate that changing
only the number of semantics caused a capacity change.

## Proposed follow-up probe, not implemented or run

Use Bloodfist 11744 in MH and Hanzo Sword 8190 in OH, retaining their static
weapon stats. Both are already in the frozen public catalogue, and the source
predicts direct physical-proc descendant edges. A second native pair with
larger per-proc damage can be prespecified if needed; it must not be chosen by
scanning held-out success labels and then presented as an independent test.

The first stage is an observational event check on a fixed build: record the
triggering action and generated action for weapon-proc callbacks, with a
parent-event identifier rather than treating simultaneous timestamps as proof
of ancestry. Logging must not change RNG draws or action ordering. Count root
melee events, Bloodfist/Hanzo proc children, self descendants, cross-weapon
descendants, extra-MH requests, and damage by source. Compare native versus the
already specified extra-MH gate with the same policies and fresh paired seeds.
The question is whether direct physical-proc descendants remain when that
gate suppresses extra-MH requests, not whether a native DPS difference happens
to be statistically nonzero.

A causal edge-cut intervention can then add
`SpellFlagSuppressWeaponProcs` to the output of the physical weapon-proc helper,
while preserving its existing `SuppressEquipProcs` flag, damage magnitude,
hit/crit resolution, proc mask, weapon stats, and initial root trigger chance.
This cuts subsequent weapon-proc callbacks from that output without using item
IDs as a global balancing rule. It leaves other permitted callbacks, such as
Flurry and Heroism, available and must be described with that exact scope.
It is a separate research mechanism, not a native fidelity fix.

Cross the two item-effect on/off factors with edge-cut on/off. Keep the
extra-MH gate as an independent panel if needed. Use the sustained and short
tasks first, the same three available policies, 32 fresh development fights
per cell followed by 128–512 independent confirmation fights only for an
informative contrast. Report the damage and descendant-count factorials,
negative or null outcomes, and both fixed-configuration and equal-budget
reoptimization consequences. The complete protocol must be frozen before
this follow-up's responses; this audit does not report an implemented intervention or a new
simulated result.

## Post-run addendum: why the q=8 filter retained the observed worst growth

The completed native finite-table search identifies the same high-armor winner
under q=2, q=4, and q=8: gear `568edd5a53cabc4b`, with Deathbringer 17068 in MH,
Thunderfury 19019 in OH, Gri'lek's Charm 19951, and Blackhand's Breadth 13965,
using `native_reck`. Other slots use the specified initial armor and Titanic
Leggings. Its active feature scores are:

```text
winner:     [110.63870884106818, 0,      0,   440, 0, 30, 0, 0]
t0 maxima:  [111.13516483516483, 0.1215, 0.2, 737, 3, 42, 0, 0]
```

Every active row passes. Its unsupported-component marker is one, but that is
the declared ninth feature rather than an uncounted rejection rule. q=2 and q=4
each reject six configurations from the 1497-configuration union; q=8 rejects
310, or 304 additional configurations. Those additional rejections cannot
reduce the maximum while this winner remains admitted. This is an exact statement about the
frozen feature test, not a statistical or causal explanation of damage.

The 180-second, 10,000-armor task gives these measured point estimates, each
using 128 fights:

| Context | Best initial mean DPS | q=2/4/8 winner mean DPS | Growth |
|---|---:|---:|---:|
| Human | 179.909482 | 212.856838 | 18.3133% |
| Orc | 178.214740 | 210.990360 | 18.3911% |

The Human initial winner is `aa43592d4c4d6059`: Vis'kag 17075, Brutality Blade
18832, HoJ 11815, and Blackhand's Breadth. The Orc initial winner is
`3ee7b15c74c9a9b8`, with the same weapons and Blackhand's Breadth but Diamond
Flask 20130 in the other trinket slot. Both use `native_reck`. These references
are maxima over all 185 initial physical configurations and all three listed
policies, not a manually selected weak baseline.

Native source verifies the following mechanism facts:

- Deathbringer is 1 PPM with a 110–140 Shadow-damage proc
  (`sim/common/item_effects.go:779`). Its native base speed is 2.9 s, so the
  helper's trigger probability is approximately 0.048333 per eligible landed
  MH event. Its proc has an empty output mask.
- Thunderfury is 6 PPM with a 300 Nature-damage primary proc, magic hit/crit
  outcome, and `SpellFlagIgnoreAttackerModifiers`
  (`sim/common/item_effects.go:2226`). Its 1.9 s base speed yields a 0.19
  trigger probability per eligible landed OH event. The custom trigger has no
  explicit weapon/equipment suppression flag test. The damage spell's output
  mask is `SpellProc | SpellDamageProc`, not an extra MH request.
- Thunderfury's separate zero-damage bounce applies a 25-point Nature
  resistance reduction to at most five targets for twelve seconds; it does
  not multiply the 300 damage by five. Its primary hit also applies the native
  attack-speed debuff. The frozen direct-damage descriptor of 300 is correct.
- The engine routes physical direct damage through target armor and Nature or
  Shadow damage through magic resistance
  (`sim/core/spell_resistances.go:18`). Target armor therefore does not directly
  attenuate either of these magic damage procs.

The rule's damage coordinate adds maxima per proc, giving 140 + 300 = 440,
but does not include trigger probability, realized event frequency, or damage
school. The initial limit 737 also uses a three-target source cap for
Masterwork Stormhammer even when evaluating the single-target armor task.
Those omissions explain **why these rows cannot guarantee this task's damage
ceiling**. They do not, without an effect-toggle comparison, apportion the
observed growth between weapon stats, proc rate, damage school, trinket choice,
or their interactions.

Damage accounting in the selected winner assigns Thunderfury 34.633789 DPS
for Human and 34.210612 DPS for Orc, about 16.2% of their totals. Deathbringer's
proc contributes 3.909483 and 3.859385 DPS, respectively. These action shares
describe the realized build. They are not counterfactual gains from adding
either item, and the pair has not received the four-cell toggle contrast.
The source identifies a concrete missing representation—per-eligible-event
yield and task-specific mitigation—without establishing positive causal
synergy between the two weapons.

The extracted evidence, source features, winner/reference gear, action
breakdowns, standard errors, and native cache keys are saved in
`$WOWFS_WORK_ROOT/artifacts/r2-discovery/latest/selected_evidence/SEMANTIC_BEST_SOURCE_AUDIT.json`.

## Action and resource behavior mapping check

The seven frozen behavior coordinates use the intended native rank IDs:
`OtherActionAttack` (all MH/OH/extra tags), Execute 20662, Whirlwind 1680 and
Cleave 20569 (all tags), Bloodthirst 23894, and all remaining damage as the
residual share. The native rank-60 registrations use exactly those IDs;
Whirlwind's OH spell is tag 2, so ignoring tags in this classification correctly
includes it. Queue-only Cleave entries have zero damage and cannot inflate a
damage-share coordinate. Heroic Strike remains in the declared residual group.

`ResourceTypeRage` is enum value 3 (`proto/api.proto:285`). Native summaries
divide attempted and actual gain by iterations once; the behavior function
then divides positive attempted rage gain by encounter seconds and by the
declared normalization of twenty. Waste is positive attempted minus actual
gain, clipped at zero and divided by total positive attempted gain. Positive
refunds are included: the feature is gross attempted rage inflow, not net
productive generation. No wrong-rank or tag omission was found in this mapping.
