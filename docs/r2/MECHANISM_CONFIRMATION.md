# Fresh-seed mechanism confirmation

Five fixed witnesses were frozen before 128 new integer seeds per condition. The four development-optimal task witnesses are unchanged in every paired seed. They demonstrate achieved native performance that the 2 s intervention cannot reduce; this is a lower bound on the post-intervention optimum, not a claim of global optimality.

| Fixed witness | Native DPS | 2 s DPS | Paired change | Bonferroni 95% interval, DPS |
| --- | ---: | ---: | ---: | --- |
| native_task_optimum_sustained | 305.280 | 305.280 | 0.000 | [0.000, 0.000] |
| native_task_optimum_short_burst | 451.301 | 451.301 | 0.000 | [0.000, 0.000] |
| native_task_optimum_four_target | 459.480 | 459.480 | 0.000 | [0.000, 0.000] |
| native_task_optimum_high_armor | 181.463 | 181.463 | 0.000 | [0.000, 0.000] |
| development_worst_fixed_loss | 354.732 | 346.955 | -7.777 | [-11.660, -3.893] |

Intervals use paired seed differences and a normal approximation with Bonferroni adjustment for the five predeclared contrasts. Selection used only the earlier development seed block. Raw telemetry records whether these old witnesses produced any requests that the intervention could suppress.

Frozen selection and full results: `/work/Users/leiyo/wow-forever-sustainability-work/runs/r2-discovery/mechanism-confirmation-v1`.
