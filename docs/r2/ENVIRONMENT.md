# R2 native engine recovered and executed

The original three engine locations are absent, but the actual community engine
has now been recovered and run. The initial location check alone did not identify
the cause. App task history subsequently showed that the previous project and its
work directory were deleted after a user cleanup request on 2026-09-24, on the same
host. That history also supplied the upstream repository and pinned revision.

The restored dependency is separate from the deleted project:

- Repository: https://github.com/sage3648/mythicsim-forever-engine
- Inherited engine and MIT attribution: https://github.com/wowsims/classic
- Commit: `17d75ccc8c67d027ae0088243ea3ee806d406847`
- Checkout: `WORK_ROOT/external/mythicsim-forever-engine-r2`
- Native binary: `WORK_ROOT/envs/r2-go/wowfs-native`
- Engine: the community MythicSim-maintained Forever fork, with explicit
  `RulesetForever`. This is not the official game client. Its equipment definitions
  retain Classic-era source data; using them under Forever engine rules does not
  establish that every item is an officially available Forever item.

Two 180-second Orc Warrior battles ran with the same equipment, talents, task,
APL, and integer seed. The effect-on configuration used the native Hand of Justice
item effect; its paired ablation disabled only that effect's registered callback,
retaining item stats, enchantments, and all other equipment effects. The observed
DPS values were 730.1209895 and 708.8888531. These two battles validate execution and
ablation plumbing; one seed does not establish an interaction finding.

The all-effects run was repeated with the unmodified upstream CLI. Its full result
matches the research runner after canonicalizing unordered action/aura/resource
metric lists; its event log is byte-identical. A separate 32-battle run without
debug logging took approximately 0.075 seconds in this environment. The bridge
validation subtotal is four native engine invocations and 35 physical battles.
Research batches are recorded separately and must be added to the final receipt.
The optional mechanism integration additionally ran two one-battle checks; its
zero-cooldown output exactly matches the native result after canonicalizing
unordered metric records. Its two unit tests cover shared cooldown admission,
iteration reset, unit isolation, batch-size accounting, zero cooldown, and
invalid parameters.

## Maintained integration and invocation

The maintained wrapper and explicit ablation helper are
`src/wowfs/simulator/native_main.go` and `native_ablation.go`. The build script
copies these into new, untracked files within the external engine snapshot;
no tracked upstream engine file is changed. With no ablation requested, the
wrapper executes the engine's native `core.RunRaidSim` directly. An unknown
item-effect or set-bonus selector raises an error. Ablation is a research
intervention, not an official native mechanism.

```bash
cd /work/Users/leiyo/GitHub/wow-forever-sustainability
source scripts/env.sh
export WOWFS_ENGINE_ROOT="$WOWFS_WORK_ROOT/external/mythicsim-forever-engine-r2"
bash scripts/native_build.sh
"$WOWFS_WORK_ROOT/envs/r2-go/wowfs-native" \
  -in "$WOWFS_WORK_ROOT/runs/r2-discovery/native-smoke/effect.input.json" \
  -out "$WOWFS_WORK_ROOT/tmp/r2-discovery/effect.replay.output.json"
```

The JSON input is an envelope containing a `request` in the engine's
`RaidSimRequest` protojson schema, `disable_item_effects` as integer IDs, and
`disable_set_bonuses` as objects with `name` and `pieces`. `request.simOptions`
must explicitly set `ruleset` to `RulesetForever`; the wrapper rejects Classic or
an omitted ruleset. The output uses the native `RaidSimResult` protojson schema,
including event logs, action metrics, resources, aura metrics, completed
iterations, and engine errors. Templates can be exported using `-template-out`
and `-engine-root`. The template copies the engine's p0.bis gear, dps_reck APL,
Forever buffs, Warrior test talent string and consumes; every resulting field is
saved in the input, including full raid buffs.

## Environment and evidence

The targeted location check observed hostname `j-12399673-job-0` and the `/work`
`wekafs` source ending in `Jobs/Terminal Ubuntu/12399673`. It checked only these
three supplied paths and relevant existing configuration/provenance:

- `/work/Users/leiyo/Github/game-budget-wow-forever`
- `/work/Users/leiyo/GitHub/game-budget-wow-forever`
- `/work/Users/leiyo/game-budget-wow-forever-work`

All three were absent. `WOWFS_ENGINE_ROOT` was initially unset, and
`/home/leiyo/.ssh/config` was absent. No whole-filesystem or credential search was
performed. The mount observation is not being used to infer that a different
server or a new mount is required; app history resolved the missing-path cause.
The cgroup provides 64 CPU equivalents (`cpu.max = 6400000 100000`) and
192000000000 bytes of memory.

The toolchain and dependencies are external: Go 1.26.8, protoc 29.3, and
protoc-gen-go 1.36.6. The Go archive was checked against its official download
metadata SHA-256. Build caches remain under `WORK_ROOT/cache/r2-discovery`.
The integration receipt is
`WORK_ROOT/artifacts/r2-discovery/latest/NATIVE_RUN_RECEIPT.json`; exact smoke
inputs, outputs and extracted event logs are in
`WORK_ROOT/runs/r2-discovery/native-smoke/`. Raw initial location diagnostics are
preserved in `WORK_ROOT/runs/r2-discovery/environment-2026-09-24/`.
