# R4 native platform and source-defined domains

The baseline reuses the frozen R2 native executable and pinned community engine
commit `17d75ccc8c67d027ae0088243ea3ee806d406847`. R1–R3 runs and binaries are not
modified. Maintained entry points are `r4_native.py`, `r4_worlds.py`,
`configs/r4_ecosystems.yaml`, and `scripts/native_build_r4.sh`. Runtime data lives
under `$WOWFS_WORK_ROOT/runs/r4-foundational-discovery`, with the corresponding
artifact and cache directories outside the source tree.

Twelve source-defined small domains cover amplitude/attribute, timing/cooldown,
resource/feedback, and target/damage/defense backgrounds, three pools each. The
first eight pools have 4×4×4×3 = 192 terminal combinations, the last four 3^4 = 81.
Each pool has exactly two old choices per variable slot and therefore 16 initial
combinations. All terminal old/new mixtures are enumerated: 1,860 pool incidences,
1,747 distinct complete equipment configurations. The first eight pools have
seven new item identities each, permitting a common inventory of five remaining
future items after two alternative initial releases. These labels describe an
experimental release order, not historical or official game releases.

The embedded `assets/database/db.bin` was decoded independently. All 70 relevant
item IDs and every non-default metadata field agree with `db.json`; every pool
combination passes native slot, hand, class, weapon and unique-item checks. The
receipt, hashes and decoding script are under
`runs/r4-foundational-discovery/engineering/EMBEDDED_ITEM_AUDIT.json`.
Acquisition metadata is retained verbatim, with unknown sources left unknown.
It is native database metadata, not independent live-game validation. Pools
avoid faction-specific PvP weapons; comparisons use the same neutral items for
Human and Orc Warriors.

Four prespecified mechanism curricula contain eight native representatives
each: static/weapon-skill, timing/event/resource, direct/periodic/damage-school,
and target/defense/feedback. All representatives occur in the enumerated domain.
Maelstrom 19289 has every partner combination inside the pools containing it.
The `resource_set_pair` pool fixes exactly two Heroism pieces; the new chest and
wrists jointly activate four pieces, whereas neither activates the threshold
alone. This source construction preceded native outcome inspection.

Eight tasks retain the four R2 conditions (sustained, short_burst, four_target,
high_armor), then add 10-second burst, 360-second endurance, two-target 60-second
combat, and incoming-attack resource pressure. The last condition uses a real
native enemy attack every two seconds with base damage 500 and 10% spread,
sets the player as tank and faces the player toward the target. It changes
incoming resource supply and the attack table; it is not a survival simulation.
Native death tracking does not halt rotation. Upstream incoming rage assumes
raw damage × 10 / max health, and upstream labels this factor unverified.
A two-seed engineering fixture confirms incoming rage events and nonzero damage
taken; no healing or survivability claim follows.

The three policies are the existing native no-Recklessness and Recklessness APLs,
and the existing fixed rage-conservative transformation. They can inspect rage,
remaining time, target count, execute phase, auras and cooldowns. They do not
optimize arbitrary action sequences. In particular, Flask is held until the
last 60 seconds; in a 180-second fixture it cannot contend at time zero with
Cloudkeeper. Native spell casts and resource traces, not APL item references,
are the evidence that a capability executed. Old and new equipment receive the
same policies.

The shared baseline completed 83,856 physical cells × 16 seeds = 1,341,696 battles,
with zero engine errors. The eight research-world comparisons completed 60,480
distinct native calls and 967,680 battles, also with zero engine errors.
Pool means and their sampling error remain distinct from exact configuration
enumeration. Every pool uses its own 16 old configurations for its frozen
initial scale/cap. R3 task anchors remain separate references; they are not
silently reused for a different ecology. The run stores the complete protocol,
requests, source snapshot, binary, results and failures. `BASE_ECOSYSTEMS.json`
in the frozen baseline directory is the authoritative domain, including a hash
verified against the protocol's science section.

## Research worlds, permission C

A separate executable at `envs/r4-go/wowfs-native-worlds` has SHA-256
`8654a90735607a1988eebd2ee401a3253873e056c0819141f30ac43f3ea57172`.
The native default preserves the full canonical native result and event log.
Canonicalization sorts unordered metric records by action ID; it never reorders
seed samples or event logs. An initial positional-array assertion failure is
preserved and diagnosed in `engineering/WORLD_SMOKE_V1_ORDERING_DIAGNOSIS.json`;
all seven underlying native invocations succeeded.

The additional `research_world` envelope supports four independent fields:

| Field | Exact intervention |
| --- | --- |
| `independent_offensive_cooldowns` | Each `GetOffensiveTrinketCD` registration receives its own timer |
| `all_offensive_shared_seconds` | Every spell with the native offensive-equipment flag shares one per-unit timer of this duration; replaces existing shared timers, retains personal cooldowns |
| `heroism_excludes_extra_attacks` | Excludes landed melee events with native extra-auto action tag 3 before the Heroism PPM draw |
| `block_extra_attack_reentry` | Suppresses an entire immediate/stored extra-MH request batch when its triggering action is native extra-auto tag 3 |

The first two fields are mutually exclusive. Default zero/false retains native
physics. World changes apply before character construction at t=0. They are
explicit counterfactual game rules, not admission-only algorithms or official
mechanics. Heroism retains ordinary/special triggers, static stats, and other
set bonuses. Reentry suppression retains ordinarily generated extra attacks
and already-triggered companion auras. A queued special replacing an extra
swing has a different action identity, so these interventions do not claim to
identify every genealogical descendant of an extra attack.

