# Shared extra-melee resource: native development result

Shared 1 s and 2 s cooldowns suppress extra-attack requests, but **neither lowers
any of the four reoptimized native performance maxima** in this finite domain.
The optimal builds bypass the targeted bottleneck. The 2 s rule also reduces
competitive gear counts from 38 to 35 in the four-target task and from 17 to 16
in the short task, using the unchanged native performance threshold. This is an
ineffective power-control intervention in the tested domain.

The predeclared development decision therefore selects a shared cooldown of
**0 seconds** after the objective ties. The unrestricted same-permission design
search selects the identical value. There is no advantage over that baseline.

| Shared cooldown | Worst retained fixed old witness | Worst reoptimized/native envelope ratio | Cells retaining 95% native DPS | Eligible |
| --- | ---: | ---: | ---: | --- |
| 0 s | 1.0000 | 1.0000 | 2076/2076 | True |
| 1 s | 1.0000 | 1.0000 | 2076/2076 | True |
| 2 s | 1.0000 | 1.0000 | 2076/2076 | True |

The reference is the same original native performance, including unchanged old gear and strategies. Reoptimization ranges over the identical 173 legal gear configurations and three policies. Competitive gear counts use 95% of the common native task maximum, so lowering the baseline cannot manufacture reward value.

| Cooldown | Task | Native maximum | Same old witness | Reoptimized | Native competitive gear | Competitive gear under common native threshold |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 0 s | sustained | 307.210 | 307.210 | 307.210 | 17 | 17 |
| 0 s | short_burst | 452.618 | 452.618 | 452.618 | 17 | 17 |
| 0 s | four_target | 455.680 | 455.680 | 455.680 | 38 | 38 |
| 0 s | high_armor | 182.596 | 182.596 | 182.596 | 16 | 16 |
| 1 s | sustained | 307.210 | 307.210 | 307.210 | 17 | 17 |
| 1 s | short_burst | 452.618 | 452.618 | 452.618 | 17 | 16 |
| 1 s | four_target | 455.680 | 455.680 | 455.680 | 38 | 37 |
| 1 s | high_armor | 182.596 | 182.596 | 182.596 | 16 | 16 |
| 2 s | sustained | 307.210 | 307.210 | 307.210 | 17 | 17 |
| 2 s | short_burst | 452.618 | 452.618 | 452.618 | 17 | 16 |
| 2 s | four_target | 455.680 | 455.680 | 455.680 | 38 | 35 |
| 2 s | high_armor | 182.596 | 182.596 | 182.596 | 16 | 16 |

Each nonzero candidate uses 32 labeled native integer seeds per cell. There are 173 unique gear sets × 4 damage tasks × 3 policies = 2076 cells per candidate, or 132864 newly requested physical battles across 1 s and 2 s. These are overlapping source-defined development pools, not randomly sampled independent ecosystems. The racial context here is Human Warrior.

The rule acts after a proc requests an extra main-hand attack batch. Every source uses one per-unit cooldown; a batch of two requested attacks consumes one admission. Both immediate and stored requests are covered. Already-triggered companion auras and original proc cooldowns remain in force. It does not scale damage, change static equipment, or rewrite the behavior of old items each round.

The count bound is on admitted requests, and requires an explicit maximum batch size to imply a requested-attack bound. Stored requests may execute later, so request-time bins do not certify emitted damage in every burst window. Cooldown zero exactly reproduces the native result in the integration comparison, including the event log.

The 1 s run records 205958 admitted and 12572 suppressed requests; the 2 s run
records 192273 admitted and 25825 suppressed requests. These totals are over
66432 native battles per candidate. The largest observed request contains two
attacks. Source-level and request-time counters are preserved in the raw outputs.
The worst fixed-cell performance ratios are 0.97348 and 0.95862 respectively;
the maximum over all configurations is nevertheless unchanged because suppression
does not address the strongest available configurations.

A selected 2 s trace in `mechanism-discovery-v1-trace/EVENTS.log` contains a
suppressed two-attack Ironfoe request and retained requests from other sources.
Its paired `TELEMETRY.json` distinguishes source counts and 10-second request
windows. This deliberately selected one-battle trace illustrates execution;
it is not a frequency or statistical-effect estimate.

The selection was fixed from development data before unseen item updates. All confidence intervals in the machine-readable development analysis are descriptive paired-seed intervals and are not adjusted for selecting configurations. Independent confirmation and all joint P/N/D/L/H/C update requirements are separate evaluations.

Full analysis: `/work/Users/leiyo/wow-forever-sustainability-work/runs/r2-discovery/mechanism-discovery-v1/ANALYSIS.json`.
Frozen selection: `/work/Users/leiyo/wow-forever-sustainability-work/runs/r2-discovery/mechanism-discovery-v1/FROZEN_SELECTION.json`.
Inputs, outputs, binary and source hashes: `/work/Users/leiyo/wow-forever-sustainability-work/runs/r2-discovery/mechanism-discovery-v1/PROTOCOL.json` and `STUDY_PROTOCOL.json`.
