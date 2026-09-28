"""Analyze the bounded native R5 gate probe without forcing a cascade model."""
from __future__ import annotations
import json
from itertools import combinations
from pathlib import Path
import numpy as np

from wowfs.paths import setup_paths,atomic_json
from wowfs.experiments.r2_native import file_hash
from wowfs.experiments.r2_analysis import interval
from wowfs.experiments.r2_sequence_analysis import behavior_vector,write_csv
from wowfs.experiments.r4_feasibility import FiniteProblem,evaluate_admission
from wowfs.experiments.r6_theory import (stable_witness_assumptions,audit_unique_repair_responses,
    least_repair_closure,interval_repair_closures)

ANCHOR=14551
SOURCES=(21998,21278)
CORE=19143
OLD_LEGS=22385
REPAIRS=(22000,15057)


def main():
    root=setup_paths();out=root/'artifacts/r6-theory-native'
    run=root/'runs/r6-theory-native/native-gate-probe-v1'
    data=json.loads((run/'RESULTS.json').read_text())
    if data['errors'] or any(row is None for row in data['rows']):
        raise ValueError('Incomplete native matrix cannot be silently completed')
    rows=data['rows'];native={(r['glove_id'],r['leg_id']):r for r in rows if r['condition']=='native'}
    expected={(g,l) for g in (ANCHOR,*SOURCES,CORE) for l in (OLD_LEGS,*REPAIRS)}
    if set(native)!=expected:raise ValueError('Complete legal4×3 matrix required')
    duration=180.;old_keys=[(g,OLD_LEGS) for g in (ANCHOR,*SOURCES)]
    old_values=np.array([native[key]['dps_mean'] for key in old_keys]);f0=float(old_values.max())
    epsilon=.05*f0;cap=1.05*f0
    v=[native[(source,OLD_LEGS)]['dps_mean'] for source in SOURCES]
    q=native[(CORE,OLD_LEGS)]['dps_mean']
    matrix=[[native[(source,repair)]['dps_mean'] for repair in REPAIRS] for source in SOURCES]
    p=[matrix[i][i] for i in range(2)]
    numeric=stable_witness_assumptions(f0,epsilon,cap,v,q,p)
    association=audit_unique_repair_responses(v,[-np.inf]*2,matrix,tolerance=1e-9)
    # Fourteen marginal mean intervals and two paired gate contrasts share
    # one declared conservative family; no distribution-free coverage claim.
    family=16;mean_intervals={(r['glove_id'],r['leg_id'],r['condition']):interval(r['dps_samples'],family=family) for r in rows}
    instances=[]
    for r in rows:
        b=behavior_vector(r,duration)
        instances.append({'m':2,'status':'executed_native_gate_probe','race':r['race'],
            'task':r['task'],'strategy':r['strategy'],'glove_id':r['glove_id'],'leg_id':r['leg_id'],
            'condition':r['condition'],'gear_id':r['gear_id'],'dps_mean':r['dps_mean'],
            **{k:mean_intervals[(r['glove_id'],r['leg_id'],r['condition'])][k] for k in ['se','ci_low','ci_high']},
            'old_frontier':f0,'epsilon_raw':epsilon,'fixed_cap':cap,'iterations':r['iterations'],
            'behavior':b.tolist(),'native_cache_key':r['cache_key']})
    gate=[]
    for source,repair,condition,label in [(21998,22000,'heroism4_off','Heroism4'),
                                         (21278,15057,'stormshroud4_off','Stormshroud4')]:
        off=next(r for r in rows if r['condition']==condition)
        on=native[(source,repair)]
        diff=np.asarray(on['dps_samples'])-np.asarray(off['dps_samples'])
        gate.append({'effect':label,'source':source,'repair':repair,
                     **interval(diff,family=family),'scope':'Same equipment and static stats; only matching4piece callback disabled.'})
    closures=[];releases=[];details=[]
    point_closure=least_repair_closure(f0,q,[x+epsilon for x in v],p)
    bounds=interval_repair_closures(f0,
        tuple(mean_intervals[(CORE,OLD_LEGS,'native')][k] for k in ['ci_low','ci_high']),
        [tuple(mean_intervals[(s,OLD_LEGS,'native')][k]+epsilon for k in ['ci_low','ci_high']) for s in SOURCES],
        [tuple(mean_intervals[(s,r,'native')][k] for k in ['ci_low','ci_high']) for s,r in zip(SOURCES,REPAIRS)])
    reference=np.array([behavior_vector(native[key],duration) for key in old_keys])
    initial_valid=all(f0-epsilon<=x<=f0+1e-9 for x in v)
    response_model_valid=True
    for count in range(3):
        for repair_indices in combinations(range(2),count):
            repair_set=set(repair_indices);legs=(OLD_LEGS,)+tuple(REPAIRS[i] for i in repair_indices)
            keys=[(g,l) for g in (ANCHOR,*SOURCES,CORE) for l in legs]
            selected=[native[key] for key in keys]
            values=np.array([r['dps_mean'] for r in selected])[:,None,None]
            behavior=np.array([behavior_vector(r,duration) for r in selected])[:,None,None,:]
            protected=np.array([key in old_keys for key in keys])
            labels=[{str(g),str(l)} for g,l in keys]
            new=[str(CORE)]+[str(REPAIRS[i]) for i in repair_indices]
            problem=FiniteProblem(values,behavior,labels,protected,new,list(map(str,SOURCES)),
                [f0],[cap],epsilon=.05,delta=.05,min_mass=.05,k_max=1,gear_ids=[r['gear_id'] for r in selected])
            metric=evaluate_admission(problem,np.ones(len(keys),bool))
            actual_frontier=float(values.max());predicted_frontier=max([f0,q]+[p[i] for i in repair_indices])
            core_mask=np.array([g==CORE for g,l in keys])
            core_D=bool(np.any((problem.distances[core_mask]>=.05-1e-9)&
                              (problem.values[core_mask]>=actual_frontier-epsilon-1e-9)))
            full_mapping=True
            for i,source in enumerate(SOURCES):
                actual_source=max(native[(source,l)]['dps_mean'] for l in legs)
                predicted_source=max(v[i],p[i]) if i in repair_set else v[i]
                matches=abs(actual_source-predicted_source)<=1e-9
                full_mapping &= matches
                closures.append({'m':2,'release_items':new,'repair_indices':list(repair_indices),'source_id':source,
                    'old_source_value':v[i],'relevance_threshold':v[i]+epsilon,
                    'designated_repair_value':p[i],'actual_final_frontier':actual_frontier,
                    'R5_projected_frontier':predicted_frontier,'actual_source_value':actual_source,
                    'R5_projected_source_value':predicted_source,'source_value_map_matches':matches,
                    'frontier_map_matches':abs(actual_frontier-predicted_frontier)<=1e-9,
                    'actual_source_competitive':actual_source>=actual_frontier-epsilon-1e-9,
                    'theorem_status':'applicable_only_if_all_R5_assumptions_hold','stable_numeric_assumptions':numeric['all_numeric_assumptions']})
            response_model_valid &= full_mapping and abs(actual_frontier-predicted_frontier)<=1e-9
            record={'m':2,'release_items':new,'release_size':len(new),'declared_configurations':len(keys),
                'admission':'every physically legal configuration induced by the release; no blacklist/cap filtering',
                'initial_old_state_valid':initial_valid,**{k:metric[k] for k in ['P','N','D','L','H','C','joint_pass']},
                'core_D':core_D,'old_portfolio_retained':f0>=actual_frontier-epsilon-1e-9,
                'final_frontier':actual_frontier,'initial_threatened_old_only_count':sum(x+epsilon<max(f0,q) for x in v),
                'fixed_cap':cap,'minimum_cap_slack':cap-actual_frontier,'K':metric['K']}
            releases.append(record);details.append({**record,'metrics':metric,'exact_gear_ids':[r['gear_id'] for r in selected]})
    eligible=[r for r in releases if r['joint_pass']]
    native_min=min((r['release_size'] for r in eligible),default=None) if initial_valid else None
    theorem_applicable=numeric['all_numeric_assumptions'] and response_model_valid and all(r['core_D'] for r in releases)
    summary={'m':2,'status':'native_gates_measured_no_R5_cascade_constructed' if not theorem_applicable else 'R5_model_verified',
        'initial_state_valid':initial_valid,'old_anchor_attains_frontier':abs(native[(ANCHOR,OLD_LEGS)]['dps_mean']-f0)<=1e-9,
        'minimum_core_required_release_size':native_min,
        'minimum_status':('not_applicable_invalid_initial_state' if not initial_valid else
                          'no_feasible_completed_release_in_declared_domain' if native_min is None else 'exact_finite_full_release_minimum'),
        'R5_theorem_applicable':theorem_applicable,'R5_predicted_minimum':point_closure['minimum_release_size_conditional_on_R5_model'] if theorem_applicable else None,
        'closure_projection_only':point_closure,'interval_closure_projection_only':bounds,
        'numeric_assumptions':numeric,'source_association_audit':association,'full_response_mapping_valid':response_model_valid,
        'gate_effects':gate,'release_results':details,
        'scope':'Native finite2048-seed means. No matched cascade/local pair, no arbitrary tolerance/stat retuning, no synthetic table treated as native.'}
    minimum_rows=[{k:v for k,v in summary.items() if k in ['m','status','initial_state_valid','minimum_core_required_release_size','minimum_status','R5_theorem_applicable','R5_predicted_minimum']}]
    for m in (4,8):
        minimum_rows.append({'m':m,'status':'not_run','minimum_status':'not_run_no_independent_native_source_selective_gate_family','R5_theorem_applicable':False})
        instances.append({'m':m,'status':'not_run_no_independent_native_source_selective_gate_family'})
    write_csv(out/'CASCADE_INSTANCES.csv',instances)
    write_csv(out/'CASCADE_CLOSURE_CHECKS.csv',closures)
    write_csv(out/'CASCADE_MIN_RELEASE.csv',minimum_rows)
    write_csv(out/'CASCADE_RELEASE_SUBSETS.csv',releases)
    write_csv(out/'CASCADE_GATE_EFFECTS.csv',gate)
    atomic_json(out/'CASCADE_ANALYSIS.json',summary)
    atomic_json(out/'CASCADE_ANALYSIS_AUDIT.json',{'source_sha256':file_hash(Path(__file__)),
        'results_sha256':file_hash(run/'RESULTS.json'),'formal_R5_sha256':file_hash(root/'inputs/r5-theory/THEORY.md'),
        'native_cells':len(rows),'native_battles':sum(r['iterations'] for r in rows),'analysis_native_calls':0,
        'DPS_interval_family':16,'uncertainty':'Approximate Student-t; sampled old numerical frontier/epsilon are fixed design values in the conditional closure diagnostic.'})
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':main()
