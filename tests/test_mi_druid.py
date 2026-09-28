"""Soundness checks for the independent moment/event reanalysis."""
import numpy as np

from wowfs.experiments.mi_druid import max_min, shifted_retention


def test_shifted_event_covers_continuous_coefficients_and_reference_uncertainty():
    rng = np.random.default_rng(927204)
    for _ in range(100):
        center = rng.normal(size=(2, 3, 3))
        width = rng.uniform(.01, 1, size=center.shape)
        bounds = {"retention_lower": center - width, "retention_upper": center + width}
        reference_lower = rng.uniform(10, 100, size=2)
        reference_upper = reference_lower + rng.uniform(.01, 2, size=2)
        for coefficient in (-.05, -.001, 0, .001, .05):
            shifted = shifted_retention(bounds, coefficient, reference_lower, reference_upper)
            for fraction in (0., .19, .53, 1.):
                reference = reference_lower + fraction * (reference_upper - reference_lower)
                true_old = bounds["retention_lower"] + fraction * (bounds["retention_upper"] - bounds["retention_lower"])
                true_new = true_old + coefficient * reference[:, None, None]
                assert np.all(shifted["retention_lower"] <= true_new + 1e-12)
                assert np.all(shifted["retention_upper"] >= true_new - 1e-12)


def test_max_min_upper_bound_retains_every_possible_source_witness():
    rng = np.random.default_rng(927205)
    for _ in range(100):
        response = rng.uniform(90, 110, size=(2, 6))
        offsets = rng.uniform(.1, 1, size=2)
        truth = response[:, :, None] - response[:, None, :] + offsets[:, None, None]
        upper = truth + rng.uniform(0, .2, size=truth.shape)
        for source in ([0], [1, 3], [0, 1, 2, 3, 4, 5]):
            for frontier in ([1, 2], [0, 1, 2, 3, 4, 5]):
                true_margin = response[:, source].max(axis=1) - response[:, frontier].max(axis=1) + offsets
                assert np.all(max_min(upper, source, frontier) >= true_margin - 1e-12)
