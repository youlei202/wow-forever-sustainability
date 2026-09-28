# Current manuscript and notebook mapping

The figure/table reference is **Retention-Preserving Completion in Growing Compositional Systems — The World of Warcraft: Forever Problem**, from the frozen `WoW_Minimal_Interface_Codex_Handoff` bundle. Its title and results—16 catalogues, 128 targets, and 42 YES / 76 NO / 10 UNKNOWN—match the supplied reorganization brief. The source entry point is `manuscript/WoW_Future_Targets_AISTATS2027/main.tex` under the externally prepared input directory. All manuscript-relative paths in this document refer to that locally supplied external bundle, not files in this repository. No `paper/` directory, manuscript source, or manuscript PDF is distributed here.

Following the actual `\input` references from `main.tex`, the current manuscript contains **4 numbered composite figures (8 panels), 15 numbered tables, and 2 unnumbered tables**. Numbers below follow source-reference order; LaTeX labels or explicit original filenames identify each asset. Three numbered tables originally have no `\label`; the manuscript has not been edited to add labels.

[`01_paper_figures.ipynb`](../notebooks/01_paper_figures.ipynb) displays every referenced figure. [`02_paper_tables.ipynb`](../notebooks/02_paper_tables.ipynb) displays all 17 tables. They call `prepare_paper_assets`, `figure_gallery`, and `paper_tables` in [`paper_assets.py`](../src/wowfs/reporting/paper_assets.py). Figures are redrawn with Matplotlib and exported as PNG/SVG/PDF; tables are displayed and exported as CSV/HTML. The plots retain the data, units, and bound directions, but are not pixel-identical copies of the TikZ layout.

## Figures

Input paths below are relative to the complete external frozen manuscript bundle. Regenerated assets are written to the external run directory under `paper-assets/manuscript/`. The committed notebook outputs display all referenced figures and tables without access to that bundle.

| Figure / label | Original entry point and panels | Numerical or construction input | Original generator / checker | Notebook |
|---|---|---|---|---|
| Figure 1 `fig:latent` | `sections/figure_theory.tex`; `latent_conflict`, `target_tradeoffs` | `theory/src/completion.py::latent_repair_instance`; original exact formulas `2+100t`, `2.8-100t-100t²` | `theory/src/verify.py`; the two original TikZ sources | 01, Figure 1 |
| Figure 2 `fig:triple` | `sections/figure_triple.tex`; `triple_targets`, `triple_retention` | `evidence/gold/checked_outputs/TRIPLE_SOURCE_CERTIFICATE_v2.json`, `TRIPLE_INDEPENDENT_CERTIFICATES.json`; paired moments in `evidence/gold/data/native/` | `evidence/gold/scripts/check_triple.py`, `triple_source_certificate.py`; `scripts/rebuild_v2_assets.py` | 01, Figure 2 |
| Figure 3 `fig:tolerance` | `sections/figure_tolerance.tex`; `tolerance_targets`, `source_obligations` | `evidence/v2/native-summary/NATIVE_EVIDENCE_SUMMARY.json`; regenerated `data/plots/new_tolerance.csv` | `scripts/rebuild_v2_assets.py`; the complete native audit replays the original contracts and ablations | 01, Figure 3 |
| Figure 4 `fig:exclusion` (supplement) | `sections/figure_certificate.tex`; `repair_conflicts`, `source_exclusion` | `theory/data/TRINKET_MOMENTS.npz`, `TRINKET_METADATA.json` → `theory/checks/NATIVE_ALL_WIDTH_CERTIFICATES.json` → `data/plots/conflicts.csv`, `retention_bounds.csv` | `theory/src/native_reanalysis.py`; `scripts/rebuild_assets.py`, `render_plot_sources.py` | 01, Figure 4 |

The three targets in Figure 2 are not three simultaneously equipped items: B and C are alternative boots in the same slot. Retention excludes all 128 publication supersets, while all 32 physical configurations in the catalogue are power-safe. The right panels of Figures 2 and 4 show one-sided upper-bound rays, not two-sided confidence intervals. Source-group attributions in Figure 3 may overlap and must not be summed as mutually exclusive categories.

The original `rebuild_v2_assets.py` uses fixed coordinates for the source-obligation panel. The reporting layer checks the corresponding evidence fields and reads 42 / 39 / 28 / 16 directly from JSON without changing those values.

## Tables

`A` = `scripts/rebuild_assets.py`; `V` = `scripts/rebuild_v2_assets.py`. Both original generators run in an external copy. Except for the final numbered table, notebook table bodies are read from the regenerated LaTeX and retain the manuscript's rounding precision.

