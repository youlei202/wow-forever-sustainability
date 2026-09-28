"""Source/configuration/task incidence and competing-frontier diagnostics.

Sources may share configurations and tasks. No matching or exclusive-niche
assumption is used. Deletion diagnostics keep admission fixed and reoptimize.
"""
from __future__ import annotations

from itertools import combinations
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import numpy as np

from wowfs.experiments.r4_feasibility import FiniteProblem, evaluate_admission, eval_all_safe, solve_subset, frontier_closure
from wowfs.experiments.r2_sequence_analysis import write_csv
from wowfs.paths import atomic_json, canonical_hash, setup_paths


STUDY_POOLS = ("static_skill", "static_accuracy", "timing_extra", "timing_shared",
               "resource_set_pair", "resource_cost", "target_damage", "target_armor")
STUDY_DESIGN = {
    "schema": 1, "pools": STUDY_POOLS,
    "selection": "two source-defined pools from each of four backgrounds, fixed before baseline responses",
    "release_actions": "every singleton new item, plus one batch containing all pool new items",
    "comparison_unit": "ecology; race and release actions are shared-table context diagnostics, not independent samples",
    "C": "full mixing versus four parity-balanced old-item templates per singleton new source; protected old16 untouched; all legacy columns retained",
    "restricted_templates": "exactly one new item per configuration; the other3 old binary slot choices have even parity (000,011,101,110)",
    "E": "all cap-safe configurations versus jointly optimized arbitrary subset, scalar, generic2 and generic4 nonnegative item-incidence budgets",
    "information": "same complete current physical table and old archive; no future release outcomes or source labels privileged",
    "objective": "maximize admitted gear count subject to P,N,D,L,H,C; arbitrary subset diagnostic is not a source-feature method",
    "price_domain": [0, 100], "strict_rejection_margin": 1e-6,
    "screen_solver_seconds_per_method": 2., "timeouts": "unresolved, never infeasible; selected cases may receive a separately recorded longer solve",
    "Gamma": "R3 epsilon/delta/minmass=.05, K4,coverage.95; R4 fixed8 tasks equalweight and own initial16 caps at1.05",
    "population_mean_inference": "not provided by exhaustive finite empirical comparisons",
}


def source_diagnostics(problem: FiniteProblem, admitted):
    p = problem; admitted = np.asarray(admitted, bool)
    optimum = p.best[admitted].max(axis=0)
    close = (p.best >= optimum - p.tol_vector - p.tolerance) & admitted[:, None]
    source_ids = sorted(set.union(set(), *(set(ss) for ss in p.sources)))
    rows, qualified = [], {}
    for source in source_ids:
        contains = np.array([source in ss for ss in p.sources])
        useful = close & contains[:, None]; qualified[source] = useful
        remains = admitted & ~contains
        without = p.best[remains].max(axis=0) if np.any(remains) else None
        rows.append({"source": source, "protected_source": source in p.protected_sources,
            "new_source": source in p.new_sources,
            "admitted_gears": int(np.sum(admitted & contains)),
            "competitive_gears": int(np.sum(np.any(useful, axis=1))),
            "competitive_task_mass": float(p.weights @ np.any(useful, axis=0)),
            "competitive_tasks": np.flatnonzero(np.any(useful, axis=0)).tolist(),
            "source_deletion_optimum": without.tolist() if without is not None else None,
            "source_deletion_raw_loss": (optimum - without).tolist() if without is not None else None,
            "source_deletion_normalized_loss": ((optimum - without) / p.scale).tolist() if without is not None else None,
            "deletion_scope": "same admitted configurations except source-containing gear removed; policies reoptimized; no repricing"})
    pairs = []
    for a, b in combinations(source_ids, 2):
        qa, qb = qualified[a], qualified[b]
        ta, tb = np.any(qa, axis=0), np.any(qb, axis=0)
        pairs.append({"source_a": a, "source_b": b,
            "shared_competitive_config_task_pairs": int(np.sum(qa & qb)),
            "shared_competitive_task_mass": float(p.weights @ (ta & tb)),
            "either_competitive_task_mass": float(p.weights @ (ta | tb)),
            "interpretation": "shared supports, not exclusive demand assignments or causal synergy"})
    return {"sources": rows, "overlap": pairs}


