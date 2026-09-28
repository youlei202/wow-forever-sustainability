"""Small, exhaustive scientific invariants for the paper's exact core.

These checks require no native engine, archived measurements, or solver package.
Their evidence scope is finite response tables with exact rational arithmetic.
"""
from dataclasses import replace
from fractions import Fraction
from functools import lru_cache
from itertools import combinations

import pytest

from wowfs.experiments import co_exact, co_reference, mi_theory


def subsets(items):
    ordered = sorted(items)
    return (frozenset(member) for width in range(len(ordered) + 1)
            for member in combinations(ordered, width))


def source_mass(model, selected, item, level):
    """Literal quantified definition, without production retention helpers."""
    return sum(weight for q, weight in enumerate(model.weights)
               if any(item in row.support and row.support <= selected
                      and row.values[q] >= level[q] - model.tolerance[q]
                      for row in model.configurations))


def support_fixture():
    # A two-task square survives; the separate alternating path peels from
    # both endpoints. An isolated source also has to be deleted.
    slots = {name: 0 for name in ("a", "b", "c", "d", "isolated")}
    slots |= {name: 1 for name in ("u", "v", "w", "z")}
    rows = [("a", "u", (10, 0)), ("a", "v", (0, 10)),
            ("b", "u", (0, 10)), ("b", "v", (10, 0)),
            ("c", "w", (10, 0)), ("d", "w", (0, 10)),
            ("d", "z", (10, 0))]
    return co_reference.Model(
        slots, tuple(co_reference.Configuration(frozenset((left, right)), values)
                     for left, right, values in rows),
        (Fraction(1, 2), Fraction(1, 2)), (0, 0), Fraction(1))


@pytest.mark.parametrize("required_mass", [Fraction(0), Fraction(1, 2), Fraction(1)])
@pytest.mark.parametrize("remove_square_vertex", [False, True])
def test_core_is_greatest_of_every_supporting_subset(required_mass, remove_square_vertex):
    model = replace(support_fixture(), required_mass=required_mass)
    ambient = model.items - ({"a"} if remove_square_vertex else set())
    level = (10, 10)
    fixed_points = [selected for selected in subsets(ambient)
                    if all(source_mass(model, selected, item, level) >= required_mass
                           for item in selected)]
    expected = frozenset().union(*fixed_points)
    core, _ = co_reference.support_core(model, ambient, level)
    synchronous, _ = co_reference.core_slow(model, ambient, level)
    assert core == synchronous == expected
    assert all(point <= core for point in fixed_points)
    assert core in fixed_points
    if required_mass == 1 and not remove_square_vertex:
        assert core == {"a", "b", "u", "v"}


def test_every_admissible_deletion_order_has_the_same_terminal_core():
    model, level = support_fixture(), (10, 10)

    @lru_cache(maxsize=None)
    def all_terminals(selected):
        deletable = [item for item in selected
                     if source_mass(model, selected, item, level) < model.required_mass]
        if not deletable:
            return frozenset({selected})
        return frozenset().union(*(all_terminals(selected - {item}) for item in deletable))

    expected = frozenset({"a", "b", "u", "v"})
    assert all_terminals(model.items) == {expected}
    assert all_terminals.cache_info().currsize > 5  # Actually explore branching orders.
    core, trace = co_reference.support_core(model, model.items, level)
    assert core == expected
    assert {event["item"] for event in trace} == model.items - expected
    assert all(event["available_task_mass"] < model.required_mass for event in trace)


def conflict_fixture():
    left, right = ("old", "x1", "x2"), ("base", "y1", "y2")
    slots = {item: 0 for item in left} | {item: 1 for item in right}
    conflicts = {frozenset(("x1", "y1")), frozenset(("x2", "y2"))}
    rows = tuple(co_reference.Configuration(
        frozenset((a, b)), (15 if frozenset((a, b)) in conflicts
                           else 10 if (a, b) == ("old", "base") else 12,))
        for a in left for b in right)
    return co_reference.Model(slots, rows, (1,), (2,), 1)


