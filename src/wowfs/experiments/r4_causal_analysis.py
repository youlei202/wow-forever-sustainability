"""Paired effect contrasts and full-domain qualification under frozen anchors."""
from __future__ import annotations
from itertools import combinations
import json
from pathlib import Path

import numpy as np
from scipy.stats import t as student_t

from wowfs.paths import setup_paths, atomic_json
from wowfs.experiments.r2_analysis import factorial
from wowfs.experiments.r2_native import file_hash
from wowfs.experiments.r2_sequence_analysis import behavior_vector, write_csv
from wowfs.experiments.r4_batches import solve_problem
from wowfs.experiments.r4_causal import RUN_ID
from wowfs.experiments.r4_data import Ecology, load_ecologies
from wowfs.experiments.r4_feasibility import eval_all_safe, evaluate_admission


def make_ecology(domain, rows, anchor, pool, race, mask):
    """A world includes every initial and available new gear, never a mask mix."""
    lookup = {(row['gear_id'], row['strategy'], row['task']): row for row in rows
              if row['pool'] == pool['id'] and row['race'] == race and row['mask'] == mask}
    keys = sorted(pool['terminal_gear_ids'])
    policies = [policy['id'] for policy in domain['strategies']]
    tasks = domain['tasks']
    n = next(iter(lookup.values()))['iterations']
    samples = np.empty((len(keys), len(policies), len(tasks), n))
    behavior = np.empty((*samples.shape[:3], 7))
    for gi, key in enumerate(keys):
        for pi, policy in enumerate(policies):
            for ti, task in enumerate(tasks):
                row = lookup[(key, policy, task['id'])]
                samples[gi, pi, ti] = row['dps_samples']
                behavior[gi, pi, ti] = behavior_vector(row, task['duration_seconds'])
    return Ecology(pool, race, tasks, policies, keys,
        [domain['gears'][key]['gear'] for key in keys], samples.mean(axis=-1),
        behavior, samples, [set(map(str, pool['source_ids_by_gear'][key])) for key in keys],
        np.array([key in pool['initial_gear_ids'] for key in keys]),
        tuple(map(str, pool['new_source_ids'])), anchor.scale.copy(), anchor.cap.copy(),
        anchor.protected_sources, anchor.config)


