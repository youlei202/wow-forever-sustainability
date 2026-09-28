# Reproducing R6

Use `source scripts/env.sh`. All runs, inputs, caches, compiled figures and
archives live in `WOWFS_WORK_ROOT`; maintained source stays in this repository.
The formal R5 packet is imported under `inputs/r5-theory/` and hash checked by
the R6 native wrapper. The native binary is the unchanged R3 variants binary.

Do not rerun freeze/execute commands against completed run names: immutable
protocols reject changed sources or inputs. Use archived per-run source and a
new run ID for genuinely new physical replication. The package contains the
full R6 jobs/results and raw native receipts; frozen executable hashes identify
the external compiled binary without shipping redundant copies.

Read-only analysis commands:

```bash
source scripts/env.sh
python -m wowfs.experiments.r6_original_domain
python -m wowfs.experiments.r6_cascade_analysis
python -m wowfs.experiments.r6_neutral_analysis
python -m wowfs.experiments.r6_capacity_precision analyze
python -m wowfs.experiments.r6_final_control_audit
python -m wowfs.reporting.r6_figures
python scripts/audit_r6_native.py --require-complete
pytest -q
python scripts/package_r6.py
```

The final capacity analysis uses only `capacity-precision-v1` observations.
`CAPACITY_CONFIRMATION.json` and `*_INITIAL.csv` preserve the earlier unresolved
capacity panel; do not replace final tables by rerunning its `analyze` command.
Neither set of design parameters is adjusted after its fresh observations.

Physical run order and scope:

1. `stress-calibration-v1`: three native anchors plus one held-out point;
   domain and amplitudes frozen first, 4×2,048 battles.
2. `neutral-development-v1`: frozen primary old/new design, 2×2,048.
3. `neutral-confirmation-v1`: old/new, 8×1,024 seeds each.
4. `native-gate-probe-v1`: 12 legal gear pairs and two set-off controls,
   14×2,048; no source/tolerance retuning after failed cascade premises.
5. `capacity-confirmation-v1`: four unchanged-region sequences;
   368 distinct calls×512; first pass, with disclosed partial B seed overlap.
6. `capacity-precision-v1`: identical four sequences, 736 distinct
   calls×2,048 on wholly disjoint fresh seed ranges; final inference.

Logical rows can exceed physical calls when several threshold sequences share
their first physical design. The native dispatcher evaluates identical requests
once and restores each row's logical metadata. Distinct physical calls can also
share seed observations; the independent audit reports that separately.

The six-inequality admission branch is a fixed grammar. Its legacy branch
retains the old anchor unchanged. The increasing item definitions/archive are
not counted as a constant-size catalogue. Native aliases remain existing
item IDs plus parameter overrides, and are never treated as official new IDs.

The imported `check_theory.py` normally rewrites a sibling checks file. R6
instead imports and invokes its verification functions, saving the results as
`R5_CHECKS_RERUN.json`, to preserve the supplied packet unchanged.
