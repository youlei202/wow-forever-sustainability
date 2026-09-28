"""Query-only benchmark with target-driven maximal SAT completion caching.

Harness copied from co_benchmark_ipc.py after the infrastructure smoke fixes,
before primary query testing. Frozen existence solver modules are unchanged.

Revision responds to preserved shared-NAS stalls, not observed algorithm losses.
Each problem starts with a fresh model/cache in an isolated process. Library
startup is common environment preparation, recorded separately. Compilation
serialization/reload is measured in memory, where repeated queries execute;
durable review archival has separate receipts and does not create solver NOs.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
from contextlib import nullcontext
from datetime import datetime,timezone
import hashlib
import io
import json
import multiprocessing as mp
import os
from pathlib import Path
import resource
import signal
import threading
import time
import traceback

from wowfs.paths import SOURCE_ROOT,atomic_json,canonical_hash
from wowfs.experiments.co_benchmark import deadline,BudgetExpired,strip_result,physical_cpus,METHODS

QUERY_METHODS=('reference_fresh','reference_cached','reference_interface',
               'sat_incremental','sat_interface','sat_maximal_cache')


def maximal_sat_query(solver,target,time_limit):
    """Return an initial YES even if optional maximal-witness growth times out.

    Only the first query may supply a target UNSAT core. Later UNSAT proves
    absence of a strict feasible superset, never target infeasibility. The
    persistent solver's strict-superset constraints are assumption gated.
    """
    started=time.perf_counter();end=started+max(0,time_limit)
    first=solver.query(target,time_limit=max(0,end-time.perf_counter()))
    if first['status']!='YES':return first
    best=dict(first);calls=0;maximal=False;growth_status='NOT_STARTED';expired=False
    first_seconds=time.perf_counter()-started
    try:
        while time.perf_counter()<end:
            before=frozenset(best['items'])
            enlarged=solver.query(time_limit=max(0,end-time.perf_counter()),strict_superset=before)
            calls+=1;growth_status=enlarged['status']
            if growth_status=='YES':
                after=frozenset(enlarged['items'])
                if not before<after:raise AssertionError('Strict-superset solver did not enlarge publication')
                best=dict(enlarged)
            elif growth_status=='NO':maximal=True;break
            else:break
    except BudgetExpired:
        # Save the already verified answer, then ask the driver to stop after
        # recording this query. Swallowing the alarm and continuing would reset
        # the whole-history budget in effect, so stop_after_query is mandatory.
        growth_status='WHOLE_HISTORY_TIMEOUT';expired=True
    if not maximal and not expired and time.perf_counter()>=end and growth_status in ('YES','NOT_STARTED'):
        growth_status='UNKNOWN_TIMEOUT'
    best.update(status='YES',elapsed_seconds=time.perf_counter()-started,
                initial_decision_seconds=first_seconds,maximality_proved=maximal,
                maximization_status=growth_status,maximization_solver_calls=calls,
                stop_after_query=expired)
    best.pop('unsat_core',None)
    return best

def compute(job):
    # Import all methods before the common method clock, including native
    # extension startup. The outer process receipt also includes startup time.
    from ortools.sat.python import cp_model  # common untimed dependency startup
    from pysat.solvers import Glucose4
    from pysat.pb import PBEnc
    from wowfs.experiments.co_exact import Model, evaluate, interface_query
    from wowfs.experiments.co_generic import CPSatSolver,IncrementalSAT,compile_interface
    from wowfs.experiments.co_reference import solve as reference_solve, compile_interface as reference_compile
    raw=job['instance'];method=job['method']
    started=time.perf_counter();budget=job['budget_seconds'];seed=job.get('solver_seed',0)
    common={'instance_id':raw['instance_id'],'family':raw.get('family','native'),'workflow':job['workflow'],
            'method':method,'solver_seed':seed,'seed_semantics':('active_CP_SAT_random_seed' if method=='cp_sat' else 'deterministic_repeat_label'),'budget_seconds':budget,'cpu_affinity':sorted(os.sched_getaffinity(0))}
    solver=None;count=0;interface=None;records=[];cumulative=[];preparation=None;qstream=io.StringIO()
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
                    serialized=json.dumps(interface,sort_keys=True,default=str)
                    interface=json.loads(serialized)
                    interface['serialized_representation_bytes']=len(serialized.encode())
                    for kernel in interface.get('kernels',[]):
                        if not evaluate(model,kernel)['valid']:raise AssertionError('invalid compiled kernel')
                elif method in ('sat_incremental','sat_maximal_cache'):solver=IncrementalSAT(model,seed=seed)
                preparation=time.perf_counter()-prep
                yes_cache=[];no_cache=[];cumulative=[]
                with nullcontext(qstream) as f:
                    for query in queries:
                        target=frozenset(query['target']);qstart=time.perf_counter();cached=None
                        if method.endswith('_interface'):
                            result=interface_query(interface,target)
                        elif method in ('sat_incremental','sat_maximal_cache','reference_cached'):
                            witness=next((k for k in yes_cache if target<=k),None)
                            core=next((k for k in no_cache if k<=target),None)
                            if witness is not None:result={'status':'YES','items':sorted(witness)};cached='verified_completion'
                            elif core is not None:result={'status':'NO','core':sorted(core)};cached='unsat_target_core'
                            else:
                                query_limit=min(job['per_query_seconds'],remaining())
                                if method=='sat_maximal_cache':result=maximal_sat_query(solver,target,query_limit)
                                elif method=='sat_incremental':result=solver.query(target,time_limit=query_limit)
                                else:result=reference_solve(model,target,time_limit=query_limit)
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
                        if result.get('stop_after_query'):
                            raise BudgetExpired('Whole-history deadline reached during optional witness maximization; verified YES retained')
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
    final['storage_scope']='In-memory interface serialization/reload and query recording included; durable archive IO recorded separately by parent, outside method clock.'
    return final,interface,qstream.getvalue()


def child(job,cpu,connection):
    os.sched_setaffinity(0,{cpu})
    connection.send({'event':'method_start','monotonic':time.monotonic(),'pid':os.getpid()})
    try:result,interface,query_text=compute(job)
    except BaseException as exc:
        result={'instance_id':job['instance']['instance_id'],'method':job['method'],'workflow':job['workflow'],
                'solver_seed':job.get('solver_seed',0),'status':'ERROR','error':repr(exc),'traceback':traceback.format_exc()}
        interface=None;query_text=''
    connection.send({'event':'computed','result':result})
    connection.send({'event':'payload','interface':interface,'query_text':query_text})
    connection.close()


def measured_job(ctx,job,cpu):
    import psutil
    recv,send=ctx.Pipe(duplex=False)
    started=time.monotonic();proc=ctx.Process(target=child,args=(job,cpu,send));proc.start();send.close()
    try:ps=psutil.Process(proc.pid)
    except psutil.NoSuchProcess:ps=None
    peak=0;clock_start=None;result=None;payload={};termination=None;computed_received=False
    while True:
        if recv.poll(.05):
            try:message=recv.recv()
            except EOFError:break
            if message['event']=='method_start':clock_start=message['monotonic']
            elif message['event']=='computed':result=message['result'];computed_received=True
            else:payload=message;break
        try:
            if ps is not None:peak=max(peak,ps.memory_info().rss)
        except psutil.NoSuchProcess:pass
        if not proc.is_alive():
            if not recv.poll():break
        elapsed=time.monotonic()-(clock_start or started)
        if clock_start is None and elapsed>300:termination='INFRASTRUCTURE_STARTUP_TIMEOUT'
        elif clock_start is not None and result is None and elapsed>job['budget_seconds']+5:termination='TIMEOUT_PROCESS'
        elif result is not None and elapsed>job['budget_seconds']+300:termination='INFRASTRUCTURE_IPC_TIMEOUT'
        if peak>8*1024**3:termination='MEMORY_LIMIT'
        if termination:
            proc.terminate();proc.join(3)
            if proc.is_alive():proc.kill()
            break
    proc.join(3)
    if proc.is_alive():proc.terminate();proc.join(3)
    recv.close()
    if result is None:
        result={'instance_id':job['instance']['instance_id'],'family':job['instance'].get('family','native'),
          'workflow':job['workflow'],'method':job['method'],'solver_seed':job.get('solver_seed',0),
          'budget_seconds':job['budget_seconds'],'status':('UNKNOWN_TIMEOUT' if termination=='TIMEOUT_PROCESS' else 'UNKNOWN_MEMORY' if termination=='MEMORY_LIMIT' else 'INFRASTRUCTURE_FAILURE'),
          'reason':termination or 'worker_died','method_elapsed_seconds':time.monotonic()-clock_start if clock_start else None,'method_time_censored_proxy':True}
    peak=max(peak,result.get('peak_self_rss_bytes',0))
    if computed_received and not payload:
        result={**result,'computed_status_before_ipc_failure':result['status'],'status':'INFRASTRUCTURE_FAILURE','reason':'payload_incomplete'}
    receipt={'outer_elapsed_seconds':time.monotonic()-started,'startup_seconds':None if clock_start is None else clock_start-started,
             'peak_process_tree_rss_bytes':peak,'returncode':proc.exitcode,'termination':termination,'cpu':cpu,
             'harness':'preloaded_forkserver_IPC','archive_IO_in_method_clock':False}
    return result,payload,receipt


def run_suite(registry,output,workers,budget,workflow='queries',query_budget=900):
    import shutil
    if workflow!='queries':raise ValueError('This driver is query-only; existence experiments retain their frozen driver')
    output=Path(output);output.mkdir(parents=True,exist_ok=True);registry=Path(registry)
    instances=[json.loads(s) for s in (registry/'BENCHMARK_INSTANCES.jsonl').read_text().splitlines()]
    streams=[json.loads(s) for s in (registry/'QUERY_STREAMS.jsonl').read_text().splitlines()]
    files=['co_exact.py','co_generic.py','co_reference.py','co_benchmark.py','co_benchmark_ipc.py','co_benchmark_preload.py',
           'co_benchmark_design.py','co_query_benchmark.py','co_query_preload.py']
    sources={x:hashlib.sha256((SOURCE_ROOT/'src/wowfs/experiments'/x).read_bytes()).hexdigest() for x in files}
    from importlib.metadata import version
    versions={name:version(name) for name in ('ortools','python-sat','pypblib','numpy','psutil')}
    protocol={'runtime_versions':versions,'registry_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in registry.glob('*.jsonl')},'source_hashes':sources,
      'workers':workers,'query_seconds':budget,'history_workflow_seconds':query_budget,'workflow':workflow,'single_thread':True,'native_pause_required':True,
      'harness':'preloaded_forkserver_IPC','cold_problem_specific_state':True,'all_common_library_startup_recorded_separately':True,
      'compilation_serialization_reload':'In-memory JSON buffer, included in method clock. Durable NAS export measured separately.',
      'infrastructure_revision':'Same frozen problems and core solvers; query-only driver adds a sixth generic baseline before query freeze.',
      'query_methods':list(QUERY_METHODS),
      'sat_maximal_cache_protocol':'First exact target decision, then strict feasible supersets within the same per-query and history budget. Cache largest independently verified YES even if maximality times out. Only initial target UNSAT cores enter the NO cache.'}
    frozen=output/'PROTOCOL_FROZEN.json'
    if frozen.exists() and json.loads(frozen.read_text())!=protocol:raise ValueError('frozen suite changed')
    if not frozen.exists():
        atomic_json(frozen,protocol);atomic_json(output/'FREEZE_TIME.json',{'utc':datetime.now(timezone.utc).isoformat()})
        (output/'source').mkdir(exist_ok=True)
        for name in files:shutil.copy2(SOURCE_ROOT/'src/wowfs/experiments'/name,output/'source'/name)
    campaign_path=next((p/'CAMPAIGN_STATUS.json' for p in [output,*output.parents] if (p/'CAMPAIGN_STATUS.json').exists()),None)
    campaign_deadline=datetime.fromisoformat(json.loads(campaign_path.read_text())['deadline_utc']).timestamp() if campaign_path else float('inf')
    jobs=[]
    if workflow=='existence':
        for i,row in enumerate(instances):
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
    # This network-backed WORK filesystem rejects filesystem Unix sockets.
    # Linux abstract sockets carry IPC in memory; no artifact is placed elsewhere.
    import multiprocessing.connection as connection
    original_address=connection.arbitrary_address
    connection.arbitrary_address=lambda family: ('\0wowfs_co_'+str(os.getpid())+'_'+str(time.monotonic_ns())) if family=='AF_UNIX' else original_address(family)
    mp.set_forkserver_preload(['wowfs.experiments.co_query_preload'])
    ctx=mp.get_context('forkserver');cpus=physical_cpus()[:workers]
    # Warm server once, before lane clocks, on the same fixed tiny instance.
    smoke={'instance_id':'independent_library_warmup','family':'infrastructure','slots':{'a':0,'b':0,'x':1},'configurations':[{'support':['a','x'],'values':['1']},{'support':['b','x'],'values':['2']}],'history':['a','x'],'weights':['1'],'tolerance':['2'],'cap':['3'],'gain':['1'],'required_mass':'1','gain_mass':'1','target':['b']}
    warm_job={'instance':smoke,'method':'sat','solver_seed':0,'workflow':'unknown_y','budget_seconds':5}
    startup=time.monotonic();warm=measured_job(ctx,warm_job,cpus[0]);atomic_json(output/'COMMON_SERVER_STARTUP.json',{'elapsed_seconds':time.monotonic()-startup,'receipt':warm[2],'not_a_test_result':True})
    if warm[0]['status']!='YES':raise RuntimeError(('preloaded server smoke failed',warm[0]))
    groups=[jobs[i::workers] for i in range(workers)];abort=threading.Event();lock=threading.Lock();decisions={}
    def lane(i):
        rows=[]
        for job in groups[i]:
            if abort.is_set() or time.time()+job['budget_seconds']+15>campaign_deadline:
                rows.append({'instance_id':job['instance']['instance_id'],'method':job['method'],'workflow':job['workflow'],'status':'NOT_RUN','reason':'correctness_or_budget_stop'});continue
            key=canonical_hash(job);sub=output/key;sub.mkdir(exist_ok=True)
            if (sub/'RESULT.json').exists():row=json.loads((sub/'RESULT.json').read_text())
            else:
                atomic_json(sub/'JOB.json',job)
                row,payload,receipt=measured_job(ctx,job,cpus[i])
                archive_started=time.monotonic()
                if payload.get('interface') is not None:atomic_json(sub/'RESULT.interface.json',payload['interface'])
                if payload.get('query_text') is not None:(sub/'RESULT.queries.jsonl').write_text(payload['query_text'])
                atomic_json(sub/'RESULT.json',row)
                receipt['durable_archive_seconds']=time.monotonic()-archive_started
                atomic_json(sub/'PROCESS.json',receipt)
            rows.append(row)
            if row['status'] in ('ERROR','INFRASTRUCTURE_FAILURE'):
                abort.set();atomic_json(output/'ERROR_STOP.json',row)
            if job['workflow'] in ('fixed_y','unknown_y') and row['status'] in ('YES','NO','INVALID_INITIAL'):
                with lock:
                    identity=(job['instance']['instance_id'],job['workflow']);previous=decisions.setdefault(identity,row['status'])
                    if previous!=row['status']:
                        abort.set();atomic_json(output/'CORRECTNESS_MISMATCH.json',{'identity':identity,'prior_status':previous,'result':row})
        return rows
    all_rows=[]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for fut in as_completed([pool.submit(lane,i) for i in range(workers)]):
            all_rows.extend(fut.result());atomic_json(output/'RESULTS_AGGREGATE.json',all_rows)
    print(json.dumps({'jobs':len(all_rows),'statuses':{s:sum(r['status']==s for r in all_rows) for s in sorted({r['status'] for r in all_rows})},'output':str(output)}),flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--registry',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--workers',type=int,default=8);p.add_argument('--budget',type=float,default=60);p.add_argument('--query-budget',type=float,default=900)
    p.add_argument('--workflow',choices=['queries'],default='queries')
    a=p.parse_args();run_suite(a.registry,a.output,a.workers,a.budget,a.workflow,a.query_budget)

if __name__=='__main__':main()
