"""Audit and compact reporting for the frozen completion benchmark.

Exact tables are deterministic numerical objects. Runtime intervals here are
descriptive cluster resamples, not population claims about native catalogues.
The --check mode recomputes headline metrics from compact CSVs without raw jobs.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import gzip
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import random
import shutil
import statistics
import subprocess
import time

DECIDED = {'YES', 'NO'}
KNOWN = DECIDED | {'INVALID_INITIAL'}
UNRESOLVED = {'UNKNOWN_TIMEOUT', 'UNKNOWN_MEMORY', 'ERROR', 'NOT_RUN'}
SOURCE_ROOT = Path(__file__).resolve().parents[3]
SOURCE_BYTES_AT_IMPORT = Path(__file__).read_bytes()
SOURCE_SHA256_AT_IMPORT = hashlib.sha256(SOURCE_BYTES_AT_IMPORT).hexdigest()
LABELS = {'reference':'Reference Python','cp_sat':'CP-SAT','sat':'Incremental SAT',
          'reference_fresh':'Reference fresh','reference_cached':'Reference cached',
          'reference_interface':'Reference interface','sat_incremental':'SAT incremental + cache',
          'sat_interface':'SAT interface','sat_maximal_cache':'SAT maximal cache'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, data):
    Path(path).write_text(json.dumps(data, sort_keys=True, indent=2)+'\n')


def dump_csv(path, rows, fields=None):
    rows=list(rows)
    fields=fields or sorted(set().union(*(set(r) for r in rows)))
    opener=gzip.open if str(path).endswith('.gz') else open
    with opener(path,'wt',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction='raise');writer.writeheader()
        for row in rows:
            writer.writerow({k:json.dumps(v,sort_keys=True,separators=(',',':')) if isinstance(v,(list,dict)) else v for k,v in row.items()})


def read_csv(path):
    opener=gzip.open if str(path).endswith('.gz') else open
    with opener(path,'rt',newline='') as f:return list(csv.DictReader(f))


def number(v, default=None):
    return default if v in ('',None) else float(v)


def integer(v, default=0):
    return default if v in ('',None) else int(float(v))


def truth(v):
    return v is True or str(v).lower() in ('true','1')


def cluster_id(identity):
    for suffix in ('_fixed_y','_unknown_y'):
        if identity.endswith(suffix):return identity[:-len(suffix)]
    return identity


def cluster_metadata(raw, identity):
    """Avoid interpreting related native histories as independent catalogues."""
    history=raw.get('history_cluster_id') or cluster_id(identity)
    native='NATIVE' in raw.get('data_kind','')
    explicit=raw.get('catalogue_cluster_id') or raw.get('resampling_cluster_id')
    if explicit:
        cluster=explicit;basis='registered catalogue/resampling cluster'
    elif native:
        cluster=raw.get('family') or 'native_catalogue_independence_unestablished'
        basis='conservative native mechanism family; catalogue independence unestablished'
    else:
        cluster=history;basis='generated history; paired fixed/unknown tasks remain together'
    return {'history_cluster_id':history,'resampling_cluster_id':cluster,'resampling_cluster_basis':basis}


def checked_suite(folder, receipts):
    folder=Path(folder).resolve();index=read_json(folder/'JOB_INDEX.json')
    protocol=read_json(folder/'PROTOCOL_FROZEN.json')
    if (folder/'INFRASTRUCTURE_CONTAMINATED.json').exists():
        raise ValueError('Contaminated infrastructure suite must be excluded, not treated as algorithm timing: '+str(folder))
    for name,expected in protocol['source_hashes'].items():
        snapshot=folder/'source'/name
        if not snapshot.is_file():raise AssertionError(('Frozen source missing',str(snapshot)))
        if digest(snapshot)!=expected:
            raise AssertionError(('Frozen source mismatch',str(snapshot)))
    receipts.append({'path':str(folder),'evidence_role':'DEVELOPMENT_ONLY' if any(k in folder.name for k in ('develop','smoke')) else 'FROZEN_COMPUTATIONAL_TEST',
                     'job_index_sha256':digest(folder/'JOB_INDEX.json'),
                     'protocol_sha256':digest(folder/'PROTOCOL_FROZEN.json'),'protocol':protocol,
                     'common_server_startup':read_json(folder/'COMMON_SERVER_STARTUP.json') if (folder/'COMMON_SERVER_STARTUP.json').exists() else None,
                     'freeze_time':read_json(folder/'FREEZE_TIME.json') if (folder/'FREEZE_TIME.json').exists() else None})
    aggregate=read_json(folder/'RESULTS_AGGREGATE.json') if (folder/'RESULTS_AGGREGATE.json').exists() else []
    missing={}
    for r in aggregate:
        if r['status']=='NOT_RUN':missing[(r['instance_id'],r['method'])]=r
    for entry in index:
        sub=folder/entry['job_hash'];jp=sub/'JOB.json';rp=sub/'RESULT.json'
        job=read_json(jp) if jp.exists() else None
        if job is not None:
            job_digest=hashlib.sha256(json.dumps(job,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            assert job_digest==entry['job_hash'],('Job differs from registered hash',str(jp))
            assert job['instance']['instance_id']==entry['instance_id'] and job['method']==entry['method'],('Job/index identity mismatch',str(jp))
        result=read_json(rp) if rp.exists() else missing.get((entry['instance_id'],entry['method']),{
            'status':'NOT_RUN','reason':'no_completed_receipt_at_report_time'})
        yield folder,entry,job,result,sub,protocol


def model_lookup(job, models):
    from .co_exact import Model
    raw=job['instance'];key=json.dumps(raw,sort_keys=True)
    if key not in models:models[key]=Model.from_dict(raw)
    return models[key]


def existence_rows(folders, receipts):
    from .co_exact import evaluate, frontier
    rows=[];models={};verified=set();answers={};questions={}
    for folder in folders:
        for folder,entry,job,result,sub,protocol in checked_suite(folder,receipts):
            if job and job['workflow'] not in ('fixed_y','unknown_y'):continue
            raw=job['instance'] if job else {};workflow=job['workflow'] if job else result.get('workflow','unknown')
            identity=entry['instance_id'];status=result['status'];method=entry['method'];seed=entry.get('solver_seed',0)
            key=(str(folder),identity,workflow)
            if status in KNOWN:
                previous=answers.setdefault(key,status)
                if previous!=status:raise AssertionError(('Decision mismatch',key,previous,status))
            witness_verified=False;contract_hash=None;mandatory_cap_violation=None;cartesian=None;max_optional_support=None
            if job:
                model=model_lookup(job,models);contract_hash=model.digest
                question=(contract_hash,tuple(sorted(raw.get('target',[]))),tuple(raw.get('fixed_y',[])) if workflow=='fixed_y' else None,job['budget_seconds'])
                previous=questions.setdefault(key,question)
                assert previous==question,('Different exact question or budget across existence methods',key)
                max_optional_support=max((len(c.support-model.history) for c in model.configurations),default=0)
                fmandatory=frontier(model,model.history|frozenset(raw.get('target',[])))
                mandatory_cap_violation=fmandatory is not None and any(a>b for a,b in zip(fmandatory,model.cap))
                f0=frontier(model,model.history)
                if f0 is not None:
                    cartesian=math.prod(len({c.values[q] for c in model.configurations if f0[q]<=c.values[q]<=model.cap[q]}) for q in range(model.q))
                if status=='YES':
                    items=frozenset(result['items']);target=frozenset(raw.get('target',[]))
                    assert target<=items,(identity,'missing target')
                    fixed_y=raw.get('fixed_y') if workflow=='fixed_y' else None
                    vkey=(contract_hash,tuple(sorted(items)),tuple(fixed_y or ()))
                    if vkey not in verified:
                        assert evaluate(model,items,fixed_y=fixed_y)['valid'],(identity,'invalid witness')
                        verified.add(vkey)
                    witness_verified=True
            process=read_json(sub/'PROCESS.json') if (sub/'PROCESS.json').exists() else {}
            counters=result.get('counters',{});budget=job['budget_seconds'] if job else protocol['query_seconds']
            elapsed=result.get('method_elapsed_seconds')
            if elapsed is not None and elapsed<0:raise AssertionError('Negative runtime')
            rows.append({'suite':folder.name,'suite_path':str(folder),'job_hash':entry['job_hash'],
                'instance_id':identity,**cluster_metadata(raw,identity),'data_kind':raw.get('data_kind','UNAVAILABLE'),
                'family':raw.get('family',result.get('family','UNAVAILABLE')),'workflow':workflow,'method':method,
                'solver_seed':seed,'seed_semantics':result.get('seed_semantics','active_CP_SAT_random_seed' if method=='cp_sat' else 'deterministic_repeat_label'),
                'status':status,'reason':result.get('reason',result.get('error','')),
                'executed':status!='NOT_RUN','budget_seconds':budget,'elapsed_seconds':elapsed,
                'within_budget':elapsed is not None and elapsed<=budget,
                'outer_elapsed_seconds':process.get('outer_elapsed_seconds'),
                'startup_seconds':process.get('startup_seconds'),'durable_archive_seconds':process.get('durable_archive_seconds'),
                'storage_scope':result.get('storage_scope','See frozen harness protocol'),
                'method_clock_closed':result.get('method_clock_closed',result.get('reason') not in ('TIMEOUT_PROCESS','MEMORY_LIMIT','worker_died') and result.get('status')!='INFRASTRUCTURE_FAILURE'),
                'peak_rss_bytes':max(result.get('peak_self_rss_bytes',0),process.get('peak_process_tree_rss_bytes',0)) or None,
                'cpu_seconds':result.get('self_user_cpu_seconds',0)+result.get('self_system_cpu_seconds',0) if status!='NOT_RUN' else None,
                'actual_N':raw.get('actual_N',len(raw.get('slots',{}))),'actual_M':raw.get('actual_M',len(raw.get('configurations',[]))),
                'Q':raw.get('Q',len(raw.get('weights',[]))),'unique_response_levels':raw.get('unique_response_levels'),
                'target':raw.get('target'),'fixed_y':raw.get('fixed_y') if workflow=='fixed_y' else None,
                'model_sha256':contract_hash,'witness_size':len(result.get('items',[])) if status=='YES' else None,
                'mandatory_global_cap_violation':mandatory_cap_violation,
                'max_nonhistory_items_per_configuration':max_optional_support,
                'residual_pair_conflicts_impossible':max_optional_support<=1 if max_optional_support is not None else None,
                'frontier_cartesian_upper':str(cartesian) if cartesian is not None else None,
                'witness_verified':witness_verified,'unsat_proof_checked':result.get('proof_checked',False) if status=='NO' else None,
                'frontiers_visited':counters.get('fixed_frontiers_started',counters.get('targets_tested')),
                'branches_completed':counters.get('branches_completed',counters.get('branches_tested',counters.get('branches'))),
                'support_deletions':counters.get('support_deletions'),
                'max_cover_encountered':counters.get('max_cover_encountered',counters.get('max_cover',counters.get('cover_size'))),
                'reference_counters_available':bool(counters) if method=='reference' else None,
                'cover_scope':'maximum encountered before return/timeout; not global' if method=='reference' else '',
                'cpu_affinity':result.get('cpu_affinity')})
    for row in rows:
        key=(row['suite_path'],row['instance_id'],row['workflow'])
        row['resolved_consensus']=answers.get(key,'UNRESOLVED')
        row['consistent_with_resolved_consensus']=row['status'] not in KNOWN or row['status']==row['resolved_consensus']
    return rows,{'unique_independently_verified_witnesses':len(verified),'resolved_exact_units':len(answers)}


def quantile(values,p):
    if not values:return None
    v=sorted(values);where=(len(v)-1)*p;lo=int(where);hi=min(lo+1,len(v)-1)
    return v[lo]*(hi-where)+v[hi]*(where-lo) if lo!=hi else v[lo]


def clustered_log_ratio(rows, a, b):
    cells=defaultdict(dict)
    for r in rows:cells[(r['suite'],r['instance_id'],r['workflow'])][r['method']]=r
    clusters=defaultdict(list);pairs=0
    for cell in cells.values():
        if a not in cell or b not in cell:continue
        ra,rb=cell[a],cell[b]
        if ra['status'] not in DECIDED or rb['status'] not in DECIDED:continue
        ta,tb=number(ra['elapsed_seconds']),number(rb['elapsed_seconds'])
        if ta is None or tb is None or ta<=0 or tb<=0:continue
        if ta>number(ra['budget_seconds']) or tb>number(rb['budget_seconds']):continue
        clusters[(ra['suite'],ra.get('resampling_cluster_id',ra['history_cluster_id']))].append(math.log(ta/tb));pairs+=1
    means=[statistics.mean(v) for v in clusters.values()]
    if not means:return {'numerator':a,'denominator':b,'common_solved_pairs':0,'history_clusters':0}
    rng=random.Random(92627810)
    native=any('NATIVE' in r['data_kind'] for r in rows)
    draws=[] if native else [math.exp(statistics.mean(rng.choices(means,k=len(means)))) for _ in range(1000)]
    return {'numerator':a,'denominator':b,'common_solved_pairs':pairs,'history_clusters':len(means),
            'history_balanced_geometric_ratio':math.exp(statistics.mean(means)),
            'descriptive_cluster_bootstrap_95pct':[quantile(draws,.025),quantile(draws,.975)] if draws else None,
            'bootstrap_unit':'native family/catalogue; no interval because independently sampled catalogue population is not established' if native else 'generated history; paired fixed/unknown tasks remain together',
            'ratio_weighting':'equal weight to registered catalogue or conservative mechanism-family clusters' if native else 'equal weight to generated histories',
            'interpretation':'>1 means denominator method faster on common solved histories; excludes unresolved'}


def compute_existence_metrics(rows):
    primary=[r for r in rows if integer(r['solver_seed'])==0]
    groups=defaultdict(list)
    for r in primary:
        diagnostic='diagnostic:mandatory_global_cap_violation' if truth(r.get('mandatory_global_cap_violation')) else 'diagnostic:mandatory_cap_safe_or_unknown'
        for scope in ('all_families',r['family'],diagnostic):
            groups[(r['data_kind'],r['workflow'],scope,r['method'])].append(r)
    grouped=[]
    for key,rs in sorted(groups.items()):
        counts=Counter(r['status'] for r in rs);executed=[r for r in rs if r['status']!='NOT_RUN']
        eligible=[r for r in executed if r['status']!='INVALID_INITIAL']
        par=[]
        for r in eligible:
            elapsed=number(r['elapsed_seconds']);budget=number(r['budget_seconds'])
            if budget is None:continue
            # Solver decisions arriving beyond the common wall cap are retained,
            # but do not count as solved within cap or receive uncensored PAR2.
            par.append(elapsed if r['status'] in DECIDED and elapsed is not None and elapsed<=budget else 2*budget)
        within=[r for r in eligible if r['status'] in DECIDED and number(r['elapsed_seconds'],math.inf)<=number(r['budget_seconds'])]
        solved=[number(r['elapsed_seconds']) for r in eligible if r['status'] in DECIDED and number(r['elapsed_seconds']) is not None]
        grouped.append({'data_kind':key[0],'workflow':key[1],'family':key[2],'method':key[3],
            'registered_primary_attempts':len(rs),'executed_primary_attempts':len(executed),'eligible_executed':len(eligible),
            'status_counts':dict(sorted(counts.items())),'resolved_within_wall_cap':len(within),'par2_mean_seconds':statistics.mean(par) if par else None,
            'par2_denominator':len(par),'median_resolved_seconds':statistics.median(solved) if solved else None,
            'max_rss_bytes':max((number(r['peak_rss_bytes'],0) for r in rs),default=0),
            'durable_archive_seconds_sum':sum(number(r.get('durable_archive_seconds'),0) for r in rs),
            'startup_seconds_sum':sum(number(r.get('startup_seconds'),0) for r in rs),
            'time_caps_seconds':sorted({number(r['budget_seconds']) for r in rs}),
            'not_run_excluded_from_PAR2':counts['NOT_RUN'],'invalid_initial_excluded_from_PAR2':counts['INVALID_INITIAL']})
    ratios=[]
    for data_kind in sorted({r['data_kind'] for r in primary}):
        for workflow in ('fixed_y','unknown_y','both_tasks_history_clustered'):
            subset=[r for r in primary if r['data_kind']==data_kind and (workflow=='both_tasks_history_clustered' or r['workflow']==workflow)]
            for a,b in (('reference','sat'),('reference','cp_sat'),('cp_sat','sat')):
                ratios.append({'data_kind':data_kind,'workflow':workflow,**clustered_log_ratio(subset,a,b)})
    profile=[]
    for data_kind in sorted({r['data_kind'] for r in primary}):
        for workflow in ('fixed_y','unknown_y'):
            cells=defaultdict(dict)
            for r in primary:
                if r['data_kind']==data_kind and r['workflow']==workflow:cells[(r['suite'],r['instance_id'])][r['method']]=r
            ratios_by_method=defaultdict(list);eligible=0;excluded=0
            for cell in cells.values():
                if not {'reference','cp_sat','sat'}<=cell.keys() or any(r['status'] in ('NOT_RUN','INVALID_INITIAL') for r in cell.values()):
                    excluded+=1;continue
                eligible+=1
                solved={m:number(r['elapsed_seconds']) for m,r in cell.items() if r['status'] in DECIDED and number(r['elapsed_seconds'],math.inf)<=number(r['budget_seconds'])}
                best=min(solved.values(),default=None)
                for method in ('reference','cp_sat','sat'):
                    ratios_by_method[method].append(solved[method]/max(best,1e-12) if method in solved else math.inf)
            for factor in (1,1.1,1.25,1.5,2,4,10,100,1000,10000):
                for method in ('reference','cp_sat','sat'):
                    profile.append({'data_kind':data_kind,'workflow':workflow,'method':method,'factor':factor,
                        'within_factor':sum(v<=factor for v in ratios_by_method[method]),'paired_executed_valid_units':eligible,
                        'excluded_missing_not_run_or_invalid_units':excluded,
                        'fraction':sum(v<=factor for v in ratios_by_method[method])/eligible if eligible else None})
    stability=[]
    cells=defaultdict(list)
    for r in rows:cells[(r['suite'],r['instance_id'],r['method'])].append(r)
    for key,rs in sorted(cells.items()):
        if len(rs)<2:continue
        resolved={r['status'] for r in rs if r['status'] in KNOWN}
        if len(resolved)>1:raise AssertionError(('Solver repeat disagreement',key,resolved))
        stability.append({'suite':key[0],'instance_id':key[1],'method':key[2],'attempts':len(rs),
            'seeds':[integer(r['solver_seed']) for r in rs],'statuses':[r['status'] for r in rs],
            'elapsed_seconds':[number(r['elapsed_seconds']) for r in rs],'seed_semantics':rs[0]['seed_semantics']})
    return {'primary_seed':0,'registered_primary_attempts':len(primary),'registered_all_repeat_attempts':len(rows),
            'groups':grouped,'common_solved_ratios':ratios,'repeat_stability':stability,'performance_profile':profile,
            'PAR2_policy':'resolved by declared wall cap: measured time; other executed valid-history outcomes: twice cap; NOT_RUN/INVALID_INITIAL excluded with counts',
            'native_or_synthetic_identity':'never pool synthetic performance with native execution/coverage',
            'reference_scope':'readable supplied Python reference; no post-freeze optimizations. Generic presolve may reject global-cap-violating H union D before reference frontier enumeration; untimed diagnostic strata separate this trivial case.'}


def query_rows(folders,receipts):
    from .co_exact import evaluate
    records=[];histories=[];interfaces=[];models={};witnesses=set();consensus={};specs={};contracts={}
    for folder in folders:
        for folder,entry,job,result,sub,protocol in checked_suite(folder,receipts):
            if job and job['workflow']!='repeat_queries':continue
            identity=entry['instance_id'];method=entry['method'];raw=job['instance'] if job else {}
            stream=job['query_stream'] if job else None;query_path=sub/'RESULT.queries.jsonl'
            interface_path=sub/'RESULT.interface.json';model=model_lookup(job,models) if job else None
            model_hash=model.digest if model is not None else None
            if job:
                shared=(model_hash,job['budget_seconds'],job.get('per_query_seconds'),job.get('compile_budget_seconds'))
                previous=contracts.setdefault((str(folder),identity),shared)
                assert previous==shared,('Different model or budgets across query methods',identity,previous,shared)
            if stream:
                key=(str(folder),identity);encoded=json.dumps(stream,sort_keys=True)
                previous=specs.setdefault(key,encoded)
                assert previous==encoded,('Different query streams',key)
                targets={q['query_index']:q for q in stream['queries']}
                assert len({tuple(q['target']) for q in stream['queries']})==len(targets),'Duplicate primary targets'
            else:targets={}
            interface=read_json(interface_path) if interface_path.exists() else None
            if interface:
                for k in interface.get('kernels',[]):
                    assert evaluate(model,k)['valid'],('Invalid compiled kernel',identity,method,k)
                order=sorted(model.items);positions={i:j for j,i in enumerate(order)}
                packed={k:v for k,v in interface.items() if k not in ('kernels','proven_maximal')}
                packed.update({'suite':folder.name,'instance_id':identity,'method':method,'model_sha256':model_hash,
                    'encoding':'hex bitsets over item_order; exact sets, no lossy truncation','item_order':order,
                    'kernel_masks':[hex(sum(1<<positions[i] for i in k)) for k in interface.get('kernels',[])],
                    'proven_maximal_masks':[hex(sum(1<<positions[i] for i in k)) for k in interface.get('proven_maximal',[])],
                    'source_interface_sha256':digest(interface_path)})
                interfaces.append(packed)
            seen=[];last_time=-1;counts=Counter();cache_counts=Counter();dispatch_seconds=0.
            if query_path.exists():
                with query_path.open() as f:
                    for line in f:
                        if not line.strip():continue
                        r=json.loads(line);qi=r['query_index'];status=r['status'];target=tuple(r['target'])
                        assert qi==len(seen)+1,('Noncontiguous query receipt',identity,method,qi)
                        assert list(target)==sorted(targets[qi]['target']),('Target mismatch',identity,qi)
                        assert r['cumulative_seconds']>=last_time,('Nonmonotone cost',identity,method)
                        last_time=r['cumulative_seconds']
                        key=(str(folder),identity,qi)
                        if status in KNOWN:
                            previous=consensus.setdefault(key,status)
                            assert previous==status,('Query answer mismatch',key,previous,status,method)
                        if method.endswith('_interface') and status=='NO':
                            assert interface and interface.get('complete'),('Partial interface answered NO',identity,method,qi)
                        verified=False
                        if status=='YES':
                            items=frozenset(r['items']);vkey=(model_hash,tuple(sorted(items)))
                            assert set(target)<=items,('Missing query target',identity,method,qi)
                            if vkey not in witnesses:
                                assert evaluate(model,items)['valid'],('Invalid query witness',identity,method,qi)
                                witnesses.add(vkey)
                            verified=True
                        counts[status]+=1;cache_counts[r.get('cache') or 'none']+=1
                        dispatch_seconds+=r['query_elapsed_seconds']
                        compact={'suite':folder.name,'suite_path':str(folder),'instance_id':identity,**cluster_metadata(raw,identity),
                            'family':raw.get('family','UNAVAILABLE'),'data_kind':raw.get('data_kind','UNAVAILABLE'),
                            'method':method,'query_index':qi,'query_kind':r['query_kind'],'target':list(target),'status':status,
                            'query_elapsed_seconds':r['query_elapsed_seconds'],'cumulative_seconds':r['cumulative_seconds'],
                            'cache':r.get('cache') or 'none','witness_size':len(r.get('items',[])) if status=='YES' else None,
                            'maximality_proved':r.get('maximality_proved'),'maximization_status':r.get('maximization_status'),
                            'maximization_solver_calls':r.get('maximization_solver_calls'),'initial_decision_seconds':r.get('initial_decision_seconds'),
                            'witness_verified':verified,'interface_complete':interface.get('complete') if interface else None,
                            'budget_seconds':job['budget_seconds']}
                        seen.append(compact);records.append(compact)
            if result['status']=='COMPLETE':
                assert stream and len(seen)==len(stream['queries']),('Completed workflow lacks queries',identity,method)
            if result.get('queries_answered') is not None:
                assert len(seen)==result['queries_answered'],('Query count mismatch',identity,method)
            histories.append({'suite':folder.name,'suite_path':str(folder),'instance_id':identity,**cluster_metadata(raw,identity),'family':raw.get('family','native'),
                'data_kind':raw.get('data_kind','UNAVAILABLE'),'method':method,'status':result['status'],
                'budget_seconds':job['budget_seconds'] if job else protocol['history_workflow_seconds'],
                'registered_queries':len(targets) if stream else None,'processed_queries':len(seen),'resolved_queries':counts['YES']+counts['NO'],
                'query_status_counts':dict(counts),'cache_counts':dict(cache_counts),'elapsed_seconds':result.get('method_elapsed_seconds'),
                'preparation_seconds':result.get('preparation_seconds'),'interface_complete':interface.get('complete') if interface else None,
                'interface_artifact_status':'SERIALIZED_ARTIFACT_PRESENT' if interface else 'NO_RETURNED_SERIALIZED_ARTIFACT' if method.endswith('_interface') else 'NOT_AN_INTERFACE_METHOD',
                'preparation_scope':'after model parsing: build/compile, exact verification, in-memory serialization and reload; unavailable if outer deadline preempts preparation return. Parsing is included in total/prefix clocks but was not separately emitted for query workflows.',
                'interface_compile_call_seconds':interface.get('elapsed_seconds') if interface else None,
                'interface_build_seconds':interface.get('build_seconds') if interface else None,
                'post_compile_preparation_seconds':result['preparation_seconds']-interface['elapsed_seconds'] if interface and result.get('preparation_seconds') is not None and interface.get('elapsed_seconds') is not None else None,
                'query_dispatch_seconds_sum':dispatch_seconds,
                'query_dispatch_scope':'sum for returned query records only: cache lookup/solver/verifier call times. Excludes query-record JSON, initial model parsing and any unrecorded interrupted query work; all remain in total/prefix clocks.',
                'startup_seconds':read_json(sub/'PROCESS.json').get('startup_seconds') if (sub/'PROCESS.json').exists() else None,
                'durable_archive_seconds':read_json(sub/'PROCESS.json').get('durable_archive_seconds') if (sub/'PROCESS.json').exists() else None,
                'storage_scope':result.get('storage_scope','See frozen harness protocol'),
                'recorded_prefix_times':result.get('prefix_times',[]),
                'kernel_count':len(interface.get('kernels',[])) if interface else None,
                'peak_rss_bytes':result.get('peak_self_rss_bytes'),'prefixes':stream['prefixes'] if stream else [],
                'source_job_hash':entry['job_hash']})
    for r in records:r['resolved_consensus']=consensus.get((r['suite_path'],r['instance_id'],r['query_index']),'UNRESOLVED')
    return records,histories,interfaces,{'unique_independently_verified_query_witnesses':len(witnesses),'query_units_with_resolved_consensus':len(consensus)}


def compute_prefixes(records,histories):
    cells=defaultdict(list)
    for r in records:cells[(r['suite'],r['instance_id'],r['method'])].append(r)
    prefixes=[]
    for h in histories:
        key=(h['suite'],h['instance_id'],h['method']);rs=cells.get(key,[])
        planned=integer(h['registered_queries']);levels=h['prefixes']
        if isinstance(levels,str):levels=json.loads(levels)
        recorded=h.get('recorded_prefix_times',[])
        if isinstance(recorded,str):recorded=json.loads(recorded or '[]')
        cost_after_recording={integer(r['prefix']):number(r['seconds']) for r in recorded}
        if not levels and not planned:continue
        for length in levels:
            available=rs[:length];counts=Counter(r['status'] for r in available)
            # If execution never reached a prefix, retain actual whole-workflow
            # cost and the remaining NOT_PROCESSED denominator. Do not invent
            # a completion time equal to the time limit.
            reached=len(available)==length
            spent=number(available[-1]['cumulative_seconds']) if reached else number(h['elapsed_seconds'])
            if reached and length in cost_after_recording:
                recorded_cost=cost_after_recording[length]
                if recorded_cost<spent:raise AssertionError('Prefix receipt predates its query record')
                spent=recorded_cost
            prefixes.append({'suite':h['suite'],'instance_id':h['instance_id'],'family':h['family'],'data_kind':h['data_kind'],
                'method':h['method'],'prefix':length,'registered_queries':planned,'prefix_reached':reached,
                'elapsed_spent_seconds':spent,'preparation_seconds':number(h['preparation_seconds']),
                'resolved_correct':counts['YES']+counts['NO'],'yes':counts['YES'],'no':counts['NO'],
                'invalid_initial':counts['INVALID_INITIAL'],'unresolved_processed':sum(v for s,v in counts.items() if s not in KNOWN),
                'not_processed':length-len(available),'all_targets_resolved':counts['YES']+counts['NO']==length,
                'within_history_budget':spent is not None and spent<=number(h.get('budget_seconds'),math.inf),
                'interface_complete':h['interface_complete'],'whole_workflow_status':h['status']})
    return prefixes


def compute_query_metrics(records,histories,prefixes):
    statuses=Counter(r['status'] for r in records);kinds=defaultdict(Counter)
    for r in records:kinds[(r.get('data_kind','UNAVAILABLE'),r['method'],r['query_kind'])][r['status']]+=1
    cells=defaultdict(dict)
    for r in prefixes:cells[(r['suite'],r['instance_id'],integer(r['prefix']))][r['method']]=r
    breaks=[];comparisons=[]
    pairs=(('reference_interface','reference_fresh'),('reference_interface','reference_cached'),
           ('reference_interface','sat_incremental'),('sat_interface','sat_incremental'),
           ('sat_interface','reference_cached'))
    if any(h['method']=='sat_maximal_cache' for h in histories):
        pairs+=(('reference_interface','sat_maximal_cache'),('sat_interface','sat_maximal_cache'),
                ('sat_maximal_cache','sat_incremental'),('sat_maximal_cache','reference_cached'))
    history_keys=sorted({(h['suite'],h['instance_id']) for h in histories})
    metadata={(h['suite'],h['instance_id']):(h.get('data_kind','UNAVAILABLE'),h.get('family','UNAVAILABLE')) for h in histories}
    for suite,identity in history_keys:
        available=sorted((length,data) for (s,i,length),data in cells.items() if (s,i)==(suite,identity))
        for compiled,online in pairs:
            both=[];crossings=[]
            for length,data in available:
                if compiled not in data or online not in data:continue
                a,b=data[compiled],data[online]
                ta,tb=number(a['elapsed_spent_seconds']),number(b['elapsed_spent_seconds'])
                eligible=truth(a['all_targets_resolved']) and truth(b['all_targets_resolved']) and truth(a.get('within_history_budget',True)) and truth(b.get('within_history_budget',True)) and ta is not None and tb is not None
                comparisons.append({'suite':suite,'instance_id':identity,'data_kind':metadata[(suite,identity)][0],
                    'family':metadata[(suite,identity)][1],'method_a':compiled,'method_b':online,'prefix':length,
                    'strict_matched_resolved_prefix':eligible,'a_elapsed_seconds':ta,'b_elapsed_seconds':tb,
                    'a_resolved_correct':integer(a['resolved_correct']),'b_resolved_correct':integer(b['resolved_correct']),
                    'a_over_b_cost_ratio':ta/tb if eligible and tb>0 else None,
                    'a_cost_advantage_seconds':tb-ta if eligible else None})
                if not eligible:continue
                both.append(length)
                if ta<=tb:crossings.append(length)
            breaks.append({'suite':suite,'instance_id':identity,'data_kind':metadata[(suite,identity)][0],
                'family':metadata[(suite,identity)][1],'compiled_method':compiled,'online_method':online,
                'observed_break_even_prefix':min(crossings) if crossings else None,
                'status':'observed_at_registered_prefix' if crossings else 'none_within_tested_common_resolved_prefixes',
                'common_fully_resolved_prefixes':both,'does_not_extrapolate_between_prefixes':True})
    distributions=[];bg=defaultdict(list)
    for row in breaks:bg[(row['data_kind'],row['compiled_method'],row['online_method'])].append(row)
    for key,rs in sorted(bg.items()):
        crossings=[r['observed_break_even_prefix'] for r in rs if r['observed_break_even_prefix'] is not None]
        distributions.append({'data_kind':key[0],'method_a':key[1],'method_b':key[2],
            'registered_paired_histories':len(rs),'histories_with_strict_comparable_prefix':sum(bool(r['common_fully_resolved_prefixes']) for r in rs),
            'histories_with_observed_crossing':len(crossings),'no_observed_crossing':len(rs)-len(crossings),
            'crossing_prefix_counts':dict(sorted(Counter(str(n) for n in crossings).items())),
            'median_observed_crossing_prefix':statistics.median(crossings) if crossings else None,
            'scope':'First observed registered prefix; no interpolation, asymptotic threshold, or permanence claim.'})
    summaries=[];hg=defaultdict(list);rg=defaultdict(list)
    per_history_resolved=Counter((r['suite'],r['instance_id'],r['method']) for r in records if r['status'] in DECIDED)
    for h in histories:hg[(h.get('data_kind','UNAVAILABLE'),h['method'])].append(h)
    for r in records:rg[(r.get('data_kind','UNAVAILABLE'),r['method'])].append(r)
    for key,hs in sorted(hg.items()):
        rows=rg[key];sc=Counter(r['status'] for r in rows)
        sizes=[integer(r['witness_size']) for r in rows if r['status']=='YES' and r.get('witness_size') not in ('',None)]
        summaries.append({'data_kind':key[0],'method':key[1],'registered_histories':len(hs),
            'executed_histories':sum(h.get('status')!='NOT_RUN' for h in hs),'registered_queries_known':sum(integer(h['registered_queries']) for h in hs),
            'histories_with_unknown_registered_count':sum(h['registered_queries'] in ('',None) for h in hs),
            'processed_queries':len(rows),'resolved_queries':sc['YES']+sc['NO'],'query_status_counts':dict(sorted(sc.items())),
            'workflow_status_counts':dict(sorted(Counter(h['status'] for h in hs).items())),
            'complete_workflows_with_all_queries_resolved':sum(h['status']=='COMPLETE' and h['registered_queries'] not in ('',None) and per_history_resolved[(h['suite'],h['instance_id'],h['method'])]==integer(h['registered_queries']) for h in hs),
            'complete_workflows_with_unresolved_queries':sum(h['status']=='COMPLETE' and h['registered_queries'] not in ('',None) and per_history_resolved[(h['suite'],h['instance_id'],h['method'])]<integer(h['registered_queries']) for h in hs),
            'maximization_status_counts':dict(sorted(Counter(r.get('maximization_status') or 'not_invoked_or_cached' for r in rows).items())),
            'cache_counts':dict(sorted(Counter(r.get('cache') or 'none' for r in rows).items())),
            'median_returned_witness_size':statistics.median(sizes) if sizes else None,'witness_size_observations':len(sizes),
            'actual_work_seconds_sum':sum(number(h.get('elapsed_seconds'),0) for h in hs),
            'reported_preparation_seconds_sum':sum(number(h.get('preparation_seconds'),0) for h in hs),
            'histories_with_unavailable_preparation_time':sum(h.get('preparation_seconds') in ('',None) for h in hs),
            'reported_interface_compile_call_seconds_sum':sum(number(h.get('interface_compile_call_seconds'),0) for h in hs),
            'histories_with_returned_compile_timing':sum(h.get('interface_compile_call_seconds') not in ('',None) for h in hs),
            'query_dispatch_seconds_sum':sum(number(h.get('query_dispatch_seconds_sum'),0) for h in hs),
            'durable_archive_seconds_sum':sum(number(h.get('durable_archive_seconds'),0) for h in hs),
            'startup_seconds_sum':sum(number(h.get('startup_seconds'),0) for h in hs)})
    return {'history_count':len(history_keys),'workflow_attempts':len(histories),'processed_query_rows':len(records),
        'query_status_counts':dict(sorted(statuses.items())),
        'by_table_kind_and_method':summaries,
        'query_kind_counts':[{'data_kind':d,'method':m,'query_kind':k,'statuses':dict(v)} for (d,m,k),v in sorted(kinds.items())],
        'break_even':breaks,
        'break_even_distributions':distributions,'matched_prefix_comparisons':comparisons,
        'observed_marginal_costs':marginal_cost_rows(prefixes),
        'correctness_basis':'exact solver consensus on overlapping decided queries plus independent checks of every distinct YES witness; NO proof logs are not independently proof checked',
        'workflow_completion_semantics':'COMPLETE means the scheduled query stream was processed; a partial interface may finish with UNKNOWN. Resolved YES/NO counts and strict matched prefixes determine useful completion, not workflow status.',
            'prefix_cost_policy':'includes model/compile preparation, verification and in-memory interface/query serialization; post-recording prefix receipts override per-row pre-recording snapshots. Incomplete execution reports actual spent work plus NOT_PROCESSED, never a fictitious completion time. Durable archival and common library startup are separate.',
        'denominator_warning':'query rows are correlated within histories; seeds and paired fixed/unknown modes are not independent worlds'}


def marginal_cost_rows(prefixes):
    cells=defaultdict(list)
    for row in prefixes:cells[(row['suite'],row['instance_id'],row['method'])].append(row)
    rows=[]
    for key,values in sorted(cells.items()):
        values.sort(key=lambda r:integer(r['prefix']))
        for a,b in zip(values,values[1:]):
            ta,tb=number(a['elapsed_spent_seconds']),number(b['elapsed_spent_seconds'])
            eligible=all(truth(r['all_targets_resolved']) and truth(r.get('within_history_budget',True)) for r in (a,b)) and ta is not None and tb is not None
            delta=integer(b['prefix'])-integer(a['prefix'])
            rows.append({'suite':key[0],'instance_id':key[1],'method':key[2],'data_kind':b.get('data_kind','UNAVAILABLE'),
                'family':b.get('family','UNAVAILABLE'),
                'from_prefix':integer(a['prefix']),'to_prefix':integer(b['prefix']),'additional_queries':delta,
                'fully_resolved_within_budget_at_both_endpoints':eligible,
                'incremental_work_seconds':tb-ta if eligible else None,
                'observed_seconds_per_additional_resolved_query':(tb-ta)/delta if eligible else None,
                'scope':'Measured timestamp difference includes query dispatch, verification and record serialization; excludes preparation already paid before the first endpoint. No extrapolation.'})
    return rows


def plot_data(output,decisions,prefixes,histories):
    figures=output/'figures';figures.mkdir()
    primary=[r for r in decisions if integer(r['solver_seed'])==0 and r['data_kind']=='SYNTHETIC_EXACT']
    for mode in ('pooled','fixed_y','unknown_y'):
        for method in ('reference','cp_sat','sat'):
            rs=[r for r in primary if r['method']==method and r['status'] not in ('NOT_RUN','INVALID_INITIAL') and (mode=='pooled' or r['workflow']==mode)]
            solved=sorted(number(r['elapsed_seconds']) for r in rs if r['status'] in DECIDED and number(r['elapsed_seconds'],math.inf)<=number(r['budget_seconds']))
            data=[{'seconds':max(1e-5,t),'fraction':100*(j+1)/len(rs)} for j,t in enumerate(solved)] if rs else []
            if rs:
                data.insert(0,{'seconds':max(1e-5,min(solved,default=60)*.9),'fraction':0})
                data.append({'seconds':max(number(r['budget_seconds']) for r in rs),'fraction':100*len(solved)/len(rs)})
            dump_csv(figures/f'decisions_{mode}_{method}.csv',data,['seconds','fraction'])
            if mode=='pooled':dump_csv(figures/f'decisions_{method}.csv',data,['seconds','fraction'])
    # Matched history sums display computation actually spent versus correct
    # answers; an incomplete cheap interface cannot look good merely by timing
    # fast UNKNOWN lookups. Prefix labels are common requests, truncated only
    # when a history's unique target universe is exhausted.
    hc=defaultdict(set)
    for h in histories:
        if h['data_kind']=='SYNTHETIC_EXACT' and h['status']!='NOT_RUN' and number(h['elapsed_seconds']) is not None:
            hc[(h['suite'],h['instance_id'])].add(h['method'])
    methods=('reference_fresh','reference_cached','reference_interface','sat_incremental','sat_interface')
    if any(h['method']=='sat_maximal_cache' for h in histories):methods+=('sat_maximal_cache',)
    common={key for key,v in hc.items() if set(methods)<=v}
    pc=defaultdict(dict)
    for p in prefixes:pc[(p['suite'],p['instance_id'],p['method'])][integer(p['prefix'])]=p
    hd={(h['suite'],h['instance_id'],h['method']):h for h in histories}
    aggregate=[]
    for method in methods:
        points=[]
        for request in (1,10,100,1000,10000):
            time_sum=0;correct=0;requested=0;available_histories=0
            for suite,identity in sorted(common):
                h=hd[(suite,identity,method)];n=integer(h['registered_queries']);length=min(request,n)
                p=pc.get((suite,identity,method),{}).get(length)
                if p is None:continue
                spent=number(p['elapsed_spent_seconds'])
                if spent is None:continue
                available_histories+=1;requested+=length;correct+=integer(p['resolved_correct']);time_sum+=spent
            aggregate.append({'method':method,'requested_prefix_per_history':request,'history_count':available_histories,
                'total_requested':requested,'resolved_correct':correct,'total_elapsed_spent_seconds':time_sum})
            if time_sum>0 and correct>0:points.append({'seconds':time_sum,'correct':correct,'prefix':request})
        dump_csv(figures/f'queries_{method}.csv',points,['seconds','correct','prefix'])
    if 'sat_maximal_cache' not in methods:
        dump_csv(figures/'queries_sat_maximal_cache.csv',[],['seconds','correct','prefix'])
    dump_csv(output/'QUERY_AGGREGATE_PROGRESS.csv',aggregate)
    prefix_audit=prefix_cost_plot_data(output,prefixes,histories)
    return {'decision_panel_denominator':'executed valid-history primary synthetic tasks; separate fixed/unknown panels are primary, pooled panel supplementary',
            'query_panel_denominator':'same executed synthetic histories containing every compared workflow; summed measured serial-equivalent work, not parallel campaign duration; native results remain separate',
            'query_panel_common_histories':len(common),'common_prefix_cost_panels':prefix_audit}


def prefix_cost_plot_data(output,prefixes,histories):
    """Cost at identical requested prefixes, retaining unresolved work honestly."""
    methods=('reference_fresh','reference_cached','reference_interface','sat_incremental','sat_interface','sat_maximal_cache')
    if not any(h['method']=='sat_maximal_cache' for h in histories):methods=methods[:-1]
    cells=defaultdict(dict);hc=defaultdict(set);hd={}
    for h in histories:
        key=(h['suite'],h['instance_id']);hd[key]=h
        if h['status']!='NOT_RUN' and number(h['elapsed_seconds']) is not None:hc[key].add(h['method'])
    for p in prefixes:cells[(p['suite'],p['instance_id'],integer(p['prefix']))][p['method']]=p
    wide=[]
    for (suite,identity,length),values in sorted(cells.items()):
        if not set(methods)<=values.keys():continue
        row={'suite':suite,'instance_id':identity,'data_kind':hd[(suite,identity)]['data_kind'],'prefix':length,
             'all_methods_resolve_prefix_within_budget':all(truth(values[m]['all_targets_resolved']) and truth(values[m].get('within_history_budget',True)) for m in methods)}
        for method in methods:
            v=values[method];row[method+'_spent_seconds']=number(v['elapsed_spent_seconds'])
            row[method+'_resolved']=integer(v['resolved_correct'])
            row[method+'_fully_resolved_within_budget']=truth(v['all_targets_resolved']) and truth(v.get('within_history_budget',True))
        wide.append(row)
    dump_csv(output/'QUERY_HISTORY_COMMON_PREFIX_COSTS.csv',wide)
    aggregates=[];audits=[]
    for kind,slug in (('SYNTHETIC_EXACT','synthetic'),('NEW_NATIVE_MEAN','new_native'),('INHERITED_NATIVE_MEAN','inherited_native')):
        registered={k for k,h in hd.items() if h['data_kind']==kind}
        common={k for k in registered if set(methods)<=hc[k]}
        audits.append({'data_kind':kind,'registered_histories':len(registered),'matched_executed_histories':len(common),
            'all_registered_histories_present':registered==common,'methods':list(methods),
            'x_axis':'actual total unique targets requested over the same matched histories; per-history prefix truncated only at exhaustion',
            'y_axis':'sum of measured work spent including preparation; an open red point retains unresolved queries and is not a cost-to-solve claim'})
        for method in methods:
            points=[]
            for request in (1,10,100,1000,10000):
                if not common:continue
                requested=resolved=0;spent=0.;fully=True;missing=False
                for key in sorted(common):
                    n=integer(hd[key]['registered_queries']);length=min(n,request)
                    p=cells.get((*key,length),{}).get(method)
                    if p is None or number(p['elapsed_spent_seconds']) is None:missing=True;break
                    requested+=length;resolved+=integer(p['resolved_correct']);spent+=number(p['elapsed_spent_seconds'])
                    fully=fully and truth(p['all_targets_resolved']) and truth(p.get('within_history_budget',True))
                if missing:continue
                row={'data_kind':kind,'method':method,'requested_prefix_per_history':request,'matched_histories':len(common),
                     'total_requested':requested,'resolved_correct':resolved,'total_spent_seconds':spent,
                     'all_targets_resolved_within_budget':fully,'cost_semantics':'completed prefix' if fully else 'spent work only; unresolved queries remain'}
                aggregates.append(row)
                if not points or requested!=points[-1]['requested']:
                    points.append({'requested':requested,'seconds':spent,'resolved':int(fully)})
            dump_csv(output/'figures'/f'prefix_{slug}_{method}.csv',points,['requested','seconds','resolved'])
            for label,value in (('resolved',1),('unresolved',0)):
                dump_csv(output/'figures'/f'prefix_{slug}_{method}_{label}.csv',[r for r in points if r['resolved']==value],['requested','seconds','resolved'])
        if 'sat_maximal_cache' not in methods:
            for suffix in ('','_resolved','_unresolved'):dump_csv(output/'figures'/f'prefix_{slug}_sat_maximal_cache{suffix}.csv',[],['requested','seconds','resolved'])
    dump_csv(output/'QUERY_AGGREGATE_PREFIX_COSTS.csv',aggregates)
    return audits


def build_figures(output):
    source=SOURCE_ROOT/'docs/completion-oral-2026-09-26/figures'
    work=Path(os.environ.get('WOWFS_WORK_ROOT','/work/Users/leiyo/wow-forever-sustainability-work'))
    compiler=work/'envs/behavioral-texlive/bin/x86_64-linux/pdflatex'
    statuses=[]
    names=('benchmark_decisions','benchmark_decisions_fixed_y','benchmark_decisions_unknown_y',
           'benchmark_query_progress','benchmark_common_prefix_cost','benchmark_new_native_prefix_cost','benchmark_inherited_native_prefix_cost')
    # Wrappers use the maintained shared standalone sources in the same folder.
    for name in names:shutil.copy2(source/f'{name}.tex',output/'figures'/f'{name}.tex')
    for name in names:
        target=output/'figures'/f'{name}.tex';shutil.copy2(source/f'{name}.tex',target)
        if not compiler.exists():statuses.append({'figure':name,'status':'NOT_RUN','reason':'pdflatex unavailable'});continue
        try:
            proc=subprocess.run([str(compiler),'-interaction=nonstopmode','-halt-on-error',target.name],cwd=target.parent,
                                stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=60)
        except subprocess.TimeoutExpired as exc:
            log=exc.stdout or ''
            if isinstance(log,bytes):log=log.decode(errors='replace')
            (target.parent/f'{name}.build.log').write_text(log+'\nBUILD TIMEOUT (60 seconds); retained as unresolved infrastructure outcome.\n')
            statuses.append({'figure':name,'status':'UNKNOWN_TIMEOUT','reason':'TeX exceeded 60-second infrastructure budget','pdf':None})
            continue
        (target.parent/f'{name}.build.log').write_text(proc.stdout)
        statuses.append({'figure':name,'status':'COMPLETE' if proc.returncode==0 else 'ERROR','returncode':proc.returncode,
                         'pdf':str(target.with_suffix('.pdf')) if target.with_suffix('.pdf').exists() else None})
    return statuses


def markdown_summary(output,em,qm,figures):
    lines=['# Completion benchmark: frozen numerical tables','',
           'Primary counts use solver seed 0; additional trials measure repeat stability. Synthetic and native tables remain separate. Every NO is a solver-issued result unless separately certified; every distinct returned YES witness was independently checked.','',
           '| Table kind / task | Method | Resolved within cap / executed eligible | PAR-2 seconds | Not run | Invalid H |',
           '|---|---|---:|---:|---:|---:|']
    for g in em['groups']:
        if g['family']!='all_families':continue
        par='not_run' if g['par2_mean_seconds'] is None else f"{g['par2_mean_seconds']:.5g}"
        lines.append(f"| {g['data_kind']} / {g['workflow']} | {LABELS.get(g['method'],g['method'])} | {g['resolved_within_wall_cap']} / {g['eligible_executed']} | {par} | {g['not_run_excluded_from_PAR2']} | {g['invalid_initial_excluded_from_PAR2']} |")
    lines+=['','The reference is the supplied readable Python implementation. Generic presolve may immediately reject an already over-cap mandatory H union D while the reference scans frontiers. Untimed exact `mandatory_global_cap_violation` flags and separate diagnostic strata preserve this distinction; broad losses must not be attributed solely to the theoretical frontier count. The frozen solver was not optimized after observing test outcomes. The outer history deadline can preempt return of live reference counters; missing timeout counters remain unavailable, not zero. Reported cover sizes are only maxima encountered in recorded work, never claimed global maxima.','',
            'Timing concerns an in-memory query service with common libraries preloaded. Every problem has fresh problem-specific state. Parsing, building, solving, verifying, interface JSON serialization/reload and query-record JSON are included; common library startup and durable NAS archival are recorded separately. These timings do not establish end-to-end cold deployment or durable-storage throughput.','',
            'Repeated-query evidence measures total preparation plus query cost on identical unique target streams. Partial interfaces can certify positive queries only; UNKNOWN is retained in the processed-query denominator. Workflow COMPLETE means the scheduled stream was processed, and does not imply that every target was resolved.','',
            f"Registered histories: {qm['history_count']}; workflow attempts: {qm['workflow_attempts']}; processed query records: {qm['processed_query_rows']}. These are computational observations, not independent native catalogues.",'',
            '| Method A vs method B | Histories with an observed cost crossing at a common fully resolved prefix |',
            '|---|---:|']
    by=defaultdict(list)
    for row in qm['break_even']:by[(row['data_kind'],row['compiled_method'],row['online_method'])].append(row)
    for pair,rs in sorted(by.items()):
        count=sum(r['observed_break_even_prefix'] is not None for r in rs)
        lines.append(f'| {pair[0]}: {LABELS[pair[1]]} vs {LABELS[pair[2]]} | {count} / {len(rs)} |')
    lines+=['','A crossing is measured only at registered prefixes where both methods resolve every queried target within the common whole-history budget. Exact matched cost ratios and crossing-prefix distributions are retained in QUERY_MATCHED_PREFIX_COMPARISONS.csv and QUERY_BREAK_EVEN_DISTRIBUTIONS.csv. No crossing is inferred for timed-out, partial or unexecuted prefixes, and an observed crossing does not imply that the method remains faster at all later prefixes. Costs are not extrapolated to hypothetical future queries.','',
            'Synthetic common-solved runtime intervals in METRICS.json resample generated histories, keeping paired fixed/unknown tasks together. Native ratios use conservative mechanism-family clusters unless catalogue clusters were explicitly registered, and receive no bootstrap interval: independently sampled catalogue populations are not established. These ratios are descriptive and conditional on both methods solving; solved counts and censored outcomes remain primary.','',
            'Recompute compact metrics with `python -m wowfs.experiments.co_benchmark_report --check <this report directory>`. The check needs only the compact CSVs and the reporting module. The original frozen job/model/protocol hashes are indexed in REPORT_INPUTS.json.','']
    (output/'BENCHMARK_SUMMARY.md').write_text('\n'.join(lines))


def report(existence,queries,output,compile_figures=True,excluded_suites=()):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    (output/'source').mkdir()
    (output/'source/co_benchmark_report.py').write_bytes(SOURCE_BYTES_AT_IMPORT)
    receipts=[];started=time.perf_counter()
    try:
        ds,da=existence_rows(existence,receipts)
        qr,qh,interfaces,qa=query_rows(queries,receipts)
        prefixes=compute_prefixes(qr,qh)
        em=compute_existence_metrics(ds);qm=compute_query_metrics(qr,qh,prefixes)
    except Exception as exc:
        write_json(output/'CORRECTNESS_REPORT_FAILURE.json',{'status':'ERROR','error':repr(exc)})
        raise
    dump_csv(output/'BENCHMARK_RESULTS.csv',ds)
    dump_csv(output/'QUERY_RESULTS.csv.gz',qr,['suite','suite_path','instance_id','history_cluster_id','resampling_cluster_id','resampling_cluster_basis','family','data_kind','method','query_index','query_kind','target','status','query_elapsed_seconds','cumulative_seconds','cache','witness_size','maximality_proved','maximization_status','maximization_solver_calls','initial_decision_seconds','witness_verified','interface_complete','budget_seconds','resolved_consensus'])
    dump_csv(output/'QUERY_HISTORY_RESULTS.csv',qh)
    dump_csv(output/'QUERY_PREFIX_RESULTS.csv',prefixes)
    dump_csv(output/'QUERY_MATCHED_PREFIX_COMPARISONS.csv',qm['matched_prefix_comparisons'])
    dump_csv(output/'QUERY_BREAK_EVEN_DISTRIBUTIONS.csv',qm['break_even_distributions'])
    dump_csv(output/'QUERY_MARGINAL_COSTS.csv',qm['observed_marginal_costs'])
    (output/'COMPILED_INTERFACES.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in interfaces))
    metrics={'existence':em,'queries':qm};write_json(output/'METRICS.json',metrics)
    dump_csv(output/'PERFORMANCE_PROFILE.csv',em['performance_profile'])
    write_json(output/'REPORT_INPUTS.json',{'input_suites':receipts,'report_source_sha256':SOURCE_SHA256_AT_IMPORT,
        'excluded_suites':[{'path':str(Path(p).resolve()),'reason':'declared infrastructure-contaminated; every attempt excluded from primary timing, not a selective algorithm rerun'} for p in excluded_suites],
        'role':'frozen computational test unless a suite explicitly names development; development is not confirmation',
        'solver_versions_file':'campaign-v1/audit/exact-solvers-v2/ENCODING_ENVIRONMENT.json'})
    execution_errors=[{'suite':r['suite'],'instance_id':r['instance_id'],'method':r['method'],'status':r['status']}
                      for r in ds+qh if r['status'] in ('ERROR','INFRASTRUCTURE_FAILURE')]
    write_json(output/'CORRECTNESS_REPORT.json',{'status':'RECORDED_DECISIONS_PASS_WITH_EXECUTION_ERRORS' if execution_errors else 'PASS',
        **da,**qa,'execution_errors':execution_errors,'timing_interpretation_valid':not execution_errors,
        'checks':['cross-method resolved consistency','distinct YES witnesses','target identity and order','unique query stream','same exact question and budgets across existence methods','same model and budgets across query methods','registered canonical job hashes','partial-interface NO prohibition','monotone cumulative cost','recorded query denominators','all frozen source snapshots present and hash verified']})
    plot=plot_data(output,ds,prefixes,qh)
    figures=build_figures(output) if compile_figures else []
    write_json(output/'FIGURE_AUDIT.json',{'data_interpretation':plot,'builds':figures})
    markdown_summary(output,em,qm,figures)
    if execution_errors:
        summary=output/'BENCHMARK_SUMMARY.md'
        summary.write_text('**Unresolved implementation/infrastructure errors remain. Timing tables are execution logs, not a validated comparative performance conclusion.**\n\n'+summary.read_text())
    hashes={str(p.relative_to(output)):digest(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name!='REPORT_HASHES.json'}
    write_json(output/'REPORT_HASHES.json',hashes)
    checked=check(output)
    return {'output':str(output),'status':'PARTIAL_WITH_EXECUTION_ERRORS' if execution_errors else 'PARTIAL_FIGURES' if any(r['status']!='COMPLETE' for r in figures) else 'COMPLETE',
            'seconds':time.perf_counter()-started,'compact_recheck':checked}


def check(output):
    output=Path(output)
    for name,expected in read_json(output/'REPORT_HASHES.json').items():
        assert digest(output/name)==expected,('Report file changed',name)
    decisions=read_csv(output/'BENCHMARK_RESULTS.csv')
    queries=read_csv(output/'QUERY_RESULTS.csv.gz')
    histories=read_csv(output/'QUERY_HISTORY_RESULTS.csv')
    prefixes=read_csv(output/'QUERY_PREFIX_RESULTS.csv')
    expected=read_json(output/'METRICS.json')
    actual={'existence':compute_existence_metrics(decisions),'queries':compute_query_metrics(queries,histories,prefixes)}
    def equal(a,b):
        if isinstance(a,dict) and isinstance(b,dict):return a.keys()==b.keys() and all(equal(a[k],b[k]) for k in a)
        if isinstance(a,list) and isinstance(b,list):return len(a)==len(b) and all(equal(x,y) for x,y in zip(a,b))
        if isinstance(a,float) and isinstance(b,(int,float)):return math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-12)
        return a==b
    if not equal(expected,actual):raise AssertionError('Compact CSV metric recomputation differs')
    # Recompute prefixes from the individual compact query receipts as well.
    recalculated=compute_prefixes(queries,histories)
    actual_by={(r['suite'],r['instance_id'],r['method'],integer(r['prefix'])):r for r in prefixes}
    for r in recalculated:
        previous=actual_by[(r['suite'],r['instance_id'],r['method'],r['prefix'])]
        for k in ('resolved_correct','not_processed','unresolved_processed','yes','no'):
            assert r[k]==integer(previous[k]),('Prefix recomputation mismatch',k,r)
        assert r['elapsed_spent_seconds']==number(previous['elapsed_spent_seconds'])
    # Independently reconstruct common-prefix panel sums from compact history
    # and prefix receipts; these figures must not turn spent work into a solve.
    aggregate_path=output/'QUERY_AGGREGATE_PREFIX_COSTS.csv'
    if aggregate_path.exists():
        methods={'reference_fresh','reference_cached','reference_interface','sat_incremental','sat_interface'}
        if any(h['method']=='sat_maximal_cache' for h in histories):methods.add('sat_maximal_cache')
        available=defaultdict(set);metadata={}
        for h in histories:
            key=(h['suite'],h['instance_id']);metadata[key]=h
            if h['status']!='NOT_RUN' and number(h['elapsed_seconds']) is not None:available[key].add(h['method'])
        for r in read_csv(aggregate_path):
            keys=sorted(k for k,h in metadata.items() if h['data_kind']==r['data_kind'] and methods<=available[k])
            pieces=[actual_by[(*k,r['method'],min(integer(r['requested_prefix_per_history']),integer(metadata[k]['registered_queries'])))] for k in keys]
            assert len(keys)==integer(r['matched_histories'])
            assert sum(integer(p['prefix']) for p in pieces)==integer(r['total_requested'])
            assert sum(integer(p['resolved_correct']) for p in pieces)==integer(r['resolved_correct'])
            assert math.isclose(sum(number(p['elapsed_spent_seconds']) for p in pieces),number(r['total_spent_seconds']),rel_tol=1e-10,abs_tol=1e-12)
            assert all(truth(p['all_targets_resolved']) and truth(p['within_history_budget']) for p in pieces)==truth(r['all_targets_resolved_within_budget'])
    return {'status':'PASS','decision_attempts':len(decisions),'query_records':len(queries),'prefix_records':len(prefixes),
            'raw_job_directories_required':False,'floating_summary_recheck_tolerance':{'relative':1e-10,'absolute':1e-12},
            'report_source_revision_matches':SOURCE_SHA256_AT_IMPORT==read_json(output/'REPORT_INPUTS.json')['report_source_sha256'],
            'counts_statuses_and_memberships_checked_exactly':True}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--existence',type=Path,action='append',default=[],help='Frozen existence suite; repeat for native/synthetic suites')
    p.add_argument('--queries',type=Path,action='append',default=[],help='Frozen query suite; repeat as needed')
    p.add_argument('--output',type=Path,help='New immutable report directory; existing directory rejected')
    p.add_argument('--no-compile-figures',action='store_true')
    p.add_argument('--excluded-suite',type=Path,action='append',default=[],help='Record a whole infrastructure-contaminated suite excluded from primary timing')
    p.add_argument('--check',type=Path,help='Recompute metrics from compact CSVs, without raw benchmark jobs')
    args=p.parse_args()
    if args.check:result=check(args.check)
    else:
        if not args.output or not(args.existence or args.queries):p.error('--output and at least one input suite required')
        result=report(args.existence,args.queries,args.output,not args.no_compile_figures,args.excluded_suite)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
