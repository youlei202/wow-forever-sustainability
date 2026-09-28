# Completion certificates inherited from the frozen native event

The new result is a target-completion obstruction in the glove catalogue that needs no power conflict. After Arcanist Gloves, publishing the common target **Magister's Gloves + Magister's Leggings** cannot retain every source at any publication width. After Sorcerer's Gloves, the same target has a supported completion. Both first histories still admit some positive-gain continuation. Thus the glove distinction concerns **which future target can be completed**, rather than the existence of any future gain or the number of release dates.

This is a post-hoc consequence of the four earlier frozen local/held-out native confirmation tables. The target comes from the previously frozen good path. It is not a new catalogue, an independently selected new target, or another native confirmation experiment.

## What changes scientifically

In each glove setting, all 8,192 target-containing supersets pass the optimistic cap and gain tests at the permissive corner of the primary parameter box. Every one fails retention of **Arcanist Gloves (16801)**. Its possible use depends only on the published leggings. There are four possible right-slot supersets containing the old Skyshroud Leggings (13170) and target Magister's Leggings (16687): optionally include Netherwind Pants (16915), Padre's Trousers (18386), both, or neither. Within each case, all Arcanist witnesses are fixed. Their retention upper bounds are negative on both tasks against the mandatory glove configurations. Additional gloves can only raise the frontier; they cannot add a new Arcanist witness. Four cases therefore cover every left-slot publication subset.

At tolerance e=.006, the least-negative upper endpoint among these cases is -1.363221 DPS locally and -1.337740 DPS under held-out durations. This excludes the common target even if the cap and gain requirements are removed. It complements the trinket case, where a future off-hand repair is excluded by an irreversible over-cap pairing. A broad claim that target loss is always a consequence of a small safety-conflict boundary would be false: this measured glove obstruction is an endogenous source-support failure.

The task-level statistical assumption is unchanged: finite fixed-N paired Student-t intervals with Bonferroni correction, approximate rather than distribution-free. The findings refer to the complete measured finite catalogues under their fixed policies and tasks.

## Certified continuous regions

| Frozen family | Common target | e range | h range | g range | Result in both local and held-out settings |
|---|---|---:|---:|---:|---|
| Alliance Gnome Mage, trinket/off-hand | Draconic Infused Emblem | [.008,.012] | [.030,.036] | [.008,.012] | After Tome YES; after Second Wind target NO |
| Horde Undead Mage, gloves/leggings | Magister's Gloves + Magister's Leggings | [.004,.006] | [.080,.120] | [.008,.012] | After Sorcerer's Gloves YES; after Arcanist Gloves target NO |

These are whole continuous boxes. For each, the good completion, original state, and both first releases pass conservative tests at the strict corner (smallest e/h, largest g); the bad target is excluded at the permissive corner. The positive reference bounds make constraint monotonicity valid throughout the box. The reported boxes were chosen from all 1,000 nondegenerate boxes with endpoints in the predeclared five-point grid. No global largest-region claim is made.

All 125 glove grid points per setting support the distinction. Of 125 trinket points per setting, 75 support the distinction, 25 leave the first releases statistically unresolved (h=.024), and 25 have supported first releases but an unresolved Tome completion (h=.027). These 50 unresolved cases are retained; they are not negative performance or proven absence.

For two equally weighted tasks, every 0<rho<=.5 has the same test. At the base thresholds, .5<rho<=1 makes both first histories provably invalid in all four settings. The rho=0 retention-disabled ablation is separate.

An additional **post-hoc inherited-event consequence** follows from the four-case glove certificate: exclusion holds for every e<.0096245358 locally and e<.0096035172 in the held-out setting, regardless of cap/gain conditions. The conservative common value e<=.0095 therefore works. This extension lies beyond the primary display grid; it has continuous-event justification but is not presented as a newly preregistered finding or an independently confirmed region.

## Why the old event really covers the new thresholds

The actual frozen `oe_inference.py` hash matches the old confirmation manifest. Its loops form every ordered row pair, including c=d, in both gain and retention families. Original family sizes are 9,312 for trinkets and 12,656 for gloves. Original per-setting core alpha is .003125.

Diagonal retention and gain contrasts are e0*S and -g0*S. Scaling and intersecting their covered intervals gives bounds [SL,SU] for the same reference mean on the same event. A changed contrast C=C0+a*S is then bounded by

    L = L0 + min(a*SL, a*SU)
    U = U0 + max(a*SL, a*SU).

The coefficients a are delta-h for cap, minus delta-g for gain, and delta-e for retention. This is a deterministic simultaneous implication for continuous parameter values. No new t critical value, new sampled direction, extra native observation, or extra alpha is used. Saved covariance alone would not have justified this extension without the diagonal-event audit.

The old campaign's total .05 remains spent. These consequences reuse that event. The new native campaign has a separate budget; combining old and new claims does not produce a fresh global .05 claim.

## Checks and small reproducible inputs

The supplied paper's trinket mean/covariance/N arrays are bitwise identical to the original compact arrays. Running the copied paper reference code reproduced the two 8,192-subset all-width exclusions and the 4 local / 8 held-out conservative Tome supersets.

The maintained sensitivity implementation passed 300 independent tiny all-subset comparisons plus 1,000 sign-aware interval arithmetic cases. Its standalone bundle checker replayed all 2,000 grid query decisions and independently enumerated 49,152 complete publications at the certified box corners, using the original weaker optimistic bound direction and no source/cap pruning. It also reproduced 280 original endpoint groups to at most 1.01e-10 DPS, including the explicitly disclosed 1e-10 outward numerical padding.

The compact bundle contains means, covariance, N, support order, base claims, original interval identities, reference-bound derivations, all grid statuses, constructive witnesses and exclusion traces. The checker needs no raw battle output or old chat:

```bash
source scripts/env.sh
python -m wowfs.experiments.co_sensitivity \
  --verify-bundle /absolute/path/to/sensitivity/propagation-v1 \
  --output /a/new/path/INDEPENDENT_RECHECK.json
```

The same module exports eight exact-rational finite mean-table histories for the fair computational benchmark. Those are inherited regression instances, not new native coverage. Source LaTeX panels are in this directory's `figures/`; compiled vector PDFs belong to the campaign work directory.

The four-case glove target certificate is a candidate for the paper's main empirical argument because it changes the design question from release counts to a common future target and separates source-support failure from safety conflicts. The continuous boxes and event audit are necessary evidence strengthening. They alone do not establish repeated-query computational value or generalization to independent catalogues; those require the other two campaign branches.
