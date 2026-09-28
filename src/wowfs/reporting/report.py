"""Auditable tables, plots and review packages; never impute missing native runs."""
from __future__ import annotations
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
import shutil
import zipfile
import numpy as np
from wowfs.paths import SOURCE_ROOT, atomic_json
from wowfs.reporting.coverage import write_coverage

def write_csv(path: Path, rows: list[dict], fallback: tuple = ("status", "reason")) -> None:
    fields = list(dict.fromkeys(k for row in rows for k in row)) or list(fallback)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, sort_keys=True) if isinstance(v, (dict, list, tuple)) else v for k, v in row.items()})

def success_prefix(rows: list[dict]) -> tuple[int, int]:
    """Unknown is not success; possible prefix stops only at known violations."""
    ordered = sorted(rows, key=lambda row: row["round"])
    certain = possible = 0
    for row in ordered:
        if row["round"] != certain + 1 or row["status"] != "pass":
            break
        certain += 1
    for row in ordered:
        if row["round"] != possible + 1 or row["status"] == "violation":
            break
        possible += 1
    return certain, possible

def _plot(rounds: list[dict], target: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    metrics = [("power_ratio", "Maximum power / fixed initial anchor"), ("new_item_fraction", "Useful new item fraction"),
               ("D", "Novel near-optimal task weight"), ("legacy_fraction", "Retained legacy source fraction"),
               ("H", "History compatibility"), ("K", "Exact portfolio size K")]
    # The paper displays this at 6.75 inches: avoid shrinking a wide slide to tiny type.
    import textwrap
    fig, axes = plt.subplots(2, 3, figsize=(8, 6.4), constrained_layout=True)
    methods = sorted({r["method"] for r in rounds})
    for ax, (key, title) in zip(axes.flat, metrics):
        for method in methods:
            grouped = defaultdict(list)
            for row in rounds:
                value = row.get(key)
                if row["method"] == method and isinstance(value, (int, float)) and np.isfinite(value):
                    grouped[row["round"]].append(float(value))
            xs = sorted(grouped)
            if xs:
                means = [np.mean(grouped[x]) for x in xs]
                line, = ax.plot(xs, means, marker=".", linewidth=1.3, label=method.replace("_", " "))
                ax.fill_between(xs, [min(grouped[x]) for x in xs], [max(grouped[x]) for x in xs], color=line.get_color(), alpha=.07)
        if key == "power_ratio":
            ax.axhline(1.05, color="black", linestyle="--", linewidth=1, label="fixed cap (1.05)")
        if key == "K":
            ax.axhline(4, color="black", linestyle="--", linewidth=1)
        ax.set_title(textwrap.fill(title, 26), fontsize=9)
        ax.set_xlabel("Update round", fontsize=9)
        ax.tick_params(labelsize=9)
        ax.grid(alpha=.15)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncols=2, fontsize=9)
    fig.suptitle("Abstract model: six updates; shading shows observed range", fontsize=10)
    fig.savefig(target / "abstract_trajectories.pdf")
    fig.savefig(target / "abstract_trajectories.png", dpi=160)
    plt.close(fig)

