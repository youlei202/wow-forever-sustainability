#!/usr/bin/env python3
"""Build a compact research review, leaving native samples in WORK_ROOT.

No simulation, inference, hypothesis selection, or source modification occurs.
The archive contains traceable summaries, complete indices, frozen designs,
compact moments and executable analysis code. It deliberately excludes binaries
and per-seed raw results; their exact local paths and hashes remain in indices.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

from wowfs.paths import SOURCE_ROOT,atomic_json,canonical_hash
from wowfs.experiments.oe_catalog_worlds import CATALOG_POOLS


def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_write(path,rows):
    if not rows:return
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for row in rows:
            w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list,tuple)) else v for k,v in row.items()})


def package(run, output):
    if output.exists():raise ValueError('Review output exists; use a new review version')
    manifest_path=run/'CONFIRMATION_MANIFEST_V2.json';manifest=read(manifest_path)
    analysis=run/'analysis/confirm-v2-results'
    decisions=read(run/'CONFIRMED_CLAIMS.json')
    if read(analysis/'SUMMARY.json')['status']!='completed':raise ValueError('Confirmation analysis incomplete')
    output.mkdir(parents=True)
    def copy(src,rel=None):
        if not src.exists():raise FileNotFoundError(src)
        dest=output/(rel or src.name);dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src,dest)
    docs=SOURCE_ROOT/'docs/open-exploration-2026-09-26'
    for p in sorted(docs.glob('*.md')):copy(p)
    reading=['READ_FIRST.md','RESEARCH_JUDGMENT.md','INDEPENDENT_AUDIT.md',
             'THEORY_BACKLOG.md','PRIOR_WORK_DELTA.md','FIGURE_GUIDE_AND_CONFIRMED_MECHANISMS.md']
    book=['# WoW Forever Open Exploration: Compact Review Document\n\n'
          'This document combines research conclusions, the independent audit, theoretical limits, and key counterevidence for standalone review. '
          'Raw samples are not included here; the complete compact reproduction package contains frozen parameters, code, means/covariances, and data indices. '
          'Distinguish finite-simulator conclusions, research stat variants, and unmodified native equipment.\n']
    book.extend('\n---\n\n<!-- Source: '+name+' -->\n\n'+(docs/name).read_text() for name in reading)
    (output/'GPT_PRO_REVIEW.md').write_text(''.join(book))
    for name in ['ENVIRONMENT.json','INPUTS_MANIFEST.json','ENGINE_SUPPORT_MATRIX.csv',
                 'RUN_RECEIPTS.jsonl',
                 'SEED_OVERLAP.json','RESOURCE_USE.json','CONFIRMED_CLAIMS.json',
                 'FACTION_GEAR_AUDIT.csv','CONFIRMATION_V1_NOT_RUN.json']:
        copy(run/name)
    copy(manifest_path,'CONFIRMATION_MANIFEST.json')
    copy(run/'batches/confirm-v2/JOBS.json','confirmation/JOBS.json')
    copy(run/'CONFIRMATION_MANIFEST.json','pre_sampling_superseded/CONFIRMATION_MANIFEST_V1.json')
    inventory=[];observations=[];worlds=[];atlas=[]
    for batch in sorted((run/'batches').iterdir()):
        if not (batch/'PROGRESS.json').exists():
            if (batch/'FREEZE_FAILURE.json').exists():
                copy(batch/'FREEZE_FAILURE.json','batches/'+batch.name+'/FREEZE_FAILURE.json')
            continue
        progress=read(batch/'PROGRESS.json')
        inventory.append(progress)
        for name in ('PROGRESS.json','PROTOCOL.json','FREEZE_TIME.json'):
            copy(batch/name,'batches/'+batch.name+'/'+name)
        index=batch/'OBSERVATION_INDEX.json'
        if index.exists():
            observations.extend({'batch_id':batch.name,**row} for row in read(index))
        diag=batch/'DIAGNOSTICS.json'
        if diag.exists():atlas.extend({'batch_id':batch.name,**row} for row in read(diag))
    fields=['batch_id','world_id','world_sha256','mechanism_id','lineage_id','context_id',
        'model_scope','parameter_scope','candidate_id','partner_id','task_id','policy_id',
        'source_ids','native_source_item_ids','class','race','faction','phase',
        'seed_block_id','iterations','dps_mean','dps_se','input_sha256','binary_sha256',
        'output_sha256','physical_key','cache_key','cache_directory','cache_hit',
        'observed_or_reconstructed','physical_legality']
    with (output/'OBSERVATION_INDEX.jsonl').open('w') as f:
        for row in observations:f.write(json.dumps({k:row[k] for k in fields if k in row},sort_keys=True)+'\n')
    for name in ('WORLD_REGISTRY.jsonl','WORLD_REGISTRY_CATALOG.jsonl','DEEP_CHALLENGE_REGISTRY.jsonl','POLICY_CHALLENGE_REGISTRY.jsonl'):
        for row in map(json.loads,(run/name).read_text().splitlines()):
            worlds.append({'registry_source':name,**row})
    worlds.extend({'registry_source':'CONFIRMATION_MANIFEST_V2.json',**w} for w in manifest['worlds'])
    (output/'WORLD_REGISTRY.jsonl').write_text(''.join(json.dumps(w,sort_keys=True)+'\n' for w in worlds))
    aliases=[];seen=set()
    for world in worlds:
        identity=(world['world_id'],world['world_sha256'])
        if identity in seen:continue
        seen.add(identity)
        for collection in ('candidates','partners'):
            aliases.extend({'world_id':world['world_id'],'world_sha256':world['world_sha256'],
                'mechanism_id':world['mechanism_id'],'index':i,'kind':collection[:-1],**alias}
                for i,alias in enumerate(world[collection]))
    (output/'CANDIDATE_LINEAGES.jsonl').write_text(''.join(json.dumps(x,sort_keys=True)+'\n' for x in aliases))
    with (run/'HYPOTHESIS_REGISTER.csv').open() as f:hypotheses=list(csv.DictReader(f))
    for name,pool in CATALOG_POOLS.items():
        hypotheses.append({'mechanism_id':name,'mechanism_label':name,'hypothesis':pool['hypothesis'],
            'native_source':pool['source_files'],'hooks':'actual_catalog_items_no_overrides',
            'support_status':'supported_source_with_documented_limits','limitations':pool['limitations']})
    csv_write(output/'HYPOTHESIS_REGISTER.csv',hypotheses)
    csv_write(output/'ENGINE_SUPPORT_MATRIX.csv',hypotheses)
    for decision,claim in zip(decisions['claims'],manifest['claims']):
        atlas.append({'batch_id':'confirm-v2','world_id':decision['world_id'],
            'mechanism_id':next(w['mechanism_id'] for w in manifest['worlds'] if w['world_id']==decision['world_id']),
            'status':decision['status'],'claim_status':decision['conditions'],
            'full_tensor_observed':True,'model_scope':claim['model_scope'],
            'role':claim['role'],'not_independent_prevalence_sample':True})
    csv_write(output/'MECHANISM_ATLAS.csv',atlas)
    csv_write(output/'BATCH_INVENTORY.csv',inventory)
    evidence=[]
    for i,(claim,decision) in enumerate(zip(manifest['claims'],decisions['claims'])):
        result=read(analysis/f'CLAIM_{i+1:02}.json')
        world=next(w for w in manifest['worlds'] if w['world_id']==claim['world_id'])
        evidence.append({'claim_id':claim['claim_id'],'mechanism_id':world['mechanism_id'],
            'objective_branch':'V' if 'first_pair' in claim else 'joint_power_screening',
            'model_scope':claim['model_scope'],'input_hash':result['analysis_input_sha256'],
            'analysis_hash':canonical_hash(manifest['analysis_hashes']),
            'development_or_confirmation':'confirmation_'+claim['role'],
            'finite_or_continuous':'complete_declared_finite','observed_or_reconstructed':'observed',
            'matching_status':result.get('matched_first',{}).get('equivalence_supported','not_applicable'),
            'same_information':True,'same_permissions':True,
            'initial_validity':'see every frozen path initial interval in confirmation/CLAIM_%02d.json'%(i+1),
            'old_and_new_source_checks':'every published component, full true history, no removed legal crosses',
            'solver_status':'conditional lower and upper graphs; preserve timeouts' if 'first_pair' in claim else 'not_needed_for_fixed_joint_cap_claim',
            'statistical_status':decision['status'],'practical_effect':decision.get('capacity_bounds',decision['conditions']),
            'alternative_repairs_tested':'complete candidate domain at B1/B2' if 'first_pair' in claim else 'all crosses measured; specified pair diagnosis',
            'policy_sensitivity':'native fixed policy; separate development guard challenge for research variants',
            'primary_source_refs':'ENGINE_SUPPORT.md; DEEP_JOINT_MECHANISM_AUDIT.md; frozen native engine sources',
            'counterevidence':'NEGATIVE_AND_UNRESOLVED.csv; RESEARCH_JUDGMENT.md; no new algorithm or universal-transfer claim',
            'conclusion':decision['status'],'alpha':claim['alpha'],'N':claim['iterations']})
    negatives=read(run/'NEGATIVE_AND_UNRESOLVED.json')
    for row in negatives:
        evidence.append({'claim_id':row['claim_id'],'mechanism_id':row['mechanism_id'],
            'objective_branch':'see finding','model_scope':'finite_native_or_explicitly_not_run',
            'input_hash':'see indexed evidence '+row['evidence'],
            'analysis_hash':'see evidence manifests','development_or_confirmation':row['status'],
            'finite_or_continuous':'finite','observed_or_reconstructed':'observed where executed; not_run is not zero',
            'matching_status':'not_applicable','same_information':'see comparison',
            'same_permissions':'see comparison','initial_validity':'preserved in raw solver records',
            'old_and_new_source_checks':'complete full-history for capacity claims',
            'solver_status':row['status'],'statistical_status':row['status'],
            'practical_effect':row['finding'],'alternative_repairs_tested':'see full-domain challenges',
            'policy_sensitivity':'see source-specific notes','primary_source_refs':row['evidence'],
            'counterevidence':row['finding'],'conclusion':row['status']})
    csv_write(output/'EVIDENCE_LEDGER.csv',evidence)
    csv_write(output/'NEGATIVE_AND_UNRESOLVED.csv',negatives)
    copy(run/'DISCOVERY_EVENTS.jsonl')
    for p in sorted(analysis.glob('*.json')):copy(p,'confirmation/'+p.name)
    for p in sorted((run/'checks').rglob('*')):
        if p.is_file() and p.suffix in ('.json','.md','.log','.txt','.csv','.py'):
            copy(p,'checks/'+str(p.relative_to(run/'checks')))
    for directory in ['broad-min-increment-v1','refine-min-increment-v1','catalog-min-increment-v1',
                      'catalog-two-slot-min-increment-v1','full-baseline-challenge-v1',
                      'catalog-full-domain-challenge-v1','refine-full-domain-batch-challenge-v1',
                      'deep-full-domain-challenge-v1','deep-joint-mechanism-audit-v1']:
        for p in sorted((run/'analysis'/directory).glob('*')):
            if p.is_file() and (p.name in ('SUMMARY.json','MANIFEST.json') or
                               p.name.startswith('CASE_') or p.suffix in ('.csv','.md')):
                copy(p,'development/'+directory+'/'+p.name)
    for p in sorted((run/'analysis/confirm-v2-compact-moments').rglob('*')):
        if p.is_file():copy(p,'compact_moments/'+str(p.relative_to(run/'analysis/confirm-v2-compact-moments')))
    final_figures=run/'figures'/read(run/'figures/FINAL_FIGURES.json')['final_directory']
    for p in sorted(final_figures.rglob('*')):
        if p.is_file():copy(p,'figures/'+str(p.relative_to(final_figures)))
    for p in sorted((docs/'figures').glob('*.tex')):copy(p,'figures/'+p.name)
    sources=[*sorted((SOURCE_ROOT/'src/wowfs/experiments').glob('oe_*.py')),
             *sorted((SOURCE_ROOT/'src/wowfs/reporting').glob('oe_*.py')),
             *sorted((SOURCE_ROOT/'scripts').glob('*oe*.py')),
             *sorted((SOURCE_ROOT/'tests').glob('test_oe_*.py')),
             *sorted((SOURCE_ROOT/'configs').glob('open_exploration*'))]
    if (SOURCE_ROOT/'scripts/audit_open_exploration.py').exists():
        sources.append(SOURCE_ROOT/'scripts/audit_open_exploration.py')
    for rel in ['scripts/env.sh','src/wowfs/paths.py','src/wowfs/__init__.py',
                'src/wowfs/experiments/fc_native.py','src/wowfs/experiments/r2_native.py',
                'configs/fc_presets.json','configs/paths.yaml','configs/official_contexts.yaml',
                'src/wowfs/simulator/native_main.go','src/wowfs/simulator/native_ablation.go',
                'src/wowfs/simulator/native_mechanism.go','src/wowfs/simulator/r3_variants.go']:
        sources.append(SOURCE_ROOT/rel)
    for p in sorted(set(sources)):copy(p,'code/'+str(p.relative_to(SOURCE_ROOT)))
    provenance={'utc':datetime.now(timezone.utc).isoformat(),'run_root':str(run),
        'manifest_sha256':sha(manifest_path),'analysis_results':str(analysis),
        'raw_data_policy':'Native raw samples, caches, frozen executables and full development solver outputs remain at their indexed WORK_ROOT paths. No old frozen run changed.',
        'world_registry_note':'Rows are versioned views, including changed initial libraries; repeated world_id is not a new physical ecology.',
        'observations_rows':len(observations),'files':{str(p.relative_to(output)):sha(p)
            for p in sorted(output.rglob('*')) if p.is_file()}}
    atomic_json(output/'PACKAGE_MANIFEST.json',provenance)
    archive=output.with_suffix('.zip')
    if archive.exists():raise ValueError('Archive exists; refuse overwrite')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(output.rglob('*')):
            if p.is_file():z.write(p,str(p.relative_to(output)))
    result={'review_directory':str(output),'archive':str(archive),'archive_bytes':archive.stat().st_size,
        'archive_sha256':sha(archive),'files':len(provenance['files'])+1}
    atomic_json(run/'REVIEW_PACKAGE_RECEIPT.json',result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-root',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    print(json.dumps(package(a.run_root,a.output)))
