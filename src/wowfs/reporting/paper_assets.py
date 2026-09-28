"""Rebuild the current manuscript's displays without changing frozen evidence.

The original numerical generators run in a fresh external copy. Matplotlib
views preserve numbers, units and bound direction, but are not TikZ facsimiles.
"""
from __future__ import annotations

import csv
import hashlib
import html
from importlib.metadata import version
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


def _json(path):
    return json.loads(Path(path).read_text())


def _csv(path):
    with Path(path).open(newline="") as stream:
        return list(csv.DictReader(stream))


def _hashes(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()
            and "__pycache__" not in p.parts and p.suffix != ".pyc"}


def prepare_paper_assets(source_root, output_root, *, checks=True):
    """Stage evidence, replay numerical checks, and run the original generators.

    A completed directory is reusable only for identical source/code hashes.
    Incomplete or changed runs require a fresh output directory. The archived
    source root is never modified. ``checks=False`` regenerates assets from
    saved checked evidence and explicitly reports that replay was not run.
    """
    source_root, output_root = Path(source_root).resolve(), Path(output_root).resolve()
    if not (source_root / "main.tex").is_file():
        raise FileNotFoundError(f"Current manuscript source is missing: {source_root}")
    repo = Path(__file__).resolve().parents[3]
    if output_root == source_root or source_root in output_root.parents or repo == output_root or repo in output_root.parents:
        raise ValueError("Paper outputs must be outside the repository and frozen input tree")
    identity = {"input_sha256": _hashes(source_root),
                "environment": {"python": sys.version, "packages": {
                    name: version(name) for name in ("numpy", "scipy", "matplotlib", "PyYAML")}},
                "reporting_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    receipt = output_root / "PAPER_ASSETS.json"
    if receipt.is_file():
        saved = _json(receipt)
        if any(saved.get(k) != v for k, v in identity.items()):
            raise ValueError("Source changed; preserve this run and choose a new WOWFS_REPRODUCTION_ROOT")
        if checks and saved["numerical_replay"] != "PASS":
            raise ValueError("This run did not replay checks; choose a new output for checks=True")
        for relative, expected in saved["generated_sha256"].items():
            p = output_root / relative
            if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != expected:
                raise ValueError(f"A completed generated asset changed or is missing: {relative}")
        return output_root
    if output_root.exists() and any(output_root.iterdir()):
        raise ValueError("Output contains an incomplete run; preserve it and choose a new output directory")
    output_root.mkdir(parents=True, exist_ok=True)
    stage = output_root / "manuscript"
    shutil.copytree(source_root, stage)
    (stage / "checks/rechecks").mkdir(parents=True, exist_ok=True)
    commands = []

    def run(relative, *args):
        command = [sys.executable, relative, *args]
        log = output_root / "logs" / (Path(relative).stem + ".log")
        log.parent.mkdir(exist_ok=True)
        # The archived verify_v2 imports its own frozen solver implementation.
        env = dict(os.environ, PYTHONHASHSEED="0", MPLBACKEND="Agg")
        with log.open("w") as stream:
            result = subprocess.run(command, cwd=stage, env=env, stdout=stream, stderr=subprocess.STDOUT)
        commands.append({"command": command, "returncode": result.returncode,
                         "log": log.relative_to(output_root).as_posix()})
        if result.returncode:
            raise RuntimeError(f"Paper replay failed; preserved log: {log}")

    if checks:
        run("theory/src/verify.py")
        run("theory/src/native_reanalysis.py")
    run("scripts/rebuild_assets.py")
    run("scripts/render_plot_sources.py")
    run("scripts/rebuild_v2_assets.py")
    if checks:
        run("scripts/verify_v2.py")
        for script in ("mine_joint_targets.py", "check_triple.py", "triple_source_certificate.py"):
            run("evidence/gold/scripts/" + script, "--output", "checks/rechecks/gold")
    # The original builder retained this table as static TeX. Reconstruct it
    # from the exact check results, and verify the printed historical counts.
    exact = _exact_rows(stage)
    expected = ["500", "700", "120", "100 / 964", "10 / 55", "1,016", "250", "200", "77"]
    if [r[1] for r in exact] != expected:
        raise AssertionError("Exact-check counts differ from the current manuscript")
    static = (source_root / "tables/exact_checks.tex").read_text()
    header, rest = static.split(r"\midrule", 1)
    _, footer = rest.split(r"\bottomrule", 1)
    (stage / "tables/exact_checks.tex").write_text(
        header + r"\midrule" + "\n" + "\n".join(" & ".join(row) + r"\\" for row in exact)
        + r"\bottomrule" + footer)
    # Guard the original fixed coordinates against evidence drift. The notebook
    # renderer below reads the JSON directly instead of these coordinates.
    obligations = _json(stage / "evidence/v2/native-summary/NATIVE_EVIDENCE_SUMMARY.json")["obligation_diagnostics"]["base_label_counts"]
    assert [obligations[k] for k in ("legacy_alone_sufficient", "targets_alone_sufficient",
            "legacy_necessary_for_obstruction", "targets_necessary_for_obstruction")] == [42, 39, 28, 16]
    # Seal the staged evidence too: later renderers read both regenerated CSV
    # and native-summary JSON, so verifying display files alone is insufficient.
    generated = {"manuscript/" + name: digest for name, digest in _hashes(stage).items()}
    receipt.write_text(json.dumps({**identity, "status": "PASS", "numerical_replay": "PASS" if checks else "not_run",
        "new_native_battles": 0, "new_timing_runs": 0, "commands": commands,
        "generated_sha256": generated, "exact_tex_build": "not_run",
        "scope": "Current manuscript numerical replay and regenerated assets; PDF typesetting is a separate optional step."}, indent=2) + "\n")
    return output_root


def _exact_rows(stage):
    d = _json(stage / "theory/checks/EXACT_CHECKS.json")
    return [
        ["Random fixed-frontier cases", str(d["fixed_frontier_vs_subsets"]["instances"])],
        ["Additional cases with nontrivial conflict covers", str(d["nontrivial_conflict_cuts"]["instances"])],
        ["Unknown-frontier completion cases", str(d["unknown_frontier_vs_subsets"]["instances"])],
        ["Complete interface cases / target-subset queries", f'{d["exact_completion_interfaces"]["instances"]} / {d["exact_completion_interfaces"]["all_target_subset_queries"]}'],
        ["Latent-conflict parameter instances / target witnesses", f'{d["latent_repair_separation"]["parameter_instances"]} / {d["latent_repair_separation"]["distinct_target_witnesses"]}'],
        ["Blocked extensions in small latent-conflict instances", f'{d["latent_repair_separation"]["all_bad_extensions_checked"]:,}'],
        [r"Perturbation instances at $\eta=.0005$", str(d["latent_response_perturbations"]["instances"])],
        ["Target-family inclusion comparisons", str(d["future_option_dominance"]["interface_pairs"])],
        ["Hypergraph-colouring reduction cases", str(d["hardness_realization"]["instances"])],
    ]


FIGURES = [
    ("fig:latent", "Current responses can agree while future completion differs", "sections/figure_theory.tex"),
    ("fig:triple", "Joint target failure in a power-safe native catalogue", "sections/figure_triple.tex"),
    ("fig:tolerance", "Retention changes the future target family", "sections/figure_tolerance.tex"),
    ("fig:exclusion", "A source/conflict certificate excludes every gaining repair batch", "sections/figure_certificate.tex"),
]


def _rays(ax, rows, labels, *, unit="DPS"):
    values = [float(r["upper"]) for r in rows]
    left = min(values) * 1.25
    for i, (v, label) in enumerate(zip(values, labels)):
        color = "#2878b5" if i % 2 == 0 else "#dd8452"
        ax.annotate("", xy=(left, i), xytext=(v, i), arrowprops=dict(arrowstyle="->", color=color, lw=2))
        ax.plot(v, i, "o", color=color)
        ax.annotate(f"{v:.3f}", (v, i), xytext=(4, 5), textcoords="offset points", fontsize=8)
    ax.axvline(0, color="gray", ls="--")
    ax.set(xlim=(left, max(0.1, abs(left) * .12)), yticks=range(len(rows)), yticklabels=labels,
           xlabel=f"Upper retention margin ({unit}); ray extends toward −∞")
    ax.invert_yaxis()


def figure_gallery(output_root):
    """Return four (metadata, Matplotlib figure) pairs; save SVG/PNG/PDF externally."""
    import matplotlib.pyplot as plt
    import numpy as np
    output_root = Path(output_root)
    stage = output_root / "manuscript"
    dest = output_root / "notebook-figures"
    dest.mkdir(exist_ok=True)
    gallery = []
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.7), constrained_layout=True)
    ax = axes[0]
    ax.axis("off")
    positions = {"o": (.1, .4), "t": (.45, .4), "b": (.82, .68), "s": (.82, .12)}
    for key, (x, y) in positions.items():
        ax.text(x, y, key, ha="center", va="center", fontsize=16,
                bbox=dict(boxstyle="circle", facecolor="white", edgecolor="#444444"))
    for end, color, text in (("o", "#27864e", "restores old use\n(1.02, 1)"),
                              ("b", "#b83c43", "unsafe: (1.05, 1.05)"),
                              ("s", "#27864e", "safe: (1.02, 1)")):
        start, stop = positions["t"], positions[end]
        ax.annotate("", xy=stop, xytext=start, arrowprops=dict(arrowstyle="-", color=color, lw=2))
        ax.text((start[0]+stop[0])/2, (start[1]+stop[1])/2+.09, text, ha="center", fontsize=9, color=color)
    ax.text(.03, .94, "Old pair (o, r): (1, 1)\nEither first choice with r: (1.02, 1)", va="top")
    ax.text(.03, -.08, "Targets need helper t to retain o. Power cap: 1.03.", fontsize=10)
    ax.set_title("(a) Same current responses; one future conflict")
    t = np.linspace(.001, .005, 51)
    axes[1].plot(2+100*t, 2.8-100*t-100*t*t, color="#2878b5", label="Exact target response curve")
    t = .001+.004*np.arange(1, 6)/6
    axes[1].scatter(2+100*t, 2.8-100*t-100*t*t, color="#2878b5", label="Five target examples")
    axes[1].set(xlabel="Long-task gain over initial reference (%)", ylabel="Short-task gain (%)",
                title="(b) After s: all targets feasible; after b: none")
    axes[1].legend(fontsize=8)
    gallery.append((FIGURES[0], fig))

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.7), constrained_layout=True)
    ax = axes[0]
    ax.axis("off")
    xyz = {"A": (.5, .85), "B": (.1, .17), "C": (.9, .17)}
    for a, b in (("A", "B"), ("B", "C"), ("C", "A")):
        x, y = xyz[a], xyz[b]
        ax.plot([x[0], y[0]], [x[1], y[1]], color="#27864e", lw=2)
        ax.text((x[0]+y[0])/2, (x[1]+y[1])/2, "YES", ha="center", backgroundcolor="white")
    for name, (x, y) in xyz.items():
        ax.text(x, y, name, ha="center", va="center", fontsize=15, bbox=dict(boxstyle="circle", fc="white"))
    ax.text(.5, .38, "ABC: NO\nall 128 supersets excluded", ha="center", color="#8459a0", weight="bold")
    ax.text(.5, -.06, "All 32 physical pairs are power-safe.\nB and C are alternative boots, not co-equipped items.", ha="center", fontsize=9)
    ax.set_title("(a) Every pair is supported; the triple is excluded")
    rows = _csv(stage / "data/plots/triple_retention.csv")
    rows.sort(key=lambda r: -float(r["y"]))
    _rays(axes[1], rows, [f'{r["task"]} / {float(r["tolerance"]):g}%' for r in rows])
    axes[1].set_title("(b) Every remaining repair loses the old boots")
    gallery.append((FIGURES[1], fig))

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.7), constrained_layout=True)
    rows = _csv(stage / "data/plots/new_tolerance.csv")
    x, bottom = np.arange(len(rows)), np.zeros(len(rows))
    for name, color in (("yes", "#27864e"), ("no", "#8459a0"), ("unknown", "#bbbbbb")):
        values = np.array([int(r[name]) for r in rows])
        axes[0].bar(x, values, bottom=bottom, color=color, label=name.upper())
        for i, v in enumerate(values):
            axes[0].text(i, bottom[i]+v/2, str(v), ha="center", va="center", fontsize=9,
                         color="black" if name == "unknown" else "white")
        bottom += values
    axes[0].set(xticks=x, xticklabels=[f'{float(r["tolerance"]):g}' for r in rows], ylim=(0, 140),
                xlabel="Allowed source deficit (% of reference)", ylabel="Target queries / 128",
                title="(a) All outcomes at four retention tolerances")
    axes[0].legend(ncols=3, fontsize=8)
    d = _json(stage / "evidence/v2/native-summary/NATIVE_EVIDENCE_SUMMARY.json")["obligation_diagnostics"]["base_label_counts"]
    groups = ["helpers", "targets", "legacy"]
    y = np.arange(3)
    axes[1].barh(y-.17, [d[g+"_alone_sufficient"] for g in groups], .32, label="Group alone excludes", color="#2878b5")
    axes[1].barh(y+.17, [d[g+"_necessary_for_obstruction"] for g in groups], .32, label="Removing group restores", color="#dd8452")
    axes[1].set(yticks=y, yticklabels=["Helpers", "Targets", "History"], xlabel="Queries with a supported change",
                title="(b) Source-group effects at 1% tolerance", xlim=(0, 50))
    axes[1].legend(fontsize=8)
    gallery.append((FIGURES[2], fig))

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.7), constrained_layout=True)
    rows = sorted(_csv(stage / "data/plots/conflicts.csv"), key=lambda r: (r["item"], r["context"] != "local"))
    for i, row in enumerate(rows):
        lower, upper = float(row["lower"]), float(row["upper"])
        color = "#2878b5" if row["context"] == "local" else "#dd8452"
        axes[0].plot([lower, upper], [i, i], color=color, lw=2)
        axes[0].plot([lower, upper], [i, i], "|", color=color, markersize=8)
    names = {"x1": "Spirit of Aquementas", "x2": "Tome of the Ice Lord", "x3": "Spellbound Tome"}
    axes[0].set(yticks=range(len(rows)), yticklabels=[f'{names[r["item"]]} / {r["context"]}' for r in rows],
                xlabel="Cap-margin interval (DPS)", title="(a) All alternative off-hands are excluded")
    axes[0].axvline(0, color="gray", ls="--")
    axes[0].invert_yaxis()
    rows = sorted(_csv(stage / "data/plots/retention_bounds.csv"), key=lambda r: -float(r["y"]))
    _rays(axes[1], rows, [f'{r["task"].title()} / {r["context"]}' for r in rows])
    axes[1].set_title("(b) The remaining gain witness loses Eye")
    gallery.append((FIGURES[3], fig))
    for metadata, fig in gallery:
        label, title, _ = metadata
        fig.suptitle(title, fontsize=13)
        for extension in ("png", "svg", "pdf"):
            fig.savefig(dest / (label.replace(":", "_") + "." + extension), dpi=160, bbox_inches="tight")
    return gallery


