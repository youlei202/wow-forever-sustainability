"""Prespecified native physical-damage compensation at a selected batch boundary.

These are research item variants, not official items or a new admission rule.
The full old/singleton/pair domain is retained at every damage scale.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import itertools
import json
from pathlib import Path
import shutil

import yaml

from wowfs.paths import SOURCE_ROOT, setup_paths, atomic_json, canonical_hash
from wowfs.experiments.r2_native import file_hash
from wowfs.experiments.r4_native import make_input, run_jobs


RUN_ID = 'constructive-reward-v1'
SCALES = (.5, .75, 1., 1.25)
SEED = 409310001
ITERATIONS = 512
SELECTED = {18203, 19019}


def domain_and_protocol():
    root = setup_paths()
    baseline = root / 'runs/r4-foundational-discovery/baseline-v1'
    base = json.loads((baseline / 'BASE_ECOSYSTEMS.json').read_text())
    cfg = yaml.safe_load((baseline / 'source/configs/r4_ecosystems.yaml').read_text())
    original = next(p for p in base['ecosystems'] if p['id'] == 'timing_shared')
    pool = deepcopy(original)
    forbidden = set(pool['new_source_ids']) - SELECTED
    pool['terminal_gear_ids'] = [g for g in pool['terminal_gear_ids']
        if not forbidden.intersection(pool['source_ids_by_gear'][g])]
    pool['slots'] = {slot: values[:2] + [v for v in values[2:] if v in SELECTED]
                     for slot, values in pool['slots'].items()}
    pool['new_source_ids'] = sorted(SELECTED)
    pool['source_ids_by_gear'] = {g: pool['source_ids_by_gear'][g]
                                for g in pool['terminal_gear_ids']}
    pool['raw_terminal_count'] = pool['legal_terminal_count'] = 36
    assert len(pool['initial_gear_ids']) == 16
    assert len(pool['terminal_gear_ids']) == 36
    assert all(not SELECTED.intersection(base['gears'][g]['gear'].values())
               for g in pool['initial_gear_ids'])
    ecology = deepcopy(base)
    ecology['ecosystems'] = [pool]
    ecology['gears'] = {g: deepcopy(base['gears'][g]) for g in pool['terminal_gear_ids']}
    ecology['candidate_design_families'] = []
    ecology['scope'] = ('Research-only physical-damage compensation on the complete selected '
                        'timing_shared domain. Variant scale is a separate table dimension; '
                        'original source IDs are retained, not claimed official variants.')
    cfg['pools'] = [{key: value for key, value in pool.items()
                    if key in {'id', 'background', 'slots', 'fixed', 'old_choices_per_slot', 'mechanism_note'}}]
    cfg['candidate_design_families'] = []
    cfg['sampling'].update(iterations=ITERATIONS, seed_start=SEED)
    binary = root / 'envs/r3-go/wowfs-native-variants'
    source_paths = [Path(__file__), SOURCE_ROOT/'src/wowfs/simulator/r3_variants.go',
                    SOURCE_ROOT/'scripts/native_build_r3.sh']
    science = {
        'permission': 'B: explicit research-only new-item physical damage compensation; old game items/rules unchanged.',
        'selection': 'timing_shared {18203,19019} selected after native discovery and independent fixed-cap confirmation; not an unselected population.',
        'pool': 'timing_shared', 'new_item_ids': sorted(SELECTED),
        'weapon_damage_scales': list(SCALES), 'seed_start': SEED, 'iterations': ITERATIONS,
        'predictions_before_new_outcomes': [
            'Orc scale0.75 and Human scale0.5 should admit a nonempty useful safe pair region with more cap margin than the native scale1 boundary.',
            'Scale1.25 should be more cap-blocked; every failed prediction remains reported.',
            'All singleton releases are tested: weaker Thunderfury may become independently admissible, which would remove a minimum-batch claim at that scale.'
        ],
        'actual_hook': 'research_variants=[{item_id:19019,weapon_damage_scale:x}] only when19019 is equipped; scales native weapon minimum and maximum damage before actual native event simulation.',
        'fixed_physics': 'Weapon speed, all stats, proc PPM/timing/eligibility, Nature proc magnitude, target attack slow, policies and all old items are unchanged. No posthoc DPS multiplier.',
        'variant_identity': 'Full input and R3 applied-variant identity hash include item_id and scale; native IDs retained as source roles.',
        'anchor': 'Frozen baseline-v1 numeric scales/caps and protected old source registry; fresh old16 sampled at the same new seeds. Report fixed-cap results without reanchoring to obtain success.',
        'comparisons': 'Complete36 gears at each of4 scales, all8 original tasks,3 policies,2 races; inspect old, both singleton and joint release domains.',
        'limits': 'Finite-policy empirical means and sampling uncertainty; no new affine/type algorithm, no Blood Talon family, no live-server claim, no new cross-class coverage.',
        'baseline_ecosystems_sha256': canonical_hash(base),
        'measured_ecosystems_sha256': canonical_hash(ecology),
        'configuration_sha256': canonical_hash(cfg),
        'binary_sha256': file_hash(binary),
        'source_hashes': {str(p.relative_to(SOURCE_ROOT)): file_hash(p) for p in source_paths}
    }
    return ecology, cfg, science, binary, source_paths


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', type=int, default=16)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    root = setup_paths()
    ecology, cfg, science, binary, sources = domain_and_protocol()
    run = root / 'runs/r4-foundational-discovery' / RUN_ID
    run.mkdir(parents=True, exist_ok=True)
    freeze = run / 'FROZEN_CONSTRUCTIVE_PREDICTIONS.json'
    if freeze.exists():
        assert json.loads(freeze.read_text())['science'] == science, 'frozen constructive protocol differs'
    else:
        atomic_json(freeze, {'utc': datetime.now(timezone.utc).isoformat(), 'science': science,
                            'status': 'frozen_before_constructive_native_outcomes'})
    if (run/'BASE_ECOSYSTEMS.json').exists():
        assert json.loads((run/'BASE_ECOSYSTEMS.json').read_text()) == ecology
    else:
        atomic_json(run/'BASE_ECOSYSTEMS.json', ecology)
    config_text = yaml.safe_dump(cfg, sort_keys=False)
    if (run/'CONFIG.yaml').exists():
        assert (run/'CONFIG.yaml').read_text() == config_text
    else:
        (run/'CONFIG.yaml').write_text(config_text)
    for source in sources:
        destination = run/'source'/source.relative_to(SOURCE_ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            assert file_hash(destination) == file_hash(source)
        else:
            shutil.copy2(source, destination)
    jobs = []
    for scale, gear_id, task, strategy, race in itertools.product(
            SCALES, ecology['ecosystems'][0]['terminal_gear_ids'], ecology['tasks'],
            ecology['strategies'], ecology['races']):
        gear = ecology['gears'][gear_id]['gear']
        value = make_input(gear, task, strategy, race, SEED, ITERATIONS, cfg)
        if 19019 in gear.values():
            value['research_variants'] = [{'item_id': 19019, 'weapon_damage_scale': scale}]
        jobs.append({'input': value, 'meta': {
            'gear_id': gear_id, 'pool': 'timing_shared', 'pools': ['timing_shared'],
            'race': race, 'task': task['id'], 'strategy': strategy['id'],
            'weapon_damage_scale': scale, 'variant_item_id': 19019,
            'variant_spec_sha256': canonical_hash(value.get('research_variants', [])),
            'world': 'research_new_item_reward', 'stage': 'constructive_compensation'}})
    unique = len({canonical_hash(job['input']) for job in jobs})
    assert len(jobs) == 6912 and unique == 3456
    print(json.dumps({'logical_cells': len(jobs), 'unique_native_cells': unique,
                      'physical_battles': unique*ITERATIONS}), flush=True)
    run_jobs(jobs, RUN_ID, binary=binary, scientific_protocol=science,
             workers=args.workers, resume=args.resume)
    print(run, flush=True)


if __name__ == '__main__':
    main()
