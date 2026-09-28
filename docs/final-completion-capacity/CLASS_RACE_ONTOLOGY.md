# Native class, race, and resource ontology

Source-only audit for the final completion-capacity study, 2026-09-25. The full
`CODEX_WOW_FOREVER_FINAL_COMPLETION_CAPACITY.md` brief was read before this audit.
No simulation was run and no earlier experiment was modified. Source capability
is separate from successful runtime execution and from live-game fidelity.

The engine inspected is
`WORK_ROOT/external/mythicsim-forever-engine-r3-variants`, where
`WORK_ROOT=/work/Users/leiyo/wow-forever-sustainability-work`. All engine paths
below are relative to that directory. The existing research binary has SHA256
`59f42b32e2c834321773188db482419238ae57556942f6f1825258722fc0aafe`.

## Registration and the frozen 56-context target

All nine classes have actively registered damage agents in
`sim/register_all.go:33–59`. The registration contains 15 agents: Balance,
Feral, Feral Tank; Elemental, Enhancement; Hunter; Mage; Shadow, Smite; Rogue;
DPS Warrior, Tank Warrior; Protection, Retribution; DPS Warlock. Restoration
Druid/Shaman, Holy Paladin, and Healing Priest are commented out. A protobuf
spec entry alone does not establish an active agent.

The research executable invokes `sim.RegisterAll()` at
`cmd/wowfs-r3/main.go:78`. Its API is the common raid simulator, not a Warrior
API: `sim/core/api.go:65` calls `RunSim`; `proto/api.proto:65–84` has the player
spec oneof and `Player.rotation` is common APL. The previous Warrior wrapper
therefore cannot serve as a limit on engine class support.

The project's target is the frozen `configs/official_contexts.yaml`, SHA256
`a5d0b2a72c421250f7b9e9d71eecb1205dc3bc7d82cec641f0781e3595f2e9ee`.
Its archived official-page comparison is
`WORK_ROOT/provenance/context_matrix_verification.json`, recording the snapshot
hash `3678c56e653478b82166fc04052a3e9f91b705aabf1bdf23fcc0096516f96417`.
This audit independently parsed the engine's `*Races` arrays in
`ui/core/proto_utils/utils.ts:1030–1085`, expanded both Skyborne entries, and
compared them with every class in the project matrix: all nine sets match
exactly, with no missing or extra pairings. This is a static comparison, not
56 executed contexts.

| Class | Native class enum | Active damage choice | Alliance contexts | Horde contexts | Resource structure |
|---|---:|---|---:|---:|---|
| Warrior | 9 | Warrior | 5 | 5 | Rage; physical attacks; Execute spending |
| Rogue | 6 | Rogue | 5 | 4 | Energy, target-associated combo points, refunds |
| Hunter | 2 | Hunter | 4 | 4 | Owner mana; autonomous pet focus; ranged swing timing |
| Mage | 3 | Mage | 3 | 3 | Mana, cast time, free-cast procs, regeneration channel |
| Warlock | 8 | Warlock | 2 | 3 | Owner/pet mana, periodic spells, sacrifice/summon effects |
| Priest | 5 | Shadow Priest or Smite Priest | 4 | 2 | Mana, periodic/channel or direct holy spells |
| Paladin | 4 | Retribution Paladin | 2 | 1 | Mana, melee and seals/judgements |
| Shaman | 7 | Elemental or Enhancement Shaman | 1 | 4 | Mana, spell/melee procs, totems |
| Druid | 1 | Balance or Feral Druid | 2 | 2 | Mana; Feral also energy/rage and form changes |
| Total | — | Nine classes | 28 | 28 | 56 representable contexts |

`proto/common.proto:30–69` defines the following actual race/class enums.
`sim/core/racials.go:553–561` maps their factions. Skyborne is not an invented
alias for another race.

