# R6 native repair gates: source-only feasibility

Status: provisional design evidence, **not native outcome evidence**. No A
simulation was launched for this audit. The complete imported R5 theory was
read before this inspection; its SHA-256 is
`a2160fda7467f3618797c91f2257f6dac39b284804774cf0751eac1d92cd8dd2`.

After this source inspection, root froze the separate `native-gate-probe-v1`
experiment with **14551 Edgemaster's Handguards as the old anchor**, 12 cross
cells plus two matched set-off controls, Human/high_armor/native_reck,
2,048 iterations and seed 609270001. The engine agent owns that execution;
this note does not report its outcomes. No tuning is authorized. The earlier
16737 Gauntlets of Valor suggestion is only a source-legal, unrun alternative.

The inspected engine is
`$WOWFS_WORK_ROOT/external/mythicsim-forever-engine-r3-variants`, based on
upstream commit `17d75ccc8c67d027ae0088243ea3ee806d406847`.
Item identities below were decoded from the actual embedded
`assets/database/db.bin`, SHA-256
`3df0c7c00f57762401c1f4d018ae54ff05c1dffe18978a5fd08a5bad723792b5`,
using the checkout's `proto/ui.proto` and
`$WOWFS_WORK_ROOT/envs/r2-go/protoc/bin/protoc --decode=proto.UIDatabase`.

## A legal pair of four-piece gates

Heroism and Stormshroud admit two fixed pieces each, protected source gloves,
and repair legs. All declared source/repair pairings are physically legal for
a Warrior. No source-label condition is introduced.

| Role | Slot | Native ID and item | Set |
|---|---|---|---|
| Fixed | Head | 21999 Helm of Heroism | Heroism |
| Fixed | Wrist | 21996 Bracers of Heroism | Heroism |
| Fixed | Chest | 15056 Stormshroud Armor | Stormshroud |
| Fixed | Shoulder | 15058 Stormshroud Shoulders | Stormshroud |
| Protected source H | Hands | 21998 Gauntlets of Heroism | Heroism |
| Protected source S | Hands | 21278 Stormshroud Gloves | Stormshroud |
| Repair H | Legs | 22000 Legplates of Heroism | Heroism |
| Repair S | Legs | 15057 Stormshroud Pants | Stormshroud |
| Possible old neutral legs | Legs | 22385 Titanic Leggings | None |
| Possible mandatory new core | Hands | 19143 Flameguard Gauntlets | None |
| Frozen old anchor candidate | Hands | 14551 Edgemaster's Handguards | None |

The Heroism pieces are Warrior-only plate; the Stormshroud pieces are
unrestricted leather. Edgemaster's is unrestricted mail; the remaining
listed pieces are unrestricted plate. None
of these decoded records is unique. Keep the remaining equipped slots free
of these sets, and freeze legal weapons and all other dimensions separately.
The core and both protected sources occupy the same slot. Two repairs cannot
be equipped together because both occupy the leg slot.

With H/S denoting the additional four-piece effect, the complete matrix is:

| Hands / legs | Old neutral | Repair H | Repair S |
|---|---|---|---|
| Protected H | None | H | None |
| Protected S | None | None | S |
| New core | None | None | None |
| Old frontier anchor | None | None | None |

All cells retain the fixed two-piece effects. The table describes **set
activation only**, not utility or source viability. Native item statistics
currently differ between rows and columns.

## Exact implemented effects

Paths and line numbers here are relative to the inspected engine.

* `sim/warrior/item_sets_pve.go:175`: Heroism 2pc adds 8 all resistances;
  3pc is an empty callback. Its 4pc callback at line 186 registers
  `Warrior's Resolve`, action 450587, on landed melee hits, 1 PPM. The handler
  heals `sim.Roll(88, 133)` and adds 10 rage when the character has a rage
  bar, with resource metrics 450589. It does not need incoming attacks.
