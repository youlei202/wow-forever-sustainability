"""Replay the paper's finite experiments from immutable portable evidence.

These wrappers leave the original inference and frozen artifacts untouched.
They recompute decisions from compact moments; they do not run a simulator or
claim to reproduce historical wall-clock measurements.
"""
from __future__ import annotations

from collections import Counter
from contextlib import redirect_stdout
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import importlib
from importlib.metadata import version
import json
from pathlib import Path
import time
import traceback
import sys


def _read(path):
    return json.loads(Path(path).read_text())


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temporary.replace(path)


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _reference(ctx, name):
    """Check the authoritative comparison file against its sealed package."""
    package = Path(ctx.package)
    manifest = _read(package / "PACKAGE_MANIFEST.json")
    records = {row["path"]: row for row in manifest["files"]}
    _require(name in records, f"Unsealed comparison artifact: {name}")
    path = package / name
    _require(_sha(path) == records[name]["sha256"], f"Changed comparison artifact: {name}")
    return path


def _identity(ctx, stage):
    modules = ["co_review_check", "co_review_oracle", "co_native_analysis",
               "co_native_sensitivity", "co_exact", "co_sensitivity",
               "co_benchmark_report", "mi_native", "mi_druid", "mi_theory"]
    sources = {name: _sha(importlib.import_module("wowfs.experiments." + name).__file__)
               for name in modules}
    sources["science"] = _sha(__file__)
    inputs = {"bundle_manifest": Path(ctx.bundle) / "REVIEW_MANIFEST.json",
              "package_manifest": Path(ctx.package) / "PACKAGE_MANIFEST.json",
              "proof": Path(ctx.proof_path)}
    prior = Path(ctx.paper_source) / "evidence/gold/checked_outputs"
    if stage == "interface":
        for name in ("TRIPLE_SOURCE_CERTIFICATE_v2.json", "TRIPLE_INDEPENDENT_CERTIFICATES.json"):
            inputs[name] = prior / name
    return {"format": "wowfs-paper-reproduction-science-v1", "stage": stage,
            "environment": {"python": sys.version, "packages": {
                name: version(name) for name in ("numpy", "scipy", "PyYAML")}},
            "inputs": {key: {"path": str(path.resolve()), "sha256": _sha(path)}
                       for key, path in inputs.items()}, "source_sha256": sources,
            "new_native_calls": 0, "additional_alpha": 0}


def _begin(ctx, stage, resume):
    output = Path(ctx.output) / "science" / stage
    source_root = Path(__file__).resolve().parents[3]
    for immutable in (ctx.bundle, ctx.package, ctx.paper_source, source_root):
        _require(not output.resolve().is_relative_to(Path(immutable).resolve()),
                 "Reproduction output must be outside immutable inputs")
    identity = _identity(ctx, stage)
    config = output / "RUN_CONFIG.json"
    if config.exists():
        _require(resume, f"Existing run: pass resume=True or select a new output: {output}")
        _require(_read(config) == identity, "Resume input/source identity mismatch; select a new output")
    else:
        _require(not output.exists() or not any(output.iterdir()),
                 f"Refusing unrecognized nonempty output: {output}")
        output.mkdir(parents=True, exist_ok=True)
        _write(config, identity)
    receipt_path = output / "RUN_RECEIPT.json"
    if receipt_path.exists():
        receipt = _read(receipt_path)
        _require(receipt["status"] == "PASS", "Completed receipt is not PASS")
        for name, digest in receipt["output_sha256"].items():
            _require(_sha(output / name) == digest, f"Completed output changed: {name}")
        # Verify frozen bundle inputs again even when the completed computation
        # is reused. A matching manifest file alone does not validate its data.
        from wowfs.experiments.co_review_check import verify_manifest
        verify_manifest(Path(ctx.bundle))
        if stage == "interface":
            for name in ("NATIVE_SUMMARY.json", "DRUID_TRIPLE_RECHECK.json",
                         "UNIVERSAL_CONSTRUCTION_CHECKS.json", "SYMBOLIC_VS_ANTICHAIN.csv",
                         "SEMANTIC_MINIMALITY_CHECKS.json"):
                _reference(ctx, name)
        return output, _read(output / "REPORT.json")
    return output, None


def _finish(output, report, started):
    _write(output / "REPORT.json", report)
    _write(output / "RUN_RECEIPT.json", {
        "status": "PASS", "completed_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": time.perf_counter() - started,
        "new_native_calls": 0, "additional_alpha": 0,
        "output_sha256": {str(path.relative_to(output)): _sha(path)
                          for path in sorted(output.rglob("*")) if path.is_file()
                          and path.name != "RUN_RECEIPT.json"}})
    return report


