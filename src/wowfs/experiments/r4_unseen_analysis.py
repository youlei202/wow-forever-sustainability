"""Independent-pool predictions and exact finite one-configuration continuation."""
from __future__ import annotations
import itertools,json
from functools import lru_cache
import numpy as np
from wowfs.paths import setup_paths,atomic_json
from wowfs.experiments.r2_sequence_analysis import write_csv
from wowfs.experiments.r4_data import load_ecologies,advance_state
from wowfs.experiments.r4_feasibility import eval_all_safe,evaluate_admission
from wowfs.experiments.r4_batches import solve_problem

def exact_continuation(e,selected,futures):
    release=selected['release'];p,ix=e.problem(release,archive=e.initial_archive());mask=p.protected.copy();mask[p.gear_ids.index(selected['gear_id'])]=True
    first=evaluate_admission(p,mask);old,archive,registry=advance_state(e,ix,mask,e.initial,e.initial_archive(),e.protected_sources)
    if not first['joint_pass']:
        return {'first':first,'valid_initial_state':False,'Psi':None,'reason':'Independently reestimated current action failed; no valid conditional comparison.'}
    # Every archived vector is represented by some retained H policy profile.
    for t,a in enumerate(archive):
        ref=e.behavior[old,:,t].reshape(-1,7)
        if np.any(np.min(np.max(np.abs(np.asarray(a)[:,None,:]-ref[None,:,:]),axis=-1),axis=1)>1e-12):raise AssertionError('History archive not contained in H')
    def key(mask):return tuple(np.flatnonzero(mask).tolist())
    @lru_cache(None)
    def actions(old_indices,registered,released,item):
        protected=np.zeros(len(e.gear_ids),bool);protected[list(old_indices)]=True
        pp,indices=e.problem([item],protected=protected,old_released=released,protected_sources=registered)
        output=[]
        for j in np.flatnonzero(pp.safe&~pp.protected):
            chosen=pp.protected.copy();chosen[j]=True;m=evaluate_admission(pp,chosen)
            if not m['joint_pass']:continue
            new=protected.copy();new[indices[j]]=True
            reg=tuple(sorted(set(registered)|{s for s,mass in m['source_masses'].items()if mass>=.05-1e-9}))
            output.append((key(new),reg))
        return tuple(output)
    @lru_cache(None)
    def length(old_indices,registered,released,sequence):
        if not sequence:return 0
        choices=actions(old_indices,registered,released,sequence[0])
        if not choices:return 0
        next_released=tuple(sorted(set(released)|{sequence[0]}))
        return 1+max(length(new,reg,next_released,sequence[1:])for new,reg in choices)
    paths=[]
    for seq in itertools.permutations(futures):
        paths.append({'future_sequence':list(seq),'maximum_successful_length':length(key(old),registry,tuple(sorted(release)),seq)})
    return {'first':first,'valid_initial_state':True,'Psi':{str(h):sum(p['maximum_successful_length']>=h for p in paths)/len(paths)for h in [1,3,5]},
        'Q_sequences':len(paths),'paths':paths,'state_sequence_problems':length.cache_info().currsize,
        'distinct_state_arrival_problems':actions.cache_info().currsize,'archive_redundancy_verified':True,
        'allowed_actions':'All individually qualified H plus one currently-new gear admissions; exactly enumerated. More-than-one-gear subset actions excluded.',
        'scope':'Existential offline finite Psi for this explicit action library and uniform permutation Q; no online access or universal capacity claim.'}

def main():
    root=setup_paths();out=root/'artifacts/r4-foundational-discovery';run=root/'runs/r4-foundational-discovery/unseen-future-v1'
    anchors=json.loads((out/'UNSEEN_FROZEN_ANCHORS.json').read_text());selections=json.loads((out/'UNSEEN_CURRENT_BRANCH_SELECTION.json').read_text())
    ecologies=load_ecologies(run,run/'CONFIG.yaml');rows=[];details=[];branches=[];single_gear=[]
    for e in ecologies:
        anchor=anchors[e.pool['id']+'__'+e.race];e.scale=np.array(anchor['scale']);e.cap=np.array(anchor['cap']);e.protected_sources=tuple(anchor['protected_sources'])
        pair=['18203','19951']if e.pool['id']=='unseen_resource_cost'else['18203','19019']
        for release in [[pair[0]],[pair[1]],pair]:
            p,ix=e.problem(release,archive=e.initial_archive());full=eval_all_safe(p);rr=solve_problem(p,30)
            rows.append({'ecology':e.pool['id'],'race':e.race,'release_items':release,'subset_feasible':rr['feasible'],'status':rr['status'],
                'all_safe_joint':full['joint_pass'],'all_safe_failures':full['failure_reasons'],'worst_L':full['worst_protected_source_mass'],
                'K':full['K'],'initial_fixed_cap_violations':int(np.sum(np.max(e.values[e.initial],axis=(0,1))>e.cap))})
            details.append({'ecology':e.pool['id'],'race':e.race,'release':release,'all_safe':full,'subset':rr})
            if len(release)==2:
                for j in np.flatnonzero(p.safe&~p.protected):
                    mask=p.protected.copy();mask[j]=True;m=evaluate_admission(p,mask)
                    if m['joint_pass']:
                        single_gear.append({'ecology':e.pool['id'],'race':e.race,'gear_id':p.gear_ids[j],'release':release,'metrics':m,
                            'min_cap_slack_DPS':float(np.min(p.cap-p.best[mask].max(axis=0))),
                            'max_competitive_D':float(np.max(p.distances[j][p.values[j]>=p.best[mask].max(axis=0)-.05*e.scale]))})
        if e.pool['id']=='unseen_resource_cost':
            selection=next(s for s in selections if s['race']==e.race)
            if selection['status']!='no_pair':
                result={'race':e.race,'selection_status':selection['status'],'frozen_current_distance':selection['distance'],'future_items':selection['future_items'],
                    'branches':[exact_continuation(e,a,selection['future_items'])for a in selection['selected']]}
                branches.append(result);atomic_json(out/'UNSEEN_BRANCH_RESULTS.partial.json',branches)
    write_csv(out/'UNSEEN_RELEASE_RESULTS.csv',rows)
    atomic_json(out/'UNSEEN_PREDICTION_RESULTS.json',{'releases':details,'constructive_one_gear_certificates':single_gear,'branches':branches})
    print(json.dumps({'releases':rows,'certificates':[{k:x[k]for k in ['ecology','race','gear_id','min_cap_slack_DPS','max_competitive_D']}for x in single_gear],
        'branches':[{'race':x['race'],'selection_status':x['selection_status'],'Psi':[b['Psi']for b in x['branches']],'valid':[b['valid_initial_state']for b in x['branches']]}for x in branches]},indent=2))

if __name__=='__main__':main()
