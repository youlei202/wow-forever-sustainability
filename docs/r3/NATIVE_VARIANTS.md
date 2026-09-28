# Native research variants and provenance

R3 uses a separate build of the community MythicSim Forever engine at commit
`17d75ccc8c67d027ae0088243ea3ee806d406847`. The executable is
`$WOWFS_WORK_ROOT/envs/r3-go/wowfs-native-variants`, SHA-256
`59f42b32e2c834321773188db482419238ae57556942f6f1825258722fc0aafe`.
The engine checkout is `$WOWFS_WORK_ROOT/external/mythicsim-forever-engine-r3-variants`.
R2 executables and frozen runs remain unchanged. `scripts/native_build_r3.sh`
maintains the patch; `src/wowfs/simulator/r3_variants.go` validates interventions.
The upstream source is https://github.com/sage3648/mythicsim-forever-engine.

The input envelope retains `request`, `disable_item_effects` and
`disable_set_bonuses`, and adds `research_variants`, an array with one specification
per original item ID. The engine changes actual gear or native event parameters
before character construction. It does not multiply final DPS. Original IDs,
weapon types, hand restrictions, class restrictions and set identities remain.
A variant identity hashes the full normalized specification; the physical cache
also hashes the complete input and executable. These variants are experimental
items, not claims about released game items.

| Fields | Semantics and validated scope |
| --- | --- |
| `item_id` | Required existing native item |
| `weapon_damage_scale` | Scales native min/max weapon damage |
| `weapon_damage_min`, `weapon_damage_max` | Absolute native weapon damage endpoints |
| `weapon_speed_seconds`, `speed_mode` | Positive swing interval; mandatory mode is `hold_base_dps` or `hold_damage` |
| `stats` | Named native stat enum values, replacing specified item stats |
| `proc_ppm` | Blood Talon 12795, Thunderfury 19019, Deathbringer 17068 |
| `periodic_damage_per_tick`, `tick_interval_seconds`, `number_of_ticks` | Blood Talon native periodic effect |
| `proc_damage` | Thunderfury primary Nature hit amplitude |
| `proc_damage_min`, `proc_damage_max` | Deathbringer native proc interval |
| `nature_resistance_reduction` | Accepted by the frozen receiver but **unsupported/no-op** in this pinned engine; excluded from scientific intervention claims |

When speed uses `hold_base_dps`, min/max damage first scale by the speed ratio;
`weapon_damage_scale` then supplies an independent DPS axis. Absolute min/max
cannot be combined with this mode or with the damage multiplier. Invalid,
ambiguous and unknown parameters reject before simulation. Amplitude-only
interventions preserve the native event registration and random-draw path,
including zero tick amplitude. Control parameters such as speed, PPM and tick
frequency are treated separately from reward amplitudes.

The Thunderfury Nature-resistance field is a native implementation limitation.
The eagerly registered attack-speed aura already owns label `Thunderfury`.
The later `GetOrRegisterAura` call reuses it without installing the intended
Nature-resistance `OnGain`/`OnExpire` callbacks. Source inspection and two native
runs with positive target Nature resistance (100), requested reduction 0 versus
25, confirm identical full canonical outputs and logs. The frozen engine retains
this behavior. Configured metadata must not be read as evidence that a reduction
was applied. See `runs/r3-gold/variant-nr-check/NR_NOOP_CHECK.json` under the work
root and the source audit in `MECHANISMS.md`.

Engineering verification comprises three Go unit tests and nine one-battle
native invocations: seven variant/default smokes plus the two resistance probes.
The default R3 input reproduces the R2 canonical result and complete event log
exactly. These engineering probes are not scientific effect estimates. Receipts,
inputs and outputs are under `runs/r3-gold/variant-smoke` and
`runs/r3-gold/variant-nr-check`; tests are logged under
`logs/r3-gold/variant_tests.log`.
