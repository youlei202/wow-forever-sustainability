# Reproducing the native R2 study

The source repository is `/work/Users/leiyo/GitHub/wow-forever-sustainability`.
Runtime files are under `/work/Users/leiyo/wow-forever-sustainability-work`.
The earlier R1 abstract study is historical and is not rerun by these commands.

The pinned engine, verified toolchain, build sources and smoke provenance are
documented in [ENVIRONMENT.md](ENVIRONMENT.md). Both engine binaries remain
outside the maintained repository. Their requests require explicit
`RulesetForever`; the rules are those of the pinned community implementation.

```bash
cd /work/Users/leiyo/GitHub/wow-forever-sustainability
source scripts/env.sh
bash scripts/native_build.sh
bash scripts/native_build_mechanism.sh
```

For an existing run, prefer its archived binary and immutable physical inputs.
The following resumes missing cached cells, verifies archived source/executable
hashes, and leaves an already completed result file byte-identical:

```bash
python scripts/resume_r2.py confirmation-v1 --workers 64
python scripts/resume_r2.py unseen-v1 --workers 64
```

Use a new run name to launch the current source/configuration version. The
per-input cache includes the exact executable hash and the complete request,
including mechanism, equipment, tasks, policy and integer seed. A cache hit is
not another native engine call or independent battle.

```bash
python -m wowfs.experiments.r2_native --stage discovery --iterations 32 \
  --seed 24092401 --run-id discovery-reproduction --workers 64
python -m wowfs.experiments.r2_native --stage factorial --iterations 128 \
  --seed 92427001 --races RaceHuman RaceOrc \
  --run-id confirmation-reproduction --workers 64
python -m wowfs.experiments.r2_sequences --run-id unseen-reproduction --workers 64
```

The original `confirmation-v1/PRIMARY_CONTRASTS.json` records the six selected
contrasts before its outcomes. Its pair convention is C-off where an eight-cell
case is used; this is stated in the confirmation findings. The original
`unseen-v1/FROZEN_DESIGN.json` embeds the actual initial thresholds, item
descriptors, proposal sequences, evaluation contract and hashes before new-item
combats. Keep those original freezes when reproducing the reported study.

Reoptimization and mechanism studies have their own archived development and
confirmation runs. Their selection manifests distinguish source-derived
settings, discovery-selected witnesses and fresh confirmation seeds. They
cannot be pooled into the six-target fixed-configuration statistical family.

```bash
python -m wowfs.reporting.r2_interactions
python scripts/audit_r2_native.py --require-complete
pytest -q
bash scripts/build_r2_paper.sh
```

The independent audit counts successful physical invocations, validates raw
output hashes and retains failures. Native combat logs may be much larger than
the review archive: all input JSON, invocation records, compressed raw engine
outputs and per-seed summaries are in
`WORK_ROOT/cache/r2-discovery/native/<prefix>/<cache_key>/`.
The review package includes selected complete event evidence and a compressed
per-call integrity ledger instead of duplicating the entire cache.

The `SOURCE_CODE.zip` review attachment is a current maintained-source snapshot;
each original run also has its own frozen source and executable hashes. This
repository has no fabricated author identity, remote push or public submission.
