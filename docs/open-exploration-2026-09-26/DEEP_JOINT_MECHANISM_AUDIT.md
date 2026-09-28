# Development audit: joint-update mechanisms and reverse controls

This is a development-data audit, not independent confirmation. It reads all
136 native cells in each of two worlds from `deep-challenge-v1` (4,096 paired
seeds per cell). No native runs were started for this audit. The binary,
physical input and retained output remain those of the original batch. Raw
aggregate action/resource records were read after verifying their output hash.
The batch also contains two catalog worlds; this audit does not analyze them.

Analysis artifacts are under
`$WOWFS_WORK_ROOT/artifacts/open-exploration-2026-09-26/campaign-v1/analysis/deep-joint-mechanism-audit-v1/`.
The reproducible read-only analysis is
`src/wowfs/experiments/oe_joint_mechanism_audit.py`. Its four tests check paired
covariance, the direction of headroom limits, multiplicity and missing/unpaired
corners. Raw output aggregates do not retain per-seed action/resource samples,
so the action counts below have no attached confidence bounds.

## Decision and precision

Both proposed headroom settings, Mage 4.3% and Druid 5.5%, are well inside the
development windows. A 32,768-seed confirmation is adequate under the observed
pilot means and variances; this is a planning calculation, not a power guarantee.
Keep the settings fixed when applying the independently drawn held-out stat
multipliers. A changed resistance saturation boundary can legitimately destroy
the transfer result.

Let S be the old a00/x1 physical configuration, A the primary-only replacement,
X the partner-only replacement, and AX the joint replacement. The additive
forecast is A+X−S and the mixed difference is AX−A−X+S. All percentages in this
report divide by the relevant task's mean S. They are not ratios computed
separately on every random seed. A headroom window requires A, X and the
additive forecast safe in every task and AX unsafe in at least one task.

| World / pair | Mean window | Simultaneous pilot window, N=4,096 | Pilot window, N=32,768 |
|---|---:|---:|---:|
| Gnome Mage a10+x3 | [3.4584%, 5.2271%) | [3.8271%, 4.9042%) | [3.5884%, 5.1129%) |
| Night Elf Druid a16+x0 | [4.9452%, 6.0460%) | [5.1588%, 5.8627%) | [5.0206%, 5.9812%) |

These intervals use paired, two-sided Bonferroni approximate t bounds with
hypothetical auxiliary alpha=.005 and family size 5Q=10. They are selected using
development data and must not be presented as confirmation intervals. At the
more conservative alpha=.001 and family size 30, the projected 32,768-seed
windows are [3.6135%, 5.0909%) and [5.0351%, 5.9688%). The final frozen manifest
controls the actual alpha allocation and family, not this planning report.

At the proposed headrooms, the conservative projected forecast cap margins
remain positive, Mage [0.6859%, 0.9974%], Druid [0.4647%, 0.6449%]; actual joint
cap margins remain negative, Mage [−1.0625%, −0.7917%], Druid
[−0.6231%, −0.4690%]. These are conditional projections from development.

## Mage: saturation changes the direction of interaction

Both tasks last 90 seconds; only added target resistance changes from 0 to 75.
The two replaced items contribute these penetration/spell-power totals:

| Configuration | Spell penetration | Spell power |
|---|---:|---:|
| S = a00/x1 | 54.1667 | 56.6667 |
| A = a10/x1 | 48.3333 | 77.3333 |
| X = a00/x3 | 87.5000 | 30.0000 |
| AX = a10/x3 | 81.6667 | 50.6667 |

The native engine subtracts penetration from resistance and truncates at zero
(`sim/core/spell_resistances.go:147`); its binary hit probability uses the
remaining resistance coefficient (`:167`). The partner x3 removes the target's
added resistance for both old and new primary. Without x3, a10 exchanges some
penetration for spell power and still pays resistance. Consequently x3 makes
that spell-power-oriented update more valuable. This familiar saturation
mechanism is not itself an originality claim.

At resistance75 the mixed DPS difference is +1.7688% (paired seed SD 3.2295%).
S/A/X/AX Frostbolt casts per battle are 28.307/28.353/28.157/28.157 and Ice Lance
casts are 6.561/6.477/6.827/6.827. The mixed action difference is −0.04565
Frostbolts and +0.08423 Ice Lances; mixed damage is +348.55 Frostbolt damage
and +240.95 Ice Lance damage per 90-second battle. Proc/action allocation thus
also changes when resistance is active. At resistance0 all four action,
resource and OOM records coincide, and the mixed DPS residual is at machine
precision (maximum per-seed absolute residual below 4e−13 DPS). Do not turn
floating-point roundoff into a statistically significant microscopic effect.

The strongest signed reverse control is **a04+x3**. a04 replaces the primary
with 65 penetration and zero spell power. a04/x1 already removes all 75 added
resistance; x3's penetration benefit is then redundant. The mixed difference is
−5.7948% at resistance75 (paired seed SD 5.7447%), while resistance0 is again
machine-zero. A, X and AX have identical cast/resource counts to their
resistance0 counterparts. Their mixed action difference against S has +0.14966
Frostbolts and −0.26587 Ice Lances, and mixed damage is −1,132.31 Frostbolt and
−798.98 Ice Lance damage. The additive forecast incorrectly rejects this joint
update at h=4.3%: predicted increase 6.2285%, actual increase 0.4337%.

