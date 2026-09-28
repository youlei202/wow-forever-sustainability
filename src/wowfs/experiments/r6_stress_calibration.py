"""Four predeclared native cells for a separately labeled amplitude stress panel."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np

from wowfs.paths import setup_paths, atomic_json, canonical_hash
from wowfs.experiments.r3_affine import raw, controls, trace_events
from wowfs.experiments.r6_native import define_alias, instantiate, r3_base, run_jobs, R5_SHA256

POINTS = [('zero_anchor',0.,0.), ('old_frontier_anchor',180.,0.),
          ('periodic_anchor',0.,500.), ('heldout_center',90.,250.)]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--resume',action='store_true')
    args=parser.parse_args()
    root=setup_paths();run_id='stress-calibration-v1'
    base,base_path=r3_base()
    aliases=[define_alias('r6_stress_'+name,12795,'main_hand',{
        'weapon_damage_scale':dps/(51/1.3), 'weapon_speed_seconds':1.3,
        'speed_mode':'hold_base_dps', 'periodic_damage_per_tick':dot}) for name,dps,dot in POINTS]
    science={
        'formal_r5_sha256':R5_SHA256,
        'purpose':'Native fixed-control amplitude stress calibration and heldout affine/control validation; not a theorem success claim.',
        'panel_scope':'Separate from original R3 rectangleDPS[24,54]×tick[0,30]; broad stress amplitudes are research-only, not realistic official catalogue items.',
        'context':{'race':'RaceHuman','class':'ClassWarrior','task':'high_armor','duration_seconds':180,
            'target_count':1,'armor':10000,'policy':'native_reck','offhand':19019,'trinkets':[11815,13965]},
        'interface':'One expanding main-hand slot; research alias labels retain baseID12795; aliases are mutually exclusive and cannot be coequipped.',
        'declared_partner_count':1,'declared_policy_count':1,'declared_task_count':1,
        'old_anchor':{'base_dps':180.,'periodic_damage_per_tick':0.},
        'prospective_parameter_domain':{'base_dps':[1.,175.],'periodic_damage_per_tick':[0.,500.]},
        'calibration_points':[{'label':name,'base_dps':dps,'periodic_damage_per_tick':dot} for name,dps,dot in POINTS[:3]],
        'heldout_prediction':{'label':POINTS[3][0],'base_dps':90.,'periodic_damage_per_tick':250.},
        'seed_start':609240001,'iterations':2048,'debug_first_iteration':True,
        'unchanged_control':'Speed1.3,1PPM,3-second periodic interval,10ticks,native effect registration,stats,all other equipment,task,APL fixed.',
        'behavior_definition':'Physical action-channel DPS normalized by fixed old-frontier scalar; fixed resource diagnostics separate. No itemID/parameter-label novelty coordinates. Distinct from R3 normalized damage fractions.',
        'tests':'Three-corner fit predicts fourth point; per-seed DPS residual plus per-action mean damage, aggregate controls and normalized first-seed trace.',
        'tolerance_dps':1e-8,
        'sequence_protocol':'Derive prospective utility0.975F0 line only from calibration and frozen response constraints; futureD never defines the region. Freeze full sequence before independent-seed confirmation.',
        'capacity_thresholds_if_B_succeeds':[.025,.035,.05,.075],
        'base_input_sha256':canonical_hash(base),'research_aliases':aliases}
    out=root/'artifacts/r6-theory-native';freeze=out/'FROZEN_STRESS_CALIBRATION.json'
    if freeze.exists():
        assert json.loads(freeze.read_text())['science']==science,'stress protocol differs from frozen design'
    else:atomic_json(freeze,{'utc':datetime.now(timezone.utc).isoformat(),'science':science,
        'status':'frozen_before_R6_native_calls'})
    jobs=[]
    for (name,dps,dot),alias in zip(POINTS,aliases):
        value=instantiate(base,[alias],seed=609240001,iterations=2048,debug=True)
        jobs.append({'input':value,'meta':{'panel':'amplitude_stress','point':name,'base_dps':dps,
            'dot_damage':dot,'research_alias':alias['research_alias'],
            'research_alias_physics_sha256':alias['physics_identity_sha256'],
            'race':'RaceHuman','task':'high_armor','strategy':'native_reck','world':'research_reward_amplitude'}})
    run=run_jobs(jobs,run_id,science,workers=args.workers,resume=args.resume,
        source_paths=[Path(__file__)],input_artifacts={'base_input.json':base_path})
    rows=json.loads((run/'RESULTS.json').read_text())['rows']
    values=[np.asarray(r['dps_samples']) for r in rows]
    prediction=values[0]+.5*(values[1]-values[0])+.5*(values[2]-values[0])
    outputs=[raw(r) for r in rows]
    control_hashes=[canonical_hash(controls(o)) for o in outputs]
    traces=[canonical_hash(trace_events(o['logs'])) for o in outputs]
    keys=set().union(*(r['actions'] for r in rows))
    action_errors={key:rows[3]['actions'].get(key,{}).get('damage',0)-
        (rows[0]['actions'].get(key,{}).get('damage',0)+
         .5*(rows[1]['actions'].get(key,{}).get('damage',0)-rows[0]['actions'].get(key,{}).get('damage',0))+
         .5*(rows[2]['actions'].get(key,{}).get('damage',0)-rows[0]['actions'].get(key,{}).get('damage',0)))
        for key in sorted(keys)}
    residual=float(np.max(np.abs(values[3]-prediction)))
    result={'run':str(run),'source_freeze':str(freeze),'native_cells':4,'physical_battles':8192,
        'means':[{'point':r['point'],'mean_dps':r['dps_mean']} for r in rows],
        'max_absolute_per_seed_dps_residual':residual,'affine_dps_pass_1e_8':residual<=1e-8,
        'max_absolute_per_action_mean_damage_residual':max(map(abs,action_errors.values())),
        'per_action_mean_damage_residuals':action_errors,
        'aggregate_control_hashes':control_hashes,'aggregate_controls_identical':len(set(control_hashes))==1,
        'first_seed_trace_hashes':traces,'normalized_first_seed_event_traces_identical':len(set(traces))==1,
        'scope':'Finite native stress calibration; structural heldout prediction, not independent means confirmation or distribution-free theorem certification.'}
    atomic_json(run/'CALIBRATION_CHECK.json',result)
    atomic_json(out/'STRESS_CALIBRATION_CHECK.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
