import numpy as np
import pytest

from wowfs.experiments.r6_geometry import line_segment, segment_certificate
from wowfs.experiments.r6_capacity import forbidden_interval, optimal_prefix_designs


def test_cube_contains_whole_neutral_segment_not_only_center():
    a=np.array([[-1,0],[1,0],[0,-1],[0,1]])
    b=np.array([0,2,0,2])
    endpoints=line_segment(a,b,[0,1,1],2)
    np.testing.assert_allclose(endpoints,[[0,2],[2,0]])
    behavior=np.array([[0,0],[1,0],[0,1]])
    certificate=segment_certificate(a,b,endpoints,behavior,.1,1,2)
    assert certificate['beta']==2
    assert certificate['grid_candidates']==7
    assert certificate['T_guaranteed']==3
    with pytest.raises(ValueError,match='violates'):
        segment_certificate(a,b,[[-1,3],[3,-1]],behavior,.1,1,2)


def test_full_archive_cost_changes_guarantee():
    a=[[-1],[1]]
    b=[0,1]
    endpoints=[[0],[1]]
    behavior=[[0],[1]]
    one=segment_certificate(a,b,endpoints,behavior,.1,1,1)
    many=segment_certificate(a,b,endpoints,behavior,.1,3,4)
    assert one['T_guaranteed']==3
    assert many['T_guaranteed']==1
    assert len(one['grid_theta'])==4


def test_capacity_upper_bound_and_robust_construction():
    start=np.array([0.,.2]);direction=np.array([1.,0.]);old=np.array([1.,.2])
    interval=forbidden_interval(start,direction,old,.21)
    assert interval==pytest.approx((.79,1.))
    result=optimal_prefix_designs(start,direction,old,.21)
    assert result['exact_fitted_continuous_capacity']==4
    values=[start+direction*x for x in result['segment_t']]
    for i,v in enumerate(values):
        assert max(abs(v-old))>.21
        assert all(max(abs(v-w))>.21 for w in values[:i])
    # Five points would require span .84 within the allowable prefix .79.
    assert 4*.21>result['allowed_prefix_endpoint']


def test_capacity_rejects_unsupported_disconnected_domain():
    with pytest.raises(ValueError,match='suffix'):
        optimal_prefix_designs(np.array([0.]),np.array([1.]),np.array([.5]),.1)
