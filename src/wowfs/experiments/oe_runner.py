"""Resumable, immutable native batches for the 2026-09-26 exploration.

The campaign deadline never resets on resume. Native cells use shared flock
tokens across batches; no historical cache or engine is modified.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from wowfs.paths import SOURCE_ROOT, setup_paths, atomic_json, canonical_hash
from wowfs.experiments.fc_native import validate_equipment
from wowfs.experiments.r2_native import file_hash, summarize

STAGE = 'open-exploration-2026-09-26'
OBSERVATION = {'version': 1, 'utility': 'native owner DPS including pets',
               'samples': 'native allValues; seed+i; labeled random streams',
               'diagnostics': 'raw actions/resources/pets/auras retained; summary actions may include friendly self damage; never use fractions as novelty'}


def now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def lock(path, blocking=True):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def append_json(path, value):
    with lock(path.with_suffix(path.suffix+'.lock')):
        with path.open('a') as f:
            f.write(json.dumps(value, sort_keys=True, allow_nan=False)+'\n')


def source_snapshot():
    paths = [SOURCE_ROOT/'src/wowfs/__init__.py', SOURCE_ROOT/'src/wowfs/paths.py',
             SOURCE_ROOT/'src/wowfs/experiments/fc_native.py',
             SOURCE_ROOT/'src/wowfs/experiments/r2_native.py',
             SOURCE_ROOT/'configs/fc_presets.json', SOURCE_ROOT/'configs/paths.yaml',
             SOURCE_ROOT/'configs/official_contexts.yaml',
             SOURCE_ROOT/'src/wowfs/simulator/r3_variants.go',
             SOURCE_ROOT/'scripts/env.sh',
             *sorted((SOURCE_ROOT/'src/wowfs/experiments').glob('oe_*.py')),
             *sorted((SOURCE_ROOT/'configs').glob('open_exploration*'))]
    return {str(p.relative_to(SOURCE_ROOT)): file_hash(p) for p in paths}


def campaign(run, hours):
    run.mkdir(parents=True, exist_ok=True)
    with lock(run/'campaign.lock'):
        p=run/'CAMPAIGN.json'
        if p.exists():
            value=json.loads(p.read_text())
            if hours > value['max_wall_hours']:
                raise ValueError('Resume cannot extend original campaign budget')
        else:
            environment=run/'ENVIRONMENT.json'
            start=(datetime.fromisoformat(json.loads(environment.read_text())['utc']).timestamp()
                   if environment.exists() else time.time())
            value={'started_utc':now(), 'started_epoch':start,
                   'deadline_epoch':start+hours*3600, 'max_wall_hours':hours,
                   'worker_limit_total':64, 'gpu':0,
                   'memory_soft_bytes':128*1024**3,
                   'budget_includes_all_elapsed_time_and_resumes':True}
            atomic_json(p,value)
    return value


def memory_used():
    try: return int(Path('/sys/fs/cgroup/memory.current').read_text())
    except (OSError,ValueError): return 0


@contextmanager
def resource_token(root, limit, deadline, memory_limit):
    slots=root/'runs'/STAGE/'worker-tokens'
    slots.mkdir(parents=True, exist_ok=True)
    while time.time()<deadline:
        if memory_used() < memory_limit:
            for i in range(limit):
                stream=(slots/str(i)).open('a')
                try: fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
                except BlockingIOError:
                    stream.close();continue
                try:
                    yield
                finally:
                    fcntl.flock(stream,fcntl.LOCK_UN);stream.close()
                return
        time.sleep(.2)
    raise TimeoutError('campaign deadline reached while waiting for resource token')


def execute_cell(job, *, root, run, batch, protocol, budget):
    physics=canonical_hash({'binary':protocol['binary_sha256'], 'input':job['input']})
    key=canonical_hash({'physical':physics, 'source':protocol['source_hashes'],
                        'observation':OBSERVATION})
    folder=root/'cache'/STAGE/'native'/key[:2]/key
    folder.mkdir(parents=True, exist_ok=True)
    with lock(folder/'cell.lock'):
        saved=folder/'summary.json'
        if saved.exists():
            row=json.loads(saved.read_text())
            if json.loads((folder/'input.json').read_text()) != job['input']:
                raise ValueError('cache input mismatch')
            if row['cache_key']!=key or not (folder/'output.json.gz').exists():
                raise ValueError('cache receipt mismatch')
            with gzip.open(folder/'output.json.gz','rb') as stream: raw=stream.read()
            if hashlib.sha256(raw).hexdigest()!=row['output_sha256']:
                raise ValueError('cached native output hash mismatch')
            measured=summarize(json.loads(raw),job['input'])
            if any(row[k]!=v for k,v in measured.items()):
                raise ValueError('cached summary differs from native output')
            return {**row, 'cache_hit':True}
        # Failures are immutable numbered attempts. One finite retry is allowed.
        attempts=sorted(folder.glob('attempt-*'))
        if len(attempts)>=2:
            raise RuntimeError('two native attempts failed; see '+str(folder))
        atomic_json(folder/'input.json', job['input'])
        trial=folder/f'attempt-{len(attempts)+1:02}'
        trial.mkdir()
        output=trial/'output.json'
        command=[str(batch/'native.frozen'),'-in',str(folder/'input.json'),'-out',str(output)]
        with resource_token(root,budget['worker_limit_total'],budget['deadline_epoch'],budget['memory_soft_bytes']):
            started=time.time()
            if started >= budget['deadline_epoch']: raise TimeoutError('campaign deadline')
            timeout=max(1,min(900,budget['deadline_epoch']-started))
            try:
                append_json(run/'RUN_RECEIPTS.jsonl',{'batch_id':batch.name,'cache_key':key,
                    'physical_key':physics,'utc':now(),'status':'started',
                    'iterations_requested':job['input']['request']['simOptions']['iterations'],
                    'attempt_directory':str(trial)})
                result=subprocess.run(command,capture_output=True,text=True,timeout=timeout,
                                      env={**os.environ,'GOMAXPROCS':'1'})
                invocation={'command':command,'started_utc':datetime.fromtimestamp(started,timezone.utc).isoformat(),'elapsed_seconds':time.time()-started,
                    'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,
                    'binary_sha256':protocol['binary_sha256'],'physical_key':physics}
                atomic_json(trial/'invocation.json',invocation)
                if result.returncode: raise RuntimeError(result.stderr[-2000:])
                raw=output.read_bytes()
                summary=summarize(json.loads(raw),job['input'])
                with gzip.open(folder/'output.json.gz.tmp','wb') as f: f.write(raw)
                os.replace(folder/'output.json.gz.tmp',folder/'output.json.gz')
                output.unlink()
                summary.update(cache_key=key,physical_key=physics,cache_directory=str(folder),
                    output_sha256=hashlib.sha256(raw).hexdigest(),input_sha256=canonical_hash(job['input']),
                    elapsed_seconds=invocation['elapsed_seconds'],observed_or_reconstructed='observed',
                    binary_sha256=protocol['binary_sha256'],observation=OBSERVATION)
                atomic_json(saved,summary)
                append_json(run/'RUN_RECEIPTS.jsonl',{'batch_id':batch.name,'cache_key':key,
                    'physical_key':physics,'utc':now(),'iterations':summary['iterations'],
                    'elapsed_seconds':summary['elapsed_seconds'],'status':'completed',
                    'cache_directory':str(folder)})
                return {**summary,'cache_hit':False}
            except Exception as exc:
                completed=None
                try:completed=json.loads(output.read_text()).get('iterationsDone')
                except (OSError,ValueError):pass
                exc.native_started=True
                exc.iterations_completed=completed
                atomic_json(trial/'failure.json',{'utc':now(),'error':repr(exc),'elapsed_seconds':time.time()-started})
                append_json(run/'RUN_RECEIPTS.jsonl',{'batch_id':batch.name,'cache_key':key,
                    'physical_key':physics,'utc':now(),'status':'failed','error':repr(exc),
                    'iterations_requested':job['input']['request']['simOptions']['iterations'],
                    'iterations_completed':completed,'native_invocation_started':True,
                    'attempt_directory':str(trial)})
                raise


def run_batch(jobs, *, run_root, batch_id, phase, workers=48, max_wall_hours=24,
              resume=False, science=None):
    root=setup_paths();run=Path(run_root)
    if Path(batch_id).name!=batch_id: raise ValueError('batch_id must be one component')
    quota=Path('/sys/fs/cgroup/cpu.max').read_text().split()
    cpus=min(64,len(os.sched_getaffinity(0)),int(quota[0])//int(quota[1]) if quota[0]!='max' else 64)
    if not 1<=workers<=cpus: raise ValueError('worker request exceeds CPU allocation')
    budget=campaign(run,max_wall_hours)
    budget['worker_limit_total']=cpus
    mem=Path('/sys/fs/cgroup/memory.max').read_text().strip()
    if mem!='max': budget['memory_soft_bytes']=min(budget['memory_soft_bytes'],int(int(mem)*.8))
    binary=root/'envs/r3-go/wowfs-native-variants'
    batch=run/'batches'/batch_id;batch.mkdir(parents=True, exist_ok=True)
    with lock(batch/'run.lock',blocking=False):
        sources=source_snapshot()
        protocol={'schema_version':1,'phase':phase,'batch_id':batch_id,'science':science or {},
                  'binary_sha256':file_hash(binary),'source_hashes':sources,
                  'jobs_sha256':canonical_hash(jobs),'logical_cells':len(jobs),
                  'observation':OBSERVATION,'randomization':'Native labeled seed+i, common random seeds within declared blocks; cells are not independent worlds.'}
        p=batch/'PROTOCOL.json'
        if p.exists():
            if not resume or json.loads(p.read_text())!=protocol:
                raise ValueError('resume requires identical jobs, source, binary and protocol')
        else:
            for job in jobs:validate_equipment(job['input'])
            atomic_json(p,protocol);atomic_json(batch/'JOBS.json',jobs)
            atomic_json(batch/'FREEZE_TIME.json',{'utc':now()})
            shutil.copy2(binary,batch/'native.frozen')
            for rel in sources:
                dest=batch/'source'/rel;dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(SOURCE_ROOT/rel,dest)
                if file_hash(dest)!=sources[rel]:
                    raise RuntimeError('source changed during freeze: '+rel)
        if file_hash(batch/'native.frozen')!=protocol['binary_sha256']:
            raise ValueError('frozen executable hash mismatch')
        for rel,expected in sources.items():
            if file_hash(batch/'source'/rel)!=expected:
                raise ValueError('frozen source hash mismatch: '+rel)
        unique={};indices={}
        for i,job in enumerate(jobs):
            key=canonical_hash(job['input']);unique.setdefault(key,job);indices.setdefault(key,[]).append(i)
        rows=[None]*len(jobs);errors=[];done=calls=battles=hits=unknown_failed=0
        pending_jobs=iter(unique.items());active={};started=time.time()
        def progress(status):
            value={'status':status,'phase':phase,'batch_id':batch_id,'logical_cells':len(jobs),
                'unique_inputs':len(unique),'completed_inputs':done,'new_calls_this_invocation':calls,
                'new_battles_this_invocation':battles,'cache_hits_this_invocation':hits,
                'failed_inputs':len(errors),'elapsed_seconds_this_invocation':time.time()-started,
                'failed_calls_with_unknown_completed_battles':unknown_failed,
                'campaign_seconds_remaining':max(0,budget['deadline_epoch']-time.time()),
                'memory_current':memory_used(),'utc':now()}
            atomic_json(batch/'PROGRESS.json',value)
            return value
        progress('running')
        with ThreadPoolExecutor(max_workers=workers) as pool:
            while True:
                while len(active)<workers and time.time()<budget['deadline_epoch']:
                    try: key,job=next(pending_jobs)
                    except StopIteration: break
                    f=pool.submit(execute_cell,job,root=root,run=run,batch=batch,protocol=protocol,budget=budget)
                    active[f]=key
                if not active: break
                ready,_=wait(active,timeout=10,return_when=FIRST_COMPLETED)
                if not ready:progress('running');continue
                for future in ready:
                    key=active.pop(future);done+=1
                    try:
                        row=future.result()
                        hits+=bool(row['cache_hit']);calls+=not row['cache_hit']
                        battles+=row['iterations'] if not row['cache_hit'] else 0
                        for i in indices[key]: rows[i]={**row,**jobs[i]['meta']}
                    except Exception as exc:
                        invoked=getattr(exc,'native_started',False)
                        completed=getattr(exc,'iterations_completed',None)
                        calls+=bool(invoked)
                        if invoked and completed is None:unknown_failed+=1
                        elif invoked:battles+=completed
                        errors.append({'input_sha256':key,'error':repr(exc),
                            'native_invocation_started':invoked,'iterations_completed':completed})
                if done%100==0 or done==len(unique):print(json.dumps(progress('running')),flush=True)
        status='completed' if done==len(unique) and not errors else 'partial'
        atomic_json(batch/'RESULTS.json',{'rows':rows,'errors':errors,'status':status})
        atomic_json(batch/'OBSERVATION_INDEX.json',[
            {k:v for k,v in row.items() if k not in ('dps_samples','actions','resources','auras')}
            for row in rows if row is not None])
        print(json.dumps(progress(status)),flush=True)
        return batch


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--resume',action='store_true')
    p.add_argument('--phase',required=True,choices=['audit','discover','challenge','confirm','report'])
    p.add_argument('--config',required=True,type=Path)
    p.add_argument('--run-root',required=True,type=Path)
    p.add_argument('--workers',type=int,default=48)
    p.add_argument('--max-wall-hours',type=float,default=24)
    args=p.parse_args();cfg=json.loads(args.config.read_text())
    jobs=json.loads(Path(cfg['jobs_file']).read_text())
    run_batch(jobs,run_root=args.run_root,batch_id=cfg['batch_id'],phase=args.phase,
              workers=args.workers,max_wall_hours=args.max_wall_hours,resume=args.resume,
              science=cfg.get('science',{}))


if __name__=='__main__':main()
