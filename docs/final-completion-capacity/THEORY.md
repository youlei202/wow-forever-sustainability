# Scalar completion capacity: exact conditions, counterexamples and native scope

The formula in the new brief is **not a consequence of h, g and X alone**.
It is an exact value-capacity theorem for a particular continuous incoming
family with complete scalar additive mixing. A minimum incoming amplitude,
legacy-source requirements, multiple tasks and behavioral novelty each need
separate treatment. This document reconstructs those conditions; it does not
attribute the formula to the supplied R5 repair-closure theorem. The maintained
prior decisive-value theory did not contain this completion-gap formula.

All examples and helper outputs below are abstract exact arithmetic. They add
zero native calls, races or classes. Native predictions require a validated
response reduction and the actual frozen family bounds.

## 1. Model and what capacity counts

There is one scalar task and a complete two-slot domain. The old primary has
value a0. The n distinct retained partner responses are
`x1 < ... < xn`; their identities remain distinct source obligations. A physical
combination has utility `u(a,x)=a+x`. The sole admission condition is
`a+x <= tau`. All legal old-old configurations are retained, so initially
`F0=a0+xn <= tau` and `h=tau-F0`.

A new primary of amplitude a has optimized admitted value

`v(a)=a+max{x in X : a+x<=tau}`,

when the maximization set is nonempty. After publication the global frontier
is the maximum of F0 and v(a) over **all** retained primaries. An update must
raise this frontier by at least g>0. A newly published primary is not required
to have a larger amplitude than previously published ones. Lower-amplitude
releases may activate stronger old partners and improve the optimized value.

`T_value` counts positive-G updates subject to the fixed cap and historical
configuration retention. It does not silently include L or the native D.
`T_retained` additionally requires every partner and every previously released
primary to have a witness within raw relevance allowance e of the current
frontier at every step. For one task, an optimal configuration is a K=1
portfolio. Every gaining new primary has a current optimal witness, hence N.

The scalar model has no behavioral representation. It cannot certify the
original seven-feature D or imply `T_joint=T_value`. A physically faithful
single-channel amplitude family can have positive G and zero D throughout.

## 2. The open completion-band theorem

Define `Delta=max_i(x_(i+1)-x_i)`; for n=1 set Delta=0. Assume the incoming
family contains every amplitude in

`tau-xn < a <= tau-x1`,

and contains no amplitude at or below `tau-xn`. Thus no future primary can
use the strongest old partner, but there is no positive lower cutoff above
that boundary. The family is continuous and contains the cap-reaching upper
endpoints. Partners and physical rules remain fixed.

**Theorem (value capacity).** Under these assumptions,

`T_value = min(floor(h/g), ceil(Delta/g))`.

**Proof of attainable values.** If the strongest legal partner is xi, i<n,
then `tau-x_(i+1) < a <= tau-x_i`; equivalently,

`tau-(x_(i+1)-x_i) < v(a) <= tau`.

The lower endpoint is open: at equality the next stronger partner is legal
and raises the optimum to tau. Every branch ends at tau, so their union is
exactly `(tau-Delta,tau]` when n>=2, and empty when n=1.

**Upper bound.** Telescoping gains imply `T*g<=h`. Also the first new frontier
is strictly above `tau-Delta`, so `(T-1)*g<Delta`. For integer T the latter
is `T<=ceil(Delta/g)`, including the case Delta/g is an integer.

**Attainment.** Let T be the smaller bound. For T>0 select values
`y_t=tau-(T-t)*g`, t=1,...,T. The first exceeds tau-Delta and is at least
F0+g. Every value is attainable, and differences are g. Publishing a primary
for each value yields the claimed sequence under complete mixing. QED.

This is an interval-packing argument for optimized scalar responses, not a
general packing theorem for native combat. If incoming amplitudes are a finite
grid, are upper bounded before a needed endpoint, are forced to increase, or
alter partners/control/event structure, the attainment proof must be redone.
Removing an endpoint can change an integer capacity by one.

## 3. Actual minimum amplitude and the meaning of lambda

For the closed continuous family `a>=a_min`, let
`lambda=a_min-a0`. This lambda is an absolute lower increment over the
initial primary, **not** a minimum increment between successive releases.
Those are different models. An upper amplitude limit is omitted in this
section; it must be checked before applying these results to bounded native
designs.

For i<n define the branch lower frontier

`L_i=max(a_min+x_i, tau-(x_(i+1)-x_i))`.

The branch is `[L_i,tau]` if `a_min>tau-x_(i+1)`, and `(L_i,tau]` otherwise.
It is discarded if empty. For the strongest partner, the direct branch is
`[a_min+xn,tau]`, if nonempty. This lists the entire attainable set exactly.

