# Minimal native release support: selected finite witnesses

The batch screen contains ten two-item releases that are feasible although both
singletons are proved infeasible on their complete declared domains. Inspecting
their native responses shows that every novel competitive witness in these ten
pairs physically equips **both** newly released items. Each singleton has a
necessary-D failure against the protected old frontier; some also fail the
necessary usefulness condition. These are not cases where one separately
qualified D carrier admits an otherwise irrelevant passenger. This observation
does not establish a positive mixed effect interaction.

## A necessary support condition and constructive sufficiency

Keep old H, its policy capabilities, the behavior archive, task scales and caps
fixed. For each physical new loadout g, write J(g) for the set of experimental
new item IDs it uses. A potentially valid D witness (g,p,t) must satisfy:

* g is below every task cap under every allowed policy;
* its behavior is at least delta from all H-only policy profiles and history
  on task t;
* `value[g,p,t] >= max(old_frontier[t], max_policy value[g,policy,t]) - e[t]`.

The last condition checks both old competition and the candidate's own
alternative policies. If it fails, adding further gear cannot repair that
witness's competitiveness. Any successful release B must contain J(g) for at
least one such witness (and enough task mass when more than one task is
required). Therefore the minimum support size among these witnesses is a lower
bound on minimum release size. Source labels alone are not enough to compute
it; the response and behavior conditions must also be established.

Conversely, if H plus one such g passes the directly checked L and portfolio
requirements, and its novel competitive task mass reaches the threshold, then
releasing precisely J(g) is constructive: each new item shares the same useful
configuration, H is retained, power is checked globally, and the same witness
gives N to every released item and D to the release. This yields an exact
minimum when its support size meets the lower bound. Several items or old
sources may share that witness; no exclusive task allocation is assumed.

This is a conditional finite-table certificate, not a claim of new generic
hypergraph or minimal-support theory. Full joint feasibility need not be
monotone in release sets because every additional new item adds its own N
obligation. See `TARGETED_PRIOR_WORK.md`.

## Selected native pairs

All values below are exploratory means of 16 native trajectories, not confirmed
population results. Every proper nonempty release for a pair is its singleton,
and both singletons have exact finite necessary-D obstructions. The recommended
confirmation retains each complete 36-configuration old/singleton/pair domain,
all eight tasks and all three policies.

| Native context | Pair | One joint witness | D distance | N margin (DPS) | Smallest cap slack for this gear (DPS) | H plus one gear: K / worst old-source task mass |
|---|---|---|---:|---:|---:|---:|
| resource_haste, Human | Eskhandar's Right Claw 18203 + Gri'lek's Charm 19951 | `331790c18dd3a920`, native_reck, burst_10s | 0.131817 | 19.5999 | 9.8914 | 2 / 0.375 |
| timing_shared, Orc | Eskhandar's Right Claw 18203 + Thunderfury 19019 | `26007bac9b64ca50`, native_reck, high_armor | 0.093897 | 8.2819 | 5.3501 | 1 / 0.375 |
| timing_extra, Orc, alternate mechanism | Thrash Blade 17705 + Diamond Flask 20130 | `6228229891fa0ca3`, native_reck, burst_10s | 0.064677 | 8.5451 | 17.6687 | 2 / 0.750 |

The first witness has offhand Flurry Axe 871 and Cloudkeeper legs 14554 in an
already active Heroism-4 background. Its strongest distinction is gross attempted
rage inflow in the ten-second burst. The second has Maelstrom 19289 and Heroism
legs 22000, with no Heroism-4 setup; the largest difference is damage composition
against high armor. The third includes Felstriker 17075 and Maelstrom 19289.
These mechanism descriptions motivate, but do not replace, effect-off and
fresh-seed checks. In particular, the second pair could involve weapon-amplitude
compensation for a magic channel, rather than a productive haste/proc synergy.

`SELECTED_PAIR_CONSTRUCTIVE_CERTIFICATES.json` stores each complete gear,
the exact 16 protected gear IDs, and verified H-plus-one-gear metrics.
`MINIMAL_PAIR_STRUCTURAL_AUDIT.json` stores all ten minimal pairs, all their
novel witnesses, singleton failures, and admission margins. These artifacts
live under `WOWFS_WORK_ROOT/artifacts/r4-foundational-discovery/`.

## Acquisition-source limits

The frozen engine database identifies Eskhandar's Right Claw as dropping from
NPC 11982, Magmadar, in zone 2717, Molten Core. It associates Thunderfury with
quest 7787, “Rise, Thunderfury!”. Gri'lek's Charm and Diamond Flask have no source
record in this database. Thrash Blade has only `soldBy.zoneId=405`, without an
NPC ID or quest record. These are exact engine metadata, not independently
verified Forever acquisition instructions. Missing provenance is not silently
filled from a remembered Classic quest chain.

