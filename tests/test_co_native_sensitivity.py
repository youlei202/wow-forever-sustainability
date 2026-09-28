import unittest
from fractions import Fraction

import numpy as np

from wowfs.experiments.co_native_analysis import finite_bounds
from wowfs.experiments.co_native_sensitivity import propagate_tolerance, reference_bounds


class SecondaryToleranceTests(unittest.TestCase):
    def setUp(self):
        self.rule = dict(tolerance='0.01', headroom='0.10', gain='0.01', retention_mass='1/2', gain_mass='1/2')
        self.mean = np.array([[10., 10.2, 10.4, 10.6], [20., 20.8, 20.4, 20.2]])
        moments = dict(means=self.mean, covariance=np.array([np.eye(4), np.eye(4)]) * .001,
                       N=10000, reference_indices=[0, 0], domain={'pairs': [(0, 0), (0, 1), (1, 0), (1, 1)]})
        self.bounds = finite_bounds(moments, self.rule, .0025)

    def test_reference_is_derived_from_both_original_diagonal_families(self):
        lo, hi, proof = reference_bounds(self.bounds, self.rule)
        self.assertTrue(np.all(lo < [10, 20])); self.assertTrue(np.all(hi > [10, 20]))
        self.assertEqual({p['family'] for p in proof}, {'gain', 'retention'})

    def test_all_new_true_directions_remain_covered(self):
        for multiplier in ['1/2', '1', '2', '5']:
            b, rule = propagate_tolerance(self.bounds, self.rule, multiplier)
            e = .01 * float(Fraction(multiplier))
            truth = self.mean[:, :, None] - self.mean[:, None, :] + e * self.mean[:, 0, None, None]
            self.assertTrue(np.all(b['retention_lower'] <= truth))
            self.assertTrue(np.all(b['retention_upper'] >= truth))
            self.assertIs(b['cap_lower'], self.bounds['cap_lower'])
            self.assertIs(b['gain_upper'], self.bounds['gain_upper'])
            self.assertEqual(b['manifest']['new_alpha'], 0.)

    def test_negative_shift_uses_upper_reference_in_lower_endpoint(self):
        b, _ = propagate_tolerance(self.bounds, self.rule, '1/2')
        sl, su, _ = reference_bounds(self.bounds, self.rule)
        expected = self.bounds['retention_lower'] - .005 * su[:, None, None]
        self.assertTrue(np.all(b['retention_lower'] <= expected))
        self.assertTrue(np.all(np.abs(b['retention_lower'] - expected) < 1e-10))


if __name__ == '__main__':
    unittest.main()
