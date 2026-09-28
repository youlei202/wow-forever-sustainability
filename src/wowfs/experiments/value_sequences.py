"""Exact cached finite-state sequences under an unchanged all-power-safe rule."""
from functools import lru_cache
from itertools import combinations
import json
from pathlib import Path
import numpy as np

from wowfs.paths import setup_paths, atomic_json
from wowfs.experiments.r2_native import file_hash
from wowfs.experiments.r2_sequence_analysis import write_csv
from wowfs.experiments.r4_data import load_ecologies
from wowfs.experiments.r4_feasibility import evaluate_admission
from wowfs.experiments.value_history import POOLS, decision_gain, deletion_records


def solve_sequences(e):
    new = set(e.new_items)
    safe = np.all(e.values.max(axis=1) <= e.cap + 1e-9, axis=1)
    new_support = [ss & new for ss in e.sources]
    transitions = []
    @lru_cache(None)
    def state(released):
        present = set(released)
        mask = e.initial | (safe & np.array([ss <= present for ss in new_support]))
        return mask, e.values[mask].max(axis=(0, 1))
    @lru_cache(None)
    def choices(released):
        old, baseline = state(released)
        remaining = sorted(new - set(released))
        valid = []
        for size in (1, 2):
            for batch in combinations(remaining, size):
                nxt = tuple(sorted(set(released) | set(batch)))
                new_mask, optimum = state(nxt)
                relative = (optimum - baseline)/e.scale
                mass = float(np.mean(relative >= .01 - 1e-9))
                record = {'ecology': e.pool['id'], 'race': e.race,
                          'previously_released': list(released), 'new_batch': list(batch),
                          'old_reoptimized': baseline.tolist(), 'new_reoptimized': optimum.tolist(),
                          'normalized_gain': relative.tolist(), 'gain_mass': mass, 'G': mass >= .125 - 1e-9,
                          'total_released_items': len(nxt), 'batch_items': size,
                          'task_ids': [x['id'] for x in e.tasks],
                          'admission_rule': 'All complete mixed loadouts satisfying every fixed task/policy power cap; no per-item exceptions.'}
                if not record['G']:
                    record.update(joint_with_G=False, status='G_fails_exact_finite_upper',
                                  other_six='not_evaluated_after_G_failure')
                else:
                    p, ix = e.problem(batch, protected=old, old_released=released,
                                      protected_sources=tuple(sorted(set(e.protected_sources)|set(released))))
                    admitted = p.safe | p.protected
                    assembled = old.copy(); assembled[ix] = admitted
                    if not np.array_equal(assembled, new_mask):
                        raise AssertionError('Full safe opening must be a function of released source set')
                    metrics = evaluate_admission(p, admitted)
                    record.update({k:metrics[k] for k in ('P','N','D','L','H','C','K')},
                                  joint_with_G=metrics['joint_pass'], status='joint_pass' if metrics['joint_pass'] else 'six_metric_failure',
                                  failure_reasons=metrics['failure_reasons'],
                                  min_normalized_cap_slack=float(np.min(np.array(metrics['cap_slack'])/e.scale)),
                                  worst_source_mass=metrics['worst_protected_source_mass'],
                                  admitted_gear_count=int(admitted.sum()), source_masses=metrics['source_masses'],
                                  deletions=deletion_records(p, admitted, batch),
                                  global_admitted_gear_ids=[e.gear_ids[i] for i in np.flatnonzero(new_mask)])
                    if metrics['joint_pass']:
                        valid.append((nxt, len(transitions)))
                transitions.append(record)
        return tuple(valid)
    @lru_cache(None)
    def best(released):
        options = []
        for nxt, index in choices(released):
            continuation = best(nxt)
            options.append((index,) + continuation)
        if not options:
            return ()
        # Fixed objective: maximize update count; tie break fewer total items,
        # then lexicographic batch sequence. No empirical threshold tuning.
        return min(options, key=lambda path: (-len(path), transitions[path[-1]]['total_released_items'],
                                             tuple(tuple(transitions[i]['new_batch']) for i in path)))
    optimum_path = best(())
    sequence = [{'round': n+1, **transitions[i]} for n, i in enumerate(optimum_path)]
    return {'ecology':e.pool['id'],'race':e.race,'max_successful_updates':len(sequence),
            'total_items_in_selected_sequence': sequence[-1]['total_released_items'] if sequence else 0,
            'joint_sequences_exist_at_horizon': {str(h):len(sequence)>=h for h in (1,3,5)},
            'reachable_states_evaluated':choices.cache_info().currsize,
            'attempted_releases':len(transitions),'rejected_releases':sum(not x['joint_with_G'] for x in transitions),
            'selected_sequence':sequence,'transitions':transitions,
            'history_order_scope':'With fixed physics/caps and full all-safe opening, equal released source sets imply equal H, source obligations, and full-policy D references. Order cannot change continuation from equal sets.',
            'scope':'Exact finite empirical DP for singleton/pair releases under the declared deterministic rule. Not arbitrary subset admission or population capacity.'}


def main():
    root=setup_paths();out=root/'artifacts/decisive-value';run=root/'runs/decisive-value/value-sequences-v1'
    run.mkdir(parents=True,exist_ok=False)
    atomic_json(run/'PROTOCOL.json',{'pools':POOLS,'source_sha256':file_hash(Path(__file__)),
        'epsilon_gain':.01,'rho_gain':.125,'release_sizes':[1,2],
        'H':'all initial16 and every previously admitted complete cap-safe loadout',
        'L':'fixed initially competitive source registry plus every previously released new source',
        'D':'Unchanged physical7-dimensional metric against every retained old gear/policy profile',
        'objective':'Maximum number of sequentially successful updates; then minimum total released items; lexicographic tie.',
        'native_calls':0,'inference':'Cached native16-seed development means; no independent confirmation.'})
    output=[]
    for e in load_ecologies(root/'runs/r4-foundational-discovery/baseline-v1'):
        if e.pool['id'] not in POOLS:continue
        result=solve_sequences(e);output.append(result)
        atomic_json(run/(e.pool['id']+'__'+e.race+'.json'),result)
        print(json.dumps({k:v for k,v in result.items() if k not in ('transitions','selected_sequence')}),flush=True)
    atomic_json(out/'LINE_C_VALUE_SEQUENCES.json',output)
    write_csv(out/'LINE_C_SEQUENCE_RESULTS.csv',[r for d in output for r in d['selected_sequence']])
    write_csv(out/'LINE_C_SEQUENCE_ATTEMPTS.csv',[r for d in output for r in d['transitions']])


if __name__=='__main__':main()
