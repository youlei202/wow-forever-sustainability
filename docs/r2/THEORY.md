# R2: reusable resource contracts and the limits of zero-growth choice

**Status: conditional analytical result; native applicability and originality
unestablished. No native observation, fitted event model, benchmark run, or
class/race coverage is asserted here.** This document does not extend or rerun
the R1 monotone reward construction. Its purpose is to state one falsifiable
mechanism hypothesis, including short windows and strategy substitution.

The result below combines standard resource accounting with a finite timing
choice witness. Neither component is claimed as an AISTATS contribution. The
scientific question still needing native evidence is whether actual effects
admit these contracts without destroying useful interactions, and whether old
items and permitted strategies can already reproduce the proposed behaviors.

## 1. A contract that covers windows, queued effects, and future items

Fix a resource inventory `r` with `q` components and componentwise capacities
`C`. It includes **escrow for delayed effects**: scheduling damage cannot remove
the associated liability from the inventory before that damage is accounted
for. For every interval `W=(s,t]`, the external supply vector satisfies
`A(W) <= a(t-s)`, componentwise. The function `a` and capacities are frozen.
These are deterministic envelopes, not empirical average regeneration rates.

Each reward/trigger transition `e` has net resource debit `d(e)` and
nonnegative output `y_k(e)` for each power endpoint `k`. Debits may have
negative coordinates for conversion/refund effects. The inventory identity is

`r(t) = r(s) + A(W) - sum_{e in W} d(e)`, with `0 <= r <= C`.

Fix nonnegative weights `w_k`. Every admitted transition must satisfy

`y_k(e) <= w_k^T d(e)` for every endpoint `k`.                   (1)

Also fix `w_* >= 0` and `epsilon > 0` such that every reward/trigger transition
satisfies `w_*^T d(e) >= epsilon`. Pure bookkeeping operations may instead be
excluded from this count, but they must separately be nonexplosive and produce
no unaccounted reward or triggers. Reservations, cancellations and refunds
must preserve the inventory identity.

These conditions are **local but uniform**: they must hold in every reachable
state, with every allowed parent trigger, target count, buff and resource
conversion. A typed effect grammar or source-level transition check could
establish them. Isolated-item mean measurements cannot establish them. All
equipped effects draw from the same inventories; adding an item cannot create
an unrecorded private refill. Damage multipliers, healing, absorbs, summons and
queued procs must enter whichever endpoints are being bounded. If they cannot
be represented faithfully, this hypothesis is inapplicable.

**Proposition (reusable safety contract with finite choice capacity).**

**(a) Window guarantee.** Under these contracts, for every admitted loadout,
every allowed strategy and every interval of length `h`,

\[
Y_k(W)\le w_k^T C+w_k^T a(h),\qquad
N(W)\le\frac{w_*^T C+w_*^T a(h)}{\epsilon}.
\]

These bounds remain valid after any number of item additions satisfying the
same contracts. The event count is finite on every finite interval when
`a(h)` is finite. If the displayed power bound is below a prescribed window
cap, that cap is guaranteed. This is a sufficient condition, potentially a
very conservative one; it does not assert that native initial optima attain
the bound. Adding items without changing the mechanism or existing primitive
semantics preserves old loadouts and their pathwise behavior.

**(b) Nonempty finite choice witness without any envelope growth.** A special
case supports the following exact, finite statement. Take one nonrenewable
unit of output credit per fight, two fixed nonoverlapping release windows
`E` and `L`, and a mandatory slot selecting one release profile. A profile
`p` spends fraction `p` in `E` and `1-p` in `L`; it cannot move its releases
between windows. The initial items have profiles `p=0` and `p=1`. Item
switching during the fight and within-fight synthesis of multiple profiles
are unavailable. All other permitted strategy choices preserve this profile.
This is an explicit mechanism assumption, not a restriction to impose after
seeing native results.

Fix the same three tasks at initialization, with equal weights:

\[
P_E(p)=p,\qquad P_L(p)=1-p,\qquad P_S(p)=p+(1-p)=1.
\]

Their meaning is early output, late output and sustained total output. Choose
an integer `m >= 2`, a **fixed** behavior separation `eta=1/m`, and one new item
for each profile `p=j/m`, `j=1,...,m-1`, in any order. The behavior is the
within-fight output pair `b(p)=(p,1-p)`, with infinity distance. Then:

