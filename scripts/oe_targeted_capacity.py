#!/usr/bin/env python3
"""Complete-domain development challenge for explicitly selected native cases."""
from __future__ import annotations
import argparse
from collections import defaultdict
from dataclasses import replace
import json
from pathlib import Path
import time

from wowfs.experiments.oe_planning import build_domain, plain
from wowfs.experiments.oe_solver import exact_capacity, state_metrics, validate_history
from wowfs.experiments.r2_native import file_hash
from wowfs.paths import atomic_json


def main():
    ap=argparse.ArgumentParser()
    for name in ('batch','registry','cases','output'):ap.add_argument('--'+name,required=True,type=Path)
    ap.add_argument('--timeout',type=float,default=30)
    args=ap.parse_args()
    if (args.output/'SUMMARY.json').exists():raise ValueError('Completed analysis is frozen: choose a new output directory')
    args.output.mkdir(parents=True,exist_ok=True)
    rows=json.loads((args.batch/'RESULTS.json').read_text())['rows']
    groups=defaultdict(list)
    for r in rows:
        if r is not None:groups[r['world_id']].append(r)
    worlds={w['world_id']:w for w in (json.loads(line) for line in args.registry.read_text().splitlines() if line.strip())}
    cases=json.loads(args.cases.read_text())
    manifest={'batch':str(args.batch),'registry':str(args.registry),'cases':str(args.cases),
        'batch_results_sha256':file_hash(args.batch/'RESULTS.json'),'registry_sha256':file_hash(args.registry),
        'cases_sha256':file_hash(args.cases),'script_sha256':file_hash(Path(__file__)),
        'solver_sha256':file_hash(Path(__file__).parents[1]/'src/wowfs/experiments/oe_solver.py'),
        'planning_sha256':file_hash(Path(__file__).parents[1]/'src/wowfs/experiments/oe_planning.py'),
        'timeout_per_call':args.timeout,'native_calls':0,
        'interpretation':'Adaptive development challenge using complete previously observed physical table; not independent confirmation.'}
    path=args.output/'MANIFEST.json'
    if path.exists() and json.loads(path.read_text())!=manifest:raise ValueError('Changed input or source; use a new output version')
    atomic_json(path,manifest)
    outputs=[];start=time.monotonic()
    for i,case in enumerate(cases):
        wid=case['world_id'];p,domain=build_domain(worlds[wid],groups[wid],max_candidates=22)
        if domain['removed_for_oracle_row_ids'] or domain['removed_for_oracle_partner_ids']:raise ValueError('Full-domain challenge unexpectedly pruned candidates')
        if not domain['full_declared_world_observed']:raise ValueError('Full declared physical table is missing observations')
        # Keep the previous finite release budget when expanding the candidate
        # pool; alternative actions are restored without extra publication rights.
        p=replace(p,gain=case['g'],cap=1+case['h'],tolerance=case['e'],
            total_item_budget=case.get('total_item_budget',12))
        domain['problem_template']=plain(p)
        result={'case':case,'domain':domain,'logical_cells':len(groups[wid]),
            'unique_physical_keys':len({r['physical_key'] for r in groups[wid]}),
            'full_unpublished_candidates':len(p.items)-len(p.initial_items),
            'total_item_budget':p.total_item_budget,'initial_state':plain(state_metrics(p)),
            'global':{},'conditional':[]}
        print(json.dumps({'case_started':i,'world_id':wid,'full_candidates':result['full_unpublished_candidates']}),flush=True)
        for B in case.get('global_B',[1,2]):
            for retain in (True,False):
                sol=exact_capacity(p,B,retention=retain,max_candidates=22,timeout_seconds=args.timeout)
                key=f'B{B}_{"retaining" if retain else "value"}';result['global'][key]=plain(sol)
                print(json.dumps({'world_id':wid,'phase':'global','method':key,'status':sol.status,'lower':sol.capacity_lower,'upper':sol.capacity_upper,'seconds':sol.elapsed_seconds}),flush=True)
                atomic_json(args.output/f'CASE_{i:02}.json',plain(result))
        for batch in case.get('first_batches',[]):
            validated=validate_history(p,[batch],1)
            initial=validated[-1].published
            entry={'first_batch':batch,'first_state':plain(validated[-1]),'continuations':{}}
            for B in case.get('conditional_B',[1,2]):
                for retain in (True,False):
                    sol=exact_capacity(p,B,initial_items=initial,retention=retain,max_candidates=22,timeout_seconds=args.timeout)
                    key=f'B{B}_{"retaining" if retain else "value"}';entry['continuations'][key]=plain(sol)
                    print(json.dumps({'world_id':wid,'phase':'conditional','first_batch':batch,'method':key,'status':sol.status,'lower':sol.capacity_lower,'upper':sol.capacity_upper,'seconds':sol.elapsed_seconds}),flush=True)
            result['conditional'].append(entry)
            atomic_json(args.output/f'CASE_{i:02}.json',plain(result))
        result['status']='completed';outputs.append(result)
        atomic_json(args.output/f'CASE_{i:02}.json',plain(result))
    atomic_json(args.output/'RESULTS.json',plain(outputs))
    atomic_json(args.output/'SUMMARY.json',{'status':'completed','cases':len(outputs),'elapsed_seconds':time.monotonic()-start,'native_calls':0})


if __name__=='__main__':main()
