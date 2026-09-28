#!/usr/bin/env python3
"""Independent final-completion physical count and frozen input/source verification."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import runpy

from wowfs.paths import SOURCE_ROOT, setup_paths, atomic_json, canonical_hash

STAGE = 'final-completion-capacity'
ORIGINS = {STAGE, 'decisive-value', 'r6-theory-native', 'r4-foundational-discovery', 'r3-gold', 'r2-discovery'}
shared = runpy.run_path(str(SOURCE_ROOT/'scripts/audit_r4_native.py'))
file_hash, read, directories, receipt_signature = (
    shared[k] for k in ('file_hash','read','directories','receipt_signature'))


def provenance_checks(root, run, protocol, issues):
    checks=[]
    source_root=(run/'source').resolve()
    for group,mapping in [('source_hashes',protocol.get('source_hashes',{})),
                         ('science.source_hashes',protocol.get('science',{}).get('source_hashes',{}))]:
        for relative,expected in mapping.items():
            path=(source_root/relative).resolve()
            actual=file_hash(path) if path.is_relative_to(source_root) and path.is_file() else None
            issues.require(actual==expected,'source_hash_mismatch',group+':'+relative)
            checks.append({'field':group+':'+relative,'expected':expected,'actual':actual})
    inputs=(run/'inputs').resolve()
    imported=protocol.get('imported_input_hashes',{})
    issues.require(bool(imported),'missing_imported_input_provenance')
    for relative,expected in imported.items():
        path=(inputs/relative).resolve()
        actual=file_hash(path) if path.is_relative_to(inputs) and path.is_file() else None
        issues.require(actual==expected,'imported_input_hash_mismatch',relative)
        checks.append({'field':'imported_input_hashes:'+relative,'expected':expected,'actual':actual})
    science=protocol.get('science',{})
    if 'formal_r5_sha256' in science:
        issues.require(science['formal_r5_sha256']==imported.get('r5-theory/THEORY.md'),
                       'formal_r5_reference_mismatch')
    if 'base_input_sha256' in science:
        base=inputs/'base_input.json'
        actual=canonical_hash(read(base)[0]) if base.is_file() else None
        issues.require(actual==science['base_input_sha256'],'base_input_canonical_hash_mismatch')
    return checks


# Reuse the independently checked streaming job/result/physical receipt join;
# change only this audit's stage and stage-specific provenance interpretation.
namespace=shared['native_snapshot'].__globals__
namespace.update(STAGE=STAGE,ORIGINS=ORIGINS,provenance_checks=provenance_checks)
snapshots=shared['snapshots']


def audit_receipt(path):
    row=shared['audit_receipt'](path)
    if row['status']=='verified_completed':
        add_seed_identity(row)
    return row


def add_seed_identity(row):
    value=read(Path(row['path'])/'input.json')[0]
    options=value['request']['simOptions']
    seed=int(options.pop('randomSeed',0));iterations=int(options.pop('iterations'))
    for flag in ('debug','debugFirstIteration','saveAllValues'):
        options.pop(flag,None)
    row['combat_design_sha256']=canonical_hash({'binary':row['binary_sha256'],'input':value})
    row['seed_interval_half_open']=[seed,seed+iterations]


def merge_intervals(intervals):
    merged=[]
    for start,stop in sorted(intervals):
        if merged and start<=merged[-1][1]:merged[-1][1]=max(stop,merged[-1][1])
        else:merged.append([start,stop])
    return merged


def interval_size(intervals):return sum(stop-start for start,stop in intervals)


def intersect_size(left,right):
    i=j=total=0
    while i<len(left) and j<len(right):
        total+=max(0,min(left[i][1],right[j][1])-max(left[i][0],right[j][0]))
        if left[i][1]<=right[j][1]:i+=1
        else:j+=1
    return total


def seed_accounting(root,runs,retained,external):
    all_rows={row['cache_key']:row for row in [*retained.values(),*external.values()]
              if row['status']=='verified_completed'}
    for row in all_rows.values():
        if 'combat_design_sha256' not in row:add_seed_identity(row)
    physical=defaultdict(list)
    for row in retained.values():
        if row['status']=='verified_completed':
            physical[row['combat_design_sha256']].append(row['seed_interval_half_open'])
    physical_unique=sum(interval_size(merge_intervals(v)) for v in physical.values())
    stage_rows={};stage_designs={};stage_seeds={}
    for run in runs:
        path=root/'runs'/STAGE/run['run']/'RESULTS.json'
        if not path.is_file():continue
        keys={row['cache_key'] for row in shared['stream_array'](path,'rows',{}) if row}
        designs=defaultdict(list);intervals=[];referenced_battles=0
        for key in keys:
            if key not in all_rows:continue
            row=all_rows[key];interval=row['seed_interval_half_open']
            designs[row['combat_design_sha256']].append(interval)
            intervals.append(interval);referenced_battles+=row['verified_physical_battles']
        designs={k:merge_intervals(v) for k,v in designs.items()}
        stage_designs[run['run']]=designs;stage_seeds[run['run']]=merge_intervals(intervals)
        stage_rows[run['run']]={'distinct_cache_receipts_referenced':len(keys),
            'battle_iterations_in_distinct_referenced_receipts':referenced_battles,
            'distinct_combat_designs':len(designs),
            'distinct_design_seed_observations':sum(interval_size(v) for v in designs.values()),
            'seed_union_half_open':stage_seeds[run['run']]}
    pairs=[];names=sorted(stage_rows)
    for i,left in enumerate(names):
        for right in names[i+1:]:
            common=intersect_size(stage_seeds[left],stage_seeds[right])
            same=sum(intersect_size(stage_designs[left][key],stage_designs[right][key])
                     for key in stage_designs[left].keys()&stage_designs[right].keys())
            pairs.append({'run_a':left,'run_b':right,'shared_seed_values_regardless_of_design':common,
                          'repeated_same_design_seed_observations':same,
                          'disjoint_seed_ranges':common==0})
    return {'physical_battle_iterations':sum(r['verified_physical_battles'] for r in retained.values()),
        'distinct_physical_combat_designs':len(physical),
        'distinct_physical_design_seed_observations':physical_unique,
        'duplicate_design_seed_iterations':sum(r['verified_physical_battles'] for r in retained.values())-physical_unique,
        'by_run':stage_rows,'pairwise_stage_seed_overlap':pairs,
        'identity':'Exact executable and complete native combat input excluding randomSeed, iterations and logging-only debug/debugFirstIteration/saveAllValues. No approximate parameter equivalence is assumed.',
        'interpretation':'Physical battles count every completed iteration actually executed. Repeated design+seed observations are not independent repetitions. Shared labeled seeds couple different designs too; zero exact-design duplication alone does not establish stage independence. Intervals follow native seed+i indexing.'}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--workers',type=int,default=16)
    parser.add_argument('--require-complete',action='store_true')
    args=parser.parse_args()
    root=setup_paths();started=datetime.now(timezone.utc)
    folder=root/'runs'/STAGE/('audit-'+started.strftime('%Y%m%dT%H%M%S%fZ'))
    folder.mkdir(parents=True)
    cache=root/'cache'/STAGE/'native'
    before=directories(cache)
    protocols_before=sorted(str(p) for p in (root/'runs'/STAGE).glob('*/PROTOCOL.json') if 'binary_sha256' in json.loads(p.read_text()))
    states=Counter();retained={};external={};problems=[]
    contexts=defaultdict(lambda:{'calls':0,'battles':0})
    binaries=defaultdict(lambda:{'calls':0,'battles':0})
    calls=battles=0
    ledger=folder/'CACHE_LEDGER.jsonl.gz'
    with gzip.open(ledger,'wt') as stream,ProcessPoolExecutor(max_workers=args.workers) as pool:
        for row in pool.map(audit_receipt,before,chunksize=32):
            stream.write(json.dumps(row,sort_keys=True)+'\n')
            retained[str(Path(row['path']).resolve())]=row;states[row['status']]+=1
            if row['status']!='verified_completed':problems.append(row);continue
            count=row['verified_physical_battles'];calls+=1;battles+=count
            binaries[row['binary_sha256']]['calls']+=1;binaries[row['binary_sha256']]['battles']+=count
            for cls,race in row['contexts']:
                contexts[cls+'/'+race]['calls']+=1;contexts[cls+'/'+race]['battles']+=count
    runs,analyses=snapshots(root,retained,external)
    seeds=seed_accounting(root,runs,retained,external)
    reuse=folder/'EXTERNAL_REUSE_LEDGER.jsonl.gz'
    with gzip.open(reuse,'wt') as stream:
        for row in external.values():stream.write(json.dumps(row,sort_keys=True)+'\n')
    atomic_json(folder/'ANALYSIS_PROTOCOL_LEDGER.json',{'records':analyses,'physical_calls_added':0})
    changed=[];all_receipts={**retained,**external}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for path,current in zip(all_receipts,pool.map(receipt_signature,all_receipts)):
            if current!=all_receipts[path]['receipt_signature']:changed.append(path)
    after=directories(cache)
    protocols_after=sorted(str(p) for p in (root/'runs'/STAGE).glob('*/PROTOCOL.json') if 'binary_sha256' in json.loads(p.read_text()))
    pending=[r['run'] for r in runs if not r.get('archive_verified',False)]
    external_problems=[r for r in external.values() if r['status']!='verified_completed']
    complete=(before==after and protocols_before==protocols_after and not changed
              and not pending and not problems and not external_problems)
    result={'schema':1,'started_utc':started.isoformat(),'finished_utc':datetime.now(timezone.utc).isoformat(),
        'snapshot_complete_and_quiescent':complete,'native_calls':calls,'physical_battles':battles,
        'cache_states':dict(states),'failed_invocations':states['failed_invocation'],
        'incomplete_invocations':states['incomplete'],'audit_errors':states['audit_error'],
        'pending_runs':pending,'problems':problems,'external_reuse_problems':external_problems,
        'cache_listing_changed':before!=after,'protocol_listing_changed':protocols_before!=protocols_after,
        'protocol_listing_scope':'Physical protocols only; concurrent read-only analysis ledgers do not add battles.',
        'changed_receipts_after_validation':changed,'run_snapshots':runs,
        'analysis_protocol_count':len(analyses),'external_reuse_receipts':len(external),
        'by_context':dict(contexts),'by_binary_sha256':dict(binaries),
        'seed_accounting':seeds,
        'ledger_path':str(ledger),'ledger_sha256':file_hash(ledger),
        'external_reuse_ledger_path':str(reuse),'external_reuse_ledger_sha256':file_hash(reuse),
        'auditor_sha256':file_hash(Path(__file__)),
        'shared_archive_validator_sha256':file_hash(SOURCE_ROOT/'scripts/audit_r4_native.py'),
        'shared_cache_validator_sha256':file_hash(SOURCE_ROOT/'scripts/audit_r2_native.py'),
        'counting':'Distinct retained final-completion native receipts once. Earlier-stage cache reuse, analysis-only protocols, interpolation and logical alias labels add zero native battles.',
        'limits':'Counts retained receipts, not hypothetical or lost attempts. Actual context coverage is listed explicitly. Native fixed-control research variants are not official catalogue items; abstract theory checks are never native combats. Summary ecological conclusions are audited separately.'}
    atomic_json(folder/'AUDIT.json',result)
    atomic_json(folder/'SEED_OVERLAP.json',seeds)
    atomic_json(root/'artifacts'/STAGE/'INDEPENDENT_NATIVE_AUDIT.json',result)
    atomic_json(root/'artifacts'/STAGE/'SEED_OVERLAP.json',seeds)
    print(json.dumps({k:result[k] for k in ['snapshot_complete_and_quiescent','native_calls',
        'physical_battles','failed_invocations','incomplete_invocations','audit_errors','pending_runs']},indent=2))
    if args.require_complete and not complete:raise SystemExit(2)


if __name__=='__main__':main()
