# Execution record

All Python/test commands were preceded by `source scripts/env.sh`; every output below is under `$WOWFS_WORK_ROOT`. Source working directory was `/work/Users/leiyo/GitHub/wow-forever-sustainability`. These entries summarize executed module commands; detailed stdout and per-phase source/configuration hashes are retained alongside the component receipts.

Preflight and user-supplied-input checks:

```bash
python scripts/audit_minimal_interface.py preflight --output "$WOWFS_WORK_ROOT/artifacts/minimal-interface-native-audit-2026-09-27"
python scripts/audit_minimal_interface.py register-supplement --output "$WOWFS_WORK_ROOT/artifacts/minimal-interface-native-audit-2026-09-27"
python scripts/audit_minimal_interface.py verify-supplement --output "$WOWFS_WORK_ROOT/artifacts/minimal-interface-native-audit-2026-09-27"
```

The first attachment was read in full with `cat`. Both user ZIP layers were inspected with Python `zipfile`, checked against absolute/parent-traversal/symlink entries, and extracted into the new `inputs/minimal-interface-2026-09-27/` directory. The initial and bundled plans were compared and are byte-identical. All 403 supplied frozen-input hashes passed; 24 path-only resealed interfaces were compared structurally to the server originals.

Phase A/B exhaustive reanalysis used `wowfs.experiments.mi_native` under tmux, with `--bundle` pointing to `artifacts/completion-oral-extension-2026-09-26/review-v2` and `--output` to the new run's `native/`. The identical command with `--resume` verified completed configuration/source/output hashes. Stdout: `logs/native.log`, `logs/native-resume-verification.log`, and `logs/native-tests.log`.

Phase B3 used `wowfs.experiments.mi_druid` under tmux `mi_druid_recheck`, with the same original bundle and output `druid/`, passing both saved files `TRIPLE_SOURCE_CERTIFICATE_v2.json` and `TRIPLE_INDEPENDENT_CERTIFICATES.json` from the imported latest manuscript. The full command and resume API distinction are preserved in `druid/REAL_COMMANDS.md`.

Phase C used tmux sessions `mi-theory-20260927` and `mi-theory-v2-20260927`. The first executed `python -m wowfs.experiments.mi_theory --out .../theory`; after the documented checker defect, corrected source executed the same defaults into `.../theory/v2`. Failed source, configuration and outputs are retained. `theory/v2/RESUME_CHECKS.json` contains successful identical resume and expected changed-source/configuration rejections.

Final tests, figures, integrity and assembly:

```bash
python -m pytest -q tests/test_mi_native.py tests/test_mi_druid.py tests/test_mi_theory.py
python -m wowfs.reporting.mi_report figures --run "$WOWFS_WORK_ROOT/artifacts/minimal-interface-native-audit-2026-09-27"
python scripts/audit_minimal_interface.py verify-inputs --output "$WOWFS_WORK_ROOT/artifacts/minimal-interface-native-audit-2026-09-27"
python -m wowfs.reporting.mi_report consolidate --run "$WOWFS_WORK_ROOT/artifacts/minimal-interface-native-audit-2026-09-27"
python -m wowfs.reporting.mi_report package --run "$WOWFS_WORK_ROOT/artifacts/minimal-interface-native-audit-2026-09-27"
```

The 14 final tests passed. Independently, 72 primary contract/order rows were checked by direct subset combinations, 300 arbitrary abstract response tables against 25,600 literal publications, and all 96 saved native contracts through `scripts/review_minimal_interface_native.py`. Their separate receipts preserve exact denominators. Vector PDF/SVG figures were generated with Matplotlib; the main PNG was visually inspected.

After sealing, the actual output ZIP is extracted into `artifacts/minimal-interface-actual-zip/`, and its contained replay wrapper is executed under tmux into `artifacts/minimal-interface-package-recheck/`. The external `PORTABLE_RECHECK.json` and ZIP receipt report that later verification independently; the sealed package itself is unchanged. No native simulator, paid API, remote push, public submission or manuscript build was executed.

That first portable attempt failed after the complete native replay because the wrapper compared integer histogram keys against their JSON string form. Both native summary files have SHA256 `901aee0c4590f3ec09f9deb1b1dd24b40405227e26f30cfe7e055cac8587f1be`. No inference change was needed. A separately assembled `artifacts/minimal-interface-review-v2/minimal-interface-native-audit-2026-09-27/` preserves the failed wrapper/log/receipt, with the corrected comparison and new packaging source hashes. Its actual ZIP extraction uses `minimal-interface-actual-zip-v2` and replay output uses `minimal-interface-package-recheck-v2`. Both sealed versions remain unchanged.
