#!/usr/bin/env python3
"""Launch the portable checker using only sealed copied code and compact data.

Run this file from an unrelated working directory, with PYTHONPATH pointing at
the bundle's code directory. Solver imports and source-workspace reads fail.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.abc
import json
import os
from pathlib import Path
import sys


class NoSolvers(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in {'pysat','ortools','pypblib','gurobipy','z3'}:
            raise RuntimeError('Portable audit forbids solver import: '+fullname)
        return None


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--bundle',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--forbid-source-root',type=Path,required=True)
    a=parser.parse_args();bundle=a.bundle.resolve();output=a.output.resolve();forbidden=str(a.forbid_source_root.resolve())
    if output.exists() or output.is_relative_to(bundle):raise ValueError('Fresh external output required')
    sys.meta_path.insert(0,NoSolvers())
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            p=os.fsdecode(args[0])
            if p==forbidden or p.startswith(forbidden+'/'):
                raise RuntimeError('Original source access forbidden: '+p)
    sys.addaudithook(audit)
    from wowfs.experiments.co_review_check import check_bundle
    result=check_bundle(bundle)
    imported={name:str(Path(module.__file__).resolve()) for name,module in sys.modules.items()
              if name.startswith('wowfs') and getattr(module,'__file__',None)}
    if not all(Path(p).is_relative_to(bundle/'code') for p in imported.values()):raise AssertionError(imported)
    assert result['primary_catalogues']==16 and result['primary_query_rows']==192
    assert result['secondary_tolerance']['queries_recomputed']==512
    assert result['task_projection']['queries_recomputed']==64
    assert result['source_obligation_ablations']['query_scope_decisions_recomputed']==192*8
    assert result['inherited_sensitivity']['replayed_query_decisions']==2000
    result['portability_gate']={'cwd':str(Path.cwd()),'solver_imports_blocked':True,
        'original_source_reads_blocked':forbidden,'all_wowfs_modules_from_sealed_bundle':True,
        'imported_modules':imported,'finished_utc':datetime.now(timezone.utc).isoformat(),
        'launcher_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ('status','primary_catalogues','primary_query_rows','secondary_tolerance','task_projection','source_obligation_ablations','elapsed_seconds')}),flush=True)


if __name__=='__main__':main()