| Frozen race name | Native enum value | Faction | Frozen legal classes |
|---|---:|---|---|
| Dwarf | 1 | Alliance | Hunter, Paladin, Priest, Rogue, Shaman, Warrior |
| Gnome | 2 | Alliance | Mage, Priest, Rogue, Warlock, Warrior |
| Human | 3 | Alliance | Hunter, Mage, Paladin, Priest, Rogue, Warlock, Warrior |
| Night Elf | 4 | Alliance | Druid, Hunter, Priest, Rogue, Warrior |
| High Order Skyborne | 9 (`RaceSkyborneHighOrder`) | Alliance | Druid, Hunter, Mage, Rogue, Warrior |
| Orc | 5 | Horde | Hunter, Mage, Rogue, Shaman, Warlock, Warrior |
| Tauren | 6 | Horde | Druid, Hunter, Shaman, Warrior |
| Troll | 7 | Horde | Hunter, Mage, Priest, Rogue, Shaman, Warlock, Warrior |
| Undead | 8 | Horde | Mage, Paladin, Priest, Rogue, Warlock, Warrior |
| Windshaper Skyborne | 10 (`RaceSkyborneWindshaper`) | Horde | Druid, Hunter, Rogue, Shaman, Warrior |

Base attributes are class baseline plus race offsets plus class base crit
(`sim/core/base_stats.go:301–303`), rather than a Classic-only precomputed legal
pair table. Both Skyborne offsets are explicitly zero at lines 54–59. The
experiment must still enforce the frozen legality matrix: acceptance of an
arbitrary class/race request is not proof that the combination is legal.

### Known racial incompleteness

Both Skyborne variants receive native 1% melee/ranged/cast speed and 5% damage
against Elementals under Forever (`sim/core/racials.go:196–215`). Windshaper
additionally registers a 15-second cooldown granting 10% of current attack
power and spell power, with a three-minute cooldown (`racials.go:392–435`).

