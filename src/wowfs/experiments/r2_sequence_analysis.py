"""Evaluate the frozen finite native catalogue without future-response decisions.

All numerical performance/behavior conclusions are Monte Carlo mean diagnostics.
No abstract response generator or substitute combat is used here.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import time

import numpy as np
from scipy.optimize import linprog
from scipy.spatial import cKDTree
from scipy.stats import t
import yaml

from wowfs.paths import atomic_json, setup_paths

METHODS = ("no_control", "scalar_reprice", "exceptions", "envelope_reference",
           "semantic_2", "semantic_4", "semantic_8", "generic_2", "generic_4", "generic_8")
REJECTION_EPSILON = 1e-6
ADMISSION_TOLERANCE = 1e-8


def behavior_vector(row, duration):
    """Four disjoint native action shares, residual share, rage flow and waste."""
    shares = np.zeros(5)
    for key, action in row["actions"].items():
        match = re.search(r"(?:^|/)spellId:(\d+)(?:/|$)", key)
        spell = int(match.group(1)) if match else None
        if "otherId:OtherActionAttack" in key:
            group = 0
        elif spell == 20662:
            group = 1
        elif spell in (1680, 20569):
            group = 2
        elif spell == 23894:
            group = 3
        else:
            group = 4
        shares[group] += action["fraction"]
    gain = waste = 0.0
    for resource in row["resources"]:
        if resource["type"] not in ("ResourceTypeRage", 3):
            continue
        if resource["gain"] > 0:
            gain += resource["gain"]
            waste += max(0.0, resource["gain"] - resource["actualGain"])
    return np.r_[shares, gain / duration / 20, waste / gain if gain else 0]


def portfolio_cover(gear_values, optimum, scale, epsilon=.05, weights=None, coverage=.95):
    """Exact equipment set cover; strategies may differ between tasks."""
    values = np.asarray(gear_values, float)
    weights = np.ones(len(optimum)) / len(optimum) if weights is None else np.asarray(weights)
    close = values >= np.asarray(optimum) - epsilon * np.asarray(scale) - 1e-10
    masks = [sum((1 << k) for k, yes in enumerate(row) if yes) for row in close]
    reachable = {0: ()}
    for index, mask in enumerate(masks):
        for before, selected in list(reachable.items()):
            after = before | mask
            candidate = selected + (index,)
            if after not in reachable or len(candidate) < len(reachable[after]):
                reachable[after] = candidate
    weight = lambda mask: sum(w for k, w in enumerate(weights) if mask & (1 << k))
    valid = [v for mask, v in reachable.items() if weight(mask) >= coverage - 1e-12]
    best = min(valid, key=lambda v: (len(v), v)) if valid else None
    return {"K": len(best) if best is not None else None,
            "indices": list(best) if best is not None else [],
            "maximum_coverage": max(map(weight, reachable))}


def nearest_distances(candidates, alternatives):
    candidates, alternatives = np.asarray(candidates), np.asarray(alternatives)
    if len(candidates) == 0:
        return np.empty(0)
    if len(alternatives) == 0:
        return np.full(len(candidates), np.inf)
    return cKDTree(alternatives).query(candidates, k=1, p=np.inf)[0]


def scalar_reprice(incidence, unsafe, history, candidates, previous):
    """Current-only LP with strict rejection margin and a protected history."""
    incidence = np.asarray(incidence, float)
    unsafe = np.asarray(unsafe, bool)
    history = np.asarray(history, bool)
    previous = np.asarray(previous, float)
    if not np.any(unsafe):
        prices = np.zeros_like(previous)
        return prices, {"solver_status": "optimal_all_current_safe", "margin": 1.0,
                        "attempts": 0, "required_new_witness": candidates[0] if len(candidates) else None}
    if np.any(unsafe & history):
        return previous.copy(), {"solver_status": "infeasible_history_contains_unsafe",
                                 "margin": None, "attempts": 0, "required_new_witness": None}
    p = incidence.shape[1]
    base_a = np.vstack([np.c_[incidence[history], np.zeros(history.sum())],
                        np.c_[-incidence[unsafe], np.ones(unsafe.sum())]])
    base_b = np.r_[np.ones(history.sum()), -np.ones(unsafe.sum())]
    objective = np.r_[np.zeros(p), -1.0]
    attempts = 0

    def solve(witness=None):
        nonlocal attempts
        attempts += 1
        a, b = base_a, base_b
        if witness is not None:
            a = np.vstack([a, np.r_[incidence[witness], 0]])
            b = np.r_[b, 1.0]
        return linprog(objective, A_ub=a, b_ub=b, bounds=[(0, 100)] * p + [(0, 1)],
                       method="highs", options={"time_limit": 5.0,
                                                 "primal_feasibility_tolerance": 1e-8})

    base = solve()
    if base.status != 0 or base.x[-1] < REJECTION_EPSILON:
        status = ("infeasible_lp" if base.status == 2 else "no_positive_rejection_margin"
                  if base.status == 0 else f"unresolved_solver_{base.status}")
        return previous.copy(), {"solver_status": status,
                                 "margin": float(base.x[-1]) if base.x is not None else None,
                                 "attempts": attempts, "required_new_witness": None}
    unresolved = []
    for witness in candidates:
        solved = solve(int(witness))
        if solved.status == 0 and solved.x[-1] >= REJECTION_EPSILON:
            return solved.x[:-1], {"solver_status": "optimal_margin_with_new_witness",
                                  "margin": float(solved.x[-1]), "attempts": attempts,
                                  "required_new_witness": int(witness),
                                  "unresolved_witness_attempts": unresolved}
        if solved.status not in (0, 2):
            unresolved.append({"witness": int(witness), "status": solved.status})
    return base.x[:-1], {"solver_status": "optimal_margin_without_new_witness",
                        "margin": float(base.x[-1]), "attempts": attempts,
                        "required_new_witness": None, "unresolved_witness_attempts": unresolved}


def load_context(rows, gear_ids, tasks, strategies, race, sample_size):
    shape = (len(gear_ids), len(strategies), len(tasks))
    means, errors = np.full(shape, np.nan), np.full(shape, np.nan)
    behavior = np.full((*shape, 7), np.nan)
    gmap, pmap, tmap = ({v: i for i, v in enumerate(values)}
                        for values in (gear_ids, strategies, [x["id"] for x in tasks]))
    seen = set()
    for row in rows:
        if row is None:
            raise ValueError("Missing native row cannot count as a zero outcome")
        if row["race"] != race:
            continue
        index = (gmap[row["gear_id"]], pmap[row["strategy"]], tmap[row["task"]])
        if index in seen:
            raise ValueError("Duplicate native gear/policy/task cell")
        seen.add(index)
        samples = np.asarray(row["dps_samples"], float)
        if len(samples) != sample_size or not np.isfinite(samples).all():
            raise ValueError("Invalid native sample count or nonfinite performance")
        means[index], errors[index] = samples.mean(), samples.std(ddof=1) / np.sqrt(sample_size)
        behavior[index] = behavior_vector(row, tasks[index[2]]["duration_seconds"])
    if not np.isfinite(means).all() or not np.isfinite(behavior).all():
        raise ValueError("Native response table incomplete")
    quantile = t.ppf(1 - .05 / (2 * np.prod(shape)), sample_size - 1)
    return means, behavior, means - quantile * errors, means + quantile * errors


def write_csv(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(k for row in records for k in row))
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in records:
            writer.writerow({k: json.dumps(v, separators=(",", ":"), allow_nan=False)
                             if isinstance(v, (list, dict, tuple)) else v for k, v in row.items()})


def evaluate_sequence(freeze, sequence, race, method, headroom, data, gear_ids, item_ids,
                      incidence_all, semantic_allow, tasks, strategies):
    means, behavior, lower, upper = data
    rules, rewards, rounds = [], [], []
    decision = freeze["decisions"]
    weights = np.asarray(decision["task_weights"])
    epsilon = decision["near_optimal_tolerance"]
    threshold = decision["behavior"]["resolution"]
    gmap = {key: i for i, key in enumerate(gear_ids)}
    initial = np.array([gmap[k] for k in freeze["initial_gear_ids"]])
    scale = means[initial].max(axis=(0, 1))
    if np.any(scale <= 0):
        raise ValueError("Initial normalizing scale must be positive")
    initial_low, initial_high = lower[initial].max(axis=(0, 1)), upper[initial].max(axis=(0, 1))
    cap = (1 + headroom) * scale
    history = set(initial.tolist())
    archive = [set((g, p) for g in initial for p in range(len(strategies))) for _ in tasks]
    legacy = []
    prices = np.zeros(len(item_ids))
    accumulated_families = 0
    prefix, prefix_open = 0, True
    q = int(method.split("_")[-1]) if method.startswith(("semantic_", "generic_")) else None
    membership = freeze["memberships"][sequence["id"]]
    faction = {"RaceHuman": "Alliance", "RaceOrc": "Horde"}[race]
    initial_item_set = set(i for k in freeze["initial_gear_ids"] for i in freeze["gears"][k].values())
    item_index = {item: i for i, item in enumerate(item_ids)}
    previous_exceptions = set()
    previous_catalogue_size = len(initial)
    common = {"scope": "native_finite_catalogue_empirical", "sequence": sequence["id"],
              "generator": sequence["generator"], "race": race, "faction": faction,
              "class": "Warrior", "method": method, "headroom": headroom}
    for arrival in sequence["arrivals"]:
        number, item = arrival["round"], arrival["item_id"]
        current = np.array(sorted(gmap[k] for k, first in membership.items() if first <= number))
        local_incidence = incidence_all[current]
        new = local_incidence[:, item_index[item]] > 0
        unsafe = np.any(means[current] > cap[None, None, :] + 1e-10, axis=(1, 2))
        solver = {"solver_status": "not_applicable", "attempts": 0}
        before_prices = prices.copy()
        if method == "no_control":
            allowed_mask = np.ones(len(current), bool)
        elif q is not None:
            allowed_mask = semantic_allow[q][current]
        elif method in ("exceptions", "envelope_reference"):
            allowed_mask = ~unsafe
        elif method == "scalar_reprice":
            safe_optimum = means[current[~unsafe]].max(axis=(0, 1))
            competitive = np.any(means[current].max(axis=1) >= safe_optimum - epsilon * scale, axis=1)
            candidates = np.flatnonzero(new & ~unsafe & competitive)
            score = (means[current].max(axis=1) / scale).max(axis=1)
            candidates = sorted(candidates.tolist(), key=lambda j: (-score[j], gear_ids[current[j]]))
            visible_columns = np.flatnonzero(np.any(local_incidence > 0, axis=0))
            solved_prices, solver = scalar_reprice(local_incidence[:, visible_columns], unsafe,
                                                  np.array([int(g) in history for g in current]),
                                                  candidates, prices[visible_columns])
            prices[visible_columns] = solved_prices
            allowed_mask = local_incidence @ prices <= 1 + ADMISSION_TOLERANCE
        else:
            raise ValueError(method)
        allowed = current[allowed_mask]
        if len(allowed) == 0:
            raise ValueError(f"Empty allowed set in {common}, round {number}; preserve as failure before reporting")
        allowed_items = incidence_all[allowed]
        new_allowed_mask = allowed_items[:, item_index[item]] > 0
        new_gears = allowed[new_allowed_mask]
        old_gears = allowed[~new_allowed_mask]
        optimum = means[allowed].max(axis=(0, 1))
        gear_best = means[allowed].max(axis=1)
        close = means[allowed] >= optimum[None, None, :] - epsilon * scale[None, None, :] - 1e-10
        n_tasks = np.any(close[new_allowed_mask], axis=(0, 1)) if len(new_gears) else np.zeros(len(tasks), bool)
        N = float(weights @ n_tasks)
        d_tasks = np.zeros(len(tasks), bool)
        behavior_distances, archive_distances = [], []
        added_families = 0
        archive_additions = []
        for k in range(len(tasks)):
            positions = np.argwhere(close[new_allowed_mask, :, k])
            candidate_pairs = [(int(new_gears[g]), int(p)) for g, p in positions]
            archive_additions.append(candidate_pairs)
            if not candidate_pairs:
                continue
            candidates_b = np.array([behavior[g, p, k] for g, p in candidate_pairs])
            old_b = behavior[old_gears, :, k].reshape(-1, 7)
            archived_b = np.array([behavior[g, p, k] for g, p in sorted(archive[k])])
            distances_old = nearest_distances(candidates_b, old_b)
            distances_archive = nearest_distances(candidates_b, archived_b)
            behavior_distances.extend(distances_old.tolist())
            archive_distances.extend(distances_archive.tolist())
            novel = (distances_old >= threshold - 1e-10) & (distances_archive >= threshold - 1e-10)
            d_tasks[k] = bool(np.any(novel))
            within_arrival = []
            for candidate in candidates_b[novel]:
                if not within_arrival or np.min(np.max(np.abs(np.asarray(within_arrival) - candidate), axis=1)) >= threshold - 1e-10:
                    within_arrival.append(candidate)
            added_families += len(within_arrival)
        D = float(weights @ d_tasks)
        accumulated_families += added_families
        legacy_masses = []
        source_items = [(source, "legacy") for source in legacy] + [(item, "current_new")]
        if number == 20:
            source_items += [(source, "initial_item_final_round") for source in sorted(initial_item_set)]
        for source, kind in source_items:
            source_mask = allowed_items[:, item_index[source]] > 0
            source_close = close[source_mask]
            task_mass = float(weights @ np.any(source_close, axis=(0, 1))) if source_mask.any() else 0.0
            if kind == "legacy":
                legacy_masses.append(task_mass)
            remaining = allowed[~source_mask]
            losses = ((optimum - means[remaining].max(axis=(0, 1))) / scale).tolist() if len(remaining) else None
            bd = []
            if source_mask.any() and len(remaining):
                source_gears = allowed[source_mask]
                for k in range(len(tasks)):
                    gp = np.argwhere(close[source_mask, :, k])
                    candidates_b = np.array([behavior[source_gears[g], p, k] for g, p in gp])
                    if len(candidates_b):
                        bd.extend(nearest_distances(candidates_b, behavior[remaining, :, k].reshape(-1, 7)).tolist())
            rewards.append({**common, "round": number, "source_item": source, "source_kind": kind,
                            "competitive_task_mass": task_mass, "useful": task_mass >= decision["minimum_task_mass"],
                            "deletion_loss_by_task_normalized": losses,
                            "maximum_deletion_loss": max(losses) if losses else None,
                            "max_competitive_behavior_deletion_distance": max(bd) if bd else None,
                            "deletion_status": "finite_catalogue_reoptimized" if len(remaining) else "unfillable_catalogue",
                            "behavior_scope": "point-estimate mean profiles; all item-free listed policies; finite catalogue"})
        L = all(m >= decision["minimum_task_mass"] for m in legacy_masses)
        retained = len(history.intersection(allowed.tolist()))
        H = retained == len(history)
        cover = portfolio_cover(gear_best, optimum, scale, epsilon, weights, decision["portfolio_coverage"])
        initial_cover = portfolio_cover(means[initial].max(axis=1), optimum, scale, epsilon, weights,
                                        decision["portfolio_coverage"])
        P = bool(np.all(optimum <= cap + 1e-10))
        power_low = float(np.max(lower[allowed].max(axis=(0, 1)) - (1 + headroom) * initial_high))
        power_high = float(np.max(upper[allowed].max(axis=(0, 1)) - (1 + headroom) * initial_low))
        power_status = "supported_violation" if power_low > 0 else "supported_pass" if power_high <= 0 else "unresolved"
        checks = {"P": P, "N": N >= decision["minimum_task_mass"], "D": D >= decision["minimum_task_mass"],
                  "L": L, "H": H, "C": cover["K"] is not None and cover["K"] <= decision["maximum_portfolio_size"],
                  "floor": bool(np.all(optimum >= (1 - decision["initial_floor_tolerance"]) * scale - 1e-10))}
        passed = all(checks.values())
        if prefix_open and passed:
            prefix += 1
        else:
            prefix_open = False
        exception_ids = {gear_ids[g] for g in current[unsafe]} if method == "exceptions" else set()
        visible_items = sorted({i for g in current for i in freeze["gears"][gear_ids[g]].values()})
        descriptors = {str(i): freeze["design"]["item_descriptors"][str(i)]
                       for i in visible_items}
        descriptor_bytes = len(json.dumps(descriptors, sort_keys=True).encode())
        changes = (float(np.abs(prices - before_prices).sum()) if method == "scalar_reprice"
                   else len(exception_ids.symmetric_difference(previous_exceptions)) if method == "exceptions" else 0)
        feature_count = q if q else 1 if method == "scalar_reprice" else 0
        row = {**common, "round": number, "new_item": item,
               "status": "empirical_pass" if passed else "empirical_violation", **checks,
               "failure_reasons": [k for k, yes in checks.items() if not yes],
               "power_growth": float(np.max(optimum / scale - 1)), "power_by_task": optimum.tolist(),
               "initial_reference_by_task": scale.tolist(), "power_ci_status": power_status,
               "power_ci_excess_lower_dps": power_low, "power_ci_excess_upper_dps": power_high,
               "power_ci_scope": "approximate simultaneous means within race across all physical cells",
               "new_task_mass": N, "novel_task_mass": D, "new_useful_fraction": float(checks["N"]),
               "legacy_useful_fraction": float(np.mean(np.asarray(legacy_masses) >= decision["minimum_task_mass"])) if legacy_masses else None,
               "legacy_denominator": len(legacy_masses), "legacy_worst_task_mass": min(legacy_masses) if legacy_masses else None,
               "legacy_source_scope": "previously competitive released items; initial-item deletion separate",
               "history_total": len(history), "history_retained": retained,
               "K": cover["K"], "portfolio_gear_ids": [gear_ids[allowed[i]] for i in cover["indices"]],
               "initial_gear_K_current_optima": initial_cover["K"], "initial_gear_task_coverage": initial_cover["maximum_coverage"],
               "distinct_new_choices": accumulated_families, "new_behavior_task_families": added_families,
               "distinct_new_choices_unit": "task-conditioned greedy separated mean profiles",
               "max_old_behavior_distance": max(behavior_distances) if behavior_distances else None,
               "max_archive_behavior_distance": max(archive_distances) if archive_distances else None,
               "available_gears": len(current), "admitted_gears": len(allowed),
               "unsafe_admitted_gears": int(np.sum(unsafe & allowed_mask)), "rule_rows": feature_count,
               "exceptions": len(exception_ids), "metadata_items": len(visible_items), "metadata_bytes": descriptor_bytes,
               "mean_descriptor_bytes": descriptor_bytes / len(visible_items),
               "rule_parameter_change": changes, "solver_status": solver["solver_status"],
               "lp_attempts": solver.get("attempts", 0), "scalar_margin": solver.get("margin"),
               "scalar_unresolved_attempts": solver.get("unresolved_witness_attempts", []),
               "physical_current_cells_available": len(current) * len(tasks) * len(strategies),
               "marginal_shared_evaluation_cells": (len(current) - previous_catalogue_size) * len(tasks) * len(strategies),
               "marginal_shared_evaluation_fights": (len(current) - previous_catalogue_size) * len(tasks) * len(strategies) * decision["sample_size"],
               "query_cost_note": "evaluation cache shared across methods and overlapping sequences; never sum these as new engine calls",
               "response_cells_used_for_rule": len(current) * len(tasks) * len(strategies) if method in ("scalar_reprice", "exceptions", "envelope_reference") else 0,
               "physics_modified": False, "all_future_results_accessed_for_decision": False}
        rounds.append(row)
        rules.append({**common, "round": number, "q": feature_count, "exception_rows": len(exception_ids),
                      "rule_parameter_change": changes, "metadata_items": len(visible_items),
                      "metadata_bytes": descriptor_bytes, "admitted_gears": len(allowed),
                      "thresholds": freeze["thresholds"][:q] if q else None,
                      "prices": {str(item_ids[j]): float(p) for j, p in enumerate(prices) if p} if method == "scalar_reprice" else None,
                      "exceptions_gear_ids": sorted(exception_ids) if method == "exceptions" else None,
                      "admitted_gear_ids": [gear_ids[g] for g in allowed],
                      "solver": solver,
                      "generic_training_optimality": "185/185, identical feasible semantic initialization" if method.startswith("generic_") else None})
        # The registration rule is unchanged even after a previous joint failure.
        competitive_new = new_gears[np.any(close[new_allowed_mask], axis=(1, 2))]
        history.update(competitive_new.tolist())
        for k, pairs in enumerate(archive_additions):
            archive[k].update(pairs)
        if checks["N"] and item not in legacy:
            legacy.append(item)
        previous_exceptions = exception_ids
        previous_catalogue_size = len(current)
    last = rounds[-1]
    sequence_row = {**common, "rounds_completed": len(rounds), "S20": prefix, "Pass20": prefix == 20,
                    "max_power_growth": max(r["power_growth"] for r in rounds),
                    "new_useful_fraction": float(np.mean([r["new_useful_fraction"] for r in rounds])),
                    "legacy_useful_fraction": last["legacy_useful_fraction"],
                    "legacy_denominator": last["legacy_denominator"], "distinct_new_choices": accumulated_families,
                    "legacy_source_scope": last["legacy_source_scope"],
                    "distinct_new_choices_unit": last["distinct_new_choices_unit"],
                    "K20": last["K"], "rule_rows": last["rule_rows"], "exceptions": last["exceptions"],
                    "first_failure_reasons": rounds[prefix]["failure_reasons"] if prefix < 20 else [],
                    "initial_gear_K20": last["initial_gear_K_current_optima"],
                    "initial_gear_coverage20": last["initial_gear_task_coverage"],
                    "power_violating_rounds": sum(not r["P"] for r in rounds),
                    "novelty_passing_rounds": sum(r["D"] for r in rounds),
                    "headroom_interpretation": "cumulative initial-anchor bound, point-estimate decisions"}
    return rounds, sequence_row, rules, rewards


def analyze(run: Path, out: Path):
    started = time.monotonic()
    freeze = json.loads((run / "FROZEN_DESIGN.json").read_text())
    result = json.loads((run / "RESULTS.json").read_text())
    if result["errors"]:
        raise ValueError("Native errors present: incomplete trajectories cannot be evaluated as complete")
    cfg = yaml.safe_load((run / "source/r2_discovery.yaml").read_text())
    tasks, strategies = cfg["tasks"], [s["id"] for s in cfg["strategies"]]
    gear_ids = sorted(freeze["gears"])
    item_ids = sorted({i for gear in freeze["gears"].values() for i in gear.values()})
    incidence = np.array([[Counter(freeze["gears"][g].values())[item] for item in item_ids] for g in gear_ids], float)
    features = np.array([freeze["features"][g] for g in gear_ids])
    semantic = {q: np.all(features[:, :q] <= np.asarray(freeze["thresholds"][:q]) + 1e-10, axis=1) for q in (2, 4, 8)}
    all_rounds, all_sequences, all_rules, all_rewards = [], [], [], []
    out.mkdir(parents=True, exist_ok=True)
    atomic_json(out / "SEQUENCE_ANALYSIS_PROTOCOL.json", {
        "frozen_design_sha256": hashlib.sha256((run / "FROZEN_DESIGN.json").read_bytes()).hexdigest(),
        "native_results_sha256": hashlib.sha256((run / "RESULTS.json").read_bytes()).hexdigest(),
        "analysis_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "numeric_rejection_epsilon": REJECTION_EPSILON, "numeric_admission_tolerance": ADMISSION_TOLERANCE,
        "methods": METHODS, "scope": "finite catalogue empirical Monte Carlo joint decisions",
        "behavior_choices": "task-conditioned greedy separated mean-profile count; lower bound on observed packing",
        "source_deletion_initial_items": "reported at final round only"})
    for race in freeze["design"]["races"]:
        data = load_context(result["rows"], gear_ids, tasks, strategies, race, freeze["decisions"]["sample_size"])
        for headroom in freeze["decisions"]["headroom_panels"]:
            for sequence in freeze["design"]["sequences"]:
                for method in METHODS:
                    rounds, seq, rules, rewards = evaluate_sequence(freeze, sequence, race, method, headroom,
                                                                    data, gear_ids, item_ids, incidence,
                                                                    semantic, tasks, strategies)
                    all_rounds.extend(rounds); all_sequences.append(seq); all_rules.extend(rules); all_rewards.extend(rewards)
                print(json.dumps({"race": race, "headroom": headroom, "sequence": sequence["id"],
                                  "completed_trajectories": len(all_sequences)}), flush=True)
    faction = []
    for race in freeze["design"]["races"]:
        for headroom in freeze["decisions"]["headroom_panels"]:
            for method in METHODS:
                selected = [r for r in all_sequences if (r["race"], r["headroom"], r["method"]) == (race, headroom, method)]
                legacy = [r["legacy_useful_fraction"] for r in selected if r["legacy_useful_fraction"] is not None]
                faction.append({"method": method, "headroom": headroom, "faction": selected[0]["faction"],
                                "classes_races_completed": "Warrior/" + race.removeprefix("Race"),
                                "sequences_completed": len(selected), "planned_sequences": 8,
                                "S20": float(np.mean([r["S20"] for r in selected])),
                                "Pass20": float(np.mean([r["Pass20"] for r in selected])),
                                "max_power_growth": max(r["max_power_growth"] for r in selected),
                                "new_useful_fraction": float(np.mean([r["new_useful_fraction"] for r in selected])),
                                "legacy_useful_fraction": float(np.mean(legacy)) if legacy else None,
                                "legacy_source_scope": "previously competitive released items; initial-item deletion separate",
                                "distinct_new_choices": float(np.mean([r["distinct_new_choices"] for r in selected])),
                                "distinct_new_choices_unit": "task-conditioned greedy separated mean profiles",
                                "K20": max(r["K20"] for r in selected), "rule_rows": selected[0]["rule_rows"],
                                "exceptions": float(np.mean([r["exceptions"] for r in selected])),
                                "aggregation": "one race and one class per faction; eight paired source-defined sequences"})
    for name, records in (("ROUND_RESULTS", all_rounds), ("SEQUENCE_RESULTS", all_sequences),
                          ("RULE_REUSE", all_rules), ("REWARD_COUNTERFACTUALS", all_rewards), ("FACTION_SUMMARY", faction)):
        write_csv(out / f"{name}.csv", records)
    summary = {"native_trajectories_per_method_headroom": 16, "methods": len(METHODS),
               "headroom_panels": 2, "round_rows": len(all_rounds), "sequence_rows": len(all_sequences),
               "reward_rows": len(all_rewards), "elapsed_seconds": time.monotonic() - started,
               "joint_successes": sum(r["Pass20"] for r in all_sequences),
               "all_scalar_statuses": dict(Counter(r["solver_status"] for r in all_rounds if r["method"] == "scalar_reprice")),
               "limitations": freeze["design"]["limitations"], "summary_by_faction": faction}
    atomic_json(out / "SEQUENCE_ANALYSIS_SUMMARY.json", summary)
    return summary


def main():
    root = setup_paths()
    p = argparse.ArgumentParser()
    p.add_argument("--run", type=Path, default=root / "runs/r2-discovery/unseen-v1")
    p.add_argument("--out", type=Path, default=root / "artifacts/r2-discovery/latest")
    args = p.parse_args()
    result = analyze(args.run, args.out)
    print(json.dumps({k: v for k, v in result.items() if k != "summary_by_faction"}))


if __name__ == "__main__":
    main()
