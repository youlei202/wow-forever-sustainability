"""Finish the frozen primary campaign without changing a running benchmark.

The original existence scheduler is paused after launching its first child.
This replacement waits for that child's complete aggregate, then runs native
existence and the independently audited six-method query comparison in order.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from wowfs.paths import atomic_json


def ensure_complete(folder):
    expected = json.loads((folder / 'JOB_INDEX.json').read_text())
    results = json.loads((folder / 'RESULTS_AGGREGATE.json').read_text())
    if len(results) != len(expected):
        return False
    if (folder / 'ERROR_STOP.json').exists() or (folder / 'CORRECTNESS_MISMATCH.json').exists():
        raise RuntimeError(f'Correctness/infrastructure stop in {folder}')
    return True


def run(root):
    root = Path(root)
    deadline = datetime.fromisoformat(json.loads((root / 'CAMPAIGN_STATUS.json').read_text())['deadline_utc']).timestamp()
    previous = root / 'benchmark/test-existence-v2'
    while time.time() < deadline:
        if (previous / 'ERROR_STOP.json').exists() or (previous / 'CORRECTNESS_MISMATCH.json').exists():
            raise RuntimeError('Previous existence suite requires intervention')
        if (previous / 'RESULTS_AGGREGATE.json').exists() and ensure_complete(previous):
            break
        time.sleep(10)
    else:
        raise TimeoutError('Cumulative campaign deadline before next suite')
    # A human/agent audit receipt must predate all primary query results.
    audit = root / 'checks/SIX_METHOD_QUERY_GATE.json'
    while not audit.exists() and time.time() < deadline:
        time.sleep(10)
    if not audit.exists() or json.loads(audit.read_text())['status'] != 'PASS':
        raise RuntimeError('Six-method correctness/audit gate missing or failed')
    suites = [
        ('co_benchmark_ipc', 'native-test-registry', 'native-existence-v2', 'existence'),
        ('co_query_benchmark', 'test-registry', 'test-queries-v2', 'queries'),
        ('co_query_benchmark', 'native-test-registry', 'native-queries-v2', 'queries'),
    ]
    for module, registry, name, workflow in suites:
        if time.time() >= deadline:
            raise TimeoutError('Cumulative deadline; remaining suites not_run')
        destination = root / 'benchmark' / name
        command = [sys.executable, '-m', f'wowfs.experiments.{module}', '--registry', str(root / registry),
                   '--output', str(destination), '--workers', '8', '--budget', '60',
                   '--query-budget', '900', '--workflow', workflow]
        atomic_json(root / 'benchmark' / f'{name}-COMMAND_START.json',
                    {'command': command, 'started_utc': datetime.now(timezone.utc).isoformat()})
        with (root / 'benchmark' / f'{name}.log').open('w') as log:
            completed = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                       env={**os.environ, 'PYTHONHASHSEED': '0'})
        atomic_json(root / 'benchmark' / f'{name}-COMMAND.json',
                    {'command': command, 'returncode': completed.returncode,
                     'finished_utc': datetime.now(timezone.utc).isoformat()})
        if completed.returncode or not ensure_complete(destination):
            raise RuntimeError(f'Incomplete or failed suite: {name}')
    atomic_json(root / 'benchmark/PRIMARY_ALL_COMPLETE.json',
                {'status': 'COMPLETE', 'utc': datetime.now(timezone.utc).isoformat(),
                 'suites': ['test-existence-v2'] + [s[2] for s in suites]})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-root', type=Path, required=True)
    run(parser.parse_args().run_root)
