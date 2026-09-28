"""Matched native release witnesses and G-qualified finite history probes."""
from functools import lru_cache
from itertools import combinations, permutations
import json
from pathlib import Path
import numpy as np

from wowfs.paths import setup_paths, atomic_json
from wowfs.experiments.r2_native import file_hash
from wowfs.experiments.r2_sequence_analysis import write_csv
from wowfs.experiments.r4_data import load_ecologies
from wowfs.experiments.r4_feasibility import evaluate_admission
from wowfs.experiments.value_history import POOLS, decision_gain

SELECTED = {
    ('resource_haste', 'RaceHuman'): [('19951', '22000')],
    ('timing_shared', 'RaceOrc'): [('18203', '19019'), ('19019', '22268')],
}


def native_witnesses(e, releases):
    records = []
    gear_lookup = {tuple(sorted(g.items())): i for i, g in enumerate(e.gears)}
    old_slot_options = {slot: sorted({e.gears[i][slot] for i in np.flatnonzero(e.initial)})
                        for slot in e.gears[0]}
    for release in releases:
        p, indices = e.problem(release, archive=e.initial_archive())
        mask = p.safe | p.protected
        gain = decision_gain(p, mask)
        for k in np.flatnonzero(np.array(gain['normalized_gain']) >= .01 - 1e-9):
            selected = p.values.copy()
            selected[~mask] = -np.inf
            gi, pi = np.unravel_index(np.argmax(selected[:, :, k]), selected[:, :, k].shape)
            global_gi = indices[gi]
            winner = e.gears[global_gi]
            slots = [next(s for s, v in winner.items() if str(v) == item) for item in release]
            if len(slots) != 2:
                continue
            baselines = []
            for a in old_slot_options[slots[0]]:
                for b in old_slot_options[slots[1]]:
                    base = {**winner, slots[0]: a, slots[1]: b}
                    key = tuple(sorted(base.items()))
                    if key in gear_lookup:
                        idx = gear_lookup[key]
                        baselines.append((e.values[idx, :, k].max(), idx, base))
            _, _, base = max(baselines, key=lambda x: (x[0], e.gear_ids[x[1]]))
            cells = []
            for flags in ((0, 0), (1, 0), (0, 1), (1, 1)):
                gear = {**base, **{slot: winner[slot] for slot, flag in zip(slots, flags) if flag}}
                idx = gear_lookup[tuple(sorted(gear.items()))]
                cells.append({'flags': list(flags), 'gear_id': e.gear_ids[idx], 'gear': gear,
                              'fixed_winner_policy': e.policies[pi],
                              'fixed_policy_DPS': e.values[idx, pi].tolist(),
                              'reoptimized_DPS': e.values[idx].max(axis=0).tolist(),
                              'normalized_cap_slack': ((e.cap - e.values[idx].max(axis=0))/e.scale).tolist()})
            values = np.array([c['fixed_policy_DPS'] for c in cells])
            opt = np.array([c['reoptimized_DPS'] for c in cells])
            records.append({'ecology': e.pool['id'], 'race': e.race, 'release': list(release),
                            'task': e.tasks[k]['id'], 'task_index': int(k),
                            'all_task_ids': [t['id'] for t in e.tasks],
                            'gain': gain, 'complete_old_optimum': e.scale.tolist(),
                            'fixed_cap': e.cap.tolist(), 'winner_gear': winner,
                            'winner_gear_id': e.gear_ids[global_gi], 'policy': e.policies[pi],
                            'matched_cells': cells,
                            'fixed_policy_pair_interaction': (values[3]-values[2]-values[1]+values[0]).tolist(),
                            'reoptimized_pair_interaction': (opt[3]-opt[2]-opt[1]+opt[0]).tolist(),
                            'scope': 'Matched real native loadouts in the complete finite cached domain; policy-max interaction is not a pure proc interaction.'})
    return records


def current_actions(e):
    result = []
    for item in e.new_items:
        p, indices = e.problem([item], archive=e.initial_archive())
        for j in np.flatnonzero(p.safe & ~p.protected):
            mask = p.protected.copy(); mask[j] = True
            gain = decision_gain(p, mask)
            if not gain['G']:
                continue
            metrics = evaluate_admission(p, mask)
            if metrics['joint_pass']:
                result.append({'item': item, 'global_index': int(indices[j]),
                               'gear_id': e.gear_ids[indices[j]], 'metrics': metrics, 'gain': gain})
    return result


