# Conditional structure for native complementary expansion

Status: source-grounded conditional propositions, not a claim that every native
item or every unexecuted variant satisfies their hypotheses. Numerical results,
finite grids, fitted coefficients, uncertainty and failures belong to the
immutable R3 experiment reports. This document does not claim a new generic
affine-reward theorem.

## 1. Why a fixed number of type names is insufficient

A type label such as “damage proc” does not bound proc rate, damage amplitude,
target scaling, mitigation, resource feedback or admissible pair relations.
Even within “physical periodic damage,” changing a period changes the event
schedule and the number of realized ticks. An unrestricted new item can raise
power arbitrarily without introducing a new label. Bounded type count therefore
does not imply a bounded useful safe rule.

The more precise object is a family with a shared control kernel and a
finite-dimensional reward representation, together with a finite-complexity
envelope over the allowed contexts and policies. The native Talon–Thunderfury
source audit identifies a candidate of this form: fixed base speeds, hit/crit,
trigger/tick timing and resistance effect, while changing base weapon and
periodic damage amplitudes. Its cap compensation may be useful without a
positive factorial interaction between the two item effects.

## 2. Trace-preserving affine family

Let `k` identify a fixed context, task, policy and control kernel, and let
`theta` range over a domain `Theta` of reward amplitudes. Couple all executions
to the same random stream `xi`. Assume:

1. The initial non-reward state and callback registrations do not depend on
   `theta`. Event timing, outcome probabilities, resource transitions,
   scheduling, policy predicates and stopping conditions depend only on this
   state and random draws, not on accumulated reward or `theta`.
2. Every realized event reward, conditional on that control state and draw, is
   affine in `theta`. Any clipping or damage-based branch is fixed throughout
   `Theta`.
3. The number of events before the fixed horizon is finite almost surely and
   total reward is integrable. No unproved rate bound is inferred from a finite
   rage capacity or nominal PPM.

**Proposition 1.** Under these assumptions, the control trace is independent of
`theta`, and total reward for each stream is

`Y_k(theta, xi) = c_k(xi) + a_k(xi)^T theta`.

Consequently `mu_k(theta) = c_k + a_k^T theta`, where coefficients are the
corresponding expectations. The statement also holds for an action-specific
reward vector. Counts and resource traces stay fixed, whereas normalized
damage shares are generally ratios of affine functions.

**Proof.** Induct on event order. Equal control state and the coupled next draw
give equal next event, control transition and scheduling decision. Its reward
is affine by assumption. Summing the finite trace preserves affine form;
integrability permits taking expectations. Damage and threat metrics may vary,
provided they are not read by control decisions. This also explains why a
changed speed, PPM or resource mechanic invalidates reuse of the same kernel.

Deep Wounds does not obstruct this argument in the audited configuration: its
tick reads hand average weapon damage plus AP, and the parent event's crit/hand
selects the hand. Fixed outcomes/AP trajectories leave that extra reward path
affine. Damage-dependent rage in Classic would obstruct it. The proposition is
therefore tied to the actual Forever reward/resource distinction rather than
an unrelated abstract equipment model.

