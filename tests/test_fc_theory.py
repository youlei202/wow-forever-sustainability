from fractions import Fraction as F

from wowfs.experiments.fc_theory import (
    completion_intervals, continuous_value_capacity, finite_capacity,
    inspect_sequence,
)


def test_stronger_partner_at_exact_cap_makes_branch_lower_endpoint_open():
    bands = completion_intervals([0, '.03', '.05'], '1.0002', '1.05')
    lower = next(x for x in bands if x['partner'] == 0)
    assert lower['lower'] == F('1.02') and not lower['lower_closed']
    # a=1.02 optimizes with partner .03 to 1.05, not with zero to 1.02.
    assert max(F('1.02')+x for x in map(F, ['0', '.03', '.05'])
               if F('1.02')+x <= F('1.05')) == F('1.05')


def test_direct_design_and_truncated_incoming_family_defeat_unqualified_gap():
    direct = continuous_value_capacity([0, '.01', '.02'], '.98', '.99', '1.05', '.01')
    assert direct['unqualified_gap_prediction'] == 1
    assert direct['value_capacity'] == direct['direct_capacity'] == 5
    cut = continuous_value_capacity([0, 1], 0, '1.8', 2, '.25')
    assert cut['unqualified_gap_prediction'] == 4
    assert cut['value_capacity'] == 1


def test_closed_minimum_primary_boundary_and_cap_endpoint_count():
    result = continuous_value_capacity([0, 1], 0, '1.5', 2, '.25')
    assert result['value_capacity'] == 3  # 1.5, 1.75, 2; inclusive lower point.
    assert result['value_capacity'] == max(result['direct_capacity'], result['gap_capacity'])


def test_matched_five_partner_models_have_exact_witnesses_and_upper_bounds():
    examples = [([0, '.0001', '.0002', '.0003', '.05'],
                 ['1.0097', '1.0197', '1.0297', '1.0397', '1.0497'], 5),
                ([0, '.0125', '.025', '.0375', '.05'],
                 ['1.0025', '1.0125'], 2)]
    for xs, path, expected in examples:
        result = continuous_value_capacity(xs, '.95', '1.0002', '1.05', '.01')
        assert result['value_capacity'] == expected
        rows = inspect_sequence(xs, '.95', path, '1.05', '.01', '.05')
        assert len(rows) == expected and all(r['value_joint'] for r in rows)
        assert all(r['D'] == 'not_evaluated_scalar_model' for r in rows)


def test_release_amplitude_may_decrease_and_restore_legacy_witness():
    path = ['1.05', '1.04']
    rows = inspect_sequence([0, '.06', '.10'], '.9', path, '1.10', '.05', '.10')
    assert all(r['value_joint'] for r in rows)
    oracle = finite_capacity([0, '.06', '.10'], '.9', path, '1.10', '.05', '.10')
    assert oracle['capacity'] == 2 and oracle['path'] == tuple(map(F, path))


def test_four_partner_legacy_constraint_reduces_capacity_on_exact_candidate_grid():
    xs = [0, '.06', '.08', '.10']
    candidates = [F(100+i, 100) for i in range(1, 11)]
    value = finite_capacity(xs, '.9', candidates, '1.1', '.02', '.1', require_legacy=False)
    retained = finite_capacity(xs, '.9', candidates, '1.1', '.02', '.1')
    assert value['capacity'] == 3
    assert retained['capacity'] == 2
    assert all(r['value_joint'] for r in inspect_sequence(xs, '.9', retained['path'], '1.1', '.02', '.1'))


def test_margin_matched_family_and_direct_escape_keep_every_old_source():
    large = [0, '.0001', '.0002', '.0003', '.044']
    dense = [0, '.011', '.022', '.033', '.044']
    cases = [(large, ['1.0097', '1.0197', '1.0297', '1.0397', '1.0497'], 5),
             (dense, ['1.007', '1.017'], 2)]
    for xs, path, count in cases:
        model = continuous_value_capacity(xs, '.956', '1.0062', '1.05', '.01')
        assert model['value_capacity'] == count
        assert all(r['value_joint'] for r in inspect_sequence(xs, '.956', path, '1.05', '.01', '.05'))
        direct = [F('.956')+F(t,100) for t in range(1,6)]
        assert all(r['value_joint'] for r in inspect_sequence(xs, '.956', direct, '1.05', '.01', '.05'))


def test_weak_partner_guard_recovers_value_but_can_remove_legacy_use():
    xs = [0, '.011', '.022', '.033', '.044']
    path = [F(1)+F(t,100) for t in range(1,6)]
    guard = lambda a, x: a <= F('.956') or x == 0
    rows = inspect_sequence(xs, '.956', path, '1.05', '.01', '.05', compatibility=guard)
    assert all(r['checks']['G'] and r['checks']['P'] and r['checks']['H'] for r in rows)
    assert [r['checks']['L'] for r in rows] == [True, False, False, False, False]
    removed = [sum(a+F(str(x)) <= F('1.05') and not guard(a,F(str(x))) for x in xs)
               for a in path]
    assert removed == [3, 2, 1, 0, 0]


def test_fixed_linear_budget_recovers_four_steps_and_repairs_all_dense_sources():
    xs = list(map(F, ['0', '.011', '.022', '.033', '.044']))
    a0 = F('.956')
    path = [F('1.01')-j*F('.011')/12 for j in range(4)]
    budget = lambda a, x: 12*(a-a0)+x <= F('.648')
    rows = inspect_sequence(xs, a0, path, '1.05', '.01', '.05', compatibility=budget)
    assert all(r['value_joint'] for r in rows)
    assert [r['frontier'] for r in rows] == [a+x for a,x in zip(path,xs)]
    assert rows[-1]['frontier'] == F('1.04025')
    assert int((rows[-1]['frontier']-1)//F('.01')) == 4
    assert sum(sum(a+x <= F('1.05') and not budget(a,x) for x in xs) for a in path) == 6
    # The only stronger partner cannot pair with ANY allowed new amplitude.
    assert F('1.0062')+xs[-1] > F('1.05')
    # For all other partners, the linear resource constraint directly upper-bounds utility.
    assert max(F('1.01')+F(11,12)*x for x in xs[:-1]) == F('1.04025')
