"""Pre-sampling secondary tolerance panel, inherited from each fresh core event.

The panel uses all registered base-menu queries at every declared multiplier.
It is a deterministic consequence of each existing full-domain confidence event,
not an additional independent confirmation or a newly covered t direction.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import hashlib
from pathlib import Path
import time

import numpy as np

from wowfs.experiments.co_native_analysis import certify_queries, exact_queries


PANEL_PROTOCOL = {
    'analysis_id': 'base_menu_retention_tolerance_secondary_v1',
    'selection': 'All 16 registered validation catalogues, all existing 8 base-menu target queries; no selection on confirmation results.',
    'tolerance_multipliers': ['1/2', '1', '2', '5'],
    'base_tolerance': '0.01', 'tolerances': ['0.005', '0.01', '0.02', '0.05'],
    'headroom': '0.10', 'gain': '0.01', 'retention_mass': '1/2', 'gain_mass': '1/2',
    'variant': 'base', 'confirmation_N_unchanged': True,
    'new_alpha': 0., 'source_event_alpha_per_catalogue': .0025,
    'declaration_scope': 'Secondary event-derivation protocol declared after development/prediction tables, before fresh confirmation sampling.',
    'coverage': 'All parameter changes are deterministic implications of the original full-domain simultaneous event; no t interval at a new coefficient is computed.',
    'interpretation': 'Tests the role of the normative source-retention tolerance in the same finite domains; not a new catalogue sample or prevalence estimate.',
}


def reference_bounds(bounds, rule):
    """Reference bounds from every diagonal already in the original event."""
    e = float(Fraction(rule['tolerance'])); g = float(Fraction(rule['gain']))
    candidates = []; proof = []
    for family, coefficient in [('retention', e), ('gain', -g)]:
        if coefficient == 0:
            continue
        lo = np.diagonal(bounds[family + '_lower'], axis1=1, axis2=2) / coefficient
        hi = np.diagonal(bounds[family + '_upper'], axis1=1, axis2=2) / coefficient
        if coefficient < 0:
            lo, hi = hi, lo
        candidates.append((lo, hi))
        proof.append({'family': family, 'coefficient': coefficient, 'row_pairs': 'all c=d',
                      'lower_by_task_and_diagonal': lo.tolist(), 'upper_by_task_and_diagonal': hi.tolist()})
    if not candidates:
        raise ValueError('No nonzero diagonal coefficient supports reference propagation')
    lower = np.max(np.concatenate([a for a, _ in candidates], axis=1), axis=1)
    upper = np.min(np.concatenate([a for _, a in candidates], axis=1), axis=1)
    guard = 128 * np.finfo(float).eps * np.maximum(1, np.maximum(np.abs(lower), np.abs(upper)))
    lower -= guard; upper += guard
    if not np.isfinite(lower).all() or not np.isfinite(upper).all() or np.any(lower > upper):
        raise ValueError('Invalid inherited reference interval')
    # The panel uses positive-reference relaxation monotonicity and fractions.
    if np.any(lower <= 0):
        raise ValueError('UNSUPPORTED_REFERENCE_SIGN: event does not certify positive reference')
    return lower, upper, proof


def propagate_tolerance(bounds, rule, multiplier):
    multiplier = Fraction(multiplier)
    if multiplier <= 0:
        raise ValueError('Tolerance multiplier must be positive')
    original = Fraction(rule['tolerance']); new_e = original * multiplier
    new_rule = dict(rule, tolerance=str(new_e))
    result = dict(bounds)  # Immutable old array references except derived retention.
    sl, su, proof = reference_bounds(bounds, rule)
    coefficient = float(new_e - original)
    lower_shift = np.minimum(coefficient * sl, coefficient * su)[:, None, None]
    upper_shift = np.maximum(coefficient * sl, coefficient * su)[:, None, None]
    result['retention_lower'] = bounds['retention_lower'] + lower_shift
    result['retention_upper'] = bounds['retention_upper'] + upper_shift
    guard = 128 * np.finfo(float).eps * np.maximum(1, np.maximum(np.abs(result['retention_lower']), np.abs(result['retention_upper'])))
    result['retention_lower'] = result['retention_lower'] - guard
    result['retention_upper'] = result['retention_upper'] + guard
    result['manifest'] = {
        'evidence_level': 'FRESH_CONFIRMATION_EVENT_DERIVATION',
        'source_manifest': deepcopy(bounds['manifest']), 'rule': new_rule,
        'new_alpha': 0., 'tolerance_multiplier': str(multiplier),
        'derivation': 'R_new(c,d,q)=R_old(c,d,q)+(e_new-e_old)*S_q; sign-aware endpoint sums on the same event.',
        'reference_lower': sl.tolist(), 'reference_upper': su.tolist(),
        'reference_diagonal_proof': proof, 'added_reference_coefficient': coefficient,
        'cap_and_gain_arrays': 'Identical to original event; all configured tasks and physical rows retained.',
        'numerics': '128 machine eps outward guard on derived endpoints and reference bounds.',
        'population_method': bounds['manifest']['population_method'],
    }
    return result, new_rule


def analyze_catalogue(world, moments, bounds, rule, *, include_means=True):
    """Return every predeclared threshold/query; callers preserve all statuses."""
    for name in ('headroom', 'gain', 'retention_mass', 'gain_mass'):
        if Fraction(rule[name]) != Fraction(PANEL_PROTOCOL[name]):
            raise ValueError(f'Panel fixed contract mismatch: {name}')
    if Fraction(rule['tolerance']) != Fraction(PANEL_PROTOCOL['base_tolerance']):
        raise ValueError('Panel base tolerance mismatch')
    start = time.perf_counter(); records = []
    reference_only = reference_bounds(bounds, rule)
    for multiplier in PANEL_PROTOCOL['tolerance_multipliers']:
        propagated, new_rule = propagate_tolerance(bounds, rule, multiplier)
        answers = certify_queries(world, moments, propagated, new_rule, 'base')
        answers['evidence_level'] = 'FRESH_CONFIRMATION_EVENT_DERIVATION'
        exact = exact_queries(world, moments, new_rule, 'base') if include_means else None
        records.append({'multiplier': multiplier, 'tolerance': new_rule['tolerance'],
                        'population_answers': answers, 'mean_table_answers': exact})
    return {'world_id': world['world_id'], 'protocol': PANEL_PROTOCOL, 'records': records,
            'source_code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'reference_bounds': {'lower': reference_only[0].tolist(), 'upper': reference_only[1].tolist()},
            'elapsed_seconds': time.perf_counter() - start, 'new_observations': 0, 'new_alpha': 0.}
