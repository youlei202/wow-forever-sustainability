"""Independent arithmetic and all-subset checks for inherited-event inference."""
import itertools
import unittest

import numpy as np
from scipy.stats import t

from wowfs.experiments.co_sensitivity import InheritedTable, shift_interval


def table(values, nl=3, nr=2, e=.13, h=.83, g=.071):
    nc, nq = np.asarray(values).shape; n = 1000; alpha = .003125
    family = nq * (2 * nc * nc + nc)
    rows = [[f'l{i}', f'r{j}', 'p'] for i, j in itertools.product(range(nl), range(nr))]
    record = {'claim_id': 'unit', 'N': n, 'configuration_order': rows,
              'reference_configuration_indices_by_task': [0] * nq,
              'task_order': [f'q{i}' for i in range(nq)]}
    claim = {'core_bounds_manifest': {'paired_seeds': n, 'configurations': nc, 'tasks': nq,
        'family_size': family, 'alpha': alpha, 'critical_value': float(t.isf(alpha / (2 * family), n - 1)),
        'gain': g, 'tolerance': e, 'cap': 1 + h}}
    return InheritedTable(np.asarray(values, dtype=float), np.zeros((nq, nc, nc)), record, claim)


def independent_feasible(data, selected, history, e, h, g, rho):
    rows = [i for i, row in enumerate(data.rows) if set(row[:2]) <= selected]
    old = [i for i, row in enumerate(data.rows) if set(row[:2]) <= history]
    if not rows or not old:
        return False
    front = np.max(data.mean[rows], axis=0); previous = np.max(data.mean[old], axis=0)
    if np.any(front > (1 + h) * data.reference):
        return False
    for item in selected:
        incident = [i for i in rows if item in data.rows[i][:2]]
        good = 0 if not incident else np.count_nonzero(np.max(data.mean[incident], axis=0) >= front - e * data.reference)
        if good / data.nq < rho:
            return False
    return np.count_nonzero(front >= previous + g * data.reference) / data.nq >= .5


class InheritedSensitivityTests(unittest.TestCase):
    def test_sign_aware_interval_sum(self):
        self.assertEqual(shift_interval(2, 3, 4, 5, 7), (22, 31))
        self.assertEqual(shift_interval(2, 3, -4, 5, 7), (-26, -17))
        self.assertEqual(shift_interval(2, 3, 0, 5, 7), (2, 3))

    def test_every_joint_realization_is_covered(self):
        rng = np.random.default_rng(826)
        for _ in range(1000):
            l, u = sorted(rng.normal(size=2)); sl, su = sorted(rng.normal(size=2)); a = rng.normal()
            lo, hi = shift_interval(l, u, a, sl, su)
            for c, s in itertools.product([l, u], [sl, su]):
                self.assertLessEqual(lo, c + a * s + 1e-12)
                self.assertGreaterEqual(hi, c + a * s - 1e-12)

    def test_diagonal_reference_bounds(self):
        d = table([[10, 13], [11, 14], [12, 10], [13, 12], [11, 16], [16, 11]])
        self.assertTrue(np.all(d.ref_lower <= [10, 13]))
        self.assertTrue(np.all(d.ref_upper >= [10, 13]))
        self.assertTrue(np.all(d.ref_upper - d.ref_lower < 1e-7))
        for q in range(2):
            self.assertEqual(len(d.reference_records[q]['derived_from']), 12)

    def test_pruning_and_witnesses_against_independent_complete_subsets(self):
        rng = np.random.default_rng(493170)
        counts = {'YES': 0, 'NO': 0}
        for _ in range(300):
            values = rng.integers(7, 19, size=(6, 2)).astype(float); values[0] = [10, 10]
            d = table(values)
            e, h, g = .13, .83, .071
            history = {'l0', 'r0'}
            target = set(rng.choice(['l1', 'l2', 'r1'], size=int(rng.integers(4)), replace=False))
            answer = d.decide(d.mask(history), d.mask(target), d.bounds(e, h, g))
            truth = False
            for size in range(4):
                for additions in itertools.combinations(['l1', 'l2', 'r1'], size):
                    selected = history | set(additions)
                    if target <= selected and independent_feasible(d, selected, history, e, h, g, .5):
                        truth = True
            if answer['status'] == 'YES':
                counts['YES'] += 1
                self.assertTrue(truth)
                self.assertTrue(independent_feasible(d, set(answer['witness']['items']), history, e, h, g, .5))
            elif answer['status'] == 'NO':
                counts['NO'] += 1
                self.assertFalse(truth)
            else:
                self.fail(f"Strict-gap deterministic test unexpectedly unresolved: {answer}")
        self.assertGreater(counts['YES'], 10)
        self.assertGreater(counts['NO'], 10)

    def test_invalid_history_is_not_no_completion(self):
        d = table([[10, 10], [18, 18], [17, 17], [12, 12], [12, 12], [12, 12]])
        ans = d.decide(d.mask(['l0', 'l1', 'r0']), 0, d.bounds(.13, .83, .071), 1.)
        self.assertEqual(ans['status'], 'INVALID_INITIAL')


if __name__ == '__main__':
    unittest.main()
