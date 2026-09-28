"""One frozen independent full-cross confirmation of a research source catalog.

Preparation validates source identities, all legal combinations, historical
permissions, and the unchanged development caps before the first native call.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import yaml
from wowfs.paths import setup_paths, SOURCE_ROOT, atomic_json, canonical_hash
from wowfs.experiments.r2_native import file_hash
from wowfs.experiments.value_native import make_input, instantiate, run_jobs
from wowfs.experiments.value_affine import aliases, BOUNDS, OLD_MH, OLD_OH, predict_model

SEED=730000001
ITERATIONS=1024


def freeze_search_design():
    """Translate the root's completed development search without tuning it."""
    root=setup_paths();folder=root/'artifacts/decisive-value'
    search_path=folder/'CONSTRUCTIVE_SEARCH.json';search=json.loads(search_path.read_text())
    source_protocol=root/'runs/decisive-value/construction-search-v1/PROTOCOL.json'
    calibration_path=folder/'FOUR_AXIS_CALIBRATION.json';cal=json.loads(calibration_path.read_text())
    catalog={'schema':1,'frozen':True,'calibration_sha256':file_hash(calibration_path),
        'development_search_sha256':file_hash(search_path),
        'development_frozen_protocol_sha256':file_hash(source_protocol),
        'initial_source_ids':['MH0','MH1','OH0','OH1'],
        'source_catalog':{slot:[{'source_id':f'{slot}{i}','theta':theta,'old':i<2}
            for i,theta in enumerate(search['final_'+slot.lower()])] for slot in ['MH','OH']},
        'full_cross':[{'gear_id':f'MH{i}__OH{j}','mh_source_id':f'MH{i}','oh_source_id':f'OH{j}'}
            for i in range(len(search['final_mh'])) for j in range(len(search['final_oh']))],
        'fixed_scale':search['protocol']['scale'],'fixed_caps':search['protocol']['cap'],
        'rule_permissions':search['protocol']['admission_rule'],
        'sequences':[{'sequence_id':'frozen_three_round_constructive','steps':[
            {'step':r['round'],'released_source_ids':[f'MH{r["round"]+1}',f'OH{r["round"]+1}'],
             'admitted_gear_ids':[f'MH{i}__OH{j}' for i,j in r['admitted_pairs']],
             'frozen_development_metrics':r['metrics']} for r in search['rounds']]}],
        'metadata_erratum':'Search RESULTS/protocol.initial_mh/oh contain mutated final lists; the separately frozen construction-search-v1/PROTOCOL.json and calibration define the original first2+2 items. No executed search result is altered.',
        'confirmation_inference':{'bootstrap_seed':731000001,'paired_bootstrap_replicates':2000,
            'alpha':.05,'gain':'Reoptimize all admitted old/new gears and policies within every paired bootstrap sample. Also simultaneous approximate t bounds on all paired new-minus-old mean differences.',
            'scope':'One fixed independent confirmation; no outcome-dependent design, mask, cap, threshold, or sample-size adjustment.'}}
    destination=folder/'DESIGN.json'
    if destination.exists():
        if json.loads(destination.read_text())!=catalog:raise ValueError('Frozen DESIGN already exists and differs')
    else:atomic_json(destination,catalog)
    predictions=[]
    for gear in catalog['full_cross']:
        i=int(gear['mh_source_id'][2:]);j=int(gear['oh_source_id'][2:])
        theta=(*search['final_mh'][i],*search['final_oh'][j])
        for model in cal['models']:
            p=predict_model(model,theta)
            predictions.append({**gear,'theta':list(theta),'race':model['race'],
                'task':model['task'],'strategy':model['strategy'],
                'predicted_utility':p['utility_mean'],'predicted_behavior':p['behavior'].tolist()})
    atomic_json(folder/'DESIGN_PREDICTIONS.json',{'design_sha256':file_hash(destination),
        'calibration_sha256':file_hash(calibration_path),'rows':predictions})
    return destination


