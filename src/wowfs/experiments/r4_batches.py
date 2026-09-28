"""Complete small-batch release screening on the same finite native final domains."""
from __future__ import annotations
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor,as_completed
from itertools import combinations
import json
from pathlib import Path
import shutil
import time
import numpy as np
from wowfs.paths import setup_paths,atomic_json,canonical_hash
from wowfs.experiments.r2_sequence_analysis import write_csv
from wowfs.experiments.r4_data import load_ecologies
from wowfs.experiments.r4_feasibility import eval_all_safe,solve_subset

def necessary_screen(problem):
    """Exact monotonic lower-frontier infeasibility, not a solver-time heuristic."""
    p=problem;floor=p.best[p.protected].max(axis=0);threshold=floor-p.tol_vector-p.tolerance
    if np.any(p.protected&~p.safe):return ['protected_power']
    reasons=[]
    for source in p.new_sources:
        selected=p.safe&np.array([source in ss for ss in p.sources])
        useful=np.any(p.best[selected]>=threshold,axis=0) if np.any(selected) else np.zeros(len(floor),bool)
        if p.weights@useful<p.min_mass-p.tolerance:reasons.append('N:'+source)
    new=p.safe&~p.protected
    novel=np.any(p.novel_best[new]>=threshold,axis=0) if np.any(new) else np.zeros(len(floor),bool)
    if p.weights@novel<p.min_mass-p.tolerance:reasons.append('D')
    return reasons

def solve_problem(problem,time_limit=2,objective='feasible'):
    metrics=eval_all_safe(problem)
    if metrics['joint_pass'] and objective=='feasible':
        return {'status':'all_safe_feasible','feasible':True,'proved_infeasible':False,
                'admitted':(problem.safe|problem.protected).tolist(),'metrics':metrics,'seconds':0.}
    reason=necessary_screen(problem)
    if reason:return {'status':'necessary_frontier_infeasible','feasible':False,'proved_infeasible':True,
                      'necessary_failures':reason,'metrics_all_safe':metrics,'seconds':0.}
    return solve_subset(problem,objective=objective,time_limit=time_limit)

def screen_ecology(ecology,outdir,time_limit=2):
    outdir=Path(outdir);checkpoint=outdir/(ecology.pool['id']+'__'+ecology.race+'.json')
    records=[];details=[]
    for size in range(1,min(4,len(ecology.new_items))+1):
        for release in combinations(ecology.new_items,size):
            pp,indices=ecology.problem(release,archive=ecology.initial_archive())
            raw=np.max(pp.best/pp.scale-1)
            allsafe=eval_all_safe(pp);result=solve_problem(pp,time_limit)
            chosen=result.get('metrics',allsafe)
            record={'ecology':ecology.pool['id'],'background':ecology.pool['background'],'race':ecology.race,
                'permission':'A_fixed_native_physics_release_existing_items','release_items':list(release),'release_size':size,
                'final_domain_size':len(ecology.gear_ids),'current_domain_size':len(indices),
                'initial_gears':int(ecology.initial.sum()),'raw_growth':float(raw),
                'all_safe_joint':allsafe['joint_pass'],'all_safe_failures':allsafe['failure_reasons'],
                'subset_status':result['status'],'subset_feasible':result['feasible'],'proved_infeasible':result.get('proved_infeasible',False),
                'necessary_failures':result.get('necessary_failures',[]),'solver_seconds':result.get('seconds',0),
                'all_safe_N':allsafe['N'],'all_safe_D':allsafe['D'],'all_safe_L':allsafe['L'],'all_safe_K':allsafe['K'],
                'subset_admitted_new':chosen.get('admitted_new_gears') if result['feasible'] else None,
                'subset_K':chosen.get('K') if result['feasible'] else None,
                'worst_source_mass':chosen.get('worst_protected_source_mass') if result['feasible'] else None,
                'protected_source_count':len(ecology.protected_sources),
                'batch_N_definition':'every released item individually competitive; D one batch profile, not every name distinct',
                'no_redraw':True,'point_means_only':True}
            records.append(record)
            details.append({'release_items':list(release),'indices':indices.tolist(),'all_safe':allsafe,'subset':result})
    by_release={tuple(r['release_items']):r for r in records};witnesses=[]
    for r in records:
        release=r['release_items']
        if len(release)<=1 or not r['subset_feasible']:continue
        proper=[by_release[subset] for k in range(1,len(release)) for subset in combinations(release,k)]
        single=[by_release[(s,)] for s in release]
        r['all_singles_proved_infeasible']=all(x['proved_infeasible'] for x in single)
        r['all_proper_batches_proved_infeasible']=all(x['proved_infeasible'] for x in proper)
        if r['all_singles_proved_infeasible']:witnesses.append(r)
    result={'ecology':ecology.pool['id'],'race':ecology.race,'rows':records,'details':details,
            'strong_pair_or_batch_witnesses':witnesses,'complete':True}
    atomic_json(checkpoint,result);return result