def necessary_exclusions(problem: FiniteProblem):
    """Exact per-source deletion minimum in the one-task-suffices regime.

    The simultaneous-source maximum is only a lower bound. A source witness on
    a task forces exclusion of every optional gear that would outpace it by
    more than epsilon. Protected blockers make that task impossible. Multiple
    sources can share the same witness; different sources' blocker unions need
    not equal the maximum or sum of their individual minima.
    """
    p = problem
    if np.any((p.weights > 0) & (p.weights < p.min_mass - p.tolerance)):
        return {"status": "not_applicable_multi_task_mass_required", "sources": []}
    old_frontier = p.best[p.protected].max(axis=0)
    selectable = p.safe & ~p.protected
    records = []
    for source in p.protected_sources:
        source_gears = np.array([source in ss for ss in p.sources]) & p.safe
        candidates = []
        for k in range(p.best.shape[1]):
            if p.weights[k] < p.min_mass - p.tolerance or not np.any(source_gears):
                continue
            source_best = float(p.best[source_gears, k].max())
            ceiling = source_best + p.tol_vector[k]
            if old_frontier[k] > ceiling + p.tolerance:
                continue
            blockers = selectable & (p.best[:, k] > ceiling + p.tolerance)
            witness = int(np.flatnonzero(source_gears & (p.best[:, k] == source_best))[0])
            candidates.append({"task": k, "source_witness_gear": witness,
                "source_value": source_best, "retention_frontier_ceiling": float(ceiling),
                "mandatory_excluded_gears": np.flatnonzero(blockers).tolist(),
                "mandatory_exclusion_count": int(np.sum(blockers))})
        best = min(candidates, key=lambda r: (r["mandatory_exclusion_count"], r["task"])) if candidates else None
        records.append({"source": source, "any_retention_possible": best is not None,
            "minimum_exclusions_for_this_source": best["mandatory_exclusion_count"] if best else None,
            "best_witness": best, "all_task_witnesses": candidates})
    impossible = any(not r["any_retention_possible"] for r in records)
    return {"status": "exact_individual_source_minima", "sources": records,
        "joint_retention_impossible_from_source_obstruction": impossible,
        "joint_exclusion_lower_bound": None if impossible else max((r["minimum_exclusions_for_this_source"] for r in records), default=0),
        "bound_scope": "individual source exact; joint maximum lower bound ignores other sources, N, D and C"}


def compare_closure_and_subset(problem: FiniteProblem, time_limit=30.):
    full = eval_all_safe(problem)
    subset = solve_subset(problem, time_limit=time_limit)
    result = {"all_safe": full, "subset": subset,
        "strict_joint_feasibility_separation": bool(not full["joint_pass"] and subset["feasible"]),
        "source_pressure": necessary_exclusions(problem),
        "all_safe_sources": source_diagnostics(problem, problem.safe | problem.protected)}
    if subset["feasible"]:
        closure = frontier_closure(problem, subset["frontier"])
        result["witness_frontier_closure"] = evaluate_admission(problem, closure)
        if not result["witness_frontier_closure"]["joint_pass"]:
            raise AssertionError("Witness-frontier closure did not preserve the joint certificate")
        result["subset_sources"] = source_diagnostics(problem, subset["admitted"])
        result["response_rule_rows"] = len(problem.cap)
        result["response_rule_scope"] = "full-information task response box; complete table probes required, not source-only feature transfer"
    return result


