# R3 reproduction and evidence map

Source is `/work/Users/leiyo/GitHub/wow-forever-sustainability`; runtime state is
`/work/Users/leiyo/wow-forever-sustainability-work` (`WOWFS_WORK_ROOT`).
Always source `scripts/env.sh` first. The external `envs/research` environment
contains the pinned research dependencies. Go/protoc and the pinned engine
checkouts remain outside the repository. See NATIVE_VARIANTS.md and the R2
environment documentation for engine/toolchain provenance.

The R3 physical stages are immutable directories under `runs/r3-gold`:

| Run | Native cells | Iterations/cell | Purpose |
|---|---:|---:|---|
| causal-factorials-v1 | 576 | 128 | Effect registration factorials |
| phase-grid-v1 | 24,192 | 32 | DPS/speed discovery |
| phase-confirmation-v1 | 3,840 | 1,024 | Once-selected fresh confirmation |
| affine-probe-v1 | 48 | 128 | Path/control and affine diagnostic |
| affine-calibration-v1 | 864 | 128 | Three anchors per context |
| affine-transfer-v1 | 3,712 | 128 | Same/shifted control and fresh seeds |
| sequences-v1 | 23,040 | 128 | Two frozen 20-wave candidate pools |

These sum to 56,272 cached calls and 8,321,024 battles. Nine uncached
engineering battles make the total 56,281 calls and 8,321,033 battles.
Atlas reuse of 35,928 R2 cells adds no new battles. Simulated variant items
retain native IDs with their complete parameter specification in the request;
their identities and cache keys distinguish their physics.

Every run retains PROTOCOL.json, JOBS.json, FREEZE_TIME.json, source snapshot,
native.frozen, PROGRESS.json and RESULTS.json. Cache entries retain input.json,
invocation.json, summary.json and output.json.gz, keyed by the binary and whole
request hash. Completed frozen runs must not be overwritten. `r3_native.run_jobs`
checks exact inputs, binary and source hashes for resume; current maintained
source may have changed after an earlier freeze, so it is not automatically
valid for resuming that older run. Use its archived source and executable.

On the existing work root, analysis can be regenerated without combat:

```bash
source scripts/env.sh
python -m wowfs.experiments.r3_atlas
python -m wowfs.experiments.r3_phase_analysis
python -m wowfs.experiments.r3_phase_confirmation_analysis
python -m wowfs.experiments.r3_affine_analysis
python -m wowfs.experiments.r3_sequence_analysis
python -m wowfs.experiments.r3_transfer_metrics
python scripts/audit_r3_native.py
python scripts/verify_r3_snapshots.py
python -m wowfs.reporting.r3_report
bash scripts/build_r3_paper.sh
python scripts/package_r3.py
python -m pytest -q
```

The affine comparison command uses the existing frozen calibration/transfer
artifacts; original per-seed fitting is archived with those physical runs.
The report depends on all analysis tables and the completed physical audit.
These listed analysis commands create no new combats.
The manuscript uses the already installed official AISTATS template in
preprint mode; it is unsubmitted and carries no invented identity.

The ZIP is a compact review package, not the full multi-gigabyte combat cache
or external environment. It includes source, complete derived tables, frozen
scientific protocols, hashes, a physical-cache ledger and selected original
native inputs/outputs (including primary interior/zero-headroom/canonical
witnesses, causal contrasts and affine traces). Full raw reanalysis requires
the retained work root. Selected-evidence entries are references to already
counted physical calls, not extra battles. Local absolute paths in receipts
identify original provenance; the selected_evidence directory is portable.

Analysis corrections are disclosed in SEQUENTIAL_ANALYSIS_PROTOCOL.json.
The first policy replay gave some baselines only the fitted cap while the
constrained policy also used observed current P; final baselines receive the
same observed current P constraint. Superseded results remain under
analysis_versions. This is an exploratory comparison, not a prospectively
frozen algorithmic-superiority result. The native candidate pools, seeds,
frozen behavior threshold and initial cap are unchanged.

Power intervals are approximate simultaneous Student-t mean intervals where
explicitly declared. Behavior has aggregate means only. Structural coupled-seed
affine tests and independent-seed mean prediction are separate panels. Do not
count unexecuted classes, randomized mixtures or live-server validation as
completed coverage.
