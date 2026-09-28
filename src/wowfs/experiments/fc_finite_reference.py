"""Independent finite-order reference and conditional dense-capacity bounds.

Reads frozen confirmation data only. It does not execute native simulations,
change masks, or reinterpret finite-domain optima as continuous capacities.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

import numpy as np

from wowfs.experiments.fc_mechanism_capacity import finite_oracle
from wowfs.experiments.r2_native import file_hash
from wowfs.paths import setup_paths, atomic_json


def point(p, x):
    return round(float(p), 14), round(float(x), 14)


def csv_write(path, rows):
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def dense_bound_certificate(zero, high, reference, critical):
    """Positive combinations of two contrasts in the EXISTING paired family.

    A=high-zero-.01*reference; B=-.01*reference. No new critical value or
    additional confidence allocation is introduced. Inputs have shape task,seed.
    """
    zero, high, reference = map(np.asarray, (zero, high, reference))
    if zero.shape != high.shape or zero.shape != reference.shape or zero.ndim != 2:
        raise ValueError('Matched task-by-seed arrays required')
    n = zero.shape[1]
    a_samples = high-zero-.01*reference
    b_samples = -.01*reference

    def bounds(samples):
        mean = samples.mean(axis=1)
        radius = critical*samples.std(axis=1, ddof=1)/np.sqrt(n)
        return mean-radius, mean+radius

    a_lo, a_hi = bounds(a_samples)
    b_lo, b_hi = bounds(b_samples)
    gap_multiplier = .011/.148
    lambda_multiplier = .0502/.148
    gap_margin_upper = gap_multiplier*a_hi+(2-gap_multiplier)*b_hi
    lambda_margin_lower = lambda_multiplier*a_lo+(3-lambda_multiplier)*b_lo
    slope_numerator_lower = a_lo-b_hi
    reference_lower = -100*b_hi
    return {
        'gap_minus_two_g_reference_upper': gap_margin_upper.tolist(),
        'lambda_minus_h_minus_two_g_reference_lower': lambda_margin_lower.tolist(),
        'high_minus_zero_lower': slope_numerator_lower.tolist(),
        'reference_lower': reference_lower.tolist(),
        'all_task_gap_at_most_two_g': bool(np.all(gap_margin_upper <= 0)),
        'some_task_lambda_above_h_minus_two_g': bool(np.any(lambda_margin_lower > 0)),
        'positive_all_task_slope': bool(np.all(slope_numerator_lower > 0)),
        'positive_all_task_reference': bool(np.all(reference_lower > 0)),
    }


def main():
    root = setup_paths()
    out = root/'artifacts/final-completion-capacity'
    run = root/'runs/final-completion-capacity/capacity-confirmation-v1'
    plan_path = run/'inputs/FUTURE_SEQUENCE_DESIGN.json'
    plan = json.loads(plan_path.read_text())
    cfg = json.loads((run/'inputs/FROZEN_MAIN_PROTOCOL.json').read_text())
    results = json.loads((run/'RESULTS.json').read_text())
    if results['errors'] or any(row is None for row in results['rows']):
        raise ValueError('Incomplete confirmation cannot be treated as zero capacity')
    summary_path = out/'SUMMARY.json'
    summary = json.loads(summary_path.read_text())
    checks = {c['context_id']: c for c in summary['contexts']}
    tasks = [t['id'] for t in cfg['tasks']]
    tables = {}
    for row in results['rows']:
        tables.setdefault(row['context_id'], {})[point(row['primary_coefficient'], row['partner_coefficient']), row['task']] = row

    oracle_rows, oracle_details, bound_rows, bound_details = [], [], [], []
    for ctx in plan['contexts']:
        cid = ctx['context_id']
        table, check = tables[cid], checks[cid]
        affine = bool(check['development_affinity'] and check['confirmation_affinity'])
        zeros = np.array([table[point(0, 0), t]['dps_samples'] for t in tasks])
        highs = np.array([table[point(.148, 0), t]['dps_samples'] for t in tasks])
        references = np.array([table[point(0, .044), t]['dps_samples'] for t in tasks])
        scale = references.mean(axis=1)

        def mean_response(p, x):
            return np.array([np.mean(table[point(p, x), t]['dps_samples']) if (point(p, x), t) in table else
                np.mean(zeros[q]+(highs[q]-zeros[q])*(float(p)+float(x))/.148)
                for q, t in enumerate(tasks)])

        for regime in ('large_gap', 'dense', 'weaker_direct', 'fixed_budget'):
            sequences = [s for s in ctx['sequences'] if s['regime'] == regime]
            partners = sequences[0]['partner_coefficients']
            candidates = {}
            for sequence in sequences:
                if sequence['partner_coefficients'] != partners:
                    raise ValueError('Candidate union requires identical old partners')
                for p, row in zip(sequence['primary_coefficients'], sequence['rows']):
                    key = point(p, 0)[0]
                    mask = row['admission_mask'][-1]
                    if key in candidates and candidates[key][1] != mask:
                        raise ValueError('Same primary has inconsistent frozen masks')
                    candidates[key] = (p, mask)
            ordered = [candidates[key] for key in sorted(candidates)]
            primaries = [0.] + [p for p, _ in ordered]
            admitted = np.array([[True]*len(partners)] + [mask for _, mask in ordered])
            row = {'context_id': cid, 'class': ctx['class'], 'faction': ctx['faction'],
                'race': ctx['race'], 'regime': regime, 'status': 'complete' if affine else 'not_run_nonaffine_exact_domain',
                'candidate_primaries': len(primaries)-1, 'old_partners': len(partners),
                'finite_value_legacy_lower': '', 'finite_value_legacy_upper': '',
                'finite_utility_lower': '', 'finite_utility_upper': '',
                'finite_value_legacy_path': '', 'states_visited': '',
                'initial_PNLHC': '', 'generic_same_fixed_rule_capacity': '',
                'D': 'not_evaluated',
                'scope': 'Exact finite subset/order optimum of fresh means, fixed masks, paired old-reference scale; no continuous or population confidence claim',
                'generic_scope': 'Identical two features and fixed row represent the identical mask; no optimization over free generic weights or algorithmic advantage'}
            if affine:
                cube = np.array([[mean_response(p, x) for x in partners] for p in primaries])
                value, _ = finite_oracle(cube, admitted, 0, scale, cfg, True)
                utility, _ = finite_oracle(cube, admitted, 0, scale, cfg, False)
                initial = all(value['initial_checks'].values())
                if not initial:
                    row['status'] = 'initial_constraints_failed'
                row.update(finite_value_legacy_lower=value['capacity'], finite_value_legacy_upper=value['capacity'],
                    finite_utility_lower=utility['capacity'], finite_utility_upper=utility['capacity'],
                    finite_value_legacy_path=json.dumps([primaries[i] for i in value['path']]),
                    states_visited=value['states_visited'], initial_PNLHC=initial,
                    generic_same_fixed_rule_capacity=value['capacity'])
                oracle_details.append({'context_id': cid, 'regime': regime, 'primary_coefficients': primaries,
                    'partner_coefficients': partners, 'admission_mask': admitted.tolist(),
                    'reference_scale': scale.tolist(), 'utility_cube': cube.tolist(),
                    'value_legacy': value, 'utility_only': utility})
            oracle_rows.append(row)

        bound = {'context_id': cid, 'class': ctx['class'], 'faction': ctx['faction'], 'race': ctx['race'],
            'status': 'not_applicable_nonaffine', 'conditional_continuous_dense_utility_upper': '',
            'max_gap_minus_two_g_upper_DPS': '', 'max_lambda_minus_h_minus_two_g_lower_DPS': '',
            'all_task_positive_slope': '', 'all_task_positive_reference': '',
            'family_size': check['simultaneous_contrast_family_size'],
            'critical': check['student_t_critical'],
            'confidence_scope': check['confidence_scope'],
            'assumption_scope': 'Conditional on common positive affine response on the declared continuum; finite native checkpoints validate but do not prove that structural assumption'}
        if affine:
            cert = dense_bound_certificate(zeros, highs, references, check['student_t_critical'])
            passes = all(cert[k] for k in ('all_task_gap_at_most_two_g',
                'some_task_lambda_above_h_minus_two_g', 'positive_all_task_slope', 'positive_all_task_reference'))
            bound.update(status='conditional_upper_certified' if passes else 'upper_unresolved',
                conditional_continuous_dense_utility_upper=2 if passes else '',
                max_gap_minus_two_g_upper_DPS=max(cert['gap_minus_two_g_reference_upper']),
                max_lambda_minus_h_minus_two_g_lower_DPS=max(cert['lambda_minus_h_minus_two_g_reference_lower']),
                all_task_positive_slope=cert['positive_all_task_slope'],
                all_task_positive_reference=cert['positive_all_task_reference'])
            bound_details.append({'context_id': cid, 'tasks': tasks, 'certificate': cert})
        bound_rows.append(bound)

    provenance = {'new_native_calls': 0, 'analysis_source_sha256': file_hash(Path(__file__)),
        'frozen_plan_sha256': file_hash(plan_path), 'results_sha256': file_hash(run/'RESULTS.json'),
        'source_summary_sha256': file_hash(summary_path)}
    csv_write(out/'SMALL_DOMAIN_ORACLE.csv', oracle_rows)
    atomic_json(out/'SMALL_DOMAIN_ORACLE.json', {'schema': 1, **provenance, 'rows': oracle_rows, 'details': oracle_details})
    csv_write(out/'CAPACITY_UPPER_BOUND_CERTIFICATES.csv', bound_rows)
    atomic_json(out/'CAPACITY_UPPER_BOUND_CERTIFICATES.json', {'schema': 1, **provenance,
        'confidence': 'Reuses existing within-context approximate simultaneous paired-t family. Positive linear combinations introduce no new alpha expenditure. No simultaneous 56-context coverage claimed.',
        'algebra': 'A=Uhigh-Uzero-.01S; B=-.01S; gap-.02S=(.011/.148)A+(2-.011/.148)B; lambda-.03S=(.0502/.148)A+(3-.0502/.148)B.',
        'scope': 'All-task gap upper bounds and at least one task direct-increment lower bound imply dense continuous utility capacity at most two, conditional on the common positive affine family. P/N/L/H/C/G capacity cannot exceed utility capacity. No D claim.',
        'rows': bound_rows, 'details': bound_details})
    print(json.dumps({'oracle_status': dict(Counter(r['status'] for r in oracle_rows)),
        'oracle_capacities': dict(Counter((r['regime']+':'+str(r['finite_value_legacy_lower'])) for r in oracle_rows)),
        'upper_status': dict(Counter(r['status'] for r in bound_rows)), 'new_native_calls': 0}, indent=2))


if __name__ == '__main__':
    main()