def _finite_data(root: Path, latest: Path) -> list[str]:
    source = root / "data/theory/finite_data"
    if not (source / "FINITE_DATA_SUMMARY.csv").exists():
        return ["Finite-data abstract diagnostic not run."]
    for name in ("FINITE_DATA_SUMMARY.csv", "FINITE_DATA_PROTOCOL.json"):
        shutil.copy2(source / name, latest / "summary" / name)
    shutil.copy2(source / "FINITE_DATA_TRIALS.csv", latest / "selected_evidence/FINITE_DATA_TRIALS.csv")
    with (source / "FINITE_DATA_SUMMARY.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.9), constrained_layout=True)
    methods = sorted({r["method"] for r in rows})
    for ax, scenario, metric, title in [
        (axes[0], "correct_model", "all_hazards_certified_count", "Correct model: all six hazardous pairings certified"),
        (axes[1], "hidden_legal_interaction", "false_model_implied_power_claim_count", "Omitted interaction: false conditional power claims")]:
        for index, method in enumerate(methods):
            selected = sorted((r for r in rows if r["method"] == method and r["scenario"] == scenario), key=lambda r: int(r["training_budget"]))
            x = np.array([int(r["training_budget"]) for r in selected])
            n = np.array([int(r["replicates"]) for r in selected])
            p = np.array([int(r[metric]) for r in selected]) / n
            line, = ax.plot(x, p, marker=["x", "o", "s"][index], linestyle=["--", "-", ":"][index], label=method.replace("_", " "))
            # Pointwise Wilson intervals conditional on this frozen synthetic model.
            z = 1.959963984540054
            center = (p + z*z/(2*n))/(1+z*z/n)
            half = z*np.sqrt(p*(1-p)/n + z*z/(4*n*n))/(1+z*z/n)
            ax.fill_between(x, center-half, center+half, alpha=.09, color=line.get_color())
        ax.set_xscale("log", base=2)
        ax.set_ylim(-.04, 1.04)
        import textwrap
        ax.set_title(textwrap.fill(title, 36), fontsize=9)
        ax.set_xlabel("Synthetic physical training draws\n(paired probes count twice)", fontsize=9)
        ax.set_ylabel("Fraction of replicates (n=128)", fontsize=9)
        ax.tick_params(labelsize=9)
        ax.grid(alpha=.2)
    axes[1].axhline(1, color="black", linewidth=.8, linestyle="--", label="Independent holdout detects 128/128 violations")
    handles, labels = axes[1].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncols=1, fontsize=9)
    fig.savefig(latest / "figures/finite_data_diagnostic.pdf")
    fig.savefig(latest / "figures/finite_data_diagnostic.png", dpi=160)
    plt.close(fig)
    point = [r for r in rows if r["scenario"] == "correct_model" and int(r["training_budget"]) == 4096]
    text = ["## Finite-data abstract diagnostic", "",
            "This frozen final-pool experiment tests interaction identification, not online joint sustainability. At 4,096 synthetic physical training draws:", ""]
    for r in point:
        text.append(f"- {r['method']}: all six hazardous pairings certified in {r['all_hazards_certified_count']}/{r['replicates']} noise replicates.")
    text += ["", "The same-feature generic estimator reuses the same observations and ties by construction. This supplies no novel statistical superiority claim. Correct-model holdout checks remain unresolved at the exact power boundary. In the omitted-interaction stress, independent holdout detects a violation in every one of 128 replicates, invalidating conditional model claims. See FINITE_DATA_PROTOCOL.json for independent seeds, support bounds, error allocation, physical counts, and cache reuse.", ""]
    return text

