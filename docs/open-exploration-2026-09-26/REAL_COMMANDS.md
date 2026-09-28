# Executed commands and receipts

All Python commands were run after `source scripts/env.sh` in
`/work/Users/leiyo/GitHub/wow-forever-sustainability`.
`RUN` below is the explanatory abbreviation for
`$WOWFS_WORK_ROOT/artifacts/open-exploration-2026-09-26/campaign-v1`.
Full raw command outputs and frozen inputs remain at the corresponding paths;
these are completed executions, except the explicitly identified freeze failure
and the unsampled confirmation draft.

## Native execution inventory

The common executable command is
`python -m wowfs.experiments.oe_runner --phase PHASE --config CONFIG --run-root RUN --workers 48 --max-wall-hours 24`.
The table identifies actual submitted batch requests; the batch protocol and
per-call receipts, rather than shell notation, establish physical execution.
Native long jobs used tmux. All eight executed batches completed without a
native-call failure.

| Batch | Phase | Config under RUN/requests | Physical calls | Completed battles |
|---|---|---|---:|---:|
| smoke-v1 | audit | smoke.json | 54 | 432 |
| benchmark-v1 | audit | benchmark.json | 54 | 27,648 |
| broad-v1 | discover | broad.json | 0 | 0: snapshot failed before native execution |
| broad-v2 | discover | broad-v2.json | 4,288 | 137,216 |
| refine-v1 | challenge | refine.json | 7,280 | 1,863,680 |
| catalog-v1 | discover | catalog.json | 1,344 | 344,064 |
| policy-challenge-v1 | challenge | policy-challenge.json | 96 | 49,152 |
| deep-challenge-v1 | challenge | deep-challenge.json | 480 | 1,966,080 |
| confirm-v1 | not_run | confirm-v1.json | 0 | 0: superseded before sampling |
| confirm-v2 | confirm | confirm-v2.json | 960 | 72,351,744 |

The final native invocation, launched in tmux `oe-confirm-v2`, was:

```bash
python -m wowfs.experiments.oe_runner --phase confirm \
  --config "$WOWFS_WORK_ROOT/artifacts/open-exploration-2026-09-26/campaign-v1/requests/confirm-v2.json" \
  --run-root "$WOWFS_WORK_ROOT/artifacts/open-exploration-2026-09-26/campaign-v1" \
  --workers 48 --max-wall-hours 24
```

Its log is `$WOWFS_WORK_ROOT/logs/oe-confirm-v2.log`. Completion was recorded
at 2026-09-26 11:29:41 UTC, with 206.01 seconds of batch wall time. Individual
call elapsed times are not CPU time; the resource report keeps that distinction.

## Development analysis and challenges

Executed analysis entry points and input/output pairs:

```text
python -m wowfs.experiments.oe_analysis
  --batch RUN/batches/{broad-v2,refine-v1,catalog-v1}
  --registry RUN/{WORLD_REGISTRY.jsonl,WORLD_REGISTRY_CATALOG.jsonl}

python -m wowfs.experiments.oe_planning
  --batch RUN/batches/{broad-v2,refine-v1,catalog-v1}
  --registry <matching original or derived registry>
  --output <new analysis directory> --max-candidates 12 --timeout 5

python -m wowfs.experiments.oe_baseline_challenge
  --analysis RUN/analysis/broad-v2-planning-v2
  --output RUN/analysis/broad-min-increment-v1

python -m wowfs.experiments.oe_baseline_challenge
  --analysis RUN/analysis/refine-v1-planning
  --output RUN/analysis/refine-min-increment-v1

python -m wowfs.experiments.oe_baseline_challenge
  --analysis RUN/analysis/catalog-v1-planning
  --output RUN/analysis/catalog-min-increment-v1

python -m wowfs.experiments.oe_baseline_challenge
  --analysis RUN/analysis/catalog-two-slot-v1/planning
  --output RUN/analysis/catalog-two-slot-min-increment-v1

python scripts/oe_targeted_capacity.py
  --batch <catalog-v1,refine-v1,deep-challenge-v1>
  --registry <recorded full-domain registry>
  --cases <recorded cases JSON> --output <new challenge directory>

python scripts/oe_full_baseline_challenge.py <recorded arguments>
python -m wowfs.experiments.oe_joint_mechanism_audit <recorded arguments>
```

Braces and placeholders above summarize multiple actual invocations rather
than claiming one literal shell command. `checks/theory/*CHALLENGE.log`, each
analysis `MANIFEST.json`, and saved `analysis-source` files identify the exact
cases, hashes and executed script versions. The source-protection addition to
some maintained scripts was made after their original analysis; the original
bytes remain alongside their manifests. Do not claim a changed script hash was
the previously executed code.

## Frozen confirmation preparation and analysis

```bash
python scripts/prepare_oe_confirmation.py \
  --run-root "$WOWFS_WORK_ROOT/artifacts/open-exploration-2026-09-26/campaign-v1" \
  --design /work/Users/leiyo/GitHub/wow-forever-sustainability/configs/open_exploration_confirmation_v2.json
python -m pytest -q tests/test_oe_*.py
python -m wowfs.experiments.oe_confirmation \
  --batch "$WOWFS_WORK_ROOT/artifacts/open-exploration-2026-09-26/campaign-v1/batches/confirm-v2" \
  --manifest "$WOWFS_WORK_ROOT/artifacts/open-exploration-2026-09-26/campaign-v1/CONFIRMATION_MANIFEST_V2.json" \
  --output "$WOWFS_WORK_ROOT/artifacts/open-exploration-2026-09-26/campaign-v1/analysis/confirm-v2-results"
python -m wowfs.experiments.oe_claim_decisions \
  --manifest "$WOWFS_WORK_ROOT/artifacts/open-exploration-2026-09-26/campaign-v1/CONFIRMATION_MANIFEST_V2.json" \
  --analysis "$WOWFS_WORK_ROOT/artifacts/open-exploration-2026-09-26/campaign-v1/analysis/confirm-v2-results" \
  --output "$WOWFS_WORK_ROOT/artifacts/open-exploration-2026-09-26/campaign-v1/CONFIRMED_CLAIMS.json"
```

The latter two ran sequentially in tmux `oe-confirm-analysis`, log
`$WOWFS_WORK_ROOT/logs/oe-confirm-analysis.log`. Analysis completed at
2026-09-26 11:32:03 UTC. Statistical support is reported by the separate frozen
adjudicator, not inferred from successful program exit.

## Independent audits

`checks/INDEPENDENT_AUDIT_EVIDENCE_v2.json` verifies all 13,596 development
raw outputs. `checks/POST_CONFIRMATION_PROVENANCE.json` and
`analysis/confirm-v2-compact-moments/MOMENTS_MANIFEST.json` verify the confirmation
data. `checks/FINAL_STATISTICAL_AUDIT.json` checks families, sources, budgets,
complete upper searches and claim identities;
`checks/SECONDARY_MOMENT_INFERENCE_CHECK.json` recomputes 166 selected linear
contrasts independently from compact moments. Counterexamples and failed
freeze receipts remain in the package. No public push or submission was made.
