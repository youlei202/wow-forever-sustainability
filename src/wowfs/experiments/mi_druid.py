"""Independent finite-moment recheck of the registered Druid completion triple.

No certificate-service, native-inference, or original replay functions are
imported. All target-containing publications and all activated physical rows
are retained. The original simultaneous event is approximate paired Student-t.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
from scipy.stats import t

WORLD = "co_druid_passive_resources__validation_02"
TRIPLE = ("a04", "x1", "x3")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def reconstruct(means, covariance, n, manifest):
    """Independently evaluate every declared linear contrast from moments."""
    nq, nc = means.shape
    family_size = nq * (nc + 2 * nc * nc)
    assert family_size == manifest["family_size"]
    critical = float(t.isf(manifest["alpha"] / (2 * family_size), n - 1))
    assert abs(critical - manifest["critical"]) < 1e-12
    rule = manifest["rule"]
    offsets = (("cap", 1 + float(Fraction(rule["headroom"]))),
               ("gain", -float(Fraction(rule["gain"]))),
               ("retention", float(Fraction(rule["tolerance"]))))
    bounds = {}
    coefficient_digest = hashlib.sha256()
    for q in range(nq):
        for name, offset in offsets:
            combinations = [(c, None) for c in range(nc)] if name == "cap" else list(itertools.product(range(nc), repeat=2))
            coefficients = []
            for c, d in combinations:
                a = np.zeros(nc)
                a[manifest["reference_indices"][q]] += offset
                a[c] += -1 if d is None else 1
                if d is not None:
                    a[d] -= 1
                coefficients.append(a)
                center = float(np.dot(a, means[q]))
                variance = float(np.dot(a, np.dot(covariance[q], a)))
                assert variance >= -1e-9
                radius = critical * np.sqrt(max(variance, 0) / n)
                guard = 128 * np.finfo(float).eps * max(1, abs(center) + radius)
                shape = (nq, nc) if d is None else (nq, nc, nc)
                index = (q, c) if d is None else (q, c, d)
                for endpoint, value in (("lower", center - radius - guard), ("upper", center + radius + guard)):
                    key = name + "_" + endpoint
                    if key not in bounds:
                        bounds[key] = np.empty(shape)
                    bounds[key][index] = value
            coefficient_digest.update(np.asarray(coefficients).tobytes())
    assert coefficient_digest.hexdigest() == manifest["coefficient_sha256"]
    return bounds


def reference_intervals(bounds, gain, tolerance):
    """Use only covered diagonal intervals, not new t directions."""
    gain_lower = np.diagonal(bounds["gain_lower"], axis1=1, axis2=2)
    gain_upper = np.diagonal(bounds["gain_upper"], axis1=1, axis2=2)
    ret_lower = np.diagonal(bounds["retention_lower"], axis1=1, axis2=2)
    ret_upper = np.diagonal(bounds["retention_upper"], axis1=1, axis2=2)
    lower = np.maximum((-gain_upper / gain).max(axis=1), (ret_lower / tolerance).max(axis=1))
    upper = np.minimum((-gain_lower / gain).min(axis=1), (ret_upper / tolerance).min(axis=1))
    assert np.all(lower > 0) and np.all(lower <= upper)
    return lower, upper


def shifted_retention(bounds, delta, ref_lower, ref_upper):
    result = {k: v.copy() for k, v in bounds.items()}
    result["retention_lower"] += np.minimum(delta * ref_lower, delta * ref_upper)[:, None, None]
    result["retention_upper"] += np.maximum(delta * ref_lower, delta * ref_upper)[:, None, None]
    return result


def max_min(matrix, source_rows, frontier_rows):
    return matrix[:, source_rows][:, :, frontier_rows].min(axis=2).max(axis=1)


class IndependentDomain:
    def __init__(self, world, moments, manifest):
        self.world, self.moments, self.manifest = world, moments, manifest
        self.items = moments["domain"]["left"] + moments["domain"]["right"]
        self.supports = list(map(frozenset, moments["domain"]["supports"]))
        self.history = frozenset(world["history"])
        self.weights = np.asarray(world["task_weights"])
        self.rho = float(Fraction(manifest["rule"]["retention_mass"]))
        self.gain_mass = float(Fraction(manifest["rule"]["gain_mass"]))
        self.optional = [x for x in self.items if x not in self.history]
        self.publications = [self.history | frozenset(x for j, x in enumerate(self.optional) if mask >> j & 1)
                             for mask in range(1 << len(self.optional))]

    def active(self, publication):
        return [j for j, support in enumerate(self.supports) if support <= publication]

    def assess(self, publication, bounds, endpoint, *, need_gain=True):
        rows = self.active(publication)
        cap = bounds["cap_" + endpoint][:, rows].min(axis=1)
        gain = max_min(bounds["gain_" + endpoint], rows, self.active(self.history))
        sources = {}
        for source in sorted(publication):
            witness_rows = [r for r in rows if source in self.supports[r]]
            margins = max_min(bounds["retention_" + endpoint], witness_rows, rows)
            sources[source] = {"witness_rows": witness_rows, "margins_DPS": margins.tolist(),
                               "passing_mass": float(self.weights[margins >= 0].sum())}
        failures = [s for s, v in sources.items() if v["passing_mass"] < self.rho]
        return dict(items=sorted(publication), active_rows=rows, cap_margins_DPS=cap.tolist(),
                    gain_margins_DPS=gain.tolist(), sources=sources, retention_failures=failures,
                    cap_pass=bool(np.all(cap >= 0)), gain_pass=bool(self.weights[gain >= 0].sum() >= self.gain_mass),
                    valid=bool(np.all(cap >= 0) and not failures and (not need_gain or self.weights[gain >= 0].sum() >= self.gain_mass)))

    def enumerate(self, bounds):
        result = []
        for mask, p in enumerate(self.publications):
            result.append({"optional_mask": mask, "items": sorted(p),
                           "supported": self.assess(p, bounds, "lower"),
                           "possible": self.assess(p, bounds, "upper")})
        return result

    def query(self, targets, enumeration):
        target = set(targets)
        selected = [r for r in enumeration if target <= set(r["items"])]
        witnesses = {}
        for mode in ("supported", "possible"):
            valid = [r for r in selected if r[mode]["valid"]]
            witnesses[mode] = min(valid, key=lambda r: (len(r["items"]), r["items"]))[mode] if valid else None
        return {"targets": sorted(target), "status": "YES" if witnesses["supported"] else "UNKNOWN" if witnesses["possible"] else "NO",
                "target_containing_publications": len(selected),
                "supported_count": sum(r["supported"]["valid"] for r in selected),
                "possible_count": sum(r["possible"]["valid"] for r in selected), "witnesses": witnesses}

    def source_proof(self, bounds, targets=TRIPLE):
        """Exclude helpers through old glove, then exclude old boot retention."""
        mandatory = self.history | frozenset(targets)
        full_rows = list(range(len(self.supports)))
        old_glove_rows = [r for r in full_rows if "a00" in self.supports[r]]
        first = []
        removed = set()
        for helper in self.optional:
            if helper in mandatory:
                continue
            required_rows = self.active(mandatory | {helper})
            margins = max_min(bounds["retention_upper"], old_glove_rows, required_rows)
            excluded = bool(self.weights[margins >= 0].sum() < self.rho)
            if excluded:
                removed.add(helper)
            first.append(dict(helper=helper, source="a00", source_rows=old_glove_rows,
                              mandatory_competitor_rows=required_rows,
                              upper_margins_DPS=margins.tolist(), excluded=excluded))
        remaining = frozenset(self.items) - removed
        old_boot_rows = [r for r in self.active(remaining) if "x0" in self.supports[r]]
        upper = max_min(bounds["retention_upper"], old_boot_rows, self.active(mandatory))
        return {"step_1": first, "excluded_helpers": sorted(removed),
                "step_2": {"source": "x0", "remaining_ambient_items": sorted(remaining),
                           "source_rows": old_boot_rows, "mandatory_competitor_rows": self.active(mandatory),
                           "upper_margins_DPS": upper.tolist(), "excluded": bool(self.weights[upper >= 0].sum() < self.rho)},
                "only_legacy_source_obligations_used": True,
                "logic": "Every source row permitted by the full ambient menu is retained in step 1. A helper is excluded only if it forces failure of old glove retention. Step 2 retains all remaining helpers and excludes old boot retention against mandatory rows; adding competitors cannot repair it."}

    def mean_valid(self, publication):
        """Exact rational decisions on the saved decimal float64 mean table."""
        rows, history_rows = self.active(publication), self.active(self.history)
        means = [[Fraction(repr(float(v))) for v in row] for row in self.moments["means"]]
        rule = {k: Fraction(v) for k, v in self.manifest["rule"].items()}
        weights = [Fraction(str(v)) for v in self.world["task_weights"]]
        nq = len(weights)
        reference = [means[q][self.manifest["reference_indices"][q]] for q in range(nq)]
        front = [max(means[q][r] for r in rows) for q in range(nq)]
        if any(front[q] > (1 + rule["headroom"]) * reference[q] for q in range(nq)):
            return False
        for source in publication:
            source_rows = [r for r in rows if source in self.supports[r]]
            passing = [q for q in range(nq) if max(means[q][r] for r in source_rows) - front[q] + rule["tolerance"] * reference[q] >= 0]
            if sum(weights[q] for q in passing) < rule["retention_mass"]:
                return False
        passing = [q for q in range(nq) if front[q] - max(means[q][r] for r in history_rows) - rule["gain"] * reference[q] >= 0]
        return sum(weights[q] for q in passing) >= rule["gain_mass"]


def run(bundle, output, resume=False, prior_certificate=None, prior_pairs=None):
    bundle, output = Path(bundle).resolve(), Path(output).resolve()
    native = bundle / "data/native" / WORLD
    relative_inputs = ["NATIVE_CATALOGUES.jsonl", "PROTOCOL_FROZEN.json", "data/native/ANALYSIS_MANIFEST.json",
                       "code/wowfs/experiments/co_native_analysis.py"]
    relative_inputs += [f"data/native/{WORLD}/{name}" for name in
                       ("MOMENTS.npz", "MOMENTS_READABLE.json", "BOUNDS.npz", "BOUNDS_MANIFEST.json", "base/CONFIDENCE_CERTIFICATES.json")]
    inputs = {str(bundle / name): sha(bundle / name) for name in relative_inputs}
    inputs[str(Path(__file__).resolve())] = sha(__file__)
    if prior_certificate:
        inputs[str(Path(prior_certificate).resolve())] = sha(prior_certificate)
    if prior_pairs:
        inputs[str(Path(prior_pairs).resolve())] = sha(prior_pairs)
    identity = {"inputs": inputs, "world_id": WORLD, "triple": TRIPLE,
                "epsilon_interval": [.01, .011], "new_native_battles": 0, "additional_alpha": 0,
                "prior_certificate": str(prior_certificate) if prior_certificate else None,
                "prior_pairs": str(prior_pairs) if prior_pairs else None}
    identity = json.loads(json.dumps(identity))
    manifest_path = output / "DRUID_RUN_MANIFEST.json"
    if manifest_path.exists():
        if not resume:
            raise ValueError("Existing run requires --resume; frozen outputs are not overwritten")
        if json.loads(manifest_path.read_text()) != identity:
            raise ValueError("Resume input/configuration/source hash mismatch")
        completed = output / "DRUID_TRIPLE_RECHECK.json"
        if completed.exists():
            return json.loads(completed.read_text())
    else:
        output.mkdir(parents=True, exist_ok=True)
        dump(manifest_path, identity)
    archive_manifest = {x["path"]: x["sha256"] for x in json.loads((bundle / "REVIEW_MANIFEST.json").read_text())["files"]}
    manifest_checks = {name: inputs[str(bundle / name)] == archive_manifest.get(name) for name in relative_inputs}
    assert all(manifest_checks.values()), manifest_checks
    protocol = json.loads((bundle / "PROTOCOL_FROZEN.json").read_text())
    frozen_code_hash = inputs[str(bundle / "code/wowfs/experiments/co_native_analysis.py")]
    assert frozen_code_hash == protocol["source_hashes"]["src/wowfs/experiments/co_native_analysis.py"]
    world = next(w for w in map(json.loads, (bundle / "NATIVE_CATALOGUES.jsonl").read_text().splitlines()) if w["world_id"] == WORLD)
    moments = json.loads((native / "MOMENTS_READABLE.json").read_text())
    npz = np.load(native / "MOMENTS.npz")
    bounds_manifest = json.loads((native / "BOUNDS_MANIFEST.json").read_text())
    assert np.array_equal(npz["means"], moments["means"])
    assert np.array_equal(npz["covariance"], moments["covariance"])
    assert moments["archive_sha256"] == sha(native / "MOMENTS.npz")
    bounds = reconstruct(npz["means"], npz["covariance"], int(npz["N"]), bounds_manifest)
    saved_bounds = np.load(native / "BOUNDS.npz")
    bound_errors = {k: float(np.max(np.abs(v - saved_bounds[k]))) for k, v in bounds.items()}
    sign_checks = {k: bool(np.array_equal(v >= 0, saved_bounds[k] >= 0)) for k, v in bounds.items()}
    assert all(sign_checks.values()) and max(bound_errors.values()) < 1e-10
    ref_lower, ref_upper = reference_intervals(bounds, .01, .01)
    domain = IndependentDomain(world, moments, bounds_manifest)
    queries = [(), ("a04",), ("x1",), ("x3",), ("a04", "x1"), ("a04", "x3"), ("x1", "x3"), TRIPLE]
    endpoint_results = []
    for epsilon in [.01, .011]:
        shifted = shifted_retention(bounds, epsilon - .01, ref_lower, ref_upper)
        checkpoint = output / f"PUBLICATIONS_e{epsilon:.3f}.json"
        if checkpoint.exists():
            enumeration = json.loads(checkpoint.read_text())
        else:
            enumeration = domain.enumerate(shifted)
            dump(checkpoint, enumeration)
        answers = [domain.query(query, enumeration) for query in queries]
        triple_rows = [r for r in enumeration if set(TRIPLE) <= set(r["items"])]
        proof = domain.source_proof(shifted)
        endpoint_results.append(dict(epsilon=epsilon, queries=answers, source_certificate=proof,
            initial={endpoint: domain.assess(domain.history, shifted, endpoint, need_gain=False) for endpoint in ("lower", "upper")},
            triple_exclusion={"enumerated_supersets": len(triple_rows),
                "all_cap_supported": all(r["supported"]["cap_pass"] for r in triple_rows),
                "all_gain_supported": all(r["supported"]["gain_pass"] for r in triple_rows),
                "all_retention_excluded": all(r["possible"]["retention_failures"] for r in triple_rows),
                "failed_sources_occurrences": dict(Counter(s for r in triple_rows for s in r["possible"]["retention_failures"]))}))
    first = json.loads((output / "PUBLICATIONS_e0.010.json").read_text())
    frozen_certificate = json.loads((native / "base/CONFIDENCE_CERTIFICATES.json").read_text())
    registered = [{"query_id": q["query_id"], "required": q["required"], "saved_status": q["status"],
                   "independent_status": domain.query(q["required"], first)["status"]} for q in frozen_certificate["queries"]]
    assert all(x["saved_status"] == x["independent_status"] for x in registered)
    expected = ["YES"] * 7 + ["NO"]
    reproduce = all([q["status"] for q in end["queries"]] == expected for end in endpoint_results)
    proof_pass = all(end["source_certificate"]["step_2"]["excluded"] for end in endpoint_results)
    prior_comparisons = []
    if prior_certificate:
        prior = json.loads(Path(prior_certificate).read_text())
        assert prior["world"] == WORLD
        for old in prior["results"]:
            epsilon = old["tolerance"]
            shifted = shifted_retention(bounds, epsilon - .01, ref_lower, ref_upper)
            actual = domain.source_proof(shifted, old["target"])
            errors = [abs(a - b) for a, b in zip(actual["step_2"]["upper_margins_DPS"], old["final_upper_retention_DPS"])]
            for saved_helper in old["excluded_helpers"]:
                now = next(h for h in actual["step_1"] if h["helper"] == saved_helper["item"])
                errors.extend(abs(a - b) for a, b in zip(now["upper_margins_DPS"], saved_helper["upper_retention_DPS"]))
            same = (actual["excluded_helpers"] == [h["item"] for h in old["excluded_helpers"]]
                    and actual["step_2"]["remaining_ambient_items"] == old["remaining_items"]
                    and actual["step_2"]["excluded"] == old["all_width_exclusion_supported"]
                    and max(errors) < 1e-10)
            prior_comparisons.append(dict(target=old["target"], epsilon=epsilon, reproduced=same,
                saved_proof_supported=old["all_width_exclusion_supported"],
                independent_proof_supported=actual["step_2"]["excluded"], maximum_margin_error_DPS=max(errors),
                independent_certificate=actual,
                interpretation="Failed sufficient two-step proof is unresolved by this proof, not a feasible-target claim"))
        assert all(c["reproduced"] for c in prior_comparisons)
    pair_comparisons = []
    if prior_pairs:
        prior = json.loads(Path(prior_pairs).read_text())
        for old in prior["triples"]:
            triple = domain.query(old["target"], first)
            for pair in old["pair_witnesses"]:
                now = domain.assess(frozenset(pair["published"]), bounds, "lower")
                saved = pair["bounds"]
                errors = [abs(min(now["cap_margins_DPS"]) - saved["cap_margin"])]
                errors += [abs(a - b) for a, b in zip(now["gain_margins_DPS"], saved["gain_margin_DPS"])]
                for source, margins in saved["source_margins_DPS"].items():
                    errors += [abs(a - b) for a, b in zip(now["sources"][source]["margins_DPS"], margins)]
                pair_comparisons.append(dict(triple=old["target"], pair=pair["pair"], publication=pair["published"],
                    saved_witness_reproduced=bool(now["valid"] and max(errors) < 1e-10),
                    maximum_margin_error_DPS=max(errors), independent_triple_status=triple["status"]))
        assert all(p["saved_witness_reproduced"] for p in pair_comparisons)
    mean_publications = [p for p in domain.publications if domain.mean_valid(p)]
    mean_queries = [{"targets": list(q), "status": "YES" if any(set(q) <= p for p in mean_publications) else "NO"} for q in queries]
    result = dict(status="PASS" if reproduce and proof_pass else "FAIL", world_id=WORLD, variant="base",
        context=world["context"], target_aliases=dict(zip("ABC", TRIPLE)),
        target_names={"A": world["candidates"][4]["item_name"], "B": world["partners"][1]["item_name"], "C": world["partners"][3]["item_name"]},
        fixed_contract={"history": world["history"], "items": domain.items, "tasks": world["tasks"], "weights": world["task_weights"], "bounds_manifest": bounds_manifest},
        independent_method="Scalar coefficient-vector moment reconstruction and direct publication enumeration; no certificate query service or original inference/replay imports",
        physical_configurations=32, complete_publications=len(domain.publications), all_physical_cap_safe=bool(np.all(bounds["cap_lower"] >= 0)),
        minimum_physical_cap_lower_margin_DPS=float(bounds["cap_lower"].min()),
        event_coverage={"frozen_inference_source_hash_matches_protocol": True,
            "actual_code_evidence": "finite_bounds enumerates (c,d) for every c,d in range(m); diagonals included. cap covers every c. The reconstructed coefficient-byte hash equals the frozen manifest.",
            "coefficient_sha256": bounds_manifest["coefficient_sha256"], "new_contrasts": 0,
            "reference_intervals_from_original_diagonals": {"lower": ref_lower.tolist(), "upper": ref_upper.tolist()},
            "population_scope": bounds_manifest["population_method"]},
        whole_interval={"epsilon": [.01, .011], "status": "CERTIFIED" if reproduce and proof_pass else "UNKNOWN",
            "argument": "The base endpoint certifies all pairs and proper subsets. The permissive .011 endpoint excludes every triple superset. All reference lower bounds are positive, so retention support is monotone in e. Cap/gain and the fixed domain are unchanged. Bounds R_e = R_.01 + (e-.01)S follow from the same covered diagonal event for every real e in the interval.",
            "new_t_intervals_at_changed_e": False},
        endpoints=endpoint_results, registered_query_replay=registered, exact_finite_mean_queries=mean_queries,
        saved_two_step_certificate_replay={"status": "NOT_SUPPORTED_MISSING_ARTIFACT" if prior_certificate is None else "PASS",
            "prior_path": prior_certificate,
            "comparisons": prior_comparisons,
            "note": "All saved rows are retained, including failed sufficient proofs at e=.012 and for the a06 triple. These failures are not converted into target YES or NO."},
        saved_pair_witness_replay={"status": "PASS" if prior_pairs else "NOT_SUPPORTED_MISSING_ARTIFACT", "prior_path": prior_pairs, "comparisons": pair_comparisons},
        attribution={"legacy_history_retention": True, "legacy_only_exclusion_proved": proof_pass,
            "power_conflict": False, "target_self_retention_needed_for_exclusion": False,
            "helper_self_retention_needed_for_exclusion": False,
            "scope": "Sufficient mechanism attribution; other individual publications can also fail target/helper obligations."},
        validation={"review_manifest_inputs": manifest_checks, "bound_max_abs_errors_DPS": bound_errors, "bound_signs_equal": sign_checks},
        evidence_classification="POST-HOC CONSEQUENCE OF FROZEN EVENT", new_native_battles=0, additional_alpha=0,
        finished_utc=datetime.now(timezone.utc).isoformat())
    dump(output / "DRUID_TRIPLE_RECHECK.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--prior-certificate")
    parser.add_argument("--prior-pairs")
    args = parser.parse_args()
    result = run(args.bundle, args.output, args.resume, args.prior_certificate, args.prior_pairs)
    print(json.dumps({"status": result["status"], "world": result["world_id"], "interval": result["whole_interval"]["status"]}))


if __name__ == "__main__":
    main()
