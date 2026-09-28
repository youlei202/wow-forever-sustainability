#!/usr/bin/env python3
"""Source and compact native evidence package; never include the full combat cache."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile
from wowfs.paths import SOURCE_ROOT, setup_paths, atomic_json

root=setup_paths();out=root/'artifacts/r2-discovery/latest'
required=['REVIEW.md','NATIVE_RUN_RECEIPT.json','DISCOVERIES.md','PROTOCOL.json',
          'RULES_AND_PERMISSIONS.json','INTERACTION_CASES.csv','ROUND_RESULTS.csv',
          'SEQUENCE_RESULTS.csv','RULE_REUSE.csv','REWARD_COUNTERFACTUALS.csv',
          'FACTION_SUMMARY.csv','COVERAGE.csv','paper/r2_main.pdf']
for name in required:
    if not (out/name).is_file():raise FileNotFoundError(name)
paths=[]
for p in SOURCE_ROOT.rglob('*'):
    rel=p.relative_to(SOURCE_ROOT)
    if p.is_file() and not any(part in {'.git','__pycache__','.pytest_cache'} for part in rel.parts):
        paths.append(p)
hashes={str(p.relative_to(SOURCE_ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
atomic_json(out/'SOURCE_MANIFEST.json',{'git_commit':None,'note':'Existing uncommitted repository preserved; no fabricated author identity',
            'files':hashes,'snapshot_hash':hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()})
with zipfile.ZipFile(out/'SOURCE_CODE.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in sorted(paths):z.write(p,'source/'+str(p.relative_to(SOURCE_ROOT)))
license_path=root/'external/mythicsim-forever-engine-r2/LICENSE'
shutil.copy2(license_path,out/'selected_evidence/UPSTREAM_ENGINE_LICENSE')
manifest={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest()
          for p in sorted(out.rglob('*')) if p.is_file() and p.name!='PACKAGE_MANIFEST.json'}
atomic_json(out/'PACKAGE_MANIFEST.json',manifest)
archive=out.parent/'WOW_FOREVER_R2_DISCOVERY_REVIEW.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in sorted(out.rglob('*')):
        if p.is_file():z.write(p,'wow_forever_r2_discovery/'+str(p.relative_to(out)))
with zipfile.ZipFile(archive) as z:
    if z.testzip() is not None:raise ValueError('archive CRC check failed')
print(json.dumps({'review_archive':str(archive),'bytes':archive.stat().st_size,
                  'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'source_files':len(hashes)},indent=2))
