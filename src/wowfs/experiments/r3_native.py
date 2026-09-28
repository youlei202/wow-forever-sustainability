"""R3 native orchestration: immutable inputs and reuse of valid R2 physics."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from wowfs.paths import SOURCE_ROOT, setup_paths, atomic_json, canonical_hash
from wowfs.experiments.r2_native import execute_job, file_hash

def dispatch(job, frozen_binary, binary_hash, root):
    key=canonical_hash({'binary':binary_hash,'input':job['input']})
    for stage in ['r2-discovery','r3-gold']:
        cache=root/f'cache/{stage}/native';folder=cache/key[:2]/key
        if (folder/'summary.json').exists():
            row=json.loads((folder/'summary.json').read_text())
            return {**job['meta'],**row,'cache_hit':True,'cache_key':key,
                    'cache_origin':stage,'cache_directory':str(folder)}
    row=execute_job(job,frozen_binary,binary_hash,root/'cache/r3-gold/native')
    return {**row,'cache_origin':'r3-gold',
            'cache_directory':str(root/'cache/r3-gold/native'/key[:2]/key)}

def run_jobs(jobs, run_id, binary, scientific_protocol, workers=64, resume=False):
    root=setup_paths();run=root/'runs/r3-gold'/run_id
    sources=[p for directory in ['src/wowfs/experiments','src/wowfs/simulator','configs']
             for p in (SOURCE_ROOT/directory).glob('r3_*') if p.is_file()]
    bh=file_hash(binary)
    protocol={'schema':1,'binary_sha256':bh,'jobs_sha256':canonical_hash(jobs),
              'source_hashes':{str(p.relative_to(SOURCE_ROOT)):file_hash(p) for p in sources},
              'science':scientific_protocol,'logical_cells':len(jobs),
              'requested_fights_including_reuse':sum(j['input']['request']['simOptions']['iterations'] for j in jobs)}
    if (run/'PROTOCOL.json').exists():
        if not resume or json.loads((run/'PROTOCOL.json').read_text())!=protocol:
            raise ValueError('resume requires identical protocol, requests, binary, source')
        if (run/'RESULTS.json').exists() and json.loads((run/'PROGRESS.json').read_text())['status']=='complete':
            print(f'Completed immutable run verified: {run}',flush=True);return run
    else:
        run.mkdir(parents=True,exist_ok=True)
        atomic_json(run/'PROTOCOL.json',protocol);atomic_json(run/'JOBS.json',jobs)
        atomic_json(run/'FREEZE_TIME.json',{'utc':datetime.now(timezone.utc).isoformat()})
        shutil.copy2(binary,run/'native.frozen')
        for p in sources:
            dest=run/'source'/p.relative_to(SOURCE_ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
    unique={};indices={}
    for i,j in enumerate(jobs):
        key=canonical_hash(j['input']);unique.setdefault(key,j);indices.setdefault(key,[]).append(i)
    output=[None]*len(jobs);errors=[];done=0;calls=0;fights=0;reused=0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        pending={pool.submit(dispatch,j,run/'native.frozen',bh,root):key for key,j in unique.items()}
        for f in as_completed(pending):
            key=pending[f];done+=1
            try:
                row=f.result()
                if row['cache_hit']:reused+=1
                else:calls+=1;fights+=row['iterations']
                for i in indices[key]:output[i]={**row,**jobs[i]['meta']}
            except Exception as e:errors.append({'input_hash':key,'error':str(e)})
            if done%100==0 or done==len(unique):
                progress={'status':'running','completed':done,'unique_cells':len(unique),
                          'new_calls':calls,'new_fights':fights,'reused_cells':reused,'errors':len(errors)}
                atomic_json(run/'PROGRESS.json',progress);print(json.dumps(progress),flush=True)
    atomic_json(run/'RESULTS.json',{'rows':output,'errors':errors})
    progress['status']='failed' if errors else 'complete';atomic_json(run/'PROGRESS.json',progress)
    if errors:raise RuntimeError(f'{len(errors)} cells failed; preserved')
    return run

def r2_witness_inputs():
    root=setup_paths();run=root/'runs/r2-discovery/unseen-v1'
    rows=json.loads((run/'RESULTS.json').read_text())['rows']
    chosen={}
    for row in rows:
        if row['gear_id'] in ('5ae0e1e5d00fbdb1','a8e48c846cd427fb'):
            path=root/'cache/r2-discovery/native'/row['cache_key'][:2]/row['cache_key']/'input.json'
            chosen[(row['gear_id'],row['race'],row['task'],row['strategy'])]=json.loads(path.read_text())
    return chosen

def replace_item(input_value,slot,item):
    value=deepcopy(input_value)
    value['request']['raid']['parties'][0]['players'][0]['equipment']['items'][slot]={'id':item}
    return value
