#!/usr/bin/env python3
"""Complete R6 review archive with all new native receipts and frozen inputs."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile
from wowfs.paths import SOURCE_ROOT,setup_paths,atomic_json


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def main():
    root=setup_paths();out=root/'artifacts/r6-theory-native'
    for path in (SOURCE_ROOT/'docs/r6').glob('*.md'):
        name='THEORY_NATIVE_ASSUMPTIONS.md' if path.name=='THEORY.md' else path.name
        shutil.copy2(path,out/name)
    shutil.copy2(root/'inputs/r5-theory/THEORY.md',out/'THEORY.md')
    required=['REVIEW.md','CASCADE_INSTANCES.csv','CASCADE_CLOSURE_CHECKS.csv',
        'CASCADE_MIN_RELEASE.csv','FRONTIER_NEUTRAL_POLYTOPE.json',
        'FRONTIER_NEUTRAL_SEQUENCE.csv','BEHAVIOR_GEOMETRY.csv','CAPACITY_SCALING.csv',
        'STATISTICAL_LOCALITY.csv','THEORY_NATIVE_MAP.md','THEORY.md',
        'CAPACITY_PRECISION_CONFIRMATION.json','FINAL_FIXED_CONTROL_AUDIT.json',
        'INDEPENDENT_NATIVE_AUDIT.json','SEED_OVERLAP.json','INDEPENDENT_ANALYSIS_REVIEW.md']
    for name in required:
        if not (out/name).is_file():raise FileNotFoundError(name)
    audit=json.loads((out/'INDEPENDENT_NATIVE_AUDIT.json').read_text())
    if not audit['snapshot_complete_and_quiescent'] or any(audit[k] for k in ['audit_errors','failed_invocations','incomplete_invocations']):
        raise ValueError('Incomplete or failed independent native audit')
    shutil.copytree(root/'inputs/r5-theory',out/'formal_r5_input',dirs_exist_ok=True)
    shutil.copy2(root/'inputs/RESEARCH_BRIEF_R6.md',out/'RESEARCH_BRIEF_R6.md')
    validation=out/'validation';validation.mkdir(exist_ok=True)
    shutil.copy2(audit['ledger_path'],validation/'CACHE_LEDGER.jsonl.gz')
    shutil.copy2(audit['external_reuse_ledger_path'],validation/'EXTERNAL_REUSE_LEDGER.jsonl.gz')
    selected={};index=[]
    for run in sorted((root/'runs/r6-theory-native').iterdir()):
        if not (run/'PROTOCOL.json').exists():continue
        destination=out/'frozen_runs'/run.name
        for path in run.rglob('*'):
            if path.is_file() and path.name!='native.frozen':
                dest=destination/path.relative_to(run);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
        if (run/'RESULTS.json').exists():
            result=json.loads((run/'RESULTS.json').read_text())
            if result['errors'] or any(row is None for row in result['rows']):raise ValueError('Native run incomplete')
            for row in result['rows']:selected[row['cache_key']]=Path(row['cache_directory'])
        index.append({'run':run.name,'protocol_sha256':digest(run/'PROTOCOL.json'),
                      'frozen_binary_sha256':digest(run/'native.frozen'),
                      'binary_archive_policy':'Identical R3 compiled binary remains external; hash and all integration source archived.'})
    atomic_json(out/'frozen_runs/INDEX.json',index)
    for key,folder in sorted(selected.items()):
        destination=out/'native_evidence'/key;destination.mkdir(parents=True,exist_ok=True)
        for name in ['input.json','invocation.json','summary.json','output.json.gz']:
            shutil.copy2(folder/name,destination/name)
    if len(selected)!=audit['native_calls']:raise ValueError('Complete receipt count mismatch')
    atomic_json(out/'native_evidence/INDEX.json',{'distinct_receipts':len(selected),
        'scope':'All R6 native receipts; exact retained calls counted once. No R3-read-only diagnostic data miscounted as new calls.'})
    shutil.copy2(root/'external/mythicsim-forever-engine-r2/LICENSE',out/'UPSTREAM_ENGINE_LICENSE')
    # Include the reused R3 affine evidence needed to recompute the diagnostic,
    # explicitly separated from new native receipts.
    external=out/'reused_r3';external.mkdir(exist_ok=True)
    for name in ['AFFINE_CALIBRATION.json','AFFINE_PROBE.json','AFFINE_TRANSFER.json']:
        shutil.copy2(root/'artifacts/r3-gold'/name,external/name)
    original_rows=json.loads((root/'runs/r3-gold/affine-calibration-v1/RESULTS.json').read_text())
    original_rows['rows']=[r for r in original_rows['rows'] if r['race']=='RaceHuman' and r['weapon_speed']==1.3]
    atomic_json(external/'ORIGINAL_DIAGNOSTIC_CALIBRATION_ROWS.json',original_rows)
    atomic_json(external/'REUSE_NOTICE.json',{'original_rows':len(original_rows['rows']),
        'new_R6_battles':0,'source':'R3 affine-calibration-v1; only the original-range diagnostic and base requests use these existing observations.'})
    source_files=[p for p in SOURCE_ROOT.rglob('*') if p.is_file() and not any(
        part in {'.git','__pycache__','.pytest_cache'} for part in p.relative_to(SOURCE_ROOT).parts)]
    hashes={str(p.relative_to(SOURCE_ROOT)):digest(p) for p in sorted(source_files)}
    for path in source_files:
        destination=out/'source_snapshot'/path.relative_to(SOURCE_ROOT)
        destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,destination)
    atomic_json(out/'SOURCE_MANIFEST.json',{'git_commit':None,'files':hashes,
        'snapshot_sha256':hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest(),
        'note':'No invented identity/commit or remote push. Prior source state preserved; snapshot contains maintained R1–R6 code.'})
    manifest={str(p.relative_to(out)):digest(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name!='PACKAGE_MANIFEST.json'}
    atomic_json(out/'PACKAGE_MANIFEST.json',manifest)
    archive=root/'artifacts/WOW_FOREVER_R6_THEORY_NATIVE_REVIEW.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in sorted(out.rglob('*')):
            if path.is_file():z.write(path,'wow_forever_r6_theory_native/'+str(path.relative_to(out)))
    with zipfile.ZipFile(archive) as z:
        if z.testzip():raise ValueError('Archive CRC failed')
    receipt={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':digest(archive),
        'native_calls':audit['native_calls'],'physical_battles':audit['physical_battles'],
        'all_native_raw_receipts':len(selected),'source_files':len(source_files),
        'package_files':len(manifest)+1,'required_files_present':True,'zip_CRC_verified':True,
        'formal_r5_theory_sha256':digest(out/'THEORY.md')}
    atomic_json(root/'artifacts/WOW_FOREVER_R6_THEORY_NATIVE_REVIEW_RECEIPT.json',receipt)
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
