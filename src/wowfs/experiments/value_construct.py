"""Prospective complete-cross reward construction from frozen primitive native responses.

Search is development and counts every rejected proposal; no native outcome of
proposed rewards is queried. All old configurations and source labels persist.
"""
import argparse
from itertools import product
import json
from pathlib import Path
import numpy as np
from scipy.stats import qmc
from scipy.spatial import cKDTree
from wowfs.paths import setup_paths,atomic_json
from wowfs.experiments.value_affine import load_models,OLD_MH,OLD_OH,BOUNDS
from wowfs.experiments.r4_feasibility import FiniteProblem,evaluate_admission
from wowfs.experiments.value_admission import decision_metrics
from wowfs.experiments.r2_native import file_hash

TASKS=['sustained','short_burst','four_target','high_armor','burst_10s','endurance_360s','two_target_60s','resource_pressure']
POLICIES=['native_no_reck','native_reck','rage_conserve']

def coefficients():
    m=load_models()
    return (np.array([[m['RaceHuman',t,p]['dps_coefficients'] for t in TASKS] for p in POLICIES]),
            np.array([[m['RaceHuman',t,p]['behavior_numerator_coefficients'] for t in TASKS] for p in POLICIES]))

def predict(theta,coefs):
    theta=np.asarray(theta);x=np.concatenate([np.ones(theta.shape[:-1]+(1,)),theta],axis=-1)
    u=np.einsum('...d,ptd->...pt',x,coefs[0]);num=np.einsum('...d,ptdf->...ptf',x,coefs[1])
    b=num.copy();b[...,:5]/=num[...,:5].sum(axis=-1,keepdims=True)
    b[...,5]/=20;b[...,6]=np.divide(num[...,6],num[...,5],out=np.zeros_like(num[...,6]),where=num[...,5]!=0)
    return u,b

def catalogue(mh,oh,coefs):
    pairs=list(product(range(len(mh)),range(len(oh))))
    theta=[[*mh[i],*oh[j]] for i,j in pairs]
    u,b=predict(theta,coefs)
    return pairs,np.asarray(theta),u,b

def make_problem(mh,oh,previous_pairs,scale,coefs,new_sources):
    pairs,theta,u,b=catalogue(mh,oh,coefs)
    # Unadmitted older crosses remain outside this rule's feasible history;
    # every newly possible physical cross is considered, even if cap-unsafe.
    ix=[k for k,(i,j) in enumerate(pairs) if (i,j) in previous_pairs or f'MH{i}' in new_sources or f'OH{j}' in new_sources]
    pairs=[pairs[k] for k in ix]
    p=FiniteProblem(u[ix],b[ix],[(f'MH{i}',f'OH{j}') for i,j in pairs],
        np.array([ij in previous_pairs for ij in pairs]),new_sources,
        [f'MH{i}' for i in range(len(mh)-(int(f'MH{len(mh)-1}' in new_sources)))] +
        [f'OH{i}' for i in range(len(oh)-(int(f'OH{len(oh)-1}' in new_sources)))],
        scale,1.05*scale,gear_ids=[f'MH{i}_OH{j}' for i,j in pairs])
    return p,pairs,theta[ix]

