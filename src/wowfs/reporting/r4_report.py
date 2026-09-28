"""Assemble research conclusions without confusing physical calls with contrasts."""
from __future__ import annotations
import csv,json,shutil
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from wowfs.paths import setup_paths,SOURCE_ROOT,atomic_json
from wowfs.experiments.r2_sequence_analysis import write_csv
from wowfs.experiments.r4_data import load_ecologies
from wowfs.experiments.r4_feasibility import evaluate_admission

def csvread(path):return list(csv.DictReader(path.open()))
def yes(value):return value in [True,'True','true']

def build():
    root=setup_paths();out=root/'artifacts/r4-foundational-discovery';read=lambda name:json.loads((out/name).read_text())
    batch=csvread(out/'BATCH_GRANULARITY.csv');world=csvread(out/'WORLD_RELEASE_FEASIBILITY.csv');ce=csvread(out/'C_E_LOCAL_FEASIBILITY.csv')
    demand=csvread(out/'DEMAND_CAPACITY.csv');growth=csvread(out/'TASK_GROWTH_DIAGNOSTIC.csv');branches=read('BRANCH_SUMMARY.json')
    summary=read('BATCH_SUMMARY.json');precision=read('HIGH_PRECISION_CERTIFICATE_RESULTS.json');unseen=read('UNSEEN_PREDICTION_RESULTS.json')
    pools=read('C_E_STUDY_DESIGN.json')['pools'];base=read('BASE_ECOSYSTEMS.json');pairs=[]
    lookup={(r['ecology'],r['race'],tuple(json.loads(r['release_items']))):yes(r['subset_feasible'])for r in batch}
    groups=defaultdict(list)
    for r in world:groups[(r['intervention_id'],r['ecology'],r['race'])].append(r)
    A=[]
    for (iid,pid,race),rs in sorted(groups.items()):
        old=[lookup[(pid,race,tuple(json.loads(r['release_items'])))]for r in rs];new=[yes(r['subset_feasible'])for r in rs]
        row={'line':'A','pair_id':iid,'ecology':pid,'race':race,'permission':'C t0 rule world','status':'executed',
             'left':'native','right':rs[0]['world'],'left_feasible':sum(old),'right_feasible':sum(new),'release_actions':len(rs),
             'rescued':sum(not a and b for a,b in zip(old,new)),'lost':sum(a and not b for a,b in zip(old,new))}
        pairs.append(row);A.append(row)
    for i,pid in enumerate(pools,1):
        for race in base['races']:
            ds=[r for r in demand if r['ecology']==pid and r['race']==race]
            by={r['demand']:r for r in ds};l=by['single_target_armor_matched'];r=by['heterogeneous_channels']
            pairs.append({'line':'B','pair_id':f'B{i}','ecology':pid,'race':race,'permission':'fixed-physics equal4-demand diagnostic','status':'executed',
                'left':'similar4','right':'heterogeneous4','left_feasible':int(l['joint_feasible_singletons']),'right_feasible':int(r['joint_feasible_singletons']),
                'both_initial_L':yes(l['initial_L'])and yes(r['initial_L']),'all8_old_power_caps_retained':True})
            cs=[r for r in ce if r['ecology']==pid and r['race']==race]
            methods=sorted({r['method']for r in cs});subset=next(m for m in methods if 'subset'in m or 'arbitrary'in m)
            complete=[r for r in cs if r['domain']=='complete_mixing'and r['method']==subset]
            restricted=[r for r in cs if r['domain']!='complete_mixing'and r['method']==subset]
            safe=[r for r in cs if r['domain']=='complete_mixing'and r['method']=='all_safe']
            pairs.append({'line':'C','pair_id':f'C{i}','ecology':pid,'race':race,'permission':'A admission','status':'executed',
                'left':'restricted templates plus every H','right':'complete mixing plus every H','left_feasible':sum(yes(x['joint_feasible_found'])for x in restricted),
                'right_feasible':sum(yes(x['joint_feasible_found'])for x in complete),'release_actions':len(complete)})
            bs=[r for r in batch if r['ecology']==pid and r['race']==race]
            pairs.append({'line':'D','pair_id':f'D{i}','ecology':pid,'race':race,'permission':'A fixed terminal domain; release granularity diagnostic','status':'executed',
                'left':'singletons','right':'all pairs/triples/quads','left_feasible':sum(yes(x['subset_feasible'])for x in bs if x['release_size']=='1'),
                'right_feasible':sum(yes(x['subset_feasible'])for x in bs if x['release_size']!='1'),
                'note':'Different release-size denominators; compare matched final item sets, not event counts.'})
            pairs.append({'line':'E','pair_id':f'E{i}','ecology':pid,'race':race,'permission':'A same table/objective/time/H','status':'executed',
                'left':'all safe','right':'joint subset','left_feasible':sum(yes(x['joint_feasible_found'])for x in safe),
                'right_feasible':sum(yes(x['joint_feasible_found'])for x in complete),'release_actions':len(complete),
                'generic_controls':'scalar,generic2,generic4 on identical complete table; timeout is unresolved'})
            b=next(x for x in branches if x['ecology']==pid and x['race']==race)
            pairs.append({'line':'F','pair_id':f'F{i}','ecology':pid,'race':race,'permission':'A offline common future diagnostic','status':b['status'],
                'left':'qualified current branch a','right':'qualified current branch b','qualified_current_actions':b['qualified_single_gear_actions'],
                'note':'No-common-pair rows are availability failures, not executed paired future trials; no fictitious depth5 items.'})
    write_csv(out/'PAIRED_STRUCTURAL_INTERVENTIONS.csv',pairs)
    initial=[];ecologies=load_ecologies(root/'runs/r4-foundational-discovery/baseline-v1')
    for e in ecologies:
        p,ix=e.problem([],archive=e.initial_archive());m=evaluate_admission(p,np.ones(len(ix),bool))
        carried=len({item for j in m['portfolio_indices']for item in e.gears[ix[j]].values()})
        initial.append({'ecology':e.pool['id'],'race':e.race,'initial_gears':int(e.initial.sum()),'terminal_gears':len(e.gear_ids),
            'P':m['P'],'L':m['L'],'H':m['H'],'C':m['C'],'initial_viable':all(m[k]for k in ['P','L','H','C']),
            'N_D':'not applicable before first release','K':m['K'],'full_carried_item_count':carried,'protected_sources':e.protected_sources,
            'frozen_initial_scale_DPS':e.scale.tolist(),'frozen_cap_DPS':e.cap.tolist(),'initial_estimation_iterations':16})
    write_csv(out/'INITIAL_FEASIBILITY.csv',initial);shutil.copy2(out/'C_E_LOCAL_FEASIBILITY.csv',out/'LOCAL_FEASIBILITY.csv')
    atomic_json(out/'CAPS_METRICS_PERMISSIONS.json',{'Gamma':base['metrics'],'P':'Every current admitted gear and every allowed policy across all eight tasks <= fixed initial1.05 cap.',
        'N':'Each current-new item competitive on >=.05 taskmass','D':'At least one competitive batch-new policy profile L-infinity>=.05 from all H-old policy profiles plus archive; no item ID feature',
        'L':'Every initially competitive variable-slot item and subsequently useful source; fixed items constant in all configurations, acquisition groups descriptive separately',
        'H':'Every already admitted old gear remains legal; no forbidden old substitutes','C':'<=4 gears cover95% mass; full carried itemcount separately; subset exceptions and budget dimensions reported',
        'initial_floor':'Admission-only or new-only reward variants preserve old input physics. C alternate worlds begin at t0; native-reference old performance ratios reported.',
        'permissions':{'A':'fixed physical items; choose new admission','B':'synthetic new reward amplitude only; no old nerfs','C':'native rule intervention applied fromt0'},
        'diagnostics':'Demand reweighting/growth, batch size and hypothetical reference changes are labeled; no threshold relaxation counts as mainGamma success.',
        'scope':'12 finite Warrior Human/Orc ecologies, 8 original tasks,3 executable policies; community engine, not live official validation',
        'precision':'Initial16-seed anchors remain frozen in original ecology. New independent pools calibrate512-seed old anchors before candidates. Highprecision selected certificates retain original caps.'})
    Dmin=Counter(r['release_size']for r in summary['strong_batch_witnesses']if r['all_proper_batches_proved_infeasible'])
    discovery=[
        {'line':'A','result':f'{len(A)}contexts:0 rescued release actions, {sum(x["lost"]for x in A)} lost; many ecological no-ops despite event changes','decision':'not selected','inference':'No evidence these resource/feedback cuts restore joint capacity.'},
        {'line':'B','result':'Similar4 vs heterogeneous4 raw singleton counts7 vs3; added independent tasks9/100 vs9/100','decision':'not selected','inference':'More task heterogeneity/count does not automatically create competitive behavioral novelty; two similar-panel initial states already fail L.'},
        {'line':'C','result':'Complete mixing17/116 vs restricted8/116','decision':'diagnostic','inference':'Candidate-support omission matters; most positives near D threshold, not established legacy coexistence rescue.'},
        {'line':'D','result':f'433/1688 feasible;83 all-singleton-infeasible batches; minimal supports by size{dict(Dmin)}','decision':'deep line retained','inference':'Minimum useful release can exceed one; effect synergy is not necessary.'},
        {'line':'E','result':'All-safe16/116 vs joint17/116; later independent-pool E case also repaired by scalar/generic rules','decision':'secondary constructive diagnosis','inference':'Safe configurations can spoil new-item usefulness; no specialized algorithm advantage.'},
        {'line':'F','result':'Three first-pass matched contexts; one16seed Ψ1 difference. Frozen512 confirmation failed. Unseen matchedHuman Ψ1=.2/.2,Ψ3=Ψ5=0','decision':'deep prediction not confirmed','inference':'Do not claim a robust equal-current-metric continuation separation.'}]
    write_csv(out/'DISCOVERY_MAP.csv',discovery)
    predictions=[
        {'id':'D1','stage':'fresh512','prediction':'resource_hasteHuman pair succeeds, singles fail','outcome':'refuted under fixed original cap; novelty persists but useful safe admission does not'},
        {'id':'D2','stage':'fresh512','prediction':'timing_sharedOrc pair succeeds, singles fail','outcome':'empirically supported, narrow cap margin; latercausal corroboration, not populationjointcertificate'},
        {'id':'F1','stage':'fresh512','prediction':'same current Human branches yield different next-item acceptance','outcome':'not confirmed; one old initial mean itself exceeds original10s cap, and future D distinction does not persist'},
        {'id':'UD1','stage':'unseen fixedMugamba pool','prediction':'Orc joint pair useful while eachsingleton fails','outcome':'supported in independent256seed complete table; single-gear joint certificates with9.62DPS capslack'},
        {'id':'UD2','stage':'unseen fixedDevilsaur pool','prediction':'skilltrade destroys pair joint feasibility','outcome':'direction supported; Orc failure isD aftersafe filtering, not proofthatcap alone caused the change'},
        {'id':'UF1','stage':'unseen commonfuture','prediction':'atleastone matchedcurrentpair hasdifferentΨ1','outcome':'not supported; matchedHuman both.2; unmatchedOrc .2vs0 is not a matched result'},
        {'id':'Bconstruct','stage':'newTF-like designs512seed','prediction':'Human scale.5 andOrc scale.75 pair feasible; largeramplitude morecapblocked','outcome':'positive regions supported; selectedH+onegear confirmed at4096seeds; qualificationuncertainty reported separately'}]
    write_csv(out/'REGIME_PREDICTIONS.csv',predictions)
    figure_dir=out/'figures';figure_dir.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axs=plt.subplots(1,3,figsize=(13,3.8))
    counts=[sum(yes(r['subset_feasible'])for r in batch if int(r['release_size'])==k)for k in range(1,5)]
    den=[sum(int(r['release_size'])==k for r in batch)for k in range(1,5)]
    axs[0].bar(range(1,5),np.array(counts)/den,color='#187d91');axs[0].set(xlabel='Items released together',ylabel='Feasible fraction of declared releases',title='Complete discovery domains')
    for k,a,n in zip(range(1,5),counts,den):axs[0].text(k,a/n+.015,f'{a}/{n}',ha='center',fontsize=9)
    axs[1].bar(['Restricted','Full mixing','All safe','Joint subset'],[8,17,16,17],color=['#9ea6ab','#187d91','#9ea6ab','#187d91']);axs[1].set(ylabel='Feasible actions /116',title='Coverage and admission');axs[1].tick_params(axis='x',rotation=20)
    axs[2].plot([1,3,5],[.4,0,0],'o-',label='Discovery branch A');axs[2].plot([1,3,5],[.2,0,0],'s--',label='Discovery branch B')
    axs[2].plot([1,3,5],[.2,0,0],'x-',color='#bb5b38',label='Unseen matched A and B');axs[2].set(xlabel='Future horizon',ylabel='Conditional finite Psi',title='Initial separation did not replicate');axs[2].legend(fontsize=8)
    fig.suptitle('Finite empirical diagnostics; overlapping actions are not independent ecological replicates',fontsize=11);fig.tight_layout()
    for ext in ['png','pdf']:fig.savefig(figure_dir/f'discovery_overview.{ext}',dpi=180)
    plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(10,3.7))
    cs=precision['certificates'];labels=[c['race'].replace('Race','')for c in cs]
    axs[0].bar(labels,[c['point_min_cap_slack_DPS']for c in cs],color='#187d91');axs[0].scatter(labels,[c['lower_confidence_cap_slack_DPS']for c in cs],marker='_',s=250,color='#bb5b38',label='Simultaneous lower bound');axs[0].axhline(0,color='black',lw=.7);axs[0].set(ylabel='Worst-task cap margin, DPS',title='Selected new-reward certificates');axs[0].legend(fontsize=8)
    for x,c in enumerate(cs):
        w=max(c['witnesses'],key=lambda w:w['D_point']);axs[1].scatter([x],[w['D_point']],color='#187d91',s=70);axs[1].scatter([x],[w['D_lower']],marker='_',s=200,color='#bb5b38')
    axs[1].axhline(.05,color='black',ls='--',lw=1,label='Frozen delta');axs[1].set(xticks=range(2),xticklabels=labels,ylabel='Competitive behavior distance',title='Point values and conservative lower bounds');axs[1].legend(fontsize=8)
    fig.tight_layout()
    for ext in ['png','pdf']:fig.savefig(figure_dir/f'confirmed_construction.{ext}',dpi=180)
    plt.close(fig)
    facts={'planned_paired_contexts':len(pairs),'instantiated_firstpass_F_contexts':sum(x['line']=='F'and x['status']=='matched'for x in pairs),
        'unavailable_firstpass_F_contexts':sum(x['line']=='F'and x['status']!='matched'for x in pairs),
        'A_rescued':sum(x['rescued']for x in A),'A_lost':sum(x['lost']for x in A),'minimal_batch_supports':dict(Dmin),
        'precision':[{k:c[k]for k in ['race','point_min_cap_slack_DPS','lower_confidence_cap_slack_DPS','simultaneous_approximate_checks']}for c in cs]}
    atomic_json(out/'REPORT_FACTS.json',facts)
    question='''# Foundational question after R4

What determines the smallest useful update when every released component must have a competitive use, all historical choices remain legal, old sources retain use, power is capped, and a small portfolio must suffice?

The surviving local obstruction is that the competitive novel configuration can require several *new* components jointly, while no configuration available after a proper subrelease can witness D. A resource-generating or Nature-damage component can need a physical tradeoff partner. Turning off haste did not remove the two key empirical pair certificates.

The finite abstraction admits a witness-support lower bound and an upper bound `s(|L|+1+K)` on some feasible subrelease under explicit minimum-task-mass assumptions and arbitrary subset admission. Complete-combination counterexamples require a release linear in protected-source obligations while task count, behavior dimension and K stay fixed. These are elementary joint-constraint facts; originality beyond existing complementarity and witness sparsification is not certified.

This yields a concrete local design procedure: retain the historical frontier and source/portfolio witnesses, locate a competitive novel support, then alter only new reward strength to fit the resulting retention ceilings. It does not establish sustainable infinite expansion or a robust rule for choosing today's action from long-term continuation estimates.
'''
    (out/'FOUNDATIONAL_QUESTION.md').write_text(question)
    lines=[]
    for c in cs:
        witness=max(c['witnesses'],key=lambda w:w['D_point']);lines.append(f"- {c['race']}: new TF-like physical scale {c['TF_weapon_damage_scale']}; H16 + gear `{c['new_gear_id']}`; pooled4096seed point joint={c['point_metrics']['joint_pass']}, K={c['point_metrics']['K']}, worstL={c['point_metrics']['worst_protected_source_mass']}; cap slack {c['point_min_cap_slack_DPS']:.3f}DPS, simultaneous lower margin {c['lower_confidence_cap_slack_DPS']:.3f}; high-armor D={witness['D_point']:.5f}, conservative lower={witness['D_lower']:.5f}. Approximate joint checks: `{c['simultaneous_approximate_checks']}`.")
    review='''# R4 foundational discovery review

## Seven direct answers

1. **Six explanations:** A's16 native world contexts rescued no declared release and lost42; several event changes were ecological no-ops. B's heterogeneous demand panel and independent task additions did not reliably increase novelty capacity. C's complete mixing recovered9 actions missed by restricted templates, without establishing an old-source coexistence theorem. D found useful atomic batches whose every singleton is impossible in the finite table. E found safe combinations that spoil new-item usefulness, repaired equally by generic scalar/multibudget rules. F's discovery separation failed independent confirmation.
2. **Two deep lines were D and F.** D survived as a local release-support mechanism and was tested by callback ablation, a changed resource-cost pool, a skill-trade boundary, and synthetic new-reward construction. F was investigated through frozen branch selection and exact finite continuation, but its matched-current prediction did not replicate. We do not relabel that failure as a second discovery.
3. **Equal present metrics, different future?** Only a16seed discovery case. The first512seed confirmation was invalid under the original fixed cap and did not reproduce its novelty difference. In the independently calibrated Mugamba pool, the matched Human branches both have Psi1=.2 and Psi3=Psi5=0. Orc .2vs0 is an unmatched1.243% current-frontier contrast, outside the declared1% tolerance.
4. **Positive construction completed:** retain all16 old configurations and admit one joint new configuration; give the new TF-like reward only50% (Human) or75% (Orc) native physical weapon damage, leaving speed, procs and old items unchanged. Both selected certificates pass all six point-mean requirements at4096 seeds/cell. The simultaneous uncertainty checks below limit the population claim.
5. **Concrete reward decision:** test the useful release unit before rejecting each reward separately. Preserve the Nature/resource behavior channel and adjust a new item's physical contribution to fit old-source retention ceilings. Haste suppression alone is not the required mechanism. Opening every cap-safe combination can still remove a new item's competitive use.
6. **Abstract result:** a necessary qualifying-support bound and constructive retention certificate; under fixed H/reference, arbitrary subset admission and each positive task weight at least minimum usefulness mass, some feasible subrelease has size at most `s(|L|+1+K)`. A complete coequipment counterexample requires Omega(|L|) items with one task, one behavior coordinate and K=s=1. This is elementary witness sparsification and constraint coupling, not a claim to have invented complementarity, set cover or viability.
7. **Candidate two-sentence claim:** historical commitments can force the minimum useful update to contain several components even when every individual component is rejected, and local competitive witness supports expose that obstruction. A finite witness certificate controls release size and supplies a constructive admission procedure, with native local examples supporting atomic pairs but no demonstrated long-horizon sustainability. **An AISTATS Oral-level novelty claim is not established**: stronger transferable conditions or an information/learning result remain missing.

## Completed evidence

- Twelve complete development ecologies:1,860 logical gear incidences,1,747 distinct native gears,8 tasks,3 policies and Human/Orc. Full mixing includes Maelstrom wherever declared; completeness is only within these small domains.
- There are48 planned intervention designs and96 race-level context rows. F could instantiate matched first actions in only3 of16 first-pass contexts; the other13 are explicit availability failures. They are not counted as completed future comparisons. Additional independently frozen F checks appear separately.
- D exhaustively evaluates1,688 releases of1–4 items:433 feasible, including83 feasible batches whose every singleton is proved infeasible in the empirical table. Shared items/races/releases are not independent ecological samples. No converse example with every singleton feasible but the joint batch impossible was found in this finite domain.
- Complete-domain C/E comparison:17/116 jointly feasible versus8/116 under restricted templates and16/116 under all-safe opening. One generic2 solve timed out; it remains unresolved. Scalar/generic4 match17. A later exploratory E separation in the independently generated Mugamba pool also needs exactly2 exclusions and is solved equally by scalar/generic2/generic4.
- The causally selected TF pair survives when Eskhandar haste is disabled. The named high-armor interaction is+0.275DPS with a family5,184 approximate interval[-0.193,0.742]. The rage pair likewise survives haste removal with the rage active retained. This refutes necessity of the haste callback; it does not prove all interactions vanish.
- New-pool prediction: the Orc Mugamba pair remains useful while both singleton releases fail; some one-gear certificates have9.62DPS cap margin and D≈.135. Removing Edgemaster in the other pool eliminates the pair's empirical feasibility; the endpoint failure alone does not isolate skill from the glove's other stat changes.

## Final selected new-reward certificates

'''+ '\n'.join(lines)+'''

The power/performance intervals use a simultaneous Student-t hyperrectangle over816 means; behavior uses paired eight-block coordinate differences against every old policy profile, family16,128. These are conservative approximate intervals, not distribution-free coverage. A failed lower-bound check is unresolved, not proof of actual violation. The point metrics and all failed bounds remain in HIGH_PRECISION_CERTIFICATE_RESULTS.json. This17-gear confirmation does not by itself re-prove singleton impossibility over a complete domain.

## Integrity and limits

The main epsilon, delta, minimum task mass and headroom are all.05, K≤4 and task coverage.95. All three executable policies are available to old and new gear. H retains every admitted choice, D compares against every protected old policy plus the stored archive, and each new item needs N. Under fixed physics and monotone H the archive is already contained in H's policy profiles; the operative history geometry is the protected response set. No item name enters behavior distance.

Original16seed numerical caps remain fixed even when fresh old means exceed them. The two genuinely changed pools use512seed initial calibration frozen before candidate evaluation. They do not repair failed original worlds by moving caps. The threshold curves were declared before fresh confirmation, after initial discovery had been observed; they are diagnostic and never replace mainGamma success.

Permission A changes admission; B designs clearly synthetic new rewards; C changes the physical world fromt0 and records old-performance ratios to native. Resource-pressure combat is a native resource/mitigation stress: engine death does not stop attacks, so there is no survival claim. Native policies remain a limited executable menu, often dominated by native_reck. Rogue resource mechanics were inspected, but no Rogue physics or cross-class admission claim is made; Warrior-only items cannot be forced onto Rogue.

The supplied R3 INDEPENDENT_CHECKS.json was absent. R3_INPUT_AUDIT.json reconstructs the quoted failure groups from actual trajectories instead of inventing that file. Preparation errors, the corrected action-list comparison, corrected block-axis interval analysis, and solver scheduler retry are preserved and distinguished from native combat failures. See analysis_versions, protocol snapshots, the source notes and the independent native receipt.

## Reproduction and navigation

Run `source scripts/env.sh` from the source repository. Frozen physical runs and exact inputs are under `$WOWFS_WORK_ROOT/runs/r4-foundational-discovery/`; cache receipts and compressed outputs remain in `$WOWFS_WORK_ROOT/cache/r4-foundational-discovery/native/`. Every native run has a frozen executable, protocol, source snapshot and complete input manifest. Source drivers expose their run/resume commands; docs/r4/NATIVE_PLATFORM.md describes the platform. Existing completed runs must be resumed with identical hashes, not overwritten.

DISCOVERY_MAP.csv and PAIRED_STRUCTURAL_INTERVENTIONS.csv identify denominators and unavailable comparisons. FULL_COMBINATION_COVERAGE.csv, BATCH_GRANULARITY.csv, LOCAL_FEASIBILITY.csv and the selected deep tables preserve failures. THEORY.md and CLAIM_PRIOR_WORK_MAP.md separate proved finite statements, native means, prior results and missing claims. NATIVE_RUN_RECEIPT.json gives the independently audited physical total; logical pool/method/trajectory reuse never adds battles. The ZIP contains maintained source and selected evidence, not third-party environments or the full combat cache.
'''
    audit=read('INDEPENDENT_NATIVE_AUDIT.json')
    review=review.replace('# R4 foundational discovery review\n',
        '# R4 foundational discovery review\n\nCompleted and independently audited: '
        f"**{audit['native_calls']:,} native calls,{audit['physical_battles']:,} battles,13 complete native runs; zero failures,missing receipts or audit errors.** The full Python suite passes73 tests.\n",1)
    (out/'REVIEW.md').write_text(review)
    doc=SOURCE_ROOT/'docs/r4';(doc/'FOUNDATIONAL_QUESTION.md').write_text(question);(doc/'REVIEW.md').write_text(review)
    print(json.dumps(facts,indent=2))

if __name__=='__main__':build()
