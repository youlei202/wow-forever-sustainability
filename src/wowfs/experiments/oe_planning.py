"""Read-only planning screen of measured native means; never launches battles.

Thresholds and index thinning are declared in this module. Every selected physical
cross is retained, including cap violations. Outputs describe a finite observed
subdomain and exploratory means, never a confidence or continuous-domain result.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from dataclasses import asdict, replace
from itertools import combinations, product
import json
from pathlib import Path
import time
from typing import Any

import numpy as np

from wowfs.paths import atomic_json, canonical_hash
from wowfs.experiments.oe_analysis import tensor, write_csv
from wowfs.experiments.oe_solver import (Configuration, Problem, _Evaluator, exact_capacity,
    fixed_partner_problem, greedy_capacity, state_metrics, validate_history)
from wowfs.experiments.r2_native import file_hash

GAINS=(.005,.01,.02)
HEADROOMS=(.03,.05,.1)
TOLERANCES=(.01,.03,.05)
FIRST_MATCH_TOLERANCE=.0025


def plain(value):
    if hasattr(value,'__dataclass_fields__'):return plain(asdict(value))
    if isinstance(value,dict):return {str(k):plain(v) for k,v in value.items()}
    if isinstance(value,(list,tuple,set,frozenset)):return [plain(v) for v in value]
    if isinstance(value,np.ndarray):return plain(value.tolist())
    if isinstance(value,np.generic):return value.item()
    if isinstance(value,float) and not np.isfinite(value):return None
    return value


def evenly_spaced(ids,limit):
    """Outcome-independent index thinning; the deleted IDs remain explicit."""
    if len(ids)<=limit:return list(ids)
    if limit<1:return []
    indexes=np.linspace(0,len(ids)-1,limit).round().astype(int)
    return [ids[i] for i in indexes]


def build_domain(world,rows,max_candidates=12):
    t=tensor(rows);dims=t['dimensions'];a=t['means']
    if not t['complete']:raise ValueError('incomplete observed Cartesian tensor: no imputation or utility-based deletion permitted')
    if not world.get('all_physical_crosses_legal',False):raise ValueError('Explicit physical compatibility is required for a non-Cartesian world')
    initial_rows=[f'a{i:02}' for i in world.get('initial_candidate_ids',[0])]
    initial_partners=[f'x{i}' for i in world['initial_partner_ids']]
    if not set(initial_rows)<=set(dims[0]) or not set(initial_partners)<=set(dims[1]):
        raise ValueError('An originally published source is missing from the observations')
    if set(dims[2])!={x['task_id'] for x in world['tasks']}:
        raise ValueError('Missing fixed evaluation task: do not renormalize away unobserved task mass')
    if set(dims[3])!=set(world['policies']):
        raise ValueError('Missing declared policy: complete the chosen policy domain before planning')
    joint=world.get('model_scope')=='joint_two_update_slots'
    new_rows=[x for x in dims[0] if x not in initial_rows]
    new_partners=[x for x in dims[1] if x not in initial_partners] if joint else []
    # Keep all observed candidate partners in the two-slot screen when possible;
    # use the remaining budget for evenly spaced primary indices. This preserves
    # the explicitly measured new-new interaction axis instead of pruning by gain.
    kept_new_partners=evenly_spaced(new_partners,min(len(new_partners),max_candidates))
    kept_new_rows=evenly_spaced(new_rows,max_candidates-len(kept_new_partners))
    kept_rows=[x for x in dims[0] if x in initial_rows or x in kept_new_rows]
    kept_partners=[x for x in dims[1] if not joint or x in initial_partners or x in kept_new_partners]
    ri=[dims[0].index(x) for x in kept_rows];xi=[dims[1].index(x) for x in kept_partners]
    refs=[];refmap=[]
    for q,task in enumerate(dims[2]):
        choices=[(float(a[dims[0].index(r),dims[1].index(x),q,k]),r,x,k)
                 for r in initial_rows for x in initial_partners for k in range(len(dims[3]))]
        value,r,x,k=max(choices,key=lambda z:z[0])
        refs.append(value)
        record=t['records'][(dims[0].index(r),dims[1].index(x),q,k)]
        refmap.append({'task_id':task,'candidate_id':r,'partner_id':x,'policy_id':dims[3][k],
            'observed_tensor_index':[dims[0].index(r),dims[1].index(x),q,k],
            'registry_candidate_index':record['candidate_index'],'registry_partner_index':record['partner_index'],
            'registry_task_index':record['task_index'],'registry_policy_index':record['policy_index'],
            'development_mean':value,'cache_key':record.get('cache_key'),
            'definition':'fixed physical initial configuration selected in development; independently remeasure this identity, do not reselect a confirmation winner'})
    selected=a[np.ix_(ri,xi,range(a.shape[2]),range(a.shape[3]))]
    registry_tasks=[task['task_id'] for task in world['tasks']]
    declared_weights=world.get('task_weights',[1/len(registry_tasks)]*len(registry_tasks))
    if len(declared_weights)!=len(registry_tasks):raise ValueError('Frozen task-weight count differs from registry task count')
    weight_map=dict(zip(registry_tasks,declared_weights))
    weights=tuple(weight_map[task] for task in dims[2])  # do not renormalize
    if joint:
        configs=tuple(Configuration(f'{r}|{x}|policy{k}',frozenset((r,x)),tuple(selected[i,j,:,k]))
            for i,r in enumerate(kept_rows) for j,x in enumerate(kept_partners) for k in range(a.shape[3]))
        p=Problem(tuple(kept_rows+kept_partners),frozenset(initial_rows+initial_partners),configs,
            weights,tuple(refs),.005,1.03,.01,.5,.5,len(kept_new_rows)+len(kept_new_partners))
    else:
        p=fixed_partner_problem(selected,row_ids=kept_rows,partner_ids=kept_partners,
            initial_rows=initial_rows,task_weights=weights,reference=refs,gain=.005,cap=1.03,tolerance=.01,
            gain_mass=.5,retention_mass=.5,total_item_budget=len(kept_new_rows))
    declared_rows=[f'a{i:02}' for i in range(len(world['candidates']))]
    declared_partners=[f'x{i}' for i in range(len(world['partners']))]
    domain={'world_id':world['world_id'],'mechanism_id':world['mechanism_id'],
        'lineage_id':world.get('lineage_id',world['mechanism_id']),'context':world['context'],
        'model_scope':world['model_scope'],'parameter_scope':world.get('parameter_scope'),
        'source_unit':world.get('source_unit'),'world_sha256':world.get('world_sha256'),
        'task_ids':dims[2],'policy_ids':dims[3],'task_weights':weights,'reference_mapping':refmap,
        'declared_row_ids':declared_rows,'declared_partner_ids':declared_partners,
        'observed_row_ids':dims[0],'observed_partner_ids':dims[1],
        'retained_row_ids':kept_rows,'retained_partner_ids':kept_partners,
        'unobserved_row_ids':[x for x in declared_rows if x not in dims[0]],
        'unobserved_partner_ids':[x for x in declared_partners if x not in dims[1]],
        'removed_for_oracle_row_ids':[x for x in dims[0] if x not in kept_rows],
        'removed_for_oracle_partner_ids':[x for x in dims[1] if x not in kept_partners],
        'thinning_rule':'keep original items; joint retains observed new partner axis, then rounded equally spaced primary indices; no outcome-dependent thinning',
        'all_declared_physical_crosses_preserved_in_selected_domain':True,
        'observed_physical_cells':len(rows),'solver_physical_cells':int(selected.size),
        'physical_tensor_dimensions':dims,'physical_tensor_shape':list(a.shape),
        'solver_tensor_dimensions':[kept_rows,kept_partners,dims[2],dims[3]],
        'solver_tensor_shape':list(selected.shape),'mean_tensor':selected.tolist(),
        'observed_or_reconstructed':'observed','statistical_status':'exploratory mean table; not confidence certified',
        'finite_domain_complete':True,'full_declared_world_observed':len(dims[0])==len(declared_rows) and len(dims[1])==len(declared_partners),
        'original_declared_source_aliases':{'rows':[x['research_alias'] for x in world['candidates']],
                                          'partners':[x['research_alias'] for x in world['partners']]},
        'problem_template':plain(p)}
    domain['domain_sha256']=canonical_hash(plain(domain))
    return p,domain


def weighted_greedy(p,weights):
    """Reasonable current-gain weight sweep; feasibility weights stay fixed."""
    start=time.monotonic();e=_Evaluator(p);mask=0;path=[]
    if not e.valid(0):return {'status':'initially_invalid','capacity_lower':None,'capacity_upper':None,'batches':[],'scoring_weights':weights}
    while True:
        options=list(e.successors(mask,1))
        if not options:break
        def key(pair):
            nxt,batch=pair;s=e.metrics(nxt)
            diff=np.array(s.frontier)-np.array(e.metrics(mask).frontier)
            return (float(np.dot(weights,diff)),min(s.source_margins.values()),tuple(batch))
        nxt,batch=max(options,key=key);path.append(batch);mask=nxt
    states=validate_history(p,path,1)
    return {'status':'heuristic','capacity_lower':len(path),'capacity_upper':e.upper(0),
        'batches':path,'frontiers':[s.frontier for s in states[1:]],
        'source_masses':[s.source_masses for s in states[1:]],
        'source_margins':[s.source_margins for s in states[1:]],'scoring_weights':weights,
        'feasibility_weights':p.task_weights,'batch_limit':1,'total_item_budget':p.total_item_budget,
        'elapsed_seconds':time.monotonic()-start}


def scalar_solution(s):
    if not isinstance(s,dict):s=plain(s)
    return {'status':s['status'],'lower':s['capacity_lower'],'upper':s['capacity_upper'],
        'released_items':sum(len(b) for b in s.get('batches',[])),
        'terminal_frontier':s.get('frontiers',[])[-1] if s.get('frontiers') else None}


def matched_first_steps(p,world_id,threshold,timeout,max_candidates):
    e=_Evaluator(p)
    if not e.valid(0):return [],[]
    first=list(e.successors(0,1));comparisons=[];needed=set()
    for (ma,ba),(mb,bb) in combinations(first,2):
        fa=np.array(e.metrics(ma).frontier);fb=np.array(e.metrics(mb).frontier)
        gap=float(np.max(abs(fa-fb)))
        if gap<=FIRST_MATCH_TOLERANCE+1e-12:
            comparisons.append((ma,ba,mb,bb,gap));needed.update((ma,mb))
    continuations={};first_rows=[]
    for mask,batch in first:
        s=e.metrics(mask)
        detail={'world_id':world_id,**threshold,'batch':batch,'frontier':s.frontier,
            'source_masses':s.source_masses,'source_margins':s.source_margins,
            'initial_items_after_first':s.published,'matching_pair_exists':mask in needed,
            'conditional_solver_status':'not_needed_no_frontier_matched_pair'}
        if mask in needed:
            retained=exact_capacity(p,1,initial_items=s.published,timeout_seconds=timeout,max_candidates=max_candidates)
            value=exact_capacity(p,1,initial_items=s.published,retention=False,timeout_seconds=timeout,max_candidates=max_candidates)
            continuations[mask]=(retained,value)
            detail.update(conditional_solver_status=retained.status,retaining_continuation=plain(retained),value_continuation=plain(value))
        first_rows.append(detail)
    pairs=[]
    for ma,ba,mb,bb,gap in comparisons:
        ar,av=continuations[ma];br,bv=continuations[mb]
        separated=(ar.capacity_lower>br.capacity_upper or br.capacity_lower>ar.capacity_upper)
        v_equal=(av.status==bv.status=='finite_exact' and av.capacity==bv.capacity)
        masses_a=e.metrics(ma).source_masses;masses_b=e.metrics(mb).source_masses
        common=set(masses_a)&set(masses_b)
        pairs.append({'world_id':world_id,**threshold,'first_a':ba,'first_b':bb,
            'frontier_a':e.metrics(ma).frontier,'frontier_b':e.metrics(mb).frontier,
            'max_task_frontier_difference':gap,'matching_tolerance':FIRST_MATCH_TOLERANCE,
            'same_first_release_count':True,'same_remaining_headroom_within_tolerance':True,
            'same_common_source_task_masses':all(masses_a[x]==masses_b[x] for x in common),
            'same_candidate_pool_including_unchosen_first_action':True,
            'same_information':True,'same_release_width':1,'same_total_item_budget':p.total_item_budget,
            'a_retaining':scalar_solution(ar),'b_retaining':scalar_solution(br),
            'a_value':scalar_solution(av),'b_value':scalar_solution(bv),
            'retaining_bounds_separate':separated,'conditional_value_capacities_equal':v_equal,
            'retention_specific_separation':separated and v_equal,
            'mean_screen_interpretation':'candidate decision effect' if separated else 'no resolved conditional capacity separation',
            'causal_limit':'approximately matched means only; changing first item also changes persistent source obligations; confirm fixed physical references and full domain independently'})
    return first_rows,pairs


def joint_cap_diagnostics(p,threshold):
    if len(p.initial_items)!=2:return []
    initial=set(p.initial_items);out=[]
    candidates=[x for x in p.items if x not in initial]
    for a,b in combinations(candidates,2):
        if a[0]==b[0]:continue
        sa=state_metrics(p,initial|{a});sb=state_metrics(p,initial|{b});sab=state_metrics(p,initial|{a,b})
        if sa.power_valid and sb.power_valid and not sab.power_valid:
            out.append({**threshold,'item_a':a,'item_b':b,'individual_frontier_a':sa.frontier,
                'individual_frontier_b':sb.frontier,'joint_frontier':sab.frontier,
                'individual_retention_valid_a':sa.retention_valid,'individual_retention_valid_b':sb.retention_valid,
                'status':'mean_joint_cap_violation_after_individual_cap_admission'})
    return out


def analyze_world(world,rows,max_candidates,timeout):
    p0,domain=build_domain(world,rows,max_candidates)
    records=[];firsts=[];pairs=[];joint=[];value_cache={}
    for g,h,e in product(GAINS,HEADROOMS,TOLERANCES):
        p=replace(p0,gain=g,cap=1+h,tolerance=e);threshold={'g':g,'h':h,'e':e}
        initial=state_metrics(p)
        if (g,h) not in value_cache:
            value_cache[g,h]=plain(exact_capacity(p,1,retention=False,timeout_seconds=timeout,max_candidates=max_candidates))
        value_method=dict(value_cache[g,h])
        # Capacity and chosen path are tolerance-independent when retention is
        # disabled; the reported source diagnostics still use the current e.
        value_states=validate_history(p,value_method['batches'],1,retention=False)
        value_method['source_masses']=[st.source_masses for st in value_states[1:]]
        value_method['source_margins']=[st.source_margins for st in value_states[1:]]
        value_method['capacity_path_reused_across_retention_tolerances']=True
        methods={'exact_B1_value':value_method}
        initial_primary_ids={f'a{i:02}' for i in world.get('initial_candidate_ids',[0])}
        first_lost=[];first_loss_round=None
        for vround,vstate in enumerate(value_states[1:],1):
            lost=[source for source,mass in vstate.source_masses.items() if mass<p.retention_mass-1e-12]
            if lost:
                first_lost=lost;first_loss_round=vround;break
        for B in (1,2,4):
            methods[f'exact_B{B}_retaining']=plain(exact_capacity(p,B,timeout_seconds=timeout,max_candidates=max_candidates))
        for policy in ('max_gain','source_aware','lookahead2'):
            methods[policy]=plain(greedy_capacity(p,1,policy=policy))
        q=len(p.reference)
        scoring=[(w,1-w) for w in (0.,.25,.5,.75,1.)] if q==2 else [tuple(1/q for _ in range(q))]+[tuple(float(i==j) for j in range(q)) for i in range(q)]
        for wi,w in enumerate(scoring):methods[f'weighted_current_gain_{wi}']=plain(weighted_greedy(p,w))
        exact=methods['exact_B1_retaining'];value=methods['exact_B1_value']
        entry={'world_id':world['world_id'],'mechanism_id':world['mechanism_id'],
            'lineage_id':world.get('lineage_id',world['mechanism_id']),
            'model_scope':world['model_scope'],'parameter_scope':world.get('parameter_scope'),
            **threshold,'gain_mass':.5,'retention_mass':.5,'task_weights':p.task_weights,
            'initial_valid':initial.valid,'initial_source_masses':initial.source_masses,
            'initial_source_margins':initial.source_margins,'domain_sha256':domain['domain_sha256'],
            'candidate_count':len(p.items)-len(p.initial_items),'total_item_budget':p.total_item_budget,
            'physical_cells':domain['solver_physical_cells'],'methods':methods,
            'retention_penalty_resolved':bool(initial.valid and value['capacity_lower']>exact['capacity_upper']),
            'retention_penalty_lower':value['capacity_lower']-exact['capacity_upper'] if initial.valid else None,
            'value_witness_first_loss_round':first_loss_round,
            'value_witness_first_lost_sources':first_lost,
            'value_witness_first_loss_only_initial_primary':bool(first_lost and set(first_lost)<=initial_primary_ids),
            'value_witness_first_loss_includes_initial_primary':bool(set(first_lost)&initial_primary_ids),
            'fixed_partner_old_primary_uses_are_immutable':world['model_scope']=='fixed_partners_multi_task',
            'cap_headroom_exceeds_old_primary_tolerance':h>e,
            'loss_diagnostic_scope':'describes the returned value-optimal witness, not every possible optimal value path',
            'batch2_improvement_resolved':bool(initial.valid and methods['exact_B2_retaining']['capacity_lower']>exact['capacity_upper']),
            'batch4_improvement_resolved':bool(initial.valid and methods['exact_B4_retaining']['capacity_lower']>exact['capacity_upper']),
            'status':'development_mean_finite_domain' if initial.valid else 'initially_invalid',
            'statistical_status':'not_confirmed; thresholds scanned in development'}
        greedy_max=max((m['capacity_lower'] for k,m in methods.items() if not k.startswith('exact') and m['capacity_lower'] is not None),default=None)
        entry['best_greedy_capacity']=greedy_max
        entry['planning_advantage_over_best_greedy_resolved']=bool(initial.valid and exact['capacity_lower']>greedy_max)
        entry['planning_advantage_may_be_gain_rationing']=entry['planning_advantage_over_best_greedy_resolved']
        records.append(entry)
        f,mp=matched_first_steps(p,world['world_id'],threshold,timeout,max_candidates)
        firsts.extend(f);pairs.extend(mp)
        if world['model_scope']=='joint_two_update_slots':joint.extend(joint_cap_diagnostics(p,threshold))
    return {'world_id':world['world_id'],'status':'completed','domain':domain,'planning':records,
            'first_steps':firsts,'matched_first_pairs':pairs,'joint_cap_violations':joint}


def flat_entry(row):
    out={k:v for k,v in row.items() if k!='methods'}
    for method,sol in row['methods'].items():
        for k,v in scalar_solution(sol).items():out[f'{method}_{k}']=v
    return out


def analyze(batch,registry_path,output,max_candidates=12,timeout=5):
    batch=Path(batch);registry_path=Path(registry_path);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    results=json.loads((batch/'RESULTS.json').read_text())
    registry={w['world_id']:w for w in (json.loads(line) for line in registry_path.read_text().splitlines() if line.strip())}
    manifest={'batch':str(batch),'batch_results_sha256':file_hash(batch/'RESULTS.json'),
        'registry':str(registry_path),'registry_sha256':file_hash(registry_path),
        'analysis_source_sha256':file_hash(Path(__file__)),'solver_source_sha256':file_hash(Path(__file__).with_name('oe_solver.py')),
        'tensor_source_sha256':file_hash(Path(__file__).with_name('oe_analysis.py')),
        'max_candidates':max_candidates,'timeout_per_exact_call':timeout,'gain_grid':GAINS,'headroom_grid':HEADROOMS,
        'retention_grid':TOLERANCES,'gain_mass':.5,'retention_mass':.5,'task_weighting':'frozen registry weights mapped by task ID; equal only if unspecified',
        'first_step_matching_tolerance':FIRST_MATCH_TOLERANCE,'native_calls':0,
        'conditional_compute_rule':'Enumerate every legal singleton first step. Solve continuations for every first step in at least one frontier-matched pair; other continuations explicitly not_needed_no_frontier_matched_pair.',
        'scope':'Exploratory numerical means, complete physical crosses in explicitly reported finite subdomain.'}
    manifest=plain(manifest);mp=output/'ANALYSIS_MANIFEST.json'
    if mp.exists() and json.loads(mp.read_text())!=manifest:raise ValueError('Existing analysis input/source hashes differ: use a new output version')
    atomic_json(mp,manifest)
    groups=defaultdict(list)
    for row in results['rows']:
        if row is not None:groups[row['world_id']].append(row)
    worlds=[];failures=[];start=time.monotonic()
    for i,(wid,rows) in enumerate(sorted(groups.items())):
        dest=output/'worlds'/f'{wid}.json'
        if dest.exists():result=json.loads(dest.read_text())
        else:
            try:result=analyze_world(registry[wid],rows,max_candidates,timeout)
            except (ValueError,KeyError) as exc:
                result={'world_id':wid,'status':'not_analyzed','reason':str(exc),'observed_physical_cells':len(rows)}
            atomic_json(dest,plain(result))
        if result['status']=='completed':worlds.append(result)
        else:failures.append(result)
        print(json.dumps({'worlds_done':i+1,'worlds_total':len(groups),'world_id':wid,'status':result['status'],
            'elapsed_seconds':time.monotonic()-start}),flush=True)
    planning=[r for w in worlds for r in w['planning']]
    pairs=[r for w in worlds for r in w['matched_first_pairs']]
    joint=[dict(world_id=w['world_id'],**r) for w in worlds for r in w['joint_cap_violations']]
    atomic_json(output/'WORLD_DOMAINS.json',[w['domain'] for w in worlds])
    atomic_json(output/'PLANNING_RESULTS.json',planning);write_csv(output/'PLANNING_RESULTS.csv',[flat_entry(r) for r in planning])
    atomic_json(output/'MATCHED_FIRST_STEPS.json',pairs);write_csv(output/'MATCHED_FIRST_STEPS.csv',pairs)
    atomic_json(output/'JOINT_CAP_FAILURES.json',joint);write_csv(output/'JOINT_CAP_FAILURES.csv',joint)
    atomic_json(output/'NOT_ANALYZED.json',failures)
    summary={'status':'completed' if not failures else 'partial','worlds_completed':len(worlds),'worlds_not_analyzed':len(failures),
        'observed_physical_cells':sum(len(x) for x in groups.values()),'planning_threshold_rows':len(planning),
        'initially_invalid_rows':sum(not r['initial_valid'] for r in planning),
        'retention_penalty_rows':sum(r['retention_penalty_resolved'] for r in planning),
        'batch2_improvement_rows':sum(r['batch2_improvement_resolved'] for r in planning),
        'batch4_improvement_rows':sum(r['batch4_improvement_resolved'] for r in planning),
        'planning_over_best_greedy_rows':sum(r['planning_advantage_over_best_greedy_resolved'] for r in planning),
        'matched_first_pairs':len(pairs),'matched_first_retaining_separations':sum(r['retaining_bounds_separate'] for r in pairs),
        'matched_first_retention_specific_separations':sum(r['retention_specific_separation'] for r in pairs),
        'joint_cap_failure_rows':len(joint),'elapsed_seconds':time.monotonic()-start,
        'interpretation':'adaptive development screen on means; counts are overlapping thresholds, not independent worlds or confirmed findings'}
    atomic_json(output/'SUMMARY.json',summary)
    print(json.dumps(summary,indent=2),flush=True)
    return summary


def main():
    p=argparse.ArgumentParser();p.add_argument('--batch',type=Path,required=True)
    p.add_argument('--registry',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--max-candidates',type=int,default=12);p.add_argument('--timeout',type=float,default=5)
    args=p.parse_args()
    if not 1<=args.max_candidates<=20:p.error('max-candidates must be 1..20; default is 12 and larger domains require explicit budget consideration')
    if args.timeout<=0:p.error('timeout must be positive')
    analyze(args.batch,args.registry,args.output,args.max_candidates,args.timeout)


if __name__=='__main__':main()