def minimize_native_separation(problem: FiniteProblem, time_limit=30.):
    """Keep H/tasks fixed; shrink safe spoilers around a constructive subset.

    This is a deletion-minimal diagnostic around the returned feasible base,
    not a claim of globally minimum counterexample size. No physics is altered.
    """
    full = eval_all_safe(problem)
    if full["joint_pass"]:
        return {"status": "no_all_safe_failure"}
    good = solve_subset(problem, objective="min_admitted", time_limit=time_limit)
    if not good["feasible"]:
        return {"status": "no_verified_feasible_base", "solver": good}
    target = next(k for k in ("L", "D", "N", "C", "P", "H") if not full[k])
    base = np.asarray(good["admitted"], bool)
    bad = problem.safe | problem.protected
    changed = True
    while changed:
        changed = False
        for g in np.flatnonzero(bad & ~base):
            trial = bad.copy(); trial[g] = False
            if not evaluate_admission(problem, trial)[target]:
                bad = trial; changed = True
    bad_metrics = evaluate_admission(problem, bad)
    harmed = [s for s in problem.protected_sources
              if good["metrics"]["source_masses"].get(s, 0) >= problem.min_mass - problem.tolerance
              and bad_metrics["source_masses"].get(s, 0) < problem.min_mass - problem.tolerance]
    return {"status": "verified_deletion_minimal_spoilers", "preserved_failure": target,
        "good_solver": good, "bad_metrics": bad_metrics,
        "good_gear_ids": [problem.gear_ids[i] for i in np.flatnonzero(base)],
        "spoiler_gear_ids": [problem.gear_ids[i] for i in np.flatnonzero(bad & ~base)],
        "bad_gear_ids": [problem.gear_ids[i] for i in np.flatnonzero(bad)],
        "harmed_protected_sources": harmed,
        "old_choices_removed": 0, "tasks_removed": 0,
        "scope": "same empirical table, fixed H and Gamma; deletion-minimal around the returned constructive base, not global minimum"}


def restricted_template_mask(ecology):
    """Four balanced old-slot combinations per new item, chosen without responses."""
    slots = list(ecology.pool["slots"])
    mask = ecology.initial.copy()
    new = set(ecology.new_items)
    for i, gear in enumerate(ecology.gears):
        new_slots = [slot for slot in slots if str(gear[slot]) in new]
        if len(new_slots) != 1:
            continue
        bits = []
        for slot in slots:
            if slot == new_slots[0]: continue
            old = ecology.pool["slots"][slot][:2]
            if gear[slot] not in old: break
            bits.append(old.index(gear[slot]))
        if len(bits) == 3 and sum(bits) % 2 == 0:
            mask[i] = True
    return mask


def _study_case(payload):
    ecology, released, time_limit = payload
    context = {"ecology": ecology.pool["id"], "background": ecology.pool["background"],
               "race": ecology.race, "released_items": list(released), "release_size": len(released),
               "permission": "A_fixed_native_physics_admission_only", "source_unit": "variable-slot item ID"}
    rows, details = [], []
    full_problem, _ = ecology.problem(released, archive=ecology.initial_archive())
    for domain, template_filter in (("complete_mixing", None), ("four_templates", restricted_template_mask(ecology))):
        problem, indices = ecology.problem(released, archive=ecology.initial_archive(), candidate_filter=template_filter)
        full = eval_all_safe(problem)
        methods = [("all_safe", {"status": "direct_complete_table", "feasible": full["joint_pass"],
                                 "metrics": full, "seconds": 0., "proved_infeasible": False,
                                 "admitted": (problem.safe | problem.protected).tolist()})]
        # C needs the exact subset reference in each domain. E additionally
        # compares matched item-feature representations on the complete domain.
        specifications = [("subset", 0)]
        if domain == "complete_mixing": specifications += [("scalar", 1), ("generic2", 2), ("generic4", 4)]
        for method, q in specifications:
            result = solve_subset(problem, time_limit=time_limit, rule_rows=q)
            methods.append((method, result))
        source_opportunities = {s: sum(s in ss for i, ss in enumerate(problem.sources) if not problem.protected[i])
                                for s in problem.protected_sources}
        for method, result in methods:
            metrics = result.get("metrics")
            record = {**context, "domain": domain, "method": method,
                "domain_gears": len(indices), "complete_release_domain_gears": len(full_problem.sources),
                "protected_gears": int(np.sum(problem.protected)),
                "protected_source_count": len(problem.protected_sources),
                "protected_sources": list(problem.protected_sources),
                "new_gear_opportunities_by_protected_source": source_opportunities,
                "status": result["status"], "joint_feasible_found": result["feasible"],
                "proved_infeasible": result["proved_infeasible"], "solver_seconds": result["seconds"],
                "minimization_dual_bound": result.get("minimization_dual_bound"),
                "mip_gap": result.get("mip_gap"), "rule_rows": result.get("rule_rows", 0),
                "rule_parameters": result.get("rule_scalar_parameters"),
                "metrics": metrics}
            if metrics:
                record.update({k: metrics[k] for k in ("P", "N", "D", "L", "H", "C", "K", "failure_reasons",
                    "worst_protected_source_mass", "admitted_new_gears", "excluded_safe_new_gears")})
            rows.append(record)
            detail = {**context, "domain": domain, "method": method, "result": result,
                      "global_gear_indices": indices.tolist(), "gear_ids": problem.gear_ids}
            if result["feasible"]:
                detail["source_diagnostics"] = source_diagnostics(problem, result["admitted"])
                if method == "subset":
                    closure = frontier_closure(problem, result["frontier"])
                    detail["frontier_closure"] = evaluate_admission(problem, closure)
                    if not detail["frontier_closure"]["joint_pass"]:
                        raise AssertionError("Native finite witness-frontier closure failed")
            if method == "all_safe":
                detail["source_diagnostics"] = source_diagnostics(problem, result["admitted"])
                detail["source_pressure"] = necessary_exclusions(problem)
            details.append(detail)
    return rows, details


