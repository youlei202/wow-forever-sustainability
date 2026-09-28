#!/usr/bin/env python3
"""Bundle maintained code and notebooks without manuscripts or private inputs."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
SOURCE_DIRECTORIES = ("src", "scripts", "tests", "notebooks", "configs", "docs")
ROOT_FILES = ("README.md", "AGENTS.md", "pyproject.toml", "Makefile", ".gitignore",
              "requirements.txt", "requirements.lock", "requirements-reproduce.lock")
# An allowlist keeps private input archives, TeX manuscripts, rendered figures,
# and other generated binaries out of a distributable source-code package.
SOURCE_SUFFIXES = {".py", ".go", ".sh", ".ipynb", ".json", ".yaml", ".yml", ".md", ".toml"}


def source_files(root):
    files = []
    for base in SOURCE_DIRECTORIES:
        files.extend(p for p in (root / base).rglob("*")
                     if p.is_file() and not p.is_symlink()
                     and not any(part in {"__pycache__", ".ipynb_checkpoints", "paper", "manuscript"}
                                 for part in p.relative_to(root).parts)
                     and p.suffix in SOURCE_SUFFIXES)
    files.extend(root / name for name in ROOT_FILES if (root / name).is_file())
    return sorted(files)


def main():
    from wowfs.reproduction.context import sha256, external
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = external(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    files = source_files(ROOT)
    manifest = {"source/" + str(p.relative_to(ROOT)): sha256(p) for p in files}
    guide = """WoW: Forever source-code reproduction package

The source/ directory contains maintained code, configurations, tests, supporting
documentation and all five Jupyter notebooks. Saved notebook outputs are retained
when present in the source checkout. Manuscripts, private input archives and
standalone rendered figures are deliberately excluded.

Saved notebook outputs can be viewed without the frozen inputs. To rerun the
native-evidence notebooks, obtain the registered frozen inputs separately and
keep them outside source/. This package does not provide those private inputs.

From source/ (use any external absolute path for WORK):

export WOWFS_WORK_ROOT=/absolute/path/to/work
python3 -m venv "$WOWFS_WORK_ROOT/envs/research"
source scripts/env.sh
python -m pip install -r requirements-reproduce.lock
python -m pip install --no-deps -e '.[reproduce]'
python scripts/reproduce/reproduce_all.py --archive /absolute/path/to/private/WOW_MINIMAL_INTERFACE_NATIVE_REVIEW.zip

See source/docs/REPRODUCIBILITY.md and source/docs/PAPER_MAP.md.
Python dependencies and the separately supplied frozen inputs are required for
the full replay; no simulator is required. No new combat or new hardware benchmark
is claimed. No manuscript is distributed in this source-code package.
"""
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for p in files:
            archive.write(p, "source/" + str(p.relative_to(ROOT)))
        archive.writestr("START_HERE.txt", guide)
        manifest["START_HERE.txt"] = hashlib.sha256(guide.encode()).hexdigest()
        archive.writestr("MANIFEST.json", json.dumps(manifest, indent=2) + "\n")
    with zipfile.ZipFile(output) as archive:
        for name, digest in manifest.items():
            if hashlib.sha256(archive.read(name)).hexdigest() != digest:
                raise ValueError("Package round-trip failed: " + name)
    receipt = {"status": "PASS", "archive": output.name, "sha256": sha256(output),
               "bytes": output.stat().st_size, "files_verified": len(manifest),
               "package_scope": "source_code_and_notebooks", "private_inputs_included": False,
               "manuscripts_included": False}
    output.with_suffix(".receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
