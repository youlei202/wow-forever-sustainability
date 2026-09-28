"""Final-completion native requests and immutable execution receipts.

Alias labels describe alternative research designs. Only existing native IDs
reach the engine, and an equipped base ID has one unambiguous parameter set.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime, timezone
from functools import lru_cache
import json
from pathlib import Path
import shutil

from wowfs.paths import SOURCE_ROOT, setup_paths, atomic_json, canonical_hash
from wowfs.experiments.r2_native import SLOTS, TYPES, execute_job, file_hash

STAGE = 'final-completion-capacity'
R5_SHA256 = 'a2160fda7467f3618797c91f2257f6dac39b284804774cf0751eac1d92cd8dd2'
CACHE_STAGES = (STAGE, 'decisive-value', 'r6-theory-native', 'r4-foundational-discovery', 'r3-gold', 'r2-discovery')
CLASS_IDS = dict(Druid=1,Hunter=2,Mage=3,Paladin=4,Priest=5,Rogue=6,Shaman=7,Warlock=8,Warrior=9)
MAX_ARMOR = dict(Druid=2,Hunter=3,Mage=1,Paladin=4,Priest=1,Rogue=2,Shaman=3,Warlock=1,Warrior=4)
WEAPONS = dict(Druid=[2,3,4,5,8],Hunter=[1,2,3,5,6,8,9],Mage=[2,5,8,9],
 Paladin=[1,4,5,6,7,9],Priest=[2,4,5,8],Rogue=[2,3,4,5,9],
 Shaman=[1,2,3,4,5,7,8],Warlock=[2,5,8,9],Warrior=list(range(1,10)))
TWO_HANDED = dict(Druid=[4,8],Hunter=[1,6,8,9],Mage=[8],Paladin=[1,4,6,9],
 Priest=[8],Rogue=[],Shaman=[1,4,8],Warlock=[8],Warrior=[1,4,6,8,9])
RANGED = dict(Druid=[4],Hunter=[1,2,3],Mage=[8],Paladin=[5],Priest=[8],Rogue=[1,2,3,6],Shaman=[7],Warlock=[8],Warrior=[1,2,3,6])


def engine_root():
    return setup_paths()/'external/mythicsim-forever-engine-r3-variants'


def contexts():
    config=json.loads((SOURCE_ROOT/'configs/official_contexts.yaml').read_text())
    aliases={'High Order Skyborne':'SkyborneHighOrder','Windshaper Skyborne':'SkyborneWindshaper'}
    return [{'context_id':f'{faction}_{row["race"].replace(" ","")}_{cls}',
             'faction':faction,'race_label':row['race'],'class':cls,
             'race':'Race'+aliases.get(row['race'],row['race'].replace(' ','')),
             'native_racial_incomplete':row['race']=='High Order Skyborne' or (row['race']=='Gnome' and cls in ('Rogue','Warrior'))}
            for faction,rows in config['factions'].items() for row in rows for cls in row['classes']]


def presets():
    return json.loads((SOURCE_ROOT/'configs/fc_presets.json').read_text())['classes']


def normalize_gear(items):
    """Native presets sometimes omit empty slots or place ranged before weapons."""
    out=[{'id':0} for _ in SLOTS]; database=native_database(); moves=[]
    for index,entry in enumerate(items):
        if not entry.get('id'): continue
        item=database[entry['id']]; typ=item['type']
        if typ==13:
            hand=item['handType']
            slots=[15] if hand==3 else ([14] if hand in (1,4) else [14,15])
        else: slots=[i for i,t in enumerate(TYPES) if t==typ]
        dest=next((i for i in slots if not out[i]['id']),None)
        if dest is None: raise ValueError('overfilled native preset slot')
        out[dest]=deepcopy(entry)
        if dest!=index: moves.append({'item_id':entry['id'],'from_index':index,'to_index':dest})
    return out,moves


def make_input(context,task,*,seed,iterations,debug=False):
    preset=presets()[context['class']]; engine=engine_root()
    gear,moves=normalize_gear(json.loads((engine/preset['gear']).read_text())['items'])
    player={'name':'FC'+context['class'],'race':context['race'],'class':'Class'+context['class'],
        'equipment':{'items':gear},'talentsString':preset['talents'],
        'rotation':json.loads((engine/preset['apl']).read_text()),
        preset['spec']:{'options':deepcopy(preset['options'])},
        'distanceFromTarget':preset['distance'],'inFrontOfTarget':False,
        'reactionTimeMs':100,'channelClipDelayMs':100,'consumes':{},'buffs':{}}
    stats=[0]*44; stats[26]=task.get('armor',3731)
    target={'name':'Target 1','level':63,'stats':stats,'tankIndex':-1,
            'mobType':task.get('mob_type','MobTypeUnknown')}
    encounter={'duration':task['duration'],'executeProportion20':task.get('execute',.2),
               'targets':[deepcopy(target) for _ in range(task.get('targets',1))]}
    value={'request':{'raid':{'parties':[{'players':[player],'buffs':{}}],
               'buffs':{},'debuffs':{},'tanks':[]},'encounter':encounter,
               'simOptions':{'iterations':iterations,'randomSeed':str(seed),'ruleset':'RulesetForever',
                'debugFirstIteration':debug,'saveAllValues':True,'useLabeledRands':True}},
           'disable_item_effects':[],'disable_set_bonuses':[],'research_variants':[]}
    validate_equipment(value)
    return value


@lru_cache(maxsize=1)
def native_database():
    path = setup_paths()/'external/mythicsim-forever-engine-r3-variants/assets/database/db.json'
    return {item['id']:item for item in json.loads(path.read_text())['items']}


def define_alias(alias, base_item_id, slot, parameters):
    if not isinstance(alias, str) or not alias or slot not in SLOTS:
        raise ValueError('research alias must have a nonempty label and an actual equipment slot')
    if base_item_id not in native_database():
        raise ValueError('research aliases must retain a real native base item ID')
    if 'item_id' in parameters:
        raise ValueError('pass base_item_id separately from parameter overrides')
    json.dumps(parameters, allow_nan=False)
    physics = {'native_base_item_id':base_item_id, 'equipment_slot':slot,
               'parameter_overrides':deepcopy(parameters)}
    return {'research_alias':alias, **physics, 'physics_identity_sha256':canonical_hash(physics),
            'identity_scope':'Research design alias, not a newly invented official item ID.'}


def validate_equipment(value):
    players = [p for party in value['request']['raid']['parties'] for p in party['players']]
    if len(players) != 1: raise ValueError('FC validates one player plus native pets')
    player = players[0]; name = player['class'].removeprefix('Class')
    if name not in CLASS_IDS: raise ValueError('unknown native class')
    if (name,player['race']) not in {(c['class'],c['race']) for c in contexts()}:
        raise ValueError('outside frozen official class/race matrix')
    items = player['equipment']['items']; ids = [x.get('id',0) for x in items]
    if len(items) != 17: raise ValueError('equipment must have17 explicit slots')
    database = native_database()
    for slot,typ,item_id in zip(SLOTS,TYPES,ids):
        if not item_id:
            if slot not in ('off_hand','ranged'): raise ValueError('required slot empty:'+slot)
            continue
        item = database.get(item_id)
        if item is None or item['type'] != typ: raise ValueError('unknown/wrong slot:'+slot)
        if item.get('unique') and ids.count(item_id)>1: raise ValueError('duplicate unique item')
        if item.get('classAllowlist') and CLASS_IDS[name] not in item['classAllowlist']:
            raise ValueError('classAllowlist rejects '+str(item_id))
        if item.get('armorType',0)>MAX_ARMOR[name]: raise ValueError('armor class rejects '+str(item_id))
        if typ==13:
            w,h=item.get('weaponType',0),item.get('handType',0)
            if w not in WEAPONS[name] or (h==4 and w not in TWO_HANDED[name]):
                raise ValueError('weapon class rejects '+str(item_id))
            if slot=='main_hand' and h not in (1,2,4): raise ValueError('invalid main hand')
            if slot=='off_hand' and h not in (2,3): raise ValueError('invalid off hand')
            if slot=='off_hand' and w not in (5,7) and name not in ('Warrior','Hunter','Rogue'):
                raise ValueError('non-dual-wield specialization')
        if typ==14 and item.get('rangedWeaponType') not in RANGED[name]:
            raise ValueError('ranged class rejects '+str(item_id))
    if database[ids[14]].get('handType')==4 and ids[15]: raise ValueError('two handed plus offhand')
    specs=value.get('research_variants',[])
    if len({s['item_id'] for s in specs})!=len(specs): raise ValueError('duplicate override')
    if any(ids.count(s['item_id'])!=1 for s in specs): raise ValueError('override requires unique equipped base ID')


def instantiate(base, aliases, *, seed=None, iterations=None, debug=None):
    """Replace one item per declared slot; different aliases cannot coequip there."""
    value = deepcopy(base)
    selected_slots = [a['equipment_slot'] for a in aliases]
    if len(set(selected_slots))!=len(selected_slots):
        raise ValueError('research alternatives in one slot are mutually exclusive')
    if len({a['research_alias'] for a in aliases})!=len(aliases):
        raise ValueError('one research alias cannot be equipped twice')
    items = value['request']['raid']['parties'][0]['players'][0]['equipment']['items']
    existing = {v['item_id']:v for v in value.get('research_variants', [])}
    for alias in aliases:
        slot, item_id = alias['equipment_slot'], alias['native_base_item_id']
        original_id = items[SLOTS.index(slot)]['id']
        existing.pop(original_id, None)
        items[SLOTS.index(slot)] = {'id':item_id}
        existing[item_id] = {'item_id':item_id, **deepcopy(alias['parameter_overrides'])}
    value['research_variants'] = [existing[i] for i in sorted(existing)]
    options = value['request']['simOptions']
    if seed is not None: options['randomSeed'] = str(seed)
    if iterations is not None: options['iterations'] = iterations
    if debug is not None: options['debugFirstIteration'] = debug
    options.update(saveAllValues=True, useLabeledRands=True)
    validate_equipment(value)
    return value


def dispatch(job, binary, binary_hash, root):
    key = canonical_hash({'binary':binary_hash, 'input':job['input']})
    for stage in CACHE_STAGES:
        folder = root/'cache'/stage/'native'/key[:2]/key
        if (folder/'summary.json').exists():
            row = json.loads((folder/'summary.json').read_text())
            return {**row, 'cache_key':key, 'cache_hit':True,
                    'cache_origin':stage, 'cache_directory':str(folder)}
    folder = root/'cache'/STAGE/'native'/key[:2]/key
    if folder.exists() and any(folder.iterdir()):
        raise RuntimeError('Incomplete/failed native attempt preserved; refuse to overwrite '+str(folder))
    row = execute_job(job, binary, binary_hash, root/'cache'/STAGE/'native')
    return {**row, 'cache_origin':STAGE, 'cache_directory':str(folder)}


def run_jobs(jobs, run_id, scientific_protocol, workers=32, resume=False,
             binary=None, source_paths=(), input_artifacts=None):
    root = setup_paths()
    if not 1 <= workers <= 64: raise ValueError('workers must be between1and64')
    if not scientific_protocol: raise ValueError('freeze a nonempty scientific protocol before new physics')
    if not jobs: raise ValueError('an empty native run is not an executed experiment')
    if Path(run_id).name!=run_id: raise ValueError('run_id must be one directory component')
    binary = Path(binary) if binary else root/'envs/r3-go/wowfs-native-variants'
    bh = file_hash(binary)
    sources = [SOURCE_ROOT/'src/wowfs/experiments/fc_native.py',
               SOURCE_ROOT/'src/wowfs/experiments/r2_native.py',
               SOURCE_ROOT/'src/wowfs/simulator/r3_variants.go',
               SOURCE_ROOT/'scripts/native_build_r3.sh', *map(Path,source_paths)]
    sources = sorted(set(p.resolve() for p in sources))
    imported = {k:Path(v) for k,v in (input_artifacts or {}).items()}
    for name in imported:
        if Path(name).is_absolute() or '..' in Path(name).parts:
            raise ValueError('input artifact destination must be a relative path without traversal')
    for job in jobs: validate_equipment(job['input'])
    protocol = {'schema':1, 'binary_sha256':bh, 'jobs_sha256':canonical_hash(jobs),
        'science':scientific_protocol, 'logical_cells':len(jobs),
        'requested_battles':sum(j['input']['request']['simOptions']['iterations'] for j in jobs),
        'source_hashes':{str(p.relative_to(SOURCE_ROOT)):file_hash(p) for p in sources},
        'imported_input_hashes':{name:file_hash(path) for name,path in imported.items()},
        'randomization':'Native labeled RNG seed+i; matched seeds across design points are coupled, not independent experimental units.'}
    run = root/'runs'/STAGE/run_id
    if (run/'PROTOCOL.json').exists():
        if not resume or json.loads((run/'PROTOCOL.json').read_text())!=protocol:
            raise ValueError('resume requires identical frozen inputs, source, imported artifacts and binary')
        if (run/'PROGRESS.json').exists() and json.loads((run/'PROGRESS.json').read_text())['status']=='complete':
            return run
    else:
        run.mkdir(parents=True, exist_ok=True)
        atomic_json(run/'PROTOCOL.json', protocol)
        atomic_json(run/'JOBS.json', jobs)
        atomic_json(run/'FREEZE_TIME.json', {'utc':datetime.now(timezone.utc).isoformat()})
        shutil.copy2(binary, run/'native.frozen')
        for source in sources:
            destination = run/'source'/source.relative_to(SOURCE_ROOT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        for name, source in imported.items():
            destination = run/'inputs'/name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    unique, indices = {}, {}
    for index, job in enumerate(jobs):
        key = canonical_hash(job['input'])
        unique.setdefault(key, job); indices.setdefault(key, []).append(index)
    output, errors = [None]*len(jobs), []
    done = calls = fights = reused = 0
    progress = {'status':'running', 'completed':0, 'unique_cells':len(unique),
                'new_calls':0, 'new_fights':0, 'reused_cells':0, 'errors':0}
    atomic_json(run/'PROGRESS.json', progress)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        pending = {pool.submit(dispatch, job, run/'native.frozen', bh, root):key
                   for key,job in unique.items()}
        for future in as_completed(pending):
            key = pending[future]; done += 1
            try:
                row = future.result()
                if row['cache_hit']: reused += 1
                else: calls += 1; fights += row['iterations']
                for index in indices[key]: output[index] = {**row, **jobs[index]['meta']}
            except Exception as exc:
                errors.append({'input_sha256':key, 'error':str(exc)})
            if done%100==0 or done==len(unique):
                progress = {'status':'running', 'completed':done, 'unique_cells':len(unique),
                            'new_calls':calls, 'new_fights':fights, 'reused_cells':reused, 'errors':len(errors)}
                atomic_json(run/'PROGRESS.json', progress)
                print(json.dumps(progress), flush=True)
    atomic_json(run/'RESULTS.json', {'rows':output, 'errors':errors})
    progress['status'] = 'failed' if errors else 'complete'
    atomic_json(run/'PROGRESS.json', progress)
    if errors: raise RuntimeError(str(len(errors))+' native cells failed; receipts preserved')
    return run

