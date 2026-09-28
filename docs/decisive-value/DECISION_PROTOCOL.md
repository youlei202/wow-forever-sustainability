# Decision protocol — development objectives

This protocol separates the preserved P/N/D/L/H/C metrics from actual decision
gain G. The main utility is native damage achieved before an encounter's fixed
deadline, expressed as mean DPS. Enemy armor, target count, duration and incoming
attacks are real native inputs. Damage-channel weights are not decision tasks.

The initial screen uses four predeclared R4 ecologies, both already-supported
races, all eight original R4 tasks and all three declared policies. Task mass
is1/8 each. The task is known before choosing equipment; equipment stays fixed
through combat. Both libraries may choose every declared legal configuration
and optimize over the same three policies. There is no mid-combat gear mixing,
new-only controller or removal of an inconvenient old substitute.

For each task, s(q) is the initial complete old-library optimum. Fixed capability
cap is1.05s(q); N/L tolerance is0.05s(q). New decision gain requires at least
0.01s(q) on task mass at least1/8. Continuous gains and descriptive thresholds
0.25/0.5/1/2% are saved, with1% remaining the primary threshold. The original
behavioral D threshold0.05 remains separately reported, as do source-level
deletion effects, history, legacy relevance and minimum portfolio bounds.

The complete old library is reoptimized at every comparison, under exactly
the same current admission rule and information/equipment permissions. If a
rule changes, the actually retained old state and original historical capability
are also reported. Same-dimensional generic admission contains any equally
parameterized structured budget; ties do not establish an algorithm advantage.

Three demand regimes are development comparisons: eight repeated sustained
encounters; the eight distinct actual encounters; and a uniform random draw
from those encounters revealed after equipment is chosen but before choosing
the combat policy. The last utility is an expectation over actual supported
combat tasks with one committed loadout, not arbitrary reweighting of logs or
switching gear inside a fight. Shared-resource multistage scenarios require
separate native support verification and are not inferred from task averages.

For the same decision family, V_t(q)=V_0(q) implies G=0. Consequently the R6
fixed-frontier single-task successes have zero additional value for that task's
optimization problem. Their prior D results are preserved unchanged. This
study allows improvements within a fixed cap and reports cumulative gains.

Cached16-seed tables are exploratory evidence, not population certificates.
Final task parameters, reward designs, all legal cross-combinations, thresholds
and a single independent confirmation panel must be frozen before evaluating
unseen proposed releases. New favorable development tasks cannot be assigned
retroactively to a specific reward. Candidate rejections and failed sequence
prefixes remain in the denominators. Details are in configs/decisive_value.yaml.

## Prospective two-slot construction and one final confirmation

The development family retains the same eight real tasks and three policies.
Only Human Warrior is newly executed. Native item12795 occupies the main-hand
slot and19019 the off-hand slot, with distinct research aliases denoting
alternative parameter designs. Four physical parameters are main-hand base
DPS, Talon periodic tick damage, off-hand physical damage scale and TF primary
Nature proc damage. Speeds, PPM, timing, actual gear permissions and control
policies are fixed. TF zero-damage bounce/slow paths remain active; proc amplitude
is not an AoE damage control and no native NR-debuff bug is repaired.

The two old main-hand designs are(39,10),(33,30); the two old off-hand designs
are(.75,300),(1,150). All four old crosses and all three policies define s(q),
using the independent development calibration seed720000001 and256 battles.
Five primitive anchors fit each task/policy response; two joint points and
all four old crosses are validation only. Twenty-four affine cap inequalities
in four physical coordinates are frozen and unchanged through the sequence.
Every newly legal cross is considered. Previous exclusions remain excluded by
the same rule, and all previous admissions remain available.

The model search uses32768 Sobol candidate pairs per round, three rounds,
seed8439+round, and bounds[10,80]×[0,150]×[.1,1.5]×[0,500]. These are design
bounds, not expanded statistical claims. Search guards are1.2% gain,4.5%
maximum cumulative growth and.055 behavioral distance; the actual scientific
thresholds remain1%,5% and.05. Selection minimizes the maximum cumulative
increase among guarded joint-feasible proposals, then maximizes distance.
This preserves room for later growth but leaves the first gain close to the
scientific threshold. All proposal, guard-rejection and selection counts are
reported separately. Model proposals execute zero native battles.

DESIGN.json freezes all ten component aliases,25 legal crosses and the three
admission masks before final native calls. All25×8×3 cells run once with1024
battles at seed730000001; the two ultimately rejected physical crosses are
included. No confirmation value can change a mask, cap, task, threshold or
source identity. Statistical resampling seed731000001 and2000 paired bootstrap
replicates are also frozen. Simultaneous Student-t bounds propagate every
new-minus-old action difference through full max/min optimization; bootstrap
resamples shared seed bundles and reoptimizes the complete libraries. Both are
approximate inference. Original D is an empirical feature check only.

Every prior new source enters the next L registry. Source deletion removes
all configurations containing that alias, retaining all other physical rules
and all old-policy alternatives. Both initial source identities and actual
native IDs are archived. Generic four-feature24-row rules contain the chosen
predicate exactly; no algorithmic superiority is inferred from that inclusion.
