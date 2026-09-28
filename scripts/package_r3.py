#!/usr/bin/env python3
"""Compact R3 review: complete derived evidence, selected raw receipts, source."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile
from wowfs.paths import SOURCE_ROOT,setup_paths,atomic_json

def main():
    root=setup_paths();out=root/'artifacts/r3-gold'
    required=['REVIEW.md','RESULTS.md','NEXT_RESEARCH.md','THEORY.md','COMPLEMENTARITY_ATLAS.csv',
        'REACTIVATION_WITNESSES.jsonl','COMPLEMENT_PHASE_GRID.csv','INTERACTION_SIGNATURES.csv',
        'INTERACTION_TYPES.yaml','TYPE_TRANSFER_RESULTS.csv','SEQUENTIAL_EXPANSION_RESULTS.csv',
        'RULE_COMPLEXITY_SCALING.csv','INDEPENDENT_NATIVE_AUDIT.json','paper/r3_main.pdf']
    for name in required:
        if not (out/name).is_file():raise FileNotFoundError(name)
    audit=json.loads((out/'INDEPENDENT_NATIVE_AUDIT.json').read_text())
    if not audit['snapshot_complete_and_quiescent']:raise ValueError('Audit not quiescent')
    if not json.loads((out/'validation/FROZEN_SNAPSHOT_AUDIT.json').read_text())['all_match']:
        raise ValueError('Frozen snapshot integrity failed')
    shutil.copy2(SOURCE_ROOT/'docs/r3/REPRODUCE.md',out/'REPRODUCE.md')
    for name in ('variant_tests.log','paper-build.log'):
        dest=out/'validation'/name;dest.parent.mkdir(exist_ok=True);shutil.copy2(root/'logs/r3-gold'/name,dest)
    shutil.copy2(audit['ledger_path'],out/'validation/CACHE_LEDGER.jsonl.gz')
    for run in (root/'runs/r3-gold').iterdir():
        if not (run/'PROTOCOL.json').exists():continue
        dest=out/'frozen_protocols'/run.name;dest.mkdir(parents=True,exist_ok=True)
        for name in ('PROTOCOL.json','FREEZE_TIME.json','PROGRESS.json'):
            shutil.copy2(run/name,dest/name)
    for run,name in [('variant-smoke','VARIANT_SMOKE_RECEIPT.json'),('variant-nr-check','NR_NOOP_CHECK.json')]:
        dest=out/'selected_evidence'/run;dest.mkdir(parents=True,exist_ok=True)
        receipt=json.loads((root/'runs/r3-gold'/run/name).read_text())
        shutil.copy2(root/'runs/r3-gold'/run/name,dest/name)
        for r in receipt['records']:
            for flag in ('-in','-out'):
                path=Path(r['command'][r['command'].index(flag)+1]);shutil.copy2(path,dest/path.name)
    selected={};index=[]
    choices=json.loads((out/'SEQUENTIAL_DECISIONS.json').read_text())
    chosen={(r['race'],r['selected_variant']) for r in choices if r['method']=='complement_constrained' and r['selected_variant']}
    for name in ['affine-probe-v1','causal-factorials-v1','phase-confirmation-v1','sequences-v1']:
        result=json.loads((root/'runs/r3-gold'/name/'RESULTS.json').read_text())
        for row in result['rows']:
            keep=(name=='affine-probe-v1' or
                name=='causal-factorials-v1' and row.get('case')=='blood_talon' and row.get('gear_stratum')=='5ae0e1e5d00fbdb1' and row['strategy']=='native_reck' or
                name=='phase-confirmation-v1' and row['offhand']==19019 and (row['point'] in ['confirm_0','confirm_1','confirm_2','confirm_3','confirm_4'] or row['point']=='confirm_6' and row['trinket1']==11815 and row['trinket2']==13965) or
                name=='sequences-v1' and (row['race'],row['variant_id']) in chosen)
            if keep:
                selected[row['cache_key']]=Path(row['cache_directory'])
                index.append({'run':name,**{k:v for k,v in row.items() if k not in ('actions','resources','auras','dps_samples')}})
    for key,folder in selected.items():
        dest=out/'selected_evidence/cache'/key;dest.mkdir(parents=True,exist_ok=True)
        for name in ('input.json','invocation.json','summary.json','output.json.gz'):shutil.copy2(folder/name,dest/name)
    atomic_json(out/'selected_evidence/INDEX.json',{'distinct_cached_calls':len(selected),'rows':index,
        'note':'Selected subsets of already audited calls; no extra battles. Full raw cache is retained outside ZIP.'})
    shutil.copy2(root/'external/mythicsim-forever-engine-r2/LICENSE',out/'selected_evidence/UPSTREAM_ENGINE_LICENSE')
    r2=root/'runs/r2-discovery/unseen-v1'
    dest=out/'frozen_protocols/r2-reference';dest.mkdir(parents=True,exist_ok=True)
    for name in ('PROTOCOL.json','FROZEN_DESIGN.json'):shutil.copy2(r2/name,dest/name)
    paths=[p for p in SOURCE_ROOT.rglob('*') if p.is_file() and not any(part in {'.git','__pycache__','.pytest_cache'} for part in p.relative_to(SOURCE_ROOT).parts)]
    hashes={str(p.relative_to(SOURCE_ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
    atomic_json(out/'SOURCE_MANIFEST.json',{'git_commit':None,'note':'Existing uncommitted source preserved, no invented identity.',
        'files':hashes,'snapshot_hash':hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()})
    with zipfile.ZipFile(out/'SOURCE_CODE.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(paths):z.write(p,'source/'+str(p.relative_to(SOURCE_ROOT)))
    manifest={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file() and p.name!='PACKAGE_MANIFEST.json'}
    atomic_json(out/'PACKAGE_MANIFEST.json',manifest)
    archive=root/'artifacts/WOW_FOREVER_R3_GOLD_REVIEW.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(out.rglob('*')):
            if p.is_file():z.write(p,'wow_forever_r3_gold/'+str(p.relative_to(out)))
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:raise ValueError('ZIP CRC failure')
    receipt={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
        'source_files':len(hashes),'selected_raw_cache_calls':len(selected),'package_files':len(manifest)+1}
    atomic_json(root/'artifacts/WOW_FOREVER_R3_GOLD_REVIEW_RECEIPT.json',receipt);print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
