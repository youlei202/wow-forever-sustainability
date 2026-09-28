#!/usr/bin/env python3
"""Reproduce independent finite-solver comparisons against the frozen reference.

Run after sourcing scripts/env.sh. Does not modify the supplied reference tree.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import sys
import time

from wowfs.experiments.oe_solver import fixed_partner_problem, exact_capacity, validate_history


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--reference',required=True,type=Path)
    ap.add_argument('--output',required=True,type=Path)
    a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    before={str(p.relative_to(a.reference)):digest(p) for p in a.reference.rglob('*') if p.is_file()}
    spec=importlib.util.spec_from_file_location('frozen_oe_reference',a.reference/'scripts/retention_capacity.py')
    old=importlib.util.module_from_spec(spec);sys.modules[spec.name]=old;spec.loader.exec_module(old)
    def convert(p):
        rows=(p.old,)+p.new
        utilities=[[[float(v) if v is not None else 0.] for v in row] for row in rows]
        legal=[[v is not None for v in row] for row in rows]
        return fixed_partner_problem(utilities,row_ids=[f'a{i}' for i in range(len(rows))],
            partner_ids=[f'x{i}' for i in range(len(p.old))],initial_rows=['a0'],
            task_weights=[1],reference=[1],gain=float(p.gain),cap=float(p.cap),tolerance=float(p.tolerance),
            gain_mass=1,retention_mass=1,legal=legal,epsilon=0)
    rng=random.Random(9262026);comparisons=[];start=time.monotonic()
    for case in range(150):
        n=rng.randint(2,4);m=rng.randint(2,6)
        initial=tuple(Q(rng.randint(2,8),2) for _ in range(n));f=max(initial)
        tol=f-min(initial)+Q(rng.randint(0,12),4)
        cap=f+Q(rng.randint(2,16),4);gain=Q(rng.randint(1,4),4)
        candidates=[]
        for _ in range(m):
            row=[None if rng.random()<.15 else Q(rng.randint(0,28),4) for _ in range(n)]
            if all(v is None for v in row):row[0]=Q(1)
            candidates.append(tuple(row))
        p=old.Problem(initial,tuple(candidates),gain,tol,cap);np=convert(p)
        for B in sorted({1,2,4,m}):
            expected=old.exact_subset_dp(p,B).capacity
            measured=exact_capacity(np,B)
            assert measured.status=='finite_exact' and measured.capacity==expected,(p,B,expected,measured)
            validate_history(np,measured.batches,B)
            comparisons.append({'case':case,'B':B,'old_exact':expected,'new_exact':measured.capacity})
        unlimited=old.exact_batched_profile(p).capacity
        assert exact_capacity(np,m).capacity==unlimited
    helper=old.Problem((Q(10),Q(5)),((Q(11),Q(0)),(Q(0),Q(6)),(Q(12),Q(7))),Q(1),Q(5),Q(12))
    p=convert(helper)
    actual=exact_capacity(p,2)
    assert actual.capacity==1 and old.exact_batched_profile(helper).capacity==1
    validate_history(p,[('a1','a2')],2)
    invalid_path=[('a1','a2'),('a3',)]
    try:validate_history(p,invalid_path,2)
    except ValueError:pass
    else:raise AssertionError('Expected the weak published repair to fail terminal retention.')
    examples={'helper_terminal_filter':{
        'old':[10,5],'candidates':[[11,0],[0,6],[12,7]],'g':1,'e':5,'cap':12,
        'true_capacity_all_B':1,'invalid_without_helper_retention':invalid_path,
        'failing_source':'a2','helper_best':6,'terminal_required':7},
        'collapsed_actual_history':{'actual_initial_rows':[[10,9],[11,9]],'future_row':[13,13],
            'g':1,'e':2,'cap':13,'true_remaining_capacity':0,
            'incorrect_collapsed_initial_row':[11,9],'incorrect_remaining_capacity':1},
        'note':'Synthetic regression counterexamples to unsafe adaptations, not counterexamples to the reference theorem.'}
    after={str(p.relative_to(a.reference)):digest(p) for p in a.reference.rglob('*') if p.is_file()}
    assert before==after
    result={'status':'passed','native_observations':0,'random_scalar_tables':150,
        'independent_solver_comparisons':len(comparisons),'unlimited_profile_comparisons':150,
        'exact_arithmetic_reference':'fractions.Fraction, quarter-integer inputs; binary float solver with epsilon=0',
        'reference_unchanged':True,'elapsed_seconds':time.monotonic()-start,
        'solver_sha256':digest(Path(__file__).resolve().parents[1]/'src/wowfs/experiments/oe_solver.py'),
        'comparisons':comparisons}
    (a.output/'INDEPENDENT_COMPARISONS.json').write_text(json.dumps(result,indent=2))
    (a.output/'UNSAFE_ADAPTATION_COUNTEREXAMPLES.json').write_text(json.dumps(examples,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='comparisons'},indent=2))


if __name__=='__main__':main()
