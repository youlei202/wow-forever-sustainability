# Native control feasibility and Ludus comparison

Source-only audit, 2026-09-25. The complete decisive-value brief was read.
No simulation was run, no native source was changed, and R1–R6 artifacts were
left unchanged. A supported mechanism is not evidence that a candidate has
positive decision gain.

## Supported scope

**A genuine shared-resource, two-stage task is available without new engine
physics:** normal combat followed by Execute availability, with one persistent
rage/cooldown state and fixed equipment. Full-encounter damage at a fixed
deadline, or single-target fixed-health completion time, is a physical objective.
General target waves and arbitrary encounter phase schedules are not exposed
by the frozen native request schema.

The engine checkout inspected is
`/work/Users/leiyo/wow-forever-sustainability-work/external/mythicsim-forever-engine-r3-variants`.
All source paths below are relative to this directory. Its R3 runner accepts
the native `RaidSimRequest` through `protojson.Unmarshal` and calls
`core.RunRaidSim` (`cmd/wowfs-r3/main.go:101`); these request fields are not
merely UI controls unavailable to the runner.

| Capability | Actual support and scope | Source |
|---|---|---|
| Normal → Execute | Duration fights expose configured 35/25/20% phase fractions. Health fights use aggregate damage thresholds. Transitions change phase flags without resetting combat resources. | `proto/common.proto:799`; `sim/core/sim.go:547`, `:568` |
| Shared rage and action change | Warrior Execute is legal only in the 20% phase, spends the remaining rage after its base cost, and deals additional damage from that rage. Rage, cooldowns, auras, and ongoing effects carry through the phase change. | `sim/warrior/execute.go:9`; `sim/core/rage.go:52`; `sim/core/sim.go:547` |
| Adaptive APL | Conditions can use elapsed/remaining time, execute phase, rage, health, spell readiness, auras, and autoattack state. Actions include casts, waits, schedules, sequences, and target change. This supports a finite, predeclared family of reactive policies. | `proto/apl.proto:113`; `sim/core/apl_values_encounter.go`; `apl_values_resources.go`; `apl_actions_timing.go`; `apl_actions_misc.go:11` |
| Target change | The APL can change `CurrentTarget` to another existing target. It does not spawn, despawn, kill, or make targets unavailable. | `sim/core/apl_actions_misc.go:16` |
| Target waves / phases | Generic `Encounter` declares a fixed target array. No spawn/despawn times or arbitrary armor/resistance timeline are provided. All targets are constructed before combat. | `proto/common.proto:799`; `sim/core/target.go:32`; `sim/core/environment.go:73` |
| Incoming attacks | A target assigned to a valid raid tank can autoattack using configured speed, damage, school, dual wield, and parry haste. Taken hits feed native rage and defensive effects. | `sim/core/environment.go:105`; `sim/core/target_ai.go:16`; `sim/core/rage.go:126` |
| Equipment changes | One alternate set supports only main hand, off hand, and ranged. No armor or trinket swap fields exist. Stats/weapons change dynamically; melee weapon changes reset swings, and a ready GCD is consumed for 1.5 seconds. | `proto/common.proto:1002`; `sim/core/item_swaps.go:29`, `:141`; `sim/core/apl_actions_misc.go:218` |

The preexisting encounter registrations do not supply a general multi-stage
boss workaround. `sim/encounters/register_all.go` registers level-60 defaults,
Vaelastrasz, and Onyxia; Naxxramas registration is commented out. Onyxia's
source explicitly omits its air phase (`onyxias_lair.go:31`). Vaelastrasz
implements Essence of the Red, while several other mechanics remain commented
out (`blackwing_lair.go`). Presence of other AI source files is not evidence
that their encounters are registered or validated in Forever.

## Objectives and controls that can be defended

For a first shared-resource comparison, freeze duration, phase fractions,
target attributes, starting rage, equipment permissions, and policy family
before evaluating candidate gear. Compare normal-only demand with a
normal→Execute demand using actual total damage/DPS. Saving rage for the
transition and selecting Execute versus other attacks are real decisions;
adding arbitrary channel weights is unnecessary. Whether these decisions
create a structural separation is an empirical question, not a source fact.

Single-target `use_health=true` gives another real objective: minimize expected
completion time, equivalently use reward `-T`. The native result reports
`avg_iteration_duration` (`proto/api.proto:391`; `sim/core/sim.go:348`). Do not
replace `E[T]` with `1/E[DPS]` or assume multi-target death behavior: the engine
sums all declared target health into one completion threshold and increments
one aggregate damage counter (`sim/core/target.go:44`;
`sim/core/spell_result.go:451`). This is not a system of independently killed
adds with subsequent spawn events.

