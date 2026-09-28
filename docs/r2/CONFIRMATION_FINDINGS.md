# Fresh-seed confirmation: shared cooldowns suppress combined value

**Confirmed in the tested native community engine:** Diamond Flask and
Cloudkeeper Legplates have negative pair interactions in the 30-second and
four-target encounters under the two selected policies. Both effects retain
standalone value, but their shared offensive timer and activation schedule
leave Cloudkeeper with zero recorded aura occupancy when Flask is enabled in
these cases. The proposed positive haste/extra-attack and resource-feedback
interactions **did not confirm** in the frozen primary family.

This is a fixed-configuration causal result, not evidence for preserved
rewards under optimized equipment choice, zero power inflation, reusable
20-round rules, or superiority to a same-information generic method. The
shared cooldown is already present in the native engine; it is not a new
mechanism invented by this study.

## Executed scope and estimand

`confirmation-v1` completed **480 native cells / 61,440 physical fights**,
with zero recorded failures: one Warrior class, Human and Orc, four tasks,
three policies, and 20 factorial effect masks across three fixed equipment
cases. Every cell used 128 iterations. These are repeated simulations of
source-defined configurations, not 61,440 independent equipment ecosystems.
The six primary contrasts below concern **Human only**; the other native
panels, including Orc, are descriptive.

The community engine is pinned at
`17d75ccc8c67d027ae0088243ea3ee806d406847`, running `RulesetForever`.
The level-60 Warrior has fixed talents `30305013-050520035150310051`,
starting rage zero, 250 ms queue delay, no enchants, consumables or external
buffs. Battle Shout and policy actions remain enabled. Targets are level 63
with 3,731 armor in all primary contrasts and a 20% execute phase. This is
native simulator evidence, not independent validation of live-server rules.

Effects were disabled by replacing their registration callback with a no-op.
All equipped item IDs, static attributes, base weapon damage/speed and other
set tiers stayed unchanged. For a pair, masks `0,1,2,3` mean neither effect,
A only, B only, and both. Where a third effect exists, the pair uses **C off**,
the discovery-selection convention. The original frozen primary manifest
records `effects: 2` but does not separately spell out C's state; this
convention is made explicit here without changing that manifest. Three-way
results use all eight masks.

Fresh confirmation seeds were `92427001` through `92427128`, paired by index
within every factorial. Discovery used a disjoint seed block. Six targets
were selected from exploratory results and recorded before confirmation;
selection uncertainty is addressed by the fresh outcomes, not by treating
the discovery estimates as prespecified evidence.

## Primary results only

All units are DPS. Intervals use paired seed-level contrasts and Student-t
quantiles with Bonferroni correction for six scalar primary targets. They
have approximate familywise 95% coverage for general nonnormal simulator
contrasts; no distribution-free or pathwise safety guarantee is asserted.

| Effects | Task / policy | Interaction | Paired SE | Adjusted interval | Conclusion |
|---|---|---:|---:|---:|---|
| Flask × Cloudkeeper | 30 s, one target / native_reck | −18.669 | 0.209 | [−19.228, −18.110] | Negative |
| Flask × Cloudkeeper | 90 s, four targets / native_no_reck | −5.563 | 0.089 | [−5.800, −5.325] | Negative |
| Flask × Cloudkeeper | 180 s, one target / native_reck | Numerically zero | Degenerate | Not informative | Numerical additivity in observed seeds only |
| Empyrean × Hand of Justice; Felstriker effect off | 90 s, four targets / native_reck | 0.187 | 2.306 | [−5.995, 6.368] | Unresolved |
| Ironfoe × Heroism four-piece × Hand of Justice | 90 s, four targets / native_no_reck | −1.254 | 2.618 | [−8.271, 5.763] | Unresolved |
| Ironfoe × Heroism four-piece; Hand of Justice effect off | 180 s, one target / native_reck | −1.484 | 1.401 | [−5.239, 2.271] | Unresolved |

The maximum absolute per-seed contrast for the sustained shared-cooldown
case was `1.7053e-13` DPS. Its essentially zero estimated sampling variance
does not establish population equivalence or universal absence of an
interaction. It is reported as observed numerical additivity, with no
meaningful confidence interval.

### Raw four-cell means

The pair estimand is `mean(AB)-mean(A)-mean(B)+mean(0)`; each cell below has
128 observations. These values show why antagonism need not mean that the
combined loadout itself is worse than either individual effect.

| Case / task / policy | Neither | A only | B only | AB |
|---|---:|---:|---:|---:|
| shared_active / short_burst / native_reck | 372.228 | 400.232 | 390.897 | 400.232 |
| shared_active / four_target / native_no_reck | 360.011 | 379.140 | 365.573 | 379.140 |
| shared_active / sustained / native_reck | 267.247 | 273.900 | 269.604 | 276.256 |
| haste_extra / four_target / native_reck, C off | 375.760 | 396.290 | 381.727 | 402.444 |
| extra_resource / sustained / native_reck, C off | 233.887 | 245.790 | 240.493 | 250.913 |

