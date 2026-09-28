"""Analysis semantics on synthetic arrays; these are not native results."""
import numpy as np
import pytest

from wowfs.experiments import r3_phase_analysis as phase
from wowfs.experiments.r3_phase_confirmation_analysis import supported_competitive


def test_components_require_edge_adjacency_and_keep_all_points():
    result = phase.components([[True, True, False], [False, False, True]])
    assert list(map(len, result)) == [2, 1]
    assert sorted(x for group in result for x in group) == [(0, 0), (0, 1), (1, 2)]


def evaluate(monkeypatch, means, old_item=1, anchor_interval=0):
    mean = np.asarray(means, float).reshape(2, 2, 1)
    features = np.zeros((2, 2, 1, 7)); features[..., 0] = .1
    lookup = {(g, p, 0): {"cache_directory": "fixture", "output_sha256": "fixture"}
              for g in range(2) for p in range(2)}
    monkeypatch.setattr(phase, "phase_arrays", lambda *args: (
        [(19019, 1, 2), (871, 1, 2)], mean, np.zeros_like(mean), features, lookup, 32))
    state = {"initial": np.array([0]), "scale": np.array([100.]), "cap": np.array([105.]),
             "before": np.array([0]), "before_raw": np.array([0, 1]), "optimum": np.array([100.]),
             "old_profiles": [np.zeros((1, 7))], "archive_profiles": [np.zeros((1, 7))]}
    old = np.array([[[100.], [99.]], [[120.], [110.]]])
    freeze = {"decisions": {"task_weights": [1]}, "gears": {"old": {"off_hand": old_item}, "unsafe_old": {"off_hand": 19019}}}
    return phase.evaluate_point([], {"headroom": .05}, "fixture", state, freeze,
        ["old", "unsafe_old"], old, old-anchor_interval, old+anchor_interval,
        [{"id": "task"}], ["a", "b"], [19019, 871], [(1, 2)], 8)[0]


def test_one_unsafe_policy_excludes_whole_loadout_and_preserves_raw_power(monkeypatch):
    result = evaluate(monkeypatch, [[99, 106], [101, 102]])
    assert result["raw_unsafe_loadouts"] == 1
    assert result["competitive_tf_loadouts"] == 0
    assert not result["tf_reactivated"]
    assert result["raw_batch_max_power_ratio_to_cap"] == pytest.approx(106/105)
    assert result["raw_all_catalogue_max_power_ratio_to_cap"] == pytest.approx(120/105)
    assert result["after_safe_optimum"] == [102]


def test_source_already_competitive_is_not_reactivated(monkeypatch):
    result = evaluate(monkeypatch, [[102, 103], [101, 100]], old_item=19019)
    assert result["tf_competitive_task_mass"] == 1
    assert result["tf_novel_task_mass"] == 1
    assert not result["tf_reactivated"]
    assert not result["empirical_tf_complement_region"]


def test_frozen_numeric_cap_and_population_anchor_uncertainty_are_distinct(monkeypatch):
    result = evaluate(monkeypatch, [[102, 103], [101, 100]], anchor_interval=10)
    assert result["empirical_region_with_fixed_cap_supported_tf_witness"]
    assert not result["empirical_region_with_supported_safe_tf_witness"]
    assert result["fixed_cap_supported_safe_novel_tf_loadouts"] == 1


def test_incomplete_phase_domain_fails_explicitly():
    with pytest.raises(ValueError, match="Incomplete phase point"):
        phase.phase_arrays([], [{"id": "x", "duration_seconds": 10}], ["a"], [19019], [(1, 2)])


def test_confirmation_frontier_keeps_uncertain_potentially_safe_competitor():
    mean = np.array([[[99.]], [[104.]]])
    se = np.array([[[0.]], [[2.]]])
    close, _, upper, frontier = supported_competitive(mean, se, np.array([100.]),
        np.array([100.]), np.array([100.]), 2, 1024)
    assert frontier[0] == upper[1, 0, 0]
    assert not close.any()


def test_confirmation_frontier_excludes_definitely_unsafe_competitor():
    mean = np.array([[[99.]], [[110.]]])
    close, _, _, frontier = supported_competitive(mean, np.zeros_like(mean),
        np.array([105.]), np.array([100.]), np.array([100.]), 2, 1024)
    assert frontier.tolist() == [100.]
    assert close[:, 0, 0].tolist() == [True, False]
