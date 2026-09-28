"""Assemble small decisive-value tables and scientific figures from frozen evidence."""
import csv
import json
import shutil
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from wowfs.paths import setup_paths,atomic_json
from wowfs.experiments.r2_sequence_analysis import write_csv
from wowfs.experiments.value_confirmation_data import load_confirmation


def main():
    root=setup_paths();out=root/'artifacts/decisive-value';a=json.loads((out/'PROSPECTIVE_CONFIRMATION.json').read_text())
    table=vars(load_confirmation());scale=np.asarray(a['fixed_scale']);cap=np.asarray(a['fixed_cap']);u=table['values']
    # Preserve the original cached screen separately before making an aggregate.
    cached=out/'LINE_A_DECISION_VALUES.csv'
    if not cached.exists():shutil.copy2(out/'DECISION_VALUE_RESULTS.csv',cached)
    with cached.open() as f:rows=[{'phase':'cached_native_16_seed_development',**r} for r in csv.DictReader(f)]
    sequence=[];decision=[];certificates=[]
    for r in a['rounds']:
        m=r['metrics'];admit=np.array([g in r['admitted_gear_ids'] for g in table['gear_ids']]);best=u[admit].max(axis=(0,1))
        sequence.append({'phase':'independent_native_confirmation','sequence':'prospective_two_slot','round':r['round'],
            'released_sources':r['released_sources'],'cumulative_released_count':2*r['round'],
            **{k:m[k] for k in ('P','N','D','L','H','C','G','K','all_seven_pass')},
            'normalized_gain':m['normalized_gain'],'gain_mass':m['gain_mass'],
            'cumulative_normalized_gain':r['cumulative_normalized_gain'],
            'old_gear_count':len(r['before_gear_ids']),'admitted_gear_count':int(admit.sum()),
            'physical_cross_count':(r['round']+2)**2,'cap':a['fixed_cap'],'scale':a['fixed_scale'],
            'minimum_normalized_cap_margin':r['minimum_normalized_cap_margin'],
            'worst_protected_source_mass':m['worst_protected_source_mass'],
            'all_source_masses':m['source_masses'],'rule_rows':24,'rule_feature_dimensions':4,'exceptions':0,
            'paired_t_G_status':'supported_approximately' if r['approx_simultaneous_paired_t_gain_pass'] else 'unresolved',
            'bootstrap_G_status':'supported_approximately' if r['paired_bootstrap_simultaneous_gain_pass'] else 'unresolved',
            'empirical_successful_prefix':r['round'],'population_joint_status':'not_established',
            'source_deletion':r['all_source_deletions']})
        for q,task in enumerate(a['tasks']):
            gi,pi=np.unravel_index(u[admit,:,q].argmax(),u[admit,:,q].shape)
            new_index=np.flatnonzero(admit)[gi]
            row={'phase':'independent_native_confirmation','ecology':'prospective_two_slot','race':'RaceHuman',
                'round':r['round'],'task':task,'task_weight':.125,'old_reoptimized':m['old_reoptimized_utility'][q],
                'new_reoptimized':m['optimum'][q],'old_library_count':len(r['before_gear_ids']),
                'new_library_count':int(admit.sum()),'allowed_policy_count':3,'winning_gear':table['gear_ids'][new_index],
                'winning_policy':a['policies'][pi],'fixed_scale':scale[q],'fixed_cap':cap[q],
                'gain_normalized':m['normalized_gain'][q],
                'delete_whole_release_utility':m['old_reoptimized_utility'][q],
                'delete_source_utilities':{s:v['utility_without_source'][q] for s,v in r['all_source_deletions'].items()},
                'paired_t_gain_lower':r['approx_simultaneous_paired_t_gain_lower'][q],
                'paired_t_gain_upper':r['approx_simultaneous_paired_t_gain_upper'][q],
                'bootstrap_joint_gain_lower':r['paired_bootstrap_simultaneous_gain_lower'][q],
                'bootstrap_joint_gain_upper':r['paired_bootstrap_simultaneous_gain_upper'][q],
                'task_gain_pass':m['normalized_gain'][q]>=.01, 'release_G':m['G'],
                **{k:m[k] for k in ('P','N','D','L','H','C','K')},
                'inference':'Frozen independent means; approximate gain intervals; original D has no population certificate'}
            rows.append(row);decision.append(row)
        for source in sorted(m['source_masses']):
            use=admit & np.array([source in s for s in table['sources']]);v=u[use].max(axis=(0,1))
            certificates.append({'round':r['round'],'source':source,
                'empirical_use_mass':m['source_masses'][source],
                'permanent_witness_task_mass':float(np.mean(v>=cap-.05*scale)),
                'source_best_utility':v.tolist(),'threshold':(cap-.05*scale).tolist(),
                'inference':'Conditional on these being population means and future fixed caps/H; empirical witness check only'})
    write_csv(out/'DECISION_VALUE_RESULTS.csv',rows)
    write_csv(out/'FINAL_DECISION_VALUE_RESULTS.csv',decision)
    with (out/'LINE_C_SEQUENCE_RESULTS.csv').open() as f:cached_seq=[{'phase':'cached_native_16_seed_development',**r} for r in csv.DictReader(f)]
    write_csv(out/'SEQUENCE_RESULTS.csv',cached_seq+sequence)
    write_csv(out/'PERMANENT_SOURCE_WITNESSES.csv',certificates)
    search=json.loads((out/'CONSTRUCTIVE_SEARCH.json').read_text())
    attempts=[{'round':r['round'],**r['counts'],'selected':1,'not_selected':r['counts']['proposed']-1,
               'guarded_joint_rejected':r['counts']['proposed']-r['counts']['strict_joint']} for r in search['rounds']]
    write_csv(out/'CONSTRUCTION_ATTEMPTS.csv',attempts)
    # Figure1: real tasks, cumulative fixed-scale growth, unchanged cap.
    fig,axes=plt.subplots(1,3,figsize=(15,4.5),layout='constrained')
    gains=100*np.array([r['metrics']['normalized_gain'] for r in a['rounds']])
    im=axes[0].imshow(gains,vmin=0,vmax=2.5,cmap='Blues',aspect='auto')
    axes[0].set(xticks=range(8),xticklabels=['180 s','30 s','4 targets','Armor 10k','10 s','360 s','2 targets','Incoming'],yticks=range(3),yticklabels=['Release 1','Release 2','Release 3'],title='Additional real-task value (%)')
    axes[0].tick_params(axis='x',rotation=60)
    for i in range(3):
        for j in range(8):axes[0].text(j,i,f'{gains[i,j]:.2f}',ha='center',va='center',fontsize=8,color='white' if gains[i,j]>1.7 else 'black')
    qlist=[3,4,1]
    for q in qlist:
        ys=[100*(a['confirmed_initial_utility'][q]/scale[q]-1)]+[100*(r['metrics']['optimum'][q]/scale[q]-1) for r in a['rounds']]
        axes[1].plot(range(4),ys,marker='o',label=a['tasks'][q])
    axes[1].axhline(5,ls='--',color='black',label='Fixed cap +5%')
    axes[1].set(xlabel='Release',ylabel='Utility above frozen initial scale (%)',xticks=range(4),ylim=(-.2,5.7),title='Growth stays inside the original cap')
    axes[1].legend(fontsize=8,loc='upper left')
    points=[r['metrics']['normalized_gain'][q] for r,q in zip(a['rounds'],[3,4,3])]
    low=[r['paired_bootstrap_simultaneous_gain_lower'][q] for r,q in zip(a['rounds'],[3,4,3])]
    high=[r['paired_bootstrap_simultaneous_gain_upper'][q] for r,q in zip(a['rounds'],[3,4,3])]
    axes[2].errorbar([1,2,3],np.array(points)*100,yerr=np.array([np.array(points)-low,np.array(high)-points])*100,fmt='o',capsize=5,color='#126b7c')
    axes[2].axhline(1,ls='--',color='darkred');axes[2].set(xticks=[1,2,3],xlabel='Release',ylabel='Additional value (%)',title='One independent confirmation panel',ylim=(0,3))
    axes[2].text(.03,.97,'Approximate simultaneous 95%\npaired bootstrap intervals\nAll old gear and policies reoptimized',va='top',transform=axes[2].transAxes,fontsize=8)
    axes[2].text(.03,.04,'Release 1: 1% threshold unresolved',transform=axes[2].transAxes,fontsize=8)
    for ext in ('png','pdf'):fig.savefig(out/f'DECISIVE_VALUE.{ext}',dpi=180)
    plt.close(fig)
    # Figure2: all first-release crosses, not only the favorable pair.
    q=3;grid=u[:,: ,q].max(axis=1).reshape(5,5)[:3,:3]/scale[q]
    fig,ax=plt.subplots(figsize=(6,4.5),layout='constrained');im=ax.imshow((grid-1)*100,cmap='coolwarm',vmin=-8,vmax=7)
    ax.set(xticks=[0,1,2],xticklabels=['Old OH0','Old OH1','New OH2'],yticks=[0,1,2],yticklabels=['Old MH0','Old MH1','New MH2'],title='First release: all 9 high-armor combinations')
    for i in range(3):
        for j in range(3):ax.text(j,i,f'{(grid[i,j]-1)*100:.2f}%'+('\nCap violation' if grid[i,j]>1.05 else ''),ha='center',va='center',fontsize=11)
    fig.colorbar(im,ax=ax,label='Above frozen initial high-armor scale (%)')
    for ext in ('png','pdf'):fig.savefig(out/f'CAP_COMPENSATION.{ext}',dpi=180)
    plt.close(fig)
    summary={'native_empirical_prefix':3,'population_joint_prefix':'not_established',
        'first_release_gain_threshold_status':'unresolved','total_development_proposals':sum(r['counts']['proposed'] for r in search['rounds']),
        'guarded_joint_candidates':sum(r['counts']['strict_joint'] for r in search['rounds']),
        'all_final_source_uses_positive':all(v>=.05 for v in a['rounds'][-1]['metrics']['source_masses'].values()),
        'permanent_source_witnesses_last_round':sum(r['permanent_witness_task_mass']>=.05 for r in certificates if r['round']==3),
        'fixed_complexity':{'inequalities':24,'physical_features':4,'exceptions':0,'near_optimal_gear_K_lower':1,'near_optimal_gear_K_upper':1},
        'final_max_cumulative_gain':max(a['rounds'][-1]['cumulative_normalized_gain']),
        'final_max_vs_fixed_scale':float(np.max(np.array(a['rounds'][-1]['metrics']['optimum'])/scale-1)),
        'empirical_integrated_headroom_upper_on_updates':int(np.floor(np.mean((cap-np.array(a['confirmed_initial_utility']))/scale)/(.01*.125))),
        'abstract_result_not_native':'5-round exact class in ABSTRACT_JOINT_CLASS_CHECKS; never added to nativeprefix or coverage'}
    atomic_json(out/'FINAL_SUMMARY.json',summary);print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
