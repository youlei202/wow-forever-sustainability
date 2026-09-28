#!/usr/bin/env python3
"""Resume immutable native inputs/binary; leave a completed run byte-identical.

Uses the archived physical requests rather than rebuilding a historical run
from today's mutable configuration. New research must use a new run directory.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import json
from pathlib import Path
from wowfs.paths import setup_paths, canonical_hash, atomic_json
from wowfs.experiments.r2_native import execute_job, file_hash

p=argparse.ArgumentParser()
p.add_argument('run');p.add_argument('--workers',type=int,default=64)
a=p.parse_args();root=setup_paths();run=Path(a.run)
if not run.is_absolute():run=root/'runs/r2-discovery'/run
protocol=json.loads((run/'PROTOCOL.json').read_text())
binary=run/'wowfs-native.frozen';bh=file_hash(binary)
assert bh==protocol['binary_sha256'], 'archived executable changed'
source_hashes=json.loads((run/'SOURCE_HASHES.json').read_text())
for name,digest in source_hashes.items():
    assert file_hash(run/'source'/name)==digest, f'archived source changed: {name}'
jobs=json.loads((run/'JOBS.json').read_text())
assert canonical_hash(jobs)==protocol['jobs_hash'], 'archived requests changed'
cache=root/'cache/r2-discovery/native';missing={}
keys=[]
for j in jobs:
    key=canonical_hash({'binary':bh,'input':j['input']});keys.append(key)
    directory=cache/key[:2]/key
    if not all((directory/name).is_file() for name in ['summary.json','input.json','output.json.gz','invocation.json']):
        missing[key]=j
report={'run':str(run),'logical_cells':len(jobs),'unique_physical_cells':len(set(keys)),
        'missing_before_resume':len(missing),'archived_binary_and_source_verified':True,
        'jobs_sha256':protocol['jobs_hash'],'new_calls':0,'new_battles':0}
result_path=run/'RESULTS.json'
old_hash=file_hash(result_path) if result_path.exists() else None
with ThreadPoolExecutor(max_workers=a.workers) as pool:
    futures=[pool.submit(execute_job,j,binary,bh,cache) for j in missing.values()]
    for f in as_completed(futures):
        row=f.result()
        report['new_calls']+=not row['cache_hit']
        if not row['cache_hit']:report['new_battles']+=row['iterations']
if not result_path.exists():
    rows=[]
    for j,key in zip(jobs,keys):
        row=json.loads((cache/key[:2]/key/'summary.json').read_text())
        rows.append({**j['meta'],**row,'cache_key':key,'cache_hit':key not in missing})
    atomic_json(result_path,{'rows':rows,'errors':[]})
report['completed_results_preserved']=old_hash is not None and old_hash==file_hash(result_path)
report['results_sha256']=file_hash(result_path)
atomic_json(root/'artifacts/r2-discovery/latest'/f'RESUME_AUDIT_{run.name}.json',report)
print(json.dumps(report,indent=2))