def _failure(output, exc):
    # Every failed invocation gets its own receipt; a later successful resume
    # cannot erase the original exception or its traceback.
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    _write(output / "failures" / (stamp + ".json"), {
        "status": "FAIL", "error_type": type(exc).__name__, "error": str(exc),
        "traceback": traceback.format_exc(), "new_native_calls": 0})


def _recompute_native_panel(bundle):
    """Return plotted counts by actually re-evaluating the covered event."""
    from wowfs.experiments.co_native_analysis import finite_bounds, certify_queries
    from wowfs.experiments.co_native_sensitivity import propagate_tolerance, PANEL_PROTOCOL
    from wowfs.experiments.co_review_check import load_moments, replay_obligations
    native = Path(bundle) / "data/native"
    manifest = _read(native / "ANALYSIS_MANIFEST.json")
    worlds = {row["world_id"]: row for row in map(json.loads, (native / "CATALOG_REGISTRY.jsonl").read_text().splitlines())}
    rule = manifest["rule"]
    catalogue_rows, query_rows = [], []
    counts = Counter()
    obligations = Counter()
    tolerance = {multiplier: Counter() for multiplier in PANEL_PROTOCOL["tolerance_multipliers"]}
    for world_id in manifest["world_ids"]:
        world = worlds[world_id]
        moments = load_moments(native / world_id, world)
        bounds = finite_bounds(moments, rule, manifest["alpha_per_unit"])
        cert = certify_queries(world, moments, bounds, rule, "base")
        value = certify_queries(world, moments, bounds, rule, "base", retention=False)
        local = Counter(row["status"] for row in cert["queries"])
        counts.update(local)
        diagnostics = replay_obligations(cert)
        for row in diagnostics:
            obligations.update({name: int(active) for name, active in row["labels"].items()})
        catalogue_rows.append({"world_id": world_id, "class": world["context"]["class"],
                               "faction": world["context"]["faction"], "queries": len(cert["queries"]),
                               **{key: local[key] for key in ("YES", "NO", "UNKNOWN")}})
        for answer, relaxed in zip(cert["queries"], value["queries"]):
            query_rows.append({"world_id": world_id, "query_id": answer["query_id"],
                               "required": answer["required"], "status": answer["status"],
                               "value_only_status": relaxed["status"],
                               "retention_essential": answer["status"] == "NO" and relaxed["status"] == "YES"})
        for multiplier in tolerance:
            shifted, new_rule = propagate_tolerance(bounds, rule, multiplier)
            result = certify_queries(world, moments, shifted, new_rule, "base")
            tolerance[multiplier].update(row["status"] for row in result["queries"])
    frozen = _read(Path(bundle) / "data/native-summary/NATIVE_EVIDENCE_SUMMARY.json")["base"]
    _require(dict(counts) == frozen["confidence_answers"], "Recomputed base outcomes differ")
    essential = sum(row["retention_essential"] for row in query_rows)
    _require(essential == frozen["retention_essential_certified"], "Recomputed retention ablation differs")
    saved_tolerance = _read(Path(bundle) / "data/secondary-tolerance/SUMMARY.json")
    for row in saved_tolerance["thresholds"]:
        _require(dict(tolerance[row["multiplier"]]) == row["confidence_counts"], "Recomputed tolerance panel differs")
    _require((len(catalogue_rows), len(query_rows)) == (16, 128), "Primary denominator changed")
    return {"catalogues": len(catalogue_rows), "registered_queries": len(query_rows),
            "confidence_counts": dict(counts), "retention_essential": essential,
            "obligation_labels": dict(obligations), "catalogue_rows": catalogue_rows,
            "query_rows": query_rows,
            "tolerance_rows": [{"multiplier": key, "tolerance": str(Fraction(rule["tolerance"]) * Fraction(key)),
                                **{status: value[status] for status in ("YES", "NO", "UNKNOWN")}}
                               for key, value in tolerance.items()],
            "evidence": "Recomputed fixed-N paired-t simultaneous finite-event consequences",
            "counting": "128 correlated targets in 16 registered menus; tolerance reanalyses reuse the same events"}


