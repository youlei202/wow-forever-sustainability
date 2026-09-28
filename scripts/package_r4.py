#!/usr/bin/env python3
"""Compact R4 scientific review, selected raw evidence, and immutable provenance."""
from pathlib import Path
import hashlib,json,shutil,zipfile
from wowfs.paths import SOURCE_ROOT,setup_paths,atomic_json

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    root=setup_paths();out=root/'artifacts/r4-foundational-discovery'
    required=['REVIEW.md','FOUNDATIONAL_QUESTION.md','DISCOVERY_MAP.csv','PAIRED_STRUCTURAL_INTERVENTIONS.csv','BASE_ECOSYSTEMS.json',
        'CANDIDATE_DESIGN_DOMAIN.json','CAPS_METRICS_PERMISSIONS.json','FULL_COMBINATION_COVERAGE.csv','LOCAL_FEASIBILITY.csv',
        'BATCH_GRANULARITY.csv','BRANCH_CONTINUATION.csv','REGIME_PREDICTIONS.csv','STRUCTURAL_WITNESSES.jsonl','THEORY.md',
        'CLAIM_PRIOR_WORK_MAP.md','NATIVE_RUN_RECEIPT.json','INDEPENDENT_NATIVE_AUDIT.json','HIGH_PRECISION_CERTIFICATE_RESULTS.json',
        'SOURCE_GROUP_DIAGNOSTICS.csv','UNSEEN_E_COMPARISON.json']
    for name in required:
        if not(out/name).is_file():raise FileNotFoundError(name)
    audit=json.loads((out/'INDEPENDENT_NATIVE_AUDIT.json').read_text())
    if not audit['snapshot_complete_and_quiescent']or any(audit[k]for k in ['failed_invocations','incomplete_invocations','audit_errors']):raise ValueError('Native audit is not complete and clean')
    validation=out/'validation';validation.mkdir(exist_ok=True)
    shutil.copy2(audit['ledger_path'],validation/'CACHE_LEDGER.jsonl.gz')
    for path in (SOURCE_ROOT/'docs/r4').glob('*.md'):
        if path.name not in ['REVIEW.md','FOUNDATIONAL_QUESTION.md']:shutil.copy2(path,out/path.name)
    logs=root/'logs'
    for path in logs.rglob('*'):
        if path.is_file()and (path.name.startswith('PYTEST_')or path.name in ['r4-report.log','r4-precision-analysis-v2.log','r4-world-unit-tests.log']):
            shutil.copy2(path,validation/path.name)
    protocol_index=[]
    for path in sorted((root/'runs/r4-foundational-discovery').glob('*/PROTOCOL.json')):
        protocol=json.loads(path.read_text());dest=out/'frozen_protocols'/path.parent.name;dest.mkdir(parents=True,exist_ok=True)
        for name in ['PROTOCOL.json','FREEZE_TIME.json','PROGRESS.json','CONFIG.yaml','BASE_ECOSYSTEMS.json','CAUSAL_HYPOTHESES.json','PREPARATION_FAILURES.json','APPLIED_VARIANT_CHECK.json']:
            if(path.parent/name).is_file():shutil.copy2(path.parent/name,dest/name)
        protocol_index.append({'run':path.parent.name,'kind':'native'if'binary_sha256'in protocol else'analysis',
            'protocol_path':str(path),'protocol_sha256':digest(path),
            'full_inputs':str(path.parent/'JOBS.json')if(path.parent/'JOBS.json').exists()else None,
            'full_results':str(path.parent/'RESULTS.json')if(path.parent/'RESULTS.json').exists()else None,
            'frozen_executable':str(path.parent/'native.frozen')if(path.parent/'native.frozen').exists()else None})
    atomic_json(out/'frozen_protocols/INDEX.json',protocol_index)
    selected={};index=[]
    for name in ['causal-pairs-v1','constructive-reward-v1','certificate-precision-v1','unseen-future-v1']:
        rows=json.loads((root/'runs/r4-foundational-discovery'/name/'RESULTS.json').read_text())['rows']
        for row in rows:
            keep=False
            if name=='causal-pairs-v1':keep=row['gear_id']in ['26007bac9b64ca50','331790c18dd3a920']and row['strategy']=='native_reck'
            if name=='constructive-reward-v1':keep=row['gear_id']=='d9ddad879238ea73'and row['strategy']=='native_reck'
            if name=='certificate-precision-v1':keep=(row['block']==0 and row['task']in ['high_armor','burst_10s'])or(row['gear_id']=='d9ddad879238ea73'and row['strategy']=='native_reck')
            if name=='unseen-future-v1':keep=row['gear_id']in ['69ec6140b8715f72','e8abfcedffc7e5c5','2e890b37368bddd5','8a0031fa7ed8d911']and row['strategy']=='native_reck'
            if keep:
                selected[row['cache_key']]=Path(row['cache_directory']);index.append({'run':name,**{k:v for k,v in row.items()if k not in ['actions','resources','auras','dps_samples']}})
    for key,folder in selected.items():
        dest=out/'selected_evidence/cache'/key;dest.mkdir(parents=True,exist_ok=True)
        for name in ['input.json','invocation.json','summary.json','output.json.gz']:shutil.copy2(folder/name,dest/name)
    atomic_json(out/'selected_evidence/INDEX.json',{'distinct_cached_calls':len(selected),'logical_rows':index,
        'counting':'Subset of already audited physical calls; adds no new battles. Full raw cache remains at absolute indexed paths.'})
    for run in ['batch-screen-v1','branch-probe-v1']:
        source=root/'runs/r4-foundational-discovery'/run;dest=out/'selected_evidence'/run;dest.mkdir(exist_ok=True)
        for path in source.glob('*__*.json'):
            if path.stem.split('__')[0]in ['timing_extra','timing_shared','resource_haste']:shutil.copy2(path,dest/path.name)
    shutil.copy2(root/'external/mythicsim-forever-engine-r2/LICENSE',out/'selected_evidence/UPSTREAM_ENGINE_LICENSE')
    files=[p for p in SOURCE_ROOT.rglob('*')if p.is_file()and not any(part in {'.git','__pycache__','.pytest_cache'}for part in p.relative_to(SOURCE_ROOT).parts)]
    hashes={str(p.relative_to(SOURCE_ROOT)):digest(p)for p in sorted(files)}
    for path in files:
        dest=out/'source_snapshot'/path.relative_to(SOURCE_ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
    atomic_json(out/'SOURCE_MANIFEST.json',{'git_commit':None,'note':'Local maintained source staged; prior R1-R3 state preserved, no invented identity and no remote push.',
        'files':hashes,'snapshot_sha256':hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()})
    manifest={str(p.relative_to(out)):digest(p)for p in sorted(out.rglob('*'))if p.is_file()and p.name!='PACKAGE_MANIFEST.json'}
    atomic_json(out/'PACKAGE_MANIFEST.json',manifest)
    archive=root/'artifacts/WOW_FOREVER_R4_FOUNDATIONAL_REVIEW.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6)as z:
        for path in sorted(out.rglob('*')):
            if path.is_file():z.write(path,'wow_forever_r4_foundational/'+str(path.relative_to(out)))
    with zipfile.ZipFile(archive)as z:
        if z.testzip():raise ValueError('ZIP CRC failed')
    receipt={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':digest(archive),'native_calls':audit['native_calls'],
        'physical_battles':audit['physical_battles'],'source_files':len(files),'package_files':len(manifest)+1,'selected_raw_calls':len(selected),
        'required_files_present':True,'zip_CRC_verified':True}
    atomic_json(root/'artifacts/WOW_FOREVER_R4_FOUNDATIONAL_REVIEW_RECEIPT.json',receipt);print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
