"""Frozen affine calibration and genuinely held-out native transfer diagnostics.

API: load_models() maps model_key(race, speed, offhand, trinket1, trinket2,
 task, strategy) tuples to model dictionaries. predict_model returns a dictionary
 with mean, standard_error, and paired_seed_values (a NumPy array).
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import numpy as np
from wowfs.paths import setup_paths, atomic_json, canonical_hash
from wowfs.experiments.r3_native import r2_witness_inputs, run_jobs
from wowfs.experiments.r3_affine import make_amplitude_input, raw, controls

CALIBRATION_SEED=309242001
FRESH_SEED=309243001
ITERATIONS=128
SPEEDS=[1.0,1.3,1.9]
PROFILES=[(offhand,11815,trinket2) for offhand in [12590,19019] for trinket2 in [13965,20130]]
ANCHORS=[(24.,0.),(54.,0.),(24.,30.)]
KEY_FIELDS=['race','weapon_speed','offhand','trinket1','trinket2','task','strategy']


def model_key(race, weapon_speed, offhand, trinket1, trinket2, task, strategy):
    return (str(race),float(weapon_speed),int(offhand),int(trinket1),int(trinket2),str(task),str(strategy))


def key_from_row(row):
    return model_key(*(row[k] for k in KEY_FIELDS))


def load_models(path=None):
    path=Path(path) if path else setup_paths()/'artifacts/r3-gold/AFFINE_CALIBRATION.json'
    return {key_from_row(row):row for row in json.loads(path.read_text())['models']}


def predict_model(model, dps, dot):
    features=np.array([1.,float(dps)-24.,float(dot)])
    values=np.asarray(model['seed_coefficients']) @ features
    variance=float(features @ np.asarray(model['per_seed_coefficient_covariance']) @ features)
    return {'mean':float(np.asarray(model['mean_coefficients']) @ features),
            'standard_error':float(np.sqrt(max(0.,variance)/model['iterations'])),
            'paired_seed_values':values}


def freeze_design():
    root=setup_paths();path=root/'artifacts/r3-gold/FROZEN_AFFINE_TRANSFER_DESIGN.json'
    rng=np.random.default_rng(309242019)
    points=[{'variant_index':i,'base_dps':float(rng.uniform(26,50)),
             'dot_damage':float(rng.uniform(2,28)),'weapon_speed':SPEEDS[i%3]} for i in range(32)]
    design={'schema':1,'generation_seed':309242019,'parameter_items':points,
        'calibration':{'seed_start':CALIBRATION_SEED,'iterations':ITERATIONS,'anchors':ANCHORS,
            'speeds':SPEEDS,'profiles':PROFILES,'contexts':'Both Human and Orc; all four tasks and three native policies',
            'models':288,'features':['1','base_dps-24','dot_damage']},
        'same_control_transfer':{'items':32,'contexts_per_item':96,'logical_cells':3072,
            'seed_start':CALIBRATION_SEED,'purpose':'Paired-seed structural diagnostic; not independent mean validation.'},
        'fresh_mean_transfer':{'items':32,'contexts_per_item':8,'logical_cells':256,
            'seed_start':FRESH_SEED,'speed':1.3,'offhand':19019,'trinkets':[11815,13965],
            'policy':'native_reck','purpose':'Independent seed panel; uncertainty combines calibration and evaluation variances.'},
        'control_shift_transfer':{'items':'first 8 predetermined parameter items','contexts_per_item':8,
            'shifts':[{'weapon_speed':1.45},{'weapon_speed':1.75},{'weapon_speed':2.35},{'proc_ppm':.7},{'proc_ppm':1.6}],
            'logical_cells':320,'seed_start':CALIBRATION_SEED,
            'predictor':'Frozen speed=1.3, PPM=1 canonical model; explicitly outside supported control kernel.'},
        'resource_context_transfer':{'items':'first 8 predetermined parameter items','contexts_per_item':8,
            'trinkets':[19951,13965],'logical_cells':64,'seed_start':CALIBRATION_SEED,
            'predictor':'Frozen [11815,13965] canonical model; Gri lek is native and known in R2, absent from these calibration contexts.'},
        'comparison':'Generic linear estimator receives identical features, anchors and seed observations; its predictions and decisions are exactly identical.',
        'complexity':'288 context-specific affine rows, each 3 coefficients. Fixed palette complexity is independent of number of amplitude items; new control kernels can require new rows.',
        'certification':'Finite native empirical prediction only. No global game cap, unseen class coverage, or distribution-free upper bound is inferred.',
        'pass_tolerance_per_seed_dps':1e-8}
    if path.exists():
        old=json.loads(path.read_text());assert old['design']==json.loads(json.dumps(design)),'frozen transfer design mismatch'
        return old
    value={'utc':datetime.now(timezone.utc).isoformat(),'design_sha256':canonical_hash(design),'design':design}
    atomic_json(path,value);return value


def contexts():
    return {(race,task,strategy):value for (gear,race,task,strategy),value in r2_witness_inputs().items()
            if gear=='5ae0e1e5d00fbdb1'}


def calibrate(workers=64,resume=False):
    root=setup_paths();design=freeze_design();jobs=[]
    for (race,task,strategy),base in contexts().items():
        for speed in SPEEDS:
            for offhand,t1,t2 in PROFILES:
                for anchor,(dps,dot) in enumerate(ANCHORS):
                    meta=dict(zip(KEY_FIELDS,(race,speed,offhand,t1,t2,task,strategy)))
                    meta.update(anchor=anchor,base_dps=dps,dot_damage=dot)
                    jobs.append({'input':make_amplitude_input(base,dps,dot,speed,offhand,(t1,t2),CALIBRATION_SEED,ITERATIONS),'meta':meta})
    protocol={'frozen_transfer_design':design,'purpose':'Fit fixed-control reward coefficients before prospective sequence outcomes.',
              'seed_start':CALIBRATION_SEED,'iterations':ITERATIONS,'generic_comparison':'Identical same-feature estimator; no claimed advantage.'}
    run=run_jobs(jobs,'affine-calibration-v1',root/'envs/r3-go/wowfs-native-variants',protocol,workers,resume)
    rows=json.loads((run/'RESULTS.json').read_text())['rows'];groups={}
    for row in rows:groups.setdefault(key_from_row(row),{})[row['anchor']]=row
    models=[]
    for key,anchors in sorted(groups.items()):
        values=[np.asarray(anchors[i]['dps_samples']) for i in range(3)]
        coefficients=np.column_stack([values[0],(values[1]-values[0])/30.,(values[2]-values[0])/30.])
        hashes=[canonical_hash(controls(raw(anchors[i]))) for i in range(3)]
        model=dict(zip(KEY_FIELDS,key));model.update(iterations=ITERATIONS,seed_start=CALIBRATION_SEED,
            mean_coefficients=coefficients.mean(axis=0).tolist(),
            per_seed_coefficient_covariance=np.cov(coefficients,rowvar=False,ddof=1).tolist(),
            seed_coefficients=coefficients.tolist(),anchor_control_hashes=hashes,
            anchor_controls_identical=len(set(hashes))==1,
            anchors=[{'base_dps':ANCHORS[i][0],'dot_damage':ANCHORS[i][1],
                'cache_key':anchors[i]['cache_key'],'cache_directory':anchors[i]['cache_directory']} for i in range(3)])
        models.append(model)
    result={'schema':1,'seed_start':CALIBRATION_SEED,'iterations':ITERATIONS,
        'features':['1','base_dps-24','dot_damage'],'key_fields':KEY_FIELDS,
        'calibration_run':str(run),'frozen_transfer_design_sha256':design['design_sha256'],
        'models':models,'all_anchor_control_metrics_identical':all(m['anchor_controls_identical'] for m in models),
        'logical_cells':len(jobs),'requested_battles':len(jobs)*ITERATIONS,
        'scope':'Coefficients estimated from 128 matched seeds; covariance is per-seed, divide by n for mean uncertainty.'}
    atomic_json(run/'AFFINE_CALIBRATION.json',result);atomic_json(root/'artifacts/r3-gold/AFFINE_CALIBRATION.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='models'}),flush=True);return result


def transfer(workers=64,resume=False):
    root=setup_paths();frozen=freeze_design();models=load_models();jobs=[]
    for (race,task,strategy),base in contexts().items():
        for point in frozen['design']['parameter_items']:
            for offhand,t1,t2 in PROFILES:
                speed=point['weapon_speed'];meta=dict(zip(KEY_FIELDS,(race,speed,offhand,t1,t2,task,strategy)))
                meta.update(point,panel='same_control',predictor_speed=speed,predictor_trinket1=t1)
                jobs.append({'input':make_amplitude_input(base,point['base_dps'],point['dot_damage'],speed,offhand,(t1,t2),CALIBRATION_SEED,ITERATIONS),'meta':meta})
            if strategy!='native_reck':continue
            meta=dict(zip(KEY_FIELDS,(race,1.3,19019,11815,13965,task,strategy)))
            meta.update(variant_index=point['variant_index'],base_dps=point['base_dps'],dot_damage=point['dot_damage'],
                panel='fresh_mean',predictor_speed=1.3,predictor_trinket1=11815)
            jobs.append({'input':make_amplitude_input(base,point['base_dps'],point['dot_damage'],1.3,19019,(11815,13965),FRESH_SEED,ITERATIONS),'meta':meta})
            if point['variant_index']>=8:continue
            for shift in frozen['design']['control_shift_transfer']['shifts']:
                speed=shift.get('weapon_speed',1.3)
                value=make_amplitude_input(base,point['base_dps'],point['dot_damage'],speed,19019,(11815,13965),CALIBRATION_SEED,ITERATIONS)
                if 'proc_ppm' in shift:value['research_variants'][0]['proc_ppm']=shift['proc_ppm']
                jobs.append({'input':value,'meta':{**meta,'panel':'control_shift','weapon_speed':speed,'shift':shift}})
            value=make_amplitude_input(base,point['base_dps'],point['dot_damage'],1.3,19019,(19951,13965),CALIBRATION_SEED,ITERATIONS)
            jobs.append({'input':value,'meta':{**meta,'panel':'resource_context','trinket1':19951}})
    protocol={'frozen_transfer_design':frozen,'calibration_sha256':canonical_hash(json.loads((root/'artifacts/r3-gold/AFFINE_CALIBRATION.json').read_text())),
        'classification':'Supported same-control and fresh-mean panels; control-shift and resource panels flagged outside calibrated support before outcomes.',
        'no_refit':True,'generic_same_feature_comparator':'Exactly identical predictor.'}
    run=run_jobs(jobs,'affine-transfer-v1',root/'envs/r3-go/wowfs-native-variants',protocol,workers,resume)
    source_rows=json.loads((run/'RESULTS.json').read_text())['rows'];rows=[]
    for source in source_rows:
        key=model_key(source['race'],source['predictor_speed'],source['offhand'],source['predictor_trinket1'],source['trinket2'],source['task'],source['strategy'])
        model=models[key];pred=predict_model(model,source['base_dps'],source['dot_damage']);observed=np.asarray(source['dps_samples'])
        residual=observed-pred['paired_seed_values'];mean_error=float(observed.mean()-pred['mean'])
        independent=source['panel']=='fresh_mean'
        error_se=float(np.sqrt(pred['standard_error']**2+observed.var(ddof=1)/ITERATIONS)) if independent else float(residual.std(ddof=1)/np.sqrt(ITERATIONS))
        supported=source['panel'] in ('same_control','fresh_mean')
        same_controls=canonical_hash(controls(raw(source)))==model['anchor_control_hashes'][0] if not independent else None
        rows.append({**{k:source[k] for k in KEY_FIELDS},'variant_index':source['variant_index'],'base_dps':source['base_dps'],
            'dot_damage':source['dot_damage'],'panel':source['panel'],'shift':source.get('shift'),
            'inside_calibrated_control_support':supported,'predicted_mean':pred['mean'],'observed_mean':float(observed.mean()),
            'mean_error':mean_error,'mean_error_standard_error':error_se,
            'approximate_95pct_mean_error_interval':[mean_error-1.96*error_se,mean_error+1.96*error_se],
            'max_absolute_paired_seed_residual':None if independent else float(np.max(np.abs(residual))),
            'aggregate_control_metrics_identical':same_controls,'cache_key':source['cache_key'],
            'same_feature_generic_prediction_difference':0.})
    panels={}
    for name in sorted({r['panel'] for r in rows}):
        selected=[r for r in rows if r['panel']==name]
        panels[name]={'cells':len(selected),'max_absolute_mean_error':max(abs(r['mean_error']) for r in selected),
            'mean_absolute_mean_error':float(np.mean([abs(r['mean_error']) for r in selected])),
            'max_absolute_paired_seed_residual':max((r['max_absolute_paired_seed_residual'] for r in selected if r['max_absolute_paired_seed_residual'] is not None),default=None),
            'aggregate_control_metric_comparison_applicable':name!='fresh_mean',
            'nonidentical_aggregate_controls':None if name=='fresh_mean' else sum(r['aggregate_control_metrics_identical'] is False for r in selected),
            'interval_containment_applicable':name!='same_control',
            'pointwise_approximate_95pct_intervals_containing_zero':None if name=='same_control' else sum(r['approximate_95pct_mean_error_interval'][0]<=0<=r['approximate_95pct_mean_error_interval'][1] for r in selected)}
    result={'schema':1,'frozen_design_sha256':frozen['design_sha256'],'panels':panels,'rows':rows,
        'same_feature_generic_comparator':'Identical predictions; no model-class superiority.',
        'interval_scope':'Normal approximations, pointwise and correlated; not simultaneous or distribution-free cap certificates.',
        'supported_structural_pass':panels['same_control']['max_absolute_paired_seed_residual']<=1e-8,
        'logical_cells':len(jobs),'requested_battles':len(jobs)*ITERATIONS}
    atomic_json(run/'AFFINE_TRANSFER.json',result);atomic_json(root/'artifacts/r3-gold/AFFINE_TRANSFER.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2),flush=True);return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['freeze','calibrate','transfer'])
    parser.add_argument('--workers',type=int,default=64);parser.add_argument('--resume',action='store_true');args=parser.parse_args()
    if args.phase=='freeze':print(json.dumps(freeze_design(),indent=2))
    elif args.phase=='calibrate':calibrate(args.workers,args.resume)
    else:transfer(args.workers,args.resume)

if __name__=='__main__':main()
