# Reproducing the completion-capacity study

The authoritative physical data are the six frozen runs under
`WOWFS_WORK_ROOT/runs/final-completion-capacity` and their native cache receipts.
The final tables, figures, manuscript and manifests are under
`WOWFS_WORK_ROOT/artifacts/final-completion-capacity`. Maintained source lives
in this repository. Earlier R1–R6 and decisive-value runs are read-only inputs
or background, and are not included in this stage's battle counts.

## Environment and native engine

The executed environment used Python 3.12.3, NumPy 2.5.3, SciPy 1.18.1,
PyYAML 6.0.3 and Matplotlib 3.11.2. `requirements.lock` records exact Python
versions; `pyproject.toml` records package requirements. Source
`scripts/env.sh` before Python or tests. It locates the environment beneath
`WOWFS_WORK_ROOT/envs/research`, directs caches and temporary outputs outside
the repository, and sets BLAS/OpenMP worker counts to one.

The native executable is the unchanged R3 research-variant binary:

```text
WOWFS_WORK_ROOT/envs/r3-go/wowfs-native-variants
SHA256 59f42b32e2c834321773188db482419238ae57556942f6f1825258722fc0aafe
upstream https://github.com/sage3648/mythicsim-forever-engine
commit 17d75ccc8c67d027ae0088243ea3ee806d406847
```

The build used Go 1.26.8 for linux/amd64, protoc 29.3, and the engine's pinned
`go.mod`/`go.sum` dependencies. The module declares Go 1.23.0 and an upstream
toolchain preference; the receipt, not that preference, identifies the compiler
actually used. `scripts/native_build.sh` builds the native bridge;
`scripts/native_build_r3.sh` reconstructs the research-variant hooks and binary
from the pinned checkout. These scripts modify the external engine worktree
and binary path. Run rebuilds only in a fresh work root, never over the frozen
study environment. The archived binary is the reference for byte-identical
execution; a rebuild in another path/toolchain may have different build
metadata and must not reuse receipts under the original binary identity.

The hooks replace real native item stats or supported weapon/effect parameters
before combat initialization. They do not multiply completed DPS. Only
`RulesetForever` is accepted. Equipment, race, class, talents, APL, pet options,
tasks, seeds and iterations are present in every input. Research alternatives
retain an existing item ID and are explicitly aliases, not new official items.

The upstream engine's `LICENSE` is MIT, copyright the wowsims team. Its separate
`tools/forever_talents/LICENSE.upstream` is also MIT and explicitly excludes
Blizzard game content from that grant. Preserve both notices when copying their
sources. Game data and the paper template are not represented as our original
content or covered by a new project license. The review package is internal;
it is not a public submission or an invented anonymous-author identity.

## Audit the retained evidence without new battles

From the original source checkout and work-root layout:

```bash
source scripts/env.sh
python scripts/audit_fc_native.py --workers 24 --require-complete
python scripts/audit_fc.py
pytest -q tests/test_fc_theory.py tests/test_fc_native.py tests/test_fc_results.py
```

The independent audit joins frozen jobs, inputs, binary/source/import hashes,
successful invocations, raw compressed outputs and iteration counts. Its
verified total is 22,032 calls and 8,181,632 battles, with no failed/incomplete
receipt or pending physical run. Analysis-only protocols, duplicate logical
cells and affine interpolation add zero battles. See [PROVENANCE.md](PROVENANCE.md)
and `INDEPENDENT_NATIVE_AUDIT.json` for the six-run ledger and seed overlap.
No benchmark is rerun by the audit commands.

The review archive contains `source/`, frozen `runs/`, `native_cache/`, the
native binary/source/notices, inputs, artifacts, and a per-file SHA-256 manifest.
It omits repeated copies of the same binary from individual run folders. To
reconstruct the original layout, put native caches under
`WOWFS_WORK_ROOT/cache/final-completion-capacity/native`, put the provided binary
at the path above and at each physical run's `native.frozen`, and restore the
native source under `external/mythicsim-forever-engine-r3-variants`.

Frozen JSON receipts contain the original absolute work-root paths. Use that
directory layout in an isolated reproduction environment for unmodified replay.
A relocated workspace requires an explicitly recorded derived path mapping;
do not edit the frozen evidence or claim that an altered manifest still has
the original hashes. A manifest/CRC check alone needs no relocation or native
execution.

## Analysis and figure reconstruction

`fc_old_analysis.py` reads the complete old domains and computes current
frontiers, old-source relevance, exact initial portfolios, taskwise endpoint
fits, and completion spectra. `fc_planner.py` reads those old measurements only
and freezes all future amplitudes, partner combinations, admission masks and
conditional predictions before confirmation. The first release need not have
a smaller physical amplitude than later releases.