For a closed branch of width `w=tau-L`, its exact capacity is

`min(floor(h/g), 1+floor(w/g))`;

for an open branch it is

`min(floor(h/g), ceil(w/g))`.

Because all nonempty branches share their upper endpoint tau, their union is
the widest such interval (closed wins a tie). The exact total capacity is
the maximum of these branch capacities. In particular

`T_value=max(T_direct,T_accessible_gap)`

is valid with these **actual** capacities. It does not justify substituting
the unqualified raw-Delta expression for the accessible gap term.

A sufficient condition for the open-band formula in Section2 with a closed
lower family bound is: no direct branch exists, and at least one maximum-gap
branch is untruncated, i.e. `a_min<=tau-x_(i+1)` for an i attaining Delta.
This condition cannot hold for a unique maximum gap immediately below xn when
`lambda>h`; that gap is truncated, although its integer capacity can remain
unchanged.

Two exact boundary examples illustrate why h,g,X are insufficient:

* `a0=.98, X={0,.01,.02}, tau=1.05, g=.01, a_min=.99`.
  Raw Delta predicts one update. Direct primaries `.99,1,1.01,1.02,1.03`
  attain five updates through partner .02. This is the predicted weak-design
  escape, not a counterexample to the restricted theorem.
* `a0=0, X={0,1}, tau=2, g=.25, a_min=1.8`.
  Raw Delta predicts four updates, but the actual attainable range is
  `[1.8,2]`, so only one is possible. With a_min=1.5 the closed lower endpoint
  instead allows three values1.5,1.75,2. A formula using only an open width
  would miss that endpoint.

If `a_min<=a0+g` and the family contains `a0+t*g` through the last complete
headroom step, the direct construction attains `floor(h/g)` for any X. It also
preserves every source when `xn-x1<=e` and `h<=e`: every partner retains the
same within-slot gap xn-x, while each earlier primary retains a witness at
least F0. This establishes the weak-design escape for scalar P/N/L/H/C/G,
but again not native D.

## 4. Legacy retention is a genuine additional restriction

The open-band theorem does not establish the same equality for T_retained.
Here is a continuous counterexample that allows nonmonotone amplitude order
and checks every legal cross:

`a0=.9, X={0,.06,.08,.10}, tau=1.10, h=e=.10, g=.02, a_min=1.0001`.

All old sources are initially within e of F0=1. The accessible maximum gap
is untruncated and equals.06, so `T_value=3`. For example primaries
`1.05,1.07,1.09` give three .02-or-larger gains when L is ignored.

**But `T_retained=2`.** For any purported three-update path, its first frontier
is >1.04 and its second must be in `(1.06,1.08]`. The two upper completion gaps
are only.02; any incoming primary that uses partner .06 or .08 has optimized
value strictly >1.08. Consequently, every primary published by the second
step must be in the zero-partner branch, with amplitude >1.04. None can
legally pair with .06. That source's best witness remains `.9+.06=.96`,
strictly below the second-step relevance threshold `frontier-.10>.96`.
This argument allows arbitrary amplitude ordering, and even multiple new
primaries within an update: any additional repair primary would itself push
the frontier above the permitted second-step level.

Two updates are feasible: publish1.06, then1.02. The first frontier is1.06;
the second uses partner .08 to reach1.10 and repairs the .06 source as well.
Every retained source is useful, all old configurations persist, and K=1.
Thus the upper bound is attained. D remains outside this scalar example.

A tempting three-partner counterexample is invalid: for
`X={0,.06,.10}, a0=.9, tau=1.10, g=.05`, publishing1.05 and then1.04
does give two legal, source-preserving gains. The second, weaker primary uses
partner .06. A regression test retains this case to prevent accidentally
assuming monotone amplitude order.

## 5. A matched five-partner class where both value and retention agree

The following exact pair establishes a legitimate prospective scalar
prediction with a margin for initial relevance:

`a0=.956, F0=1, tau=1.05, h=e=.05, g=.01, a_min=1.0062`.

| Quantity | Large-gap ecosystem | Dense ecosystem |
|---|---|---|
| Retained partner responses | 0,.0001,.0002,.0003,.044 | 0,.011,.022,.033,.044 |
| Initial complete configurations | 5 | 5 |
| Initial primary + partner source count | 6 | 6 |
| Initial source-use mass, each source | 1 | 1 |
| Initial weakest source relevance margin | .006 | .006 |
| Raw Delta | .0437 | .011 |
| Actual lowest attainable frontier | 1.0065, included | 1.039, excluded |
| Exact T_value | 5 | 2 |
| Achieved T_retained | 5 | 2 |
| K throughout | 1 | 1 |
| Native D | not established | not established |

