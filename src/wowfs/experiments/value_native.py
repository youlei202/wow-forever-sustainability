"""Decisive-value native requests and immutable execution receipts.

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

STAGE = 'decisive-value'
R5_SHA256 = 'a2160fda7467f3618797c91f2257f6dac39b284804774cf0751eac1d92cd8dd2'
CACHE_STAGES = (STAGE, 'r6-theory-native', 'r4-foundational-discovery', 'r3-gold', 'r2-discovery')


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
    if len(players)!=1 or players[0]['class']!='ClassWarrior':
        raise ValueError('Decisive-value validated wrapper currently supports one Warrior only')
    items = players[0]['equipment']['items']
    if len(items)!=len(SLOTS):
        raise ValueError('expected exactly17 actual equipment slots')
    ids = [item['id'] for item in items]
    database = native_database()
    for slot, typ, item_id in zip(SLOTS, TYPES, ids):
        item = database.get(item_id)
        if item is None or item['type']!=typ:
            raise ValueError('unknown or slot-incompatible native item at '+slot)
        if item.get('unique') and ids.count(item_id)>1:
            raise ValueError('duplicate unique native item')
        if item.get('classAllowlist') and 9 not in item['classAllowlist']:
            raise ValueError('item is not native Warrior equipment')
        if slot=='main_hand' and item.get('handType') not in (1,2):
            raise ValueError('invalid main-hand assignment')
        if slot=='off_hand' and item.get('handType') not in (2,3):
            raise ValueError('invalid off-hand assignment')
    specs = value.get('research_variants', [])
    if len({s['item_id'] for s in specs})!=len(specs):
        raise ValueError('one parameter set per native base ID is required')
    for spec in specs:
        if ids.count(spec['item_id'])!=1:
            raise ValueError('global native override must identify exactly one equipped item')


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


def r3_base(race='RaceHuman', task='high_armor', strategy='native_reck',
            speed=1.3, offhand=19019, trinkets=(11815,13965)):
    """Return one exact archived R3 calibration input and its provenance path."""
    path = setup_paths()/'artifacts/r3-gold/AFFINE_CALIBRATION.json'
    rows = json.loads(path.read_text())['models']
    selected = [r for r in rows if (r['race'],r['task'],r['strategy'],r['weapon_speed'],
                 r['offhand'],r['trinket1'],r['trinket2']) ==
                (race,task,strategy,speed,offhand,*trinkets)]
    if len(selected)!=1: raise ValueError('R3 context is not uniquely calibrated')
    source = Path(selected[0]['anchors'][0]['cache_directory'])/'input.json'
    value = json.loads(source.read_text())
    validate_equipment(value)
    return value, source


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
    theory = root/'inputs/r5-theory/THEORY.md'
    if file_hash(theory)!=R5_SHA256: raise ValueError('formal R5 theory differs from reviewed source')
    binary = Path(binary) if binary else root/'envs/r3-go/wowfs-native-variants'
    bh = file_hash(binary)
    sources = [SOURCE_ROOT/'src/wowfs/experiments/value_native.py',
               SOURCE_ROOT/'src/wowfs/experiments/r2_native.py',
               SOURCE_ROOT/'src/wowfs/simulator/r3_variants.go',
               SOURCE_ROOT/'scripts/native_build_r3.sh', *map(Path,source_paths)]
    sources = sorted(set(p.resolve() for p in sources))
    imported = {'r5-theory/THEORY.md':theory, **{k:Path(v) for k,v in (input_artifacts or {}).items()}}
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


def load_decision_ecologies(pool_ids=None, races=None):
    """Read only the exact R4 complete table; no new simulation or changed cap."""
    from wowfs.experiments.r4_data import load_ecologies
    run = setup_paths()/'runs/r4-foundational-discovery/baseline-v1'
    selected = set(pool_ids) if pool_ids is not None else None
    chosen_races = set(races) if races is not None else None
    return [e for e in load_ecologies(run)
            if (selected is None or e.pool['id'] in selected)
            and (chosen_races is None or e.race in chosen_races)]


def make_input(gear, task, strategy, race, *, seed, iterations=32, cfg=None,
               disabled=(), debug=False):
    """Use the existing real task/APL builder; native binary is selected explicitly."""
    from wowfs.experiments.r4_native import make_input as existing_input
    value = existing_input(gear, task, strategy, race, seed, iterations, cfg, disabled, debug)
    validate_equipment(value)
    return value
