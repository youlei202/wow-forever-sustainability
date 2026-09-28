"""Sequential metric fixtures are analysis checks, not native observations."""
import numpy as np

from wowfs.experiments.r3_sequence_analysis import new_metrics, source_mass


def fixture():
    means = np.full((1, 3, 4), 100.)
    behavior = np.zeros((1, 3, 4, 7))
    return means, behavior, np.full(4, 100.), np.full(4, 105.)


def test_new_item_identity_cannot_make_copied_behavior_novel():
    old, behavior, scale, cap = fixture()
    result = new_metrics(old, behavior, old.copy(), behavior.copy(), scale, cap,
                         [np.zeros((1, 7)) for _ in range(4)])
    assert result["N"] and result["P"]
    assert not result["D"]


def test_all_old_policies_are_behavioral_substitutes_even_if_noncompetitive():
    old, behavior, scale, cap = fixture()
    old[:, 1] = 1
    behavior[:, 1, :, 0] = .1
    new = np.full_like(old, 100.)
    new_behavior = np.zeros_like(behavior); new_behavior[..., 0] = .1
    result = new_metrics(old, behavior, new, new_behavior, scale, cap,
                         [np.zeros((1, 7)) for _ in range(4)])
    assert result["N"]
    assert not result["D"]


def test_historical_profile_blocks_repeated_novelty_even_if_current_old_differs():
    old, behavior, scale, cap = fixture()
    new_behavior = np.zeros_like(behavior); new_behavior[..., 0] = .1
    history = [np.array([[.1, 0, 0, 0, 0, 0, 0]]) for _ in range(4)]
    result = new_metrics(old, behavior, old.copy(), new_behavior, scale, cap, history)
    assert not result["D"]


def test_source_mass_recomputes_competitiveness_against_new_frontier():
    means = np.array([[[94.] * 4] * 3, [[100.] * 4] * 3])
    sources = [["old", "shared"], ["new", "shared"]]
    masses = source_mass(means, sources, np.full(4, 100.), np.full(4, 100.))
    assert masses == {"new": 1., "old": 0., "shared": 1.}
