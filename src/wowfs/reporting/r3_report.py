"""Assemble R3 evidence without turning finite diagnostics into universal claims."""
from pathlib import Path
import csv
import json
import shutil
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import yaml
from wowfs.paths import SOURCE_ROOT,setup_paths,atomic_json

def read_csv(p):return list(csv.DictReader(p.open()))

def figures(out):
    rr=read_csv(out/'SEQUENTIAL_WAVE_RESULTS.csv');seq=read_csv(out/'SEQUENTIAL_EXPANSION_RESULTS.csv')
    methods=[('random_horizontal','Random'),('immediate_utility','Immediate utility'),
             ('novelty_first','Novelty first'),('legacy_first','Legacy first'),
             ('complement_constrained','Complement = generic = scalar')]
    fig,axes=plt.subplots(2,2,figsize=(10,6.8),layout='constrained')
    specs=[('distinct_new_choices','New separated task profiles'),('power_ratio_to_fixed_cap','Worst-condition peak / fixed cap'),
           ('reactivated_legacy_sources','Previously blocked sources reactivated'),('rule_rows','Dense rule rows per race')]
    colors=['#7b818b','#ba6530','#765ca8','#599777','#126d90']
    for ax,(metric,label) in zip(axes.flat,specs):
        for (method,name),color in zip(methods,colors):
            values=np.array([[float(r[metric]) for r in rr if r['method']==method and int(r['wave'])==w] for w in range(1,21)])
            aggregate=values.max(axis=1) if metric=='power_ratio_to_fixed_cap' else values.mean(axis=1)
            ax.plot(range(1,21),aggregate,label=name,color=color,lw=2 if method=='complement_constrained' else 1.25,
                    linestyle='-' if method=='complement_constrained' else '--',alpha=.95)
        if metric=='power_ratio_to_fixed_cap':ax.axhline(1,color='#333333',lw=.8,ls=':')
        if metric=='rule_rows':
            ax.plot(range(1,21),np.ones(20),color='#333333',ls=':',label='Scalar: 1 row, changing item coefficients')
            ax.set_ylim(-5,155)
        ax.set_xlabel('Update wave');ax.set_ylabel(label);ax.set_xticks([1,5,10,15,20]);ax.grid(alpha=.15)
    handles,labels=axes[1,1].get_legend_handles_labels()
    fig.legend(handles,labels,loc='outside lower center',ncol=2,fontsize=8)
    fig.suptitle('Two candidate pools × two races: means; power shows worst condition\nRepeated useful items do not imply repeated behavioral novelty',fontsize=12)
    for ext in ('pdf','png'):fig.savefig(out/f'figures/sequential_trajectories.{ext}',dpi=190)
    plt.close(fig)

