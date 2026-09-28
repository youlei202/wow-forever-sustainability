"""Assemble the native R2 review from executed, separately scoped studies."""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path
import shutil
import zipfile
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from wowfs.paths import SOURCE_ROOT, setup_paths, atomic_json

def read_csv(path):
    with path.open() as f:return list(csv.DictReader(f))

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    root=setup_paths();out=root/'artifacts/r2-discovery/latest';run=root/'runs/r2-discovery'
    audit=json.loads((out/'INDEPENDENT_NATIVE_AUDIT.json').read_text())
    if not audit['snapshot_complete_and_quiescent'] or audit['audit_errors']:
        raise ValueError('native audit is incomplete')
    sequences=read_csv(out/'SEQUENCE_RESULTS.csv');rounds=read_csv(out/'ROUND_RESULTS.csv')
    faction=read_csv(out/'FACTION_SUMMARY.csv')
    freeze=json.loads((run/'unseen-v1/FROZEN_DESIGN.json').read_text())
    primary=read_csv(out/'CONFIRMATION_PRIMARY.csv')
    shutil.copy2(out/'CONFIRMATION_PRIMARY.csv',out/'INTERACTION_CASES.csv')
    previous=out/'NATIVE_RUN_RECEIPT.json';bridge=out/'BRIDGE_RUN_RECEIPT.json'
    if previous.exists() and not bridge.exists():shutil.copy2(previous,bridge)
    atomic_json(previous,{'schema_version':2,'scope':'all executed native R2 studies; no R1 abstract rows',
        'engine_repository':'https://github.com/sage3648/mythicsim-forever-engine',
        'engine_commit':'17d75ccc8c67d027ae0088243ea3ee806d406847','ruleset':'RulesetForever',
        'native_invocations':audit['total_verified_successful_native_invocations'],
        'physical_battles':audit['total_verified_physical_battles'],
        'failed_receipts':audit['failed_invocation_receipts'],'audit_errors':audit['audit_errors'],
        'executed_contexts':audit['executed_contexts'],'class_count':1,'race_count':2,'factions':2,
        'unique_native_update_trajectories':16,'rounds_per_trajectory':20,
        'methods':10,'headroom_panels':[0,.05],
        'decision_rows':len(rounds),'not_independent_battle_replications':'Methods reuse identical physical inputs; contexts share source-defined equipment catalogues.',
        'coverage_missing':'Mage/Hunter/Warlock/other classes, other races, target 3-class48 and full9-class360 trajectories not completed',
        'independent_audit_sha256':sha(out/'INDEPENDENT_NATIVE_AUDIT.json'),
        'ledger_sha256':audit['ledger_sha256'],'ledger_path':audit['ledger_path'],
        'native_cache':str(root/'cache/r2-discovery/native'),
        'unseen_protocol_sha256':sha(run/'unseen-v1/FROZEN_DESIGN.json'),
        'validation_limit':'Pinned community implementation, not official/live-server fidelity certification',
        'early_smoke_limit':'Original pre-gofmt smoke binary bytes not retained; six uncached bridge calls have input/output hashes and explicit provenance limitations.'})
    with (out/'COVERAGE.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['class','race','faction','native_status','matched_sequences','rounds_each','native_physical_scope'])
        w.writerow(['Warrior','Human','Alliance','completed',8,20,'four tasks, three policies, finite loadout catalogue'])
        w.writerow(['Warrior','Orc','Horde','completed',8,20,'four tasks, three policies, finite loadout catalogue'])
    atomic_json(out/'PROTOCOL.json',{'native_run':str(run/'unseen-v1'),
        'frozen_design_sha256':sha(run/'unseen-v1/FROZEN_DESIGN.json'),
        'actual_initial_thresholds':freeze['thresholds'],'decisions':freeze['decisions'],
        'counts':freeze['counts'],'primary_confirmation':json.loads((run/'confirmation-v1/PRIMARY_CONTRASTS.json').read_text()),
        'analysis_protocol':json.loads((out/'SEQUENCE_ANALYSIS_PROTOCOL.json').read_text()),
        'freeze_source_files':freeze['source_hashes']})
    atomic_json(out/'RULES_AND_PERMISSIONS.json',{
        'source_semantic_and_generic':{'rows':[2,4,8],'frozen':True,'same_features':True,
            'source_semantics_known':True,'learned_unknown_signatures':False,
            'generic_training_optimum':'185/185 initial loadouts admitted, global maximum of declared training count; retain feasible structured initialization',
            'future_responses_used_for_rule':False,'validation_responses':'full finite physical table, separate from rule decisions'},
        'scalar_exceptions_and_envelope':{'information':'all currently available finite responses; no future responses',
            'role':'strong full-current-information baselines and finite-table reference, not query-matched statistical estimators'},
        'mechanism_panel':{'parameters_seconds':[0,1,2],'same_permission_generic':True,'frozen_selected_seconds':0,
            'selection':'retain95% four common-native witnesses; minimize worst reoptimized ratio; ties smaller cooldown'},
        'metadata':'fixed q is not fixed total description length; per-item descriptor bytes recorded each round',
        'not_completed':['quality-matched synthetic native variants','isolated causal semantic-count axis','finite-data adaptive signature acquisition','same-state future-branch experiment','three-class native confirmation']})

    labels={'no_control':'No control','scalar_reprice':'Scalar (full data)',
            'semantic_2':'Frozen semantic q=2','semantic_8':'Frozen semantic q=8'}
    colors={'no_control':'#ba4d3b','scalar_reprice':'#2f7c66','semantic_2':'#4267a2','semantic_8':'#87539c'}
    plt.rcParams.update({'font.size':8,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(figsize=(6.8,2.7),layout='constrained')
    compact_labels=['Flask / Cloudkeeper: 30 s','Flask / Cloudkeeper: four targets',
                    'Flask / Cloudkeeper: 180 s','Haste / extra: four targets',
                    'Extra / rage / HoJ: four targets','Extra / rage: 180 s']
    for i,r in enumerate(primary):
        est=float(r['estimate'])
        if r['degenerate_observed_variance']=='True':
            ax.scatter([0],[i],marker='D',facecolor='none',edgecolor='gray',s=25)
            ax.annotate('numerical zero; degenerate variance',(0,i),xytext=(5,0),textcoords='offset points',fontsize=7,va='center')
        else:ax.errorbar(est,i,xerr=[[est-float(r['ci_low'])],[float(r['ci_high'])-est]],fmt='o',capsize=3,color='#a43d42' if r['direction']=='negative' else '#355b7c')
    ax.set_yticks(range(6),compact_labels);ax.invert_yaxis();ax.axvline(0,color='gray',ls='--',lw=1)
    ax.set_xlim(-22,17);ax.set_xlabel('Paired factorial interaction (DPS); adjusted family of six');ax.grid(axis='x',alpha=.2)
    fig.savefig(out/'figures/primary_interactions_compact.pdf');plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(7.2,2.8),layout='constrained')
    for method,label in labels.items():
        data=[r for r in rounds if r['method']==method and float(r['headroom'])==.05]
        x=np.arange(1,21)
        def agg(key,op):return [op([float(r[key]) for r in data if int(r['round'])==t]) for t in x]
        axes[0].plot(x,np.array(agg('power_growth',max))*100,label=label,color=colors[method])
        axes[1].plot(x,np.array(agg('new_useful_fraction',np.mean))*100,color=colors[method])
        axes[2].plot(x,agg('distinct_new_choices',np.mean),color=colors[method])
    axes[0].axhline(5,color='black',ls='--',lw=1)
    for a in axes:a.set_xlabel('Arrival round');a.set_xlim(1,20);a.grid(alpha=.15)
    axes[0].set_ylabel('Worst growth (%)')
    axes[1].set_ylabel('Competitive new items (%)')
    axes[2].set_ylabel('New task profiles (mean)')
    axes[0].legend(fontsize=6,loc='upper left')
    fig.suptitle('5% cumulative headroom in the tested catalogue',fontsize=10)
    for ext in ['png','pdf']:fig.savefig(out/'figures'/f'expansion_tradeoffs.{ext}',dpi=160)
    plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10.8,3.7),layout='constrained')
    for ax,expanded in zip(axes,[False,True]):
        for method,label in labels.items():
            data=[r for r in rounds if r['method']==method and float(r['headroom'])==.05 and r['generator'].startswith('expanded')==expanded]
            x=sorted({int(r['metadata_items']) for r in data})
            y=[max(float(r['power_growth']) for r in data if int(r['metadata_items'])==n)*100 for n in x]
            ax.plot(x,y,label=label,color=colors[method])
        ax.axhline(5,color='black',ls='--',lw=1);ax.set_xlabel('Available native item IDs');ax.set_ylabel('Worst observed growth (%)');ax.grid(alpha=.15)
        ax.set_title('Expanded primitive families' if expanded else 'Fixed broad primitive families')
    axes[0].legend(fontsize=7)
    fig.suptitle('Descriptive grammar split; item strength is not matched between families')
    for ext in ['png','pdf']:fig.savefig(out/'figures'/f'item_and_grammar_expansion.{ext}',dpi=160)
    plt.close(fig)

    table=['\\begin{table*}[t]','\\centering\\small',
           '\\begin{tabular}{llrrrrrr}\\toprule',
           'Method & Context & $S_{20}$ & Pass & Max growth & New use & New choices & $K_{20}$\\\\\\midrule']
    for method,label in [('no_control','No control'),('scalar_reprice','Scalar repricing'),('semantic_2','Semantic 2'),('semantic_8','Semantic 8'),('envelope_reference','Finite safe reference')]:
        for r in faction:
            if r['method']==method and float(r['headroom'])==.05:
                context='Human (A)' if r['faction']=='Alliance' else 'Orc (H)'
                table.append(f"{label} & {context} & {float(r['S20']):.0f} & 0/8 & {float(r['max_power_growth'])*100:.2f}\\% & {float(r['new_useful_fraction'])*100:.1f}\\% & {float(r['distinct_new_choices']):.3f} & {int(r['K20'])}\\\\")
    table.extend(['\\bottomrule\\end{tabular}',
        '\\caption{Executed Warrior subset, cumulative 5\\% panel. Growth is the largest observed value across eight paired sequences per context; new use and task-conditioned separated-choice counts are means. Generic q models exactly match their semantic counterparts. The full table, including legacy denominators and rule metadata, is supplied as CSV.}',
        '\\end{table*}',
        'All methods have $S_{20}=0$ and zero complete successes in both headroom panels. The first arrival never supplies a behavior separated from the fixed historical archive at the declared resolution. Across 320 round decisions per method at 5\\%, frozen semantic rules violate power in 32; all these violations are supported by the approximate simultaneous mean bounds within context. Increasing q from 2 to 8 does not reduce the worst observed growth (18.39\\%), while rejecting additional loadouts. Full-current-response scalar repricing and the finite safe reference keep point-estimate growth below 5\\%, but do not achieve the joint reward requirement. These safety decisions are not pathwise certificates.',
        'Every evaluated portfolio has $K=1$. Thus this damage-task domain does not supply evidence that equipment-management complexity is the limiting factor. At zero extra headroom no method yields a new separated competitive behavior under the fixed mean-profile definition. Proposal quality and task diversity remain major limitations; this is not an impossibility result for sustainable expansion.',
        '\\begin{figure*}[t]\\centering\\includegraphics[width=\\textwidth]{expansion_tradeoffs.pdf}\\caption{Observed finite-catalogue tradeoffs. Curves reuse the same physical combat data and are not independent method samples. New choices are task-conditioned greedy separated mean-profile counts, excluding item identity.}\\end{figure*}'])
    target=SOURCE_ROOT/'paper/r2_tables/results.tex';target.parent.mkdir(exist_ok=True);target.write_text('\n'.join(table)+'\n')

    for name in ['ENVIRONMENT','NATIVE_MECHANISMS','CONFIRMATION_FINDINGS','MECHANISM_FINDINGS','MECHANISM_CONFIRMATION','SEQUENCE_FINDINGS','DESCRIPTOR_AUDIT','UNSEEN_DESIGN','STATISTICAL_DESIGN','REPRODUCE']:
        p=SOURCE_ROOT/f'docs/r2/{name}.md'
        if p.exists():shutil.copy2(p,out/p.name)
    theory=out/'theory';theory.mkdir(exist_ok=True)
    for name in ['THEORY','RELATED_WORK']:shutil.copy2(SOURCE_ROOT/f'docs/r2/{name}.md',theory/f'{name}.md')
    ledger=Path(audit['ledger_path']);shutil.copy2(ledger,out/'NATIVE_CALL_LEDGER.jsonl.gz')
    evidence=out/'selected_evidence';evidence.mkdir(exist_ok=True)
    shutil.copy2(run/'unseen-v1/FROZEN_DESIGN.json',evidence/'UNSEEN_FROZEN_DESIGN.json')
    shutil.copy2(run/'RECOVERED_ENGINE_REFERENCE.json',evidence/'RECOVERED_ENGINE_REFERENCE.json')
    for name in ['native-smoke','mechanism-smoke']:
        destination=evidence/name;destination.mkdir(exist_ok=True)
        for p in (run/name).glob('*.json'):shutil.copy2(p,destination/p.name)
    (out/'DISCOVERIES.md').write_text('''# What changed the scientific direction

1. **Suppressing one real trigger family can hurt alternatives while leaving the strongest achieved outputs untouched.** Fresh seeds confirm a -7.777 DPS loss for one selected build, while four strong native task witnesses produce no gated requests and retain identical outputs. The generic selector with the same permissions also selects zero intervention.
2. **An existing shared cooldown destroys marginal reward value in short encounters.** Flask plus Cloudkeeper has a -18.669 DPS pair interaction at 30 seconds. Both effects have standalone value; the native timer and schedule suppress one in combination. Reoptimization does not establish a persistent global cost.
3. **More descriptor rows did not fix the frozen rule.** q=2/4/8 have the same worst observed 18.39% power growth; q=8 excludes additional DoT/armor configurations by its zero initial thresholds. Same-dimensional generic models reproduce these frozen solutions exactly.
4. **Even strong full-current-information baselines fail the joint goal.** Scalar repricing and the finite safe reference keep point-estimate power within the chosen cap but supply too little distinct competitive behavior. All 16 trajectories per method/headroom fail immediately on D, and K remains1. This is evidence about this proposal/task domain, not an impossibility theorem.

Positive amplification hypotheses, quality-matched synthetic proposals, a clean semantic-count causal axis, new statistical learning theory, and broader classes remain unestablished. The full finite-dataset means and uncertainty are retained, including failures.
''')
    (out/'REVIEW.md').write_text(f'''# R2 native discovery review

**Actually completed: {audit['total_verified_successful_native_invocations']:,} native calls and {audit['total_verified_physical_battles']:,} battles; the independent audit found zero failures, missing cells, or hash errors.**
Engine: `sage3648/mythicsim-forever-engine`, pinned commit `17d75ccc8c67d027ae0088243ea3ee806d406847`, `RulesetForever`. These are native simulation results from a community implementation, not certification of official server mechanics.

Coverage comprises Warrior / Human (Alliance) and Orc (Horde), 4 tasks, and 3 implemented policies. Each faction has 8 complete 20-round sequences, totaling 16 per method; 10 methods and two headroom panels, 0 and cumulative 5%, yield 6400 update decisions. Physical data are shared, so the 320 method panels are not treated as 320 independent equipment ecologies. The planned 48 sequences across three classes, nine-class breadth, and other races are not yet completed.

## Main findings

**Restricting one proc chain need not restrict power after player reoptimization, and can hurt alternative loadouts first.** Shared extra-main-hand-attack cooldowns of 1/2 seconds do reduce procs. Across 128 fresh seeds, four strong native configurations bypass this chain and retain identical battle-by-battle outputs, while one affected configuration loses 7.777 DPS, with a five-comparison-adjusted interval of [-11.660,-3.893]. The generic design with the same permissions also selects 0 seconds; this candidate mechanism should be abandoned.

An existing shared offensive cooldown has a confirmed local cost: the Diamond Flask × Cloudkeeper interaction over 30 seconds is **−18.669 DPS**, with a six-comparison-adjusted interval of [-19.228,-18.110]; the four-target task interaction is −5.563 DPS. Native logs explain the cause. A persistent global loss has not been confirmed after allowing equipment and policy reoptimization. The three primary positive-amplification hypotheses were not confirmed; a near-zero sustained-combat result is not proof of universal equivalence.

## Strongest baselines and joint tradeoffs

The frozen q=2/4/8 semantic rules tie the same-dimensional generic models exactly; all have a maximum empirical power growth of **18.39%**. The same Deathbringer+Thunderfury loadout passes every q: its per-proc damage descriptor of 440 is below the old threshold of 737, while proc frequency and resistance-state dependence are absent from that numerical row. The ninth-dimension unknown-semantic marker is also not a rejection condition for q=8. This refutes the frozen heuristic tested here, not every eight-dimensional rule. q=8 rejects more combinations without reducing the strongest measured output. Compatible single-budget repricing with all current information and the finite safe-set reference keep empirical growth within 5%, but also fail the joint objective.

**Every method has S20=0 and Pass20=0/16 in both headroom panels.** All first rounds fail D, and new rewards also often lack competitive use. K is 1 in all 6400 round results; loadout complexity is not the main bottleneck here. Behavior counts use task-conditioned mean profiles of finite configurations and exclude equipment IDs; they do not rule out substitutes among unsearched policies or randomized mixtures. The legacy-source fraction refers to previously registered new items with competitive uses. Per-item deletion results for initial equipment are reported separately and do not establish that every initial item is irreplaceable.

The two-axis test uses existing native items, 1 per round. Fixed-grammar and expanding-grammar strengths are not matched, so differences cannot be causally attributed to the number of types. Source-code semantics are known inputs; an equal-budget adaptive-learning experiment for unknown interaction signatures has not yet been completed. All results retain failures and report statistical bounds separately from empirical point estimates.

## Theory and review entry points

Completed theoretical results include a conditional resource-contract window upper bound, non-explosion conditions, and a finite temporal-choice witness with zero power growth (K=2). These conditions have not yet been validated on native feedback chains. Resource accounting and positive-systems tools are not claimed as original; native K is actually 1.

- `paper/r2_main.pdf`: standalone R2 manuscript rewritten around native findings; the historical R1 manuscript is retained.
- `INTERACTION_CASES.csv`, `CONFIRMATION_FINDINGS.md`: six confirmations and original four/eight-cell means.
- `ROUND_RESULTS.csv`, `SEQUENCE_RESULTS.csv`, `FACTION_SUMMARY.csv`: executed native joint results.
- `RULE_REUSE.csv`, `REWARD_COUNTERFACTUALS.csv`: admission, full metadata costs, and reoptimization after deletion.
- `PROTOCOL.json`, `RULES_AND_PERMISSIONS.json`, `NATIVE_RUN_RECEIPT.json`: frozen conditions, information permissions, and actual call counts.
- `selected_evidence/`: actual inputs, outputs, complete event logs, commands, and frozen designs.
- `theory/`, `SOURCE_CODE.zip`: complete propositions, positioning in the literature, and maintained source code.
- `NATIVE_CALL_LEDGER.jsonl.gz`: input/output/executable hashes for all physical calls.

Bulk data: `{root}/cache/r2-discovery/native/`; frozen run: `{run}/`. Use the commands in `REPRODUCE.md`. Both confirmation and the main 20-round run pass read-only resume validation; existing result bytes are unchanged and no battles were added. Binaries for some early smoke calls were not retained; inputs/outputs remain for all 37 bridge checks, and provenance differences are explicitly recorded in the independent audit.

## Three next research questions

1. After matching individual-item quality, can changes to actual proc timing/resource paths add new behavior beyond substitutability?
2. How can all competitive alternative paths be controlled, rather than suppressing only one conspicuous chain?
3. Which finite combat probes can identify new interaction signatures and remain effective for Mage or pet classes?
''')
    print(str(out))

if __name__=='__main__':main()
