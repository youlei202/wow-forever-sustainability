# Recompute the review conclusions

Use the included data and code; no original server path, simulator, or account is
needed for the principal decision/certificate recheck. Install the pinned
`requirements-recheck.txt` in a separate Python environment. The recorded run
uses Python 3.12; dependencies are listed in `DEPENDENCIES.json`.

Set `BUNDLE` to the extracted `review-v2` directory, and `RECHECK_WORK` to a new
directory outside that bundle. Keep environments, caches and generated files in
that external directory. The commands below do not modify the bundle:

```bash
export BUNDLE=/absolute/path/review-v2
export RECHECK_WORK=/absolute/path/external-recheck
mkdir -p "$RECHECK_WORK/tmp" "$RECHECK_WORK/cache"
export TMPDIR="$RECHECK_WORK/tmp"
export XDG_CACHE_HOME="$RECHECK_WORK/cache"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$BUNDLE/code"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
python -m wowfs.experiments.co_review_check \
  --bundle "$BUNDLE" --output "$RECHECK_WORK/CERTIFICATE_RECHECK.json"
python -m wowfs.experiments.co_benchmark_report \
  --check "$BUNDLE/data/benchmark" > "$RECHECK_WORK/BENCHMARK_METRIC_RECHECK.json"
```

The first command checks file identity, compact sufficient statistics, the full
contrast family, initial-state validity, all allowed publication subsets and
saved witnesses. It reproduces primary native decisions, secondary tolerances,
task projections, source-obligation ablations, and the inherited continuous
parameter certificates. Exact mean decisions use an independent Fraction/bitmask
oracle; no SAT/CP solver is imported. The two expanded frozen constructions that
fail on fresh means remain failures even though alternative completions exist.

The second command recomputes runtime summaries, query counts and matched-prefix
comparisons from the included compact per-attempt/per-query receipts. It does not
rerun wall-clock measurements. CSV fields record unresolved and unprocessed
queries, partial interfaces, timeouts, and actual distinct-query pool sizes.
`data/benchmark/QUERY_RESULTS.csv.gz` is a losslessly compressed CSV, not a sampled
result set. `ARTIFACT_INDEX.json` maps its logical deliverable name; the large
compressed table is stored once to keep the upload small.

The saved interfaces under `data/certificate-interfaces/` also answer new targets
inside their fixed menu and contract, without further combat simulations. To
compile one independently from its source certificate and query it:

```bash
python -m wowfs.experiments.co_certificate_service compile \
  --bundle "$BUNDLE" --world co_mage_timed_resources__validation_00 \
  --variant base --output "$RECHECK_WORK/mage-base-interface.json"
python -m wowfs.experiments.co_certificate_service query \
  --interface "$RECHECK_WORK/mage-base-interface.json" \
  --target a01 a02 --output "$RECHECK_WORK/new-target-answer.json"
```

The example returns NO. This is reuse of an already covered finite event, not a
new independent experiment. Out-of-menu items are rejected. History, task set,
weights and thresholds cannot be silently changed; see
`docs/CERTIFICATE_SERVICE.md` for contract and UNKNOWN semantics. This utility was
added after confirmation and is not an additional measured performance baseline.

For an optional fresh solver execution on Linux, install `requirements-solvers.txt` and
use the launcher below. It reconstructs the expected source layout in a **new**
external output directory, preserving the bundle. It uses the included frozen
registry and the same exact models, with single-thread methods. A full repeated
query suite can take hours; budgets are explicit, and runtime comparisons with
the original machine require matched hardware and execution conditions.

```bash
python "$BUNDLE/scripts/review_run_benchmark.py" \
  --bundle "$BUNDLE" --output "$RECHECK_WORK/native-existence" \
  --registry native --workflow existence --workers 1 --seconds 60
python "$BUNDLE/scripts/review_run_benchmark.py" \
  --bundle "$BUNDLE" --output "$RECHECK_WORK/synthetic-queries" \
  --registry synthetic --workflow queries --workers 1 \
  --seconds 60 --history-seconds 900
```

The main figures have standalone LaTeX sources under `docs/figures/`. Native and
sensitivity panels contain their plotted values. Benchmark panels use companion
CSV files under `data/benchmark/figures/`; compile from a copy of that directory
into an external output directory. No font binaries are distributed. The
scripts used to generate the tables/panels are included for inspection.

Raw combat trajectories, the executable engine, full dependencies, and duplicate
per-job input copies remain in the indexed work archive. `OBSERVATION_INDEX.jsonl`
records physical cells, native input/output/binary hashes and seed/N identities;
`provenance/ARCHIVE_EXCLUSIONS.json` describes the limits of this compact bundle.
It reconstructs the finite consequences of the stored event, rather than proving
the event's population coverage or regenerating the underlying battles.

The fixed-N paired-t approximation, the .04 new main allocation, and the old
campaign's separate .05 event retain their original assumptions. A solver-issued
UNSAT answer is not an independently checked DRUP proof. The old and new events
do not combine into a fresh global .05 guarantee.