def prepare(catalog_path):
    root=setup_paths();catalog_path=Path(catalog_path)
    catalog=json.loads(catalog_path.read_text())
    calibration_path=root/'artifacts/decisive-value/FOUR_AXIS_CALIBRATION.json'
    calibration=json.loads(calibration_path.read_text())
    if not calibration['all_validations_pass']:raise ValueError('Calibration has not passed')
    if catalog['calibration_sha256']!=file_hash(calibration_path):
        raise ValueError('Catalog calibration provenance differs from frozen models')
    if not catalog.get('frozen'):raise ValueError('Catalog must be marked frozen before physical confirmation')
    sources=catalog['source_catalog'];maps={};all_ids=set();old_ids=set()
    for slot,bounds,old_parameters in [('MH',BOUNDS[:2],OLD_MH),('OH',BOUNDS[2:],OLD_OH)]:
        records=sources[slot];mapping={};parameters=set()
        for item in records:
            identity=item['source_id'];theta=tuple(map(float,item['theta']))
            if identity in all_ids or len(theta)!=2 or theta in parameters:
                raise ValueError('Source IDs and physical parameter identities must be distinct within slots')
            if not all(lo<=value<=hi for value,(lo,hi) in zip(theta,bounds)):
                raise ValueError('Confirmation candidate outside the frozen amplitude domain')
            mapping[identity]=item;parameters.add(theta);all_ids.add(identity)
            if item['old']:old_ids.add(identity)
        if {tuple(i['theta']) for i in records if i['old']}!=set(old_parameters):
            raise ValueError('The complete declared old source library changed')
        maps[slot]=mapping
    cross=catalog['full_cross'];pairs=set();gear_ids=set();gear_sources={}
    for gear in cross:
        pair=(gear['mh_source_id'],gear['oh_source_id']);gid=gear['gear_id']
        if pair in pairs or gid in gear_ids:raise ValueError('Duplicate full-cross cell or gear identity')
        if pair[0] not in maps['MH'] or pair[1] not in maps['OH']:raise ValueError('Unknown source in full cross')
        pairs.add(pair);gear_ids.add(gid);gear_sources[gid]=set(pair)
    if pairs!={(mh,oh) for mh in maps['MH'] for oh in maps['OH']}:
        raise ValueError('Physical confirmation must retain every old/new and new/new combination')
    initial_gears={g for g,ss in gear_sources.items() if ss<=old_ids}
    if len(initial_gears)!=4:raise ValueError('Exactly four old crosses are required')
    for sequence in catalog.get('sequences',[]):
        history=set(initial_gears);released=set(old_ids)
        for step in sequence['steps']:
            released.update(step['released_source_ids']);admitted=set(step['admitted_gear_ids'])
            if not released<=all_ids or not admitted<=gear_ids or not history<=admitted:
                raise ValueError('Sequence changes historical gear permission or references unknown sources')
            if any(not gear_sources[g]<=released for g in admitted):
                raise ValueError('Sequence admits an unreleased item')
            history=admitted
    science=calibration['protocol'];models=calibration['models']
    expected=[]
    for task in science['tasks']:
        expected.append(1.05*max(predict_model(m,(*mh,*oh))['utility_mean']
            for m in models if m['task']==task['id'] for mh in OLD_MH for oh in OLD_OH))
    if not np.allclose(catalog['fixed_caps'],expected,rtol=0,atol=1e-8):
        raise ValueError('Fixed development caps changed; independent confirmation cannot reanchor')
    cfg_path=root/'runs/decisive-value/four-axis-calibration-v1/inputs/r4_frozen_config.yaml'
    cfg=yaml.safe_load(cfg_path.read_text());jobs=[]
    for gear in cross:
        theta=tuple(maps['MH'][gear['mh_source_id']]['theta'])+tuple(maps['OH'][gear['oh_source_id']]['theta'])
        variants=aliases(theta,gear['gear_id'])
        variants[0]['research_alias']=gear['mh_source_id'];variants[1]['research_alias']=gear['oh_source_id']
        for task in science['tasks']:
            for strategy in science['strategies']:
                base=make_input(science['base_gear'],task,strategy,'RaceHuman',seed=SEED,
                                iterations=ITERATIONS,cfg=cfg,debug=False)
                value=instantiate(base,variants,seed=SEED,iterations=ITERATIONS,debug=False)
                jobs.append({'input':value,'meta':{'gear_id':gear['gear_id'],
                    'mh_source_id':gear['mh_source_id'],'oh_source_id':gear['oh_source_id'],
                    'theta':list(theta),'race':'RaceHuman','task':task['id'],'strategy':strategy['id'],
                    'initial':gear['gear_id'] in initial_gears}})
    protocol={'stage':'fixed_design_independent_confirmation','seed':SEED,'iterations':ITERATIONS,
        'candidate_catalog_sha256':file_hash(catalog_path),'calibration_sha256':file_hash(calibration_path),
        'tasks':science['tasks'],'strategies':science['strategies'],'task_weights':[.125]*8,
        'fixed_caps':catalog['fixed_caps'],'gain_threshold':.01,'gain_mass':.125,
        'physical_domain':'Complete research MH×OH source Cartesian product, including unsafe combinations; masks only affect later decisions.',
        'old_library':'All four declared old research crosses, all three policies; reoptimized independently for every task.',
        'sequence_designs_frozen':catalog.get('sequences',[]),'new_rule_permissions':catalog.get('rule_permissions'),
        'calibration_seed':720000001,'seed_independence':'730000001..730001024 disjoint from development; common random numbers across designs/tasks/policies.',
        'prediction_scope':'Development coefficients are predictions for new independent samples, not per-seed exact fits to this confirmation panel.',
        'physically_legal_research_designs':'Existing native12795MH/19019OH with distinct analysis aliases; no newly invented official item IDs.'}
    return jobs,protocol,{'frozen_catalog.json':catalog_path,'four_axis_calibration.json':calibration_path,
                         'r4_frozen_config.yaml':cfg_path,
                         'frozen_predictions.json':root/'artifacts/decisive-value/DESIGN_PREDICTIONS.json',
                         'construction_search.json':root/'artifacts/decisive-value/CONSTRUCTIVE_SEARCH.json',
                         'construction_protocol.json':root/'runs/decisive-value/construction-search-v1/PROTOCOL.json'}


def confirm(catalog_path,run_id='native-confirmation-v1',workers=32,resume=False):
    jobs,protocol,inputs=prepare(catalog_path)
    return run_jobs(jobs,run_id,protocol,workers=workers,resume=resume,
        source_paths=[Path(__file__),SOURCE_ROOT/'src/wowfs/experiments/value_affine.py',
                      SOURCE_ROOT/'src/wowfs/experiments/r4_native.py'],input_artifacts=inputs)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('catalog');parser.add_argument('--run-id',default='native-confirmation-v1')
    parser.add_argument('--workers',type=int,default=32);parser.add_argument('--resume',action='store_true')
    parser.add_argument('--prepare-only',action='store_true');args=parser.parse_args()
    if args.prepare_only:
        jobs,protocol,_=prepare(args.catalog)
        print(json.dumps({'native_calls':0,'planned_cells':len(jobs),'planned_battles':len(jobs)*ITERATIONS,
                          'jobs_sha256':canonical_hash(jobs),'protocol':protocol},indent=2))
    else:print(confirm(args.catalog,args.run_id,args.workers,args.resume))