def main():
    root=setup_paths();out=root/'artifacts/r3-gold';figures(out)
    for ext in ('pdf','png'):
        shutil.copy2(out/f'RULE_COMPLEXITY_SCALING.{ext}',out/f'figures/rule_complexity_scaling.{ext}')
    seq=read_csv(out/'SEQUENTIAL_EXPANSION_RESULTS.csv');atlas=json.loads((out/'ATLAS_AUDIT.json').read_text())
    transfer=json.loads((out/'AFFINE_TRANSFER.json').read_text());comparison=json.loads((out/'AFFINE_COMPARISONS.json').read_text())
    audit=json.loads((out/'INDEPENDENT_NATIVE_AUDIT.json').read_text())
    if not audit['snapshot_complete_and_quiescent']:raise ValueError('Physical audit incomplete')
    for filename in ['THEORY.md','MECHANISMS.md','NATIVE_VARIANTS.md','AFFINE_FINDINGS.md','PHASE_FINDINGS.md','CONFIRMATION_FINDINGS.md','ATLAS.md']:
        shutil.copy2(SOURCE_ROOT/'docs/r3'/filename,out/filename)
    types=yaml.safe_load((SOURCE_ROOT/'configs/r3_types.yaml').read_text())
    types['artifact_note']='Source vocabulary copied for review; original exploration status retained. Actual immutable calibration/transfer design and archived source hashes are in FROZEN_AFFINE_TRANSFER_DESIGN.json and run protocols.'
    (out/'INTERACTION_TYPES.yaml').write_text(yaml.safe_dump(types,sort_keys=False,allow_unicode=True))
    selected=[r for r in seq if r['method']=='complement_constrained']
    review=f'''# R3 — Rule reuse is supported; sustained novelty is not yet established

1. **Is Blood Talon–Thunderfury an isolated case or a family?** In the existing item-ID atlas, it remains the only pair that meets the original behavioral-difference threshold. Changing weapon parameters within the actual engine expands it into a reproducible compensation family. Under the 5% cap, four interior parameter points × Human/Orc give 8 conditions, each with 4 Thunderfury loadouts supported by power and competitiveness intervals. Behavioral difference D remains an empirical mean. The original canonical Human loadout itself has not been confirmed safe.
2. **What mechanism predicts complementarity?** Weakening or changing main-hand physical damage and speed leaves room for a previously over-cap off-hand magic-damage channel. All eight primary effect-toggle contrasts fall within the predeclared interaction tolerance of ±1% of initial DPS; no large positive effect amplification was found.
3. **Does complexity grow with the number of items or types?** A simple type count is not the right variable. The reusable object is a fixed event-control mechanism and its power envelope. The current rule originally had 288 conditions; removing numerical redundancy leaves 12 power constraints, 24 fixed-configuration branches, and 4 parameter-domain boundaries, with a compact JSON size of 3,408 bytes. With this configuration fixed, increasing new parameterized items from 4→32 does not enlarge the rule. Holding 8 items fixed and increasing speed mechanisms from 1→3 increases compressed constraints from 4→12. This curve measures control mechanisms, not new semantic types.
4. **Can the frozen rule transfer?** For 32 unseen parameterized items coupled by the same random seeds, the maximum per-seed error across 3,072 native results is 3.41e−13 DPS. The typed rule, same-feature generic method, and finite safe-set reference agree exactly, admitting 197/256 loadouts. Coefficients fail when speed, proc rate, or rage mechanisms change; unknown configurations should be rejected. Independent-seed means show substantial errors, so algebraic exactness must not be treated as a statistical safety certificate.
5. **Does complementary selection sustain expansion over 20 waves?** Evidence is insufficient. Two candidate pools × two races give four conditions with successful prefixes of {[int(r['S20']) for r in selected]}; 0/4 pass all 20 waves. Only 4/80 waves are accepted and 76/80 are rejected, without replacement draws. Complementary selection, generic optimization with the same information, and repricable scalar methods have identical trajectories. New items can remain useful, but new behavior is soon exhausted, and Human is additionally constrained by legacy-source competitiveness.
6. **What is the strongest theoretical result?** With event trajectories invariant to reward amplitude, affine rewards, a finite context envelope, and strict safety/competitiveness/behavior margins, a fixed-complexity rule permits a nonempty complementary parameter neighborhood. Capacity for positively separated behaviors is finite; low rank or finitely many type names alone does not control the number of constraints. This reward decomposition agrees with existing successor-feature ideas and is not presented as an original theorem.
7. **Is this enough to support the central AISTATS 2027 claim?** **Not yet.** There is solid evidence for a native mechanism case, transfer limits, and failure of sustained novelty. Sustained new value across mechanism families and multiple rounds remains unproven, and there is no evidence of an advantage over generic or scalar optimization with the same information.

This round adds **{audit['total_new_r3_native_calls']:,} native calls / {audit['total_new_r3_physical_battles']:,} battles**. The independent audit checks inputs, binaries, compressed raw outputs, sample counts, and run receipts, with 0 errors. The atlas reuses 35,928 physical cells from R2, contributing 0 new battles to this round. Actual coverage is limited to Human/Orc Warrior.

Start with `RESULTS.md`, `CONFIRMATION_FINDINGS.md`, and `NEXT_RESEARCH.md`. Main tables, figures, frozen designs, raw evidence excerpts, and complete source snapshots are packaged together. Every "safe" judgment is limited to the listed tasks, loadouts, and ability policies; mean power, changes in behavioral proportions, and changes in actual action policies are reported separately.
'''
    (out/'REVIEW.md').write_text(review)
    table='| Policy | Mean S20 | Joint passing waves /80 | Useful waves /80 | Rejected /80 | Mean distinct task profiles | Max growth |\n|---|---:|---:|---:|---:|---:|---:|\n'
    for method in dict.fromkeys(r['method'] for r in seq):
        rows=[r for r in seq if r['method']==method]
        table+=f"| {method} | {np.mean([int(r['S20']) for r in rows]):.2f} | {sum(int(r['joint_passing_waves']) for r in rows)} | {sum(round(float(r['useful_fraction'])*20) for r in rows)} | {sum(int(r['rejected_waves']) for r in rows)} | {np.mean([int(r['distinct_new_choices']) for r in rows]):.2f} | {max(float(r['max_power_growth']) for r in rows):.3%} |\n"
    results=f'''# R3 results and evidential limits

## Native complementarity, with exact denominators

The atlas contains60,800 pair/state rows,30,720 with a nonempty co-equipment domain. Positive safe reactivation gain occurs in162rows spanning28distinct item pairs. Binary reactivation occurs in110rows spanning19pairs:108legal-but-noncompetitive returns and2previously-cap-blocked returns. Only the two race instances of Blood Talon→Thunderfury also pass the frozen behavioral novelty criterion. Other reactivation pairs, including Deathbringer with weak legacy weapons and Teebu with Hameya's Slayer, do not acquire this D property. There are only6qualifying apparent-but-power-unsafe rows; the requested top10 category is not padded. These are overlapping rows, not independent discoveries.

The63-point DPS×speed grid executes24,192cells×32seeds. With5% fixed headroom, safe-set-filtered TF reactivation+N+D occurs at32/63Human and38/63Orc points, one connected observed-grid component each. Entire new batches are belowcap at only18/63 and22/63; the response-based reference is explicit and not a learned transferable rule. At0% the analogous region counts are4/63 and6/63. Connected grid cells do not prove all intervening parameters safe.

The ten once-selected fresh points execute3,840cells×1,024seeds. All8primary interior conditions retain4TFloadouts with approximate simultaneous fixed-numeric-cap power and competitive-use support. D is empirical. At0% the24DPS/1.0s control retains3Human and4Orc supported loadouts, with unchanged selected empirical envelope; population-anchor uncertainty does not certify those zero-headroom cases. The original Human canonical point remains unresolved after1,024seeds, and its separate128seed replication exceeds the fixed cap. Full detail is in CONFIRMATION_FINDINGS.md.

## What causes the complement

576factorial cells×128seeds compare native Blood Talon, Deathbringer and Thrash Blade effects with Thunderfury across two gear strata. The eight declared primary Blood Talon contrasts range from−0.4492 to+0.2083DPS; every adjusted interval is inside the predeclared ±1%-of-initial-DPS margin. A large positive effect interaction is unnecessary for re-entry. There is no native bleed→Thunderfury trigger chain. The actual pinned implementation reuses a Thunderfury aura label, making its intended Nature-resistance callback ineffective; a two-invocation positive-resistance intervention confirms this no-op. We retain and disclose that engine behavior.

## Frozen transfer and rule complexity

The reward coordinates are weapon base DPS and periodic tick damage. Registration, speed, proc probability, tick timing, equipment context and APL are fixed per control kernel. Three anchors identify each sampled affine function. Calibration uses864cells×128seeds for288task/policy/context rows. Thirty-two numerical items are frozen before heldout results; these are research variants, not32new official IDs.

Same-control predictions match3,072cells to3.41e−13DPS per seed. Typed and same-feature generic classifiers admit197/256loadouts, precisely matching the paired-seed finite safe reference. Frozen unknown-item whitelists reject all; an empty blacklist admits59unsafe loadouts; a refitted per-item lookup exactly matches but uses all current responses. A conservative common scalar majorant admits8/256with no observed violation. This majorant is not an optimized scalar impossibility result; the stronger adaptive scalar method ties the complement method in the sequential study.

The complete compact rule is3,408bytes:12retained numerical cap facets,24configuration selectors and4shared rectangle bounds. Counting only12while hiding selectors would understate complexity. The dense unpruned form has288rows/864coefficients. At fixed palette, rulebytes are constant as the content catalogue grows4→32items; content descriptors still grow. At matched n=8,1/2/3speed kernels require4/8/12retained facets and1,429/2,426/3,408bytes. These are implemented representation costs, not proven minimal description lengths. Every matched generic method may use the same compression.

Forced out-of-domain transfer has maximum mean errors19.696DPS for speed/PPM shifts and5.263DPS for a heldout rage-trinket context. The frozen deployable rule rejects those unsupported kernels. The separate256cell independent-seed panel has maximum mean error11.957DPS; approximate pointwise intervals include zero for160/256cells, with failures clustered in3/8shared contexts. This is not an independent256trial coverage estimate or validated simultaneous certificate.

TYPE_TRANSFER_RESULTS.csv retains P/N/D/L/H/C. In the complete heldout pool, typed/generic rules make17/32Human and19/32Orc items competitive and D-distinct against the old catalogue. These are not17/19mutually distinct new behaviors. Human retains23/24previously competitive variable-slot sources and needsK=2; Orc retains21/21andK=1. Thus even a perfect safe-set predictor does not guarantee global legacy retention.

## Prospective pools, exploratory policy replay

Two source-seeded20wave pools each contain6native candidates/wave:240items total, speed1.0/1.3/1.9, baseDPS26–52, DOT0–30. Four gear profiles,4tasks,3policies and2races yield23,040new cells×128independent seeds. Amplitude, periodic contribution, speed specialization and vertical pressure vary within the calibrated family. Resource-bearing new mechanisms are not smuggled into the supported family. This is a narrow pilot, not the broad multi-family expansion needed for the central claim.

All policies receive the same current six response tables and calibration. No future response is used for a current choice. Generic constrained selection contains the same rule/objective, so its tie is deliberate and honest. Compatible scalar repricing uses current-only LPs while protecting prior legal choices. Baseline immediate/novelty/legacy selection is enforced under the same observed current power cap; a first implementation used only the predicted cap for these baselines. That was corrected after outcomes to honor the brief and equalize information; the earlier analysis is retained in analysis_versions. Hence this policy comparison is an exploratory replay, not a claim of preregistered algorithmic superiority. Physics, pools, distances and thresholds are unchanged.

{table}
All28method×pool×race trajectories complete20attempted waves; all havePass20=false. Complement/generic/scalar have identical trajectories, zero observed power violations,76/80rejected waves and4successful admissions total. Successful prefix stops at the first failure even if a later wave succeeds. Random choices can be useless or violate P. Baselines optimized under the cap can keep issuing useful labels while D saturates; Human can lose Darkmoon Card: Maelstrom's former competitive use. Historical loadout legality is preserved. Cumulative profile counts use frozen task-conditioned L-infinity0.05 separation; they are greedy packing lower bounds, not certificates against randomized policy mixtures.

## Measurement and provenance

{audit['total_new_r3_native_calls']:,} new native calls and{audit['total_new_r3_physical_battles']:,} new battles are physically verified. Engine commit17d75ccc8c67d027ae0088243ea3ee806d406847; R3variant binary SHA25659f42b32e2c834321773188db482419238ae57556942f6f1825258722fc0aafe. Cache keys hash the executable plus whole request including research variants. Runs archive sources, inputs, seeds, commands and hashes. No process failure, missing cell or unexecuted class is coded as zero. No public submission or push was made.

The finite APL and equipment catalogue exclude arbitrary policies, defenses, random mixtures and live-server validity. Aggregate damage shares may change even when casts, hit/crit counts, rage and first-seed event schedules remain unchanged. Therefore D is a frozen operational behavior metric, not proof of a new player decision or rotation. More classes were not run because the sequential structural target failed in the supported Warrior domain.
'''
    (out/'RESULTS.md').write_text(results)
    next_research='''# Next research decision

The current AISTATS central claim is not established. Preserve the confirmed complement family, but stop increasing the number of amplitude variants: it primarily relabels a small behavior set.

1. Define a behavior representation that distinguishes decision policies/action schedules from reward shares. Freeze it as a new study; retain the R2/R3 metric and results for comparison instead of silently replacing them.
2. Find several mechanisms that alter useful event/control structure under an unchanged cap and preserve every registered legacy source. Require at least two qualitatively different native families before broadening classes. Current source vocabulary is a useful audit checklist, not a guaranteed transfer class.
3. Target the joint feasible intersection: cap upper bounds, robust competitive lower witnesses for new and all old sources, and distance from the complete evolving archive. The old-source loss and finite novelty packing are active constraints; solving only P cannot solve them.
4. Separate structural interpolation from calibration uncertainty. Obtain independent seed blocks for retained facet coefficients, validate simultaneous bounds and test previously unseen kernels. The current128seed fit is not a deployable statistical cap guarantee.
5. For a future sequential confirmatory study, freeze candidate generator, exact under-cap policy tie breaks, exclusions, archive updates, scalar permissions and all source denominators before new outcomes. Use more independent candidate pools and novel control families. Retain all rejection waves.
6. Only after this succeeds, transfer to an actually supported caster and pet/hybrid system. Do not invent executed coverage from class availability.

Current viable manuscript: a careful native case study of safe reward-kernel reuse and its separation from sustained novelty. A new general theorem or algorithmic superiority claim needs additional evidence. The standard fixed-dynamics linear-reward identity and finite packing argument are not original contributions.
'''
    (out/'NEXT_RESEARCH.md').write_text(next_research)
    (out/'TYPE_DISCOVERY.md').write_text('''# Discovered unit of reuse

The useful unit is a source-audited control kernel plus reward coordinates, not an item label. The compact vocabulary separates weapon reward, triggered damage, periodic damage, target mitigation, extra attacks, active stat windows and active resource. Only the reward-amplitude subfamily is calibrated for transfer here. Timing/probability/resource changes modify the event process even inside the same verbal type.

Blood Talon and Thunderfury exhibit compensation under a fixed cap, not demonstrated positive proc amplification. Fixed-control amplitude variants leave observed action frequencies and resource traces unchanged; damage composition changes. More distinct item IDs therefore need not add new playstyles. Rank2reward coordinates do not bound the number of envelope facets for arbitrary kernels.

The immutable transfer design freezes anchors, parameter items, seen/shifted panels and the generic comparator before their outcomes. Source config INTERACTION_TYPES.yaml remains explicitly exploratory; the actual tested support is narrower and encoded in AFFINE_ADMISSION_RULE_NUMERIC_PRUNING.json. Gri'lek was withheld from this calibration, but was already present in R2 and the R3phase grid; it is not globally unseen.
''')
    (out/'WITNESS_CAUSAL_DECOMPOSITION.md').write_text('''# Causal decomposition

See CAUSAL_FACTORIALS.json and INTERACTION_SIGNATURES.csv for all144paired groups, including8primary comparisons. All576physical cells ran128fresh common seeds. Primary intervals use paired seed contrasts with an eight-comparison Student-t correction. Their inclusion in the frozen ±1%initial-DPS equivalence region rules out effects larger than that chosen practical margin under the approximate interval model; it does not prove universal zero interaction.

Removing an effect registration changes callback/RNG scheduling; setting its damage amplitude to zero preserves registration. These interventions have different meanings and are not pooled. The affine probe uses the latter intervention. The broad phase changes weapon speed while independently holding specified base DPS, preserving native proc implementation; those points are native research variants, not official new items.

The original Human exact loadout is near the cap and not independently certified. The confirmed interior family provides the stronger witness. Thunderfury's intended resistance reduction is a pinned-engine no-op, confirmed by native toggles; no claim relies on its intended tooltip behavior.
''')
    (out/'RELATED_WORK.md').write_text('''# Primary-source positioning

[Dayan (1993), Improving Generalization for Temporal Difference Learning](https://www.gatsby.ucl.ac.uk/~dayan/papers/d93b.pdf) develops successor representations. [Barreto et al. (2017), Successor Features for Transfer in Reinforcement Learning, section3](https://proceedings.neurips.cc/paper_files/paper/2017/file/350db081a661525235354dd3e19b8c05-Paper.pdf) separates fixed dynamics from linear rewards. Both primary papers were opened and checked during R3. The affine reward identity here is a native specialization of known structure, not a new identity.

The possible contribution is locating source-audited useful complement regions, distinguishing kernel reuse from verbal type reuse, and showing why transferable power rules still fail sustainable novelty/legacy goals. Finite strict-inequality neighborhoods, elementary exception-list counting and bounded-space packing are standard arguments. The native finite case study does not itself establish broad originality or AISTATS suitability.
''')
    for filename in ['REVIEW.md','RESULTS.md','NEXT_RESEARCH.md','TYPE_DISCOVERY.md','WITNESS_CAUSAL_DECOMPOSITION.md','RELATED_WORK.md']:
        shutil.copy2(out/filename,SOURCE_ROOT/'docs/r3'/filename)
    atomic_json(out/'COVERAGE.json',{'executed':['Warrior/RaceHuman','Warrior/RaceOrc'],
        'additional_classes':'not_run','reason':'Confirmed single controlled family does not sustain20waves; broaden only after structural target succeeds.',
        'live_server_validation':False,'randomized_policy_mixtures':False,'defensive_pressure_tasks':False})

if __name__=='__main__':main()
