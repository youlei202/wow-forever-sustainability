# Finite expansion under incompatible interaction channels

**Status: proved for the abstract model below; originality UNESTABLISHED.**
This is a constructive joint feasibility statement, not a claim about the missing
native Forever simulator. The six-slot finite experiment uses a different
eight-task utility table and does not inherit this theorem's joint feasibility.
The scalar obstruction is classical trade nonseparability. The construction
combines it with explicit reward, history, and portfolio conditions; its
scientific novelty requires further assessment. All mechanisms here are line A:
the utility function is fixed, and only admissibility changes.

## 1. Definitions and common initial state

There are two mandatory equipment slots. The left slot initially contains
`n` (neutral) and `p_0` (channel 1). The right slot contains `r_0` and `r_1`,
of channels 0 and 1 respectively. One new left-slot item `p_t` arrives at
each round `t = 1,...,T`; its channel is 0 for odd `t` and 1 for even `t`.
Thus the same right-slot rewards pair with rewards from arbitrarily many
different rounds: channel compatibility is not an age restriction.

Fix `0 < w <= epsilon < a < 1`, `delta > 0`, positive integer `T`,
`T delta <= w`, and `beta > w`.
The two tasks `+` and `-` have weight 1/2 each. Their scales are 1. Define

\[
q(n)=-a,\qquad q(p_t)=a-w+t\delta\quad(0\le t\le T).
\]

Let `I(z)` indicate that the left item is nonneutral and its channel differs
from the right channel. Fixed task utilities, which also serve as power
endpoints, are

\[
u_+(z)=1+q(z)+\beta I(z),\qquad
u_-(z)=1-q(z)+\beta I(z).
\]

The same fixed cap `tau = 1+a` applies on both tasks at every round. The
behavior vector is the *actual two-task utility vector* `(u_+,u_-)`, with
the infinity norm. This records a performance tradeoff, not an equipment ID.
There is one action policy. The initial admissible set is

\[
F_0=\{(n,r_0),(n,r_1),(p_0,r_1)\}.
\]

All methods begin with exactly this set. It is representable by one scalar
budget: price `p_0` and `r_0` at 1, the other initial items at 0, and set
the budget to 1. In particular the scalar class is not already infeasible at
initialization. Register **all** of `F_0` as historical witnesses. After each
successful round, register all currently legal configurations. Assign each
left item its own source; right items belong to the initial neutral source.
Every source has an admissible configuration in which its left reward changes
the two-task utility vector. Competitive use does not imply unique necessity.

The required joint thresholds are: power at most `tau`; one new item with
epsilon-optimal use on task mass at least 1/2; novelty at least `delta` from
every legal old-only behavior under the current rule and from the historical
behavior archive; every past source epsilon-optimal on task mass at least
1/2; preservation of all historical configurations without changes in their
performance; and `K(epsilon,alpha) <= 2` for any `0 <= alpha < 1/2`.

## 2. Background lemma: the protected two-trade

Let `v(z)` be a configuration's item-incidence vector. Suppose two required
configurations `g_1,g_2` and two unsafe configurations `b_1,b_2` satisfy

\[
v(g_1)+v(g_2)=v(b_1)+v(b_2).
\]

No scalar rule `c^T v(z) <= B`, even with arbitrary real prices and arbitrary
repricing, can admit both `g_i` while rejecting both `b_i`.

**Proof.** Admitting the first pair gives a total price at most `2B`.
Rejecting the second pair gives a total strictly greater than `2B`.
The incidence identity makes the totals equal, a contradiction. This proof
does not require nonnegative prices. Ties at the budget are admissible. ∎

