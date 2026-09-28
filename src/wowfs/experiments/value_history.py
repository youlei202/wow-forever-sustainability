"""Decision-value screening of cached native R4 release/history domains.

No native simulations and no changes to earlier runs. Each reported value
reoptimizes every admitted gear and every declared native policy per task.
"""
from __future__ import annotations

import argparse
from itertools import combinations
import json
from pathlib import Path
import shutil
import numpy as np

from wowfs.paths import setup_paths, atomic_json
from wowfs.experiments.r2_native import file_hash
from wowfs.experiments.r2_sequence_analysis import write_csv
from wowfs.experiments.r4_data import load_ecologies
from wowfs.experiments.r4_feasibility import evaluate_admission

POOLS = ('resource_haste', 'timing_extra', 'timing_shared', 'static_skill')
GAIN = .01
MASS = .125
CURVE = (.0025, .005, .01, .02)


def decision_gain(problem, admitted, baseline=None):
    p = problem
    admitted = np.asarray(admitted, bool)
    old = p.best[p.protected].max(axis=0) if baseline is None else np.asarray(baseline, float)
    value = p.best[admitted].max(axis=0)
    gain = value - old
    relative = gain / p.scale
    mass = float(p.weights @ (relative >= GAIN - p.tolerance))
    return {'old_reoptimized': old.tolist(), 'new_reoptimized': value.tolist(),
            'gain': gain.tolist(), 'normalized_gain': relative.tolist(),
            'gain_mass': mass, 'G': mass >= MASS - p.tolerance,
            'max_normalized_gain': float(relative.max()),
            'weighted_normalized_gain': float(p.weights @ relative),
            'gain_mass_curve': {str(x): float(p.weights @ (relative >= x - p.tolerance)) for x in CURVE}}


def deletion_records(p, admitted, release):
    full = p.best[admitted].max(axis=0)
    output = []
    for source in release:
        remaining = admitted & np.array([str(source) not in ss for ss in p.sources])
        if not np.any(remaining):
            raise ValueError('Deleting a current-new source must retain the complete old domain')
        removed = p.best[remaining].max(axis=0)
        output.append({'deleted_source': str(source), 'without_source_reoptimized': removed.tolist(),
                       'deletion_effect': (full - removed).tolist(),
                       'max_normalized_deletion_effect': float(np.max((full - removed) / p.scale))})
    return output


def screen(e, previous):
    old_details = {tuple(x['release_items']): x for x in previous.get('details', [])}
    records, details = [], []
    for size in (1, 2, 3):
        for release in combinations(e.new_items, size):
            p, indices = e.problem(release, archive=e.initial_archive())
            candidates = [('natural_complete', np.ones(len(indices), bool)),
                          ('all_power_safe', p.safe | p.protected)]
            cached = old_details.get(release, {}).get('subset', {})
            if cached.get('feasible'):
                legacy_indices = old_details[release]['indices']
                if list(indices) != legacy_indices:
                    raise ValueError('Cached subset indices do not match immutable native catalogue')
                candidates.append(('cached_R4_subset', np.asarray(cached['admitted'], bool)))
            upper = decision_gain(p, p.safe | p.protected)
            for method, mask in candidates:
                metrics = evaluate_admission(p, mask)
                gain = decision_gain(p, mask)
                record = {'ecology': e.pool['id'], 'race': e.race, 'release_items': list(release),
                          'release_size': size, 'method': method, 'initial_gears': int(e.initial.sum()),
                          'policies': len(e.policies), 'tasks': len(e.tasks),
                          'candidate_gears': len(indices), 'admitted_gears': int(mask.sum()),
                          'registered_initial_sources': len(e.protected_sources),
                          **{k: metrics[k] for k in ('P', 'N', 'D', 'L', 'H', 'C', 'K')},
                          **gain, 'joint_with_G': bool(metrics['joint_pass'] and gain['G']),
                          'G_impossible_under_any_safe_subset': not upper['G'],
                          'safe_gain_upper': upper['normalized_gain'],
                          'min_normalized_cap_slack': float(np.min(np.asarray(metrics['cap_slack']) / e.scale)),
                          'worst_source_mass': metrics['worst_protected_source_mass'],
                          'point_native_samples': int(e.samples.shape[-1]),
                          'scope': 'Cached native development means; no independent or population confirmation.'}
                records.append(record)
                details.append({'row': record, 'global_admitted_indices': indices[mask].tolist(),
                                'admitted_gear_ids': [e.gear_ids[i] for i in indices[mask]],
                                'metrics': metrics, 'deletions': deletion_records(p, mask, release)})
    lookup = {(tuple(x['release_items']), x['method']): x for x in records}
    positives = []
    for record in records:
        release = tuple(record['release_items'])
        if len(release) < 2 or not record['joint_with_G']:
            continue
        singles = [lookup[((s,), 'all_power_safe')] for s in release]
        record['all_single_G_impossible'] = all(x['G_impossible_under_any_safe_subset'] for x in singles)
        record['no_single_same_method_joint_G'] = all(
            not lookup.get(((s,), record['method']), {}).get('joint_with_G', False) for s in release)
        record['no_single_same_method_scope'] = 'Only evaluated admissions; absence of a solver witness is not infeasibility.'
        singleton_sum = np.sum([x['gain'] for x in singles], axis=0)
        record['batch_minus_sum_single_safe_gain'] = (np.asarray(record['gain']) - singleton_sum).tolist()
        positives.append(record)
    return {'ecology': e.pool['id'], 'race': e.race, 'rows': records, 'details': details,
            'positive_batches': positives, 'complete': True}


