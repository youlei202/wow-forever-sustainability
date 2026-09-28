from __future__ import annotations
import argparse
from pathlib import Path
import sys
from wowfs.paths import SOURCE_ROOT, setup_paths

def main() -> int:
    parser = argparse.ArgumentParser(description="Sequential equipment expansion research")
    parser.add_argument("command", choices=["bootstrap", "freeze", "run", "analyze", "report", "package"])
    parser.add_argument("--config", type=Path, default=SOURCE_ROOT / "configs/development.yaml")
    parser.add_argument("--suite", default="exact-small")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--workers", type=int)
    parser.add_argument("--run-dir", type=Path)
    args = parser.parse_args()
    root = setup_paths()
    try:
        if args.command == "bootstrap":
            from wowfs.simulator.bridge import bootstrap
            print(bootstrap(root))
        elif args.command in ("freeze", "run"):
            from wowfs.experiments.runner import freeze, load_config, run
            config = load_config(args.config)
            if args.command == "freeze":
                print(freeze(config, root)[0])
            else:
                if args.suite not in ("exact-small", "mechanism-discovery"):
                    raise RuntimeError(f"Suite {args.suite!r} requires native Forever integration; not run. No synthetic substitution.")
                print(run(config, root, args.resume, args.workers))
        else:
            from wowfs.reporting.report import build_report, package
            latest = build_report(root, args.run_dir)
            print(package(root, latest) if args.command == "package" else latest)
        return 0
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        print(f"wowfs: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
