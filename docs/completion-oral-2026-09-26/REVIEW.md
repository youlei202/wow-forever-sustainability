# Completion-interface reuse, independent equipment catalogues, and certificate robustness

This round adds recomputable complete-update audits, certificate queries for new targets within a fixed contract, and a fair six-method reuse comparison. **Interfaces are reusable, but native data have not demonstrated a clear additional speed benefit over strong incremental SAT services**: all three SAT services solve all 6,160 new-catalogue targets in about 0.10 seconds; full compilation also leaves unresolved cases on synthetic models with large outputs. Independent native confirmation supports 42 completable targets, excludes 76, and leaves 10 unresolved; all predicted existence answers transfer, but two concrete plans in expanded catalogues fail. The target-specific obstruction in the earlier gloves data holds throughout the entire ±20% parameter box, through valid propagation of the old simultaneous event. The strongest main-text claim concerns how legacy-source retention obligations block specified future targets; the next step should focus on choosing concrete release plans with sufficient statistical margin.

The result most suitable as the paper's main theme is currently: **given a new-equipment target, audit whether a complete update exists that preserves the usefulness of all released sources, and distinguish which retention obligations cause the obstruction.** Checking power and gain alone accepts some updates that actually obsolete legacy sources. Independent evidence now supports this problem in four native source structures; its value does not depend on a specialized solver universally outperforming generic solvers.

The clearest overturned speed expectation is that “a low conflict parameter alone predicts this reference implementation's unknown-frontier solving cost.” SAT and CP-SAT both solve all 240 main benchmark problems, while the reference implementation solves 205; 31 of its 35 timeouts lack a simple cap-violating conflict among mandatory configurations, including controls with structurally no conflicts between optional sources. These reflect the reference implementation's enumeration cost and do not establish that these particular problems are intrinsically hard. The most important remaining research gap is **how to select concrete release plans with sufficient statistical margin in larger practical catalogues before confirmation**; this round demonstrates the problem and provides auditing capabilities, but does not develop or confirm a new robust plan-selection algorithm.

## 1. Added research capabilities

The same finite contract now supports exact single-query solving, repeated target queries, complete or partial interface compilation, and statistically supported constructive/exclusion audits. The contract fixes history, optional equipment and policies, task weights, power caps, minimum gain, and usefulness-retention thresholds; helper counts are unrestricted, every released source must retain usefulness, and every activated physical loadout is checked.

The two generic exact encodings and the reference algorithm were cross-checked on 1,200 small models, 28,800 decisions, and 7,200 complete-interface comparisons. A separate independent rational subset enumerator can recompute native mean answers from packaged means, paired covariances, and sample sizes. Statistical certificates also enumerate the entire finite release space: a supported plan gives YES; NO requires excluding every optimistic candidate; all other cases remain UNKNOWN.

The new certificate-query service compiles each catalogue into two families of maximal releases, representing supported and still-possibly-feasible plans. The 24 interfaces total about 563 KB; they reproduce all 192 registered answers and pass independent checks of all 73,728 target combinations across four base/expanded models. New targets within the fixed contract directly reuse the original simultaneous event without new simulations or significance budget; unknown items are rejected. This tool capability, delivered afterward, is not counted as a seventh performance baseline or an additional independent experiment.

The reuse comparison includes six services: solving from scratch each time, reference-algorithm caching, complete reference interfaces, persistent SAT with caching, complete SAT interfaces, and on-demand caching of SAT plans extended to maximality. All services receive the same complete response table and the same unique target sequence, with the same single-thread setting and budget. The last baseline avoids disadvantaging generic solvers merely because they return smaller plans.

## 2. What independent native confirmation changes

The 16 catalogues were registered from equipment metadata before viewing confirmation results; the four source strata actually run Warrior, Paladin, Mage, and Druid, with 8 fixed targets per catalogue. Each physical cell has 16,384 runs, for 1,712 cells and 28,049,408 new confirmation simulations, with no missing or failed calls.

