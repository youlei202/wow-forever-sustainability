import numpy as np

from wowfs.experiments.r4_feasibility import FiniteProblem, evaluate_admission
from wowfs.experiments.r4_support import minimum_support_bound, old_retention_box, one_gear_box_candidates, sparsify_feasible_release


def fixture(values, behavior, sources, **kwargs):
    values=np.asarray(values,float)
    return FiniteProblem(values,np.asarray(behavior,float),sources,[0],['a','b'],['old'],
        np.full(values.shape[-1],100.),np.full(values.shape[-1],105.),**kwargs)


def test_support_bound_excludes_novel_but_self_dominated_policy():
    # A novel low-output policy on singleton a cannot witness D while that
    # same gear's unnovel stronger policy is legal. The joint gear can.
    v=np.array([[[100],[100]],[[95],[104]],[[99],[99]]])
    b=np.zeros((*v.shape,1));b[1,0,0,0]=.1;b[2,:,:,0]=.1
    p=fixture(v,b,[{'old'},{'a'},{'a','b'}])
    result=minimum_support_bound(p)
    assert result['minimum_release_size_lower_bound']==2
    assert result['attaining_relaxed_releases']==[['a','b']]


def test_weighted_support_lower_bound_requires_union_when_one_task_is_not_enough():
    v=np.array([[[100,100]],[[99,50]],[[50,99]]])
    b=np.zeros((*v.shape,1));b[1:,:,:,0]=.1
    p=fixture(v,b,[{'old'},{'a'},{'b'}],min_mass=.75)
    assert minimum_support_bound(p)['minimum_release_size_lower_bound']==2


def test_old_only_box_certifies_all_obligations_without_candidate_reoptimization():
    v=np.array([[[100,100]],[[99,99]],[[104,104]]])
    b=np.zeros((*v.shape,1));b[1:,:,:,0]=.1
    p=fixture(v,b,[{'old'},{'a','b'},{'a','b'}],k_max=1)
    box=old_retention_box(p)
    assert box['constructed'] and box['upper']==[105.,105.]
    for candidate in one_gear_box_candidates(p,box):
        mask=p.protected.copy();mask[candidate['gear_index']]=True
        assert evaluate_admission(p,mask)['joint_pass']


def test_old_only_box_does_not_certify_an_already_unsafe_H():
    v=np.array([[[106]],[[99]]]);b=np.zeros((*v.shape,1));b[1]=.1
    p=fixture(v,b,[{'old'},{'a','b'}])
    assert old_retention_box(p)=={'constructed':False,'reason':'protected_power'}


def test_witness_sparsification_removes_released_items_but_preserves_joint_constraints():
    v=np.array([[[100]],[[99]],[[99]],[[99]]])
    b=np.zeros((*v.shape,1));b[1:]=.1
    p=FiniteProblem(v,b,[{'old'},{'a'},{'b'},{'c'}],[0],['a','b','c'],['old'],[100.],[105.],k_max=1)
    result=sparsify_feasible_release(p,[True]*4)
    assert result['metrics']['joint_pass']
    assert len(result['new_sources']) < 3
    assert len(result['new_sources']) <= result['upper_bound']


def test_complete_coequipment_diagonal_requires_all_source_specific_new_items():
    # Independent enumeration of every admitted candidate subset, not a MILP
    # answer used to test another MILP. This is abstract evidence only.
    from itertools import product
    m=3
    old=[set()]+[{f's{i}'} for i in range(m)]
    new=[{f's{i}',f'a{j}'} for i in range(m) for j in range(m)]
    values=np.array([100.]+[96.]*m+[104. if i==j else 96. for i in range(m) for j in range(m)])[:,None,None]
    behavior=np.zeros((*values.shape,1))
    for i in range(m):behavior[1+m+i*m+i]=.1
    minimum=m+1; feasible_count=0
    for bits in product((False,True),repeat=m*m):
        release=set.union(set(),*[set(ss)-{f's{i}'for i in range(m)} for ss,keep in zip(new,bits) if keep])
        if not release:continue
        available=[i for i,ss in enumerate(new) if (ss & {f'a{j}' for j in range(m)}) <= release]
        domain=list(range(1+m))+[1+m+i for i in available]
        p=FiniteProblem(values[domain],behavior[domain],old+[new[i] for i in available],
            list(range(1+m)),release,[f's{i}'for i in range(m)],[100.],[105.],k_max=1)
        mask=[True]*(1+m)+[bits[i] for i in available]
        if evaluate_admission(p,mask)['joint_pass']:
            feasible_count+=1;minimum=min(minimum,len(release))
            assert sparsify_feasible_release(p,mask)['metrics']['joint_pass']
    assert feasible_count > 0 and minimum==m
