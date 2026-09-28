"""Matched qualified states and exact finite common-future continuation probes."""
from __future__ import annotations
import argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
from itertools import combinations,permutations
import hashlib,json,shutil
from pathlib import Path
import numpy as np
from wowfs.paths import setup_paths,atomic_json
from wowfs.experiments.r2_sequence_analysis import write_csv
from wowfs.experiments.r4_data import load_ecologies,advance_state
from wowfs.experiments.r4_feasibility import evaluate_admission,eval_all_safe

POOLS=['static_skill','static_accuracy','timing_extra','timing_shared','resource_set_pair','resource_cost','target_damage','target_armor']
DESIGN={'pools':POOLS,'current_library':'H plus exactly one new configuration, one new item; enumerate every such action',
 'pair_selection':'same new item, same K; minimize maximum normalized current frontier difference, then novelty-mass and legacy-mass differences, then gear IDs',
 'matched_frontier_tolerance':.01,'matched_mass_tolerance':.125,
 'future_inventory':'lexicographically first five remaining new IDs; pool with fewer than five is unavailable, never completed by fictitious rewards',
 'Q':'uniform over all 120 permutations of five common future items, one item per wave',
 'future_policy':'deterministically admit all cap-safe currently-new configurations; stop at first failed P/N/D/L/H/C',
 'horizons':[1,3,5],'information':'pair selected without future evaluation; future table offline diagnostic only',
 'Psi_scope':'exact under declared finite Q and fixed all-safe continuation policy, not an oracle over all admissible subset policies',
 'Gamma':'main eight-task .05 epsilon/delta, fixed initial caps, K4; H and archive accumulate',
 'not_independent':'races, permutations, and overlapping pools are context diagnostics'}

def initial_actions(e):
    archive=e.initial_archive();actions=[]
    for item in e.new_items:
        pp,ix=e.problem([item],archive=archive)
        for j in np.flatnonzero(pp.safe&~pp.protected):
            mask=pp.protected.copy();mask[j]=True;m=evaluate_admission(pp,mask)
            if m['joint_pass']:
                actions.append({'item':item,'global_index':int(ix[j]),'gear_id':e.gear_ids[ix[j]],'metrics':m})
    return actions

def structural_state(e,admitted):
    best=e.values.max(axis=1);frontier=best[admitted].max(axis=0);sources=[]
    for s in e.protected_sources:
        own=np.array([s in ss for ss in e.sources])&admitted
        margin=(best[own].max(axis=0)+.05*e.scale-frontier)/e.scale
        sources.append({'source':s,'retention_margin_by_task':margin.tolist(),
                        'competitive_config_count':int(np.sum(np.any(best[own]>=frontier-.05*e.scale,axis=1)))})
    return {'source_retention_margins':sources,'registered_old_sources':len(e.protected_sources),
            'note':'computed entirely from current admitted source/config/task incidence and responses; not a future feasibility count'}

def branch(e,action,futures):
    pp,ix=e.problem([action['item']],archive=e.initial_archive());mask=pp.protected.copy()
    mask[np.flatnonzero(ix==action['global_index'])[0]]=True
    admitted,archive,registry=advance_state(e,ix,mask,e.initial,e.initial_archive(),e.protected_sources)
    state_structure=structural_state(e,admitted);cache={};paths=[]
    for sequence in permutations(futures):
        old=admitted.copy();hist=[a.copy() for a in archive];reg=registry;released=[action['item']];survived=0;failure=[]
        for depth,item in enumerate(sequence,1):
            prefix=sequence[:depth]
            if prefix in cache:
                saved=cache[prefix]
            else:
                p,indices=e.problem([item],protected=old,old_released=released,archive=hist,protected_sources=reg)
                metrics=eval_all_safe(p)
                if metrics['joint_pass']:
                    nxt=advance_state(e,indices,p.safe|p.protected,old,hist,reg)
                    saved=(True,nxt,[])
                else:saved=(False,None,metrics['failure_reasons'])
                cache[prefix]=saved
            if not saved[0]:failure=saved[2];break
            old,hist,reg=saved[1];released.append(item);survived=depth
        paths.append({'future_sequence':list(sequence),'survived':survived,'first_failure':failure})
    return {'action':action,'structure':state_structure,'initial_archive_profiles':sum(map(len,archive)),
            'initial_protected_gears':int(admitted.sum()),'initial_registered_sources':len(registry),
            'Psi':{str(h):sum(p['survived']>=h for p in paths)/len(paths) for h in DESIGN['horizons']},
            'paths':paths,'unique_prefixes_evaluated':len(cache)}

