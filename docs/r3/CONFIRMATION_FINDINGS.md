# Fresh finite-family confirmation

The once-selected ten-point family completed 3,840 native cells with 1,024 fresh
iterations each: 3,932,160 battles, zero failures. Approximate simultaneous
Student-t intervals cover all 3,840 fresh means across both races at family
level 95%. The R2 numeric task caps and old response table are fixed design
quantities. Uncertainty in the underlying initial population optimum is a
separate sensitivity analysis.

At 5% headroom, all eight primary cases—DPS {28, 32} × speed {1.0, 1.3} ×
Human/Orc—retain all four Thunderfury loadouts with supported mean-power safety
and supported near-optimality. Each has an empirical D witness against the
unchanged old-plus-history behavior comparison. The whole 16-loadout batch is
also empirically below the cap in every primary case.

| DPS, speed | Human raw batch peak / cap | Orc raw batch peak / cap | Supported TF loadouts, Human / Orc |
|---|---:|---:|---:|
| 28, 1.0 | 0.9562 | 0.9486 | 4 / 4 |
| 28, 1.3 | 0.9680 | 0.9622 | 4 / 4 |
| 32, 1.0 | 0.9660 | 0.9581 | 4 / 4 |
| 32, 1.3 | 0.9780 | 0.9722 | 4 / 4 |

For these Thunderfury loadouts the smallest simultaneous lower cap-slack bounds
are 2.8739 DPS in Human and 3.9184 DPS in Orc, across all tasks, policies, and
primary points. Near-optimality support compares a candidate's lower bound to
an upper frontier retaining every competitor whose true response could still
be admissible. Population-anchor sensitivity supports a witness in seven of
eight primary cases; Human (32, 1.3) remains unresolved under that sensitivity.

At **literal 0% headroom**, (24 DPS, 1.0 s) retains three Human and four Orc
Thunderfury loadouts with supported power and near-optimality plus empirical D.
Orc (28 DPS, 1.0 s) retains two. Their selected empirical task envelope is
exactly unchanged. This is a finite zero-growth choice example against frozen
numeric caps. None is supported by the population-anchor sensitivity.

Across all ten selected points, the counts of empirical region points are
Human 2/10 at 0% and 7/10 at 5%, and Orc 4/10 and 9/10. The corresponding counts
with supported power and near-optimality plus empirical D are Human 1/10 and
6/10, and Orc 2/10 and 7/10. These selected fractions do not estimate the
prevalence of success over a random weapon distribution.

The original native Human canonical loadout remains unresolved at 5%: its
1,024-seed high-armor mean is 188.1738 against cap 188.90496, but the adjusted
upper excess is +0.6125 DPS. Its separate 128-seed causal run produced 189.8007,
above that cap. The two Human Gri'lek-trinket alternatives and all four Orc
loadouts are supported at the original native parameter point. Do not call
the exact canonical Human loadout replicated safe.

This confirms a limited compensation family obtained by reducing main-hand
amplitude and/or changing speed while preserving the native proc. It does not
establish positive proc synergy, a joint statistical P/N/D certificate, a
population-wide power envelope, or 20-round sustainability. Behavior remains
an aggregate-mean measurement without per-iteration uncertainty. The separate
causal factorials put all eight primary effect-pair intervals inside the
predeclared ±1%-of-initial-DPS margin.

Artifacts are `PHASE_CONFIRMATION.csv`,
`PHASE_CONFIRMATION_SUPPORTED_WITNESSES.csv`,
`PHASE_CONFIRMATION_WITNESSES.json`, and `PHASE_CONFIRMATION_SUMMARY.json` under
`WOWFS_WORK_ROOT/artifacts/r3-gold/`. Source is
`src/wowfs/experiments/r3_phase_confirmation_analysis.py`; eighteen focused
phase/sequence analysis tests pass. No additional native calls were made by
the analyzer.