def run_study(run, out, workers=8, time_limit=2.):
    from wowfs.experiments.r4_data import load_ecologies
    ecologies = [e for e in load_ecologies(run) if e.pool["id"] in STUDY_POOLS]
    if len(ecologies) != 2 * len(STUDY_POOLS):
        raise ValueError("Missing selected ecology/race contexts")
    payloads = []
    for ecology in ecologies:
        releases = [(s,) for s in ecology.new_items] + [tuple(ecology.new_items)]
        payloads.extend((ecology, release, time_limit) for release in releases)
    out.mkdir(parents=True, exist_ok=True)
    design_path = out / "C_E_STUDY_DESIGN.json"
    if design_path.exists() and json.loads(design_path.read_text()) != json.loads(json.dumps(STUDY_DESIGN)):
        raise ValueError("C/E design changed; use a new study directory/version")
    if not design_path.exists(): atomic_json(design_path, STUDY_DESIGN)
    rows, details = [], []
    with ProcessPoolExecutor(max_workers=workers) as executor:
        pending = {executor.submit(_study_case, p): p for p in payloads}
        for future in as_completed(pending):
            local_rows, local_details = future.result(); rows.extend(local_rows); details.extend(local_details)
            atomic_json(out / "C_E_PROGRESS.json", {"status": "running", "completed_actions": len(details)//7,
                        "expected_actions": len(payloads), "comparison_rows": len(rows)})
    rows.sort(key=lambda r: (r["ecology"], r["race"], r["released_items"], r["domain"], r["method"]))
    details.sort(key=lambda r: (r["ecology"], r["race"], r["released_items"], r["domain"], r["method"]))
    write_csv(out / "C_E_LOCAL_FEASIBILITY.csv", rows)
    atomic_json(out / "C_E_STRUCTURAL_WITNESSES.json", details)
    atomic_json(out / "C_E_PROGRESS.json", {"status": "complete", "completed_actions": len(payloads),
                "expected_actions": len(payloads), "comparison_rows": len(rows)})
    atomic_json(out / "C_E_ANALYSIS_AUDIT.json", {"design_sha256": canonical_hash(STUDY_DESIGN),
        "physics_results_sha256": hashlib.sha256((Path(run)/"RESULTS.json").read_bytes()).hexdigest(),
        "analysis_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "solver_seconds_per_method": time_limit, "new_native_calls": 0,
        "rows": len(rows), "actions": len(payloads)})
    print(json.dumps({"rows": len(rows), "actions": len(payloads), "feasible_rows": sum(r["joint_feasible_found"] for r in rows)}))
    return rows, details


def main():
    root = setup_paths(); parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, default=root/"runs/r4-foundational-discovery/baseline-v1")
    parser.add_argument("--out", type=Path, default=root/"artifacts/r4-foundational-discovery")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--time-limit", type=float, default=2.)
    parser.add_argument("--freeze-only", action="store_true")
    args = parser.parse_args()
    if args.freeze_only:
        args.out.mkdir(parents=True, exist_ok=True)
        path = args.out/"C_E_STUDY_DESIGN.json"
        if path.exists() and json.loads(path.read_text()) != json.loads(json.dumps(STUDY_DESIGN)):
            raise ValueError("Existing C/E design differs")
        atomic_json(path, STUDY_DESIGN); print(path)
    else:
        run_study(args.run, args.out, args.workers, args.time_limit)


if __name__ == "__main__": main()
