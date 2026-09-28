"""Tests of joint-metric semantics; fixtures do not represent native combat."""
import numpy as np
import pytest

from wowfs.experiments.r2_sequence_analysis import (
    behavior_vector, nearest_distances, portfolio_cover, scalar_reprice,
)


def test_portfolio_counts_gear_and_keeps_required_task_tradeoff():
    result = portfolio_cover(np.array([[100, 0, 100, 0], [0, 100, 0, 100]]),
                             [100] * 4, [100] * 4)
    assert result["K"] == 2
    assert result["maximum_coverage"] == 1
    old = portfolio_cover(np.array([[100, 0, 100, 0]]), [100] * 4, [100] * 4)
    assert old["K"] is None
    assert old["maximum_coverage"] == .5


def test_single_gear_can_cover_four_tasks_without_four_policy_costs():
    result = portfolio_cover(np.array([[100, 100, 100, 100]]), [100] * 4, [100] * 4)
    assert result["K"] == 1


def test_behavior_uses_native_action_families_and_preserves_refund_flow():
    row = {"actions": {
        "otherId:OtherActionAttack/tag:1": {"fraction": .4},
        "spellId:20662": {"fraction": .2},
        "spellId:1680/tag:2": {"fraction": .1},
        "spellId:20569/tag:1": {"fraction": .1},
        "spellId:23894": {"fraction": .1},
        "spellId:777": {"fraction": .1}},
        "resources": [{"type": "ResourceTypeRage", "gain": 100, "actualGain": 80},
                      {"type": "ResourceTypeRage", "gain": -80, "actualGain": -80},
                      {"type": "ResourceTypeMana", "gain": 900, "actualGain": 900}]}
    assert behavior_vector(row, 10) == pytest.approx([.4, .2, .2, .1, .1, .5, .2])


def test_behavior_substitution_considers_more_than_best_performing_old_gear():
    candidate = np.array([[.2, .8], [.8, .2]])
    all_old = np.array([[.5, .5], [.21, .79]])
    assert nearest_distances(candidate, all_old) == pytest.approx([.01, .3])


def test_scalar_prices_reject_unsafe_and_protect_historical_new_witness():
    incidence = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
    prices, status = scalar_reprice(incidence, [False, False, True],
                                    [True, False, False], [1], [0, 0, 0])
    assert status["solver_status"] == "optimal_margin_with_new_witness"
    assert incidence[0] @ prices <= 1 + 1e-8
    assert incidence[1] @ prices <= 1 + 1e-8
    assert incidence[2] @ prices >= 1 + 1e-6


def test_scalar_two_trade_obstruction_keeps_prior_prices_and_failure():
    # Protected good rows sum to the same incidence as unsafe rows.
    incidence = np.array([[1, 0, 1, 0], [0, 1, 0, 1],
                          [1, 0, 0, 1], [0, 1, 1, 0]])
    before = np.array([.2, .2, .2, .2])
    prices, status = scalar_reprice(incidence, [False, False, True, True],
                                    [True, True, False, False], [], before)
    assert np.array_equal(prices, before)
    assert status["solver_status"] == "no_positive_rejection_margin"


def test_scalar_must_not_silently_forget_an_unsafe_historical_witness():
    before = np.array([.25])
    prices, status = scalar_reprice([[1]], [True], [True], [], before)
    assert status["solver_status"] == "infeasible_history_contains_unsafe"
    assert np.array_equal(prices, before)
