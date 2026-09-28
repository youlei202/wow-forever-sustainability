# R4 reproduction and immutable records

Source: `/work/Users/leiyo/GitHub/wow-forever-sustainability`.
Work products: `/work/Users/leiyo/wow-forever-sustainability-work`.

Activate the existing environment from the source directory:

```bash
source scripts/env.sh
pytest -q
python scripts/audit_r4_native.py --workers 24 --require-complete
```

The audit is read-only with respect to physical runs and writes a new timestamped
ledger. It checks frozen input manifests, native binary/source hashes, all raw
result receipts, iterations, complete statuses and deduplicated physical counts.
Analysis-only protocols are classified separately.

All physical runs under `runs/r4-foundational-discovery` are complete. Their
`JOBS.json`, `PROTOCOL.json`, frozen native executable and source files are the
authoritative replay inputs. Do not regenerate a frozen job using a different
configuration and call that a resume. New experiments require a new run identity.
The maintained drivers document actual configuration and seed choices:

| Driver | Scope |
|---|---|
| `r4_native` | complete12-ecology baseline and incoming engineering check |
| `r4_worlds` | eight source-defined permission-C interventions and parity checks |
| `r4_task_growth` | four independent demand additions; actual config is CONFIG.yaml |
| `r4_confirmation` | selected complete domains, fresh512 seeds |
| `r4_causal` | callback factorials, selected complete domains |
| `r4_unseen initial_current` | changed pools, initial512 calibration and current action selection |
| `r4_unseen future` | complete future table after current branch selection froze |
| `r4_constructive` and `r4_certificates` | synthetic new-reward amplitudes and eight precision blocks |

The root `source` dependency snapshot sometimes contains the original broad
configuration. For a custom run, its explicit `CONFIG.yaml`, `BASE_ECOSYSTEMS.json`
and scientific protocol specify the measured domain. World, factorial and
amplitude results have multiple rows per gear/task/policy; filter the world or
amplitude before constructing a response table.

Current analysis entrypoints are `r4_batches`, `r4_coexistence`, `r4_demand`,
`r4_growth_analysis`, `r4_world_analysis`, `r4_confirm_analysis`,
`r4_unseen_analysis`, `r4_design_analysis`, `r4_precision_analysis`,
`r4_structural_report` and `r4_source_groups`. These operate on retained native
results. The two finite continuation libraries are explicit: the first pass uses
all-safe deterministic continuation; the unseen analysis exhaustively optimizes
the finite library adding exactly one new configuration at each future arrival.

Some analysis runs enforce a one-use output directory and exact source hashes.
Use a fresh external work directory or the archived analysis snapshot for a new
reproduction; do not delete or overwrite the original check-point directory.
`r4_feasibility.py`'s later scheduler retry changes only an inherited HiGHS runtime
initialization failure. Original solver outputs and frozen source snapshots remain
available; see SOLVER_RUNTIME.md.

For an individual native replay, copy a selected `input.json` to a new external
temporary directory, invoke the corresponding frozen binary with `-in` and `-out`
pointing to that copy and a new output path, and compare parsed numerical content
and seed order. Do not overwrite a retained cache output. Native action arrays
can differ in Go map iteration order; combat logs and numerical per-action
identities are the relevant comparison. Such a newly executed replay is a new
physical call and is not included in the delivered R4 receipt.

Regenerate the compact review after all analyses and the independent audit exist:

```bash
python -m wowfs.reporting.r4_report
python scripts/package_r4.py
```

The review ZIP includes maintained source, frozen protocols, selected raw
receipts, figures and the complete physical audit ledger. The full combat cache
and large native JOBS/RESULTS manifests stay at their recorded work-root paths.
Source files were staged locally without inventing a Git identity or pushing.
