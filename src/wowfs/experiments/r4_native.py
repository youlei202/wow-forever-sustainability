"""Complete small native R4 equipment domains, immutable shared combat tables."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
from copy import deepcopy
from datetime import datetime,timezone
import gzip
import itertools
import json
from pathlib import Path
import shutil
import yaml
from wowfs.paths import SOURCE_ROOT,setup_paths,atomic_json,canonical_hash
from wowfs.experiments.r2_native import SLOTS,TYPES,file_hash,make_input as old_make_input,execute_job

STAGE='r4-foundational-discovery'


def load_config():return yaml.safe_load((SOURCE_ROOT/'configs/r4_ecosystems.yaml').read_text())


def engine_root():return setup_paths()/'external/mythicsim-forever-engine-r3-variants'


def legality(gear,database):
    ids=list(gear.values())
    for slot,typ in zip(SLOTS,TYPES):
        item=database.get(gear[slot])
        if item is None:return 'missing_native_item:'+str(gear[slot])
        if item['type']!=typ:return 'wrong_slot:'+slot
        if item.get('unique') and ids.count(item['id'])>1:return 'duplicate_unique:'+str(item['id'])
        if item.get('classAllowlist') and 9 not in item['classAllowlist']:return 'class_not_warrior:'+str(item['id'])
        if slot=='main_hand' and item.get('handType') not in (1,2):return 'illegal_main_hand'
        if slot=='off_hand' and item.get('handType') not in (2,3):return 'illegal_off_hand'
        if slot in ('main_hand','off_hand') and item.get('weaponType',0)==0:return 'non_melee_weapon'
    return None


def enumerate_ecosystems(cfg=None):
    cfg=cfg or load_config();database={x['id']:x for x in json.loads((engine_root()/'assets/database/db.json').read_text())['items']}
    gears={};ecosystems=[];excluded=[]
    for pool in cfg['pools']:
        slots=list(pool['slots']);initial=[];terminal=[];memberships={}
        old=set(i for choices in pool['slots'].values() for i in choices[:2]);new=set(i for choices in pool['slots'].values() for i in choices[2:])
        if old&new:raise ValueError('ambiguous old/new item identity in '+pool['id'])
        for choices in itertools.product(*pool['slots'].values()):
            gear=dict(cfg['character']['base_equipment']);gear.update(pool.get('fixed',{}));gear.update(zip(slots,choices))
            why=legality(gear,database)
            if why:excluded.append({'pool':pool['id'],'gear':gear,'reason':why});continue
            key=canonical_hash(gear)[:16];record=gears.setdefault(key,{'gear_id':key,'gear':gear,'pools':[]})
            record['pools'].append(pool['id']);terminal.append(key);memberships[key]=sorted(set(choices))
            if all(i in pool['slots'][s][:2] for s,i in zip(slots,choices)):initial.append(key)
        if len(initial)!=16:raise ValueError('initial domain is not all16 legal combinations: '+pool['id'])
        ecosystems.append({**pool,'initial_gear_ids':initial,'terminal_gear_ids':terminal,
            'old_source_ids':sorted(old),'new_source_ids':sorted(new),'source_ids_by_gear':memberships,
            'raw_terminal_count':int(__import__('math').prod(map(len,pool['slots'].values()))),
            'legal_terminal_count':len(terminal),'initial_count':len(initial)})
    allids=sorted(set(i for g in gears.values() for i in g['gear'].values()))
    for family in cfg['candidate_design_families']:
        if not set(family['item_ids'])<=set(allids):raise ValueError('family representatives not in domain:'+family['id'])
    return {'schema':1,'scope':cfg['ecology_scope'],'ecosystems':ecosystems,'gears':gears,'excluded':excluded,
        'tasks':cfg['tasks'],'strategies':cfg['strategies'],'races':cfg['races'],'metrics':cfg['metrics'],
        'candidate_design_families':cfg['candidate_design_families'],
        'item_metadata':{str(i):{k:database[i].get(k) for k in ['id','name','type','handType','weaponType','classAllowlist','unique','setName','setId','sources']} for i in allids}}


def make_input(gear,task,strategy,race,seed=409240001,iterations=16,cfg=None,disabled=(),debug=False):
    cfg=cfg or load_config();root=setup_paths()
    template=json.loads((root/'runs/r2-discovery/native-smoke/effect.input.json').read_text())
    value=old_make_input(template,cfg,gear,task,strategy,engine_root(),race,seed,iterations,disabled,debug)
    player=value['request']['raid']['parties'][0]['players'][0]
    player['inFrontOfTarget']=False
    value['request']['raid']['tanks']=[]
    if 'starting_rage' in task:player['warrior']['options']['startingRage']=task['starting_rage']
    if 'incoming' in task:
        incoming=task['incoming'];value['request']['raid']['tanks']=[{'type':'Player','index':0}]
        player['inFrontOfTarget']=incoming.get('in_front',True)
        for target in value['request']['encounter']['targets']:
            target.update(tankIndex=0,minBaseDamage=incoming['min_base_damage'],swingSpeed=incoming['swing_speed'],
                damageSpread=incoming.get('damage_spread',0),spellSchool=incoming.get('spell_school','SpellSchoolPhysical'))
    for target in value['request']['encounter']['targets']:
        if 'mob_type' in task:target['mobType']=task['mob_type']
        for index,value_stat in task.get('resistance_stats',{}).items():target['stats'][int(index)]=value_stat
    return value


def prepare(cfg=None,tasks=None,pool_ids=None,seed=None,iterations=None,races=None):
    cfg=deepcopy(cfg or load_config());ecology=enumerate_ecosystems(cfg)
    selected=set(pool_ids or [p['id'] for p in ecology['ecosystems']]);gears={k:g for k,g in ecology['gears'].items() if selected.intersection(g['pools'])}
    tasks=tasks or cfg['tasks'];races=races or cfg['races'];seed=seed if seed is not None else cfg['sampling']['seed_start'];iterations=iterations or cfg['sampling']['iterations']
    jobs=[]
    for record,task,strategy,race in itertools.product(gears.values(),tasks,cfg['strategies'],races):
        jobs.append({'input':make_input(record['gear'],task,strategy,race,seed,iterations,cfg),
            'meta':{'gear_id':record['gear_id'],'pools':record['pools'],'race':race,'task':task['id'],'strategy':strategy['id'],'world':'native','stage':'complete_ecology'}})
    return jobs,ecology


def dispatch(job,binary,binary_hash,root):
    key=canonical_hash({'binary':binary_hash,'input':job['input']})
    for stage in [STAGE,'r3-gold','r2-discovery']:
        folder=root/'cache'/stage/'native'/key[:2]/key
        if (folder/'summary.json').exists():
            summary=json.loads((folder/'summary.json').read_text())
            return {**job['meta'],**summary,'cache_key':key,'cache_hit':True,'cache_origin':stage,'cache_directory':str(folder)}
    summary=execute_job(job,binary,binary_hash,root/'cache'/STAGE/'native')
    return {**summary,'cache_origin':STAGE,'cache_directory':str(root/'cache'/STAGE/'native'/key[:2]/key)}


def run_jobs(jobs,run_id,binary=None,scientific_protocol=None,workers=64,resume=False):
    root=setup_paths();run=root/'runs'/STAGE/run_id;binary=Path(binary) if binary else root/'envs/r2-go/wowfs-native';bh=file_hash(binary)
    sources=[SOURCE_ROOT/'src/wowfs/experiments/r4_native.py',SOURCE_ROOT/'src/wowfs/experiments/r2_native.py',SOURCE_ROOT/'configs/r4_ecosystems.yaml']
    protocol={'schema':1,'binary_sha256':bh,'jobs_sha256':canonical_hash(jobs),'science':scientific_protocol or {},
        'logical_cells':len(jobs),'requested_battles':sum(j['input']['request']['simOptions']['iterations'] for j in jobs),
        'source_hashes':{str(p.relative_to(SOURCE_ROOT)):file_hash(p) for p in sources},'randomization':'native labeled RNG seed+i; matched seeds across equipment/tasks/strategies/races; not independent ecosystem samples'}
    if (run/'PROTOCOL.json').exists():
        if not resume or json.loads((run/'PROTOCOL.json').read_text())!=protocol:raise ValueError('resume requires exact frozen inputs, source, science, binary')
        if (run/'PROGRESS.json').exists() and json.loads((run/'PROGRESS.json').read_text())['status']=='complete':return run
    else:
        run.mkdir(parents=True,exist_ok=True);atomic_json(run/'PROTOCOL.json',protocol);atomic_json(run/'JOBS.json',jobs)
        atomic_json(run/'FREEZE_TIME.json',{'utc':datetime.now(timezone.utc).isoformat()});shutil.copy2(binary,run/'native.frozen')
        for p in sources:
            dst=run/'source'/p.relative_to(SOURCE_ROOT);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dst)
    unique={};indices={}
    for i,j in enumerate(jobs):
        key=canonical_hash(j['input']);unique.setdefault(key,j);indices.setdefault(key,[]).append(i)
    output=[None]*len(jobs);errors=[];done=calls=fights=reused=0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        pending={pool.submit(dispatch,j,run/'native.frozen',bh,root):key for key,j in unique.items()}
        for future in as_completed(pending):
            key=pending[future];done+=1
            try:
                row=future.result()
                if row['cache_hit']:reused+=1
                else:calls+=1;fights+=row['iterations']
                for i in indices[key]:output[i]={**row,**jobs[i]['meta']}
            except Exception as exc:errors.append({'input_sha256':key,'error':str(exc)})
            if done%100==0 or done==len(unique):
                progress={'status':'running','completed':done,'unique_cells':len(unique),'new_calls':calls,'new_fights':fights,'reused_cells':reused,'errors':len(errors)}
                atomic_json(run/'PROGRESS.json',progress);print(json.dumps(progress),flush=True)
    atomic_json(run/'RESULTS.json',{'rows':output,'errors':errors});progress['status']='failed' if errors else 'complete';atomic_json(run/'PROGRESS.json',progress)
    if errors:raise RuntimeError(f'{len(errors)} failed cells preserved')
    return run


def save_ecology(ecology):
    root=setup_paths();out=root/'artifacts'/STAGE
    atomic_json(out/'BASE_ECOSYSTEMS.json',ecology)
    atomic_json(out/'CANDIDATE_DESIGN_DOMAIN.json',{'families':ecology['candidate_design_families'],
        'release_semantics':'Native existing items in experimental release roles, not official future items.',
        'pools':[{'id':p['id'],'slots':p['slots'],'old_source_ids':p['old_source_ids'],'new_source_ids':p['new_source_ids']} for p in ecology['ecosystems']]})


def smoke():
    root=setup_paths();cfg=load_config();ecology=enumerate_ecosystems(cfg);save_ecology(ecology)
    gear=ecology['gears'][ecology['ecosystems'][0]['initial_gear_ids'][0]]['gear'];jobs=[]
    for task in [cfg['tasks'][0],cfg['tasks'][-1]]:
        jobs.append({'input':make_input(gear,task,cfg['strategies'][1],'RaceHuman',409239001,2,cfg,debug=True),
                     'meta':{'task':task['id'],'race':'RaceHuman','strategy':'native_reck','gear_id':canonical_hash(gear)[:16]}})
    run=run_jobs(jobs,'incoming-smoke-v1',scientific_protocol={'purpose':'Check incoming native attacks and rage; no survival inference.'},workers=2)
    result=json.loads((run/'RESULTS.json').read_text());checks=[]
    for row in result['rows']:
        with gzip.open(Path(row['cache_directory'])/'output.json.gz','rt') as f:raw=json.load(f)
        player=raw['raidMetrics']['parties'][0]['players'][0]
        checks.append({'task':row['task'],'dps_mean':row['dps_mean'],'resources':row['resources'],
            'dtps':player.get('dtps'),'death_metrics':{k:v for k,v in player.items() if 'died' in k.lower() or 'death' in k.lower()},
            'incoming_log_lines':[line for line in raw.get('logs','').splitlines() if 'Target 1' in line and ('damage' in line or 'rage' in line)][:12]})
    atomic_json(run/'INCOMING_CHECK.json',{'checks':checks,'scope':'Native resource/mitigation stress, not survival.'});print(json.dumps(checks,indent=2))


def main():
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','smoke','baseline']);p.add_argument('--workers',type=int,default=64);p.add_argument('--resume',action='store_true');a=p.parse_args()
    if a.stage=='smoke':smoke();return
    ecology=enumerate_ecosystems();save_ecology(ecology)
    print(json.dumps({'pools':len(ecology['ecosystems']),'unique_gears':len(ecology['gears']),'pool_configurations':sum(p['legal_terminal_count'] for p in ecology['ecosystems']),'exclusions':ecology['excluded']}),flush=True)
    if a.stage=='prepare':return
    cfg=load_config();jobs,_=prepare(cfg)
    run=run_jobs(jobs,'baseline-v1',scientific_protocol={'configuration':cfg,'base_ecosystems_sha256':canonical_hash(ecology),'permission':'Native physical table, reusable for all admission comparisons; no rule or item physics changed.'},workers=a.workers,resume=a.resume)
    atomic_json(run/'BASE_ECOSYSTEMS.json',ecology);print(str(run),flush=True)

if __name__=='__main__':main()
