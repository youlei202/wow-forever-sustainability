# R3 source mechanism audit

This document concerns the community engine `sage3648/mythicsim-forever-engine`,
commit `17d75ccc8c67d027ae0088243ea3ee806d406847`, under `RulesetForever`. It is an
audit of implemented mechanics, not validation against a live game server.
Native measurements and their immutable protocols are reported separately.
Source paths below are relative to that pinned checkout.

## The canonical pair has no direct bleed–lightning trigger edge

| Component | Native implementation | Important distinctions |
|---|---|---|
| Blood Talon, 12795 | MH-only fist weapon, 35–67 base damage, 1.3 s; `sim/common/item_effects.go:684` registers 1 PPM, spell 13318, ten 10-damage ticks at 3 s intervals | Physical, melee defense, empty proc mask; an extra application hit check precedes the DoT. Reapplication resets the tick count. Forever ticks may crit. |
| Thunderfury, 19019 | One-hand sword, 60–145, 1.9 s; `item_effects.go:2226` registers 6 PPM, spell 21992 | Tag 1 deals 300 Nature damage with magic hit/crit and ignores attacker damage modifiers. Tag 2 deals zero damage and is intended to apply −25 Nature resistance for 12 s to at most five targets; see the aura collision below. The attack-speed slow is not player haste. |
| Deathbringer, 17068 | One-hand axe, 114–213, 2.9 s; `item_effects.go:779` registers 1 PPM, spell 18138 | 110–140 Shadow damage, magic hit/crit, empty proc mask. It is a different base/speed/school comparator, not a one-factor Talon ablation. |

Blood Talon's trigger uses `CreateWeaponProcSpell`
(`sim/common/itemhelpers/weaponprocs.go:110`): landed events matching the equipped
hand's melee mask may roll; `SpellFlagSuppressWeaponProcs` excludes triggering.
Its periodic events dispatch through `OnPeriodicDamageDealt`, not the
`OnSpellHitDealt` callback to which Thunderfury listens
(`sim/core/spell_result.go:461`). Its proc mask is empty. Therefore the Talon tick
does not directly trigger Thunderfury. Conversely, Thunderfury's damage mask is
spell-proc/spell-damage-proc, not the Talon weapon's melee mask. Its resistance
effect would not amplify Physical Talon ticks. Thunderfury's custom callback lacks
the helper's explicit suppression-flag check; that distinction matters for
other melee-proc descendants, but does not add a Talon-bleed trigger edge.

`sim/core/attack.go:962` converts PPM to chance using base weapon speed. In the
canonical hands, the nominal chances are 1.3/60 for Talon and 6×1.9/60 = 0.19
for Thunderfury per eligible event, before landed/application outcomes. These
are probabilities per event, not hard rates per minute. Eligible special
attacks, haste, extra attacks and the policy change realized proc rates.
Thunderfury's 300 damage is primary-target damage; multiplying it by five is
incorrect because its bounce events deal zero damage.

**Native implementation caveat: the resistance callback is shadowed.**
`NewEnemyAuraArray` initializes each aura immediately (`sim/core/aura.go:936`).
Thunderfury first creates the attack-speed array through `ThunderfuryASAura`,
which registers label `Thunderfury` (`sim/core/debuffs.go:910`). The subsequent
resistance array requests the same label through `GetOrRegisterAura`. That
function returns the existing aura and replaces selected event callbacks, but
does not install the new `OnGain` or `OnExpire` (`sim/core/aura.go:433`). Thus the
intended resistance-changing closures are not the registered callbacks in this
path. The later bounce activation also addresses the existing speed aura.
The actual speed factor is `1/1.2`, from `AtkSpeedReductionEffect`, not `0.8`.
R3 preserves this pinned behavior; the exposed resistance-amplitude parameter
must not be interpreted as an effective intervention without a separate native
check or explicitly versioned repair. Neither a repair nor new results are
reported by this source audit.

Physical direct damage is reduced by armor, whereas the periodic Physical
channel avoids the direct-attack armor reduction
(`sim/core/spell_resistances.go:18`). Nature and Shadow use their resistance
paths. School, timing and actual exposure to eligible events therefore belong
in an interaction description; an unweighted count or maximum damage per proc
does not represent these mechanics.

## Re-entry and positive effect interaction are different measurements

For a fixed physical loadout, compare all four registrations of Talon effect A
and Thunderfury effect B while retaining weapon damage, speed and static stats.
The factorial contrast is `mean_AB − mean_A − mean_B + mean_none`. Its sign and
uncertainty measure effect interaction in that context. Switching an entire
weapon changes several attributes and is a separate contrast.

A weak-base new weapon can compensate for the power of a legacy weapon so that
their complete loadout enters a cap-constrained competitive set. This can happen
with zero factorial interaction. It is a useful re-entry event only if the
preregistered competitive, legacy-use and behavioral criteria also pass. The
source establishes neither that event nor a positive causal effect contrast;
both require native results. An effect-switch experiment also need not preserve
the same random event trace, because removing a registration removes its events
and random-number requests.

## A candidate family with fixed control and changing rewards

The more specific reusable object is a **control kernel**: a fixed ruleset,
task, character, policy, weapon speed/type, resource rules, trigger graph,
probabilities, timing, debuffs and callback registrations. Numeric reward
amplitudes may vary within a kernel if all state-transition decisions remain
unchanged. This is more restrictive than a shared verbal effect type.

For the audited Warrior configuration, `30305013-050520035150310051`, the
following source paths support testing a reward-linear family:

