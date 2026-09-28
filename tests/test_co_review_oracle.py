"""Independent exact-mask auditor versus the direct rational definition."""
from dataclasses import replace
from fractions import Fraction
from itertools import combinations
import random
import unittest

from wowfs.experiments.co_exact import Model, exhaustive, evaluate
from wowfs.experiments.co_review_oracle import ExactMaskOracle


class ExactReviewOracleTests(unittest.TestCase):
    def test_160_boundary_rich_models_against_direct_all_subsets(self):
        rng = random.Random(871293)
        cases = 0
        for trial in range(160):
            left = ['a' + str(i) for i in range(rng.randint(2, 4))]
            right = ['x' + str(i) for i in range(rng.randint(1, 3))]
            q = rng.randint(1, 3)
            weights = [Fraction(1, q)] * q
            rows = [dict(support=[a, x], values=[str(Fraction(rng.randint(0, 8), 3)) for _ in range(q)])
                    for a in left for x in right if (a, x) == (left[0], right[0]) or rng.random() > .1]
            model = Model.from_dict(dict(slots={**{a: 0 for a in left}, **{x: 1 for x in right}},
                configurations=rows, weights=list(map(str, weights)), tolerance=[str(Fraction(rng.randint(0, 4), 3))] * q,
                cap=[str(Fraction(rng.randint(4, 10), 3))] * q, gain=[str(Fraction(rng.randint(1, 3), 3))] * q,
                required_mass=str(Fraction(rng.randint(0, q), q)), gain_mass=str(Fraction(rng.randint(1, q), q)),
                history=[left[0], right[0]]))
            fixed = None if trial % 3 else tuple(Fraction(rng.randint(1, 8), 3) for _ in range(q))
            oracle = ExactMaskOracle(model, fixed_y=fixed)
            value = replace(model, required_mass=Fraction(0))
            for retention, reference_model, solutions in [(True, model, oracle.valid), (False, value, oracle.value_valid)]:
                direct = exhaustive(reference_model, fixed_y=fixed, all_solutions=True)
                represented = {frozenset(name for i, name in enumerate(oracle.names) if p >> i & 1) for p in solutions}
                self.assertEqual(represented, {frozenset(x) for x in direct.get('solutions', [])})
                for target in ([], [left[-1]], [right[-1]], [left[-1], right[-1]]):
                    answer = oracle.query(target, retention=retention)
                    expected = exhaustive(reference_model, target, fixed_y=fixed)
                    self.assertEqual(answer['status'], expected['status'])
                    if answer['status'] == 'YES':
                        self.assertTrue(evaluate(reference_model, answer['items'], fixed_y=fixed)['valid'])
                    cases += 1
        self.assertEqual(cases, 1280)

    def test_sub_float_ulp_strict_boundary_is_preserved(self):
        model = Model.from_dict(dict(slots={'a0': 0, 'a1': 0, 'x0': 1},
            configurations=[dict(support=['a0', 'x0'], values=['1']),
                            dict(support=['a1', 'x0'], values=['1.000000000000000000000000000001'])],
            weights=['1'], tolerance=['0'], required_mass='1', history=['a0', 'x0'],
            cap=['2'], gain=['0.000000000000000000000000000001'], gain_mass='1'))
        oracle = ExactMaskOracle(model)
        self.assertEqual(oracle.query(['a1'])['status'], 'NO')
        self.assertEqual(oracle.query(['a1'], retention=False)['status'], 'YES')

    def test_unknown_target_is_rejected(self):
        model = Model.from_dict(dict(slots={'a': 0, 'x': 1}, configurations=[dict(support=['a', 'x'], values=['1'])],
            weights=['1'], tolerance=['0'], required_mass='1', history=['a', 'x'], cap=['2'], gain=['1'], gain_mass='1'))
        with self.assertRaisesRegex(ValueError, 'Unknown target'):
            ExactMaskOracle(model).query(['missing'])


if __name__ == '__main__':
    unittest.main()
