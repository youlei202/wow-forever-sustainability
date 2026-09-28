"""Finite native-combat discovery. Every cached cell contains executable input/output."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
import gzip
import hashlib
import itertools
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

import numpy as np
import yaml

from wowfs.paths import SOURCE_ROOT, atomic_json, canonical_hash, setup_paths

SLOTS = ['head','neck','shoulder','back','chest','wrist','hands','waist','legs','feet',
         'finger1','finger2','trinket1','trinket2','main_hand','off_hand','ranged']
TYPES = [1,2,3,4,5,6,7,8,9,10,11,11,12,12,13,13,14]

def file_hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def load_config():
    return yaml.safe_load((SOURCE_ROOT/'configs/r2_discovery.yaml').read_text())

def engine_root(root):
    return Path(os.environ.get('WOWFS_ENGINE_ROOT', root/'external/mythicsim-forever-engine-r2'))

def legal(gear, database):
    ids = list(gear.values())
    for slot, typ in zip(SLOTS, TYPES):
        item = database[gear[slot]]
        if item['type'] != typ:
            return False
        if item.get('unique') and ids.count(item['id']) > 1:
            return False
        if item.get('classAllowlist') and 9 not in item['classAllowlist']:
            return False
        if slot == 'off_hand' and item.get('handType') not in (2, 3):
            return False
    return True

def enumerate_gear(cfg, database):
    records = {}
    excluded = []
    for pool in cfg['pools']:
        names = list(pool['slots'])
        for values in itertools.product(*pool['slots'].values()):
            gear = dict(cfg['character']['base_equipment'])
            gear.update(pool.get('fixed', {}))
            gear.update(zip(names, values))
            if not legal(gear, database):
                excluded.append({'pool':pool['id'], 'gear':gear})
                continue
            key = canonical_hash(gear)[:16]
            row = records.setdefault(key, {'gear_id':key,'gear':gear,'pools':[]})
            row['pools'].append(pool['id'])
    return records, excluded

def rotation(engine, strategy):
    result = json.loads((engine/strategy['source']).read_text())
    transform = strategy.get('transformation')
    if not isinstance(transform, dict):
        return result
    def replace(node, old, new):
        if isinstance(node, dict):
            if node.get('lhs', {}).get('currentRage') == {} and 'currentRage' in node.get('lhs', {}):
                v = node.get('rhs', {}).get('const', {})
                if v.get('val') == str(old):
                    v['val'] = str(new)
                    return 1
            return sum(replace(v, old, new) for v in node.values())
        if isinstance(node, list):
            return sum(replace(v, old, new) for v in node)
        return 0
    for change in transform['action_rage_thresholds']:
        count = 0
        for entry in result['priorityList']:
            action = entry.get('action', {})
            ident = action.get('castSpell', {}).get('spellId', {})
            if ident.get('spellId') == change['spell_id'] and ident.get('tag',0) == change.get('tag',0):
                count += replace(action.get('condition', {}), change['old'], change['new'])
        if count != 1:
            raise ValueError(f'Expected exactly one APL transformation: {change}, got {count}')
    return result

def make_input(template, cfg, gear, task, strategy, engine, race, seed, iterations,
               disabled=(), debug=False):
    value = deepcopy(template)
    request = value['request']
    raid = request['raid']
    raid['buffs'] = {}; raid['debuffs'] = {}
    party = raid['parties'][0]; party['buffs'] = {}
    player = party['players'][0]
    player['buffs'] = {}; player['consumes'] = {}
    player['name'] = 'R2Warrior'; player['race'] = race
    player['equipment'] = {'items':[{'id':gear[s]} for s in SLOTS]}
    player['talentsString'] = cfg['character']['talents']
    player['rotation'] = rotation(engine, strategy)
    player['warrior'] = {'options':{'startingRage':cfg['character']['starting_rage'],
                                   'queueDelay':cfg['character']['queue_delay_ms'],
                                   'shout':cfg['character']['shout'],
                                   'stance':cfg['character']['stance']}}
    target = deepcopy(request['encounter']['targets'][0])
    target['level'] = task['target_level']; target['stats'][26] = task['target_armor']
    target['tankIndex'] = -1
    request['encounter'] = {'duration':task['duration_seconds'],
                            'executeProportion20':task['execute_proportion_20'],
                            'targets':[deepcopy(target) for _ in range(task['targets'])]}
    request['simOptions'] = {'iterations':iterations,'randomSeed':str(seed),
                             'ruleset':'RulesetForever','debugFirstIteration':debug,
                             'saveAllValues':True,'useLabeledRands':True}
    value['disable_item_effects'] = [x['item_id'] for x in disabled if 'item_id' in x]
    value['disable_set_bonuses'] = [{'name':x['set_name'],'pieces':x['pieces']}
                                    for x in disabled if 'set_name' in x]
    return value

def action_key(ident):
    return '/'.join(f'{k}:{v}' for k,v in sorted(ident.items()) if v)

def summarize(output, request):
    count = int(output['iterationsDone'])
    expected = request['request']['simOptions']['iterations']
    if output.get('error') or count != expected:
        raise ValueError(f'native incomplete: {output.get("error")}, {count}/{expected}')
    player = output['raidMetrics']['parties'][0]['players'][0]
    samples = np.array(player['dps']['allValues'])
    if len(samples) != count or not np.isfinite(samples).all():
        raise ValueError('native per-iteration DPS samples missing or nonfinite')
    if not np.isclose(samples.mean(), player['dps']['avg'], rtol=1e-9):
        raise ValueError('native sample mean mismatch')
    damage = sum(t['damage'] for a in player['actions'] for t in a['targets'])
    actions = {action_key(a['id']):{
        'casts':sum(t['casts'] for t in a['targets'])/count,
        'damage':sum(t['damage'] for t in a['targets'])/count,
        'fraction':sum(t['damage'] for t in a['targets'])/damage if damage else 0,
    } for a in player['actions']}
    return {'iterations':count,'dps_mean':float(samples.mean()),
            'dps_se':float(samples.std(ddof=1)/np.sqrt(count)) if count>1 else None,
            'dps_samples':samples.tolist(),'actions':actions,
            'resources':[{**r, **{k:r[k]/count for k in ('events','gain','actualGain')}}
                         for r in player['resources']],
            'auras':player['auras']}

def execute_job(job, binary, binary_hash, cache):
    key = canonical_hash({'binary':binary_hash, 'input':job['input']})
    directory = cache/key[:2]/key
    summary_path = directory/'summary.json'
    if summary_path.exists():
        saved = json.loads(summary_path.read_text())
        return {**job['meta'], 'cache_key':key,'cache_hit':True,**saved}
    directory.mkdir(parents=True, exist_ok=True)
    atomic_json(directory/'input.json', job['input'])
    output_path = directory/'output.json'
    started = time.monotonic()
    command = [str(binary),'-in',str(directory/'input.json'),'-out',str(output_path)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=180,
                            env={**os.environ,'GOMAXPROCS':'1'})
    atomic_json(directory/'invocation.json', {'command':command,'binary_sha256':binary_hash,
                'returncode':result.returncode,'elapsed_seconds':time.monotonic()-started,
                'stdout':result.stdout,'stderr':result.stderr})
    if result.returncode:
        raise RuntimeError(f'native failure {key}: {result.stderr[-2000:]}')
    raw = output_path.read_bytes()
    output = json.loads(raw)
    summary = summarize(output, job['input'])
    summary['output_sha256'] = hashlib.sha256(raw).hexdigest()
    with gzip.open(directory/'output.json.gz','wb') as f:
        f.write(raw)
    output_path.unlink()
    atomic_json(summary_path, summary)
    return {**job['meta'],'cache_key':key,'cache_hit':False,**summary}

def prepare(cfg, template, engine, database, stage, seed, iterations, races):
    gears, excluded = enumerate_gear(cfg, database)
    jobs = []
    if stage in ('discovery','matrix'):
        for row, task, strategy, race in itertools.product(gears.values(),cfg['tasks'],cfg['strategies'],races):
            meta = {k:v for k,v in row.items() if k!='gear'}
            meta.update(stage=stage,task=task['id'],strategy=strategy['id'],race=race)
            jobs.append({'meta':meta,'input':make_input(template,cfg,row['gear'],task,strategy,engine,race,seed,iterations)})
    if stage in ('discovery','factorial'):
        for case in cfg['causal_cases']:
            gear = dict(cfg['character']['base_equipment']); gear.update(case['equipment_overrides'])
            effects = [case['effect_a'],case['effect_b']]
            if 'optional_effect_c' in case: effects.append(case['optional_effect_c'])
            for mask,task,strategy,race in itertools.product(range(2**len(effects)),cfg['tasks'],cfg['strategies'],races):
                disabled = [e for i,e in enumerate(effects) if not mask&(1<<i)]
                meta = {'stage':stage,'case':case['id'],'mask':mask,'n_effects':len(effects),
                        'task':task['id'],'strategy':strategy['id'],'race':race}
                jobs.append({'meta':meta,'input':make_input(template,cfg,gear,task,strategy,engine,race,seed,iterations,disabled)})
    return jobs,gears,excluded

def run_jobs(jobs, run, binary, workers=64, resume=False):
    root=setup_paths(); cache=root/'cache/r2-discovery/native'
    bh=file_hash(binary)
    sources=[SOURCE_ROOT/'src/wowfs/experiments/r2_native.py',SOURCE_ROOT/'configs/r2_discovery.yaml',
             *list((SOURCE_ROOT/'src/wowfs/simulator').glob('native*.go'))]
    protocol={'schema_version':2,'binary_sha256':bh,'jobs_hash':canonical_hash(jobs),
              'source_sha256':{str(p.relative_to(SOURCE_ROOT)):file_hash(p) for p in sources},
              'logical_cells':len(jobs),'requested_physical_battles':sum(j['input']['request']['simOptions']['iterations'] for j in jobs),
              'workers':workers,'randomization':'labeled native RNG, seed+i, common seeds within stage',
              'scope':'source-defined finite native community-engine domains; no live-server fidelity claim'}
    manifest=run/'PROTOCOL.json'
    if manifest.exists():
        if not resume or json.loads(manifest.read_text())!=protocol:
            raise ValueError('existing run requires --resume and exact frozen protocol match')
    else:
        run.mkdir(parents=True,exist_ok=True)
        atomic_json(manifest,protocol);atomic_json(run/'JOBS.json',jobs)
        shutil.copy2(binary,run/'wowfs-native.frozen')
        snapshot=run/'source';snapshot.mkdir()
        for source in sources:
            shutil.copy2(source,snapshot/source.name)
        atomic_json(run/'SOURCE_HASHES.json',{p.name:file_hash(p) for p in snapshot.iterdir()})
    # Dedupe exact physical inputs; an output can serve overlapping named cells.
    unique={}; indices={}
    for i,job in enumerate(jobs):
        key=canonical_hash(job['input']); unique.setdefault(key,job);indices.setdefault(key,[]).append(i)
    outputs=[None]*len(jobs);errors=[];new_calls=0;new_battles=0;done=0
    atomic_json(run/'PROGRESS.json',{'status':'running','unique_inputs':len(unique),'complete':0})
    with ThreadPoolExecutor(max_workers=workers) as pool:
        pending={pool.submit(execute_job,job,run/'wowfs-native.frozen',bh,cache):key for key,job in unique.items()}
        for future in as_completed(pending):
            key=pending[future];done+=1
            try:
                row=future.result()
                if not row['cache_hit']:new_calls+=1;new_battles+=row['iterations']
                for i in indices[key]:outputs[i]={**row,**jobs[i]['meta']}
            except Exception as exc:
                errors.append({'input_hash':key,'error':str(exc)})
            if done%100==0 or done==len(unique):
                progress={'status':'running','complete':done,'unique_inputs':len(unique),'new_calls':new_calls,
                          'new_physical_battles':new_battles,'failures':len(errors)}
                atomic_json(run/'PROGRESS.json',progress);print(json.dumps(progress),flush=True)
    atomic_json(run/'RESULTS.json',{'rows':outputs,'errors':errors})
    atomic_json(run/'PROGRESS.json',{'status':'complete' if not errors else 'failed','complete':done,
        'unique_inputs':len(unique),'new_calls':new_calls,'new_physical_battles':new_battles,'failures':len(errors)})
    if errors:raise RuntimeError(f'{len(errors)} native cells failed; preserved in RESULTS.json')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--stage',choices=['discovery','matrix','factorial'],default='discovery')
    parser.add_argument('--iterations',type=int,default=32);parser.add_argument('--seed',type=int,default=24092401)
    parser.add_argument('--races',nargs='+',default=['RaceHuman'])
    parser.add_argument('--run-id',required=True);parser.add_argument('--workers',type=int,default=64)
    parser.add_argument('--resume',action='store_true');args=parser.parse_args()
    root=setup_paths();engine=engine_root(root);cfg=load_config()
    template=json.loads((root/'runs/r2-discovery/native-smoke/effect.input.json').read_text())
    database={i['id']:i for i in json.loads((engine/'assets/database/db.json').read_text())['items']}
    jobs,gears,excluded=prepare(cfg,template,engine,database,args.stage,args.seed,args.iterations,args.races)
    run=root/'runs/r2-discovery'/args.run_id
    run_jobs(jobs,run,root/'envs/r2-go/wowfs-native',args.workers,args.resume)
    atomic_json(run/'GEARS.json',{'gears':gears,'excluded':excluded})

if __name__=='__main__':main()
