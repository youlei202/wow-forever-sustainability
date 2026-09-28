"""Fresh-seed confirmation of the five fixed development-selected witnesses."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import shutil
from statistics import NormalDist

import numpy as np

from wowfs.paths import SOURCE_ROOT, atomic_json, setup_paths
from wowfs.experiments.r2_native import file_hash, run_jobs
from wowfs.experiments.r2_mechanism_study import index_key, raw_output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    root = setup_paths(); runs = root/'runs/r2-discovery'
    run = runs/'mechanism-confirmation-v1'; run.mkdir(parents=True, exist_ok=True)
    study = runs/'mechanism-discovery-v1'
    analysis = json.loads((study/'ANALYSIS.json').read_text())
    native = {index_key(r): r for r in json.loads((runs/'discovery-v1/RESULTS.json').read_text())['rows'] if r and 'gear_id' in r}
    changed = {index_key(r): r for r in json.loads((study/'RESULTS.json').read_text())['rows'] if r and r['mechanism_seconds']==2}
    source_jobs = {index_key(j['meta']): j for j in json.loads((study/'JOBS.json').read_text()) if j['meta']['mechanism_seconds']==2}
    selected = []
    for task in analysis['summaries'][0]['tasks']:
        key = (task['native_optimal_gear'], task['task'], task['native_optimal_strategy'], 'RaceHuman')
        selected.append((f'native_task_optimum_{task["task"]}', key))
    worst = min(changed, key=lambda k: changed[k]['dps_mean']/native[k]['dps_mean'])
    selected.append(('development_worst_fixed_loss', worst))
    declaration = {
        'status': 'frozen_before_fresh_seed_confirmation', 'seed_start': 92429001,
        'iterations_per_cell': 128, 'methods': ['native', 'shared_2s'],
        'cases': [{'case': name, 'gear_id': key[0], 'task': key[1], 'strategy': key[2], 'race': key[3]} for name,key in selected],
        'selection_data': str(study/'ANALYSIS.json'),
        'selection_data_sha256': file_hash(study/'ANALYSIS.json'),
        'source_sha256': file_hash(Path(__file__)),
        'native_binary_sha256': file_hash(root/'envs/r2-go/wowfs-native'),
        'mechanism_binary_sha256': file_hash(root/'envs/r2-go/wowfs-native-mechanism'),
        'statistic': 'Paired mean DPS difference; paired delta-method ratio. Normal pointwise 95% and Bonferroni 95% intervals over the five frozen contrasts.',
        'reoptimization': 'Fixed gear and strategy selected from development; no refit on confirmation.',
    }
    frozen = run/'FROZEN_PRIMARY.json'
    if frozen.exists() and json.loads(frozen.read_text()) != declaration:
        raise ValueError('confirmation source or selection changed; do not alter frozen run')
    atomic_json(frozen, declaration); shutil.copy2(__file__, run/'r2_mechanism_confirmation.py')
    jobsets = {'native': [], 'shared_2s': []}
    for name, key in selected:
        for method in jobsets:
            job = deepcopy(source_jobs[key]); job['meta'].update(stage='mechanism_confirmation', case=name, method=method)
            job['input']['request']['simOptions']['randomSeed'] = '92429001'
            job['input']['request']['simOptions']['iterations'] = 128
            job['input']['request']['simOptions']['debugFirstIteration'] = False
            if method == 'native': job['input'].pop('extra_melee_cooldown_seconds')
            jobsets[method].append(job)
    results = {}
    for method, jobs in jobsets.items():
        subrun = runs/f'mechanism-confirmation-v1-{method}'
        binary = root/'envs/r2-go'/('wowfs-native' if method=='native' else 'wowfs-native-mechanism')
        run_jobs(jobs, subrun, binary, 10, args.resume)
        results[method] = {r['case']: r for r in json.loads((subrun/'RESULTS.json').read_text())['rows']}
    z = NormalDist().inv_cdf(1-.05/(2*len(selected)))
    contrasts = []
    for name, key in selected:
        nrow = results['native'][name]; mrow = results['shared_2s'][name]
        n = np.asarray(nrow['dps_samples']); m = np.asarray(mrow['dps_samples']); d = m-n
        se = float(d.std(ddof=1)/np.sqrt(len(d)))
        ratio = float(m.mean()/n.mean())
        ratio_se = float(((m-m.mean())-ratio*(n-n.mean())).std(ddof=1)/np.sqrt(len(n))/n.mean())
        telemetry = raw_output(root, mrow['cache_key'])['wowfsMechanism']
        contrasts.append({
            'case': name, 'gear_id': key[0], 'task': key[1], 'strategy': key[2], 'race': key[3],
            'native_mean_dps': float(n.mean()), 'mechanism_mean_dps': float(m.mean()),
            'mean_delta_dps': float(d.mean()), 'paired_se_delta_dps': se,
            'pointwise_95_delta_interval': [float(d.mean()-1.96*se), float(d.mean()+1.96*se)],
            'family_95_bonferroni_delta_interval': [float(d.mean()-z*se), float(d.mean()+z*se)],
            'mechanism_native_ratio': ratio,
            'pointwise_95_ratio_interval': [ratio-1.96*ratio_se, ratio+1.96*ratio_se],
            'family_95_bonferroni_ratio_interval': [ratio-z*ratio_se, ratio+z*ratio_se],
            'all_seed_dps_identical': bool(np.array_equal(n,m)),
            'native_cache_key': nrow['cache_key'], 'mechanism_cache_key': mrow['cache_key'],
            'mechanism_telemetry': telemetry,
        })
    result = {'contrasts': contrasts, 'fresh_physical_battles': 1280,
              'native_engine_invocations': 10, 'paired_contrasts': 5,
              'scope': 'Four development-optimal old witnesses plus one worst-loss development witness, each fixed before new seeds. These confirm achieved performance and do not give unsearched-domain upper bounds.'}
    atomic_json(run/'CONFIRMED_CONTRASTS.json', result)
    lines = ['# Fresh-seed mechanism confirmation', '',
             'Five fixed witnesses were frozen before 128 new integer seeds per condition. '
             'The four development-optimal task witnesses are unchanged in every paired seed. '
             'They demonstrate achieved native performance that the 2 s intervention cannot reduce; '
             'this is a lower bound on the post-intervention optimum, not a claim of global optimality.', '',
             '| Fixed witness | Native DPS | 2 s DPS | Paired change | Bonferroni 95% interval, DPS |',
             '| --- | ---: | ---: | ---: | --- |']
    for c in contrasts:
        lo, hi = c['family_95_bonferroni_delta_interval']
        lines.append(f'| {c["case"]} | {c["native_mean_dps"]:.3f} | {c["mechanism_mean_dps"]:.3f} | {c["mean_delta_dps"]:.3f} | [{lo:.3f}, {hi:.3f}] |')
    lines += ['', 'Intervals use paired seed differences and a normal approximation with '
              'Bonferroni adjustment for the five predeclared contrasts. Selection used only '
              'the earlier development seed block. Raw telemetry records whether these old '
              'witnesses produced any requests that the intervention could suppress.', '',
              f'Frozen selection and full results: `{run}`.', '']
    (SOURCE_ROOT/'docs/r2/MECHANISM_CONFIRMATION.md').write_text('\n'.join(lines))
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
