"""Frozen matched completion ecologies, native baselines and prospective sequences."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
from wowfs.paths import SOURCE_ROOT,setup_paths,atomic_json
from wowfs.experiments.fc_native import contexts,run_jobs,STAGE
from wowfs.experiments.fc_calibration import stat_input,load_protocol,STAT_BY_CLASS
from wowfs.experiments.r2_native import file_hash

LARGE=[0.,.0001,.0002,.0003,.044]
DENSE=[0.,.011,.022,.033,.044]
PARTNERS=sorted(set(LARGE+DENSE))
# Each list is fixed before any sequence output. Primary values denote the
# added physical stat contribution in units U; old primary has contribution0.
PATHS={
 'large_gap':([.0537,.0637,.0737,.0837,.0937],LARGE,'power_only'),
 'dense':([.051,.061],DENSE,'power_only'),
 'weaker_direct':([.01,.02,.03,.04,.05],DENSE,'power_only'),
 'fixed_budget':([.054-j*.011/12 for j in range(4)],DENSE,'budget12'),
}
# Conservatively interior trajectories complement exact endpoint witnesses.
# Their thresholds/caps are identical; these are separate predeclared attempts.
GUARDED_PATHS={
 'large_gap_interior':([.0547,.0657,.0767,.0877],LARGE,'power_only'),
 'dense_interior':([.052],DENSE,'power_only'),
 'weaker_direct_interior':([.011,.022,.033,.044],DENSE,'power_only'),
 'fixed_budget_interior':([.0545,.0545-.011/12,.0545-.022/12],DENSE,'budget12'),
}


def ecology_design():
    root=setup_paths();path=root/'artifacts'/STAGE/'SCALAR_CALIBRATION.json'
    cal=json.loads(path.read_text());cfg=load_protocol();models={(m['context_id'],m['task']):m for m in cal['models']}
    check={c['context_id']:c for c in cal['context_checks']};rows=[]
    for c in contexts():
        coeff=np.array([models[c['context_id'],t['id']]['dps_coefficients'] for t in cfg['tasks']])
        if np.any(coeff[:,1]<=0):raise ValueError('Nonpositive slope requires explicit failed-context handling')
        unit=float(np.min(coeff[:,0]/coeff[:,1])/.956)
        rows.append({**c,'physical_stat':STAT_BY_CLASS[c['class']],'stat_unit':unit,
            'coefficients':coeff.tolist(),'binding_development_task':cfg['tasks'][int(np.argmin(coeff[:,0]/coeff[:,1]))]['id'],
            'affinity_development_validated':check[c['context_id']]['fixed_control_scalar_validated'],
            'original_native_calibration_check':check[c['context_id']],
            'large_partner_stats':[unit*x for x in LARGE],'dense_partner_stats':[unit*x for x in DENSE],
            'calibration_extrapolation_above500':.104*unit>500})
    return {'schema':1,'source_sha256':file_hash(Path(__file__)),'main_config_sha256':file_hash(SOURCE_ROOT/'configs/final_completion_capacity.json'),
        'calibration_sha256':file_hash(path),'tasks':cfg['tasks'],'large_gap':LARGE,'dense':DENSE,
        'same_count':5,'initial_primary_stat':0,'normalized_old_span':.044,'contexts':rows,
        'paths':{k:{'primary_coefficients':v[0],'partner_coefficients':v[1],'admission':v[2]} for k,v in (PATHS|GUARDED_PATHS).items()},
        'min_strong_primary_coefficient':.0502,'max_strong_primary_coefficient':.104,
        'blocked_probe_primary_coefficient':.104,
        'stat_unit_definition':'min_task(native_intercept/native_slope)/.956. Same physical partner endpoints and primary family in the matched pair.',
        'scope':'Old native completion spectra measured next; future capacity outcomes not yet opened. Original seven-dimensional WarriorD and cross-class physical channels are reported separately.'}


def baseline(workers=32,resume=False):
    root=setup_paths();out=root/'artifacts'/STAGE;dest=out/'MATCHED_DESIGN.json'
    design=ecology_design()
    if dest.exists():
        if json.loads(dest.read_text())!=design:raise ValueError('Frozen matched design differs')
    else:atomic_json(dest,design)
    jobs=[]
    for c in design['contexts']:
        for task in design['tasks']:
            for index,x in enumerate(PARTNERS):
                jobs.append({'input':stat_input(c,task,0.,x*c['stat_unit'],seed=810200001,iterations=128),
                    'meta':{k:c[k] for k in ('context_id','class','faction','race','race_label','native_racial_incomplete')}|
                    {'task':task['id'],'partner_coefficient':x,'partner_index':index,'primary_coefficient':0.,'stat_unit':c['stat_unit']}})
    science={'phase':'Old complete ecology measurement before final capacity predictions/future calls',
        'matched_design_sha256':file_hash(dest),'seed':810200001,'iterations':128,'partner_coefficients':PARTNERS,
        'old_ecologies':{'large_gap':LARGE,'dense':DENSE},'tasks':design['tasks'],
        'same_old_endpoint_native_input':'Both ecologies share the identical strongest old partner; all five choices are reoptimized.',
        'caps_next':'For each matched context use1.05 times the larger of the two fully optimized old task means; record mismatch rather than hiding it.'}
    return run_jobs(jobs,'old-ecologies-v1',science,workers=workers,resume=resume,
        source_paths=[Path(__file__),SOURCE_ROOT/'src/wowfs/experiments/fc_calibration.py',SOURCE_ROOT/'configs/final_completion_capacity.json'],
        input_artifacts={'MATCHED_DESIGN.json':dest,'SCALAR_CALIBRATION.json':out/'SCALAR_CALIBRATION.json','FROZEN_MAIN_PROTOCOL.json':out/'FROZEN_MAIN_PROTOCOL.json'})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['baseline']);p.add_argument('--workers',type=int,default=32);p.add_argument('--resume',action='store_true');a=p.parse_args()
    if a.phase=='baseline':print(baseline(a.workers,a.resume))
