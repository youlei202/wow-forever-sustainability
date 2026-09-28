# Decision value, composition, and retained sources

This note separates exact conditional facts, native finite-table evidence and
unfinished contribution claims. The original R5/R6 statements and outputs are
unchanged. The development decision problem is eight actual R4 combat tasks,
equal task weights, fixed equipment during combat, task known beforehand and
all three allowed policies available to both old and expanded libraries.
G uses the complete admissible old gear/policy optimum. Its fixed threshold is
1% of the initial task optimum on task mass at least 1/8. P/N/D/L/H/C retain
their earlier meanings. D is never substituted for G.

## 1. Logical and historical boundaries

**Fixed-frontier boundary.** If the same decision problem satisfies
`V_t(q)=V_0(q)` at every time, then `G_t(q)=V_t(q)-V_(t-1)(q)=0` identically.
This is an identity, not a new impossibility theorem. In its single declared
task/policy/partner domain R6 preserved the old optimum, so its D-positive
sequence provides no positive G for that same decision problem.

**Released-set state boundary.** Suppose physics, task and policy permissions,
and a memoryless gear admission predicate are fixed. At each publication admit
every legal configuration using available components that satisfies the
predicate, retain all previous configurations, and register the initial source
obligations plus every published new source. Then two histories with the same
released component set have identical available configurations, task optima,
source obligations and full-configuration behavior reference sets. They have
identical feasible continuations under any fixed common future sequence.

Proof: each legal configuration's inclusion depends only on the set of its
components and the fixed predicate. The set therefore agrees across histories.
Every recorded past behavior is a profile of a retained configuration under a
fixed policy, and is already contained in the full old-profile reference.
Thus archived competitive profiles add no extra comparators. All predicates
and transition domains agree; induction gives identical future possibilities.
This statement does not cover history-specific exceptions, changing physics,
extra registration conventions or changed information/strategy permissions.
It rules out interpreting a different component arrival time as a separate
history effect in our all-power-safe finite DP.

## 2. Complete additive coequipment: source gaps cancel

Let slots have finite option sets X and Y, every cross-pair be legal and
admitted, and task utility after the declared control optimization be exactly
`u(x,y;q)=a_x(q)+b_y(q)`. Optimization must preserve this separability; a shared
policy that couples the two components cannot be silently maximized separately.
For a protected source identified with x, write its best value as V_x(q).
Then

```
V(q) - V_x(q) = max_(x' in X) a_x'(q) - a_x(q).
```

Proof: both unconstrained optima contain the identical additive term
`max_y b_y(q)`, which cancels. Adding or improving opposite-slot partners can
raise output, but cannot reduce x's relevance gap. The identity holds task by
task, so it also preserves the tasks on which x is within any fixed raw
relevance allowance. A native cross-slot restoration claim must consequently
identify interaction, coupled policy/legality, or admission truncation.
This is an elementary separability result, not an original algorithm.

## 3. Fixed upper caps change valid component substitutions

Under an unchanged capability cap, the full legal cross product is still
considered, but the admitted set is

```
S = {(x,y): a_x(k)+b_y(k) <= tau(k) for every capped context k}.
```

Source x now has partner set
`Y_x={y: b_y(k)<=tau(k)-a_x(k), every k}`. Its value is
`a_x(q)+max_(y in Y_x)b_y(q)`, if Y_x is nonempty. The partner term depends on
x and no longer cancels. This formula is directly computable from component
coefficients and cap rows; it does not assume joint feasibility in advance.

Reward-only component dominance is insufficient for deletion. Replacing a
component by one with larger reward in every task can violate an upper cap.
This does not contradict convex coverage or constrained dominance: valid
substitution must also preserve every relevant resource/feasibility direction.
If performance is both a maximized reward and a capped capability, the two
directions oppose each other. The observation alone is established constrained
optimization logic, not a new dominance theorem.

For one task let the old anchor have value F0, headroom h>0, a new primary
contribute a, and a new companion contribute b relative to their old
components. Assume the old library contains only the baseline option in each
of these two slots, all four combinations are legal, and responses are exactly
additive. A fixed cap is F0+h. For required gain g>0, the new pair both fits and
improves iff

```
g-a <= b <= h-a.
```

If `a>h` and `b<=0`, both singleton releases have zero admissible positive
gain, while a pair in that interval has gain at least g. The stronger primary
with the old companion is rejected by the same cap predicate; the weaker
companion alone cannot improve the old optimum. Deleting either new source
from the pair returns value F0. Thus minimum gain-bearing publication size is
two, despite an exactly zero physical interaction term. If the cap is removed,
the primary alone wins and the companion is unnecessary.

