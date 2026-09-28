"""Centralized paths; never write runtime products to the source tree."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import tempfile
import yaml

SOURCE_ROOT = Path(__file__).resolve().parents[2]

def work_root() -> Path:
    cfg = yaml.safe_load((SOURCE_ROOT / "configs/paths.yaml").read_text())
    path = Path(os.environ.get(cfg["work_root_env"], str(SOURCE_ROOT / cfg["work_root_default"]))).resolve()
    if path == SOURCE_ROOT or SOURCE_ROOT in path.parents:
        raise ValueError("WOWFS_WORK_ROOT must be outside the source repository")
    return path

def setup_paths() -> Path:
    root = work_root()
    for name in ("envs", "external", "inputs", "data", "cache", "runs", "logs", "tmp", "artifacts", "provenance"):
        (root / name).mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(root / "cache/matplotlib"))
    os.environ.setdefault("XDG_CACHE_HOME", str(root / "cache"))
    tempfile.tempdir = str(root / "tmp")
    return root

def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def source_hash() -> str:
    """Hash scientific executable sources; reporting/prose edits do not change physics."""
    paths = [p for p in (SOURCE_ROOT / "src/wowfs").rglob("*.py") if "reporting" not in p.parts]
    digest = hashlib.sha256()
    for p in sorted(paths):
        digest.update(str(p.relative_to(SOURCE_ROOT)).encode())
        digest.update(p.read_bytes())
    return digest.hexdigest()

def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    os.replace(tmp, path)
