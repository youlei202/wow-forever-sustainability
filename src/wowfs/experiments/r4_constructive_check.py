"""Verify actual native variant application; no additional combat execution."""
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import gzip
import json
from pathlib import Path

from wowfs.paths import setup_paths, atomic_json, canonical_hash


def check_native(pair):
    key, row = pair
    folder = Path(row['cache_directory'])
    request = json.loads((folder/'input.json').read_text())
    with gzip.open(folder/'output.json.gz', 'rt') as stream:
        raw = json.load(stream)
    specifications = request.get('research_variants', [])
    applied = raw['wowfsResearchVariants']
    assert len(applied) == len(specifications)
    for specification, metadata in zip(specifications, applied):
        assert specification == metadata['specification']
        before, after = metadata['native_item_before'], metadata['research_item_after']
        scale = specification['weapon_damage_scale']
        assert before['ID'] == after['ID'] == 19019
        assert after['WeaponDamageMin'] == before['WeaponDamageMin']*scale
        assert after['WeaponDamageMax'] == before['WeaponDamageMax']*scale
        for field in before:
            if field not in {'WeaponDamageMin', 'WeaponDamageMax'}:
                assert before[field] == after[field], field
        assert metadata['resolved_effects'] == {
            'proc_ppm': 6, 'proc_damage': 300, 'nature_resistance_reduction': 25}
    return key, bool(applied)


def ordered(records):
    return sorted(records, key=lambda x: canonical_hash(x['id']))


def main():
    root = setup_paths()
    run = root/'runs/r4-foundational-discovery/constructive-reward-v1'
    results = json.loads((run/'RESULTS.json').read_text())
    assert not results['errors'] and all(results['rows'])
    rows = results['rows']
    unique = {r['cache_key']: r for r in rows}
    metadata_counts = defaultdict(int)
    with ThreadPoolExecutor(max_workers=16) as executor:
        for _, applied in executor.map(check_native, unique.items()):
            metadata_counts['variant_cells' if applied else 'unchanged_cells'] += 1
    groups = defaultdict(dict)
    for row in rows:
        groups[(row['gear_id'], row['race'], row['task'], row['strategy'])][row['weapon_damage_scale']] = row
    changed_actions = changed_resources = changed_auras = 0
    maximal_affine_residual = 0.
    for group in groups.values():
        assert set(group) == {.5, .75, 1., 1.25}
        reference = group[.5]
        actions = {k: v['casts'] for k, v in reference['actions'].items()}
        changed_actions += any({k: v['casts'] for k,v in r['actions'].items()} != actions for r in group.values())
        changed_resources += any(ordered(r['resources']) != ordered(reference['resources']) for r in group.values())
        changed_auras += any(ordered(r['auras']) != ordered(reference['auras']) for r in group.values())
        low, high = reference['dps_samples'], group[1.25]['dps_samples']
        for scale in (.75, 1.):
            weight = (scale-.5)/.75
            residual = max(abs(y-((1-weight)*a+weight*b))
                for y,a,b in zip(group[scale]['dps_samples'],low,high))
            maximal_affine_residual = max(maximal_affine_residual, residual)
    result = {
        'status': 'all_actual_variant_metadata_verified', 'additional_native_battles': 0,
        'logical_cells': len(rows), 'unique_physical_output_keys': len(unique),
        'metadata_counts': dict(metadata_counts), 'matched_gear_context_groups': len(groups),
        'groups_with_changed_action_cast_means': changed_actions,
        'groups_with_changed_resource_summaries': changed_resources,
        'groups_with_changed_aura_summaries': changed_auras,
        'max_per_seed_affine_dps_residual': maximal_affine_residual,
        'scope': 'Direct native before/after metadata check for every distinct output; reward/control diagnostic only, not an admission result.',
        'nature_resistance_caveat': 'Resolved metadata retains intended25, but native aura-label collision makes that NR callback a no-op; attack-speed slow and Nature damage remain native.'}
    atomic_json(run/'APPLIED_VARIANT_CHECK.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
