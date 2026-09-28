#!/usr/bin/env python3
"""Synthetic final-pool interaction identification and independent model challenge.

This is not a native simulator or an online/joint-sustainability experiment.
Three methods compare identical physical training budgets: shared coefficients,
the identical generic-feature model (cache-reused measurements), and separate
configuration contrasts. A hidden legal interaction stress falsifies the shared
model. Holdout intervals may be unresolved at an exact cap and are never called
certificates of safety merely because no violation is detected.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np

from verify_theory import Instance


@dataclass(frozen=True)
class Protocol:
    repeats: int = 128
    budgets: tuple[int, ...] = (256, 1024, 4096, 16384)
    seed: int = 270924
    noise_halfwidth: float = 0.1
    holdout_per_configuration: int = 512
    error_budget: float = 0.05
    hidden_legal_bonus: float = 0.08


def true_utilities(model: Instance, z: tuple[int, int], scenario: str,
                   protocol: Protocol) -> np.ndarray:
    mean = np.array([float(x) for x in model.utility(z)])
    if scenario == "hidden_legal_interaction" and z == (model.rounds, model.channel(model.rounds)):
        mean[0] += protocol.hidden_legal_bonus
    return mean


def holdout(model: Instance, scenario: str, protocol: Protocol, replicate: int) -> dict:
    legal = tuple(z for z in model.configs(model.rounds) if model.allowed(z))
    rng = np.random.default_rng(np.random.SeedSequence([protocol.seed, replicate, 991]))
    truth = np.stack([true_utilities(model, z, scenario, protocol) for z in legal])
    noise = rng.uniform(-protocol.noise_halfwidth, protocol.noise_halfwidth,
                        size=(len(legal), protocol.holdout_per_configuration, 2))
    observed = truth + noise.mean(axis=1)
    # One physical synthetic trial supplies both endpoint observations.
    coordinates = len(legal) * 2
    holdout_eta = protocol.error_budget / 2
    radius = 2 * protocol.noise_halfwidth * math.sqrt(
        math.log(2 * coordinates / holdout_eta) / (2 * protocol.holdout_per_configuration))
    if np.any(observed - radius > float(model.cap)):
        state = "violation"
    elif np.all(observed + radius <= float(model.cap)):
        state = "pass"
    else:
        state = "unresolved"
    return {"holdout_status": state, "holdout_radius": radius,
            "holdout_physical_simulations": len(legal) * protocol.holdout_per_configuration,
            "truth_max_legal_excess": float(np.max(truth - float(model.cap))),
            "holdout_max_lower_excess": float(np.max(observed - radius - float(model.cap))),
            "holdout_max_upper_excess": float(np.max(observed + radius - float(model.cap)))}


def estimate_contrasts(model: Instance, scenario: str, protocol: Protocol,
                       replicate: int, budget: int, shared: bool) -> dict:
    if budget < 4 or budget % 2:
        raise ValueError("Physical budgets must be positive even integers >= 4")
    probes = (0, 1) if shared else tuple(range(model.rounds + 1))
    if budget // 2 < len(probes):
        raise ValueError("Need at least one paired contrast per probe")
    pairs, remainder = divmod(budget // 2, len(probes))
    rng = np.random.default_rng(np.random.SeedSequence(
        [protocol.seed, replicate, budget, int(shared), 123]))
    train_eta = protocol.error_budget / (2 * len(protocol.budgets) * 2)
    means, radii, counts = {}, {}, {}
    for index, left in enumerate(probes):
        n = pairs + int(index < remainder)
        channel = model.channel(left)
        assert channel is not None
        matched, crossed = (left, channel), (left, 1 - channel)
        matched_mean = true_utilities(model, matched, scenario, protocol)[0]
        crossed_mean = true_utilities(model, crossed, scenario, protocol)[0]
        noise = rng.uniform(-protocol.noise_halfwidth, protocol.noise_halfwidth, size=(n, 2))
        differences = crossed_mean - matched_mean + noise[:, 0] - noise[:, 1]
        key = channel if shared else left
        means[key] = float(differences.mean())
        # A contrast of two independent uniforms of width 2*sigma has width 4*sigma.
        radii[key] = 4 * protocol.noise_halfwidth * math.sqrt(
            math.log(2 * len(probes) / train_eta) / (2 * n))
        counts[key] = n
    certified, false_certified = 0, 0
    for left in range(model.rounds + 1):
        key = model.channel(left) if shared else left
        lower_power = 1 + float(model.q(left)) + means[key] - radii[key]
        if lower_power > float(model.cap):
            certified += 1
            crossed = (left, 1 - model.channel(left))
            if true_utilities(model, crossed, scenario, protocol)[0] <= float(model.cap):
                false_certified += 1
    return {"hazards_certified": certified, "hazards_total": model.rounds + 1,
            "all_hazards_certified": certified == model.rounds + 1,
            "false_hazard_certifications": false_certified,
            "training_physical_simulations": 2 * sum(counts.values()),
            "n_identifiable_parameters_assumed": len(probes),
            "maximum_coefficient_radius": max(radii.values()),
            "minimum_coefficient_radius": min(radii.values()),
            "hazard_status": "pass" if certified == model.rounds + 1 else "unresolved"}


def run(protocol: Protocol = Protocol()) -> tuple[list[dict], list[dict], dict]:
    if protocol.repeats < 1 or protocol.holdout_per_configuration < 1:
        raise ValueError("Positive repeats and holdout sizes required")
    if not 0 < protocol.error_budget < 1 or protocol.noise_halfwidth <= 0:
        raise ValueError("Require error probability in (0,1) and positive bounded noise")
    model = Instance()
    rows = []
    physical_total = 0
    for scenario in ("correct_model", "hidden_legal_interaction"):
        for replicate in range(protocol.repeats):
            challenge = holdout(model, scenario, protocol, replicate)
            physical_total += challenge["holdout_physical_simulations"]
            for budget in protocol.budgets:
                shared_result = estimate_contrasts(model, scenario, protocol, replicate, budget, True)
                separate_result = estimate_contrasts(model, scenario, protocol, replicate, budget, False)
                physical_total += (shared_result["training_physical_simulations"] +
                                   separate_result["training_physical_simulations"])
                for name, result, new_physical, cached in (
                    ("shared_channel_coefficients", shared_result, budget, 0),
                    ("generic_same_features", shared_result, 0, budget),
                    ("separate_configuration_contrasts", separate_result, budget, 0),
                ):
                    assumed_safe = result["all_hazards_certified"]
                    rows.append({
                        "evidence_scope": "abstract_synthetic_final_pool",
                        "scenario": scenario, "replicate": replicate, "method": name,
                        "training_budget": budget, **result, **challenge,
                        "new_training_physical_simulations": new_physical,
                        "shared_training_cache_observations": cached,
                        "model_implied_power_claim": assumed_safe,
                        "false_model_implied_power_claim": assumed_safe and challenge["truth_max_legal_excess"] > 1e-12,
                        "holdout_veto": assumed_safe and challenge["holdout_status"] == "violation",
                    })
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["scenario"], row["method"], row["training_budget"]].append(row)
    summary = []
    for (scenario, method, budget), values in sorted(grouped.items()):
        n = len(values)
        cert = sum(int(x["all_hazards_certified"]) for x in values)
        false = sum(int(x["false_model_implied_power_claim"]) for x in values)
        summary.append({
            "scenario": scenario, "method": method, "training_budget": budget,
            "replicates": n, "all_hazards_certified_count": cert,
            "all_hazards_certified_rate": cert / n,
            "mean_hazards_certified": sum(x["hazards_certified"] for x in values) / n,
            "false_model_implied_power_claim_count": false,
            "holdout_violation_count": sum(x["holdout_status"] == "violation" for x in values),
            "holdout_unresolved_count": sum(x["holdout_status"] == "unresolved" for x in values),
            "holdout_pass_count": sum(x["holdout_status"] == "pass" for x in values),
            "holdout_veto_count": sum(x["holdout_veto"] for x in values),
            "false_hazard_certifications": sum(x["false_hazard_certifications"] for x in values),
            "holdout_physical_per_replicate": values[0]["holdout_physical_simulations"],
        })
    manifest = {
        "evidence_scope": "abstract_synthetic_final_pool",
        "protocol": asdict(protocol), "native_simulations": 0,
        "physical_synthetic_simulations_generated": physical_total,
        "independent_holdout_per_replication_shared_across_methods": True,
        "generic_same_features_reuses_shared_measurements_and_must_tie": True,
        "training_probe_observation": "two independent physical draws per matched/mismatched contrast",
        "holdout_observation": "one physical draw returns both task endpoints",
        "decision_target": "complete certification of hazardous crossed pairings; not joint P/N/D/L/H/C success",
        "model_claim_warning": "Model-implied safety is conditional on completeness of the channel feature model; hidden interaction deliberately violates it",
        "validation_warning": "No detected holdout violation does not certify safety; exact-cap values generally remain unresolved",
        "error_allocation": "Per replication/scenario: half error budget for independent holdout, half divided across two distinct estimators and all fixed budgets",
    }
    return rows, summary, manifest


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--repeats", type=int, default=128)
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1]
    work = Path(os.environ.get("WOWFS_WORK_ROOT",
                              source.parent.parent / "wow-forever-sustainability-work"))
    output = (args.output_dir or work / "data/theory/finite_data").resolve()
    if output.is_relative_to(source):
        parser.error("Generated outputs must be outside the source repository")
    rows, summary, manifest = run(Protocol(repeats=args.repeats))
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "FINITE_DATA_TRIALS.csv", rows)
    write_csv(output / "FINITE_DATA_SUMMARY.csv", summary)
    manifest["source_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    manifest["theory_source_sha256"] = hashlib.sha256((Path(__file__).parent / "verify_theory.py").read_bytes()).hexdigest()
    manifest["output_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in (output / "FINITE_DATA_TRIALS.csv", output / "FINITE_DATA_SUMMARY.csv")}
    (output / "FINITE_DATA_PROTOCOL.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output_directory": str(output), "trial_rows": len(rows),
                      "summary_rows": len(summary), "physical_synthetic_simulations": manifest["physical_synthetic_simulations_generated"]}))


if __name__ == "__main__":
    main()
