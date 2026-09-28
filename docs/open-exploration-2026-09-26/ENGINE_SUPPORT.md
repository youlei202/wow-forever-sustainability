# Native mechanism support audit, 2026-09-26

This is a source audit and request-generation contract, not an executed-mechanism
or effect-size claim. Native smoke outcomes, including ignored or ineffective
interventions, supersede `supported_source` labels in the execution atlas.

The existing executable is
`/work/Users/leiyo/wow-forever-sustainability-work/envs/r3-go/wowfs-native-variants`.
The inspected source tree is
`/work/Users/leiyo/wow-forever-sustainability-work/external/mythicsim-forever-engine-r3-variants`.
No native source, binary, existing data, or old experiment module was modified.
The existing `fc_native.make_input` / `instantiate` bridge supplies real item IDs,
complete presets, legal class/race combinations, and explicit equipment slots.
The campaign runner owns executable/source hashes and retains raw native stdout.

## Source-grounded corrections before collecting outcomes

1. **Higher damage and critical hits do not directly give more white-hit rage in
   this Forever implementation.** `sim/core/ruleset.go:67–110` makes rage per
   landed swing proportional to weapon base speed. Crit can still cause Flurry,
   giving additional swings and therefore indirect resource feedback. A Classic
   damage-to-rage explanation would be false here.
2. **Equipment hit and crit are universal in Forever.**
   `sim/core/ruleset.go:44–63` merges the two gear pools, subtracting duplicates.
   Spell and melee hypotheses concern their different attack tables, not two
   independent equipment stats. Overrides explicitly zero the opposite hit/crit
   field when testing one axis.
3. **Thunderfury bounce deals zero damage.**
   `sim/common/item_effects.go:2222–2308` has one 300-nature-damage proc and a
   zero-damage bounce applying nature resistance reduction. Calling this a
   damaging multi-target chain would misdescribe the executable.
4. **Life Tap has a fidelity limitation.** `sim/warlock/lifetap.go:51–65` restores
   mana and optionally pet mana but deals the self damage only while tanking.
   These DPS requests have no tank; policy results are not health/survival results.
5. Existing Hunter/Warlock pet-owner inheritance omissions and incomplete racial
   behaviors remain as documented in the prior native support report. This
   campaign does not fix physics or infer live-game fidelity from simulator runs.

## Registered search hypotheses

The 12 registered families contain 8 settings each: four legal class/race
contexts and two parameter/task strata. Race replicas do not increase the number
of mechanism families. Crit/Flurry and hit attack-table families share some
infrastructure; a positive result must identify actual differing response and
choice consequences, rather than treating these labels as proof of independence.

| Family | Actual input hooks | Mathematical possibility | Important boundary |
|---|---|---|---|
| mana_regen | MP5 versus spell power; short/long encounters | Resource-limited casts and damage tradeoffs | Source hooks do not establish a mana bottleneck in every setting |
| melee_hit | Universal hit versus AP; armor task pair | Saturation, dual-wield misses, resource feedback | 19 percentage-point dual-wield white-miss penalty; current talent/preset fixed |
| spell_hit | Universal hit versus SP; duration pair | Spell miss saturation and gear substitution | Native 1% miss floor; not separate melee/spell gear pools |
| crit_flurry | Crit versus AP, Warrior and Rogue controls | Indirect action feedback versus a non-rage control | Crit-to-rage is indirect, not damage-based |
| weapon_cadence | Main-hand speed with `hold_base_dps`; small DPS budget variants | Timing and skill normalization | Matched weapon DPS does not imply matched total performance |
| periodic_refresh | Blood Talon PPM, native DoT, tick damage variant | Refresh/truncation and periodic utility | Blood Talon main hand only; no synthetic proc formula |
| nature_proc | Thunderfury PPM versus weapon damage, nature resistance/target count | Mixed-school response and resistance debuff | No damaging chain bounce |
| shadow_proc | Deathbringer PPM versus weapon damage; armor pair | Magic versus physical composition | Axe-compatible Warrior/Hunter only; Hunter melee inactivity is an informative control |
| onuse_shared_cd | Actual trinkets 18820, 22268, 11832; passive alternatives; priority policy | Shared-timer contention and burst/duration dependence | Native item powers/cooldowns unchanged; other stats are research variants |
| policy_resource | Warlock Life Tap or Mage Evocation threshold, MP5/SP | Equipment/strategy substitution | 35% threshold is a declared finite strategy alternative, not optimized policy |
| resistance_penetration | Spell penetration versus SP; actual target resistances | Task-specific floors and crossover | Explicit magic resistances are research encounters |
| joint_slots | Neck and back stats, complete joint configurations | New-new combinations and component-level legality | Only a00/x0 initially present; fixed-partner algorithms need a different model |

