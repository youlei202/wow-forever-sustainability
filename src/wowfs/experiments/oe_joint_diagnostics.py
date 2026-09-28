"""Measured two-slot and task-choice challenges, separate from value capacity."""
from __future__ import annotations
import argparse
from collections import defaultdict
import json
from pathlib import Path
import numpy as np
from wowfs.paths import atomic_json
from wowfs.experiments.oe_analysis import tensor,write_csv


def analyze(batch,worlds,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    groups=defaultdict(list)
    for row in json.loads((Path(batch)/'RESULTS.json').read_text())['rows']:
        if row is not None:groups[row['world_id']].append(row)
    joint=[];choices=[];policy=[]
    for w in worlds:
        if w['world_id'] not in groups:continue
        t=tensor(groups[w['world_id']]);a=t['means'];dims=t['dimensions']
        # This diagnostic requires complete physical data within the observed subdomain.
        if not t['complete']:continue
        u=a.max(axis=3);r0=dims[0].index('a00');x0=dims[1].index('x0')
        initial=[dims[1].index('x'+str(x)) for x in w['initial_partner_ids']]
        ref=u[r0,initial].max(axis=0)
        if w['model_scope']=='joint_two_update_slots':
            if len(initial)!=1:raise ValueError('This diagnostic requires one declared old option per slot')
            x0=initial[0]
            for i,cid in enumerate(dims[0]):
                if i==r0:continue
                for j,pid in enumerate(dims[1]):
                    if j==x0:continue
                    separate=(u[i,x0]+u[r0,j]-u[r0,x0])/ref
                    combined=u[i,j]/ref
                    one=u[i,x0]/ref;two=u[r0,j]/ref
                    for h in [.03,.05,.10]:
                        safe=bool(np.all(np.maximum(one,two)<=1+h))
                        actual_safe=bool(np.all(combined<=1+h))
                        forecast_safe=bool(np.all(separate<=1+h))
                        joint.append({'world_id':w['world_id'],'mechanism_id':w['mechanism_id'],
                            'parameter_scope':w['parameter_scope'],'candidate_id':cid,'partner_id':pid,'headroom':h,
                            'initial_partner_id':dims[1][x0],
                            'both_components_safe_alone':safe,'combined_safe':actual_safe,
                            'additive_forecast_safe':forecast_safe,'individual_only_check_misses_violation':safe and not actual_safe,
                            'additive_forecast_misses_violation':safe and forecast_safe and not actual_safe,
                            'first_slot_response':one.tolist(),'second_slot_response':two.tolist(),
                            'joint_response':combined.tolist(),'additive_forecast':separate.tolist(),
                            'nonseparable_residual':(combined-separate).tolist(),
                            'scope':'development means; all four legal old/new combinations retained; no source-retention or confidence certification yet'})
        for i,cid in enumerate(dims[0]):
            if i==r0:continue
            before=u[r0,initial].max(axis=0)
            # Fixed-partner H diagnostic only. Joint worlds require actual item activation.
            if w['model_scope']=='joint_two_update_slots':continue
            after=np.maximum(before,u[i,initial].max(axis=0))
            gains=(after-before)/ref
            for h in [.03,.05,.1]:
                if not np.all(after/ref<=1+h):continue
                flat=np.concatenate([a[r0,initial].transpose(0,2,1).reshape((-1,len(ref))),
                                     a[i,initial].transpose(0,2,1).reshape((-1,len(ref)))])
                near=flat>=after-.01*ref
                one_covers=bool(np.any(np.all(near,axis=1)))
                choices.append({'world_id':w['world_id'],'mechanism_id':w['mechanism_id'],
                    'candidate_id':cid,'parameter_scope':w['parameter_scope'],'headroom':h,
                    'gain_per_task':gains.tolist(),'maximum_task_gain':float(gains.max()),
                    'minimum_task_gain':float(gains.min()),'single_configuration_within_one_percent_all_tasks':one_covers,
                    'decision_diagnostic':bool(gains.max()>=.01 and not one_covers),
                    'scope':'development fixed-task useful-choice diagnostic; no claim of new behavior or unbounded novelty'})
        if len(dims[3])>1:
            old_best=a[r0,initial].max(axis=(0,2))
            for i,cid in enumerate(dims[0]):
                frontier_per_policy=a[i].max(axis=0)
                if np.any(np.ptp(frontier_per_policy,axis=1)>.005*old_best):
                    policy.append({'world_id':w['world_id'],'candidate_id':cid,
                        'policies':dims[3],'task_best_policy_indices':np.argmax(frontier_per_policy,axis=1).tolist(),
                        'frontier_by_task_policy':(frontier_per_policy/old_best[:,None]).tolist(),
                        'scope':'development; policy-induced mean choice variation, not a new policy algorithm'})
    for name,rows in [('JOINT_SLOT_CHALLENGES',joint),('TASK_CHOICE_DIAGNOSTICS',choices),('POLICY_DIAGNOSTICS',policy)]:
        atomic_json(output/(name+'.json'),rows);write_csv(output/(name+'.csv'),rows)
    summary={'joint_comparisons':len(joint),'individual_check_misses':sum(r['individual_only_check_misses_violation'] for r in joint),
        'additive_check_misses':sum(r['additive_forecast_misses_violation'] for r in joint),
        'task_choice_cases':sum(r['decision_diagnostic'] for r in choices),'policy_cases':len(policy),
        'inference':'all development means; comparisons across h are threshold sensitivity, not independent discoveries'}
    atomic_json(output/'SUMMARY.json',summary);return summary


def main():
    p=argparse.ArgumentParser();p.add_argument('--batch',required=True,type=Path)
    p.add_argument('--registry',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    args=p.parse_args();worlds=[json.loads(s) for s in args.registry.read_text().splitlines() if s.strip()]
    print(json.dumps(analyze(args.batch,worlds,args.output)))


if __name__=='__main__':main()