Proof: the four gains are 0,a,b,a+b. The premises make a inadmissible and b
nonpositive. The interval is precisely `g<=a+b<=h`. No other configurations
exist in this specified model. These inequalities also show why a wider old
library must be checked: an existing weak partner may already complete a.
The general vector completion set is the intersection of upper halfspaces
`b(k)<=tau(k)-a(k)` and usefulness lower halfspaces at the designated tasks;
this is ordinary constrained additive composition, not a new polytope method.

## 4. Permanent usefulness witnesses can be shared

Fix raw relevance allowances e(q), caps tau(q), task weights and a source-use
mass threshold rho. For each protected source s suppose there is a retained
configuration/policy witness attaining at least `tau(q)-e(q)` on a set of
tasks of mass rho. Every future library satisfying the same caps and retaining
those witnesses preserves source s's competitive use, regardless of other
combinations and regardless of how many sources share a witness.

Proof: future optimum V(q)<=tau(q), so each retained witness has utility at
least `V(q)-e(q)` on its certified tasks. Its mass remains rho. Apply this
argument separately to all sources. No one-to-one source/witness matching is
required or implied.

An actionable special case is `tau(q)-F0(q)<=e(q)`. Any new source participating
in a retained configuration at least as good as F0 on sufficient task mass
then has a permanent source-use witness. A gaining pair can establish this for
both new sources simultaneously. Initially merely near-optimal old sources
need their own witnesses; the headroom inequality alone does not protect them.
This sufficient condition is checked from fixed caps and actual source-bearing
configurations. It is stronger than ordinary N, and does not assume every
future release already passes L.

In the scalar completion class, if h<=e and 0<g<=a+b<=h, both new sources are
permanently useful under the cap, while the old anchor also remains within e
of the optimum. If each old source has that anchor or another certified old
witness, P/N/L/H hold and the old anchor supplies a size-one near-optimal
portfolio C. Actual combat-observable D still requires a separate check; it
does not follow from additive rewards, item names or cap completion.

**Finite gain budget.** With retained old choices, V_t(q) is nondecreasing. If
every successful release gains at least gamma*s(q) on task mass rho, integrating
and telescoping gives

```
T*gamma*rho <= integral [(tau(q)-V_0(q))/s(q)] dnu(q).
```

For finite tasks, sum the normalized increments over times and tasks; each
step contributes at least gamma*rho, while each task's total increment is at
most its fixed headroom. This standard potential bound is not a new capacity
theorem. Behavioral packing can impose another independent restriction; its
threshold must remain fixed. Neither shrinking thresholds nor adding
item-specific tasks constitutes continued success under the same objective.

## 5. What the native development table establishes

Four cached ecosystems and two races produce 927 method/release evaluations
for singletons, pairs and triples. Eighty-six all-power-safe releases pass all
six original predicates and G; no naturally unrestricted complete opening in
this screen does. The exact finite monotonic upper bound for a singleton is
its full cap-safe optimum: if that cannot provide G, no cap-safe subset can.
This proves gain-specific singleton failure for the following pair witnesses,
without a timeout or dependence on D:

* `resource_haste`, Human, sources 19951+22000, gear 56f6e84ebc6b9963:
  burst_10s complete-old optimum391.9981 to410.5790, fixed cap411.5980.
  A matched fixed-policy four-cell contrast is +7.2072 DPS, so this case may
  involve physical interaction as well as compensation; its cap margin is small.
* `timing_shared`, Orc, sources 18203+19019, gear feca88feff2548de:
  high_armor complete-old optimum182.1205 to186.7005, fixed cap191.2265.
  Matched old/old, weak/new-primary slot variants have values173.8694,
  156.2695,204.0517,186.7005 at fixed native_reck. The positive item alone
  exceeds caps, its weaker partner restores safety, and the mixed interaction
  is only+.2487 DPS. The same pair improves endurance_360s despite a negative
  fixed-policy interaction of−5.5684 DPS. Positive synergy is not necessary
  for these finite-table decision-gain observations.

All values above are selected 16-seed development means, not independent
confirmation or exact population identities. Complete gear dictionaries,
task IDs, all eight cap margins and matched four-cell responses are archived
in `LINE_C_NATIVE_WITNESSES.json`.

The exact deterministic all-power-safe DP tests 724 reachable-state release
transitions and rejects662. Singleton/pair releases attain three updates
using four sources in timing_extra Orc, and two updates using three sources
in resource_haste Human; no five-step sequence exists in those declared finite
action domains. Each step separately requires new G and the original D, with
all earlier sources and configurations retained. The strongest paths are
development-selected and require one fixed-design independent confirmation.

The distinct arbitrary H-plus-one-gear branch probe finds no pair meeting the
frozen .25%-frontier/current-gain match tolerance. Its nearest Human pair has
equal future Psi=(0,0,0); the nearest Orc pair has equal Psi=(.2,0,0) at horizons
1/3/5. There is no established G-bearing matched-history separation.

