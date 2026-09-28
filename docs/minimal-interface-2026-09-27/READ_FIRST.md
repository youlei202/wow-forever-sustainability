# Minimal target-interface audit — 2026-09-27

Phases A–C are complete. The failure of the first Phase C checker is preserved; corrected version v2 passed. The paper was not changed, no new native battles were run, and no additional alpha was spent. Phase D was not activated.

Authoritative output directory: `$WOWFS_WORK_ROOT/artifacts/minimal-interface-native-audit-2026-09-27/`. This note is included in `WOW_MINIMAL_INTERFACE_NATIVE_REVIEW.zip` together with machine-readable results, source code, frozen inputs, and failure archives.

The final second-version review bundle is at `artifacts/minimal-interface-review-v2/WOW_MINIMAL_INTERFACE_NATIVE_REVIEW.zip`. The first version reproduced the scientific JSON exactly, but its portable wrapper failed by comparing integer keys against JSON string keys. That first bundle remains unchanged; the failed script, logs, hashes, and correction note are included in the second version under `packaging-failures/`.

## 1. Does target projection preserve every query answer?

Yes. All 184,320 target subsets were enumerated across 96 fixed contracts. The exact fresh-mean, supported, and possible interfaces were each checked against the full publication family, and all were equivalent: 552,960 comparisons across the three modes in total. The primary analysis comprises 16 independently registered base menus and 8 nested expanded menus: 24 contracts, 81,920 target queries, and 192 originally registered queries. The other 8 task-projection contracts and 64 tolerance contracts are reported separately. All 768 registered query rows across the 96 contracts were reproduced; they must not be counted as 768 independent native observations.

The target universe is fixed as `E=I\H` under the original certificate's contract permitting arbitrary targets within a menu; it was not selected based on outcomes. Every physical cross-product configuration and any number of helpers within each menu are retained. The empty target still requires positive gain. Possible witnesses satisfy only necessary interval conditions and are not certifiable feasible constructions; NO is permitted only when the complete upper interface provides no coverage. UNKNOWN and initial-state anomalies have distinct semantics.

## 2. How many certifiable decisions do low-order summaries miss?

| Contract group | Target pool | r=1 | r=2 | r=3 | UNKNOWN-subset blocks at r=1/2/3 |
|---|---:|---:|---:|---:|---|
| 16 primary base menus | 16,384 | 351 | 3 | 0 | 974 / 4 / 0 |
| 8 nested expanded menus | 65,536 | 8,632 | 0 | 0 | 570 / 12 / 0 |
| 8 frozen task-projection contracts | 36,864 | 8,260 | 0 | 0 | 122 / 0 / 0 |
| 64 frozen tolerance contracts | 65,536 | 3,199 | 189 | 0 | 1,450 / 410 / 0 |

A miss here strictly requires the full target to be certified NO while every subset of size at most r is certified YES. UNKNOWN is never treated as YES. The UNKNOWN-block column requires a full-target NO, no low-order NO, and at least one low-order UNKNOWN. Counts for which the full target itself is UNKNOWN are stored separately in `LOW_ORDER_ABLATION.csv` and are not included in that column.

The 3 base misses at r=2 are `{a04,x1,x3}`, `{a06,x1,x3}`, and `{a04,a06,x1,x3}` in Druid validation-02. The first two are minimal triple obstructions; the third is their four-item union and must not be described as a third minimal triple or a minimal four-item obstruction. The primary base exact fresh-mean misses at r=1/2/3 are 403 / 9 / 0; these finite-mean-table conclusions do not replace statistical certification.

## 3. Which minimal-obstruction orders appear in each catalogue?

See `tables/BASE_CATALOGUE_REPRESENTATION.md` for the per-menu inventory and `tables/representation_audit.csv` for all 96 contracts. All target IDs, native item IDs, factions, attributions, tolerances, and counts of exhaustive helper exclusions are in `tables/native_minimal_obstruction_inventory_all_contracts.csv`.

Across the 16 primary base menus, there are 2 order-0, 40 order-1, 20 order-2, and 2 order-3 obstructions. Only Druid validation-02 has certified order-3 obstructions under the primary contracts. The order-0 obstructions in Warrior validation-03 and Paladin validation-02 mean that even the empty target has no gaining completion; they must not be dropped or misreported as invalid initial states. The 8 expanded contracts have 37 order-1 and 37 order-2 obstructions, with none certified at order 3 or higher.

The frozen 2% tolerance contracts contain another 10 triple obstructions: two in Paladin validation-01, two in Mage validation-02, and six in Druid validation-03. These change the normative retention tolerance and therefore must remain separate from the primary 1% contracts. They involve no new sampling and cannot increase the count of independent menus. The 12 triple records across the 64 tolerance contracts also include the original two Druid triples repeated at 1%.

## 4. Was the Druid pairwise-YES / triple-NO result independently reproduced?

Yes. Alliance / Night Elf / Druid validation-02: A=Shivery Handwraps (`a04`), B=Mooncloth Boots (`x1`), C=Premier Knight-Champion's Lunarhide Boots (`x3`). All 4,160 simultaneous contrast directions were recomputed independently, coefficient by coefficient, from the original compact moments, without calling the original certificate-query service or inference/replay functions. AB, AC, and BC are all YES; ABC is NO. Native N=16,384, and the original event has alpha=.0025.

