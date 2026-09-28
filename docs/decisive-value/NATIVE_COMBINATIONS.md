# Native combination screen

On ten development-selected release/race cases, unrestricted combinations pass none of the joint P/N/D/L/H/C plus decision-gain tests. An optimized one-row additive item budget passes six, exactly matching the arbitrary-subset reference in this screen. There is no demonstrated advantage over the generic rule class.

This is a reanalysis of the unchanged R4 `baseline-v1` table, with 16 battles per cell and no new native execution. Four ecologies are included: `static_skill`, `timing_extra`, `timing_shared`, and `resource_haste`. Both Human and Orc Warrior are retained. Each selected two-item release has all 36 legal old/old, old/new, and new/new configurations, including all 16 protected old configurations, all three policies, and all eight existing combat tasks. Gear is fixed during combat; each side can select its best allowed gear and policy for the known task.

Decision gain is the new optimized DPS minus the fully reoptimized old DPS, scaled by the frozen initial task optimum. The development threshold is 1% on at least one of eight equally weighted tasks. Caps remain 105% of the initial task optimum. The original behavior-distance D is evaluated independently, and all six existing predicates remain required for a strict positive result. Source deletion reoptimizes every remaining configuration and policy. L protects the initially registered source identities; initially unregistered identities are listed explicitly, not silently merged into other sources.

The comparison uses the same native response table for every method:

- Natural composition admits every legal combination.
- The all-power-safe mask is a full-information diagnostic, not a predictive rule.
- The singleton-increment rule assigns each new item its largest positive singleton gain divided by the 5% cap headroom, assigns zero to old items, and bounds their sum by one. It is an observed-component heuristic, not an established composition condition.
- The optimized generic rule has one nonnegative additive budget over the same ten old/new item-incidence coordinates. It preserves every old configuration and jointly requires P/N/D/L/H/C and G.
- The arbitrary-subset reference has unrestricted admission variables, preserving all old configurations and identical ecological obligations.

The gain solver enumerates the finite disjunction of power-safe gain witnesses. A forced witness is an admission constraint only: the original historical D references and H definition are retained. Any one qualifying task suffices at the declared mass threshold. Exhaustive infeasibility is reported only when every witness model proves infeasible; no time limit is called an impossibility result. The screen produced no unresolved solver cases. It does not estimate population confidence.

| Release | Race | Largest retained decision gain | Generic/reference strict result |
|---|---|---:|---|
| Felstriker 12590 + Deathbringer 17068, static_skill | Human | 4.765% | Both pass |
| Eskhandar 18203 + Gri'lek 19951, timing_extra | Human | 4.538% | Both pass |
| Eskhandar 18203 + Gri'lek 19951, timing_extra | Orc | 1.545% | Both pass |
| Gri'lek 19951 + Heroism legs 22000, resource_haste | Human | 4.740% | Both pass |
| Eskhandar 18203 + Thunderfury 19019, timing_shared | Orc | 2.515% | Both pass |
| Thunderfury 19019 + Draconic Infused Emblem 22268, timing_shared | Orc | 2.459% | Both pass |

The singleton-increment rule rejects all useful releases in these ten cases. A price based only on the strongest old partner can rule out a new item entirely, even though a weaker partner makes a useful, cap-safe configuration. The generic rule can price both old and new components and represent those compensations. This is a development explanation to test prospectively, not a new theorem inferred from the fitted table.

Deleting either source removes the full gain for the Human Gri'lek/22000 pair and the two Orc Thunderfury pairs. In contrast, deleting Eskhandar from the two `timing_extra` positives causes zero decision-frontier loss: Eskhandar satisfies N there, but those cases are not evidence that both sources are necessary for G. Static-skill source deletion has nonzero but unequal effects.

For review, each selected generic mask was rewritten as a small integer budget without changing a single admitted configuration. Weights are between zero and three, budgets between three and four, and rejected configurations have integer separation of at least one. Each rule has ten labeled features, four or five nonzero weights, and one inequality. The serialized predicate and item-weight record occupies 282–284 bytes; that count excludes the shared task/domain/protocol description. These are fitted finite-domain rules. Prices for unseen item identities remain undefined.

Artifacts under `WORK_ROOT/artifacts/decisive-value` are `LINE_B_COMBINATIONS.json`, `LINE_B_COMBINATIONS.csv`, and `LINE_B_INTEGER_RULES.json`. The analysis-only receipt is `runs/decisive-value/combination-screen-v1`. Maintained code is `value_native.py`, `value_admission.py`, `value_combinations.py`, and `value_rule_display.py`; four focused admission tests pass. Prior R1–R6 code, binaries, and results were read without modification.
