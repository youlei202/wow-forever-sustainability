"""Explicit, verified inputs and external outputs for paper reproduction."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
import zipfile

from wowfs.paths import SOURCE_ROOT, setup_paths, work_root

ARCHIVE_NAME = "WOW_MINIMAL_INTERFACE_NATIVE_REVIEW.zip"
ARCHIVE_SHA256 = "9f598b3ee487e266a58213e383ad86dad6b9c8ca6f4ee7d725b1addd5d1dbbde"
PACKAGE_NAME = "minimal-interface-native-audit-2026-09-27"


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def external(path: Path) -> Path:
    path = path.expanduser().resolve()
    if path == SOURCE_ROOT or SOURCE_ROOT in path.parents:
        raise ValueError("Data and generated output must be outside the source repository")
    return path


def extract(archive: Path, destination: Path) -> None:
    """Reject traversal, symbolic links, duplicate names, and absolute members."""
    with zipfile.ZipFile(archive) as zipped:
        seen = set()
        for member in zipped.infolist():
            path = Path(member.filename)
            if (path.is_absolute() or ".." in path.parts or "\\" in member.filename
                    or stat.S_ISLNK(member.external_attr >> 16)
                    or member.filename in seen):
                raise ValueError(f"Unsafe archive member: {member.filename}")
            seen.add(member.filename)
        destination.mkdir(parents=True, exist_ok=False)
        zipped.extractall(destination)


def verify_inputs(root: Path) -> dict:
    manifest = json.loads((root / "INPUT_MANIFEST.json").read_text())
    if manifest["archive_sha256"] != ARCHIVE_SHA256:
        raise ValueError("Expected the final v2 audit archive")
    for name, expected in manifest["files"].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()) or sha256(path) != expected:
            raise ValueError(f"Reproduction input changed or is missing: {name}")
    return manifest


def prepare_inputs(archive: Path | None = None, destination: Path | None = None) -> Path:
    """Unpack the exact archived events and manuscript without touching frozen runs."""
    setup_paths()
    destination = external(destination or Path(os.environ.get(
        "WOWFS_REPRO_INPUTS", str(work_root() / "inputs/paper-reproduction"))))
    archive = Path(archive or os.environ.get("WOWFS_REPRO_ARCHIVE", str(
        work_root() / "artifacts/minimal-interface-review-v2" / ARCHIVE_NAME))).expanduser().resolve()
    if destination.exists():
        verify_inputs(destination)
        if archive.exists() and sha256(archive) != ARCHIVE_SHA256:
            raise ValueError("Supplied archive does not match the registered final v2 archive")
        return destination
    if not archive.is_file():
        raise FileNotFoundError(
            f"Missing frozen data archive: {archive}. Supply --archive /path/to/{ARCHIVE_NAME} "
            "or set WOWFS_REPRO_ARCHIVE. Native data are never replaced by synthetic data.")
    if sha256(archive) != ARCHIVE_SHA256:
        raise ValueError("Archive SHA256 mismatch; expected the final v2 review archive")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".paper-reproduction-", dir=destination.parent))
    try:
        extract(archive, staging / "audit")
        package = staging / "audit" / PACKAGE_NAME
        original_manifest = json.loads((package / "PACKAGE_MANIFEST.json").read_text())
        for row in original_manifest["files"]:
            path = (package / row["path"]).resolve()
            if not path.is_relative_to(package.resolve()) or sha256(path) != row["sha256"]:
                raise ValueError("Audit package manifest mismatch: " + row["path"])
        extract(package / "inputs/review-v2.zip", staging / "review")
        extract(package / "inputs/WoW_Minimal_Interface_Codex_Handoff.zip", staging / "handoff")
        handoff = staging / "handoff/WoW_Minimal_Interface_Codex_Handoff"
        extract(handoff / "WoW_Future_Targets_AISTATS2027_LaTeX.zip", staging / "manuscript")
        manifest = {"archive_sha256": ARCHIVE_SHA256, "archive_name": ARCHIVE_NAME,
                    "files": {str(p.relative_to(staging)): sha256(p)
                              for p in sorted(staging.rglob("*")) if p.is_file()}}
        (staging / "INPUT_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
        staging.rename(destination)
    except BaseException:
        # Only our incomplete extraction is disposable; original archives are untouched.
        shutil.rmtree(staging)
        raise
    return destination


@dataclass(frozen=True)
class ReproductionContext:
    inputs: Path
    package: Path
    bundle: Path
    paper_source: Path
    proof_path: Path
    output: Path


def get_context() -> ReproductionContext:
    inputs = prepare_inputs()
    output = external(Path(os.environ.get("WOWFS_REPRODUCTION_ROOT", str(
        work_root() / "artifacts/paper-reproduction/interactive"))))
    if output.is_relative_to(inputs) or inputs.is_relative_to(output):
        raise ValueError("Output and immutable input trees must be separate")
    output.mkdir(parents=True, exist_ok=True)
    return ReproductionContext(
        inputs=inputs, package=inputs / "audit" / PACKAGE_NAME,
        bundle=inputs / "review/review-v2",
        paper_source=inputs / "manuscript/WoW_Future_Targets_AISTATS2027",
        proof_path=inputs / "handoff/WoW_Minimal_Interface_Codex_Handoff/wow_minimal_interface_proof.pdf",
        output=output,
    )
