"""Matched-task, process-isolated solver and repeat-query measurements.

All methods receive the same exact model and target order. Python/module launch
is recorded separately; timed method work includes exact parsing, construction,
solving, witness checking, and interface serialization/reload. Each worker is
pinned to one physical core and all native runs must be paused for primary data.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
from contextlib import contextmanager
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
import traceback
import threading

from wowfs.paths import atomic_json, canonical_hash, SOURCE_ROOT

METHODS=('reference','cp_sat','sat')
QUERY_METHODS=('reference_fresh','reference_cached','reference_interface','sat_incremental','sat_interface')

class BudgetExpired(Exception):pass

@contextmanager
def deadline(seconds):
    def handle(*args):raise BudgetExpired('end-to-end wall budget expired')
    previous=signal.signal(signal.SIGALRM,handle)
    signal.setitimer(signal.ITIMER_REAL,max(.001,seconds))
    try:yield
    finally:signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,previous)


def strip_result(result):
    return {k:v for k,v in result.items() if k not in ('verifier','solutions')}


def run_worker(job_path, output):
    # Import all methods before the common method clock, including native
    # extension startup. The outer process receipt also includes startup time.
    from ortools.sat.python import cp_model  # common untimed dependency startup
    from pysat.solvers import Glucose4
    from pysat.pb import PBEnc
    from wowfs.experiments.co_exact import Model, evaluate, interface_query
    from wowfs.experiments.co_generic import CPSatSolver,IncrementalSAT,compile_interface
    from wowfs.experiments.co_reference import solve as reference_solve, compile_interface as reference_compile
    job=json.loads(Path(job_path).read_text());raw=job['instance'];method=job['method']
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    started=time.perf_counter();budget=job['budget_seconds'];seed=job.get('solver_seed',0)
    common={'instance_id':raw['instance_id'],'family':raw.get('family','native'),'workflow':job['workflow'],
            'method':method,'solver_seed':seed,'seed_semantics':('active_CP_SAT_random_seed' if method=='cp_sat' else 'deterministic_repeat_label'),'budget_seconds':budget,'cpu_affinity':sorted(os.sched_getaffinity(0))}
    solver=None;count=0;interface=None;records=[];cumulative=[];preparation=None
    def remaining():return max(.001,budget-(time.perf_counter()-started))
    try:
        with deadline(budget):
            model=Model.from_dict(raw)
            parsed=time.perf_counter()
            if job['workflow'] in ('fixed_y','unknown_y'):
                fixed=raw['fixed_y'] if job['workflow']=='fixed_y' else None
                if method=='reference':result=reference_solve(model,raw.get('target',()),fixed_y=fixed,time_limit=remaining())
                else:
                    solver=(CPSatSolver if method=='cp_sat' else IncrementalSAT)(model,fixed_y=fixed,seed=seed)
                    result=solver.query(raw.get('target',()),time_limit=remaining())
                # Generic/reference methods already use a common independent
                # witness checker; retain its result and charge that work.
                if result['status']=='YES' and not result.get('verifier',{}).get('valid',False):
                    checked=evaluate(model,result['items'],fixed_y=fixed)
                    if not checked['valid']:raise AssertionError(('bad witness',checked,result))
                final={**common,**strip_result(result),'method_elapsed_seconds':time.perf_counter()-started,'parse_seconds':parsed-started}
            else:
                stream=job['query_stream'];queries=stream['queries'];prefixes=set(stream['prefixes'])
                prep=time.perf_counter()
                if method.endswith('_interface'):
                    allowance=min(job.get('compile_budget_seconds',budget),remaining())
                    interface=reference_compile(model,time_limit=allowance) if method.startswith('reference') else compile_interface('sat',model,time_limit=allowance,seed=seed)
                    # Serialize and reload the representation and validate all
                    # returned kernels before they can answer even one query.
                    ip=output.with_suffix('.interface.json');atomic_json(ip,interface)
                    interface=json.loads(ip.read_text())
                    for kernel in interface.get('kernels',[]):
                        if not evaluate(model,kernel)['valid']:raise AssertionError('invalid compiled kernel')
                elif method=='sat_incremental':solver=IncrementalSAT(model,seed=seed)
                preparation=time.perf_counter()-prep
                yes_cache=[];no_cache=[];cumulative=[]
                qfile=output.with_suffix('.queries.jsonl')
                with qfile.open('w') as f:
                    for query in queries:
                        target=frozenset(query['target']);qstart=time.perf_counter();cached=None
                        if method.endswith('_interface'):
                            result=interface_query(interface,target)
                        elif method in ('sat_incremental','reference_cached'):
                            witness=next((k for k in yes_cache if target<=k),None)
                            core=next((k for k in no_cache if k<=target),None)
                            if witness is not None:result={'status':'YES','items':sorted(witness)};cached='verified_completion'
                            elif core is not None:result={'status':'NO','core':sorted(core)};cached='unsat_target_core'
                            else:
                                result=solver.query(target,time_limit=min(job['per_query_seconds'],remaining())) if method=='sat_incremental' else reference_solve(model,target,time_limit=min(job['per_query_seconds'],remaining()))
                                if result['status']=='YES':yes_cache.append(frozenset(result['items']))
                                elif result['status']=='NO':no_cache.append(frozenset(result.get('unsat_core',target)))
                        else:result=reference_solve(model,target,time_limit=min(job['per_query_seconds'],remaining()))
                        record={**common,'query_index':query['query_index'],'query_kind':query['query_kind'],
                                'target':sorted(target),**strip_result(result),'cache':cached,
                                'query_elapsed_seconds':time.perf_counter()-qstart,'cumulative_seconds':time.perf_counter()-started}
                        # No full source-witness matrix replicated per query.
                        f.write(json.dumps(record,sort_keys=True,default=str)+'\n');f.flush();count+=1
                        if count in prefixes:
                            cumulative.append({'prefix':count,'seconds':time.perf_counter()-started})
                final={**common,'status':'COMPLETE','queries_answered':count,'queries_total':len(queries),
                       'preparation_seconds':preparation,'interface_complete':None if interface is None else interface.get('complete',False),
                       'kernel_count':None if interface is None else len(interface.get('kernels',[])),
                       'prefix_times':cumulative,'method_elapsed_seconds':time.perf_counter()-started}
    except (BudgetExpired,TimeoutError) as exc:
        final={**common,'status':'UNKNOWN_TIMEOUT','queries_answered':count,'method_elapsed_seconds':time.perf_counter()-started,'error':str(exc),'prefix_times':cumulative,'preparation_seconds':preparation,'interface_complete':None if interface is None else interface.get('complete',False),'kernel_count':None if interface is None else len(interface.get('kernels',[]))}
    except Exception as exc:
        final={**common,'status':'ERROR','error':repr(exc),'traceback':traceback.format_exc(),'queries_answered':count,'method_elapsed_seconds':time.perf_counter()-started}
    finally:
        if solver is not None:solver.close()
    final['peak_self_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    final['self_user_cpu_seconds']=resource.getrusage(resource.RUSAGE_SELF).ru_utime
    final['self_system_cpu_seconds']=resource.getrusage(resource.RUSAGE_SELF).ru_stime
    atomic_json(output,final)
    print(json.dumps(final,default=str),flush=True)


def physical_cpus():
    seen=set();cpus=[]
    for cpu in sorted(os.sched_getaffinity(0)):
        p=Path(f'/sys/devices/system/cpu/cpu{cpu}/topology')
        key=((p/'physical_package_id').read_text(),(p/'core_id').read_text())
        if key not in seen:seen.add(key);cpus.append(cpu)
    return cpus


def run_job(job, folder, cpu):
    import psutil
    key=canonical_hash(job);sub=folder/key;sub.mkdir(exist_ok=True)
    jp=sub/'JOB.json';out=sub/'RESULT.json'
    if jp.exists() and json.loads(jp.read_text())!=job:raise ValueError('changed benchmark job')
    if out.exists():return json.loads(out.read_text())
    atomic_json(jp,job);started=time.monotonic();peak=0
    command=['taskset','-c',str(cpu),sys.executable,'-m','wowfs.experiments.co_benchmark','--worker-job',str(jp),'--worker-output',str(out)]
    with (sub/'stdout.log').open('w') as stdout,(sub/'stderr.log').open('w') as stderr:
        proc=subprocess.Popen(command,stdout=stdout,stderr=stderr,start_new_session=True,
            env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','PYTHONHASHSEED':'0'})
        parent=psutil.Process(proc.pid);termination=None
        while proc.poll() is None:
            try:peak=max(peak,sum(p.memory_info().rss for p in [parent]+parent.children(recursive=True)))
            except psutil.NoSuchProcess:pass
            if time.monotonic()-started>job['budget_seconds']+15:termination='TIMEOUT_PROCESS'
            if peak>8*1024**3:termination='MEMORY_LIMIT'
            if termination:
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=3)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
                break
            time.sleep(.1)
    receipt={'command':command,'outer_elapsed_seconds':time.monotonic()-started,'peak_process_tree_rss_bytes':peak,'returncode':proc.returncode,'termination':termination}
    atomic_json(sub/'PROCESS.json',receipt)
    if not out.exists():
        atomic_json(out,{'instance_id':job['instance']['instance_id'],'family':job['instance'].get('family','native'),
            'workflow':job['workflow'],'method':job['method'],'solver_seed':job.get('solver_seed',0),
            'budget_seconds':job['budget_seconds'],'status':'UNKNOWN_TIMEOUT' if termination=='TIMEOUT_PROCESS' else 'UNKNOWN_MEMORY' if termination=='MEMORY_LIMIT' else 'ERROR',
            'reason':termination or 'worker_died','method_elapsed_seconds':job['budget_seconds'] if termination else receipt['outer_elapsed_seconds']})
    return json.loads(out.read_text())


def run_suite(registry, output, workers, budget, workflow='existence', query_budget=300):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    registry=Path(registry);instances=[json.loads(s) for s in (registry/'BENCHMARK_INSTANCES.jsonl').read_text().splitlines()]
    streams=[json.loads(s) for s in (registry/'QUERY_STREAMS.jsonl').read_text().splitlines()]
    files=['co_exact.py','co_generic.py','co_reference.py','co_benchmark.py','co_benchmark_design.py']
    sources={x:hashlib.sha256((SOURCE_ROOT/'src/wowfs/experiments'/x).read_bytes()).hexdigest() for x in files}
    protocol={'registry_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in registry.glob('*.jsonl')},'source_hashes':sources,
              'workers':workers,'query_seconds':budget,'history_workflow_seconds':query_budget,'workflow':workflow,'single_thread':True,'native_pause_required':True}
    frozen=output/'PROTOCOL_FROZEN.json'
    if frozen.exists() and json.loads(frozen.read_text())!=protocol:raise ValueError('frozen protocol changed; use a new directory')
    if not frozen.exists():
        import shutil
        atomic_json(frozen,protocol);atomic_json(output/'FREEZE_TIME.json',{'utc':datetime.now(timezone.utc).isoformat()})
        (output/'source').mkdir(exist_ok=True)
        for name in files:shutil.copy2(SOURCE_ROOT/'src/wowfs/experiments'/name,output/'source'/name)
    campaign_path=next((p/'CAMPAIGN_STATUS.json' for p in [output,*output.parents] if (p/'CAMPAIGN_STATUS.json').exists()),None)
    campaign_deadline=datetime.fromisoformat(json.loads(campaign_path.read_text())['deadline_utc']).timestamp() if campaign_path else float('inf')
    jobs=[]
    if workflow=='existence':
        for i,row in enumerate(instances):
            # Balanced fixed registry subset gets three repetitions; shared
            # seeds apply to every method, even deterministic reference.
            rep=int(row['instance_id'].split('_')[2]) if row.get('data_kind')=='SYNTHETIC_EXACT' else i
            seeds=(0,1,2) if rep in (0,6,12,18,19) else (0,)
            for seed in seeds:
                for offset in range(len(METHODS)):
                    method=METHODS[(i+offset)%len(METHODS)]
                    jobs.append({'instance':row,'method':method,'solver_seed':seed,'workflow':row['workflow'],'budget_seconds':budget})
    else:
        lookup={r['instance_id']:r for r in instances}
        for i,stream in enumerate(streams):
            for offset in range(len(QUERY_METHODS)):
                method=QUERY_METHODS[(i+offset)%len(QUERY_METHODS)]
                jobs.append({'instance':lookup[stream['instance_id']],'query_stream':stream,'method':method,'workflow':'repeat_queries','solver_seed':0,
                             'budget_seconds':query_budget,'compile_budget_seconds':query_budget*.8,'per_query_seconds':budget})
    atomic_json(output/'JOB_INDEX.json',[{'job_hash':canonical_hash(j),'instance_id':j['instance']['instance_id'],'method':j['method'],'solver_seed':j['solver_seed']} for j in jobs])
    cpus=physical_cpus()[:workers]
    # Each lane owns its core; no concurrent workers share a logical or SMT core.
    groups=[jobs[i::workers] for i in range(workers)]
    abort=threading.Event();decision_lock=threading.Lock();decisions={}
    def lane(index):
        rows=[]
        for job in groups[index]:
            if abort.is_set():
                rows.append({'instance_id':job['instance']['instance_id'],'method':job['method'],'workflow':job['workflow'],'status':'NOT_RUN','reason':'correctness_or_runtime_error_requires_audit'});continue
            if time.time()+job['budget_seconds']+15>campaign_deadline:
                rows.append({'instance_id':job['instance']['instance_id'],'method':job['method'],'workflow':job['workflow'],'status':'NOT_RUN','reason':'campaign_deadline_would_be_exceeded'});continue
            row=run_job(job,output,cpus[index]);rows.append(row)
            if row['status']=='ERROR':
                abort.set();print(json.dumps({'error':row}),flush=True)
            if job['workflow'] in ('fixed_y','unknown_y') and row['status'] in ('YES','NO','INVALID_INITIAL'):
                with decision_lock:
                    identity=(job['instance']['instance_id'],job['workflow'])
                    previous=decisions.setdefault(identity,row['status'])
                    if previous!=row['status']:
                        abort.set();atomic_json(output/'CORRECTNESS_MISMATCH.json',{'identity':identity,'prior_status':previous,'result':row})
        return rows
    all_rows=[]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for fut in as_completed([pool.submit(lane,i) for i in range(workers)]):
            all_rows.extend(fut.result());atomic_json(output/'RESULTS_AGGREGATE.json',all_rows)
    print(json.dumps({'jobs':len(all_rows),'statuses':{s:sum(r['status']==s for r in all_rows) for s in sorted({r['status'] for r in all_rows})},'output':str(output)}),flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--worker-job',type=Path);p.add_argument('--worker-output',type=Path)
    p.add_argument('--registry',type=Path);p.add_argument('--output',type=Path);p.add_argument('--workers',type=int,default=8)
    p.add_argument('--budget',type=float,default=60);p.add_argument('--query-budget',type=float,default=300);p.add_argument('--workflow',choices=['existence','queries'],default='existence')
    args=p.parse_args()
    if args.worker_job:run_worker(args.worker_job,args.worker_output)
    else:run_suite(args.registry,args.output,args.workers,args.budget,args.workflow,args.query_budget)

if __name__=='__main__':main()
