# Effect ablations on selected complete native domains

The surviving pairs do not require Eskhandar's haste callback. The complete
factorial distinguishes a joint item-support requirement from a productive
interaction between the two effects.

The frozen `causal-pairs-v1` study covers resource_haste (18203,19951),
timing_shared (18203,19019), and timing_extra (18203,19951), each with all
36 induced old/singleton/pair configurations, both races, eight tasks, three
policies and four callback states. Timing_extra was explicitly added after
the independent 512-seed result, before these ablation outcomes. Seed409260001
starts 256 labeled trajectories per input. The 20,736 logical cells collapse
to 9,216 unique inputs: 2,359,296 battles, no failures. One preparation error
before freezing or calling the engine is preserved in PREPARATION_FAILURES.

Mask0 disables both new callbacks; mask1 enables only Eskhandar; mask2 enables
only the other item; mask3 enables both. Static stats, weapon damage/speed,
identity, and set membership remain. Thunderfury ablation removes its entire
proc package, including attack-speed slow; it is not a pure Nature-damage
scalar in the incoming-damage task. All old16 responses are bit-identical
across the four worlds. Power uses the original discovery numerical caps,
scale and old-source obligations; fresh old profiles determine the behavior
reference. No cap is retuned.

| Complete pair domain | Mask0 | Mask1 | Mask2 | Mask3 |
|---|---|---|---|---|
| timing_extra Human | infeasible N/D | infeasible N/D | feasible | feasible |
| timing_extra Orc | infeasible N/D | infeasible N/D | feasible | feasible |
| timing_shared Human | infeasible N/D | infeasible N/D | infeasible N/D | infeasible N/D |
| timing_shared Orc | infeasible N/D | infeasible N/D | feasible | feasible |
| resource_haste Human | protected P fails | protected P fails | protected P fails | protected P fails |
| resource_haste Orc | protected P fails | protected P fails | protected P fails | protected P fails |

These are finite empirical feasibility statements. Every failure above is a
necessary obstruction, and every success has an explicit all-safe admission.
The fresh resource_haste old frontier itself exceeds the frozen cap by 2.6191
DPS for Human and 0.1183 DPS for Orc. Its original named Human pair gear
331790c18dd3a920 exceeds the cap by 15.3507 DPS with both effects enabled.
Its D distance survives (.117703), illustrating why D alone is insufficient.

For the named timing_shared Orc gear26007bac9b64ca50, high_armor/native_reck:

| Callback state | Mean DPS | D distance | H plus this gear jointly passes |
|---|---:|---:|---|
| neither | 155.9006 | .016134 | no |
| Eskhandar only | 157.8415 | .015541 | no |
| Thunderfury only | 188.3594 | .091779 | yes |
| both | 190.5752 | .094321 | yes |

Thunderfury adds approximately32.5–32.7DPS here. Haste adds approximately1.9–2.2.
The paired mixed contrast is +.2749DPS with simultaneous approximate95% interval
[-.1927,.7424], using the frozen family of all5,184 gear/task/policy/race
factorials. Thus the named contrast does not establish a positive interaction,
and disabling haste does not remove qualification. Other contexts do have
detectable small positive interactions:52/5,184 contrasts exclude zero
positively (all in timing_shared, estimates .3687–.9668DPS); none exclude zero
negatively. These counts do not establish that interactions are necessary for
the joint item-support result.

Power remains close to the boundary for the named TF gear. Its full-effect
point-mean minimum slack is .6513DPS; its approximate simultaneous candidate
mean upper bound exceeds the fixed numeric cap by2.4818DPS (family9,216).
With haste disabled the corresponding values are2.8671DPS slack and .3363DPS
upper-bound excess. Therefore neither named state has a simultaneous
population cap certificate from this panel. Behavior distances are summaries,
not confidence bounds. The timings and labels refer to the executable
community engine, not live-server validation.

Timing_extra Orc also admits gear48d1cb0f8a17565d with both effects: its
candidate-only simultaneous cap slack is8.0268DPS. This was identified within
the ablation table and is a selected finite witness. The old16 domain still
needs its own uncertainty check. Its ten-second paired effect interaction is
-.0154DPS, interval[-9.6954,9.6646]. The useful rage active on the physically
weaker weapon is sufficient; this evidence does not establish required
haste/rage synergy.

Maintained analysis is `src/wowfs/experiments/r4_causal_analysis.py`. The full
denominators, per-mask singleton checks, all joint-gear certificates, and all
factorial contrasts are in CAUSAL_PAIR_ADMISSIONS.csv, CAUSAL_PAIR_DETAILS.json,
CAUSAL_PAIR_WITNESSES.csv, and CAUSAL_PAIR_FACTORIALS.csv under the R4 artifact
directory. Approximate Student-t intervals are paired across matched seeds;
they are not exact nonparametric or behavior-distance guarantees.
