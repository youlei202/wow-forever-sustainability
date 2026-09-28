"""Research report and anonymous-manuscript numbers from verified artifacts."""
import csv
import json
from pathlib import Path
import shutil
from wowfs.paths import SOURCE_ROOT,setup_paths,atomic_json


def csvrows(path):
    with path.open() as f:return list(csv.DictReader(f))


def main():
    root=setup_paths();out=root/'artifacts/final-completion-capacity';paper=out/'paper'
    data=json.loads((out/'SUMMARY.json').read_text());audit=json.loads((out/'EXECUTION_AUDIT.json').read_text())
    upper=csvrows(out/'CAPACITY_UPPER_BOUND_CERTIFICATES.csv');oracle=csvrows(out/'SMALL_DOMAIN_ORACLE.csv')
    affine={c['context_id'] for c in data['contexts'] if c['confirmation_affinity']}
    expected={'large_gap':4,'dense':1,'weaker_direct':4,'fixed_budget':3}
    for row in data['sequences']:
        if row['context_id'] in affine and row['variant']=='interior':
            assert row['confirmed_prefix']==expected[row['regime']]
            assert row['minimum_legacy_mass']==1 and row['K']==1
    assert len(affine)==51 and audit['status']=='pass'
    numbers=r'''\newcommand{\FCAbstractResults}{In 51 contexts across eight classes, independently checked affine response models support source-preserving paths of four updates in large-gap ecologies versus one in dense controls, with a conditional continuous upper bound of two for the dense family. Smaller direct increments support four updates and a fixed one-row budget supports three. Five non-affine Warlock contexts and three event-changing mechanism families expose limits to this transfer.}
\newcommand{\FCUpperBoundResult}{Using positive combinations of the same simultaneous contrast bounds, all 51 contexts also satisfy a conditional continuous dense-family upper bound of two. Thus the four-step large-gap path exceeds that upper bound under the affine model. This is stronger than comparing two selected paths, but remains conditional on the response model over the declared family; finite checkpoint agreement is not a simulator-wide proof.}
\newcommand{\FCOracleResult}{An exact finite reference reorders the union of the frozen exact and interior primary candidates without imposing monotone amplitudes. It obtains fresh-mean value-and-retention capacities four, one and four for the first three regimes in all 51 affine contexts, and budget capacity four in 33 contexts and three in 18. This is finite-domain mean optimality, distinct from confidence-supported paths and continuous population capacity.}
\newcommand{\FCDiscussion}{The evidence supports a conditional separation between current value and future controllable gains in a native stat family across eight classes. It does not support the broader claim that completion-gap density alone controls event-changing mechanics. The intervention paths begin from the same retained old history; they redesign the release schedule prospectively. They cannot refund headroom already consumed by a dense release, so they are not a retroactive recovery after saturation.}
'''
    (paper/'fc_numbers.tex').write_text(numbers)
    review='''# Final completion-capacity review

1. **Can equal current value coexist with different future capacity?** Yes, within the validated scalar-response domain. All 56 pairs of old ecologies have identical per-task optimal values, 5 partners, 100% legacy-source relevance, and K=1. Large-gap ecologies support 4 rounds in 51 contexts, whereas the dense ecologies have a conditional continuous upper bound of 2; the prespecified robust dense path supports 1 round.
2. **Are the exact theoretical predictions correct?** The conditional direction is supported. Frozen predictions are 5 for large-gap, 2 for dense, and 5 for weaker-direct designs; the budget prediction is 4 in 38 contexts and 3 in 13. Native confirmation does not measure an exact 5 versus 2: endpoint paths retain unresolved threshold cases and failures. Formulas must specify reachable intervals, open/closed endpoints, minimum amplitudes, and legacy-source constraints.
3. **Does weaker-direct design restore capacity?** A prospective release policy starting from the same old catalogue supports 4 rounds, exceeding the dense family's conditional upper bound of 2. This does not refund headroom already consumed by a released dense history; the remaining rounds after saturation of the original history are still limited by its remaining headroom.
4. **Does a fixed compatibility/resource rule restore capacity?** Yes. In the same strong-primary family, one fixed two-feature linear budget supports 3 rounds, retains all old combinations, and uses zero per-item exceptions. The rule is a research admission budget, not a claim about the game's native mana mechanism.
5. **What current opportunities are sacrificed?** The three-round robust paths in the 51 valid scalar-mapping contexts exclude 3–6 new combinations that would otherwise pass frozen power admission. The largest first-round task opportunity loss is 2.16%–3.27% of the old reference value; zero old combinations are excluded. The four-round budget path in the exact nominal model reduces the reachable peak by 0.00975.
6. **Does the result hold across mechanisms?** General support was not obtained. Weapon speed, mana regeneration, and triggered damage over time each completed independent native confirmation in one Alliance and one Horde context; no nonempty prespecified path passes every P/G/N/L interval check jointly. Finite mean capacities, directional counterexamples, and original/subsequent sensitivity analyses are all retained.
7. **Is the result robust across Alliance and Horde?** The supported 4/1/4/3 paths replicate in all 26 Alliance and 25 Horde contexts with valid scalar mappings. The main faction table weights classes equally and retains the finite experiments for 5 Warlock contexts. Prediction columns include only the 8 applicable classes; observation columns include all 9, with explicit denominators.
8. **How many classes and race/class combinations were executed?** All 9/9 classes and 56/56 official combinations have actual executions. Scalar mappings are validated in 51/56; the formula is inapplicable to the 5/56 Warlock contexts. Known missing racial mechanics are labeled in 7 contexts. The 20 exact-endpoint Warlock paths remain not_run, never zero-filled; all their robust cross-combinations were executed.
9. **What is the strongest defensible claim?** Within the specified native equipment/policy families and validated affine-response model, equal current optimal values, legacy-source relevance, and administrative complexity do not determine future value-preserving capacity at a fixed resolution. Reachable completion intervals and the minimum direct-design scale yield testable restrictions and costly prospective interventions.
10. **Is this enough to anchor an AISTATS manuscript?** It supports a complete research manuscript centered on these conditional results and failure boundaries. It does not establish a universal cross-mechanism law, sustainable expansion satisfying all seven conditions, mathematical originality, or a guaranteed oral presentation. The anonymous manuscript is based on the actual evidence.

## Evidence and limits

The study executed **22,032 native calls and 8,181,632 battles**, with zero failed or missing physical cells. Exact native design-seed observations are not duplicated. Shared seed ranges across different physical designs are disclosed; combat seeds are not independent research units.

All 51 affine contexts pass the guarded P/N/L/H/C/G paths at the mean and under approximate simultaneous paired Student-t bounds **within each context**. This is not a joint 95% claim over all 56 contexts, nor a distribution-free or live-server guarantee. The continuous dense upper bound reuses the same contrast family, so it adds no separate unbudgeted testing family. Its validity remains conditional on the affine model across the declared family.

Original Warrior behavioral D fails at the mean in all 274 attempted stages. Other classes' physical-channel diagnostic does not substitute for the original seven coordinates. No fully certified T_joint sequence is claimed.

The finite candidate-union oracle gives mean capacities 4/1/4 for large/dense/direct in all 51 applicable contexts; budget is 4 in 33 and 3 in 18. It allows arbitrary release order and retains all historical crosses/sources. Its finite mean optimum is not a continuous or confidence-certified optimum. Generic models with the same two features contain the linear budget; no algorithmic advantage is claimed.

## Files to inspect

- `paper/fc_main.pdf`: anonymous AISTATS-format research manuscript, not submitted.
- `SUMMARY.json`, `SEQUENCE_CAPACITY_SUMMARY.csv`, `NATIVE_CAPACITY_RESULTS.csv`: every frozen path and attempted stage, including failed and uncertain endpoint paths.
- `CAPACITY_UPPER_BOUND_CERTIFICATES.csv`, `SMALL_DOMAIN_ORACLE.csv`: conditional continuous bounds and separate exact finite references.
- `MATCHED_ECOLOGIES.csv`, `COMPLETION_SPECTRA.csv`: complete current-value match and deliberately different interior spectra.
- `DIRECT_REDESIGN_ESCAPE.csv`, `COMPATIBILITY_ESCAPE.csv`, `COSTS.csv`: prospective interventions and opportunity costs.
- `CLASS_FACTION_RESULTS.csv`, `FACTION_SUMMARY.csv`, `FACTION_MAIN_TABLE.csv`, `RACE_CLASS_56_RESULTS.csv`: full denominators, class-equal summaries and omissions.
- `LEGACY_RELEVANCE.csv`, `PORTFOLIO_COMPLEXITY.csv`: every retained source and exact task-set cover.
- `MECHANISM_CAPACITY.md`, `MECHANISM_CAPACITY_RESULTS.csv`, `MECHANISM_CAPACITY_SENSITIVITY_V2.csv`: original negative/uncertain transfer results and explicitly post-confirmation estimand sensitivity.
- `THEORY.md`, `PRIOR_WORK_DELTA.md`, `ABSTRACT_STRESS.csv`: formal conditions, credited prior work and abstract-only stresses.
- `EXECUTION_AUDIT.json`, `INDEPENDENT_NATIVE_AUDIT.json`, `SEED_OVERLAP.json`: physical execution audits.
- `REPRODUCE.md`: frozen execution and reproduction instructions.

## Preserved errors and scope changes

The attached raw-gap formula is not present in the supplied R5 artifact. R5 is retained verbatim as a separate formal input; the new formula was reconstructed with explicit assumptions, not attributed to R5. A tempting three-partner legacy counterexample was rejected because a later weaker primary repairs it; the valid four-partner counterexample permits decreasing release amplitudes. Rational regression tests preserve both.

The old-baseline matched design contains an invalid, unexecuted budget-interior prototype. Its first primary violates the budget even with the weakest partner. The future-design freeze records the erratum and the corrected sequence chosen before confirmation. No frozen old run was rewritten. The initial damage partition included friendly self-damage for Undead; a separate analysis revision excludes it, without changing utility or native physics. The original analysis is preserved.

The eight task definitions include a continuous endurance encounter and an actual execute phase. They do not implement repeated waves, movement, PvP, survival or every possible policy. One unchanged native APL per class is the declared strategy domain. Research stat alternatives use real native base IDs and physics hooks but are counterfactual item designs, not official released rewards.

No public upload, remote push, submission or invented author identity was performed. The review ZIP is internal and retains local provenance paths; the PDF is anonymous.
'''
    (out/'REVIEW.md').write_text(review)
    results='''# Final results

The positive result is a **conditional native value-and-source-retention capacity separation**. Across 51 validated affine contexts (eight classes), the prospective interior paths achieve and statistically support 4/1/4/3 updates for large-gap/dense/weaker-direct/fixed-budget regimes. Complete historical sources remain relevant, K=1, and all admitted historical gear stays legal. The dense continuous upper bound is at most2 under the same affine model and paired simultaneous contrast event.

The full target matrix is executed: nine classes, 56 legal race–class contexts, eight fixed tasks. Five Warlock contexts fail scalar affinity and use complete finite physical tables. Their exact endpoint paths are not_run. Seven contexts carry known native racial omissions. Neither source support nor abstract calculations count as executed coverage.

| Evidence layer | Result | Interpretation |
|---|---|---|
| Exact nominal scalar model | 5 vs2; direct5; fixed budget4 | Complete proofs with family, endpoint and source conditions; D excluded |
| Per-context frozen scalar prediction | 51×(5,2,5); budget38×4+13×3 | Old-data predictions before future calls |
| Independent guarded native paths | 51×(4,1,4,3), mean and simultaneous lower bounds | All P/N/L/H/C/G; model-conditioned interpolation explicitly labeled |
| Exact finite fresh-mean reference | 51×(4,1,4); budget33×4+18×3 | All subset/order possibilities in frozen candidate union; not continuous capacity |
| Non-affine Warlock | Dense1 supported in4/5; budget1 in5/5; large/direct none certified | No scalar upper bound; a zero lower bound is not a zero optimum |
| Three event-changing families | No certified nonempty prospective complete path | Full native transfer tests completed; universal direction not supported |
| Original behavioral D | All274 attempted Warrior stages fail at mean | No full seven-condition claim; otherclass originalD unassessed |

The weaker/direct and budget arms redesign future releases from an identical retained old history. They cannot undo headroom already spent by a published dense path. The remaining-headroom continuation bound is separate from the prospective capacity comparison.

## Statistical and execution accounting

The simulation reference is always the same strongest old gear. Main-study inference compares held-out responses to this fixed population reference with paired samples. Sensitivity to the literal development numeric cap is recorded separately. The original event-mechanism study froze numeric calibration caps; its fixed-population-reference sensitivity was chosen after confirmation and is explicitly secondary.

Bonferroni-corrected paired Student-t contrasts cover finite gain/relevance/cap comparisons within each context. They protect comparisons between optimized frontiers, not just the observed winning gear pair. They are approximate, conditional model inference and not across-context joint 95% coverage. Family/context, rather than combat seed, is the scientific unit.

All physical stages total22,032 calls and8,181,632 battles. Every output checksum, frozen source/input/binary and seed denominator was audited twice independently. Source/table scripts and native raw outputs are included in the internal review package. No runtime output was put in the maintained source repository.

## What remains unestablished

- Exact native population capacity5 vs2 at endpoint resolution.
- A universal capacity law across weapon-speed, mana-generation and proc-control changes.
- Native original-D joint sustainability, or every player policy/gear configuration.
- Novelty over all prior literature or conference acceptance quality.
- Live-server fidelity for known incomplete mechanics.

See REVIEW.md for the ten requested decisions and the provenance of every corrected assumption.
'''
    (out/'RESULTS.md').write_text(results)
    docs=SOURCE_ROOT/'docs/final-completion-capacity'
    for name in ('REVIEW.md','RESULTS.md'):shutil.copy2(out/name,docs/name)
    for source in [SOURCE_ROOT/'paper/fc_main.tex',SOURCE_ROOT/'paper/fc_references.bib']:
        shutil.copy2(source,paper/source.name)
    shutil.copytree(SOURCE_ROOT/'paper/fc_sections',paper/'fc_sections',dirs_exist_ok=True)
    atomic_json(out/'REPORT_DATA.json',{'verified_affine_contexts':51,'native_contexts':56,
        'native_calls':audit['new_calls'],'native_battles':audit['new_battles'],
        'capacity_upper_rows':len(upper),'finite_oracle_rows':len(oracle),
        'main_result':'Supported guarded prefixes4/1/4/3 and conditional dense upper2; originalDnotestablished.'})


if __name__=='__main__':main()
