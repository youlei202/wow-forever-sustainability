"""Read-only completed-run resource, seed, coverage and frozen-source ledger."""
from collections import Counter,defaultdict
from copy import deepcopy
from datetime import datetime,timezone
import argparse,hashlib,json
from pathlib import Path
from wowfs.paths import SOURCE_ROOT,canonical_hash
from wowfs.experiments.fc_native import contexts


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def main(root):
    checks=root/'checks';stamp=datetime.now(timezone.utc).isoformat()
    manifest_path=root/'CONFIRMATION_MANIFEST_V2.json';manifest=json.loads(manifest_path.read_text())
    receipts=[json.loads(s) for s in (root/'RUN_RECEIPTS.jsonl').read_text().splitlines()]
    per=defaultdict(list)
    for row in receipts:per[row['batch_id']].append(row)
    batches=[];allrows=[];designs=defaultdict(set);blocks=[];issues=[];sources=[]
    for folder in sorted((root/'batches').iterdir()):
        if not (folder/'PROTOCOL.json').exists():continue
        proto=json.loads((folder/'PROTOCOL.json').read_text());jobs=json.loads((folder/'JOBS.json').read_text())
        if canonical_hash(jobs)!=proto['jobs_sha256']:issues.append([folder.name,'jobs hash'])
        if not (folder/'PROGRESS.json').exists():
            batches.append({'batch':folder.name,'status':'not_run','declared_jobs':len(jobs),'completed_native_calls':0});continue
        progress=json.loads((folder/'PROGRESS.json').read_text())
        if progress['status']!='completed':raise ValueError('Run still incomplete: '+folder.name)
        rows=json.loads((folder/'OBSERVATION_INDEX.json').read_text())
        if len(rows)!=len(jobs):raise ValueError('Index/job count differs')
        successful=[x for x in per[folder.name] if x['status']=='completed']
        failures=[x for x in per[folder.name] if x['status']=='failed']
        rowskeys={x['physical_key'] for x in rows}
        if rowskeys!={x['physical_key'] for x in successful}:issues.append([folder.name,'physical receipt/index mismatch'])
        source_checks={rel:sha(folder/'source'/rel)==v for rel,v in proto['source_hashes'].items()}
        binary_ok=sha(folder/'native.frozen')==proto['binary_sha256']
        sources.append({'batch':folder.name,'protocol_sha256':sha(folder/'PROTOCOL.json'),
            'frozen_source_matches':source_checks,'frozen_binary_matches':binary_ok,
            'frozen_binary_sha256':proto['binary_sha256']})
        if not all(source_checks.values()) or not binary_ok:issues.append([folder.name,'frozen source/binary mismatch'])
        for job,row in zip(jobs,rows):
            if canonical_hash(job['input'])!=row['input_sha256'] or any(row.get(k)!=v for k,v in job['meta'].items()):
                issues.append([folder.name,'row identity mismatch'])
            inp=deepcopy(job['input']);opts=inp['request']['simOptions'];s=int(opts['randomSeed']);n=int(opts['iterations'])
            blocks.append({'batch':folder.name,'phase':proto['phase'],'world':row['world_id'],'start':s,'end':s+n-1,'N':n})
            for key in ('randomSeed','iterations','debug','debugFirstIteration'):opts.pop(key,None)
            design=canonical_hash({'binary':proto['binary_sha256'],'input_without_seed_N_debug':inp})
            designs[design].add(folder.name)
        allrows.extend(rows)
        batches.append({'batch':folder.name,'phase':proto['phase'],'status':progress['status'],
            'logical_rows':len(rows),'physical_requests':len(rowskeys),'completed_native_calls':len(successful),
            'completed_battles':sum(x['iterations'] for x in successful),'failed_native_calls':len(failures),
            'failed_unknown_completed_battles':progress.get('failed_calls_with_unknown_completed_battles',0),
            'cache_hits_this_invocation':progress['cache_hits_this_invocation'],
            'native_invocation_seconds_sum':sum(x['elapsed_seconds'] for x in successful),
            'batch_elapsed_seconds':progress['elapsed_seconds_this_invocation'],'finished_utc':progress['utc'],
            'end_memory_current_bytes':progress['memory_current']})
    good=[x for x in receipts if x['status']=='completed'];fail=[x for x in receipts if x['status']=='failed']
    tracked={x['batch_id'] for x in receipts if x['status']=='started'};active=maximum=0
    for x in receipts:
        if x['batch_id'] not in tracked:continue
        active+=(1 if x['status']=='started' else -1 if x['status'] in ('completed','failed') else 0);maximum=max(maximum,active)
    resource={'audit_utc':stamp,'scope':'Completed native requests; analysis CPU and preexisting environment memory not attributed as native work.',
        'batches':batches,'successful_native_calls':len(good),'completed_battles':sum(x['iterations'] for x in good),
        'failed_native_calls':len(fail),'logical_observation_rows':len(allrows),
        'unique_complete_physical_requests':len({x['physical_key'] for x in allrows}),
        'distinct_encoded_design_inputs_without_seed_N_debug':len(designs),
        'design_deduplication':'Hash binary plus full request envelope after deleting only randomSeed, iterations, debug, debugFirstIteration. All other mechanical inputs retained. This is encoded input identity, not proof of different response functions.',
        'native_invocation_seconds_sum':sum(x['elapsed_seconds'] for x in good),
        'max_simultaneous_started_invocations_observed':maximum,'started_not_closed_at_audit':active,
        'concurrency_tracking_limitation':'First 108 smoke/benchmark calls predate started receipts; their durations/counts remain in successful receipts.',
        'campaign_budget':json.loads((root/'CAMPAIGN.json').read_text()),
        'campaign_time_interpretation':{
            'budget_origin_utc':json.loads((root/'ENVIRONMENT.json').read_text())['utc'],
            'authoritative_elapsed_origin':'CAMPAIGN.started_epoch, taken from ENVIRONMENT.utc',
            'started_utc_field':'CAMPAIGN.started_utc is the later campaign-record creation time at the first native batch call, not the elapsed-budget origin.',
            'deadline_rule':'deadline_epoch = started_epoch + max_wall_hours * 3600; the earlier origin includes setup and does not extend the budget.',
            'source':'src/wowfs/experiments/oe_runner.py:campaign'},
        'max_batch_end_memory_current_bytes':max(x.get('end_memory_current_bytes',0) for x in batches),
        'memory_limitation':'Cgroup memory at batch completion, not process-only memory or an observed peak.',
        'receipts_sha256':sha(root/'RUN_RECEIPTS.jsonl'),'issues':issues}
    unique_blocks={tuple(b[k] for k in ('batch','phase','world','start','end','N')) for b in blocks}
    unique_blocks=[dict(zip(('batch','phase','world','start','end','N'),v)) for v in sorted(unique_blocks)]
    develop=[b for b in unique_blocks if b['phase']!='confirm'];confirm=[b for b in unique_blocks if b['phase']=='confirm']
    overlaps=[{'confirm':a,'development':b} for a in confirm for b in develop if a['start']<=b['end'] and b['start']<=a['end']]
    cross=[{'a':a,'b':b} for i,a in enumerate(confirm) for b in confirm[i+1:] if a['world']!=b['world'] and a['start']<=b['end'] and b['start']<=a['end']]
    seed={'audit_utc':stamp,'method':'Closed integer intervals seed..seed+N-1; global no-overlap is stronger than physical-design-conditioned no-overlap.',
        'all_declared_executed_blocks':unique_blocks,'confirmation_vs_development_overlaps':overlaps,
        'between_confirmation_world_overlaps':cross,'all_seed_starts_positive':all(b['start']>0 for b in unique_blocks),
        'paired_use_within_world':'The same seed block is intentionally reused across configurations/tasks. These are paired observations; total battle count is not independent sample size.',
        'fixed_confirmation_N_by_claim':{c['claim_id']:c['iterations'] for c in manifest['claims']}}
    registered=[]
    for name in ('WORLD_REGISTRY.jsonl','WORLD_REGISTRY_CATALOG.jsonl'):
        registered.extend(json.loads(s) for s in (root/name).read_text().splitlines() if s.strip())
    mainids={w['world_id'] for w in registered}|{w['world_id'] for w in manifest['worlds']}
    observed_ids={r['world_id'] for r in allrows};observed_contexts={r['context_id'] for r in allrows}
    maincontexts={r['context_id'] for r in allrows if r['world_id'] in mainids}
    counts=Counter(r['world_id'] for r in allrows)
    coverage={'audit_utc':stamp,'registered_original_research_worlds':96,'registered_actual_catalog_worlds':12,
        'new_heldout_worlds':sum(c['role']=='heldout' for c in manifest['claims']),
        'main_study_world_ID_union':len(mainids),'observed_main_study_world_ID_union':len(mainids&observed_ids),
        'raw_all_batches_world_ID_union':len(observed_ids),'auxiliary_world_IDs':sorted(observed_ids-mainids),
        'main_context_count':len(maincontexts),'all_observed_context_count_including_smoke':len(observed_contexts),
        'class_race_coverage':[dict(c,execution_status='main_mechanism_exploration' if c['context_id'] in maincontexts else 'smoke_only' if c['context_id'] in observed_contexts else 'not_run') for c in contexts()],
        'logical_rows_per_world_ID':dict(counts),
        'distinct_encoded_design_inputs_without_seed_N_debug':len(designs),
        'physical_worlds_with_full_tables':'48 refined research worlds + 12 catalog worlds + 4 heldout worlds. Original 96-world broad stage alone has only anchor tables.',
        'limitations':['World IDs combine strata, race replications and parameter settings; not independent mechanisms.',
            'The same physical table was reinterpreted under new explicit initial publication histories; this is not a new native world or extra observations.',
            'Recorded engine equipment acceptance is separate from independently verified acquisition; see FACTION_GEAR_AUDIT.']}
    provenance={'audit_utc':stamp,'status':'passed' if not issues else 'issues_found','successful_batch_source_checks':sources,
        'confirmation_manifest_sha256':sha(manifest_path),'confirmation_preflight_sha256':sha(checks/'CONFIRMATION_PREFLIGHT_V2.json'),
        'confirmation_result_sha256':sha(root/'batches/confirm-v2/RESULTS.json'),
        'development_raw_verification':'checks/INDEPENDENT_AUDIT_EVIDENCE_v2.json verifies 13,596 raw outputs.',
        'confirmation_raw_verification':'analysis/confirm-v2-compact-moments/MOMENTS_MANIFEST.json independently verifies the 960 raw outputs; consult that receipt when export is complete.',
        'issues':issues}
    for name,data in [('RESOURCE_USE.json',resource),('SEED_OVERLAP.json',seed),('COVERAGE_ACCOUNTING.json',coverage),('POST_CONFIRMATION_PROVENANCE.json',provenance)]:
        (checks/name).write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'calls':resource['successful_native_calls'],'battles':resource['completed_battles'],'logical':len(allrows),'designs':len(designs),'main_worlds':len(mainids&observed_ids),'all_world_IDs':len(observed_ids),'max_concurrent':maximum,'seed_overlaps':len(overlaps)+len(cross),'issues':issues}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);main(p.parse_args().root)
