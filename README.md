# Preserving Future Design Options in Growing Systems — The World of Warcraft: Forever Problem

How can a system add new rewards under a fixed level and power cap while keeping old rewards useful? This repository contains exact completion algorithms, target-family representations, statistical certification, and native WoW experiments for *Preserving Future Design Options in Growing Systems — The World of Warcraft: Forever Problem*.

This is a code repository: manuscript sources, manuscript PDFs, and manuscript-containing archives are kept outside GitHub. The notebooks include saved, executed outputs, so every figure and table can be viewed directly on GitHub without running Jupyter. The subsequent minimal-interface audit is identified separately from the current paper results.

## Start with the notebooks

| Notebook | Contents |
|---|---|
| [00_model_and_completion](notebooks/00_model_and_completion.ipynb) | Rational model, support deletion, conflicts, completion witnesses, and a third-order obstruction |
| [01_paper_figures](notebooks/01_paper_figures.ipynb) | All 4 composite figures in the current manuscript, comprising 8 panels |
| [02_paper_tables](notebooks/02_paper_tables.ipynb) | All 15 numbered tables and 2 unnumbered tables |
| [03_native_certification](notebooks/03_native_certification.ipynb) | Certification, retention ablation, tolerance analysis, and saved runtime statistics recomputed from compact moments |
| [04_target_interface](notebooks/04_target_interface.ipynb) | Subsequent full-target audit, 351/3 low-order misses, independent Druid replay, and construction checks |

The committed notebooks contain embedded figures and tables. Reexecution writes a fresh set of notebooks, figures, tables, logs, and reports to an external work directory. Matplotlib redraws the figures from the original values; the original TikZ sources are preserved in the private external input bundle. See [PAPER_MAP.md](docs/PAPER_MAP.md) for every figure and table's identifier, generator, and input data.

## Installation and reproduction

No installation is needed to view the committed notebook outputs on GitHub. To reexecute them, use Python 3.12 and the dependency lockfile. Keep environments, private inputs, and standalone generated files outside the repository; executed notebook outputs are intentionally versioned.

```bash
export WOWFS_WORK_ROOT=/absolute/path/to/wow-work
python3 -m venv "$WOWFS_WORK_ROOT/envs/research"
source scripts/env.sh
python -m pip install -r requirements-reproduce.lock
python -m pip install --no-deps -e '.[reproduce]'
export WOWFS_REPRO_ARCHIVE=/absolute/path/to/WOW_MINIMAL_INTERFACE_NATIVE_REVIEW.zip
make prepare
make reproduce
```

Reexecution requires the privately supplied `WOW_MINIMAL_INTERFACE_NATIVE_REVIEW.zip`. Set `WOWFS_REPRO_ARCHIVE` to its local path. The archive includes manuscript material and is deliberately not hosted in this repository or its releases. It is not needed to view the committed notebook figures and tables.

The input must be the final v2 data archive; its SHA256 is checked automatically. In the existing workspace, the default paths support `source scripts/env.sh && make reproduce`. Each invocation creates a fresh output directory and prints the locations of `REPRODUCTION_REPORT.json` and the executed notebooks. The report is marked PASS only after the tests and every notebook finish successfully.

After a successful reproduction run, copy its five executed `.ipynb` files from the reported output directory into `notebooks/` before committing refreshed results. Preserve their outputs. For interactive work, run `make notebooks`. To run the tests alone, use `make test`. To resume an interrupted run, pass `--output <original-output-directory> --resume` to the reproduction script; source code, inputs, and dependencies must match. See the [complete instructions and limitations](docs/REPRODUCIBILITY.md).

## Code and evidence layout

```text
src/wowfs/
  experiments/      Mathematical algorithms, statistics, native experiments, and earlier studies
  reporting/        Existing report generators and the current paper_assets.py entry point
  reproduction/     Verified inputs, cached-data replay, and execution orchestration
notebooks/          5 executed notebooks with embedded figures and tables
scripts/reproduce/  One command for tests, analysis, figures, tables, and notebooks
tests/              Scientific behavior and reproduction checks
docs/               Paper mapping, reproduction instructions, data scope, and history
```

See [CODE_MAP.md](docs/CODE_MAP.md) for the mathematical entry points. Existing module paths remain intact to preserve frozen source references and historical script dependencies. Historical research notes remain under [docs/history](docs/history/README_before_reorganization.md). Manuscript files are held in private local storage; sealed input archives and scientific calculations remain unchanged.

## Reproduction scope

The cache contains paired moment statistics from native observations. It supports recomputation of the 16 base catalogues and 128 registered queries yielding 42 YES / 76 NO / 10 UNKNOWN, along with the ablations, tolerance analyses, target families, and Druid certificates. Inference retains the original fixed sample sizes, simultaneous paired-t Bonferroni approximation, and its assumptions; UNKNOWN remains unresolved. The target interface covers a fixed finite catalogue of defined, measured components.

Generating new combat observations requires the separately archived engine, patches, configurations, and seeds. This workflow runs no new battles. Runtime tables are recomputed from saved measurements and are not new benchmarks on the current hardware. Exact manuscript typesetting requires TeX. See [DATA.md](docs/DATA.md).
