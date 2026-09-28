# Conditional finite-table structure, with native limits

These results describe the frozen finite admission problem. They are
elementary structural certificates, not a claimed new theory of packing,
hypergraph complementarity, set cover, integer programming, or viability.
Native sample means establish a finite empirical table; they do not establish
population caps or behavior distances. The prior-work map records the relevant
established objects.

## State, permissions and obligations

H is the fixed protected set of old gear configurations, with every allowed
policy available. A release B permits candidate gear containing current-new
item IDs from B; an admission can select an arbitrary subset of those gears,
while retaining all H. Old-only alternatives cannot be selectively removed.
For task t let f_t be H's optimum, c_t the fixed cap, e_t the fixed epsilon
allowance and w_t its weight. The final frontier is the maximum response of
every admitted gear/policy. N requires every current-new item to be useful;
L requires each protected item-source to remain useful. D requires a batch
novel competitive profile, not a distinct novel profile for each item.
C requires at most K gears covering the specified task mass, with policy
optimized separately per task. Multiple sources can share one gear/task.

In R4, eight tasks have weight1/8, minimum mass .05, epsilon .05, delta .05,
coverage .95 and K=4. Thus one useful task suffices for N/L/D and all eight
tasks must be covered for C. Caps are fixed numerical1.05-times-initial
frontiers. A protected H above its cap makes admission impossible.

Under fixed physics and monotone H, the competitive history archive is
contained in all H policy profiles: every archived gear is now protected.
Consequently the stored archive is redundant for D in this experiment. The
identities of protected profiles still matter, including noncompetitive
policies. Equal present frontiers or equal archive counts do not determine
equal future admissibility. A change of physics or reference convention
requires revisiting this containment.

## Necessary qualifying supports

Write J(g) for the set of current-new items in gear g and a_gt for its best
policy response. A triple (g,p,t) can witness D only if g satisfies every
task/policy cap, its fixed-reference behavior distance is at least delta,
and `mu_gpt >= max(f_t,a_gt)-e_t`. The own-policy term is essential: a novel
but much weaker policy cannot be made competitive by admitting its gear,
because the gear's stronger alternative remains available.

For release B, collect tasks with at least one such triple and J(g) contained
in B. Their total mass must reach the minimum D mass. Minimizing |B| subject
to this relaxed support-cover condition gives a lower bound on the true
minimum release size. At R4 weights this reduces to the smallest qualifying
support. Proof: every actual D witness obeys these necessary conditions, since
the admitted frontier exceeds both the old and its own gear's frontier.
The converse fails because candidates can harm each other's competitiveness,
L may fail, and every new item has a separate N obligation.

## Witness-response closure is an exact finite representation

Take any feasible admission A and retain competitive witnesses for N, L and
D on sufficient task mass, together with the policies used by a valid
portfolio. On each task define U_t as the minimum of c_t and every chosen
witness reward plus e_t assigned to that task. A task without an assigned
witness contributes only its cap. The original frontier is at most U.
Admit H and every available **new** gear whose entire best-policy response
vector lies below U. This response-box closure includes A and hence every
chosen witness, while its frontier is still at most U. All witnesses remain
competitive, the portfolio still covers the required mass, and power is
bounded by c. Fixed old-only H and behavior reference make D unchanged.

Thus a feasible subset exists exactly when such a witness-supported response
box exists. This is a full-information representation with at most one response
threshold per task. It is not an item-price rule, not a source-only prediction
result, and not evidence that admitting every cap-safe option is feasible.
Changing old-only alternatives or the D reference during closure can invalidate
the statement. Conjunctive screening and witness certificates are established
objects; the contribution here is explicit applicability to this joint
finite predicate.

## Constructive old-only retention ceilings

Choose old source witnesses on sufficient task mass for each protected source.
Choose an old portfolio of at most K gears covering the required task mass.
Set U_t to the minimum of c_t, each chosen source witness reward plus e_t
on its assigned task, and the chosen portfolio's best reward plus e_t on
covered tasks. Valid old choices imply U_t at least f_t.

