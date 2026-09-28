"""Prepare source-frozen heldout native item arrivals and their finite response table."""
from __future__ import annotations
import argparse
from copy import deepcopy
import itertools
import json
from pathlib import Path
import numpy as np
import yaml
from wowfs.paths import SOURCE_ROOT, setup_paths, atomic_json, canonical_hash
from wowfs.experiments.r2_native import load_config, engine_root, enumerate_gear, legal, make_input, file_hash, run_jobs

def catalogue(cfg, design, database):
    old,_=enumerate_gear(cfg,database)
    all_gears={k:v['gear'] for k,v in old.items()}
    initial=set(all_gears)
    base=dict(cfg['character']['base_equipment']);base.update(design['initial_catalogue']['base_equipment_overrides'])
    original=design['initial_catalogue']['variable_slots']
    memberships={}
    for sequence in design['sequences']:
        slots=deepcopy(original)
        release={a['item_id']:a['round'] for a in sequence['arrivals']}
        for a in sequence['arrivals']:slots[a['slot']].append(a['item_id'])
        membership={k:0 for k in old}
        for values in itertools.product(*slots.values()):
            gear={**base,**dict(zip(slots,values))}
            if not legal(gear,database):raise ValueError(f'illegal frozen heldout gear {gear}')
            key=canonical_hash(gear)[:16]
            round_available=max([release.get(i,0) for i in gear.values()])
            all_gears[key]=gear;membership[key]=round_available
            if not round_available:initial.add(key)
        memberships[sequence['id']]=membership
    return all_gears,initial,memberships

def features(gear, design, database):
    stats=np.array([database[i]['stats'] for i in gear.values()]).sum(axis=0)
    proxy=(stats[17]+2*stats[0])/14
    for slot,weight in [('main_hand',1),('off_hand',.5)]:
        item=database[gear[slot]]
        proxy+=weight*(item['weaponDamageMin']+item['weaponDamageMax'])/(2*item['weaponSpeed'])
    effect=np.zeros(8)
    for item in gear.values():
        descriptor=design['item_descriptors'][item]
        if not descriptor['source_syntax_supported']:raise ValueError('unresolved effect syntax')
        effect+=descriptor['coordinates']
    for entry in design['set_descriptors']:
        count=sum(design['item_descriptors'][i].get('set_name')==entry['name'] for i in gear.values())
        if count>=entry['pieces']:effect+=entry['coordinates']
    return np.r_[proxy,effect].tolist()

def prepare_run(run_id='unseen-v1',workers=64,resume=False):
    root=setup_paths();engine=engine_root(root);cfg=load_config()
    design=yaml.safe_load((SOURCE_ROOT/'configs/r2_unseen.yaml').read_text())
    decisions=yaml.safe_load((SOURCE_ROOT/'configs/r2_decisions.yaml').read_text())
    database={i['id']:i for i in json.loads((engine/'assets/database/db.json').read_text())['items']}
    gears,initial,memberships=catalogue(cfg,design,database)
    vectors={key:features(gear,design,database) for key,gear in gears.items()}
    thresholds=np.max([vectors[k] for k in initial],axis=0).tolist()
    freeze={'design':design,'decisions':decisions,'initial_gear_ids':sorted(initial),'features':vectors,
            'thresholds':thresholds,'memberships':memberships,'gears':gears,
            'counts':{'initial_gears':len(initial),'union_gears':len(gears),'sequences':len(memberships),
                      'final_domain_sizes':{k:len(v) for k,v in memberships.items()}},
            'source_hashes':{str(p.relative_to(SOURCE_ROOT)):file_hash(p) for p in
                [SOURCE_ROOT/'configs/r2_discovery.yaml',SOURCE_ROOT/'configs/r2_unseen.yaml',
                 SOURCE_ROOT/'configs/r2_decisions.yaml',Path(__file__)]},
            'native_mechanism':'unaltered; source-fixed gate study selected cooldown0',
            'static_proxy_formula':'sum(AP+2Strength)/14+MH_avg_weapon_DPS+0.5*OH_avg_weapon_DPS; excludes crit/hit and is not a DPS bound'}
    run=root/'runs/r2-discovery'/run_id
    frozen_path=run/'FROZEN_DESIGN.json'
    if frozen_path.exists():
        if json.loads(frozen_path.read_text())!=freeze:raise ValueError('frozen design mismatch')
    else:atomic_json(frozen_path,freeze)
    template=json.loads((root/'runs/r2-discovery/native-smoke/effect.input.json').read_text())
    jobs=[]
    for key,task,strategy,race in itertools.product(sorted(gears),cfg['tasks'],cfg['strategies'],design['races']):
        seed=decisions['initial_seed_start'] if key in initial else decisions['new_item_seed_start']
        jobs.append({'meta':{'stage':'unseen_frozen','gear_id':key,'task':task['id'],
                    'strategy':strategy['id'],'race':race,'initial':key in initial},
                    'input':make_input(template,cfg,gears[key],task,strategy,engine,race,seed,decisions['sample_size'])})
    print(json.dumps(freeze['counts']),flush=True)
    run_jobs(jobs,run,root/'envs/r2-go/wowfs-native',workers,resume)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-id',default='unseen-v1');p.add_argument('--workers',type=int,default=64);p.add_argument('--resume',action='store_true');a=p.parse_args()
    prepare_run(a.run_id,a.workers,a.resume)
