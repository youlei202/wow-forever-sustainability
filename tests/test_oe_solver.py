"""Small independent enumeration and regression tests for full-history planning."""
from dataclasses import replace
from itertools import combinations
import random

import numpy as np
import pytest

from wowfs.experiments.oe_solver import (Configuration, Problem, exact_capacity,
    fixed_partner_problem, first_step_continuations, greedy_capacity, state_metrics,
    task_choice_diagnostics, validate_history)


def make(rows, *, initial=('a0',), g=1, e=3, cap=20, mass=1, budget=None):
    a=np.asarray(rows,dtype=float)
    if a.ndim==2:a=a[:,:,None]
    return fixed_partner_problem(a,row_ids=[f'a{i}' for i in range(len(a))],
        partner_ids=[f'x{i}' for i in range(a.shape[1])],initial_rows=initial,
        task_weights=[1/a.shape[2]]*a.shape[2],reference=[1]*a.shape[2],
        gain=g,cap=cap,tolerance=e,gain_mass=mass,retention_mass=mass,
        total_item_budget=budget,epsilon=0)


def brute(p,B,initial=None,retention=True):
    """Independent recursive ordered-history enumeration, no solver metrics."""
    initial=set(initial or p.initial_items)
    rem=set(p.items)-initial
    def metric(pub):
        cs=[c for c in p.configurations if c.items<=pub]
        if not cs:return None
        f=[max(c.utilities[q]/p.reference[q] for c in cs) for q in range(len(p.reference))]
        cap=[p.cap]*len(f) if np.ndim(p.cap)==0 else p.cap
        tol=[p.tolerance]*len(f) if np.ndim(p.tolerance)==0 else p.tolerance
        if any(v>cap[q] for q,v in enumerate(f)):return None
        for source in pub:
            uses=[c for c in cs if source in c.items]
            if retention and not uses:return None
            if retention:
                mass=sum(p.task_weights[q] for q in range(len(f))
                    if max(c.utilities[q]/p.reference[q] for c in uses)>=f[q]-tol[q])
                if mass+1e-12<p.retention_mass:return None
        return f
    def visit(pub):
        f=metric(pub)
        if f is None:return -1
        best=0
        for n in range(1,B+1):
            for batch in combinations(sorted(set(p.items)-pub),n):
                nxt=pub|set(batch)
                if p.total_item_budget is not None and len(nxt-set(p.initial_items))>p.total_item_budget:continue
                nf=metric(nxt)
                if nf is None:continue
                mass=sum(p.task_weights[q] for q in range(len(f)) if nf[q]-f[q]>=p.gain)
                if mass+1e-12>=p.gain_mass:best=max(best,1+visit(nxt))
        return best
    return visit(initial)


def test_random_small_multitask_against_independent_histories():
    rng=random.Random(260926)
    for _ in range(32):
        q=rng.choice([1,2,3]);n=rng.choice([2,3]);m=rng.choice([2,3,4])
        values=[[[rng.randint(4,12) for _ in range(q)] for _ in range(n)] for _ in range(m+1)]
        p=make(values,e=rng.choice([3,5,8]),cap=12,mass=1/q,budget=rng.choice([None,2,3]))
        for B in (1,2,4):
            for retention in (False,True):
                oracle=brute(p,B,retention=retention)
                sol=exact_capacity(p,B,retention=retention)
                if oracle<0:assert sol.status=='initially_invalid'
                else:
                    assert sol.status=='finite_exact'
                    assert sol.capacity_lower==sol.capacity_upper==oracle
                    validate_history(p,sol.batches,B,retention=retention)


def test_real_published_history_cannot_collapse_to_column_maxima():
    p=make([[10,9],[11,9],[13,13]],initial=('a0','a1'),g=1,e=2,cap=13)
    assert exact_capacity(p).capacity==0
    collapsed=make([[11,9],[13,13]],e=2,cap=13)
    assert exact_capacity(collapsed).capacity==1


def test_repair_item_itself_must_survive_every_later_frontier():
    p=make([[10,6],[11,1],[1,6],[12,12]],e=5,cap=12)
    validate_history(p,[('a1','a2')],2)
    history=set(p.initial_items)|{'a1','a2'}
    assert state_metrics(p,history).source_masses['a2']==1
    assert exact_capacity(p,2,initial_items=history).capacity==0
    with pytest.raises(ValueError):validate_history(p,[('a1','a2'),('a3',)],2)
    assert exact_capacity(p,2,initial_items=history,retention=False).capacity==1


def test_small_B_and_helper_overlap_are_not_unlimited_batch():
    # Three partners require leader plus two distinct repair items together.
    p=make([[1,.75,.75],[1.5,.5,.5],[.5,1.25,.5],[.5,.5,1.25]],g=.4,e=.6,cap=1.75)
    assert exact_capacity(p,1).capacity==0
    assert exact_capacity(p,2).capacity==0
    assert exact_capacity(p,4).capacity==1
    assert set(exact_capacity(p,4).batches[0])=={'a1','a2','a3'}


