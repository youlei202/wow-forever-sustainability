"""Fresh independent blocks for two fixed, post-design selected certificates."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import itertools
import json
from pathlib import Path
import shutil

import yaml

from wowfs.paths import setup_paths, SOURCE_ROOT, atomic_json, canonical_hash
from wowfs.experiments.r2_native import file_hash
from wowfs.experiments.r4_native import make_input, run_jobs

RUN_ID = 'certificate-precision-v1'
GEAR_ID = 'd9ddad879238ea73'
CERTIFICATES = [('RaceHuman', .5), ('RaceOrc', .75)]
BLOCK_SEEDS = [409320001 + 10000*b for b in range(8)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', type=int, default=64)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    root = setup_paths()
    reference = root/'runs/r4-foundational-discovery/constructive-reward-v1'
    full = json.loads((reference/'BASE_ECOSYSTEMS.json').read_text())
    cfg = yaml.safe_load((reference/'CONFIG.yaml').read_text())
    domain = deepcopy(full)
    pool = domain['ecosystems'][0]
    initial = pool['initial_gear_ids']
    assert len(initial) == 16 and GEAR_ID not in initial
    assert {18203,19019}.issubset(set(domain['gears'][GEAR_ID]['gear'].values()))
    support = initial + [GEAR_ID]
    pool['terminal_gear_ids'] = support
    pool['raw_terminal_count'] = pool['legal_terminal_count'] = 17
    pool['source_ids_by_gear'] = {g: pool['source_ids_by_gear'][g] for g in support}
    pool['sampling_scope'] = 'Selected17-gear certificate support: complete protectedold16 plus one fixed pair witness, not the complete36-gear release domain.'
    domain['gears'] = {g: domain['gears'][g] for g in support}
    domain['scope'] = pool['sampling_scope']
    cfg['sampling'].update(iterations=512, seed_start=BLOCK_SEEDS[0])
    binary = root/'envs/r3-go/wowfs-native-variants'
    science = {
        'permission': 'B research variants; independent confirmation of two selected finite-support certificates.',
        'selection': 'Chosen after constructive-reward-v1 means and uncertainty inspection; exploratory selection followed by fresh seeds, not prespecified before discovery.',
        'certificates': [{'race': r, 'weapon_damage_scale': x, 'gear_id': GEAR_ID} for r,x in CERTIFICATES],
        'block_seeds': BLOCK_SEEDS, 'blocks': 8, 'iterations_per_block': 512,
        'native_calls': 6528, 'physical_battles': 3342336,
        'measured_support': 'For each race/scale: all16 protected old gears plus exactly one fixed pair gear;8 original tasks×3 original policies×8 blocks.',
        'fixed_before_new_outcomes': ['selected gear', 'race-specific scale', 'all8 block seeds', 'tasks', 'policies', 'support'],
        'unchanged_anchors': 'Use original baseline-v1 discovery numeric caps, scales and protected source registry. Do not reanchor to fresh old estimates to rescue feasibility.',
        'old_physics': 'Old equipment has no research_variants entry. The fixed new pair scales only item19019 weapon min/max; all original native effects, speed and stats remain unchanged.',
        'inference': 'Parent analysis aggregates4096 DPS samples per context and8 independent block summaries for paired behavior/resource diagnostics; selected confirmation, not a broad parameter search.',
        'reference_domain_sha256': canonical_hash(full), 'measured_ecosystems_sha256': canonical_hash(domain),
        'configuration_sha256': canonical_hash(cfg), 'binary_sha256': file_hash(binary),
        'source_hashes': {str(Path(__file__).relative_to(SOURCE_ROOT)): file_hash(Path(__file__))}}
    run = root/'runs/r4-foundational-discovery'/RUN_ID
    run.mkdir(parents=True, exist_ok=True)
    freeze = run/'HIGH_PRECISION_CERTIFICATE_DESIGN.json'
    if freeze.exists():
        assert json.loads(freeze.read_text())['science'] == science
    else:
        atomic_json(freeze, {'utc': datetime.now(timezone.utc).isoformat(), 'science': science,
                            'status': 'frozen_before_new_block_outcomes'})
    for name, obj in [('BASE_ECOSYSTEMS.json', domain), ('FULL_REFERENCE_ECOSYSTEMS.json', full)]:
        path = run/name
        if path.exists(): assert json.loads(path.read_text()) == obj
        else: atomic_json(path, obj)
    config_text = yaml.safe_dump(cfg, sort_keys=False)
    config = run/'CONFIG.yaml'
    if config.exists(): assert config.read_text() == config_text
    else: config.write_text(config_text)
    source = Path(__file__)
    destination = run/'source'/source.relative_to(SOURCE_ROOT)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists(): assert file_hash(destination) == file_hash(source)
    else: shutil.copy2(source, destination)
    jobs = []
    for (race, scale), block, gear_id, task, strategy in itertools.product(
            CERTIFICATES, range(8), support, domain['tasks'], domain['strategies']):
        gear = domain['gears'][gear_id]['gear']
        value = make_input(gear, task, strategy, race, BLOCK_SEEDS[block], 512, cfg)
        if gear_id == GEAR_ID:
            value['research_variants'] = [{'item_id':19019, 'weapon_damage_scale':scale}]
        jobs.append({'input':value, 'meta':{
            'gear_id':gear_id, 'pool':'timing_shared', 'pools':['timing_shared'],
            'race':race, 'task':task['id'], 'strategy':strategy['id'], 'block':block,
            'seed_start':BLOCK_SEEDS[block], 'weapon_damage_scale':scale,
            'certificate_id':race+'_tf_'+str(scale), 'selected_pair_witness':gear_id==GEAR_ID,
            'world':'research_new_item_reward', 'stage':'selected_certificate_precision'}})
    assert len(jobs)==6528 and len({canonical_hash(j['input']) for j in jobs})==6528
    print(json.dumps({'jobs':len(jobs), 'physical_battles':len(jobs)*512}), flush=True)
    run_jobs(jobs, RUN_ID, binary=binary, scientific_protocol=science,
             workers=args.workers, resume=args.resume)
    print(run, flush=True)


if __name__ == '__main__': main()
