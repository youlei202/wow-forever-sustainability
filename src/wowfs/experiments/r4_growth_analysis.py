"""Independent demand additions, with all original power constraints retained."""
from __future__ import annotations
import copy,json
import numpy as np
from wowfs.paths import setup_paths,atomic_json
from wowfs.experiments.r4_data import load_ecologies
from wowfs.experiments.r4_batches import solve_problem
from wowfs.experiments.r4_feasibility import eval_all_safe
from wowfs.experiments.r2_sequence_analysis import write_csv

def main():
    root=setup_paths();run=root/'runs/r4-foundational-discovery/task-growth-v1'
    base={(e.pool['id'],e.race):e for e in load_ecologies(root/'runs/r4-foundational-discovery/baseline-v1')};growth=load_ecologies(run,run/'CONFIG.yaml')
    rows=[];details=[]
    for new in growth:
        old=base[(new.pool['id'],new.race)]
        if old.gear_ids!=new.gear_ids:raise ValueError('Task expansion changed gear domain')
        combined=copy.deepcopy(old);combined.tasks=old.tasks+new.tasks
        combined.values=np.concatenate([old.values,new.values],axis=2);combined.behavior=np.concatenate([old.behavior,new.behavior],axis=2)
        combined.samples=np.concatenate([old.samples,new.samples],axis=2);combined.scale=np.r_[old.scale,new.scale];combined.cap=np.r_[old.cap,new.cap]
        for label,e in [('fixed8',old),('expanded12',combined)]:
            for item in e.new_items:
                p,ix=e.problem([item],archive=e.initial_archive());result=solve_problem(p,2);full=eval_all_safe(p)
                rows.append({'ecology':e.pool['id'],'race':e.race,'demand':label,'new_item':item,'joint_feasible':result['feasible'],
                    'status':result['status'],'all_safe_failures':full['failure_reasons'],'K':full['K'],'novel_task_mass':full['novel_task_mass'],
                    'worst_L':full['worst_protected_source_mass'],'all_old_caps_retained':True,'unchanged_legacy_registry':True,
                    'interpretation':'Independent task additions diagnostic; expanded12 is not original eight-task joint success'})
                details.append({'ecology':e.pool['id'],'race':e.race,'demand':label,'new_item':item,'subset':result,'all_safe':full})
    out=root/'artifacts/r4-foundational-discovery';write_csv(out/'TASK_GROWTH_DIAGNOSTIC.csv',rows);atomic_json(out/'TASK_GROWTH_DETAILS.json',details)
    print(json.dumps({'actions':len(rows),'fixed8':sum(r['joint_feasible']for r in rows if r['demand']=='fixed8'),
                      'expanded12':sum(r['joint_feasible']for r in rows if r['demand']=='expanded12')}))

if __name__=='__main__':main()