This is an elementary instance of the trading characterization of weighted
games; see [Taylor and Zwicker (1992), original paper](https://www.math.hkust.edu.hk/~maykwok/courses/MATH392K/07Spring/trade%20robust.pdf).
It is background, not a new theorem about threshold functions.

## 3. Joint finite-horizon theorem

**Theorem 1.** For the sequence and thresholds in Section 1, a fixed rule
with two semantic budget constraints satisfies P/N/D/L/H/C at every one of
the `T` rounds, retains the initial performance floor, and has exact
`K(epsilon,alpha)=2` for `0<=alpha<1/2`. In contrast, no compatible scalar
budget can satisfy P, H, and N jointly at round 1. Thus the maximum jointly
successful prefix over this specified finite sequence is `T` for the two-rule
class and 0 for the scalar class.

The two-rule class is a subclass of unrestricted generic two-budget rules.
Consequently this theorem gives **no expressivity separation** between
structured rules and generic rules of the same dimension.

**Construction.** Assign all left items their channel tag at release. Keep
the following two inequalities unchanged forever:

\[
\mathbf 1\{\text{left channel}=1\}+\mathbf 1\{\text{right}=r_0\}\le1,
\]
\[
\mathbf 1\{\text{left channel}=0\}+\mathbf 1\{\text{right}=r_1\}\le1.
\]

The neutral item has neither left tag. These are two forbidden-effect-pair
constraints, equivalently two additive nonnegative budgets. They admit the
two neutral configurations and exactly one configuration for each `p_t`.
At initialization the second constraint is vacuous. The number of rule
dimensions is 2; item metadata and the item library still grow with `T`.

**Proof of P and floor.** An admitted configuration has `I(z)=0`. Since
`-a <= q(z) <= a`, both utilities are at most `1+a`. Each previous
configuration remains admitted and its utility function is unchanged, so
`V_t(x) >= V_0(x)` on both tasks. Power control follows from the explicit
interaction model and forbidden terms, not from assuming the conclusion.

**Proof of N.** The newly released `p_t` has the largest `q`. Pairing it
with the right item of the same channel attains `V_t(+) = 1+q(p_t)`.
It therefore has competitive use on task mass at least 1/2. Every proposal
consists of one item, so the useful new-item fraction is 1.

**Proof of D.** Among old nonneutral items, the largest `q` is
`q(p_{t-1}) = q(p_t)-delta`. All others are further away, including the
neutral item because `2a-w > epsilon >= delta`. On admissible
configurations the infinity distance between utility vectors equals the
absolute difference in `q`, so the minimum old-only distance is `delta`.
All earlier admissible behaviors use these same older `q` values. Thus
the historical archive gives the same lower bound. No optimization budget
or rule-change artifact creates this novelty.

**Proof of L and H.** The neutral source attains `V_t(-)=1+a`. For every
`j<=t`, the configuration containing `p_j` falls short of `V_t(+)` by
`(t-j)delta <= w <= epsilon`; it is competitive on mass at least 1/2.
The same fixed inequalities protect *all* previously legal configurations.
Performance of each historical witness is exactly unchanged.

**Proof of C.** A neutral configuration and the current `p_t` configuration
attain both task optima, proving `K<=2`. Every nonneutral configuration
is more than epsilon below the optimum on task `-`, because its deficit
is at least `2a-w > epsilon`. Every neutral configuration is more than
epsilon below the optimum on task `+`, for the same reason. A singleton
therefore covers only task mass 1/2. Since `alpha<1/2`, `K=2`.

**Proof of scalar impossibility.** History requires
`g_1=(p_0,r_1)`. At round 1, the only configuration using the new item
that can satisfy power is `g_2=(p_1,r_0)`: its other pairing is unsafe.
New-reward usefulness requires some admissible configuration using that
item, and hence requires `g_2`. Meanwhile
`b_1=(p_0,r_0)` and `b_2=(p_1,r_1)` are unsafe on task `+`, since

\[
u_+(b_1)=1+a-w+\beta>1+a,
\quad
u_+(b_2)=1+a-w+\delta+\beta>1+a.
\]

Both must be rejected. Each of the four involved items occurs once on
each side of `v(g_1)+v(g_2)=v(b_1)+v(b_2)`, so the lemma applies.
This is a **P+H+N** obstruction. P+H alone permits rejecting the new item. ∎

### Concrete working point

`a=0.25, w=epsilon=0.05, delta=0.01, beta=0.08, T=5`.
The cap is 1.25 on both tasks. Initial optima are 1.20 and 1.25; final
optima are 1.25 and 1.25. Therefore total growth relative to the initial
task optimum is at most 4.167%, and never compounds. Every source remains
competitive on at least 50% task weight, each update adds behavior distance
0.01, and `K=2`. These values are a theorem example, not a native study
working point or a 20-round empirical result.

### What is and is not quantified

For this monotone schedule, the explicit width condition is `T delta<=w`.
There is no infinite-expansion claim: with fixed `w` and `delta`, the
construction permits at most `floor(w/delta)` such increments. Changing
delta to shrink with `T` changes the scientific requirement.
The result does not characterize the optimal capacity of arbitrary
nonmonotone sequences, higher-dimensional behavior, or larger mechanism
classes. It also does not establish that the two-tag hypothesis describes
native combat, or that protected sources are each indispensable. Interior
positive-cluster items are substitutable, despite changing actual utility.

## 4. General hyperedge representation and a statistical implication

Suppose known incidence features `phi_j(z,x)` and known baseline `g(z,x)`
satisfy the exact fixed model

\[
\mu(z,x)=g(z,x)+\sum_{j=1}^d\theta_j\phi_j(z,x),
\qquad \sup_{z,x}\sum_j|\phi_j(z,x)|\le L.
\]

An interaction feature can be a hyperedge indicator `1{E subset z}`.
Requiring `sum_{i in E} 1{i in z} <= |E|-1` removes that interaction
exactly. The inequality and any overlap with other rules must be counted
in the total rule complexity. Knowing that some interactions are absent
does not prove that omitted interactions do not exist; completeness of the
feature model is an explicit, falsifiable assumption.

**Proposition 2 (conditional finite-data certification).** Assume each
coefficient is identifiable by a specified probe whose independent repeated
observations have mean `theta_j` and lie in an interval of length `R`.
The probes may be actual paired contrasts, but a paired contrast counts
its underlying physical simulations separately. Fix a predeclared finite
parameter list and sample size. For `rho>0`, `eta in (0,1)`, sample each
probe

\[
n\ge\frac{R^2}{2\rho^2}\log\frac{2d}{\eta}
\]

times. With probability at least `1-eta`, simultaneously for all
configurations and tasks in the specified feature model,

\[
|\widehat\mu(z,x)-\mu(z,x)|\le L\rho=:e.
\]

Hence the following conservative checks are jointly valid on that event:

* P: `max_{z in F} muhat(z,x)+e <= tau(x)` for each task.
* N/L/C: a proposed utility witness is epsilon-optimal if
  `max_{z in F} muhat(z,x)-muhat(witness,x)+2e <= epsilon s(x)`.
* D: if behavior is a fixed vector of these utility endpoints, an estimated
  infinity distance from every old/current and archived comparator of at
  least `delta+2e` certifies distance at least `delta`.
* H is checked exactly from the rule and item-incidence data.

All candidates chosen *after seeing the estimates* are covered because the
event is uniform. If additional adaptive parameter lists or new batches are
introduced, allocate a summable roundwise error budget; the displayed
fixed-sample argument is not an anytime confidence sequence. Exact boundary
points may remain unresolved at every finite sample size. This proposition
does not guarantee that a certificate is found without slack.

**Proof.** For each coordinate, Hoeffding's two-sided bound gives
`Pr(|thetahat_j-theta_j|>rho)<=2 exp(-2n rho^2/R^2)`. Union bounding over
`d` coordinates gives the asserted event. On it, the prediction error is
at most `sum_j |phi_j| rho <= L rho`. The maximum of a family of numbers
changes by at most the largest componentwise change. A difference of two
utilities, or a distance of two utility vectors, therefore changes by at
most `2e`. The displayed conservative inequalities follow. ∎

This uses a mature concentration argument, not a statistical novelty claim.
The link to structure is the *identifiable coefficient model* and the fact
that a blocked interaction has identically zero feature on the admitted
set. The total probe count is `d n`; it need not be proportional to the
number of full configurations. This is **not a minimax improvement over
generic methods**, which can use the same features and measurements. It
is also not independent of library size unless `d`, `L`, the probe access,
and bounded support remain controlled as the library grows. Transductive
linear experimental design has substantially stronger prior guarantees:
[Fiez et al. (2019)](https://papers.neurips.cc/paper_files/paper/2019/hash/8ba6c657b03fc7c8dd4dff8e45defcd2-Abstract.html).

In Theorem 1, known `q` values and two unknown channel-mismatch coefficients
give `d=2`. A mismatched/matched contrast for a fixed left item identifies
its channel coefficient, assuming the model has no other right-item effect.
Once the two interactions are excluded, neither coefficient contributes
to admitted utility; sampling primarily confirms that the exclusions address
real hazards. If right items also alter base performance or hidden three-way
interactions occur, these probes do not identify the assumed two coefficients.
The general proposition is an assumption-level bridge, not a native estimate.

## 5. Counterexamples and scope checks

1. **Remove history.** At round 1 a scalar rule can ban `p_0` and admit
   `p_1`; the protected two-trade disappears, while a legacy condition may
   still fail. History must appear explicitly in the impossibility statement.
2. **Remove useful release.** Price every new item prohibitively; P and H
   are feasible for the scalar class. Rejection is not a successful expansion.
3. **Remove interaction.** If `beta=0`, the unrestricted library is power
   feasible; the threshold obstruction has no unsafe configurations.
4. **Allow generic two budgets.** Use the exact two semantic rows as free
   weights. Generic capacity is at least structured capacity. Any observed
   difference is an algorithm, optimization, regularization, or information
   difference, and must be labeled accordingly.
5. **Rename rewards.** Repeating an old `q` gives D=0 even when a new item
   has a new ID or channel; behavioral novelty cannot be inferred from names.
6. **Unmodeled triples.** An added positive interaction on a configuration
   satisfying both pair rules can violate P. Pairwise exclusion gives no
   universal guarantee for arbitrary higher-order combat.
7. **Finite behavior.** Pairwise delta-separated points in a compact
   behavior space form a finite set. The one-dimensional positive cluster
   contains at most `floor(w/delta)+1` separated values, including `p_0`.
   This is a standard packing obstruction, not a main novelty claim.

## 6. Claim-to-evidence map

| Statement | Assumptions | Known tool | Contribution attempted here | Proof status | Observable quantity / experiment | Counterexample |
|---|---|---|---|---|---|---|
| Scalar P+H+N obstruction | Two required and two unsafe configurations with equal summed incidence | Trading/nonweightedness | Correct sequential protected/new-witness interpretation | Complete | Four configurations and incidence identity; finite experiment pair family | Drop N or H |
| Joint finite expansion | Exact two-channel model, two tasks, bounded novelty interval | Two threshold intersections; elementary tradeoff geometry | Explicit simultaneous P/N/D/L/H/K construction | Complete; originality unestablished | Standalone rational enumeration; separate from six-slot run | Hidden interactions, overlong novelty schedule |
| Generic containment | Generic admits arbitrary same-count additive rows | Set inclusion | Baseline correctness constraint | Complete | Reuse structured rows in generic optimizer | Restricted generic class must be renamed |
| Finite-data decision | Identifiable fixed finite coefficients; independent bounded probes; exact model | Hoeffding and triangle inequality; linear experimental design | Conditional mapping from interaction probes to joint checks | Complete conditional proposition; no statistical novelty | Probe rank, residuals, support, interval widths; native unrun | Unidentified or missing interactions |
| Native Forever relevance | Real event model and measured shared structure | None substitutes for evidence | Application and transfer claim | **Not established: engine unavailable** | Requires native data | Abstract fixtures do not certify engine support |

Reproduction: `source scripts/env.sh` then `python scripts/verify_theory.py`.
The rational verifier checks all rounds, all configurations, the minimal
portfolio, current-rule and archival D, and the trade identity. Its JSON
output goes under `WOWFS_WORK_ROOT/artifacts/latest/theory/`.
For legacy use, the verifier reports the task weight of witnesses containing
each source's designated left item. These are sufficient lower bounds on the
source's best competitive weight; the neutral source can additionally occur
through its right-slot items. No exact deletion-source loss is claimed.
