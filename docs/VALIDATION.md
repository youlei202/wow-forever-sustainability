# Validation — 2026-09-28

The maintained repository publishes executed notebooks with embedded figures and tables. Manuscript files and the frozen input archive are not distributed through the repository or releases. Reexecution requires the locally supplied unchanged archive (or its verified external extraction); viewing the committed notebook outputs does not.

## Current code-only repository with executed notebooks

The complete reproduction ran from `/tmp` after removing `paper/` and its dependency from the reporting workflow. The output directory is `$WOWFS_WORK_ROOT/artifacts/paper-reproduction/code-only-rendered-20260928`.

- **298 tests passed in 24.94 seconds**, including the source-package exclusion and notebook-output preservation checks.
- All **5 notebooks executed successfully**, with 45 code cells executed sequentially and no error outputs.
- The executed notebooks were copied into `notebooks/` with **8 embedded PNG figures and 33 rendered tables** (24 HTML tables and 9 Markdown tables).
- Notebook 01 includes all 4 composite manuscript figures (8 panels); notebook 02 includes all 15 numbered tables and 2 unnumbered tables.
- Notebook content and outputs are English. A final Markdown-only instruction in notebook 00 was updated to require retaining outputs; its executed code and results are unchanged.
- The replay passed all registered scientific comparisons using the unchanged private external inputs. It ran no new native battles or hardware timing measurements.
- Manuscripts and private archives are excluded from the repository and the source-packaging command. The previous Git history was backed up locally before replacement; old releases and tags containing manuscript material were removed from GitHub.

The run's `REPRODUCTION_REPORT.json`, `RUN_CONFIG.json`, and `pytest.log` record the result, dependencies, input/source hashes, and test output. Separate exported figures, tables, and manuscript staging files remain in the external work directory.

## Historical initial reproduction

The initial reorganized source version was run from `/tmp`, outside the repository:

```bash
source /path/to/repository/scripts/env.sh
python /path/to/repository/scripts/reproduce/reproduce_all.py \
  --output "$WOWFS_WORK_ROOT/artifacts/paper-reproduction/final-20260928-v2"
```

- **297 tests passed** in 25.38 seconds. This includes 15 new scientific-core tests and 17 input/provenance tests.
- All **5 notebooks executed successfully**, top to bottom, in separate kernels.
- Notebook 01 contains **4 rendered paper figures** (8 panels), with PNG/SVG/PDF exports.
- Notebook 02 contains **17 rendered HTML tables**: 15 numbered manuscript tables and 2 unnumbered tables, with CSV/HTML exports.
- At the time of this historical run, the 54 imported manuscript source files were byte-identical to the frozen handoff. Those imports have since been removed from the repository.
- All 9 original manuscript replay/generation commands returned zero.
- Recomputed 16 base catalogues / 128 registered queries: **42 YES / 76 NO / 10 UNKNOWN**.
- Recomputed retention ablation: **69 of 76 exclusions** become feasible without retention.
- Recomputed full base powersets: **351 / 3 / 0** certified misses at orders 1 / 2 / 3.
- All 96 dependent contracts / 184,320 target subsets matched the archived scientific outputs.
- Independent Druid replay: all three pairs YES, triple NO, all 32 physical configurations cap-safe. Minimum cap lower margin: 0.6601399294 DPS.
- Universal-construction replay: **2,466 checks**, with expected out-of-guarantee boundary counterexamples retained separately.
- Input archive, individual inputs, scientific comparison artifacts and generated output hashes were verified.
- No new native battles, no new alpha, no new historical solver timing measurements.

The complete receipt is `$WOWFS_WORK_ROOT/artifacts/paper-reproduction/final-20260928-v2/REPRODUCTION_REPORT.json`. Executed notebooks are in its `notebooks/`; generated current-paper plots and tables are in `paper-assets/notebook-figures/` and `paper-assets/notebook-tables/`. That historical revision kept notebook sources without outputs; the current repository intentionally tracks successful execution outputs for readers.

Python 3.12.3; NumPy 2.5.3; SciPy 1.18.1; Matplotlib 3.11.2; pandas 3.0.6. Full dependencies are in `requirements-reproduce.lock`; run configuration records the complete installed distribution versions and source/input hashes.

Original TikZ/PDF typesetting was not compiled because the TeX toolchain is not installed. All numerical checks and notebook figure/table regeneration passed; exact typography is a separate optional build. Native observation generation still requires the archived simulator.

At the time of this historical validation, no pre-existing research file had been removed or moved. The old README was preserved in `docs/history/README_before_reorganization.md`, and manuscript sources were copied into `paper/current/`. The entire `paper/` directory has since been removed from the maintained repository; those historical paths do not describe the current layout.

## Historical English-only repository revision

The English-only revision translated all maintained repository prose into English, including the README, historical research notes, notebook explanations and comments, and report-generation templates. A scan of all 522 tracked files, decoded JSON/notebook strings, and Python string literals found no remaining Chinese characters or fullwidth punctuation. Filenames remain ASCII. The frozen input archive was preserved byte-for-byte.

The complete reproduction command was rerun from `/tmp` with output at `$WOWFS_WORK_ROOT/artifacts/paper-reproduction/english-20260928`. All **297 tests passed in 26.76 seconds**, and **all 5 notebooks executed successfully**. Both notebook source text and executed outputs passed the English-language scan. The numerical replay matched the same archived scientific results.

Notebook code ASTs remained identical. Python generator ASTs remained identical apart from translated string constants; paths, f-string expressions, numerical constants, and computational structure were preserved. Historical document translations retained the original numeric-token counts and scientific caveats.

The historical English reproduction release originally included the frozen archive. That distribution has been withdrawn because it included manuscript material. The current code repository provides rendered notebooks directly; its reproducibility instructions require a locally supplied archive for reexecution.
