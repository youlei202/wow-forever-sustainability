# Native execution support

The pinned community Forever engine executes all 56 official class/race contexts
in the frozen legality matrix, covering all nine classes. This is an execution
support result. It does not establish release capacity, complete strategy
coverage, balance, or agreement with the live game.

The actual executable is
`WOWFS_WORK_ROOT/envs/r3-go/wowfs-native-variants`, SHA-256
`59f42b32e2c834321773188db482419238ae57556942f6f1825258722fc0aafe`.
Its upstream is `sage3648/mythicsim-forever-engine`, commit
`17d75ccc8c67d027ae0088243ea3ee806d406847`, with the already archived R3
research-variant hooks. The unchanged binary calls `sim.RegisterAll()`; earlier
Warrior-only research templates were not a limitation of the executable.

The frozen support run is
`runs/final-completion-capacity/support-smoke-v1` beneath `WOWFS_WORK_ROOT`.
Its protocol SHA-256 is
`17749153a9bd44910fa6b0f1eece2bf93eb9abce3cb74af379f0681e2101b779`.
All 56 invocations succeeded with 16 iterations each: **896 actual battles**,
zero failed invocations, and 56 contexts with positive finite damage. Seed
810000001 is shared across contexts. These are coupled simulations, not 56
independent ecological samples. The machine-readable receipt is
`artifacts/final-completion-capacity/NATIVE_SUPPORT_RECEIPT.json`.

| Class | Alliance | Horde | Executed | Fixed native DPS specialization |
|---|---:|---:|---:|---|
| Warrior | 5 | 5 | 10 | Fury, Recklessness APL |
| Rogue | 5 | 4 | 9 | Combat Sinister Strike |
| Hunter | 4 | 4 | 8 | Native P1 ranged build, Cat |
| Mage | 3 | 3 | 6 | Forever Frost |
| Warlock | 2 | 3 | 5 | Forever Pact, Succubus |
| Priest | 4 | 2 | 6 | Shadow |
| Paladin | 2 | 1 | 3 | Retribution, Seal of Command |
| Shaman | 1 | 4 | 5 | Forever Elemental |
| Druid | 2 | 2 | 4 | Balance |

Each input uses the maintained `configs/fc_presets.json`, actual native UI
equipment/APLs, and source-test talents/options. The combat lasts 180 seconds
against one level-63 target with 3731 armor, with the final 20% of time marked
below 20% target health. There are no external raid buffs, consumes, incoming
attacks, or population-calibrated strategy optimization. Native preset enchants
are retained. Pet attack speed is explicitly the Hunter enum `Two` (2 seconds);
the source test's numeric 2 denotes a different enum value and was not copied
as a duration.

Preset normalization preserves item identity and enchants. The Paladin preset
places ranged item 22400 before two-handed weapon 18830; they are assigned to
their actual ranged and main-hand slots. Missing optional off-hand/relic slots
in Druid and Shaman presets are represented by ID 0. No replacement item was
invented. Class legality is checked against native UI armor, weapon, hand,
ranged-type restrictions and database class allowlists, not permissive Go
test item filters.

Known source omissions affect seven contexts: five High Order Skyborne contexts
lack the racial health/mana regeneration cooldown, and Gnome Rogue/Warrior lack
racial energy/rage pool enlargement. The remaining 49 are not asserted to have
complete live fidelity. Detailed registration, races, presets, and other
limitations appear in [CLASS_RACE_ONTOLOGY.md](CLASS_RACE_ONTOLOGY.md).

Hunter and Warlock pet damage is included in the player's DPS by native
`UnitMetrics.AddFinalPetMetrics`. Their individual pet actions remain in nested
raw pet metrics; the earlier R2 summary's player-only action fractions must not
be treated as complete behavior coordinates for these classes. The smoke
records active Cat and Succubus damage, with unused Warlock pet entries at zero.

## Supported research controls

The existing R3 hook can replace a named stat on an actually equipped native
item before character initialization. These are research aliases of the same
base ID, not official future item IDs. A base ID must appear exactly once when
overridden. Neck and back slots provide distinct non-set base IDs in every
chosen preset; Mage and Priest duplicate-ring presets make ring overrides
ambiguous and are unsuitable without a separately declared change.

Primary AP, ranged AP, or spell-power addition is a hypothesis about reward
response, not proof of affinity. In particular, Warlock Life Tap converts spell
power into mana and pet mana, so event/control changes can break affine response.
Both Hunter and Warlock currently have empty owner-stat-to-pet inheritance
functions. Owner AP/SP increases must not be interpreted as pet-stat increases.

Distinct available mechanisms include Warrior weapon speed and rage schedules,
Mage MP5 through native two-second mana ticks, and actual Hunter pet item 19992
(Devilsaur Tooth) affecting the next Bite/Claw critical strike. Hunter pet speed
and uptime options alter real events, but are configuration parameters rather
than equipment rewards unless the experiment explicitly declares that design
language. No capacity experiment is counted by this support receipt.

To reproduce the frozen support inputs and run, source `scripts/env.sh` and run
`python -m wowfs.experiments.fc_support`. An existing frozen run requires the
matching archived source and `--resume`; changed source is intentionally refused.

## Native stat-response calibration

The separate `scalar-calibration-v1` physical run completed 2240 successful
invocations and 143360 battles, with zero failures. For each of 56 contexts and
eight actual encounter conditions, points 0 and 250 fit a primary-stat response;
100 and 500 are held out. A fifth input puts 125 on each of neck/back instead of
250 on neck alone. All equipment entries and enchants remain unchanged; only
the named native stat is replaced before initialization. This is not an
after-simulation damage multiplier.

All 51 non-Warlock contexts pass all eight contexts' held-out per-seed DPS
affinity checks (maximum absolute residual 1.052e-12), recursive player/pet
aggregate controls, and the first seed's normalized event trace. All five
Warlock contexts fail the affinity/control checks: their maximum per-seed
residuals range from 84.59 to 107.00 DPS. The recorded source mechanism is
spell power affecting Life Tap mana and pet-mana restoration, changing future
actions. These cases remain available for finite-table evaluation; they are
not included in the affine native mapping.

All 56 contexts pass the equal-total-stat allocation check. Five cross-class
damage coordinates partition owner auto-attacks, owner periodic damage, owner
direct physical damage, owner other direct damage, and all pet damage. Typed
resource rates are stored separately. These are not the historical
Warrior-specific seven behavioral coordinates.

An analysis correction excludes friendly/self targets from damage channels,
matching native DPS aggregation. Undead racial self-damage was present in raw
action metrics but is not outgoing enemy damage. The original physical-run
analysis is preserved; the corrected read-only analysis is archived separately
as `scalar-calibration-analysis-v2`. Its damage-coordinate sum agrees with native
DPS within 3.41e-13. No native calls or utility fits were changed. The current
`SCALAR_CALIBRATION.json` artifact names both physical and analysis provenance.

These checks validate a finite set of seeds and design points. They do not
prove exact affinity at every future parameter or establish any expansion
capacity without the separately frozen release experiment.