* Forever auto-attack rage depends on base weapon speed, handedness and fixed
  talent multipliers, not actual damage or critical damage
  (`sim/core/ruleset.go:87`, `sim/core/rage.go:77`). Unbridled Wrath depends on
  landed white-hit eligibility. Fixed-speed damage amplitude therefore does
  not itself alter resource supply. This claim is specific to Forever; the
  Classic branch is damage-dependent.
* `Weapon.BaseDamage` always draws the same uniform variate, then computes
  `min + (max−min)*u`. Weapon attacks add an AP term with fixed speed or fixed
  normalization (`sim/core/attack.go:117`). Scaling only base min/max is affine
  at a fixed event, while the AP contribution is an intercept.
* Deep Wounds does not copy actual crit damage. The latest Physical crit selects
  a hand; ticks read that hand's current **average weapon damage plus AP**, and
  the current multipliers (`sim/warrior/deep_wounds.go:21,61,81`). Thus MH base
  scaling also changes some Deep Wounds rewards affinely. Trigger and refresh
  decisions depend on crit/hand, not the damage amplitude. Deep Wounds itself
  has empty proc mask and explicitly opts out of Forever periodic crits.
* Bloodthirst is flat damage plus 0.35 AP, and Execute uses remaining rage.
  Refunds depend on landed outcomes, not damage magnitude
  (`sim/warrior/bloodthirst.go:66`, `sim/warrior/execute.go:55`). Their control
  paths stay fixed when rage/outcomes stay fixed.
* Blood Talon tick amplitude and Thunderfury direct amplitude appear in damage
  calls without an amplitude-dependent trigger condition. The R3 hooks retain
  callbacks and calls even for a zero amplitude. Tick timing, tick count, PPM
  are **not** reward-only coordinates. Thunderfury's intended resistance knob
  is also not assumed to be effective because of the native collision above.
* Time-limited encounters use time-based execute thresholds and do not terminate
  when damage exceeds a health budget (`sim/core/sim.go:403,488,552`). The R3
  duration tasks have no incoming attacker (`tankIndex:-1`), and no explicit
  front-facing flag. The native DPS APL predicates are time, rage, cooldowns,
  target count and aura state; no predicate reads accumulated damage.

This yields the testable form `DPS(seed, theta) = intercept(seed) +
coefficient(seed) · theta`, including action-specific damage totals, at fixed
kernel. `theta` can contain base-weapon amplitude and Talon tick amplitude;
Thunderfury direct amplitude can be a third coordinate with debuff unchanged.
The coefficients include mitigation and realized event exposure; they are not
hand-assigned item-power coefficients. Mean response is then affine as well.
Fixed-policy envelopes are maxima of affine functions and can have kinks.

## Explicit boundaries of the audit

| Potential dependency | Source and status in the audited family |
|---|---|
| Damage-based encounter stopping / execute threshold | `sim/core/sim.go:403,552`; excluded by fixed-duration task |
| Rage from incoming damage | `sim/core/rage.go:137`; excluded by no incoming attacks |
| Enrage and Blood Craze damage conditions | `sim/warrior/talents.go:257,559`; no incoming attacks, and Blood Craze absent from talents |
| Sweeping Strikes copying parent damage | `sim/warrior/sweeping_strikes.go`; talent absent; do not generalize the audit to it automatically |
| Positive-damage item callbacks or lifesteal health feedback | Present elsewhere in `sim/common/item_effects.go`; not certified by merely sharing the label “proc” |
| Block and post-outcome clipping | `sim/core/spell_outcome.go:728,877`, `sim/core/spell_result.go:259`; rear-facing attacks avoid block, but an amplitude domain must still be branch-stable |
| Iteration-end damage test in rage accounting | `sim/core/rage.go:270`; calculates rage-gain threat metrics after combat and does not feed the DPS control trace |
| Speed / PPM changes | Change hit timing, proc probability, rage per hit, normalized/AP terms, and sometimes outcome opportunities; new kernel even within one weapon type |
| Hit/crit/haste/skill stats | Change outcomes, Flurry and policy/resource timing; new kernel, not an amplitude-only transfer |
| DoT interval or count changes | Change scheduler/refresh exposure, crit draws and completed ticks; new kernel |
| Resistance-reduction magnitude | Would change mitigation if correctly registered; pinned Thunderfury path shadows the callback, so do not infer an effective intervention from requested metadata |
| Removing an effect | Changes registrations and random draws; not the same operation as retaining it at zero reward |
| Full combat-policy optimization | Different best policy can produce a piecewise-affine envelope; the current claim covers the finite frozen APL catalogue, not all possible strategies |

The native Hand of Justice in the canonical loadout adds attacks on landed
eligible events; that graph remains part of the fixed kernel. The audit does
not assume that the canonical environment has no other procs. Exact action
counts, hit/crit counts, aura uptimes and attempted/actual resource gains at
amplitude corners provide an empirical falsification check, not a proof for
unexecuted configurations. Floating-point tolerance must be declared; exact
bit equality is not necessary for the real-arithmetic affine statement.

## Transfer families and honest scope

`configs/r3_types.yaml` separates reward amplitudes, within-type control changes,
and new control mechanisms. The primary seen-family transfer is fresh numeric
variants of the native Talon/Thunderfury mechanisms, not discovery of new
official item IDs. Diamond Flask 20130 provides an actual on-use Strength
window (75 Strength, 60 s, 6 min cooldown, shared offensive-trinket lockout of
60 s); Gri'lek's Charm of Might 19951 gives 30 rage on a 3 min cooldown
(`sim/warrior/items.go:21,64`). Their activation/resource semantics introduce
new control structure relative to the amplitude family. Both appeared in R2,
so any held-out designation is relative to R3 fitting, never first exposure
across the project. A new mechanism may itself admit a fresh amplitude family
after a separate audit; failure of an old kernel does not imply irreducible
per-item complexity.