The frozen eight comparisons are A1 independent timing_shared; A2/A3 unified
60-second active equipment in timing_extra/timing_periodic; A4–A6 Heroism event
filtering in the three resource pools; A7/A8 reentry filtering in timing_extra
and resource_haste. Each uses its entire frozen pool, all eight tasks, all three
policies and both races, at 16 matched seeds. World-specific old anchors and
common-native raw old performance must both be reported. Single-item marginal
strength is not compensated or claimed to match perfectly.

Telemetry preserves eligible and suppressed Heroism events, extra-attack
request batches and requested attack counts, reentrant and suppressed batches,
source identities and ten-second request-time windows. Requested attacks are
not identical to realized attacks, especially on the stored path. Scientific
interpretation requires the native action/resource summaries as well.

## Added demand diagnostic

`task-growth-v1` completed 31,080 distinct native calls and 497,280 battles with
zero engine errors. Its four additional tasks are (45 seconds, one target,
5,000 armor), (120 seconds, three targets, 5,000 armor), (45 seconds, three
targets, 7,500 armor), and (120 seconds, one target, 7,500 armor). Every target
has level 63 and a 20% execute phase, with no incoming attacks. This is a
prespecified duration-by-target factorial with balanced armor assignments,
not a random sample from a task population or an item-conditioned demand.

The complete domains of static_skill, static_accuracy, timing_extra,
timing_shared, resource_set_pair, resource_cost, target_damage and target_armor
were measured for both races and all three policies. Each new task has its own
initial 16-configuration anchor and 5% cap headroom. A twelve-task comparison
must retain all eight original caps and the original source registry. These
extra tasks are a separate diagnostic, not additional evidence that the
original eight-task joint criterion passed.

Use the run's `CONFIG.yaml` with its `BASE_ECOSYSTEMS.json` when loading this
table: the dependency snapshot under `source/configs` deliberately retains the
original eight-task runner configuration. `FULL_COMBINATION_COVERAGE.csv`
labels each run and task scope, and `TASK_GROWTH_COMBINATION_COVERAGE.csv` keeps
the additional diagnostic separate. Coverage counts logical pool exposures;
the independent physical cache audit deduplicates actual engine calls.

## Selected reward compensation and precision followup

`constructive-reward-v1` keeps the complete 36-gear timing_shared subdomain
generated by new source IDs 18203 and 19019, and changes only Thunderfury's
native weapon minimum/maximum damage by factors 0.5, 0.75, 1 and 1.25. It uses
the unchanged R3 research-variant executable. All eight original tasks,
policies and races remain fixed. The study completed 3,456 distinct calls and
1,769,472 battles at 512 fresh seeds per cell; shared old and Eskhandar-only
inputs are executed once across scale labels. These are research items, not
official items or a new admission algorithm.

`APPLIED_VARIANT_CHECK.json` verifies every distinct native output: 2,304 cells
apply a variant and 1,152 retain native items. Only weapon min/max differ in
the applied item metadata. Across 1,728 matched gear/context groups, action
cast means, resource summaries and aura summaries are identical across the
four scales. The largest per-seed affine DPS residual is 3.41e-13. This checks
the intended reward intervention; it does not itself establish admission.

After inspecting that study, `certificate-precision-v1` fixes gear
`d9ddad879238ea73` at scale 0.5 for Human and 0.75 for Orc. It measures each
selected witness and all 16 protected old configurations for eight tasks and
three policies. Eight independent blocks of 512 seeds begin at
409320001 + 10000 × block. The run completed 6,528 calls and 3,342,336 battles
with no engine errors. This is a selected 17-gear certificate support, not a
new complete-domain scan. `HIGH_PRECISION_CERTIFICATE_DESIGN.json` froze the
support and seeds before these outcomes. Original discovery caps, scales and
the protected old registry remain fixed; uncertainty analysis must preserve
the post-selection scope and cannot silently reanchor them.

## Independent physical audit

The final quiescent audit completed on 2026-09-24 at 19:39:54 UTC. It verified
**214,890 retained native invocations and 17,847,624 physical battles**, with
zero failed receipts, incomplete invocations, audit errors or pending runs.
All 13 native run archives pass; the two analysis-only protocols add no combat
calls. Human Warrior accounts for 107,454 calls / 8,924,040 battles and Orc
Warrior for 107,436 calls / 8,923,584 battles. No additional class coverage is
implied.

`artifacts/r4-foundational-discovery/INDEPENDENT_NATIVE_AUDIT.json` has SHA-256
`afc8fd4748234c7603e986d5d455e36b9b1e01005936b024c2a030526f3ed11e`.
The dated audit directory is `audit-20260924T193550703569Z`; its compressed
physical ledger has SHA-256
`7bc4069ce5ec84f0af1c7a6e894a283fe78f3e670a59a4c3f6a4582111b8a62f`.
The auditor checks raw output hashes and iteration counts, every archived
job/result/cache-key join, canonical job hashes, frozen binaries, archived
source and scientific metadata hashes, and final file signatures. It counts
distinct retained receipts, not logical pool/method reuse or unrecoverable
historical retries. Numerical ecological conclusions require their separate
analysis. An earlier read-only audit attempt was stopped to replace Python
threads with processes; its partial ledger and reason are retained, and no
native simulation was interrupted or rerun by that change.

Use `source scripts/env.sh` before commands. The original baseline launches with
`python -m wowfs.experiments.r4_native baseline --workers 64`; exact-source
resumption adds `--resume`. World runs use
`python -m wowfs.experiments.r4_worlds run --workers 64` and the same resume flag.
The actual tmux sessions are `wowfs-r4-foundational` and `wowfs-r4-worlds`.
A running frozen job's source must not be edited. Job-count status comes from
each run's `PROGRESS.json`; this document does not imply a running job finished.
