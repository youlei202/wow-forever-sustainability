#!/usr/bin/env python3
"""Restore full physical candidate domains and challenge apparent planning gains."""
import argparse
from collections import defaultdict
from dataclasses import replace
import json
from pathlib import Path
import time
import numpy as np
from wowfs.paths import atomic_json
from wowfs.experiments.oe_planning import build_domain, plain, weighted_greedy
from wowfs.experiments.oe_solver import _Evaluator,exact_capacity,greedy_capacity,validate_history
from wowfs.experiments.oe_baseline_challenge import minimum_increment
from wowfs.experiments.r2_native import file_hash


def rolling_minimum(p,weights,preference='weighted'):
    ev=_Evaluator(p);mask=0;path=[]
    if not ev.valid(0):return {'status':'initially_invalid','capacity':None,'path':[]}
    def amount(delta):return float(max(delta)) if preference=='max_task' else float(np.dot(weights,delta))
    while True:
        options=list(ev.successors(mask,1))
        if not options:break
        before=np.array(ev.metrics(mask).frontier)
        def score(pair):
            nxt,batch=pair;future=list(ev.successors(nxt,1));front=np.array(ev.metrics(nxt).frontier)
            least=min((amount(np.array(ev.metrics(after).frontier)-before) for after,_ in future),default=amount(front-before))
            return (-int(bool(future)),least,amount(front-before),-min(ev.metrics(nxt).source_margins.values()),batch)
        mask,batch=min(options,key=score);path.append(batch)
    return {'status':'heuristic','capacity':len(path),'path':path,'score_weights':weights,'score_preference':preference}


def normalize(p,result):
    d=plain(result);path=d.get('batches',d.get('path',[]));states=validate_history(p,path,1)
    return {'status':d['status'],'capacity_lower':d.get('capacity_lower',d.get('capacity')),
        'capacity_upper':d.get('capacity_upper'),'batches':path,'released_items':sum(map(len,path)),
        'frontiers':[x.frontier for x in states[1:]],'terminal_frontier':states[-1].frontier,
        'source_masses':[x.source_masses for x in states], 'source_margins':[x.source_margins for x in states]}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run-root',type=Path,default=Path('/work/Users/leiyo/wow-forever-sustainability-work/artifacts/open-exploration-2026-09-26/campaign-v1'))
    parser.add_argument('--output',type=Path)
    args=parser.parse_args();root=args.run_root;out=args.output or root/'analysis/full-baseline-challenge-v1'
    if (out/'SUMMARY.json').exists():raise ValueError('Completed analysis is frozen: choose a new output directory')
    out.mkdir(parents=True,exist_ok=True)
    sources=[('refine-min-increment-v1','refine-v1',root/'WORLD_REGISTRY.jsonl'),
             ('catalog-two-slot-min-increment-v1','catalog-v1',root/'analysis/catalog-two-slot-v1/DERIVED_WORLD_REGISTRY.jsonl')]
    manifest={'script_sha256':file_hash(Path(__file__)),'native_calls':0,'sources':[],
        'scope':'Full observed candidate domains; original total publication budget remains 12. Development means only. All paths checked at every source/prefix.'}
    outputs=[];start=time.monotonic()
    for label,batch,registry in sources:
        original=root/'analysis'/label/'MIN_INCREMENT_CHALLENGE.json';raw=root/'batches'/batch/'RESULTS.json'
        manifest['sources'].append({'batch_results':str(raw),'sha256':file_hash(raw),'registry':str(registry),'registry_sha256':file_hash(registry),'prior_analysis':str(original),'prior_sha256':file_hash(original)})
        worlds={w['world_id']:w for w in map(json.loads,registry.read_text().splitlines())}
        groups=defaultdict(list)
        for row in json.loads(raw.read_text())['rows']:
            if row is not None:groups[row['world_id']].append(row)
        for old in json.loads(original.read_text()):
            if not old['planning_gap_survives_challenge']:continue
            wid=old['world_id'];p,domain=build_domain(worlds[wid],groups[wid],22)
            p=replace(p,gain=old['g'],cap=1+old['h'],tolerance=old['e'],total_item_budget=12)
            assert not domain['removed_for_oracle_row_ids'] and not domain['removed_for_oracle_partner_ids']
            methods={'exact':normalize(p,exact_capacity(p,1,max_candidates=22,timeout_seconds=30))}
            for policy in ('max_gain','source_aware','lookahead2'):methods[policy]=normalize(p,greedy_capacity(p,1,policy=policy))
            weights=[(x,1-x) for x in (0.,.25,.5,.75,1.)]
            for i,w in enumerate(weights):
                methods[f'weighted_current_{i}']=normalize(p,weighted_greedy(p,w))
                methods[f'minimum_increment_{i}']=normalize(p,minimum_increment(p,w))
                methods[f'rolling_minimum2_{i}']=normalize(p,rolling_minimum(p,w))
            methods['minimum_max_task_increment']=normalize(p,minimum_increment(p,p.task_weights,'max_task'))
            methods['rolling_minimum2_max_task']=normalize(p,rolling_minimum(p,p.task_weights,'max_task'))
            best=max(v['capacity_lower'] for k,v in methods.items() if k!='exact')
            exact=methods['exact'];ef=np.array(exact['terminal_frontier'])
            simple_dominates=[k for k,v in methods.items() if k!='exact' and np.all(np.array(v['terminal_frontier'])>=ef-1e-10)]
            same_best=[k for k,v in methods.items() if k!='exact' and v['capacity_lower']==best and np.allclose(v['terminal_frontier'],ef,rtol=0,atol=1e-10)]
            result={'world_id':wid,'g':old['g'],'h':old['h'],'e':old['e'],'original_narrow_exact':old['finite_exact_lower'],
                'original_narrow_minimum':old['minimum_increment_best'],'full_candidate_count':len(p.items)-len(p.initial_items),
                'total_item_budget':12,'domain':domain,'methods':methods,'best_simple_capacity':best,
                'exact_advantage_survives':exact['capacity_lower']>best,'same_terminal_best_simple_methods':same_best,
                'simple_methods_reaching_or_dominating_returned_exact_terminal':simple_dominates,
                'interpretation':'A capacity advantage with an already attained terminal may only be finer release scheduling; this does not prove better total content value.'}
            outputs.append(result);atomic_json(out/f'CASE_{len(outputs)-1:02}.json',plain(result))
            print(json.dumps({'world_id':wid,'g':old['g'],'h':old['h'],'e':old['e'],'exact':exact['capacity_lower'],'best_simple':best,'survives':result['exact_advantage_survives'],'best_simple_same_terminal':same_best,'any_simple_dominates_terminal':bool(simple_dominates)}),flush=True)
    atomic_json(out/'MANIFEST.json',manifest);atomic_json(out/'RESULTS.json',plain(outputs))
    atomic_json(out/'SUMMARY.json',{'status':'completed','challenged_rows':len(outputs),'gap_survives':sum(r['exact_advantage_survives'] for r in outputs),'elapsed_seconds':time.monotonic()-start,'native_calls':0})

if __name__=='__main__':main()
