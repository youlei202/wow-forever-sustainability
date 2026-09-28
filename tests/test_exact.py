"""Tests of scientific guarantees, not snapshots of favorable benchmark rows."""

import itertools
import json

import numpy as np

from wowfs.experiments.exact import (
    METHODS,
    PROTOCOL,
    _edge_mask,
    _solve_budgets,
    _two_trade_certificate,
    build_domain,
    minimum_portfolio,
    run_instance,
)


def test_exact_portfolio_matches_bruteforce():
    # No single configuration covers both tasks; two suffice.
    values = np.array([[1.0, 0.5], [0.5, 1.0], [0.7, 0.7]])
    k, portfolio = minimum_portfolio(values, np.ones(2), epsilon=0.05, alpha=0)
    assert k == 2
    assert np.all(values[portfolio].max(axis=0) >= 0.95)
    rng = np.random.default_rng(704)
    for _ in range(12):
        table = rng.random((7, 4))
        k, _ = minimum_portfolio(table, np.ones(4), epsilon=0.15, alpha=0.25)
        brute = None
        for n in range(1, 8):
            if any(np.sum(table[list(rows)].max(axis=0) >= table.max(axis=0) - 0.15 - 1e-12) >= 3
                   for rows in itertools.combinations(range(7), n)):
                brute = n
                break
        assert k == brute


def test_initial_anchor_reveal_visibility_and_paired_order_design():
    first, second = build_domain(0), build_domain(1)
    assert first.response.shape == (729, 3, 8)
    np.testing.assert_array_equal(first.response, second.response)
    assert first.order != second.order
    assert len(first.visible_ids(0)) == 64
    assert len(first.visible_ids(6)) == 729
    np.testing.assert_allclose(first.cap, 1.05 * first.response[first.initial_ids].max(axis=(0, 1)))
    for round_number in range(7):
        visible = first.configurations[first.visible_ids(round_number)]
        for slot in set(range(6)) - set(first.order[:round_number]):
            assert np.all(visible[:, slot] < 2)


def test_hyperedge_rules_equal_same_dimension_generic_budgets_and_safe_envelope():
    for variant in ("pair", "triple", "mixed"):
        domain = build_domain(4, variant)
        allowed = np.ones(729, dtype=bool)
        prices = []
        for hazard in domain.hazards:
            allowed &= ~_edge_mask(domain.configurations, hazard)
            row = np.zeros(18)
            for slot, choice in hazard.items:
                row[3 * slot + choice] = 1 / (len(hazard.items) - 1)
            prices.append(row)
        np.testing.assert_array_equal(allowed, np.all(domain.incidence @ np.asarray(prices).T <= 1 + 1e-10, axis=1))
        np.testing.assert_array_equal(allowed, np.all(domain.response <= domain.cap[None, None, :], axis=(1, 2)))


def test_two_trade_proves_scalar_obstruction_but_two_budgets_admit_new():
    # Equip one of two choices in each of two slots. Diagonal is safe.
    incidence = np.array([[1, 0, 1, 0], [1, 0, 0, 1], [0, 1, 1, 0], [0, 1, 0, 1]], dtype=float)
    safe = np.array([True, False, False, True])
    new = np.array([False, False, False, True])
    scalar = _solve_budgets(incidence, safe, new, np.array([0]), 1, 5)
    assert scalar["solver_status"] == "infeasible"
    two = _solve_budgets(incidence, safe, new, np.array([0]), 2, 5)
    assert two["solver_status"] == "optimal"
    np.testing.assert_array_equal(two["allowed"], safe)
    # Verify the domain-sized combinatorial certificate independent of LP tolerances.
    domain = build_domain(0, "pair")
    visible = domain.visible_ids(6)
    safe = np.all(domain.response <= domain.cap[None, None, :], axis=(1, 2))
    new = domain.configurations[:, 0] == 2
    historical_id = int(np.dot(np.ones(6, dtype=int), 3 ** np.arange(5, -1, -1)))
    certificate = _two_trade_certificate(domain.configurations, domain.incidence, safe, new, np.array([historical_id]))
    assert certificate is not None
    assert certificate["new_candidates_covered"] == int(np.sum(safe & new))
    for p, h, q, r in certificate["witnesses_local_ids"]:
        np.testing.assert_array_equal(domain.incidence[p] + domain.incidence[h], domain.incidence[q] + domain.incidence[r])
        assert not safe[q] and not safe[r]


def test_runner_contract_history_metrics_and_checkpoint():
    checkpoints = []
    result = run_instance(0, "pair", 2, checkpoints.append)
    json.dumps(result, allow_nan=False)
    assert len(result["rounds"]) == 2 * len(METHODS)
    assert len(checkpoints) == 2
    assert result["evidence"]["native_engine"] is False
    assert result["evidence"]["physical_simulations"] == 0
    assert result["evidence"]["capacity_T_star_solved"] is False
    assert result["evidence"]["protocol"] == PROTOCOL
    for row in result["rounds"]:
        assert row["scope"] == "abstract_exact"
        assert row["joint_oracle"] is False
        assert row["power_ratio"] == row["power_cap_ratio"] * 1.05 or np.isclose(row["power_ratio"], row["power_cap_ratio"] * 1.05)
        assert row["K_status"] == "exact_set_cover_dp"
        if row["method"] == "compatible_scalar_full_history":
            assert row["H_all"] == 1
    for row in result["relevance"]:
        if row["kind"] == "current_new":
            assert row["effect_contribution"] is not None
