# Fixed-control reward amplitudes: native result and limits

The checked Forever Warrior family has an unusually simple reward map when the
control process is fixed. Changing Blood Talon base weapon DPS and its periodic
hit amplitude leaves the sampled actions and resource evolution unchanged in
the tested contexts. Three native reward anchors then predict all tested
interior rewards to floating-point precision. This is a property of a restricted
native family, not evidence that broad effect labels predict every interaction.

The initial probe covered Human and Orc, four tasks, and the `native_reck`
policy at speed 1.3, Thunderfury off hand and trinkets 11815/13965. Three corners
fit `[1, base_dps - 24, tick_damage]`; a fourth corner and two interior points
were held out. Across 48 cells × 128 matched seeds, maximum per-seed error was
2.28e-13 DPS. Aggregate cast/hit/crit/tick, resource and aura metrics matched;
the normalized event schedule of the first logged seed also matched. This does
not assert that an aggregate metric records every seed's event schedule.

Before later transfer outcomes, the design was frozen in
`artifacts/r3-gold/FROZEN_AFFINE_TRANSFER_DESIGN.json` under the work root, SHA-256
`a76ce3e62b631ece689f0c1f89eec63d5902b1c5d35fb7612a733d23080d9656`.
Calibration used 128 new matched seeds starting 309242001, three anchors
(24,0), (54,0), (24,30), and 288 context-specific models: two races × three
speeds (1.0, 1.3, 1.9) × four offhand/trinket profiles × four tasks × three
policies. The 864 native calibration calls contained 110,592 battles, with no
failures. All three anchors had identical aggregate control metrics in every
model. Calibration finished before the independent prospective sequence study.

The frozen 32 parameter items used base DPS in [26,50] and tick amplitude in
[2,28], generated from seed 309242019. Each retained one of the three calibrated
speeds and was tested across all 96 remaining contexts. The other panels tested
specific predeclared departures, without fitting a new model to their results.

| Panel | Native cells × 128 | Largest absolute mean error | Largest per-seed error | Interpretation |
| --- | ---: | ---: | ---: | --- |
| Held-out amplitudes, supported controls | 3,072 | 3.41e-13 DPS | 3.41e-13 DPS | All control metrics match; paired-seed affine diagnostic passes |
| Fresh independent seeds, canonical context | 256 | 11.957 DPS | Not paired | Sampling uncertainty remains |
| Speeds 1.45/1.75/2.35 or PPM 0.7/1.6 | 320 | 19.696 DPS | 142.221 DPS | All control metrics differ; outside frozen support |
| Gri'lek resource context | 64 | 5.263 DPS | 109.813 DPS | All control metrics differ; outside frozen support |

The fresh panel uses seeds starting 309243001. Its mean-error standard error is
`sqrt(calibration prediction variance / 128 + evaluation variance / 128)`.
Only 160/256 pointwise normal intervals contain zero. These cells share just
eight context kernels: all 32 intervals exclude zero for both short-burst
contexts and Orc four-target, while all 32 include zero for the other five.
This is not a 256-independent-trial coverage estimate, a simultaneous bound,
or a validated cap certificate. For the matched-seed structural panel,
interval containment at 1e-13 roundoff is not meaningful; the prespecified
1e-8 residual tolerance is the criterion. Control equality across the fresh
seed blocks was not tested and is recorded as not applicable.

Gri'lek was absent from this calibration, but it was already present in R2 and
phase studies. Diamond Flask was included in the expanded calibration. Neither
is claimed as a newly discovered effect vocabulary. Changing speed or PPM also
changes a control kernel inside existing broad mechanic types. A deployable
rule must reject unsupported kernels or acquire new coefficients.

Using the unchanged numeric R2 cap (1.05 times the initial catalogue task
optimum), 197/256 held-out matched-seed loadouts are safe over all tasks and
policies. The typed affine rule and a generic linear estimator with identical
features, data and coefficients admit exactly those 197. A finite response
oracle and refitted per-item lookup agree after observing all 3,072 held-out
response cells. The frozen unknown-item whitelist admits none; a frozen empty
blacklist admits all 256, including 59 unsafe loadouts. A deliberately
conservative common scalar majorant admits eight and excludes all unsafe
loadouts. That scalar construction is not an optimized scalar LP and does not
establish impossibility or a generic model-class separation. These comparisons
are finite point-estimate decisions, not global expected-performance guarantees.

The full rule has 288 task/policy inequalities and 864 fitted reward
coefficients. Numeric LP pruning on DPS [24,54] and tick amplitude [0,30] leaves
12 cap inequalities across 24 context branches. The branch selectors and four
shared domain bounds remain necessary. A compact JSON rule including caps,
bounds and selectors occupies 3,408 bytes and reproduces all 256 tested
full-rule decisions. Pruning uses frozen coefficients and caps, but was performed
after transfer; it is a descriptive compression, not a preregistered deployment
or proof of minimum description length.

At fixed palette, the rule size stays constant across the measured 4, 8, 16
and 32 parameter-item prefixes. At a matched count of eight parameter items,
one/two/three speed kernels require 96/192/288 unpruned rows and retain
4/8/12 numeric cap facets, with compact rule sizes 1,429/2,426/3,408 bytes.
This illustrates dependence on control kernels under an unchanged verbal
vocabulary. The generic estimator has exactly the same complexity. The result
does not establish that continuous new control parameters admit a uniformly
bounded catalogue-wide rule.

Maintained implementations are `r3_affine.py`, `r3_affine_transfer.py` and
`r3_affine_analysis.py` in `src/wowfs/experiments`. Work-root artifacts include
`AFFINE_PROBE.json`, `AFFINE_CALIBRATION.json`, `AFFINE_TRANSFER.json`,
`AFFINE_COMPARISONS.json`, `AFFINE_METHOD_COMPARISON.csv`,
`AFFINE_TRANSFER_DECISIONS.csv`, `RULE_COMPLEXITY_SCALING.csv`, and
`AFFINE_ADMISSION_RULE_NUMERIC_PRUNING.json`. Raw frozen analysis remains in
each run; the transfer report artifact records the later reporting correction
that marks inapplicable interval/control checks explicitly. No combat output
was changed. This affine work used 4,624 new native calls and 591,872 battles;
the nine separate engineering smoke battles are documented in NATIVE_VARIANTS.md.
