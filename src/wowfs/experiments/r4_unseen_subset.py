"""Exploratory fair rule comparison for the newly observed unseen N repair."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from wowfs.paths import setup_paths, atomic_json
from wowfs.experiments.r2_native import file_hash
from wowfs.experiments.r4_data import load_ecologies
from wowfs.experiments.r4_feasibility import eval_all_safe, solve_subset
from wowfs.experiments.r4_coexistence import source_diagnostics


def main():
    root=setup_paths();out=root/'artifacts/r4-foundational-discovery'
    run=root/'runs/r4-foundational-discovery/unseen-future-v1'
    anchor=json.loads((out/'UNSEEN_FROZEN_ANCHORS.json').read_text())['unseen_resource_cost__RaceHuman']
    ecology=next(e for e in load_ecologies(run,run/'CONFIG.yaml')
                 if e.pool['id']=='unseen_resource_cost' and e.race=='RaceHuman')
    ecology.scale=np.array(anchor['scale']);ecology.cap=np.array(anchor['cap'])
    ecology.protected_sources=tuple(anchor['protected_sources'])
    problem,indices=ecology.problem(['18203','19951'],archive=ecology.initial_archive())
    protocol={'selection':'Exploratory E follow-up, identified in a previously predicted new D ecology; not a preregistered E success.',
        'pool':ecology.pool['id'],'race':ecology.race,'release':['18203','19951'],
        'native_results_sha256':file_hash(run/'RESULTS.json'),'fixed_anchor':anchor,
        'information':'Same full current response table, H old16, all policies/tasks, same source-incidence features.',
        'methods':['arbitrary_subset','scalar','generic2','generic4'],'objective':'max_admitted',
        'time_limit_seconds_each':30,'price_bounds':[0,100],'strict_exclusion_margin':1e-6,
        'timeout':'unknown rather than infeasible; report primal/dual directions',
        'source_sha256':file_hash(Path(__file__))}
    path=out/'UNSEEN_E_PROTOCOL.json'
    if path.exists() and json.loads(path.read_text())!=protocol:raise ValueError('Do not overwrite frozen comparison')
    atomic_json(path,protocol)
    full=eval_all_safe(problem);results={}
    for name,rows in [('arbitrary_subset',0),('scalar',1),('generic2',2),('generic4',4)]:
        result=solve_subset(problem,objective='max_admitted',time_limit=30,rule_rows=rows)
        if result['feasible']:
            mask=np.array(result['admitted'])
            result['excluded_safe_gears']=[{'gear_id':problem.gear_ids[g],'gear':ecology.gears[indices[g]]}
                for g in np.flatnonzero(problem.safe & ~problem.protected & ~mask)]
            result['source_diagnostics']=source_diagnostics(problem,mask)
        results[name]=result
        atomic_json(out/'UNSEEN_E_COMPARISON.json',{'protocol':protocol,'all_safe':full,'methods':results})
        print(json.dumps({'method':name,'feasible':result['feasible'],'status':result['status'],
            'excluded_safe_new':result.get('metrics',{}).get('excluded_safe_new_gears'),
            'max_total_upper':result.get('maximum_total_admitted_upper_bound'),
            'max_total_lower':result.get('maximum_total_admitted_lower_bound')}),flush=True)


if __name__=='__main__':main()
