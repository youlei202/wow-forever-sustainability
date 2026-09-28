#!/usr/bin/env python3
"""Exact rational verification of docs/THEORY.md; no native simulator claims."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from fractions import Fraction as F
from itertools import combinations
import json
import os
from pathlib import Path


@dataclass(frozen=True)
class Instance:
    a: F = F(1, 4)
    width: F = F(1, 20)
    epsilon: F = F(1, 20)
    delta: F = F(1, 100)
    beta: F = F(2, 25)
    rounds: int = 5

    def __post_init__(self) -> None:
        if not 0 < self.width <= self.epsilon < self.a < 1:
            raise ValueError("Require 0 < width <= epsilon < a < 1")
        if self.rounds < 1 or self.delta <= 0 or self.rounds * self.delta > self.width:
            raise ValueError("Require positive horizon/delta and rounds * delta <= width")
        if self.beta <= self.width:
            raise ValueError("Require beta > width")

    @property
    def cap(self) -> F:
        return 1 + self.a

    def left_items(self, t: int) -> tuple[int, ...]:
        # -1 is neutral; 0 is the initial positive anchor; j>=1 arrives at j.
        return tuple(range(-1, t + 1))

    def q(self, left: int) -> F:
        return -self.a if left == -1 else self.a - self.width + left * self.delta

    @staticmethod
    def channel(left: int) -> int | None:
        return None if left == -1 else 1 - (left % 2)

    def configs(self, t: int) -> tuple[tuple[int, int], ...]:
        return tuple((left, right) for left in self.left_items(t) for right in (0, 1))

    def prices(self, z: tuple[int, int]) -> tuple[int, int]:
        left, right = z
        return (int(self.channel(left) == 1) + int(right == 0),
                int(self.channel(left) == 0) + int(right == 1))

    def allowed(self, z: tuple[int, int]) -> bool:
        return max(self.prices(z)) <= 1

    def utility(self, z: tuple[int, int]) -> tuple[F, F]:
        left, right = z
        mismatch = self.channel(left) is not None and self.channel(left) != right
        bonus = self.beta * int(mismatch)
        return 1 + self.q(left) + bonus, 1 - self.q(left) + bonus


def distance(a: tuple[F, F], b: tuple[F, F]) -> F:
    return max(abs(x - y) for x, y in zip(a, b))


def incidence(z: tuple[int, int], t: int) -> tuple[int, ...]:
    return tuple(int(z[0] == left) for left in range(-1, t + 1)) + (
        int(z[1] == 0), int(z[1] == 1))


def add_vectors(a: tuple[int, ...], b: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(x + y for x, y in zip(a, b))


def minimum_portfolio(model: Instance, legal: tuple[tuple[int, int], ...],
                      alpha: F = F(1, 20)) -> tuple[int, tuple[tuple[int, int], ...]]:
    optimum = tuple(max(model.utility(z)[task] for z in legal) for task in (0, 1))
    for k in range(1, len(legal) + 1):
        for group in combinations(legal, k):
            covered = sum(max(model.utility(z)[task] for z in group) >=
                          optimum[task] - model.epsilon for task in (0, 1))
            if F(covered, 2) >= 1 - alpha:
                return k, group
    raise AssertionError("The complete finite portfolio must cover both tasks")


def verify(model: Instance = Instance()) -> dict:
    archive: dict[tuple[int, int], tuple[F, F]] = {}
    rows = []
    for t in range(model.rounds + 1):
        configs = model.configs(t)
        legal = tuple(z for z in configs if model.allowed(z))
        unsafe = tuple(z for z in configs if max(model.utility(z)) > model.cap)
        assert set(legal).isdisjoint(unsafe)
        assert set(legal) | set(unsafe) == set(configs)
        assert set(archive).issubset(legal)
        assert all(model.utility(z) == original for z, original in archive.items())
        optimum = tuple(max(model.utility(z)[task] for z in legal) for task in (0, 1))
        k, portfolio = minimum_portfolio(model, legal)
        assert k == 2
        source_weights = {}
        for source in model.left_items(t):
            witnesses = tuple(z for z in legal if z[0] == source)
            count = sum(max(model.utility(z)[task] for z in witnesses) >=
                        optimum[task] - model.epsilon for task in (0, 1))
            source_weights[str(source)] = F(count, 2)
        assert min(source_weights.values()) >= F(1, 2)
        novelty_current = novelty_archive = None
        new_weight = None
        if t:
            new = tuple(z for z in legal if z[0] == t)
            assert len(new) == 1
            old_current = tuple(z for z in legal if z[0] != t)
            novelty_current = min(distance(model.utility(new[0]), model.utility(z))
                                  for z in old_current)
            novelty_archive = min(distance(model.utility(new[0]), value)
                                  for value in archive.values())
            assert novelty_current == novelty_archive == model.delta
            assert model.utility(new[0])[0] == optimum[0]
            new_weight = F(sum(model.utility(new[0])[task] >= optimum[task] - model.epsilon
                               for task in (0, 1)), 2)
            assert new_weight >= F(1, 2)
        rows.append({
            "round": t, "configurations": len(configs), "legal": len(legal),
            "unsafe": len(unsafe), "optimal_utilities": optimum,
            "cap": model.cap, "novelty_current": novelty_current,
            "novelty_archive": novelty_archive, "new_task_weight": new_weight,
            "legacy_source_task_weights": source_weights, "exact_K": k,
            "portfolio": portfolio, "history_witnesses_checked": len(archive),
            "all_joint_conditions": t > 0,
        })
        archive.update({z: model.utility(z) for z in legal})

    good = ((0, 1), (1, 0))
    bad = ((0, 0), (1, 1))
    good_sum = add_vectors(*(incidence(z, 1) for z in good))
    bad_sum = add_vectors(*(incidence(z, 1) for z in bad))
    assert good_sum == bad_sum
    assert all(model.allowed(z) for z in good)
    assert all(model.utility(z)[0] > model.cap for z in bad)
    assert good[0] in tuple(z for z in model.configs(0) if model.allowed(z))
    # At initialization a single budget represents the common safe set exactly.
    initial_scalar = lambda z: int(z[0] == 0) + int(z[1] == 0) <= 1
    assert all(initial_scalar(z) == model.allowed(z) for z in model.configs(0))
    # The structured class is explicitly represented inside generic two budgets.
    assert all(model.allowed(z) == all(x <= 1 for x in model.prices(z))
               for z in model.configs(model.rounds))

    initial_optimum, final_optimum = rows[0]["optimal_utilities"], rows[-1]["optimal_utilities"]
    growth = tuple(final_optimum[i] / initial_optimum[i] - 1 for i in (0, 1))
    assert all(value >= 0 for value in growth)
    return {
        "evidence_scope": "abstract_exact_rational_theorem_instance",
        "native_forever_simulations": 0,
        "originality": "UNESTABLISHED",
        "parameters": vars(model), "rounds": rows,
        "maximum_joint_prefix_scalar": 0,
        "maximum_joint_prefix_two_constraints": model.rounds,
        "generic_same_dimension_contains_structured": True,
        "total_growth_from_initial_task_optimum": growth,
        "scalar_obstruction": {"requires": ["P", "H", "N"],
                               "required": good, "unsafe": bad,
                               "required_incidence_sum": good_sum,
                               "unsafe_incidence_sum": bad_sum,
                               "proof": "required total <= 2B; unsafe total > 2B; totals equal"},
        "verification": "all checks passed using exact rational arithmetic",
    }


def encode(value):
    if isinstance(value, F):
        return {"rational": str(value), "decimal": float(value)}
    raise TypeError(type(value).__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1]
    work = Path(os.environ.get("WOWFS_WORK_ROOT",
                              source.parent.parent / "wow-forever-sustainability-work"))
    output = (args.output or work / "artifacts/latest/theory/THEORY_VERIFICATION.json").resolve()
    if output.is_relative_to(source):
        parser.error("Generated verification outputs must be outside the source repository")
    result = verify()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, default=encode) + "\n", encoding="utf-8")
    print(json.dumps({"verification": result["verification"], "output": str(output),
                      "scalar_prefix": 0, "two_constraint_prefix": result["parameters"]["rounds"]}))


if __name__ == "__main__":
    main()
