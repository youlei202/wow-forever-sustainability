#!/usr/bin/env python3
"""Read-only independent review of saved minimal-interface native analyses."""
from collections import Counter
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def review(root, output):
    native = root / "native"
    inputs = sorted((native / "contracts").glob("*.json"))
    before = {str(p): sha(p) for p in inputs}
    checks, observations = [], []
    scopes_checked = minimal_checked = 0
    for path in inputs:
        record = json.loads(path.read_text())
        states = np.asarray(record["statuses"])
        exact = np.asarray(record["exact_query_statuses"])
        masks = np.arange(len(states))
        orders = np.asarray([int(m).bit_count() for m in masks])
        rows = []
        # Explicitly mark supersets of every observed low-order bad subset.
        # This does not call the production subset-minimum transform.
        for r in (1, 2, 3):
            has_no = np.zeros(len(states), dtype=bool)
            has_unknown = np.zeros(len(states), dtype=bool)
            has_exact_no = np.zeros(len(states), dtype=bool)
            for subset in masks[orders <= r]:
                containing = (masks & subset) == subset
                if states[subset] == "NO":
                    has_no |= containing
                elif states[subset] != "YES":
                    has_unknown |= containing
                if exact[subset] == "NO":
                    has_exact_no |= containing
            row = {"order_r": r,
                   "certified_false_positive_count": int(np.count_nonzero((states == "NO") & ~has_no & ~has_unknown)),
                   "unknown_blocked_cases": int(np.count_nonzero((states == "NO") & ~has_no & has_unknown)),
                   "unresolved_full_targets_with_no_low_order_NO": int(np.count_nonzero((states == "UNKNOWN") & ~has_no)),
                   "exact_false_positive_count": int(np.count_nonzero((exact == "NO") & ~has_exact_no)) if record["exact_initial_valid"] else None}
            saved = next(x for x in record["low_order"] if x["order_r"] == r)
            assert all(saved[k] == v for k, v in row.items()), (path, row, saved)
            rows.append(row)
        certified_masks = []
        exact_masks = []
        for d in masks:
            proper = masks[((masks & d) == masks) & (masks != d)]
            if states[d] == "NO" and np.all(states[proper] == "YES"):
                certified_masks.append(int(d))
            if exact[d] == "NO" and np.all(exact[proper] == "YES"):
                exact_masks.append(int(d))
        obs = record["minimal_obstructions"]
        assert certified_masks == sorted(o["target_mask"] for o in obs if o["evidence"] == "CERTIFIED NATIVE NO")
        assert exact_masks == sorted(o["target_mask"] for o in obs if o["evidence"] == "EXACT FINITE-TABLE RESULT")
        minimal_checked += len(certified_masks) + len(exact_masks)
        names, history = record["items"], record["replay_certificate"]["history_mask"]
        for obstruction in obs:
            if obstruction["evidence"] != "CERTIFIED NATIVE NO":
                continue
            target = sum(1 << names.index(x) for x in obstruction["target"])
            selected = [p for p in record["publication_exclusion_table"] if p["publication"] & target == target]
            for scope, saved in obstruction["attribution"]["scopes"].items():
                accepts = {}
                for mode in ("supported", "possible"):
                    valid = []
                    for p in selected:
                        sources = p["publication"]
                        groups = {"history": history, "targets": target, "helpers": sources & ~(history | target)}
                        required = (sources if scope in ("all", "drop_cap") else 0 if scope == "none" else
                                    groups[scope.removeprefix("only_")] if scope.startswith("only_") else
                                    sources & ~groups[scope.removeprefix("drop_")])
                        mode_data = p["modes"][mode]
                        if (scope == "drop_cap" or not mode_data["cap_failed"]) and mode_data["gain_satisfied"] and not (required & mode_data["failed_sources"]):
                            valid.append(sources)
                    accepts[mode] = bool(valid)
                    assert len(valid) == saved["exhaustive_counts"][mode].get("valid", 0)
                status = "YES" if accepts["supported"] else "UNKNOWN" if accepts["possible"] else "NO"
                assert status == saved["status"], (path, obstruction["target"], scope)
                scopes_checked += 1
            if obstruction["order"] == 3 or (record["stratum"] == "primary_base" and obstruction["order"] == 0):
                observations.append({"contract_id": record["contract_id"], "stratum": record["stratum"],
                    "target": obstruction["target"], "order": obstruction["order"],
                    "attribution": obstruction["attribution"]["labels"],
                    "scope_statuses": {k: v["status"] for k, v in obstruction["attribution"]["scopes"].items()}})
        checks.append({"contract_id": record["contract_id"], "stratum": record["stratum"], "queries": len(states),
                       "query_statuses": dict(Counter(states.tolist())), "low_order_independent": rows,
                       "certified_minimal_obstructions": certified_masks, "exact_minimal_obstructions": exact_masks})
    # Independent scalar-moment B3 evaluator supplies all 1,024 publications.
    druid = json.loads((root / "druid/PUBLICATIONS_e0.010.json").read_text())
    druid_native = json.loads((native / "contracts/co_druid_passive_resources__validation_02__base.json").read_text())
    for mask, original in enumerate(druid_native["statuses"]):
        target = {x for i, x in enumerate(druid_native["target_universe"]) if mask >> i & 1}
        possible = [r for r in druid if target <= set(r["items"])]
        answer = "YES" if any(r["supported"]["valid"] for r in possible) else "UNKNOWN" if any(r["possible"]["valid"] for r in possible) else "NO"
        assert answer == original
    assert before == {str(p): sha(p) for p in inputs}, "Review modified a frozen checkpoint"
    result = {"status": "PASS", "finished_utc": datetime.now(timezone.utc).isoformat(),
        "read_only": True, "native_checkpoint_hashes_unchanged": True,
        "source_sha256": sha(__file__), "native_method_source_sha256": sha(Path(__file__).parents[1] / "src/wowfs/experiments/mi_native.py"),
        "contract_input_sha256": before, "contracts": len(checks), "target_queries": sum(c["queries"] for c in checks),
        "checks": checks, "attribution_scopes_independently_replayed": scopes_checked,
        "all_proper_subset_minimality_checks": minimal_checked,
        "independent_druid_complete_query_comparison": {"queries": 1024, "mismatches": 0},
        "empty_and_order_three_observations": observations,
        "findings": [],
        "interpretation_guards": [
            "Exact mean-table NO is distinct from population certified NO; the 16 base r=2 counts are 9 exact and 3 certified.",
            "Three primary r=2 misses comprise two minimal triples and their union, not three independent triples.",
            "The two primary empty obstructions mean no gaining publication, with vacuous proper-subset minimality; they are not higher-order target interaction.",
            "UNKNOWN-blocked counts are full NO targets lacking low-order NO but containing low-order UNKNOWN; full UNKNOWN targets are separately counted.",
            "Only-group NO plus value-only YES proves a sufficient obstruction group; dropped-group YES proves that group is necessary to the full obstruction for this contract. Neither is a unique causal decomposition.",
            "The 10 new triple rows at 2% are post-hoc frozen-event consequences in three already registered menus; the secondary total 12 also repeats two base Druid triples at multiplier1.",
            "No helper or mixed label is observed in this certification rule; absence of a label does not prove absence of all helper/mixed mechanisms.",
            "E=I minus H makes the projection injective on full publications containing H; byte savings from dropping H do not constitute structural antichain compression.",
            "Inference remains approximate fixed-N simultaneous paired Student-t, not distribution-free or game-wide prevalence."
        ]}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "contracts": len(checks), "target_queries": result["target_queries"], "attribution_scopes": scopes_checked}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    review(args.root, args.output)