`fc_results.py` reads the frozen main confirmation inputs/results. It checks
fresh zero/high native anchors against every executed checkpoint before using
affine interpolation. The full old/new configuration library is reoptimized
under the frozen mask. All five nonaffine Warlock contexts use physically
executed robust-path crosses; their exact endpoint paths are `not_run`.
`fc_behavior_validation.py` independently verifies the original Warrior damage
and resource partition at every executed Warrior checkpoint.

Clean analysis workspaces may run:

```bash
source scripts/env.sh
python -m wowfs.experiments.fc_old_analysis
python -m wowfs.experiments.fc_planner
python -m wowfs.experiments.fc_results
python -m wowfs.experiments.fc_behavior_validation
python -m wowfs.experiments.fc_finite_reference
python -m wowfs.experiments.fc_continuation
python scripts/audit_fc.py
python -m wowfs.experiments.fc_report
python -m wowfs.experiments.fc_publication
bash scripts/build_fc_paper.sh
```

The physical runs and their required artifacts must already be restored.
The finite reference checks arbitrary order within the frozen candidate union;
the continuation analysis bounds remaining same-family updates after a retained
dense history. Both consume completed data and execute zero new battles.
Old-ecology and main analysis scripts refuse to overwrite an existing frozen
analysis directory. Reproduce in a clean derived workspace or retain an explicit
new analysis revision. The stored per-run source snapshots take precedence when
reconstructing an original protocol hash; maintained source includes subsequent
documented analysis corrections. The paper build uses Tectonic 0.17.0 and the
provided AISTATS template under `external/AISTATS2027PaperPack`.

The main outputs are `NATIVE_CAPACITY_RESULTS.csv` (round-level decisions),
`SEQUENCE_CAPACITY_SUMMARY.csv` (tested prefixes and conditional bounds),
`RACE_CLASS_56_RESULTS.csv`, `CLASS_FACTION_RESULTS.csv`, `FACTION_SUMMARY.csv`,
`LEGACY_RELEVANCE.csv`, `PORTFOLIO_COMPLEXITY.csv` and `COSTS.csv`. Main faction
report tables additionally expose predicted capacities separately from observed
prefixes. Equal-class faction aggregation excludes unassessed strata with an
explicit denominator; it does not replace missing results with zero.

## Re-executing physical inputs

The exact request for each battle batch is stored in its native cache
`input.json`, with `invocation.json`, `summary.json` and `output.json.gz`.
A selected request can be replayed to a new scratch output using the archived
binary's `-in` and `-out` flags with `GOMAXPROCS=1`. Never overwrite the archived
output or count that replay as part of the original receipt.

For a complete new reproduction, restore the protocol/configuration/input
artifacts in a fresh work root and execute, in order:

```text
python -m wowfs.experiments.fc_support
python -m wowfs.experiments.fc_calibration --workers 32
python -m wowfs.experiments.fc_mechanisms --workers 32
python -m wowfs.experiments.fc_capacity baseline --workers 32
python -m wowfs.experiments.fc_old_analysis
python -m wowfs.experiments.fc_planner
python -m wowfs.experiments.fc_confirmation --workers 32
python -m wowfs.experiments.fc_mechanism_capacity --workers 32
```

The two mechanism modules freeze their own grids and prospective design before
native calls. All commands retain their declared seeds/sample counts; there is
no outcome-dependent resampling. Resume requires identical configuration,
source, imported inputs and binary. A different environment is a new run,
not permission to rewrite an old one. The main and mechanism confirmations share
seed values and are not independent replications of one another.

## Formal and statistical boundaries

The supplied R5 theory input is preserved verbatim with SHA-256
`a2160fda7467f3618797c91f2257f6dac39b284804774cf0751eac1d92cd8dd2`.
Its unique-repair closure and frontier-neutral behavior-packing theorems are
different from the new positive-value completion-band calculation. The latter
requires an explicit incoming amplitude domain, complete mixing, endpoint
conventions and separate legacy checks. `THEORY.md`, exact rational tests and
`PRIOR_WORK_DELTA.md` state those conditions; abstract checks add no native
coverage.

Main confirmation contrasts use the fixed initial strongest old configuration
as the population reference for cap, gain and relevance. Paired Student-t
intervals with a finite Bonferroni family account for both old and new
optimization. They are approximate Monte Carlo intervals within a context, not
distribution-free or jointly simultaneous across 56 contexts. Safety against
the literal 128-battle development numeric cap is retained separately. The
mechanism study's original cap definition and its separately labeled reference
sensitivity must not be merged silently with the main estimand.

The strongest observed main result is the robust value/retention prefix pattern
4/1/4/3 in 51 validated affine contexts. Conditional theoretical endpoint
capacities and statistical support for their upper bounds are separate outputs.
Failed endpoint attempts do not prove zero optimal capacity. Original Warrior
behavioral D fails as a mean diagnostic; other classes have a different physical
damage diagnostic and no original-D assessment. Three genuine mechanism grids
were executed, but no complete prospective mechanism path passes all reported
joint confidence checks. Thus the study does not establish the unrestricted
full-objective, all-mechanism theorem or exact live-game expansion capacity.
