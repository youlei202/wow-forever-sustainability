import numpy as np
import pytest

from wowfs.experiments.oe_joint_mechanism_audit import means, precision, quartet


def synthetic_quartet():
    # Shared stochastic level dominates, while each paired contrast is fixed.
    s = np.array([90., 100., 110., 105., 95., 98., 102., 100.])
    a, x = s + 2., s + 3.
    joint = s + 8.
    return [{'task_id': 'q', 'reference': s, 'one_a': a, 'one_x': x,
             'joint': joint, 'forecast': a + x - s, 'mixed': joint - a - x + s}]


def test_h_window_requires_both_isolated_updates_and_additive_forecast_safe():
    q = synthetic_quartet()
    m = means(q)
    assert m['mean_admissible_h_lower'] == pytest.approx(.05)
    assert m['mean_admissible_h_upper'] == pytest.approx(.08)
    assert m['tasks'][0]['mixed_relative_mean'] == pytest.approx(.03)
    q[0]['one_a'] = q[0]['reference'] + 20.
    assert not means(q)['has_mean_window']


def test_paired_covariance_is_preserved_and_zero_se_not_inflated():
    p = precision(synthetic_quartet(), .06, 4096)
    mixed = p['tasks'][0]['mixed']
    assert mixed['relative_halfwidth'] == 0.
    assert mixed['relative_lower'] == mixed['relative_upper'] == pytest.approx(.03)
    assert p['pilot_based_h_interval'][0] > .05
    assert p['pilot_based_h_interval'][1] < .08


def test_larger_declared_family_widens_intervals():
    q = synthetic_quartet()
    small = precision(q, .06, 4096)
    large = precision(q, .06, 4096, family_multiplier=3)
    assert large['family_size'] == 15
    assert large['critical'] > small['critical']
    assert large['pilot_based_h_interval'][0] > small['pilot_based_h_interval'][0]
    assert large['pilot_based_h_interval'][1] < small['pilot_based_h_interval'][1]


def test_quartet_rejects_different_seed_blocks_and_missing_corner():
    data={(a,x,'q'):{'seed_block_id':'7:2','dps_samples':[1.,2.]}
          for a in ('a00','a01') for x in ('x0','x1')}
    assert len(quartet(data,'a01','x1','x0')) == 1
    data[('a01','x1','q')]['seed_block_id']='8:2'
    with pytest.raises(ValueError,match='unpaired'):
        quartet(data,'a01','x1','x0')
    del data[('a01','x1','q')]
    with pytest.raises(ValueError,match='Missing'):
        quartet(data,'a01','x1','x0')