def build_report(root: Path, run_dir: Path | None = None) -> Path:
    if run_dir is None:
        marker = root / "runs/LATEST.json"
        if not marker.exists():
            raise RuntimeError("No completed run checkpoint index; run exact-small first")
        run_dir = Path(json.loads(marker.read_text())["run_dir"])
    run_dir = run_dir.resolve()
    protocol = json.loads((run_dir / "FROZEN_PROTOCOL.json").read_text())
    manifest = json.loads((run_dir / "SEQUENCE_MANIFEST.json").read_text())
    latest = root / "artifacts/latest"
    for name in ("summary", "figures", "theory", "paper", "selected_evidence"):
        (latest / name).mkdir(parents=True, exist_ok=True)
    summary = latest / "summary"
    coverage = write_coverage(SOURCE_ROOT, summary)
    atomic_json(summary / "FROZEN_PROTOCOL.json", protocol)
    write_csv(summary / "SEQUENCE_MANIFEST.csv", manifest)
    if manifest and manifest[0].get("table_file"):
        table_file = Path(manifest[0]["table_file"])
        if table_file.exists():
            shutil.copy2(table_file, latest / "selected_evidence" / table_file.name)
    collections = {k: [] for k in ("rounds", "feasibility", "rules", "relevance", "ablations", "costs")}
    sequence_results, run_failures = [], []
    for entry in manifest:
        file = run_dir / "checkpoints" / f"{entry['sequence_id']}.json"
        if not file.exists():
            run_failures.append({**entry, "status": "not_run"})
            continue
        saved = json.loads(file.read_text())
        if saved["protocol"] != protocol:
            raise RuntimeError("Refusing to mix result protocols")
        if saved["status"] != "complete":
            run_failures.append({**entry, "status": saved["status"], "error": saved.get("error", "")})
            continue
        result = saved["result"]
        metadata = {"sequence_id": entry["sequence_id"], "context_id": "abstract_no_class_or_race",
                    "seed": entry["seed"], "pool_seed": entry["seed"] // 2, "variant": entry["variant"],
                    "scope": "abstract_exact", "split": protocol["split"], "commit": protocol["commit"],
                    "source_hash": protocol["source_hash"], "config_hash": protocol["config_hash"],
                    "engine_hash": protocol["engine_hash"]}
        for key in collections:
            collections[key].extend({**row, **metadata} for row in result.get(key, []))
        atomic_json(latest / "selected_evidence" / f"{entry['sequence_id']}.json", saved)
        methods = sorted({r["method"] for r in result["rounds"]})
        for method in methods:
            rows = sorted((r for r in result["rounds"] if r["method"] == method), key=lambda x: x["round"])
            lower, upper = success_prefix(rows)
            first_bad = next((r for r in rows if r["status"] != "pass"), {})
            sequence_results.append({**metadata, "method": method, "horizon": entry["horizon"],
                                     "status": "evaluated",
                                     "success_prefix": lower, "possible_prefix": upper,
                                     "pass_horizon": int(lower == entry["horizon"]),
                                     "evaluated_rounds": len(rows),
                                     "unresolved_rounds": sum(r["status"] == "unresolved" for r in rows),
                                     "first_failure": first_bad.get("failure_reasons", "none"),
                                     "final_K": rows[-1].get("K"),
                                     "max_power_ratio": max((r["power_ratio"] for r in rows if r["power_ratio"] is not None), default=None),
                                     "mean_new_item_fraction": float(np.mean([r["new_item_fraction"] for r in rows])),
                                     "min_legacy_fraction": min(r["legacy_fraction"] for r in rows)})
    from wowfs.experiments.exact import METHODS
    for entry in run_failures:
        for method in METHODS:
            sequence_results.append({"sequence_id": entry["sequence_id"], "context_id": "abstract_no_class_or_race",
                                     "seed": entry["seed"], "pool_seed": entry["seed"] // 2, "variant": entry["variant"],
                                     "scope": "abstract_exact", "split": protocol["split"], "method": method,
                                     "status": entry["status"], "horizon": entry["horizon"], "success_prefix": 0,
                                     "possible_prefix": entry["horizon"], "pass_horizon": 0,
                                     "evaluated_rounds": 0, "unresolved_rounds": entry["horizon"],
                                     "first_failure": entry["status"], "final_K": None, "max_power_ratio": None,
                                     "mean_new_item_fraction": None, "min_legacy_fraction": None,
                                     "source_hash": protocol["source_hash"], "config_hash": protocol["config_hash"],
                                     "engine_hash": protocol["engine_hash"], "commit": protocol["commit"]})
    write_csv(summary / "SEQUENCE_RESULTS.csv", sequence_results)
    write_csv(summary / "RUN_FAILURES.csv", run_failures)
    mapping = {"rounds": "ROUND_RESULTS.csv", "feasibility": "FEASIBILITY_RESULTS.csv",
               "relevance": "REWARD_RELEVANCE.csv", "ablations": "ABLATIONS.csv", "costs": "COSTS.csv"}
    for key, name in mapping.items():
        write_csv(summary / name, collections[key])
    with (summary / "RULE_SNAPSHOTS.jsonl").open("w") as stream:
        for row in collections["rules"]:
            stream.write(json.dumps(row, sort_keys=True) + "\n")
    methods = sorted({r["method"] for r in sequence_results})
    aggregates = []
    for method in methods:
        rows = [r for r in sequence_results if r["method"] == method]
        method_rounds = [r for r in collections["rounds"] if r["method"] == method]
        def observed_mean(key):
            vals = [r[key] for r in rows if r[key] is not None]
            return float(np.mean(vals)) if vals else float("nan")
        aggregates.append({"method": method, "scope": "abstract_exact", "horizon": protocol["config"]["horizon"],
                           "evaluated_sequences": sum(r["status"] == "evaluated" for r in rows), "required_sequences": len(manifest),
                           "pool_clusters": len({(r["variant"], r["pool_seed"]) for r in rows}),
                           "mean_success_prefix": float(np.mean([r["success_prefix"] for r in rows])),
                           "mean_possible_prefix": float(np.mean([r["possible_prefix"] for r in rows])),
                           "success_prefix_interpretation": "conservative across every prescribed sequence",
                           "pass_numerator": sum(r["pass_horizon"] for r in rows), "pass_denominator": len(manifest),
                           "max_power_ratio": max((r["max_power_ratio"] for r in rows if r["max_power_ratio"] is not None), default=float("nan")),
                           "mean_new_item_fraction": observed_mean("mean_new_item_fraction"),
                           "min_legacy_fraction": min((r["min_legacy_fraction"] for r in rows if r["min_legacy_fraction"] is not None), default=float("nan")),
                           "mean_final_K": observed_mean("final_K"),
                           "final_K_denominator": sum(r["final_K"] is not None for r in rows),
                           "max_rule_dimensions": max((r["rule_dimensions"] for r in method_rounds if r.get("rule_dimensions") is not None), default=None),
                           "max_K": max((r["K"] for r in method_rounds if r.get("K") is not None), default=None),
                           "min_new_task_weight": min((r["N"] for r in method_rounds), default=None),
                           "min_novel_task_weight": min((r["D"] for r in method_rounds), default=None),
                           "min_legacy_task_weight": min((r["legacy_worst"] for r in method_rounds), default=None),
                           "min_full_history_retention": min((r["H_all"] for r in method_rounds), default=None),
                           "optimizer_limited_rounds": sum(r.get("solver_status") == "limit" for r in method_rounds),
                           "infeasible_admission_subproblems": sum(str(r.get("solver_status", "")).startswith("infeasible") for r in method_rounds),
                           "uncertainty": "descriptive finite construction; no population interval"})
    write_csv(summary / "ABSTRACT_COMPARISON.csv", aggregates)
    paired_orders = []
    for method in methods:
        for variant in protocol["config"]["variants"]:
            pool_ids = sorted({r["pool_seed"] for r in sequence_results if r["variant"] == variant})
            for pool in pool_ids:
                pair = sorted((r for r in sequence_results if r["method"] == method and r["variant"] == variant and r["pool_seed"] == pool), key=lambda r: r["seed"])
                if len(pair) == 2:
                    paired_orders.append({"scope": "abstract_exact", "method": method, "variant": variant,
                                          "pool_seed": pool, "first_seed": pair[0]["seed"], "second_seed": pair[1]["seed"],
                                          "first_prefix": pair[0]["success_prefix"], "second_prefix": pair[1]["success_prefix"],
                                          "difference_second_minus_first": pair[1]["success_prefix"]-pair[0]["success_prefix"]})
    write_csv(summary / "PAIRED_REVEAL_ORDERS.csv", paired_orders)
    permissions = []
    for method in methods:
        permissions.append({"method": method, "scope": "abstract_exact", "line": "A", "physics_change": False,
                            "deployment": "abstract_instance_adapted", "status": "diagnostic" if "envelope" in method else "comparison",
                            "rules": "See RULE_SNAPSHOTS.jsonl for actual constraints and complexity"})
    write_csv(summary / "MECHANISM_PERMISSIONS.csv", permissions)
    if collections["rounds"]:
        _plot(collections["rounds"], latest / "figures")
    finite_data_text = _finite_data(root, latest)
    for source, target in [(root / "provenance/ENGINE_BRIDGE.md", latest / "ENGINE_BRIDGE.md"),
                           (SOURCE_ROOT / "docs/THEORY.md", latest / "theory/THEORY.md"),
                           (SOURCE_ROOT / "docs/RELATED_WORK.md", latest / "theory/RELATED_WORK.md"),
                           (SOURCE_ROOT / "docs/STATISTICAL_EVIDENCE.md", latest / "theory/STATISTICAL_EVIDENCE.md"),
                           (SOURCE_ROOT / "docs/ABSTRACT_FINDINGS.md", latest / "ABSTRACT_FINDINGS.md"),
                           (SOURCE_ROOT / "docs/DECISIONS.md", latest / "DECISIONS.md"),
                           (SOURCE_ROOT / "docs/SOURCES.md", latest / "SOURCES.md"),
                           (SOURCE_ROOT / "docs/SUBMISSION.md", latest / "paper/SUBMISSION.md")]:
        if source.exists():
            shutil.copy2(source, target)
    table = ["| Method | Mean S(6) | Pass 6 | Maximum power / anchor | Useful new fraction | Worst retained-source fraction | Final K |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for row in aggregates:
        table.append(f"| {row['method']} | {row['mean_success_prefix']:.3f} | {row['pass_numerator']}/{row['pass_denominator']} | {row['max_power_ratio']:.4f} | {row['mean_new_item_fraction']:.3f} | {row['min_legacy_fraction']:.3f} | {row['mean_final_K']:.2f} |")
    report = ["# Research review: initial abstract evidence", "",
              "**Scope: exact deterministic abstract model. Native Forever runs: 0/56 contexts. This is not a completed AISTATS study.**", "",
              "1. **Structure.** A protected-configuration trade obstructs a single additive budget from excluding both dangerous mixtures while retaining required configurations. The threshold obstruction is established background. A finite joint construction links power, useful novelty, legacy, history and portfolio requirements; its originality is not established.",
              "2. **Comparison.** The table below is computed from finite development instances. It compares achieved sequential outcomes, not oracle sustainable capacity. A structured mechanism is contained in a sufficiently expressive generic budget class; a tie is scientifically meaningful.",
              "3. **Joint requirements.** A power-safe row does not establish sustainable expansion. Success prefixes require all implemented P/N/D/L/H/C criteria and the floor. Inspect per-round failure reasons and current-rule counterfactuals.",
              "4. **Coverage.** Alliance 0/28; Horde 0/28; nine classes 0/9. Native faction and class tables explicitly say not run. The engine was not present at the three supplied paths, nor found in a connected GitHub exact-name search.",
              "5. **Theory.** See theory/THEORY.md for statements, proofs and their precise assumptions. Abstract propositions do not establish native engine structure. Statistical guarantees are conditional on the model and are not finite-data native results.",
              "6. **Paper claim.** At present: a formal problem, a finite structural construction, and exact development evidence. No native mechanism superiority, cross-context robustness, or submission-ready empirical claim is supported.", "",
              "## Measured abstract comparison", "",
              f"{len(manifest)} prescribed sequences; {len({(r['variant'], r['seed']//2) for r in manifest})} parameterized pool clusters; paired reveal orders; horizon {protocol['config']['horizon']}. Same-pool orderings are correlated. Values are descriptive; no combat or population confidence intervals are inferred.", "",
              *table, "", "Safe-set envelope is a diagnostic: pointwise maximal safe sets need not optimize the joint novelty criterion. It is not labelled a joint feasibility oracle.",
              "", *finite_data_text,
              "", "## Reproduction and provenance", "",
              f"Run directory: `{run_dir}`", f"Scientific source hash: `{protocol['source_hash']}`", f"Config hash: `{protocol['config_hash']}`", "",
              "From the source checkout: `source scripts/env.sh`; `bash scripts/run_research.sh --resume`.",
              "Resume reuses only complete matching instance checkpoints; interruption inside an instance recomputes that instance. Every completed checkpoint retains all round results and rule snapshots. This is not yet a native per-round resumable runner.",
              "Git identity was unavailable. The source snapshot and file hashes record uncommitted code without inventing an author.",
              "", "## Missing decisive evidence", "",
              "The native engine, native interaction ablations, 20-round main matrix, finite-data comparison, class-shared deployment, and role transfer have not run. Formal main protocol has not been frozen. No old calibration result is being reused as new evidence."]
    (latest / "REVIEW.md").write_text("\n".join(report) + "\n")
    findings = SOURCE_ROOT / "docs/ABSTRACT_FINDINGS.md"
    (latest / "RESULTS.md").write_text(findings.read_text() if findings.exists() else "\n".join(report) + "\n")
    (latest / "NEXT_RESEARCH.md").write_text("# Next research\n\n1. Connect the existing Forever engine and extract event-supported interaction counterexamples.\n2. Test whether structured parameterization improves search or sample cost over equally expressive generic budgets; retain negative results.\n3. Freeze native tasks and behavior scale, then execute independent 20-round strata and shared-rule transfer.\n")
    # Generated LaTeX is maintained source; figures and all numeric datasets stay external.
    tex = [r"\begin{tabular}{lrrrr}", r"\toprule", r"Method & Mean $S(6)$ & Pass 6 & Max. power & $K_6$ \\", r"\midrule"]
    for r in aggregates:
        name = r["method"].replace("_", r"\_")
        tex.append(f"{name} & {r['mean_success_prefix']:.2f} & {r['pass_numerator']}/{r['pass_denominator']} & {r['max_power_ratio']:.3f} & {r['mean_final_K']:.2f}" + r" \\")
    tex.extend([r"\bottomrule", r"\end{tabular}"])
    (SOURCE_ROOT / "paper/tables/exact_results.tex").write_text("\n".join(tex) + "\n")
    return latest

def package(root: Path, latest: Path) -> Path:
    for name in ("ABSTRACT_FINDINGS.md", "DECISIONS.md"):
        if (SOURCE_ROOT / "docs" / name).exists():
            shutil.copy2(SOURCE_ROOT / "docs" / name, latest / name)
    if (SOURCE_ROOT / "docs/ABSTRACT_FINDINGS.md").exists():
        shutil.copy2(SOURCE_ROOT / "docs/ABSTRACT_FINDINGS.md", latest / "RESULTS.md")
    for path in (root / "provenance").glob("*.json"):
        shutil.copy2(path, latest / "selected_evidence" / path.name)
    run = Path(json.loads((root / "runs/LATEST.json").read_text())["run_dir"])
    for name in ("INDEPENDENT_ABSTRACT_AUDIT.json", "INITIAL_RUN_STATE.json", "RUN_STATE.json", "SOURCE_SNAPSHOT_HASHES.json"):
        if (run / name).exists():
            shutil.copy2(run / name, latest / "selected_evidence" / name)
    if (root / "logs/tests.log").exists():
        shutil.copy2(root / "logs/tests.log", latest / "selected_evidence/TEST_RESULTS.txt")
    files = [p for p in SOURCE_ROOT.rglob("*") if p.is_file() and not any(part in {".git", "__pycache__", ".pytest_cache"} or part.endswith(".egg-info") for part in p.relative_to(SOURCE_ROOT).parts)]
    files = [p for p in files if p.suffix not in {".pyc", ".pdf", ".zip", ".csv", ".jsonl", ".log"}]
    source_zip = root / "artifacts/SOURCE_SNAPSHOT.zip"
    hashes = []
    with zipfile.ZipFile(source_zip, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            name = str(path.relative_to(SOURCE_ROOT))
            archive.write(path, name)
            hashes.append({"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    atomic_json(latest / "selected_evidence/SOURCE_MANIFEST.json", {"commit": "uncommitted-no-git-identity", "files": hashes})
    artifact_hashes = [{"path": str(p.relative_to(latest)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                       for p in sorted(latest.rglob("*")) if p.is_file() and p.name != "ARTIFACT_MANIFEST.json"]
    atomic_json(latest / "ARTIFACT_MANIFEST.json", {
        "files": artifact_hashes, "source_archive_sha256": hashlib.sha256(source_zip.read_bytes()).hexdigest(),
        "scope": "abstract development and explicit native not-run tables"})
    archive_path = root / "artifacts/WOW_FOREVER_SUSTAINABILITY_REVIEW.zip"
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(latest.rglob("*")):
            if path.is_file():
                archive.write(path, str(path.relative_to(latest)))
    return archive_path
