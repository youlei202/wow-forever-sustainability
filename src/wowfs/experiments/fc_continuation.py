"""Remaining same-family gain capacity after a frozen dense history."""
from collections import Counter
import json
from math import floor
from pathlib import Path

import numpy as np

from wowfs.experiments.fc_finite_reference import csv_write
from wowfs.experiments.r2_native import file_hash
from wowfs.paths import setup_paths, atomic_json


def remaining_capacity(height, headroom=.05, gain=.01):
    """Scalar point-model upper bound; unsafe history is not a zero result."""
    if height > headroom+1e-10:
        return None
    return max(0, floor((headroom-height)/gain+1e-10))


def main():
    root = setup_paths()
    out = root/'artifacts/final-completion-capacity'
    run = root/'runs/final-completion-capacity/capacity-confirmation-v1'
    summary_path = out/'SUMMARY.json'
    summary = json.loads(summary_path.read_text())
    cfg = json.loads((run/'inputs/FROZEN_MAIN_PROTOCOL.json').read_text())
    tasks = [t['id'] for t in cfg['tasks']]
    results = json.loads((run/'RESULTS.json').read_text())
    refs = {(r['context_id'], r['task']): r for r in results['rows']
        if r['primary_coefficient'] == 0 and r['partner_coefficient'] == .044}
    sequences = {(s['context_id'], s['sequence']): s for s in summary['sequences']}
    rounds = {}
    for r in summary['rounds']:
        rounds.setdefault((r['context_id'], r['sequence']), []).append(r)
    records, details = [], []
    for context in summary['contexts']:
        cid = context['context_id']
        affine = context['development_affinity'] and context['confirmation_affinity']
        for name in ('dense_interior', 'dense'):
            seq = sequences[cid, name]
            row = {'context_id': cid, 'class': context['class'], 'faction': context['faction'],
                'race': context['race'], 'sequence': name, 'status': 'not_applicable_nonaffine',
                'history_rounds': '', 'history_mean_successful_prefix': seq.get('mean_successful_prefix', ''),
                'history_ci_supported_prefix': seq.get('ci_supported_prefix', ''),
                'terminal_history_reached_by_value_conditions': '',
                'max_task_normalized_frontier_growth': '', 'remaining_headroom': '',
                'conditional_point_remaining_updates_upper': '',
                'same_family_no_continuation_approx_certificate': '',
                'best_growth_minus_four_percent_lower_DPS': '',
                'scope': 'Same common positive affine family, fixed old reference/cap, retained realized history; prospective alternative regimes do not refund spent headroom',
                'confidence_scope': context['confidence_scope']}
            if affine:
                last = max(rounds[cid, name], key=lambda x: x['round'])
                scale = np.array(last['fixed_reference_scale'])
                normalized = np.array(last['frontier'])/scale-1
                height = float(normalized.max())
                bound = remaining_capacity(height, cfg['fixed_headroom'], cfg['meaningful_gain'])
                reached = seq['mean_successful_prefix'] == seq['planned_rounds']
                row.update(status='reached_mean_history' if reached else 'unreached_frozen_terminal_counterfactual',
                    history_rounds=last['round'], terminal_history_reached_by_value_conditions=reached,
                    max_task_normalized_frontier_growth=height, remaining_headroom=.05-height,
                    conditional_point_remaining_updates_upper='' if bound is None else bound)
                if bound is None:
                    row['status'] = 'unsafe_frozen_terminal_counterfactual'
                # The interior path has one step from the old library. Its
                # existing gain-margin bound is growth-.01*S. Add three times
                # the existing self-pair B=-.01*S lower bound. No new family.
                if name == 'dense_interior' and last['round'] == 1:
                    ref = np.array([refs[cid, t]['dps_samples'] for t in tasks])
                    b = -.01*ref
                    b_lower = b.mean(axis=1)-context['student_t_critical']*b.std(axis=1, ddof=1)/np.sqrt(b.shape[1])
                    lower = np.array(last['gain_contrast_lower'])+3*b_lower
                    cert = bool(np.any(lower > 0))
                    row.update(same_family_no_continuation_approx_certificate=cert,
                        best_growth_minus_four_percent_lower_DPS=float(lower.max()))
                    details.append({'context_id': cid, 'sequence': name, 'tasks': tasks,
                        'growth_minus_four_percent_lower_DPS': lower.tolist(),
                        'uses_existing_family': True})
            records.append(row)
    payload = {'schema': 1, 'new_native_calls': 0,
        'analysis_source_sha256': file_hash(Path(__file__)), 'summary_sha256': file_hash(summary_path),
        'native_results_sha256': file_hash(run/'RESULTS.json'),
        'theorem': 'For a retained scalar frontier F_k under cap tau, every later accepted update adds at least g, so remaining updates <= floor((tau-F_k)/g). For multi-task positive affine responses use the maximum normalized slope and fixed old reference; this is a same-family result.',
        'boundary': 'Changing future admission cannot lower an already retained historical optimum. A new non-collinear response direction is outside this scalar-family result, not a demonstrated recovery.',
        'records': records, 'details': details}
    csv_write(out/'CONTINUATION_BOUND.csv', records)
    atomic_json(out/'CONTINUATION_BOUND.json', payload)
    print(json.dumps({'statuses': dict(Counter(r['status'] for r in records)),
        'guarded_remaining': dict(Counter(str(r['conditional_point_remaining_updates_upper']) for r in records if r['sequence']=='dense_interior')),
        'guarded_approx_zero_certificates': sum(r['same_family_no_continuation_approx_certificate'] is True for r in records),
        'new_native_calls': 0}, indent=2))


if __name__ == '__main__':
    main()