All 32 physical configurations are cap-safe, with a minimum cap lower-bound margin of 0.6601399294 DPS. All 128 publications containing ABC satisfy the sufficient cap and gain conditions but are excluded by necessary retention conditions. Covered diagonal intervals for positive reference values, together with monotonicity, establish the entire `e∈[1.0%,1.1%]` interval; this is not merely a check of two points or a reallocation of alpha.

All 6 saved rows of the two-step source certificate and the margins of all 6 pair witnesses were reproduced. The 4 failed rows of the two-step certificate remain: a04 at 1.2%, and a06 at 1.0/1.1/1.2%. These only indicate failure of that sufficient exclusion proof and must not be converted into target YES decisions. See `DRUID_TRIPLE_RECHECK.json`.

## 5. What causes the obstructions?

Of the 64 certified minimal obstructions in the primary base contracts, 32 establish attribution to legacy-history retention, 29 to target self-retention, and 3 to power/composition safety; the corresponding expanded counts are 29 / 42 / 3. No helper-only or mixed attribution was established in the primary contracts, which does not imply that those mechanisms are impossible. The category definitions allow overlap. The scope of causal attribution is established through sufficient witnesses after removing or retaining only specific obligations, together with exhaustive exclusion using necessary conditions.

Legacy retention alone suffices to exclude both Druid triples in the primary contracts, and removing that obligation yields a sufficient feasible witness. The newly listed triples under the 2% contracts are attributed to target self-retention. Across all 96 contracts, 1 unresolved attribution is retained; see the complete trace for its other failed obligations and UNKNOWN outcomes under relaxed contracts. Aggregate values describe only these fixed contracts.

## 6. Does native target projection substantially compress the explicit interface?

There is no structural reduction in the number of entries. Every publication contains H, and E=I\H, so projection preserves inclusion and is injective. Every contract has `|K_H|=|A_H|`, with 0 merges. Removing repeated history labels shortens JSON without metadata, but adding the complete witness payload increases its byte count. All three measured byte counts are in `TARGET_INTERFACE_AUDIT.csv`; no claim is made that the explicit antichain is the shortest encoding.

In the abstract pair-exclusion comparison, the 65,536 explicit maximal sets at p=16 serialize to 2,949,121 bytes, whereas 16 rules require only 157 bytes. The query spot checks for p=12/16 do not exhaust the full powerset; the scope of the structural identity and of checks over all maximal sets is reported separately.

## 7. Did the theory implementation checks fail?

The first version did fail. A subset-enumerator bug caused 179 random inputs to violate the downset premise, producing 716 mismatches within the stated guarantee range. The complete failed inputs, source code, and outputs are preserved in `theory/` without being overwritten. Only the enumerator was corrected, and independent literal-oracle regression tests were added before rerunning in `theory/v2/`; the construction, thresholds, and random seeds were not tuned.

All 2,466 checks passed in the corrected version: all 199 downsets for n=0…4, 64 random downsets each for n=5…7, positive/negative construction pairs for r=1…10, and the 5 required perturbation magnitudes. None of the 1,644 checks within the strict guarantee range failed. Deterministic boundary counterexamples at η=.50/.51 are preserved separately and are consistent with the absence of a guarantee there. No counterexample to the supplied mathematical argument was found. Finite checks do not experimentally prove a universal theorem and do not constitute a review of bibliographic originality.

## 8. Was Phase D activated?

No. The correctness checks in A–C are complete. The current frozen data already provide a full quantification of information loss, an independent triple certificate, and triple mechanisms in other classes at another fixed tolerance. Further prospective sampling would primarily add independent breadth; it is not a condition for the theorem or completion of this audit. The current evidence does not provide a stronger justification for additional battles. No fictitious selection/protocol/confirmation records were written. Phase D is `not_run`, not a zero effect. If reopened, at least four metadata-only directories should first be frozen separately, before inspecting new outcomes.

## 9. Which results belong in the main text, supplement, and negative-results ledger?

- Main-text candidates: the exact scope of the target-semantics theorem, the Druid triple and legacy-source exclusion, and the 351/3/0 ablation plot for the 16 base menus. Emphasize that the 3 misses are not 3 minimal obstructions.
- Supplement candidates: all 24 primary contracts, task projections, tolerance contracts, every witness/exclusion, per-obligation attribution, independent reproduction methods, and checks of the abstract construction and symbolic representation.
- Negative-results ledger: no reduction in entry count from projection; no certified order-3 obstruction in 15/16 primary menus; all UNKNOWN outcomes, order-0/order-1 obstructions, unresolved attribution, four failed rows of the source proof, the first-version checker failure, and more compact symbolic rules. Negative results from the original review-v2 are also archived unchanged.

## 10. How does this audit materially strengthen the case for an oral presentation?

The contribution is verifiable scope and decision loss: exhaustive equivalence of target semantics, quantified false acceptance by low-order summaries, independent reproduction of the native retention triple, complete preservation of uncertainty, and a demonstration that semantic minimality differs from storage minimality. It connects the existing Druid example to a full-target audit and the general construction. It does not add native sampling, establish prevalence across the game, demonstrate a speed advantage for the original algorithm, or guarantee acceptance for an oral presentation. All 59 order-two-or-higher obstructions already present in the latest handoff were reproduced; this audit additionally supplies the 2 empty-set and 77 singleton obstructions absent from the original inventory.

Statistical YES/NO decisions are conditional on the original fixed-N simultaneous paired-t Bonferroni approximation and its assumptions; they are not a distribution-free guarantee. See `CLAIM_EVIDENCE_MATRIX.md` for evidence categories and all limitations.
