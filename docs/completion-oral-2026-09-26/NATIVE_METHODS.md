# Independent catalogue registration and completion certificates

The new catalogue panel contains 8 developer menus and 16 validation menus. A
menu, not a seed, target query, nested expansion, or faction repetition, is the
registered validation unit. Four metadata/source strata each contribute two
developer and four validation menus: Warrior one-hand weapon/skill interactions,
Paladin two-hand physical/holy seal interactions, Mage timed/resource trinkets,
and Druid passive resource statistics under the fixed balance policy.

The database pool uses item level 52–75, rare-or-better quality, class/slot/armor
legality, and no encoded faction restriction for varying items. Caster and melee
armor pools require the declared relevant statistics. The Mage trinket pool is
an explicit source-checked list. Item IDs can overlap earlier work; whole menus,
sample membership, references and cross combinations were registered without
reading old outcomes. New custom item IDs in the native database are actual
database items, not parameter overrides. The panel does not verify every live
acquisition rule or every tooltip effect. Faction-named acquisition gear without
an encoded faction restriction remains acquisition-unverified.

Membership is sampled using recorded deterministic seeds. History uses the
upper median by `(item_level, item_id)` of each sampled base slot. Each base menu
has 8 left and 4 right items, including one history item per slot. Eight
prespecified validation units add the two lowest-item-level unselected left
alternatives and one corresponding right alternative, making 10 by 5. They are
optional helpers; every original cell and reference remains identical. Every
physical cross is observed. Eight queries per menu are selected by metadata:
four singletons, three mixed-slot pairs, and one triple. They are shared between
base and expanded menus.

The first validation menu in each stratum has four tasks; the others have two.
Tasks are conditions for a single unchanged native policy, not extra strategy
probability. A prespecified task-contract challenge retains Q=4 task indices
`[0,3]` with equal half weights. It is a changed task distribution, so no task
monotonicity is asserted. Original per-task responses and thresholds are kept.

The shared threshold rule is `e=.01, h=.10, g=.01, rho=rho_g=.5`, all offsets
relative to the originally registered history reference on each task. The first
default was retained after the eight developer menus had both feasible and
infeasible queries and source-retention effects across all four strata. No
alternative threshold grid was evaluated. This is developer-based protocol
selection; the developer answers are not independent confirmation.

## Finite event and all-width certificate

For M complete physical configurations and Q tasks, each validation unit uses
one simultaneous family of `Q*(M+2*M*M)` two-sided contrasts:

* cap: `(1+h) S_q - mu_cq` for all c;
* gain: `mu_cq - mu_dq - g S_q` for all ordered c,d;
* retention: `mu_cq - mu_dq + e S_q` for all ordered c,d.

Diagonal contrasts are included. Full paired covariance includes the reference
configuration, so its uncertainty is not discarded. Fixed-N Student-t intervals
use `isf(alpha/(2*family_size), N-1)`. This Bonferroni paired-t approximation is
not distribution-free. Each of the 16 validation units receives alpha .0025;
base/expanded menus, all target queries and retention-disabled ablations are
deterministic consequences of that same event. The four-task projection slices
these original bounds, retaining their original critical value and family size.
It adds no contrast direction or error allocation.

For a publication P let A(P) be every configuration whose two items are in P.
Cap validity requires all activated cap contrasts to be nonnegative. A source
i is useful on task q exactly when some activated c containing i satisfies the
retention contrast against **every** d in A(P). Gain on task q similarly requires
some c in A(P) satisfying every gain contrast against the history configurations.

Replacing each contrast by its lower endpoint gives sufficient conditions for
a concrete publication. Replacing each by its upper endpoint gives necessary
conditions: every true feasible publication satisfies them on the joint event.
The implementation exhausts every superset of H in the registered finite menu,
without a helper-count limit. Thus no optimistic publication containing D is an
all-width NO certificate. A pessimistically valid publication containing D is a
YES witness. Statistical ambiguity is UNKNOWN. If H is not supported but remains
possible, the answer is UNKNOWN_INITIAL; a demonstrably invalid H is not a NO.

At most 8,192 supersets are enumerated for a 15-item expanded menu with two old
items. Exported certificates include item/support masks, forbidden cap masks,
source-witness comparison masks, gain masks, target-specific rejection counts,
and a hash of the complete exhaustion trace. Compact means/covariance and code
reconstruct every endpoint. This exhaustive certificate is an independent
checker, not a claim that native enumeration scales to arbitrarily large menus.

## Prospective evaluation and simple comparisons

Prediction uses the separate 1,024-seed table. Fresh confirmation uses a new
fixed 16,384-seed block for each unit. The prediction answer and its selected
witness are preserved. Confirmation separately records the fresh exact-mean
answer, the population-supported answer, and whether the **original frozen
witness** is supported; a newly found witness never replaces a failed prediction.

Exact mean comparisons parse exported decimal means as rational numbers and use
the same model for every method. Native constructive comparisons include direct
publication, minimum-increment greedy, current-gain greedy, weakest-source
repair, and a two-helper lookahead. Floating-point scores affect search order
only. Every YES is checked against the full exact contract, including all
helpers. Every unsuccessful heuristic returns UNKNOWN. A depth-two failure is
never a NO and is not an unrestricted-helper certificate.

Development and prediction outputs already show that a simple heuristic can
find all feasible primary queries; confirmation may change that assessment.
There is no presumption that the specialised exact algorithm has a native speed
advantage or that low-item-level candidate additions remove an obstruction.
