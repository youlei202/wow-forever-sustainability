"""Exact scalar completion calculations. Abstract models, zero native calls.

The continuous value result does not assert original behavioral novelty or
legacy retention. The finite oracle checks all retained scalar source witnesses
and permits nonmonotone incoming amplitudes.
"""
from fractions import Fraction
from functools import lru_cache


def q(value):
    return value if isinstance(value, Fraction) else Fraction(str(value))


def ceil_q(value):
    value = q(value)
    return -((-value.numerator) // value.denominator)


def completion_intervals(partners, minimum_primary, cap):
    """Branch ranges for a in [minimum_primary,infinity), all legal crosses.

    Every nonempty branch ends at cap. A lower boundary at which the next
    stronger partner is just legal is OPEN, including when a_min equals it.
    """
    xs = sorted(set(map(q, partners)))
    amin, tau = q(minimum_primary), q(cap)
    if not xs:
        raise ValueError('At least one retained partner is required')
    result = []
    for i, x in enumerate(xs):
        if i + 1 == len(xs):
            lower, closed = amin + x, True
        else:
            threshold = tau - xs[i + 1]
            lower = max(amin + x, threshold + x)
            closed = amin > threshold
        if lower < tau or (lower == tau and closed):
            result.append({'partner': x, 'lower': lower, 'lower_closed': closed,
                           'upper': tau, 'direct': i + 1 == len(xs)})
    return result


def interval_capacity(intervals, initial_frontier, cap, gain):
    """Exact increasing g-separated sequence length for these cap-ended bands."""
    f0, tau, g = map(q, (initial_frontier, cap, gain))
    if g <= 0 or f0 > tau:
        raise ValueError('Require positive gain and a legal initial frontier')
    headroom_count = int((tau - f0) // g)
    best = 0
    for band in intervals:
        width = tau - band['lower']
        branch_count = (1 + int(width // g) if band['lower_closed']
                        else ceil_q(width / g))
        best = max(best, min(headroom_count, branch_count))
    return best


def continuous_value_capacity(partners, old_primary, minimum_primary, cap, gain):
    xs = sorted(set(map(q, partners)))
    f0 = q(old_primary) + max(xs)
    bands = completion_intervals(xs, minimum_primary, cap)
    gaps = [b-a for a, b in zip(xs, xs[1:])]
    delta = max(gaps, default=Fraction(0))
    return {'initial_frontier': f0, 'delta': delta, 'intervals': bands,
            'value_capacity': interval_capacity(bands, f0, cap, gain),
            'direct_capacity': interval_capacity([b for b in bands if b['direct']], f0, cap, gain),
            'gap_capacity': interval_capacity([b for b in bands if not b['direct']], f0, cap, gain),
            'unqualified_gap_prediction': min(int((q(cap)-f0)//q(gain)), ceil_q(delta/q(gain)))}


def inspect_sequence(partners, old_primary, incoming, cap, gain, relevance,
                     compatibility=None):
    """Full Cartesian, cap-filtered scalar sequence; D explicitly unevaluated."""
    xs = tuple(sorted(set(map(q, partners))))
    a0, tau, g, e = map(q, (old_primary, cap, gain, relevance))
    if not xs or a0 + max(xs) > tau or min(a0+x for x in xs) < a0+max(xs)-e:
        raise ValueError('Initial full old library must be legal and all sources useful')
    primaries = [a0]
    previous = a0 + max(xs)
    historical = {(0, i) for i in range(len(xs))}
    rows = []
    for a in map(q, incoming):
        primaries.append(a)
        admitted = {(j, i): p+x for j, p in enumerate(primaries)
                    for i, x in enumerate(xs) if p+x <= tau and
                    (compatibility is None or compatibility(p, x))}
        frontier = max(admitted.values())
        primary_witness = [max((v for (j, _), v in admitted.items() if j == k), default=None)
                           for k in range(len(primaries))]
        partner_witness = [max(v for (_, i), v in admitted.items() if i == k)
                           for k in range(len(xs))]
        useful = lambda v: v is not None and v >= frontier-e
        checks = {'P': frontier <= tau, 'N': useful(primary_witness[-1]),
                  'L': all(map(useful, primary_witness[:-1]+partner_witness)),
                  'H': historical <= set(admitted), 'C': bool(admitted),
                  'G': frontier-previous >= g}
        rows.append({'primary': a, 'frontier': frontier, 'gain': frontier-previous,
                     'checks': checks, 'value_joint': all(checks.values()),
                     'D': 'not_evaluated_scalar_model', 'K': 1,
                     'partner_witnesses': partner_witness,
                     'primary_witnesses': primary_witness,
                     'legal_crosses': len(primaries)*len(xs),
                     'admitted_crosses': len(admitted)})
        previous, historical = frontier, set(admitted)
    return rows


def finite_capacity(partners, old_primary, candidates, cap, gain, relevance,
                    require_legacy=True):
    """Exact finite candidate-set oracle, all release orders, no monotonicity assumption.

    A source is its candidate index, and every admitted configuration is retained.
    The oracle is intentionally for tiny mathematical examples, not simulations.
    """
    xs = tuple(sorted(set(map(q, partners))))
    vals = tuple(sorted(set(map(q, candidates))))
    a0, tau, g, e = map(q, (old_primary, cap, gain, relevance))
    inspect_sequence(xs, a0, [], tau, g, e)
    if len(vals) > 24:
        raise ValueError('Exact subset oracle limited to 24 distinct candidates')

    @lru_cache(None)
    def solve(mask):
        selected = [vals[i] for i in range(len(vals)) if mask & (1 << i)]
        all_primaries = [a0]+selected
        before = max(a+x for a in all_primaries for x in xs if a+x <= tau)
        best = ()
        for i, a in enumerate(vals):
            if mask & (1 << i):
                continue
            new_values = [a+x for x in xs if a+x <= tau]
            if not new_values or max(new_values)-before < g:
                continue
            after = max(new_values)
            if require_legacy:
                ps = all_primaries+[a]
                if any(max(p+x for p in ps if p+x <= tau) < after-e for x in xs):
                    continue
                if any(max(p+x for x in xs if p+x <= tau) < after-e for p in all_primaries):
                    continue
            candidate = (a,)+solve(mask | (1 << i))
            if len(candidate) > len(best):
                best = candidate
        return best

    path = solve(0)
    return {'capacity': len(path), 'path': path, 'states': solve.cache_info().currsize,
            'scope': 'abstract_exact_finite_candidates_not_continuous_not_native'}
