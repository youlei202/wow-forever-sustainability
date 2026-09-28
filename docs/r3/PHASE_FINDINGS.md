# Native counterfactual complementarity phase grid

The 63-point native weapon grid contains an observed region where a weaker and/or
faster Blood Talon makes Thunderfury usable within a fixed response-informed cap.
This is evidence for a finite compensation family. It is not evidence for a
positive proc interaction, a learned reusable admission rule, or an indefinitely
renewable supply of distinct rewards.

## Frozen experiment and analysis

`runs/r3-gold/phase-grid-v1` contains 24,192 native response cells and 774,144
battles: 9 main-hand base-DPS values, 7 speeds, 4 offhands, 4 trinket pairs,
4 tasks, 3 policies, 2 races, and 32 iterations per cell. There were no native
errors. The intervention changes Blood Talon's damage scale and attack speed
inside the engine; changing speed holds the specified weapon DPS fixed. Its
native proc remains unchanged. These are engine counterfactual weapons, not
claims about obtainable live-game items.

The before state is R2 `expanded_interleaved_0`, round 19. R2's independently
sampled 185-loadout initial reference and numeric cap remain fixed. Every new
loadout is checked against all 12 task/policy cells; one excessive cell excludes
that whole loadout in the safe-reference view. The analysis also reports every
raw batch's maximum power and number of excessive loadouts before filtering.
No power claim is inferred from the fact that the reference filter removes
excessive responses.

The reported region requires Thunderfury to change from below the frozen useful
task-mass threshold to at least that threshold, together with a competitive
new Thunderfury loadout whose physical behavior is at least 0.05 away from both
the old allowed configurations and the historical archive. Competitiveness uses
each point's combined old-plus-admitted-new optimum and the frozen 5% of initial
DPS tolerance. The behavior space is the same seven coordinates as R2; no item-ID
coordinate was introduced. Four-neighbor connectivity refers only to tested
grid points. No interpolation or continuous-space guarantee is claimed.

## Observed grid

| Context | Cumulative headroom | Empirical reactivation + N + D points | Components | With a selected witness supported against the fixed numeric cap | Entire raw batch below cap |
|---|---:|---:|---:|---:|---:|
| Human | 0% | 4 / 63 | 1 | 0 / 63 | 1 / 63 |
| Human | 5% | 32 / 63 | 1 | 4 / 63 | 18 / 63 |
| Orc | 0% | 6 / 63 | 1 | 0 / 63 | 2 / 63 |
| Orc | 5% | 38 / 63 | 1 | 8 / 63 | 22 / 63 |

The 0%-headroom selected sets have exactly unchanged empirical task envelopes;
they contain behaviorally different competitive choices. At 32 samples their
mean-power safety is not supported by the conservative simultaneous intervals.
At 5%, all four points in the DPS {28, 32} by speed {1.0, 1.3} rectangle have four
empirical competitive, novel Thunderfury loadouts in each race. The maximum
task/policy response of the lowest-peak qualifying loadout ranges from roughly
94.3% to 95.8% of the Human cap and 93.4% to 95.7% of the Orc cap. Their selected
behavior distances are around 0.08–0.09. This interior is materially farther
from the cap boundary than the original native Blood Talon parameters.

The region is obtained using all currently measured task responses. It therefore
does not solve the source-only prediction or reusable-rule problem. With a
fixed old offhand, simply reducing main-hand amplitude can bring an otherwise
blocked combination below a cap. Source re-entry alone cannot distinguish this
compensation from a productive interaction; the separate causal factorials are
needed for that distinction.

## Uncertainty and the original native point

Power intervals are approximate Student-t mean intervals with a two-sided
Bonferroni family over all 12,096 phase response cells within each race.
Post-selection of a loadout or either headroom uses the same covered physical
means. The fixed numeric R2 cap is the primary design threshold. A separate
sensitivity analysis widens both the old initial-anchor means and the new
means using the union of old and phase cells. No region point is supported by
that more conservative population-anchor sensitivity at 32 iterations. These
are different estimands and are explicitly separate in the CSV.

Behavior is reported from native aggregate action/resource means. The current
outputs do not provide per-iteration action/resource vectors, so no behavior
confidence interval or statistical D certification is invented. The numerical
N and D memberships in this exploratory grid require independent confirmation.

At the original 39.230769 DPS and 1.3-second speed, the 32-seed phase run retains
four empirical Thunderfury choices in each race at 5% headroom. Its raw batch
peak is 99.9075% of the Human cap and 99.1055% of the Orc cap; this is a boundary
observation, not replicated safety. In particular, the separate fresh
128-seed causal run's canonical Human loadout has high-armor DPS 189.8007,
above the frozen numeric cap 188.90496. R2's selected canonical value was
188.7091. The phase run's same exact loadout and native-reck policy yields
187.6754, with an independent-seed difference from R2 of -1.0336 ± 1.7773
standard errors. This seed-to-seed variation is why an interior family and
fresh selected-point validation are more informative than a single boundary
witness. No statement here calls the original point confirmed safe.

## Frozen follow-up selection

The phase table was used to select the following ten parameter points before
viewing any follow-up outputs. Each is to be measured on the complete 16-loadout,
3-policy, 4-task, 2-race domain using fresh seeds:

| DPS | Speed | Role |
|---:|---:|---|
| 28 | 1.0 | Interior rectangle |
| 28 | 1.3 | Interior rectangle |
| 32 | 1.0 | Interior rectangle |
| 32 | 1.3 | Interior rectangle |
| 24 | 1.0 | Low-power, zero-headroom control |
| 28 | 1.9 | Slower-speed region point |
| 39.230769230769226 | 1.3 | Original native boundary |
| 46 | 1.3 | Upper boundary |
| 54 | 1.0 | Race-dependent boundary |
| 54 | 2.8 | Outside-region high-power control |

This is a selected follow-up family, not an independent estimate of the
fraction of all weapon parameters that work. The exact sample count and seed
belong in the follow-up run's frozen protocol.

## Fresh selected-point confirmation

`phase-confirmation-v1` completed all 3,840 cells using 1,024 fresh iterations
per cell, seed block starting 309246001: 3,932,160 battles and zero failures.
The selected four-point rectangle at 5% headroom was the primary family; the
other six points are controls. Confirmation intervals conservatively cover all
3,840 means across both races, not merely the primary points or a chosen
loadout. The same family therefore also permits examination of the controls.

All eight primary point-by-race cases retain all four Thunderfury loadouts with
supported mean-power safety against the frozen numeric cap and supported
near-optimality conditional on the fixed old response table. Each loadout also
has an empirical behavior witness above the unchanged D threshold. These are
eight confirmations of a finite counterfactual region, with 32
point-by-race-by-loadout memberships, not 32 different item mechanisms.

| DPS, speed | Human raw batch peak / cap | Orc raw batch peak / cap | Supported TF loadouts in Human / Orc |
|---|---:|---:|---:|
| 28, 1.0 | 0.9562 | 0.9486 | 4 / 4 |
| 28, 1.3 | 0.9680 | 0.9622 | 4 / 4 |
| 32, 1.0 | 0.9660 | 0.9581 | 4 / 4 |
| 32, 1.3 | 0.9780 | 0.9722 | 4 / 4 |

The entire 16-loadout raw batch is empirically below the cap at all eight
primary cases. For the four Thunderfury loadouts, simultaneous lower cap-slack
bounds across all task/policy cells are at least 2.8739 DPS in Human and
3.9184 DPS in Orc over this rectangle. The near-optimality calculation includes
every new competitor that could still be admissible under its lower confidence
bound; it does not discard an uncertain competitor just because its point
estimate crosses the cap. Its old response table, initial tolerance scale, and
numeric cap are fixed design quantities. The separate population-anchor
sensitivity supports at least one novel Thunderfury witness at seven of the
eight primary cases; Human at (32, 1.3) remains unresolved under that sensitivity.

At literal 0% headroom, (24, 1.0) has three Human and four Orc Thunderfury
loadouts with supported power and near-optimality and empirical D. Orc at
(28, 1.0) has two. Their cap-filtered empirical task envelope is unchanged.
This provides a finite zero-growth choice example against the frozen numeric
design threshold. It does not certify the unknown population initial optimum,
all possible strategies, or future rounds; all these zero-headroom witnesses
remain unresolved under the population-anchor sensitivity.

Across all ten selected points, Human has 2 / 7 empirical region points at
0% / 5% headroom and Orc has 4 / 9. Supported power plus near-optimality with
empirical D remains at 1 / 6 points for Human and 2 / 7 for Orc. The original
native point is still a boundary case: the canonical Human Hand of Justice /
Blackhand's Breadth loadout has mean high-armor DPS 188.1738, but its adjusted
upper excess over the frozen cap is +0.6125 DPS. Both Human loadouts using
Gri'lek's Charm instead of Hand of Justice are supported at this point; all
four Orc loadouts are supported. This does not turn the earlier canonical
128-seed cap violation into an error or justify calling that exact canonical
Human loadout safely replicated.

The confidence construction concerns DPS means under a Student-t approximation.
Behavior has only aggregate native summaries and remains empirical. Accordingly
the output explicitly sets `joint_statistical_P_N_D_certificate=false` even
when its power and near-optimality fields are supported. Fresh confirmation
does not change the separate factorial finding that the native effect pair has
negligible interaction at the predeclared 1%-of-initial-DPS margin.

## Artifacts and checks

All generated artifacts live under `WOWFS_WORK_ROOT/artifacts/r3-gold/`:
`COMPLEMENT_PHASE_GRID.csv` (252 context/headroom/point rows),
`PHASE_WITNESSES.json`, `PHASE_SUMMARY.json`,
`NATIVE_POINT_COMPARISON.csv` (384 descriptive fresh-versus-R2 native-parameter
cell comparisons), and `figures/complement_phase_diagram.{png,pdf}`.
The figure colors raw unfiltered batch power and outlines the retained region;
the two quantities are intentionally visible together.

Run `source scripts/env.sh` then
`python -m wowfs.experiments.r3_phase_analysis` to reproduce analysis from the
existing native cache. The analysis validates complete race/parameter domains,
sample counts, duplicate cells, finite samples, and complete behavior arrays.
Five focused synthetic analysis tests pass; they check whole-loadout exclusion
by one unsafe policy, raw-versus-filtered power, source reactivation semantics,
the two uncertainty estimands, missing-cell failure, and grid connectivity.
These tests do not count as native experiments.

Fresh confirmation is reproduced with
`python -m wowfs.experiments.r3_phase_confirmation_analysis` and writes
`PHASE_CONFIRMATION.csv`, `PHASE_CONFIRMATION_SUPPORTED_WITNESSES.csv`,
`PHASE_CONFIRMATION_WITNESSES.json`, and `PHASE_CONFIRMATION_SUMMARY.json`.
Two additional tests check the near-optimality bound's treatment of uncertain
versus definitely unsafe competitors; all seven focused tests pass.