def main():
    root=setup_paths();p=argparse.ArgumentParser();p.add_argument('--run',type=Path,default=root/'runs/r4-foundational-discovery/baseline-v1')
    p.add_argument('--workers',type=int,default=4);p.add_argument('--time-limit',type=float,default=2.);p.add_argument('--resume',action='store_true');args=p.parse_args()
    out=root/'artifacts/r4-foundational-discovery';checkpoints=root/'runs/r4-foundational-discovery/batch-screen-v1';checkpoints.mkdir(exist_ok=True)
    ecologies=load_ecologies(args.run);done=[];pending=[]
    for ecology in ecologies:
        path=checkpoints/(ecology.pool['id']+'__'+ecology.race+'.json')
        if args.resume and path.exists():done.append(json.loads(path.read_text()))
        else:pending.append(ecology)
    protocol={'native_run':str(args.run),'native_results_sha256':__import__('hashlib').sha256((args.run/'RESULTS.json').read_bytes()).hexdigest(),
        'release_sizes':[1,2,3,4],'same_final_domain':True,'source_sha256':__import__('hashlib').sha256(Path(__file__).read_bytes()).hexdigest(),
        'dependency_sha256':{name:__import__('hashlib').sha256((Path(__file__).parent/name).read_bytes()).hexdigest() for name in ['r4_feasibility.py','r4_data.py']},
        'time_limit':args.time_limit,'unknown_not_infeasible':True,'initial_anchor':'frozen initial16 perpool','metrics':'R4mainGamma; batch each-new N, batch existential D'}
    if (checkpoints/'PROTOCOL.json').exists():
        if not args.resume or json.loads((checkpoints/'PROTOCOL.json').read_text())!=protocol:raise ValueError('Analysis resume requires exact protocol/source/physics')
    else:
        atomic_json(checkpoints/'PROTOCOL.json',protocol)
        for name in ['r4_batches.py','r4_feasibility.py','r4_data.py']:
            (checkpoints/'source').mkdir(exist_ok=True);shutil.copy2(Path(__file__).parent/name,checkpoints/'source'/name)
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures={pool.submit(screen_ecology,e,checkpoints,args.time_limit):(e.pool['id'],e.race) for e in pending}
        for f in as_completed(futures):
            result=f.result();done.append(result)
            print(json.dumps({'completed_contexts':len(done),'context':futures[f],'strong_batch_witnesses':len(result['strong_pair_or_batch_witnesses'])}),flush=True)
    rows=[r for result in done for r in result['rows']];write_csv(out/'BATCH_GRANULARITY.csv',rows)
    atomic_json(out/'BATCH_SUMMARY.json',{'contexts':len(done),'release_evaluations':len(rows),'statuses':dict(Counter(r['subset_status'] for r in rows)),
        'feasible_by_size':{str(k):sum(r['subset_feasible'] for r in rows if r['release_size']==k) for k in range(1,5)},
        'strong_batch_witnesses':[r for result in done for r in result['strong_pair_or_batch_witnesses']]})

if __name__=='__main__':main()
