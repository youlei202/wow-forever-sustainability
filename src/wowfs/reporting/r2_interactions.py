"""Render only the frozen primary native interaction family; no new combat."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np

from wowfs.experiments.r2_analysis import factorial, group_factorials
from wowfs.paths import atomic_json, setup_paths


LABELS = {
    ("shared_active", "short_burst", "native_reck"):
        "Flask × Cloudkeeper | 30 s, 1 target\nRecklessness policy",
    ("shared_active", "four_target", "native_no_reck"):
        "Flask × Cloudkeeper | 90 s, 4 targets\nNo-Recklessness policy",
    ("shared_active", "sustained", "native_reck"):
        "Flask × Cloudkeeper | 180 s, 1 target\nRecklessness policy",
    ("haste_extra", "four_target", "native_reck"):
        "Empyrean × Hand of Justice | 90 s, 4 targets\nRecklessness; Felstriker effect off",
    ("extra_resource", "four_target", "native_no_reck"):
        "Ironfoe × Heroism × Hand of Justice | 90 s, 4 targets\nThree-way contrast; no-Recklessness",
    ("extra_resource", "sustained", "native_reck"):
        "Ironfoe × Heroism | 180 s, 1 target\nRecklessness; Hand of Justice effect off",
}


def primary_records(run: Path, root: Path):
    manifest = json.loads((run / "PRIMARY_CONTRASTS.json").read_text())
    result = json.loads((run / "RESULTS.json").read_text())
    if result["errors"]:
        raise ValueError("Native confirmation has recorded failed cells")
    keys = [(r["case"], r["task"], r["strategy"], r["race"], r["mask"])
            for r in result["rows"] if r is not None]
    if len(set(keys)) != len(keys):
        raise ValueError("Duplicate native factorial cells cannot be silently merged")
    groups = group_factorials(result["rows"])
    records = []
    for target in manifest["contrasts"]:
        group_key = (target["case"], target["task"], target["strategy"], manifest["race"])
        cells = groups[group_key]
        # Discovery selected two-effect contrasts with the optional third effect
        # disabled. Preserve that convention; do not choose a slice after seeing
        # confirmation. The original PRIMARY_CONTRASTS.json remains untouched.
        selected = {m: cells[m] for m in range(2 ** target["effects"])}
        for cell in selected.values():
            key = cell["cache_key"]
            request = json.loads((root / "cache/r2-discovery/native" / key[:2]
                                  / key / "input.json").read_text())
            options = request["request"]["simOptions"]
            if (int(options["randomSeed"]) != manifest["seed_start"]
                    or options["iterations"] != manifest["iterations"]
                    or len(cell["dps_samples"]) != manifest["iterations"]):
                raise ValueError("Primary cell does not match frozen seed/iteration count")
        samples = {m: cell["dps_samples"] for m, cell in selected.items()}
        estimate = factorial(samples, target["effects"], manifest["primary_family_size"])
        contrast = sum((-1) ** (target["effects"] - m.bit_count()) * np.asarray(v)
                       for m, v in samples.items())
        row = {**target, "race": manifest["race"], **estimate,
               "third_effect_state_for_pair": "disabled" if len(cells) == 8 and target["effects"] == 2 else None,
               "max_abs_seed_contrast": float(np.max(np.abs(contrast))),
               "cell_mean_dps": {str(m): float(np.mean(v)) for m, v in samples.items()},
               "cache_keys": {str(m): c["cache_key"] for m, c in selected.items()},
               "output_sha256": {str(m): c["output_sha256"] for m, c in selected.items()}}
        records.append(row)
    return manifest, records


def export_shared_trace(root: Path, out: Path):
    run = root / "runs/r2-discovery/event-traces-v1"
    if not (run / "RESULTS.json").exists():
        return
    data = json.loads((run / "RESULTS.json").read_text())
    selected = [r for r in data["rows"] if r and r["case"] == "shared_active"]
    if {r["mask"] for r in selected} != set(range(4)) or len(selected) != 4:
        raise ValueError("Shared cooldown trace requires all four masks exactly once")
    directory = out / "selected_evidence/shared_cooldown_seed_92427001"
    directory.mkdir(parents=True, exist_ok=True)
    receipts = []
    for row in sorted(selected, key=lambda r: r["mask"]):
        key = row["cache_key"]
        cache = root / "cache/r2-discovery/native" / key[:2] / key
        raw = gzip.decompress((cache / "output.json.gz").read_bytes())
        output = json.loads(raw)
        request = json.loads((cache / "input.json").read_text())
        if (int(request["request"]["simOptions"]["randomSeed"]) != 92427001
                or request["request"]["simOptions"]["iterations"] != 1):
            raise ValueError("Trace seed or iteration count mismatch")
        stem = f"mask_{row['mask']}"
        (directory / f"{stem}.events.log").write_text(output["logs"])
        atomic_json(directory / f"{stem}.input.json", request)
        invocation = json.loads((cache / "invocation.json").read_text())
        receipts.append({"mask": row["mask"], "cache_key": key,
                         "dps": row["dps_samples"][0],
                         "output_sha256": hashlib.sha256(raw).hexdigest(),
                         "invocation": invocation,
                         "matching_log_lines": [
                             {"line": n, "text": line}
                             for n, line in enumerate(output["logs"].splitlines(), 1)
                             if "24427" in line or "14554" in line]})
    atomic_json(directory / "TRACE_RECEIPT.json", {"records": receipts,
                "scope": "One existing confirmation seed replayed with logs; not independent confirmation data"})


def render(run: Path, out: Path, root: Path):
    manifest, records = primary_records(run, root)
    out.mkdir(parents=True, exist_ok=True)
    provenance = {name: hashlib.sha256((run / name).read_bytes()).hexdigest()
                  for name in ("PRIMARY_CONTRASTS.json", "RESULTS.json", "PROTOCOL.json")}
    atomic_json(out / "CONFIRMATION_PRIMARY.json", {
        "run_directory": str(run), "source_sha256": provenance,
        "manifest": manifest, "records": records,
        "interpretation": "Fixed-configuration native community-engine contrasts; no optimized/global/20-round claim",
    })
    fields = ["case", "task", "strategy", "race", "effects", "iterations", "family",
              "estimate", "se", "ci_low", "ci_high", "direction",
              "degenerate_observed_variance", "third_effect_state_for_pair",
              *[f"mean_mask_{m}" for m in range(8)]]
    with (out / "CONFIRMATION_PRIMARY.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for record in records:
            row = {k: record.get(k) for k in fields}
            row.update({f"mean_mask_{m}": v for m, v in record["cell_mean_dps"].items()})
            writer.writerow(row)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False})
    figure, ax = plt.subplots(figsize=(11, 6.3))
    for i, row in enumerate(records):
        if row["degenerate_observed_variance"]:
            ax.plot(0, i, marker="D", markerfacecolor="white", markeredgecolor="#66717c", ms=7)
            ax.annotate("Numerical additivity\nobserved; unresolved", (0, i),
                        xytext=(9, 0), textcoords="offset points", va="center", fontsize=9,
                        color="#66717c")
        else:
            color = "#a43d42" if row["direction"] == "negative" else "#355b7c"
            ax.errorbar(row["estimate"], i,
                        xerr=[[row["estimate"] - row["ci_low"]], [row["ci_high"] - row["estimate"]]],
                        fmt="o", color=color, markersize=6, capsize=4, linewidth=1.5)
    ax.axvline(0, color="#aab1b7", linewidth=1, linestyle="--", zorder=0)
    ax.set_yticks(range(len(records)), [LABELS[(r["case"], r["task"], r["strategy"])] for r in records])
    ax.invert_yaxis()
    ax.set_xlim(-22.5, 16)
    ax.set_xlabel("Factorial interaction in DPS (negative = antagonistic)")
    ax.grid(axis="x", color="#e5e8eb", linewidth=0.7)
    ax.set_axisbelow(True)
    figure.suptitle("Shared cooldown conflicts confirmed; proposed positive amplification remains unresolved",
                   x=0.02, ha="left", fontsize=12, fontweight="bold")
    figure.text(0.02, 0.925,
                "Human Warrior · 128 fresh paired seeds per cell · six frozen primary contrasts",
                fontsize=10, color="#475461")
    figure.text(0.02, 0.02,
                "Intervals: paired Student-t with Bonferroni family = 6 (approximate for nonnormal contrasts).\n"
                "Community Forever engine; fixed gear and policies. No live-server or 20-round extension claim.",
                fontsize=8.5, color="#475461")
    figure.subplots_adjust(left=0.42, right=0.98, top=0.85, bottom=0.16)
    figures = out / "figures"
    figures.mkdir(exist_ok=True)
    for extension in ("png", "pdf"):
        figure.savefig(figures / f"primary_interactions.{extension}", dpi=180)
    plt.close(figure)
    export_shared_trace(root, out)
    return records


def main():
    root = setup_paths()
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, default=root / "runs/r2-discovery/confirmation-v1")
    parser.add_argument("--out", type=Path, default=root / "artifacts/r2-discovery/latest")
    args = parser.parse_args()
    records = render(args.run, args.out, root)
    print(json.dumps({"primary_contrasts": len(records), "output": str(args.out)}))


if __name__ == "__main__":
    main()