# Titles/columns are display metadata. All body rows come from regenerated
# TeX, frozen task/catalogue evidence, or replayed exact-check JSON.
TABLES = [
    ("tab:newfactions", "Registered future targets in independent native catalogues", "new_faction_rows.tex", ["Class", "Alliance YES", "Alliance NO", "Alliance UNKNOWN", "Horde YES", "Horde NO", "Horde UNKNOWN"]),
    ("tab:runtime", "Exact repeated-query services (recorded work, not new timings)", "runtime_rows.tex", ["Service", "Native resolved / 6160", "Native work (s)", "Synthetic resolved / 67445", "Synthetic work (s)"]),
    ("tab:allcatalogues", "All 16 registered base catalogues", "catalogue_rows.tex", ["ID", "Class", "Race", "Faction", "Varied slots", "Q", "YES", "NO", "UNKNOWN"]),
    ("tab:pairwitnesses", "Supported Druid pair completions", "triple_pair_rows.tex", ["Targets", "Short lower (DPS)", "Long lower (DPS)", "Full publication supported"]),
    ("tab:triplehelpers", "Excluded optional gloves", "triple_helper_rows.tex", ["Optional gloves", "Old-glove short upper (DPS)", "Old-glove long upper (DPS)"]),
    ("tab:alltol", "All 128 base queries at each tolerance", "tolerance_rows.tex", ["Tolerance (%)", "YES", "NO", "UNKNOWN", "Retention-dependent NO", "Menus"]),
    ("tab:protocol", "Frozen confirmation settings", "protocol.tex", ["Family", "Setting", "Samples per cell", "Cap / retention (%)"]),
    ("tab:durations", "Physical task settings", "durations.tex", ["Family", "Setting", "Short / resistance 0 (s)", "Long / resistance 75 (s)"]),
    ("tab:items", "Complete trinket/off-hand catalogue", "catalog_items.tex", ["Slot", "Item", "Database ID", "Role"]),
    ("tab:gloves", "Complete gloves/legs catalogue", "glove_items.tex", ["Slot", "Item", "Database ID", "Role"]),
    ("tab:firstdetails", "First trinket states on confirmation means", "first_states.tex", ["Setting", "First item", "Long DPS", "Short DPS", "Long / reference", "Short / reference"]),
    ("table:all_width", "Upper bounds excluding every completion after Second Wind", "all_width.tex", ["Test", "Configuration/source", "Local (DPS)", "Held out (DPS)"]),
    ("table:maximal_sets", "Maximal completions after Tome on finite mean tables", "maximal_sets.tex", ["Setting", "Set", "Additional items"]),
    ("tab:jointall", "Selected cap and signed interaction contrasts", "joint_all.tex", ["Family", "Setting", "Contrast", "Mean (%)", "Lower (%)", "Upper (%)"]),
    ("table:exact_checks", "Exact-arithmetic checks against independent enumeration", "exact_checks.tex", ["Check", "Count"]),
]


