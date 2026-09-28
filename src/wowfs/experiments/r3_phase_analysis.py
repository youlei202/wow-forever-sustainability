"""Analyze native weapon counterfactuals against the unchanged R2 reference.

Reports raw batch power before cap filtering as well as selected safe choices.
No new native jobs are launched; behavior uncertainty is not invented from
aggregate action/resource summaries.
"""
from __future__ import annotations

import argparse
from collections import defaultdict, deque
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.stats import t
import yaml

from wowfs.experiments.r2_sequence_analysis import behavior_vector, load_context, nearest_distances, write_csv
from wowfs.paths import atomic_json, canonical_hash, setup_paths


def components(mask):
    mask = np.asarray(mask, bool)
    unseen = set(map(tuple, np.argwhere(mask)))
    result = []
    while unseen:
        start = min(unseen); unseen.remove(start)
        found, queue = [start], deque([start])
        while queue:
            y, x = queue.popleft()
            for neighbor in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if neighbor in unseen:
                    unseen.remove(neighbor); queue.append(neighbor); found.append(neighbor)
        result.append(found)
    return sorted(result, key=len, reverse=True)


def source_state(freeze, ids, old_mean, old_behavior, headroom):
    index = {g: i for i, g in enumerate(ids)}
    initial = np.array([index[g] for g in freeze["initial_gear_ids"]])
    scale = old_mean[initial].max(axis=(0, 1)); cap = (1 + headroom) * scale
    safe = np.all(old_mean <= cap[None, None, :] + 1e-10, axis=(1, 2))
    membership = freeze["memberships"]["expanded_interleaved_0"]
    before_raw = np.array([index[g] for g, first in membership.items() if first <= 19])
    before = before_raw[safe[before_raw]]
    optimum = old_mean[before].max(axis=(0, 1))
    archive = [set((int(g), p) for g in initial for p in range(old_mean.shape[1])) for _ in range(old_mean.shape[2])]
    sequence = next(s for s in freeze["design"]["sequences"] if s["id"] == "expanded_interleaved_0")
    for arrival in sequence["arrivals"][:19]:
        current = np.array([index[g] for g, first in membership.items() if first <= arrival["round"]])
        current = current[safe[current]]
        current_optimum = old_mean[current].max(axis=(0, 1))
        newly = [g for g in current if arrival["item_id"] in freeze["gears"][ids[g]].values()]
        for k in range(len(optimum)):
            for g in newly:
                for p in range(old_mean.shape[1]):
                    if old_mean[g, p, k] >= current_optimum[k] - .05 * scale[k] - 1e-10:
                        archive[k].add((int(g), p))
    return {"initial": initial, "scale": scale, "cap": cap, "before_raw": before_raw,
            "before": before, "optimum": optimum,
            "old_profiles": [old_behavior[before, :, k].reshape(-1, 7) for k in range(len(optimum))],
            "archive_profiles": [np.array([old_behavior[g, p, k] for g, p in sorted(archive[k])])
                                 for k in range(len(optimum))]}


def phase_arrays(rows, tasks, policies, offhands, trinkets):
    gear_keys = [(oh, *pair) for oh in offhands for pair in trinkets]
    gmap, pmap, tmap = ({key: j for j, key in enumerate(keys)}
                        for keys in (gear_keys, policies, [x["id"] for x in tasks]))
    shape = (len(gear_keys), len(policies), len(tasks))
    mean, se = np.full(shape, np.nan), np.full(shape, np.nan)
    behaviors = np.full((*shape, 7), np.nan)
    lookup, seen = {}, set()
    n = None
    for row in rows:
        gp = (row["offhand"], row["trinket1"], row["trinket2"])
        index = gmap[gp], pmap[row["strategy"]], tmap[row["task"]]
        if index in seen:
            raise ValueError("Duplicate phase gear/policy/task")
        seen.add(index)
        samples = np.asarray(row["dps_samples"], float)
        if samples.ndim != 1 or len(samples) < 2 or not np.isfinite(samples).all():
            raise ValueError("Incomplete/nonfinite phase samples")
        if n is None:
            n = len(samples)
        if len(samples) != n:
            raise ValueError("Mismatched phase sample counts")
        mean[index], se[index] = samples.mean(), samples.std(ddof=1) / np.sqrt(n)
        behaviors[index] = behavior_vector(row, tasks[index[2]]["duration_seconds"])
        lookup[index] = row
    if not np.isfinite(mean).all() or not np.isfinite(behaviors).all():
        raise ValueError("Incomplete phase point response table")
    return gear_keys, mean, se, behaviors, lookup, n


