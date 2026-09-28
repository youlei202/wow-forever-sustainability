from dataclasses import replace
import pytest
from wowfs.experiments.oe_planning import build_domain, evenly_spaced, matched_first_steps, weighted_greedy
from wowfs.experiments.oe_solver import exact_capacity


def observed(joint=False):
    world={'world_id':'test','mechanism_id':'joint_slots' if joint else 'test',
        'context':{},'model_scope':'joint_two_update_slots' if joint else 'fixed_partners_multi_task',
        'initial_candidate_ids':[0],'initial_partner_ids':[0] if joint else [0,1],
        'all_physical_crosses_legal':True,'tasks':[{'task_id':'q0'},{'task_id':'q1'}],
        'policies':['native'],'candidates':[{'research_alias':f'a{i:02}'} for i in range(5)],
        'partners':[{'research_alias':f'x{j}'} for j in range(2)]}
    rows=[]
    for i in range(5):
        for j in range(2):
            for q in range(2):
                rows.append(dict(candidate_id=f'a{i:02}',partner_id=f'x{j}',task_id=f'q{q}',policy_id='native',
                    candidate_index=i,partner_index=j,task_index=q,policy_index=0,dps_mean=100+2*i+j+q,
                    dps_se=.1))
    return world,rows


def test_thinning_is_index_fixed_and_keeps_all_crosses():
    w,r=observed();p,d=build_domain(w,r,max_candidates=2)
    assert d['retained_row_ids']==['a00','a01','a04']
    assert d['removed_for_oracle_row_ids']==['a02','a03']
    assert len(p.configurations)==6
    assert len(p.items)-len(p.initial_items)==2
    assert d['reference_mapping'][0]['partner_id']=='x1'
    assert d['reference_mapping'][0]['candidate_id']=='a00'
    assert d['reference_mapping'][0]['development_mean']==101
    assert evenly_spaced(list(range(16)),12)[-1]==15


def test_joint_initial_reference_and_candidate_budget():
    w,r=observed(True);p,d=build_domain(w,r,max_candidates=3)
    assert p.initial_items==frozenset(('a00','x0'))
    assert d['reference_mapping'][0]['partner_id']=='x0'
    assert d['retained_partner_ids']==['x0','x1']
    assert len(p.items)-len(p.initial_items)==3
    assert any(c.items==frozenset(('a04','x1')) for c in p.configurations)


def test_incomplete_cross_is_not_masked_or_imputed():
    w,r=observed()
    with pytest.raises(ValueError,match='incomplete observed Cartesian'):build_domain(w,r[:-1])
    with pytest.raises(ValueError,match='Missing fixed evaluation task'):
        build_domain(w,[x for x in r if x['task_id']=='q0'])


def test_weight_sweep_changes_scoring_only():
    w,r=observed();p,d=build_domain(w,r)
    p=replace(p,gain=.01,cap=1.1,tolerance=.1)
    sol=weighted_greedy(p,(0,1))
    assert sol['feasibility_weights']==(.5,.5)
    assert sol['capacity_lower']<=exact_capacity(p).capacity


def test_matched_first_keeps_unselected_action_in_candidate_pool():
    w,r=observed()
    for row in r:
        if row['candidate_index']==2:row['dps_mean']-=2 # a01 and a02 exactly match
    p,d=build_domain(w,r);p=replace(p,gain=.01,cap=1.1,tolerance=.1)
    first,pairs=matched_first_steps(p,'test',{'g':.01,'h':.1,'e':.1},5,12)
    assert len(first)==4
    pair=next(x for x in pairs if set(x['first_a']+x['first_b'])=={'a01','a02'})
    assert pair['max_task_frontier_difference']==0
    assert pair['same_candidate_pool_including_unchosen_first_action']
    a=next(x for x in first if x['batch']==('a01',))
    assert 'a02' not in a['initial_items_after_first']
    assert a['retaining_continuation']['total_item_budget']==4


def test_task_weights_follow_registry_task_ids_without_renormalizing():
    w,r=observed();w['tasks']=[{'task_id':'q1'},{'task_id':'q0'}];w['task_weights']=[.2,.8]
    p,d=build_domain(w,r)
    assert p.task_weights==(.8,.2)
    w['task_weights']=[.1,.8]
    with pytest.raises(ValueError,match='sum to one'):build_domain(w,r)

def test_value_cache_diagnostics_use_current_retention_tolerance():
    from wowfs.experiments.oe_planning import analyze_world
    w,r=observed();result=analyze_world(w,r,12,5)
    rows=[x for x in result['planning'] if x['g']==.005 and x['h']==.1]
    by_e={x['e']:x['methods']['exact_B1_value'] for x in rows}
    assert by_e[.01]['batches']==by_e[.05]['batches']
    a=by_e[.01]['source_margins'][0]['a00'];b=by_e[.05]['source_margins'][0]['a00']
    assert b-a==pytest.approx(.04)
