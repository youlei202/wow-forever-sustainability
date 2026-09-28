"""Frozen callback ablations on complete selected R4 release subdomains.

Each mask is a physical intervention, not a gear-identity change.  A bit set
means the corresponding new item's callback is enabled when it is equipped.
Old and singleton configurations retain their identities in every logical
world; canonicalizing absent disabled IDs avoids rerunning identical battles.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import itertools
import json
from pathlib import Path
import shutil

import yaml

from wowfs.paths import SOURCE_ROOT, setup_paths, atomic_json, canonical_hash
from wowfs.experiments.r2_native import file_hash
from wowfs.experiments.r4_native import make_input, run_jobs


SELECTIONS = {
    "resource_haste": (18203, 19951),
    "timing_shared": (18203, 19019),
    "timing_extra": (18203, 19951),
}
SEED = 409260001
ITERATIONS = 256
RUN_ID = "causal-pairs-v1"


def disabled_effects(gear, effects, mask):
    """Only disable equipped effects; item identities and every stat stay fixed."""
    if mask not in range(1 << len(effects)):
        raise ValueError("invalid factorial mask")
    equipped = set(gear.values())
    return sorted(item for bit, item in enumerate(effects)
                  if item in equipped and not mask & (1 << bit))


def select_domain(base):
    """Restrict an archived full domain without reading any new outcome."""
    out = deepcopy(base)
    out["ecosystems"] = []
    retained = set()
    for pool in base["ecosystems"]:
        if pool["id"] not in SELECTIONS:
            continue
        selected = set(SELECTIONS[pool["id"]])
        forbidden = set(pool["new_source_ids"]) - selected
        record = deepcopy(pool)
        record["terminal_gear_ids"] = [key for key in pool["terminal_gear_ids"]
            if not forbidden.intersection(pool["source_ids_by_gear"][key])]
        assert len(record["initial_gear_ids"]) == 16
        assert len(record["terminal_gear_ids"]) == 36
        assert all(not selected.intersection(base["gears"][key]["gear"].values())
                   for key in record["initial_gear_ids"])
        record["slots"] = {slot: values[:2] + [v for v in values[2:] if v in selected]
                           for slot, values in pool["slots"].items()}
        record["new_source_ids"] = sorted(selected)
        record["source_ids_by_gear"] = {key: pool["source_ids_by_gear"][key]
                                       for key in record["terminal_gear_ids"]}
        record["raw_terminal_count"] = record["legal_terminal_count"] = 36
        retained.update(record["terminal_gear_ids"])
        out["ecosystems"].append(record)
    assert len(out["ecosystems"]) == len(SELECTIONS)
    out["gears"] = {key: deepcopy(base["gears"][key]) for key in sorted(retained)}
    out["candidate_design_families"] = []
    return out


def protocol(base, cfg):
    return {
        "stage": "new-seed callback interventions on discovery-selected complete finite domains",
        "selections": {key: list(value) for key, value in SELECTIONS.items()},
        "seed_start": SEED, "iterations": ITERATIONS,
        "factorial": "bit0=18203 callback enabled; bit1=other selected item callback enabled; stats/speed/identity/set membership fixed",
        "effects": {
            "18203": "Remove Eskhandar 1 PPM proc giving 10% attack speed for 6 seconds.",
            "19951": "Remove Gri'lek 30-rage active, 3-minute cooldown; retain Vindicator set membership and bonuses.",
            "19019": "Remove whole Thunderfury callback: Nature hit and attack-speed slow. Native intended resistance debuff is a no-op; this is not a pure damage-amplitude intervention.",
        },
        "hypotheses": [
            {"pool": "resource_haste", "selection": "16-seed discovery, then failed fixed-cap 512-seed confirmation",
             "test": "Does haste/rage effect interaction produce reward or D beyond static compensation? A positive interaction is not assumed; fixed-cap failure remains a failure."},
            {"pool": "timing_shared", "selection": "16-seed discovery; Orc pair survived fixed-cap 512-seed confirmation",
             "test": "Does joint novelty rely on haste feedback plus Thunderfury, or is a weak physical mainhand compensating for a Nature channel? Separate statistical interaction from pair qualification."},
            {"pool": "timing_extra", "selection": "Added after independent 512-seed confirmation unexpectedly found Orc 18203+19951 qualified",
             "test": "Does the rage active create D by itself once equipped on the weaker mainhand, or is the Eskhandar haste callback necessary? This is a selected replication, not a pre-confirmation prediction."},
        ],
        "primary_estimands": "Per-gear/task/policy/race paired DPS double difference Y11-Y10-Y01+Y00; finite admission P,N,D,L,C,H recomputed by mask.",
        "inference": "Bonferroni paired Student-t approximate intervals over all selected pool/gear/task/policy/race factorials. Behavior summaries are empirical means, with no seed-level D confidence claim.",
        "anchor": "Frozen baseline-v1 numeric cap, scale, and initial useful-item registry. Each intervention uses the same fresh unaffected old16 behavior reference. No silent cap reanchoring.",
        "interpretation": "Factorial interaction is an effect contrast conditional on fixed gear; minimum batch feasibility can instead arise through static compensation or conjunctive requirements. Native community engine, not live-server validation.",
        "base_domain_sha256": canonical_hash(base), "configuration": cfg,
        "driver_sha256": file_hash(Path(__file__)),
    }


def prepare():
    root = setup_paths()
    baseline = root / "runs/r4-foundational-discovery/baseline-v1"
    base = json.loads((baseline / "BASE_ECOSYSTEMS.json").read_text())
    cfg = yaml.safe_load((baseline / "source/configs/r4_ecosystems.yaml").read_text())
    selected = select_domain(base)
    cfg["pools"] = [{key: value for key, value in pool.items()
                     if key in {"id", "background", "slots", "fixed", "rationale"}}
                    for pool in selected["ecosystems"]]
    cfg["candidate_design_families"] = []
    cfg["sampling"].update(iterations=ITERATIONS, seed_start=SEED)
    jobs = []
    for pool in selected["ecosystems"]:
        effects = SELECTIONS[pool["id"]]
        for gear_id, task, strategy, race, mask in itertools.product(
                pool["terminal_gear_ids"], selected["tasks"], selected["strategies"],
                selected["races"], range(4)):
            gear = selected["gears"][gear_id]["gear"]
            disabled = disabled_effects(gear, effects, mask)
            value = make_input(gear, task, strategy, race, SEED, ITERATIONS,
                               cfg, disabled=[{"item_id": item} for item in disabled])
            jobs.append({"input": value, "meta": {
                "pool": pool["id"], "pools": [pool["id"]], "gear_id": gear_id,
                "race": race, "task": task["id"], "strategy": strategy["id"],
                "mask": mask, "effect_ids": list(effects), "disabled_effects": disabled,
                "world": "callback_factorial", "stage": "selected_pair_causal"}})
    return jobs, selected, protocol(base, cfg)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=32)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--freeze-only", action="store_true")
    args = parser.parse_args()
    jobs, domain, science = prepare()
    root = setup_paths()
    run = root / "runs/r4-foundational-discovery" / RUN_ID
    run.mkdir(parents=True, exist_ok=True)
    freeze = run / "CAUSAL_HYPOTHESES.json"
    if freeze.exists() and json.loads(freeze.read_text()) != science:
        raise ValueError("Frozen causal protocol changed")
    atomic_json(freeze, science)
    atomic_json(run / "BASE_ECOSYSTEMS.json", domain)
    (run / "source").mkdir(exist_ok=True)
    shutil.copy2(Path(__file__), run / "source" / Path(__file__).name)
    unique = len({canonical_hash(job["input"]) for job in jobs})
    print(json.dumps({"logical_cells": len(jobs), "unique_cells": unique,
                      "maximum_new_battles": unique * ITERATIONS}), flush=True)
    if args.freeze_only:
        return
    result = run_jobs(jobs, RUN_ID, scientific_protocol=science,
                      workers=args.workers, resume=args.resume)
    print(result, flush=True)


if __name__ == "__main__":
    main()