def run_certification_checks(ctx, resume=False):
    """Recompute primary certificates, ablations, tolerance and timing metrics."""
    from wowfs.experiments import co_review_check, co_benchmark_report
    output, completed = _begin(ctx, "certification", resume)
    if completed is not None:
        return completed
    started = time.perf_counter()
    try:
        with (output / "replay.log").open("a") as log, redirect_stdout(log):
            certificate = co_review_check.check_bundle(Path(ctx.bundle))
            _write(output / "CERTIFICATE_RECHECK.json", certificate)
            benchmark = co_benchmark_report.check(Path(ctx.bundle) / "data/benchmark")
            _write(output / "BENCHMARK_RECHECK.json", benchmark)
            panel = _recompute_native_panel(Path(ctx.bundle))
            _write(output / "NATIVE_PANEL.json", panel)
        _require(certificate["status"] == benchmark["status"] == "PASS", "Replay did not pass")
        return _finish(output, {"status": "PASS", "native_panel": panel,
                       "certificate_recheck": certificate, "benchmark_recheck": benchmark,
                       "benchmark_scope": "Metrics recomputed from compact per-attempt/per-query receipts; historical runtimes are not rerun",
                       "new_native_calls": 0, "additional_alpha": 0}, started)
    except BaseException as exc:
        _failure(output, exc)
        raise


def run_interface_checks(ctx, resume=False):
    """Recompute all target sets, the independent Druid proof and abstract cases."""
    from wowfs.experiments import mi_native, mi_druid, mi_theory
    output, completed = _begin(ctx, "interface", resume)
    if completed is not None:
        return completed
    started = time.perf_counter()
    try:
        with (output / "replay.log").open("a") as log, redirect_stdout(log):
            native_output = output / "native"
            native = mi_native.run(ctx.bundle, native_output,
                                   resume=(native_output / "NATIVE_RUN_CONFIG.json").exists())
            _require(_read(native_output / "NATIVE_SUMMARY.json") == _read(_reference(ctx, "NATIVE_SUMMARY.json")),
                     "Full native target audit differs from authoritative package")
            prior = Path(ctx.paper_source) / "evidence/gold/checked_outputs"
            druid_output = output / "druid"
            druid = mi_druid.run(ctx.bundle, druid_output,
                                 resume=(druid_output / "DRUID_RUN_MANIFEST.json").exists(),
                                 prior_certificate=str(prior / "TRIPLE_SOURCE_CERTIFICATE_v2.json"),
                                 prior_pairs=str(prior / "TRIPLE_INDEPENDENT_CERTIFICATES.json"))
            original = _read(_reference(ctx, "DRUID_TRIPLE_RECHECK.json"))
            for key in ("endpoints", "all_physical_cap_safe", "minimum_physical_cap_lower_margin_DPS",
                        "exact_finite_mean_queries", "whole_interval", "attribution", "validation"):
                _require(druid[key] == original[key], f"Independent Druid recheck differs: {key}")
            theory_output = output / "theory"
            old_proof = mi_theory.PROOF_PATH
            try:
                mi_theory.PROOF_PATH = Path(ctx.proof_path)
                mi_theory.run(theory_output, resume=(theory_output / "CHECKPOINT.json").exists())
            finally:
                mi_theory.PROOF_PATH = old_proof
            theory = _read(theory_output / "UNIVERSAL_CONSTRUCTION_CHECKS.json")
            original_theory = _read(_reference(ctx, "UNIVERSAL_CONSTRUCTION_CHECKS.json"))
            for key in ("checks", "boundary_corners", "high_order_pairs", "check_count", "expected_guarantee_failure_count"):
                _require(theory[key] == original_theory[key], f"Abstract finite construction recheck differs: {key}")
            for name in ("SYMBOLIC_VS_ANTICHAIN.csv", "SEMANTIC_MINIMALITY_CHECKS.json"):
                _require((theory_output / name).read_bytes() == _reference(ctx, name).read_bytes(),
                         f"Abstract semantic recheck differs: {name}")
        return _finish(output, {"status": "PASS", "native": native, "druid": druid,
                       "theory": {key: theory[key] for key in ("scope", "case_count", "check_count", "expected_guarantee_failure_count", "high_order_pairs", "boundary_corners")},
                       "scientific_results_equal_saved_outputs": True,
                       "new_native_calls": 0, "additional_alpha": 0}, started)
    except BaseException as exc:
        _failure(output, exc)
        raise


def run_cached_checks(ctx, resume=False):
    """One API for the complete compact-evidence replay used by notebooks."""
    return {"status": "PASS", "certification": run_certification_checks(ctx, resume),
            "interface": run_interface_checks(ctx, resume),
            "new_native_calls": 0, "additional_alpha": 0}