def main():
    root = setup_paths()
    run = root / 'runs/r4-foundational-discovery' / RUN_ID
    output = root / 'artifacts/r4-foundational-discovery'
    data = json.loads((run / 'RESULTS.json').read_text())
    if data['errors'] or any(row is None for row in data['rows']):
        raise ValueError('Incomplete native worlds cannot be filled with zeros')
    rows = data['rows']
    domain = json.loads((run / 'BASE_ECOSYSTEMS.json').read_text())
    anchors = {(e.pool['id'], e.race): e for e in
               load_ecologies(root / 'runs/r4-foundational-discovery/baseline-v1')}
    groups = {}
    for row in rows:
        key = (row['pool'], row['race'], row['gear_id'], row['task'], row['strategy'])
        if row['mask'] in groups.setdefault(key, {}):
            raise ValueError('Duplicate logical factorial cell')
        groups[key][row['mask']] = row
    family = len(groups)
    contrasts = []
    for key, cells in groups.items():
        contrast = factorial({mask: row['dps_samples'] for mask, row in cells.items()},
                             family=family)
        means = {mask: float(np.mean(row['dps_samples'])) for mask, row in cells.items()}
        contrasts.append(dict(zip(['pool','race','gear_id','task','strategy'], key)) | {
            **contrast, **{f'mean_{mask:02b}': means[mask] for mask in range(4)},
            'A_gain_B_off': means[1]-means[0], 'A_gain_B_on': means[3]-means[2],
            'B_gain_A_off': means[2]-means[0], 'B_gain_A_on': means[3]-means[1],
        })

    admissions, details, witnesses, one_gears = [], [], [], []
    old_checks = []
    unique_cells = len({row['cache_key'] for row in rows})
    named = {'resource_haste': '331790c18dd3a920', 'timing_shared': '26007bac9b64ca50'}
    for pool in domain['ecosystems']:
        for race in domain['races']:
            anchor = anchors[(pool['id'], race)]
            worlds = [make_ecology(domain, rows, anchor, pool, race, mask) for mask in range(4)]
            assert all(np.array_equal(worlds[0].samples[worlds[0].initial], e.samples[e.initial])
                       for e in worlds[1:])
            assert all(np.array_equal(worlds[0].behavior[worlds[0].initial], e.behavior[e.initial])
                       for e in worlds[1:])
            old_checks.append({'pool': pool['id'], 'race': race, 'initial16_bit_exact_across_masks': True,
                'fresh_old_frontier_to_frozen_scale': (worlds[0].values[worlds[0].initial].max(axis=(0,1))/anchor.scale).tolist()})
            for mask, e in enumerate(worlds):
                for size in (1, 2):
                    for release in combinations(e.new_items, size):
                        problem, indices = e.problem(release, archive=e.initial_archive())
                        full = eval_all_safe(problem)
                        solved = solve_problem(problem, 30.)
                        record = {'pool': pool['id'], 'race': race, 'mask': mask,
                            'release': list(release), 'size': size, 'subset_feasible': solved['feasible'],
                            'proved_infeasible': solved.get('proved_infeasible', False), 'status': solved['status'],
                            'necessary_failures': solved.get('necessary_failures', []),
                            'all_safe_joint': full['joint_pass'], 'all_safe_failures': full['failure_reasons'],
                            'D_mass': full['novel_task_mass'], 'worst_L': full['worst_protected_source_mass'],
                            'K': full['K'], 'cap_slack_min_DPS': min(full['cap_slack'])}
                        admissions.append(record)
                        details.append({**record, 'all_safe': full, 'subset': solved})
                        if size != 2:
                            continue
                        for g in np.flatnonzero(~problem.protected):
                            equipped_new = set(problem.sources[g]) & set(problem.new_sources)
                            if len(equipped_new) != 2:
                                continue
                            opening = problem.protected.copy(); opening[g] = True
                            direct = evaluate_admission(problem, opening)
                            frontier = problem.best[opening].max(axis=0)
                            global_g = indices[g]
                            sample = e.samples[global_g]
                            critical = student_t.ppf(1-.05/(2*unique_cells), sample.shape[-1]-1)
                            upper = sample.mean(axis=-1) + critical*sample.std(axis=-1,ddof=1)/np.sqrt(sample.shape[-1])
                            one_gears.append({'pool': pool['id'], 'race': race, 'mask': mask,
                                'gear_id': problem.gear_ids[g], 'gear': e.gears[global_g],
                                'named_pre_ablation_witness': named.get(pool['id']) == problem.gear_ids[g],
                                'metrics': direct, 'candidate_only_simultaneous_cap_slack': float(np.min(problem.cap-upper)),
                                'cap_CI_family': unique_cells,
                                'cap_CI_scope': 'Approximate simultaneous Student-t means of candidate policies/tasks against fixed numeric cap; initial H must separately remain safe.'})
                            for pi, policy in enumerate(e.policies):
                                for ti, task in enumerate(e.tasks):
                                    distance = problem.distances[g,pi,ti]
                                    margin = problem.values[g,pi,ti] - frontier[ti] + problem.tol_vector[ti]
                                    witnesses.append({'pool': pool['id'], 'race': race, 'mask': mask,
                                        'gear_id': problem.gear_ids[g], 'strategy': policy, 'task': task['id'],
                                        'D_distance': float(distance), 'competitive_margin_DPS': float(margin),
                                        'D_and_competitive': bool(distance >= problem.delta-problem.tolerance and margin >= -problem.tolerance),
                                        'candidate_safe': bool(problem.safe[g]), 'one_gear_joint': direct['joint_pass'],
                                        'mean_DPS': float(problem.values[g,pi,ti]),
                                        'behavior': e.behavior[global_g,pi,ti].tolist(),
                                        'candidate_cap_slack': float(np.min(problem.cap-problem.best[g]))})
    write_csv(output/'CAUSAL_PAIR_FACTORIALS.csv', contrasts)
    write_csv(output/'CAUSAL_PAIR_ADMISSIONS.csv', admissions)
    write_csv(output/'CAUSAL_PAIR_WITNESSES.csv', witnesses)
    atomic_json(output/'CAUSAL_PAIR_DETAILS.json', {'details':details, 'one_gear_certificates':one_gears,
        'unchanged_old_world_checks':old_checks, 'family':family,
        'scope':'Complete selected finite tables, approximate DPS intervals, empirical behavior distances; fixed baseline numeric anchors.'})
    atomic_json(run/'ANALYSIS_AUDIT.json', {'source_sha256':file_hash(Path(__file__)),
        'results_sha256':file_hash(run/'RESULTS.json'), 'logical_cells':len(rows), 'unique_cells':unique_cells,
        'factorial_family':family, 'release_world_evaluations':len(admissions), 'native_calls':0,
        'source_selection':'Three domains selected before these ablations; third added after prior fresh-seed confirmation.'})
    print(json.dumps({'factorials':family,'release_worlds':len(admissions),
        'pair_outcomes':[r for r in admissions if r['size']==2],
        'positive_interactions':sum(r['direction']=='positive' for r in contrasts),
        'negative_interactions':sum(r['direction']=='negative' for r in contrasts)},indent=2),flush=True)


if __name__ == '__main__':
    main()
