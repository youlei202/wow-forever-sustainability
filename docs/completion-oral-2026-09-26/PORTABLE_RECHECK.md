# Recompute the compact review package

The review package can reconstruct the native completion decisions from its compact paired means/covariance/N without the original server, raw battle archive, or simulator executable. The checker also replays the inherited-event parameter boxes, the four-case glove source certificate, and any included secondary tolerance, task-projection, and source-obligation panels.

After extracting `review-v2.zip`, use its recorded Python dependency versions (NumPy, SciPy, and PyYAML). The checker uses its own exact-rational subset oracle; no SAT, CP, MILP, native simulator or database package is required. The command below writes its audit receipt outside the immutable extracted bundle:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/absolute/path/review-v2/code \
  python -m wowfs.experiments.co_review_check \
  --bundle /absolute/path/review-v2 \
  --output /a/new/path/RECHECK.json
```

No native battle is run. Do not pass development smoke flags when reviewing the final confirmation package. The optional `--allow-predictions` flag makes the output explicitly `SMOKE_PASS_PREDICTION_TABLES_ONLY`; it cannot turn prediction tables into confirmation evidence. `--allow-unsealed` is likewise a development-only escape hatch for packages whose file manifest has not yet been created.

## What is recomputed

1. All code/data hashes and file sizes against `REVIEW_MANIFEST.json`; unsafe relative paths and unsealed code/data files are rejected. The manifest checks content consistency. Check the separately supplied archive SHA256 for external identity.
2. Compact NPZ versus readable moments; fixed sample count and reference mapping; complete physical pair/task receipt identities.
3. Original cap, ordered gain, and ordered retention contrast families from the paired covariance. Reference uncertainty and covariance are retained. The original family size, coefficient hash and critical value are checked.
4. Every physical publication subset for each primary catalogue/menu, with all old, target and helper obligations. Both conservative witnesses and optimistic exclusion counts/masks are compared with the saved certificates. The retention-disabled comparison is checked separately.
5. Exact rational finite-mean decisions, their full response-model identities, and every saved constructive witness. An independently implemented bitmask oracle enumerates all publications with Fraction-exact response comparisons and integer task masses; it does not call the original SAT solver or round coefficients. Frozen prediction witnesses are separately checked on the fresh event.
6. All included secondary consequences and the old continuous-region bundle. The source-obligation replay is implemented independently in the portable checker and retains all physical rows, power constraints and gain constraints.

The paired-t guarantee remains an approximate, fixed-N statistical guarantee under the original assumptions. Exhaustive finite-model computation is not a proof-assistant theorem check or a solver-generated formal UNSAT proof. This command does not regenerate combat trajectories, test higher moments/tails, or reproduce wall-clock benchmark measurements. The separate 1,000-case encoding battery concerns solver correctness and must not be counted as new native evidence.

## Package paths consumed by the checker

```
REVIEW_MANIFEST.json
code/wowfs/{__init__.py,paths.py}
code/wowfs/experiments/co_{review_check,review_oracle,native_analysis,exact,sensitivity,native_sensitivity}.py
data/native/CATALOG_REGISTRY.jsonl
data/native/ANALYSIS_MANIFEST.json
data/native/NATIVE_DECISIONS.json
data/native/<world>/MOMENTS.npz
data/native/<world>/MOMENTS_READABLE.json
data/native/<world>/BOUNDS_MANIFEST.json
data/native/<world>/<variant>/EXACT_QUERIES.json
data/native/<world>/<variant>/CONFIDENCE_CERTIFICATES.json
data/native/<world>/<variant>/VALUE_ONLY_CONFIDENCE.json
data/sensitivity/<the compact inherited-event files>
data/secondary-tolerance/<world>/TOLERANCE_RESULTS.json   # if included
data/projection/<world>/<variant>/{EXACT_QUERIES,CONFIDENCE_CERTIFICATES}.json  # if included
data/obligations/<world>/<variant>/OBLIGATION_AUDIT.json  # if included
```

`BOUNDS.npz` is optional: the checker reconstructs its contents, and compares them if the file is included. The inherited-event directory contains `INHERITED_MOMENTS.npz`, metadata, base claims, all grid certificates, and certified regions. It needs no original absolute path. Absolute raw-cache paths inside provenance records remain references only and are never opened by this checker.

The file-manifest schema is `{"files":[{"path":"relative/path","sha256":"...","bytes":123}]}`. Every code/data file must be listed. The manifest itself is outside its own hash list. Generated `__pycache__` files do not count as inputs, but the command above disables their creation.
