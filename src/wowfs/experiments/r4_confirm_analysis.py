"""Fresh native confirmation; preserve discovery numerical anchors explicitly."""
from __future__ import annotations
import json
from itertools import combinations
import numpy as np
from wowfs.paths import setup_paths,atomic_json
from wowfs.experiments.r2_sequence_analysis import write_csv
from wowfs.experiments.r4_data import load_ecologies,advance_state
from wowfs.experiments.r4_batches import solve_problem
from wowfs.experiments.r4_feasibility import eval_all_safe,evaluate_admission

def anchored_ecologies():
    root=setup_paths();baseline={(e.pool['id'],e.race):e for e in load_ecologies(root/'runs/r4-foundational-discovery/baseline-v1')}
    fresh=load_ecologies(root/'runs/r4-foundational-discovery/confirmation-v1')
    for e in fresh:
        b=baseline[(e.pool['id'],e.race)];e.fresh_anchor=e.scale.copy()
        e.scale=b.scale.copy();e.cap=b.cap.copy();e.protected_sources=b.protected_sources
    return fresh

def main():
    root=setup_paths();out=root/'artifacts/r4-foundational-discovery';ecologies=anchored_ecologies();rows=[];details=[];certificates=[]
    selected={'resource_haste':'331790c18dd3a920','timing_shared':'26007bac9b64ca50'}
    for e in ecologies:
        for size in range(1,len(e.new_items)+1):
            for release in combinations(e.new_items,size):
                p,ix=e.problem(release,archive=e.initial_archive());result=solve_problem(p,30);full=eval_all_safe(p)
                rows.append({'ecology':e.pool['id'],'race':e.race,'release_items':list(release),'release_size':size,
                    'feasible':result['feasible'],'proved_infeasible':result.get('proved_infeasible',False),'status':result['status'],
                    'all_safe':full['joint_pass'],'all_safe_failures':full['failure_reasons'],'K':full['K'],
                    'D_mass':full['novel_task_mass'],'worst_L':full['worst_protected_source_mass'],
                    'fresh_anchor_to_frozen_ratio':(e.fresh_anchor/e.scale).tolist(),'iterations':e.samples.shape[-1]})
                details.append({'ecology':e.pool['id'],'race':e.race,'release':list(release),'subset':result,'all_safe':full})
                if len(release)==2 and e.pool['id']in selected:
                    gid=selected[e.pool['id']];j=p.gear_ids.index(gid);mask=p.protected.copy();mask[j]=True;m=evaluate_admission(p,mask)
                    floor=p.best[mask].max(axis=0);witness=[]
                    for policy in range(p.values.shape[1]):
                        for t,task in enumerate(e.tasks):
                            if p.distances[j,policy,t]>=.05 and p.values[j,policy,t]>=floor[t]-.05*e.scale[t]:
                                witness.append({'policy':e.policies[policy],'task':task['id'],'distance':p.distances[j,policy,t],
                                    'competitive_margin_DPS':p.values[j,policy,t]-floor[t]+.05*e.scale[t]})
                    certificates.append({'ecology':e.pool['id'],'race':e.race,'release':list(release),'gear_id':gid,'metrics':m,'witnesses':witness,
                                         'cap_slack_min_DPS':float(np.min(p.cap-p.best[mask].max(axis=0)))})
    branches=[]
    for e in ecologies:
        if e.pool['id']!='timing_extra':continue
        for gid in ['426712995313d7dc','b2a3b09c5d796149']:
            p,ix=e.problem(['19951'],archive=e.initial_archive());j=p.gear_ids.index(gid);mask=p.protected.copy();mask[j]=True
            m=evaluate_admission(p,mask);old,archive,registry=advance_state(e,ix,mask,e.initial,e.initial_archive(),e.protected_sources)
            futures=[]
            for item in ['18203','22321']:
                pp,ii=e.problem([item],protected=old,old_released=['19951'],archive=archive,protected_sources=registry)
                rr=solve_problem(pp,30);ff=eval_all_safe(pp)
                futures.append({'new_item':item,'all_safe':ff,'subset':rr})
            branches.append({'race':e.race,'first_gear':gid,'first_joint':m['joint_pass'],'first_metrics':m,'future':futures,
                             'conditional_state_valid':m['joint_pass'],'archive_count':sum(map(len,archive))})
    write_csv(out/'FRESH_RELEASE_CONFIRMATION.csv',rows)
    atomic_json(out/'FRESH_CONFIRMATION_RESULTS.json',{'release_details':details,'one_gear_certificates':certificates,'branches':branches,
        'scope':'Frozen discovery numerical cap/scale and source obligations; fresh512seed mean values and behavior summaries. No behavior population-confidence assertion.'})
    print(json.dumps({'releases':len(rows),'certificates':[{k:x[k]for k in ['ecology','race','witnesses','cap_slack_min_DPS']}|{'joint':x['metrics']['joint_pass'],'failures':x['metrics']['failure_reasons']}for x in certificates],
        'F':[{k:b[k]for k in ['race','first_gear','first_joint','archive_count']}|{'future':[(f['new_item'],f['all_safe']['failure_reasons'],f['subset']['feasible'])for f in b['future']]}for b in branches]},indent=2))

if __name__=='__main__':main()