def main():
    root = setup_paths()
    parser = argparse.ArgumentParser()
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    native = root / 'runs/r4-foundational-discovery/baseline-v1'
    old = root / 'runs/r4-foundational-discovery/batch-screen-v1'
    directory = root / 'runs/decisive-value/history-screen-v1'
    out = root / 'artifacts/decisive-value'
    directory.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    protocol = {'pools': POOLS, 'epsilon_gain': GAIN, 'rho_gain': MASS, 'curve': CURVE,
                'Q': 'All eight existing R4 tasks, equal weights, task known before combat; fixed gear through encounter; all three declared policies equally available.',
                'old': 'Every initial gear and policy reoptimized; fixed initial scales/caps. No old-only options removed.',
                'P_N_D_L_H_C': 'Unchanged R4: epsilon=.05,delta=.05,K4,coverage=.95.',
                'release_sizes': [1, 2, 3], 'native_calls': 0,
                'native_results_sha256': file_hash(native / 'RESULTS.json'),
                'source_sha256': file_hash(Path(__file__))}
    path = directory / 'PROTOCOL.json'
    if path.exists():
        if not args.resume or json.loads(path.read_text()) != json.loads(json.dumps(protocol)):
            raise ValueError('Resume requires identical source and protocol')
    else:
        atomic_json(path, protocol)
        shutil.copy2(Path(__file__), directory / Path(__file__).name)
    done = []
    for e in load_ecologies(native):
        if e.pool['id'] not in POOLS:
            continue
        name = e.pool['id'] + '__' + e.race + '.json'
        checkpoint = directory / name
        if args.resume and checkpoint.exists():
            result = json.loads(checkpoint.read_text())
        else:
            previous = json.loads((old / name).read_text()) if (old / name).exists() else {}
            result = screen(e, previous)
            atomic_json(checkpoint, result)
        done.append(result)
        print(json.dumps({'context': name, 'evaluations': len(result['rows']),
                          'joint_G': sum(x['joint_with_G'] for x in result['rows']),
                          'batch_gain_dependencies': sum(x.get('all_single_G_impossible', False) for x in result['positive_batches'])}), flush=True)
    write_csv(out / 'LINE_C_RELEASE_SCREEN.csv', [r for d in done for r in d['rows']])
    atomic_json(out / 'LINE_C_RELEASE_SCREEN.json', done)
    atomic_json(out / 'LINE_C_RELEASE_SUMMARY.json', {
        'contexts': len(done), 'evaluations': sum(len(d['rows']) for d in done),
        'joint_G_by_method': {m: sum(x['joint_with_G'] for d in done for x in d['rows'] if x['method'] == m)
                              for m in ('natural_complete', 'all_power_safe', 'cached_R4_subset')},
        'all_single_G_impossible_but_batch_joint_G': [x for d in done for x in d['positive_batches'] if x['all_single_G_impossible']],
        'native_calls': 0})


if __name__ == '__main__':
    main()
