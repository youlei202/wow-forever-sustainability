"""Decision-gain admission on a complete frozen native response table.

The solver is a finite empirical comparator, not a population certificate.
The existing P/N/D/L/H/C predicates are retained. G is a separate obligation.
"""
from copy import deepcopy
from time import monotonic
import numpy as np
from wowfs.experiments.r4_feasibility import evaluate_admission, solve_joint_admission


def decision_metrics(problem, admitted, gain_baseline=None, gain_threshold=.01,
                     gain_mass=.125):
    p = problem
    mask = np.asarray(admitted, bool)
    baseline = (p.best[p.protected].max(axis=0) if gain_baseline is None
                else np.asarray(gain_baseline, float))
    result = evaluate_admission(p, mask)
    optimum = p.best[mask].max(axis=0)
    gain = optimum - baseline
    relative = gain / p.scale
    mass = float(p.weights @ (relative >= gain_threshold - p.tolerance))
    deletion = {}
    for source in p.new_sources:
        remaining = mask & np.array([source not in ss for ss in p.sources])
        if not remaining.any():
            raise ValueError('Removing a new source unexpectedly removed the complete old library')
        without = p.best[remaining].max(axis=0)
        deletion[source] = {'utility_without_source':without.tolist(),
                            'normalized_loss':((optimum-without)/p.scale).tolist()}
    return {**result, 'old_reoptimized_utility':baseline.tolist(),
            'decision_gain':gain.tolist(), 'normalized_gain':relative.tolist(),
            'gain_mass':mass, 'gain_threshold':gain_threshold,
            'gain_required_mass':gain_mass, 'G':mass >= gain_mass-p.tolerance,
            'all_seven_pass':result['joint_pass'] and mass >= gain_mass-p.tolerance,
            'source_deletion':deletion,
            'gain_scope':'Expected DPS for each fixed real combat task, empirical mean; all allowed gear and three policies reoptimized on each side.'}


def solve_gain_subset(problem, gain_baseline=None, gain_threshold=.01,
                      gain_mass=.125, *, time_limit=30., per_witness_limit=5.,
                      rule_rows=0, features=None, require_behavior=True,
                      objective='max_admitted'):
    """Exact finite OR over qualifying gain witnesses when one task is enough.

    Every feasible positive-gain library admits at least one qualifying gear.
    Forcing each such gear in turn therefore preserves completeness. The
    original D reference is computed before this added admission constraint;
    the forced new gear is never retrospectively counted as historical gear.
    Search exhaustion proves infeasibility only if every witness MILP proves
    infeasible. Timeouts are retained as unknown, never recoded as failure.
    """
    started = monotonic(); p = problem
    baseline = (p.best[p.protected].max(axis=0) if gain_baseline is None
                else np.asarray(gain_baseline, float))
    positive_weights = p.weights[p.weights > 0]
    if not len(positive_weights) or gain_mass > positive_weights.min()+p.tolerance:
        raise ValueError('This exact OR solver requires one qualifying task to satisfy gain mass')
    eligible = p.best >= baseline[None,:] + gain_threshold*p.scale[None,:] - p.tolerance
    witness = np.flatnonzero(p.safe & np.any(eligible & (p.weights>0)[None,:], axis=1))
    witness = sorted(witness, key=lambda i:float(np.max((p.best[i]-baseline)/p.scale)), reverse=True)
    attempts=[]; best=None
    for i in witness:
        remaining=time_limit-(monotonic()-started)
        if remaining <= 0: break
        forced=deepcopy(p)
        forced.protected[i]=True
        if not require_behavior:
            # This relaxed comparator is labeled P/N/L/H/C+G; actual D is
            # always recomputed on the unchanged original problem below.
            forced.novel_best=forced.best.copy()
        result=solve_joint_admission(forced, objective=objective,
            time_limit=min(per_witness_limit,remaining), rule_rows=rule_rows,
            features=features)
        attempt={'witness_gear_index':int(i),'status':result['status'],
                 'proved_infeasible':result['proved_infeasible'],
                 'feasible':result['feasible'],'seconds':result.get('seconds')}
        attempts.append(attempt)
        if result['feasible']:
            metrics=decision_metrics(p,result['admitted'],baseline,gain_threshold,gain_mass)
            required=all(metrics[k] for k in ('P','N','L','H','C','G')) and (metrics['D'] or not require_behavior)
            result.update(metrics=metrics,feasible=required,
                force_admitted_for_gain_witness_only=int(i))
            if required: best=result; break
    proved=(best is None and len(attempts)==len(witness)
            and all(a['proved_infeasible'] for a in attempts))
    return {'status':'feasible' if best else ('infeasible' if proved else 'unknown'),
        'feasible':best is not None,'proved_infeasible':proved,
        'gain_witnesses':len(witness),'attempted_witnesses':len(attempts),
        'attempts':attempts,'result':best,'seconds':monotonic()-started,
        'behavior_constraint_required':require_behavior,
        'method':'finite_disjunction_of_native_gain_witnesses',
        'optimization_scope':'Feasibility is exact when witnessed or exhausted; first feasible mask is not globally gain-optimal.'}
