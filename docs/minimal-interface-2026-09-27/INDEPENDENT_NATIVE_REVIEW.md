# Independent scientific review of the native interface audit

The review passes. No actionable numerical, logical, or evidence-direction defect was found in `mi_native.py` or its saved native outputs. This is a read-only review: all 96 native checkpoint hashes remained unchanged. No native battle or additional alpha was used.

The independent review script is `scripts/review_minimal_interface_native.py`. Its receipt is `checks/INDEPENDENT_NATIVE_REVIEW.json` under the new audit artifact root. It does not import `mi_native.py`, the certificate service, or its low-order and attribution helpers.

## What was independently checked

- Recomputed order-1, order-2, and order-3 counts across all 184,320 target queries using explicit containment of low-order bad subsets, rather than the production subset-minimum transform.
- Checked all proper subsets of every target to recover all 968 saved minimal obstructions: 562 exact mean-table and 406 certified statistical rows, across dependent contract variants.
- Replayed the statuses and accepted-publication counts of all 3,654 attribution scopes, retaining power, gain, and all source obligations separately.
- Compared all 1,024 Druid02 target answers against the separate scalar-moment B3 evaluator. There were no mismatches.
- Read the exact rational oracle and checked the YES/NO/UNKNOWN directions, history gate, complete-upper requirement, projection, witness payload, and target-universe convention.

These checks supplement, rather than replace, the original moment/source/manifest verification. Statistical inference remains a fixed-N simultaneous paired Student-t approximation, not a distribution-free guarantee.

## Primary results and their denominators

The 16 primary base contracts contain 16,384 enumerated target sets. The exact finite-mean order-1/2/3 false-positive counts are 403/9/0. The certified counts are 351/3/0. Their distinct evidence levels must remain visible; the six additional exact order-2 misses are not certified population failures.

The primary certified obstruction inventory is order 0: 2; order 1: 40; order 2: 20; order 3: 2. The two order-0 obstructions occur in Warrior03 and Paladin02. Their initial histories are supported, but no gaining completion exists. The empty target has no proper subsets, so its minimality check is vacuous. These rows are valid degenerate cases and should not be described as higher-order item interactions or zero performance.

All three certified order-2 misses occur in the same Druid02 contract:

1. `{a04, x1, x3}`;
2. `{a06, x1, x3}`;
3. `{a04, a06, x1, x3}`, their four-item union.

Thus three missed decisions correspond to two minimal triples, not three independent triples. The item sets are correlated target queries in one fixed catalogue.

The primary UNKNOWN-blocked counts are 974/4/0 for orders 1/2/3. A blocked case has a full target certified NO, no checked low-order NO subset, and at least one checked low-order UNKNOWN subset; it is not counted as a certified miss. All four order-2 blocked cases occur in Mage02. The same contract has 44 *full UNKNOWN* targets with no low-order NO at order 2. Those are a different class and are separately recorded. Neither UNKNOWN category is YES or NO.

## Attribution is a certified counterfactual, not unique causality

The code uses two sound directions. A supported completion after deleting one obligation group establishes that the group is necessary to the full obstruction under the fixed remaining obligations. A complete optimistic exclusion with only that group retained, together with a supported value-only completion, establishes that the group is sufficient relative to the fixed cap/gain requirements. These are scoped counterfactual statements. Labels may overlap and do not constitute a unique causal decomposition.

Both primary Druid triples have `none=YES`, `only_history=NO`, and `drop_history=YES`. Complete enumeration therefore certifies both necessity and sufficiency of legacy retention in this contract. For the named a04 triple, the separate two-step B3 proof additionally establishes exclusion from legacy source obligations alone while every physical row is cap-safe. The simpler saved two-step proof fails for the a06 triple, but the complete enumeration still certifies its legacy-only attribution. Failure of that sufficient proof must remain distinct from failure of the complete result.

No helper-only or mixed label is produced by the implemented certification rule. That negative result does not prove that helper or mixed mechanisms are absent throughout the catalogue or full model. Power/gain constraints remain fixed in the only-group tests; a target-self-retention label alone does not assert that every physical configuration is cap-safe.

## Secondary native breadth

At tolerance 2%, ten certified minimal triples occur in three other registered menus: Paladin01 has two, Mage02 has two, and Druid03 has six. All ten have supported value-only completions, `only_targets=NO`, and `drop_targets=YES`, certifying target self-retention as both a sufficient and necessary obligation group under the stated contract.

These are post-hoc consequences of the existing simultaneous events, not new prospective native experiments. The secondary aggregate of 12 triple rows includes the two original Druid02 triples repeated at tolerance multiplier 1. It must not be reported as 12 new native triples or as 64 independently sampled catalogues. The 96 total contracts consist of 16 base contracts plus dependent expansion, task-projection, and tolerance reanalyses. None supports a game-wide prevalence estimate.

## Projection and representation scope

The target universe is fixed from metadata as `E = I minus H`, before response evaluation. For full publications containing H, removing the same H is injective. Consequently the native full and target maximal interfaces have the same cardinality and zero projection merges. Reduced serialization from omitting repeated history labels is not structural antichain compression. Witness payloads are explicitly saved, and possible witnesses remain optimistic test witnesses rather than certified feasible constructions.

The possible interface is exhaustive in every audited contract. The implementation correctly requires completeness before issuing NO and preserves invalid/unknown initial-history gates. The target equivalence checks therefore have full finite-powerset coverage, without extending their conclusion to another catalogue, threshold contract, task set, or native population.

## Reproduction

Run with the repository environment configured. The completed review used a single-worker tmux session named `mi_native_independent_review`:

```bash
source scripts/env.sh
python scripts/review_minimal_interface_native.py \
  --root /work/Users/leiyo/wow-forever-sustainability-work/artifacts/minimal-interface-native-audit-2026-09-27 \
  --output /work/Users/leiyo/wow-forever-sustainability-work/artifacts/minimal-interface-native-audit-2026-09-27/checks/INDEPENDENT_NATIVE_REVIEW.json
```