The closer same-primary control **a10+x0** keeps every quartet corner below
75 penetration. Its development mixed difference is only +0.0138% (paired seed
SD 4.4591%). This is a useful near-zero candidate, but failure to detect an
effect does not establish equivalence. The same-duration resistance0 task is
the cleaner environmental mechanism control.

## Druid: resource/damage complementarity, not the challenged Starfire guard

The two replaced items contribute these MP5/spell-power totals:

| Configuration | MP5 | Spell power |
|---|---:|---:|
| S = a00/x1 | 21.6667 | 56.6667 |
| A = a16/x1 | 50.6667 | 26.6667 |
| X = a00/x0 | 15.0000 | 70.0000 |
| AX = a16/x0 | 44.0000 | 40.0000 |

The primary exchanges 30 spell power for 29 MP5. The partner reverses that
direction, exchanging 6.6667 MP5 for 13.3333 spell power. In the 180-second
task, resource access and damage per cast therefore complement each other.
The engine implements the direct MP5 regeneration contribution linearly
(`sim/core/mana.go:143`), and Wrath separately uses mana cost and a spell-power
damage coefficient (`sim/druid/wrath.go`). The finding is not evidence that
the MP5 input itself has a nonlinear regeneration rule.

Long-task mixed DPS is +1.1008% (paired seed SD 2.6523%). S/A/X/AX spend
58.531/39.723/63.020/43.001 seconds out of mana and cast
68.465/79.728/65.698/77.989 Wraths. Mixed actual mana regeneration is only
+0.477 mana per battle, while mixed Wrath casts are +1.0271. Mixed Wrath damage
is +353.42, Moonfire −117.02 and Insect Swarm +7.99 per 180-second battle.
This is consistent with resource-dependent action allocation and damage per
cast. Aggregate records alone do not isolate every causal contribution.

Starfire is absent from all four long-task configurations. The native APL's
Starfire gate includes `currentMana >= remainingTime * 35`
(`ui/balance_druid/apls/launch.apl.json:10`). Changing this coefficient to 20 or
50 in the 512-seed challenge left the long-task samples exactly unchanged.
Thus that particular policy-guard hypothesis did not explain this interaction.
All four configurations cast Innervate once, with the same 20-second aura.

The strongest same-primary signed reverse control is **a16+x3**: x3 also
trades spell power for MP5, pushing both replacements in the same direction.
The long-task mixed difference becomes −1.4500% (paired seed SD 3.4747%).
S/A/X/AX OOM times are 58.531/39.723/49.736/31.922 seconds and Wrath casts
68.465/79.728/73.818/84.392. Mixed mana regeneration remains nearly additive
(+2.432 mana), but mixed Wrath casts are −0.68945 and mixed Wrath damage
−316.59. The control rejects a rule that more mana alone guarantees positive
joint interaction. At h=5.5% both the forecast and joint update are safe.

The 30-second task is an additional resource-unconstrained context control:
OOM time is effectively zero, and the main pair's mixed difference is only
+0.0257%. It changes action allocation as well as duration, so it does not by
itself isolate a single causal channel.

## Counterexamples, denominators and development history

All 16 nonold primaries × 3 nonold partners were checked in each world: 48
pairs per world per headroom. No pair was discarded for having the wrong sign.
At h=4.3%, Mage has five pairs whose isolated replacements are safe but joint
replacement is unsafe, including two that also fool the additive forecast.
At h=5.5%, Druid has three and one respectively. These are full finite-domain
development counts, not an estimated prevalence or multiplicity-adjusted
number of discoveries. `FULL_PAIR_CHALLENGES.json` retains all outcomes at
3%, 5%, 10% and the proposed world-specific headroom.

`256_512_4096_HISTORY.json` preserves all earlier results and challenged
policies. Main-pair mean windows were:

| World | 256 native | 512 native | 4,096 native |
|---|---:|---:|---:|
| Mage | [4.2215%, 6.1898%) | [3.2224%, 5.0661%) | [3.4584%, 5.2271%) |
| Druid | [4.3329%, 5.6739%) | [4.9942%, 6.2203%) | [4.9452%, 6.0460%) |

The Druid additive-safety margin at 5% in the 512-seed run was only 0.00584
percentage points. Even a 32,768-seed projection from the 4,096 pilot cannot
resolve additive safety at exactly 5%; choosing 5.5% before confirmation avoids
that unstable target. The Druid short-task mixed difference changed sign
across native seed blocks: +0.0242%, −0.0882%, +0.0257%. Preserve that reversal
as a near-zero outcome. Mage's 5% joint-violation margin was also close to zero
in the 512-seed run; the positive interaction remained, but the exact 5%
classification was fragile.

Both worlds are engine-supported research stat variants, not unchanged
catalog updates. Independent confirmation must report that model scope. The
potential design result is the failure of isolated/additive joint-update
screening, with a direction-changing control and bounded transfer evidence;
neither observed interaction nor a saturation law alone establishes novelty.
