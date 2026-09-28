"""Frozen native mechanism grids, separate from capacity confirmation."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path

import numpy as np

from wowfs.paths import SOURCE_ROOT, setup_paths, atomic_json, canonical_hash
from wowfs.experiments.fc_native import (
    STAGE, contexts, presets, engine_root, make_input, validate_equipment, run_jobs,
)
from wowfs.experiments.fc_calibration import all_controls, damage_channels, resource_rates, CHANNELS
from wowfs.experiments.r2_native import SLOTS, file_hash
from wowfs.experiments.r3_affine import raw, trace_events

CONFIG = SOURCE_ROOT / 'configs/fc_mechanisms.json'


def load_grid():
    cfg = json.loads(CONFIG.read_text())
    main = json.loads((SOURCE_ROOT / cfg['task_source']).read_text())
    tasks = main['tasks']
    if [t['id'] for t in tasks] != cfg['tasks']:
        raise ValueError('Mechanism grid must use the same frozen eight tasks')
    return cfg, main


def override(parameter, amount, fixed=None):
    value = deepcopy(fixed or {})
    if parameter.startswith('Stat'):
        value['stats'] = {parameter: float(amount)}
    else:
        value[parameter] = float(amount)
    return value


def mechanism_input(context, task, family, i, j, cfg):
    value = make_input(context, task, seed=cfg['seed'], iterations=cfg['iterations'], debug=True)
    items = value['request']['raid']['parties'][0]['players'][0]['equipment']['items']
    variants = []
    for side, index in (('primary', i), ('partner', j)):
        slot = SLOTS.index(family[side + '_slot'])
        item_id = family[side + '_item_id']
        # Existing entries retain suffixes/enchants. A deliberately new base item
        # receives no transferred enchant or suffix from the replaced item.
        if items[slot]['id'] != item_id:
            items[slot] = {'id': item_id}
        params = override(family[side + '_parameter'], family[side + '_values'][index],
                          family.get(side + '_fixed_parameters'))
        variants.append({'item_id': item_id, **params})
    value['research_variants'] = variants
    validate_equipment(value)
    return value


def prepare():
    cfg, main = load_grid()
    jobs = []
    selected_contexts = []
    for family in cfg['families']:
        cs = [c for c in contexts() if c['class'] == family['class'] and c['race_label'] in family['races']]
        if len(cs) != 2 or {c['faction'] for c in cs} != {'Alliance', 'Horde'}:
            raise ValueError('Each mechanism requires exactly one legal context per faction')
        selected_contexts.extend(cs)
        for context in cs:
            for task in main['tasks']:
                for i, primary in enumerate(family['primary_values']):
                    for j, partner in enumerate(family['partner_values']):
                        jobs.append({'input': mechanism_input(context, task, family, i, j, cfg),
                                     'meta': {**context, 'family': family['id'], 'task': task['id'],
                                              'strategy': presets()[context['class']]['apl'],
                                              'primary_index': i, 'partner_index': j,
                                              'primary_value': primary, 'partner_value': partner,
                                              'is_reference_primary': i == family['reference_primary_index']}})
    if len(jobs) != 1440:
        raise ValueError('Expected complete 6-context x 8-task x 6-primary x 5-partner grid')
    return cfg, main, selected_contexts, jobs


def analyze(run):
    protocol = json.loads((run / 'PROTOCOL.json').read_text())
    science = protocol['science']; cfg = science['grid']
    durations = {t['id']: t['duration'] for t in science['main_protocol']['tasks']}
    families = {f['id']: f for f in cfg['families']}
    data = json.loads((run / 'RESULTS.json').read_text())
    if data['errors'] or any(row is None for row in data['rows']):
        raise ValueError('Preserve failed/incomplete calibration; cannot analyze as complete')
    rows, groups = [], {}
    for result in data['rows']:
        output = raw(result)
        control_hash = canonical_hash(all_controls(output))
        row = {k: result[k] for k in ('family', 'context_id', 'class', 'faction', 'race', 'task',
            'primary_index', 'partner_index', 'primary_value', 'partner_value',
            'is_reference_primary', 'dps_mean', 'dps_se', 'iterations', 'cache_key', 'cache_directory')}
        duration = durations[result['task']]
        channels = damage_channels(output, duration)
        row.update(control_sha256=control_hash,
                   first_seed_event_sha256=canonical_hash(trace_events(output.get('logs', ''))),
                   damage_channels=channels.tolist(),
                   damage_partition_residual=float(abs(channels.sum() - result['dps_mean'])),
                   resources=resource_rates(output, duration))
        rows.append(row)
        groups.setdefault((result['family'], result['context_id'], result['task']), {})[
            (result['primary_index'], result['partner_index'])] = (result, row)
    checks = []
    for (family_id, context_id, task), cells in sorted(groups.items()):
        family = families[family_id]
        xs, ys = family['primary_values'], family['partner_values']
        if len(cells) != len(xs) * len(ys):
            raise ValueError('Incomplete native cross-product')
        means = np.array([[cells[i, j][0]['dps_mean'] for j in range(len(ys))] for i in range(len(xs))])
        primary_checks = []
        for i, x in enumerate(xs):
            low = np.asarray(cells[i, 0][0]['dps_samples'])
            high = np.asarray(cells[i, len(ys)-1][0]['dps_samples'])
            slope = (high-low) / (ys[-1]-ys[0])
            residuals = []
            for j in range(1, len(ys)-1):
                actual = np.asarray(cells[i, j][0]['dps_samples'])
                residuals.append(float(np.max(abs(actual-(low+slope*(ys[j]-ys[0]))))))
            same_controls = len({cells[i, j][1]['control_sha256'] for j in range(len(ys))}) == 1
            same_trace = len({cells[i, j][1]['first_seed_event_sha256'] for j in range(len(ys))}) == 1
            primary_checks.append({'primary_index': i, 'primary_value': x,
                'partner_endpoint_mean_slope': float(slope.mean()),
                'max_partner_heldout_per_seed_residual': max(residuals),
                'partner_affinity_validated': max(residuals) <= cfg['residual_tolerance'],
                'partner_controls_identical': same_controls,
                'partner_first_seed_events_identical': same_trace})
        reference = family['reference_primary_index']
        controls_change = any(cells[i, j][1]['control_sha256'] != cells[reference, j][1]['control_sha256']
                              for i in range(len(xs)) for j in range(len(ys)))
        mixed = means-means[:, [0]]-means[[0], :]+means[0, 0]
        checks.append({'family': family_id, 'context_id': context_id, 'task': task,
            'mean_dps_grid': means.tolist(), 'primary_checks': primary_checks,
            'all_partner_affinity_validated': all(c['partner_affinity_validated'] for c in primary_checks),
            'all_partner_controls_identical': all(c['partner_controls_identical'] for c in primary_checks),
            'primary_changes_control_metrics': controls_change,
            'largest_primary_mean_range_at_fixed_partner': float(np.ptp(means, axis=0).max()),
            'max_absolute_mixed_mean_contrast': float(abs(mixed).max()),
            'reference_primary_index': reference,
            'reference_partner_response_spectrum': means[reference].tolist(),
            'scope': 'Development grid; a mixed contrast diagnoses response coupling, not superadditivity or capacity.'})
    summary = []
    for family in cfg['families']:
        cs = [c for c in checks if c['family'] == family['id']]
        summary.append({'family': family['id'], 'context_tasks': len(cs),
                        'context_tasks_with_primary_control_changes': sum(c['primary_changes_control_metrics'] for c in cs),
                        'context_tasks_with_partner_affinity': sum(c['all_partner_affinity_validated'] for c in cs),
                        'max_partner_residual': max(p['max_partner_heldout_per_seed_residual'] for c in cs for p in c['primary_checks']),
                        'largest_primary_response_range': max(c['largest_primary_mean_range_at_fixed_partner'] for c in cs)})
    artifact = {'schema': 1, 'scope': cfg['scope'], 'run': str(run),
                'protocol_sha256': file_hash(run/'PROTOCOL.json'), 'results_sha256': file_hash(run/'RESULTS.json'),
                'cells': len(rows), 'physical_battles': sum(r['iterations'] for r in rows),
                'damage_channel_names': CHANNELS, 'families': summary, 'checks': checks, 'rows': rows,
                'capacity_status': 'not_run; matched ecologies and prospective predictions require a separate freeze',
                'max_damage_partition_residual': max(r['damage_partition_residual'] for r in rows),
                'inference': '32 coupled development seeds per cell. Not independent confirmation, not a continuous-domain certificate.'}
    atomic_json(run/'MECHANISM_CALIBRATION.json', artifact)
    atomic_json(setup_paths()/'artifacts'/STAGE/'MECHANISM_CALIBRATION.json', artifact)
    print(json.dumps({k: v for k, v in artifact.items() if k not in ('checks', 'rows')}, indent=2), flush=True)
    return artifact


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', type=int, default=32)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--analyze-only', action='store_true')
    args = parser.parse_args()
    cfg, main_cfg, cs, jobs = prepare()
    run = setup_paths()/'runs'/STAGE/cfg['run_id']
    if args.prepare_only:
        print(json.dumps({'cells': len(jobs), 'battles': sum(j['input']['request']['simOptions']['iterations'] for j in jobs),
                          'contexts': [c['context_id'] for c in cs], 'jobs_sha256': canonical_hash(jobs)}, indent=2))
        return
    if args.analyze_only:
        analyze(run); return
    inputs = {p[k]: engine_root()/p[k] for c in cs for p in [presets()[c['class']]] for k in ('gear', 'apl')}
    for source in ('sim/core/wowfs_r3_variants.go', 'sim/core/ruleset.go', 'sim/core/mana.go',
                   'sim/common/item_effects.go', 'sim/rogue/talents.go', 'sim/mage/talents.go'):
        inputs['native-source/'+source] = engine_root()/source
    science = {'purpose': cfg['scope'], 'grid': cfg, 'main_protocol': main_cfg, 'contexts': cs,
               'presets': {c['class']: presets()[c['class']] for c in cs},
               'equipment': 'Original preset entries retained when base ID is unchanged; Rogue MH replacement explicitly removes its old enchant and original set membership.',
               'confirmation': 'No future update outcomes or capacity confirmation in this run.'}
    run = run_jobs(jobs, cfg['run_id'], science, workers=args.workers, resume=args.resume,
                   source_paths=[Path(__file__), CONFIG, SOURCE_ROOT/cfg['task_source'],
                       SOURCE_ROOT/'configs/fc_presets.json', SOURCE_ROOT/'configs/official_contexts.yaml',
                       SOURCE_ROOT/'src/wowfs/experiments/fc_calibration.py',
                       SOURCE_ROOT/'src/wowfs/experiments/r3_affine.py'], input_artifacts=inputs)
    analyze(run)


if __name__ == '__main__':
    main()
