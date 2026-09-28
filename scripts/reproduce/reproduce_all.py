#!/usr/bin/env python3
"""Verify frozen inputs, test the code, and execute every paper notebook."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, help="Final v2 audit ZIP (registered SHA256 is checked)")
    parser.add_argument("--inputs", type=Path, help="External directory for verified extracted inputs")
    parser.add_argument("--output", type=Path, help="Fresh external run directory")
    parser.add_argument("--prepare-only", action="store_true", help="Prepare and verify inputs without running analysis")
    parser.add_argument("--skip-tests", action="store_true", help="Explicitly skip tests; recorded in report")
    parser.add_argument("--resume", action="store_true", help="Resume identical code, inputs, and environment only")
    args = parser.parse_args()
    from wowfs.paths import setup_paths, work_root
    from wowfs.reproduction.context import prepare_inputs, get_context, sha256
    setup_paths()
    if args.archive:
        os.environ["WOWFS_REPRO_ARCHIVE"] = str(args.archive.resolve())
    if args.inputs:
        os.environ["WOWFS_REPRO_INPUTS"] = str(args.inputs.resolve())
    if args.prepare_only:
        print(prepare_inputs())
        return
    names = ["numpy", "scipy", "matplotlib", "PyYAML", "pytest", "nbformat", "nbclient", "ipykernel", "pandas"]
    versions = {name: importlib.metadata.version(name) for name in names}
    installed = dict(sorted((d.metadata["Name"], d.version) for d in importlib.metadata.distributions()
                            if d.metadata["Name"]))
    output = (args.output or work_root() / "artifacts/paper-reproduction" /
              datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")).resolve()
    os.environ["WOWFS_REPRODUCTION_ROOT"] = str(output)
    os.environ["WOWFS_SOURCE_ROOT"] = str(ROOT)
    os.environ["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + os.environ.get("PYTHONPATH", "")
    for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[variable] = "1"
    ctx = get_context()
    sources = [p for base in ("src", "scripts", "tests", "notebooks", "configs")
               for p in (ROOT / base).rglob("*") if p.is_file() and
               "__pycache__" not in p.parts and ".ipynb_checkpoints" not in p.parts]
    sources += [ROOT / name for name in ("pyproject.toml", "requirements.txt", "requirements.lock",
                                         "requirements-reproduce.lock", "Makefile", "AGENTS.md")]
    identity = {"source_sha256": {str(p.relative_to(ROOT)): sha256(p) for p in sorted(sources)},
                "input_manifest_sha256": sha256(ctx.inputs / "INPUT_MANIFEST.json"),
                "versions": installed, "python": sys.version, "tests_requested": not args.skip_tests}
    identity_path = output / "RUN_CONFIG.json"
    if identity_path.exists():
        if not args.resume or json.loads(identity_path.read_text()) != identity:
            raise ValueError("Use a fresh output directory, or --resume with unchanged source and inputs")
        saved_report = output / "REPRODUCTION_REPORT.json"
        if saved_report.exists() and json.loads(saved_report.read_text())["status"] == "PASS":
            saved = json.loads(saved_report.read_text())
            for name, digest in saved["output_sha256"].items():
                path = (output / name).resolve()
                if not path.is_relative_to(output) or sha256(path) != digest:
                    raise ValueError("Completed run output changed: " + name)
            print(json.dumps({k: v for k, v in saved.items() if k != "output_sha256"}, indent=2))
            return
    elif any(output.iterdir()):
        raise ValueError("Output directory already contains unrelated files")
    else:
        identity_path.write_text(json.dumps(identity, indent=2) + "\n")
    report = {"status": "RUNNING", "output": str(output), "new_native_battles": 0,
              "python": sys.version, "platform": platform.platform(), "versions": versions,
              "tests": "SKIPPED" if args.skip_tests else "PENDING", "notebooks": []}
    def save():
        (output / "REPRODUCTION_REPORT.json").write_text(json.dumps(report, indent=2) + "\n")
    save()
    try:
        if not args.skip_tests:
            print("Running deterministic test suite...", flush=True)
            with (output / "pytest.log").open("w") as log:
                subprocess.run([sys.executable, "-m", "pytest", "-q", str(ROOT / "tests")],
                               cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
            report["tests"] = "PASS"
            save()
        import nbformat
        from nbclient import NotebookClient
        from jupyter_client.kernelspec import KernelSpecManager
        # Use this interpreter even on machines with another globally registered python3 kernel.
        kernel_dir = output / "kernel"
        kernel_dir.mkdir(exist_ok=True)
        (kernel_dir / "kernel.json").write_text(json.dumps({"argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
            "display_name": "WoW paper reproduction", "language": "python"}))
        manager = KernelSpecManager(kernel_dirs=[str(output)])
        notebook_dir = output / "notebooks"
        notebook_dir.mkdir(exist_ok=True)
        notebooks = sorted((ROOT / "notebooks").glob("[0-9][0-9]_*.ipynb"))
        if not notebooks:
            raise FileNotFoundError("No paper notebooks found")
        for source in notebooks:
            print(f"Executing {source.name}...", flush=True)
            status = {"name": source.name, "status": "RUNNING"}
            report["notebooks"].append(status)
            save()
            notebook = nbformat.read(source, as_version=4)
            nbformat.validate(notebook)
            client = NotebookClient(notebook, timeout=3600, kernel_name="kernel",
                                    resources={"metadata": {"path": str(ROOT)}},
                                    kernel_manager_class="jupyter_client.manager.KernelManager")
            client.km = client.create_kernel_manager()
            client.km.kernel_spec_manager = manager
            try:
                client.execute()
            except BaseException:
                status["status"] = "FAIL"
                raise
            finally:
                nbformat.write(notebook, notebook_dir / source.name)
            status["status"] = "PASS"
            save()
        report["status"] = "PASS"
        report["limitations"] = ["No new native combat simulation or hardware timing was run.",
                                 "Notebook figures are regenerated views; exact manuscript typesetting requires TeX."]
        report["output_sha256"] = {str(p.relative_to(output)): sha256(p)
                                   for p in sorted(output.rglob("*")) if p.is_file()
                                   and p.name != "REPRODUCTION_REPORT.json"}
    except BaseException as error:
        report["status"] = "FAIL"
        report["error"] = f"{type(error).__name__}: {error}"
        failures = output / "failures"
        failures.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        (failures / (stamp + ".log")).write_text(traceback.format_exc())
        (failures / (stamp + ".json")).write_text(json.dumps(report, indent=2) + "\n")
        raise
    finally:
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        save()
    print(json.dumps({k: v for k, v in report.items() if k != "output_sha256"}, indent=2))


if __name__ == "__main__":
    main()
