"""Independent arithmetic and state/edge checks; these are synthetic test data."""
import itertools
import json
import unittest
import numpy as np
from scipy.stats import t
from wowfs.experiments.oe_inference import FiniteBounds


class FiniteBoundsTests(unittest.TestCase):
    def test_each_interval_matches_paired_covariance_formula(self):
        rng=np.random.default_rng(45)
        shared=rng.normal(size=(2,19))
        samples=100+8*shared[None]+rng.normal(size=(3,2,19))
        reference=100+5*shared+.2*rng.normal(size=(2,19))
        bounds=FiniteBounds(samples,reference,.013,.04,1.08,.0125)
        self.assertEqual(bounds.family_size,2*(2*3*3+3))
        expected_critical=t.isf(.0125/(2*bounds.family_size),18)
        self.assertAlmostEqual(bounds.critical,expected_critical)
        for q,i,j,offset in itertools.product(range(2),range(3),range(3),(.013,-.04)):
            matrix=np.cov(np.array([samples[i,q],samples[j,q],reference[q]]),ddof=1)
            coefficients=np.array([1.,-1.,-offset])
            variance=float(coefficients@matrix@coefficients)
            mean=samples[i,q].mean()-samples[j,q].mean()-offset*reference[q].mean()
            radius=expected_critical*np.sqrt(max(0,variance)/19)
            self.assertAlmostEqual(bounds.pairs[offset][0][q,i,j],mean-radius,places=10)
            self.assertAlmostEqual(bounds.pairs[offset][1][q,i,j],mean+radius,places=10)
        cap=1.08*reference[None]-samples
        np.testing.assert_allclose(bounds.cap_mean,cap.mean(axis=-1))
        np.testing.assert_allclose(bounds.cap_lower,
            cap.mean(axis=-1)-expected_critical*cap.std(axis=-1,ddof=1)/np.sqrt(19))

    def test_exact_zero_standard_error_is_a_point_interval(self):
        reference=np.array([[80.,88.,96.,104.]])
        samples=np.array([reference,1.125*reference,1.25*reference])
        bounds=FiniteBounds(samples,reference,.125,0.,1.,.05)
        np.testing.assert_array_equal(bounds.pairs[.125][0][:,1,0],0.)
        np.testing.assert_array_equal(bounds.pairs[.125][1][:,1,0],0.)
        np.testing.assert_array_equal(bounds.cap_lower[0],0.)
        np.testing.assert_array_equal(bounds.cap_upper[0],0.)
        # Shared noise is not counted twice as if two designs were independent.
        b=FiniteBounds(np.array([reference,reference+2]),reference,0.,0.,2.,.05)
        np.testing.assert_array_equal(b.pairs[0.][0][:,1,0],[2.])
        np.testing.assert_array_equal(b.pairs[0.][1][:,1,0],[2.])

    def test_frontier_extrema_against_explicit_rectangular_enumeration(self):
        rng=np.random.default_rng(919)
        samples=100+rng.normal(size=(4,2,17))
        reference=100+rng.normal(size=(2,17))
        bounds=FiniteBounds(samples,reference,.01,.03,1.1,.05)
        for left,right in [([0,3],[1,2]),([0],[0,1,2]),([0,1,2,3],[1])]:
            low,high=bounds.frontier_contrast(left,right,.01)
            for q in range(2):
                explicit_low=max(min(bounds.pairs[.01][0][q,i,j] for j in right) for i in left)
                explicit_high=min(max(bounds.pairs[.01][1][q,i,j] for i in left) for j in right)
                self.assertEqual(low[q],explicit_low)
                self.assertEqual(high[q],explicit_high)
        # Independent interval-box populations: all pairwise intervals hold for
        # each vector below, so max-minus-max must also be enclosed.
        means=np.array([3.,5.,4.,6.]);radii=np.array([1.,2.,.5,1.5])
        bounds.pairs[.01]=(np.repeat((means[:,None]-means[None,:]-1-radii[:,None]-radii[None,:])[None],2,axis=0),
                           np.repeat((means[:,None]-means[None,:]-1+radii[:,None]+radii[None,:])[None],2,axis=0))
        lo,hi=bounds.frontier_contrast([0,3],[1,2],.01)
        for signs in itertools.product((-1,0,1),repeat=4):
            values=means+np.array(signs)*radii
            contrast=values[[0,3]].max()-values[[1,2]].max()-1
            self.assertLessEqual(lo[0],contrast)
            self.assertGreaterEqual(hi[0],contrast)

    def test_full_joint_configuration_power_and_source_incidence(self):
        # a0b0,a1b0,a0b1,a1b1: each isolated update is below 110,
        # but the physically legal new-new configuration reaches 112.
        samples=np.repeat(np.array([[100.],[104.],[104.],[112.]])[:,:,None],8,axis=2)
        reference=np.full((1,8),100.)
        bounds=FiniteBounds(samples,reference,.01,.2,1.1,.05)
        incidence={'a0':[0,2],'a1':[1,3],'b0':[0,1],'b1':[2,3]}
        result=bounds.evaluate([0,1,2,3],incidence,[1.],1.)
        self.assertFalse(result['checks']['power']['upper'])
        self.assertTrue(result['checks']['retention']['lower'])
        self.assertEqual(result['stateconfig_indices'],[0,1,2,3])
        missing=bounds.evaluate([0,1],incidence,[1.],1.)
        self.assertFalse(missing['sources']['b1']['upper'])
        self.assertEqual(missing['sources']['b1']['reason'],'source_absent_from_state')
        json.dumps(missing,allow_nan=False)

    def test_multitask_retention_and_gain_mass_are_not_scalarized(self):
        samples=np.repeat(np.array([[100.,10.],[101.,110.],[110.,11.]])[:,:,None],8,axis=2)
        bounds=FiniteBounds(samples,samples[0],.05,.02,20.,.05)
        incidence={'old':[0,1],'new':[2],'shared':[0,1,2]}
        transition=bounds.transition([0],[0,1,2],incidence,.5,weights=[.5,.5],retention_mass=.5)
        self.assertTrue(transition['lower'])
        self.assertEqual(transition['sources']['old']['mass']['lower'],.5)
        self.assertEqual(transition['sources']['new']['mass']['lower'],.5)
        self.assertEqual(transition['checks']['gain']['mass']['lower'],1.)
        stricter=bounds.transition([0],[0,1,2],incidence,.5,weights=[.5,.5],retention_mass=1.)
        self.assertFalse(stricter['upper'])

    def test_optimistic_edge_can_survive_when_mean_gain_fails(self):
        samples=np.array([[[100.,100.,100.,100.]],[[90.,110.,90.,130.]]])
        bounds=FiniteBounds(samples,samples[0],.1,.5,10.,.05)
        result=bounds.transition([0],[0,1],{'old':[0],'new':[1]},1.,retention_mass=1.)
        self.assertFalse(result['checks']['gain']['mean'])
        self.assertTrue(result['checks']['gain']['upper'])
        self.assertTrue(result['upper'])
        self.assertFalse(result['lower'])
        self.assertEqual(result['statistical_status'],'unresolved')
        removed=bounds.transition([0],[1],{'new':[1]},1.,retention_mass=1.)
        self.assertFalse(removed['upper'])
        self.assertEqual(removed['checks']['history']['removed_configuration_indices'],[0])

    def test_validation_prevents_missing_cells_unbudgeted_offsets_and_weight_drift(self):
        samples=np.full((2,2,5),100.)
        b=FiniteBounds(samples,samples[0],.01,.05,1.1,.05)
        with self.assertRaises(ValueError): b.frontier_contrast([0],[1],.02)
        with self.assertRaises(ValueError): b.evaluate([0],{'s':[0]},[1.,1.],.5)
        with self.assertRaises(ValueError): b.evaluate([0],{},[.5,.5],.5)
        with self.assertRaises(ValueError): b.frontier_contrast([0],[],.01)
        with self.assertRaises(ValueError): b.evaluate([0],{'s':[2]},[.5,.5],.5)
        with self.assertRaises(ValueError): b.evaluate([True],{'s':[0]},[.5,.5],.5)
        bad=samples.copy();bad[0,0,1]=np.nan
        with self.assertRaises(ValueError): FiniteBounds(bad,samples[0],.01,.05,1.1,.05)
        with self.assertRaises(ValueError): FiniteBounds(samples,samples[0,:,:2],.01,.05,1.1,.05)
        samples[:]=999.
        self.assertEqual(b.samples[0,0,0],100.)


if __name__=='__main__':
    unittest.main()
