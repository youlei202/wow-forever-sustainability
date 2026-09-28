"""Equal-cardinality demand diagnostics; all eight original power caps stay active."""
from __future__ import annotations
import argparse
from itertools import combinations
import json
from pathlib import Path
import numpy as np
from wowfs.paths import setup_paths,atomic_json
from wowfs.experiments.r2_sequence_analysis import portfolio_cover,write_csv
from wowfs.experiments.r4_data import load_ecologies
from wowfs.experiments.r4_batches import solve_problem

POOLS=['static_skill','static_accuracy','timing_extra','timing_shared','resource_set_pair','resource_cost','target_damage','target_armor']
DEMANDS={'single_target_armor_matched':['sustained','short_burst','burst_10s','endurance_360s'],
         'heterogeneous_channels':['short_burst','four_target','high_armor','resource_pressure']}

def frozen_design():
    return {'pools':POOLS,'demand_sets':DEMANDS,'task_count_each':4,'all_power_caps_active':8,
        'interpretation':'Declared demand diagnostic, not original eight-equal-weight joint success. Same candidates/physics/initial protected-source registry; only competitive-demand weights and K coverage differ.',
        'initial_feasibility':'If protected old source has no competitive use in a demand panel initially, report that rather than attributing the failure to an update.',
        'advantage_reversal_margin':.02,'primary_epsilon':.05,'primary_delta':.05,
        'counts':'8pool paired diagnostics ×2races; no independence claim for overlapping equipment.'}

def main():
    root=setup_paths();p=argparse.ArgumentParser();p.add_argument('--freeze-only',action='store_true')
    p.add_argument('--run',type=Path,default=root/'runs/r4-foundational-discovery/baseline-v1');args=p.parse_args()
    out=root/'artifacts/r4-foundational-discovery';protocol=frozen_design()
    if args.freeze_only:
        if (out/'B_DEMAND_DESIGN.json').exists() and json.loads((out/'B_DEMAND_DESIGN.json').read_text())!=protocol:raise ValueError('Existing demand design differs')
        atomic_json(out/'B_DEMAND_DESIGN.json',protocol);return
    if json.loads((out/'B_DEMAND_DESIGN.json').read_text())!=protocol:raise ValueError('Demand design not frozen')
    ecologies=load_ecologies(args.run);rows=[];details=[]
    for e in ecologies:
        if e.pool['id'] not in POOLS:continue
        best=e.values.max(axis=1);safe=np.all(best<=e.cap+1e-9,axis=1)
        for name,names in DEMANDS.items():
            taskindices=[next(i for i,t in enumerate(e.tasks) if t['id']==n) for n in names]
            weights=np.zeros(len(e.tasks));weights[taskindices]=.25
            oldclose=best[e.initial]>=e.scale-.05*e.scale
            oldss=[ss for ss,a in zip(e.sources,e.initial) if a]
            retained={s:float(weights@np.any(oldclose[np.array([s in ss for ss in oldss])],axis=0)) for s in e.protected_sources}
            initial_L=all(v>=.05 for v in retained.values())
            initial_K=portfolio_cover(best[e.initial],e.scale,e.scale,weights=weights)['K']
            capacity=0;newN=newD=0;statuses=[]
            for item in e.new_items:
                problem,indices=e.problem([item],archive=e.initial_archive(),weights=weights)
                result=solve_problem(problem,time_limit=2)
                from wowfs.experiments.r4_feasibility import eval_all_safe
                full=eval_all_safe(problem);capacity+=int(result['feasible']);newN+=int(full['N']);newD+=int(full['D']);statuses.append(result['status'])
                details.append({'ecology':e.pool['id'],'race':e.race,'demand':name,'new_item':item,'all_safe':full,'subset':result})
            available=best[safe][:,taskindices]/e.scale[taskindices]
            reversals=0;comparisons=0
            for a,b in combinations(range(len(available)),2):
                delta=available[a]-available[b];comparisons+=1
                reversals+=int(np.max(delta)>=.02 and np.min(delta)<=-.02)
            optimum=best[safe].max(axis=0);cover=portfolio_cover(best[safe],optimum,e.scale,weights=weights)
            winners=np.argmax(best[safe][:,taskindices],axis=0)
            policy=np.argmax(e.values[safe][:,:,taskindices],axis=1)
            rows.append({'ecology':e.pool['id'],'background':e.pool['background'],'race':e.race,'line':'B','demand':name,
                'competitive_tasks':names,'power_tasks':8,'initial_L':initial_L,'initial_K':initial_K,'initial_source_masses':retained,
                'candidate_items':len(e.new_items),'joint_feasible_singletons':capacity,'solver_statuses':statuses,
                'all_safe_useful_new_items':newN,'all_safe_novel_new_items':newD,
                'reversing_safe_gear_pairs':reversals,'safe_gear_pair_denominator':comparisons,
                'reversal_fraction':reversals/comparisons if comparisons else 0,
                'different_task_winning_gears':len(set(winners.tolist())),'K_all_safe_terminal':cover['K'],
                'policies_optimal_any_task':sorted(set(e.policies[p] for p in policy.flat)),
                'tasks_are_item_independent':True,'not_main_gamma':'Competitive-demand reweighting only; all physical means/caps preserved.'})
    write_csv(out/'DEMAND_CAPACITY.csv',rows);atomic_json(out/'DEMAND_DETAILS.json',details)
    print(json.dumps({'paired_ecology_contexts':len(rows)//2,'rows':len(rows)},indent=2))

if __name__=='__main__':main()
