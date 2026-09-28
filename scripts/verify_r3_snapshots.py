#!/usr/bin/env python3
"""Check archived requests, native executable and source files against the freeze."""
import hashlib
import json
from wowfs.paths import setup_paths,canonical_hash,atomic_json

def main():
    root=setup_paths();rows=[]
    for p in sorted((root/'runs/r3-gold').glob('*/PROTOCOL.json')):
        protocol=json.loads(p.read_text());run=p.parent;bad=[]
        if hashlib.sha256((run/'native.frozen').read_bytes()).hexdigest()!=protocol['binary_sha256']:bad.append('binary')
        for name,expected in protocol['source_hashes'].items():
            path=run/'source'/name
            if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:bad.append(name)
        jobs=json.loads((run/'JOBS.json').read_text())
        if canonical_hash(jobs)!=protocol['jobs_sha256']:bad.append('jobs')
        rows.append({'run':run.name,'archived_source_files':len(protocol['source_hashes']),
                     'logical_jobs':len(jobs),'mismatches':bad})
    result={'runs':rows,'all_match':all(not r['mismatches'] for r in rows)}
    atomic_json(root/'artifacts/r3-gold/validation/FROZEN_SNAPSHOT_AUDIT.json',result)
    print(json.dumps(result,indent=2))
    if not result['all_match']:raise SystemExit(2)

if __name__=='__main__':main()
