#!/usr/bin/env python3
"""Review archive with every new native receipt and explicit reused-data scope."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile
from wowfs.paths import SOURCE_ROOT,setup_paths,atomic_json


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def main():
    root=setup_paths();out=root/'artifacts/decisive-value'
    for p in (SOURCE_ROOT/'docs/decisive-value').glob('*.md'):shutil.copy2(p,out/p.name)
    required=['CORE_RESULT.md','DECISION_PROTOCOL.md','DECISION_VALUE_RESULTS.csv',
        'STRUCTURAL_CONTRASTS.csv','THEORY.md','SEQUENCE_RESULTS.csv','PRIOR_WORK_DELTA.md',
        'PROSPECTIVE_CONFIRMATION.json','CONFIRMATION_TABLE.npz','DECISIVE_VALUE.png',
        'CAP_COMPENSATION.png','NATIVE_AUDIT.json','INDEPENDENT_NATIVE_AUDIT.json',
        'FINAL_SUMMARY.json','CONSTRUCTION_REVIEW.md','reused_r4/MANIFEST.json']
    for name in required:
        if not(out/name).is_file():raise FileNotFoundError(name)
    audit=json.loads((out/'NATIVE_AUDIT.json').read_text())
    for path in ('NATIVE_AUDIT.json','INDEPENDENT_NATIVE_AUDIT.json'):
        a=json.loads((out/path).read_text())
        if any(a[k] for k in ('audit_errors','failed_invocations','incomplete_invocations')):raise ValueError('Native audit failed')
        if a['native_calls']!=864 or a['physical_battles']!=681984:raise ValueError('Execution denominator mismatch')
    shutil.copytree(root/'inputs/r5-theory',out/'formal_r5_input',dirs_exist_ok=True)
    shutil.copy2(root/'inputs/RESEARCH_BRIEF_DECISIVE_VALUE.md',out/'RESEARCH_BRIEF_DECISIVE_VALUE.md')
    selected={};index=[]
    for run in sorted((root/'runs/decisive-value').iterdir()):
        if not run.is_dir():continue
        for p in sorted(run.rglob('*')):
            if p.is_file() and p.name!='native.frozen':
                dest=out/'frozen_runs'/run.name/p.relative_to(run);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
        if not (run/'PROTOCOL.json').exists():continue
        record={'run':run.name,'protocol_sha256':digest(run/'PROTOCOL.json'),
                'kind':'native' if (run/'native.frozen').exists() else 'analysis_only'}
        if record['kind']=='native':
            data=json.loads((run/'RESULTS.json').read_text())
            if data['errors'] or any(r is None for r in data['rows']):raise ValueError('Incomplete native run')
            for row in data['rows']:selected[row['cache_key']]=Path(row['cache_directory'])
            record.update(binary_sha256=digest(run/'native.frozen'),logical_cells=len(data['rows']),
                binary_archive_policy='Compiled executable stays external; source, provenance, hashes and exact invocation archived.')
        index.append(record)
    atomic_json(out/'frozen_runs/INDEX.json',index)
    for key,folder in sorted(selected.items()):
        dest=out/'native_evidence'/key;dest.mkdir(parents=True,exist_ok=True)
        for name in ('input.json','invocation.json','summary.json','output.json.gz'):shutil.copy2(folder/name,dest/name)
    if len(selected)!=audit['native_calls']:raise ValueError('Missing physical receipt')
    atomic_json(out/'native_evidence/INDEX.json',{'receipts':len(selected),'battles':audit['physical_battles'],
        'scope':'Every new retained decisive-value invocation once; old R4 reuse and exact abstract results add no new native execution.'})
    shutil.copy2(root/'external/mythicsim-forever-engine-r3-variants/LICENSE',out/'UPSTREAM_ENGINE_LICENSE')
    source_files=[p for p in SOURCE_ROOT.rglob('*') if p.is_file() and not any(
        part in {'.git','__pycache__','.pytest_cache'} for part in p.relative_to(SOURCE_ROOT).parts)]
    hashes={str(p.relative_to(SOURCE_ROOT)):digest(p) for p in sorted(source_files)}
    for p in source_files:
        dest=out/'source_snapshot'/p.relative_to(SOURCE_ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
    atomic_json(out/'SOURCE_MANIFEST.json',{'git_commit':None,'files':hashes,
        'snapshot_sha256':hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest(),
        'note':'No invented identity or remote push; preserved maintained source and per-run exact snapshots. Prior R1–R6 results are read-only.'})
    manifest={str(p.relative_to(out)):digest(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name!='PACKAGE_MANIFEST.json'}
    atomic_json(out/'PACKAGE_MANIFEST.json',manifest)
    archive=root/'artifacts/WOW_FOREVER_DECISIVE_VALUE_REVIEW.zip';tmp=archive.with_suffix('.partial.zip')
    with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(out.rglob('*')):
            if p.is_file():z.write(p,'wow_forever_decisive_value/'+str(p.relative_to(out)))
    with zipfile.ZipFile(tmp) as z:
        if z.testzip():raise ValueError('Review ZIP CRC failed')
        inside=json.loads(z.read('wow_forever_decisive_value/PACKAGE_MANIFEST.json'))
        for name,sha in inside.items():
            if hashlib.sha256(z.read('wow_forever_decisive_value/'+name)).hexdigest()!=sha:raise ValueError('Packaged checksum mismatch '+name)
    tmp.replace(archive)
    receipt={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':digest(archive),
        'new_native_calls':audit['native_calls'],'new_native_battles':audit['physical_battles'],
        'all_native_raw_receipts':len(selected),'source_files':len(source_files),'package_files':len(manifest)+1,
        'required_files_present':True,'zip_CRC_verified':True,'all_packaged_hashes_verified':True,
        'scope':'3 empirical joint native steps; first population1% gain unresolved; abstract5steps separately labeled.'}
    atomic_json(root/'artifacts/WOW_FOREVER_DECISIVE_VALUE_REVIEW_RECEIPT.json',receipt);print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
