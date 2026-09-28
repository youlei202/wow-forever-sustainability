#!/usr/bin/env python3
"""Independent pre-query correctness gate; never a performance measurement."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from fractions import Fraction as F
import hashlib
from itertools import combinations, product
import json
from pathlib import Path
import random
from unittest.mock import patch

from wowfs.experiments.co_exact import Model, exhaustive, evaluate, frontier
from wowfs.experiments.co_generic import IncrementalSAT
from wowfs.experiments.co_query_benchmark import QUERY_METHODS, compute, maximal_sat_query, BudgetExpired


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def models():
    # Independent control family: two incompatible optional diagonals plus
    # heterogeneous exact two-task perturbations; includes infeasible targets.
    result=[]
    for index in range(8):
        rng=random.Random(920262601+index)
        rows=[]
        for l,r in product(('l0','a','b'),('r0','x','y')):
            v=[10,10] if (l,r)==('l0','r0') else [11,11] if index==0 else [rng.randrange(9,15),rng.randrange(9,15)]
            if index==0 and (l,r) in (('a','x'),('b','y')):v=[14,14]
            rows.append({'support':[l,r],'values':list(map(str,v))})
        result.append(Model.from_dict({'slots':{'l0':0,'a':0,'b':0,'r0':1,'x':1,'y':1},
            'configurations':rows,'history':['l0','r0'],'weights':['1/2','1/2'],
            'tolerance':['2','2'],'cap':['12','12'],'gain':['1','1'],
            'required_mass':'1/2','gain_mass':'1/2'}))
    return result


def query_gate():
    checked=0;cached=0;selector_checks=0;yes=0;no=0
    for i,model in enumerate(models()):
        optional=sorted(model.items-model.history)
        targets=[list(d) for n in range(len(optional)+1) for d in combinations(optional,n)]
        # Revisit early targets after incompatible strict-superset constraints.
        targets+=targets[::-1]
        truth=exhaustive(model,all_solutions=True)
        feasible=[set(p) for p in truth.get('solutions',[])]
        expected=['YES' if any(set(d)<=p for p in feasible) else 'NO' for d in targets]
        for method in QUERY_METHODS:
            job={'instance':{'instance_id':f'independent_query_gate_{i}',**model.to_dict()},
                 'method':method,'workflow':'repeat_queries','budget_seconds':15,
                 'per_query_seconds':2,'compile_budget_seconds':10,
                 'query_stream':{'queries':[{'query_index':j+1,'target':d,'query_kind':'audit'} for j,d in enumerate(targets)],'prefixes':[len(targets)]}}
            final,interface,text=compute(job)
            assert final['status']=='COMPLETE',(i,method,final)
            records=[json.loads(line) for line in text.splitlines()]
            assert len(records)==len(targets)
            for row,expected_status,target in zip(records,expected,targets):
                assert row['status']==expected_status,(i,method,target,row,expected_status)
                if row['status']=='YES':
                    assert set(target)<=set(row['items'])
                    assert evaluate(model,row['items'])['valid']
                    yes+=1
                else:no+=1
                cached+=bool(row.get('cache'));checked+=1
        solver=IncrementalSAT(model)
        try:
            for target,wanted in zip(targets,expected):
                row=maximal_sat_query(solver,target,2)
                assert row['status']==wanted,(i,target,wanted,row)
                if wanted=='YES':
                    assert row['maximality_proved']
                    assert not any(set(row['items'])<p for p in feasible)
                selector_checks+=1
        finally:solver.close()
    # Scripted growth decisions isolate the answer/proof-direction rules.
    model=models()[0];valid=exhaustive(model,['a'])['items']
    for ending in ('NO','UNKNOWN_TIMEOUT','ALARM'):
        class Fake:
            def __init__(self):self.calls=0
            def query(self,*args,**kw):
                self.calls+=1
                if self.calls==1:return {'status':'YES','items':valid,'verifier':evaluate(model,valid)}
                if ending=='ALARM':raise BudgetExpired('independent gate alarm')
                return {'status':ending,'unsat_core':['b']}
        result=maximal_sat_query(Fake(),['a'],2)
        assert result['status']=='YES' and result['items']==valid and 'unsat_core' not in result
        assert result['maximality_proved']==(ending=='NO')
        assert result['stop_after_query']==(ending=='ALARM')
    return {'six_method_answers':checked,'verified_yes':yes,'matched_no':no,'cache_hits':cached,
            'persistent_selector_maximality_checks':selector_checks,'timeout_direction_checks':3}


def registry_gate(run):
    import numpy as np
    rows=[json.loads(s) for s in (run/'native-test-registry/BENCHMARK_INSTANCES.jsonl').read_text().splitlines()]
    streams=[json.loads(s) for s in (run/'native-test-registry/QUERY_STREAMS.jsonl').read_text().splitlines()]
    assert len(rows)==48 and len(streams)==24
    assert sum(r['data_kind']=='NEW_NATIVE_MEAN' for r in rows)==32
    assert sum(r['data_kind']=='INHERITED_NATIVE_MEAN' for r in rows)==16
    bundle=run/'sensitivity/propagation-v1'
    metadata=json.loads((bundle/'INHERITED_MOMENTS_METADATA.json').read_text())
    claims=json.loads((bundle/'INHERITED_BASE_CLAIMS.json').read_text())
    old={r['claim_id']:(r,c) for r,c in zip(metadata,claims)}
    arrays=np.load(bundle/'INHERITED_MOMENTS.npz')
    new=0;inherited=0;unaltered_fields=('slots','configurations','weights','tolerance','required_mass','history','cap','gain','gain_mass')
    pairs={}
    for row in rows:
        m=Model.from_dict(row);f0=frontier(m,m.history)
        y=[max(c.values[q] for c in m.configurations if f0[q]<=c.values[q]<=m.cap[q]) for q in range(m.q)]
        assert list(map(F,row['fixed_y']))==y
        pairs.setdefault(row['instance_id'].rsplit('__',1)[0],[]).append(row)
        if row['data_kind']=='NEW_NATIVE_MEAN':
            wid=row['instance_id'].removeprefix('new__').rsplit('__',1)[0]
            p=run/'native/confirmation-v1'/wid/'base/EXACT_QUERIES.json'
            original=json.loads(p.read_text())
            assert row['source_exact_queries_sha256']==sha(p)
            assert all(row[k]==original['model'][k] for k in unaltered_fields)
            assert row['target']==original['queries'][0]['required'];new+=1
        else:
            record,claim=old[row['claim_id']];mean=arrays[record['array_prefix']+'_mean']
            refs=[F(repr(float(mean[index,q]))) for q,index in enumerate(record['reference_configuration_indices_by_task'])]
            b=claim['core_bounds_manifest']
            for key,scale in [('tolerance','tolerance'),('cap','cap'),('gain','gain')]:
                assert list(map(F,row[key]))==[F(str(b[scale]))*s for s in refs]
            assert set(row['history'])==set(claim['initial_items'])|{row['first_item']}
            for native,encoded in zip(record['configuration_order'],row['configurations']):
                assert set(native[:2])==set(encoded['support'])
            assert [[F(v) for v in c['values']] for c in row['configurations']]==[[F(repr(float(v))) for v in vals] for vals in mean]
            inherited+=1
    for pair in pairs.values():
        assert len(pair)==2
        assert all(pair[0][k]==pair[1][k] for k in unaltered_fields+('target','fixed_y'))
    for stream in streams:
        targets=[tuple(sorted(q['target'])) for q in stream['queries']]
        assert len(targets)==len(set(targets))==stream['count']
        assert all(set(d)<=set(stream['future_universe']) for d in targets)
    return {'matched_native_workflows':len(rows),'new_table_copies_verified':new,
            'inherited_original_reference_and_current_history_contracts_verified':inherited,
            'identical_fixed_unknown_model_pairs':len(pairs),'unique_query_histories':len(streams)}


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    report={'status':'PASS','utc':datetime.now(timezone.utc).isoformat(),'reviewer':'co_native_catalogs independent of query-driver implementation',
        'query_gate':query_gate(),'registry_gate':registry_gate(a.run_root),
        'source_hashes':{str(path):sha(path) for path in [Path(__file__),Path('src/wowfs/experiments/co_query_benchmark.py'),Path('src/wowfs/experiments/co_generic.py'),Path('src/wowfs/experiments/co_native_benchmark_design.py')]},
        'scope':'Correctness/contract gate, not a performance result. Original frozen primary modules untouched.'}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)


if __name__=='__main__':main()