def evaluate_point(rows, point, race, state, freeze, ids, old_mean, old_lower, old_upper,
                   tasks, policies, offhands, trinkets, multiplicity, fixed_cap_multiplicity=None):
    gear_keys, mean, se, behaviors, lookup, n = phase_arrays(rows, tasks, policies, offhands, trinkets)
    quantile = t.ppf(1 - .05 / (2 * multiplicity), n - 1)
    lower, upper = mean - quantile * se, mean + quantile * se
    scale, cap, before = state["scale"], state["cap"], state["before"]
    headroom = float(point["headroom"])
    anchor_low = old_lower[state["initial"]].max(axis=(0, 1))
    anchor_high = old_upper[state["initial"]].max(axis=(0, 1))
    max_ratio = np.max(mean / cap[None, None, :], axis=(1, 2))
    safe = max_ratio <= 1 + 1e-10
    supported_safe = np.all(upper <= (1 + headroom) * anchor_low[None, None, :], axis=(1, 2))
    supported_unsafe = np.any(lower > (1 + headroom) * anchor_high[None, None, :], axis=(1, 2))
    fixed_q = t.ppf(1 - .05 / (2 * (fixed_cap_multiplicity or multiplicity)), n - 1)
    fixed_upper, fixed_lower = mean + fixed_q * se, mean - fixed_q * se
    fixed_safe = np.all(fixed_upper <= cap[None, None, :], axis=(1, 2))
    fixed_unsafe = np.any(fixed_lower > cap[None, None, :], axis=(1, 2))
    optimum = np.maximum(state["optimum"], mean[safe].max(axis=(0, 1))) if np.any(safe) else state["optimum"].copy()
    raw_new_peak = mean.max(axis=(0, 1))
    raw_optimum = np.maximum(old_mean[state["before_raw"]].max(axis=(0, 1)), raw_new_peak)
    close = (mean >= optimum[None, None, :] - .05 * scale[None, None, :] - 1e-10) & safe[:, None, None]
    qualifying_gears = np.any(close, axis=(1, 2))
    old_distance = np.empty(mean.shape); archive_distance = np.empty(mean.shape)
    for k in range(len(tasks)):
        queries = behaviors[:, :, k].reshape(-1, 7)
        old_distance[:, :, k] = nearest_distances(queries, state["old_profiles"][k]).reshape(len(gear_keys), len(policies))
        archive_distance[:, :, k] = nearest_distances(queries, state["archive_profiles"][k]).reshape(len(gear_keys), len(policies))
    novel = close & (old_distance >= .05 - 1e-10) & (archive_distance >= .05 - 1e-10)
    tf = np.array([key[0] == 19019 for key in gear_keys])
    weights = np.asarray(freeze["decisions"]["task_weights"])
    new_mass = float(weights @ np.any(close, axis=(0, 1)))
    novel_mass = float(weights @ np.any(novel, axis=(0, 1)))
    tf_mass = float(weights @ np.any(close[tf], axis=(0, 1)))
    tf_novel_mass = float(weights @ np.any(novel[tf], axis=(0, 1)))
    legacy = {}
    for source in offhands:
        source_before = [g for g in before if source in freeze["gears"][ids[g]].values()]
        before_mass = (float(weights @ np.any(old_mean[source_before] >= state["optimum"][None, None, :] - .05 * scale[None, None, :] - 1e-10, axis=(0, 1)))
                       if source_before else 0.0)
        source_rows = np.array([g[0] == source for g in gear_keys])
        pair_mass = float(weights @ np.any(close[source_rows], axis=(0, 1)))
        legacy[str(source)] = {"before_mass": before_mass, "pair_mass": pair_mass,
                               "gain": pair_mass - before_mass,
                               "binary_reactivated": before_mass < .05 <= pair_mass,
                               "old_allowed_gears": len(source_before)}
    tf_reactivated = legacy["19019"]["binary_reactivated"]
    tf_novel_gears = tf & np.any(novel, axis=(1, 2))
    selected_points = []
    for g in np.flatnonzero(tf_novel_gears):
        # A witness must actually be competitive and novel on its stated task.
        pairs = np.argwhere(novel[g])
        p, k = min((tuple(x) for x in pairs), key=lambda pk: (-old_distance[g, pk[0], pk[1]], pk))
        row = lookup[int(g), int(p), int(k)]
        selected_points.append({"offhand": 19019, "trinket1": gear_keys[g][1], "trinket2": gear_keys[g][2],
                                "policy": policies[p], "task": tasks[k]["id"],
                                "mean_dps": float(mean[g, p, k]), "all_task_means_this_policy": mean[g, p].tolist(),
                                "old_distance": float(old_distance[g, p, k]),
                                "archive_distance": float(archive_distance[g, p, k]),
                                "all_policy_peak_ratio_to_cap": float(max_ratio[g]),
                                "all_policy_power_upper_excess": float(np.max(upper[g] - (1 + headroom) * anchor_low)),
                                "supported_safe_mean_power": bool(supported_safe[g]),
                                "fixed_cap_supported_safe_mean_power": bool(fixed_safe[g]),
                                "fixed_cap_upper_excess": float(np.max(fixed_upper[g] - cap)),
                                "cache_directory": row["cache_directory"], "output_sha256": row["output_sha256"]})
    region = bool(tf_reactivated and tf_novel_mass >= .05)
    record = {**point, "race": race, "iterations_per_cell": n,
              "native_new_loadouts": len(gear_keys), "raw_unsafe_loadouts": int(np.sum(~safe)),
              "raw_batch_max_power_ratio_to_cap": float(np.max(raw_new_peak / cap)),
              "raw_batch_max_growth_from_initial": float(np.max(raw_new_peak / scale - 1)),
              "raw_all_catalogue_max_power_ratio_to_cap": float(np.max(raw_optimum / cap)),
              "unfiltered_batch_P": bool(np.all(safe)),
              "safe_new_loadouts": int(np.sum(safe)), "safe_new_fraction": float(np.mean(safe)),
              "competitive_new_loadouts": int(np.sum(qualifying_gears)),
              "competitive_tf_loadouts": int(np.sum(qualifying_gears & tf)),
              "competitive_non_tf_loadouts": int(np.sum(qualifying_gears & ~tf)),
              "novel_competitive_tf_loadouts": int(np.sum(tf_novel_gears)),
              "new_competitive_task_mass": new_mass, "new_novel_task_mass": novel_mass,
              "tf_competitive_task_mass": tf_mass, "tf_novel_task_mass": tf_novel_mass,
              "tf_reactivated": tf_reactivated, "reactivated_legacy_sources": sum(v["binary_reactivated"] for v in legacy.values()),
              "legacy_reactivation": legacy, "empirical_tf_complement_region": region,
              "safe_reference_peak_growth": float(np.max(optimum / scale - 1)),
              "safe_reference_envelope_increment": float(np.max((optimum - state["optimum"]) / scale)),
              "initial_reference": scale.tolist(), "before_optimum": state["optimum"].tolist(),
              "after_safe_optimum": optimum.tolist(), "raw_new_batch_peak": raw_new_peak.tolist(),
              "raw_after_optimum": raw_optimum.tolist(),
              "supported_safe_new_loadouts": int(np.sum(supported_safe)),
              "supported_unsafe_new_loadouts": int(np.sum(supported_unsafe)),
              "power_unresolved_new_loadouts": int(np.sum(~supported_safe & ~supported_unsafe)),
              "supported_safe_novel_tf_loadouts": int(np.sum(supported_safe & tf_novel_gears)),
              "empirical_region_with_supported_safe_tf_witness": bool(region and np.any(supported_safe & tf_novel_gears)),
              "fixed_cap_supported_safe_new_loadouts": int(np.sum(fixed_safe)),
              "fixed_cap_supported_unsafe_new_loadouts": int(np.sum(fixed_unsafe)),
              "fixed_cap_unresolved_new_loadouts": int(np.sum(~fixed_safe & ~fixed_unsafe)),
              "fixed_cap_supported_safe_novel_tf_loadouts": int(np.sum(fixed_safe & tf_novel_gears)),
              "empirical_region_with_fixed_cap_supported_tf_witness": bool(region and np.any(fixed_safe & tf_novel_gears)),
              "fixed_cap_interval_scope": "approximate simultaneous Student-t means over phase physical cells within race; R2 numeric cap held fixed",
              "power_interval_scope": "approximate simultaneous Student-t means over old and phase physical cells within race",
              "behavior_interval_scope": "not estimated; aggregate native action/resource means only",
              "reference_task_caps": len(tasks), "excluded_configuration_rows": int(np.sum(~safe)),
              "learned_type_rule": False, "admission_information": "full current point response table",
              "tf_witnesses": selected_points}
    return record, (gear_keys, mean, se, lookup)