* Every fixed-task optimum stays **exactly 1**, including both window tasks.
  No initial power envelope is consumed: all three growth values are zero.
* There are `m-1` additional, mutually `eta`-separated competitive behaviors.
  Each is exactly optimal on sustained output, so both new and retained
  items have competitive task mass at least `1/3` at every round.
* Deleting any one item and reoptimizing over all remaining profiles leaves
  behavior distance at least `eta` from its removed profile. All old profiles
  remain unchanged and legal. After all additions, every profile has a
  neighbor at distance exactly `eta`.
* For relative near-optimality tolerance `tau < 1/2` and required task
  coverage greater than `2/3` (including `tau=0.05`, coverage `0.95`), the
  minimum portfolio size is **exactly `K=2`** at every round.
* No new reward is required to improve a task optimum: deleting an interior
  item has **zero optimal scalar performance loss on all three tasks**.
  Its certified value is a competitive timing option with positive behavior
  deletion loss. This distinction must accompany any usefulness claim.

For an arbitrary fixed separation `0<eta<=1`, keeping both endpoints leaves
at most `floor(1/eta)-1` additional profiles with separation at least `eta`.
An equally spaced grid with `m=floor(1/eta)` attains that bound when `m>=2`;
when `m=1`, the two original endpoints already exhaust the capacity.
Capacity is finite and depends on meaningful timing resolution; it does not
depend on upward drift in the task envelope. This arithmetic example is not
a 20-round study, evidence for native timing mechanics, or evidence that the
native 5% usefulness definition is sufficient for player value.

### Proof

For any finite prefix of transitions in a window, sum (1) and substitute the
inventory identity. Nonnegative inventory at the end and `r(s)<=C` give

`sum y_k <= w_k^T [r(s)+A(W)-r(t)] <= w_k^T[C+a(h)]`.

The same calculation using `w_*^T d >= epsilon` bounds the number of counted
transitions in every prefix. Consequently an infinite number in a finite
window is impossible; the argument does not assume finite event counts and
then use the resulting inequality to assert nonexplosion. It uses no linear
state dynamics or spectral-radius estimate. Every future primitive satisfying
the contract obeys the identical telescoping calculation.

For (b), use a unit inventory and debit exactly the released output; delayed
credit stays in escrow. Outputs are deterministic, nonnegative and sum to
one. There are at most two release events; on the grid each nonzero debit is
at least `1/m`, so the event-count contract holds with `epsilon=1/m`. Each
window output and total output is at most one, and the original endpoints
continue to attain each relevant optimum. Infinity distance between profiles
is `|p-p'|`; all distinct grid points are at least `1/m` apart. Thus neither
old-only reoptimization nor the complete historical archive contains a closer
profile. All profiles attain the sustained optimum. One profile can be
`tau`-near-optimal for early output only if `p>=1-tau`, and for late output
only if `p<=tau`. These cannot both hold for `tau<1/2`. A singleton covers at
most two of the three equally weighted tasks, whereas the two unchanged
endpoints cover all three. Hence `K=2`. Finally, sorted separated profiles
including both endpoints have at most `floor(1/eta)` gaps in an interval of
length one; the grid attains that bound. ∎

## 2. Why the strategy and behavior clauses matter

The witness does not justify treating arbitrary expected timing vectors as
new choices. If old gear can vary release timing, split charges, switch items,
or combine the two endpoints within one fight, it may already realize every
interior profile. Then the deletion distance is zero. Full reoptimization
must include those actions.

Even randomizing between the original endpoint items before a fight can
match **every mean** profile. If novelty is defined only on expectations and
randomized loadouts are allowed, part (b)'s novelty conclusion does not apply.
The pathwise/profile interpretation distinguishes a guaranteed split from
a mixture that produces all-early or all-late output in each fight. One can
formalize that distinction by distance between per-fight profile distributions:
against a deterministic profile, the 1-Wasserstein infinity-norm distance of
any mixture of remaining grid profiles is at least `eta`. This does not imply
that native players value that distinction; the task and behavior definition
must be frozen from real combat before confirmation.

Thus the constructive statement supports **behavioral option value**, while
exposing the limitation of competitiveness alone. It does not prove new
sources indispensable for task performance, solve arbitrary nonlinear
objectives, or establish an advantage over a generic optimizer with the same
resource contracts and information. A generic rule class containing these
contracts can implement the same result.

## 3. Failure tests and connection to event amplification

