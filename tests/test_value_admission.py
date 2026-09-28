import numpy as np
import pytest
from wowfs.experiments.r4_feasibility import FiniteProblem
from wowfs.experiments.value_admission import decision_metrics, solve_gain_subset


def problem(new_value=104., novel=True):
    return FiniteProblem(values=np.array([[[100.,98.]],[[98.,100.]],[[new_value,99.]]]),
        behavior=np.array([[[[0.],[0.]]],[[[0.],[0.]]],[[[float(novel)],[float(novel)]]]]),
        sources=[{'old_a'},{'old_b'},{'old_a','new'}],protected=np.array([True,True,False]),
        new_sources=['new'],protected_sources=['old_a','old_b'],scale=np.array([100.,100.]),
        cap=np.array([105.,105.]),epsilon=.05,delta=.05,k_max=2)


def test_gain_witness_does_not_change_history_or_behavior_reference():
    p=problem();before=p.protected.copy();distances=p.distances.copy()
    answer=solve_gain_subset(p,gain_mass=.5,time_limit=10)
    assert answer['feasible']
    assert answer['result']['metrics']['all_seven_pass']
    assert np.array_equal(p.protected,before)
    assert np.array_equal(p.distances,distances)
    assert answer['result']['metrics']['source_deletion']['new']['normalized_loss']==[.04,0.]


def test_behavior_distance_is_not_decision_gain():
    p=problem(new_value=100.5)
    metrics=decision_metrics(p,[True,True,True],gain_mass=.5)
    assert metrics['D'] and not metrics['G']
    result=solve_gain_subset(p,gain_mass=.5)
    assert result['proved_infeasible'] and result['gain_witnesses']==0


def test_relaxed_behavior_constraint_is_explicit():
    p=problem(novel=False)
    strict=solve_gain_subset(p,gain_mass=.5,time_limit=10)
    relaxed=solve_gain_subset(p,gain_mass=.5,time_limit=10,require_behavior=False)
    assert strict['proved_infeasible']
    assert relaxed['feasible'] and relaxed['result']['metrics']['G']
    assert not relaxed['result']['metrics']['D']
    assert not relaxed['result']['metrics']['all_seven_pass']


def test_single_task_or_rejects_inapplicable_mass():
    with pytest.raises(ValueError):solve_gain_subset(problem(),gain_mass=.75)


def test_paired_frontier_interval_reoptimizes_both_libraries():
    from wowfs.experiments.value_confirm_analysis import paired_frontier_bounds
    rng=np.random.default_rng(8)
    old=rng.normal(size=(3,2,32));new=rng.normal(size=(4,2,32))
    low,high=paired_frontier_bounds(new,old,0.)
    expected=new.mean(axis=-1).max(axis=0)-old.mean(axis=-1).max(axis=0)
    assert np.allclose(low,expected)
    assert np.allclose(high,expected)


def test_paired_frontier_keeps_common_seed_cancellation():
    from wowfs.experiments.value_confirm_analysis import paired_frontier_bounds
    common=np.arange(32,dtype=float)[None,None,:]
    old=common+np.array([[2.,0.],[0.,3.]])[:,:,None]
    new=old+2.
    low,high=paired_frontier_bounds(new,old,10.)
    assert np.allclose(low,[2.,2.],atol=1e-7)
    assert np.allclose(high,[2.,2.],atol=1e-7)
