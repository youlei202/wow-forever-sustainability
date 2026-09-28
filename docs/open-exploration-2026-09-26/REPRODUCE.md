# Reproduce the open exploration

Maintained source: `/work/Users/leiyo/GitHub/wow-forever-sustainability`.
Runtime root: `/work/Users/leiyo/wow-forever-sustainability-work`.
Campaign: `artifacts/open-exploration-2026-09-26/campaign-v1` under that root.
The source repository had no initial commit or remote; the campaign branch is
`codex/open-exploration-2026-09-26`. Existing staged and untracked work was preserved.

## Read-only reproduction of confirmation

Use the existing research environment and configure every cache before Python:

```bash
cd /work/Users/leiyo/GitHub/wow-forever-sustainability
source scripts/env.sh
python -m pytest -q tests/test_oe_*.py
python -m wowfs.experiments.oe_confirmation \
  --batch "$WOWFS_WORK_ROOT/artifacts/open-exploration-2026-09-26/campaign-v1/batches/confirm-v2" \
  --manifest "$WOWFS_WORK_ROOT/artifacts/open-exploration-2026-09-26/campaign-v1/CONFIRMATION_MANIFEST_V2.json" \
  --output "$WOWFS_WORK_ROOT/artifacts/open-exploration-2026-09-26/campaign-v1/analysis/confirmation-reproduction-v1"
python -m wowfs.experiments.oe_claim_decisions \
  --manifest "$WOWFS_WORK_ROOT/artifacts/open-exploration-2026-09-26/campaign-v1/CONFIRMATION_MANIFEST_V2.json" \
  --analysis "$WOWFS_WORK_ROOT/artifacts/open-exploration-2026-09-26/campaign-v1/analysis/confirmation-reproduction-v1" \
  --output "$WOWFS_WORK_ROOT/artifacts/open-exploration-2026-09-26/campaign-v1/analysis/confirmation-reproduction-v1/DECISIONS.json"
```

Output directories must be new. Existing frozen analyses reject replacement.
The manifest audits current analysis-source hashes, original physical reference
identities, binary, all cells, N, seed ordering and the pre-outcome freeze link.
If scientific source changes later, use the original source snapshot in
`batches/confirm-v2/source/` with its required configurations and environment;
do not edit the snapshot to make a check pass. Keep the original manifest paths
and package identity guards consistent.

The primary method uses raw paired samples. `compact_moments/` in the review
archive is a secondary, small sufficient-statistics export for checking linear
contrasts: means, covariance, N, configuration/task order and reference IDs.
For a contrast with coefficient vector c, its sample mean is c' m and estimated
standard error is sqrt(c' Cov c / N). Use the exact critical value and contrast
family from the frozen analysis. Covariance export is derived data, not new
simulation. Tiny floating-point residuals should not be called new mechanisms.

## Native inputs, binary and recovery

The actual executable is
`$WOWFS_WORK_ROOT/envs/r3-go/wowfs-native-variants`, SHA256
`59f42b32e2c834321773188db482419238ae57556942f6f1825258722fc0aafe`.
The engine checkout is
`$WOWFS_WORK_ROOT/external/mythicsim-forever-engine-r3-variants`, based on commit
`17d75ccc8c67d027ae0088243ea3ee806d406847` plus the recorded local bridge/variants.
Do not substitute a different executable and call it the frozen experiment.
Each batch contains `native.frozen`, `JOBS.json`, `PROTOCOL.json`, source snapshot
and freeze timestamp. Every successful physical cell has input JSON, gzip raw
output, native output hash, sample summary and immutable attempt receipts in its
indexed cache directory. These large files remain outside the source tree.

The executed native command was:

```bash
python -m wowfs.experiments.oe_runner --phase confirm \
  --config "$WOWFS_WORK_ROOT/artifacts/open-exploration-2026-09-26/campaign-v1/requests/confirm-v2.json" \
  --run-root "$WOWFS_WORK_ROOT/artifacts/open-exploration-2026-09-26/campaign-v1" \
  --workers 48 --max-wall-hours 24
```

An interrupted run can use the identical command with `--resume` while the
original cumulative campaign deadline remains open. Resume checks source,
configuration and binary hashes and verifies cached output against its summary.
A completed run does not need another native execution. An independently changed
design belongs in a new batch with an explicit statistical status; the original
alpha budget is fully spent and cannot be reset.

## Development, policy probes and exact search

Every batch's `PROTOCOL.json`, request config and `JOBS.json` identify its
physical domain. `oe_worlds.py` generates the 96 research settings;
`oe_catalog_worlds.py` generates 12 actual-item controls. They have distinct job
constructors because catalog fixed equipment is part of the physical input.
Use the recorded constructor, not an approximately similar setup.

`oe_planning.py` analyzes development means, with explicit candidate limits.
`scripts/oe_targeted_capacity.py` restores full candidate domains for selected
challenges. `oe_baseline_challenge.py` and `scripts/oe_full_baseline_challenge.py`
challenge apparent gains with minimum qualifying increments and stronger simple
baselines. Their manifests pin analysis inputs and script versions. Full solver
outputs are in the campaign analysis directory; compact summaries are packaged.
The 550 independent exact-oracle comparisons and separate wide-batch checks are
under `checks/theory/`. Solver timeouts retain lower/upper direction and are not
rewritten as exact outcomes.

The 73-test confirmation-source suite passed before sampling. Independent
audits also reread raw native outputs, cache summaries, receipts and seed blocks.
See `REAL_COMMANDS.md` and `checks/` for actual execution evidence.

## Scope

This is a finite native-executable study, with actual catalog controls and
clearly tagged research stat variants. It is not live-server telemetry. Fixed
native policies and two equal-weight tasks do not cover all possible play.
Unsupported PvP/healing/survival behavior and unexecuted task-creation branch C
remain explicitly not run. Known faction/acquisition inconsistencies in some
development presets are preserved and flagged; the selected confirmation
settings use clean checked equipment. Neither new racial counts nor millions
of seeds create new independent mechanisms.
