"""Develop a shared extra-melee batch resource against a common native reference.

The intervention and unrestricted baseline share exactly the same candidate
parameter set, information and deterministic selection objective. This is a
mechanism tradeoff study, not an expressive-capacity comparison.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from copy import deepcopy
import gzip
import json
from pathlib import Path
import shutil
import subprocess

import numpy as np

from wowfs.paths import SOURCE_ROOT, atomic_json, canonical_hash, setup_paths
from wowfs.experiments.r2_native import (
    engine_root, file_hash, load_config, prepare, run_jobs,
)


def index_key(row):
    return tuple(row[k] for k in ('gear_id', 'task', 'strategy', 'race'))


def interval(values):
    x = np.asarray(values, dtype=float)
    se = float(x.std(ddof=1) / np.sqrt(len(x)))
    return {'mean': float(x.mean()), 'se': se,
            'normal_95_interval': [float(x.mean()-1.96*se), float(x.mean()+1.96*se)],
            'sampling_unit': 'paired integer-seed battles within this fixed cell',
            'selection_adjusted': False}


def raw_output(root, key):
    p = root / 'cache/r2-discovery/native' / key[:2] / key / 'output.json.gz'
    with gzip.open(p, 'rt') as f:
        return json.load(f)


def sum_counts(target, source):
    for k, v in source.items():
        target[k] += v


def analyze(root, run, cfg):
    native_path = root/'runs/r2-discovery/discovery-v1/RESULTS.json'
    native_rows = [r for r in json.loads(native_path.read_text())['rows'] if r and 'gear_id' in r]
    native = {index_key(r): r for r in native_rows}
    changed = json.loads((run/'RESULTS.json').read_text())['rows']
    by_cd = {0: native}
    for cd in (1, 2):
        by_cd[cd] = {index_key(r): r for r in changed if r and r['mechanism_seconds'] == cd}
        if set(by_cd[cd]) != set(native):
            raise ValueError('mechanism and native physical configuration domains differ')
    tasks = [task['id'] for task in cfg['tasks']]
    summaries = []
    for cd, rows in by_cd.items():
        task_rows = []
        for task in tasks:
            subset = {k: r for k, r in native.items() if r['task'] == task}
            native_key = max(subset, key=lambda k: subset[k]['dps_mean'])
            best_key = max(subset, key=lambda k: rows[k]['dps_mean'])
            old = native[native_key]
            old_now = rows[native_key]
            best = rows[best_key]
            native_competitive = {r['gear_id'] for r in subset.values()
                                  if r['dps_mean'] >= .95*old['dps_mean']}
            mech_competitive = {rows[k]['gear_id'] for k in subset
                                if rows[k]['dps_mean'] >= .95*old['dps_mean']}
            task_rows.append({
                'task': task, 'native_optimal_gear': old['gear_id'],
                'native_optimal_strategy': old['strategy'],
                'native_optimal_dps': old['dps_mean'],
                'same_witness_dps_under_mechanism': old_now['dps_mean'],
                'same_witness_ratio': old_now['dps_mean']/old['dps_mean'],
                'same_witness_delta': interval(np.array(old_now['dps_samples'])-old['dps_samples']),
                'reoptimized_dps': best['dps_mean'],
                'reoptimized_gear': best['gear_id'], 'reoptimized_strategy': best['strategy'],
                'reoptimized_ratio_to_native': best['dps_mean']/old['dps_mean'],
                'native_competitive_gear_count': len(native_competitive),
                'mechanism_competitive_gear_count_common_native_threshold': len(mech_competitive),
                'retained_native_competitive_gear_count': len(native_competitive & mech_competitive),
                'finite_gear_denominator': len({r['gear_id'] for r in subset.values()}),
            })
        cell_ratios = [rows[k]['dps_mean']/native[k]['dps_mean'] for k in native]
        summaries.append({
            'cooldown_seconds': cd, 'tasks': task_rows,
            'min_fixed_old_witness_ratio': min(r['same_witness_ratio'] for r in task_rows),
            'worst_reoptimized_ratio': max(r['reoptimized_ratio_to_native'] for r in task_rows),
            'eligible_under_old_witness_retention': all(r['same_witness_ratio'] >= .95 for r in task_rows),
            'fixed_cell_ratio_quantiles_0_05_50_95_100': np.quantile(cell_ratios, [0, .05, .5, .95, 1]).tolist(),
            'fixed_cells_retaining_95pct': sum(r >= .95 for r in cell_ratios),
            'fixed_cell_denominator': len(cell_ratios),
        })
    eligible = [s for s in summaries if s['eligible_under_old_witness_retention']]
    selected = min(eligible, key=lambda s: (s['worst_reoptimized_ratio'], s['cooldown_seconds']))
    selection = {
        'selected_cooldown_seconds': selected['cooldown_seconds'],
        'candidate_seconds': [0, 1, 2],
        'decision_rule': 'Retain at least 95% of each of the four native task-optimal fixed witnesses; among eligible candidates minimize worst task-specific reoptimized envelope/native ratio; tie by smaller cooldown.',
        'generic_same_permission_selected_cooldown_seconds': selected['cooldown_seconds'],
        'generic_comparison': 'Identical candidate set, observations, initialization and objective imply exact same selection; no superiority claim.',
        'development_seed_start': 24092401, 'iterations': 32,
        'source_run': str(run), 'native_reference': str(native_path),
        'template_fixed_before_unseen_updates': True,
        'development_inference_limit': 'Selected empirical means are not fresh-seed confirmation and are not uniform safety certificates.',
    }
    telemetry = {}
    for cd in (1, 2):
        totals = defaultdict(int); sources = defaultdict(lambda: defaultdict(int))
        max_batch = 0
        for row in by_cd[cd].values():
            detail = raw_output(root, row['cache_key'])['wowfsMechanism']
            sum_counts(totals, detail['totals'])
            for source, counts in detail['by_source'].items(): sum_counts(sources[source], counts)
            max_batch = max(max_batch, detail['max_requested_batch_size'])
        telemetry[str(cd)] = {'totals': dict(totals), 'by_source': {k: dict(v) for k,v in sources.items()},
                              'maximum_observed_requested_batch_size': max_batch,
                              'finite_cell_denominator': len(by_cd[cd]),
                              'physical_battles': sum(r['iterations'] for r in by_cd[cd].values())}
    result = {'summaries': summaries, 'selection': selection, 'telemetry': telemetry,
              'denominators': {'unique_gears': len({r['gear_id'] for r in native.values()}),
                               'tasks': len(tasks), 'strategies': len(cfg['strategies']),
                               'races': sorted({r['race'] for r in native.values()}),
                               'native_cells_reused': len(native), 'mechanism_cells': len(changed)},
              'scope': 'Finite source-defined development domains. No live-server statement, whole-game upper bound, or 20-round joint-success claim.'}
    atomic_json(run/'ANALYSIS.json', result)
    atomic_json(run/'FROZEN_SELECTION.json', selection)
    return result, by_cd


def write_report(run, result):
    selected = result['selection']['selected_cooldown_seconds']
    lines = ['# Shared extra-melee resource: native development result', '',
             f'The predeclared development decision selected a shared cooldown of **{selected} seconds**.',
             'The unrestricted same-permission design search selects the identical value. '
             'This study identifies the intervention tradeoff; it provides no advantage over that strong baseline.', '',
             '| Shared cooldown | Worst retained fixed old witness | Worst reoptimized/native envelope ratio | Cells retaining 95% native DPS | Eligible |',
             '| --- | ---: | ---: | ---: | --- |']
    for s in result['summaries']:
        lines.append(f'| {s["cooldown_seconds"]} s | {s["min_fixed_old_witness_ratio"]:.4f} | '
                     f'{s["worst_reoptimized_ratio"]:.4f} | {s["fixed_cells_retaining_95pct"]}/{s["fixed_cell_denominator"]} | '
                     f'{s["eligible_under_old_witness_retention"]} |')
    lines += ['', 'The reference is the same original native performance, including unchanged old gear and strategies. '
              'Reoptimization ranges over the identical 173 legal gear configurations and three policies. '
              'Competitive gear counts use 95% of the common native task maximum, so lowering the baseline cannot manufacture reward value.', '',
              '| Cooldown | Task | Native maximum | Same old witness | Reoptimized | Native competitive gear | Competitive gear under common native threshold |',
              '| --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for s in result['summaries']:
        for task in s['tasks']:
            lines.append(f'| {s["cooldown_seconds"]} s | {task["task"]} | {task["native_optimal_dps"]:.3f} | '
                         f'{task["same_witness_dps_under_mechanism"]:.3f} | {task["reoptimized_dps"]:.3f} | '
                         f'{task["native_competitive_gear_count"]} | {task["mechanism_competitive_gear_count_common_native_threshold"]} |')
    lines += ['', 'Each nonzero candidate uses 32 labeled native integer seeds per cell. '
              'There are 173 unique gear sets × 4 damage tasks × 3 policies = 2076 cells per candidate, '
              'or 132864 newly requested physical battles across 1 s and 2 s. These are overlapping source-defined '
              'development pools, not randomly sampled independent ecosystems. The racial context here is Human Warrior.', '',
              'The rule acts after a proc requests an extra main-hand attack batch. Every source uses one '
              'per-unit cooldown; a batch of two requested attacks consumes one admission. Both immediate and stored '
              'requests are covered. Already-triggered companion auras and original proc cooldowns remain in force. '
              'It does not scale damage, change static equipment, or rewrite the behavior of old items each round.', '',
              'The count bound is on admitted requests, and requires an explicit maximum batch size to imply a '
              'requested-attack bound. Stored requests may execute later, so request-time bins do not certify '
              'emitted damage in every burst window. Cooldown zero exactly reproduces the native result in the '
              'integration comparison, including the event log.', '',
              'The selection was fixed from development data before unseen item updates. All confidence '
              'intervals in the machine-readable development analysis are descriptive paired-seed intervals '
              'and are not adjusted for selecting configurations. Independent confirmation and all joint '
              'P/N/D/L/H/C update requirements are separate evaluations.', '',
              f'Full analysis: `{run}/ANALYSIS.json`.',
              f'Frozen selection: `{run}/FROZEN_SELECTION.json`.',
              f'Inputs, outputs, binary and source hashes: `{run}/PROTOCOL.json` and `STUDY_PROTOCOL.json`.', '']
    (SOURCE_ROOT/'docs/r2/MECHANISM_FINDINGS.md').write_text('\n'.join(lines))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', default='mechanism-discovery-v1')
    parser.add_argument('--workers', type=int, default=64)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    root = setup_paths(); cfg = load_config(); engine = engine_root(root)
    template = json.loads((root/'runs/r2-discovery/native-smoke/effect.input.json').read_text())
    database = {i['id']: i for i in json.loads((engine/'assets/database/db.json').read_text())['items']}
    jobs, gears, excluded = prepare(cfg, template, engine, database, 'matrix', 24092401, 32, ['RaceHuman'])
    all_jobs = []
    for cd in (1, 2):
        for job in jobs:
            new = deepcopy(job); new['meta']['mechanism_seconds'] = cd
            new['meta']['stage'] = 'mechanism_discovery'
            new['input']['extra_melee_cooldown_seconds'] = cd
            all_jobs.append(new)
    run = root/'runs/r2-discovery'/args.run_id
    run.mkdir(parents=True, exist_ok=True)
    sources = [Path(__file__), SOURCE_ROOT/'scripts/native_build_mechanism.sh',
               SOURCE_ROOT/'src/wowfs/simulator/native_mechanism.go']
    patch = subprocess.check_output(['git', '-C', str(root/'external/mythicsim-forever-engine-r2-mechanism'), 'diff', '--', 'sim/core/attack.go'], text=True)
    protocol = {'candidate_seconds': [0,1,2], 'native_reference': 'discovery-v1',
                'selection_rule': 'Native task-optimal fixed witnesses must all retain >=95%; minimize worst reoptimized/native task envelope among eligible settings; tie smaller cooldown.',
                'generic_permissions': 'Same three candidate settings, same observations, same objective, same optimization.',
                'native_preserved': 'Original common native capability reference retained in every comparison.',
                'source_hashes': {str(p): file_hash(p) for p in sources},
                'engine_mechanism_patch': patch, 'jobs_hash': canonical_hash(all_jobs)}
    pp = run/'STUDY_PROTOCOL.json'
    if pp.exists() and json.loads(pp.read_text()) != protocol:
        raise ValueError('mechanism study source/protocol changed; choose a new run')
    atomic_json(pp, protocol)
    for p in sources: shutil.copy2(p, run/p.name)
    run_jobs(all_jobs, run, root/'envs/r2-go/wowfs-native-mechanism', args.workers, args.resume)
    atomic_json(run/'GEARS.json', {'gears': gears, 'excluded': excluded})
    result, by_cd = analyze(root, run, cfg)
    write_report(run, result)
    # Preserve one deliberately selected suppression trace. It is a mechanism
    # illustration and is not used to estimate a population frequency.
    representative = min(by_cd[2], key=lambda k: by_cd[2][k]['dps_mean']/by_cd[0][k]['dps_mean'])
    source_job = next(j for j in all_jobs if j['meta']['mechanism_seconds']==2 and index_key(j['meta'])==representative)
    trace = deepcopy(source_job); trace['meta']['stage'] = 'mechanism_selected_trace'
    trace['input']['request']['simOptions']['iterations'] = 1
    trace['input']['request']['simOptions']['debugFirstIteration'] = True
    trace_run = root/'runs/r2-discovery'/(args.run_id+'-trace')
    run_jobs([trace], trace_run, root/'envs/r2-go/wowfs-native-mechanism', 1, args.resume)
    trace_row = json.loads((trace_run/'RESULTS.json').read_text())['rows'][0]
    raw = raw_output(root, trace_row['cache_key'])
    (trace_run/'EVENTS.log').write_text(raw['logs'])
    atomic_json(trace_run/'TELEMETRY.json', raw['wowfsMechanism'])
    print(json.dumps(result['selection'], indent=2))


if __name__ == '__main__':
    main()
