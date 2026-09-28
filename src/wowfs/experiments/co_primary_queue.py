"""Wait for our frozen native batch, then run matched primary CPU suites."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from wowfs.paths import atomic_json


def run(root):
    root=Path(root);state=json.loads((root/'CAMPAIGN_STATUS.json').read_text())
    deadline=datetime.fromisoformat(state['deadline_utc']).timestamp()
    target=root/'batches/confirm16384/PROGRESS.json'
    while time.time()<deadline:
        if target.exists():
            value=json.loads(target.read_text())
            if value['status']=='partial':raise RuntimeError('native batch incomplete; preserve and investigate')
            if value['status']=='completed':break
        time.sleep(10)
    else:raise TimeoutError('campaign deadline before primary scheduling')
    for workflow,name in [('existence','test-existence-v2'),('queries','test-queries-v2')]:
        dest=root/'benchmark'/name
        command=[sys.executable,'-m','wowfs.experiments.co_benchmark_ipc','--registry',str(root/'test-registry'),
                 '--output',str(dest),'--workers','8','--budget','60','--query-budget','900','--workflow',workflow]
        with (root/'benchmark'/f'{name}.log').open('w') as log:
            completed=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONHASHSEED':'0'})
        atomic_json(root/'benchmark'/f'{name}-COMMAND.json',{'command':command,'returncode':completed.returncode,'finished_utc':datetime.now(timezone.utc).isoformat()})
        if completed.returncode or (dest/'ERROR_STOP.json').exists() or (dest/'CORRECTNESS_MISMATCH.json').exists():
            raise RuntimeError('primary benchmark requires audit: '+name)
    atomic_json(root/'benchmark/PRIMARY_SYNTHETIC_COMPLETE.json',{'utc':datetime.now(timezone.utc).isoformat(),'status':'COMPLETE'})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-root',required=True);a=p.parse_args();run(a.run_root)
