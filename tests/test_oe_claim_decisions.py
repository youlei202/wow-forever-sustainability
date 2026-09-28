from copy import deepcopy
import pytest
from wowfs.paths import canonical_hash
from wowfs.experiments.oe_claim_decisions import decide


def joint_example():
    claim={'claim_id':'local','world_id':'w','role':'local','finding_id':'joint',
           'alpha':.00625,'iterations':32768,'joint_pair':['a01','x1']}
    result={'claim_id':'local','world_id':'w','pre_outcome_freeze_verified':True,
            'analysis_input_sha256':canonical_hash(claim),'task_order':['long','short'],
            'joint':dict.fromkeys(['both_single_component_pairs_cap_supported',
                'joint_pair_cap_excluded','separable_prediction_cap_supported',
                'positive_mixed_interaction_supported_any_task'],True)}
    return claim,result


def test_positive_interaction_alone_does_not_confirm_a_cap_decision():
    claim,result=joint_example()
    result['joint']['separable_prediction_cap_supported']=False
    assert decide(claim,result)['status']=='not_confirmed'


def test_wrong_outcome_or_changed_threshold_is_rejected():
    claim,result=joint_example()
    altered=deepcopy(claim);altered['headroom']=.07
    with pytest.raises(ValueError,match='hash'):decide(altered,result)
    result['world_id']='other'
    with pytest.raises(ValueError,match='identity'):decide(claim,result)


def test_unverified_freeze_cannot_be_called_confirmed():
    claim,result=joint_example()
    assert decide(claim,result)['status']=='confirmed_local'
    result['pre_outcome_freeze_verified']=False
    assert decide(claim,result)['status']=='not_confirmed'


def test_multiple_claim_types_must_not_silently_drop_conditions():
    claim,result=joint_example();claim['first_pair']=['a01','a02']
    with pytest.raises(ValueError,match='Exactly one'):decide(claim,result)