For the triple, A=Ironfoe, B=Heroism four-piece, C=Hand of Justice. The
eight means are:

| Mask | 0 | A | B | AB | C | AC | BC | ABC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| DPS | 308.600 | 325.914 | 320.805 | 338.013 | 313.314 | 331.196 | 324.424 | 340.945 |

### Native event coordinates behind the confirmed result

Diamond Flask is item `20130`, aura/spell `24427`; Cloudkeeper is item
`14554`, with that item action ID. The shared-active case also equips
Empyrean `17112`, Felstriker `12590`, and Blackhand's Breadth `13965`.
The compared effects are only Flask and Cloudkeeper; the other effects are
kept enabled in all four cells.

In the 30-second AB cell, mean Flask uptime is 30 s and Cloudkeeper uptime
is zero. Cloudkeeper alone has 30 s uptime. In the 90-second four-target AB
cell, Flask uptime is 60 s and Cloudkeeper uptime is zero; Cloudkeeper alone
has 27.815 s mean uptime. **AB and A-only DPS are exactly equal seed by seed
in all 128 observations in both cases.** Thus the negative contrast equals
the lost standalone marginal value of Cloudkeeper for these policies.

The four-target AB cell nevertheless records Cloudkeeper `procsAvg=0.2734375`
with zero uptime. That counter is not evidence of useful occupancy; a claim
that Cloudkeeper literally never activates would be too strong without
checking the event boundary. The observed statement is zero recorded active
duration and no DPS contribution in these samples. In the sustained AB
cell both buffs retain their full mean durations (Flask 60 s, Cloudkeeper
30 s), consistent with the source-defined schedule allowing separate windows.
The fixed policy and encounter horizon therefore matter to the reward
tradeoff; a source-only assertion of shared cooldown would not quantify it.

The first confirmation seed (`92427001`) was replayed in all four masks with
debug logs. In A-only and AB, log lines 6–9 show Flask cast, completed, gained
and adding 75 Strength at `0.00 s`; lines 1089–1090 remove its aura at the
`30.00 s` fight boundary. No Cloudkeeper activation appears in AB. B-only
instead casts Cloudkeeper at `0.00 s` (lines 6–9), adds 100 attack power and
100 ranged attack power, and removes its aura at `30.00 s` (lines 1085–1086).
The four observed DPS values are 399.469, 428.911, 419.097 and 428.911 for
0/A/B/AB, respectively. These are illustrative raw events from an existing
confirmation seed, not four additional independent statistical observations.
Full logs, inputs, commands, output hashes and exact line coordinates are
exported in `selected_evidence/shared_cooldown_seed_92427001/`.

The positive hypotheses remain worth distinguishing mechanistically, but
the primary data do not support claiming positive amplification. Neither
non-significance nor a small point estimate proves no interaction. Further
case selection or sample expansion must be labelled follow-up research rather
than appended to this completed fixed-sample confirmation.

The separate reoptimization panel changes the conclusion's scope. After
development search over each declared 16-loadout domain and three policies,
fresh-seed evaluation of the frozen selected winners does not establish a
remaining negative shared-cooldown interaction. Several selected winners
avoid the disadvantaged effects entirely; their measured contrasts are zero.
That panel uses its own 12-contrast family and is not included in the primary
table or figure here. The local mechanism is real in these simulations, but
this study has **not established a reoptimized performance benefit from a new
composition rule**. Selected finite-domain winners are not certified global
optima. Its complete results are in
`runs/r2-discovery/reoptimization-confirmation-v1/CONTRASTS.json` under the
work root.

## Evidence and reproduction

The maintained renderer is `src/wowfs/reporting/r2_interactions.py`:

```bash
source scripts/env.sh
python -m wowfs.reporting.r2_interactions
```

It reads the unmodified run under
`WOWFS_WORK_ROOT/runs/r2-discovery/confirmation-v1/`, validates primary seed
starts and sample lengths against cached requests, recomputes paired
contrasts, and writes these products under
`WOWFS_WORK_ROOT/artifacts/r2-discovery/latest/`:

* `CONFIRMATION_PRIMARY.json`: raw cell means, estimates, interval conventions,
  each raw output's hash and cache key, plus hashes of the source manifest,
  protocol and complete results.
* `CONFIRMATION_PRIMARY.csv`: all six targets with four/eight cell means.
* `figures/primary_interactions.png` and `.pdf`: the primary family only.

Native inputs, invocation records and compressed raw outputs remain in
`WOWFS_WORK_ROOT/cache/r2-discovery/native/<prefix>/<cache_key>/`.
These fixed-configuration results must stay distinct from the separately
executed reoptimization and mechanism-intervention panels.
