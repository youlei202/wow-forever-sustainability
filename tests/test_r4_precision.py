import numpy as np
import pytest
from wowfs.experiments.r4_precision_analysis import paired_behavior_lower_bounds,pool_rows


def test_common_block_variation_cancels_in_paired_reference_distance():
    # Large block-specific variation shared by all choices must not make a
    # deterministic between-choice difference uncertain. Different policy and
    # task centers also expose accidental movement of the leading block axis.
    base=np.zeros((4,2,3,7))
    for gear in range(4):
        for policy in range(2):
            for task in range(3):
                base[gear,policy,task,0]=.02*gear+.01*policy+.01*task
    for policy in range(2):
        for task in range(3):base[1,policy,task,0]=.3+.02*policy+.01*task
    noise=np.random.default_rng(59281).normal(0,2,(8,1,1,3,7))
    blocks=base[None,...]+noise
    pooled=blocks.mean(axis=0)
    bounds=paired_behavior_lower_bounds(blocks,pooled,[True,False,True,True],1,100.)
    # Closest old policy has coordinate .07+.01*task, so distances are .23/.25.
    np.testing.assert_allclose(bounds,[[.23]*3,[.25]*3],atol=1e-12,rtol=0)


def test_unshared_block_variation_reduces_the_distance_lower_bound():
    pooled=np.zeros((2,1,1,1));pooled[1]=.2
    shared=np.arange(8,dtype=float)[:,None,None,None,None]
    blocks=np.broadcast_to(pooled,(8,*pooled.shape)).copy()+shared
    before=paired_behavior_lower_bounds(blocks,pooled,[True,False],1,2.)
    blocks[:,1,0,0,0]+=np.linspace(-1,1,8)
    after=paired_behavior_lower_bounds(blocks,pooled,[True,False],1,2.)
    assert before[0,0]==pytest.approx(.2)
    assert after[0,0] < before[0,0]


def test_pooling_rebuilds_damage_shares_and_treats_absent_actions_as_zero():
    rows=[{'iterations':2,'dps_samples':[4.,6.],
           'actions':{'white':{'damage':10.,'casts':2.,'fraction':1.}},'resources':[]},
          {'iterations':2,'dps_samples':[8.,12.],
           'actions':{'white':{'damage':10.,'casts':2.,'fraction':.5},
                      'proc':{'damage':10.,'casts':1.,'fraction':.5}},'resources':[]}]
    pooled=pool_rows(rows)
    assert pooled['dps_mean']==7.5
    assert pooled['actions']['white']['fraction']==pytest.approx(2/3)
    assert pooled['actions']['proc']['fraction']==pytest.approx(1/3)
    assert pooled['actions']['proc']['casts']==.5
    rows[1]['iterations']=3
    with pytest.raises(ValueError,match='equal-size'):pool_rows(rows)
