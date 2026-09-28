"""Nontrivial proof checks: historical trade, joint novelty, and finite width."""
from fractions import Fraction as F
import importlib.util
from pathlib import Path
import sys

import pytest


_PATH = Path(__file__).resolve().parents[1] / "scripts/verify_theory.py"
_SPEC = importlib.util.spec_from_file_location("theory_verifier", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
theory = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = theory
_SPEC.loader.exec_module(theory)


@pytest.mark.parametrize("instance", [
    theory.Instance(),
    theory.Instance(width=F(1, 25), delta=F(1, 200), rounds=8),
    theory.Instance(width=F(1, 20), delta=F(1, 20), rounds=1),
])
def test_joint_theorem_exactly(instance):
    result = theory.verify(instance)
    assert result["maximum_joint_prefix_scalar"] == 0
    assert result["maximum_joint_prefix_two_constraints"] == instance.rounds
    assert all(row["exact_K"] == 2 for row in result["rounds"])
    assert all(row["novelty_archive"] == instance.delta for row in result["rounds"][1:])
    assert result["generic_same_dimension_contains_structured"]


def test_trade_requires_new_release_and_history():
    model = theory.Instance()
    # Reject all new items: the initial single budget is P+H feasible.
    old_legal = [z for z in model.configs(1) if z[0] <= 0 and
                 int(z[0] == 0) + int(z[1] == 0) <= 1]
    assert all(max(model.utility(z)) <= model.cap for z in old_legal)
    assert (0, 1) in old_legal
    assert not any(z[0] == 1 for z in old_legal)
    # Remove the positive historical witness: a scalar can retain the new pair.
    prices = {-1: 0, 0: 2, 1: 1}
    new_legal = [z for z in model.configs(1) if prices[z[0]] + int(z[1] == 1) <= 1]
    assert (1, 0) in new_legal and (0, 1) not in new_legal
    assert all(max(model.utility(z)) <= model.cap for z in new_legal)


def test_portfolio_changes_when_half_the_tasks_may_be_uncovered():
    model = theory.Instance()
    legal = tuple(z for z in model.configs(5) if model.allowed(z))
    assert theory.minimum_portfolio(model, legal, alpha=F(1, 2))[0] == 1
    assert theory.minimum_portfolio(model, legal, alpha=F(49, 100))[0] == 2


def test_novelty_width_cannot_be_silently_exceeded():
    with pytest.raises(ValueError, match="rounds"):
        theory.Instance(rounds=6)
    with pytest.raises(ValueError, match="beta"):
        theory.Instance(beta=F(1, 20))
