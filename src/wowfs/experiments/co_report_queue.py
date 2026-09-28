"""Build a new compact report only after all four frozen suites complete."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time


def write(path, data):
    path=Path(path)
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(data,sort_keys=True,indent=2)+'\n')
    temporary.replace(path)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root',type=Path,required=True)
    parser.add_argument('--output-name',default='report-final-v2')
    args=parser.parse_args();root=args.run_root
    if hasattr(os,'sched_setaffinity'):
        allowed=os.sched_getaffinity(0)
        os.sched_setaffinity(0,{120 if 120 in allowed else max(allowed)})
    suites=('test-existence-v2','native-existence-v2','test-queries-v2','native-queries-v2')
    deadline=datetime.fromisoformat(json.loads((root/'CAMPAIGN_STATUS.json').read_text())['deadline_utc']).timestamp()
    state=root/'benchmark/REPORT_QUEUE_STATUS.json'
    write(state,{'status':'WAITING_FOR_ALL_FOUR_SUITES','pid':os.getpid(),'output_name':args.output_name,
                 'started_utc':datetime.now(timezone.utc).isoformat(),'suites':suites})
    try:
        while not (root/'benchmark/PRIMARY_ALL_COMPLETE.json').exists():
            for name in suites:
                directory=root/'benchmark'/name
                for marker in ('ERROR_STOP.json','CORRECTNESS_MISMATCH.json','INFRASTRUCTURE_CONTAMINATED.json'):
                    if (directory/marker).exists():raise RuntimeError(f'Input suite requires intervention: {name}/{marker}')
            if time.time()>deadline:raise TimeoutError('Campaign deadline before all four suites completed; no incomplete final report built')
            time.sleep(15)
        for name in suites:
            directory=root/'benchmark'/name
            index=json.loads((directory/'JOB_INDEX.json').read_text())
            aggregate=json.loads((directory/'RESULTS_AGGREGATE.json').read_text())
            if len(index)!=len(aggregate):raise RuntimeError(f'Incomplete aggregate: {name}')
            if any(r['status'] in ('NOT_RUN','ERROR','INFRASTRUCTURE_FAILURE') for r in aggregate):
                raise RuntimeError(f'Unexecuted or failed attempt in frozen primary suite: {name}')
        # Import only once inputs are final so the exact reporting revision is
        # snapshotted at execution, after all pre-report metric audits finish.
        from .co_benchmark_report import report
        write(state,{'status':'BUILDING_REPORT','pid':os.getpid(),'started_utc':datetime.now(timezone.utc).isoformat(),
                     'output_name':args.output_name,'suites':suites})
        result=report([root/'benchmark'/n for n in suites[:2]], [root/'benchmark'/n for n in suites[2:]],
                      root/'benchmark'/args.output_name,True,[root/'benchmark/test-existence-v1'])
        write(state,{**result,'finished_utc':datetime.now(timezone.utc).isoformat(),'suites':suites})
        print(json.dumps(result,indent=2))
    except Exception as exc:
        write(state,{'status':'ERROR','error':repr(exc),'finished_utc':datetime.now(timezone.utc).isoformat(),
                     'suites':suites,'output_name':args.output_name})
        raise


if __name__=='__main__':main()
