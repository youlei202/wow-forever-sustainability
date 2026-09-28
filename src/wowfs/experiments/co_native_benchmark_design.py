"""Freeze all inherited histories and all new base catalogues for exact timing.

No unit is selected for a solver result. New native tables are deterministic
objects exported from the same confirmation samples, not more physical evidence.
"""
from __future__ import annotations
import argparse
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
from .co_benchmark_design import query_stream


def register(analysis,inherited,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    analysis=Path(analysis);inherited=Path(inherited)
    raw=[json.loads(s) for s in inherited.read_text().splitlines()]
    for p in sorted(analysis.glob('co_*__validation_*/base/EXACT_QUERIES.json')):
        value=json.loads(p.read_text());model=value['model']
        raw.append({**model,'instance_id':'new__'+value['world_id'],'data_kind':'NEW_NATIVE_MEAN',
          'family':value['world_id'].split('__')[0].removeprefix('co_'),
          'registered_target':value['queries'][0]['required'],'source_exact_queries_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
          'scope':'All sixteen registered base catalogues, no outcome filter; same confirmation response object used for exact algorithm comparison.'})
    if sum(r['data_kind']=='NEW_NATIVE_MEAN' for r in raw)!=16:raise ValueError('all sixteen new catalogues required')
    instances=[];streams=[]
    for i,row in enumerate(raw):
        q=len(row['weights']);f0=[max(F(c['values'][t]) for c in row['configurations'] if set(c['support'])<=set(row['history'])) for t in range(q)]
        levels=[sorted({F(c['values'][t]) for c in row['configurations'] if f0[t]<=F(c['values'][t])<=F(row['cap'][t])}) for t in range(q)]
        row.update(actual_N=len(row['slots']),actual_M=len(row['configurations']),Q=q,nominal_N_axis=None,
                   target=row['registered_target'],fixed_y=[str(max(v)) for v in levels],
                   fixed_y_selection='Coordinatewise largest response between current frontier and cap, common given exact y for all methods; no claim it is jointly attainable.',
                   unique_response_levels=[len(v) for v in levels])
        for mode in ('fixed_y','unknown_y'):
            inst={**row,'instance_id':row['instance_id']+'__'+mode,'workflow':mode}
            instances.append(inst)
            if mode=='unknown_y':streams.append(query_stream(inst,49627000+i))
    (output/'BENCHMARK_INSTANCES.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in instances))
    (output/'QUERY_STREAMS.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in streams))
    (output/'REGISTRY_HASHES.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.glob('*.jsonl')},indent=2)+'\n')
    print(json.dumps({'underlying_histories':len(raw),'inherited':8,'new':16,'matched_questions':len(instances),'query_histories':len(streams),'directory':str(output)}))


def main():
    p=argparse.ArgumentParser();p.add_argument('--analysis',required=True);p.add_argument('--inherited',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();register(a.analysis,a.inherited,a.output)

if __name__=='__main__':main()
