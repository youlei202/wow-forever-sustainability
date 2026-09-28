# Native resource mechanisms and unexecuted Rogue transfer

These statements describe the pinned community engine at
`17d75ccc8c67d027ae0088243ea3ee806d406847`. They are source evidence, not new
combat results or live-server validation. Rogue remains `not_run` in R4.
Paths below are relative to the external engine checkout retained under
`$WOWFS_WORK_ROOT/external/mythicsim-forever-engine-r4-worlds`.

## Warrior: white-event resource feedback

`sim/core/ruleset.go:87–112` defines one-hand rage as 3.46 times the weapon's
base swing speed per landed main-hand white attack. An off-hand white attack
receives half of this amount, before other rage multipliers. Two-hand weapons
use 4.5 times base speed. Reward amplitude and critical damage do not enter
this formula. `sim/core/rage.go:76–114` rejects misses, dodges and parries and
requires the main-hand or off-hand auto proc mask.

The formula uses base weapon speed, not the current hasted interval. The
upstream source explicitly identifies this distinction as an assumption to
re-measure: the calibration sample had no haste. Under the implemented rule,
haste and extra eligible white events increase resource arrival frequency.
The same resource callback sees extra main-hand auto attacks; their action
tag changes to 3, as recorded by `rage.go:63–65`, but the accepted proc mask
is still an auto attack. This supplies a source-grounded feedback hypothesis,
not proof that a particular pair's admission depends on feedback.

The baseline cap is 100 rage (`rage.go:10`), with native modifier support.
`AddRage` records both offered and actual gain after capping and calls the
rotation (`rage.go:200–224`). Resource arrivals can therefore change action
selection. Incoming attacks use a separate pre-armor-damage / maximum-health
formula; its factor 10 is explicitly marked as requiring upstream validation.

## Rogue: periodic energy, with other native resource mechanisms

`sim/core/energy.go:16–17` defines **20.2 energy every 2.02 seconds**, with a
random initial tick phase (`energy.go:313`). Tick advancement uses
`EnergyPerTick * EnergyTickMultiplier` (`energy.go:290`); it does not read
white damage, weapon speed or white-event count. `sim/rogue/rogue.go:186–187`
initializes maximum energy at 100 plus 5 per Vigor rank. Adrenaline Rush changes
the tick multiplier (`sim/rogue/talents.go:432–435`).

This is a contrast between the two base resource-arrival rules. It is not a
claim that Rogue actions and resources are independent: finishers can refund
energy through Relentless Strikes (`talents.go:89`), attacks can change combo
points, and native item/talent effects can alter decisions and resource use.
A transfer experiment would need its own legal gear, talents, APL, baseline
domain and executed resource trace.

## Legal active-resource comparison

Gri'lek 19951 and Diamond Flask 20130 have the native class allowlist `[9]`
(Warrior); Renataki 19954 has `[6]` (Rogue). Gri'lek's callback explicitly casts
the character to `WarriorAgent` (`sim/warrior/items.go:64–65`). Placing it on a
Rogue is neither a legal same-item transfer nor a valid negative control.

Gri'lek supplies 30 rage with a three-minute personal cooldown and no native
shared cooldown (`sim/warrior/items.go:64–92`). Renataki supplies 60 energy,
has a three-minute personal cooldown and ten-second shared offensive timer,
and its major-cooldown condition requires energy at most 40
(`sim/rogue/items.go:18–50`). The latter is a different native item and control
rule. Any comparison must be labeled a mechanism-level transfer, with these
differences disclosed.

The engine registers an actual DPS Rogue module. A candidate engineering
input would use `ClassRogue`, the `rogue` options oneof, native Combat Sinister
Strike talent string `00530310501-32003311201515231`, and the native
`ui/rogue/apls/combat_sinister_strike.apl.json`. The neutral phase-one preset
`ui/rogue/gear_sets/combat_sinister_strike_p1_bis.gear.json` avoids the
faction-specific pre-BiS PvP pieces. These are inspected capabilities only;
they add no executed class, race, ecology or trajectory coverage.
