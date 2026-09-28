"""Synthetic finite-table tests; none count as native research observations."""
import numpy as np
import pytest

from wowfs.experiments.r4_data import Ecology
from wowfs.experiments.value_history import decision_gain, deletion_records
from wowfs.experiments.value_sequences import solve_sequences
from wowfs.experiments.value_theory import completion_sequence, inspect_completion_sequence
from fractions import Fraction


def ecology():
    values = np.array([[[100.], [99.]], [[99.], [102.]], [[104.], [95.]]])
    behavior = np.zeros((3, 2, 1, 7))
    behavior[1] = .1
    behavior[2] = .2
    return Ecology(pool={'id':'synthetic'}, race='test', tasks=[{'id':'task'}],
        policies=['p0','p1'], gear_ids=['old','a','b'], gears=[{}, {}, {}],
        values=values, behavior=behavior, samples=np.repeat(values[...,None],2,axis=-1),
        sources=[{'old'}, {'old','a'}, {'old','b'}], initial=np.array([True,False,False]),
        new_items=('a','b'), scale=np.array([100.]), cap=np.array([105.]),
        protected_sources=('old',), config={})


def test_gain_reoptimizes_both_old_and_new_policies_and_deletes_new_source():
    e = ecology(); p, _ = e.problem(['a'])
    mask = np.ones(len(p.gear_ids), bool)
    result = decision_gain(p, mask)
    assert result['old_reoptimized'] == [100.]
    assert result['new_reoptimized'] == [102.]
    assert result['normalized_gain'] == pytest.approx([.02])
    assert result['G']
    deletion = deletion_records(p, mask, ['a'])[0]
    assert deletion['without_source_reoptimized'] == [100.]
    assert deletion['deletion_effect'] == [2.]


def test_sequence_gain_is_against_current_old_library_not_initial_anchor():
    result = solve_sequences(ecology())
    assert result['max_successful_updates'] == 2
    assert [x['new_batch'] for x in result['selected_sequence']] == [['a'], ['b']]
    assert result['selected_sequence'][1]['old_reoptimized'] == [102.]
    assert result['selected_sequence'][1]['normalized_gain'] == pytest.approx([.02])
    after_b = next(x for x in result['transitions'] if x['previously_released']==['b'])
    assert after_b['new_batch'] == ['a']
    assert after_b['normalized_gain'] == [0.]
    assert not after_b['joint_with_G']


def test_exact_additive_class_has_positive_gain_and_damage_share_novelty():
    model = completion_sequence('.05', '.01', '.05', partner_damage='.1')
    rows = inspect_completion_sequence(model)
    assert len(rows) == 5
    assert all(all(r['checks'].values()) for r in rows)
    assert [r['gain'] for r in rows] == [Fraction(1, 100)] * 5
    assert [r['novelty'] for r in rows] == [Fraction(1, 20)] * 5
    assert rows[-1]['legal_gears'] == 12
    assert rows[-1]['admitted_gears'] == 7
    assert rows[-1]['optimum'] == Fraction(21, 20)
    # The companion is reward-weaker than the old one, yet removing it makes
    # every new primary exceed the cap. This checks actual deletion value.
    old_partner = sum(model['partners']['old_partner'])
    assert all(sum(channels)+old_partner > 1+model['headroom']
               for name,channels in model['primaries'].items() if name != 'old_primary')
    # Removing the cap reverses its decision role: the old partner improves
    # every primary's reward by .1, with exactly zero pair interaction.
    assert old_partner > sum(model['partners']['weak_partner'])


def test_exact_class_keeps_gain_and_behavior_bounds_distinct():
    power_limited = completion_sequence('.05', '.02', '.05', partner_damage='.1')
    behavior_limited = completion_sequence('.8', '.01', '.3', partner_damage='.9')
    assert power_limited['count'] == 2
    assert behavior_limited['count'] == 3
    assert all(all(r['checks'].values()) for r in inspect_completion_sequence(behavior_limited))


def test_future_completion_summary_needs_retention_reserve_and_every_point():
    cap, h, e, step = map(Fraction, ('1', '.02', '.05', '.005'))
    frontier = cap-h
    n = 1+(e-h)//step
    old = [frontier-(n-1-i)*step for i in range(n)]
    assert n == 7
    assert max(old) == frontier  # One option suffices for current utility.
    for i, own in enumerate(old):
        future = cap-own
        full = max([frontier]+[x+future for x in old if x+future<=cap])
        assert full == cap
        compressed = max([frontier]+[x+future for j,x in enumerate(old)
                                     if j!=i and x+future<=cap])
        assert full-compressed >= step
        # Every old source retains its actual old option within relevance;
        # summary compression is not a physical permission to delete H.
        assert all(x >= full-e for x in old)
    assert 1+(e-e)//step == 1  # No old-source spread from this proof if h=e.
