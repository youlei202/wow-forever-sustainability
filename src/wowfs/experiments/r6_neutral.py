"""Frozen R5-guided native frontier-neutral stress experiment.

The stress amplitudes, single task/policy/partner, and fixed-frontier action-DPS
behavior normalization are explicitly different from the original R3 panel.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import numpy as np

from wowfs.paths import setup_paths, atomic_json, canonical_hash, SOURCE_ROOT
from wowfs.experiments.r2_native import file_hash
from wowfs.experiments.r3_affine import raw, controls
from wowfs.experiments.r2_sequence_analysis import write_csv
from wowfs.experiments.r6_geometry import affine_fit, damage_channels, line_segment, polygon_vertices, segment_certificate, greedy_grid
from wowfs.experiments.r6_native import run_jobs, r3_base, define_alias, instantiate

OUT = 'artifacts/r6-theory-native'
CALIBRATION_RUN = 'stress-calibration-v1'
DELTA = .05
SCALING_DELTAS = [.025,.035,.05,.075]


def native_job(theta, design_id, seed, iterations, **meta):
    base, _ = r3_base()
    dps, tick = map(float, theta)
    alias = define_alias(design_id,12795,'main_hand',{
        'weapon_damage_scale':dps/(51/1.3), 'weapon_speed_seconds':1.3,
        'speed_mode':'hold_base_dps','periodic_damage_per_tick':tick})
    return {'input':instantiate(base,[alias],seed=seed,iterations=iterations,debug=False),
            'meta':{'design_id':design_id,'theta':[dps,tick], 'research_alias':alias,
                    'race':'RaceHuman','task':'high_armor','strategy':'native_reck',**meta}}


def freeze(calibration_run=None):
    root=setup_paths(); out=root/OUT
    run=Path(calibration_run) if calibration_run else root/'runs/r6-theory-native'/CALIBRATION_RUN
    result=json.loads((run/'RESULTS.json').read_text())
    if result['errors']: raise ValueError('Incomplete calibration')
    rows=result['rows']
    # Use physics parameters in each archived request, not incidental labels.
    jobs=json.loads((run/'JOBS.json').read_text())
    by_point={}
    for row,job in zip(rows,jobs):
        variant=job['input']['research_variants'][0]
        point=(round(variant['weapon_damage_scale']*(51/1.3),9),float(variant['periodic_damage_per_tick']))
        by_point[point]=row
    anchors=[(0.,0.),(180.,0.),(0.,500.)]
    selected=[by_point[p] for p in anchors]
    u=affine_fit(anchors,[r['dps_mean'] for r in selected])
    c=affine_fit(anchors,[damage_channels(r,180) for r in selected])
    seed_coefficients=affine_fit(anchors,[r['dps_samples'] for r in selected])
    f0=float(np.r_[1.,180.,0.] @ u)
    behavior=c/f0
    held=by_point[(90.,250.)]
    residual=np.asarray(held['dps_samples'])-np.r_[1.,90.,250.] @ seed_coefficients
    channel_residual=damage_channels(held,180)-np.r_[1.,90.,250.] @ c
    control_hashes=[canonical_hash(controls(raw(r))) for r in rows]
    structural={'all_aggregate_controls_identical':len(set(control_hashes))==1,
                'max_heldout_per_seed_DPS_residual':float(np.max(np.abs(residual))),
                'max_heldout_mean_channel_DPS_residual':float(np.max(np.abs(channel_residual))),
                'scope':'Finite matched-seed control/affinity audit; population identity remains a native fixed-control model assumption.'}
    if not structural['all_aggregate_controls_identical'] or np.max(np.abs(residual))>1e-8 or np.max(np.abs(channel_residual))>1e-8:
        atomic_json(out/'FAILED_STRESS_CALIBRATION.json',structural)
        raise ValueError('Native fixed-control affine premise failed')
    a=[[-1,0],[1,0],[0,-1],[0,1],u[1:].tolist(),(-u[1:]).tolist()]
    b=[-1,175,0,500,f0-u[0],u[0]-.95*f0]
    endpoints=line_segment(a,b,u,.975*f0)
    cert=segment_certificate(a,b,endpoints,behavior,DELTA,1,1)
    old_phi=np.r_[1.,180.,0.] @ behavior
    proposed=greedy_grid(cert,behavior,[old_phi])
    accepted=[r for r in proposed if r['accepted']]
    # Archive-interference checks choose the grid sequence only after geometry
    # and its lower bound have been computed; no native candidate outcomes used.
    if len(accepted)<cert['T_guaranteed']: raise ValueError('R5 packing construction discrepancy')
    selected_sequence=accepted[:cert['T_guaranteed']]
    for i,row in enumerate(selected_sequence,1): row['design_id']=f'neutral_stress_{i:02d}'
    protocol={'formal_basis_sha256':file_hash(root/'inputs/r5-theory/THEORY.md'),
        'created_utc':datetime.now(timezone.utc).isoformat(),'calibration_run':str(run),
        'calibration_results_sha256':file_hash(run/'RESULTS.json'),'calibration_protocol_sha256':file_hash(run/'PROTOCOL.json'),
        'domain_scope':'Native research amplitude stress domain; Human Warrior, one high-armor180s task, native_reck policy, fixed Thunderfury OH and HoJ/Blackhands partners. No other partners/policies/tasks are claimed.',
        'amplitude_departure':'New DPS[1,175], tick[0,500]; old research DPS180/tick0. Exceeds original R3 DPS[24,54],tick[0,30]. Not an official item balance proposal.',
        'old_theta':[180.,0.], 'initial_frontier':f0,'fixed_cap':1.05*f0,
        'epsilon_raw':.05*f0,'delta':DELTA,'task_weight':1.,'K0':1,
        'old_sources':['old_research_talon','fixed_partner_equipment'],
        'J':1,'policies':1,'M0':1,'p':1,'slot':'main_hand','slot_new_new_coequipment':False,
        'behavior_coordinates':['white_DPS/F0','execute_DPS/F0','whirlwind_cleave_DPS/F0','bloodthirst_DPS/F0','other_action_DPS/F0'],
        'behavior_normalizer':'Frozen initial calibration frontier, not each new design total damage. Real native action channels; no item IDs.',
        'tracked_capabilities':['total task DPS'],
        'nonutility_scope':'Rage flow/waste, event counters and auras checked for fixed controls. Individual damage channels are behavior directions, not separately capped capabilities; no survival/healing/PvP frontier claim.',
        'A':a,'b':b,'constraint_labels':['DPS>=1','DPS<=175','tick>=0','tick<=500','all_new_utility<=F0','witness_utility>=.95F0'],
        'vertices':polygon_vertices(a,b).tolist(),'utility_coefficients':u.tolist(),'channel_DPS_coefficients':c.tolist(),
        'behavior_coefficients':behavior.tolist(),'constant_utility_fraction':.975,
        'segment':endpoints.tolist(),'geometry':cert,'structural_calibration':structural,
        'construction_order':'Increasing physical weapon DPS on the R5 3delta/beta grid; discard archive-blocked points; stop at predicted guaranteed length.',
        'grid_candidates':proposed,'frozen_sequence':selected_sequence,
        'development':{'seed':609250001,'iterations':2048},
        'fresh_confirmation':{'seed_start':609260001,'blocks':8,'seed_stride':10000,'iterations_per_block':1024,'retuning':False},
        'confirmation_inference':'Paired per-seed utility differences and independent block-level action-channel contrasts; simultaneous approximate Student t intervals with explicit family count. No distribution-free guarantee.',
        'capacity_scaling':{'deltas':SCALING_DELTAS,'gate':'Execute only if frozen B sequence passes fresh confirmation; same frozen segment, no region changes.'},
        'grammar':'Fixed one-slot parameter inequalities; every admitted old design remains available; no per-item exclusion.'}
    path=out/'FRONTIER_NEUTRAL_POLYTOPE.json'
    if path.exists(): raise ValueError('Never overwrite a frozen design')
    atomic_json(path,protocol)
    atomic_json(out/'FRONTIER_NEUTRAL_FREEZE_RECEIPT.json',{'utc':protocol['created_utc'],'sha256':file_hash(path)})
    write_csv(out/'BEHAVIOR_GEOMETRY.csv',[{'panel':'native_stress_embedded_line',**{k:cert[k] for k in ['r','h','beta','delta','M0','p','grid_candidates','T_guaranteed']},'frozen_before_native_sequence':True}])
    print(json.dumps({'path':str(path),'f0':f0,'geometry':cert,'sequence':selected_sequence,'structural':structural},indent=2))


def execute(phase, workers=32):
    root=setup_paths(); path=root/OUT/'FRONTIER_NEUTRAL_POLYTOPE.json'
    spec=json.loads(path.read_text())
    if file_hash(path)!=json.loads((path.parent/'FRONTIER_NEUTRAL_FREEZE_RECEIPT.json').read_text())['sha256']:
        raise ValueError('Frozen B sequence modified')
    designs=[{'design_id':'old_anchor','theta':spec['old_theta']},*spec['frozen_sequence']]
    jobs=[]
    if phase=='development':
        for d in designs: jobs.append(native_job(d['theta'],d['design_id'],**spec['development']))
    elif phase=='confirmation':
        protocol=spec['fresh_confirmation']
        for block in range(protocol['blocks']):
            for d in designs:
                jobs.append(native_job(d['theta'],d['design_id'],protocol['seed_start']+block*protocol['seed_stride'],protocol['iterations_per_block'],block=block))
    else: raise ValueError(phase)
    return run_jobs(jobs,'neutral-'+phase+'-v1',
        {'phase':phase,'frozen_polytope_sha256':file_hash(path),'retuning':False},workers=workers,
        source_paths=[Path(__file__),SOURCE_ROOT/'src/wowfs/experiments/r6_geometry.py'],
        input_artifacts={'frozen_polytope.json':path})


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['freeze','development','confirmation']);parser.add_argument('--calibration-run');parser.add_argument('--workers',type=int,default=32)
    args=parser.parse_args()
    if args.phase=='freeze': freeze(args.calibration_run)
    else: print(execute(args.phase,args.workers))


if __name__=='__main__': main()