def search(seed=8439,power=17,max_rounds=3,run_name='construction-search-v1'):
    root=setup_paths();run=root/'runs/decisive-value'/run_name;run.mkdir(parents=True,exist_ok=False)
    coefs=coefficients();mh=list(map(list,OLD_MH));oh=list(map(list,OLD_OH));pairs,theta,u,b=catalogue(mh,oh,coefs)
    scale=u.max(axis=(0,1));history=set(pairs)
    protocol={'phase':'development_model_search_no_new_reward_native_calls','source_sha256':file_hash(Path(__file__)),
        'model_sha256':file_hash(root/'artifacts/decisive-value/FOUR_AXIS_CALIBRATION.json'),
        'seed':seed,'proposals_per_round':2**power,'max_rounds':max_rounds,'gain_threshold':.01,'delta':.05,
        'design_guards':{'gain_min':.012,'cap_max':1.045,'novel_distance_min':.055},
        'admission_rule':'Fixed24 affine task-policy inequalities u_hat(theta)<=1.05*s; all legal crossproducts tested, no blacklists.',
        'tasks':TASKS,'policies':POLICIES,'scale':scale.tolist(),'cap':(scale*1.05).tolist(),
        'initial_mh':[x.copy() for x in mh],'initial_oh':[x.copy() for x in oh],'physical_parameter_bounds':BOUNDS,
        'selection':'Among all guarded joint feasible proposals minimize maximum cumulative normalized growth, then maximize novelty margin. Every round proposes one component in each slot.'}
    atomic_json(run/'PROTOCOL.json',protocol);rounds=[]
    for step in range(1,max_rounds+1):
        pairs,_,uv,bv=catalogue(mh,oh,coefs);oldmask=np.array([ij in history for ij in pairs]);baseline=uv[oldmask].max(axis=(0,1));ref=bv[oldmask]
        trees=[cKDTree(ref[:,:,k].reshape(-1,7)) for k in range(8)]
        candidate=qmc.Sobol(4,scramble=True,seed=seed+step).random_base2(power)
        bounds=np.array(BOUNDS);candidate=qmc.scale(candidate,bounds[:,0],bounds[:,1]);best=None
        counts={'proposed':len(candidate),'gain_guard':0,'D_guard':0,'strict_joint':0};attempts=[]
        for start in range(0,len(candidate),1024):
            c=candidate[start:start+1024];n=len(c)
            crosses=np.stack([np.c_[c[:,:2],np.tile(v,(n,1))] for v in oh]+[np.c_[np.tile(v,(n,1)),c[:,2:]] for v in mh]+[c],axis=1)
            val,beh=predict(crosses,coefs);gbest=val.max(axis=2);safe=np.all(gbest<=1.05*scale,axis=-1)
            opt=np.maximum(np.max(np.where(safe[:,:,None],gbest,-np.inf),axis=1),baseline)
            gains=(opt-baseline)/scale;cum=(opt-scale)/scale
            use=safe & np.all(gbest<=1.045*scale,axis=-1)
            eligible=(gains.max(axis=1)>=.012)&(cum.max(axis=1)<=.045)
            indices=np.flatnonzero(eligible);counts['gain_guard']+=len(indices)
            if not len(indices):continue
            subbeh=beh[indices];dist=np.zeros(subbeh.shape[:-1])
            for t,tree in enumerate(trees):dist[...,t]=tree.query(subbeh[:,:,:,t].reshape(-1,7),p=np.inf)[0].reshape(len(indices),crosses.shape[1],3)
            comp=val[indices]>=opt[indices,None,None,:]-.05*scale
            novel=np.max(np.where(comp & use[indices,:,None,None],dist,-np.inf),axis=(1,2,3))
            for loc in np.flatnonzero(novel>=.055):
                ci=indices[loc];counts['D_guard']+=1;th=c[ci]
                nmh=mh+[th[:2].tolist()];noh=oh+[th[2:].tolist()]
                p,pp,tt=make_problem(nmh,noh,history,scale,coefs,[f'MH{len(mh)}',f'OH{len(oh)}'])
                met=decision_metrics(p,p.safe)
                if not met['all_seven_pass']:continue
                counts['strict_joint']+=1
                score=(float(cum[ci].max()),-float(novel[loc]))
                if best is None or score<best[0]:best=(score,th,met,pp,p.safe,tt,novel[loc],start+ci)
        if best is None:
            rounds.append({'round':step,'counts':counts,'status':'search_no_guarded_joint_candidate'});break
        _,th,met,pp,safe,tt,novel,index=best
        mh.append(th[:2].tolist());oh.append(th[2:].tolist());history={ij for ij,s in zip(pp,safe) if s}
        row={'round':step,'status':'model_joint_pass','counts':counts,'selected_proposal_index':int(index),'theta':th.tolist(),
            'mh':mh.copy(),'oh':oh.copy(),'admitted_pairs':[list(ij) for ij in sorted(history)],'metrics':met,
            'max_competitive_novel_distance':float(novel),'physical_cross_count':len(mh)*len(oh)}
        rounds.append(row);atomic_json(run/'CHECKPOINT.json',{'protocol':protocol,'rounds':rounds})
        print(json.dumps({'round':step,'counts':counts,'theta':th.tolist(),'gain':met['normalized_gain'],'K':met['K'],'D':novel}),flush=True)
    result={'protocol':protocol,'rounds':rounds,'final_mh':mh,'final_oh':oh,'confirmed_native':False}
    atomic_json(run/'RESULTS.json',result);atomic_json(root/'artifacts/decisive-value/CONSTRUCTIVE_SEARCH.json',result)
    return result

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--seed',type=int,default=8439);a.add_argument('--power',type=int,default=17);a.add_argument('--rounds',type=int,default=3);a.add_argument('--run',default='construction-search-v1');x=a.parse_args();search(x.seed,x.power,x.rounds,x.run)
