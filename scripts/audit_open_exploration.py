"""Read-only accounting/provenance audit of the current exploration snapshot.

Run after sourcing scripts/env.sh. Outputs belong under WOWFS_WORK_ROOT. Native
simulations are never launched. The audit excludes confirmation batches so it
cannot choose, certify, or spend error budget on a final scientific claim.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path

from wowfs.paths import SOURCE_ROOT, canonical_hash
from wowfs.experiments.r2_native import summarize


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit(root, output, verify_raw=False):
    root=Path(root); evidence={}; batches=[]; issues=[]; physical={}; logical=0
    contexts=set(); mechanism_contexts=set(); mechanisms=set(); worlds=set()
    def read(path):
        evidence[str(path.relative_to(root))]=digest(path)
        return json.loads(path.read_text())
    for directory in sorted((root/'batches').iterdir()):
        if not directory.is_dir() or not (directory/'PROTOCOL.json').exists():continue
        protocol=read(directory/'PROTOCOL.json')
        if protocol.get('phase')=='confirm':continue
        jobs=read(directory/'JOBS.json')
        entry={'batch':directory.name,'phase':protocol.get('phase'),
               'declared_logical_jobs':len(jobs),'jobs_hash_matches_protocol':canonical_hash(jobs)==protocol['jobs_sha256'],
               'binary_sha256':protocol.get('binary_sha256'),'frozen_source_checks':[],
               'live_source_differs':[]}
        for rel,expected in protocol['source_hashes'].items():
            frozen=directory/'source'/rel
            actual=digest(frozen) if frozen.exists() else None
            entry['frozen_source_checks'].append({'file':rel,'expected':expected,'actual':actual,'matches':actual==expected})
            live=SOURCE_ROOT/rel
            if not live.exists() or digest(live)!=expected:entry['live_source_differs'].append(rel)
        binary=directory/'native.frozen'
        entry['frozen_binary_matches']=binary.exists() and digest(binary)==protocol.get('binary_sha256')
        if (directory/'FREEZE_FAILURE.json').exists():entry['freeze_failure']=read(directory/'FREEZE_FAILURE.json')
        if not (directory/'RESULTS.json').exists():
            entry.update(status='not_run',observed_logical_rows=0,observed_physical_keys=0,observed_battles=0)
            batches.append(entry);continue
        data=read(directory/'RESULTS.json');progress=read(directory/'PROGRESS.json')
        rows=data['rows']; observed=[x for x in rows if x is not None]
        unique={row['physical_key']:row for row in observed}
        entry.update(status=data.get('status'),errors=data.get('errors'),
                     observed_logical_rows=len(observed),missing_rows=len(rows)-len(observed),
                     observed_physical_keys=len(unique),observed_battles=sum(x['iterations'] for x in unique.values()),
                     cache_hits_reported=progress.get('cache_hits_this_invocation'),
                     progress=progress,worlds=sorted({x['world_id'] for x in observed}),
                     contexts=sorted({x['context_id'] for x in observed}),
                     mechanisms=sorted({x['mechanism_id'] for x in observed}))
        checks=Counter()
        if len(rows)!=len(jobs):issues.append({'batch':directory.name,'error':'row/job length mismatch'})
        for job,row in zip(jobs,rows):
            if row is None:continue
            checks['observed_rows']+=1
            expected=canonical_hash({'binary':protocol['binary_sha256'],'input':job['input']})
            tests={'input_hash':canonical_hash(job['input'])==row.get('input_sha256'),
                   'physical_key':expected==row.get('physical_key'),
                   'binary':row.get('binary_sha256')==protocol['binary_sha256'],
                   'actual_observed':row.get('observed_or_reconstructed')=='observed',
                   'sample_count':len(row['dps_samples'])==row['iterations']==job['input']['request']['simOptions']['iterations'],
                   'metadata':all(row.get(k)==v for k,v in job['meta'].items())}
            for key,passed in tests.items():
                checks[key+'_passed']+=bool(passed)
                if not passed:issues.append({'batch':directory.name,'physical_key':expected,'error':key})
            contexts.add(row['context_id']);worlds.add(row['world_id'])
            if protocol['phase']!='audit':
                mechanism_contexts.add(row['context_id']);mechanisms.add(row['mechanism_id'])
        entry['row_checks']=dict(checks)
        for key,row in unique.items():
            if key in physical and physical[key]['dps_samples']!=row['dps_samples']:
                issues.append({'batch':directory.name,'physical_key':key,'error':'identical physical request has different output'})
            physical.setdefault(key,row)
        logical+=len(observed);batches.append(entry)
    names={x['batch'] for x in batches}
    receipt_path=root/'RUN_RECEIPTS.jsonl';evidence['RUN_RECEIPTS.jsonl']=digest(receipt_path)
    receipts=[json.loads(line) for line in receipt_path.read_text().splitlines()]
    receipts=[r for r in receipts if r['batch_id'] in names]
    completed=[r for r in receipts if r['status']=='completed']
    raw={'requested':verify_raw,'unique_outputs_checked':0,'issues':[]}
    if verify_raw:
        for i,(key,row) in enumerate(physical.items(),1):
            try:
                directory=Path(row['cache_directory']);request=json.loads((directory/'input.json').read_text())
                with gzip.open(directory/'output.json.gz','rb') as stream:payload=stream.read()
                if hashlib.sha256(payload).hexdigest()!=row['output_sha256']:raise ValueError('raw output hash mismatch')
                if canonical_hash(request)!=row['input_sha256']:raise ValueError('cached input hash mismatch')
                measured=summarize(json.loads(payload),request)
                if any(row.get(k)!=v for k,v in measured.items()):raise ValueError('summary differs from complete native raw output')
                raw['unique_outputs_checked']+=1
            except Exception as exc:raw['issues'].append({'physical_key':key,'error':repr(exc)})
            if i%2000==0:print(json.dumps({'raw_verified':raw['unique_outputs_checked'],'of':len(physical)}),flush=True)
    summaries={}
    for path in sorted((root/'analysis').glob('*/SUMMARY.json')):
        if 'confirm' not in str(path):summaries[str(path.parent.relative_to(root))]=read(path)
    challenges=[]
    for name in ('catalog-full-domain-challenge-v1','refine-full-domain-batch-challenge-v1','deep-full-domain-challenge-v1'):
        path=root/'analysis'/name/'RESULTS.json'
        if not path.exists():continue
        for case in read(path):
            compact=lambda x:{k:x.get(k) for k in ('status','capacity_lower','capacity_upper','batches','retention_enforced')}
            challenges.append({'evidence':str(path.relative_to(root)),'case':case['case'],
                'full_unpublished_candidates':case['full_unpublished_candidates'],
                'full_declared_world_observed':case['domain']['full_declared_world_observed'],
                'global':{k:compact(v) for k,v in case['global'].items()},
                'conditional':[{'first_batch':c['first_batch'],'first_state':c['first_state'],
                    'continuations':{k:compact(v) for k,v in c['continuations'].items()}} for c in case['conditional']]})
    baseline_path=root/'analysis/full-baseline-challenge-v1/RESULTS.json'
    baseline_challenges=[]
    if baseline_path.exists():
        for item in read(baseline_path):
            baseline_challenges.append({k:v for k,v in item.items() if k not in ('domain','methods','exact','baselines')})
    supplementary={}
    for relative in ('analysis/deep-joint-mechanism-audit-v1/SELECTED_MECHANISMS.json',
                     'analysis/deep-joint-mechanism-audit-v1/256_512_4096_HISTORY.json',
                     'FACTION_GEAR_AUDIT.json'):
        if (root/relative).exists():supplementary[relative]=read(root/relative)
    diagnostic_counts={}
    for name in ('broad-v2','refine-v1','catalog-v1'):
        rows=read(root/'batches'/name/'DIAGNOSTICS.json')
        diagnostic_counts[name]={'worlds':len(rows),'full_tensor_observed':sum(r['full_tensor_observed'] for r in rows),
            'mixed_contrast_above_half_percent':sum(r['max_relative_mixed_contrast']>.005 for r in rows),
            'worlds_with_best_partner_task_change':sum(r['rows_with_different_best_partner_across_tasks']>0 for r in rows),
            'interpretation':'Adaptive point diagnostics, not confirmed decision effects or independent mechanism counts.'}
    result={'audit_utc':datetime.now(timezone.utc).isoformat(),'scope':'Snapshot of development/audit/challenge batches only; confirmation claims not assessed.',
            'script_sha256':digest(Path(__file__)),'batches':batches,'totals':{
                'observed_logical_rows':logical,'unique_physical_requests':len(physical),
                'unique_request_battles':sum(x['iterations'] for x in physical.values()),
                'completed_invocations':len(completed),'completed_invocation_battles':sum(x['iterations'] for x in completed),
                'receipt_status_counts':dict(Counter(x['status'] for x in receipts)),
                'failed_receipts':[x for x in receipts if x['status']=='failed'],
                'observed_contexts_including_smoke':sorted(contexts),'mechanism_exploration_contexts':sorted(mechanism_contexts),
                'executed_mechanism_labels':sorted(mechanisms),'distinct_observed_world_ids_including_smoke':len(worlds)},
            'row_integrity_issues':issues,'raw_integrity':raw,'diagnostic_counts':diagnostic_counts,
            'analysis_summaries':summaries,'full_domain_challenges':challenges,
            'full_baseline_challenges':baseline_challenges,'supplementary_audits':supplementary,
            'evidence_file_hashes':evidence,
            'limitations':['Logical aliases are not extra physical observations.',
                'Different seeds, tasks, strata, thresholds and race replicas do not create independent discoveries.',
                'Complete native tables and exact combinatorial mean-table solves do not certify population hypotheses.',
                'Native item/faction tags do not independently establish live acquisition or fidelity.']}
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')
    print(json.dumps({'output':str(output),'totals':result['totals'],'row_issues':len(issues),'raw_checked':raw['unique_outputs_checked'],'raw_issues':len(raw['issues'])}),flush=True)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--verify-raw',action='store_true')
    args=p.parse_args();audit(args.root,args.output,args.verify_raw)
