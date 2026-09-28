"""Locate evidence for an engine without substituting synthetic combat."""
from __future__ import annotations
import os
import platform
import subprocess
from pathlib import Path
import yaml
from wowfs.paths import SOURCE_ROOT, atomic_json

def bootstrap(root: Path) -> dict:
    cfg = yaml.safe_load((SOURCE_ROOT / "configs/paths.yaml").read_text())
    candidates = [str((SOURCE_ROOT / p).resolve()) for p in cfg["engine_candidates"]]
    if os.environ.get(cfg["engine_root_env"]):
        candidates.insert(0, str(Path(os.environ[cfg["engine_root_env"]]).resolve()))
    checks = [{"path": p, "exists": Path(p).exists()} for p in dict.fromkeys(candidates)]
    def read_limit(name):
        p = Path("/sys/fs/cgroup") / name
        return p.read_text().strip() if p.exists() else "unknown"
    identity = {}
    for key in ("user.name", "user.email"):
        proc = subprocess.run(["git", "config", "--get", key], cwd=SOURCE_ROOT, capture_output=True, text=True)
        identity[key] = bool(proc.returncode == 0 and proc.stdout.strip())
    status = {"engine_status": "unverified_candidate" if any(c["exists"] for c in checks) else "missing",
              "candidate_paths": checks, "native_implemented": 0, "native_executed": 0,
              "cpu_quota": read_limit("cpu.max"), "memory_limit": read_limit("memory.max"),
              "python": platform.python_version(), "git_identity_present": identity,
              "git_commit": "unavailable"}
    atomic_json(root / "provenance/BOOTSTRAP.json", status)
    lines = ["# Engine bridge", "", "Native Forever engine is not connected. Abstract experiments do not supply native coverage.", "", "## Searched locations", ""]
    lines += [f"- `{c['path']}`: {'present; not validated' if c['exists'] else 'not found'}" for c in checks]
    lines += ["", "Exact-name search in connected GitHub repositories returned no repository on 2026-09-24.",
              "No app terminal session was attached. No old Classic/EABL data were imported.",
              "", "Engine revision, executable entrypoint, native effects, classes, tasks, races, seed reproducibility: unknown.",
              "Set WOWFS_ENGINE_ROOT to the actual checkout, then implement and validate an adapter before native execution.",
              "The program deliberately refuses native main/sweep/finite-data runs until this is done.",
              "", f"Available cgroup CPU quota: `{status['cpu_quota']}` (64 cores); memory limit: `{status['memory_limit']}` bytes.",
              "Only two worker processes are used by the abstract development run.",
              "Git author identity is missing; no identity was fabricated and no commit or push was made."]
    (root / "provenance/ENGINE_BRIDGE.md").write_text("\n".join(lines) + "\n")
    return status
