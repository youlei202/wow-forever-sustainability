"""Synthetic regression fixtures for analysis; these are not native results."""
import numpy as np
import pytest

from wowfs.experiments.r6_neutral_analysis import analyze_rows


def panel(order, white, common_block_noise):
    rows = []
    for block, noise in enumerate(common_block_noise):
        for design, channel in zip(order, white):
            total = 100. if design == 'old' else 98.
            samples = total + np.array([-5., -1., 0., 0., 1., 5.])
            rows.append({'design_id': design, 'block': block,
                         'dps_samples': samples.tolist(), 'dps_mean': total,
                         'actions': {
                             'otherId:OtherActionAttack': {'damage': 180 * (channel + noise)},
                             'spellId:999': {'damage': 180 * (total - channel - noise)},
                         }})
    return rows


def test_common_block_variation_cancels_in_paired_behavior_and_utility():
    order = ['old', 'new']
    rows = panel(order, [50., 40.], [-20., -15., -10., -5., 5., 10., 15., 20.])
    result = analyze_rows(rows, order, f0=100., epsilon=5., delta=.08, cap=110.)
    comparison = result['behavior_comparisons'][0]
    # Individual action means vary strongly between blocks, but the paired
    # physical contrast is exactly (-10,0,0,0,+8) DPS in every block.
    assert comparison['simultaneous_linf_lower'] == pytest.approx(.1)
    assert max(comparison['coordinate_standard_errors']) < 1e-15
    assert result['rows'][0]['paired_difference_lower'] == pytest.approx(-2.)
    assert result['rows'][0]['paired_difference_upper'] == pytest.approx(-2.)
    assert result['all_joint_supported']
    assert result['utility_df'] == 47
    assert result['behavior_df'] == 7


def test_all_history_checked_even_when_latest_predecessor_is_distant():
    order = ['old', 'first', 'second', 'returns_near_first']
    rows = panel(order, [50., 35., 65., 36.], [0.] * 8)
    result = analyze_rows(rows, order, f0=100., epsilon=5., delta=.1, cap=110.)
    last = result['rows'][-1]
    assert result['confirmed_updates'] == 2
    assert last['min_full_archive_distance'] == pytest.approx(.01)
    assert not last['D_supported']
    comparisons = [r for r in result['behavior_comparisons']
                   if r['candidate'] == order[-1]]
    assert {r['comparator'] for r in comparisons} == set(order[:-1])
    assert next(r for r in comparisons if r['comparator'] == 'second')['point_linf'] > .1
    assert result['utility_family'] == 7
    assert result['behavior_family'] == 30


def test_unpaired_behavior_noise_is_not_cancelled():
    order = ['old', 'new']
    rows = panel(order, [50., 40.], [0.] * 8)
    for row, extra in zip((r for r in rows if r['design_id'] == 'new'),
                          [-20., -15., -10., -5., 5., 10., 15., 20.]):
        row['actions']['otherId:OtherActionAttack']['damage'] += 180 * extra
        row['actions']['spellId:999']['damage'] -= 180 * extra
    result = analyze_rows(rows, order, f0=100., epsilon=5., delta=.08, cap=110.)
    assert result['rows'][0]['min_full_archive_distance'] == pytest.approx(.1)
    assert not result['rows'][0]['D_supported']
    assert result['confirmed_updates'] == 0