## 6. A complete finite sequence class with original D and positive G

The following construction solves a restricted model class. It is an exact
abstract result, not an assertion that arbitrary native amplitude settings
implement it. Its ingredients are elementary; originality remains unestablished.

There is one combat task with fixed scale F0=1. Two mutually exclusive slots
compose additively, with two nonnegative physical damage channels: ordinary
damage and periodic damage. Utility is their sum. Behavior comprises their
damage fractions, so it has the same physical meaning as two of the original
damage-composition coordinates; other behavior coordinates are constant.
All old/new and new/new cross-pairs are legal. The only admission rule is the
single additive inequality `total damage <= 1+h`. Take parameters

```
0 < h < c < 1,  relevance e >= h,  gain g > 0,  0 < delta <= 1,
T = min(floor(h/g), floor(1/delta)).
```

The old primary has channel vector `(1-c,0)` and the old partner `(c,0)`, so
their retained anchor has utility1 and behavior(1,0). Introduce a weak partner
with vector(0,0). For t=1,...,T introduce a primary with vector

```
u_t * (1-t*delta, t*delta),    where u_t=1+t*g.
```

The first release is the weak partner plus primary1; subsequent releases add
one primary each. Admission always includes every cross-pair passing the
same fixed inequality. There are no item-ID exceptions or pair exclusions
outside that rule.

**Claim.** This sequence has T updates passing P/N/D/L/H/C and gaining g each
time, while retaining all prior sources. It uses one rule, a fixed size-one
portfolio and T+1 new items. The initial gain-bearing batch must have size2.
No positive physical interaction is present.

Proof: channels are nonnegative because t*delta<=1. Each new primary with the
old partner has utility `1+t*g+c>1+h`, hence is excluded by the fixed rule.
With the weak partner it has utility1+t*g<=1+h and is admitted. The old
anchor and old-primary/weak-partner combination remain available. Thus the
current optimum is1+t*g, previous optimum1+(t-1)*g, and G=g. Neither first
singleton gives positive admissible gain: the weak partner lowers output;
primary1 has no admissible partner until the weak one is released.

Every earlier primary s retains a source-bearing configuration of utility
1+s*g>=1. The original sources retain the old anchor of utility1. Since the
future optimum never exceeds1+h<=1+e, these permanent witnesses prove L.
The two new sources in round1 share its single gaining configuration, and
every subsequent new primary has its own current optimum, proving N. The
weak partner's optimal witness is updated by later primaries; it is never
sacrificed. The old anchor covers the one task within relevance e at every
time, proving C with K=1. H and P follow from unchanged retained configurations
and the same rule.

The admitted new profile at time t has fractions(1-t*delta,t*delta). Its
distance from an earlier profile s is `(t-s)*delta`, while both old profiles
have fractions(1,0). Thus D>=delta against the complete old/history archive,
including noncompetitive retained configurations. Finally, component channel
vectors add exactly, so every fixed four-cell physical interaction is zero.

The gain bound `T<=floor(h/g)` follows from the fixed headroom. In this
specific monotone two-channel family, behavior moves from fraction0 toward1
by at least delta per update, giving `T<=floor(1/delta)`. The construction
attains both combined bounds. The latter is not an upper bound for arbitrary
multidimensional or nonmonotone native behavior spaces.

At the main normalized values h=e=.05, g=.01 and delta=.05, choose c=.10:
five updates use six new components, and all12 final legal crosses are
considered; seven pass the rule and five are rejected. Removing the weak
partner leaves no admissible new primary and returns the optimum to1. With
the cap removed, the old partner strictly improves every primary over the
weak partner, so the weak partner loses its decision role. This intervention
changes admission while preserving physical responses; it is not a claim
that unequal-permission algorithms should be compared as if identical.

`value_theory.py` checks this class using exact rational arithmetic and full
cross-pair enumeration. Its outputs and tests are explicitly abstract and add
zero native battles. A native realization needs actual affine/control checks,
all declared tasks/policies and original behavior coordinates, followed by
independent confirmation; two designed damage channels alone do not imply
that the native engine has the required independent controls.

## 7. Current coverage need not summarize capped future completions

Here is a quantitative, conditional summary-size example, not a claim of
new qualitative dominance theory. Consider one task, cap tau, raw relevance
allowance e, old frontier F=tau-h, and old primary values
`a_i=F-w+(i-1)*gamma`, i=1,...,n, where `w=(n-1)*gamma`, gamma>0 and
`0<=w<=e-h`. The sole old partner contributes zero. All n old primaries are
retained as distinct sources. For each i consider a separate possible future
partner `b_i=tau-a_i`; future probes are alternatives, not a sequence.

