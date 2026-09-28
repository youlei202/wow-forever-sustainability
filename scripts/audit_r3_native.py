#!/usr/bin/env python3
"""Verify every R3 physical receipt once; atlas reuse contributes no new battles."""
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import runpy
from wowfs.paths import SOURCE_ROOT, setup_paths, atomic_json

audit=runpy.run_path(str(SOURCE_ROOT/'scripts/audit_r2_native.py'))
sha,read,directories,audit_cache=(audit[n] for n in ('sha','read','directories','audit_cache'))

def main():
    root=setup_paths();out=root/'artifacts/r3-gold';start=datetime.now(timezone.utc)
    folder=root/'runs/r3-gold'/('audit-'+start.strftime('%Y%m%dT%H%M%S%fZ'));folder.mkdir()
    cache=root/'cache/r3-gold/native';before=directories(cache);counts=Counter();problems=[]
    by_context=defaultdict(lambda:{'native_calls':0,'physical_battles':0});calls=battles=0
    ledger=folder/'CACHE_LEDGER.jsonl.gz'
    with gzip.open(ledger,'wt') as stream,ThreadPoolExecutor(max_workers=24) as pool:
        for row in pool.map(audit_cache,before):
            stream.write(json.dumps(row,sort_keys=True)+'\n');counts[row['status']]+=1
            if row['status']!='verified_completed':problems.append(row);continue
            calls+=1;battles+=row['verified_physical_battles']
            for cls,race in row['contexts']:
                by_context[cls+'/'+race]['native_calls']+=1
                by_context[cls+'/'+race]['physical_battles']+=row['verified_physical_battles']
    bridge=[]
    for rel in ('variant-smoke/VARIANT_SMOKE_RECEIPT.json','variant-nr-check/NR_NOOP_CHECK.json'):
        receipt,rh=read(root/'runs/r3-gold'/rel)
        for record in receipt['records']:
            command=record['command'];inp=Path(command[command.index('-in')+1]);raw=Path(command[command.index('-out')+1])
            iv,ih=read(inp);ov,oh=read(raw);n=iv['request']['simOptions']['iterations']
            if ih!=record['input_sha256'] or oh!=record['output_sha256'] or ov.get('error') or ov['iterationsDone']!=n:
                raise ValueError('Engineering receipt mismatch '+str(inp))
            if iv['request']['simOptions'].get('saveAllValues',False) and len(ov['raidMetrics']['parties'][0]['players'][0]['dps']['allValues'])!=n:
                raise ValueError('Engineering requested raw samples incomplete')
            bridge.append({'input_path':str(inp),'output_path':str(raw),'input_sha256':ih,'output_sha256':oh,
                           'iterations':n,'receipt_sha256':rh,'status':'verified_completed'})
    snapshots=[]
    for pp in sorted((root/'runs/r3-gold').glob('*/PROTOCOL.json')):
        protocol,ph=read(pp);progress=read(pp.parent/'PROGRESS.json')[0] if (pp.parent/'PROGRESS.json').exists() else {'status':'missing'}
        snapshot={'run':pp.parent.name,'protocol_sha256':ph,'progress':progress,'logical_cells':protocol['logical_cells']}
        if (pp.parent/'RESULTS.json').exists():
            result,rh=read(pp.parent/'RESULTS.json');snapshot.update(results_sha256=rh,errors=result['errors'],rows=len(result['rows']),missing_rows=sum(r is None for r in result['rows']))
        snapshots.append(snapshot)
    after=directories(cache);pending=[s['run'] for s in snapshots if s['progress']['status']!='complete' or s.get('errors') or s.get('missing_rows')]
    result={'started_utc':start.isoformat(),'finished_utc':datetime.now(timezone.utc).isoformat(),
        'snapshot_complete_and_quiescent':before==after and not pending and not problems,
        'cache_states':dict(counts),'cache_verified_native_calls':calls,'cache_verified_physical_battles':battles,
        'engineering_native_calls':len(bridge),'engineering_physical_battles':sum(r['iterations'] for r in bridge),
        'total_new_r3_native_calls':calls+len(bridge),'total_new_r3_physical_battles':battles+sum(r['iterations'] for r in bridge),
        'r2_atlas_reused_cells':35928,'r2_atlas_new_physical_battles':0,
        'audit_errors':len(problems),'problems':problems,'pending_runs':pending,'run_snapshots':snapshots,
        'engineering_ledger':bridge,'by_context_cache_only':dict(by_context),
        'ledger_path':str(ledger),'ledger_sha256':sha(ledger.read_bytes()),'auditor_sha256':sha(Path(__file__).read_bytes()),
        'counting':'Distinct binary+full-input completed physical receipts, plus9uncached engineering calls. No cache-hit/method/trajectory multiplication.',
        'limits':'One retained invocation per cache key; no invented count for unretained attempts. R2 audit remains separate. Human/Orc Warrior only.'}
    atomic_json(folder/'AUDIT.json',result);atomic_json(out/'INDEPENDENT_NATIVE_AUDIT.json',result)
    print(json.dumps({k:result[k] for k in ('snapshot_complete_and_quiescent','total_new_r3_native_calls','total_new_r3_physical_battles','audit_errors','pending_runs')},indent=2))
    if not result['snapshot_complete_and_quiescent']:raise SystemExit(2)

if __name__=='__main__':main()
