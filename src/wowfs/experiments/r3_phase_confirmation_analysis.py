"""Fresh selected-point validation, conditional on the frozen R2 numeric design.

The family covers all fresh means across both races. It separates power support from
behavior memberships, which remain empirical aggregate-response measurements.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.stats import t
import yaml

from wowfs.experiments.r2_sequence_analysis import load_context, nearest_distances, write_csv
from wowfs.experiments.r3_phase_analysis import evaluate_point, phase_arrays, source_state
from wowfs.paths import atomic_json, setup_paths


def supported_competitive(mean, se, cap, old_optimum, scale, multiplicity, n):
    """Conservative N support when cap and old response table are fixed numbers.

    A potentially admissible new gear contributes its upper bound to the
    frontier; it is excluded only if some lower bound already exceeds the cap.
    This remains valid when fresh data choose which gear to report, conditional
    on the simultaneous mean event. A gear's entire policy/task domain must
    have upper bounds under the cap before it can become a supported witness.
    """
    half = t.ppf(1 - .05 / (2 * multiplicity), n - 1) * se
    lower, upper = mean - half, mean + half
    possible = np.all(lower <= cap, axis=(1, 2))
    definite = np.all(upper <= cap, axis=(1, 2))
    frontier_upper = np.asarray(old_optimum).copy()
    if np.any(possible):
        frontier_upper = np.maximum(frontier_upper, upper[possible].max(axis=(0, 1)))
    close = (lower >= frontier_upper - .05 * scale) & definite[:, None, None]
    return close, lower, upper, frontier_upper


def analyze(run, old_run, out):
    if json.loads((run / "PROGRESS.json").read_text())["status"] != "complete":
        raise ValueError("Confirmation native run is incomplete")
    protocol = json.loads((run / "PROTOCOL.json").read_text())
    science = protocol["science"]
    fresh = json.loads((run / "RESULTS.json").read_text())
    if fresh["errors"] or any(r is None for r in fresh["rows"]):
        raise ValueError("Missing/error confirmation cells")
    freeze = json.loads((old_run / "FROZEN_DESIGN.json").read_text())
    old = json.loads((old_run / "RESULTS.json").read_text())
    cfg = yaml.safe_load((old_run / "source/r2_discovery.yaml").read_text())
    tasks, policies = cfg["tasks"], [s["id"] for s in cfg["strategies"]]
    ids = sorted(freeze["gears"])
    offhands, trinkets = science["counterpart_offhands"], science["trinket_pairs"]
    grouped = defaultdict(list)
    for row in fresh["rows"]:
        grouped[row["race"], row["point"]].append(row)
    races = freeze["design"]["races"]
    point_sets = [{point for race, point in grouped if race == context} for context in races]
    if not point_sets or not point_sets[0] or any(s != point_sets[0] for s in point_sets):
        raise ValueError("Confirmation point sets differ across contexts")
    if len(fresh["rows"]) != protocol["logical_cells"]:
        raise ValueError("Confirmation cell count disagrees with frozen job family")
    expected = {f"confirm_{i}": tuple(point) for i, point in enumerate(science["points"])}
    if point_sets[0] != set(expected):
        raise ValueError("Confirmation points disagree with frozen protocol")
    for (_, point_id), rows in grouped.items():
        if any((r["base_dps"], r["weapon_speed"]) != expected[point_id] for r in rows):
            raise ValueError("Confirmation coordinates disagree with frozen protocol")
    records, witness_records = [], []
    for race in races:
        old_mean, old_behavior, lo, hi = load_context(old["rows"], ids, tasks, policies, race, 128)
        new_count = len(fresh["rows"])
        old_count = old_mean.size; union_count = new_count + old_count * len(races)
        old_se = (hi - lo) / (2 * t.ppf(1 - .05 / (2 * old_count), 127))
        old_half = t.ppf(1 - .05 / (2 * union_count), 127) * old_se
        old_lower, old_upper = old_mean - old_half, old_mean + old_half
        for headroom in (0., .05):
            state = source_state(freeze, ids, old_mean, old_behavior, headroom)
            for (context, point_id), rows in sorted(grouped.items()):
                if context != race:
                    continue
                first = rows[0]
                if any(r["base_dps"] != first["base_dps"] or r["weapon_speed"] != first["weapon_speed"]
                       or len(r["dps_samples"]) != science["iterations"] for r in rows):
                    raise ValueError("Confirmation parameters/sample count inconsistent")
                point = {"point": point_id, "base_dps": first["base_dps"],
                         "weapon_speed": first["weapon_speed"], "headroom": headroom}
                result, _ = evaluate_point(rows, point, race, state, freeze, ids, old_mean, old_lower, old_upper,
                    tasks, policies, offhands, trinkets, union_count, new_count)
                keys, mean, se, behavior, lookup, n = phase_arrays(rows, tasks, policies, offhands, trinkets)
                close, lower, upper, frontier = supported_competitive(
                    mean, se, state["cap"], state["optimum"], state["scale"], new_count, n)
                novel = np.zeros_like(close)
                for k in range(len(tasks)):
                    queries = behavior[:, :, k].reshape(-1, 7)
                    old_d = nearest_distances(queries, state["old_profiles"][k]).reshape(mean.shape[:2])
                    archive_d = nearest_distances(queries, state["archive_profiles"][k]).reshape(mean.shape[:2])
                    novel[:, :, k] = (old_d >= .05 - 1e-10) & (archive_d >= .05 - 1e-10)
                tf = np.array([key[0] == 19019 for key in keys])
                supported_novel = np.any(close & novel, axis=(1, 2)) & tf
                result.update({
                    "fresh_mean_family_both_races": new_count,
                    "fixed_cap_and_N_supported_tf_loadouts": int(np.sum(np.any(close, axis=(1, 2)) & tf)),
                    "fixed_cap_and_N_supported_empirical_D_tf_loadouts": int(np.sum(supported_novel)),
                    "fixed_cap_N_supported_empirical_D_reactivation": bool(result["tf_reactivated"] and np.any(supported_novel)),
                    "possible_admissible_frontier_upper": frontier.tolist(),
                    "N_support_scope": "conditional on frozen numeric old response table and initial tolerance; simultaneous fresh-mean family",
                    "fixed_cap_interval_scope": "approximate simultaneous Student-t means over all3840 fresh cells across both races; R2 numeric cap held fixed",
                    "power_interval_scope": "approximate simultaneous Student-t means over old and fresh physical cells across both races; population-anchor sensitivity",
                    "joint_statistical_P_N_D_certificate": False,
                })
                for g in np.flatnonzero(supported_novel):
                    for p, k in np.argwhere(close[g] & novel[g]):
                        witness_records.append({**point, "race": race, "offhand": keys[g][0],
                            "trinket1": keys[g][1], "trinket2": keys[g][2],
                            "policy": policies[p], "task": tasks[k]["id"],
                            "mean": float(mean[g, p, k]), "lower": float(lower[g, p, k]),
                            "upper": float(upper[g, p, k]),
                            "competitive_margin_lower": float(lower[g, p, k] - frontier[k] + .05 * state["scale"][k]),
                            "cap_slack_lower_all_policy_task": float(np.min(state["cap"] - upper[g])),
                            "behavior_support": "empirical means only",
                            "cache_directory": lookup[int(g), int(p), int(k)]["cache_directory"]})
                records.append(result)
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "PHASE_CONFIRMATION.csv", [{k: v for k, v in r.items() if k != "tf_witnesses"} for r in records])
    write_csv(out / "PHASE_CONFIRMATION_SUPPORTED_WITNESSES.csv", witness_records)
    summaries = []
    for race in races:
        for headroom in (0., .05):
            rs = [r for r in records if r["race"] == race and r["headroom"] == headroom]
            summaries.append({"race": race, "headroom": headroom, "points": len(rs),
                "empirical_region_points": sum(r["empirical_tf_complement_region"] for r in rs),
                "fixed_cap_power_supported_region_points": sum(r["empirical_region_with_fixed_cap_supported_tf_witness"] for r in rs),
                "fixed_cap_N_supported_empirical_D_points": sum(r["fixed_cap_N_supported_empirical_D_reactivation"] for r in rs),
                "anchor_sensitivity_power_supported_points": sum(r["empirical_region_with_supported_safe_tf_witness"] for r in rs)})
    atomic_json(out / "PHASE_CONFIRMATION_WITNESSES.json", records)
    atomic_json(out / "PHASE_CONFIRMATION_SUMMARY.json", {"summaries": summaries,
        "new_native_cells": len(fresh["rows"]), "iterations_per_cell": science["iterations"],
        "analysis_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "protocol_sha256": hashlib.sha256((run / "PROTOCOL.json").read_bytes()).hexdigest(),
        "results_sha256": hashlib.sha256((run / "RESULTS.json").read_bytes()).hexdigest()})
    print(json.dumps(summaries))
    return records


def main():
    root = setup_paths(); p = argparse.ArgumentParser()
    p.add_argument("--run", type=Path, default=root / "runs/r3-gold/phase-confirmation-v1")
    p.add_argument("--old-run", type=Path, default=root / "runs/r2-discovery/unseen-v1")
    p.add_argument("--out", type=Path, default=root / "artifacts/r3-gold")
    args = p.parse_args(); analyze(args.run, args.old_run, args.out)


if __name__ == "__main__":
    main()
