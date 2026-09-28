import numpy as np

from wowfs.experiments.fc_finite_reference import dense_bound_certificate
from wowfs.experiments.fc_mechanism_capacity import finite_oracle
from wowfs.experiments.fc_continuation import remaining_capacity


def test_remaining_capacity_never_refunds_realized_headroom():
    assert remaining_capacity(0.) == 5
    assert remaining_capacity(.03) == 2
    assert remaining_capacity(.041) == 0
    assert remaining_capacity(.05) == 0
    assert remaining_capacity(.051) is None


def test_existing_contrast_combinations_recover_exact_geometry():
    # Deterministic utility gives zero-width intervals. Tasks have distinct
    # scales and slopes; the binding task alone certifies the direct boundary.
    reference = np.repeat(np.array([[100.], [240.]]), 32, axis=1)
    ratios = np.array([[1.], [.4]])
    zero = .956*reference
    high = zero+.148*reference*ratios
    cert = dense_bound_certificate(zero, high, reference, 5.)
    np.testing.assert_allclose(cert['gap_minus_two_g_reference_upper'],
        ((.011*ratios-.02)*reference).mean(axis=1))
    np.testing.assert_allclose(cert['lambda_minus_h_minus_two_g_reference_lower'],
        ((.0502*ratios-.03)*reference).mean(axis=1))
    assert cert['all_task_gap_at_most_two_g']
    assert cert['some_task_lambda_above_h_minus_two_g']


def test_dense_bound_can_fail_due_to_wide_completion_gap():
    reference = np.full((1, 20), 100.)
    zero = np.full((1, 20), 90.)
    cert = dense_bound_certificate(zero, zero+.148*3*reference, reference, 5.)
    assert not cert['all_task_gap_at_most_two_g']


def test_finite_order_oracle_retains_nonmonotone_primary_repair():
    # A smaller second primary reaches the cap with an old partner that was
    # unavailable to the first. An amplitude-monotone search would miss it.
    primaries = np.array([.9, 1.05, 1.04])
    partners = np.array([0., .06, .10])
    utility = (primaries[:, None]+partners[None, :])[:, :, None]
    admitted = utility[:, :, 0] <= 1.10+1e-12
    cfg = dict(task_weights=[1.], fixed_headroom=.10, legacy_epsilon=.10,
        legacy_required_mass=1., portfolio_coverage=1., portfolio_K=1,
        meaningful_gain=.05, gain_required_mass=1.)
    answer, _ = finite_oracle(utility, admitted, 0, [1.], cfg, True)
    assert answer['capacity'] == 2
    assert answer['path'] == [1, 2]
    assert all(row['checks']['N_and_L_all_retained_sources'] for row in answer['path_rows'])
