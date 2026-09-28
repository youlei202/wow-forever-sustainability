"""New two-slot native reward calibration for actual multitask decision value."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import re
import numpy as np
import yaml
from wowfs.paths import setup_paths, atomic_json, canonical_hash, SOURCE_ROOT
from wowfs.experiments.value_native import make_input, define_alias, instantiate, run_jobs, native_database
from wowfs.experiments.r3_affine import raw, controls, trace_events
from wowfs.experiments.r2_native import file_hash

ANCHORS=[(24,0,.5,0),(54,0,.5,0),(24,60,.5,0),(24,0,1,0),(24,0,.5,300)]
HELDOUT=[(43,25,.85,220),(67,105,1.25,430)]
OLD_MH=[(39,10),(33,30)]
OLD_OH=[(.75,300),(1,150)]
SEED=720000001
ITERATIONS=256
BOUNDS=[[10,80],[0,150],[.1,1.5],[0,500]]


def incoming_controls(output):
    return [{'actions':controls({'raidMetrics':{'parties':[{'players':[target]}]}})['actions'],
             'auras':target.get('auras',[]),
             'outgoing_enemy_damage_samples':target.get('dps',{}).get('allValues',[])}
            for target in output['encounterMetrics']['targets']]


def aliases(theta, prefix):
    dps,dot,scale,proc=map(float,theta)
    item=native_database()[12795]
    native_dps=(item['weaponDamageMin']+item['weaponDamageMax'])/(2*item['weaponSpeed'])
    return [define_alias(prefix+'_MH',12795,'main_hand',
            {'weapon_damage_scale':dps/native_dps,'periodic_damage_per_tick':dot}),
            define_alias(prefix+'_OH',19019,'off_hand',
            {'weapon_damage_scale':scale,'proc_damage':proc})]


def behavior_numerators(row,duration):
    channels=np.zeros(5)
    for key,action in row['actions'].items():
        match=re.search(r'(?:^|/)spellId:(\d+)(?:/|$)',key)
        spell=int(match.group(1)) if match else None
        group=(0 if 'otherId:OtherActionAttack' in key else 1 if spell==20662
               else 2 if spell in (1680,20569) else 3 if spell==23894 else 4)
        channels[group]+=action['damage']/duration
    gain=waste=0.
    for resource in row['resources']:
        if resource['type'] in ('ResourceTypeRage',3) and resource['gain']>0:
            gain+=resource['gain'];waste+=max(0.,resource['gain']-resource['actualGain'])
    return np.r_[channels,gain/duration,waste/duration]


def predict_model(model,theta):
    feature=np.r_[1.,np.asarray(theta,float)]
    numerators=feature@np.asarray(model['behavior_numerator_coefficients'])
    shares=numerators[:5]/numerators[:5].sum()
    behavior=np.r_[shares,numerators[5]/20.,numerators[6]/numerators[5] if numerators[5] else 0.]
    return {'utility_mean':float(feature@np.asarray(model['dps_coefficients'])),
            'dps_samples':feature@np.asarray(model['dps_sample_coefficients']),
            'behavior':behavior,'behavior_numerators':numerators}


def load_models(path=None):
    path=Path(path) if path else setup_paths()/'artifacts/decisive-value/FOUR_AXIS_CALIBRATION.json'
    result=json.loads(path.read_text())
    if not result['all_validations_pass']:raise ValueError('Native fixed-control calibration did not pass')
    return {(m['race'],m['task'],m['strategy']):m for m in result['models']}


def calibration(workers=32,resume=False):
    root=setup_paths();prior=root/'runs/r4-foundational-discovery/baseline-v1'
    source_cfg=prior/'source/configs/r4_ecosystems.yaml'
    cfg=yaml.safe_load(source_cfg.read_text())
    gear={**cfg['character']['base_equipment'],'main_hand':12795,'off_hand':19019,
          'trinket1':11815,'trinket2':13965}
    old=[(*mh,*oh) for mh in OLD_MH for oh in OLD_OH]
    points=ANCHORS+HELDOUT+old
    point_ids=[f'anchor_{i}' for i in range(5)]+[f'heldout_{i}' for i in range(2)]+[f'old_{i}' for i in range(4)]
    old_sources={'MH':[aliases((*mh,*OLD_OH[0]),f'old_mh_{i}')[0] for i,mh in enumerate(OLD_MH)],
                 'OH':[aliases((*OLD_MH[0],*oh),f'old_oh_{i}')[1] for i,oh in enumerate(OLD_OH)]}
    protocol={'study':'New two-slot four-amplitude native calibration; decision value studied on8 real tasks, not an extension of the R6 zero-gain sequence.',
        'phase':'development_calibration_only','race':'RaceHuman','tasks':cfg['tasks'],
        'strategies':cfg['strategies'],'task_weights':[.125]*8,
        'utility':'Native full-fight DPS; complete declared old gear and all3policies reoptimized.',
        'gain_threshold':.01,'gain_mass':.125,'fixed_cap_multiplier':1.05,
        'equipment_permission':'One alias per actual slot, fixed equipment throughout combat; no swap or controller asymmetry.',
        'base_gear':gear,'old_source_aliases':old_sources,'old_complete_cross':old,
        'theta_names':['mh_physical_dps','mh_dot_tick_damage','oh_physical_scale','oh_primary_nature_proc_damage'],
        'prospective_theta_bounds':BOUNDS,'fit_anchors':ANCHORS,'heldouts':HELDOUT,
        'old_crosses_are_validation_only':True,'seed':SEED,'iterations':ITERATIONS,
        'fixed_control':'Native1.3sTalon and nativeTFspeed, allPPM/tick counts/timing/stats/debuffs retained; TFproc axis alters primary hit only, zero-damage bounces unchanged.',
        'fit_basis':['1','mh_physical_dps','mh_dot_tick_damage','oh_physical_scale','oh_primary_nature_proc_damage'],
        'generic_comparison':'Same four features/anchors and native permissions imply identical generic affine predictions; no estimator advantage claimed.',
        'validation':'All6nonfit points per context: per-seedDPS≤1e-8,7 physical behavior numerator means≤1e-8, full aggregated action/resource/aura controls, incoming attack controls and first logged seed event schedule identical.',
        'behavior_scope':'Five action-channel DPS numerators plus rage gain/sec and waste/sec are affine candidates; normalized damage fractions are not claimed globally affine.',
        'new_future_designs':'No physical candidate calls or final independent confirmation in this calibration.'}
    jobs=[]
    for task in cfg['tasks']:
        for strategy in cfg['strategies']:
            base=make_input(gear,task,strategy,'RaceHuman',seed=SEED,iterations=ITERATIONS,cfg=cfg,debug=True)
            for index,(label,theta) in enumerate(zip(point_ids,points)):
                value=instantiate(base,aliases(theta,label),seed=SEED,iterations=ITERATIONS)
                jobs.append({'input':value,'meta':{'point_id':label,'point_index':index,'theta':list(theta),
                    'is_fit_anchor':index<5,'race':'RaceHuman','task':task['id'],
                    'strategy':strategy['id'],'gear_id':canonical_hash({'gear':gear,'theta':theta})[:16]}})
    run=run_jobs(jobs,'four-axis-calibration-v1',protocol,workers=workers,resume=resume,
        source_paths=[Path(__file__),SOURCE_ROOT/'src/wowfs/experiments/r4_native.py',
                      SOURCE_ROOT/'src/wowfs/experiments/r3_affine.py'],
        input_artifacts={'r4_frozen_config.yaml':source_cfg,'r4_frozen_domain.json':prior/'BASE_ECOSYSTEMS.json'})
    data=json.loads((run/'RESULTS.json').read_text());assert not data['errors']
    groups={}
    for row in data['rows']:groups.setdefault((row['race'],row['task'],row['strategy']),{})[row['point_index']]=row
    matrix=np.c_[np.ones(5),np.asarray(ANCHORS,float)]
    durations={t['id']:t['duration_seconds'] for t in cfg['tasks']};models=[];checks=[]
    for (race,task,strategy),cells in sorted(groups.items()):
        duration=durations[task]
        dps_fit=np.linalg.solve(matrix,np.array([cells[i]['dps_samples'] for i in range(5)]))
        num_fit=np.linalg.solve(matrix,np.array([behavior_numerators(cells[i],duration) for i in range(5)]))
        reference_raw=raw(cells[0])
        reference=canonical_hash(controls(reference_raw))
        incoming_reference=canonical_hash(incoming_controls(reference_raw))
        trace_reference=canonical_hash(trace_events(reference_raw['logs']))
        model={'race':race,'task':task,'strategy':strategy,'duration':duration,
            'dps_coefficients':dps_fit.mean(axis=1).tolist(),
            'dps_sample_coefficients':dps_fit.tolist(),
            'behavior_numerator_coefficients':num_fit.tolist(),
            'fit_anchor_cache_keys':[cells[i]['cache_key'] for i in range(5)],
            'reference_control_sha256':reference}
        models.append(model)
        for index,theta in enumerate(points):
            prediction=predict_model(model,theta);row=cells[index]
            output=raw(row);controls_sha=canonical_hash(controls(output))
            incoming_sha=canonical_hash(incoming_controls(output))
            trace_sha=canonical_hash(trace_events(output['logs']))
            checks.append({'race':race,'task':task,'strategy':strategy,'point_id':point_ids[index],
                'point_index':index,'theta':list(theta),'is_fit_anchor':index<5,
                'max_per_seed_dps_residual':float(np.max(abs(prediction['dps_samples']-np.asarray(row['dps_samples'])))),
                'max_behavior_numerator_residual':float(np.max(abs(prediction['behavior_numerators']-behavior_numerators(row,duration)))),
                'full_control_sha256':controls_sha,'aggregate_controls_identical':controls_sha==reference,
                'incoming_controls_identical':incoming_sha==incoming_reference,
                'first_seed_events_identical':trace_sha==trace_reference,
                'cache_key':row['cache_key']})
    held=[r for r in checks if not r['is_fit_anchor']]
    result={'schema':1,'run':str(run),'protocol':protocol,'models':models,'validation':checks,
        'native_cells':len(jobs),'physical_battles':len(jobs)*ITERATIONS,
        'prediction_models':len(models),'fit_native_cells':5*len(models),'heldout_native_cells':len(held),
        'heldout_per_seed_predictions':len(held)*ITERATIONS,
        'max_heldout_per_seed_dps_residual':max(c['max_per_seed_dps_residual'] for c in held),
        'max_heldout_behavior_numerator_residual':max(c['max_behavior_numerator_residual'] for c in held),
        'all_aggregate_controls_identical':all(c['aggregate_controls_identical'] for c in checks),
        'all_incoming_controls_identical':all(c['incoming_controls_identical'] for c in checks),
        'all_first_seed_events_identical':all(c['first_seed_events_identical'] for c in checks),
        'results_sha256':file_hash(run/'RESULTS.json')}
    result['all_validations_pass']=(result['max_heldout_per_seed_dps_residual']<=1e-8 and result['max_heldout_behavior_numerator_residual']<=1e-8 and result['all_aggregate_controls_identical'] and result['all_incoming_controls_identical'] and result['all_first_seed_events_identical'])
    atomic_json(run/'CALIBRATION.json',result)
    atomic_json(root/'artifacts/decisive-value/FOUR_AXIS_CALIBRATION.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('protocol','models','validation')},indent=2),flush=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--workers',type=int,default=32);parser.add_argument('--resume',action='store_true')
    args=parser.parse_args();calibration(args.workers,args.resume)