The proposed nonnegative event model `v <= b+Gv` is an alternative candidate,
not an assumption discovered in native traces. If `v` is finite, `G>=0`, and
`rho(G)<1`, multiplication by the nonnegative inverse yields
`v <= (I-G)^(-1)b`. This is standard positive-system reasoning; linear storage
methods are established in [Rantzer (2015)](https://arxiv.org/abs/1203.0047).
An inequality in extended expectations alone does not prove finiteness:
`infinity <= 1 + (1/2) infinity` supplies no finite bound. Generation-wise
domination can instead establish integrability, but that stronger model must
be proved or justified.

Concrete ways for the candidate contracts or interpretations to fail:

1. **Mean stability is not a burst cap.** A parent creates `M` simultaneous
   children with probability `c/M`, otherwise none, for fixed `0<c<1`.
   Reproduction mean is `c`, yet one burst has at least `M+1` events with
   positive probability, for arbitrarily large `M`. A mean guarantee cannot
   be reported as a pathwise or high-quantile cap. Even `G=0` permits arbitrary
   synchronized external bursts unless external arrivals are window-bounded.
2. **Individually stable effects need not compose.** The two matrices with
   sole nonzero entries `G_A[1,2]=2` and `G_B[2,1]=2` each have spectral radius
   zero, but their sum has radius two. Isolated stability certificates cannot
   replace a common compositional condition.
3. **Queued effects can hide boundary debt.** Charging a proc when scheduled,
   discarding its liability, and observing only later release windows can
   violate the window bound. Escrow, bounded pending work, or a justified
   carry-in term is necessary; whole-fight accounting alone is insufficient.
4. **A zero-cost loop defeats event finiteness.** A trigger that refunds its
   complete debit and recursively retriggers has no positive debit margin.
   It is excluded by the event-count contract. Replacing that condition with
   a fitted mean cost does not exclude a reachable explosive state.
5. **Hidden interactions defeat identifiability.** Let all isolated-item
   observations agree, while one engine has output `a+b` and another has
   `a+b+theta*1{A and B active}`. No amount of isolated-item replication
   distinguishes them. A paired effect switch can reveal this interaction;
   an additional hidden `A*B*C` term still escapes all probes of order at most
   two. Source-level semantic closure or richer interventions are necessary.
6. **New semantics can consume contract capacity.** A new trigger entrance,
   resource refill, target-dependent multiplier or unrepresented stock must
   obey the original inventory and weights. If it cannot, admitting it
   requires changing the model, rejecting the item or changing the mechanism.
   Adding a type, stock, endpoint, exception or threshold is rule growth.

## 4. What would make this relevant to native Forever

The recovered community engine's inspected source now provides concrete
hypotheses; see [NATIVE_MECHANISMS.md](NATIVE_MECHANISMS.md). In that engine,
white-hit rage is based on weapon speed, extra attacks can produce more
eligible events, and item/set procs can refill rage. Therefore its finite
rage cap is **not** a finite bound on cumulative resource supply. Substituting
the cap alone for `C+a(h)` would be invalid. The candidate contracts above
have not been verified for these feedback paths.

The inspected Diamond Flask/Cloudkeeper implementation already shares an
offensive cooldown timer that excludes overlapping activations. This supports
a native occupancy hypothesis, not a claim that we invented shared cooldowns
or that their nonoverlap bounds every damage source. Likewise, a research
gate accepting at most one extra-attack request batch per `c` seconds bounds
accepted batches in a length-`h` interval by `1+floor(h/c)`. To turn that into
a realized-hit bound additionally requires a maximum batch size and either
a maximum release delay or bounded pending carry-in. Delayed queues cannot
be silently omitted from a burst claim.

The next native evidence must identify an actual finite inventory (including
delayed liabilities), all its refill and conversion routes, and the complete
reachable event contracts. It must then show a useful set of old and new
profiles surviving the same frozen mechanism, with isolated and mixed effect
switches plus full strategy reoptimization. Finite observations can falsify a
uniform contract; without a validated structural model they cannot certify
all reachable states or unseen interaction orders.

There is no new statistical guarantee in this document. With an identified
finite signature model, measurement vectors and admission decisions may
differ, but that is already the setting addressed by
[Fiez et al. (2019)](https://arxiv.org/abs/1906.08399). A fair comparator gets
the same signatures, probes and source access. The proposed contribution
remains **unestablished** until a native mechanism and its preserved reward
tradeoffs substantiate the conditional result.