def _plain_tex(value):
    value = re.sub(r"\\(?:midrule|toprule|bottomrule|endfirsthead|endhead)", "", value)
    value = re.sub(r"\\addlinespace(?:\[[^]]*\])?", "", value)
    value = value.replace(r"\%", "%").replace(r"\&", "&").replace(r"\_", "_")
    return value.replace("$", "").replace(r"\eta", "η").strip()


def _table_rows(path, columns):
    text = path.read_text()
    if r"\midrule\endhead" in text:
        text = text.split(r"\midrule\endhead", 1)[1]
    elif r"\begin{tabular}" in text:
        text = text.split(r"\midrule", 1)[1]
    text = text.split(r"\bottomrule", 1)[0]
    rows = []
    for raw in text.split(r"\\"):
        cells = [_plain_tex(c) for c in re.split(r"(?<!\\)&", raw)]
        if len(cells) == columns:
            rows.append(cells)
        elif any(cells):
            raise ValueError(f"Unexpected TeX row in {path}: {cells}")
    return rows


def paper_tables(output_root):
    """Return all 15 numbered tables plus two unnumbered tables; export CSV/HTML.

    Labels starting ``table:`` identify tables without original LaTeX labels.
    Table order follows manuscript source order, not float placement.
    """
    output_root = Path(output_root)
    stage = output_root / "manuscript"
    dest = output_root / "notebook-tables"
    dest.mkdir(exist_ok=True)
    result = []
    for label, title, filename, columns in TABLES:
        path = stage / "tables" / filename
        result.append(dict(label=label, title=title, columns=columns,
                           rows=_table_rows(path, len(columns)), source="tables/" + filename))
    for label, title, filename, columns, selector in [
        ("unnumbered:regions", "Certified continuous threshold boxes", "appendix_new_methods.tex", ["Catalogue", "e", "h", "g"], 0),
        ("unnumbered:druid_items", "Druid history and three target items", "appendix_new_results.tex", ["Role", "Native database item", "ID", "Slot"], 0),
    ]:
        text = (stage / "sections" / filename).read_text()
        block = re.findall(r"\\begin\{tabular\}.*?\\end\{tabular\}", text, re.DOTALL)[selector]
        body = block.split(r"\midrule", 1)[1].split(r"\bottomrule", 1)[0]
        rows = [[_plain_tex(c) for c in re.split(r"(?<!\\)&", line)] for line in body.split(r"\\") if line.strip()]
        result.append(dict(label=label, title=title, columns=columns, rows=rows, source="sections/"+filename))
    for table in result:
        stem = table["label"].replace(":", "_")
        with (dest / (stem + ".csv")).open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(table["columns"])
            writer.writerows(table["rows"])
        (dest / (stem + ".html")).write_text(table_html(table))
    (dest / "TABLE_INDEX.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def table_html(table):
    def row(values, tag):
        return "<tr>" + "".join(f"<{tag}>{html.escape(str(v))}</{tag}>" for v in values) + "</tr>"
    return ('<div style="overflow-x:auto"><table style="border-collapse:collapse">'
            + "<thead>" + row(table["columns"], "th") + "</thead><tbody>"
            + "".join(row(r, "td") for r in table["rows"]) + "</tbody></table></div>")
