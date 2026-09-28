import random

import pytest

from wowfs.experiments.mi_theory import (
    SCALE, all_downsets, brute_family, construction, exact_family,
    pair_exclusion_check, perturb, semantic_check, submasks, downclosure,
)


def test_all_downsets_includes_empty_and_known_counts():
    assert [len(all_downsets(n)) for n in range(5)] == [2, 3, 6, 20, 168]
    for n in range(5):
        for family in all_downsets(n):
            table, _ = construction(n, family)
            assert exact_family(table)[0] == family == brute_family(table)


def test_nonprefix_submask_and_downclosure_regression():
    assert set(submasks(0b1011)) == {0, 1, 2, 3, 8, 9, 10, 11}
    assert len(list(submasks(0b1011))) == 8
    assert set(submasks(0)) == {0}
    assert downclosure({0b1011, 0b1100}) == {0, 1, 2, 3, 4, 8, 9, 10, 11, 12}


def test_independent_checker_matches_literal_powerset_after_perturbations():
    # Nonuniform finite tables, including cases outside the theorem's radius.
    rng = random.Random(172)
    for n in (1, 2, 3):
        for _ in range(60):
            table = [[rng.randrange(98, 106)*SCALE for _ in range(4)] for _ in range(n+2)]
            assert exact_family(table)[0] == brute_family(table)
    for family in all_downsets(3):
        table, _ = construction(3, family)
        for eta in (.1, .49, .5, .51, 2):
            changed = perturb(table, eta, 45)
            assert exact_family(changed)[0] == brute_family(changed)


def test_empty_family_and_boundary_corner_are_preserved():
    table, selectors = construction(4, set())
    assert selectors == ()
    assert exact_family(table)[0] == set()
    table, _ = construction(2, {0, 1, 2})
    for eta, expected in ((.49, {0, 1, 2}), (.5, {0, 1, 2, 3}), (.51, {0, 1, 2, 3})):
        changed = [[v-round(eta*SCALE) if v == 104*SCALE else v+round(eta*SCALE) for v in row] for row in table]
        assert exact_family(changed)[0] == expected


def test_target_semantics_forget_helpers_and_symbolic_scope(tmp_path):
    semantic = semantic_check()
    assert semantic["all_target_query_answers_identical"]
    assert semantic["helper_witnesses_differ"]
    assert not semantic["target_semantics_preserve_helper_details"]
    symbolic = pair_exclusion_check(4, tmp_path, 17)
    assert symbolic["query_equivalence"]
    assert symbolic["queried_target_count"] == 256
    assert symbolic["explicit_antichain_count"] == 16


def test_invalid_family_is_rejected():
    with pytest.raises(ValueError):
        construction(2, {3})