Suppose a new gear g has certified response bounds lower_gpt and upper_gpt.
Require its maximum upper bound on every task to lie under U_t. On tasks
of sufficient D mass, require a policy with certified behavior distance delta
and `lower_gpt >= max(f_t,max_p upper_gpt)-e_t`. Release exactly J(g) and admit
H plus g. Power follows because the new frontier is bounded by U_t and hence
c_t. All chosen old source and portfolio witnesses remain competitive. The
novel policy remains competitive against both H and g's other policies, so
D holds and every item of J(g) shares its N witness. H is retained.

This is a sufficient construction, not an assumed output cap. With exact
finite values, bounds collapse to equality. Population use requires justified
bounds on both old witnesses and new responses. Failing a particular box is
not infeasibility: new gears can instead supply a portfolio or restore an old
source. `r4_support.py` computes the finite construction without using new
responses to choose the old retention ceiling.

## Witness sparsification bounds minimum release size

Assume arbitrary subset admission, fixed H/reference, batch-existential D,
and every positive task weight at least the minimum usefulness mass. Let s
be the largest number of current-new item IDs in a gear. If a feasible
release exists, a feasible subrelease B' exists with

`|B'| <= s * (|L| + 1 + K)`.

Proof. From a feasible admission choose one competitive gear/policy witness
for each of the |L| protected sources and one novel competitive D witness.
Choose a portfolio with at most K gears, dropping any gear that is never
competitive on a positive-weight covered task. Retain H plus those selected
gears. Deleting other optional gears weakly lowers the frontier, preserving
P, L, D, C and all selected witnesses. Define B' as the union of current-new
IDs in the selected gears. Every such gear is competitive on some positive
task, so all its current-new items meet N on that task. Every chosen gear
is available under B'. There are at most |L|+1+K selected witness gears,
each with at most s new IDs. This proves the bound. Sources and witnesses
may overlap, reducing the support in individual cases.

The statement is about existence of a selected subrelease, not about retaining
every originally released item's N obligation. It does not guarantee that an
all-safe filter or a fixed scalar-price grammar expresses that subset. If a
single task cannot meet minimum mass, one witness per source/D no longer
suffices and this bound must be changed. It does not imply infinitely many
future releases or establish a source-only prediction rule.

## Dependence on protected commitments can be linear

An abstract complete coequipment construction shows that dependence on |L|
cannot in general be removed. Use one task, epsilon .05, cap1.05, K=1 and
one behavior coordinate. H contains an anchor of value1 and, for each old
source i=1,...,m, gear of value .96. There are m new items a_i. Include every
old-source/new-item combination: gear(i,a_j) has value1.04 when i=j and .96
otherwise. Only diagonal gear1 has novel behavior (all diagonals may instead
share that behavior); old and off-diagonal profiles are nonnovel. Each gear
contains at most one current-new item, so s=1. There is no missing-edge
assumption hiding unavailable off-diagonal combinations.

Any D witness forces frontier1.04 and competitive threshold .99. Retaining
old source i then requires its diagonal gear(i,a_i), hence all m new items.
Conversely admitting all diagonals preserves every source, satisfies N/D and
the1.05 cap, and one diagonal gear covers the only task. Minimum release size
is exactly m while task/behavior dimension, s and K remain one. This is an
abstract constraint-coupling counterexample, not an executed native family or
a proof of a new complementarity formalism. With the anchor labeled as an
additional protected source, the same example has |L|=m+1 and still gives a
linear lower bound.

The tests independently enumerate all512 candidate admission subsets of the
m=3 complete coequipment instance and verify minimum support3. Tests also
cover own-policy domination, task-weighted support unions, power-invalid H,
and reconstruction after witness sparsification. These tests count as
mathematical implementation checks only.

## Native evidence and what it does not establish

Discovery supplied minimum-size-two examples, each with complete36-gear
old/singleton/pair domains. The 512-seed check rejected resource_haste Human
under its original cap. The timing_shared Orc pair survived as an empirical
certificate, but its power margin was small. The independent256-seed causal
panel again gives H-plus-gear26007bac9b64ca50 a point-mean joint certificate:
D=.094321 on high_armor, minimum cap slack .651331DPS, K=1. Both singletons
are obstructed. Its simultaneous upper confidence bound nevertheless exceeds
the fixed cap by2.481792DPS; a population-safe theorem is not established.