def test_overcap_legal_pair_invalidates_entire_release():
    p=make([[10,9],[11,30]],e=50,cap=12)
    assert exact_capacity(p).capacity==0
    # All four pairs remain present; over-cap cell must never be dropped.
    assert len(p.configurations)==4


def test_generic_incidence_new_new_interactions_are_activated():
    p=Problem(('old','a','b'),frozenset(('old',)),(
        Configuration('old',frozenset(('old',)),(10,10)),
        Configuration('a',frozenset(('a',)),(11,10)),
        Configuration('b',frozenset(('b',)),(10,11)),
        Configuration('ab',frozenset(('a','b')),(20,20))),(.5,.5),(1,1),1,12,3,.5,.5)
    assert exact_capacity(p,1).capacity==1
    assert exact_capacity(p,2).capacity==1
    assert not state_metrics(p,('old','a','b')).power_valid


def test_task_tradeoff_and_policy_choices_are_distinct_from_weighted_scalarization():
    values=np.array([[[10,5]],[[5,11]],[[12,4]]])
    p=make(values,e=2,cap=12,mass=.5)
    assert exact_capacity(p).capacity==2
    assert not task_choice_diagnostics(p,p.items)['single_configuration_optimal_all_tasks']
    # Policies maximize within task; they do not add or dilute task weight.
    two_policy=np.stack([values,values[...,::-1]],axis=-1)
    pp=fixed_partner_problem(two_policy,row_ids=['a0','a1','a2'],partner_ids=['x0'],
        initial_rows=['a0'],task_weights=[.5,.5],reference=[1,1],gain=1,cap=12,tolerance=2,
        gain_mass=.5,retention_mass=.5,epsilon=0)
    assert state_metrics(pp).frontier==(10,10)


def test_continuation_keeps_total_budget_and_all_candidates():
    p=make([[10,10],[11,11],[12,12],[13,13]],e=4,cap=14,budget=2)
    assert exact_capacity(p).capacity==2
    rows=first_step_continuations(p)
    assert {r['batch'] for r in rows}=={('a1',),('a2',),('a3',)}
    assert exact_capacity(p,initial_items=set(p.initial_items)|{'a1'}).capacity==1
    assert exact_capacity(p,initial_items=set(p.initial_items)|{'a1','a2'}).capacity==0
    with pytest.raises(ValueError):exact_capacity(p,initial_items={'a1','x0','x1'})


def test_timeout_not_reported_as_exact_zero():
    p=make([[10,10],[11,11],[12,12]],e=5,cap=12)
    sol=exact_capacity(p,timeout_seconds=0)
    assert sol.status=='timeout' and sol.capacity_lower==0 and sol.capacity_upper==2


def test_baselines_keep_permissions_and_paths():
    p=make([[10,10],[11,11],[12,12],[13,13]],e=5,cap=13)
    assert greedy_capacity(p,policy='max_gain').capacity==1
    assert exact_capacity(p).capacity==3
    for policy in ('max_gain','source_aware','lookahead2','value_only'):
        s=greedy_capacity(p,policy=policy)
        validate_history(p,s.batches)
        assert s.batch_limit==1 and s.total_item_budget is None
    unsafe=make([[10,9],[11,10],[12,1]],e=2,cap=12)
    s=greedy_capacity(unsafe,policy='value_only')
    assert s.capacity==0 and s.invalid_attempt==('a2',)
    assert greedy_capacity(unsafe,policy='max_gain').capacity==2


def test_fail_loudly_on_missing_measurement_or_invalid_weights():
    with pytest.raises(ValueError):make([[10,9],[11,float('nan')]])
    p=make([[10,9],[11,10]])
    with pytest.raises(ValueError):replace(p,task_weights=(.5,))
    with pytest.raises(ValueError):exact_capacity(p,max_candidates=0)


def test_value_ablation_can_preload_dormant_items_but_retention_cannot():
    # Full incidence model: useful a+c+d needs a 3-way interaction. Under B=2,
    # value-only can preload dormant a together with b, then activate c+d.
    p=Problem(('old','a','b','c','d'),frozenset(('old',)),(
        Configuration('old',frozenset(('old',)),(10,)),
        Configuration('b',frozenset(('b',)),(11,)),
        Configuration('acd',frozenset(('a','c','d')),(12,))),
        (1,),(1,),1,12,5,1,1,epsilon=0)
    assert exact_capacity(p,2,retention=False).capacity==2
    assert exact_capacity(p,2,retention=True).capacity==1
    assert brute(p,2,retention=False)==2 and brute(p,2,retention=True)==1