For the large-gap ecosystem choose `a_t=1+.01*t-.0003`, t=1,...,5.
Every new frontier is1+.01t, using partner .0003. The strongest partner .044
keeps its old witness1; every cluster partner gains a new witness above1.
All earlier primaries retain witnesses at least1.01. Hence every source is
within e of every frontier through1.05. The headroom bound proves maximality.

For the dense ecosystem choose1.007 and1.017, giving1.04 and1.05 through
partner .033. All lower partners have witnesses above1; the strongest retains
the old witness1. The open attainable band `(1.039,1.05]` proves that three
g-separated improvements are impossible. This proves maximality with L.

The largest gap in the large ecology is slightly truncated by a_min:
its lower output is1.0065, not the raw-gap value1.0063. Both computations
happen to yield capacity5. The prediction should preserve this distinction
instead of reporting an unverified maximum-gap access assumption.

These scalar ecologies have equal initial optimum, cap, item count,
source-use masses and portfolio size. They do not have identical distributions
of old suboptimal utilities. A native match must report that difference and
cannot infer a common scalar response map from comparable current DPS alone.

## 6. Compatibility escape: recovery has both opportunity and legacy costs

### 6.1 A weakest-partner restriction fails the main legacy requirement

Consider a fixed semantic rule that allows every old primary/partner pairing
but restricts any primary above the old-primary amplitude to the weakest
partner x1. This rule is fixed before release; it can be represented by a
threshold feature and a single partner-load constraint. It is not an assertion
that this artificial scalar rule is already a native resource mechanism.

With all target amplitudes available, choose
`a_t=F0+t*g-x1`. Values rise by g until the headroom limit, independently of
the dense spectrum. Every original old-old configuration remains legal.

For a candidate a, the cost relative to natural cap-safe admission is exactly

* removed currently safe combinations:
  `#{x : a+x<=tau}-1`;
* immediate optimized value foregone:
  `max{x : a+x<=tau}-x1`.

In the revised dense example and the five amplitudes1.01,...,1.05, these costs
are respectively `3,2,1,0,0` combinations and `.033,.022,.011,0,0` utility.
Six new configurations are suppressed across the five releases; no old-old
configuration is removed.

However this escape has only **one** successful retained-source update under
the original e=.05. Partner .011 never receives a new witness; its old utility
is.967, so it ceases to be relevant once the frontier exceeds1.017. At final
frontier1.05, the three intermediate partners .011,.022,.033 are all obsolete.
Value-only capacity5 is therefore not a source-preserving recovery claim.

A simple sufficient condition for this guard also to preserve every old
partner is `e>=h+(xn-x1)`, because old witnesses alone then exceed tau-e.
That is **not** the primary matched setting, where e=h=.05 and span=.044.
Alternatively the compatibility design must supply other legal source-bearing
witnesses, with their immediate frontier consequences included. A label rule
that silently excludes old obligations is not an admissible escape.

### 6.2 One fixed linear budget recovers four steps while retaining every source

For the revised dense ecosystem in Section5, retain the original strong family
`a>=1.0062`, fixed cap1.05 and e=.05. Add the single, fixed inequality

`12*(a-a0)+x <= .648`, equivalently `12*a+x <= 12.12`.

This is a budget on the two component response features, applied equally to
every configuration. Every old primary/partner pair remains legal because
`a=a0=.956` and `x<=.044<.648`. No source-ID exception or changing rule is used.
It is a proposed compatibility budget; scalar algebra alone does not make it
an actual mana, rage or other engine resource-consumption mechanism.

Publish, in this order, the four amplitudes

`a_j=1.01-j*.011/12`, j=0,1,2,3.

They are all above a_min. Their optimized values are
`1.01, 1.020083333..., 1.030166666..., 1.04025`, using successively the
partners0,.011,.022,.033. Each step gains at least.01. When the frontier
would make an intermediate partner's old witness inadequate, that partner
has acquired a new legal witness. Direct substitution shows every old and
new source remains within.05 at every step. The old frontier1 remains a
K=1 portfolio, and all old/history configurations persist.

**Continuous upper bound.** Partner .044 is incompatible with the original
power cap for every incoming amplitude because `1.0062+.044>1.05`.
For each remaining partner, the fixed budget implies
`a+x<=1.01+(11/12)*x<=1.04025`. Thus every new configuration has utility at
most1.04025 and any sequence has at most `floor(.04025/.01)=4` updates. The
displayed path attains four, so this is exact T_value and T_retained for the
modified scalar class. Original D is still not established.

