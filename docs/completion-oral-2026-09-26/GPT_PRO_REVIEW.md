# WoW:Forever completion-interface research: independent review entry point

These materials present research results for review; they are not instructions to accept the conclusions or continue an earlier plan. Please focus on whether the paper's actual contribution holds, whether the evidence is sufficient, and whether simpler explanations or counterexamples exist. Detailed materials are in `REVIEW.md`, `CLAIM_EVIDENCE_MATRIX.md`, and `REPRODUCE.md` in the same package; the earlier paper and formal theory are in `references/`. The paper was not modified in this round.

## Problem and added capabilities

Given a released equipment history H and a specified new-equipment target D, does a complete release containing D exist such that every activated loadout stays within the task power caps, the release achieves the required minimum gain, and every old and new source retains sufficient usefulness? The number of helper items is unrestricted, and helper sources must also retain usefulness. The finite model fixes the equipment catalogue, tasks/weights, policies, and thresholds; it does not address all future catalogues or arbitrary release orders.

There are now a reference algorithm, exact CP-SAT and SAT/PB encodings, and six repeated-query services for the same model. Small-domain cross-checks cover 1,200 models, 28,800 decisions, and 7,200 complete-interface comparisons. An independent rational enumerator and a statistical-event replayer can recompute the key conclusions from the compact statistics in the package, without the original server or game engine.

The new certificate service compresses the same simultaneous event into two families of maximal releases: supported and still possible. Within the fixed contract, any new target can receive YES/NO/UNKNOWN without new simulation or alpha. The 24 interfaces occupy about 563 KB; they reproduce 192 registered answers and pass independent checks of all 73,728 target combinations across four models. This tool was delivered after confirmation; it is not counted as an additional performance baseline or an independent empirical finding.

## Strongest findings

The 16 new catalogues were selected from equipment metadata before confirmation, covering four source strata—Warrior, Paladin, Mage, and Druid—and Alliance/Horde. The base catalogues contain 128 related targets, with confidence-supported results of **42 YES, 76 NO, and 10 UNKNOWN**; the fresh-mean answers are 43 YES and 85 NO, and all predicted answers remain consistent.

Of the 76 supported NO answers, 69 have a supported feasible update after removing usefulness-retention requirements. **Retention obligations for legacy-history sources alone suffice to block 42 targets across 10 catalogues; removing legacy-source obligations restores supported feasibility for 28 targets.** This shows that checking power and gain alone misses genuine update barriers. The two attributions can overlap; they do not causally identify skill or racial mechanisms.

The retention standard is a design choice: relaxing the degradation tolerance from 1% to 5% turns 58 of the original 76 NO answers into YES; however, 11 targets across four catalogues remain blocked by source retention. These deliberately selected finite menus cannot establish that the game as a whole is “generally unsustainable.”

The earlier gloves data also yield a new implication: both first-release histories still permit some gaining updates, but releasing Arcanist Gloves first blocks the specified Magister gloves-and-pants target, whereas releasing Sorcerer's Gloves first permits it. The difference holds throughout the entire ±20% parameter box; source retention alone excludes the target under the bad history, without a power cap or minimum gain. This is a post hoc implication of the earlier statistical event, not a new independent confirmation.

## Counterresults that must be preserved

- In the main single-query benchmark, CP-SAT and SAT both solve 240/240 cases, while reference Python solves 205/240. Low-conflict controls can also time out under this reference implementation; this reflects implementation/enumeration cost and does not prove that the problems themselves are hard.
- Interfaces reduce repeated reference solving, but show no clear native speed advantage over strong incremental baselines. For the same 6,160 new-catalogue targets, reference caching/reference interfaces take about 298.63/14.57 seconds; incremental SAT, SAT interfaces, and on-demand maximal SAT caching all solve every target, taking about 0.0986/0.0962/0.0995 seconds. Millisecond differences come from one timing per history and do not establish a reliable speedup. In synthetic tests, both on-demand SAT services solve all 67,445 targets; the full SAT interface leaves 6,392 unresolved, and the reference interface also has a timeout that returns no representation.
- The 64 paired targets across eight nested expanded catalogues have no mean or confidence-answer flips. There is no supported native blocking case due to helpers' own retention obligations; both shallow heuristics find all 43 feasible base mean targets.
- Two original plans among the 24 positive predictions for expanded catalogues fail on fresh means, although their targets still have alternative plans. Both failures belong to one Warrior catalogue. Stable existence does not imply a robust selected plan.
- Task projection produces five base mean flips, but zero pairs of opposite answers both receive confidence support. It changes the task set, weights, and required task caps together, so it cannot be interpreted as an isolated weight effect.

## Evidence limits and review priorities

The new main confirmation spends nominal alpha=.04, with .0025 for each of 16 catalogues; the reserved .01 is unused. The old event's .05 is accounted for separately, giving a nominal old-plus-new union bound of .09; this cannot be called a new overall .05. Intervals use a fixed-sample paired-t approximation; the packaged code checks logical consequences of the finite event, not population coverage. Every native physical cell has 16,384 runs, and all 1,712 confirmation cells are complete; abstract computations do not count as native coverage. Solver UNSAT is not an independent DRUP proof.

Please assess three points:

1. Are “complete repairability for a specified future target and legacy-source retention barriers” sufficient as the paper's main theme? Is the added evidence or research capability relative to existing theory clear?
2. After allowing generic solvers to win and retaining full compilation costs and failures, what practical value can interfaces still claim? Which statements need narrowing?
3. Are there concrete counterexamples that would overturn source attribution, the continuous parameter box, or statistical-reuse guarantees? Should the next step focus on selecting release plans with sufficient statistical margin rather than adding similar cases?

`review-v2.zip` contains full responses/compact moments, native certificates, compressed per-query records, figure sources, source code, frozen identities, and a failure ledger. Raw per-battle outputs remain on the server with absolute paths and content hashes; this is not a summary package containing only figures and tables.
