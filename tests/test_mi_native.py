"""Target semantics audit tests with nonmonotone helper publications."""
import unittest

from wowfs.experiments.mi_native import (
    closure, low_order_analysis, maximal, projected_interface, status_from_membership,
    compile_event, enumerate_publications,
)
from wowfs.experiments.co_native_analysis import finite_bounds
from test_co_certificate_service import cyclic_certificate
from test_co_native_analysis import toy_world, toy_moments
import numpy as np


class MinimalInterfaceNativeTests(unittest.TestCase):
    def test_helper_joint_maximality(self):
        self.assertEqual(maximal([0b001, 0b111]), [0b111])
        result = projected_interface([0b001, 0b111], ['h', 'a', 'b'], 0b001)
        self.assertEqual(result['maximal_target_masks'], [0b11])
        self.assertEqual(result['witnesses'][0]['publication'], ['h', 'a', 'b'])
        self.assertEqual(result['projection_merge_count'], 0)

    def test_triple_miss_and_unknown_blocking(self):
        family = [True] * 7 + [False]
        statuses = ['YES'] * 7 + ['NO']
        exact, certified, rows, misses = low_order_analysis(family, statuses, 3)
        self.assertEqual(exact, [7]); self.assertEqual(certified, [7])
        self.assertEqual([row['certified_false_positive_count'] for row in rows], [1, 1, 0])
        statuses[3] = 'UNKNOWN'
        _, certified, rows, _ = low_order_analysis(family, statuses, 3)
        self.assertEqual(certified, [])
        self.assertEqual(rows[1]['unknown_blocked_cases'], 1)
        self.assertEqual(rows[1]['certified_false_positive_count'], 0)

    def test_empty_obstruction_and_invalid_initial(self):
        _, cert, rows, _ = low_order_analysis([False] * 4, ['NO'] * 4, 2)
        self.assertEqual(cert, [0])
        self.assertEqual(rows[0]['exact_false_positive_count'], 0)
        ex, cert, rows, _ = low_order_analysis([False] * 4, ['INVALID_INITIAL'] * 4, 2, exact_initial_valid=False)
        self.assertEqual(ex, []); self.assertEqual(cert, [])
        self.assertIsNone(rows[0]['exact_false_positive_count'])

    def test_closure_excludes_full_triple(self):
        self.assertEqual(closure([0b011, 0b101, 0b110], 3), [True] * 7 + [False])

    def test_incomplete_possible_no_and_initial_gate(self):
        initial = dict(supported='valid', possible='valid')
        self.assertEqual(status_from_membership(False, False, initial), 'NO')
        self.assertEqual(status_from_membership(False, False, initial, complete=False), 'UNKNOWN')
        self.assertEqual(status_from_membership(False, False, dict(supported='retention', possible='valid')), 'UNKNOWN_INITIAL')
        self.assertEqual(status_from_membership(True, True, dict(supported='retention', possible='retention')), 'INVALID_INITIAL')

    def test_independent_masks_and_exhaustion(self):
        world = toy_world(3, 2, 1)
        means = np.array([[20, 16, 24, 16, 16, 22]], dtype=float)
        moments = toy_moments(world, means, None, n=100)
        rule = dict(tolerance='.25', headroom='.25', gain='.15', retention_mass='1', gain_mass='1')
        frozen = cyclic_certificate()
        rebuilt = compile_event(world, moments, finite_bounds(moments, rule, .0025), rule, 'base')
        self.assertEqual(rebuilt, frozen['replay_certificate'])
        publications, initial = enumerate_publications(rebuilt)
        self.assertEqual(initial, frozen['initial'])
        self.assertEqual(len(publications), frozen['examined_publications'])
        self.assertIn(31, [row['publication'] for row in publications if row['modes']['supported']['reason'] == 'valid'])


if __name__ == '__main__':
    unittest.main()