@pytest.mark.parametrize("required,expected_cover,expected_maxima", [
    (frozenset(), 2, 4),
    (frozenset({"x1"}), 1, 2),
    (frozenset({"x1", "y1"}), 0, 0),
])
def test_conflict_branches_cover_exactly_all_feasible_publications(
        required, expected_cover, expected_maxima):
    model, level = conflict_fixture(), (12,)
    mandatory = frozenset({"old", "base"}) | required
    # Independent exhaustive definition includes actual frontier attainment.
    feasible = []
    for selected in subsets(model.items):
        if not mandatory <= selected:
            continue
        rows = [row for row in model.configurations if row.support <= selected]
        if not rows or max(row.values[0] for row in rows) != level[0]:
            continue
        if all(source_mass(model, selected, item, level) >= model.required_mass
               for item in selected):
            feasible.append(selected)
    maxima = {selected for selected in feasible
              if not any(selected < other for other in feasible)}
    answer = co_reference.fixed_frontier(model, mandatory, level, all_branches=True)
    assert answer["feasible"] == bool(feasible)
    assert answer["cover_size"] == expected_cover
    assert set(answer["kernels"]) == maxima
    assert len(maxima) == expected_maxima
    assert all(any(selected <= kernel for kernel in answer["kernels"])
               for selected in feasible)
    if required == {"x1"}:
        assert answer["unary_forbidden"] == {"y1"}
    if required == {"x1", "y1"}:
        assert answer["reason"] == "mandatory_above_frontier"


def test_retaining_below_a_level_does_not_prove_frontier_attainment():
    model = replace(conflict_fixture(), tolerance=(3,))
    result = co_reference.fixed_frontier(model, {"old", "base"}, (13,), all_branches=True)
    assert not result["feasible"]
    assert not result["kernels"]


def physical_construction(n, family):
    table, selectors = mi_theory.construction(n, family)
    gloves = ["old", "helper"] + [f"x{i}" for i in range(n)]
    boots = ["base"] + [f"selector_{i}" for i in range(len(selectors))]
    slots = {item: 0 for item in gloves} | {item: 1 for item in boots}
    rows = tuple(co_exact.Configuration(
        frozenset((glove, boot)), (Fraction(table[g][b], mi_theory.SCALE),))
        for g, glove in enumerate(gloves) for b, boot in enumerate(boots))
    return co_exact.Model(slots, rows, (1,), (1,), 1,
                          frozenset({"old", "base"}), (110,), (1,), 1)


@pytest.mark.parametrize("n,family", [
    (2, frozenset()),
    (2, frozenset({0})),
    (2, frozenset({0, 1, 2})),
    (3, frozenset(range(7))),
])
def test_physical_interface_target_antichain_and_downset_answer_every_query(n, family):
    model = physical_construction(n, family)
    result = co_reference.compile_interface(model)
    assert result["complete"]
    truth = co_exact.exhaustive(model, all_solutions=True)
    assert {frozenset(kernel) for kernel in result["kernels"]} == {
        frozenset(kernel) for kernel in truth["kernels"]}
    targets = frozenset(f"x{i}" for i in range(n))
    projections = {frozenset(kernel) & targets for kernel in result["kernels"]}
    maximal_projections = {projection for projection in projections
                           if not any(projection < other for other in projections)}
    antichain_masks = {sum(1 << i for i in range(n) if f"x{i}" in projection)
                       for projection in maximal_projections}
    assert antichain_masks == set(mi_theory.maximal(family))
    for mask in range(1 << n):
        query = frozenset(f"x{i}" for i in range(n) if mask >> i & 1)
        explicit_answer = co_exact.interface_query(result, query)["status"] == "YES"
        antichain_answer = any(query <= projection for projection in maximal_projections)
        assert explicit_answer == antichain_answer == (mask in family)
    # The final fixture admits every pair but excludes the three-way query.
    if n == 3:
        assert all(mask in family for mask in (3, 5, 6))
        assert 7 not in family