High Order's health/mana regeneration cooldown is explicitly **omitted** at
`racials.go:216–217`. The source's reason that this changes nothing measured
does not establish irrelevance for a mana-constrained experiment. Its five
contexts are source-representable with a known incomplete racial mechanic;
they must not be labeled complete live-game racial implementations. Keep
execution status and fidelity limitation in separate fields. Other source
comments also flag uncertain details, such as Gnome Eureka's mana saving
scope and Undead Touch of the Grave's critical behavior (`racials.go:220–226,
295–300`); the study measures this frozen simulator.

Gnome Expansive Mind explicitly applies only its mana-pool increase and omits
rage/energy-pool increases (`racials.go:64–67`). Gnome Warrior and Gnome Rogue
therefore have a second concrete missing-racial limitation. At least seven
frozen contexts have the specific omissions identified here; this is not a
claim that the remaining contexts have fully validated live-game fidelity.

## Credible preset inputs for a general wrapper

These tuples are sourced from existing native **Forever** Go tests. They are
starting configurations, not a claim that this audit ran those tests or that
their consumables/buffs are required. Freeze buffs/consumes explicitly and
preserve any removed optional APL actions as a documented policy change.
All gear paths are `ui/<directory>/gear_sets/<gear>.gear.json`; all APL paths
are `ui/<directory>/apls/<apl>.apl.json`. Options below are the interior of
the selected spec's `options` object using protobuf JSON field names.

| Class / spec oneof | UI directory | Gear | APL | Talents | Options |
|---|---|---|---|---|---|
| Warrior / `warrior` | `warrior` | `p0.bis` | `dps_reck` | `30305013-050520035150310051` | `{"startingRage":50,"shout":1}` |
| Rogue / `rogue` | `rogue` | `combat_sinister_strike_prebis` | `combat_sinister_strike` | `00530310501-32003311201515231` | `{}` |
| Hunter / `hunter` | `hunter` | `p0.bis` | `p1` | `5023000501-0050550501503051` | `{"ammo":1,"petType":1,"petUptime":1,"petAttackSpeed":2}`; see enum caveat |
| Mage / `mage` | `mage` | `p0.bis` | `forever_frost` | `050005013--0555003301001301251` | `{"armor":3}` |
| Warlock / `warlock` | `warlock` | `prebis` | `forever_pact` | `113-0005003221220311351-0550005` | `{"armor":1,"summon":3,"sacrifice":2,"weaponImbue":0}` |
| Priest / `shadowPriest` | `shadow_priest` | `p0.bis` | `p1` | `0253000311--550022501201302251` | `{"armor":1}` |
| Paladin / `retributionPaladin` | `retribution_paladin` | `launch` | `basic_ret` | `0550030022001--052251310002330321` | `{"primarySeal":1}` |
| Shaman / `elementalShaman` | `elemental_shaman` | `launch` | `default` | `2505301500123031-0500001-053050001` | `{}` |
| Druid / `balanceDruid` | `balance_druid` | `p0.bis` | `launch` | `5502220115501351--055003` | `{"okfUptime":0.2}` |

Exact test sources: `sim/warrior/dps_warrior/dps_warrior_test.go:16–85`,
`sim/rogue/dps_rogue/dps_rogue_test.go:15–135`,
`sim/hunter/hunter_test.go:15–103`, `sim/mage/mage_test.go:144–213`,
`sim/warlock/dps/dps_warlock_test.go:16–170`,
`sim/priest/shadow/shadow_priest_test.go:16–74`,
`sim/paladin/retribution/retribution_test.go:15–115`,
`sim/shaman/elemental/elemental_test.go:41–93`, and
`sim/druid/balance/balance_test.go:40–98`.

Hunter requires `distanceFromTarget:30` for this ranged APL. The test assigns
`PetAttackSpeed:2.0`, but the protobuf field is an **enum**: numeric 2 is
`OneThree`, which `sim/hunter/pet.go:40–46` converts to 1.3 seconds. Numeric 7
or the enum name `Two` means 2.0 seconds (`proto/hunter.proto:138–158`). A wrapper
must choose and freeze the intended interpretation rather than silently treat
the enum as seconds. Ammo 1 is Razor Arrow; pet type 1 is Cat. Mage armor 3 is
Molten Armor; Priest armor 1 is Inner Fire. Warlock summon 3 is Succubus and
sacrifice 2 is Voidwalker; the selected Demonic Pact talent supports retaining
a different sacrificed demon's effect with the active summon.

Two supported alternatives expose more resource structure:

- Feral: directory `feral_druid`, gear `p0.bis`, APL `feral`, talents
  `-5521002023132213051-05503`, options
  `{"innervateTarget":{},"latencyMs":100,"assumeBleedActive":false}` from the
  no-assumed-bleed test option in `sim/druid/feral/feral_test.go:45–64`.
- Enhancement: directory `enhancement_shaman`, gear `launch`, APL `default`,
  talents `05023015-055030030205112251`, options `{"syncType":3}` (Auto),
  from `sim/shaman/enhancement/enhancement_test.go:43–87`.

Balance's `okfUptime` is present in the test/protobuf, but no corresponding
runtime read was found in `sim/druid`; retaining that field does not establish
an active Owlkin Frenzy mechanic.

## Equipment legality is broader than test filters

Use the engine's UI eligibility tables in
`ui/core/proto_utils/utils.ts:1319–1505`, actual embedded item metadata
(`classAllowlist`, armor/weapon/hand/item types), and the complete loadout's
slot/unique/two-hand constraints. The backend's successful calculation alone
does not prove a loadout is legal.

| Class | Maximum armor | Eligible weapon types; `(2H)` also allows two-handed form | Ranged/relic |
|---|---|---|---|
| Warrior | Plate | Axe(2H), dagger, fist, mace(2H), held offhand, polearm(2H), shield, staff(2H), sword(2H) | Bow, crossbow, gun, thrown |
| Rogue | Leather | Dagger, fist, mace, held offhand, sword | Bow, crossbow, gun, thrown |
| Hunter | Mail | Axe(2H), dagger, fist, held offhand, polearm(2H), sword(2H), staff(2H) | Bow, crossbow, gun |
| Mage | Cloth | Dagger, held offhand, staff(2H), sword | Wand |
| Warlock | Cloth | Dagger, held offhand, staff(2H), sword | Wand |
| Priest | Cloth | Dagger, mace, held offhand, staff(2H) | Wand |
| Paladin | Plate | Axe(2H), mace(2H), held offhand, polearm(2H), shield, sword(2H) | Libram |
| Shaman | Mail | Axe(2H), dagger, fist, mace(2H), held offhand, shield, staff(2H) | Totem |
| Druid | Leather | Dagger, fist, mace(2H), held offhand, staff(2H) | Idol |

Dual wield is supported for Warrior, Rogue, Hunter, and Shaman under Forever
(`utils.ts:1088–1098`). Non-dual-wield classes may use shields or held offhands
where their class list permits. Hand enum values are main-hand-only 1,
one-hand 2, off-hand-only 3, two-hand 4 (`proto/common.proto:242–248`).

Go test `ItemFilters` are item-effect test selection, not a complete legality
ontology (`sim/core/test_generators.go:202–253`). Examples of mismatches are
Hunter's test filter including mace, Druid's including polearm while omitting
fist, and Warlock's restricting sword/dagger and off-hand hand type. They must
not override the UI class tables and database item restrictions.

## Mechanistic systems suitable for transfer

The strongest three-way Layer-A design is physical Warrior, mana-constrained
Mage, and a genuinely active pet/resource mechanism in Hunter or Warlock.
Rogue is also a strong independent resource-system transfer, but three weapon
amplitude studies across melee classes would not establish three event systems.

1. **Rogue energy and combo-point system.** `sim/rogue/rogue.go:174–196`
   initializes energy and dual swings; `sim/core/energy.go:15–17` supplies
   20.2 energy per 2.02-second tick. APL thresholds and ability costs control
   action opportunities. Relentless Strikes returns 25 energy with probability
   `0.2 * spent combo points` (`sim/rogue/talents.go:81–92`); Adrenaline Rush
   changes the energy-tick multiplier (`talents.go:419–465`). These are real
   resource/control changes, not damage-log reweighting. Energy and combo
   points are APL-readable (`sim/core/apl_values_resources.go:197–243`).
   Weapon speed, poison/proc timing, energy-refund items, or native cooldown
   items may change this system's kernel; do not carry over Warrior's affine
   fixed-control conclusion without independent validation.

2. **Mage mana, cast-time, and regeneration system.**
   `sim/mage/mage.go:158–185` initializes mana and spirit regeneration.
   Clearcasting temporarily removes magic mana costs and is consumed by a
   cost-bearing Mage cast (`sim/mage/talents.go:146–200`). Evocation is an
   eight-second channel with an eight-minute cooldown that changes actual
   mana regeneration (`sim/mage/evocation.go:9–75`). The supplied Frost APL
   consumes a mana gem below 80%, uses Evocation below 20% when more than
   25 seconds remain, and responds to Fingers of Frost. Spell power, mana/MP5,
   cast haste, and on-use effects can therefore trade off in actual DPS across
   burst and endurance tasks. Restrict a proposed scalar reduction only after
   measuring this stateful response; MP5-induced extra casts are not a fixed
   additive damage coefficient in general.

3. **Hunter or Warlock pet/resource system.** Hunter has owner mana,
   ranged swing timing and actual Aimed/Multi-Shot shared cooldown under
   Forever (`sim/hunter/hunter.go:194–211`), plus a separately scheduled focus
   pet (`sim/hunter/pet.go:120–180`). Cat prioritizes Bite over Claw to allocate
   focus (`pet.go:213–229`). Talent effects include pet damage, crit-triggered
   Frenzy, Bestial Wrath and focus-regeneration changes
   (`sim/hunter/talents.go:12–58,108–173`). Warlock creates real mana-bearing
   pets (`sim/warlock/pet.go:80–132`); Life Tap can restore active-pet mana
   through Demonic Energies (`sim/warlock/lifetap.go:21–63`). Pet actions and
   resources are separately present in `UnitMetrics.pets` (`proto/api.proto:341`).
   A study claiming pet-owner interaction must perturb a native item/effect
   or configuration that actually changes this coupling and inspect pet
   metrics, rather than merely include constant pet DPS beside owner gear.

Concrete native knob semantics matter:

- Mage MP5 is stat enum 12. It contributes `MP5 / 5` mana per second both
  while casting and outside casting; the native scheduler applies two-second
  mana ticks (`sim/core/mana.go:142–199`). This changes available casts and
  mana-cooldown policy, rather than post hoc weighting an existing damage log.
- Warrior weapon speed changes actual swing scheduling and Forever rage per
  landed swing (`sim/core/ruleset.go:78–112`). A change in speed must specify
  whether damage per swing or nominal weapon DPS is held fixed.
- Hunter `petAttackSpeed` selects native swing timing, while pet base damage
  is also set to `[18.17,27.66] * speed` (`sim/hunter/pet.go:38–69`). Nominal
  white-attack DPS is consequently held constant before discrete timing and
  procs; pet speed is not simply a pet damage multiplier. It can shift event
  timing and, where selected talents supply it, crit-triggered Frenzy.
- Hunter `petUptime` is clamped to `[0,1]`; the pet is permanently disabled
  after the corresponding initial fraction of the fight
  (`sim/hunter/pet.go:132–143`). It is not random intermittent uptime.
- A real item-driven pet coupling exists: Devilsaur Tooth, item 19992,
  registers Primal Instinct 24353. Its use gives the pet's focus dump and
  special ability +100 bonus crit until the next such ability hit consumes
  the aura. It requires an enabled pet, uses the normal GCD, and has a
  two-minute cooldown (`sim/hunter/items.go:164–241`). Its actual effect
  amplitude is not exposed by the current generic R3 item-variant interface.

Pet speed/uptime are native pet configuration/environment options. Calling
their variation a new equipment reward would require a separately justified
and frozen design language; an option that changes combat is not automatically
an equipment mechanism. For an equipment-only pet experiment, verify a real
pet-affecting item and its legal cross-combinations before freezing.

Two constraints are material. Both Hunter and Warlock
`makeStatInheritance()` return empty stats (`sim/hunter/pet.go:190–194`,
`sim/warlock/pet.go:201–204`): generic owner AP/SP equipment changes do not
automatically scale pets. Also, DPS Warlock Life Tap only deals its computed
health damage when `IsTanking()` (`sim/warlock/lifetap.go:55–57`). The default
damage role therefore supports a GCD-to-mana mechanism, but not a faithfully
charged health-for-mana utility claim. These facts favor Mage for the clean
mana branch and require an explicit coupling choice for the pet branch.

Core APL supports current mana/energy/rage/combo points, time, cooldowns,
auras and spells for all registered classes. Custom APL factories extend that
interface; no separate Warrior-only APL registration is required
(`sim/core/agent.go:35–43`, `sim/core/apl_value.go:104–121,225`). Built-in
resource-injection actions are not automatically legitimate player policies.

The audited task limitations remain: generic target lists are fixed at combat
start; there is no generic target-spawn/wave or movement schedule. Long fights
with persistent mana are supported, but should not be called multi-wave
encounters. Target count, armor, resistance/mob type, fixed duration, incoming
attacks, and execute thresholds provide genuine task dimensions. A general
wrapper should retain resource channels per class and pet metrics instead of
labeling every resource as Warrior rage.

The native Elemental mob-type enum is 4 (`proto/common.proto:745–750`).
Encounter `execute_proportion_20` is field 3 (`common.proto:810`): in a
fixed-duration encounter, 0.2 enters the 20% execute phase at 80% of elapsed
duration. The engine raises 25%/35% execute proportions to at least the 20%
proportion (`sim/core/target.go:33–41`) and advances phase flags without
resetting resources (`sim/core/sim.go:547–589`). With health termination, phase
transitions instead use accumulated encounter damage. These are existing
phase semantics, not a generic externally programmable phase schedule.

The audit supports attempting all 56 target contexts with real native inputs.
Only new protocol-bound execution receipts can establish completed coverage;
until then, completion-capacity checkpoints remain `not_run`.

## Primary-stat control feedback and mechanism calibration

Source audit of the actual `configs/fc_presets.json` policies distinguishes
damage amplitude from resource feedback. These expectations do not replace
the separate native calibration receipts.

| Selected class | AP/RAP/SP intervention: expected control behavior in the fixed-duration, no-incoming task set |
|---|---|
| Warrior | Forever white-hit rage depends on speed/outcome, not damage. AP changes attack/ability/Deep Wounds amounts; fixed action outcomes can preserve control. |
| Rogue | AP does not directly change energy ticks, combo-point gains or refunds. Blade Flurry does check positive damage before copying a hit, so conclusions require staying away from a zero-damage boundary (`sim/rogue/talents.go:350–369`). |
| Hunter | RAP changes owner ranged damage; owner mana costs and pet focus remain separately defined. Empty pet stat inheritance prevents an automatic RAP-to-pet-damage path. |
| Mage | SP changes damage while Clearcasting/Master of Elements depend on landed/critical outcomes and base costs. SP is distinct from an MP5 intervention, which can change casts. |
| Warlock | A definite feedback path exists: rank-6 Life Tap has a 0.8 SP coefficient; calculated amount becomes owner mana and potentially active-pet mana (`sim/warlock/lifetap.go:16–17,51–62`). SP can change the mana-threshold APL and pet mana availability. A fixed-control affine reduction should not be assumed. |
| Priest | The selected Shadow APL does not cast Vampiric Embrace. Its native callback would convert damage to health, not mana (`sim/priest/vampiric_embrace.go:29–35`). Shadow Word: Death deliberately omits backlash and an unresolved script effect (`shadow_word_death.go:11–17`). Thus an actual health-cost tradeoff is not present in this preset. |
| Paladin | Sanctified Judgement returns a fraction of consumed seal mana cost, not damage (`sim/paladin/talents.go:347–373`). Shield Specialization's block mana is inactive without incoming attacks. AP-driven damage alone need not change the mana-threshold seal APL. |
| Shaman | Elemental SP changes damage; relevant cost/cast procs depend on event identity/outcome. Water Shield gives a fraction of maximum mana on incoming hits or healing crits (`sim/shaman/water_shield.go:25–63`), neither supplied by this no-incoming damage task set. |
| Druid | Balance Eclipse stacks depend on completed Wrath/Starfire casts (`sim/druid/talents.go:215–256`), Nature's Grace on crits, and Innervate on mana. No SP-to-mana restoration path was found for the selected Balance policy. |

The control audit must include each pet recursively: action outcome counts,
resource events and amounts, auras and OOM duration. Checking only the owner's
casts misses the Warlock feedback path. Aggregate equality plus one normalized
first-seed trace is a finite diagnostic, not evidence of equality of all
per-seed event schedules or all continuous parameter values.

A class-independent five-channel damage partition is owner autos, owner
periodic, owner direct physical, owner direct other, and all pet damage.
Action metrics encode the native school **bitmask**; physical is 2 in that
output (`sim/core/metrics_aggregator.go:146`, `sim/core/spell_school.go:11–13`),
whereas the input protobuf school enum uses physical 0. Resource rates must
be reported by unit and native type separately, not mapped to fictitious
Warrior rage. This feature definition is a new cross-class behavior definition,
not the original Warrior-specific seven coordinates.

The independently authorized mechanism calibration is frozen in
`configs/fc_mechanisms.json` and implemented by
`src/wowfs/experiments/fc_mechanisms.py`. It measures all six-by-five legal
crosses for Human/Orc Warrior, Gnome/Undead Mage, and Human/Orc Rogue on the
same eight tasks, 32 seeds per cell: 1,440 calls and 46,080 requested battles.
The primary mechanisms are held-DPS weapon speed, MP5, and actual Talon proc
rate; their partners are offhand weapon amplitude, back spell power, and
offhand weapon amplitude. Endpoint fits predict the three interior partner
columns separately for every primary/context/task; no interpolation across
primary settings is assumed. The reference primary is declared before results.
The calibration seed 810200001 is shared with the separate old-ecology
development calibration by coordination; these are coupled development data,
not independent replications. Prospective confirmation seed 820000001 is
separate. This grid is not a completed matched-ecology capacity experiment.

The grid completed with 1,440 new successful physical receipts, 46,080 battles,
zero errors and zero cache reuse. Results are
`WORK_ROOT/artifacts/final-completion-capacity/MECHANISM_CALIBRATION.json`;
run `mechanism-calibration-v1` protocol SHA256 is
`ef6127fb5cd86bb409e4e3e2ae6e12c3788e1e9d5142cf0d77d49abcafe65aad`.

| Mechanism | Context/task pairs | Maximum partner-interpolation per-seed residual | Largest primary response range at fixed partner |
|---|---:|---:|---:|
| Warrior speed | 16 | 2.27e-13 DPS | 40.828 DPS |
| Mage MP5 | 16 | 3.41e-13 DPS | 184.914 DPS |
| Rogue Talon PPM | 16 | 1.14e-13 DPS | 7.082 DPS |

All tested partner columns preserve recursive control metrics; all three
families change primary event/resource metrics in each context/task pair.
This latter statement includes resource amounts and must not be read as a
claim that every task gains casts or DPS. For example, Gnome Mage's ten-second
damage and action outcomes are unchanged by MP5. On endurance at back SP400,
however, MP5 0 to 200 raises Gnome Frostbolt casts from 52.906 to 91.531 per
battle and DPS from 242.856 to 427.770; Undead casts rise from 49.625 to 87.500.
That is an actual resource-to-cast effect.

Warrior speed has nonmonotone, task-dependent responses: Human cleave peaks
at 2.9 seconds in this grid, while sustained peaks at 2.5 seconds. Rogue PPM
response is small and nonmonotone in these 32-seed development estimates,
typically about a 1–2% range in sustained/high-armor tasks. Do not assume a
monotone PPM-to-value ordering or hide a weak transfer result.

Partner slopes differ across primary settings, so the complete surface is
not a single additive `primary + partner` scalar response. The validated
result is conditional partner interpolation at each tested primary setting.
Matched ecology construction must retain all eight task coordinates and
complete cross-combinations, freeze its predictions separately, and report
generalization or failure of the scalar theorem. No native capacity claim
has been obtained from this calibration alone.
