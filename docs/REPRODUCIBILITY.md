# Viewing and reproducing the experiments

Open the numbered notebooks in `notebooks/` to view the executed results, figures, and tables directly. Their cell outputs are intentionally committed; viewing them requires no archive or local environment.

For reexecution, follow the installation instructions in the root README and supply the unchanged frozen input archive locally. The repository does not contain a `paper/` directory, manuscript source, or manuscript PDF, and the frozen archive is not hosted in its releases. The figure/table mapping refers to the 2026-09-27 handoff manuscript inside the external frozen bundle; the later minimal-interface audit is shown separately in notebook 04.

```bash
source scripts/env.sh
# Supply the original frozen archive locally:
export WOWFS_REPRO_ARCHIVE=/path/to/final-v2/WOW_MINIMAL_INTERFACE_NATIVE_REVIEW.zip
python scripts/reproduce/reproduce_all.py
```

This verifies dependency availability and input hashes, runs the full tests, then executes every numbered notebook in a fresh kernel using the current interpreter. It writes a timestamped external directory under `$WOWFS_WORK_ROOT/artifacts/paper-reproduction` with executed notebooks, regenerated plots/tables, scientific audits, pytest.log and REPRODUCTION_REPORT.json. A failed cell produces FAIL, traceback and the partial notebook.

The script resolves its own location and accepts absolute --archive, --inputs and --output paths, so it works outside the repository. Use --resume only for identical code, inputs and dependencies; otherwise choose a fresh output. --prepare-only only verifies/extracts data. --skip-tests is explicit and recorded.

Interactive: `make prepare`, then `make notebooks`. Generated standalone output defaults to `$WOWFS_WORK_ROOT/artifacts/paper-reproduction/interactive`; set `WOWFS_REPRODUCTION_ROOT` for a fresh interactive run after edits. Reexecution runs notebook cells top to bottom in fresh kernels. The committed outputs are a recorded execution for readers; use the reproduction report to distinguish a new successful replay from that saved display.

| Paper result | Source code | Input | Output / notebook | New simulator? |
|---|---|---|---|---|
| Exact completion, supporting core, conflicts | co_exact.py, co_reference.py, test_reproducible_core.py | Small deterministic tables | 00 and test log | No |
| Maximal target queries, arbitrary-order construction | mi_theory.py, mi_native.py | Mathematical examples and native events | 00/04 | No |
| All current figures and tables | reporting/paper_assets.py, original manuscript generators | manuscript/WoW_Future_Targets_AISTATS2027/evidence | 01/02; paper-assets | No |
| 16 base catalogues, 128 queries, 42/76/10 | co_review_check.check_bundle | review/review-v2/data/native compact moments | 03; science | No |
| Retention ablation, 69/76 | Same checker and original obligation analysis | Sealed bundle obligation/native data | 03 and paper table | No |
| 0.5%, 1%, 2%, 5% tolerance | verify_secondary, co_native_sensitivity.py | Sealed secondary events and moments | 01–03 | No |
| Exact-solver runtime comparison | co_benchmark_report.py, original benchmark checks | Saved benchmark runs | 02/03 | No; fresh timing is separate |
| Full-target audit, 351/3 low-order misses | mi_native.run | Entire sealed review-v2 | 04 | No |
| Druid pairs YES, triple NO; cap vs retention | mi_druid.run | Native moments + gold certificate JSONs | 01/04 | No |
| New combat observations | Archived simulator orchestration | Engine, patches, configurations, seeds | Not run | Yes |

Exact asset labels, captions and paths are in [PAPER_MAP.md](PAPER_MAP.md); algorithms in [CODE_MAP.md](CODE_MAP.md); archive identity and inference assumptions in [DATA.md](DATA.md).

Notebook figures reconstruct data/formulae using Matplotlib. They are not pixel-identical TikZ typesetting. Original plot sources and generated LaTeX tables are available only in the locally supplied external bundle and external run directory. Building the exact full manuscript PDF there needs TeX; no manuscript is published with this code repository.

The 3 pairwise missed targets are two minimal triples and their four-item union, not three minimal triple obstructions. Target queries remain within the measured catalogue. Possible witnesses are not certified feasible releases. UNKNOWN, failed certificates and frozen denominators remain visible.

The `paper/` directory has been removed from the maintained repository. The prior README is preserved in `docs/history/README_before_reorganization.md` as historical documentation; its old manuscript paths and distribution instructions do not describe the current workflow. Scientific module paths are retained to preserve archived references. No locally supplied frozen input or historical run is edited.

See [VALIDATION.md](VALIDATION.md) for the actual delivered run. Missing or failed reports are never successful reproduction.
