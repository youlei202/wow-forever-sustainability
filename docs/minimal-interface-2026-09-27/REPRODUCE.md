# Reproduce the audit

Use an external work root. The archive includes the complete original `review-v2.zip`, the user-supplied handoff ZIP, maintained code and tests, all audit outputs, and the failed first theory checker. No native executable or battle is needed. Python versions are recorded in `requirements-recheck.txt`; environments, extraction, logs and caches belong under `WOWFS_WORK_ROOT`.

After extracting `WOW_MINIMAL_INTERFACE_NATIVE_REVIEW.zip`, set `AUDIT_PACKAGE` to its `minimal-interface-native-audit-2026-09-27` directory. Configure caches first:

```bash
export WOWFS_WORK_ROOT=/absolute/external/work/root
source "$AUDIT_PACKAGE/scripts/env.sh"
export PYTHONPATH="$AUDIT_PACKAGE/code:$AUDIT_PACKAGE/tests"
export GOMAXPROCS=1
python -m pytest -q "$AUDIT_PACKAGE/tests/test_mi_native.py" "$AUDIT_PACKAGE/tests/test_mi_druid.py" "$AUDIT_PACKAGE/tests/test_mi_theory.py"
```

Use tmux for the full replay (one worker), with a new output directory outside the package:

```bash
python "$AUDIT_PACKAGE/scripts/recheck_minimal_interface_package.py" \
  --package "$AUDIT_PACKAGE" \
  --output "$WOWFS_WORK_ROOT/artifacts/minimal-interface-portable-replay"
```

The wrapper verifies every package-manifest file, safely extracts both frozen input archives, replays all 96 native contracts and all 184,320 target queries, independently reconstructs the Druid moments and prior certificate margins, and repeats all corrected theory/symbolic checks. It compares scientific outputs against saved results. Python reads of the original repository and original data roots are blocked, and module locations must resolve inside the extracted package. `PORTABLE_RECHECK.json` records the result. It does not rebuild or modify the manuscript.

The theory module's original absolute proof-note location is retained as provenance. The wrapper relocates only the module's `PROOF_PATH` to the extracted byte-identical proof PDF before running. This creates a fresh configuration with the relocated path; it does not edit the module or pretend that a differently located run has the original configuration hash.

Append `--resume` to continue exactly the same replay configuration. Each analysis retains checkpoints and checks source/input/configuration identity; use a new directory after changing any configuration or source. Preserve failed runs. A completed native/theory/druid run returns its saved result on matching resume instead of replacing frozen outputs.

For a fast read-only independent check of the saved analysis, with the same cache setup:

```bash
python "$AUDIT_PACKAGE/scripts/review_minimal_interface_native.py" \
  --root "$AUDIT_PACKAGE" \
  --output "$WOWFS_WORK_ROOT/artifacts/minimal-interface-saved-output-review.json"
```

The archive's sibling `WOW_MINIMAL_INTERFACE_NATIVE_REVIEW.zip.receipt.json` records the actual ZIP hash and every inner-file hash check. The final actual-archive replay is stored separately at `$WOWFS_WORK_ROOT/artifacts/minimal-interface-package-recheck-v2/PORTABLE_RECHECK.json`, so the already sealed archive is never edited to insert a later receipt. Missing or interrupted replay results are not a PASS. The first wrapper's integer-key/JSON-string-key comparison failure is retained under `packaging-failures/`; its reproduced scientific JSON was byte-identical. The corrected wrapper compares serialized JSON on both sides. Both archives are preserved.

The corrected theory evidence is at `theory/v2/`. The top-level theory JSONs are exact copies of v2; `theory/UNIVERSAL_CONSTRUCTION_CHECKS.json` is the deliberately retained failed v1. Never combine the two versions' success counts. The original run's resource quota was 64 CPU equivalents; this audit used one worker per analysis and at most four concurrent task workers, GPU=0, new-native-calls=0 and additional-alpha=0.
