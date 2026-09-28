# Theory backlog after open exploration

Status: research judgment updated after frozen confirmation, 26 September
2026. Both actual-catalog continuation claims pass in their local and one
held-out setting. The Druid joint-cap claim passes both settings; the Mage
joint-cap claim passes locally and fails in its held-out setting, where the
joint configuration is supported safe. Results remain limited to the frozen
finite domains and approximate simultaneous inference. Numerical examples are
labeled development or confirmation below. This document changes no frozen
analysis, historical result or manuscript.

Artifact paths below are relative to
`$WOWFS_WORK_ROOT/artifacts/open-exploration-2026-09-26/campaign-v1/`.

## 1. Formal inheritance, with its actual scope

The formal bases are the supplied R5 `inputs/r5-theory/THEORY.md` and the
26 September structural research note under
`inputs/open-exploration-2026-09-26/WoW_Forever_Open_Exploration/structural-reference/WoW_Structural_Research_2026_09_26/`.
Input paths in this paragraph are relative to `WOWFS_WORK_ROOT`. They are
preserved inputs, not new results of the native campaign.

| Supplied result | Assumptions that carry the result | What this campaign adds, and does not add |
|---|---|---|
| R5 exact least repair closure | One scalar task; a unique designated repair per old source; stable near-cap repair/core witnesses; no alternative or joint repairs. Minimum completion size is one core plus the least closure's repairs. Intermediate closure states are planning states, not valid published releases. | Full-incidence histories expose why the restrictions matter. The current catalog examples have alternative tasks, alternative items and two growing slots. They are not instances establishing the unique-repair formula empirically. |
| R5 one initial threat can induce arbitrarily many repairs under arbitrarily small total frontier movement | The explicit restricted construction for every `m` and positive movement bound; densely spaced source thresholds. | Not reproduced natively in this campaign. A source-specific continuation gap or one blocked repair is not an arbitrarily long cascade. |
| R5 frontier-neutral design region and constructive capacity lower bound | Fixed single growing slot, all fixed partners/policies, exact affine response region, persistent witnesses, fixed portfolio coverage and a measured behavioral packing at positive resolution. | No new native proof of this affine region or behavioral packing. Item labels, nonlinear response rank and more release dates are not behavioral capacity. Fixed positive packing resolution does not imply infinitely many distinct useful designs. |
| R5 interval propagation and statistical locality lower bound | The closure's monotone model for the former; the stated statistical experiments and change-of-measure assumptions for the latter. | Simultaneous conservative/optimistic finite planning is related evidence discipline, not a new proof of the locality theorem or a universal native sample-complexity law. |
| Structural note: equal action-indexed optimized response and optimizer can hide capacities `k` versus `1` | Two fixed partners, scalar smooth quadratic response, a common continuous action domain, immutable legal pairs; all release widths allowed. | Near-matched native first frontiers provide a different, weaker empirical comparison. They do not establish equality of complete native response functions. |
| Structural note: terminal-filtered source coverage characterizes sufficiently wide releases | Scalar finite response table, fixed partners, one growing primary slot; terminal filter preserves the repair primaries themselves; width equal to the number of partners suffices. | The independent oracle agrees on the audited domain. Multitask, restricted-width and newly co-equipped items require the full incidence solver. The formula must not be silently applied to them. |
| Structural note: singleton-release hardness and tight sufficient width | The supplied set-cover reduction and fixed-partner model. | Exact finite subset dynamic programming is a reference implementation, not a new algorithmic result. The supplied theorem does not classify every intermediate width. |
| Structural note: max-norm perturbation sandwich | A uniform response-error bound and fixed legality relation. | It motivates robust bounds. Observed sample error is not uniformly bounded merely because the perturbation theorem exists. The confirmation uses its separately audited approximate simultaneous inference. |

The frozen old verifier passed, including 1,192 profile/oracle comparisons and
the provided construction, reduction and perturbation checks. A separately
implemented incidence solver matched 550 additional scalar oracle comparisons
on 150 rational tables, and all 150 wide-profile optima. Direct ordered-history
tests cover multitask cases. These checks are evidence against implementation
mistakes, not a substitute for continuous proofs or a novelty review. Details
and preserved test-development corrections are in
`checks/theory/THEORY_AUDIT.md`.

## 2. The state must retain future witness structure

Let `S` be the actual published item set, `H(S)` its legal configurations, and
`u_q(c)` the immutable response on task `q`. Fix reference values and task
weights before the history. Define

```
F_q(S)   = max { u_q(c) : c in H(S) }
V_iq(S)  = max { u_q(c) : c in H(S), configuration c contains source i }
M_i(S)   = sum_q w_q * 1{ V_iq(S) >= F_q(S) - e_q }.
```

