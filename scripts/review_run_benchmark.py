#!/usr/bin/env python3
"""Reexecute a frozen exact benchmark in a new external source/work layout.

The immutable review bundle stays unchanged. This is an optional Linux solver
rerun, not the lightweight native-certificate recheck and not a new simulation.
Install the bundle's requirements-solvers.txt in an external environment first.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--registry', choices=['synthetic', 'native'], default='native')
    parser.add_argument('--workflow', choices=['existence', 'queries'], default='existence')
    parser.add_argument('--workers', type=int, default=1)
    parser.add_argument('--seconds', type=float, default=60)
    parser.add_argument('--history-seconds', type=float, default=900)
    args = parser.parse_args()
    bundle, output = args.bundle.resolve(), args.output.resolve()
    if output.is_relative_to(bundle):
        parser.error('--output must be outside the immutable bundle')
    if args.workers < 1 or args.seconds <= 0 or args.history_seconds <= 0:
        parser.error('workers and budgets must be positive')
    manifest = json.loads((bundle / 'REVIEW_MANIFEST.json').read_text())
    for row in manifest['files']:
        relative = Path(row['path'])
        target = bundle / relative
        if relative.is_absolute() or '..' in relative.parts or target.is_symlink() or not target.resolve().is_relative_to(bundle):
            parser.error('Unsafe path in bundle manifest')
        if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != row['sha256']:
            parser.error(f'Bundle identity check failed: {relative}')
    output.mkdir(parents=True, exist_ok=False)
    source, work = output / 'source', output / 'work'
    shutil.copytree(bundle / 'code/wowfs', source / 'src/wowfs')
    shutil.copytree(bundle / 'configs', source / 'configs')
    for name in ('tmp', 'cache', 'cache/matplotlib'):
        (work / name).mkdir(parents=True, exist_ok=True)
    registry = bundle / 'data/benchmark-registry' / args.registry
    module = 'co_benchmark_ipc' if args.workflow == 'existence' else 'co_query_benchmark'
    environment = {**os.environ, 'WOWFS_WORK_ROOT': str(work), 'PYTHONPATH': str(source / 'src'),
                   'PYTHONPYCACHEPREFIX': str(work / 'cache/pycache'), 'TMPDIR': str(work / 'tmp'),
                   'XDG_CACHE_HOME': str(work / 'cache'), 'MPLCONFIGDIR': str(work / 'cache/matplotlib'),
                   'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'PYTHONHASHSEED': '0'}
    command = [sys.executable, '-m', f'wowfs.experiments.{module}', '--registry', str(registry),
               '--output', str(output / 'results'), '--workflow', args.workflow,
               '--workers', str(args.workers), '--budget', str(args.seconds),
               '--query-budget', str(args.history_seconds)]
    raise SystemExit(subprocess.call(command, cwd=source, env=environment))


if __name__ == '__main__':
    main()