def plot(records, science, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import TwoSlopeNorm
    from matplotlib.lines import Line2D
    dps = science["axes"]["base_weapon_dps"]; speed = science["axes"]["weapon_speed_seconds"]
    races = ["RaceHuman", "RaceOrc"]
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 9), sharex=True, sharey=True)
    max_ratio = max(r["raw_batch_max_power_ratio_to_cap"] for r in records)
    norm = TwoSlopeNorm(vmin=.8, vcenter=1, vmax=max(1.2, max_ratio))
    for ri, race in enumerate(races):
        for hi, headroom in enumerate((0., .05)):
            ax = axes[ri, hi]
            rows = [r for r in records if r["race"] == race and r["headroom"] == headroom]
            power = np.full((len(speed), len(dps)), np.nan)
            region = np.zeros_like(power, bool); supported = region.copy()
            for row in rows:
                y, x = speed.index(row["weapon_speed"]), dps.index(row["base_dps"])
                power[y, x] = row["raw_batch_max_power_ratio_to_cap"]
                region[y, x] = row["empirical_tf_complement_region"]
                supported[y, x] = row["empirical_region_with_fixed_cap_supported_tf_witness"]
            im = ax.imshow(power, origin="lower", norm=norm, cmap="coolwarm", aspect="auto")
            if np.any(region) and not np.all(region):
                ax.contour(region.astype(float), levels=[.5], colors="black", linewidths=1.5)
            for row in rows:
                if row["empirical_tf_complement_region"]:
                    y, x = speed.index(row["weapon_speed"]), dps.index(row["base_dps"])
                    ax.text(x, y, str(row["novel_competitive_tf_loadouts"]), ha="center", va="center", fontsize=9)
            ys, xs = np.nonzero(supported)
            ax.scatter(xs, ys, facecolors="none", edgecolors="#006d2c", s=155, linewidths=1.7)
            ax.scatter([dps.index(51 / 1.3)], [speed.index(1.3)], marker="*", s=155,
                       facecolors="white", edgecolors="black", zorder=5)
            ax.set_title(f"{race.removeprefix('Race')} | {headroom:.0%} cumulative headroom\n"
                         f"{int(region.sum())}/63 observed region points; {int(supported.sum())} power-supported", fontsize=11)
            ax.set_xticks(range(len(dps)), [f"{x:.2f}" if x % 1 else f"{x:g}" for x in dps], rotation=45)
            ax.set_yticks(range(len(speed)), [f"{x:.1f}" for x in speed])
            if ri == 1: ax.set_xlabel("Main-hand base weapon DPS")
            if hi == 0: ax.set_ylabel("Main-hand base speed (s)")
    fig.suptitle("Thunderfury re-entry: raw power and the region retained by a response-informed cap filter",
                 fontsize=12, fontweight="bold", y=.985)
    fig.subplots_adjust(left=.07, right=.86, top=.90, bottom=.18, wspace=.16, hspace=.35)
    cax = fig.add_axes([.89, .27, .022, .53])
    fig.colorbar(im, cax=cax, label="Raw all-counterpart peak / fixed cap (before admission)")
    handles = [Line2D([0], [0], color="black", label="Outline: TF reactivated + novel after cap filtering"),
               Line2D([0], [0], marker="o", color="#006d2c", markerfacecolor="none", linestyle="none",
                      label="Green ring: selected witness has supported mean-power safety against the frozen numeric cap"),
               Line2D([0], [0], marker="*", color="black", markerfacecolor="white", linestyle="none",
                      label="Star: original native Blood Talon parameters")]
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(.05, .035), fontsize=8.5, frameon=False)
    fig.text(.06, .013, "Numbers count novel competitive TF loadouts, not independent items. Outline does not certify behavior or a learned rule.", fontsize=8)
    (out / "figures").mkdir(exist_ok=True)
    for suffix in ("png", "pdf"):
        fig.savefig(out / f"figures/complement_phase_diagram.{suffix}", dpi=190)
    plt.close(fig)