| The 128 target queries in base catalogues | Result |
|---|---:|
| Certificate-supported completion | 42 |
| All allowed helper combinations excluded | 76 |
| Statistically unresolved | 10 |
| YES / NO on fresh means | 43 / 85 |
| Answer flips between predictions and fresh means | 0 |

Of the 76 supported NO answers, 69 have a supported feasible update after removing usefulness-retention requirements. Retaining only legacy-history source obligations suffices to block **42 queries across 10 catalogues**; removing those obligations restores supported feasibility for **28 queries across 10 catalogues**. The former shows that legacy-source retention can itself create a barrier; the latter shows that it is indispensable in these instances. These labels can overlap and must not be added together.

Queries blocked by legacy sources alone are distributed as Druid 11, Mage 3, Paladin 14, and Warrior 14. These distinguish constraint responsibility within update contracts; they do not prove causal effects of a skill, proc, or racial mechanism. Target items' own retention obligations can also block updates; this round finds no supported native case where helpers' own retention obligations change the answer.

## 3. Thresholds and concrete plans both matter

Relaxing allowed usefulness degradation from 1% to 5% changes 58 of the original 76 supported NO answers into supported YES answers. The four predeclared tolerance levels give:

| Tolerance | YES | NO | UNKNOWN |
|---|---:|---:|---:|
| 0.5% | 21 | 92 | 15 |
| 1% | 42 | 76 | 10 |
| 2% | 68 | 50 | 10 |
| 5% | 106 | 14 | 8 |

At 5%, source retention still blocks 11 queries across four catalogues. However, the data do not support the conclusion that “most updates are inherently unsustainable”; the retention standard is itself a policy choice that affects design.

Stable existence answers do not guarantee stable selected plans. The original plans for all 43 base YES predictions pass fresh-mean checks, but only 38 receive confidence support. Of the 24 YES predictions in expanded catalogues, two original plans fail on fresh means while alternative plans still exist for the same targets; both belong to one Warrior catalogue and cannot count as two independent mechanism discoveries. All 67 original plans are recomputed individually; alternatives are not used to hide original-plan failures or unresolved outcomes.

The earlier gloves data also yield an informative new implication: after releasing Arcanist Gloves first, the specified Magister gloves-and-pants target cannot preserve legacy-source usefulness with any number of helpers; after releasing Sorcerer's Gloves first, it is completable. Both histories still allow some gaining updates. This difference holds throughout the entire ±20% parameter box; the obstruction under the bad history does not even require power-cap or minimum-gain conditions. It is a new post hoc implication of the old event, not a new independent confirmation experiment.

## 4. Complete computational comparison

The main single-query benchmark contains 120 fixed-frontier and 120 unknown-frontier problems; additional paired comparisons use the same mean tables derived from all eight old histories and sixteen new catalogues. Extra repetitions check execution stability and do not increase the number of independent problems.

| Main synthetic problems | Reference Python | CP-SAT | SAT/PB |
|---|---:|---:|---:|
| Fixed frontier, solved / 120 | 112 | 120 | 120 |
| Unknown frontier, solved / 120 | 93 | 120 | 120 |

The reference algorithm is faster on some fixed-frontier problems solved by both sides; the results therefore support neither universal superiority of specialized methods nor generic methods being faster on every problem. The Python reference implementation and optimized solver libraries also differ in implementation engineering. Missing internal timeout counts remain empty and cannot imply a zero conflict parameter.

Repeated queries cover 36 histories and 216 services, recording 495,454 processed queries. Each method receives the same unique target stream; each new-catalogue history has 385 targets, totaling 6,160. The following costs include model construction, compilation, validation, and in-memory serialization/reloading; work times are summed across histories and are not total wall-clock time for parallel execution.

| New catalogues: the same complete target pool | Histories fully solved / 16 | Total elapsed work time, seconds |
|---|---:|---:|
| Reference solving from scratch | 15 | 1,021.45 (some unresolved and unprocessed) |
| Reference caching | 16 | 298.63 |
| Complete reference interface | 16 | 14.57 |
| Incremental SAT with caching | 16 | 0.0986 |
| Complete SAT interface | 16 | 0.0962 |
| On-demand maximal SAT plan caching | 16 | 0.0995 |