def exact_continuation(e, first, futures):
    start = e.initial.copy(); start[first['global_index']] = True
    initial_registry = tuple(sorted(set(e.protected_sources) | {
        s for s, mass in first['metrics']['source_masses'].items() if mass >= .05 - 1e-9}))
    @lru_cache(None)
    def actions(old_indices, registry, released, item):
        old = np.zeros(len(e.gear_ids), bool); old[list(old_indices)] = True
        p, indices = e.problem([item], protected=old, old_released=released, protected_sources=registry)
        result = []
        for j in np.flatnonzero(p.safe & ~p.protected):
            mask = p.protected.copy(); mask[j] = True
            if not decision_gain(p, mask)['G']:
                continue
            metrics = evaluate_admission(p, mask)
            if not metrics['joint_pass']:
                continue
            new = old.copy(); new[indices[j]] = True
            registered = tuple(sorted(set(registry) | {
                s for s, mass in metrics['source_masses'].items() if mass >= .05 - 1e-9}))
            result.append((tuple(np.flatnonzero(new)), registered))
        return tuple(result)
    @lru_cache(None)
    def length(old_indices, registry, released, future):
        if not future:
            return 0
        choices = actions(old_indices, registry, released, future[0])
        if not choices:
            return 0
        next_release = tuple(sorted(set(released) | {future[0]}))
        return 1 + max(length(old, reg, next_release, future[1:]) for old, reg in choices)
    paths = [{'sequence': list(seq), 'max_successful_steps': length(
        tuple(np.flatnonzero(start)), initial_registry, (first['item'],), seq)}
             for seq in permutations(futures)]
    return {'Psi': {str(h): (sum(x['max_successful_steps'] >= h for x in paths)/len(paths)
                             if h <= len(futures) else None) for h in (1, 3, 5)},
            'paths': paths, 'unique_state_arrival_problems': actions.cache_info().currsize,
            'unique_state_sequence_problems': length.cache_info().currsize,
            'scope': 'Exact offline existential continuation for the finite H-plus-one-new-gear action library; every wave requires fresh G>=1% on at least one task and original six metrics. Not arbitrary subset or online optimality.'}


def branch_probe(e):
    actions = current_actions(e); candidates = []
    for a, b in combinations(actions, 2):
        if a['item'] != b['item'] or a['metrics']['K'] != b['metrics']['K']:
            continue
        distance = float(np.max(abs(np.array(a['metrics']['optimum'])-b['metrics']['optimum'])/e.scale))
        masses = sorted(set(a['metrics']['source_masses']) | set(b['metrics']['source_masses']))
        mass = max(abs(a['metrics']['source_masses'].get(s, 0)-b['metrics']['source_masses'].get(s, 0)) for s in masses)
        candidates.append((distance, mass, a['gear_id'], b['gear_id'], a, b))
    output = {'ecology': e.pool['id'], 'race': e.race, 'current_actions': actions,
              'current_action_count': len(actions), 'current_pair_count': len(candidates), 'status': 'no_pair'}
    if not candidates:
        return output
    distance, mass, _, _, a, b = min(candidates, key=lambda x: x[:4])
    futures = [s for s in e.new_items if s != a['item']][:5]
    matched = distance <= .0025 and mass <= .125
    output.update(status='matched' if matched else 'nearest_unmatched_diagnostic',
                  frontier_gain_cap_distance=distance, source_mass_distance=mass,
                  selected=[a, b], futures=futures,
                  selection='Minimum current frontier distance, then full source-mass-vector distance, then gear IDs; no future outcomes used.')
    output['branches'] = [exact_continuation(e, x, futures) for x in (a, b)]
    return output


def main():
    root = setup_paths(); out = root/'artifacts/decisive-value'
    run = root/'runs/decisive-value/history-followup-v1'; run.mkdir(parents=True, exist_ok=False)
    atomic_json(run/'PROTOCOL.json', {'source_sha256': file_hash(Path(__file__)),
        'selected_release_witnesses': [{'pool': p, 'race': r, 'releases': b} for (p,r),b in SELECTED.items()],
        'branch_pools': POOLS, 'current_matched_frontier_tolerance': .0025,
        'current_matched_source_mass_tolerance': .125, 'same_current_item_and_K': True,
        'future': 'lexicographically first up to five remaining candidate items; uniform permutations',
        'G': {'epsilon': .01, 'mass': .125}, 'native_calls': 0,
        'information': 'Offline existential common-future reference, same future sequence revealed to both branches; current pair selection reads current responses only.'})
    witnesses = []; branches = []
    for e in load_ecologies(root/'runs/r4-foundational-discovery/baseline-v1'):
        if e.pool['id'] not in POOLS:
            continue
        witnesses += native_witnesses(e, SELECTED.get((e.pool['id'], e.race), []))
        result = branch_probe(e); branches.append(result)
        atomic_json(run/(e.pool['id']+'__'+e.race+'.json'), result)
        atomic_json(out/'LINE_C_NATIVE_WITNESSES.json', witnesses)
        print(json.dumps({'context': [e.pool['id'],e.race], 'actions': result['current_action_count'],
                          'status': result['status'], 'Psi': [b['Psi'] for b in result.get('branches', [])]}), flush=True)
    atomic_json(out/'LINE_C_BRANCHES.json', branches)
    write_csv(out/'LINE_C_BRANCH_SUMMARY.csv', [{k:v for k,v in x.items() if k not in ('current_actions','selected','branches')}
        | {'Psi': [b['Psi'] for b in x.get('branches', [])]} for x in branches])


if __name__ == '__main__': main()