The primary L denominator remains item IDs. A mechanism-family label and an
actual acquisition source are different groupings. Incomplete acquisition
metadata prevents a claim that this screen preserves every real NPC, quest,
or raid's reward value.

## A task-weighted lower bound

Let `f[t] = max_{h in H,p} value[h,p,t]`, `e[t] = epsilon*scale[t]`,
and `a[g,t] = max_p value[g,p,t]`. Define a qualifying triple by
`g` being safe on **all** tasks and policies, fixed-reference distance at least
delta, and `value[g,p,t] >= max(f[t],a[g,t])-e[t]`. For a proposed release B,
let Q(B) be the tasks having at least one qualifying triple with
`J(g) subset B`. Then every feasible release satisfies
`sum_{t in Q(B)} weight[t] >= min_mass`.

Proof: each actual D witness belongs to an admitted gear, hence is globally
safe. Its competitive threshold uses the admitted frontier, which is at least
both f and that gear's own best policy. Its item support must have been
released. Thus every task counted by actual D is in Q(B). The stated weighted
condition follows. Consequently minimizing `|B|` subject to this relaxed
condition gives a valid lower bound. For the frozen eight equal-weight tasks
and min_mass .05, one task suffices and the bound reduces to the smallest
qualifying support. In general a union of supports may be needed. This relaxed
problem ignores mutual competition and per-item N, so passing it is not a
sufficient joint certificate. The full predicate need not be monotone in B.

The test is conditional on the complete declared response catalogue. A missing
legal gear or alternative policy can invalidate the claimed lower bound.
Empirical mean tables establish an empirical obstruction; population claims
need valid simultaneous bounds or an analytic combat model.

## An old-only retention ceiling with explicit sufficient conditions

This construction gives a sufficient **one-release** certificate before asking
the joint-admission oracle. Start from feasible H and keep its archive fixed.
Choose a portfolio Q of at most K_max old gears and a set C of tasks of total
mass at least the coverage target, with
`v_Q[t] = max_{h in Q,p} value[h,p,t] >= f[t]-e[t]` on C.
For each protected source s, choose tasks T_s of total mass at least min_mass
and old witnesses using s with rewards r_s,t at least `f[t]-e[t]`.
These choices may overlap arbitrarily: one gear can protect several sources.

Define an old-only response ceiling:

```
U[t] = min(cap[t],
           v_Q[t] + e[t]                 if t is in C,
           r_s,t + e[t]                  for every s with t in T_s).
```

An absent entry imposes no bound. Feasible witness choices imply `U[t]>=f[t]`.
Now suppose a candidate gear g uses exactly the proposed new items J(g), and
its responses have independently justified bounds
`lower[g,p,t] <= value[g,p,t] <= upper[g,p,t]`. Require:

1. `max_p upper[g,p,t] <= U[t]` for every task, not merely the D task.
2. On a task set T_D of mass at least min_mass, a policy p_t has certified
   fixed-reference distance at least delta and
   `lower[g,p_t,t] >= max(f[t],max_p upper[g,p,t])-e[t]`.

Then H plus g satisfies H/P/N/D/L/C. Power follows from
`max(f[t],a[g,t]) <= U[t] <= cap[t]`; it is not an assumed output property.
Every chosen old-source witness remains competitive because the new frontier
is bounded by its reward plus e. The same reasoning preserves the old
portfolio's coverage. The lower/upper condition makes the novel policy
competitive against both H and all policies of g. Each item of J(g) shares
that useful gear, yielding N. With exact finite responses the bounds collapse
to equality and this certificate is directly checkable. Analytic or valid
simultaneous population bounds would be needed for a stronger claim; the native
simulator means alone do not supply them.

This sufficient box can be conservative: a feasible release may use new
portfolio gears, may restore an old source through a new mixed gear, or may
protect each source on different tasks than those chosen above. Failing this
box is not an infeasibility proof. Its value is that all retention ceilings
come from the old state, leaving a concrete candidate interval to predict and
test independently.

## Why a minimal pair is not perpetual expansion

Minimum support two proves a local obstruction to singleton releases in a
specified state. It gives no lower bound on the number of future feasible
pairs and no guarantee that next-round item usefulness persists. In this
fixed-physics study, monotone H already contains every gear whose competitive
profile entered history, and D compares against **all** policies of H. The
stored competitive archive is therefore contained in the protected reference
and is redundant. History affects D through which gear profiles become
protected, including their noncompetitive policies; archive count alone does
not identify that state. This containment need not hold if physics, policies,
or the protected-domain convention change.

In a bounded seven-coordinate behavior space with fixed positive delta,
mutually separated successive protected witnesses have a finite packing
bound. History-dependent viability therefore requires its own quantified
transition problem. Existing dependency/co-installability,
hypergraph-complementarity, and viability theory already cover the general
logical forms; the present result is a native diagnostic and certificate.
