"""Exact finite problem tests, deliberately separate from native evidence."""
from itertools import product
import numpy as np

from wowfs.experiments.r4_feasibility import FiniteProblem, evaluate_admission, eval_all_safe, solve_subset, frontier_closure


def problem(values, sources, protected, protected_sources, **kwargs):
    values = np.asarray(values, float)
    if values.ndim == 1: values = values[:, None, None]
    behavior = np.zeros((*values.shape, 7))
    behavior[len(protected):, ..., 0] = .1
    return FiniteProblem(values, behavior, sources, protected, ["new"], protected_sources,
        np.full(values.shape[-1], 100.), np.full(values.shape[-1], 105.), **kwargs)


def test_all_safe_can_fail_legacy_while_joint_subset_succeeds():
    p = problem([100, 96, 99, 104], [{"A"}, {"B"}, {"new", "A"}, {"new", "A"}], [0, 1], ["A", "B"])
    full = eval_all_safe(p)
    assert full["P"] and not full["L"] and full["failure_reasons"] == ["L"]
    result = solve_subset(p)
    assert result["status"] == "optimal" and result["feasible"]
    assert result["admitted"] == [True, True, True, False]
    closure = frontier_closure(p, result["frontier"])
    assert evaluate_admission(p, closure)["joint_pass"]


def test_multiple_sources_can_share_a_single_configuration_and_task():
    p = problem([100, 99], [{"A", "B", "C"}, {"new", "A"}], [0], ["A", "B", "C"], k_max=1)
    result = solve_subset(p)
    assert result["feasible"] and result["metrics"]["K"] == 1
    assert all(result["metrics"]["source_masses"][s] == 1 for s in ["A", "B", "C"])


def test_protected_unsafe_choice_is_infeasible_instead_of_dropped():
    p = problem([106, 99], [{"A"}, {"new"}], [0], ["A"])
    assert solve_subset(p)["proved_infeasible"]
    assert eval_all_safe(p)["H"] and not eval_all_safe(p)["P"]


def test_optional_old_substitutes_cannot_be_silently_removed():
    import pytest
    with pytest.raises(ValueError, match="Unprotected old-only"):
        problem([100, 99, 99], [{"A"}, {"old_optional"}, {"new"}], [0], ["A"])


def test_item_budget_cannot_hide_an_arbitrary_blacklist_for_identical_features():
    p = problem([100, 96, 99, 104], [{"A"}, {"B"}, {"new", "A"}, {"new", "A"}], [0, 1], ["A", "B"])
    assert solve_subset(p)["feasible"]
    for q in (1, 2):
        constrained = solve_subset(p, rule_rows=q)
        assert constrained["proved_infeasible"]


def test_joint_generic_budget_finds_the_subset_with_sufficient_features():
    p = problem([100, 96, 99, 104], [{"A"}, {"B"}, {"new", "A"}, {"new", "A"}], [0, 1], ["A", "B"])
    result = solve_subset(p, rule_rows=1, features=np.eye(4))
    assert result["feasible"] and result["induced_opening_matches"]
    assert result["admitted"] == [True, True, True, False]


def test_every_batch_item_must_be_useful_not_just_one_strong_item():
    values = np.array([100., 99., 50.])[:, None, None]
    behavior = np.zeros((*values.shape, 7)); behavior[1:, ..., 0] = .1
    p = FiniteProblem(values, behavior, [{"old"}, {"new1"}, {"new2"}], [0],
                      ["new1", "new2"], ["old"], [100.], [105.])
    assert not eval_all_safe(p)["N"]
    assert solve_subset(p)["proved_infeasible"]


def test_milp_matches_exhaustive_subsets_on_small_random_tables():
    rng = np.random.default_rng(7301)
    for _ in range(12):
        values = rng.uniform(89, 109, (6, 2, 3))
        values[:2] = np.minimum(values[:2], 100)
        p = problem(values, [{"A"}, {"B"}] + [{"new", "A" if i % 2 else "B"} for i in range(4)],
                    [0, 1], ["A", "B"], k_max=2)
        feasible = []
        for bits in product((False, True), repeat=4):
            mask = np.array([True, True, *bits])
            metrics = evaluate_admission(p, mask)
            if metrics["joint_pass"]: feasible.append(int(mask.sum()))
        result = solve_subset(p, time_limit=10)
        assert result["status"] in ("optimal", "infeasible")
        assert result["feasible"] == bool(feasible)
        if feasible:
            assert sum(result["admitted"]) == max(feasible)
            assert evaluate_admission(p, frontier_closure(p, result["frontier"]))["joint_pass"]


def test_prior_linprog_scheduler_does_not_turn_feasible_milp_into_solver_error():
    import pytest
    import warnings
    from scipy.optimize import linprog
    core=pytest.importorskip('scipy.optimize._highspy._core')
    core._Highs.resetGlobalScheduler(True)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        prior=linprog([1.],bounds=[(0.,1.)],options={'threads':2})
    assert prior.success
    p=problem([100,99],[{'A'},{'new'}],[0],['A'])
    result=solve_subset(p)
    assert result['status']=='optimal' and result['feasible']
    assert result['runtime_scheduler_retry']['initial_status']==4
    assert 'HiGHS Status 0: Not Set' in result['runtime_scheduler_retry']['initial_message']
