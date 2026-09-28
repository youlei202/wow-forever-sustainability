"""Exactly enumerated *abstract* equipment domains, not a combat simulator.

The finite response function is deterministic and explicitly constructed.  No
result from this module is evidence about a WoW class, race, or native engine.
An instance has six slots, two initial choices per slot, one revealed choice
per round, eight fixed tasks, and three fixed policy response vectors.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import time
from dataclasses import dataclass
from typing import Callable

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix


SCOPE = "abstract_exact"
VARIANTS = ("pair", "triple", "mixed")
METHODS = (
    "unrestricted_extension",
    "frozen_scalar",
    "compatible_scalar",
    "compatible_scalar_full_history",
    "generic_two_budget",
    "generic_matched_budget",
    "structured_hyperedges",
    "safe_set_envelope",
)
PROTOCOL = {
    "scope": SCOPE,
    "slots": 6,
    "initial_choices_per_slot": 2,
    "final_choices_per_slot": 3,
    "final_configurations": 729,
    "tasks": 8,
    "policies": 3,
    "horizon": 6,
    "total_cap_slack": 0.05,
    "epsilon_new": 0.05,
    "epsilon_legacy": 0.05,
    "epsilon_portfolio": 0.05,
    "epsilon_floor": 0.05,
    "minimum_task_weight": 0.05,
    "delta_behavior": 0.012,
    "alpha_portfolio": 0.05,
    "K_bound": 4,
    "behavior": "8 task values after exact maximization over 3 policies, divided by fixed initial scales; L-infinity distance",
    "history_registration": "initial and each round: lexicographic minimum, lexicographic maximum, and lexicographic first exact maximizers on tasks 0 and 4",
    "novelty_archive": "all configurations admitted in any previous round, with fixed physics and behavior; stronger than representative-only archive",
    "legacy_sources": "all initial choices form source initial; each previously revealed item is a separate source",
    "initial_rule": "one additive nonnegative budget excludes the first hazard edge; its exact admitted set defines the initial anchor",
    "frozen_new_price": "arithmetic mean of the two old item prices in the same slot, fixed before reveals",
    "unrestricted_extension": "retains initial budget and assigns zero prices to newly revealed items; introduces no additional control",
    "solver_separation_margin": 1e-5,
    "solver_time_limit_seconds_scalar": 2.0,
    "solver_time_limit_seconds_two_budget": 1.0,
    "solver_objective": "require a current-new admitted configuration; then lexicographically maximize competitive legacy-source coverage, current-new configuration count, total safe configuration count; achieved rule, not joint PNDLHC oracle",
    "generic_matched_budget": "same visible hyperedge information and number of budgets as structured; initialize by exact additive re-encoding of every forbidden conjunction; this reaches the all-safe count upper bound",
    "paired_order_design": "pool_seed = seed // 2; each adjacent pair of seeds shares the final pool and changes revelation order",
    "information": "full deterministic response table for currently visible configurations only; no stochastic fights or native engine",
}


@dataclass(frozen=True)
class Hazard:
    items: tuple[tuple[int, int], ...]
    coefficient: float
    label: str


@dataclass
class Domain:
    seed: int
    pool_seed: int
    variant: str
    configurations: np.ndarray
    incidence: np.ndarray
    response: np.ndarray
    base_response: np.ndarray
    hazards: tuple[Hazard, ...]
    order: tuple[int, ...]
    initial_prices: np.ndarray
    initial_ids: np.ndarray
    scale: np.ndarray
    cap: np.ndarray

    def visible_ids(self, round_number: int) -> np.ndarray:
        revealed = set(self.order[:round_number])
        mask = np.ones(len(self.configurations), dtype=bool)
        for slot in range(6):
            if slot not in revealed:
                mask &= self.configurations[:, slot] < 2
        return np.flatnonzero(mask)


def _edge_mask(configurations: np.ndarray, hazard: Hazard) -> np.ndarray:
    return np.all(
        np.column_stack([configurations[:, slot] == choice for slot, choice in hazard.items]),
        axis=1,
    )


def build_domain(seed: int, variant: str = "pair") -> Domain:
    """Construct fixed physics; adjacent seeds differ only in reveal order."""
    if variant not in VARIANTS:
        raise ValueError(f"variant must be one of {VARIANTS}")
    pool_seed = int(seed) // 2
    variant_id = VARIANTS.index(variant)
    rng = np.random.default_rng(np.random.SeedSequence([pool_seed, variant_id, 41021]))
    configurations = np.asarray(list(itertools.product(range(3), repeat=6)), dtype=np.int8)
    incidence = np.zeros((729, 18), dtype=float)
    incidence[np.arange(729)[:, None], np.arange(6)[None, :] * 3 + configurations] = 1
    task_count, policy_count = 8, 3
    item_effects = np.zeros((6, 3, task_count))
    for slot in range(6):
        tilt = rng.uniform(0.0005, 0.0015, task_count)
        signs = np.where((np.arange(task_count) + slot) % 2, 1.0, -1.0)
        item_effects[slot, 0] = tilt * signs
        item_effects[slot, 1] = -tilt * signs
        item_effects[slot, 2] = 0.5 * item_effects[slot, 0]
        item_effects[slot, 2, slot] += rng.uniform(0.031, 0.036)
        item_effects[slot, 2, (slot + 2) % 8] -= rng.uniform(0.016, 0.021)
    policy_effect = np.zeros((policy_count, task_count))
    policy_effect[1] = np.where(np.arange(8) < 4, 0.004, -0.006)
    policy_effect[2] = np.where(np.arange(8) % 2, 0.005, -0.005)
    values = np.ones((729, task_count))
    for slot in range(6):
        values += item_effects[slot, configurations[:, slot]]
    base_response = values[:, None, :] + policy_effect[None, :, :]
    triple_initial = variant == "triple"
    initial_items = ((0, 1), (1, 0), (2, 1)) if triple_initial else ((0, 1), (1, 0))
    cross_extra = ((2, 1),) if triple_initial else ()
    hazards = [
        Hazard(initial_items, 0.17, "initial_cross"),
        Hazard(((0, 2), (1, 1)) + cross_extra, 0.18, "new_cross_old_right"),
        Hazard(((0, 2), (1, 2)) + cross_extra, 0.18, "new_cross_new_right"),
    ]
    if variant == "pair":
        hazards.extend([
            Hazard(((2, 2), (3, 2)), 0.15, "new_pair_23"),
            Hazard(((4, 2), (5, 2)), 0.15, "new_pair_45"),
        ])
    elif variant == "triple":
        hazards.extend([
            Hazard(((1, 2), (3, 2), (4, 2)), 0.18, "new_triple_134"),
            Hazard(((2, 2), (4, 2), (5, 2)), 0.18, "new_triple_245"),
        ])
    else:
        hazards.extend([
            Hazard(((2, 2), (3, 2)), 0.15, "new_pair_23"),
            Hazard(((1, 2), (4, 2), (5, 2)), 0.18, "new_triple_145"),
        ])
    response = base_response.copy()
    for hazard in hazards:
        response[_edge_mask(configurations, hazard)] += hazard.coefficient
    initial_prices = np.zeros(18)
    for slot, choice in initial_items:
        initial_prices[3 * slot + choice] = 1.0 / (len(initial_items) - 1)
    initial_mask = np.all(configurations < 2, axis=1)
    initial_mask &= incidence @ initial_prices <= 1 + 1e-10
    initial_ids = np.flatnonzero(initial_mask)
    scale = response[initial_ids].max(axis=(0, 1))
    cap = (1 + PROTOCOL["total_cap_slack"]) * scale
    order_rng = np.random.default_rng(np.random.SeedSequence([int(seed), variant_id, 9061]))
    order = tuple(int(i) for i in order_rng.permutation(6))
    return Domain(int(seed), pool_seed, variant, configurations, incidence,
                  response, base_response, tuple(hazards), order, initial_prices,
                  initial_ids, scale, cap)


def minimum_portfolio(task_values: np.ndarray, scale: np.ndarray,
                      epsilon: float = 0.05, alpha: float = 0.05) -> tuple[int | None, list[int]]:
    """Exact set-cover DP over at most 2**8 task masks; returns local row IDs."""
    if len(task_values) == 0:
        return None, []
    task_count = task_values.shape[1]
    covered = task_values >= task_values.max(axis=0) - epsilon * scale - 1e-12
    masks = (covered * (1 << np.arange(task_count))).sum(axis=1).astype(int)
    representative = {int(mask): i for i, mask in enumerate(masks) if mask}
    dp: dict[int, tuple[int, ...]] = {0: ()}
    for mask, row in representative.items():
        for current, rows in list(dp.items()):
            merged = current | mask
            if merged not in dp or len(rows) + 1 < len(dp[merged]):
                dp[merged] = rows + (row,)
    required = math.ceil((1 - alpha) * task_count - 1e-12)
    candidates = [rows for mask, rows in dp.items() if mask.bit_count() >= required]
    if not candidates:
        return None, []
    best = min(candidates, key=lambda rows: (len(rows), rows))
    return len(best), list(best)


def _min_distances(query: np.ndarray, reference: np.ndarray) -> np.ndarray:
    if not len(query):
        return np.empty(0)
    if not len(reference):
        return np.full(len(query), np.inf)
    return np.max(np.abs(query[:, None, :] - reference[None, :, :]), axis=2).min(axis=1)


def _register(ids: np.ndarray, values: np.ndarray) -> set[int]:
    """Uniform ex ante registration, including extremal configurations."""
    if not len(ids):
        return set()
    result = {int(ids[0]), int(ids[-1])}
    for task in (0, 4):
        result.add(int(ids[np.argmax(values[ids, task])]))
    return result


def _solve_budgets(incidence: np.ndarray, safe: np.ndarray, new: np.ndarray,
                   history_local: np.ndarray, dimensions: int,
                   time_limit: float, require_new: bool = True,
                   legacy_masks: list[np.ndarray] | None = None) -> dict:
    """MILP for safe compatible additive rules, with explicit achieved status.

    Continuous prices are nonnegative; budget is normalized to one.  Bounds
    [0,2] lose no representable admitted set: each price >1 can be clipped to
    2 without changing any admitted configuration (one item per slot).
    A numerical 1e-5 strict exclusion margin is part of this implemented class.
    MILP optimality certifies the count objective, not all joint metric goals.
    """
    started = time.perf_counter()
    count, items = incidence.shape
    safe_ids, unsafe_ids = np.flatnonzero(safe), np.flatnonzero(~safe)
    legacy_masks = legacy_masks or []
    price_n = dimensions * items
    admitted_n = len(safe_ids)
    assignment_n = len(unsafe_ids) if dimensions == 2 else 0
    source_start = price_n + admitted_n + assignment_n
    variable_n = source_start + len(legacy_masks)
    margin, big_m = PROTOCOL["solver_separation_margin"], 12.0
    # An unsafe configuration must be excluded by one of the two budgets.
    constraint_n = dimensions * (admitted_n + len(history_local)) + dimensions * len(unsafe_ids)
    if require_new:
        constraint_n += 1
    constraint_n += len(legacy_masks)
    matrix = lil_matrix((constraint_n, variable_n), dtype=float)
    lower = np.full(constraint_n, -np.inf)
    upper = np.full(constraint_n, np.inf)
    cursor = 0
    for dimension in range(dimensions):
        price_slice = slice(dimension * items, (dimension + 1) * items)
        for local_i, configuration_i in enumerate(safe_ids):
            matrix[cursor, price_slice] = incidence[configuration_i]
            matrix[cursor, price_n + local_i] = big_m
            upper[cursor] = 1 + big_m
            cursor += 1
        for configuration_i in history_local:
            matrix[cursor, price_slice] = incidence[configuration_i]
            upper[cursor] = 1
            cursor += 1
        for unsafe_i, configuration_i in enumerate(unsafe_ids):
            matrix[cursor, price_slice] = incidence[configuration_i]
            if dimensions == 2:
                indicator_i = price_n + admitted_n + unsafe_i
                matrix[cursor, indicator_i] = big_m if dimension == 0 else -big_m
                lower[cursor] = 1 + margin if dimension == 0 else 1 + margin - big_m
            else:
                lower[cursor] = 1 + margin
            cursor += 1
    if require_new:
        matrix[cursor, price_n:price_n + admitted_n] = new[safe_ids].astype(float)
        lower[cursor] = 1
        cursor += 1
    for source_i, source_mask in enumerate(legacy_masks):
        matrix[cursor, source_start + source_i] = 1
        matrix[cursor, price_n:price_n + admitted_n] = -source_mask[safe_ids].astype(float)
        upper[cursor] = 0
        cursor += 1
    objective = np.zeros(variable_n)
    objective[price_n:price_n + admitted_n] = -(1 + (count + 1) * new[safe_ids])
    source_weight = (count + 1) ** 3
    objective[source_start:] = -source_weight
    variable_upper = np.ones(variable_n)
    variable_upper[:price_n] = 2
    integrality = np.ones(variable_n)
    integrality[:price_n] = 0
    result = milp(
        objective,
        integrality=integrality,
        bounds=Bounds(np.zeros(variable_n), variable_upper),
        constraints=LinearConstraint(matrix.tocsr(), lower, upper),
        options={"time_limit": time_limit, "mip_rel_gap": 0.0, "presolve": True},
    )
    statuses = {0: "optimal", 1: "limit", 2: "infeasible", 3: "unbounded", 4: "solver_error"}
    result_dict = {
        "solver_status": statuses.get(int(result.status), "unknown"),
        "solver_message": str(result.message),
        "solver_seconds": time.perf_counter() - started,
        "require_new": require_new,
        "dimensions": dimensions,
        "objective": "legacy_source_coverage_then_new_admitted_count_then_total_safe_admitted_count",
        "objective_lower_bound": None,
        "objective_upper_bound": None,
        "mip_gap": None,
        "prices": None,
        "allowed": None,
    }
    dual_bound = getattr(result, "mip_dual_bound", None)
    if dual_bound is not None and np.isfinite(dual_bound):
        result_dict["objective_upper_bound"] = float(-dual_bound)
    gap = getattr(result, "mip_gap", None)
    if gap is not None and np.isfinite(gap):
        result_dict["mip_gap"] = float(gap)
    if result.x is not None:
        prices = result.x[:price_n].reshape(dimensions, items)
        allowed = np.all(incidence @ prices.T <= 1 + 1e-7, axis=1)
        valid = not np.any(allowed & ~safe) and np.all(allowed[history_local])
        valid &= (not require_new or bool(np.any(allowed & new)))
        if valid:
            result_dict["prices"] = prices
            result_dict["allowed"] = allowed
            result_dict["objective_lower_bound"] = float(
                np.sum(allowed) + (count + 1) * np.sum(allowed & new)
                + source_weight * sum(bool(np.any(allowed & mask)) for mask in legacy_masks)
            )
        else:
            result_dict["incumbent_rejected"] = "enumerated safety/history/new-item verification failed"
    return result_dict


def _safe_fallback_prices(previous: np.ndarray, new_slot: int) -> np.ndarray:
    result = previous.copy()
    result[:, 3 * new_slot + 2] = 2
    return result


def _two_trade_certificate(configurations: np.ndarray, incidence: np.ndarray,
                           safe: np.ndarray, new: np.ndarray,
                           history_local: np.ndarray) -> dict | None:
    """Exact combinatorial certificate excluding *every* safe new candidate.

    For each candidate p and protected h, swapping a coordinate produces two
    unsafe configurations q,r with a(p)+a(h)=a(q)+a(r). No real additive
    prices (even signed) can admit both p,h and exclude both q,r.
    """
    candidates = np.flatnonzero(safe & new)
    if not len(candidates):
        return None
    weights = 3 ** np.arange(5, -1, -1)
    global_ids = configurations @ weights
    local_lookup = np.full(729, -1, dtype=int)
    local_lookup[global_ids] = np.arange(len(configurations))
    covered: dict[int, list[int]] = {}
    for slot in range(6):
        delta = configurations[history_local, slot][None, :] - configurations[candidates, slot][:, None]
        qids = local_lookup[global_ids[candidates, None] + delta * weights[slot]]
        rids = local_lookup[global_ids[history_local][None, :] - delta * weights[slot]]
        if np.any(qids < 0) or np.any(rids < 0):
            raise AssertionError("coordinate swap escaped the visible product domain")
        obstruction = (~safe[qids]) & (~safe[rids])
        for candidate_i in np.flatnonzero(np.any(obstruction, axis=1)):
            candidate = int(candidates[candidate_i])
            if candidate in covered:
                continue
            history_i = int(np.flatnonzero(obstruction[candidate_i])[0])
            historical = int(history_local[history_i])
            qid, rid = int(qids[candidate_i, history_i]), int(rids[candidate_i, history_i])
            if not np.array_equal(incidence[candidate] + incidence[historical], incidence[qid] + incidence[rid]):
                raise AssertionError("invalid two-trade incidence identity")
            covered[candidate] = [candidate, historical, qid, rid]
    if len(covered) != len(candidates):
        return None
    witnesses = [covered[int(candidate)] for candidate in candidates]
    return {"kind": "exact_two_trade_cover", "new_candidates_covered": len(witnesses),
            "witnesses_local_ids": witnesses,
            "claim": "no scalar additive rule can satisfy P, registered H, and admit any current-new configuration"}


def _item_contribution(domain: Domain, values: np.ndarray, allowed_ids: np.ndarray,
                       slot: int) -> tuple[float, float | None]:
    """Best positive local effect and reoptimized loss after source removal."""
    configurations = domain.configurations
    source_mask = configurations[allowed_ids, slot] == 2
    source_ids = allowed_ids[source_mask]
    admitted = set(int(i) for i in allowed_ids)
    contribution = 0.0
    for identifier in source_ids:
        candidate = configurations[identifier].copy()
        replacements = []
        for old_choice in (0, 1):
            candidate[slot] = old_choice
            replacement_id = int(np.dot(candidate, 3 ** np.arange(5, -1, -1)))
            if replacement_id in admitted:
                replacements.append(replacement_id)
        if replacements:
            contribution = max(contribution, float(np.max(
                (values[identifier] - values[replacements].max(axis=0)) / domain.scale)))
    alternative_ids = allowed_ids[~source_mask]
    removal_loss = (float(np.max((values[allowed_ids].max(axis=0) - values[alternative_ids].max(axis=0))
                                 / domain.scale)) if len(alternative_ids) else None)
    return contribution, removal_loss


def _evaluate(domain: Domain, round_number: int, method: str, visible: np.ndarray,
              allowed_ids: np.ndarray, history: set[int], archive: set[int],
              all_history: set[int], solver_status: str) -> tuple[dict, list[dict]]:
    values = domain.response.max(axis=1)
    behavior = values / domain.scale
    configurations = domain.configurations
    current_slot = domain.order[round_number - 1]
    old_mask = configurations[allowed_ids, current_slot] != 2
    new_mask = ~old_mask
    rows: list[dict] = []
    base = {
        "scope": SCOPE, "seed": domain.seed, "pool_seed": domain.pool_seed,
        "variant": domain.variant, "method": method, "round": round_number,
        "K_bound": PROTOCOL["K_bound"], "solver_status": solver_status,
        "visible_configurations": len(visible), "allowed_configurations": len(allowed_ids),
        "new_slot": current_slot, "proposed_items": 1, "raw_unit": "abstract_response",
    }
    if not len(allowed_ids):
        base.update(status="optimizer_failure", power_ratio=None, power_cap_ratio=None, max_excess=None,
                    N=0.0, new_item_fraction=0.0, D=0.0, legacy_fraction=0.0,
                    legacy_worst=0.0, H=0.0, H_all=0.0, K=None, floor=0.0,
                    failure_reasons=["empty_admitted_set"])
        return base, rows
    allowed_values = values[allowed_ids]
    best = allowed_values.max(axis=0)
    ratio = float(np.max(domain.response[allowed_ids] / domain.cap[None, None, :]))
    excess = float(np.max(best - domain.cap))
    close = allowed_values >= best - PROTOCOL["epsilon_new"] * domain.scale - 1e-12
    legacy_close = allowed_values >= best - PROTOCOL["epsilon_legacy"] * domain.scale - 1e-12
    new_coverage = np.any(close[new_mask], axis=0) if np.any(new_mask) else np.zeros(8, dtype=bool)
    N = float(new_coverage.mean())
    old_ids = allowed_ids[old_mask]
    new_ids = allowed_ids[new_mask]
    old_distances = _min_distances(behavior[new_ids], behavior[old_ids])
    archive_distances = _min_distances(behavior[new_ids], behavior[sorted(archive)])
    novel = ((old_distances >= PROTOCOL["delta_behavior"] - 1e-12)
             & (archive_distances >= PROTOCOL["delta_behavior"] - 1e-12))
    novelty_coverage = np.any(close[new_mask][novel], axis=0) if np.any(novel) else np.zeros(8, dtype=bool)
    D = float(novelty_coverage.mean())
    new_contribution, new_removal_loss = _item_contribution(domain, values, allowed_ids, current_slot)
    rows.append({**{k: base[k] for k in ("scope", "seed", "pool_seed", "variant", "method", "round")},
                 "source": f"release_{round_number}", "kind": "current_new", "task_weight": N,
                 "useful": N >= PROTOCOL["minimum_task_weight"],
                 "novel_task_weight": D,
                 "best_old_counterfactual_distance": float(old_distances.max()) if len(old_distances) else None,
                 "best_archive_distance": float(archive_distances.max()) if len(archive_distances) else None,
                 "counterfactual_rule": "same_current_rule", "effect_contribution": new_contribution,
                 "removal_loss": new_removal_loss})
    legacy_weights = []
    sources = [("initial", None)] + [(f"release_{r + 1}", slot) for r, slot in enumerate(domain.order[:round_number - 1])]
    for source, slot in sources:
        has_source = np.any(configurations[allowed_ids] < 2, axis=1) if slot is None else configurations[allowed_ids, slot] == 2
        relevance = float(np.any(legacy_close[has_source], axis=0).mean()) if np.any(has_source) else 0.0
        legacy_weights.append(relevance)
        if slot is None:
            alternatives = ~has_source
            contribution = None  # initial is a multi-item source, not an invented single effect.
        else:
            alternatives = ~has_source
            contribution, _ = _item_contribution(domain, values, allowed_ids, slot)
        removal_loss = float(np.max((best - allowed_values[alternatives].max(axis=0)) / domain.scale)) if np.any(alternatives) else None
        rows.append({**{k: base[k] for k in ("scope", "seed", "pool_seed", "variant", "method", "round")},
                     "source": source, "kind": "legacy", "task_weight": relevance,
                     "useful": relevance >= PROTOCOL["minimum_task_weight"],
                     "novel_task_weight": None, "best_old_counterfactual_distance": None,
                     "best_archive_distance": None, "counterfactual_rule": "same_current_rule",
                     "effect_contribution": contribution, "removal_loss": removal_loss})
    legacy_fraction = float(np.mean(np.asarray(legacy_weights) >= PROTOCOL["minimum_task_weight"]))
    legacy_worst = float(min(legacy_weights))
    allowed_set = set(int(i) for i in allowed_ids)
    H = len(history & allowed_set) / len(history) if history else 1.0
    H_all = len(all_history & allowed_set) / len(all_history) if all_history else 1.0
    K, portfolio_local = minimum_portfolio(allowed_values, domain.scale,
                                          PROTOCOL["epsilon_portfolio"], PROTOCOL["alpha_portfolio"])
    floor_ratio = float(np.min(best / domain.scale))
    checks = {
        "P": ratio <= 1 + 1e-10,
        "N": N >= PROTOCOL["minimum_task_weight"],
        "D": D >= PROTOCOL["minimum_task_weight"],
        "L": legacy_fraction == 1,
        "H": H == 1,
        "C": K is not None and K <= PROTOCOL["K_bound"],
        "floor": floor_ratio >= 1 - PROTOCOL["epsilon_floor"] - 1e-10,
    }
    failures = [key for key, value in checks.items() if not value]
    base.update(
        status="pass" if not failures else "violation", power_ratio=float(np.max(best / domain.scale)),
        power_cap_ratio=ratio,
        max_excess=max(0.0, excess), N=N,
        new_item_fraction=float(N >= PROTOCOL["minimum_task_weight"]), D=D,
        legacy_fraction=legacy_fraction, legacy_worst=legacy_worst,
        H=H, H_all=H_all, registered_history_count=len(history),
        all_history_count=len(all_history), K=K, K_status="exact_set_cover_dp",
        portfolio=[int(allowed_ids[i]) for i in portfolio_local], floor=floor_ratio,
        failure_reasons=failures, power_by_task=best.tolist(),
        cap_by_task=domain.cap.tolist(), source_count=len(sources),
        old_counterfactual_configurations=len(old_ids),
        cumulative_archive_configurations=len(archive),
        joint_oracle=False,
        interpretation="upper_envelope_diagnostic_not_joint_oracle" if method == "safe_set_envelope" else "achieved_online_rule",
    )
    return base, rows


def _interaction_ablations(domain: Domain) -> list[dict]:
    """Fixed-configuration and reoptimized controls for every hazardous term."""
    records = []
    values = domain.response.max(axis=1)
    initial_extension = domain.incidence @ domain.initial_prices <= 1 + 1e-10
    structured = np.ones(729, dtype=bool)
    for hazard in domain.hazards:
        structured &= ~_edge_mask(domain.configurations, hazard)
    for hazard in domain.hazards:
        mask = _edge_mask(domain.configurations, hazard)
        eligible = np.flatnonzero(mask)
        representative = int(eligible[np.argmax(values[eligible].max(axis=1))])
        counterfactual = domain.response.copy()
        counterfactual[mask] -= hazard.coefficient
        records.append({
            "scope": SCOPE, "seed": domain.seed, "pool_seed": domain.pool_seed,
            "variant": domain.variant, "ablation": f"remove_effect_{hazard.label}",
            "interaction_order": len(hazard.items), "configuration": representative,
            "fixed_before": float(domain.response[representative].max()),
            "fixed_after": float(counterfactual[representative].max()),
            "reoptimized_before": float(domain.response[initial_extension].max()),
            "reoptimized_after": float(counterfactual[initial_extension].max()),
            "physics_changed": True, "diagnostic_only": True,
        })
        without_rule = np.ones(729, dtype=bool)
        for other in domain.hazards:
            if other.label != hazard.label:
                without_rule &= ~_edge_mask(domain.configurations, other)
        records.append({
            "scope": SCOPE, "seed": domain.seed, "pool_seed": domain.pool_seed,
            "variant": domain.variant, "ablation": f"remove_rule_{hazard.label}",
            "interaction_order": len(hazard.items), "configuration": representative,
            "fixed_before": None, "fixed_after": None,
            "reoptimized_before": float(domain.response[structured].max()),
            "reoptimized_after": float(domain.response[without_rule].max()),
            "physics_changed": False, "diagnostic_only": True,
        })
    return records


def run_instance(seed: int, variant: str = "pair", horizon: int = 6,
                 checkpoint_callback: Callable[[dict], None] | None = None) -> dict:
    """Return JSON-serializable exact finite-domain results and audit metadata.

    The optional callback receives a completed round checkpoint. Restoring a
    mid-instance solver/history state is deliberately not claimed: callers
    may resume at completed-instance boundaries or deterministically replay.
    """
    if not 1 <= horizon <= 6:
        raise ValueError("horizon must be between 1 and 6")
    started = time.perf_counter()
    domain = build_domain(seed, variant)
    task_values = domain.response.max(axis=1)
    initial_history = _register(domain.initial_ids, task_values)
    histories = {method: set(initial_history) for method in METHODS}
    histories["compatible_scalar_full_history"] = set(int(i) for i in domain.initial_ids)
    archives = {method: set(int(i) for i in domain.initial_ids) for method in METHODS}
    all_histories = {method: set(int(i) for i in domain.initial_ids) for method in METHODS}
    scalar_prices = domain.initial_prices[None, :].copy()
    full_history_prices = scalar_prices.copy()
    two_prices = np.vstack([domain.initial_prices, np.zeros(18)])
    frozen_prices = domain.initial_prices.copy()
    for slot in range(6):
        frozen_prices[3 * slot + 2] = np.mean(frozen_prices[3 * slot:3 * slot + 2])
    result: dict = {key: [] for key in ("rounds", "feasibility", "rules", "relevance", "ablations", "costs")}
    for round_number in range(1, horizon + 1):
        visible = domain.visible_ids(round_number)
        current_configurations = domain.configurations[visible]
        incidence = domain.incidence[visible]
        safe = np.all(domain.response[visible] <= domain.cap[None, None, :] + 1e-12, axis=(1, 2))
        current_slot = domain.order[round_number - 1]
        new = current_configurations[:, current_slot] == 2
        available_items = {(slot, choice) for slot in range(6) for choice in range(3)
                           if choice < 2 or slot in domain.order[:round_number]}
        visible_hazards = [edge for edge in domain.hazards if all(item in available_items for item in edge.items)]
        local_by_global = {int(global_i): i for i, global_i in enumerate(visible)}
        for method in METHODS:
            method_started = time.perf_counter()
            solver_status = "not_applicable_exact_enumeration"
            rules: dict = {}
            solver_seconds = 0.0
            if method == "unrestricted_extension":
                prices = domain.initial_prices[None, :]
                allowed = np.all(incidence @ prices.T <= 1 + 1e-10, axis=1)
                rules = {"type": "initial_rule_only", "dimensions": 1, "prices": prices.tolist()}
            elif method == "frozen_scalar":
                prices = frozen_prices[None, :]
                allowed = np.all(incidence @ prices.T <= 1 + 1e-10, axis=1)
                rules = {"type": "frozen_nonnegative_scalar", "dimensions": 1, "prices": prices.tolist()}
            elif method in ("compatible_scalar", "compatible_scalar_full_history", "generic_two_budget"):
                dimensions = 2 if method == "generic_two_budget" else 1
                history_local = np.asarray([local_by_global[i] for i in sorted(histories[method])], dtype=int)
                time_limit = PROTOCOL["solver_time_limit_seconds_scalar"] if dimensions == 1 else PROTOCOL["solver_time_limit_seconds_two_budget"]
                safe_envelope = task_values[visible[safe]].max(axis=0)
                competitive = np.any(task_values[visible] >= safe_envelope - PROTOCOL["epsilon_legacy"] * domain.scale - 1e-12, axis=1)
                legacy_masks = [(current_configurations[:, slot] == 2) & competitive
                                for slot in domain.order[:round_number - 1]]
                certificate_started = time.perf_counter()
                certificate = _two_trade_certificate(current_configurations, incidence, safe, new, history_local) if dimensions == 1 else None
                if certificate is not None:
                    solved = {"solver_status": "infeasible_exact_trade_certificate",
                              "solver_message": "every safe new candidate has a verified two-trade with a protected configuration",
                              "solver_seconds": time.perf_counter() - certificate_started,
                              "require_new": True, "dimensions": 1,
                              "objective": "legacy_source_coverage_then_new_admitted_count_then_total_safe_admitted_count",
                              "objective_lower_bound": None, "objective_upper_bound": None,
                              "mip_gap": None, "prices": None, "allowed": None,
                              "certificate": certificate}
                else:
                    solved = _solve_budgets(incidence, safe, new, history_local, dimensions, time_limit,
                                            legacy_masks=legacy_masks)
                solver_seconds = solved["solver_seconds"]
                solver_status = solved["solver_status"]
                prior_prices = (full_history_prices if method == "compatible_scalar_full_history"
                                else scalar_prices if dimensions == 1 else two_prices)
                fallback_used = solved["allowed"] is None
                if fallback_used:
                    prices = _safe_fallback_prices(prior_prices, current_slot)
                    allowed = np.all(incidence @ prices.T <= 1 + 1e-7, axis=1)
                    # This constructive fallback preserves all previously
                    # admitted configurations and rejects the current item.
                    if np.any(allowed & ~safe) or not np.all(allowed[history_local]):
                        raise RuntimeError("safe historical fallback verification failed")
                else:
                    prices, allowed = solved["prices"], solved["allowed"]
                if method == "compatible_scalar_full_history":
                    full_history_prices = prices
                elif dimensions == 1:
                    scalar_prices = prices
                else:
                    two_prices = prices
                feasibility = {k: v for k, v in solved.items() if k not in ("prices", "allowed")}
                feasibility.update(scope=SCOPE, seed=seed, pool_seed=domain.pool_seed,
                                   variant=variant, method=method, round=round_number,
                                   fallback_used=fallback_used,
                                   claim="P + registered H + admission of at least one current-new configuration, with numerical margin; not full joint feasibility",
                                   achieved_safe=True, full_joint_oracle=False,
                                   unsafe_configurations=int(np.sum(~safe)))
                result["feasibility"].append(feasibility)
                rules = {"type": "nonnegative_additive_budgets", "dimensions": dimensions,
                         "prices": prices.tolist(), "fallback_used": fallback_used,
                         "solver_status": solver_status, "margin": PROTOCOL["solver_separation_margin"],
                         "price_l1_change": float(np.abs(prices - prior_prices).sum())}
            elif method in ("structured_hyperedges", "generic_matched_budget"):
                allowed = np.ones(len(visible), dtype=bool)
                for hazard in visible_hazards:
                    allowed &= ~_edge_mask(current_configurations, hazard)
                rules = {"type": "forbidden_effect_conjunctions", "dimensions": len(visible_hazards),
                         "max_order": max(len(hazard.items) for hazard in visible_hazards),
                         "hazards": [{"items": [list(item) for item in hazard.items], "label": hazard.label}
                                     for hazard in visible_hazards],
                         "information": "currently revealed effect interaction annotations plus exact table verification"}
                if method == "generic_matched_budget":
                    prices = np.zeros((len(visible_hazards), 18))
                    for row_i, hazard in enumerate(visible_hazards):
                        for slot, choice in hazard.items:
                            prices[row_i, 3 * slot + choice] = 1 / (len(hazard.items) - 1)
                    encoded_allowed = np.all(incidence @ prices.T <= 1 + 1e-10, axis=1)
                    if not np.array_equal(encoded_allowed, allowed) or not np.array_equal(allowed, safe):
                        raise AssertionError("matched generic budgets failed exact safe-envelope equality")
                    allowed = encoded_allowed
                    solver_status = "optimal_safe_count_bound_attained"
                    rules = {"type": "generic_additive_budgets_with_structural_initialization",
                             "dimensions": len(visible_hazards), "prices": prices.tolist(),
                             "solver_status": solver_status,
                             "information": "same visible hyperedge information as structured; supplied feasible initialization attains all safe configurations",
                             "joint_oracle": False}
                    result["feasibility"].append({
                        "scope": SCOPE, "seed": seed, "pool_seed": domain.pool_seed,
                        "variant": variant, "method": method, "round": round_number,
                        "dimensions": len(visible_hazards), "solver_status": solver_status,
                        "objective": "total_safe_configurations", "objective_lower_bound": int(safe.sum()),
                        "objective_upper_bound": int(safe.sum()), "mip_gap": 0.0,
                        "solver_seconds": 0.0, "fallback_used": False,
                        "achieved_safe": True, "full_joint_oracle": False,
                        "claim": "explicit additive representation attains all-safe cardinality upper bound; joint metrics evaluated separately"})
            else:
                allowed = safe
                rules = {"type": "arbitrary_safe_set_upper_envelope", "dimensions": None,
                         "exceptions": int(np.sum(~safe)), "joint_oracle": False}
            allowed_ids = visible[allowed]
            round_result, relevance = _evaluate(domain, round_number, method, visible, allowed_ids,
                                               histories[method], archives[method], all_histories[method],
                                               solver_status)
            round_result["rule_dimensions"] = rules.get("dimensions")
            round_result["rule_exceptions"] = rules.get("exceptions", 0)
            round_result["admitted_new_configurations"] = int(np.sum(allowed & new))
            result["rounds"].append(round_result)
            result["relevance"].extend(relevance)
            result["rules"].append({"scope": SCOPE, "seed": seed, "pool_seed": domain.pool_seed,
                                    "variant": variant, "method": method, "round": round_number,
                                    "visible_items": [list(item) for item in sorted(available_items)],
                                    "registered_before": sorted(histories[method]),
                                    "admitted_ids": allowed_ids.tolist(), "rule": rules})
            if method == "compatible_scalar_full_history":
                histories[method].update(int(i) for i in allowed_ids)
            else:
                histories[method] |= _register(allowed_ids, task_values)
            archives[method].update(int(i) for i in allowed_ids)
            all_histories[method].update(int(i) for i in allowed_ids)
            result["costs"].append({"scope": SCOPE, "seed": seed, "pool_seed": domain.pool_seed,
                                    "variant": variant, "method": method, "round": round_number,
                                    "physical_simulations": 0, "stochastic_samples": 0,
                                    "response_cells_read": int(len(visible) * 8 * 3),
                                    "solver_seconds": solver_seconds,
                                    "wall_seconds": time.perf_counter() - method_started,
                                    "cost_kind": "deterministic_abstract_table_and_optimization"})
        if checkpoint_callback is not None:
            checkpoint_callback({"scope": SCOPE, "seed": seed, "variant": variant,
                                 "completed_round": round_number,
                                 "rounds": [row for row in result["rounds"] if row["round"] == round_number],
                                 "resume_capability": "completed_instance_or_deterministic_replay"})
    result["ablations"] = _interaction_ablations(domain)
    table_hash = hashlib.sha256(domain.response.tobytes()).hexdigest()
    result["evidence"] = {
        "scope": SCOPE, "native_engine": False, "stochastic_simulator": False,
        "seed": int(seed), "pool_seed": domain.pool_seed, "variant": variant,
        "protocol": PROTOCOL.copy(), "reveal_order": list(domain.order[:horizon]),
        "full_reveal_order": list(domain.order), "table_sha256": table_hash,
        "initial_admitted_configurations": domain.initial_ids.tolist(),
        "initial_registered_ids": sorted(initial_history),
        "initial_prices": domain.initial_prices.tolist(), "initial_scale": domain.scale.tolist(),
        "cap": domain.cap.tolist(), "configuration_encoding": "base-3 lexicographic product; id=sum(choice_s*3**(5-s))",
        "task_weights": [0.125] * 8, "hazards": [
            {"items": [list(item) for item in hazard.items], "coefficient": hazard.coefficient,
             "label": hazard.label} for hazard in domain.hazards],
        "all_current_old_counterfactuals_enumerated": True,
        "K_exact": True, "P_exact_for_declared_finite_domain": True,
        "capacity_T_star_solved": False, "physical_simulations": 0,
        "initial_anchor_scope": "initial admission rule, not unrestricted initial Cartesian product",
        "full_history_supplement": "compatible_scalar_full_history protects every previously admitted configuration including all initial admitted configurations; H_all also reports retention for every method",
        "runtime_seconds": time.perf_counter() - started,
    }
    # Fail loudly if downstream checkpoint/package serialization would fail.
    json.dumps(result, allow_nan=False)
    return result
