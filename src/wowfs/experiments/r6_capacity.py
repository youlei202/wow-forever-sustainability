"""Gated capacity experiment in the already-frozen native line segment."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import numpy as np

from wowfs.paths import setup_paths, atomic_json, SOURCE_ROOT
from wowfs.experiments.r2_native import file_hash
from wowfs.experiments.r2_sequence_analysis import write_csv
from wowfs.experiments.r6_geometry import segment_certificate
from wowfs.experiments.r6_native import run_jobs
from wowfs.experiments.r6_neutral import native_job
from wowfs.experiments.r6_neutral_analysis import analyze_rows


def forbidden_interval(start, direction, old, delta):
    """Closed archive ball intersected with [0,1], computed coordinatewise."""
    lower,upper=0.,1.
    for c,v,o in zip(start,direction,old):
        if abs(v)<1e-12:
            if abs(c-o)>delta: return None
        else:
            endpoints=sorted([(o-delta-c)/v,(o+delta-c)/v])
            lower=max(lower,endpoints[0]);upper=min(upper,endpoints[1])
    return (lower,upper) if lower<=upper else None


def optimal_prefix_designs(start, direction, old, delta):
    beta=float(max(abs(direction)))
    forbidden=forbidden_interval(start,direction,old,delta)
    if forbidden is None:
        end=1.
    else:
        if forbidden[1]<1-1e-10 or forbidden[0]<=0:
            raise ValueError('This prespecified solver requires one archive-blocked suffix')
        end=forbidden[0]
    # In one dimension all two-new distances equal beta*|t-s|. Packing
    # a prefix of length end therefore gives this exact continuous upper bound.
    count=int(np.floor(beta*end/delta+1e-10))+1
    def okay(q):
        grid=np.arange(count)*q/beta
        if grid[-1]>1: return False
        return all(max(abs(start+direction*z-old))>=q for z in grid)
    low,high=delta,beta+delta
    if not okay(low): raise ValueError('Capacity formula/construction discrepancy')
    for _ in range(100):
        mid=(low+high)/2
        if okay(mid): low=mid
        else: high=mid
    q=(low+delta)/2
    z=np.arange(count)*q/beta
    return {'exact_fitted_continuous_capacity':count,'allowed_prefix_endpoint':float(end),
            'archive_ball_intersection':forbidden,'max_common_separation':low,
            'selected_common_separation':q,'segment_t':z.tolist(),
            'proof_scope':'Exact numeric 1D fitted-affine model with sole old profile; not whole-game or population optimality.'}


def freeze():
    root=setup_paths();out=root/'artifacts/r6-theory-native'
    gate=json.loads((out/'FRONTIER_NEUTRAL_CONFIRMATION.json').read_text())
    if not gate['all_joint_supported']: raise ValueError('C gate closed: B independent confirmation failed')
    spec=json.loads((out/'FRONTIER_NEUTRAL_POLYTOPE.json').read_text())
    segment=np.asarray(spec['segment']); b=np.asarray(spec['behavior_coefficients'])
    first=np.r_[1.,segment[0]]@b; direction=(segment[1]-segment[0])@b[1:]
    old=np.r_[1.,spec['old_theta']]@b
    panels=[]
    for delta in spec['capacity_scaling']['deltas']:
        construction=optimal_prefix_designs(first,direction,old,delta)
        designs=[{'design_id':f'capacity_{delta:.3f}_{i:02d}',
                  'theta':(segment[0]+(segment[1]-segment[0])*z).tolist()}
                 for i,z in enumerate(construction['segment_t'],1)]
        cert=segment_certificate(spec['A'],spec['b'],segment,b,delta,spec['M0'],spec['p'])
        panels.append({'delta':delta,'theorem_T_guaranteed':cert['T_guaranteed'],
                       'construction':construction,'designs':designs})
    result={'created_utc':datetime.now(timezone.utc).isoformat(),
            'fixed_region_sha256':file_hash(out/'FRONTIER_NEUTRAL_POLYTOPE.json'),
            'B_gate_confirmation_sha256':file_hash(out/'FRONTIER_NEUTRAL_CONFIRMATION.json'),
            'deltas_predeclared_in_B_freeze':True,'region_changed':False,
            'panels':panels,'fresh_confirmation':{'blocks':16,'iterations_per_block':512,'seed_start':609280001,'seed_stride':10000},
            'global_approximate_alpha':.05,'per_panel_alpha':.05/len(panels),
            'retuning_after_fresh_outcomes':False,'dimension_scaling':'not_run; only r=1 affine slice certified',
            'interpretation':'Four threshold values in one frozen finite-width family; no empirical asymptotic-law claim.'}
    path=out/'FROZEN_CAPACITY_DESIGN.json'
    if path.exists(): raise ValueError('Capacity design already frozen')
    atomic_json(path,result)
    print(json.dumps(result,indent=2))


def execute(workers=32):
    root=setup_paths();out=root/'artifacts/r6-theory-native'
    spec=json.loads((out/'FRONTIER_NEUTRAL_POLYTOPE.json').read_text())
    frozen=json.loads((out/'FROZEN_CAPACITY_DESIGN.json').read_text())
    assert file_hash(out/'FRONTIER_NEUTRAL_POLYTOPE.json')==frozen['fixed_region_sha256']
    protocol=frozen['fresh_confirmation'];jobs=[]
    designs=[{'design_id':'old_anchor','theta':spec['old_theta']}]
    designs += [d for panel in frozen['panels'] for d in panel['designs']]
    for block in range(protocol['blocks']):
        for design in designs:
            jobs.append(native_job(design['theta'],design['design_id'],protocol['seed_start']+block*protocol['seed_stride'],protocol['iterations_per_block'],block=block))
    return run_jobs(jobs,'capacity-confirmation-v1',{'purpose':'Independent fresh confirmation of four fixed-region capacity sequences',
                      'frozen_capacity_sha256':file_hash(out/'FROZEN_CAPACITY_DESIGN.json')},workers=workers,
                    source_paths=[Path(__file__),SOURCE_ROOT/'src/wowfs/experiments/r6_neutral.py',SOURCE_ROOT/'src/wowfs/experiments/r6_geometry.py'],
                    input_artifacts={'frozen_capacity.json':out/'FROZEN_CAPACITY_DESIGN.json','frozen_polytope.json':out/'FRONTIER_NEUTRAL_POLYTOPE.json'})


def analyze():
    root=setup_paths();out=root/'artifacts/r6-theory-native'
    spec=json.loads((out/'FRONTIER_NEUTRAL_POLYTOPE.json').read_text())
    frozen=json.loads((out/'FROZEN_CAPACITY_DESIGN.json').read_text())
    data=json.loads((root/'runs/r6-theory-native/capacity-confirmation-v1/RESULTS.json').read_text())
    if data['errors']: raise ValueError('Incomplete C native run')
    summaries=[]; sequences=[]; analyses=[]
    for panel in frozen['panels']:
        order=['old_anchor']+[d['design_id'] for d in panel['designs']]
        analysis=analyze_rows([r for r in data['rows'] if r['design_id'] in order],order,
            spec['initial_frontier'],spec['epsilon_raw'],panel['delta'],spec['fixed_cap'],frozen['per_panel_alpha'])
        analyses.append({'delta':panel['delta'],**analysis})
        for row in analysis['rows']: sequences.append({'panel':'capacity',**row})
        summaries.append({'delta':panel['delta'],'r':1,'same_frozen_region':True,
            'theorem_guaranteed':panel['theorem_T_guaranteed'],
            'fitted_continuous_maximum':panel['construction']['exact_fitted_continuous_capacity'],
            'native_fresh_candidates':len(panel['designs']),'confirmed_prefix':analysis['confirmed_updates'],
            'all_joint_supported':analysis['all_joint_supported'],
            'point_successes':sum(r['joint_point_estimate'] for r in analysis['rows']),
            'minimum_novelty_lower':min(r['min_full_archive_distance_lower'] for r in analysis['rows']),
            'maximum_frontier_growth':max(r['point_frontier_growth_vs_fresh_old'] for r in analysis['rows']),
            'K':1,'fixed_rule_rows':6,'per_panel_alpha':frozen['per_panel_alpha'],
            'scope':'Native lower bound plus fitted-line geometric maximum; no population/whole-game maximum claim.'})
    atomic_json(out/'CAPACITY_CONFIRMATION.json',{'panels':analyses,'summary':summaries,'global_alpha':frozen['global_approximate_alpha']})
    write_csv(out/'CAPACITY_SCALING.csv',summaries)
    write_csv(out/'CAPACITY_SEQUENCES.csv',sequences)
    print(json.dumps(summaries,indent=2))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['freeze','execute','analyze']);parser.add_argument('--workers',type=int,default=32)
    args=parser.parse_args()
    if args.phase=='freeze': freeze()
    elif args.phase=='execute': print(execute(args.workers))
    else: analyze()


if __name__=='__main__': main()