The old library must receive the same policy family, information, and equipment
permissions as the enlarged library and be reoptimized within that domain.
An optimum over three declared APLs is an optimum over that finite controller
set, not over every conceivable player policy. A scheduled target switch is
a controller choice among currently available targets; forcing it only on the
old side, or treating it as enemy availability, changes the decision problem.
Likewise, APL helper actions that directly activate auras or add resources
must not become unrestricted optimization actions merely because the parser
accepts them.

Fixed equipment is a supported common permission for both libraries. It is
also the cleanest scope for current proc-weapon research variants because
the existing swap subsystem does **not** generally reinitialize item effects.
`sim/core/character.go:382` applies native item effects for initially equipped
gear; its alternate-item loop at line 397 registers enchant effects, not
alternate item effects. `item_swaps.go` changes stats/weapons and invokes
explicitly registered callbacks. Neither general set-bonus recomputation nor
universal item-proc activation/deactivation occurs there. Thus the existence
of an item-swap APL action does not certify correct swapping of arbitrary
proc weapons. A swap-enabled study needs effect-specific inspection and
validation; it cannot use a free mixture of old weapon responses.

## Incoming damage and survival limitations

Incoming attacks are executable physics, but the frozen Forever rules carry
explicit calibration assumptions. White-hit rage depends on base weapon speed,
not dealt damage; incoming-hit rage uses pre-armor damage multiplied by 10 and
divided by maximum health. The upstream comments identify the incoming factor
and base-versus-hasted-speed choice as assumptions needing further in-game
testing (`sim/core/ruleset.go:93`). This should be reported as native simulator
behavior, not newly established game truth.

The death implementation also matters for the utility. With a tank assignment
and non-nil healing model, `sim/core/health.go:91` tracks incoming health loss
and records the first zero-health event in `Metrics.Died`. It does not stop
the character's actions or terminate the encounter. The other uses of `Died`
in core aggregate the death metric (`metrics_aggregator.go:522`). Consequently:

* A first-death probability under declared incoming attacks/healing can be a
  native measured constraint, with this simulation semantics stated.
* Full-encounter DPS is not automatically damage delivered before death.
* A kill-before-death reward or surviving multi-wave encounter cannot be
  claimed from ordinary DPS plus a death flag without validating the required
  event ordering and termination semantics.

No source-only finding establishes decision gain, cap compliance, retained old
uses, or a useful new release. Those remain comparisons over the full frozen
equipment/controller domain.

## Closest-paper boundary: Ludus

Ludus combines simulation and genetic search to balance card parameters using
per-card win-rate metrics. It enumerates ordered three-card lineups with
duplicates and approximates tournaments through random groups. Crucially,
§4.5 optimizes five new cards alongside five fixed old cards; expansion with
old parameters frozen is already studied. §4.2 also demonstrates that uniform
win rates can collapse into universally tied games. See
[the primary paper, §§3–4](https://ojs.aaai.org/index.php/AAAI/article/view/21550/21299).

The proposed distinction is therefore not automated balancing, complete
combinations, or retaining old parameters. Our target adds a fixed capability
cap, explicit competitive-use obligations for old sources, decision gain
against the reoptimized complete old library, and sequential capacity/complexity
claims. The examined paper does not impose this conjunction. Its extensible
metrics could incorporate additional goals, so this is a problem/guarantee
distinction, not proof of algorithmic novelty. The decisive result must establish
those guarantees rather than merely demonstrate another balanced expansion.
[Publication record and DOI](https://ojs.aaai.org/index.php/AAAI/article/view/21550).

## Source receipts

| File | SHA-256 |
|---|---|
| `sim/core/target.go` | `07c59f09143897900d9ff2243774551552221834f5990318b94b1df5b26f80db` |
| `sim/core/sim.go` | `7593b011d0b9059c4db051076ecca40c8971c63a549483bbc45d5fd9c177e892` |
| `sim/core/item_swaps.go` | `b1c21c0a8833e0616e2dce58518ac3fdddbe6e5712418ffe2d00b7f6f8f284ed` |
| `sim/core/health.go` | `b9e9342b14e3c9483e8886c34808be33630ef2e55276b751e8f4223d5256b423` |
| `sim/warrior/execute.go` | `1967bc091628875712738d762d928f9c4eae1b9d7a1f9d491f42c00f02b2d039` |
