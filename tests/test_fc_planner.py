from fractions import Fraction as F

import numpy as np

from wowfs.experiments.fc_planner import (
    G, inspect_plan, optimal_value_sequence, plan_context, scalar_bands,
)


def context(ratio='1'):
    r=float(ratio);B=np.array([1-.044*r,2*(1-.044*r)])
    c=np.array([r,2*r]);ctx={
        'context_id':'abstract', 'class':'abstract', 'faction':'none','race':'none',
        'race_label':'none','physical_stat':'abstract','native_racial_incomplete':False,
        'U':1.,'U_eff':1/r,'B':B.tolist(),'c':c.tolist(),'s_q':[1.,2.],
        'caps':[1.05,2.10],'binding_effective_task':'a','tasks':['a','b'],
        'affinity_validated':True,'regimes':{}}
    for name,xs in [('large_gap',[0,.0001,.0002,.0003,.044]),('dense',[0,.011,.022,.033,.044])]:
        ctx['regimes'][name]={'partner_coefficients':xs,
                            'values':(B+np.array(xs)[:,None]*c).tolist()}
    return ctx


def test_disconnected_response_bands_need_more_than_a_global_peak_floor():
    xs=[0,'.011','.022','.033','.044']
    bands=scalar_bands(xs,F('.96'),F('.0502'),rule='budget12')
    values=optimal_value_sequence(bands)
    assert len(values)==3
    assert int((max(b['upper'] for b in bands)-1)//G)==4
    assert values==list(map(F,['1.02832','1.03832','1.04832']))


def test_context_scale_is_used_for_exact_and_weaker_direct_paths():
    c=context('1.05');plan=plan_context(c,[.5,.5])
    seq={s['name']:s for s in plan['sequences']}
    assert seq['large_gap']['continuous_utility_upper']==5
    assert seq['dense']['continuous_utility_upper']==2
    assert seq['weaker_direct']['continuous_utility_upper']==5
    assert np.isclose(seq['weaker_direct']['minimum_primary_coefficient'],.01/1.05)
    assert all(r['value_legacy_pass'] for r in seq['weaker_direct']['rows'])
    # With both synthetic tasks equally binding, the tighter minimum primary
    # excludes a middle partner's repair. Value capacity must not hide its L failure.
    assert not seq['dense']['rows'][0]['checks']['L']
    assert not seq['dense']['value_legacy_capacity_exactly_matched']


def test_every_old_partner_and_prior_primary_is_in_source_checks():
    c=context();rows,prefix=inspect_plan(c,'dense',[.05218,.05165,.05120],'budget12',[.5,.5])
    assert prefix==3
    assert len(rows[-1]['source_masses'])==9  # 5 old partners, old primary, 3 new primaries.
    assert all(v==1 for v in rows[-1]['source_masses'].values())
    for step,row in enumerate(rows,1):
        assert np.shape(row['admission_mask'])==(step+1,5)
        assert all(row['admission_mask'][0])


def test_inadmissible_new_source_remains_a_failed_attempt_without_mask_repair():
    c=context();rows,prefix=inspect_plan(c,'dense',[.0545],'budget12',[.5,.5])
    assert prefix==0
    assert not any(rows[0]['admission_mask'][-1])
    assert not rows[0]['checks']['N'] and not rows[0]['checks']['G']
    assert rows[0]['checks']['H']


def test_nonaffine_context_is_not_given_a_continuous_native_prediction():
    c=context();c['affinity_validated']=False
    plan=plan_context(c,[.5,.5])
    for s in plan['sequences']:
        assert s['continuous_utility_upper'] is None
        assert s['achieved_value_legacy_lower'] is None
        if s['variant']=='exact':assert s['execution_plan']=='exact_not_run_nonaffine'