Complete interfaces substantially reduce the reference implementation's repeated work, but generic incremental services are already fast. In new catalogues, SAT interfaces cross the incremental SAT cost at some registered query prefix solved completely by both methods in 12/16 histories; first observed crossings occur at 1, 10, 100, and 385 queries, in 1, 2, 2, and 7 histories respectively. This does not mean they remain ahead afterward. Across the full target pool, the total times of the three SAT services differ by only about 2–3 milliseconds. This round has no repeated timing trials for repeated-query services, so these differences cannot establish a reliable or practically important speedup. The eight old histories show a similar result: the three SAT services solve the same 12,096 targets in about 0.110, 0.107, and 0.112 seconds.

Synthetic tests more clearly show the cost of full compilation: incremental SAT and on-demand maximal caching solve all 67,445 targets at total costs of about 2.14 and 2.70 seconds. The reference interface fully solves only 10/12 histories and the SAT interface 11/12; the reference interface leaves 7,289 processed-but-unresolved and 10,000 unprocessed queries, while the SAT interface leaves 6,392 unresolved. A partial interface lacking a plan for a target means only UNKNOWN. One reference-interface timeout returns no serializable representation; its plan count is missing, not zero. A service status of COMPLETE means only that the query stream was processed, not that all targets were resolved.

Each history has a total budget of 900 seconds, with 720 seconds allocated to complete-interface search/enumeration; output postprocessing is also charged, so an actual compilation call can exceed 720 seconds. Full compilation's usefulness depends on representation size, the target stream, and existing on-demand caches; it cannot be judged solely by low query costs after compilation.

The measured objects are in-memory services after shared dependencies are preloaded. Persistent disk archives and general startup costs have separate receipts and are outside this timing conclusion; no cold-start deployment or disk-throughput claim follows. Optional secondary comparisons with longer limits and multiple threads were not run.

## 5. Negative results to preserve

Optional-equipment expansions in eight catalogues measure all new loadouts; the 64 paired targets show no mean or confidence-status flips. Projection from four tasks to two changes mean answers for five base targets, but no pair of opposite answers both receives certificate support. This simultaneously changes the allowed task set, weights, and required task caps, so differences cannot be attributed to weights alone. Weak-source repair and two-step helper search both find all 43 feasible base mean targets, so these native data do not establish a need for deep specialized search; neither method replaces NO audits that exclude every combination.

## 6. Main-text recommendation and evidence limits

The recommended main theme is “complete repairability for specified future targets and source-retention barriers,” supported by the earlier gloves counterexample without power conflicts, obligation attribution in 16 new catalogues, and results on tolerances and concrete plan stability. The computational contribution should be framed, according to the final measurements, as exact planning interfaces and certificate tools, without presupposing universal speedups. Source selection, all negative results, nested expansions, and unresolved projections belong in traceable supplementary materials. The paper was not modified in this round.

New confirmation uses a nominal .04 simultaneous-event budget, divided among 16 catalogues at .0025 each; the reserved .01 is unused. The old event's .05 has already been spent separately, so the old-plus-new main events cannot be relabeled an overall .05. Intervals use a fixed-sample paired-t approximation and have no distribution-free exact-coverage guarantee. Catalogues and targets are also not probability samples of game content, and the 128 related targets cannot be treated as independent binomial trials.

`REPRODUCE.md` gives recomputation commands independent of the original server; `CLAIM_EVIDENCE_MATRIX.md` identifies each conclusion's evidence level; complete costs and failure records are in `data/benchmark/` and `NEGATIVE_AND_UNRESOLVED.csv`, respectively. The archive retains only the code, statistics, finite tables, certificates, figure sources, and receipts needed for verification; raw battle outputs and environments remain in indexed work archives.