Policies are configurations within each task, not additional task weight.
Source retention requires `M_i(S) >= rho` for every published item, including
repair items. A future item can improve `V_iq`, increase `F_q`, activate an
unsafe composition, and create its own obligation. The joint relationship
between those effects is the object a useful continuation representation must
preserve.

The current frontier and aggregate source mass discard this relationship.
The independently confirmed Trinket instance has nearly identical first frontiers and
exactly equal minimum, sum and **unlabeled multiset** of current source masses,
yet retaining continuations differ. Its labeled source-mass vectors are not
equal: Eye of the Beast is vulnerable in one state and Drakestone in the other.
The full source-conditioned response vectors are also different. Both first
releases and the frontier match within `.0025` are simultaneously supported;
the retaining continuation bounds close at zero versus one, and the value-only
bounds at one versus one, at B=1 and B=2 in both frozen settings. Thus the
experiment challenges a coarse summary; it does not prove that every
representation omitting literal source IDs fails. Relabeling-isomorphic states
with the same response/incidence structure should be equivalent.

Even exact current `V_iq` values generally need information about the remaining
candidate pool and its future incidence. A precise abstraction target is
**continuation equivalence**: for the same declared future action permissions,
two represented states admit the same feasible labeled release histories, or
have an explicitly bounded error for the chosen value objective. Capacity
alone is a weaker equivalence than preserving all histories. Proving necessity
of the complete table would be excessive; compressed interfaces may suffice.

A safe special-case reduction already illustrates this distinction. In the
scalar fixed-partner model, retain column maxima, the exact remaining
candidates, and tighten the cap to
`min(original_cap, min_published_primary_value + e)`. This preserves actual
old-primary obligations. Column maxima without that last quantity are unsafe.
The independent synthetic example has remaining capacity zero while the
incorrect compression reports one. Another example shows that ignoring a
repair's own later relevance overcounts capacity. These are counterexamples to
unsafe adaptations, not to the correctly scoped supplied theorems.

## 3. A small monotonicity fact with a consequential design boundary

**Proposition (power violations cannot be repaired by adding immutable items).**
Suppose publishing more items only adds legal configurations,
`S subset S' => H(S) subset H(S')`; responses, task set and power caps remain
fixed; and the power condition checks every available legal configuration.
If a configuration in `H(S)` exceeds a cap, every extension `S'` also violates
the power condition.

**Proof.** The same configuration remains in `H(S')` with the same response and
cap. It is still a violating witness.

This is elementary set inclusion, not a novel theorem. Its practical role is
to separate two different obstructions. A loss of source relevance can
sometimes be repaired by adding a useful partner. An already activated
over-cap combination cannot be repaired this way. Nerfing, removing an item,
forbidding a pair, raising the cap or changing tasks are different update
permissions and require a different model.

In a finite incidence table, minimal unsafe item supports form forbidden
hyperedges: a publication state is power-safe exactly when it contains no
such support. This safety subsystem is downward closed. **Full update
feasibility is not**: removing a helpful item may destroy source retention or
the required gain. Safety conflicts and positive retention witnesses must be
represented together. Calling the whole problem a monotone conflict system
would lose the main interaction.

The Trinket example makes this boundary concrete. Second Wind and Spellbound
Tome remain individually available choices, but their joint long-task
development mean is `1.045659796`, above the frozen cap `1.03`. Confirmation
also excludes this composition: the frozen local blocked-repair path has a
long-task cap-margin interval `[-4.070412,-3.695870]` DPS; the held-out interval
is `[-3.496027,-3.138224]` DPS. Publishing Tome after Second Wind cannot avoid
activating that violation. The solver does not delete the joint cell or remove
the unchosen first alternative. This particular composition stays unsafe at
larger batch widths by the proposition; the **full bad-history capacity** was
only certified at B=1 and B=2. Other large-batch repairs are not excluded by
this observation alone.

## 4. Avoid mistaking reward staging for additional useful capacity

The release-count objective rewards splitting total improvement into smaller
qualifying steps. Minimum-qualified-increment baselines remove 46/46 broad
planning advantages, 17/17 original fixed-partner catalog advantages, and
144/153 refinement advantages. Of twelve residual refinement/two-slot catalog
rows challenged with full menus and stronger rolling baselines, six retain a
count gap; five of those have an exact terminal frontier reached or dominated
by a simple method. The sixth is a small, unconfirmed terminal difference.

This defeats the proposed general algorithmic story. A count advantage may
still matter if release cadence is explicitly the desired objective, but it
cannot be renamed greater content value, behavior diversity or stronger final
performance. Useful comparisons should condition on achieved terminal
frontiers and report publication cost, source-specific opportunity and
behavioral differences separately.

