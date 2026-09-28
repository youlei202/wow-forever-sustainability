"""Paired ecological consequences of source-fixed native rule interventions."""
from __future__ import annotations
import argparse,copy,json
from concurrent.futures import ProcessPoolExecutor,as_completed
from itertools import combinations
from pathlib import Path
import numpy as np
from wowfs.paths import setup_paths,atomic_json
from wowfs.experiments.r2_sequence_analysis import behavior_vector,write_csv
from wowfs.experiments.r4_data import load_ecologies
from wowfs.experiments.r4_batches import solve_problem
from wowfs.experiments.r4_feasibility import eval_all_safe
from wowfs.experiments.r4_worlds import INTERVENTIONS

def world_ecology(base,rows):
    e=copy.deepcopy(base);lookup={(r['gear_id'],r['task'],r['strategy']):r for r in rows if r['race']==e.race}
    for g,gid in enumerate(e.gear_ids):
        for p,policy in enumerate(e.policies):
            for t,task in enumerate(e.tasks):
                row=lookup[(gid,task['id'],policy)]
                e.samples[g,p,t]=row['dps_samples'];e.values[g,p,t]=np.mean(row['dps_samples'])
                e.behavior[g,p,t]=behavior_vector(row,task['duration_seconds'])
    e.scale=e.values[e.initial].max(axis=(0,1));e.cap=1.05*e.scale
    close=e.values.max(axis=1)>=e.scale-.05*e.scale
    old=set.union(set(),*[s for s,a in zip(e.sources,e.initial) if a])
    e.protected_sources=tuple(sorted(s for s in old if np.any(close[np.array([s in ss for ss in e.sources])&e.initial])))
    return e

def screen(args):
    base,rows,contrast,directory=args;e=world_ecology(base,rows);records=[];details=[]
    for size in range(1,min(4,len(e.new_items))+1):
        for release in combinations(e.new_items,size):
            pp,ix=e.problem(release,archive=e.initial_archive());full=eval_all_safe(pp);result=solve_problem(pp,2)
            records.append({'intervention_id':contrast['id'],'ecology':e.pool['id'],'race':e.race,'world':contrast['world'],
                'release_items':list(release),'release_size':size,'subset_feasible':result['feasible'],
                'proved_infeasible':result.get('proved_infeasible',False),'subset_status':result['status'],
                'all_safe_joint':full['joint_pass'],'all_safe_failures':full['failure_reasons'],
                'N':full['N'],'D':full['D'],'L':full['L'],'K':full['K'],
                'worst_source_mass':full['worst_protected_source_mass'],'admitted_new_gears':full['admitted_new_gears'],
                'permission':'C t0 world; own frozen initial anchor','population_confirmation':False})
            details.append({'release_items':list(release),'indices':ix.tolist(),'all_safe':full,'subset':result})
    ratios=e.values[base.initial]/base.values[base.initial]
    summary={'intervention_id':contrast['id'],'ecology':e.pool['id'],'race':e.race,'world':contrast['world'],
        'initial_gear_policy_task_min_ratio_to_native':float(ratios.min()),
        'initial_gear_policy_task_max_ratio_to_native':float(ratios.max()),
        'initial_best_ratio_by_task':(e.scale/base.scale).tolist(),
        'world_protected_sources':e.protected_sources,'native_protected_sources':base.protected_sources,
        'world_initial_registry_removed':sorted(set(base.protected_sources)-set(e.protected_sources)),
        'world_raw_max_ratio_to_own_initial_by_task':(e.values.max(axis=(0,1))/e.scale).tolist(),
        'native_raw_max_ratio_to_native_initial_by_task':(base.values.max(axis=(0,1))/base.scale).tolist(),
        'feasible_by_size':{str(k):sum(r['subset_feasible'] for r in records if r['release_size']==k)for k in range(1,5)},
        'rows':records,'details':details}
    atomic_json(Path(directory)/(contrast['id']+'__'+e.race+'.json'),summary);return summary

def main():
    root=setup_paths();parser=argparse.ArgumentParser();parser.add_argument('--workers',type=int,default=8);args=parser.parse_args()
    run=root/'runs/r4-foundational-discovery';directory=run/'world-analysis-v1';directory.mkdir(exist_ok=False)
    worlds=json.loads((run/'worlds-v1/RESULTS.json').read_text())
    if worlds['errors']:raise ValueError('Incomplete world data')
    base=load_ecologies(run/'baseline-v1');jobs=[]
    for c in INTERVENTIONS:
        rows=[r for r in worlds['rows'] if r['intervention_id']==c['id']]
        for e in base:
            if e.pool['id']==c['pool']:jobs.append((e,rows,c,directory))
    done=[]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for future in as_completed([pool.submit(screen,j)for j in jobs]):
            result=future.result();done.append(result)
            print(json.dumps({k:result[k]for k in ['intervention_id','race','feasible_by_size']}),flush=True)
    out=root/'artifacts/r4-foundational-discovery'
    write_csv(out/'WORLD_RELEASE_FEASIBILITY.csv',[r for d in done for r in d['rows']])
    atomic_json(out/'WORLD_STRUCTURAL_SUMMARY.json',[{k:v for k,v in d.items()if k not in ['rows','details']}for d in done])

if __name__=='__main__':main()
