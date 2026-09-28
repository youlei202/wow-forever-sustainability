# Independent integration review — 27 September 2026

The native figure/table counts and corrected theory checker pass this review.
No remaining issue found here blocks completion of Phases A–C. This review
does not activate Phase D and does not claim that finite checks prove the
universal theorem. The native audit author performed this separate review
of the reporting code and the other agent's theory implementation.

## Native figure and table accounting

All 72 primary contract-by-order rows (24 contracts, r=1,2,3) were independently
recomputed from the saved per-target status arrays by explicit enumeration
with `itertools.combinations`. This avoids the native audit's subset-minimum
dynamic program. Certified misses, UNKNOWN-blocked cases, unresolved full
targets, and exact finite-table misses all match.

The 16 base menus give 351, 3, and 0 certified missed target decisions over
16,384 target queries. The eight nested expanded menus separately give
8,632, 0, and 0 over 65,536 queries. The figure keeps these strata separate;
they are not 24 independent sampled menus. Its UNKNOWN panels correctly
separate full NO decisions blocked by a low-order UNKNOWN from full UNKNOWN
decisions without a low-order NO. Counts have no binomial error bars.

The three base order-2 misses are exactly
`{a04,x1,x3}`, `{a06,x1,x3}`, and `{a04,a06,x1,x3}` in Druid validation-02.
There are two minimal triples; the third missed decision is their four-item
union. The corrected figure annotation now states this distinction. The
rendered PNG was inspected; vector PDF and SVG versions are present.

The native representation table uses the supported interface consistently,
preserves empty-family order-zero obstructions and catalogues without a
certified obstruction, and reports zero projection merges. Raw Markdown
absolute-value pipes originally created extra header cells; the corrected
header uses plain column names and the generated table has five cells per row.

## Corrected theory implementation

The checker was independently compared with literal enumeration of every
publication on 300 additional arbitrary response tables, using a separate
seed (270927). These include n=0,...,4 targets, one to five boots, responses
from 94.0 to 115.0, and 25,600 publications in total. Every target family
matched. The inputs extend beyond the theorem's prescribed construction
and perturbation radius, so this is also a check of the general finite
algorithm used to adjudicate construction instances.

The frontier algorithm is complete in its one-task setting. For a fixed
glove set and attainable frontier y, every boot in a valid publication has
column maximum in [y−1,y]. Adding all other boots in this interval cannot
increase the frontier or remove a glove witness, and each added boot has
its own retention witness. Enumerating these frontiers, requiring the old
boot, checking gain against the perturbed history response, and taking the
downward closure therefore cover all helper extensions. The old-glove and
old-boot frontier ceilings are necessary upper bounds and do not discard a
valid publication.

The high-order pair construction keeps component labels and supports equal
between its positive and negative instances. The symbolic pair-exclusion
construction also has a valid all-helper exclusion: an included forbidden
pair activates response 104 while the mandatory old glove cannot exceed
102. The p=12 and p=16 sampled query checks are labelled non-exhaustive;
the separate structural identity supplies the full representation argument.

The corrected v2 checker passes; the failed v1 run remains evidence of a
checker defect rather than a theorem counterexample. No native coverage is
credited to any abstract construction check, and eta≥0.5 uniform samples
are not used to extend the strict theorem guarantee.

## Packaging review and limits

The initial package implementation copied only `test_mi_*.py`, although the
native tests import two `test_co_*` helper modules. It now copies the test
directory's Python files, resolving that dependency omission. This review
checked packaging code, not a completed archive; actual ZIP integrity and
portable execution remain the packaging receipt's responsibility.

The detailed computation record is
`checks/INDEPENDENT_INTEGRATION_COMPUTATIONS.json`, and the final review
receipt is `checks/INDEPENDENT_INTEGRATION_REVIEW.json` in the new run root.
No native frozen output, theory run, inference code, or manuscript was
modified during this review.
