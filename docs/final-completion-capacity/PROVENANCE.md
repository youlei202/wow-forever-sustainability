# Native provenance and counting

The independent physical-receipt audit verified **22,032 native invocations and
8,181,632 completed battle iterations** in this stage. There are zero retained
failed invocations, incomplete invocations, output-audit errors, or unfinished
physical runs. All six frozen run archives pass binary, input, job, imported
artifact, source, output, and iteration-count checks. The audit covers all nine
classes and all 56 official race/class contexts.

| Frozen physical run | Invocations | Battles | Purpose |
|---|---:|---:|---|
| support-smoke-v1 | 56 | 896 | Source-defined class/race execution support |
| scalar-calibration-v1 | 2,240 | 143,360 | Stat-response and allocation calibration |
| mechanism-calibration-v1 | 1,440 | 46,080 | Three event/resource families |
| old-ecologies-v1 | 3,584 | 458,752 | Complete matched initial domains |
| capacity-confirmation-v1 | 12,408 | 6,352,896 | Independent main-design checkpoints and full nonaffine finite crosses |
| mechanism-capacity-confirmation-v1 | 2,304 | 1,179,648 | Independent mechanism-design confirmation |

These totals count physical cached receipts exactly once. Logical research
aliases, unexecuted affine interpolations, exact arithmetic, finite searches,
read-only analysis, and reuse of any earlier stage add no native battles. All
R1–R6 and decisive-value inputs/runs remain separate and unmodified.

The executable hash is
`59f42b32e2c834321773188db482419238ae57556942f6f1825258722fc0aafe`.
The compressed physical ledger hash is
`3868b30f5114e2ebc5036df04b53324d62f9b115b2c4eb0e07256a5adbbd2f4d`.
The authoritative audit is
`WOWFS_WORK_ROOT/artifacts/final-completion-capacity/INDEPENDENT_NATIVE_AUDIT.json`;
its exact ledger path and the archived per-run verification details are stored
there. The audit command is `python scripts/audit_fc_native.py --require-complete`
after sourcing `scripts/env.sh`.

The exact native input identity, excluding seeds, iteration count, and logging
flags, gives 20,160 distinct combat designs and 8,181,632 distinct design/seed
observations. There are no exact repeated design/seed observations. This does
not imply independent stages: old-ecology measurement and mechanism calibration
share 32 seed values, while the main and mechanism confirmations share 512.
Matched labeled seeds intentionally couple different designs. Full interval
and pairwise-stage accounting is retained in `SEED_OVERLAP.json`.

Hardware is the available AMD EPYC 9535 host with 256 logical CPUs. Concurrent
native workers were limited to 64 in total, commonly split into two groups of
32; each native process used `GOMAXPROCS=1`. No GPU results are counted.

Execution support is broader than the exact scalar-model mapping: 51 contexts
pass fresh per-seed/control affinity validation, while all five Warlock
contexts retain their nonaffine status and their explicitly executed finite
tables. Seven contexts have known upstream racial omissions. Runtime success
does not validate the live game or all possible policies/specifications.

Two analysis corrections/additions are explicitly separate from physical
runs. Scalar calibration analysis v2 excludes friendly/self damage from
outgoing-enemy damage channels; native utility and battles are unchanged.
The original Warrior behavior partition receives a separate checkpoint audit
before interpolated behavior is interpreted. Original behavioral D has only a
mean diagnostic here, and is unavailable as the same seven-coordinate object
for other classes. Approximate simultaneous Student-t inference concerns the
declared finite utility/relevance contrasts within each context, not a joint
population guarantee across all contexts or every model assumption.
