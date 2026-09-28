# Frozen data and provenance

The repository contains code, documentation, and executed notebooks with embedded figures and tables. Viewing those notebooks on GitHub or in Jupyter requires no input archive. Manuscript sources, manuscript PDFs, and the frozen input archive are not distributed through the repository or its releases.

To reexecute the analyses, supply your own unchanged copy of the frozen input archive locally, or use an already prepared and verified external input directory. The archive contains manuscript material as well as numerical evidence, so keep it outside the repository and do not upload it to GitHub. Set `WOWFS_REPRO_ARCHIVE=/absolute/path/to/WOW_MINIMAL_INTERFACE_NATIVE_REVIEW.zip` before running `make prepare` or `make reproduce`.

The portable input is the final v2 `WOW_MINIMAL_INTERFACE_NATIVE_REVIEW.zip`:

```text
bytes: 59402828
sha256: 9f598b3ee487e266a58213e383ad86dad6b9c8ca6f4ee7d725b1addd5d1dbbde
```

The earlier same-named archive has a different hash. The loader requires v2, which includes the corrected JSON-key comparison in the portable checker. Failed earlier analyses remain as provenance.

`make prepare` verifies the archive and package manifest, then unpacks nested review-v2, handoff and manuscript archives. Inputs default to `$WOWFS_WORK_ROOT/inputs/paper-reproduction`; set WOWFS_REPRO_INPUTS to relocate them. INPUT_MANIFEST.json records every extracted file's SHA256, verified before use. Do not edit these immutable inputs.

The package includes compact MOMENTS.npz/readable moments, registered catalogues and thresholds, simultaneous-event parameters, certificates, saved solver timing/decisions, manuscript evidence and proof note. Rebuilding moments from original per-battle trajectories is separate from replaying compact statistics.

No new simulator is required for finite response-table queries, intervals, tolerance/retention analyses, Druid evidence or saved benchmark aggregates. Fresh combat needs the archived engine, patches, configurations and seeds; original input provenance records available paths/hashes. This workflow does not recreate the engine, raw battles or live-game mechanics.

Statistical YES/NO decisions retain the fixed-N simultaneous paired-t Bonferroni approximation. Observations remain paired, no new alpha is spent, and UNKNOWN remains unresolved. Tolerance contracts and task projections reuse observations and do not add independent native catalogues. Power safety, retention and completion are separate properties.

Each run records source hashes, full input-manifest hash, dependency versions, platform, notebook status and failures. Saved timing retains its original hardware scope; replay duration is not substituted for it.

Source code and executed notebooks remain in Git. Notebook cell outputs are intentionally tracked so every figure and table is visible without reexecution. Environments, imported data, staged manuscript files, generated standalone plots/tables/PDFs, logs, and full run directories remain external, following AGENTS.md. Do not package or publish the locally supplied frozen archive with this repository. No license or author identity has been invented for inherited material.
