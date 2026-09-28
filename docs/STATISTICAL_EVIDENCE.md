# Finite-data coefficient diagnostic

This completed experiment uses the final pool of the two-slot theorem
construction and bounded synthetic observations. It measures identification
of its six hazardous crossed pairings. It is **not** an online update study,
a joint P/N/D/L/H/C success count, or native Forever simulation.

The known baseline is `1+q` on task `+`. Each training observation is a
matched/mismatched contrast made from two independent physical draws, each
with uniform noise in `[-0.1,0.1]`. Shared estimation uses two channel
coefficients; separate estimation uses six configuration contrasts. A generic
estimator with the same two features is included and exactly reproduces the
shared estimator using the same measurements. Thus parameter sharing is the
tested assumption; the experiment shows no advantage over a generic method
given the same model. All methods receive the same nominal physical training
budget. Cached reuse and newly generated draws are recorded separately.

There are 128 independent replications, four fixed budgets, and two paired
scenarios. Half the per-replication error budget of 0.05 is reserved for an
independent holdout; half is divided across both distinct estimators and all
four training budgets. The holdout samples each of eight legal configurations
512 times, for 4,096 additional physical draws per replication. Each holdout
draw returns both task endpoints. Holdouts are shared across methods and
budgets in a replication, so duplicated report rows are not independent data.

| Scenario | Physical training budget | Shared coefficients: all hazards certified | Generic, same features | Separate configuration contrasts | Holdout outcome |
|---|---:|---:|---:|---:|---|
| Correct shared model | 256 | 0/128 | 0/128 | 0/128 | 128/128 unresolved |
| Correct shared model | 1,024 | 0/128 | 0/128 | 0/128 | 128/128 unresolved |
| Correct shared model | 4,096 | 127/128 | 127/128 | 0/128 | 128/128 unresolved |
| Correct shared model | 16,384 | 128/128 | 128/128 | 128/128 | 128/128 unresolved |
| Hidden legal interaction | 4,096 | 127/128 | 127/128 | 0/128 | 128/128 violation |
| Hidden legal interaction | 16,384 | 128/128 | 128/128 | 0/128 | 128/128 violation |

The correct-model holdout remains unresolved because a legal configuration
attains the cap exactly; finite upper confidence bounds cross that cap. No
detected violation is therefore never reported as a statistical safety
certificate. Exact rational verification establishes the construction's
power result separately from these noisy holdout results.

The misspecification scenario adds an omitted `+0.08` task-`+` interaction to
the legal matched configuration containing the final new item. The two shared
calibration probes do not see it. At budget 4,096, 127/128 shared/generic
model-implied power conclusions are consequently false; at 16,384, all 128
are false. The independent holdout identifies a violation in 128/128
replications and vetoes every such false conclusion. This is a constructed
stress test, not a general detection theorem. It demonstrates why reducing
the feature dimension without validating model completeness is insufficient.

The full run generated 12,189,696 tiny synthetic physical draws, saved 3,072
trial rows and 24 grouped rows. The run uses seed 270924 and fixed declared
parameters; no native combat draw was generated. Source hashes, protocol,
denominators, states, independent holdout costs, and output hashes accompany
the data under `WORK_ROOT/data/theory/finite_data/`.

Reproduce with `source scripts/env.sh` followed by
`python scripts/verify_statistics.py`. The output directory can be changed
with `--output-dir` but must remain outside the source repository.