| Table / original label | Contents and original row file | Input | Generation / verification |
|---|---|---|---|
| 1 `tab:newfactions` | Class/faction YES/NO/UNKNOWN; `new_faction_rows.tex` | `evidence/v2/native-summary/BASE_CATALOG_SUMMARY.csv` | V; `scripts/verify_v2.py` |
| 2 `tab:runtime` | 6 repeated-query services; `runtime_rows.tex` | `evidence/v2/benchmark/QUERY_HISTORY_RESULTS.csv` | V; `co_benchmark_report.check` aggregates original receipts without remeasuring runtime |
| 3 `tab:allcatalogues` | 16 base catalogues; `catalogue_rows.tex` | `BASE_CATALOG_SUMMARY.csv`, `evidence/v2/NATIVE_CATALOGUES.jsonl` | V |
| 4 `tab:pairwitnesses` | Boots-retention lower bounds for the three target pairs; `triple_pair_rows.tex` | `TRIPLE_INDEPENDENT_CERTIFICATES.json` | V; `check_triple.py` |
| 5 `tab:triplehelpers` | Excluded optional gloves; `triple_helper_rows.tex` | `TRIPLE_SOURCE_CERTIFICATE_v2.json` | V; `triple_source_certificate.py` |
| 6 `tab:alltol` | Complete 128-target outcomes at 0.5/1/2/5%; `tolerance_rows.tex` | `NATIVE_EVIDENCE_SUMMARY.json::secondary_tolerance` | V; tolerance-contract replay in the complete native audit |
| 7 `tab:protocol` | Frozen confirmation sample sizes and thresholds; `protocol.tex` | `data/source/CONFIRMATION_MANIFEST.json` | A |
| 8 `tab:durations` | All physical task durations; `durations.tex` | World/task objects in the same manifest | A |
| 9 `tab:items` | Complete native trinket/off-hand catalogue; `catalog_items.tex` | `data/source/B_SOURCE_IDENTITIES.csv` | A |
| 10 `tab:gloves` | Complete gloves/legs catalogue; `glove_items.tex` | The same identity CSV | A |
| 11 `tab:firstdetails` | Confirmation means and normalized first-release results; `first_states.tex` | `data/source/B_SOURCE_HISTORY_PATHS.json` | A |
| 12 (originally unlabeled) | All-width exclusion upper bounds after Second Wind; `all_width.tex` | `theory/checks/NATIVE_ALL_WIDTH_CERTIFICATES.json` | `native_reanalysis.py` → A |
| 13 (originally unlabeled) | Maximal sets after Tome on finite mean tables; `maximal_sets.tex` | `theory/checks/NATIVE_MEAN_INTERFACES.json` | `native_reanalysis.py` → A |
| 14 `tab:jointall` | Cap and interaction contrasts; `joint_all.tex` | `data/source/C_JOINT_CONTRASTS_ALL.csv` | A |
| 15 (originally unlabeled) | Exact-arithmetic check sizes; `exact_checks.tex` | `theory/checks/EXACT_CHECKS.json` | `theory/src/verify.py` → reporting-layer generation |
| Unnumbered | Continuous threshold regions; `sections/appendix_new_methods.tex` | The manuscript's two certified parameter boxes | Displays original LaTeX entries without inferring a larger region |
| Unnumbered | Druid history / A / B / C item identities; `sections/appendix_new_results.tex` | Fixed database IDs and slots in the manuscript | Displays original LaTeX entries |

The original builder reads `EXACT_CHECKS.json` but does not rewrite `exact_checks.tex`. The reporting layer adds this step, extracting all 9 rows from the actual replay JSON and checking the manuscript's counts: 500, 700, 120, 100/964, 10/55, 1,016, 250, 200, and 77. Duration fields are not treated as byte-for-byte reproducible values.

## Subsequent audits and unreferenced assets

The 351 singleton-only misses, 3 pairwise misses, 96 contracts, 184,320 targets, and subsequent construction checks for arbitrary downward-closed families come from `docs/minimal-interface-2026-09-27/` and the frozen `minimal-interface-native-audit-2026-09-27` package. These audits postdate the reference manuscript and appear separately in the audit notebook. They must not be presented as figures or tables already included in this manuscript, or as additional native samples. Of the 3 pairwise misses, two are minimal triple obstructions and the third is their four-item union, not a third minimal triple obstruction.

The following original assets are not referenced by the current `main.tex`. They are preserved in the external frozen bundle but excluded from the figure/table coverage denominator:

- `sections/figure_native.tex`: `first_equivalence`, `source_uses`; original paired-equivalence/source-mask evidence, generator A and `render_plot_sources.py`.
- `sections/figure_interactions.tex`: `penetration_joint`, `mana_joint`; original joint-contrast CSV, generator A and `render_plot_sources.py`.
- `sections/table_factions.tex` / `tables/faction_rows.tex`: earlier source-retention capacity comparison from `B_CAPACITY_BOUNDS.csv`.
- `sections/table_interfaces.tex` / `tables/interface_rows.tex`: earlier finite mean interfaces and optimistic survivors.

The original generators still regenerate these assets in the external run directory. No old-manuscript data are added to the reference manuscript's sample totals.

## External outputs and replay scope

`prepare_paper_assets(ctx.paper_source, ctx.output / "paper-assets", checks=True)` copies the complete locally supplied frozen source bundle to an external directory and runs exact-arithmetic checks, inherited-moment analysis, 24 base/expanded certificate interfaces, a post-confirmation target scan, Druid covariance/source certificates, and benchmark-receipt checks. Original inputs remain read-only. Regenerated tables, panel sources, logs, and provenance reside in the copy. A completed directory is reused only when source/code/output hashes match; changed inputs or code require a new output root, and failed directories are preserved.

`PAPER_ASSETS.json` records external input source hashes, reporting-code hashes, environment details, actual commands, logs, and `numerical_replay` status. `checks=False` regenerates displays from saved evidence and explicitly records `numerical_replay=not_run`; this is not a replay PASS. The complete notebook/runner enables checks by default.

These steps require no new simulator calls. New combat simulation requires the archived engine/executable, database, and per-battle outputs. The paper records engine revision `17d75ccc8c67d027ae0088243ea3ee806d406847` and the original bridge/research variants. Statistical YES/NO decisions are conditional on the original fixed-sample paired Student-t/Bonferroni approximation, not a distribution-free guarantee. Solver receipts support recomputation of aggregates; historical elapsed wall-clock times cannot be rerun identically.

For optional local TeX typesetting, run `bash build.sh` in the **external staged manuscript**. This requires `pdflatex`, BibTeX/BibTeX8, standalone, TikZ/PGFPlots, and the other packages listed by the original manuscript. The default notebooks display every figure using Matplotlib without TeX. The receipt records `exact_tex_build=not_run` separately from numerical replay status.
