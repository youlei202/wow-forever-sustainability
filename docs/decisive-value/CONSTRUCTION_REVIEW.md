# Independent construction review

Reviewed the archived `construction-search-v1` source and frozen protocol,
`CONSTRUCTIVE_SEARCH.json`, the current `value_construct.py`, and its admission
and behavior helpers. No native simulation or construction search was rerun.
The checks below recompute the selected finite models from the calibration
coefficients; they do not substitute for independent native confirmation.

## Computation checks

No computational discrepancy was found in the selected three-round prefix.
Independent enumeration used every physical main-hand/off-hand pair, direct
affine evaluation, explicit all-policy cap checks, and pairwise L-infinity
behavior distances against the complete prior admitted library.

| Round | Full physical crosses | Admitted crosses | Maximum cumulative gain / initial scale |
|---|---:|---:|---:|
| 1 | 9 | 8 | 1.202877335% |
| 2 | 16 | 15 | 1.301930991% |
| 3 | 25 | 23 | 3.279226029% |

For each round, the stored admission set exactly equals the set satisfying
the fixed 24 task/policy cap inequalities over the full physical cross-product.
Every previously admitted pair remains admitted. The helper omits previously
rejected old-only pairs from its `FiniteProblem`, but they remain unsafe under
the same fixed coefficients and cap; full enumeration confirms that none is
silently turned into an admissible substitute or excluded despite safety.

The initial reference uses all four old equipment crosses and all three
policies. Later G baselines reoptimize over every previously admitted cross
and policy. Recomputed baselines, gains, N/L source masses, D task mass, and
per-source D masses match the recorded values exactly. Initial scale and cap
are unchanged across all rounds. Both new aliases enter the protected-source
registry in subsequent rounds.

D normalization agrees with the existing metric: five disjoint damage shares,
rage gain/second divided by 20, and rage waste divided by positive rage gain
(zero when gain is zero). Ratios are formed after affine numerator prediction;
the search does not incorrectly treat normalized shares as affine. The nearest
reference includes every prior admitted equipment/policy behavior for the
same task. D is required for the release; N is required for each new source.

The frozen search proposes 32,768 Sobol points per round, or 98,304 proposals
in total. Regenerating the declared Sobol designs reproduced all three saved
selected recipes exactly at their recorded indices. This check does not
independently certify the optimizer's ranking over every rejected proposal
or completeness over the continuous design box. Recorded strict-joint proposal
counts are 915, 25, and 11.

## First-pair contrast: cap compensation

The following are model results, with all three policies reoptimized. Gains
are relative to the complete initial old-library optimum on `high_armor`:

| Equipment | Gain | Admitted by fixed cap rule? |
|---|---:|---|
| New MH2 + old OH0 | +6.201543% | No; exceeds the 5% headroom |
| New MH2 + old OH1 | −0.773937% | Yes |
| New MH2 + new OH2 | +1.202877% | Yes |

The new off hand is weaker beside either old main hand. The admitted old-plus-MH2
library and old-plus-OH2 library each have zero G on all eight tasks. Releasing
both gives +1.202877% on the high-armor task, and deleting either new source
removes that gain. The lower-output off hand makes the useful main-hand tradeoff
compatible with the shared cap. The unsafe cross remains in the physical
domain and is rejected by the same public rule, not a source-specific blacklist.

At each fixed task and policy, the mixed finite difference
`U(MH2,OH2) - U(MH2,OH0) - U(MH0,OH2) + U(MH0,OH0)`
has maximum absolute residual `5.684341886080802e-14` DPS. The response model is
additive. The positive batch-versus-singleton library contrast comes from cap
admission and optimization, not superadditive combat physics.

## Metadata issue and interpretation limits

The original source stored mutable `mh`/`oh` lists inside the protocol object.
Consequently the `protocol.initial_mh` and `protocol.initial_oh` fields embedded
in the final search `RESULTS.json` and `CONSTRUCTIVE_SEARCH.json` incorrectly
contain all five final aliases per slot. The separately frozen run
`PROTOCOL.json`, written before the lists grew, correctly contains two initial
aliases per slot. Its recorded source hash matches the archived original
source. The current maintained code differs by copying those initial lists,
which prevents the defect in later runs. Historical files were not rewritten
by this review; reproductions must use the frozen `PROTOCOL.json` for the
initial state and disclose this metadata discrepancy.

Further limits:

* Search outcomes are predictions from 256-seed development coefficients,
  selected adaptively. `confirmed_native` is correctly false in the search
  artifact. Population means, fresh native controls, and prospective reward
  outcomes require the separate confirmation experiment.
* Three releases add six aliases, but not six independently essential decision
  improvements. OH3 has zero decision-frontier deletion loss in round 2;
  MH4 has zero loss in round 3. They satisfy the declared N/D conditions;
  their individual necessity for G is not established.
* All recorded portfolios have K=1. This prefix does not show that preserving
  its uses requires additional carried loadouts or greater management burden.
* The same four features and 24 inequalities are available to a generic
  affine method. The results do not establish an estimator advantage, a new
  nonlinear interaction, or a theorem of unlimited expansion.

Evidence paths are under
`$WOWFS_WORK_ROOT/runs/decisive-value/construction-search-v1` and
`$WOWFS_WORK_ROOT/artifacts/decisive-value`. The inspected calibration hash is
`c85e34b797e01430b64cf2959ec4262df9315d63839449935f0909816d009cb5`;
the archived construction source hash is
`eab7f5ff1d5337e1906b454294048c5df0dec4609c749d81789589aa5277b00d`.
