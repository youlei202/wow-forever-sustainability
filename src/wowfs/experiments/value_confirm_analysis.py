"""Analyze the single frozen native confirmation without changing its masks."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from scipy.stats import t
from wowfs.paths import setup_paths, atomic_json
from wowfs.experiments.r2_native import file_hash
from wowfs.experiments.r2_sequence_analysis import behavior_vector
from wowfs.experiments.r4_feasibility import FiniteProblem
from wowfs.experiments.value_admission import decision_metrics


def paired_frontier_bounds(new,old,critical):
    """Simultaneous pair-difference intervals propagated through max/min.

    new/old are action×task×seed. max_j min_i(mu_new_j-mu_old_i)
    equals the fully reoptimized frontier difference; no old BIS is fixed.
    """
    n=new.shape[-1];lower=[];upper=[]
    for q in range(new.shape[1]):
        x,y=new[:,q],old[:,q]
        mx,my=x.mean(axis=1),y.mean(axis=1)
        cx,cy=x-mx[:,None],y-my[:,None]
        vx=(cx*cx).sum(axis=1)/(n-1);vy=(cy*cy).sum(axis=1)/(n-1)
        cov=cx@cy.T/(n-1)
        se=np.sqrt(np.maximum(0.,vx[:,None]+vy[None,:]-2*cov)/n)
        difference=mx[:,None]-my[None,:]
        lower.append(float((difference-critical*se).min(axis=1).max()))
        upper.append(float((difference+critical*se).min(axis=1).max()))
    return np.array(lower),np.array(upper)


def analyze(run_id='native-confirmation-v1'):
    root=setup_paths();run=root/'runs/decisive-value'/run_id
    if json.loads((run/'PROGRESS.json').read_text())['status']!='complete':
        raise ValueError('Confirmation native physics is not complete')
    design=json.loads((run/'inputs/frozen_catalog.json').read_text())
    cal=json.loads((run/'inputs/four_axis_calibration.json').read_text())
    result=json.loads((run/'RESULTS.json').read_text())
    if result['errors'] or any(r is None for r in result['rows']):raise ValueError('Missing native cells cannot be filled')
    tasks=cal['protocol']['tasks'];task_ids=[x['id'] for x in tasks]
    policies=[x['id'] for x in cal['protocol']['strategies']]
    gears=design['full_cross'];gear_ids=[g['gear_id'] for g in gears]
    sources=[{g['mh_source_id'],g['oh_source_id']} for g in gears]
    initial=np.array([s<=set(design['initial_source_ids']) for s in sources])
    scale=np.asarray(design['fixed_scale']);cap=np.asarray(design['fixed_caps'])
    lookup={(r['gear_id'],r['strategy'],r['task']):r for r in result['rows']}
    shape=(len(gears),len(policies),len(tasks));samples=np.empty((*shape,1024));behavior=np.empty((*shape,7))
    for gi,gid in enumerate(gear_ids):
        for pi,policy in enumerate(policies):
            for qi,task in enumerate(tasks):
                row=lookup[gid,policy,task['id']]
                if len(row['dps_samples'])!=1024:raise ValueError('Confirmation sample size changed')
                samples[gi,pi,qi]=row['dps_samples']
                behavior[gi,pi,qi]=behavior_vector(row,task['duration_seconds'])
    values=samples.mean(axis=-1);initial_value=values[initial].max(axis=(0,1))
    steps=design['sequences'][0]['steps'];history=initial.copy();registry=set(design['initial_source_ids'])
    records=[];pair_count=0
    for step in steps:
        admitted=np.array([g in set(step['admitted_gear_ids']) for g in gear_ids])
        if not np.all(admitted[history]):raise ValueError('Frozen history was removed')
        released=set(step['released_source_ids']);available=registry|released
        domain=history|np.array([bool(s&released) and s<=available for s in sources])
        ids=np.flatnonzero(domain)
        p=FiniteProblem(values=values[domain],behavior=behavior[domain],
            sources=[sources[i] for i in ids],protected=history[domain],new_sources=released,
            protected_sources=registry,scale=scale,cap=cap,gear_ids=[gear_ids[i] for i in ids])
        old=values[history].max(axis=(0,1));metrics=decision_metrics(p,admitted[domain],old)
        deletion={}
        for source in sorted(available):
            without=admitted&np.array([source not in s for s in sources])
            if without.any():
                v=values[without].max(axis=(0,1))
                deletion[source]={'utility_without_source':v.tolist(),
                    'normalized_frontier_loss':((np.asarray(metrics['optimum'])-v)/scale).tolist()}
        record={'round':step['step'],'released_sources':sorted(released),
            'before_gear_ids':[gear_ids[i] for i in np.flatnonzero(history)],
            'admitted_gear_ids':step['admitted_gear_ids'],'metrics':metrics,
            'all_source_deletions':deletion,
            'cumulative_normalized_gain':((np.asarray(metrics['optimum'])-initial_value)/scale).tolist(),
            'minimum_normalized_cap_margin':float(np.min((cap-np.asarray(metrics['optimum']))/scale)),
            'historical_registry_before':sorted(registry),'K_finite_table_lower':metrics['K'],'K_finite_table_upper':metrics['K'],
            'new_source_gain_necessity':{s:max(metrics['source_deletion'][s]['normalized_loss']) for s in sorted(released)},
            'gain_mass_curve':{str(v):float(np.mean(np.asarray(metrics['normalized_gain'])>=v)) for v in [0,.005,.01,.02,.03]},
            'behavior_inference':'Original seven empirical mean features; no sampling-confidence certificate for D is asserted.'}
        pair_count+=int(admitted.sum()*history.sum()*len(policies)**2*len(tasks))
        records.append((record,history.copy(),admitted.copy()))
        history=admitted;registry.update(released)
    inference=design['confirmation_inference'];alpha=inference['alpha'];n=samples.shape[-1]
    pair_critical=float(t.ppf(1-alpha/(2*pair_count),n-1))
    cell_critical=float(t.ppf(1-alpha/(2*np.prod(shape)),n-1))
    cell_upper=values+cell_critical*samples.std(axis=-1,ddof=1)/np.sqrt(n)
    rng=np.random.default_rng(inference['bootstrap_seed']);b=inference['paired_bootstrap_replicates']
    flat=samples.reshape(-1,n);bootstrap=np.empty((b,*shape))
    for start in range(0,b,100):
        stop=min(start+100,b)
        weights=rng.multinomial(n,np.full(n,1/n),size=stop-start)/n
        bootstrap[start:stop]=(weights@flat.T).reshape(stop-start,*shape)
    boot_gains=[];point_gains=[]
    for record,old_mask,new_mask in records:
        new=samples[new_mask].reshape(-1,len(tasks),n)
        old=samples[old_mask].reshape(-1,len(tasks),n)
        lower,upper=paired_frontier_bounds(new,old,pair_critical)
        gain=(bootstrap[:,new_mask].max(axis=(1,2))-bootstrap[:,old_mask].max(axis=(1,2)))/scale
        point=np.asarray(record['metrics']['normalized_gain']);boot_gains.append(gain);point_gains.append(point)
        record['approx_simultaneous_paired_t_gain_lower']=(lower/scale).tolist()
        record['approx_simultaneous_paired_t_gain_upper']=(upper/scale).tolist()
        record['approx_simultaneous_paired_t_gain_pass']=bool(np.mean(lower/scale>=.01)>=.125)
        record['paired_bootstrap_percentile_gain_lower']=np.quantile(gain,.025,axis=0).tolist()
        record['paired_bootstrap_percentile_gain_upper']=np.quantile(gain,.975,axis=0).tolist()
        record['paired_bootstrap_gain_mass_interval']=np.quantile(np.mean(gain>=.01,axis=1),[.025,.975]).tolist()
        record['approx_simultaneous_cell_t_power_upper']=cell_upper[new_mask].max(axis=(0,1)).tolist()
        record['approx_simultaneous_cell_t_power_pass']=bool(np.all(cell_upper[new_mask].max(axis=(0,1))<=cap))
    bootstrap_joint=np.stack(boot_gains,axis=1);points=np.stack(point_gains)
    simultaneous_radius=float(np.quantile(np.max(np.abs(bootstrap_joint-points[None]),axis=(1,2)),1-alpha))
    for record,_,_ in records:
        point=np.asarray(record['metrics']['normalized_gain'])
        record['paired_bootstrap_simultaneous_gain_lower']=(point-simultaneous_radius).tolist()
        record['paired_bootstrap_simultaneous_gain_upper']=(point+simultaneous_radius).tolist()
        record['paired_bootstrap_simultaneous_gain_pass']=bool(np.mean(point-simultaneous_radius>=.01)>=.125)
    predictions=json.loads((run/'inputs/frozen_predictions.json').read_text())['rows']
    errors=[abs(lookup[r['gear_id'],r['strategy'],r['task']]['dps_mean']-r['predicted_utility']) for r in predictions]
    strict=[r['metrics']['all_seven_pass'] for r,_,_ in records]
    prefix=next((i for i,v in enumerate(strict) if not v),len(strict))
    document={'schema':1,'run':str(run),'design_sha256':file_hash(run/'inputs/frozen_catalog.json'),
        'results_sha256':file_hash(run/'RESULTS.json'),'analysis_source_sha256':file_hash(Path(__file__)),
        'native_cells':len(result['rows']),'physical_battles':len(result['rows'])*n,
        'source_aliases':design['source_catalog'],'tasks':task_ids,'policies':policies,
        'fixed_scale':scale.tolist(),'fixed_cap':cap.tolist(),'confirmed_initial_utility':initial_value.tolist(),
        'empirical_joint_passes':sum(strict),'rounds_attempted':len(strict),'successful_prefix':prefix,
        'full_crosses':len(gears),'full_cross_empirical_unsafe_gears':[gear_ids[i] for i in np.flatnonzero(np.any(values.max(axis=1)>cap,axis=1))],
        'max_absolute_development_mean_prediction_error':max(errors),
        'statistical_scope':'One independent frozen finite-domain confirmation. Empirical P/N/D/L/H/C/G are not a population joint certificate. Student-t and bootstrap bounds are approximate; no distribution-free guarantee.',
        'gain_interval_construction':'Complete old and new maximization retained in every bootstrap replicate; paired t bounds cover all selected new-minus-old action means before max/min propagation.',
        'paired_difference_family_size':pair_count,'paired_t_critical':pair_critical,
        'power_cell_family_size':int(np.prod(shape)),'power_t_critical':cell_critical,
        'paired_bootstrap_replicates':b,'paired_bootstrap_seed':inference['bootstrap_seed'],
        'bootstrap_joint_gain_radius':simultaneous_radius,'bootstrap_family':'All3rounds×8tasks, allgear/policy means resampled as a shared-seed bundle.',
        'admission_and_sequence':'The pre-test masks, caps, thresholds, source identities, and sequence are unchanged regardless of the outcomes.',
        'rounds':[r for r,_,_ in records]}
    out=root/'artifacts/decisive-value';atomic_json(out/'PROSPECTIVE_CONFIRMATION.json',document)
    atomic_json(run/'PROSPECTIVE_CONFIRMATION.json',document)
    rows=[]
    for record,_,_ in records:
        m=record['metrics']
        for q,task in enumerate(task_ids):
            rows.append({'round':record['round'],'task':task,
                **{k:m[k] for k in ['P','N','D','L','H','C','G','all_seven_pass','K']},
                'old_reoptimized':m['old_reoptimized_utility'][q],'new_reoptimized':m['optimum'][q],
                'fixed_cap':cap[q],'gain_normalized':m['normalized_gain'][q],
                'paired_t_gain_lower':record['approx_simultaneous_paired_t_gain_lower'][q],
                'paired_t_gain_upper':record['approx_simultaneous_paired_t_gain_upper'][q],
                'bootstrap_joint_gain_lower':record['paired_bootstrap_simultaneous_gain_lower'][q],
                'bootstrap_joint_gain_upper':record['paired_bootstrap_simultaneous_gain_upper'][q],
                'point_inference':'Empirical finite table; intervals approximate'})
    with (out/'PROSPECTIVE_CONFIRMATION.csv').open('w') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(json.dumps({'rounds_attempted':len(strict),'empirical_joint_passes':sum(strict),'successful_prefix':prefix,
        'rounds':[{'round':r['round'],'gain':r['metrics']['normalized_gain'],
            'failures':r['metrics']['failure_reasons'],'G':r['metrics']['G'],
            'paired_t_gain_pass':r['approx_simultaneous_paired_t_gain_pass'],
            'bootstrap_gain_pass':r['paired_bootstrap_simultaneous_gain_pass'],
            'power_ucb_pass':r['approx_simultaneous_cell_t_power_pass']} for r,_,_ in records]},indent=2),flush=True)
    return document


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run-id',default='native-confirmation-v1')
    args=parser.parse_args();analyze(args.run_id)