The primary source locations are exported to `ENGINE_SUPPORT_MATRIX.csv` and
`HYPOTHESIS_REGISTER.csv`. Stat enum names are checked against
`proto/common.proto:81–125`; the fixed R3 hook restrictions are in
`src/wowfs/simulator/r3_variants.go`. PPM hooks exist only for Blood Talon,
Thunderfury and Deathbringer. Weapon-speed modifications explicitly declare
whether base DPS or swing damage is held fixed.

The on-use source is `sim/core/item_effects.go:132–141`, sharing the offensive
trinket timer for the duration of the effect. Talisman is registered at
`sim/common/item_effects.go:2811`, Draconic Infused Emblem at line 2487, and Burst
of Knowledge at lines 2437–2480. Spell hit and dual-wield calculations are in
`sim/core/spell_result.go:195–214` and `sim/core/spell_outcome.go:675–695`.
Penetration uses `max(0,resistance-penetration)` in
`sim/core/spell_resistances.go:147`. Mana acquisition and spending are in
`sim/core/mana.go`; Flurry is in `sim/warrior/talents.go:269–342`.

## Physical domain and source units

Every world registers 17 primary alternatives including old a00, four partner
alternatives, two actual encounter settings and one or two finite policies.
Native presets retain the unmodified gear/talents/enchants outside replacement
slots, no added raid buffs/consumes and no incoming attacks. Replacements use
existing real item IDs; aliases identify distinct research designs and never
claim newly official reward IDs or dungeon provenance.

For ordinary worlds a00 and all four partners are initially available. For the
eight `joint_slots` worlds only a00 and x0 are old; both slots have future
components, recorded in `component_incidence`. Their tensors cannot be treated
as fixed-old-partner tables. Power-cap violations disqualify a release; they
never remove a physically legal tensor cell.

The candidate design is fixed before observations: old allocation .5 and budget
.75, followed by 16 combinations of four allocations and budgets .65, .8, .95,
1.1. All weak and alternative allocations remain in the declared candidate set.
The on-use family alternates actual active and passive trinkets while retaining
its full public candidate set. Parameter strata are explicitly
`research_variant_moderate` and `research_variant_stress`; neither is labelled a
verified obtainable game-item range. Every alias includes raw distances to its
actual native base item's stat or effect values. A 2x stratum is not evidence of
practical realism. A promising effect requires a subsequent narrower/native-item
challenge if it depends on these amplitudes.

Default anchors schedule five primary indices against all four partners. The
runner can instead schedule all 17 against endpoint partners plus the remaining
old-row partners through the explicit selection dict. Scheduling a subset never
asserts that its omitted physical cells are illegal or safe. A fully observed
registry has 15,232 design cells before seed blocks, but this number is a design
count until actual receipts establish execution.

## Unsupported or deferred claims

- Full PvP, healing balance, survivability, movement and live multiplayer are not
  demonstrated by these stationary, no-incoming-attack requests.
- General pet-owner stat-inheritance corrections require a separately versioned
  engine; not implemented in this campaign branch.
- Arbitrary new proc effects, unimplemented item IDs, arbitrary internal cooldown
  changes, new shared timers and new set bonuses are not synthesized.
- A mathematical capacity or retention conclusion is not inferred from source
  support, a registered world, a low-precision anchor, or an ignored APL action.
- C/new-task expansion has not been implemented by this world generator. Two
  fixed tasks are V/H exploration contexts; changing them mid-sequence would
  require explicit C accounting and preservation of old task weights.

`tests/test_oe_worlds.py` checks all registered physical crosses for equipment
legality, incidence, cardinality and deterministic task/policy interventions,
without executing the native engine or pretending those checks are observations.
