# R3 native complementarity atlas

The cached native catalogue contains many cases of **competitive participation
returning**, but only one item pair satisfies both binary reactivation and the
frozen behavioral-novelty condition: Blood Talon with Thunderfury, in the
matched Human and Orc 5% headroom contexts. This is not yet a family of
mechanistically validated sustainable complements.

The atlas reuses all 35,928 cells of R2's complete held-out catalogue table,
which includes every loadout needed for these states. No identical physical
simulation was rerun, and no new combat was launched. Earlier development
and factorial runs are not blended into these means because their gear,
interventions, seeds and selection roles differ. Their existing event/source
evidence remains available for causal follow-up.

## Denominators and result

There are 60,800 legacy/candidate/state rows across eight sequences, 20 rounds,
Human/Orc, zero/5% cumulative headroom, and two admission views. Of these,
30,720 have at least one joint loadout in the finite catalogue. Incompatible
or absent joint loadouts remain in the denominator; their performance is
missing, not zero.

In the fixed-cap empirical safe-set view:

* 162 rows have positive reactivation gain, spanning 28 distinct item pairs.
* 110 rows represent a binary transition from below 5% competitive task mass
  to at least 5%, spanning 19 item pairs.
* Of those 110, 108 start legally available but noncompetitive. Only two start
  with no power-compliant loadout at all.
* Only those last two also pass novelty at the frozen physical resolution:
  they are the same Blood Talon–Thunderfury pair in two race contexts.

Repeated appearances across sequences, caps and races are not independent
replications. The 28/19/1 distinct-pair counts expose that distinction.

The five requested ranked lists contain 10, 10, **6**, 10 and **2** selected
cases, respectively. Lists stop when qualifying cases run out; they are not
padded with renamed copies. The full data includes all candidates, not only
these selected examples. Rank is binary reactivation, gain, novelty, covered
task mass, qualifying loadout count, then earlier round; repeated
context/cap/item-pair entries are deduplicated within each list.

## Exact reactivation quantity

For a legacy item `s` and current arrival `b`, the first term is competitive
task mass of loadouts containing **both** items relative to the **after**
state's optimum. The subtracted term is the source's best competitive task
mass relative to the **before** state's optimum. Both use the same frozen
initial normalization and 5% near-optimality tolerance. Task weights remain
one quarter each. A new pair's raw DPS improvement alone is not reactivation.

The empirical safe view excludes a loadout if any of its three policies on
any of four tasks exceeds its fixed cap. The no-control view admits all
available loadouts. The atlas records both and distinguishes sources that
are cap-blocked, legally noncompetitive, or already competitive. It also
records pair-level cap slack and current source-rule rejection counts.

Behavior uses the same seven R2 physical features: action-family damage
shares, gross attempted rage inflow per second divided by 20, and overcap
waste fraction. Inflow includes refunds and is not net productive generation.
Novelty checks every listed old-only policy on the same task and the complete
registered historical behavior archive at infinity distance 0.05. This does
not exclude randomized strategy mixtures or unsearched loadouts.

## Canonical native witness

The state is `expanded_interleaved_0`, round 20. Blood Talon `12795` arrives
in the main hand; Thunderfury `19019` has occupied the off-hand candidate
library since round 5. At the 5% cap, Thunderfury has **zero allowed loadouts
before** this arrival and **four competitive joint loadouts after** it.

| Context | Legacy task mass before → pair after | Novel task mass | Maximum old-only distance | New total peak growth |
|---|---:|---:|---:|---:|
| Human | 0 → 0.75 | 0.50 | 0.07808 | 4.8911% |
| Orc | 0 → 0.50 | 0.50 | 0.08393 | 4.2191% |

All four joint loadouts are blocked by the old 8-row semantic rule. That is
a specific failure of its frozen zero periodic-damage threshold, not proof
that every type-level rule must fail.

For Human, loadout `5ae0e1e5d00fbdb1` with `native_reck` produces mean DPS
`[294.502820, 406.169071, 424.203083, 188.709061]` in the fixed task order
sustained, short, four-target, high-armor. Its trinkets are Hand of Justice
`11815` and Blackhand's Breadth `13965`. For Orc, the strongest high-armor
pair witness is `a8e48c846cd427fb`, the same equipment except Diamond Flask
`20130` replaces Blackhand's Breadth, with mean DPS
`[289.919961, 436.313724, 432.759312, 185.733731]` under `native_reck`.
Full 17-slot equipment and cached native requests are in the witness JSONL.

This re-entry **uses remaining headroom**. Human high-armor best performance
rises from 179.909482 to 188.709061 DPS; Orc rises from 182.968166 to
185.733731. It does not occur at zero headroom in this catalogue. Thus the
existing witness supports cap-compliant new participation, not literal zero
capability growth. It is compatible with compensatory weakening of the main
hand making a powerful off-hand legal. A positive proc interaction has not
been established by this filtering result.

## Other native cases to investigate

Deathbringer `17068` restores competitive participation for several legally
available but noncompetitive off-hands, including Joonho's Mercy `17054`,
Shadowblade `2163`, Bloodletter Scalpel `9511`, Searing Needle `12531`, and
Gut Ripper `2164`. Some gains reach all four tasks while the fixed initial
power envelope is unchanged. These cases all fail the frozen novelty test;
they can reflect a stronger main hand carrying an interchangeable off-hand.
Competitive membership does not establish that the legacy source is
indispensable or contributes a distinctive mechanic.

Teebu's Blazing Longsword `1728` restores Hameya's Slayer `15814` on one task
in both races and both cap panels, but again without novel behavior. The
8-row source rule blocks those pair choices. By contrast, Thunderfury's
arrival improves the competitive role of Ironfoe, and in Orc also Empyrean,
in the unrestricted view; their qualifying joint loadouts violate the cap.
The atlas contains six such power-failing state rows, not ten independent
causal examples.

The safe-set view uses full per-loadout responses. Its unchanged numeric cap
does not establish fixed rule complexity: the information needed to evaluate
new combinations still grows. No learned type rule, causal synergy, or
item-count-independent control guarantee is claimed by the atlas.

## Files and reproduction

```bash
source scripts/env.sh
python -m wowfs.experiments.r3_atlas
```

Outputs are under `WOWFS_WORK_ROOT/artifacts/r3-gold/`:
`COMPLEMENTARITY_ATLAS.csv`, `REACTIVATION_WITNESSES.jsonl`,
`COMPLEMENTARITY_SUMMARY.md`, and `ATLAS_AUDIT.json`.
Each selected example preserves taskwise raw values, exact equipment, policy,
native input and compressed-output paths, output hashes, effect definitions,
aggregate event/resource/aura records, cap state, and semantic thresholds.
The audit records input and analysis hashes and the zero-new-battle count.