def analyze(phase_run, old_run, out):
    if json.loads((phase_run / "PROGRESS.json").read_text())["status"] != "complete":
        raise ValueError("Phase native run is not complete")
    protocol = json.loads((phase_run / "PROTOCOL.json").read_text()); science = protocol["science"]
    phase = json.loads((phase_run / "RESULTS.json").read_text())
    if phase["errors"] or any(r is None for r in phase["rows"]):
        raise ValueError("Incomplete native phase outputs")
    freeze = json.loads((old_run / "FROZEN_DESIGN.json").read_text())
    old = json.loads((old_run / "RESULTS.json").read_text())
    cfg = yaml.safe_load((old_run / "source/r2_discovery.yaml").read_text())
    tasks, policies = cfg["tasks"], [x["id"] for x in cfg["strategies"]]
    ids = sorted(freeze["gears"]); gmap = {g: i for i, g in enumerate(ids)}
    offhands, trinkets = science["counterpart_offhands"], science["trinket_pairs"]
    grouped = defaultdict(list)
    for row in phase["rows"]:
        grouped[row["race"], row["point"]].append(row)
    expected_points = {(race, f"d{di}_s{si}") for race in freeze["design"]["races"]
                       for di in range(len(science["axes"]["base_weapon_dps"]))
                       for si in range(len(science["axes"]["weapon_speed_seconds"]))}
    if set(grouped) != expected_points:
        raise ValueError("Missing or unexpected race/grid points")
    for (race, point_id), rows in grouped.items():
        di, si = (int(part[1:]) for part in point_id.split("_"))
        for row in rows:
            if (row["base_dps"] != science["axes"]["base_weapon_dps"][di]
                    or row["weapon_speed"] != science["axes"]["weapon_speed_seconds"][si]
                    or len(row["dps_samples"]) != science["iterations"]):
                raise ValueError("Phase parameter/sample metadata disagrees with frozen protocol")
    out.mkdir(parents=True, exist_ok=True)
    records, native_comparison = [], []
    connectivity = []
    for race in freeze["design"]["races"]:
        old_mean, old_behavior, old_lo, old_hi = load_context(old["rows"], ids, tasks, policies, race, 128)
        old_count = old_mean.size; new_count = sum(len(v) for (r, _), v in grouped.items() if r == race)
        multiplicity = old_count + new_count
        old_q = t.ppf(1 - .05 / (2 * old_count), 127)
        old_se = (old_hi - old_lo) / (2 * old_q)
        full_q = t.ppf(1 - .05 / (2 * multiplicity), 127)
        old_lower, old_upper = old_mean - full_q * old_se, old_mean + full_q * old_se
        states = {h: source_state(freeze, ids, old_mean, old_behavior, h) for h in (0., .05)}
        for (context, point_id), rows in sorted(grouped.items()):
            if context != race:
                continue
            first = rows[0]
            for h, state in states.items():
                point = {"point": point_id, "base_dps": first["base_dps"], "weapon_speed": first["weapon_speed"], "headroom": h}
                result, arrays = evaluate_point(rows, point, race, state, freeze, ids, old_mean, old_lower, old_upper,
                                                tasks, policies, offhands, trinkets, multiplicity, new_count)
                records.append(result)
            # Native parameter identity checked descriptively against independent R2 seeds.
            if abs(first["base_dps"] - 51 / 1.3) < 1e-9 and abs(first["weapon_speed"] - 1.3) < 1e-9:
                gear_keys, means, errors, lookup = arrays
                for g, (oh, t1, t2) in enumerate(gear_keys):
                    gear = dict(freeze["gears"]["5ae0e1e5d00fbdb1"])
                    gear.update(off_hand=oh, trinket1=t1, trinket2=t2)
                    key = canonical_hash(gear)[:16]
                    if key not in gmap:
                        continue
                    gi = gmap[key]
                    for p, policy in enumerate(policies):
                        for k, task in enumerate(tasks):
                            se = float(np.hypot(errors[g, p, k], old_se[gi, p, k]))
                            difference = float(means[g, p, k] - old_mean[gi, p, k])
                            native_comparison.append({"race": race, "gear_id": key, "task": task["id"], "policy": policy,
                                                      "r2_mean": float(old_mean[gi, p, k]), "phase_mean": float(means[g, p, k]),
                                                      "independent_seed_difference": difference, "difference_se": se,
                                                      "standardized_difference": difference / se if se else None,
                                                      "scope": "descriptive fresh-seed mean comparison, not a deterministic identity test"})
        for h in (0., .05):
            subset = [r for r in records if r["race"] == race and r["headroom"] == h]
            axes = science["axes"]; speeds, dps = axes["weapon_speed_seconds"], axes["base_weapon_dps"]
            mask = np.zeros((len(speeds), len(dps)), bool)
            for row in subset:
                mask[speeds.index(row["weapon_speed"]), dps.index(row["base_dps"])] = row["empirical_tf_complement_region"]
            groups = components(mask)
            connectivity.append({"race": race, "headroom": h, "region_points": int(mask.sum()),
                                 "components": len(groups), "component_sizes": [len(x) for x in groups],
                                 "power_supported_region_points": sum(r["empirical_region_with_supported_safe_tf_witness"] for r in subset),
                                 "fixed_cap_power_supported_region_points": sum(r["empirical_region_with_fixed_cap_supported_tf_witness"] for r in subset),
                                 "raw_safe_batch_points": sum(r["unfiltered_batch_P"] for r in subset),
                                 "interpretation": "four-neighbor connected observed grid points, not unobserved continuous-space guarantee"})
    write_csv(out / "COMPLEMENT_PHASE_GRID.csv", [{k: v for k, v in r.items() if k != "tf_witnesses"} for r in records])
    write_csv(out / "NATIVE_POINT_COMPARISON.csv", native_comparison)
    atomic_json(out / "PHASE_WITNESSES.json", records)
    atomic_json(out / "PHASE_SUMMARY.json", {"connectivity": connectivity,
                "phase_native_cells": len(phase["rows"]), "iterations_per_cell": science["iterations"],
                "native_parameter_comparison_rows": len(native_comparison),
                "analysis_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "phase_protocol_sha256": hashlib.sha256((phase_run / "PROTOCOL.json").read_bytes()).hexdigest(),
                "phase_results_sha256": hashlib.sha256((phase_run / "RESULTS.json").read_bytes()).hexdigest()})
    plot(records, science, out)
    print(json.dumps(connectivity))
    return records


def main():
    root = setup_paths()
    p = argparse.ArgumentParser()
    p.add_argument("--run", type=Path, default=root / "runs/r3-gold/phase-grid-v1")
    p.add_argument("--old-run", type=Path, default=root / "runs/r2-discovery/unseen-v1")
    p.add_argument("--out", type=Path, default=root / "artifacts/r3-gold")
    args = p.parse_args()
    analyze(args.run, args.old_run, args.out)


if __name__ == "__main__":
    main()
