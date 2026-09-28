"""Independent, exact finite implementation checks for the target interface note.

This module deliberately imports no wowfs checker or solver.  The construction
is transcribed from the attachment and checked against the supplied proof PDF.
All response comparisons use integer nanounits; these are abstract tables,
never native measurements.  A completed run is immutable; --resume checks both
the configuration hash and this source hash before reusing any checkpoint.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import random
from pathlib import Path

SCALE = 10**9
PROOF_PATH = Path('/work/Users/leiyo/wow-forever-sustainability-work/inputs/minimal-interface-2026-09-27/WoW_Minimal_Interface_Codex_Handoff/wow_minimal_interface_proof.pdf')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def submasks(mask):
    current = mask
    yield current
    while current:
        current = (current - 1) & mask
        yield current


def downclosure(maxima):
    return frozenset(s for m in maxima for s in submasks(m))


def maximal(family):
    return tuple(sorted(m for m in family if not any(m != k and m & k == m for k in family)))


def all_downsets(n):
    """Generate every downset, including the empty family, without duplicates."""
    if n == 0:
        return (frozenset(), frozenset({0}))
    smaller = all_downsets(n - 1)
    bit = 1 << (n - 1)
    return tuple(lower | frozenset(bit | x for x in upper)
                 for lower in smaller for upper in smaller if upper <= lower)


def construction(n, family):
    family = frozenset(family)
    if family != downclosure(family) or any(x < 0 or x >= 1 << n for x in family):
        raise ValueError("Expected a downward closed target family")
    selectors = maximal(family)
    # Rows: old glove o, helper s, then targets x_i. Columns: r then b_A.
    rows = [[100] + [102] * len(selectors), [102] * (len(selectors) + 1)]
    rows += [[102] + [102 if a >> i & 1 else 104 for a in selectors] for i in range(n)]
    return [[v * SCALE for v in row] for row in rows], selectors


def evaluate_publication(table, gloves, boots):
    """Literal one-task gain, cap and retention predicate; both old items stay."""
    if 0 not in gloves or 0 not in boots:
        return False
    frontier = max(table[g][b] for g in gloves for b in boots)
    return (frontier >= table[0][0] + SCALE and frontier <= 110 * SCALE
            and all(max(table[g][b] for b in boots) >= frontier - SCALE for g in gloves)
            and all(max(table[g][b] for g in gloves) >= frontier - SCALE for b in boots))


def exact_family(table):
    """Compile all target answers with a complete independent finite algorithm.

    Enumerate every glove subset containing o. At each attainable frontier y,
    include all boots whose column maximum is in [y-1,y]. This is complete:
    any valid publication uses only such boots; adding the remaining such boots
    cannot increase its frontier, violate a boot's retention, or remove a glove
    witness. Check mandatory r, gain, cap, attainment and every selected glove.
    This argument does not use the claimed universal-construction identity.
    """
    n = len(table) - 2
    valid_projections = set()
    witnesses = {}
    for target in range(1 << n):
        target_rows = [i + 2 for i in range(n) if target >> i & 1]
        for helper in (False, True):
            gloves = [0] + ([1] if helper else []) + target_rows
            columns = [max(table[g][b] for g in gloves) for b in range(len(table[0]))]
            ceiling = min(110 * SCALE, columns[0] + SCALE, max(table[0]) + SCALE)
            levels = sorted({v for v in columns if table[0][0] + SCALE <= v <= ceiling})
            for level in levels:
                boots = [b for b, v in enumerate(columns) if level - SCALE <= v <= level]
                if 0 not in boots:
                    continue
                if all(max(table[g][b] for b in boots) >= level - SCALE for g in gloves):
                    if not evaluate_publication(table, gloves, boots):
                        raise AssertionError("Independent witness failed literal evaluation")
                    valid_projections.add(target)
                    witnesses[str(target)] = {"gloves": gloves, "boots": boots, "frontier": level}
                    break
            if target in valid_projections:
                break
    return downclosure(valid_projections), witnesses


def brute_family(table):
    """Deliberately slow publication powerset oracle for small unit fixtures."""
    n = len(table) - 2
    projections = set()
    for gm in range(1 << (len(table) - 1)):
        gloves = [0] + [i + 1 for i in range(len(table) - 1) if gm >> i & 1]
        target = sum(1 << i for i in range(n) if i + 2 in gloves)
        for bm in range(1 << (len(table[0]) - 1)):
            boots = [0] + [b + 1 for b in range(len(table[0]) - 1) if bm >> b & 1]
            if evaluate_publication(table, gloves, boots):
                projections.add(target)
    # Deliberately avoid the production submask/downclosure helper here.
    return frozenset(query for query in range(1 << n)
                     if any(query & projection == query for projection in projections))


def perturb(table, eta, seed):
    # Independent pseudorandom U[-eta,eta] draws, rounded to exact nanounits.
    rng = random.Random(seed)
    return [[v + round(rng.uniform(-eta, eta) * SCALE) for v in row] for row in table]


def case_check(case, eta=0, seed=None):
    n, family = case["n"], frozenset(case["family"])
    original, selectors = construction(n, family)
    if case["kind"] == "high_order_pair" and case["id"].endswith("-full"):
        original, selectors = construction(n, range((1 << n)-1))
        original = [[102*SCALE if v == 104*SCALE else v for v in row] for row in original]
    table = perturb(original, eta, seed) if eta else original
    actual, witnesses = exact_family(table)
    differences = sorted(actual ^ family)
    row = {"case": case["id"], "kind": case["kind"], "n": n, "eta": eta,
           "seed": seed, "target_query_count": 1 << n, "family_size": len(family),
           "selector_count": len(selectors), "response_table_sha256": digest(table),
           "actual_family_size": len(actual), "family_unchanged": not differences,
           "guarantee_expected": eta < .5, "mismatched_target_masks": differences}
    if differences:
        row["expected_family"] = sorted(family)
        row["actual_family"] = sorted(actual)
        row["response_table_nanounits"] = table
        row["witnesses"] = {str(d): witnesses.get(str(d)) for d in differences if d in actual}
    return row


def make_cases(config):
    cases = []
    for n in range(5):
        for i, family in enumerate(all_downsets(n)):
            cases.append({"id": f"exhaustive-n{n}-{i}", "kind": "all_downsets",
                          "n": n, "family": sorted(family)})
    rng = random.Random(config["seed"])
    for n in (5, 6, 7):
        for i in range(config["random_downsets_per_n"]):
            maxima = rng.sample(range(1 << n), rng.randrange((1 << n) + 1))
            cases.append({"id": f"random-n{n}-{i}", "kind": "random_downset",
                          "n": n, "family": sorted(downclosure(maxima))})
    for r in range(1, 11):
        n = r + 1
        for full in (False, True):
            cases.append({"id": f"order-{r}-{'full' if full else 'punctured'}",
                          "kind": "high_order_pair", "n": n,
                          "family": list(range((1 << n) - (not full)))})
    return cases


def semantic_check():
    history, targets = {"o", "r"}, {"x0", "x1"}
    interfaces = [[history | {"x0", "helper_a"}, history | {"x0", "helper_b"}],
                  [history | {"x0", "helper_c"}]]
    queries = [set(s) for k in range(3) for s in itertools.combinations(sorted(targets), k)]
    answers = [[any(d <= p for p in interface) for d in queries] for interface in interfaces]
    projections = [[sorted(p & targets) for p in interface] for interface in interfaces]
    return {"scope": "abstract set interfaces, not native data", "history": sorted(history),
            "target_universe": sorted(targets), "full_interfaces": [[sorted(p) for p in f] for f in interfaces],
            "raw_projections": projections, "projected_maximal_interfaces": [[["x0"]], [["x0"]]],
            "queries": [sorted(d) for d in queries], "answers": answers,
            "all_target_query_answers_identical": answers[0] == answers[1],
            "helper_witnesses_differ": interfaces[0] != interfaces[1],
            "target_semantics_preserve_helper_details": False}


def pair_exclusion_check(p, out, seed):
    explicit = [[2 * i + ((choice >> i) & 1) for i in range(p)] for choice in range(1 << p)]
    symbolic = {"target_count": 2 * p, "forbidden_pairs": [[2*i, 2*i+1] for i in range(p)]}
    payload = canonical(explicit)
    (out / f"symbolic-p{p}-explicit.json").write_bytes(payload)
    (out / f"symbolic-p{p}-rules.json").write_bytes(canonical(symbolic))
    # Inverted bitsets answer the explicit antichain's containment query. They
    # are an audit index, excluded from the explicit serialization comparison.
    postings = [bytearray(((1 << p) + 7) // 8) for _ in range(2*p)]
    for k, member in enumerate(explicit):
        for item in member:
            postings[item][k // 8] |= 1 << (k % 8)
    postings = [int.from_bytes(b, "little") for b in postings]
    all_members = (1 << (1 << p)) - 1
    full = p <= 8
    if full:
        queries = range(1 << (2*p))
        checked = len(queries)
    else:
        rng = random.Random(seed + p)
        queries = {0, (1 << (2*p))-1}
        queries.update(rng.randrange(1 << (2*p)) for _ in range(10000))
        queries.update(sum(1 << item for item in member) for member in explicit)
        queries.update(3 << (2*i) for i in range(p))
        checked = len(queries)
    mismatch = []
    physical_failures = []
    table = [[102*SCALE for _ in range(p+2)] for _ in range(p+2)]
    table[0][0] = 100*SCALE
    for i in range(p):
        table[i+2][i+2] = 104*SCALE
    for query in queries:
        candidate = all_members
        for item in range(2*p):
            if query >> item & 1:
                candidate &= postings[item]
                if not candidate:
                    break
        rule_answer = all(query & (3 << (2*i)) != (3 << (2*i)) for i in range(p))
        if bool(candidate) != rule_answer:
            mismatch.append(query)
        if rule_answer:
            gloves = [0, 1] + [i+2 for i in range(p) if query >> (2*i) & 1]
            boots = [0, 1] + [i+2 for i in range(p) if query >> (2*i+1) & 1]
            valid = evaluate_publication(table, gloves, boots)
        else:
            # An active diagonal104 forces F>=104 while mandatory old o has
            # best possible value102, even with every optional helper.
            valid = max(table[0]) < 104*SCALE-SCALE
        if not valid:
            physical_failures.append(query)
    structural = (len({tuple(x) for x in explicit}) == 1 << p
                  and all(len(member) == p and {v//2 for v in member} == set(range(p)) for member in explicit))
    return {"p": p, "target_count": 2*p, "explicit_antichain_count": len(explicit),
            "explicit_serialization_bytes": len(payload), "symbolic_rule_count": p,
            "symbolic_serialization_bytes": len(canonical(symbolic)),
            "query_equivalence": not mismatch and structural and not physical_failures,
            "query_equivalence_scope": "exhaustive" if full else "sampled_and_all_maxima_plus_structural_identity",
            "queried_target_count": checked, "full_target_universe_count": 1 << (2*p),
            "structural_identity_checked": structural, "mismatched_query_count": len(mismatch),
            "physical_realization_checked": not physical_failures,
            "physical_component_count": 2*p+4, "physical_configuration_count": (p+2)**2,
            "explicit_sha256": hashlib.sha256(payload).hexdigest()}


def atomic_json(path, value):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    temp.replace(path)


def run(out, *, resume=False, random_count=64, seed=927202601):
    out.mkdir(parents=True, exist_ok=True)
    config = {"format": "wowfs-minimal-interface-theory-v1", "seed": seed,
              "random_downsets_per_n": random_count, "etas": [.1, .25, .49, .5, .51],
              "perturbation_replicates": 1, "scale": SCALE, "workers": 1,
              "proof_note_path": str(PROOF_PATH),
              "proof_note_sha256": hashlib.sha256(PROOF_PATH.read_bytes()).hexdigest(),
              "proof_note_status": "read_all_five_pages; no original checker imported"}
    source_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    checkpoint = out / "CHECKPOINT.json"
    identity = {"config_sha256": digest(config), "source_sha256": source_hash}
    if checkpoint.exists():
        if not resume:
            raise ValueError("Run exists; use --resume with unchanged source/configuration")
        saved = json.loads(checkpoint.read_text())
        if saved["identity"] != identity:
            raise ValueError("Resume rejected: configuration/source hash mismatch")
    else:
        if resume:
            raise ValueError("No checkpoint to resume")
        saved = {"identity": identity, "config": config, "checks": [], "completed_cases": []}
        atomic_json(checkpoint, saved)
    if saved.get("complete"):
        print(json.dumps({"status": "already_complete", **identity}), flush=True)
        return
    cases = make_cases(config)
    atomic_json(out / "FROZEN_CASES.json", cases)
    for i, case in enumerate(cases):
        if case["id"] in saved["completed_cases"]:
            continue
        rows = [case_check(case)]
        rows += [case_check(case, eta, seed + i*101 + j) for j, eta in enumerate(config["etas"])]
        saved["checks"].extend(rows)
        saved["completed_cases"].append(case["id"])
        atomic_json(checkpoint, saved)
        if i % 20 == 0 or i == len(cases)-1:
            print(json.dumps({"completed_cases": i+1, "total_cases": len(cases)}), flush=True)
    checks = saved["checks"]
    # The endpoint has no strict-margin theorem guarantee. This deliberately
    # chosen corner is separate from the independent uniform perturbation runs.
    corner_table, _ = construction(2, {0, 1, 2})
    corners = []
    for eta in config["etas"]:
        table = [[v - round(eta*SCALE) if v == 104*SCALE else v + round(eta*SCALE)
                  for v in row] for row in corner_table]
        actual, witnesses = exact_family(table)
        corners.append({"eta": eta, "kind": "deterministic_boundary_corner_not_uniform_sample",
                        "expected_family": [0, 1, 2], "actual_family": sorted(actual),
                        "family_unchanged": actual == {0, 1, 2},
                        "response_table_nanounits": table, "witnesses": witnesses})
    pairs = []
    for r in range(1, 11):
        n = r+1
        punctured = next(row for row in checks if row["case"] == f"order-{r}-punctured" and row["eta"] == 0)
        complete = next(row for row in checks if row["case"] == f"order-{r}-full" and row["eta"] == 0)
        pairs.append({"r": r, "n": n, "all_queries_up_to_r_agree": punctured["family_unchanged"] and complete["family_unchanged"],
                      "low_order_query_count": (1 << n)-1, "distinguishing_target": (1 << n)-1,
                      "minimal_obstruction_order": n})
    failures = [row for row in checks if row["guarantee_expected"] and not row["family_unchanged"]]
    summary = {"identity": identity, "config": config, "scope": "abstract exact finite implementation checks; no native runs",
               "case_count": len(cases), "check_count": len(checks),
               "nominal_checks": len(cases), "uniform_perturbation_checks": len(cases)*len(config["etas"]),
               "enumerated_downsets_by_n": {str(n): len(all_downsets(n)) for n in range(5)},
               "empty_family_cases_retained": [row for row in checks if row["family_size"] == 0],
               "expected_guarantee_failure_count": len(failures), "expected_guarantee_failures": failures,
               "no_guarantee_uniform_changes": [row for row in checks if not row["guarantee_expected"] and not row["family_unchanged"]],
               "perturbation_distribution": "independent Python Random.uniform(-eta,eta) draws per physical response, rounded to exact integer nanounits",
               "high_order_pairs": pairs, "boundary_corners": corners,
               "checks": checks, "passed_within_stated_strict_guarantee": not failures}
    atomic_json(out / "UNIVERSAL_CONSTRUCTION_CHECKS.json", summary)
    atomic_json(out / "SEMANTIC_MINIMALITY_CHECKS.json", semantic_check())
    symbolic = [pair_exclusion_check(p, out, seed) for p in (4, 8, 12, 16)]
    with (out / "SYMBOLIC_VS_ANTICHAIN.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(symbolic[0]))
        writer.writeheader()
        writer.writerows(symbolic)
    saved["complete"] = True
    atomic_json(checkpoint, saved)
    print(json.dumps({"status": "complete", "case_count": len(cases), "check_count": len(checks),
                      "expected_guarantee_failure_count": len(failures)}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--random-downsets-per-n", type=int, default=64)
    parser.add_argument("--seed", type=int, default=927202601)
    args = parser.parse_args()
    run(args.out, resume=args.resume, random_count=args.random_downsets_per_n, seed=args.seed)


if __name__ == "__main__":
    main()