The current reward coverage set is the singleton highest primary a_n=F.
For future b_i, primary a_i uniquely attains tau. Larger primaries violate the
cap; smaller ones lose at least gamma. If a computational summary must also
preserve the current optimum and approximate every future capped optimum to
strictly less than gamma, and h>=gamma, it must retain all n primaries. Without
a_i, both smaller completions and the retained old optimum are at most
tau-gamma, while larger completions are inadmissible. Therefore a singleton
current coverage set can require an extension-sufficient summary of size
`1+floor((e-h)/gamma)` for such a family, with the endpoint width chosen on
the gamma grid. This is a finite-resolution bound; the size grows only when
the approximation resolution shrinks or the available relevance reserve grows.

All original old sources remain competitive after any one probe because
`a_i>=F-w>=tau-e`, even through their old configurations. The old best
configuration is a size-one e-portfolio; the future partner is optimal and
has gain h. For a physical two-channel behavior realization one may take old
primary `(a_i-c,0)`, old partner `(c,0)` and future partner
`(0,tau-a_i+c)`, with delta<=c<=a_1. Old profiles have periodic share0 and
the completed optimum has periodic share at least c/tau; choosing
c>=tau*delta gives D against the old archive. This adds no label coordinate.

The width condition is essential to this particular permanent-old-witness
proof: it reserves e-h for old-source spread. At the exact one-task main
setting h=e, the constructed bound is only one. A nontrivial bound at those
numbers requires extra old-source witness tasks or explicit source repair;
neither can be silently assumed. This example is about the adequacy of a
computational summary while physical H remains intact. Actually deleting
historical components would violate H and is not an admissible positive method.

## 8. Native bridge and remaining contribution gap

The independent native confirmation now contains a three-update candidate in
the actual Human Warrior engine: five main-hand variants crossed with five
off-hand variants, all25 combinations evaluated on eight combat tasks and
three policies. The initial library contains all four crosses of two old
variants per slot. The frozen24 task-policy cap inequalities admit23 of the
25 final combinations. All three updates satisfy P/N/D/L/H/C/G in the
confirmation mean table, with K=1. The successive largest normalized decision
gains are1.0138168% on high_armor,1.3496852% on burst_10s, and2.1810876% on
high_armor. Every gain compares against all previously admitted gear/policy
choices; this is not a comparison against a fixed old policy.

The first pair provides a native instance of joint cap completion: deleting
either new component removes that round's entire gain. This does not extend
to every later member of a batch. Deleting OH3 in round2 or MH4 in round3
causes zero decision-frontier loss; those components satisfy the separate
relevance and behavior criteria. The later improvement uses retained partners,
so the construction also does not require every new component to improve
utility independently.

The permanent-witness lemma has a limited empirical bridge. At the final
admitted table, eight of ten source aliases have a retained witness at least
the fixed initial scale on one or more tasks, meeting the lemma's sufficient
threshold because the cap is1.05scale and relevance allowance is.05scale.
Old OH1 and new OH3 do not meet that sufficient condition. All ten sources
satisfy finite-horizon relevance through the three observed updates; perpetual
retention of all ten is not established. These are checks of confirmation
means, not population lower confidence bounds on each permanent witness.

The first gain is close to the frozen1% threshold. Its approximate simultaneous
paired-t interval is[0.44955%,1.57809%], and its simultaneous bootstrap interval
also crosses1%. Thus three empirical passes do not establish a population
three-update seven-condition certificate. The paired-t gain lower bounds for
rounds2 and3 exceed1% on at least one task, and approximate simultaneous
performance bounds remain below the frozen caps for every admitted cell.
Original seven-feature D is checked on empirical means without a sampling
confidence certificate. No class-level capacity or other race is inferred.

The independent provenance audit records264 calibration calls at256 iterations
and600 confirmation calls at1024 iterations:864 native calls and681,984 battles,
with disjoint calibration and confirmation seed ranges, complete frozen-source
and physical-receipt checks, and zero audit errors. Cached R4 screens and the
exact abstract constructions add no native calls. Details are in
`NATIVE_AUDIT.json` and `PROSPECTIVE_CONFIRMATION.json`.

The identities, completion intervals, retention witness argument, complete
sequence class and summary lower bound above are proved here. We do not claim
they are new mathematics or that their conjunction already meets the requested
contribution standard.
The native candidate demonstrates the intended joint mechanism at the level
of the frozen confirmation mean table. Threshold uncertainty, incomplete
permanent-witness coverage and the absence of a confidence certificate for D
limit the stronger interpretation. A sharper class-level condition would also
need to distinguish the contribution from known constrained composition and
safe-pruning results. Same-dimensional generic admission already matches the screened
structured feasibility in the selected comparisons; no algorithm superiority
is claimed. Neither these native results nor the abstract capacity attainment
provide an originality or unlimited-capacity claim.