* `sim/common/item_sets/crafted.go:170`: Stormshroud 2pc registers a 5%
  chance on landed melee attacks to deal `sim.Roll(15, 25)` Nature damage,
  using magic hit/crit. This effect exists in every matrix cell because two
  fixed pieces are always equipped. Its 3pc callback at line 207 returns
  immediately without an energy bar, so it contributes nothing for Warrior.
  Its 4pc callback at line 239 adds 14 attack power and 14 ranged attack power.
* `sim/core/item_sets.go:109`: the engine counts equipped items by actual set
  ID/name and applies each reached threshold. The associations above follow
  from native set membership and slot exclusivity, not wrapper filtering.

Source SHA-256 receipts:

* `sim/warrior/item_sets_pve.go`:
  `0a6c432b9c8491c3571a6dbff07977143e578a9cfab9cba590e28598d0f1d9fd`
* `sim/common/item_sets/crafted.go`:
  `565a5ce36680c384ded57a66044361363cbd1a130402fcf6aa84627c635ef7c0`
* `sim/core/item_sets.go`:
  `aeb1c5f3a5f2e3e5be3bd056c6b9634ffadf987171ad31936d48f27a12110b2a`

## What still needs evidence

R3's existing `sim/core/wowfs_r3_variants.go` accepts finite nonnegative
native-stat replacements per original item ID, including zero. Consequently
the three leg alternatives can receive identical complete stat vectors,
while source/core/anchor glove stats can be declared independently. Any
such intervention must be explicitly archived as a research variant of its
actual base item. The supported wrapper does not modify set membership,
set thresholds, the Heroism proc rate/rage amount, or Stormshroud's 14 AP.
It cannot tune an arbitrary source-dependent reward table.

Equalizing repair leg stats is a plausible way to isolate the real set gates.
It is not yet a validation of R5's exact source-response equations: every
cross-pair, core pair, old alternative, policy, and task in the frozen domain
must still be measured or otherwise justified. Rage feedback and policy
changes can alter utility. Existing Blood Talon affine results do not certify
this different mechanism or arbitrary AP interventions. Stormshroud's fixed
14 AP increment may leave narrow or nonexistent robust cascade margins.

A full two-repair cascade also needs an old frontier above both protected
source values. If the old domain contains only the two protected glove
choices, then `f0 = max(vH, vS)`, and R5's cap `tau <= f0 + epsilon`
prevents the higher source from becoming obsolete. The separate old anchor
row supplies a possible larger frontier without either repair gate. Thus a
complete minimal candidate here has four glove choices and three leg
choices, or 12 cells, unless a separately declared old configuration already
supplies that frontier. The frozen Edgemaster's anchor has native +7 axe,
sword, and dagger skill; those weapon-skill entries are not changed by R3's
ordinary stat replacements. Whether it actually attains the intended old
frontier is an outcome to check, not an assumption or a reason to tune.

Only two physical associations have been found here. This is not an arbitrary
`m` native construction, a forced cascade, or evidence of a minimum release
size. The next authorized experiment would need a frozen complete domain and
independent validation of old competitiveness, core novelty, cap, source
responses, and all strict/weak closure inequalities from the imported R5.

## Rejected nearby alternatives

* Dungeon set 1 was changed in Forever: Valor's 4pc is an empty disarm-break
  callback; its rage proc is 5pc (`sim/common/item_sets/dungeon_set_1.go:318`).
  Lightforge and the other dungeon-1 4pc movement/control effects are also
  unmodeled. Classic set descriptions would misidentify these gates.
* Might's 5pc proc is on incoming melee spell-hit callbacks, so it is inactive
  in a no-incoming-attack task. A proposed Might/Wrath 5pc pair also fails the
  current embedded item domain: only Wrath legs 16962 and head 16963 occur in
  this database, insufficient to equip five pieces.
* Heroism 4pc with Devilsaur 2pc is a legal asymmetric fallback, using the
  same hands/legs layout, but the symmetric Heroism/Stormshroud arrangement
  above supplies actual four-piece gates on both sides.
