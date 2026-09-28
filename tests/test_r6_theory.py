"""Checks of the supplied R5 theorem mapping; these are not native runs."""
from fractions import Fraction as F
from itertools import product
import pytest
from wowfs.experiments.r6_theory import (least_repair_closure,interval_repair_closures,
    stable_witness_assumptions,audit_unique_repair_responses,frontier_neutral_grid_bound)


def test_supplied_four_source_cascade_and_local_example():
    thresholds=[F(100)+F(i,4) for i in range(4)]
    core=F(100)+F(1,8)
    repairs=[F(100)+F(2*i+3,8) for i in range(3)]+[F(101)]
    cascade=least_repair_closure(F(100),core,thresholds,repairs)
    local=least_repair_closure(F(100),core,thresholds,[core]*4)
    assert cascade['repairs']==[0,1,2,3]
    assert local['repairs']==[0]
    assert [step['newly_forced'] for step in cascade['trace']]==[[0],[1],[2],[3],[]]


def test_threshold_equality_never_forces_a_repair():
    assert least_repair_closure(100,101,[101,102],[102,103])['repairs']==[]


def test_interval_bracket_contains_every_corner_realization():
    qi=(F(100),F(101));ti=[(F(100),F(101)),(F(101),F(102))]
    pi=[(F(101),F(103)),(F(100),F(104))]
    bracket=interval_repair_closures(F(100),qi,ti,pi)
    # Enumerate all32 endpoint worlds independently, including strict ties.
    for q,t0,t1,p0,p1 in product(qi,*ti,*pi):
        actual=set(least_repair_closure(F(100),q,[t0,t1],[p0,p1])['repairs'])
        assert set(bracket['forced']['repairs'])<=actual<=set(bracket['possible']['repairs'])


def test_scalar_cross_repairs_and_core_restoration_are_not_hidden_by_labels():
    result=audit_unique_repair_responses([96,97],[96,99],[[100,104],[101,105]])
    assert not result['unique_source_value_mapping_holds']
    assert len(result['core_alternative_restoration'])==1
    assert len(result['off_diagonal_alternative_restoration'])==2


def test_stable_witness_assumptions_are_separate_from_closure_recurrence():
    result=stable_witness_assumptions(100,5,105,[96,97],101,[99,104])
    assert not result['all_numeric_assumptions']
    assert not result['checks']['core_and_repairs_stably_near_cap']


def test_packing_ceiling_handles_divisible_and_remainder_cases():
    # Nine mutually spaced candidates: with M0=1,p4 exactly2 updates are
    # guaranteed, while M0=0 requires3. No extra update follows at equality.
    args=dict(h=F(1,4),beta=1,dimension=2,delta=F(2,25),profiles_per_item=4)
    assert frontier_neutral_grid_bound(**args,initial_profiles=1)['guaranteed_updates']==2
    assert frontier_neutral_grid_bound(**args,initial_profiles=0)['guaranteed_updates']==3
    assert frontier_neutral_grid_bound(**args,initial_profiles=9)['guaranteed_updates']==0
    with pytest.raises(ValueError,match='accepted witness'):
        frontier_neutral_grid_bound(F(1,4),1,2,F(2,25),0,0)