Disabling Eskhandar's haste while retaining the weak physical weapon and
Thunderfury still passes empirically: D=.091779, cap slack2.867134DPS, K=1.
The high-armor paired effect interaction is +.274873DPS with family5,184
approximate95% interval[-.192666,.742412]. Thus minimum item support two is
not evidence that haste interaction is necessary. Timing_extra rage pairs
also survive with haste off. The main native explanation is conditional
coequipment and reward-channel compensation; causal effects and static
attributes must be distinguished.

The predeclared C/E screen also has one all-safe-versus-subset separation:
static_skill Human, all seven new IDs. Removing two safe competitor gears
restores new item18376's usefulness from zero to one task (mass.125).
The failing obligation is N, not old-source L. Scalar and generic4 rules with
the same information also find a feasible opening. The generic2 method's
two-second screen was unresolved, not proved infeasible. This is useful
evidence that all-safe closure is not a joint oracle, with no structured-rule
advantage established.

A second E case was detected in the independently constructed
unseen_resource_cost Human pool after its D prediction. This E follow-up is
exploratory. All-safe fails only N for18203 (task mass0). Arbitrary subset,
scalar, generic2 and generic4 all solve to the same optimum:33 total gears
admitted, exactly two safe optional gears excluded,18203 mass restored to.125,
D mass.125, K=1, and minimum empirical cap slack10.084032DPS. This strengthens
the native evidence against treating all-safe admission as a joint oracle;
it again provides no structured-rule advantage. New pool calibration was
frozen independently before its future gear table, not used to rescue the
failed original resource_haste cap.

## Selected research variant with simultaneous approximate support

A separate B-permission construction changes Thunderfury's physical weapon
damage amplitude while retaining its native proc, weapon speed and other
stats. This is a research item variant, not an unchanged live-game item. The
final independent panel fixes gear d9ddad879238ea73 plus all16 old gears,
eight original tasks and three policies. Human uses weapon damage scale.5;
Orc uses.75. These two choices were selected from earlier exploratory means
and frozen before eight new512-seed blocks, totaling4096 samples per cell.
Original baseline numerical caps, scales and source obligations are retained.

For Human, all six checks have simultaneous **approximate** support: the
minimum lower-confidence cap slack is1.677617DPS, and high_armor/native_reck
has D lower bound.063498 above delta.05 and conservative competitiveness
margin4.857498DPS. For Orc, P/N/D/H/C have approximate support, but L remains
unresolved: item17112 has point-mean useful mass.375 while its conservative
mass lower bound is0. Its D lower bound is.057361, and lower-confidence cap
slack3.833792DPS. The Orc result is not counted as a joint pass.

The procedure allocates error budget.025 to816 performance mean intervals
and.025 to16,128 block-paired behavior-coordinate differences, covering both
selected certificates. Performance uses4096 trajectory values and df4095;
behavior uses eight matched block summaries and df7. Coordinate rectangles
propagate to distance against all48 old gear/policy profiles, and conservative
performance bounds propagate to usefulness and portfolio coverage. Common
randomness across configurations is retained in behavior differences.
Bonferroni does not require cross-configuration independence, but the underlying
Student-t/block/ratio approximation is not an exact distribution-free bound.
The independent review verifies axes, nonoverlapping block seeds and family
counts. It adds a regression test where large shared block fluctuations cancel
from candidate-reference differences.

This supplies a selected approximate joint-admission certificate for a finite
research variant. It does not rescue the earlier failed native cap, prove
population-level singleton impossibility from a17-gear domain, establish a
uniform rule over untested item families, or imply indefinite continuation.

No independently confirmed pair of equal-current-metric states with unequal
future viability was established in R4. The matched new Human states both
have one-step continuation fraction .2 and three/five-step fraction0 on the
declared finite future set. The Orc states differ in their current frontiers,
so their differing continuations are not evidence for the matched-state
claim. These finite outcomes cannot support indefinite expansion.
