#!/usr/bin/env python3
"""Independent retained-receipt and frozen-input audit for decisive-value.

Reuses the prior streaming JSON and raw native receipt validators read-only.
The new namespace is audited independently; analysis-only cache screens add no
native calls. Numerical ecological claims require their separate analysis.
"""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import runpy

from wowfs.paths import SOURCE_ROOT, setup_paths, atomic_json

STAGE='decisive-value'
ORIGINS={STAGE,'r6-theory-native','r4-foundational-discovery','r3-gold','r2-discovery'}
shared=runpy.run_path(str(SOURCE_ROOT/'scripts/audit_r6_native.py'))
archive_shared=shared['shared']
archive_shared['native_snapshot'].__globals__.update(
    STAGE=STAGE,ORIGINS=ORIGINS,provenance_checks=shared['provenance_checks'])
shared['seed_accounting'].__globals__.update(STAGE=STAGE,ORIGINS=ORIGINS)
file_hash,read,directories,receipt_signature=(shared[k] for k in
    ('file_hash','read','directories','receipt_signature'))


def audit_receipt(path):
    return shared['audit_receipt'](path)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--workers',type=int,default=16)
    parser.add_argument('--require-complete',action='store_true');args=parser.parse_args()
    root=setup_paths();started=datetime.now(timezone.utc)
    folder=root/'runs'/STAGE/('audit-'+started.strftime('%Y%m%dT%H%M%S%fZ'))
    folder.mkdir(parents=True)
    cache=root/'cache'/STAGE/'native';before=directories(cache)
    protocols_before=sorted(str(p) for p in (root/'runs'/STAGE).glob('*/PROTOCOL.json'))
    retained={};external={};states=Counter();problems=[];calls=battles=0
    contexts=defaultdict(lambda:{'calls':0,'battles':0})
    binaries=defaultdict(lambda:{'calls':0,'battles':0})
    ledger=folder/'CACHE_LEDGER.jsonl.gz'
    with gzip.open(ledger,'wt') as stream,ProcessPoolExecutor(max_workers=args.workers) as pool:
        for row in pool.map(audit_receipt,before,chunksize=16):
            stream.write(json.dumps(row,sort_keys=True)+'\n')
            retained[str(Path(row['path']).resolve())]=row;states[row['status']]+=1
            if row['status']!='verified_completed':problems.append(row);continue
            count=row['verified_physical_battles'];calls+=1;battles+=count
            binaries[row['binary_sha256']]['calls']+=1;binaries[row['binary_sha256']]['battles']+=count
            for cls,race in row['contexts']:
                contexts[cls+'/'+race]['calls']+=1;contexts[cls+'/'+race]['battles']+=count
    runs,analyses=archive_shared['snapshots'](root,retained,external)
    seeds=shared['seed_accounting'](root,runs,retained,external)
    reuse=folder/'EXTERNAL_REUSE_LEDGER.jsonl.gz'
    with gzip.open(reuse,'wt') as stream:
        for row in external.values():stream.write(json.dumps(row,sort_keys=True)+'\n')
    analysis_path=folder/'ANALYSIS_PROTOCOL_LEDGER.json'
    atomic_json(analysis_path,{'records':analyses,'physical_calls_added':0})
    changed=[];receipts={**retained,**external}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for path,current in zip(receipts,pool.map(receipt_signature,receipts)):
            if current!=receipts[path]['receipt_signature']:changed.append(path)
    after=directories(cache)
    protocols_after=sorted(str(p) for p in (root/'runs'/STAGE).glob('*/PROTOCOL.json'))
    pending=[x['run'] for x in runs if not x.get('archive_verified',False)]
    external_problems=[r for r in external.values() if r['status']!='verified_completed']
    complete=(before==after and protocols_before==protocols_after and not changed
              and not pending and not problems and not external_problems)
    result={'schema':1,'started_utc':started.isoformat(),'finished_utc':datetime.now(timezone.utc).isoformat(),
        'snapshot_complete_and_quiescent':complete,'native_calls':calls,'physical_battles':battles,
        'cache_states':dict(states),'failed_invocations':states['failed_invocation'],
        'incomplete_invocations':states['incomplete'],'audit_errors':states['audit_error'],
        'pending_runs':pending,'problems':problems,'external_reuse_problems':external_problems,
        'cache_listing_changed':before!=after,'protocol_listing_changed':protocols_before!=protocols_after,
        'changed_receipts_after_validation':changed,'run_snapshots':runs,
        'analysis_protocol_count':len(analyses),'analysis_ledger_path':str(analysis_path),
        'analysis_ledger_sha256':file_hash(analysis_path),'external_reuse_receipts':len(external),
        'by_context':dict(contexts),'by_binary_sha256':dict(binaries),'seed_accounting':seeds,
        'ledger_path':str(ledger),'ledger_sha256':file_hash(ledger),
        'external_reuse_ledger_path':str(reuse),'external_reuse_ledger_sha256':file_hash(reuse),
        'auditor_sha256':file_hash(Path(__file__)),
        'shared_auditor_hashes':{name:file_hash(SOURCE_ROOT/'scripts'/name) for name in
            ('audit_r6_native.py','audit_r4_native.py','audit_r2_native.py')},
        'counting':'Each distinct verified retained decisive-value physical binary+input receipt once. Reused R4 development tables, logical comparisons, theoretical checks and aliases add zero new native battles.',
        'limits':'Only actual native class/race contexts shown. Research parameter aliases retain existing native item IDs and are not official catalogue releases. Raw outputs, samples, jobs, source snapshots, imported inputs and binary hashes are checked; scientific success and approximate inference are separate. No lost/unretained invocation is invented.'}
    atomic_json(folder/'AUDIT.json',result);atomic_json(folder/'SEED_OVERLAP.json',seeds)
    atomic_json(root/'artifacts'/STAGE/'NATIVE_AUDIT.json',result)
    atomic_json(root/'artifacts'/STAGE/'SEED_OVERLAP.json',seeds)
    print(json.dumps({k:result[k] for k in ('snapshot_complete_and_quiescent','native_calls',
        'physical_battles','failed_invocations','incomplete_invocations','audit_errors','pending_runs','by_context')},indent=2))
    if args.require_complete and not complete:raise SystemExit(2)


if __name__=='__main__':main()