An elementary reduction provides another diagnostic. With immutable fixed
partners, no retention constraint, and each task able by itself to meet the
gain-mass requirement, any feasible batch history can select one witnessing
new primary per release. This gives the same release count with width one and
no greater item budget. It does not apply when newly published items must be
co-equipped, or several task gains must be witnessed simultaneously.
`checks/theory/VALUE_WIDTH_REDUCTION.md` gives the proof. It separately sharpens
one value-only model bound to three; the original B4 search timeout `[3,12]`
is preserved and is not relabeled a completed enumeration.

## 5. Ranked questions worth further theory work

1. **A sufficient update interface for continuation decisions.** Characterize
   when source/task witness information plus unsafe composition supports
   admits an exact or quantitatively approximate compression. Begin with two
   growing slots and two tasks; compare directly with existing quality/resource
   interfaces, state abstraction and coverage/ordering models. A successful
   theorem should say what can safely be omitted and enable a decision or
   sample saving beyond generic exhaustive search. A coarse-summary
   counterexample alone is not enough.
2. **Completion under alternative repairs and irreversible composition
   conflicts.** R5's unique-repair closure is a tractable special case. Ask
   which structural restrictions on witness bundles and unsafe supports admit
   efficient minimum completion or certified infeasibility. Preserve repair
   self-retention and intermediate published-prefix legality. First establish
   the precise mapping to known covering/conflict problems; a generic hardness
   reduction or renaming hypergraphs is not a new contribution.
3. **Separate future-option preservation from gain rationing.** Specify a
   decision objective under matched current/terminal value and equal
   publication budgets that measures useful later choices. Derive a baseline
   or guarantee only after this objective is operational. The current data
   support scrutinizing this question, not a proposed universal new metric.

The R5 frontier-neutral behavioral branch remains valid as a separate backlog
item, but this campaign did not supply the native behavioral witnesses needed
to promote it. Likewise, native long repair cascades and a locality learning
lower bound remain unvalidated directions; they must not be filled in by a
short continuation example.

## 6. Confirmation changes the evidence, not the theorem scope

The adjudication `CONFIRMED_CLAIMS.json` records seven supported setting-level
claims among eight frozen in `CONFIRMATION_MANIFEST_V2.json`; these are not seven
independent mechanisms. Catalog claims meet every prespecified first-step
feasibility, simultaneous frontier-match, conservative lower-bound, optimistic
upper-bound and equal value-only condition at both specified widths. Magister
has retaining continuation one versus two and value three versus three;
Trinket has zero versus one and value one versus one. Each passes locally and
in its one held-out transformed setting. The original Magister `.01` failure
remains a failure; confirmation concerns the new frozen `.005` target.

Joint-cap claims require both singletons and the additive forecast safe, the
actual joint excluded, and positive mixed interaction. Druid passes in both
settings. Mage passes locally, while its held-out joint is supported safe:
the resistance75 cap margin is `[1.806975,2.625500]` DPS. Its positive mixed
interaction still has interval `[6.666534,7.192440]` DPS. This is an explicit
example of an interaction transferring without the design decision
transferring; it is not merely an underpowered unresolved result.

The inference is fixed-N approximate simultaneous paired Student-t under the
frozen simulator and seed setup, not distribution-free coverage or validation
of live game behavior. The nonrenewable campaign allocation is `.05`. Prior
work comparison is recorded in [PRIOR_WORK_DELTA.md](PRIOR_WORK_DELTA.md);
none of the questions above has established priority relative to that work.
Selected original-unit intervals, exact source-mass bounds and input hashes
are preserved in `analysis/theory-judgment-v1/CONFIRMATION_DIAGNOSTICS.json`.

An independent post-confirmation check imports neither campaign inference nor
solver code. It reconstructs the core paired contrasts from the saved means
and sample covariance. For each Magister setting it checks all 120 singleton/
pair first continuations after the bad first release, retains eight optimistic
states, and checks all 756 possible next edges; none survives. For each Trinket
setting, none of the 91 first continuations survives. It also verifies 48
returned supported path prefixes with every published source and all active
physical configurations. The largest saved/source-margin discrepancy is
`1.02e-13` DPS, with no negative-variance clamp needed. Thus the bad-side B2
upper bounds one/zero have an independent short-prefix certificate; B1
inherits those bounds. `checks/SECONDARY_CATALOG_CAPACITY_CHECK.json` preserves
the complete remaining pools, counts, numerical diagnostics and source hashes.
This check inherits the approximate inference assumptions and the separately
audited compact-moment provenance; it creates no new statistical guarantee.