def context(e,directory):
    actions=initial_actions(e);pairs=[]
    for a,b in combinations(actions,2):
        if a['item']!=b['item'] or a['metrics']['K']!=b['metrics']['K']:continue
        distance=float(np.max(np.abs(np.array(a['metrics']['optimum'])-b['metrics']['optimum'])/e.scale))
        mass=max(abs(a['metrics']['novel_task_mass']-b['metrics']['novel_task_mass']),
                 abs(a['metrics']['worst_protected_source_mass']-b['metrics']['worst_protected_source_mass']))
        futures=[s for s in e.new_items if s!=a['item']][:5]
        if len(futures)<5:continue
        pairs.append((distance,mass,a['gear_id'],b['gear_id'],a,b,futures))
    result={'ecology':e.pool['id'],'race':e.race,'qualified_single_gear_actions':len(actions),
            'available_pair_count':len(pairs),'actions':actions,'status':'no_common_five_item_pair','rows':[]}
    if pairs:
        distance,mass,_,_,a,b,futures=min(pairs,key=lambda p:p[:4])
        matched=distance<=DESIGN['matched_frontier_tolerance'] and mass<=DESIGN['matched_mass_tolerance']
        result.update(status='matched' if matched else 'nearest_unmatched_diagnostic',current_frontier_distance=distance,
                      current_mass_distance=mass,future_items=futures)
        result['branches']=[branch(e,x,futures) for x in [a,b]]
        for h in DESIGN['horizons']:
            values=[x['Psi'][str(h)] for x in result['branches']]
            result['rows'].append({'ecology':e.pool['id'],'race':e.race,'line':'F','status':result['status'],
                'current_item':a['item'],'branch_a':a['gear_id'],'branch_b':b['gear_id'],'current_frontier_distance':distance,
                'current_mass_distance':mass,'horizon':h,'Q_sequences':120,'Psi_a':values[0],'Psi_b':values[1],
                'Psi_difference':values[0]-values[1],'continuation_policy':'all-safe; conditional finite Q',
                'no_online_future_information':True})
    atomic_json(Path(directory)/(e.pool['id']+'__'+e.race+'.json'),result)
    return result

def main():
    root=setup_paths();parser=argparse.ArgumentParser();parser.add_argument('--workers',type=int,default=8)
    parser.add_argument('--run',type=Path,default=root/'runs/r4-foundational-discovery/baseline-v1');args=parser.parse_args()
    out=root/'artifacts/r4-foundational-discovery';directory=root/'runs/r4-foundational-discovery/branch-probe-v1';directory.mkdir(exist_ok=False)
    atomic_json(out/'F_BRANCH_DESIGN.json',DESIGN);atomic_json(directory/'PROTOCOL.json',{'design':DESIGN,
        'results_sha256':hashlib.sha256((args.run/'RESULTS.json').read_bytes()).hexdigest()})
    (directory/'source').mkdir()
    for name in ['r4_branches.py','r4_data.py','r4_feasibility.py']:shutil.copy2(Path(__file__).parent/name,directory/'source'/name)
    ecologies=[e for e in load_ecologies(args.run) if e.pool['id'] in POOLS];done=[]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures=[pool.submit(context,e,directory) for e in ecologies]
        for future in as_completed(futures):
            result=future.result();done.append(result)
            print(json.dumps({k:result[k] for k in ['ecology','race','qualified_single_gear_actions','status']}),flush=True)
    write_csv(out/'BRANCH_CONTINUATION.csv',[row for d in done for row in d['rows']])
    atomic_json(out/'BRANCH_SUMMARY.json',[{k:v for k,v in d.items() if k not in ['actions','branches']} for d in done])

if __name__=='__main__':main()
