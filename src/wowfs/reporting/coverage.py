"""Verified targets and explicit missing native results, never synthetic coverage.

The JSON-compatible YAML configuration needs only the Python standard library.
This initial report intentionally records no native simulator execution. Real
execution ingestion must validate engine, protocol, trajectory, and context IDs
before replacing any of these missing-result records.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path

METHODS = (
    "unrestricted", "frozen_prices", "compatible_repricing",
    "generic_multi_budget", "proposed",
)
METHOD_LABELS = (
    "Unrestricted", "Frozen prices", "Compatible repricing",
    "Generic multi-budget", "Proposed",
)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def load_contexts(source_root: Path) -> list[dict]:
    """Expand and validate the externally verified 28 + 28 target matrix."""
    config = json.loads((source_root / "configs/official_contexts.yaml").read_text())
    rows = []
    for faction, races in config["factions"].items():
        for race in races:
            for character_class in race["classes"]:
                rows.append({
                    "context_id": "__".join(map(_slug, (faction, race["race"], character_class))),
                    "faction": faction,
                    "race": race["race"],
                    "class": character_class,
                    "role_target": "pve_damage",
                    "spec": "not_selected",
                    "required": 1,
                    "legality_status": config["verification"]["status"],
                    "source_url": config["verification"]["url"],
                    "implemented": 0,
                    "executed": 0,
                    "trajectory_count": 0,
                    "status": "not_run",
                    "reason": "native_forever_engine_unavailable",
                })
    counts = Counter(row["faction"] for row in rows)
    expected = config["expected_counts"]
    if len(rows) != expected["total"] or len({r["context_id"] for r in rows}) != len(rows):
        raise ValueError("Official context total or uniqueness check failed")
    if counts != Counter({faction: expected[faction] for faction in config["factions"]}):
        raise ValueError("Official per-faction context counts differ from target")
    if {r["class"] for r in rows} != set(config["classes"]) or len(config["classes"]) != 9:
        raise ValueError("Official class coverage check failed")
    return rows


def _csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_coverage(source_root: Path, output_dir: Path) -> dict:
    """Write honest native-only coverage and not-run faction summary tables."""
    source_root, output_dir = Path(source_root), Path(output_dir)
    if output_dir.resolve().is_relative_to(source_root.resolve()):
        raise ValueError("Generated coverage belongs outside the source repository")
    output_dir.mkdir(parents=True, exist_ok=True)
    contexts = load_contexts(source_root)
    _csv(output_dir / "COVERAGE.csv", contexts)
    config = json.loads((source_root / "configs/official_contexts.yaml").read_text())
    empty_metrics = {
        "s20_mean": "not_run", "s20_ci_lower": "not_run", "s20_ci_upper": "not_run",
        "pass20": "not_run", "pass20_numerator": "not_run", "pass20_denominator": 0,
        "new_item_useful_fraction": "not_run", "legacy_source_retained_fraction": "not_run",
        "worst_source_task_weight": "not_run", "k20": "not_run", "k20_denominator": 0,
        "max_k": "not_run", "max_power_excess": "not_run", "delta_s20_vs_repricing": "not_run",
        "engine_hash": "unavailable", "protocol_hash": "not_frozen", "data_split": "not_run",
        "status": "not_run", "reason": "native_forever_engine_unavailable",
    }
    faction_rows, class_rows, sweep_rows = [], [], []
    for method in METHODS:
        for faction in config["factions"]:
            faction_rows.append({
                "method": method, "faction": faction, "deployment": "context-adapted",
                "required_classes": 9, "completed_classes": 0, "required_contexts": 28,
                "executed_contexts": 0, "target_trajectories": 180, "executed_trajectories": 0,
                "aggregation": "equal_race_then_equal_class", **empty_metrics,
            })
            for character_class in config["classes"]:
                n_race = sum(c["faction"] == faction and c["class"] == character_class for c in contexts)
                class_rows.append({
                    "method": method, "faction": faction, "class": character_class,
                    "deployment": "context-adapted", "required_races": n_race,
                    "executed_races": 0, "target_trajectories": 20, "executed_trajectories": 0,
                    **empty_metrics,
                })
        for context in contexts:
            sweep_rows.append({
                "context_id": context["context_id"], "faction": context["faction"],
                "race": context["race"], "class": context["class"], "method": method,
                "deployment": "context-adapted", "checkpoint_round": 20,
                "executed_trajectories": 0, **empty_metrics,
            })
    _csv(output_dir / "FACTION_SUMMARY.csv", faction_rows)
    _csv(output_dir / "CLASS_FACTION_SUMMARY.csv", class_rows)
    _csv(output_dir / "RACE_CLASS_SWEEP.csv", sweep_rows)
    table = [
        "# Faction-context robustness of sustainable equipment expansion", "",
        "Native Forever only; context-adapted deployment. Each method requires 360 trajectories,",
        "with 20 updates per trajectory. None has run. S20 is a finite-horizon success prefix,",
        "not oracle capacity. Counts refer to the verified legality targets.", "",
        "| Mechanism | Alliance S20 | Alliance Pass20 | Alliance New/Legacy | Alliance K20 | Horde S20 | Horde Pass20 | Horde New/Legacy | Horde K20 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    table += [f"| {label} | not run | not run (0 evaluated) | not run | not run | not run | not run (0 evaluated) | not run | not run |" for label in METHOD_LABELS]
    table += ["", "Coverage: Alliance 0/28, Horde 0/28, classes 0/9. A missing result is neither a failed trajectory nor a zero score.", "",
              "Aggregation, once data exist, averages matched sequences within race, then races equally within class, then all nine classes equally.",
              "No available subset is silently substituted for the full result; sequence clusters must be retained for uncertainty estimates.", ""]
    (output_dir / "FACTION_SUMMARY.md").write_text("\n".join(table))
    return {"required_contexts": len(contexts), "Alliance": 28, "Horde": 28,
            "required_classes": 9, "implemented": 0, "executed": 0,
            "status": "not_run", "output_dir": str(output_dir)}
