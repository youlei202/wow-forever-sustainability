# Independent B/C analysis review

Reviewed `r6_geometry.py`, `r6_neutral.py`, `r6_neutral_analysis.py`,
`r6_capacity.py`, `r6_capacity_precision.py`, the calibration/original-domain
drivers, frozen parameter files and final C logical rows. No scientific
geometry or inference bug was found in the executed domain. Physical drivers
were not changed by this review.

The five behavior coordinates are actual native action DPS divided by frozen
calibration F0. They are not the earlier R3 per-design damage fractions. The
normalizer is fixed before sequence confirmation, so fitting an affine native
response yields an affine behavior model. The source audit and held-out
calibration support that model finitely; they do not prove population affinity.
The old fresh mean and calibration F0 remain distinct: confirmation checks
both paired new-minus-old utility and absolute new utility against frozen F0.

The one expanding main-hand slot has exactly one fixed partner, policy and
task. All old configurations and all previously introduced designs remain
available. Therefore M0=p=1 describes the full declared profile interface.
This count would fail after adding partners, policies, tasks with different
novelty witnesses, or coequipment between newly expanding slots. The original
R3 diagnostic correctly counts 12 profiles per witness task and has zero
packing lower bound at delta=.05.

For the frozen affine segment, L-infinity distance between new profiles is
beta times scalar parameter distance, with beta=0.24993740194498712. The old
profile's forbidden interval is a suffix for each of the four predeclared
deltas. The reported capacity n satisfies
`(n-1)*delta <= beta*allowed_prefix < n*delta`. This proves the numerical
maximum 10/7/5/3 in the fitted one-dimensional model. The selected equal-spaced
constructions also keep positive novelty margins from the old profile and all
prior new profiles. This upper bound is not a native population or whole-game
maximum. R5's more conservative lower bounds are 3/2/1/1.

The final C table has 832 logical design/block rows and 736 unique physical
cache keys, each representing 2,048 native battles. There are exactly 32
blocks per design and no errors. Design coordinates match the original frozen
capacity file. Every input uses `saveAllValues=true`, `useLabeledRands=true`
and seed `614000001+10000*block`; all logical paired rows use the same block
and seed order. Reused physical calls for identical designs across panels do
not create extra independent observations.

With n including the old design, each panel's simultaneous utility family
contains n absolute means and n-1 paired contrasts, hence 2n-1 members. The
behavior family contains five coordinates for every unordered profile pair,
hence `5*n*(n-1)/2` members. Half of each panel's alpha=.0125 goes to each
family. The four panels therefore use global alpha=.05 by union bound even
though their shared old designs and some new designs are correlated. Utility
uses 65,536 per-seed paired observations with 65,535 degrees of freedom;
behavior uses 32 paired block means with 31 degrees of freedom. Full-history
pair sets were checked directly against the frozen orders.

Final lower novelty bounds are .0258711153, .0365437222, .0515442635 and
.0812484424 for thresholds .025, .035, .05 and .075. All 10/7/5/3 updates pass
their joint approximate checks. These are separate alternative sequences,
not one combined 25-update history. Initial C had unresolved lower bounds in
two panels and partial B seed overlap; final C uses only its new disjoint
dataset, preserving initial outputs without pooling or parameter changes.

Three regression tests in `tests/test_r6_inference.py` check that common
block noise cancels in paired behavior contrasts, nonshared noise retains
uncertainty, and proximity to a nonadjacent old profile causes D failure.
These synthetic test fixtures are software checks and never enter native
sample counts. Student-t coverage remains approximate for Monte Carlo outputs;
the review does not convert selected-design confirmation into uniform safety
over an uncountable native parameter region.