The intervention therefore recovers capacity **2 to4**, toward the original
headroom limit5. It does not provide a free increase in immediate opportunity.
For these four primaries, natural cap admission allows four old partners each;
the budget permits respectively1,2,3,4. It blocks six otherwise cap-safe new
configurations, with per-primary optimized opportunity losses
`.033,.022,.011,0`. Over the whole strong incoming family, the attainable peak
falls from1.05 to1.04025, a loss of.00975. All five old-old configurations
remain unchanged and legal. A same-information generic linear budget can
express this exact rule; no structured-method superiority follows.

## 7. Multiple tasks, policies, inference and prior work

For more than one task, partner responses are vectors and admission may
couple all task/policy caps. The scalar branches need not share an upper
endpoint or even admit the same partner ordering. A gap statistic computed
separately on each task therefore does not prove a joint capacity formula.
Policy switching is part of the optimizer; a scalar reduction must cover it
or explicitly restrict the policy family. The original behavior archive and
D thresholds require a separate finite-table and statistical analysis.

Threshold equalities here use exact rational arithmetic. Monte Carlo mean
estimates do not justify exact capacities at floor/ceil boundaries. Native
predictions need uncertainty or a declared numerical tolerance; dense sampling
alone is an achieved lower bound, not a continuous-family impossibility proof.

The interval arguments above are elementary and have no originality claim.
Component composition and safe pruning are already developed in
[Geilen et al., An Algebra of Pareto Points, Section6.4](https://tbasten.estue.nl/papers/pareto.pdf):
dominance-preserving pruning requires constraints closed under favorable
replacement. A cap on maximized utility violates that premise. The closely
related interface treatment in
[Hendriks et al., Definition3.19 and Proposition3.20](https://lmcs.episciences.org/7513/pdf)
also states a safe-constraint condition for preserving dominance during
composition. These results explain why a scalar current-best summary need
not preserve capped completion options; that qualitative observation is not
new. [Roijers, Whiteson and Oliehoek](https://www.jair.org/index.php/jair/article/view/10933)
develop convex coverage for multiobjective coordination, which is relevant
background for current decision coverage but does not supply the additional
legacy and sequential restrictions here. No exhaustive novelty review is
claimed for the specialized capacity identity.

## 8. Executable checks and allowed conclusion

`src/wowfs/experiments/fc_theory.py` uses rational arithmetic for accessible
bands, endpoint-sensitive value capacity, full Cartesian source witnesses and
an exhaustive finite candidate-set oracle over all publication orders.
`tests/test_fc_theory.py` checks direct escape, lambda truncation, closed/open
endpoints, two matched five-partner constructions, decreasing-amplitude
repairs, the four-partner L obstruction, the weakest-partner guard's source
cost and the four-step linear-budget recovery.

The defensible mathematical statement is conditional: **some matched
scalar additive ecologies have equal current value but different exact future
value-and-retention capacities; the brief's raw-Delta formula is valid under
stated family conditions, not universally for the complete sustainability
objective.** The exact five-versus-two family above is an abstract result;
native executed sequences, uncertainty and finite-oracle outcomes are reported
separately in `FINITE_REFERENCE_AND_UPPER_BOUNDS.md`. Neither D, cross-mechanism transfer, class/race
coverage nor a general automatic legacy-preserving compatibility escape
follows from this proof. The particular fixed budget in Section6.2 does have
a complete scalar retained-source recovery proof and explicit opportunity cost.

## 9. Fixed history and the continuation boundary

The direct and compatibility interventions above compare prospective policies
from the same original library. They do not reset a realized history. If a
history already attained frontier `F_k` and every admitted configuration remains
available, the remaining number of same-scalar-family updates is bounded by
`floor((tau-F_k)/g)`: after `t` further successful updates, monotonicity and the
gain condition require `F_(k+t) >= F_k+t*g <= tau`. No future compatibility rule
can refund past headroom while H is retained. This bound is necessary, not
generally sufficient for all value/legacy conditions. It permits decreasing
incoming amplitudes and arbitrary future composition choices.

Under the common positive affine native reduction, use the fixed initial
reference `S_q` and maximum normalized slope to express the same scalar
frontier. The fresh fitted guarded dense histories in all 51 affine contexts
have normalized growth above .04 and below .05, leaving fewer than one .01
gain. `CONTINUATION_BOUND.csv` therefore reports point-model remaining capacity
upper zero for all 51. Existing simultaneous paired margins support the
stronger growth-above-.04 statement in 35 contexts; the other 16 remain
statistically unresolved. The five nonaffine contexts are not applicable.

The frozen exact dense terminal points are not completed histories: 28 are
unreached counterfactual endpoints, and 23 also breach fresh mean power. They
are labeled separately rather than represented as successful saturation. The
abstract exact dense construction does reach its cap and then has zero
continuation capacity by the elementary bound. A genuinely new response
direction could escape a one-dimensional bound, but it is outside the tested
same-family continuation and has not been demonstrated by these comparisons.
