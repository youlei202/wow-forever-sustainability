"""Complementarity atlas from existing R2 native outputs; launches no simulator."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import yaml

from wowfs.experiments.r2_sequence_analysis import load_context, nearest_distances
from wowfs.paths import atomic_json, setup_paths

MODES = ("empirical_safe", "no_control")
CATEGORIES = ("positive_reactivation", "power_neutral_nonreactivating",
              "apparent_complement_fails_power", "local_rule_blocks_useful_complement",
              "dangerous_legacy_safe_only_with_new_complement")


def finite(values):
    return [float(v) if np.isfinite(v) else None for v in values]


def competitive_mass(values, optimum, scale, weights, epsilon):
    values = np.asarray(values)
    if len(values) == 0:
        return 0.0, np.zeros(len(optimum), bool)
    flags = np.max(values, axis=(0, 1)) >= optimum - epsilon * scale - 1e-10
    return float(weights @ flags), flags


def row_categories(row):
    useful = row["pair_task_mass_after"] >= .05
    if row["mode"] == "empirical_safe":
        categories = []
        if row["reactivation_gain"] > 0 and useful:
            categories.append("positive_reactivation")
        if useful and row["reactivation_gain"] <= 0 and row["max_envelope_increment_normalized"] <= 1e-10:
            categories.append("power_neutral_nonreactivating")
        if useful and row["q8_blocked_competitive_loadouts"] > 0:
            categories.append("local_rule_blocks_useful_complement")
        if useful and row["legacy_status_before"] == "cap_blocked":
            categories.append("dangerous_legacy_safe_only_with_new_complement")
        return categories
    if (useful and row["reactivation_gain"] > 0 and row["unsafe_competitive_pair_loadouts"] > 0
            and row["safe_competitive_pair_loadouts"] == 0):
        return ["apparent_complement_fails_power"]
    return []


def atlas_records(freeze, data, ids, tasks, policies):
    decision = freeze["decisions"]
    epsilon, resolution = decision["near_optimal_tolerance"], decision["behavior"]["resolution"]
    weights = np.asarray(decision["task_weights"])
    gmap = {key: i for i, key in enumerate(ids)}
    initial = np.array([gmap[g] for g in freeze["initial_gear_ids"]])
    gear_items = [set(freeze["gears"][g].values()) for g in ids]
    features = np.array([freeze["features"][g] for g in ids])
    semantic = {q: np.all(features[:, :q] <= np.asarray(freeze["thresholds"][:q]) + 1e-10, axis=1)
                for q in (2, 4, 8)}
    descriptors = freeze["design"]["item_descriptors"]
    for race, (means, behavior, _lower, _upper) in data.items():
        scale = means[initial].max(axis=(0, 1))
        for headroom in decision["headroom_panels"]:
            cap = (1 + headroom) * scale
            power_ratio = np.max(means / cap[None, None, :], axis=(1, 2))
            safe = power_ratio <= 1 + 1e-10
            for sequence in freeze["design"]["sequences"]:
                membership = freeze["memberships"][sequence["id"]]
                first_round = np.full(len(ids), 999, int)
                for key, first in membership.items():
                    first_round[gmap[key]] = first
                for mode in MODES:
                    archive = [set((int(g), p) for g in initial for p in range(len(policies))) for _ in tasks]
                    allowed_filter = safe if mode == "empirical_safe" else np.ones(len(ids), bool)
                    for arrival in sequence["arrivals"]:
                        number, new = arrival["round"], arrival["item_id"]
                        before_raw = np.flatnonzero(first_round < number)
                        after_raw = np.flatnonzero(first_round <= number)
                        before = before_raw[allowed_filter[before_raw]]
                        after = after_raw[allowed_filter[after_raw]]
                        before_opt, after_opt = means[before].max(axis=(0, 1)), means[after].max(axis=(0, 1))
                        new_raw = np.array([g for g in after_raw if new in gear_items[g]], int)
                        new_after = new_raw[allowed_filter[new_raw]]
                        old_after = np.array([g for g in after if new not in gear_items[g]], int)
                        new_mass, _ = competitive_mass(means[new_after], after_opt, scale, weights, epsilon)
                        new_close = means[new_after] >= after_opt[None, None, :] - epsilon * scale[None, None, :] - 1e-10
                        old_distance = np.zeros((len(new_after), len(policies), len(tasks)))
                        archive_distance = np.zeros_like(old_distance)
                        for k in range(len(tasks)):
                            query = behavior[new_after, :, k].reshape(-1, 7)
                            old_distance[:, :, k] = nearest_distances(query, behavior[old_after, :, k].reshape(-1, 7)).reshape(len(new_after), len(policies))
                            archived = np.array([behavior[g, p, k] for g, p in sorted(archive[k])])
                            archive_distance[:, :, k] = nearest_distances(query, archived).reshape(len(new_after), len(policies))
                        legacy_items = sorted(set.union(*(gear_items[g] for g in before_raw)))
                        for legacy in legacy_items:
                            if legacy == new:
                                continue
                            legacy_before_raw = np.array([g for g in before_raw if legacy in gear_items[g]], int)
                            legacy_before = legacy_before_raw[allowed_filter[legacy_before_raw]]
                            legacy_mass, _ = competitive_mass(means[legacy_before], before_opt, scale, weights, epsilon)
                            pair_raw = np.array([g for g in new_raw if legacy in gear_items[g]], int)
                            pair_positions = np.array([j for j, g in enumerate(new_after) if legacy in gear_items[g]], int)
                            pair = new_after[pair_positions]
                            pair_mass, pair_tasks = competitive_mass(means[pair], after_opt, scale, weights, epsilon)
                            pair_close = new_close[pair_positions]
                            qualifying = np.any(pair_close, axis=(1, 2)) if len(pair) else np.zeros(0, bool)
                            qualifiers = pair[qualifying]
                            raw_close = (means[pair_raw] >= after_opt[None, None, :] - epsilon * scale[None, None, :] - 1e-10)
                            raw_qualifiers = pair_raw[np.any(raw_close, axis=(1, 2))] if len(pair_raw) else pair_raw
                            old_d, archive_d = old_distance[pair_positions], archive_distance[pair_positions]
                            novel = pair_close & (old_d >= resolution - 1e-10) & (archive_d >= resolution - 1e-10)
                            novel_mass = float(weights @ np.any(novel, axis=(0, 1))) if len(pair) else 0.0
                            best_pairs = []
                            for k in range(len(tasks)):
                                if not len(pair):
                                    best_pairs.append(None)
                                    continue
                                gp = np.unravel_index(np.argmax(means[pair, :, k]), (len(pair), len(policies)))
                                g, p = int(pair[gp[0]]), int(gp[1])
                                best_pairs.append({"gear_id": ids[g], "policy": policies[p], "task": tasks[k]["id"],
                                                   "utility": float(means[g, p, k]), "old_distance": float(old_d[gp[0], p, k]),
                                                   "archive_distance": float(archive_d[gp[0], p, k]),
                                                   "all_policy_peak_ratio_to_cap": float(power_ratio[g]),
                                                   "cap_slack_by_task": (cap - means[g, p]).tolist()})
                            status = ("cap_blocked" if not len(legacy_before) and len(legacy_before_raw)
                                      else "competitive" if legacy_mass >= .05 else "legal_noncompetitive")
                            row = {"race": race, "faction": "Alliance" if race == "RaceHuman" else "Horde",
                                   "sequence": sequence["id"], "generator": sequence["generator"],
                                   "round": number, "headroom": headroom, "mode": mode,
                                   "new_item": new, "new_name": descriptors[str(new)]["name"],
                                   "legacy_item": legacy, "legacy_name": descriptors[str(legacy)]["name"],
                                   "new_effect_kind": descriptors[str(new)]["effect"]["kind"],
                                   "legacy_effect_kind": descriptors[str(legacy)]["effect"]["kind"],
                                   "initial_scale": scale.tolist(), "fixed_cap": cap.tolist(),
                                   "global_optimum_before": before_opt.tolist(), "global_optimum_after": after_opt.tolist(),
                                   "legacy_best_before": means[legacy_before].max(axis=(0, 1)).tolist() if len(legacy_before) else [None] * len(tasks),
                                   "pair_best_after": means[pair].max(axis=(0, 1)).tolist() if len(pair) else [None] * len(tasks),
                                   "legacy_mass_before": legacy_mass, "pair_task_mass_after": pair_mass,
                                   "reactivation_gain": pair_mass - legacy_mass,
                                   "binary_reactivation": legacy_mass < .05 <= pair_mass,
                                   "new_item_mass_after": new_mass, "new_use_qualifies": new_mass >= .05,
                                   "pair_novel_task_mass": novel_mass, "pair_D": novel_mass >= .05,
                                   "legacy_status_before": status, "legacy_raw_loadouts_before": len(legacy_before_raw),
                                   "legacy_allowed_loadouts_before": len(legacy_before),
                                   "pair_raw_loadouts_after": len(pair_raw), "pair_allowed_loadouts_after": len(pair),
                                   "pair_competitive_loadouts": len(qualifiers),
                                   "safe_competitive_pair_loadouts": int(np.sum(safe[raw_qualifiers])),
                                   "unsafe_competitive_pair_loadouts": int(np.sum(~safe[raw_qualifiers])),
                                   "max_pair_old_distance_competitive": float(np.max(old_d[pair_close])) if np.any(pair_close) else None,
                                   "max_pair_archive_distance_competitive": float(np.max(archive_d[pair_close])) if np.any(pair_close) else None,
                                   "all_competitive_profiles_have_old_substitute": bool(np.all(old_d[pair_close] < resolution - 1e-10)) if np.any(pair_close) else None,
                                   "minimum_pair_peak_ratio_to_cap": float(power_ratio[pair_raw].min()) if len(pair_raw) else None,
                                   "maximum_pair_peak_ratio_to_cap": float(power_ratio[pair_raw].max()) if len(pair_raw) else None,
                                   "max_envelope_increment_normalized": float(np.max((after_opt - before_opt) / scale)),
                                   "max_total_envelope_growth": float(np.max(after_opt / scale - 1)),
                                   "q2_blocked_competitive_loadouts": int(np.sum(~semantic[2][qualifiers])),
                                   "q4_blocked_competitive_loadouts": int(np.sum(~semantic[4][qualifiers])),
                                   "q8_blocked_competitive_loadouts": int(np.sum(~semantic[8][qualifiers])),
                                   "rule_state": "unchanged fixed empirical power caps; per-loadout response access" if mode == "empirical_safe" else "unrestricted current catalogue",
                                   "new_item_specific_exception_introduced": False,
                                   "reusable_rule_established": False,
                                   "per_configuration_response_filter": mode == "empirical_safe",
                                   "causal_synergy_established": False,
                                   "best_pair_witnesses_by_task": best_pairs}
                            row["categories"] = row_categories(row)
                            yield row
                        for k in range(len(tasks)):
                            for g, p in np.argwhere(new_close[:, :, k]):
                                archive[k].add((int(new_after[g]), int(p)))


def selection_key(row, category):
    return (int(row["binary_reactivation"]), row["reactivation_gain"], int(row["pair_D"]),
            row["pair_task_mass_after"], row["pair_competitive_loadouts"], -row["round"])


def select_cases(records):
    chosen = {}
    for category in CATEGORIES:
        candidates = sorted((r for r in records if category in r["categories"]),
                            key=lambda r: selection_key(r, category), reverse=True)
        seen, selected = set(), []
        for row in candidates:
            key = (row["race"], row["headroom"], row["new_item"], row["legacy_item"], row["mode"])
            if key not in seen:
                selected.append(row); seen.add(key)
            if len(selected) == 10:
                break
        chosen[category] = selected
    return chosen


def run(run_directory: Path, out: Path, root: Path):
    start = time.monotonic()
    freeze = json.loads((run_directory / "FROZEN_DESIGN.json").read_text())
    raw = json.loads((run_directory / "RESULTS.json").read_text())
    if raw["errors"] or any(r is None for r in raw["rows"]):
        raise ValueError("Atlas input has incomplete native cells")
    cfg = yaml.safe_load((run_directory / "source/r2_discovery.yaml").read_text())
    tasks, policies = cfg["tasks"], [x["id"] for x in cfg["strategies"]]
    ids = sorted(freeze["gears"])
    data = {race: load_context(raw["rows"], ids, tasks, policies, race, 128) for race in freeze["design"]["races"]}
    lookup = {(r["race"], r["gear_id"], r["strategy"], r["task"]): r for r in raw["rows"]}
    out.mkdir(parents=True, exist_ok=True)
    records = list(atlas_records(freeze, data, ids, tasks, policies))
    fields = [k for k in records[0] if k != "best_pair_witnesses_by_task"]
    with (out / "COMPLEMENTARITY_ATLAS.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in records:
            writer.writerow({k: json.dumps(v, separators=(",", ":"), allow_nan=False)
                             if isinstance(v, (dict, list)) else v for k, v in row.items() if k in fields})
    selected = select_cases(records)
    canonical = [r for r in records if r["new_item"] == 12795 and r["legacy_item"] == 19019
                 and r["sequence"] == "expanded_interleaved_0" and r["headroom"] == .05
                 and r["mode"] == "empirical_safe"]
    selections = [(category, row) for category, rows in selected.items() for row in rows]
    selections += [("mandatory_canonical", row) for row in canonical]
    evidence = []
    for category, row in selections:
        witness = {**row, "selected_category": category,
                   "new_effect": freeze["design"]["item_descriptors"][str(row["new_item"])],
                   "legacy_effect": freeze["design"]["item_descriptors"][str(row["legacy_item"])],
                   "rule_details": {"admission": row["mode"], "power_caps": row["fixed_cap"],
                                    "q8_feature_names": freeze["design"]["rule_feature_order"][:8],
                                    "q8_thresholds": freeze["thresholds"][:8],
                                    "semantic_rule_used_for_actual_admission": False}}
        details = []
        for point in row["best_pair_witnesses_by_task"]:
            if point is None:
                details.append(None); continue
            combat = lookup[row["race"], point["gear_id"], point["policy"], point["task"]]
            key = combat["cache_key"]
            cache = root / "cache/r2-discovery/native" / key[:2] / key
            details.append({**point, "equipment": freeze["gears"][point["gear_id"]],
                            "source_features": freeze["features"][point["gear_id"]],
                            "input_path": str(cache / "input.json"), "raw_output_path": str(cache / "output.json.gz"),
                            "cache_key": key, "output_sha256": combat["output_sha256"],
                            "event_summary": {"actions": combat["actions"], "resources": combat["resources"], "auras": combat["auras"]}})
        witness["task_witness_details"] = details
        evidence.append(witness)
    with (out / "REACTIVATION_WITNESSES.jsonl").open("w") as stream:
        for row in evidence:
            stream.write(json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n")
    summary = {"native_calls": 0, "native_battles": 0, "reused_native_cells": len(raw["rows"]),
               "atlas_rows": len(records), "states_context_headroom_mode": 16 * 20 * 2 * 2,
               "records_with_pair_loadouts": sum(r["pair_raw_loadouts_after"] > 0 for r in records),
               "category_raw_counts": {cat: sum(cat in r["categories"] for r in records) for cat in CATEGORIES},
               "category_selected_counts": {cat: len(rows) for cat, rows in selected.items()},
               "safe_binary_reactivation_rows": sum(r["binary_reactivation"] and r["mode"] == "empirical_safe" for r in records),
               "safe_binary_reactivation_and_D_rows": sum(r["binary_reactivation"] and r["pair_D"] and r["mode"] == "empirical_safe" for r in records),
               "canonical": canonical,
               "analysis_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "safe_positive_unique_item_pairs": len({(r["new_item"], r["legacy_item"]) for r in records
                                                       if r["mode"] == "empirical_safe" and r["reactivation_gain"] > 0}),
               "safe_binary_unique_item_pairs": len({(r["new_item"], r["legacy_item"]) for r in records
                                                     if r["mode"] == "empirical_safe" and r["binary_reactivation"]}),
               "safe_binary_and_D_unique_item_pairs": len({(r["new_item"], r["legacy_item"]) for r in records
                                                           if r["mode"] == "empirical_safe" and r["binary_reactivation"] and r["pair_D"]}),
               "source_hashes": {name: hashlib.sha256((run_directory / name).read_bytes()).hexdigest()
                                 for name in ("FROZEN_DESIGN.json", "RESULTS.json", "PROTOCOL.json")},
               "elapsed_seconds": time.monotonic() - start}
    atomic_json(out / "ATLAS_AUDIT.json", summary)
    lines = ["# Native complementarity atlas", "", f"Reused {len(raw['rows']):,} R2 cells; no new simulation calls.",
             f"{len(records):,} legacy/candidate/state rows across Human and Orc, eight sequences, twenty rounds, two caps and two admission views.",
             "", "Reactivation uses the before and after task optima separately. A cap-filter re-entry is not a causal proc-synergy estimate.",
             "The current safe-set reference reads complete current responses and is not an established reusable rule.", ""]
    for category, chosen in selected.items():
        lines += [f"## {category}", "", f"Selected {len(chosen)} of {summary['category_raw_counts'][category]} state rows; deduplicated by context/cap/item pair.",
                  "", "| New → legacy | Context / cap | State | Before → pair task mass | Gain | Novel | Before status |", "|---|---|---|---:|---:|---|---|"]
        for r in chosen:
            lines.append(f"| {r['new_name']} ({r['new_item']}) → {r['legacy_name']} ({r['legacy_item']}) | {r['race']} / {r['headroom']:.0%} | {r['sequence']}:{r['round']} | {r['legacy_mass_before']:.2f} → {r['pair_task_mass_after']:.2f} | {r['reactivation_gain']:.2f} | {r['pair_D']} | {r['legacy_status_before']} |")
        lines.append("")
    lines += ["## Interpretation limits", "", "The two races share proposals; repeated sequence appearances are not independent replications.",
              "Behavior uses the frozen seven physical mean features. Randomized mixtures and unsearched loadouts are outside the comparison.",
              "Rage flow is gross attempted inflow including refunds; the waste coordinate records capped positive inflow.",
              "Power-neutral means no task-envelope increase versus the preceding state, not merely remaining below a cap.",
              "An empty pair domain is retained in the denominator and is not treated as observed zero performance.",
              "Every selected row links exact equipment, policy, native cached request/output hashes, event summaries and rule state in REACTIVATION_WITNESSES.jsonl.", ""]
    (out / "COMPLEMENTARITY_SUMMARY.md").write_text("\n".join(lines))
    print(json.dumps({k: v for k, v in summary.items() if k not in ("canonical", "source_hashes")}))
    return records, selected, summary


def main():
    root = setup_paths()
    p = argparse.ArgumentParser()
    p.add_argument("--run", type=Path, default=root / "runs/r2-discovery/unseen-v1")
    p.add_argument("--out", type=Path, default=root / "artifacts/r3-gold")
    args = p.parse_args()
    run(args.run, args.out, root)


if __name__ == "__main__":
    main()
