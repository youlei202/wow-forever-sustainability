"""All-context native total-stat calibration with prespecified held-out tests."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
from wowfs.paths import SOURCE_ROOT,setup_paths,atomic_json,canonical_hash
from wowfs.experiments.fc_native import contexts,presets,engine_root,make_input,run_jobs,validate_equipment,STAGE
from wowfs.experiments.r2_native import file_hash
from wowfs.experiments.r3_affine import raw,controls,trace_events

POINTS=[('fit_0',0.,0.),('fit_250',250.,0.),('held_100',100.,0.),('held_500',500.,0.),('allocation_250',125.,125.)]
CHANNELS=['owner_auto','owner_periodic','owner_direct_physical','owner_direct_other','pet_all']
STAT_BY_CLASS={c:('StatAttackPower' if c in ('Warrior','Rogue','Paladin') else 'StatRangedAttackPower' if c=='Hunter' else 'StatSpellPower') for c in presets()}


def load_protocol():
    return json.loads((SOURCE_ROOT/'configs/final_completion_capacity.json').read_text())


def stat_input(context,task,primary,partner,*,seed,iterations,debug=False):
    """Replace only the chosen absolute stat on existing neck/back base IDs."""
    value=make_input(context,task,seed=seed,iterations=iterations,debug=debug)
    items=value['request']['raid']['parties'][0]['players'][0]['equipment']['items']
    stat=STAT_BY_CLASS[context['class']]
    value['research_variants']=[{'item_id':items[i]['id'],'stats':{stat:float(amount)}} for i,amount in ((1,primary),(3,partner))]
    validate_equipment(value)
    return value


def all_controls(output):
    def unit(p):
        base=controls({'raidMetrics':{'parties':[{'players':[p]}]}})
        return {**base,'name':p['name'],'secondsOomAvg':p.get('secondsOomAvg'),
                'pets':sorted([unit(x) for x in p.get('pets',[])],key=lambda x:x['name'])}
    return unit(output['raidMetrics']['parties'][0]['players'][0])


def damage_channels(output,duration):
    n=output['iterationsDone']; channels=np.zeros(5)
    enemy_indices={t['unitIndex'] for t in output['encounterMetrics']['targets']}
    def unit(p,pet=False):
        for a in p['actions']:
            targets=[t for t in a['targets'] if t['unitIndex'] in enemy_indices]
            damage=sum(t['damage'] for t in targets)
            periodic=sum(t.get('tickDamage',0) for t in targets)
            if pet: channels[4]+=damage
            elif a['id'].get('otherId') in ('OtherActionAttack','OtherActionShoot',1,2): channels[0]+=damage
            else:
                channels[1]+=periodic
                channels[2 if a.get('spellSchool')==2 else 3]+=damage-periodic
        for p2 in p.get('pets',[]):unit(p2,True)
    unit(output['raidMetrics']['parties'][0]['players'][0])
    return channels/(n*duration)


def resource_rates(output,duration):
    n=output['iterationsDone']; rows={}
    def unit(p,kind):
        for r in p.get('resources',[]):
            key=kind+':'+str(r['type']); item=rows.setdefault(key,{'positive_gain':0.,'waste':0.,'spent':0.,'events':0.})
            item['positive_gain']+=max(0,r['gain']);item['waste']+=max(0,r['gain']-r['actualGain'])
            item['spent']+=max(0,-r['actualGain']);item['events']+=r['events']
        for pet in p.get('pets',[]):unit(pet,'pet:'+pet['name'])
    unit(output['raidMetrics']['parties'][0]['players'][0],'owner')
    return {k:{m:v/(n*duration) for m,v in row.items()} for k,row in sorted(rows.items())}


def fit_and_check(run):
    data=json.loads((run/'RESULTS.json').read_text());protocol=json.loads((run/'PROTOCOL.json').read_text())
    cfg=protocol['science']['main_protocol']; durations={t['id']:t['duration'] for t in cfg['tasks']}
    groups={}
    for row in data['rows']:groups.setdefault((row['context_id'],row['task']),{})[row['point_id']]=row
    models=[];checks=[]
    for (context,task),cells in sorted(groups.items()):
        a=np.array(cells['fit_0']['dps_samples']);b=(np.array(cells['fit_250']['dps_samples'])-a)/250.
        outputs={key:raw(row) for key,row in cells.items()}
        nums={key:damage_channels(out,durations[task]) for key,out in outputs.items()}
        num_a=nums['fit_0'];num_b=(nums['fit_250']-num_a)/250.
        ref=canonical_hash(all_controls(outputs['fit_0']))
        trace=canonical_hash(trace_events(outputs['fit_0'].get('logs','')))
        for point,x,y in POINTS:
            row=cells[point];output=outputs[point];controls_sha=canonical_hash(all_controls(output))
            checks.append({'context_id':context,'class':row['class'],'race':row['race'],'task':task,'point_id':point,
                'is_fit':point.startswith('fit_'),'stat_total':x+y,
                'max_per_seed_dps_residual':float(np.max(abs(np.asarray(row['dps_samples'])-(a+b*(x+y))))),
                'max_damage_channel_residual':float(np.max(abs(nums[point]-(num_a+num_b*(x+y))))),
                'aggregate_controls_identical':controls_sha==ref,
                'first_seed_events_identical':canonical_hash(trace_events(output.get('logs','')))==trace,
                'control_sha256':controls_sha,'mean_dps':row['dps_mean'],
                'damage_channels':nums[point].tolist(),'resource_rates':resource_rates(output,durations[task]),
                'damage_channel_total_residual':float(abs(nums[point].sum()-row['dps_mean'])),
                'cache_directory':row['cache_directory'],'cache_key':row['cache_key']})
        models.append({k:cells['fit_0'][k] for k in ('context_id','class','faction','race','native_racial_incomplete','strategy')} | {
            'task':task,'stat':cells['fit_0']['stat'],'dps_coefficients':[float(a.mean()),float(b.mean())],
            'dps_sample_coefficients':[a.tolist(),b.tolist()],
            'damage_channel_coefficients':[num_a.tolist(),num_b.tolist()],
            'anchor_cache_directories':[cells[p]['cache_directory'] for p in ('fit_0','fit_250')],
            'anchor_input_paths':[str(Path(cells[p]['cache_directory'])/'input.json') for p in ('fit_0','fit_250')]})
    context_checks=[]
    for c in contexts():
        selected=[r for r in checks if r['context_id']==c['context_id']];held=[r for r in selected if not r['is_fit']]
        ms=[m for m in models if m['context_id']==c['context_id']]
        positive=all(m['dps_coefficients'][1]>0 for m in ms)
        residual=max(x['max_per_seed_dps_residual'] for x in held)
        channels=max(x['max_damage_channel_residual'] for x in held)
        same=all(x['aggregate_controls_identical'] for x in selected)
        allocation=[x for x in held if x['point_id']=='allocation_250']
        direct_equal=max(float(np.max(np.abs(np.asarray(groups[(c['context_id'],t)]['allocation_250']['dps_samples'])-
                    np.asarray(groups[(c['context_id'],t)]['fit_250']['dps_samples'])))) for t in durations)
        context_checks.append({**c,'tasks_tested':len(ms),'heldout_cells':len(held),
            'max_per_seed_residual':residual,'max_damage_channel_residual':channels,
            'all_aggregate_controls_identical':same,
            'all_first_seed_events_identical':all(x['first_seed_events_identical'] for x in selected),
            'allocation_dps_identical_1e_8':direct_equal<=1e-8,'allocation_max_per_seed_residual':direct_equal,
            'all_positive_slopes':positive,'scalar_affinity_validated_1e_8':residual<=1e-8 and channels<=1e-8,
            'fixed_control_scalar_validated':residual<=1e-8 and channels<=1e-8 and same and positive,
            'min_intercept_over_slope':min(m['dps_coefficients'][0]/m['dps_coefficients'][1] for m in ms) if positive else None,
            'scope':'Finite seed/point validation, not a proof over every future parameter or native state.'})
    result={'schema':1,'run':str(run),'protocol_sha256':file_hash(run/'PROTOCOL.json'),'results_sha256':file_hash(run/'RESULTS.json'),
        'models':models,'context_checks':context_checks,'checks':checks,'damage_channels':CHANNELS,
        'fit_points':[0,250],'validation_points':[100,500],'allocation_validation':[125,125],
        'models_count':len(models),'cells':len(data['rows']),'physical_battles':sum(r['iterations'] for r in data['rows']),
        'fixed_control_contexts':sum(c['fixed_control_scalar_validated'] for c in context_checks),
        'affine_contexts':sum(c['scalar_affinity_validated_1e_8'] for c in context_checks),
        'allocation_equivalent_contexts':sum(c['allocation_dps_identical_1e_8'] for c in context_checks),
        'max_damage_partition_residual':max(c['damage_channel_total_residual'] for c in checks),
        'behavior_scope':'New cross-class physical damage partition plus separately typed resource rates; not a relabeling of the original Warrior-specific seven coordinates.'}
    # v1 retained in the physical run. This separate read-only analysis revision
    # excludes friendly/self damage from utility channels, matching native DPS.
    analysis=setup_paths()/'runs'/STAGE/'scalar-calibration-analysis-v2'
    source_sha=file_hash(Path(__file__))
    result['analysis_revision']='v2_enemy_targets_only'
    result['analysis_source_sha256']=source_sha
    result['analysis_run']=str(analysis)
    atomic_json(analysis/'PROTOCOL.json',{'analysis_only':True,'native_calls':0,'source_sha256':source_sha,
        'physical_results_sha256':result['results_sha256'],
        'correction':'Filter action damage to native enemy target unit indices; Undead racial self-damage belongs to no utility damage channel. No utility fits/physics changed.'})
    (analysis/'fc_calibration.py').write_text(Path(__file__).read_text())
    atomic_json(analysis/'CALIBRATION.json',result);atomic_json(setup_paths()/'artifacts'/STAGE/'SCALAR_CALIBRATION.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('models','checks','context_checks')},indent=2),flush=True)
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=64);p.add_argument('--resume',action='store_true');p.add_argument('--analyze-only',action='store_true');a=p.parse_args()
    run=setup_paths()/'runs'/STAGE/'scalar-calibration-v1'
    if a.analyze_only:fit_and_check(run);return
    cfg=load_protocol();jobs=[]
    for c in contexts():
        for task in cfg['tasks']:
            for point,x,y in POINTS:
                jobs.append({'input':stat_input(c,task,x,y,seed=810100001,iterations=64,debug=True),
                    'meta':{**c,'task':task['id'],'strategy':presets()[c['class']]['apl'],'point_id':point,
                        'stat':STAT_BY_CLASS[c['class']],'primary_stat':x,'partner_stat':y}})
    inputs={p[k]:engine_root()/p[k] for p in presets().values() for k in ('gear','apl')}
    inputs['FROZEN_MAIN_PROTOCOL.json']=setup_paths()/'artifacts'/STAGE/'FROZEN_MAIN_PROTOCOL.json'
    science={'purpose':'Prespecified native primary-stat calibration and allocation validation, not a capacity outcome.',
        'main_protocol':cfg,'stat_by_class':STAT_BY_CLASS,'variable_slots':['neck','back'],'points':POINTS,
        'fit_points':[0,250],'heldout_points':[100,500],'allocation_holdout':[125,125],
        'iterations':64,'seed':810100001,'pet_metrics':'Recursive controls, damage channels and resource rates include all native pets.',
        'validation':'Per-seed DPS and mean physical damage channels residual tolerance1e-8; aggregate controls/first trace exact; failures retained percontext.',
        'preserves_equipment_entries':'Only research_variants stat fields supplied; native IDs, other stats, enchants, APL, options remain unchanged.'}
    run=run_jobs(jobs,'scalar-calibration-v1',science,workers=a.workers,resume=a.resume,
        source_paths=[Path(__file__),SOURCE_ROOT/'src/wowfs/experiments/r3_affine.py',
            SOURCE_ROOT/'configs/final_completion_capacity.json',SOURCE_ROOT/'configs/fc_presets.json',SOURCE_ROOT/'configs/official_contexts.yaml'],input_artifacts=inputs)
    fit_and_check(run)


if __name__=='__main__':main()
