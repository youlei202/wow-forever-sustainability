"""Paired interventions on the identical complete native coequipment table."""
import json
from itertools import product
import numpy as np
from wowfs.paths import setup_paths,atomic_json
from wowfs.experiments.value_construct import TASKS,POLICIES,coefficients,catalogue
from wowfs.experiments.r4_feasibility import FiniteProblem
from wowfs.experiments.value_admission import decision_metrics
from wowfs.experiments.value_affine import behavior_numerators
from wowfs.experiments.r2_sequence_analysis import write_csv


def contrasts(values,behavior,design,phase):
    mh,oh=design['final_mh'],design['final_oh'];pairs=list(product(range(len(mh)),range(len(oh))))
    pair_index={ij:k for k,ij in enumerate(pairs)};scale=np.array(design['protocol']['scale']);cap=1.05*scale
    old=set(product(range(2),repeat=2));rows=[]
    for step,record in enumerate(design['rounds'],start=1):
        if record['status']!='model_joint_pass':break
        present=set(product(range(step+2),repeat=2));new={f'MH{step+1}',f'OH{step+1}'}
        ix=[pair_index[ij] for ij in sorted(present) if ij in old or max(ij)==step+1]
        pp=[pairs[i] for i in ix];protected=np.array([ij in old for ij in pp]);src=[(f'MH{i}',f'OH{j}') for i,j in pp]
        p=FiniteProblem(values[ix],behavior[ix],src,protected,new,
              [f'{slot}{i}' for slot in ('MH','OH') for i in range(step+1)],scale,cap)
        frozen=set(map(tuple,record['admitted_pairs']));frozen_mask=np.array([ij in frozen for ij in pp])
        for method,mask in [('component_cap_completion',frozen_mask),('same_four_features_generic_24_rows',frozen_mask)]:
            m=decision_metrics(p,mask)
            rows.append({'phase':phase,'round':step,'contrast':'admission','method':method,
                'candidate_items':2,'physically_legal_crosses':len(present),'admitted':int(mask.sum()),
                'rules':0 if method=='unrestricted_natural' else 24,'feature_dimensions':4,'exceptions':0,
                'fixed_rule':method!='unrestricted_natural',**m})
        natural_pairs=sorted(present);natural_ix=[pair_index[ij] for ij in natural_pairs]
        natural_p=FiniteProblem(values[natural_ix],behavior[natural_ix],
            [(f'MH{i}',f'OH{j}') for i,j in natural_pairs],
            np.array([max(ij)<step+1 for ij in natural_pairs]),new,p.protected_sources,scale,cap)
        rows.append({'phase':phase,'round':step,'contrast':'admission','method':'unrestricted_natural',
            'candidate_items':2,'physically_legal_crosses':len(present),'admitted':len(present),
            'rules':0,'feature_dimensions':4,'exceptions':0,
            'history_scope':'Counterfactual fully open sequence including prior unsafe crosses; failures do not reset.',
            **decision_metrics(natural_p,np.ones(len(natural_ix),bool))})
        # A stable demand repeats the same actual sustained task eight times.
        stable=FiniteProblem(np.repeat(values[ix,:,0:1],8,axis=2),np.repeat(behavior[ix,:,0:1],8,axis=2),src,protected,new,
            p.protected_sources,np.repeat(scale[0],8),np.repeat(cap[0],8))
        m=decision_metrics(stable,frozen_mask)
        rows.append({'phase':phase,'round':step,'contrast':'demand','method':'eight_copies_of_sustained_same_physical_candidates_and_admission',**m})
        full=decision_metrics(p,frozen_mask)
        for item in sorted(new):
            # Counterfactual publication omits the other current new source;
            # the historical library is kept entirely, as are all old policies.
            without_other=frozen_mask & np.array([not bool((new-{item})&set(s)) for s in src])
            singleton_domain=np.array([not bool((new-{item})&set(s)) for s in src])
            sp=FiniteProblem(p.values[singleton_domain],p.behavior[singleton_domain],
                [s for s,keep in zip(src,singleton_domain) if keep],protected[singleton_domain],
                [item],p.protected_sources,scale,cap)
            single_metrics=decision_metrics(sp,without_other[singleton_domain])
            rows.append({'phase':phase,'round':step,'contrast':'single_vs_batch','method':'singleton_'+item,
                **single_metrics,
                'historical_gear_retained':int(protected.sum())})
        # The no-positive-interaction check concerns fixed policies, not maxima.
        for task_i,task in enumerate(TASKS):
            for policy_i,policy in enumerate(POLICIES):
                a,b=step+1,step+1
                four=[values[pair_index[ij],policy_i,task_i] for ij in ((0,0),(a,0),(0,b),(a,b))]
                interaction=four[3]-four[2]-four[1]+four[0]
                rows.append({'phase':phase,'round':step,'contrast':'fixed_policy_factorial','method':'four_component_cells',
                    'task':task,'policy':policy,'old_old':four[0],'new_mh_old_oh':four[1],
                    'old_mh_new_oh':four[2],'new_new':four[3],'physical_interaction_dps':float(interaction),
                    'fixed_cap':float(cap[task_i]),'complete_old_library_optimum':full['old_reoptimized_utility'][task_i],
                    'complete_new_library_optimum':full['optimum'][task_i]})
        old=frozen
    return rows


def main():
    root=setup_paths();out=root/'artifacts/decisive-value';d=json.loads((out/'CONSTRUCTIVE_SEARCH.json').read_text())
    _,_,u,b=catalogue(d['final_mh'],d['final_oh'],coefficients());rows=contrasts(u,b,d,'development_prediction')
    predicted=rows.copy()
    run=root/'runs/decisive-value/native-confirmation-v1/RESULTS.json'
    if run.exists():
        data=json.loads(run.read_text());assert not data['errors']
        u=np.full((len(d['final_mh'])*len(d['final_oh']),3,8),np.nan)
        b=np.full((*u.shape,7),np.nan)
        durations=dict(zip(TASKS,[180,30,90,180,10,360,60,180]))
        for r in data['rows']:
            i=int(r['mh_source_id'][2:])*len(d['final_oh'])+int(r['oh_source_id'][2:])
            p=POLICIES.index(r['strategy']);t=TASKS.index(r['task'])
            if np.isfinite(u[i,p,t]):raise ValueError('Duplicate physical response')
            u[i,p,t]=np.mean(r['dps_samples']);bn=behavior_numerators(r,durations[r['task']])
            b[i,p,t,:5]=bn[:5]/bn[:5].sum();b[i,p,t,5]=bn[5]/20;b[i,p,t,6]=bn[6]/bn[5]
        if not np.isfinite(u).all() or not np.isfinite(b).all():raise ValueError('Incomplete full-cross table')
        confirmed=contrasts(u,b,d,'independent_native_confirmation');rows+=confirmed
        atomic_json(out/'PROSPECTIVE_STRUCTURAL_CONFIRMATION.json',confirmed)
    atomic_json(out/'PROSPECTIVE_STRUCTURAL_PREDICTIONS.json',predicted)
    write_csv(out/'STRUCTURAL_CONTRASTS.csv',rows)
    print(json.dumps({'rows':len(rows),'max_fixed_policy_interaction':max(abs(r['physical_interaction_dps']) for r in rows if 'physical_interaction_dps'in r),
        'main_comparisons':[{k:r[k] for k in ('round','method','P','G','D') if k in r} for r in rows if r['contrast']!='fixed_policy_factorial']}),flush=True)

if __name__=='__main__':main()