This identity is a finite-horizon specialization of existing reward/dynamics
factorization. Dayan's successor representation predicts future state occupancy;
Barreto et al. represent value as expected future features multiplied by reward
weights. Those results precede this work. The possible research contribution
here is a source-audited native family, its complementary safe region, and the
identified limits of mechanism reuse. See [Dayan (1993)](https://www.gatsby.ucl.ac.uk/~dayan/papers/d93b.pdf)
and [Barreto et al. (2017), section 3](https://proceedings.neurips.cc/paper_files/paper/2017/file/350db081a661525235354dd3e19b8c05-Paper.pdf).

## 3. Fixed rule rows and what controls their number

Suppose a finite audited family has `h` control kernels and at most `J` relevant
task/context/policy evaluations per kernel. If all amplitudes share a fixed
dimension `d`, one exact mean-power rule is

`c_k + a_k^T theta <= tau_k` for every allowed evaluation `k`.

This uses at most `hJ` scalar inequalities, plus the explicit kernel membership
predicate and any domain restrictions. Its description contains `O(hJ(d+1))`
numeric coefficients at a fixed declared precision. Admitting arbitrarily many
item IDs whose amplitudes satisfy these same inequalities adds no exception
rows. IDs still require storage of their own `d` numeric parameters; the claim
concerns rule description, not the entire content catalogue.

The union over kernels requires an explicit dispatch rule: a single admitted
loadout must match one certified kernel. Membership checks and unsupported
families cannot be hidden outside the complexity accounting. A generic linear
rule method given the same features and dispatch can reproduce these rows.
There is no structured-over-generic expressivity separation.

The sharper row bound is the number `F` of irredundant envelope inequalities.
Response-matrix rank can bound representation or coefficient-estimation
dimension, but **rank alone does not bound `F`**: a polygon in two dimensions
can have arbitrarily many necessary sides. Likewise, infinitely many speeds
under one verbal type can yield infinitely many control kernels. To claim a
bound for that continuum requires a separately proved finite cover, monotonic
envelope, or approximation with a stated safety slack. Without it, type count
is not the right complexity parameter.

For an approximate upper envelope `U_k(theta)` satisfying
`mu_k(theta) <= U_k(theta)` throughout the declared domain, replace the exact
row by `U_k(theta) <= tau_k`. Numerical residuals on a finite test grid do not
prove a uniform upper envelope between points. An empirical fit with standard
errors must be labeled accordingly; a native mean-power check is not a
worst-random-seed bound.

## 4. A nonvacuous finite useful-complement condition

Let `V_old(x)` be the old competitive value on task `x`, and let `tau(x)` be the
fixed ceiling. For a candidate containing a selected legacy source `s`, let
`u_x(theta)` denote the achievable value of one allowed candidate loadout and
policy, and let `b_x(theta)` be its continuous task-conditioned behavior vector.
Let `B_old(x)` be the union of **all legal old-only policy profiles** and the
registered historical behavior archive on task `x`. The archive alone is
insufficient for the R3 substitution criterion. Fix competitive tolerance
`epsilon*s_x` and behavioral separation `delta > 0`.

Suppose there is a domain point `theta_0`, a nonempty task subset `X_*`, and
strict positive margins such that:

* Every relevant power row has positive slack below its fixed ceiling.
* For each `x` in `X_*`, `u_x(theta_0) > tau(x) − epsilon*s_x`.
* For each `x` in `X_*`, `min_{b in B_old(x)} distance(b_x(theta_0),b) > delta`.
* The legacy source's old competitive task fraction was below the required
  threshold, while the measure of `X_*` reaches it; the loadouts witnessing
  these tasks contain both the new item and `s`.

**Proposition 2.** If Proposition 1 applies on a neighborhood and the behavior
map is continuous there, a nonzero neighborhood of `theta_0` consists of safe,
competitive, behaviorally new variants that reactivate `s` under the same rule.

**Reason.** Finite strict affine inequalities and strict continuous-distance
inequalities persist locally. The competitive condition is sufficient against
any future admitted competitor, because its value is at most `tau(x)`. It is
stronger than comparison only with today's optimum. Source reactivation follows
from the assumed task measure. This is a conditional feasibility criterion,
not evidence that such a point exists in the native grid.

The condition describes actual cap compensation: a lower Physical base reward
may leave room for a legacy magic-damage channel, whose relative value depends
on task mitigation, while a periodic channel changes damage composition. No
positive mixed factorial contrast is required. Finding only a point on the cap
or novelty boundary gives no open-region conclusion.

To guarantee multiple mutually distinct future variants, suppose a segment
inside this region has length `ell` and the behavior map obeys the additional
lower-separation condition
`distance(b(theta(t)),b(theta(t'))) >= m*abs(t−t')`, with `m > 0`.
Then points spaced at least `delta/m` yield a finite set of
`1 + floor(ell*m/delta)` mutually `delta`-separated useful variants. For a strict
`>delta` definition use spacing slightly greater than `delta/m`. This is a
sufficient finite packing bound. If the behavior map is constant, reward
amplitude variants provide zero new playstyle despite different item names.
At fixed positive separation a bounded finite-dimensional behavior space has
finite packing capacity; no infinite novelty follows.

The packing statement is about the selected profiles. A sequential protocol
that archives every competitive profile of every admitted item additionally
needs separation from that larger evolving archive; pairwise separation of
one selected profile per item does not establish twenty successful waves.

These propositions preserve P and C and, under their explicit assumptions, N,
D and reactivation of the named source. H additionally requires that old
registered choices remain admitted. Global L requires a surviving competitive
witness for every legacy source in the specified registry, and does not follow
from reactivating one source. The empirical study must retain those separate
denominators and failures.

## 5. Restricted exception grammars and statistical scope

A rule language that can only add a row naming a particular forbidden pair
requires at least `n` rows to distinguish `n` separate unsafe named pairs when
no row may match more than one. The analogous item-exception list needs one
entry per individually distinguished item. A fixed affine semantic envelope
can classify arbitrarily many parameterized items using the same rows when
the assumptions above hold. This is a separation from those **restricted list
grammars**, not from general rules with wildcards, shared features, algebraic
predicates or the same feature space. The lower bound is elementary description
counting and is not presented as a novel complexity theorem.

With coupled seeds and an exact `d`-dimensional family, `d+1` affinely independent
anchors identify each seed's affine coefficients; independent held-out seeds
and amplitude points test empirical transfer. This only identifies the sampled
mean coefficient vector. Mean uncertainty still depends on independent seed
variation, event-tail behavior and the stated multiple-comparison method.
Identical action counts and tiny interpolation residuals at tested points are
strong diagnostics, not a guarantee against untested branch changes. A generic
method given the same features, anchors and coupling has the same information;
no statistical advantage over that matched method is asserted.
